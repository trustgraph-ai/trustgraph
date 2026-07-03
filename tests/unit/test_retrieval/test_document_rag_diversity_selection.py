from trustgraph.retrieval.document_rag.rerank import (
    RerankCandidate, normalize_candidate_scores, mmr_select,
    _pair_diversity_penalty
)

def candidate(index, chunk_id, text, score):
    return RerankCandidate(
        index=index,
        chunk_id=chunk_id,
        text=text,
        reranker_score=score,
    )


def test_normalize_candidate_scores_min_max_scales_raw_scores():
    candidates = [
        candidate(0, "a", "alpha", -2.0),
        candidate(1, "b", "beta", 0.0),
        candidate(2, "c", "gamma", 4.0),
    ]

    normalized = normalize_candidate_scores(candidates)

    assert normalized[0].normalized_score == 0.0
    assert normalized[1].normalized_score == 1.0 / 3.0
    assert normalized[2].normalized_score == 1.0


def test_normalize_candidate_scores_handles_equal_scores():
    candidates = [
        candidate(0, "a", "alpha", 3.0),
        candidate(1, "b", "beta", 3.0),
        candidate(2, "c", "gamma", 3.0),
    ]

    normalized = normalize_candidate_scores(candidates)

    assert [c.normalized_score for c in normalized] == [0.5, 0.5, 0.5]


def test_mmr_select_limits_results():
    candidates = [
        candidate(0, "a", "alpha policy", 0.9),
        candidate(1, "b", "beta refund", 0.8),
        candidate(2, "c", "gamma shipping", 0.7),
    ]

    selected = mmr_select(candidates, limit=2)

    assert len(selected) == 2


def test_mmr_select_prefers_highest_reranker_score_first():
    candidates = [
        candidate(0, "a", "weakly relevant text", 0.1),
        candidate(1, "b", "strongly relevant answer", 10.0),
        candidate(2, "c", "medium relevant text", 5.0),
    ]

    selected = mmr_select(candidates, limit=1)

    assert selected[0].chunk_id == "b"


def test_mmr_select_penalizes_near_duplicate_chunks():
    candidates = [
        candidate(0, "a", "apple banana fruit return policy", 1.00),
        candidate(1, "b", "apple banana fruit return policy duplicate", 0.95),
        candidate(2, "c", "engine motor vehicle warranty", 0.90),
    ]

    selected = mmr_select(
        candidates,
        limit=2,
        lambda_mult=0.2,
        token_overlap_weight=1.0,
    )

    assert [c.chunk_id for c in selected] == ["a", "c"]


def test_pair_diversity_penalty_is_clamped():
    left = candidate(0, "a", "same same same", 1.0)
    right = candidate(1, "b", "same same same", 0.9)

    penalty = _pair_diversity_penalty(
        left,
        right,
        token_overlap_weight=10.0,
    )

    assert penalty == 1.0
