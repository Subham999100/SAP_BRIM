import pytest
from backend.app.database import SessionLocal
from backend.app.config import settings
from backend.app.services.retrieval_service import retrieval_service
from backend.app.services.reranking_service import reranking_service, RerankingService


@pytest.fixture
def db_session():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def test_hybrid_retrieval_produces_rrf_candidates(db_session):
    """1 & 2: Test that hybrid retrieval works and RRF produces the expected candidate pool."""
    query = "What is SAP Convergent Charging?"
    candidates = retrieval_service.hybrid_search(db_session, query, top_k=settings.RRF_CANDIDATE_K)

    assert isinstance(candidates, list)
    assert len(candidates) > 0
    assert len(candidates) <= settings.RRF_CANDIDATE_K

    # Verify RRF score and normalized score exist
    for c in candidates:
        assert "chunk_id" in c
        assert "document_name" in c
        assert "chunk_text" in c
        assert "rrf_score" in c
        assert c["rrf_score"] > 0.0
        assert "score" in c
        assert 0.0 <= c["score"] <= 1.0


def test_reranker_processes_rrf_candidates_and_returns_final_k(db_session):
    """3 & 4: Test that reranker receives RRF candidates and returns top_n (Top 5)."""
    query = "What is SAP Convergent Charging?"
    candidates = retrieval_service.hybrid_search(db_session, query, top_k=settings.RRF_CANDIDATE_K)
    assert len(candidates) >= 5

    top_chunks, has_sufficient = reranking_service.rerank(
        query=query,
        candidates=candidates,
        top_n=settings.FINAL_TOP_K
    )

    assert isinstance(top_chunks, list)
    assert len(top_chunks) == settings.FINAL_TOP_K
    assert isinstance(has_sufficient, bool)


def test_chunk_fields_and_metadata_preserved(db_session):
    """5: Test that all existing chunk fields and metadata are preserved after reranking."""
    query = "SAP Convergent Charging pricing and rating"
    candidates = retrieval_service.hybrid_search(db_session, query, top_k=10)
    top_chunks, _ = reranking_service.rerank(query, candidates, top_n=5)

    required_fields = [
        "chunk_id",
        "document_id",
        "document_name",
        "page_number",
        "section",
        "chunk_text",
        "vector_score",
        "keyword_score",
        "rrf_score",
        "score",
        "rerank_score",
        "retrieval_method"
    ]

    for chunk in top_chunks:
        for field in required_fields:
            assert field in chunk, f"Missing required field '{field}' in reranked chunk"
        assert isinstance(chunk["rerank_score"], float)
        assert 0.0 <= chunk["rerank_score"] <= 1.0
        assert chunk["retrieval_method"] in ("hybrid_rrf_rerank", "hybrid_rrf_fallback")


def test_empty_candidates_handled_safely():
    """6: Test that empty retrieval results are handled gracefully without exceptions."""
    empty_result, has_sufficient = reranking_service.rerank(
        query="nonexistent topic",
        candidates=[],
        top_n=5
    )
    assert empty_result == []
    assert has_sufficient is False


def test_reranking_failure_safe_fallback(db_session):
    """7: Test that if the neural reranker model fails or is unavailable, fallback still succeeds."""
    query = "What is SAP Convergent Charging?"
    candidates = retrieval_service.hybrid_search(db_session, query, top_k=10)
    assert len(candidates) > 0

    # Instantiate a mock/isolated reranking service that simulates model failure
    service = RerankingService()
    service._score_with_model = lambda q, c: None  # force neural failure

    fallback_chunks, sufficient = service.rerank(query, candidates, top_n=5)

    assert len(fallback_chunks) == min(5, len(candidates))
    for chunk in fallback_chunks:
        assert chunk["retrieval_method"] == "hybrid_rrf_fallback"
        assert "rerank_score" in chunk
        assert "rrf_score" in chunk


def test_retrieve_and_rerank_unified_pipeline(db_session):
    """Test the complete 2-stage retrieve_and_rerank pipeline and baseline comparison."""
    query = "SAP Convergent Charging"

    # 1. Proposed 2-stage pipeline (enable_rerank=True)
    reranked_chunks, reranked_sufficient = retrieval_service.retrieve_and_rerank(
        db=db_session,
        query=query,
        candidate_k=settings.RRF_CANDIDATE_K,
        final_k=settings.FINAL_TOP_K,
        enable_rerank=True
    )

    assert len(reranked_chunks) == settings.FINAL_TOP_K
    assert "rerank_score" in reranked_chunks[0]

    # 2. Baseline comparison (enable_rerank=False)
    baseline_chunks, baseline_sufficient = retrieval_service.retrieve_and_rerank(
        db=db_session,
        query=query,
        candidate_k=settings.RRF_CANDIDATE_K,
        final_k=settings.FINAL_TOP_K,
        enable_rerank=False
    )

    assert len(baseline_chunks) == settings.FINAL_TOP_K
    assert baseline_chunks[0]["retrieval_method"] == "hybrid_rrf"
