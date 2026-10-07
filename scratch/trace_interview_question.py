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
from backend.app.services.llm_service import llm_service
from backend.app.services.rag_service import rag_service
from backend.app.services.embedding_service import embedding_service
from backend.app.models.chunk import DocumentChunk
from sqlalchemy import func, desc

query = "Design a ₹499 telecom pricing plan with 100 GB included data, ₹10 per additional GB, weekday/weekend pricing differences, and a 20% discount for the first 3 months."

print("==================================================")
print("TRACING QUERY:")
print(query)
print("==================================================")

# 1. SAP Classifier
is_sap, reason = sap_classifier.classify(query)
print(f"\n[1] SAP CLASSIFIER:")
print(f"    is_sap: {is_sap}")
print(f"    reason: {reason}")

db = SessionLocal()
try:
    # 2. Vector search details
    processed_query = retrieval_service.preprocess_query(query)
    query_vector = embedding_service.embed_text(processed_query)
    vec_hits = (
        db.query(DocumentChunk)
        .order_by(DocumentChunk.embedding.op("<=>")(query_vector))
        .limit(60)
        .all()
    )
    print(f"\n[2] VECTOR SEARCH:")
    print(f"    Vector count: {len(vec_hits)}")
    for i, c in enumerate(vec_hits[:5], 1):
        print(f"    [{i}] Doc: {c.document_name} | Page: {c.page_number} | Sec: {c.section}")

    # Lexical search details
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
    print(f"\n[3] LEXICAL SEARCH:")
    print(f"    Lexical count: {len(lex_hits)}")
    for i, (c, s) in enumerate(lex_hits[:5], 1):
        print(f"    [{i}] Doc: {c.document_name} | Page: {c.page_number} | Score: {s:.4f} | Sec: {c.section}")

    # Hybrid + RRF
    candidates = retrieval_service.hybrid_search(db, query, top_k=30)
    print(f"\n[4] HYBRID RRF CANDIDATES: {len(candidates)}")
    for i, c in enumerate(candidates[:5], 1):
        print(f"    [{i}] Doc: {c.get('document_name')} | Page: {c.get('page_number')} | RRF: {c.get('rrf_score'):.4f} | Score: {c.get('score'):.4f}")

    # 3. Reranker
    reranked, sufficient = reranking_service.rerank(query, candidates, top_n=5)
    print(f"\n[5] RERANKER:")
    print(f"    Reranked count: {len(reranked)}")
    print(f"    Sufficient evidence flag: {sufficient}")
    for i, c in enumerate(reranked, 1):
        print(f"    [{i}] Doc: {c.get('document_name')} | Page: {c.get('page_number')} | Sec: {c.get('section')} | Rerank Score: {c.get('rerank_score')}")
        print(f"        Snippet: {c.get('chunk_text', '')[:200]}...")

    # 4. Context Builder
    formatted_context = context_builder.build_context(reranked)
    print(f"\n[6] CONTEXT BUILDER:")
    print(f"    Context length: {len(formatted_context)} chars")
    print(f"\n--- FORMATTED CONTEXT HEAD (first 600 chars) ---")
    print(formatted_context[:600])

    # 5. LLM Service Execution
    print(f"\n[7] GENERATING ANSWER (VIA LLM SERVICE)...")
    answer = llm_service.generate_answer(query, reranked, source_type="knowledge_base")
    print("\n--- GENERATED ANSWER ---")
    print(answer)
    print("------------------------")

finally:
    db.close()
