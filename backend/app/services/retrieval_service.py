import re
import logging
from typing import List, Dict, Any, Optional, Tuple
from sqlalchemy.orm import Session
from sqlalchemy import func, desc

from backend.app.config import settings
from backend.app.models.chunk import DocumentChunk
from backend.app.services.embedding_service import embedding_service
from backend.app.services.reranking_service import reranking_service

logger = logging.getLogger(__name__)

STOP_WORDS = {
    "what", "is", "the", "a", "an", "how", "to", "in", "of", "and", "for",
    "with", "does", "do", "explain", "describe", "can", "you", "tell", "me",
    "about", "design", "first", "per", "and", "or", "as", "at", "by", "from",
    "this", "that", "these", "those", "have", "has", "had", "which", "are", "be"
}


class RetrievalService:
    @staticmethod
    def preprocess_query(query: str) -> str:
        # Normalize whitespace, keep relevant punctuation like hyphens and slashes (e.g. S/4HANA, T-Code)
        cleaned = re.sub(r"[ \t]+", " ", query).strip()
        return cleaned

    def _extract_lexical_tokens(self, query: str) -> List[str]:
        """Extract clean alphanumeric tokens safe for PostgreSQL to_tsquery."""
        raw_tokens = re.findall(r"\b[a-zA-Z0-9\-_/]+\b", query.lower())
        clean_tokens = []
        for t in raw_tokens:
            sanitized = t.replace("-", "").replace("/", "")
            if sanitized not in STOP_WORDS and len(sanitized) > 2:
                clean_tokens.append(sanitized)
        return clean_tokens

    def hybrid_search(
        self,
        db: Session,
        query: str,
        top_k: Optional[int] = None,
        document_filter: Optional[str] = None,
    ) -> List[Dict[str, Any]]:
        """Hybrid retrieval using PostgreSQL vector and full‑text search with RRF fusion.

        Retrieves a candidate pool (default settings.RRF_CANDIDATE_K = 30) for downstream reranking.
        Returns a list of candidate chunk dictionaries compatible with the existing pipeline.
        """
        k = top_k or settings.RRF_CANDIDATE_K
        processed_query = self.preprocess_query(query)
        logger.debug(f"Starting hybrid search for query: '{processed_query[:60]}...' (candidate_k={k})")

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
        logger.debug(f"Vector search retrieved {len(vec_hits)} candidate chunks")

        # 3️⃣ Lexical search using GIN full‑text index
        # 3a. Strict full-text search first
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

        # 3b. Robust fallback for long scenario questions where strict plainto_tsquery AND-logic drops hits
        if len(lex_hits) < 10:
            tokens = self._extract_lexical_tokens(processed_query)
            if tokens:
                or_expr = " | ".join(tokens[:10])
                try:
                    fallback_q = db.query(DocumentChunk, func.ts_rank_cd(
                        func.to_tsvector('english', DocumentChunk.chunk_text),
                        func.to_tsquery('english', or_expr)
                    ).label('lex_score'))
                    if document_filter:
                        fallback_q = fallback_q.filter(DocumentChunk.document_name == document_filter)
                    fallback_q = (
                        fallback_q.filter(func.to_tsvector('english', DocumentChunk.chunk_text).op('@@')(func.to_tsquery('english', or_expr)))
                        .order_by(desc('lex_score'))
                        .limit(k * 2)
                    )
                    fallback_hits = [(c, s) for c, s in fallback_q.all()]
                    if not lex_hits:
                        lex_hits = fallback_hits
                    else:
                        seen_ids = {c.id for c, _ in lex_hits}
                        for c, s in fallback_hits:
                            if c.id not in seen_ids:
                                lex_hits.append((c, s))
                                seen_ids.add(c.id)
                        lex_hits = lex_hits[:k * 2]
                except Exception as err:
                    logger.debug(f"Fallback tsquery search error: {err}")

        logger.debug(f"Lexical search retrieved {len(lex_hits)} candidate chunks")

        # 4️⃣ Reciprocal Rank Fusion (RRF)
        def rrf_fusion(vec_hits: List[DocumentChunk], lex_hits: List[tuple], denom: int = 60) -> List[Tuple[DocumentChunk, float]]:
            """
            Return a list of (DocumentChunk, rrf_score) tuples ordered by descending RRF score.
            """
            scores: Dict[str, float] = {}
            for rank, chunk in enumerate(vec_hits, start=1):
                scores[chunk.id] = scores.get(chunk.id, 0.0) + 1.0 / (denom + rank)
            for rank, (chunk, _) in enumerate(lex_hits, start=1):
                scores[chunk.id] = scores.get(chunk.id, 0.0) + 1.0 / (denom + rank)
            # Map IDs to chunks from both sources
            id_to_chunk: Dict[str, DocumentChunk] = {c.id: c for c in vec_hits}
            id_to_chunk.update({c.id: c for c, _ in lex_hits})
            # Select top-k by RRF score
            top_items = sorted(scores.items(), key=lambda x: x[1], reverse=True)[:k]
            fused = [(id_to_chunk[_id], score) for _id, score in top_items]
            return fused

        fused_with_scores = rrf_fusion(vec_hits, lex_hits, denom=60)
        logger.debug(f"RRF fusion produced {len(fused_with_scores)} candidates")

        # Normalize RRF scores relative to the highest RRF score in the current fused result set
        max_rrf_score = max((s for _, s in fused_with_scores), default=0.0)

        # 5️⃣ Build result dictionaries compatible with downstream code
        results: List[Dict[str, Any]] = []
        for chunk, rrf_score in fused_with_scores:
            normalized_score = (rrf_score / max_rrf_score) if max_rrf_score > 0 else 0.0
            results.append({
                "chunk_id": chunk.id,
                "document_id": chunk.document_id,
                "document_name": chunk.document_name,
                "page_number": chunk.page_number,
                "section": chunk.section or f"Page {chunk.page_number}",
                "chunk_text": chunk.chunk_text,
                "vector_score": None,
                "keyword_score": None,
                "rrf_score": rrf_score,
                "score": normalized_score,
                "retrieval_method": "hybrid_rrf",
            })
        return results

    def retrieve_and_rerank(
        self,
        db: Session,
        query: str,
        candidate_k: Optional[int] = None,
        final_k: Optional[int] = None,
        threshold: Optional[float] = None,
        document_filter: Optional[str] = None,
        enable_rerank: bool = True,
    ) -> Tuple[List[Dict[str, Any]], bool]:
        """
        Complete 2-stage retrieval pipeline:
        Stage 1: Vector Search + Lexical Search -> RRF fusion (Candidate Set)
        Stage 2: Reranker scoring -> Final Top-K Chunks

        Supports benchmark evaluation:
        - Baseline: enable_rerank=False (Vector + Lexical + RRF)
        - Proposed: enable_rerank=True (Vector + Lexical + RRF + Reranker)
        """
        r_k = candidate_k or settings.RRF_CANDIDATE_K
        f_k = final_k or settings.FINAL_TOP_K

        # Stage 1: Hybrid candidate retrieval via RRF
        candidates = self.hybrid_search(
            db=db,
            query=query,
            top_k=r_k,
            document_filter=document_filter
        )

        if not candidates:
            return [], False

        # Stage 2: Reranker stage (or fallback to RRF top-k if rerank disabled)
        if enable_rerank:
            return reranking_service.rerank(
                query=query,
                candidates=candidates,
                top_n=f_k,
                threshold=threshold
            )
        else:
            # Baseline mode (RRF only)
            baseline_chunks = candidates[:f_k]
            thresh = threshold if threshold is not None else settings.SIMILARITY_THRESHOLD
            has_sufficient = bool(baseline_chunks and (baseline_chunks[0].get("score", 0.0) >= thresh))
            return baseline_chunks, has_sufficient


retrieval_service = RetrievalService()
