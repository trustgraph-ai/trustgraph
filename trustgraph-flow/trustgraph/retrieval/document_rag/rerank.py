import re
from dataclasses import dataclass
from typing import List, Optional, Sequence, Set


@dataclass(frozen=True)
class RerankCandidate:
    chunk_id: str
    text: str
    rank: int
    score: Optional[float] = None


_TOKEN_RE = re.compile(r"[A-Za-z0-9_]+")


def _token_set(text: str) -> Set[str]:
    return set(token.lower() for token in _TOKEN_RE.findall(text or ""))


def _jaccard(a: str, b: str) -> float:
    a_tokens = _token_set(a)
    b_tokens = _token_set(b)

    if not a_tokens or not b_tokens:
        return 0.0

    return len(a_tokens & b_tokens) / len(a_tokens | b_tokens)


def _rank_relevance(candidate: RerankCandidate) -> float:
    """
    Use backend score when available. Otherwise preserve original retrieval
    ordering with reciprocal rank.
    """
    if candidate.score is not None:
        return float(candidate.score)

    return 1.0 / float(candidate.rank + 1)


def mmr_rerank(
    query: str,
    candidates: Sequence[RerankCandidate],
    limit: int,
    lambda_mult: float = 0.7,
) -> List[RerankCandidate]:
    """
    Dependency-free Maximal Marginal Relevance reranking.

    Selects chunks that are relevant to the query while penalizing chunks that
    are too similar to already selected chunks.
    """
    if limit <= 0:
        return []

    remaining = list(candidates)
    selected: List[RerankCandidate] = []

    while remaining and len(selected) < limit:
        best_idx = 0
        best_score = None

        for idx, candidate in enumerate(remaining):
            relevance = max(
                _rank_relevance(candidate),
                _jaccard(query, candidate.text),
            )

            if selected:
                diversity_penalty = max(
                    _jaccard(candidate.text, chosen.text)
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
