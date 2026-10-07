"""
Context Builder Service for SAP BRIM Copilot
Formats reranked document chunks, web sources, and conversation history
into structured, bounded, deterministic context blocks for INTERNAL LLM prompt consumption only.
This context represents internal evidence and is NEVER returned directly as a user-facing answer.
"""

import hashlib
import re
from typing import List, Dict, Any, Optional


class ContextBuilder:
    def __init__(
        self,
        default_max_chunks: int = 5,
        default_max_chunk_chars: int = 1500,
        default_max_total_chars: int = 8000,
        default_max_history_chars: int = 1500
    ):
        self.default_max_chunks = default_max_chunks
        self.default_max_chunk_chars = default_max_chunk_chars
        self.default_max_total_chars = default_max_total_chars
        self.default_max_history_chars = default_max_history_chars

    @staticmethod
    def _clean_text(text: str) -> str:
        """Normalizes whitespace and removes unwanted noise characters."""
        if not text:
            return ""
        cleaned = re.sub(r"[ \t]+", " ", text)
        cleaned = re.sub(r"\n{3,}", "\n\n", cleaned)
        return cleaned.strip()

    @staticmethod
    def _content_fingerprint(text: str) -> str:
        """Generates a normalized hash to detect duplicate chunks."""
        norm = re.sub(r"\s+", " ", text.lower().strip())
        return hashlib.sha256(norm.encode("utf-8")).hexdigest()

    def normalize_chunk(self, chunk: Dict[str, Any]) -> Dict[str, Any]:
        """
        Normalizes a candidate chunk dictionary while strictly preserving all existing metadata.
        """
        cleaned_text = self._clean_text(chunk.get("chunk_text", ""))
        return {
            "chunk_id": chunk.get("chunk_id", ""),
            "document_id": chunk.get("document_id", ""),
            "document_name": chunk.get("document_name") or chunk.get("document", "Unknown SAP Document"),
            "page_number": chunk.get("page_number") or chunk.get("page"),
            "section": chunk.get("section"),
            "chunk_text": cleaned_text,
            "vector_score": chunk.get("vector_score"),
            "keyword_score": chunk.get("keyword_score"),
            "rrf_score": chunk.get("rrf_score"),
            "score": chunk.get("score"),
            "rerank_score": chunk.get("rerank_score"),
            "retrieval_method": chunk.get("retrieval_method", "hybrid_rrf_rerank")
        }

    def build_context(
        self,
        evidence: List[Dict[str, Any]],
        source_type: str = "knowledge_base",
        business_data: Optional[Dict[str, Any]] = None,
        chat_history: Optional[List[Dict[str, str]]] = None,
        max_chunks: Optional[int] = None,
        max_chunk_chars: Optional[int] = None,
        max_total_chars: Optional[int] = None
    ) -> str:
        """
        Builds a deterministic, structured, and bounded context block.
        Separates Conversation History, Knowledge Evidence, and Business Data.
        """
        limit_chunks = max_chunks or self.default_max_chunks
        limit_chunk_len = max_chunk_chars or self.default_max_chunk_chars
        limit_total = max_total_chars or self.default_max_total_chars

        # -------------------------------------------------------------
        # 0. Conversation History Formatting (Bounded multi-turn memory)
        # -------------------------------------------------------------
        history_header = ""
        if chat_history:
            history_lines = []
            cur_hist_len = 0
            # Take up to last 6 messages
            for turn in chat_history[-6:]:
                role = "User" if turn.get("role") == "user" else "Assistant"
                c = self._clean_text(turn.get("content", ""))
                if role == "Assistant" and len(c) > 350:
                    c = c[:350].rstrip() + " ... [truncated]"
                line = f"{role}: {c}"
                if cur_hist_len + len(line) > self.default_max_history_chars:
                    break
                history_lines.append(line)
                cur_hist_len += len(line)

            if history_lines:
                history_content = "\n".join(history_lines)
                history_header = (
                    f"CONVERSATION HISTORY (RECENT TURNS):\n"
                    f"------------------------------------\n"
                    f"{history_content}\n\n"
                )

        if not evidence:
            return (
                f"{history_header}"
                "KNOWLEDGE EVIDENCE:\n"
                "No relevant document evidence was retrieved for this query.\n\n"
                "BUSINESS DATA:\n"
                "None provided for this query. (Document knowledge only)."
            )

        # -------------------------------------------------------------
        # 1. Web Source Formatting
        # -------------------------------------------------------------
        if source_type == "web":
            source_blocks = []
            seen_urls = set()
            for idx, item in enumerate(evidence[:limit_chunks], 1):
                url = item.get("url", "")
                if url and url in seen_urls:
                    continue
                if url:
                    seen_urls.add(url)

                title = item.get("title", "SAP Web Source")
                domain = item.get("domain", "")
                snippet = self._clean_text(item.get("snippet", ""))
                if len(snippet) > limit_chunk_len:
                    snippet = snippet[:limit_chunk_len].rstrip() + " ... [truncated]"

                header_lines = [f"SOURCE {idx}"]
                if title:
                    header_lines.append(f"Title: {title}")
                if domain:
                    header_lines.append(f"Domain: {domain}")
                if url:
                    header_lines.append(f"URL: {url}")
                header_lines.append(f"Evidence:\n{snippet}")
                source_blocks.append("\n".join(header_lines))

            knowledge_content = "\n\n".join(source_blocks)
            return (
                f"{history_header}"
                f"KNOWLEDGE EVIDENCE (WEB):\n"
                f"------------------------\n"
                f"{knowledge_content}\n\n"
                f"BUSINESS DATA:\n"
                f"-------------\n"
                f"None provided for this query. (Web source knowledge only)."
            )

        # -------------------------------------------------------------
        # 2. Private Knowledge Base Formatting
        # -------------------------------------------------------------
        source_blocks = []
        seen_fingerprints = set()
        seen_chunk_ids = set()
        current_total_len = 0
        source_counter = 1

        for raw_chunk in evidence:
            if source_counter > limit_chunks:
                break

            normalized = self.normalize_chunk(raw_chunk)
            chunk_id = normalized["chunk_id"]
            text = normalized["chunk_text"]

            if not text:
                continue

            # Deduplication
            if chunk_id and chunk_id in seen_chunk_ids:
                continue
            fp = self._content_fingerprint(text)
            if fp in seen_fingerprints:
                continue

            seen_chunk_ids.add(chunk_id)
            seen_fingerprints.add(fp)

            # Chunk truncation
            if len(text) > limit_chunk_len:
                text = text[:limit_chunk_len].rstrip() + " ... [truncated for context budget]"

            # Format source metadata headers deterministically
            headers = [f"SOURCE {source_counter}"]
            doc_name = normalized["document_name"]
            headers.append(f"Document: {doc_name}")

            section = normalized["section"]
            if section and section.strip() and section.strip() != "None":
                headers.append(f"Section: {section.strip()}")

            page = normalized["page_number"]
            if page is not None and str(page).isdigit() and int(page) > 0:
                headers.append(f"Page: {page}")

            score = normalized["rerank_score"] or normalized["score"]
            if score is not None:
                headers.append(f"Relevance Score: {score:.4f}")

            headers.append(f"Evidence:\n{text}")
            block = "\n".join(headers)

            # Total budget enforcement
            if current_total_len + len(block) > limit_total and source_blocks:
                break

            source_blocks.append(block)
            current_total_len += len(block)
            source_counter += 1

        knowledge_content = "\n\n".join(source_blocks) if source_blocks else "No evidence available."

        # -------------------------------------------------------------
        # 3. Business Data Section (Clean architectural boundary)
        # -------------------------------------------------------------
        if business_data:
            biz_lines = []
            for k, v in business_data.items():
                biz_lines.append(f"{k}: {v}")
            business_content = "\n".join(biz_lines)
        else:
            business_content = "None provided for this query. (Document knowledge only)."

        return (
            f"{history_header}"
            f"KNOWLEDGE EVIDENCE:\n"
            f"------------------\n"
            f"{knowledge_content}\n\n"
            f"BUSINESS DATA:\n"
            f"-------------\n"
            f"{business_content}"
        )


context_builder = ContextBuilder()
