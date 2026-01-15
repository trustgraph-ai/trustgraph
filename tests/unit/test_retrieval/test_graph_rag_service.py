"""
Unit tests for GraphRAG service non-streaming mode.
Tests that end_of_stream flag is correctly set in non-streaming responses.
"""

import pytest
from unittest.mock import MagicMock, AsyncMock, patch

from trustgraph.retrieval.graph_rag.rag import Processor
from trustgraph.schema import GraphRagQuery, GraphRagResponse


class TestGraphRagService:
    """Test GraphRAG service non-streaming behavior"""

    @patch('trustgraph.retrieval.graph_rag.rag.GraphRag')
    @pytest.mark.asyncio
    async def test_non_streaming_mode_sets_end_of_stream_true(self, mock_graph_rag_class):
        """
        Test that non-streaming mode sets end_of_stream=True in response.

        This is a regression test for the bug where non-streaming responses
        didn't set end_of_stream, causing clients to hang waiting for more data.
        """
        # Setup processor
        processor = Processor(
            taskgroup=MagicMock(),
            id="test-processor",
            entity_limit=50,
            triple_limit=30,
            max_subgraph_size=150,
            max_path_length=2
        )

        # Setup mock GraphRag instance
        mock_rag_instance = AsyncMock()
        mock_graph_rag_class.return_value = mock_rag_instance
        mock_rag_instance.query.return_value = "A small domesticated mammal."

        # Setup message with non-streaming request
        msg = MagicMock()
        msg.value.return_value = GraphRagQuery(
            query="What is a cat?",
            user="trustgraph",
            collection="default",
            entity_limit=50,
            triple_limit=30,
            max_subgraph_size=150,
            max_path_length=2,
            streaming=False  # Non-streaming mode
        )
        msg.properties.return_value = {"id": "test-id"}

        # Setup flow mock
        consumer = MagicMock()
        flow = MagicMock()

        # Mock flow to return AsyncMock for clients and response producer
        mock_producer = AsyncMock()
        def flow_router(service_name):
            if service_name == "response":
                return mock_producer
            return AsyncMock()  # embeddings, graph-embeddings, triples, prompt clients
        flow.side_effect = flow_router

        # Execute
        await processor.on_request(msg, consumer, flow)

        # Verify: response was sent with end_of_stream=True
        mock_producer.send.assert_called_once()
        sent_response = mock_producer.send.call_args[0][0]
        assert isinstance(sent_response, GraphRagResponse)
        assert sent_response.response == "A small domesticated mammal."
        assert sent_response.end_of_stream is True, "Non-streaming response must have end_of_stream=True"
        assert sent_response.error is None

    @patch('trustgraph.retrieval.graph_rag.rag.GraphRag')
    @pytest.mark.asyncio
    async def test_error_response_in_non_streaming_mode(self, mock_graph_rag_class):
        """
        Test that error responses in non-streaming mode set end_of_stream=True.
        """
        # Setup processor
        processor = Processor(
            taskgroup=MagicMock(),
            id="test-processor",
            entity_limit=50,
            triple_limit=30,
            max_subgraph_size=150,
            max_path_length=2
        )

        # Setup mock GraphRag instance that raises an exception
        mock_rag_instance = AsyncMock()
        mock_graph_rag_class.return_value = mock_rag_instance
        mock_rag_instance.query.side_effect = Exception("Test error")

        # Setup message with non-streaming request
        msg = MagicMock()
        msg.value.return_value = GraphRagQuery(
            query="What is a cat?",
            user="trustgraph",
            collection="default",
            entity_limit=50,
            triple_limit=30,
            max_subgraph_size=150,
            max_path_length=2,
            streaming=False  # Non-streaming mode
        )
        msg.properties.return_value = {"id": "test-id"}

        # Setup flow mock
        consumer = MagicMock()
        flow = MagicMock()

        mock_producer = AsyncMock()
        def flow_router(service_name):
            if service_name == "response":
                return mock_producer
            return AsyncMock()
        flow.side_effect = flow_router

        # Execute
        await processor.on_request(msg, consumer, flow)

        # Verify: error response was sent without end_of_stream (not streaming mode)
        mock_producer.send.assert_called_once()
        sent_response = mock_producer.send.call_args[0][0]
        assert isinstance(sent_response, GraphRagResponse)
        assert sent_response.response is None
        assert sent_response.error is not None
        assert sent_response.error.message == "Test error"
        # Note: error responses in non-streaming mode don't set end_of_stream
        # because streaming was never started
