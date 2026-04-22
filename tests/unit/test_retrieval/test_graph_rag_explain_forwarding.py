"""
Tests that explain_triples are forwarded correctly through the graph-rag
service and client layers.

Covers:
- Service: explain messages include triples from the provenance callback
- Client: explain_callback receives explain_triples from the response
- End-to-end: triples survive the full service → client → callback chain
"""

import pytest
from unittest.mock import MagicMock, AsyncMock, patch

from trustgraph.schema import (
    GraphRagQuery, GraphRagResponse,
    Triple, Term, IRI, LITERAL,
)
from trustgraph.base.graph_rag_client import GraphRagClient


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def make_triple(s_iri, p_iri, o_value, o_type=IRI):
    """Create a Triple with IRI subject/predicate and typed object."""
    o = (
        Term(type=IRI, iri=o_value) if o_type == IRI
        else Term(type=LITERAL, value=o_value)
    )
    return Triple(
        s=Term(type=IRI, iri=s_iri),
        p=Term(type=IRI, iri=p_iri),
        o=o,
    )


def sample_focus_triples():
    """Focus-style triples with a quoted triple (edge selection)."""
    return [
        make_triple(
            "urn:trustgraph:focus:abc",
            "http://www.w3.org/1999/02/22-rdf-syntax-ns#type",
            "https://trustgraph.ai/ns/Focus",
        ),
        make_triple(
            "urn:trustgraph:focus:abc",
            "http://www.w3.org/ns/prov#wasDerivedFrom",
            "urn:trustgraph:exploration:abc",
        ),
        make_triple(
            "urn:trustgraph:focus:abc",
            "https://trustgraph.ai/ns/selectedEdge",
            "urn:trustgraph:edge-sel:abc:0",
        ),
    ]


def sample_question_triples():
    """Question-style triples."""
    return [
        make_triple(
            "urn:trustgraph:question:abc",
            "http://www.w3.org/1999/02/22-rdf-syntax-ns#type",
            "https://trustgraph.ai/ns/GraphRagQuestion",
        ),
        make_triple(
            "urn:trustgraph:question:abc",
            "https://trustgraph.ai/ns/query",
            "What is quantum computing?",
            o_type=LITERAL,
        ),
    ]


# ---------------------------------------------------------------------------
# Service-level: explain messages carry triples
# ---------------------------------------------------------------------------

class TestGraphRagServiceExplainTriples:
    """Test that the graph-rag service includes explain_triples in messages."""

    @patch('trustgraph.retrieval.graph_rag.rag.GraphRag')
    @pytest.mark.asyncio
    async def test_explain_messages_include_triples(self, mock_graph_rag_class):
        """
        When the provenance callback is invoked with triples, the service
        should include them in the explain response message.
        """
        from trustgraph.retrieval.graph_rag.rag import Processor

        processor = Processor(
            taskgroup=MagicMock(),
            id="test-processor",
            entity_limit=50,
            triple_limit=30,
            max_subgraph_size=150,
            max_path_length=2,
        )

        mock_rag_instance = AsyncMock()
        mock_graph_rag_class.return_value = mock_rag_instance

        question_triples = sample_question_triples()
        focus_triples = sample_focus_triples()

        async def mock_query(**kwargs):
            explain_callback = kwargs.get('explain_callback')
            if explain_callback:
                await explain_callback(
                    question_triples, "urn:trustgraph:question:abc"
                )
                await explain_callback(
                    focus_triples, "urn:trustgraph:focus:abc"
                )
            return "The answer."

        mock_rag_instance.query.side_effect = mock_query

        msg = MagicMock()
        msg.value.return_value = GraphRagQuery(
            query="What is quantum computing?",
            collection="default",
            streaming=False,
        )
        msg.properties.return_value = {"id": "test-id"}

        consumer = MagicMock()
        flow = MagicMock()
        mock_response = AsyncMock()
        mock_provenance = AsyncMock()

        def flow_router(name):
            if name == "response":
                return mock_response
            if name == "explainability":
                return mock_provenance
            return AsyncMock()

        flow.side_effect = flow_router

        await processor.on_request(msg, consumer, flow)

        # Find the explain messages
        explain_msgs = [
            call[0][0]
            for call in mock_response.send.call_args_list
            if call[0][0].message_type == "explain"
        ]

        assert len(explain_msgs) == 2

        # First explain message should carry question triples
        assert explain_msgs[0].explain_id == "urn:trustgraph:question:abc"
        assert explain_msgs[0].explain_triples == question_triples

        # Second explain message should carry focus triples
        assert explain_msgs[1].explain_id == "urn:trustgraph:focus:abc"
        assert explain_msgs[1].explain_triples == focus_triples


# ---------------------------------------------------------------------------
# Client-level: explain_callback receives triples
# ---------------------------------------------------------------------------

class TestGraphRagClientExplainForwarding:
    """Test that GraphRagClient.rag() forwards explain_triples to callback."""

    @pytest.mark.asyncio
    async def test_explain_callback_receives_triples(self):
        """
        The explain_callback should receive (explain_id, explain_graph,
        explain_triples) — not just (explain_id, explain_graph).
        """
        focus_triples = sample_focus_triples()

        # Simulate the response sequence the client would receive
        responses = [
            GraphRagResponse(
                message_type="explain",
                explain_id="urn:trustgraph:focus:abc",
                explain_graph="urn:graph:retrieval",
                explain_triples=focus_triples,
            ),
            GraphRagResponse(
                message_type="chunk",
                response="The answer.",
                end_of_stream=True,
            ),
            GraphRagResponse(
                message_type="chunk",
                response="",
                end_of_session=True,
            ),
        ]

        # Capture what the explain_callback receives
        received_calls = []

        async def explain_callback(explain_id, explain_graph, explain_triples):
            received_calls.append({
                "explain_id": explain_id,
                "explain_graph": explain_graph,
                "explain_triples": explain_triples,
            })

        # Patch self.request to feed responses to the recipient
        client = GraphRagClient.__new__(GraphRagClient)

        async def mock_request(req, timeout=600, recipient=None):
            for resp in responses:
                done = await recipient(resp)
                if done:
                    return resp

        client.request = mock_request

        result = await client.rag(
            query="test",
            explain_callback=explain_callback,
        )

        assert result == "The answer."
        assert len(received_calls) == 1
        assert received_calls[0]["explain_id"] == "urn:trustgraph:focus:abc"
        assert received_calls[0]["explain_graph"] == "urn:graph:retrieval"
        assert received_calls[0]["explain_triples"] == focus_triples

    @pytest.mark.asyncio
    async def test_explain_callback_receives_empty_triples(self):
        """
        When an explain event has no triples, the callback should still
        receive an empty list (not None or missing).
        """
        responses = [
            GraphRagResponse(
                message_type="explain",
                explain_id="urn:trustgraph:question:abc",
                explain_graph="urn:graph:retrieval",
                explain_triples=[],
            ),
            GraphRagResponse(
                message_type="chunk",
                response="Answer.",
                end_of_stream=True,
                end_of_session=True,
            ),
        ]

        received_calls = []

        async def explain_callback(explain_id, explain_graph, explain_triples):
            received_calls.append(explain_triples)

        client = GraphRagClient.__new__(GraphRagClient)

        async def mock_request(req, timeout=600, recipient=None):
            for resp in responses:
                done = await recipient(resp)
                if done:
                    return resp

        client.request = mock_request

        await client.rag(query="test", explain_callback=explain_callback)

        assert len(received_calls) == 1
        assert received_calls[0] == []

    @pytest.mark.asyncio
    async def test_multiple_explain_events_all_forward_triples(self):
        """
        Each explain event in a session should forward its own triples.
        """
        q_triples = sample_question_triples()
        f_triples = sample_focus_triples()

        responses = [
            GraphRagResponse(
                message_type="explain",
                explain_id="urn:trustgraph:question:abc",
                explain_graph="urn:graph:retrieval",
                explain_triples=q_triples,
            ),
            GraphRagResponse(
                message_type="explain",
                explain_id="urn:trustgraph:focus:abc",
                explain_graph="urn:graph:retrieval",
                explain_triples=f_triples,
            ),
            GraphRagResponse(
                message_type="chunk",
                response="Answer.",
                end_of_stream=True,
                end_of_session=True,
            ),
        ]

        received_calls = []

        async def explain_callback(explain_id, explain_graph, explain_triples):
            received_calls.append({
                "explain_id": explain_id,
                "explain_triples": explain_triples,
            })

        client = GraphRagClient.__new__(GraphRagClient)

        async def mock_request(req, timeout=600, recipient=None):
            for resp in responses:
                done = await recipient(resp)
                if done:
                    return resp

        client.request = mock_request

        await client.rag(query="test", explain_callback=explain_callback)

        assert len(received_calls) == 2
        assert received_calls[0]["explain_id"] == "urn:trustgraph:question:abc"
        assert received_calls[0]["explain_triples"] == q_triples
        assert received_calls[1]["explain_id"] == "urn:trustgraph:focus:abc"
        assert received_calls[1]["explain_triples"] == f_triples

    @pytest.mark.asyncio
    async def test_no_explain_callback_does_not_error(self):
        """
        When no explain_callback is provided, explain events should be
        silently skipped without errors.
        """
        responses = [
            GraphRagResponse(
                message_type="explain",
                explain_id="urn:trustgraph:question:abc",
                explain_graph="urn:graph:retrieval",
                explain_triples=sample_question_triples(),
            ),
            GraphRagResponse(
                message_type="chunk",
                response="Answer.",
                end_of_stream=True,
                end_of_session=True,
            ),
        ]

        client = GraphRagClient.__new__(GraphRagClient)

        async def mock_request(req, timeout=600, recipient=None):
            for resp in responses:
                done = await recipient(resp)
                if done:
                    return resp

        client.request = mock_request

        result = await client.rag(query="test")
        assert result == "Answer."
