import importlib.util
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[3]
RERANK_PATH = (
    REPO_ROOT
    / "trustgraph-flow"
    / "trustgraph"
    / "retrieval"
    / "document_rag"
    / "rerank.py"
)

spec = importlib.util.spec_from_file_location("document_rag_rerank", RERANK_PATH)
rerank = importlib.util.module_from_spec(spec)
spec.loader.exec_module(rerank)

RerankCandidate = rerank.RerankCandidate
mmr_rerank = rerank.mmr_rerank


def test_mmr_rerank_limits_results():
    candidates = [
        RerankCandidate("1", "apple banana fruit", rank=0),
        RerankCandidate("2", "apple banana fruit duplicate", rank=1),
        RerankCandidate("3", "engine motor vehicle", rank=2),
    ]

    result = mmr_rerank(
        query="apple fruit",
        candidates=candidates,
        limit=2,
        lambda_mult=0.7,
    )

    assert len(result) == 2


def test_mmr_rerank_returns_empty_for_zero_limit():
    candidates = [
        RerankCandidate("1", "apple banana fruit", rank=0),
    ]

    result = mmr_rerank(
        query="apple fruit",
        candidates=candidates,
        limit=0,
    )

    assert result == []


def test_mmr_rerank_prefers_query_relevant_chunk():
    candidates = [
        RerankCandidate("1", "irrelevant text", rank=5),
        RerankCandidate("2", "query answer target", rank=0),
        RerankCandidate("3", "another unrelated chunk", rank=2),
    ]

    result = mmr_rerank(
        query="query answer",
        candidates=candidates,
        limit=1,
        lambda_mult=0.9,
    )

    assert result[0].chunk_id == "2"
