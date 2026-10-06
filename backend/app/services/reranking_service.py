import re
from typing import List, Dict, Any, Tuple
from backend.app.config import settings

STOP_WORDS = {
    "what", "is", "the", "a", "an", "how", "to", "in", "of", "and", "for", "with",
    "does", "explain", "describe", "can", "you", "tell", "me", "about", "which", "are"
}

class RerankingService:
    def rerank(
        self,
        query: str,
        candidates: List[Dict[str, Any]],
        top_n: int = None,
        threshold: float = None
    ) -> Tuple[List[Dict[str, Any]], bool]:
        """
        Reranks top candidate chunks using semantic alignment, section relevance,
        exact phrase match boosting, and entity presence validation.
        Returns: (reranked_chunks, has_sufficient_evidence)
        """
        if not candidates:
            return [], False

        n = top_n or settings.RERANK_TOP_K
        thresh = threshold or settings.SIMILARITY_THRESHOLD
        query_lower = query.lower()
        query_words = set(re.findall(r"\b[a-z0-9\/\-_]+\b", query_lower))
        significant_query_words = [w for w in query_words if w not in STOP_WORDS and len(w) > 2]

        scored_candidates = []
        for c in candidates:
            base_score = c.get("score", 0.0)
            text_lower = c.get("chunk_text", "").lower()
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

            rerank_score = min(base_score + section_boost + ngram_boost, 1.0)
            c_copy = dict(c)
            c_copy["rerank_score"] = round(rerank_score, 4)
            scored_candidates.append(c_copy)

        scored_candidates.sort(key=lambda x: x["rerank_score"], reverse=True)
        top_chunks = scored_candidates[:n]

        if not top_chunks:
            return [], False

        top_score = top_chunks[0]["rerank_score"]
        # Basic score threshold check
        if top_score < thresh:
            return top_chunks, False

        # Entity presence validation:
        # If user is asking about specific distinctive entities (e.g. "ariba", "concur", "fieldglass"),
        # ensure that entity actually appears in the retrieved chunks.
        combined_text = " ".join([c["chunk_text"].lower() for c in top_chunks])
        for word in significant_query_words:
            # If a distinct product name is not found anywhere in top chunks, evidence is insufficient
            if word in {"ariba", "concur", "fieldglass", "hybris", "c4c", "qualtrics", "celonis"} and word not in combined_text:
                return top_chunks, False

        return top_chunks, True

reranking_service = RerankingService()
