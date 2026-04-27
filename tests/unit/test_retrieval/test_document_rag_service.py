"""
Unit test for DocumentRAG service parameter passing fix.
Tests that the collection parameter from the message is correctly
passed to the DocumentRag.query() method.
"""

import pytest
from unittest.mock import MagicMock, AsyncMock, patch, ANY

from trustgraph.retrieval.document_rag.rag import Processor
from trustgraph.schema import DocumentRagQuery, DocumentRagResponse


class TestDocumentRagService:
    """Test DocumentRAG service parameter passing"""

    @patch('trustgraph.retrieval.document_rag.rag.DocumentRag')
    @pytest.mark.asyncio
    async def test_collection_parameter_passed_to_query(self, mock_document_rag_class):
        """
        Test that collection from message is passed to DocumentRag.query().

        This is a regression test for the bug where the collection parameter
        was ignored, causing wrong collection names like 'd_trustgraph_default_384'
        instead of one that reflects the requested collection.
        """
        # Setup processor
        processor = Processor(
            taskgroup=MagicMock(),
            id="test-processor",
            doc_limit=10
        )

        # Setup mock DocumentRag instance
        mock_rag_instance = AsyncMock()
        mock_document_rag_class.return_value = mock_rag_instance
        mock_rag_instance.query.return_value = ("test response", {"in_token": None, "out_token": None, "model": None})

        # Setup message with custom collection
        msg = MagicMock()
        msg.value.return_value = DocumentRagQuery(
            query="test query",
            collection="test_coll_1",  # Custom collection (not default "default")
            doc_limit=5
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
            return AsyncMock()  # embeddings, doc-embeddings, prompt clients
        flow.side_effect = flow_router
        
        # Execute
        await processor.on_request(msg, consumer, flow)
        
        # Verify: DocumentRag.query was called with correct parameters
        mock_rag_instance.query.assert_called_once_with(
            "test query",
            workspace=ANY,            # Workspace comes from flow.workspace (mock)
            collection="test_coll_1", # Must be from message, not hardcoded default
            doc_limit=5,
            explain_callback=ANY,     # Explainability callback is always passed
            save_answer_callback=ANY, # Librarian save callback is always passed
        )
        
        # Verify response was sent
        mock_producer.send.assert_called_once()
        sent_response = mock_producer.send.call_args[0][0]
        assert isinstance(sent_response, DocumentRagResponse)
        assert sent_response.response == "test response"
        assert sent_response.error is None

    @patch('trustgraph.retrieval.document_rag.rag.DocumentRag')
    @pytest.mark.asyncio
    async def test_non_streaming_mode_sets_end_of_stream_true(self, mock_document_rag_class):
        """
        Test that non-streaming mode sets end_of_stream=True in response.

        This is a regression test for the bug where non-streaming responses
        didn't set end_of_stream, causing clients to hang waiting for more data.
        """
        # Setup processor
        processor = Processor(
            taskgroup=MagicMock(),
            id="test-processor",
            doc_limit=10
        )

        # Setup mock DocumentRag instance
        mock_rag_instance = AsyncMock()
        mock_document_rag_class.return_value = mock_rag_instance
        mock_rag_instance.query.return_value = ("A document about cats.", {"in_token": None, "out_token": None, "model": None})

        # Setup message with non-streaming request
        msg = MagicMock()
        msg.value.return_value = DocumentRagQuery(
            query="What is a cat?",
            collection="default",
            doc_limit=10,
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

        # Verify: response was sent with end_of_stream=True
        mock_producer.send.assert_called_once()
        sent_response = mock_producer.send.call_args[0][0]
        assert isinstance(sent_response, DocumentRagResponse)
        assert sent_response.response == "A document about cats."
        assert sent_response.end_of_stream is True, "Non-streaming response must have end_of_stream=True"
        assert sent_response.end_of_session is True
        assert sent_response.error is None