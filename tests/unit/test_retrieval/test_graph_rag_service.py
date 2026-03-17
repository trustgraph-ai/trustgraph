"""
Unit tests for GraphRAG service message format.
Tests the new message protocol with message_type, explain_id, and end_of_session.
Real-time explainability emission via callback.
"""

import pytest
from unittest.mock import MagicMock, AsyncMock, patch

from trustgraph.retrieval.graph_rag.rag import Processor
from trustgraph.schema import GraphRagQuery, GraphRagResponse


class TestGraphRagService:
    """Test GraphRAG service message protocol"""

    @patch('trustgraph.retrieval.graph_rag.rag.GraphRag')
    @pytest.mark.asyncio
    async def test_non_streaming_sends_chunk_then_provenance_messages(self, mock_graph_rag_class):
        """
        Test that non-streaming mode sends real-time provenance messages
        followed by chunk message with response.
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

        # Setup mock GraphRag instance that calls explain_callback
        mock_rag_instance = AsyncMock()
        mock_graph_rag_class.return_value = mock_rag_instance

        # Mock query() to call the explain_callback with each provenance event
        async def mock_query(**kwargs):
            explain_callback = kwargs.get('explain_callback')
            if explain_callback:
                # Simulate real-time provenance emission
                await explain_callback([], "urn:trustgraph:session:test")
                await explain_callback([], "urn:trustgraph:prov:retrieval:test")
                await explain_callback([], "urn:trustgraph:prov:selection:test")
                await explain_callback([], "urn:trustgraph:prov:answer:test")
            return "A small domesticated mammal."

        mock_rag_instance.query.side_effect = mock_query

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
            streaming=False
        )
        msg.properties.return_value = {"id": "test-id"}

        # Setup flow mock
        consumer = MagicMock()
        flow = MagicMock()

        mock_response_producer = AsyncMock()
        mock_provenance_producer = AsyncMock()
        def flow_router(service_name):
            if service_name == "response":
                return mock_response_producer
            elif service_name == "explainability":
                return mock_provenance_producer
            return AsyncMock()
        flow.side_effect = flow_router

        # Execute
        await processor.on_request(msg, consumer, flow)

        # Verify: 6 messages sent (4 provenance + 1 chunk + 1 end_of_session)
        assert mock_response_producer.send.call_count == 6

        # First 4 messages are explain (emitted in real-time during query)
        for i in range(4):
            prov_msg = mock_response_producer.send.call_args_list[i][0][0]
            assert prov_msg.message_type == "explain"
            assert prov_msg.explain_id is not None

        # 5th message is chunk with response
        chunk_msg = mock_response_producer.send.call_args_list[4][0][0]
        assert chunk_msg.message_type == "chunk"
        assert chunk_msg.response == "A small domesticated mammal."
        assert chunk_msg.end_of_stream is True

        # 6th message is empty chunk with end_of_session=True
        close_msg = mock_response_producer.send.call_args_list[5][0][0]
        assert close_msg.message_type == "chunk"
        assert close_msg.response == ""
        assert close_msg.end_of_session is True

        # Verify provenance triples were sent to provenance queue
        assert mock_provenance_producer.send.call_count == 4

    @patch('trustgraph.retrieval.graph_rag.rag.GraphRag')
    @pytest.mark.asyncio
    async def test_error_response_closes_session(self, mock_graph_rag_class):
        """
        Test that error responses set end_of_session=True.
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
            streaming=False
        )
        msg.properties.return_value = {"id": "test-id"}

        # Setup flow mock
        consumer = MagicMock()
        flow = MagicMock()

        mock_response_producer = AsyncMock()
        mock_provenance_producer = AsyncMock()
        def flow_router(service_name):
            if service_name == "response":
                return mock_response_producer
            elif service_name == "explainability":
                return mock_provenance_producer
            return AsyncMock()
        flow.side_effect = flow_router

        # Execute
        await processor.on_request(msg, consumer, flow)

        # Verify: error response was sent with session closed
        mock_response_producer.send.assert_called_once()
        sent_response = mock_response_producer.send.call_args[0][0]
        assert isinstance(sent_response, GraphRagResponse)
        assert sent_response.message_type == "chunk"
        assert sent_response.error is not None
        assert sent_response.error.message == "Test error"
        assert sent_response.end_of_stream is True
        assert sent_response.end_of_session is True

    @patch('trustgraph.retrieval.graph_rag.rag.GraphRag')
    @pytest.mark.asyncio
    async def test_no_provenance_sends_empty_chunk_to_close(self, mock_graph_rag_class):
        """
        Test that when no provenance callback is invoked, an empty chunk closes the session.
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

        # Setup mock GraphRag instance that doesn't call provenance callback
        mock_rag_instance = AsyncMock()
        mock_graph_rag_class.return_value = mock_rag_instance

        async def mock_query(**kwargs):
            # Don't call explain_callback
            return "Response text"

        mock_rag_instance.query.side_effect = mock_query

        # Setup message
        msg = MagicMock()
        msg.value.return_value = GraphRagQuery(
            query="Test query",
            user="trustgraph",
            collection="default",
            streaming=False
        )
        msg.properties.return_value = {"id": "test-id"}

        # Setup flow mock
        consumer = MagicMock()
        flow = MagicMock()

        mock_response_producer = AsyncMock()
        mock_provenance_producer = AsyncMock()
        def flow_router(service_name):
            if service_name == "response":
                return mock_response_producer
            elif service_name == "explainability":
                return mock_provenance_producer
            return AsyncMock()
        flow.side_effect = flow_router

        # Execute
        await processor.on_request(msg, consumer, flow)

        # Verify: 2 messages (chunk + empty chunk to close)
        assert mock_response_producer.send.call_count == 2

        # First is the response chunk
        chunk_msg = mock_response_producer.send.call_args_list[0][0][0]
        assert chunk_msg.message_type == "chunk"
        assert chunk_msg.response == "Response text"
        assert chunk_msg.end_of_stream is True

        # Second is empty chunk to close session
        close_msg = mock_response_producer.send.call_args_list[1][0][0]
        assert close_msg.message_type == "chunk"
        assert close_msg.response == ""
        assert close_msg.end_of_session is True
