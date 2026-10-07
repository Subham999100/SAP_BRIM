import sys
import io
import json

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
sys.path.insert(0, r"c:\Users\Subham Patnaik\OneDrive\Desktop\agent\SAP_Project")

from backend.app.database import SessionLocal
from backend.app.config import settings
from backend.app.services.rag_service import rag_service
from backend.app.services.llm_service import llm_service
from groq import Groq
from backend.app.services.prompts import SAP_BRIM_SYSTEM_PROMPT, build_brim_user_prompt
from backend.app.services.context_builder import context_builder

query = "Design a ₹499 telecom pricing plan with 100 GB included data, ₹10 per additional GB, weekday/weekend pricing differences, and a 20% discount for the first 3 months."

print("======================================================================")
print("VERIFYING FIXES FOR SAP BRIM EVALUATOR QUESTION")
print("Query:", query)
print("======================================================================")

print("\n1. CONFIGURATION VERIFICATION:")
print(f"   Provider: {settings.LLM_PROVIDER}")
print(f"   Model: {settings.LLM_MODEL}")
print(f"   Configured LLM_MAX_OUTPUT_TOKENS: {settings.LLM_MAX_OUTPUT_TOKENS}")

db = SessionLocal()
try:
    # 2. Run full end-to-end RAG Service
    print("\n2. EXECUTING FULL RAG SERVICE PIPELINE...")
    res = rag_service.process_query(db, query)

    # 3. Direct Groq call to verify actual runtime request parameters
    candidates = res.get("citations", [])
    print(f"\n3. RUNTIME GROQ CALL DETAILS:")
    client = Groq(api_key=settings.GROQ_API_KEY)
    
    # Retrieve top chunks for prompt context building
    from backend.app.services.retrieval_service import retrieval_service
    from backend.app.services.reranking_service import reranking_service
    cands = retrieval_service.hybrid_search(db, query, top_k=settings.RRF_CANDIDATE_K)
    reranked, suff = reranking_service.rerank(query, cands, top_n=settings.FINAL_TOP_K)
    ctx = context_builder.build_context(reranked, source_type="knowledge_base")
    user_prompt = build_brim_user_prompt(query, ctx, source_type="knowledge_base")

    groq_resp = client.chat.completions.create(
        model=settings.LLM_MODEL,
        messages=[
            {"role": "system", "content": SAP_BRIM_SYSTEM_PROMPT},
            {"role": "user", "content": user_prompt}
        ],
        temperature=0.1,
        max_tokens=settings.LLM_MAX_OUTPUT_TOKENS
    )
    
    choice = groq_resp.choices[0]
    finish_reason = choice.finish_reason
    usage = groq_resp.usage
    reasoning_tokens = getattr(getattr(usage, 'completion_tokens_details', None), 'reasoning_tokens', 'N/A')

    print(f"   Runtime max_tokens sent: {settings.LLM_MAX_OUTPUT_TOKENS}")
    print(f"   Runtime finish_reason: {finish_reason}")
    print(f"   Token Usage: Prompt={usage.prompt_tokens}, Completion={usage.completion_tokens}, Reasoning={reasoning_tokens}, Total={usage.total_tokens}")

    answer = res["answer"]
    print(f"\n4. RAG PIPELINE OUTPUT:")
    print(f"   Source Type: {res['source_type']}")
    print(f"   Grounding Score: {res['grounding_score']}")
    print(f"   Citations Count: {len(res['citations'])}")
    print(f"   Answer Character Length: {len(answer)}")

    print("\n========================= COMPLETE LLM ANSWER =========================")
    print(answer)
    print("=======================================================================\n")

    # 5. Requirement and quality checklist
    ans_lower = answer.lower()
    checklist = {
        "Base Subscription (₹499)": any(k in ans_lower for k in ["499", "recurring", "subscription fee"]),
        "Included Allowance (100 GB)": any(k in ans_lower for k in ["100 gb", "allowance", "included"]),
        "Excess Usage (₹10/GB)": any(k in ans_lower for k in ["10", "overage", "additional gb", "tier", "gscale"]),
        "Weekday vs Weekend Handling": any(k in ans_lower for k in ["weekday", "weekend", "uncertain", "unverified", "calendar", "release"]),
        "20% Discount for First 3 Months": any(k in ans_lower for k in ["20%", "20 percent", "3 months", "three months", "validity"]),
        "Architectural Mapping (SOM/CC/CI/FI-CA)": all(c in ans_lower for c in ["som", "cc", "ci", "fi-ca"]),
        "Price Plan vs Price Table Distinction": "price plan" in ans_lower and "price table" in ans_lower,
        "Scenario Calculations / Arithmetic": any(c in ans_lower for c in ["net", "total", "calculate", "discounted", "month"]),
        "No Raw Chunk Text Leakage": "raw_chunk" not in ans_lower and len(answer) > 500,
        "Non-Refusal (Applied Synthesis)": res["source_type"] != "refusal" and "evidence is insufficient to answer this question" not in ans_lower
    }

    print("5. EVALUATION CRITERIA CHECKLIST:")
    for criterion, passed in checklist.items():
        status = "[PASS]" if passed else "[FAIL]"
        print(f"   {status} {criterion}")

finally:
    db.close()
