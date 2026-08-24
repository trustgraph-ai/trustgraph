"""Contract tests for REST triples queries used by explainability."""

from unittest.mock import MagicMock

import pytest

from trustgraph.api.explainability import (
    ExplainabilityClient,
    Question,
    RDF_TYPE,
    TG_GRAPH_RAG_QUESTION,
    TG_QUERY,
    TG_QUESTION,
)
from trustgraph.api.flow import FlowInstance
from trustgraph.knowledge import Literal, Uri


def _make_flow(response):
    parent = MagicMock()
    parent.api.workspace = "workspace-a"
    parent.request.return_value = response
    return FlowInstance(parent, "default"), parent


@pytest.mark.parametrize("graph", ["urn:graph:retrieval", "*"])
def test_rest_triples_query_accepts_string_terms_and_graph(graph):
    flow, parent = _make_flow({"response": []})

    result = flow.triples_query(
        s="urn:entity:subject",
        p="urn:relation:predicate",
        o="urn:entity:object",
        g=graph,
        collection="explainability",
        limit=25,
    )

    assert result == []
    parent.request.assert_called_once_with(
        path="default/service/triples",
        request={
            "workspace": "workspace-a",
            "limit": 25,
            "collection": "explainability",
            "s": {"t": "i", "i": "urn:entity:subject"},
            "p": {"t": "i", "i": "urn:relation:predicate"},
            "o": {"t": "i", "i": "urn:entity:object"},
            "g": graph,
        },
    )


def test_rest_triples_query_preserves_typed_terms_without_graph():
    flow, parent = _make_flow({"response": []})

    flow.triples_query(
        s=Uri("urn:entity:subject"),
        p=Uri("urn:relation:label"),
        o=Literal("https://example.org/display-name"),
    )

    request = parent.request.call_args.kwargs["request"]
    assert request["s"] == {"t": "i", "i": "urn:entity:subject"}
    assert request["p"] == {"t": "i", "i": "urn:relation:label"}
    assert request["o"] == {
        "t": "l",
        "v": "https://example.org/display-name",
    }
    assert "g" not in request


def test_explainability_client_uses_rest_flow_contract():
    question_uri = "urn:trustgraph:question:123"
    response = {
        "response": [
            {
                "s": {"t": "i", "i": question_uri},
                "p": {"t": "i", "i": RDF_TYPE},
                "o": {"t": "i", "i": TG_QUESTION},
            },
            {
                "s": {"t": "i", "i": question_uri},
                "p": {"t": "i", "i": RDF_TYPE},
                "o": {"t": "i", "i": TG_GRAPH_RAG_QUESTION},
            },
            {
                "s": {"t": "i", "i": question_uri},
                "p": {"t": "i", "i": TG_QUERY},
                "o": {"t": "l", "v": "What caused the deviation?"},
            },
        ]
    }
    flow, parent = _make_flow(response)
    client = ExplainabilityClient(flow, max_retries=2, retry_delay=0.0)

    entity = client.fetch_entity(
        question_uri,
        graph="urn:graph:retrieval",
        collection="explainability",
    )

    assert isinstance(entity, Question)
    assert entity.query == "What caused the deviation?"
    assert parent.request.call_count == 2
    for call in parent.request.call_args_list:
        request = call.kwargs["request"]
        assert request["s"] == {"t": "i", "i": question_uri}
        assert request["g"] == "urn:graph:retrieval"
        assert request["collection"] == "explainability"
