import os
import re
import logging
from typing import List, Dict, Any, Generator

from backend.app.config import settings

logger = logging.getLogger(__name__)


SYSTEM_PROMPT = """You are an SAP Knowledge Assistant.

Your scope is strictly SAP and SAP-related topics.

Answer ONLY from the evidence supplied by the retrieval system.

Never invent facts.
Never use general pretrained knowledge as evidence.
Never claim that information exists in the private knowledge base unless the supplied evidence supports it.

For private knowledge-base answers:
- Give a concise, direct answer.
- Summarize the evidence instead of dumping document text.
- Preserve important SAP technical terms and definitions.
- Do not reproduce document headers, confidentiality notices, or unnecessary metadata.
- Do not mention information that is not supported by the retrieved evidence.

For web answers:
- Use only the supplied web evidence.
- Clearly indicate that the information came from web sources.

If the evidence is insufficient, explicitly say that the information could not be verified.

For non-SAP questions, refuse briefly.

Be precise, concise, factual, and evidence-grounded."""


class LLMService:

    def __init__(self):
        self.provider = settings.LLM_PROVIDER.lower()

        self.api_key = (
            settings.LLM_API_KEY
            or settings.GROQ_API_KEY
            or os.getenv("OPENAI_API_KEY", "")
        )

    # =========================================================
    # TEXT CLEANING
    # =========================================================

    @staticmethod
    def _clean_document_text(text: str) -> str:

        if not text:
            return ""

        cleaned = text

        cleaned = re.sub(
            r"CONFIDENTIAL\s*&\s*PROPRIETARY[^\n]*",
            "",
            cleaned,
            flags=re.IGNORECASE
        )

        cleaned = re.sub(
            r"SAP\s+S/4HANA\s+OFFICIAL\s+REFERENCE\s+MANUAL",
            "",
            cleaned,
            flags=re.IGNORECASE
        )

        cleaned = re.sub(
            r"Module:\s*[^\n]*",
            "",
            cleaned,
            flags=re.IGNORECASE
        )

        cleaned = re.sub(
            r"Document:\s*[^\n]*",
            "",
            cleaned,
            flags=re.IGNORECASE
        )

        cleaned = re.sub(
            r"[ \t]+",
            " ",
            cleaned
        )

        cleaned = re.sub(
            r"\n{3,}",
            "\n\n",
            cleaned
        )

        return cleaned.strip()

    # =========================================================
    # SENTENCE EXTRACTION
    # =========================================================

    @staticmethod
    def _extract_sentences(text: str) -> List[str]:

        if not text:
            return []

        text = re.sub(
            r"\s+",
            " ",
            text
        ).strip()

        sentences = re.split(
            r"(?<=[.!?])\s+",
            text
        )

        cleaned = []

        for sentence in sentences:

            sentence = sentence.strip()

            if len(sentence) < 20:
                continue

            lower = sentence.lower()

            if any(
                phrase in lower
                for phrase in [
                    "confidential & proprietary",
                    "official reference manual",
                    "module:",
                    "document:"
                ]
            ):
                continue

            cleaned.append(sentence)

        return cleaned

    # =========================================================
    # TERM MATCHING
    # =========================================================

    @staticmethod
    def _contains_term(text: str, term: str) -> bool:

        if not text or not term:
            return False

        pattern = (
            rf"(?<![a-z0-9])"
            rf"{re.escape(term.lower())}"
            rf"(?![a-z0-9])"
        )

        return bool(
            re.search(
                pattern,
                text.lower()
            )
        )

    # =========================================================
    # LOCAL GROUNDED RESPONSE
    # =========================================================

    def _generate_grounded_local_response(
        self,
        query: str,
        evidence_text: str,
        source_type: str,
        metadata: List[Dict[str, Any]]
    ) -> str:

        if not metadata:
            return (
                "I couldn't find sufficient information about this "
                "in the available SAP knowledge base."
            )

        # -----------------------------------------------------
        # WEB RESPONSE
        # -----------------------------------------------------

        if source_type == "web":

            useful_snippets = []

            for item in metadata[:3]:

                title = item.get(
                    "title",
                    "SAP web source"
                )

                snippet = item.get(
                    "snippet",
                    ""
                ).strip()

                if not snippet:
                    continue

                snippet = self._clean_document_text(
                    snippet
                )

                if snippet:
                    useful_snippets.append(
                        f"- **{title}**: {snippet}"
                    )

            if not useful_snippets:
                return (
                    "I couldn't find sufficient verified web "
                    "information to answer this SAP question."
                )

            return (
                "Based on verified SAP web sources:\n\n"
                + "\n".join(useful_snippets)
            )

        # -----------------------------------------------------
        # QUERY TERMS
        # -----------------------------------------------------

        stop_words = {
            "what",
            "is",
            "the",
            "a",
            "an",
            "how",
            "to",
            "in",
            "of",
            "and",
            "for",
            "with",
            "does",
            "explain",
            "can",
            "you",
            "tell",
            "me",
            "about",
            "are",
            "why",
            "which",
            "where",
            "when"
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

        # -----------------------------------------------------
        # COLLECT CANDIDATE SENTENCES
        # -----------------------------------------------------

        candidate_sentences = []

        for item in metadata[:6]:

            raw_text = item.get(
                "chunk_text",
                ""
            )

            cleaned_text = self._clean_document_text(
                raw_text
            )

            sentences = self._extract_sentences(
                cleaned_text
            )

            if not sentences:
                continue

            rerank_score = float(
                item.get(
                    "rerank_score",
                    item.get(
                        "score",
                        0.0
                    )
                )
            )

            for sentence in sentences:

                sentence_lower = sentence.lower()

                # Query-term matching
                matched_terms = sum(
                    1
                    for term in query_terms
                    if self._contains_term(
                        sentence_lower,
                        term
                    )
                )

                query_match_score = (
                    matched_terms /
                    max(1, len(query_terms))
                )

                # Definition bonus
                definition_bonus = 0.0

                if (
                    " is " in sentence_lower
                    or " are " in sentence_lower
                    or " refers to " in sentence_lower
                    or " means " in sentence_lower
                    or " designed for " in sentence_lower
                ):
                    definition_bonus = 1.0

                # Direct subject bonus
                subject_bonus = 0.0

                if (
                    "sap s/4hana" in sentence_lower
                    and (
                        " is " in sentence_lower
                        or " refers to " in sentence_lower
                        or " designed " in sentence_lower
                    )
                ):
                    subject_bonus = 1.0

                # Final relevance
                relevance_score = (
                    query_match_score * 0.50
                    + rerank_score * 0.20
                    + definition_bonus * 0.15
                    + subject_bonus * 0.15
                )

                candidate_sentences.append(
                    {
                        "sentence": sentence,
                        "score": relevance_score
                    }
                )

        # -----------------------------------------------------
        # SORT BY RELEVANCE
        # -----------------------------------------------------

        candidate_sentences.sort(
            key=lambda x: x["score"],
            reverse=True
        )

        # -----------------------------------------------------
        # REMOVE DUPLICATES
        # -----------------------------------------------------

        selected = []

        seen = set()

        for item in candidate_sentences:

            sentence = item["sentence"].strip()

            normalized = sentence.lower()

            if normalized in seen:
                continue

            seen.add(normalized)

            selected.append(item)

            if len(selected) >= 4:
                break

        if not selected:
            return (
                "I couldn't find sufficient information about this "
                "in the available SAP knowledge base."
            )

        # -----------------------------------------------------
        # BUILD ANSWER
        # -----------------------------------------------------

        query_lower = query.lower()

        if (
            query_lower.startswith("what is")
            or query_lower.startswith("what are")
            or "define" in query_lower
        ):

            answer = " ".join(
                item["sentence"]
                for item in selected[:3]
            )

        elif (
            "explain" in query_lower
            or "how does" in query_lower
            or "how do" in query_lower
        ):

            answer = "\n\n".join(
                f"- {item['sentence']}"
                for item in selected[:4]
            )

        else:

            answer = "\n\n".join(
                f"- {item['sentence']}"
                for item in selected[:4]
            )

        return (
            "According to the private SAP knowledge base:\n\n"
            + answer
        )

    # =========================================================
    # MAIN ANSWER GENERATION
    # =========================================================

    def generate_answer(
        self,
        query: str,
        evidence: List[Dict[str, Any]],
        source_type: str = "knowledge_base"
    ) -> str:

        evidence_context = ""

        if source_type == "knowledge_base":

            evidence_context = "\n\n".join(
                [
                    (
                        f"[Document: {c.get('document_name')}, "
                        f"Page: {c.get('page_number')}, "
                        f"Section: {c.get('section')}]\n"
                        f"{c.get('chunk_text')}"
                    )
                    for c in evidence
                ]
            )

        elif source_type == "web":

            evidence_context = "\n\n".join(
                [
                    (
                        f"[Source: {w.get('title')} "
                        f"- {w.get('domain')}]\n"
                        f"{w.get('snippet')}"
                    )
                    for w in evidence
                ]
            )

        # =====================================================
        # CLOUD LLM
        # =====================================================

        if self.api_key:

            try:

                if (
                    "groq" in self.provider
                    or self.api_key.startswith("gsk_")
                ):

                    from groq import Groq

                    client = Groq(
                        api_key=self.api_key
                    )

                    model = "llama-3.3-70b-versatile"

                else:

                    from openai import OpenAI

                    client = OpenAI(
                        api_key=self.api_key
                    )

                    model = (
                        settings.LLM_MODEL
                        or "gpt-4o-mini"
                    )

                user_prompt = f"""
USER QUERY:
{query}

SOURCE TYPE:
{source_type.upper()}

RETRIEVED EVIDENCE:
{evidence_context}

TASK:

Answer the user's question using ONLY the retrieved evidence.

Rules:

1. Do not invent facts.
2. Do not use outside knowledge.
3. Do not reproduce large sections of the documents.
4. Give a concise answer.
5. Preserve important SAP technical terminology.
6. Remove document headers and confidentiality notices.
7. Prefer the evidence that directly answers the user's question.
8. If the evidence is insufficient, say so.
"""

                response = client.chat.completions.create(
                    model=model,
                    messages=[
                        {
                            "role": "system",
                            "content": SYSTEM_PROMPT
                        },
                        {
                            "role": "user",
                            "content": user_prompt
                        }
                    ],
                    temperature=0.1,
                    max_tokens=500
                )

                return (
                    response
                    .choices[0]
                    .message
                    .content
                    .strip()
                )

            except Exception as e:

                logger.warning(
                    f"Cloud LLM error ({e}). "
                    "Using local grounded synthesis."
                )

        # =====================================================
        # LOCAL FALLBACK
        # =====================================================

        return self._generate_grounded_local_response(
            query=query,
            evidence_text=evidence_context,
            source_type=source_type,
            metadata=evidence
        )

    # =========================================================
    # STREAMING
    # =========================================================

    def stream_answer(
        self,
        query: str,
        evidence: List[Dict[str, Any]],
        source_type: str = "knowledge_base"
    ) -> Generator[str, None, None]:

        full_answer = self.generate_answer(
            query,
            evidence,
            source_type
        )

        words = full_answer.split(" ")

        for i, word in enumerate(words):

            yield word + (
                " "
                if i < len(words) - 1
                else ""
            )


llm_service = LLMService()