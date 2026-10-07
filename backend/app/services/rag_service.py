import json
import logging
from typing import Dict, Any, List, Optional, Tuple, Generator
from datetime import datetime, timezone
from sqlalchemy.orm import Session

from backend.app.config import settings
from backend.app.models.chat import Chat
from backend.app.models.message import Message
from backend.app.models.citation import Citation
from backend.app.models.web_source import WebSource
from backend.app.services.sap_classifier import sap_classifier
from backend.app.services.retrieval_service import retrieval_service
from backend.app.services.reranking_service import reranking_service
from backend.app.services.grounding_service import grounding_service
from backend.app.services.web_search_service import web_search_service
from backend.app.services.llm_service import llm_service

logger = logging.getLogger(__name__)


class RAGService:
    """
    Authoritative, unified RAG execution service.
    Orchestrates:
    1. SAP domain classification
    2. Multi-turn conversation context retrieval
    3. Hybrid retrieval (vector + keyword)
    4. Neural late-interaction reranking & threshold check
    5. Context preparation & Web fallback
    6. LLM answer synthesis (strictly LLM-only output)
    7. Claim-to-citation alignment & grounding evaluation
    8. Unified database persistence across standard and streaming queries
    """

    @staticmethod
    def get_recent_chat_history(db: Session, chat_id: Optional[str], limit: int = 6) -> List[Dict[str, str]]:
        """Retrieves recent conversation turns for multi-turn conversational grounding."""
        if not chat_id:
            return []
        try:
            messages = (
                db.query(Message)
                .filter(Message.chat_id == chat_id)
                .order_by(Message.created_at.asc(), Message.id.asc())
                .all()
            )
            history = []
            for m in messages:
                if m.role in ("user", "assistant") and m.content:
                    history.append({"role": m.role, "content": m.content})
            return history[-limit:]
        except Exception as e:
            logger.warning(f"Could not retrieve chat history for {chat_id}: {e}")
            return []

    def prepare_context_and_sources(
        self,
        db: Session,
        query: str,
        chat_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Executes domain classification, retrieval, reranking, and evidence gathering.
        Returns a structured preparation state ready for answer generation.
        """
        # STEP 1: Domain Restriction Validation
        is_sap, reason = sap_classifier.classify(query)
        if not is_sap:
            return {
                "status": "refusal",
                "answer": "I can only help with SAP and SAP-related topics.",
                "source_type": "refusal",
                "grounding_score": 0.0,
                "citations": [],
                "web_sources": [],
                "evidence": [],
                "chat_history": []
            }

        # STEP 2: Conversation Context (Multi-turn support)
        chat_history = self.get_recent_chat_history(db, chat_id, limit=6)

        # STEP 3: Private Knowledge Base Hybrid Retrieval + Neural Reranking
        candidates = retrieval_service.hybrid_search(db, query, top_k=settings.RRF_CANDIDATE_K)
        top_chunks, has_sufficient_evidence = reranking_service.rerank(
            query,
            candidates,
            top_n=settings.FINAL_TOP_K,
            threshold=settings.SIMILARITY_THRESHOLD
        )

        # STEP 4: Evidence Sufficiency Evaluation
        if has_sufficient_evidence and top_chunks:
            # Candidate citations for preliminary preview
            candidate_citations = [
                {
                    "document": c["document_name"],
                    "page": c["page_number"],
                    "section": c["section"],
                    "score": c["rerank_score"],
                    "snippet": c["chunk_text"][:280] + ("..." if len(c["chunk_text"]) > 280 else "")
                }
                for c in top_chunks
            ]
            return {
                "status": "ready",
                "source_type": "knowledge_base",
                "evidence": top_chunks,
                "candidate_citations": candidate_citations,
                "candidate_web_sources": [],
                "chat_history": chat_history
            }

        # STEP 5: Authoritative Web Fallback
        if settings.WEB_FALLBACK_ENABLED:
            web_results = web_search_service.search_sap_authoritative(query)
            if web_results:
                candidate_web_sources = [
                    {
                        "title": w["title"],
                        "url": w["url"],
                        "domain": w["domain"],
                        "snippet": w["snippet"]
                    }
                    for w in web_results[:3]
                ]
                return {
                    "status": "ready",
                    "source_type": "web",
                    "evidence": web_results,
                    "candidate_citations": [],
                    "candidate_web_sources": candidate_web_sources,
                    "chat_history": chat_history
                }

        # STEP 6: Insufficient Information Everywhere
        return {
            "status": "insufficient",
            "answer": "I couldn't find sufficient information about this in the available SAP knowledge base.",
            "source_type": "knowledge_base",
            "grounding_score": 0.0,
            "citations": [],
            "web_sources": [],
            "evidence": [],
            "chat_history": chat_history
        }

    def _persist_interaction(
        self,
        db: Session,
        chat_id: Optional[str],
        query: str,
        answer: str,
        source_type: str,
        grounding_score: float,
        citations: List[Dict[str, Any]],
        web_sources: List[Dict[str, Any]]
    ) -> Tuple[Optional[str], Optional[str]]:
        """
        Persists user message, assistant message, citations, and web sources consistently.
        Returns (assistant_message_id, chat_id).
        """
        if not chat_id:
            return None, None

        chat = db.query(Chat).filter(Chat.id == chat_id).first()
        if not chat:
            return None, None

        # Check if user message already logged to avoid double insertion
        last_msg = (
            db.query(Message)
            .filter(Message.chat_id == chat_id)
            .order_by(Message.created_at.desc())
            .first()
        )
        if not last_msg or last_msg.role != "user" or last_msg.content.strip() != query.strip():
            user_msg = Message(
                chat_id=chat_id,
                role="user",
                content=query.strip()
            )
            db.add(user_msg)
            # Auto-title chat on first turn
            if chat.title in ("New SAP Chat", "New Chat", "", None):
                words = query.strip().split()
                chat.title = " ".join(words[:6]) + ("..." if len(words) > 6 else "")

        # Create assistant message
        assistant_msg = Message(
            chat_id=chat_id,
            role="assistant",
            content=answer,
            source_type=source_type,
            grounding_score=grounding_score
        )
        db.add(assistant_msg)
        chat.updated_at = datetime.now(timezone.utc)
        db.commit()
        db.refresh(assistant_msg)

        # Persist citations
        if citations:
            for c in citations:
                db.add(Citation(
                    message_id=assistant_msg.id,
                    source_type="knowledge_base",
                    document_id="doc-" + str(c.get("document", "sap")),
                    document_name=c.get("document", "Unknown SAP Document"),
                    chunk_id="chunk-ref",
                    page_number=c.get("page", 1),
                    section=c.get("section"),
                    similarity_score=float(c.get("score", 0.0)),
                    citation_text=c.get("snippet", "")
                ))
            db.commit()

        # Persist web sources
        if web_sources:
            for w in web_sources:
                db.add(WebSource(
                    message_id=assistant_msg.id,
                    url=w.get("url", ""),
                    title=w.get("title", ""),
                    domain=w.get("domain", ""),
                    snippet=w.get("snippet", "")
                ))
            db.commit()

        db.refresh(assistant_msg)
        return assistant_msg.id, chat_id

    def process_query(
        self,
        db: Session,
        query: str,
        chat_id: Optional[str] = None,
        user_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Executes the synchronous RAG pipeline with full persistence and citation alignment.
        """
        prep = self.prepare_context_and_sources(db, query, chat_id)

        # Refusal or Insufficient Evidence
        if prep["status"] in ("refusal", "insufficient"):
            msg_id, c_id = self._persist_interaction(
                db=db,
                chat_id=chat_id,
                query=query,
                answer=prep["answer"],
                source_type=prep["source_type"],
                grounding_score=prep["grounding_score"],
                citations=prep["citations"],
                web_sources=prep["web_sources"]
            )
            return {
                "answer": prep["answer"],
                "source_type": prep["source_type"],
                "grounding_score": prep["grounding_score"],
                "citations": prep["citations"],
                "web_sources": prep["web_sources"],
                "chat_id": c_id,
                "message_id": msg_id
            }

        # Knowledge Base or Web Evidence Synthesis
        answer = llm_service.generate_answer(
            query=query,
            evidence=prep["evidence"],
            source_type=prep["source_type"],
            chat_history=prep["chat_history"]
        )

        if prep["source_type"] == "knowledge_base":
            aligned_citations = grounding_service.align_citations(answer, prep["evidence"])
            final_web_sources = []
            grounding = grounding_service.evaluate_grounding(
                query, answer, prep["evidence"], source_type="knowledge_base"
            )
        else:
            aligned_citations = []
            final_web_sources = prep["candidate_web_sources"]
            web_evidence = [
                {
                    "chunk_text": f"{w.get('title', '')} {w.get('snippet', '')}",
                    "score": 0.85,
                    "rerank_score": 0.85
                }
                for w in prep["evidence"]
            ]
            grounding = grounding_service.evaluate_grounding(
                query, answer, web_evidence, source_type="web"
            )

        msg_id, c_id = self._persist_interaction(
            db=db,
            chat_id=chat_id,
            query=query,
            answer=answer,
            source_type=prep["source_type"],
            grounding_score=grounding,
            citations=aligned_citations,
            web_sources=final_web_sources
        )

        return {
            "answer": answer,
            "source_type": prep["source_type"],
            "grounding_score": grounding,
            "citations": aligned_citations,
            "web_sources": final_web_sources,
            "chat_id": c_id,
            "message_id": msg_id
        }

    def stream_query(
        self,
        db: Session,
        query: str,
        chat_id: str,
        user_id: Optional[str] = None
    ) -> Generator[str, None, None]:
        """
        Executes genuine incremental provider streaming over SSE with consistent persistence.
        """
        prep = self.prepare_context_and_sources(db, query, chat_id)

        # Handle non-LLM immediate terminal outcomes
        if prep["status"] in ("refusal", "insufficient"):
            msg_id, _ = self._persist_interaction(
                db=db,
                chat_id=chat_id,
                query=query,
                answer=prep["answer"],
                source_type=prep["source_type"],
                grounding_score=prep["grounding_score"],
                citations=prep["citations"],
                web_sources=prep["web_sources"]
            )
            # SSE Metadata
            meta_payload = {
                "message_id": msg_id,
                "source_type": prep["source_type"],
                "grounding_score": prep["grounding_score"],
                "citations": prep["citations"],
                "web_sources": prep["web_sources"]
            }
            yield f"event: metadata\ndata: {json.dumps(meta_payload)}\n\n"
            yield f"event: token\ndata: {json.dumps({'token': prep['answer']})}\n\n"
            yield f"event: done\ndata: {json.dumps({'status': 'complete'})}\n\n"
            return

        # Preliminary preview metadata for immediate client display
        preliminary_meta = {
            "message_id": None,
            "source_type": prep["source_type"],
            "grounding_score": 0.85 if prep["source_type"] == "knowledge_base" else 0.75,
            "citations": prep.get("candidate_citations", []),
            "web_sources": prep.get("candidate_web_sources", [])
        }
        yield f"event: metadata\ndata: {json.dumps(preliminary_meta)}\n\n"

        # Stream incremental tokens from LLM provider
        tokens_accumulated = []
        for token in llm_service.stream_answer(
            query=query,
            evidence=prep["evidence"],
            source_type=prep["source_type"],
            chat_history=prep["chat_history"]
        ):
            tokens_accumulated.append(token)
            yield f"event: token\ndata: {json.dumps({'token': token})}\n\n"

        full_answer = "".join(tokens_accumulated).strip()
        if not full_answer:
            full_answer = "The AI reasoning service did not return content. Please retry your query."

        # Post-generation grounding and citation verification
        if prep["source_type"] == "knowledge_base":
            aligned_citations = grounding_service.align_citations(full_answer, prep["evidence"])
            final_web_sources = []
            grounding = grounding_service.evaluate_grounding(
                query, full_answer, prep["evidence"], source_type="knowledge_base"
            )
        else:
            aligned_citations = []
            final_web_sources = prep["candidate_web_sources"]
            web_evidence = [
                {
                    "chunk_text": f"{w.get('title', '')} {w.get('snippet', '')}",
                    "score": 0.85,
                    "rerank_score": 0.85
                }
                for w in prep["evidence"]
            ]
            grounding = grounding_service.evaluate_grounding(
                query, full_answer, web_evidence, source_type="web"
            )

        # Consistent database persistence
        msg_id, _ = self._persist_interaction(
            db=db,
            chat_id=chat_id,
            query=query,
            answer=full_answer,
            source_type=prep["source_type"],
            grounding_score=grounding,
            citations=aligned_citations,
            web_sources=final_web_sources
        )

        # Final metadata event with confirmed message ID and aligned citations
        final_meta = {
            "message_id": msg_id,
            "source_type": prep["source_type"],
            "grounding_score": grounding,
            "citations": aligned_citations,
            "web_sources": final_web_sources
        }
        yield f"event: metadata\ndata: {json.dumps(final_meta)}\n\n"
        yield f"event: done\ndata: {json.dumps({'status': 'complete'})}\n\n"


rag_service = RAGService()
