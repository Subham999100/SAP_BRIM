import sys
import os
import io

# Ensure UTF-8 output on Windows stdout
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
sys.path.insert(0, r"c:\Users\Subham Patnaik\OneDrive\Desktop\agent\SAP_Project")

from backend.app.database import SessionLocal
from backend.app.services.rag_service import rag_service
from backend.app.services.retrieval_service import retrieval_service
from backend.app.services.reranking_service import reranking_service
from backend.app.services.context_builder import context_builder

def test_query(query: str, label: str):
    print("=" * 70)
    print(f"TEST: {label}")
    print(f"QUERY: '{query}'")
    print("=" * 70)
    
    db = SessionLocal()
    try:
        # Step 1: Hybrid Retrieval + RRF
        candidates = retrieval_service.hybrid_search(db, query, top_k=30)
        retrieved_count = len(candidates)
        print(f"1. Hybrid + RRF Candidates: {retrieved_count}")
        
        # Step 2: ColBERT Reranker
        reranked, is_sufficient = reranking_service.rerank(query, candidates, top_n=5)
        reranked_count = len(reranked)
        print(f"2. Reranked Chunks (Top 5): {reranked_count}")
        for i, r in enumerate(reranked, 1):
            doc = r.get("document_name") or r.get("document")
            page = r.get("page_number") or r.get("page")
            score = r.get("rerank_score", r.get("score"))
            print(f"   [{i}] Doc: {doc} | Page: {page} | Score: {score:.4f}")
            
        # Step 3: Context Builder
        formatted_context = context_builder.build_context(reranked)
        print(f"3. Structured Context: {len(formatted_context)} chars")
        print("\n--- FORMATTED CONTEXT PREVIEW ---")
        preview_lines = formatted_context.split("\n")[:18]
        print("\n".join(preview_lines))
        print("...")
        
        # Step 4: Full RAG generation
        result = rag_service.process_query(db, query)
        print("\n4. Generation Result:")
        print(f"   Source Type: {result.get('source_type')}")
        print(f"   Grounding Score: {result.get('grounding_score')}")
        print(f"   Citations Count: {len(result.get('citations', []))}")
        for i, c in enumerate(result.get("citations", []), 1):
            print(f"     Citation {i}: {c.get('document')} | Page {c.get('page')} | Section: {c.get('section')}")
            
        print("\n5. Answer Preview:")
        answer = result.get("answer", "")
        print(answer[:800])
        if len(answer) > 800:
            print("... [truncated preview]")
            
    finally:
        db.close()
    print("\n")

if __name__ == "__main__":
    test_query("What is SAP Convergent Charging?", "Grounded SAP BRIM Query")
    test_query("What does SAP Convergent Charging say about the Charging Server?", "Uncertainty / Insufficient Evidence Query")
