"""Exercise the actual RAGChunk / ProvenanceEvent-shaped event contract."""
import sys
from dataclasses import dataclass, field
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from evaluate import DatasetError
from record import collect_stream


@dataclass
class RAGChunk:
    content: str = ""
    sources: list = field(default_factory=list)
    error: object = None


@dataclass
class ProvenanceEvent:
    explain_id: str
    explain_graph: str
    event_type: str
    triples: list


def test_stream_provenance_and_final_chunk_sources():
    result = collect_stream([
        ProvenanceEvent("urn:question:1", "urn:graph:1", "question", [{"s": 1}]),
        RAGChunk("A"), RAGChunk("nswer"),
        RAGChunk("", [{"uri": "urn:doc:one", "title": "Doc 1"}]),
    ])
    assert result["answer"] == "Answer"
    assert result["sources"] == [{"uri": "urn:doc:one", "title": "Doc 1"}]
    assert result["provenance"] == [{"explain_id": "urn:question:1", "explain_graph": "urn:graph:1",
                                      "event_type": "question", "triple_count": 1}]


def test_stream_deduplicates_sources():
    assert collect_stream([RAGChunk("A", [{"uri": "urn:a", "title": "A"}]),
                           RAGChunk("B", [{"uri": "urn:a", "title": "A"}])])["sources"] == [
        {"uri": "urn:a", "title": "A"}]


def test_malformed_source_is_rejected():
    with pytest.raises(DatasetError):
        collect_stream([RAGChunk("", [{"title": "missing URI"}])])


def test_stream_error_fails_fast():
    with pytest.raises(RuntimeError, match="RAG stream error"):
        collect_stream([RAGChunk(error={"message": "broken"})])


def test_unknown_chunk_fails_fast():
    with pytest.raises(DatasetError):
        collect_stream([42])


def test_empty_stream_does_not_masquerade_as_abstention():
    with pytest.raises(RuntimeError, match="without an answer chunk"):
        collect_stream([])


def test_record_cases_calls_existing_graph_rag_explain_api(monkeypatch):
    import types
    from record import record_cases

    calls = []

    class FakeFlow:
        def graph_rag_explain(self, query, collection):
            calls.append((query, collection))
            return iter([RAGChunk("Evidence", [{"uri": "doc:a", "title": "A"}])])

    class FakeSocket:
        def flow(self, flow_id):
            assert flow_id == "live-flow"
            return FakeFlow()

    class FakeApi:
        def __init__(self, **kwargs):
            assert kwargs == {"url": "http://localhost:8888/", "timeout": 90,
                              "token": None, "workspace": "default"}

        def __enter__(self):
            return self

        def __exit__(self, *args):
            return False

        def socket(self):
            return FakeSocket()

    monkeypatch.setitem(sys.modules, "trustgraph", types.ModuleType("trustgraph"))
    fake_api_module = types.ModuleType("trustgraph.api")
    fake_api_module.Api = FakeApi
    monkeypatch.setitem(sys.modules, "trustgraph.api", fake_api_module)

    result = record_cases([
        {"id": "case", "question": "Query?", "answerability": "answerable",
         "expected_source_uris": ["doc:a"]}],
        url="http://localhost:8888/", flow_id="live-flow", collection="my-coll",
        workspace="default", token=None, timeout=90)
    assert calls == [("Query?", "my-coll")]
    assert result == [{"id": "case", "answer": "Evidence",
                       "sources": [{"uri": "doc:a", "title": "A"}], "provenance": []}]
