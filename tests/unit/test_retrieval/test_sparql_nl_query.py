"""
Unit tests for the sparql-nl-query orchestration service.
Tests _execute (the orchestration pipeline) and _term_to_string.
"""

import pytest
from unittest.mock import AsyncMock, MagicMock
from dataclasses import dataclass, field

from trustgraph.retrieval.sparql_nl_query.service import Processor
from trustgraph.schema import (
    SparqlNLQueryRequest, SparqlNLQueryResponse,
    QuestionToSparqlRequest, QuestionToSparqlResponse,
    SparqlQueryRequest, SparqlQueryResponse,
    Error, Term, IRI, LITERAL, TRIPLE,
    ResolvedEntity,
)
from trustgraph.schema.triples import SparqlBinding


@pytest.fixture
def processor():
    return object.__new__(Processor)


def _nl_response(sparql="SELECT ?x WHERE { ?x a ?t }", entities=None,
                 error=None):
    return QuestionToSparqlResponse(
        error=error,
        sparql=sparql,
        resolved_entities=entities or [],
    )


def _sparql_response(query_type="select", variables=None, bindings=None,
                     ask_result=False, error=None):
    return SparqlQueryResponse(
        error=error,
        query_type=query_type,
        variables=variables or [],
        bindings=bindings or [],
        ask_result=ask_result,
    )


def _mock_flow(nl_response, sparql_response=None):
    nl_client = AsyncMock()
    nl_client.request = AsyncMock(return_value=nl_response)

    sparql_client = AsyncMock()
    if sparql_response is not None:
        sparql_client.request = AsyncMock(return_value=sparql_response)

    def flow_lookup(name):
        if name == "nl-sparql-request":
            return nl_client
        if name == "sparql-request":
            return sparql_client
        raise KeyError(name)

    flow = MagicMock(side_effect=flow_lookup)
    return flow, nl_client, sparql_client


class TestTermToString:

    def test_iri_returns_iri_field(self, processor):
        term = Term(type=IRI, iri="http://example.org/Dog")
        assert processor._term_to_string(term) == "http://example.org/Dog"

    def test_literal_returns_value_field(self, processor):
        term = Term(type=LITERAL, value="Fido")
        assert processor._term_to_string(term) == "Fido"

    def test_triple_returns_str(self, processor):
        term = Term(type=TRIPLE)
        result = processor._term_to_string(term)
        assert isinstance(result, str)

    def test_none_returns_empty(self, processor):
        assert processor._term_to_string(None) == ""


class TestExecuteHappyPath:

    @pytest.mark.asyncio
    async def test_select_returns_full_response(self, processor):
        entities = [
            ResolvedEntity(
                mention="Fido", uri="http://example.org/Fido",
                rdf_type="Dog", score=0.95,
            ),
        ]
        nl_resp = _nl_response(
            sparql="SELECT ?name WHERE { <http://example.org/Fido> :name ?name }",
            entities=entities,
        )
        sparql_resp = _sparql_response(
            query_type="select",
            variables=["name"],
            bindings=[
                SparqlBinding(values=[Term(type=LITERAL, value="Fido")]),
            ],
        )
        flow, _, _ = _mock_flow(nl_resp, sparql_resp)

        request = SparqlNLQueryRequest(question="What is the dog's name?")
        result = await processor._execute(flow, request)

        assert result.error is None
        assert result.sparql == nl_resp.sparql
        assert result.resolved_entities == entities
        assert result.query_type == "select"
        assert result.variables == ["name"]
        assert result.bindings == [["Fido"]]

    @pytest.mark.asyncio
    async def test_ask_query(self, processor):
        nl_resp = _nl_response(sparql="ASK { <http://example.org/Fido> a :Dog }")
        sparql_resp = _sparql_response(
            query_type="ask", ask_result=True,
        )
        flow, _, _ = _mock_flow(nl_resp, sparql_resp)

        request = SparqlNLQueryRequest(question="Is Fido a dog?")
        result = await processor._execute(flow, request)

        assert result.error is None
        assert result.ask_result is True
        assert result.query_type == "ask"

    @pytest.mark.asyncio
    async def test_multiple_bindings_rows(self, processor):
        nl_resp = _nl_response(sparql="SELECT ?x WHERE { ?x a :Dog }")
        sparql_resp = _sparql_response(
            query_type="select",
            variables=["x"],
            bindings=[
                SparqlBinding(values=[Term(type=IRI, iri="http://example.org/Fido")]),
                SparqlBinding(values=[Term(type=IRI, iri="http://example.org/Rex")]),
            ],
        )
        flow, _, _ = _mock_flow(nl_resp, sparql_resp)

        request = SparqlNLQueryRequest(question="List dogs")
        result = await processor._execute(flow, request)

        assert len(result.bindings) == 2
        assert result.bindings[0] == ["http://example.org/Fido"]
        assert result.bindings[1] == ["http://example.org/Rex"]

    @pytest.mark.asyncio
    async def test_null_terms_become_empty_strings(self, processor):
        nl_resp = _nl_response(sparql="SELECT ?a ?b WHERE { ?a :p ?b }")
        sparql_resp = _sparql_response(
            query_type="select",
            variables=["a", "b"],
            bindings=[
                SparqlBinding(values=[
                    Term(type=IRI, iri="http://example.org/x"),
                    None,
                ]),
            ],
        )
        flow, _, _ = _mock_flow(nl_resp, sparql_resp)

        request = SparqlNLQueryRequest(question="test")
        result = await processor._execute(flow, request)

        assert result.bindings == [["http://example.org/x", ""]]


class TestExecuteErrors:

    @pytest.mark.asyncio
    async def test_nl_sparql_error(self, processor):
        nl_resp = _nl_response(
            sparql="",
            error=Error(type="llm-error", message="LLM failed"),
        )
        flow, _, _ = _mock_flow(nl_resp)

        request = SparqlNLQueryRequest(question="test")
        result = await processor._execute(flow, request)

        assert result.error is not None
        assert result.error.type == "nl-sparql-error"
        assert "LLM failed" in result.error.message

    @pytest.mark.asyncio
    async def test_empty_sparql(self, processor):
        nl_resp = _nl_response(sparql="")
        flow, _, _ = _mock_flow(nl_resp)

        request = SparqlNLQueryRequest(question="test")
        result = await processor._execute(flow, request)

        assert result.error is not None
        assert result.error.type == "nl-sparql-error"
        assert "empty" in result.error.message.lower()

    @pytest.mark.asyncio
    async def test_sparql_execution_error_preserves_sparql_and_entities(
        self, processor
    ):
        entities = [
            ResolvedEntity(mention="x", uri="http://example.org/x"),
        ]
        nl_resp = _nl_response(
            sparql="SELECT ?x WHERE { bad }",
            entities=entities,
        )
        sparql_resp = _sparql_response(
            error=Error(type="parse-error", message="Bad SPARQL"),
        )
        flow, _, _ = _mock_flow(nl_resp, sparql_resp)

        request = SparqlNLQueryRequest(question="test")
        result = await processor._execute(flow, request)

        assert result.error is not None
        assert result.error.type == "sparql-execution-error"
        assert result.sparql == "SELECT ?x WHERE { bad }"
        assert result.resolved_entities == entities


class TestExecuteParameterPassing:

    @pytest.mark.asyncio
    async def test_defaults_collection_and_limit(self, processor):
        nl_resp = _nl_response()
        sparql_resp = _sparql_response()
        flow, nl_client, sparql_client = _mock_flow(nl_resp, sparql_resp)

        request = SparqlNLQueryRequest(question="test")
        await processor._execute(flow, request)

        nl_call = nl_client.request.call_args[0][0]
        assert nl_call.collection == "default"
        assert nl_call.limit == 10

        sparql_call = sparql_client.request.call_args[0][0]
        assert sparql_call.collection == "default"
        assert sparql_call.limit == 10

    @pytest.mark.asyncio
    async def test_custom_collection_and_limit(self, processor):
        nl_resp = _nl_response()
        sparql_resp = _sparql_response()
        flow, nl_client, sparql_client = _mock_flow(nl_resp, sparql_resp)

        request = SparqlNLQueryRequest(
            question="test", collection="mydata", limit=50,
        )
        await processor._execute(flow, request)

        nl_call = nl_client.request.call_args[0][0]
        assert nl_call.collection == "mydata"
        assert nl_call.limit == 50

        sparql_call = sparql_client.request.call_args[0][0]
        assert sparql_call.collection == "mydata"
        assert sparql_call.limit == 50

    @pytest.mark.asyncio
    async def test_sparql_not_called_on_nl_error(self, processor):
        nl_resp = _nl_response(
            error=Error(type="fail", message="broken"),
        )
        flow, _, sparql_client = _mock_flow(nl_resp)

        request = SparqlNLQueryRequest(question="test")
        await processor._execute(flow, request)

        sparql_client.request.assert_not_called()
