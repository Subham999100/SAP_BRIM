import re
from typing import List, Dict, Any


class GroundingService:

    @staticmethod
    def _contains_term(text: str, term: str) -> bool:
        """Match a term without accidental substring matches."""
        pattern = rf"(?<![a-z0-9]){re.escape(term.lower())}(?![a-z0-9])"
        return bool(re.search(pattern, text.lower()))

    @classmethod
    def align_citations(
        cls,
        answer: str,
        chunks: List[Dict[str, Any]],
        min_top_k: int = 1
    ) -> List[Dict[str, Any]]:
        """
        Aligns retrieved evidence chunks with claims and references in the generated answer.
        Filters out retrieved chunks that were neither referenced nor relevant to the final answer.
        """
        if not chunks or not answer:
            return []

        answer_lower = answer.lower()
        aligned = []

        for idx, chunk in enumerate(chunks):
            doc_name = (chunk.get("document_name") or "").lower()
            section = (chunk.get("section") or "").lower()
            chunk_text = (chunk.get("chunk_text") or "").lower()

            # Check 1: Explicit citation or document mention in the answer
            doc_mentioned = bool(doc_name and doc_name in answer_lower)
            section_mentioned = bool(section and len(section) > 4 and section in answer_lower)

            # Check 2: Content alignment based on distinctive term overlap
            chunk_tokens = set(re.findall(r"\b[a-z0-9\-_/]{4,}\b", chunk_text))
            chunk_tokens.difference_update({
                "this", "that", "with", "from", "have", "more", "also", "into", "than",
                "been", "each", "were", "when", "some", "such", "only", "other", "about",
                "which", "there", "their", "these", "those", "would", "could", "should"
            })
            overlap_count = sum(1 for token in chunk_tokens if token in answer_lower)
            overlap_ratio = overlap_count / max(len(chunk_tokens), 1)

            # A chunk is aligned if:
            # - It is explicitly cited/mentioned, OR
            # - It has substantial conceptual term overlap (>= 15% of key terms), OR
            # - It is the primary ranked evidence (idx < min_top_k) with a strong rerank score >= 0.60
            rerank_score = float(chunk.get("rerank_score", chunk.get("score", 0.0)))
            is_primary = (idx < min_top_k and rerank_score >= 0.60)

            if doc_mentioned or section_mentioned or overlap_ratio >= 0.15 or is_primary:
                aligned.append({
                    "document": chunk.get("document_name", "Unknown SAP Document"),
                    "page": chunk.get("page_number", 1),
                    "section": chunk.get("section"),
                    "score": rerank_score,
                    "snippet": (chunk.get("chunk_text") or "")[:280] + ("..." if len(chunk.get("chunk_text") or "") > 280 else "")
                })

        return aligned if aligned else [
            {
                "document": chunks[0].get("document_name", "Unknown SAP Document"),
                "page": chunks[0].get("page_number", 1),
                "section": chunks[0].get("section"),
                "score": float(chunks[0].get("rerank_score", chunks[0].get("score", 0.0))),
                "snippet": (chunks[0].get("chunk_text") or "")[:280] + ("..." if len(chunks[0].get("chunk_text") or "") > 280 else "")
            }
        ]

    @classmethod
    def evaluate_grounding(
        cls,
        query: str,
        answer: str,
        chunks: List[Dict[str, Any]],
        source_type: str = "knowledge_base"
    ) -> float:

        # Refusal = no grounding
        if source_type == "refusal":
            return 0.0

        # No evidence = no grounding
        if not chunks:
            return 0.0

        # ---------------------------------------------------------
        # 1. Retrieval quality
        # ---------------------------------------------------------
        rerank_scores = [
            float(c.get("rerank_score", c.get("score", 0.0)))
            for c in chunks
        ]

        top_score = max(rerank_scores) if rerank_scores else 0.0

        avg_score = (
            sum(rerank_scores) / len(rerank_scores)
            if rerank_scores
            else 0.0
        )

        retrieval_signal = (
            0.7 * top_score +
            0.3 * avg_score
        )

        # ---------------------------------------------------------
        # 2. Query-term coverage
        # ---------------------------------------------------------
        stop_words = {
            "what", "is", "the", "a", "an", "how", "to",
            "in", "of", "and", "for", "with", "does",
            "explain", "can", "you", "tell", "me", "about"
        }

        query_terms = [
            word.lower()
            for word in re.findall(
                r"\b[a-z0-9\/\-_]+\b",
                query.lower()
            )
            if word.lower() not in stop_words
            and len(word) > 1
        ]

        combined_chunk_text = " ".join(
            c.get("chunk_text", "")
            for c in chunks
        ).lower()

        if query_terms:
            matched_terms = sum(
                1
                for term in query_terms
                if cls._contains_term(
                    combined_chunk_text,
                    term
                )
            )

            coverage_signal = matched_terms / len(query_terms)
        else:
            coverage_signal = 1.0

        # ---------------------------------------------------------
        # 3. Answer grounding
        # ---------------------------------------------------------
        answer_terms = [
            word.lower()
            for word in re.findall(
                r"\b[a-z0-9\/\-_]{3,}\b",
                answer.lower()
            )
            if word.lower() not in stop_words
        ]

        if answer_terms:
            supported_terms = sum(
                1
                for term in answer_terms
                if cls._contains_term(
                    combined_chunk_text,
                    term
                )
            )

            answer_grounding_signal = (
                supported_terms / len(answer_terms)
            )
        else:
            answer_grounding_signal = 0.0

        # ---------------------------------------------------------
        # 4. Evidence corroboration
        # ---------------------------------------------------------
        corroboration_signal = min(
            1.0,
            len(chunks) / 3.0
        )

        # ---------------------------------------------------------
        # 5. Final grounding score
        # ---------------------------------------------------------
        raw_score = (
            0.40 * retrieval_signal +
            0.30 * coverage_signal +
            0.20 * answer_grounding_signal +
            0.10 * corroboration_signal
        )

        final_score = max(
            0.0,
            min(0.98, raw_score)
        )

        return round(float(final_score), 2)


grounding_service = GroundingService()