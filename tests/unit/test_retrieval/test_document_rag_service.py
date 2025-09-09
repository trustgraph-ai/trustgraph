"""
Unit test for DocumentRAG service parameter passing fix.
Tests that user and collection parameters from the message are correctly
passed to the DocumentRag.query() method.
"""

import pytest
from unittest.mock import MagicMock, AsyncMock, patch

from trustgraph.retrieval.document_rag.rag import Processor
from trustgraph.schema import DocumentRagQuery, DocumentRagResponse


class TestDocumentRagService:
    """Test DocumentRAG service parameter passing"""

    @patch('trustgraph.retrieval.document_rag.rag.DocumentRag')
    @pytest.mark.asyncio
    async def test_user_and_collection_parameters_passed_to_query(self, mock_document_rag_class):
        """
        Test that user and collection from message are passed to DocumentRag.query().
        
        This is a regression test for the bug where user/collection parameters
        were ignored, causing wrong collection names like 'd_trustgraph_default_384'
        instead of 'd_my_user_test_coll_1_384'.
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
        mock_rag_instance.query.return_value = "test response"
        
        # Setup message with custom user/collection
        msg = MagicMock()
        msg.value.return_value = DocumentRagQuery(
            query="test query",
            user="my_user",        # Custom user (not default "trustgraph")  
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
            user="my_user",           # Must be from message, not hardcoded default
            collection="test_coll_1", # Must be from message, not hardcoded default  
            doc_limit=5
        )
        
        # Verify response was sent
        mock_producer.send.assert_called_once()
        sent_response = mock_producer.send.call_args[0][0]
        assert isinstance(sent_response, DocumentRagResponse)
        assert sent_response.response == "test response"
        assert sent_response.error is None