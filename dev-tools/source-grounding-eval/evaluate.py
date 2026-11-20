#!/usr/bin/env python3
"""Deterministic document-source evaluation of GraphRAG observations.

Only source *identities* are scored automatically. Passage/claim support is
human-reviewed and intentionally excluded unless explicit review labels exist.
"""

from __future__ import annotations

import argparse
import json
from collections import Counter
from pathlib import Path
from typing import Any


class DatasetError(ValueError):
    """A malformed or inconsistent benchmark input."""


def read_jsonl(path: str | Path) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    with Path(path).open(encoding="utf-8") as file:
        for lineno, line in enumerate(file, 1):
            if not line.strip():
                continue
            try:
                obj = json.loads(line)
            except json.JSONDecodeError as exc:
                raise DatasetError(f"{path}:{lineno}: {exc}") from exc
            if not isinstance(obj, dict):
                raise DatasetError(f"{path}:{lineno}: expected an object")
            rows.append(obj)
    if not rows:
        raise DatasetError(f"{path}: no cases found")
    return rows


def write_json(path: str | Path, data: dict[str, Any]) -> None:
    dst = Path(path)
    dst.parent.mkdir(parents=True, exist_ok=True)
    dst.write_text(json.dumps(data, indent=2, ensure_ascii=False, sort_keys=True) + "\n", encoding="utf-8")


def _unique_nonempty_strings(value: Any, name: str) -> set[str]:
    if not isinstance(value, list) or any(not isinstance(x, str) or not x.strip() for x in value):
        raise DatasetError(f"{name} must be a list of nonempty strings")
    if len(value) != len(set(value)):
        raise DatasetError(f"{name} contains duplicate values")
    return set(value)


def validate_gold(rows: list[dict[str, Any]]) -> dict[str, dict[str, Any]]:
    cases: dict[str, dict[str, Any]] = {}
    for row in rows:
        case_id = row.get("id")
        if not isinstance(case_id, str) or not case_id.strip():
            raise DatasetError("gold id must be a nonempty string")
        if case_id in cases:
            raise DatasetError(f"duplicate gold id: {case_id}")
        question = row.get("question")
        if not isinstance(question, str) or not question.strip():
            raise DatasetError(f"{case_id}: question must be a nonempty string")
        status = row.get("answerability")
        if status not in ("answerable", "conflicting", "unanswerable"):
            raise DatasetError(f"{case_id}: invalid answerability {status!r}")
        expected = _unique_nonempty_strings(row.get("expected_source_uris"), f"{case_id}.expected_source_uris")
        if status == "unanswerable" and expected:
            raise DatasetError(f"{case_id}: unanswerable case must not have expected sources")
        if status != "unanswerable" and not expected:
            raise DatasetError(f"{case_id}: answerable/conflicting case requires expected sources")
        evidence = row.get("evidence", [])
        if not isinstance(evidence, list):
            raise DatasetError(f"{case_id}.evidence must be a list")
        for e in evidence:
            if (not isinstance(e, dict) or e.get("source_uri") not in expected or
                    not isinstance(e.get("passage"), str) or not e["passage"].strip()):
                raise DatasetError(f"{case_id}: evidence needs a known source_uri and nonempty passage")
        cases[case_id] = row
    return cases


def validate_observations(rows: list[dict[str, Any]], gold: dict[str, Any]) -> dict[str, dict[str, Any]]:
    observations: dict[str, dict[str, Any]] = {}
    for row in rows:
        case_id = row.get("id")
        if not isinstance(case_id, str) or case_id not in gold:
            raise DatasetError(f"unknown observation id: {case_id!r}")
        if case_id in observations:
            raise DatasetError(f"duplicate observation id: {case_id}")
        if not isinstance(row.get("answer"), str):
            raise DatasetError(f"{case_id}: answer must be a string")
        sources = row.get("sources")
        if not isinstance(sources, list):
            raise DatasetError(f"{case_id}: sources must be a list")
        uris: list[str] = []
        for source in sources:
            if not isinstance(source, dict) or not isinstance(source.get("uri"), str) or not source["uri"].strip():
                raise DatasetError(f"{case_id}: each source needs a nonempty uri")
            uris.append(source["uri"])
        if len(uris) != len(set(uris)):
            raise DatasetError(f"{case_id}: duplicate source URIs")
        review = row.get("review", {})
        if not isinstance(review, dict):
            raise DatasetError(f"{case_id}: review must be an object")
        for field in ("answer_supported", "passage_trace_verified", "abstained_appropriately", "conflict_handled"):
            if field in review and review[field] is not None and not isinstance(review[field], bool):
                raise DatasetError(f"{case_id}: review.{field} must be a boolean or null")
        if review.get("abstained_appropriately") is not None and gold[case_id]["answerability"] != "unanswerable":
            raise DatasetError(f"{case_id}: abstained_appropriately applies only to unanswerable cases")
        if review.get("conflict_handled") is not None and gold[case_id]["answerability"] != "conflicting":
            raise DatasetError(f"{case_id}: conflict_handled applies only to conflicting cases")
        if "error" in row and row["error"] is not None:
            raise DatasetError(f"{case_id}: error observation is not scoreable: {row['error']}")
        observations[case_id] = row
    return observations


def _fraction(numerator: int, denominator: int) -> float | None:
    return round(numerator / denominator, 6) if denominator else None


def evaluate(gold_rows: list[dict[str, Any]], observation_rows: list[dict[str, Any]]) -> dict[str, Any]:
    gold = validate_gold(gold_rows)
    observations = validate_observations(observation_rows, gold)
    count = Counter()
    details: list[dict[str, Any]] = []
    for case_id, case in gold.items():
        observation = observations.get(case_id)
        if observation is None:
            details.append({"id": case_id, "status": "missing_observation"})
            continue
        actual = {s["uri"] for s in observation["sources"]}
        expected = set(case["expected_source_uris"])
        tp = actual & expected
        count["evaluated"] += 1
        count["total_predicted_sources"] += len(actual)
        count["false_positive"] += len(actual - expected)
        count["true_positive"] += len(tp)
        count["false_negative"] += len(expected - actual)
        if expected:
            count["answerable_cases"] += 1
            count["macro_source_recall_sum"] += len(tp) / len(expected)
            count["exact_source_set"] += int(actual == expected)
        else:
            count["unanswerable_cases"] += 1
            count["unanswerable_no_source"] += int(not actual)
        review = observation.get("review", {})
        for field in ("answer_supported", "passage_trace_verified", "abstained_appropriately", "conflict_handled"):
            if review.get(field) is not None:
                count[f"{field}_reviewed"] += 1
                count[f"{field}_positive"] += int(review[field])
        details.append({
            "id": case_id,
            "status": "scored",
            "answerability": case["answerability"],
            "expected_source_uris": sorted(expected),
            "observed_source_uris": sorted(actual),
            "missing_source_uris": sorted(expected - actual),
            "unexpected_source_uris": sorted(actual - expected),
            "source_recall": _fraction(len(tp), len(expected)),
            "source_set_exact": actual == expected if expected else None,
            "review": {key: value for key, value in review.items() if key in (
                "answer_supported", "passage_trace_verified", "abstained_appropriately", "conflict_handled"
            ) and value is not None},
        })
    precision = _fraction(count["true_positive"], count["true_positive"] + count["false_positive"])
    recall = _fraction(count["true_positive"], count["true_positive"] + count["false_negative"])
    f1 = (round(2 * precision * recall / (precision + recall), 6) if precision + recall else 0.0) if precision is not None and recall is not None else None
    reviewed = {}
    for field in ("answer_supported", "passage_trace_verified", "abstained_appropriately", "conflict_handled"):
        n = count[f"{field}_reviewed"]
        reviewed[field] = {"reviewed": n, "positive": count[f"{field}_positive"],
                           "positive_rate": _fraction(count[f"{field}_positive"], n)}
    return {
        "schema_version": 1,
        "scope": "document-source URI identity, not passage- or claim-level automatic grounding",
        "summary": {
            "gold_cases": len(gold), "evaluated_cases": count["evaluated"],
            "missing_observations": len(gold) - count["evaluated"],
            "source_precision_micro": precision,
            "source_recall_micro": recall,
            "source_f1_micro": f1,
            "source_recall_macro_answerable": (round(count["macro_source_recall_sum"] / count["answerable_cases"], 6)
                                                  if count["answerable_cases"] else None),
            "exact_source_set_rate_answerable": _fraction(count["exact_source_set"], count["answerable_cases"]),
            "unanswerable_without_sources_rate": _fraction(count["unanswerable_no_source"], count["unanswerable_cases"]),
            "true_positive_sources": count["true_positive"],
            "false_positive_sources": count["false_positive"],
            "false_negative_sources": count["false_negative"],
            "human_review": reviewed,
        },
        "cases": details,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--gold", required=True, help="Gold JSONL with expected_source_uris")
    parser.add_argument("--observations", required=True, help="Recorded/annotated responses in JSONL")
    parser.add_argument("--output", required=True, help="JSON report path")
    parser.add_argument("--require-complete", action="store_true", help="Exit nonzero for missing observations")
    args = parser.parse_args()
    try:
        result = evaluate(read_jsonl(args.gold), read_jsonl(args.observations))
        write_json(args.output, result)
        print(json.dumps(result["summary"], indent=2, sort_keys=True))
        if args.require_complete and result["summary"]["missing_observations"]:
            return 2
    except (DatasetError, OSError) as exc:
        parser.error(str(exc))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
