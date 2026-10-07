import sys
import io
import json

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
sys.path.insert(0, r"c:\Users\Subham Patnaik\OneDrive\Desktop\agent\SAP_Project")

from backend.app.database import SessionLocal
from backend.app.services.rag_service import rag_service
from backend.app.services.retrieval_service import retrieval_service
from backend.app.services.reranking_service import reranking_service
from backend.app.services.context_builder import context_builder
from backend.app.services.embedding_service import embedding_service
from backend.app.models.chunk import DocumentChunk
from backend.app.config import settings
from sqlalchemy import func, desc
from groq import Groq
from backend.app.services.prompts import SAP_BRIM_SYSTEM_PROMPT, build_brim_user_prompt

query = "Design a ₹499 telecom pricing plan with 100 GB included data, ₹10 per additional GB, weekday/weekend pricing differences, and a 20% discount for the first 3 months."

print("======================================================================")
print("EXACT END-TO-END SAP BRIM INTERVIEW QUESTION TEST")
print("QUERY:", query)
print("======================================================================")

db = SessionLocal()
try:
    # 1. Vector candidates
    processed_query = retrieval_service.preprocess_query(query)
    query_vector = embedding_service.embed_text(processed_query)
    vec_hits = (
        db.query(DocumentChunk)
        .order_by(DocumentChunk.embedding.op("<=>")(query_vector))
        .limit(60)
        .all()
    )
    print(f"\n1. Vector Candidates Count: {len(vec_hits)}")
    for i, c in enumerate(vec_hits[:3], 1):
        print(f"   [{i}] {c.document_name} | Page {c.page_number} | Section: {c.section}")

    # 2. Lexical candidates
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
    print(f"\n2. Lexical Candidates Count: {len(lex_hits)}")

    # 3. Hybrid RRF candidates
    candidates = retrieval_service.hybrid_search(db, query, top_k=30)
    print(f"\n3. RRF Candidates Count: {len(candidates)}")

    # 4. ColBERT Reranker candidates
    reranked, sufficient = reranking_service.rerank(query, candidates, top_n=5)
    print(f"\n4. Reranked Candidates Count: {len(reranked)}")
    for i, c in enumerate(reranked, 1):
        print(f"   [{i}] {c['document_name']} | Page {c['page_number']} | Score: {c['rerank_score']:.4f}")

    # 5. Context Builder
    structured_context = context_builder.build_context(reranked, source_type="knowledge_base")
    print(f"\n5. Final Context Size: {len(structured_context)} characters")

    # 6. Groq LLM Direct Call to check finish_reason and usage
    client = Groq(api_key=settings.GROQ_API_KEY)
    user_prompt = build_brim_user_prompt(
        query=query,
        structured_context=structured_context,
        source_type="knowledge_base"
    )
    print(f"\n6. LLM Configuration:")
    print(f"   Model: {settings.LLM_MODEL}")
    print(f"   Configured Output Token Limit: {settings.LLM_MAX_OUTPUT_TOKENS}")

    raw_response = client.chat.completions.create(
        model=settings.LLM_MODEL,
        messages=[
            {"role": "system", "content": SAP_BRIM_SYSTEM_PROMPT},
            {"role": "user", "content": user_prompt}
        ],
        temperature=0.1,
        max_tokens=settings.LLM_MAX_OUTPUT_TOKENS
    )
    choice = raw_response.choices[0]
    finish_reason = choice.finish_reason
    usage = raw_response.usage
    print(f"\n7. Generation Status:")
    print(f"   finish_reason: {finish_reason}")
    print(f"   Usage: completion_tokens={usage.completion_tokens}, prompt_tokens={usage.prompt_tokens}, total_tokens={usage.total_tokens}")
    if hasattr(usage, "completion_tokens_details") and usage.completion_tokens_details:
        print(f"   Reasoning Tokens: {usage.completion_tokens_details.reasoning_tokens}")

    # 8. Run Full rag_service.process_query to verify grounding and citations
    rag_res = rag_service.process_query(db, query)
    print(f"\n8. RAG Service Pipeline Result:")
    print(f"   Source Type: {rag_res['source_type']}")
    print(f"   Grounding Score: {rag_res['grounding_score']}")
    print(f"   Citations Count: {len(rag_res['citations'])}")
    for i, cit in enumerate(rag_res['citations'], 1):
        print(f"     Citation {i}: {cit['document']} | Page {cit['page']} | Section: {cit['section']}")

    answer = rag_res["answer"]
    print(f"\n9. Complete Answer Length: {len(answer)} characters")
    print("\n========================= COMPLETE ANSWER =========================")
    print(answer)
    print("===================================================================\n")

    # 10. Requirement evaluation checklist
    ans_lower = answer.lower()
    checklist = {
        "₹499 monthly subscription": any(w in ans_lower for w in ["499", "recurring", "monthly fee", "subscription"]),
        "100 GB included": any(w in ans_lower for w in ["100 gb", "allowance", "included", "quota", "100"]),
        "₹10 per additional GB": any(w in ans_lower for w in ["10", "additional gb", "usage", "overage", "graduated scale"]),
        "weekday/weekend pricing": any(w in ans_lower for w in ["weekday", "weekend", "day-based", "calendar"]),
        "20% discount": any(w in ans_lower for w in ["20%", "20 percent", "discount"]),
        "first 3 months": any(w in ans_lower for w in ["3 months", "three months", "promotional", "validity"]),
        "Price Plan": "price plan" in ans_lower or "charge plan" in ans_lower or "rate plan" in ans_lower,
        "Price Table": "price table" in ans_lower or "mapping table" in ans_lower or "range table" in ans_lower or "scale" in ans_lower,
        "testing": "test" in ans_lower,
        "debugging": "debug" in ans_lower or "core tool" in ans_lower or "simulation" in ans_lower,
        "stakeholder/business validation": "validation" in ans_lower or "stakeholder" in ans_lower or "verification" in ans_lower
    }
    print("10. Requirement Coverage Evaluation:")
    for req, met in checklist.items():
        status_sym = "[X]" if met else "[ ]"
        print(f"   {status_sym} {req}")

finally:
    db.close()
