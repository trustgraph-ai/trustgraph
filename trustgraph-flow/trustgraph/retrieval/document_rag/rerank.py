import re
from dataclasses import dataclass, replace
from typing import List, Sequence, Set


@dataclass(frozen=True)
class RerankCandidate:
    """
    Candidate chunk after cross-encoder reranking.

    reranker_score is the raw score returned by the reranker backend. It may
    not be normalized, so MMR should use normalized_score instead.
    """
    index: int
    chunk_id: str
    text: str
    reranker_score: float
    normalized_score: float = 0.0


_TOKEN_RE = re.compile(r"[A-Za-z0-9_]+")


def _clamp01(value: float) -> float:
    return max(0.0, min(1.0, value))


def _token_set(text: str) -> Set[str]:
    return set(token.lower() for token in _TOKEN_RE.findall(text or ""))


def _jaccard(a: str, b: str) -> float:
    a_tokens = _token_set(a)
    b_tokens = _token_set(b)

    if not a_tokens or not b_tokens:
        return 0.0

    return len(a_tokens & b_tokens) / len(a_tokens | b_tokens)


def normalize_candidate_scores(
    candidates: Sequence[RerankCandidate],
) -> List[RerankCandidate]:
    """
    Min-max normalize reranker scores within the current candidate set.

    Reranker backends may return different score scales: probabilities,
    logits, or prompt-defined scores. MMR needs a stable [0, 1] relevance
    signal, so normalize per candidate set instead of assuming a global range.
    """
    if not candidates:
        return []

    scores = [float(candidate.reranker_score) for candidate in candidates]
    min_score = min(scores)
    max_score = max(scores)

    if max_score == min_score:
        return [
            replace(candidate, normalized_score=0.5)
            for candidate in candidates
        ]

    score_range = max_score - min_score

    return [
        replace(
            candidate,
            normalized_score=(float(candidate.reranker_score) - min_score) / score_range,
        )
        for candidate in candidates
    ]


def _pair_diversity_penalty(
    candidate: RerankCandidate,
    selected: RerankCandidate,
    token_overlap_weight: float,
) -> float:
    """
    Pairwise diversity penalty between two candidate chunks.

    The first revision only uses token overlap because the current Document-RAG
    reranker document_id is the candidate index, not a source document id.
    """
    penalty = token_overlap_weight * _jaccard(candidate.text, selected.text)
    return _clamp01(penalty)


def mmr_select(
    candidates: Sequence[RerankCandidate],
    limit: int,
    lambda_mult: float = 0.7,
    token_overlap_weight: float = 1.0,
) -> List[RerankCandidate]:
    """
    Select a diverse final context set using MMR.

    Relevance comes from normalized cross-encoder reranker scores.
    Diversity comes from token overlap against already selected chunks.
    """
    if limit <= 0:
        return []

    lambda_mult = _clamp01(lambda_mult)
    token_overlap_weight = max(0.0, token_overlap_weight)

    remaining = normalize_candidate_scores(candidates)
    selected: List[RerankCandidate] = []

    while remaining and len(selected) < limit:
        best_idx = 0
        best_score = None

        for idx, candidate in enumerate(remaining):
            relevance = candidate.normalized_score

            if selected:
                diversity_penalty = max(
                    _pair_diversity_penalty(
                        candidate,
                        chosen,
                        token_overlap_weight=token_overlap_weight,
                    )
                    for chosen in selected
                )
            else:
                diversity_penalty = 0.0

            mmr_score = (
                lambda_mult * relevance
                - (1.0 - lambda_mult) * diversity_penalty
            )

            if best_score is None or mmr_score > best_score:
                best_score = mmr_score
                best_idx = idx

        selected.append(remaining.pop(best_idx))

    return selected
