import re
import numpy as np
from typing import List, Dict, Any, Optional
from sqlalchemy.orm import Session
from sqlalchemy import or_

from backend.app.config import settings
from backend.app.models.chunk import DocumentChunk
from backend.app.services.embedding_service import embedding_service

class RetrievalService:
    @staticmethod
    def preprocess_query(query: str) -> str:
        # Normalize whitespace, keep relevant punctuation like hyphens and slashes (e.g. S/4HANA, T-Code)
        cleaned = re.sub(r"[ \t]+", " ", query).strip()
        return cleaned

    @staticmethod
    def _compute_keyword_score(query: str, text: str) -> float:
        """Computes BM25-inspired term frequency match with SAP acronym boosting."""
        text_lower = text.lower()
        # Extract query terms, ignoring common stop words
        stop_words = {"what", "is", "the", "a", "an", "how", "to", "in", "of", "and", "for", "with", "does", "do", "explain", "describe", "can", "you", "tell", "me", "about"}
        raw_tokens = re.findall(r"\b[a-z0-9\/\-_]+\b", query.lower())
        tokens = [t for t in raw_tokens if t not in stop_words and len(t) > 1]
        if not tokens:
            return 0.0

        matches = 0
        boosted_matches = 0
        for token in tokens:
            count = text_lower.count(token)
            if count > 0:
                matches += 1
                # Boost SAP codes / tables / tcodes (e.g. me21n, mara, bseg, fi, mm)
                if len(token) >= 4 or token in {"fi", "co", "mm", "sd", "pp", "qm", "pm", "hr"}:
                    boosted_matches += min(count, 3)

        coverage = matches / len(tokens)
        density = min(boosted_matches / 6.0, 1.0)
        return float(0.7 * coverage + 0.3 * density)

    def hybrid_search(
        self,
        db: Session,
        query: str,
        top_k: Optional[int] = None,
        document_filter: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        k = top_k or settings.TOP_K
        processed_query = self.preprocess_query(query)
        query_vector = np.array(embedding_service.embed_text(processed_query), dtype=np.float32)
        q_norm = np.linalg.norm(query_vector)

        # Base query for chunks
        query_set = db.query(DocumentChunk)
        if document_filter:
            query_set = query_set.filter(DocumentChunk.document_name == document_filter)

        all_chunks = query_set.all()
        if not all_chunks:
            return []

        scored_candidates = []
        for chunk in all_chunks:
            # 1. Vector similarity
            raw_emb = chunk.embedding
            if raw_emb is None:
                vec_sim = 0.0
            else:
                chunk_vector = np.array(raw_emb, dtype=np.float32)
                c_norm = np.linalg.norm(chunk_vector)
                if q_norm > 0 and c_norm > 0:
                    vec_sim = float(np.dot(query_vector, chunk_vector) / (q_norm * c_norm))
                else:
                    vec_sim = 0.0

            # Scale cosine sim (-1..1) to (0..1)
            normalized_vec_score = max(0.0, min(1.0, (vec_sim + 1.0) / 2.0))

            # 2. Keyword score
            keyword_score = self._compute_keyword_score(processed_query, chunk.chunk_text)

            # 3. Hybrid fusion score
            hybrid_score = 0.60 * normalized_vec_score + 0.40 * keyword_score

            scored_candidates.append({
                "chunk_id": chunk.id,
                "document_id": chunk.document_id,
                "document_name": chunk.document_name,
                "page_number": chunk.page_number,
                "section": chunk.section or f"Page {chunk.page_number}",
                "chunk_text": chunk.chunk_text,
                "vector_score": normalized_vec_score,
                "keyword_score": keyword_score,
                "score": hybrid_score
            })

        # Sort descending by hybrid score
        scored_candidates.sort(key=lambda x: x["score"], reverse=True)
        return scored_candidates[:k]

retrieval_service = RetrievalService()
