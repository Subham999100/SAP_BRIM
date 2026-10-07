import sys
import io
import json

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
sys.path.insert(0, r"c:\Users\Subham Patnaik\OneDrive\Desktop\agent\SAP_Project")

from backend.app.database import SessionLocal
from backend.app.services.sap_classifier import sap_classifier
from backend.app.services.retrieval_service import retrieval_service
from backend.app.services.reranking_service import reranking_service
from backend.app.services.context_builder import context_builder
from backend.app.services.prompts import SAP_BRIM_SYSTEM_PROMPT, build_brim_user_prompt
from backend.app.services.embedding_service import embedding_service
from backend.app.services.grounding_service import grounding_service
from backend.app.models.chunk import DocumentChunk
from backend.app.config import settings
from sqlalchemy import func, desc
from groq import Groq

# 1. Exact original user question
question = "Design a ₹499 telecom pricing plan with 100 GB included data, ₹10 per additional GB, weekday/weekend pricing differences, and a 20% discount for the first 3 months."
print("=== 1. EXACT ORIGINAL USER QUESTION ===")
print(question)

# 2. Classifier result
is_sap, reason = sap_classifier.classify(question)
print("\n=== 2. CLASSIFIER RESULT ===")
print(f"is_sap: {is_sap}")
print(f"reason: {reason}")

db = SessionLocal()
try:
    processed_query = retrieval_service.preprocess_query(question)
    query_vector = embedding_service.embed_text(processed_query)

    # 3. Top retrieved chunks BEFORE RRF
    vec_hits = (
        db.query(DocumentChunk)
        .order_by(DocumentChunk.embedding.op("<=>")(query_vector))
        .limit(60)
        .all()
    )
    lex_q = db.query(DocumentChunk, func.ts_rank_cd(
        func.to_tsvector('english', DocumentChunk.chunk_text),
        func.plainto_tsquery('english', processed_query)
    ).label('lex_score'))
    lex_hits = (
        lex_q.filter(func.to_tsvector('english', DocumentChunk.chunk_text).op('@@')(func.plainto_tsquery('english', processed_query)))
        .order_by(desc('lex_score'))
        .limit(60)
        .all()
    )
    print("\n=== 3. TOP RETRIEVED CHUNKS BEFORE RRF ===")
    print(f"Vector search count: {len(vec_hits)}")
    for i, c in enumerate(vec_hits[:5], 1):
        print(f"  Vector [{i}]: Doc: {c.document_name} | Page: {c.page_number} | Sec: {c.section}")
    print(f"Lexical search count: {len(lex_hits)}")
    for i, (c, s) in enumerate(lex_hits[:5], 1):
        print(f"  Lexical [{i}]: Doc: {c.document_name} | Page: {c.page_number} | Score: {s:.4f} | Sec: {c.section}")

    # 4. RRF top candidates
    candidates = retrieval_service.hybrid_search(db, question, top_k=settings.RRF_CANDIDATE_K)
    print(f"\n=== 4. RRF TOP CANDIDATES (Pool count: {len(candidates)}) ===")
    for i, c in enumerate(candidates[:10], 1):
        print(f"  RRF [{i}]: Doc: {c.get('document_name')} | Page: {c.get('page_number')} | RRF: {c.get('rrf_score'):.5f} | Score: {c.get('score'):.4f}")

    # 5. ColBERT top 5
    reranked, sufficient = reranking_service.rerank(question, candidates, top_n=settings.FINAL_TOP_K)
    print(f"\n=== 5. COLBERT TOP 5 (Sufficient: {sufficient}) ===")
    for i, c in enumerate(reranked, 1):
        print(f"  ColBERT [{i}]: Doc: {c.get('document_name')} | Page: {c.get('page_number')} | Sec: {c.get('section')} | Score: {c.get('rerank_score'):.4f}")
        print(f"      Snippet: {c.get('chunk_text', '')[:180].replace(chr(10), ' ')}...")

    # 6. EXACT context string sent to the LLM
    context_str = context_builder.build_context(reranked, source_type="knowledge_base")
    print(f"\n=== 6. EXACT CONTEXT STRING SENT TO THE LLM (Length: {len(context_str)} chars) ===")
    print(context_str[:1200])
    print("... [TRUNCATED FOR DISPLAY] ...")

    # 7. EXACT system prompt sent to the LLM
    print("\n=== 7. EXACT SYSTEM PROMPT SENT TO THE LLM ===")
    print(SAP_BRIM_SYSTEM_PROMPT[:1500])
    print("... [TRUNCATED FOR DISPLAY] ...")

    # 8. EXACT user prompt sent to the LLM
    user_prompt = build_brim_user_prompt(
        query=question,
        structured_context=context_str,
        source_type="knowledge_base"
    )
    print(f"\n=== 8. EXACT USER PROMPT SENT TO THE LLM (Length: {len(user_prompt)} chars) ===")
    print(user_prompt[:1200])
    print("... [TRUNCATED FOR DISPLAY] ...")

    # 9. Exact Groq request parameters/model
    model = settings.LLM_MODEL or "openai/gpt-oss-120b"
    max_tokens = settings.LLM_MAX_OUTPUT_TOKENS
    temperature = 0.1
    print("\n=== 9. EXACT GROQ REQUEST PARAMETERS/MODEL ===")
    print(f"Provider: Groq")
    print(f"Model: {model}")
    print(f"Temperature: {temperature}")
    print(f"Max Tokens: {max_tokens}")
    print(f"Messages count: 2 (System + User)")

    # 10. Exact raw LLM response
    client = Groq(api_key=settings.GROQ_API_KEY)
    response = client.chat.completions.create(
        model=model,
        messages=[
            {"role": "system", "content": SAP_BRIM_SYSTEM_PROMPT},
            {"role": "user", "content": user_prompt}
        ],
        temperature=temperature,
        max_tokens=max_tokens
    )
    raw_choice = response.choices[0]
    raw_content = raw_choice.message.content
    finish_reason = raw_choice.finish_reason
    usage = response.usage
    reasoning_tokens = getattr(getattr(usage, 'completion_tokens_details', None), 'reasoning_tokens', 'N/A')

    print("\n=== 10. EXACT RAW LLM RESPONSE ===")
    print(f"Finish Reason: {finish_reason}")
    print(f"Usage: Prompt={usage.prompt_tokens}, Completion={usage.completion_tokens}, Reasoning={reasoning_tokens}, Total={usage.total_tokens}")
    print(f"Raw Response Length: {len(raw_content)} chars")
    print(f"Raw Response Head:\n{raw_content[:800]}")

    # 11. Any post-processing performed after the LLM response
    # In llm_service.py: content.strip()
    # In rag_service.py: evaluate_grounding(raw_content, reranked), build citations list
    clean_answer = raw_content.strip() if raw_content else ""
    grounding_score = grounding_service.evaluate_grounding(
        query=question,
        answer=clean_answer,
        chunks=reranked,
        source_type="knowledge_base"
    )
    citations = [
        {
            "id": c.get("chunk_id"),
            "document": c.get("document_name"),
            "page": c.get("page_number"),
            "section": c.get("section"),
            "score": round(float(c.get("rerank_score", c.get("score", 0.0))), 4),
            "snippet": c.get("chunk_text", "")[:200]
        }
        for c in reranked
    ]
    print("\n=== 11. POST-PROCESSING PERFORMED AFTER THE LLM RESPONSE ===")
    print(f"1. whitespace strip: yes (content.strip())")
    print(f"2. grounding_score computed: {grounding_score}")
    print(f"3. citations structured: {len(citations)} citations")

    # 12. Exact final API answer returned to the user
    final_api_response = {
        "answer": clean_answer,
        "source_type": "knowledge_base",
        "grounding_score": grounding_score,
        "citations": citations,
        "web_sources": []
    }
    print(f"\n=== 12. EXACT FINAL API ANSWER RETURNED TO THE USER (Length: {len(clean_answer)} chars) ===")
    print(clean_answer[:1000])

finally:
    db.close()
