import re
import numpy as np
from typing import List, Dict, Any, Optional
from sqlalchemy.orm import Session
from sqlalchemy import or_, func, desc

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
        document_filter: Optional[str] = None,
    ) -> List[Dict[str, Any]]:
        """Hybrid retrieval using PostgreSQL vector and full‑text search with RRF fusion.

        Returns a list of candidate chunk dictionaries compatible with the existing pipeline.
        """
        k = top_k or settings.TOP_K
        processed_query = self.preprocess_query(query)

        # 1️⃣ Compute query embedding via embedding service
        query_vector = embedding_service.embed_text(processed_query)

        # 2️⃣ Vector search (high‑recall) – fetch extra candidates for fusion
        vec_q = db.query(DocumentChunk)
        if document_filter:
            vec_q = vec_q.filter(DocumentChunk.document_name == document_filter)
        vec_q = (
            vec_q.order_by(DocumentChunk.embedding.op("<=>")(query_vector))
            .limit(k * 2)
        )
        vec_hits = vec_q.all()

        # 3️⃣ Lexical search using GIN full‑text index
        lex_q = db.query(DocumentChunk, func.ts_rank_cd(
            func.to_tsvector('english', DocumentChunk.chunk_text),
            func.plainto_tsquery('english', processed_query)
        ).label('lex_score'))
        if document_filter:
            lex_q = lex_q.filter(DocumentChunk.document_name == document_filter)
        lex_q = (
            lex_q.filter(func.to_tsvector('english', DocumentChunk.chunk_text).op('@@')(func.plainto_tsquery('english', processed_query)))
            .order_by(desc('lex_score'))
            .limit(k * 2)
        )
        lex_hits = [(c, s) for c, s in lex_q.all()]

        # 4️⃣ Reciprocal Rank Fusion (RRF)
        def rrf_fusion(vec_hits: List[DocumentChunk], lex_hits: List[tuple], denom: int = 60) -> List[DocumentChunk]:
            scores: Dict[str, float] = {}
            for rank, chunk in enumerate(vec_hits, start=1):
                scores[chunk.id] = scores.get(chunk.id, 0.0) + 1.0 / (denom + rank)
            for rank, (chunk, _) in enumerate(lex_hits, start=1):
                scores[chunk.id] = scores.get(chunk.id, 0.0) + 1.0 / (denom + rank)
            top_ids = sorted(scores.items(), key=lambda x: x[1], reverse=True)[:k]
            id_to_chunk: Dict[str, DocumentChunk] = {c.id: c for c in vec_hits}
            id_to_chunk.update({c.id: c for c, _ in lex_hits})
            return [id_to_chunk[_id] for _id, _ in top_ids]

        fused_chunks = rrf_fusion(vec_hits, lex_hits, denom=60)

        # 5️⃣ Build result dictionaries compatible with downstream code
        results: List[Dict[str, Any]] = []
        for chunk in fused_chunks:
            results.append({
                "chunk_id": chunk.id,
                "document_id": chunk.document_id,
                "document_name": chunk.document_name,
                "page_number": chunk.page_number,
                "section": chunk.section or f"Page {chunk.page_number}",
                "chunk_text": chunk.chunk_text,
                "vector_score": None,
                "keyword_score": None,
                "score": None,
            })
        return results

retrieval_service = RetrievalService()
