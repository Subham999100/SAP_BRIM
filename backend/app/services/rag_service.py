import logging
from typing import Dict, Any, List
from sqlalchemy.orm import Session

from backend.app.config import settings
from backend.app.services.sap_classifier import sap_classifier
from backend.app.services.retrieval_service import retrieval_service
from backend.app.services.reranking_service import reranking_service
from backend.app.services.grounding_service import grounding_service
from backend.app.services.web_search_service import web_search_service
from backend.app.services.llm_service import llm_service

logger = logging.getLogger(__name__)

class RAGService:
    def process_query(self, db: Session, query: str) -> Dict[str, Any]:
        """
        Executes the full RAG pipeline:
        1. SAP domain classification
        2. Hybrid retrieval (vector + keyword)
        3. Reranking & threshold evaluation
        4. Context selection / Web fallback decision
        5. Answer synthesis
        6. Citations & Grounding evaluation
        """
        # STEP 1: Domain Restriction Validation
        is_sap, reason = sap_classifier.classify(query)
        if not is_sap:
            return {
                "answer": "I can only help with SAP and SAP-related topics.",
                "source_type": "refusal",
                "grounding_score": 0.0,
                "citations": [],
                "web_sources": []
            }

        # STEP 2: Private Knowledge Base Retrieval
        candidates = retrieval_service.hybrid_search(db, query, top_k=settings.TOP_K)
        top_chunks, has_sufficient_evidence = reranking_service.rerank(
            query,
            candidates,
            top_n=settings.RERANK_TOP_K,
            threshold=settings.SIMILARITY_THRESHOLD
        )

        # If knowledge base contains sufficient evidence
        if has_sufficient_evidence and top_chunks:
            answer = llm_service.generate_answer(query, top_chunks, source_type="knowledge_base")
            grounding = grounding_service.evaluate_grounding(query, answer, top_chunks, source_type="knowledge_base")

            citations = [
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
                "answer": answer,
                "source_type": "knowledge_base",
                "grounding_score": grounding,
                "citations": citations,
                "web_sources": []
            }

        # STEP 3: Web Fallback if enabled and KB has insufficient evidence
        if settings.WEB_FALLBACK_ENABLED:
            web_results = web_search_service.search_sap_authoritative(query)
            if web_results:
                answer = llm_service.generate_answer(query, web_results, source_type="web")
                web_evidence = [
                    {
                        "chunk_text": f"{w.get('title', '')} {w.get('snippet', '')}",
                        "score": 0.85,
                        "rerank_score": 0.85
                    }
                    for w in web_results
                ]
                grounding = grounding_service.evaluate_grounding(query, answer, web_evidence, source_type="web")

                return {
                    "answer": answer,
                    "source_type": "web",
                    "grounding_score": grounding,
                    "citations": [],
                    "web_sources": [
                        {
                            "title": w["title"],
                            "url": w["url"],
                            "domain": w["domain"],
                            "snippet": w["snippet"]
                        }
                        for w in web_results[:3]
                    ]
                }

        # STEP 4: Insufficient information everywhere
        return {
            "answer": "I couldn't find sufficient information about this in the available SAP knowledge base.",
            "source_type": "knowledge_base",
            "grounding_score": 0.0,
            "citations": [],
            "web_sources": []
        }

rag_service = RAGService()
