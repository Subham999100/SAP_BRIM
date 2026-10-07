import re
import logging
import numpy as np
from typing import List, Dict, Any, Tuple, Optional
from backend.app.config import settings

logger = logging.getLogger(__name__)

STOP_WORDS = {
    "what", "is", "the", "a", "an", "how", "to", "in", "of", "and", "for", "with",
    "does", "explain", "describe", "can", "you", "tell", "me", "about", "which", "are"
}


class RerankingService:
    def __init__(self):
        self._model = None
        self._model_failed = False
        self.model_name = settings.RERANKER_MODEL

    def _get_model(self):
        if not settings.RERANKER_ENABLED:
            return None
        if self._model is not None:
            return self._model
        if self._model_failed:
            return None

        # Attempt to load FastEmbed ONNX late-interaction (ColBERT) reranking model
        try:
            from fastembed import LateInteractionTextEmbedding
            logger.info(f"Loading neural reranker model ({self.model_name}) via FastEmbed ONNX runtime...")
            self._model = LateInteractionTextEmbedding(model_name=self.model_name)
            logger.info("Neural reranker model loaded successfully.")
            return self._model
        except Exception as e:
            logger.warning(
                f"Could not load neural reranker model ({self.model_name}): {e}. "
                "Will use robust heuristic scoring fallback."
            )
            self._model_failed = True
            return None

    def _score_with_model(
        self,
        query: str,
        candidates: List[Dict[str, Any]]
    ) -> Optional[List[float]]:
        """
        Computes late-interaction MaxSim relevance scores using the ONNX ColBERT model.
        Returns a list of float scores in [0.0, 1.0] corresponding to candidates,
        or None if model scoring fails.
        """
        model = self._get_model()
        if model is None:
            return None

        try:
            chunk_texts = [c.get("chunk_text", "") for c in candidates]
            # Embed query token representations: shape (q_tokens, dim)
            q_emb = list(model.embed([query]))[0]
            # Embed candidates token representations
            doc_embs = list(model.embed(chunk_texts))

            q_len = max(q_emb.shape[0], 1)
            raw_scores = []
            for d_emb in doc_embs:
                # MaxSim: dot product between query tokens and document tokens,
                # then max over document tokens, summed across query tokens
                sim_matrix = np.dot(q_emb, d_emb.T)
                maxsim = float(np.sum(np.max(sim_matrix, axis=1)))
                raw_scores.append(maxsim)

            # Normalize to approximately [0.0, 1.0] relative to query length
            # ColBERT token embeddings have L2 norm ~1, so max possible dot product per query token is ~1.0
            normalized = [min(max(s / q_len, 0.0), 1.0) for s in raw_scores]
            return normalized
        except Exception as e:
            logger.warning(f"Error during neural reranker scoring: {e}. Falling back to heuristic reranking.")
            return None

    def rerank(
        self,
        query: str,
        candidates: List[Dict[str, Any]],
        top_n: Optional[int] = None,
        threshold: Optional[float] = None
    ) -> Tuple[List[Dict[str, Any]], bool]:
        """
        Reranks candidate chunks from RRF fusion.
        1. Preserves all incoming metadata (chunk_id, document_name, rrf_score, page, section, etc.)
        2. Applies neural ColBERT reranking if available, with section and query phrase reinforcement.
        3. Falls back gracefully to heuristic/RRF scoring if the neural model is disabled or unavailable.
        4. Returns top_n items (default: settings.FINAL_TOP_K) and an evidence sufficiency boolean.
        """
        if not candidates:
            logger.debug("Reranker received 0 candidates.")
            return [], False

        n = top_n or settings.FINAL_TOP_K
        thresh = threshold if threshold is not None else settings.SIMILARITY_THRESHOLD
        query_lower = query.lower()
        query_words = set(re.findall(r"\b[a-z0-9\/\-_]+\b", query_lower))
        significant_query_words = [w for w in query_words if w not in STOP_WORDS and len(w) > 2]

        logger.debug(f"Reranking {len(candidates)} candidates for query: '{query[:60]}...' (target top_n={n})")

        # Attempt neural scoring
        neural_scores = self._score_with_model(query, candidates)
        used_neural = neural_scores is not None

        scored_candidates = []
        for idx, c in enumerate(candidates):
            c_copy = dict(c)
            base_score = float(c.get("score") or c.get("rrf_score") or 0.0)
            text_lower = (c.get("chunk_text") or "").lower()
            section_lower = (c.get("section") or "").lower()

            # Boost if section title directly matches query keywords
            section_matches = sum(1 for w in query_words if w in section_lower and len(w) > 2)
            section_boost = min(section_matches * 0.05, 0.15)

            # Boost if exact n-grams from query appear in text
            ngram_boost = 0.0
            if len(query_lower.split()) >= 2:
                words_list = query_lower.split()
                for i in range(len(words_list) - 1):
                    bigram = f"{words_list[i]} {words_list[i+1]}"
                    if bigram in text_lower and len(bigram) > 6:
                        ngram_boost += 0.04
            ngram_boost = min(ngram_boost, 0.12)

            if used_neural:
                n_score = neural_scores[idx]
                # Combine neural score with section relevance boost
                combined_score = min(n_score + section_boost * 0.5, 1.0)
                method = "hybrid_rrf_rerank"
            else:
                # Heuristic fallback: base RRF score + section boost + n-gram boost
                combined_score = min(base_score + section_boost + ngram_boost, 1.0)
                method = "hybrid_rrf_fallback"

            final_score = round(combined_score, 4)
            c_copy["rerank_score"] = final_score
            c_copy["score"] = final_score  # preserve backward compatibility
            c_copy["retrieval_method"] = method
            # Ensure rrf_score is present
            if "rrf_score" not in c_copy:
                c_copy["rrf_score"] = base_score

            scored_candidates.append(c_copy)

        # Sort descending by rerank score
        scored_candidates.sort(key=lambda x: x["rerank_score"], reverse=True)
        top_chunks = scored_candidates[:n]

        if not top_chunks:
            return [], False

        top_score = top_chunks[0]["rerank_score"]
        logger.debug(
            f"Reranking complete: {len(top_chunks)} final chunks selected (method={top_chunks[0]['retrieval_method']}). "
            f"Top reranker scores: {[c['rerank_score'] for c in top_chunks]}"
        )

        # Basic score threshold check
        if top_score < thresh:
            return top_chunks, False

        # Entity presence validation for distinctive products
        combined_text = " ".join([(c.get("chunk_text") or "").lower() for c in top_chunks])
        for word in significant_query_words:
            if word in {"ariba", "concur", "fieldglass", "hybris", "c4c", "qualtrics", "celonis"} and word not in combined_text:
                return top_chunks, False

        return top_chunks, True


reranking_service = RerankingService()
