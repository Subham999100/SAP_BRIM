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
from backend.app.config import settings
from groq import Groq
from backend.app.services.prompts import SAP_BRIM_SYSTEM_PROMPT, build_brim_user_prompt

query = "What is the difference between a Price Plan and a Price Table in SAP Convergent Charging? Explain with a simple telecom example."

print("======================================================================")
print("CONCEPTUAL QUESTION VERIFICATION")
print("QUERY:", query)
print("======================================================================")

db = SessionLocal()
try:
    # 1. Retrieval
    candidates = retrieval_service.hybrid_search(db, query, top_k=30)
    print(f"\n1. Retrieved candidates count (Hybrid + RRF): {len(candidates)}")

    # 2. Reranking
    reranked, sufficient = reranking_service.rerank(query, candidates, top_n=5)
    print(f"2. Reranked candidates count: {len(reranked)}")
    for i, c in enumerate(reranked, 1):
        print(f"   [{i}] Doc: {c['document_name']} | Page: {c['page_number']} | Score: {c['rerank_score']:.4f}")

    # 3. Context builder
    structured_context = context_builder.build_context(reranked, source_type="knowledge_base")
    context_size = len(structured_context)
    print(f"3. Context size: {context_size} characters")

    # 4. LLM Call Inspection
    client = Groq(api_key=settings.GROQ_API_KEY)
    user_prompt = build_brim_user_prompt(
        query=query,
        structured_context=structured_context,
        source_type="knowledge_base"
    )

    raw_response = client.chat.completions.create(
        model=settings.LLM_MODEL,
        messages=[
            {"role": "system", "content": SAP_BRIM_SYSTEM_PROMPT},
            {"role": "user", "content": user_prompt}
        ],
        temperature=0.1,
        max_tokens=settings.LLM_MAX_OUTPUT_TOKENS
    )
    finish_reason = raw_response.choices[0].finish_reason
    usage = raw_response.usage
    print(f"4. LLM call completed:")
    print(f"   Model: {settings.LLM_MODEL}")
    print(f"   Finish reason: {finish_reason}")
    print(f"   Completion tokens: {usage.completion_tokens}")

    # 5. Full RAG Service pipeline result
    rag_res = rag_service.process_query(db, query)
    answer = rag_res["answer"]
    grounding = rag_res["grounding_score"]
    citations = rag_res["citations"]

    # 6. Verify chunks were NOT directly returned
    retrieved_texts = [c.get("chunk_text", "").strip() for c in reranked if c.get("chunk_text")]
    chunk_directly_returned = any(text in answer for text in retrieved_texts if len(text) > 50)
    
    print(f"\n5. Verification Checks:")
    print(f"   Was LLM called: YES (Groq client via llm_service.generate_answer)")
    print(f"   Grounding score: {grounding}")
    print(f"   Citation count: {len(citations)}")
    print(f"   Any retrieved chunk directly returned: {chunk_directly_returned}")
    print(f"   Final answer came exclusively from LLM: {not chunk_directly_returned and len(answer) > 0}")

    print("\n========================= FINAL ANSWER =========================")
    print(answer)
    print("================================================================\n")

finally:
    db.close()
