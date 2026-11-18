"""Offline source-scoring tests; no TrustGraph server required."""
import json
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from evaluate import DatasetError, evaluate, read_jsonl, validate_gold, write_json


def g(case_id="x", expected=None, answerability="answerable"):
    return {"id": case_id, "question": "Question?", "answerability": answerability,
            "expected_source_uris": expected if expected is not None else ["doc:a"]}


def o(case_id="x", sources=None, answer="Answer.", review=None):
    data = {"id": case_id, "answer": answer,
            "sources": [{"uri": uri} for uri in (sources if sources is not None else ["doc:a"])]}
    if review is not None:
        data["review"] = review
    return data


def test_perfect_retrieval_metrics():
    summary = evaluate([g()], [o()])["summary"]
    assert summary["source_precision_micro"] == 1
    assert summary["source_recall_micro"] == 1
    assert summary["source_f1_micro"] == 1
    assert summary["exact_source_set_rate_answerable"] == 1
    assert summary["human_review"]["answer_supported"]["reviewed"] == 0


def test_partial_recall_multi_doc_and_false_positive():
    r = evaluate([g(expected=["doc:a", "doc:b"])], [o(sources=["doc:a", "doc:c"])])
    s = r["summary"]
    assert s["source_precision_micro"] == .5
    assert s["source_recall_micro"] == .5
    assert s["source_recall_macro_answerable"] == .5
    assert s["exact_source_set_rate_answerable"] == 0
    assert r["cases"][0]["missing_source_uris"] == ["doc:b"]
    assert r["cases"][0]["unexpected_source_uris"] == ["doc:c"]


def test_unanswerable_is_not_denominator_for_recall():
    result = evaluate([g("known"), g("unknown", [], "unanswerable")],
                      [o("known"), o("unknown", [])])
    s = result["summary"]
    assert s["source_recall_macro_answerable"] == 1
    assert s["unanswerable_without_sources_rate"] == 1
    assert result["cases"][1]["source_recall"] is None


def test_unanswerable_false_citation_counted():
    s = evaluate([g("unknown", [], "unanswerable")], [o("unknown", ["doc:irrelevant"])])["summary"]
    assert s["false_positive_sources"] == 1
    assert s["unanswerable_without_sources_rate"] == 0
    assert s["source_recall_micro"] is None


def test_unanswered_retrieval_is_not_automatically_abstention():
    s = evaluate([g("missing", [], "unanswerable")], [o("missing", [], answer="Made-up answer")])["summary"]
    assert s["unanswerable_without_sources_rate"] == 1
    assert s["human_review"]["abstained_appropriately"]["positive_rate"] is None


def test_manual_review_is_only_counted_when_explicit():
    s = evaluate([g("a"), g("b")], [o("a", review={"answer_supported": False, "passage_trace_verified": True}),
                                        o("b")])["summary"]
    assert s["human_review"]["answer_supported"] == {"reviewed": 1, "positive": 0, "positive_rate": 0}
    assert s["human_review"]["passage_trace_verified"] == {"reviewed": 1, "positive": 1, "positive_rate": 1}


def test_missing_observation_is_reported_not_implicitly_scored():
    r = evaluate([g("a"), g("b")], [o("a")])
    assert r["summary"]["evaluated_cases"] == 1
    assert r["summary"]["missing_observations"] == 1
    assert r["cases"][1]["status"] == "missing_observation"


@pytest.mark.parametrize("rows", [
    [g("x"), g("x")],
    [g(expected=[])],
    [g(expected=["x", "x"])],
    [g(answerability="not_valid")],
    [g("x", ["doc:a"], "unanswerable")],
    [{**g(), "evidence": [{"source_uri": "not-in-gold", "passage": "foo"}]}],
])
def test_invalid_gold_rejected(rows):
    with pytest.raises(DatasetError):
        validate_gold(rows)


@pytest.mark.parametrize("rows", [
    [o("x"), o("x")],
    [o("unknown")],
    [{**o(), "sources": [{"title": "No URI"}]}],
    [o(sources=["doc:a", "doc:a"])],
    [o(review={"answer_supported": "yes"})],
    [{**o(), "error": "connection refused"}],
])
def test_invalid_observations_rejected(rows):
    with pytest.raises(DatasetError):
        evaluate([g()], rows)


def test_jsonl_error_has_line_number(tmp_path):
    p = tmp_path / "bad.jsonl"
    p.write_text('{"id": "good"}\n{not json}\n')
    with pytest.raises(DatasetError, match=r":2:"):
        read_jsonl(p)


def test_roundtrip_unicode(tmp_path):
    p = tmp_path / "report.json"
    write_json(p, {"question": "Qué pasó?"})
    assert json.loads(p.read_text(encoding="utf-8")) == {"question": "Qué pasó?"}


def test_review_labels_are_scoped_to_matching_scenarios():
    with pytest.raises(DatasetError, match="conflict_handled"):
        evaluate([g()], [o(review={"conflict_handled": True})])
    with pytest.raises(DatasetError, match="abstained_appropriately"):
        evaluate([g()], [o(review={"abstained_appropriately": True})])


def test_zero_f1_is_zero_not_missing():
    s = evaluate([g()], [o(sources=["doc:wrong"])])["summary"]
    assert s["source_f1_micro"] == 0.0
