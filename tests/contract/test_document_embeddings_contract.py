"""
Contract tests for document embeddings message schemas and translators
Ensures that message formats remain consistent across services
"""

import pytest
from unittest.mock import MagicMock

from trustgraph.schema import DocumentEmbeddingsRequest, DocumentEmbeddingsResponse, ChunkMatch, Error
from trustgraph.messaging.translators.embeddings_query import (
    DocumentEmbeddingsRequestTranslator,
    DocumentEmbeddingsResponseTranslator
)


class TestDocumentEmbeddingsRequestContract:
    """Test DocumentEmbeddingsRequest schema contract"""

    def test_request_schema_fields(self):
        """Test that DocumentEmbeddingsRequest has expected fields"""
        # Create a request
        request = DocumentEmbeddingsRequest(
            vector=[0.1, 0.2, 0.3],
            limit=10,
            user="test_user",
            collection="test_collection"
        )

        # Verify all expected fields exist
        assert hasattr(request, 'vector')
        assert hasattr(request, 'limit')
        assert hasattr(request, 'user')
        assert hasattr(request, 'collection')

        # Verify field values
        assert request.vector == [0.1, 0.2, 0.3]
        assert request.limit == 10
        assert request.user == "test_user"
        assert request.collection == "test_collection"

    def test_request_translator_decode(self):
        """Test request translator converts dict to Pulsar schema"""
        translator = DocumentEmbeddingsRequestTranslator()

        data = {
            "vector": [0.1, 0.2, 0.3, 0.4],
            "limit": 5,
            "user": "custom_user",
            "collection": "custom_collection"
        }

        result = translator.decode(data)

        assert isinstance(result, DocumentEmbeddingsRequest)
        assert result.vector == [0.1, 0.2, 0.3, 0.4]
        assert result.limit == 5
        assert result.user == "custom_user"
        assert result.collection == "custom_collection"

    def test_request_translator_decode_with_defaults(self):
        """Test request translator uses correct defaults"""
        translator = DocumentEmbeddingsRequestTranslator()

        data = {
            "vector": [0.1, 0.2]
            # No limit, user, or collection provided
        }

        result = translator.decode(data)

        assert isinstance(result, DocumentEmbeddingsRequest)
        assert result.vector == [0.1, 0.2]
        assert result.limit == 10  # Default
        assert result.user == "trustgraph"  # Default
        assert result.collection == "default"  # Default

    def test_request_translator_encode(self):
        """Test request translator converts Pulsar schema to dict"""
        translator = DocumentEmbeddingsRequestTranslator()

        request = DocumentEmbeddingsRequest(
            vector=[0.5, 0.6],
            limit=20,
            user="test_user",
            collection="test_collection"
        )

        result = translator.encode(request)

        assert isinstance(result, dict)
        assert result["vector"] == [0.5, 0.6]
        assert result["limit"] == 20
        assert result["user"] == "test_user"
        assert result["collection"] == "test_collection"


class TestDocumentEmbeddingsResponseContract:
    """Test DocumentEmbeddingsResponse schema contract"""

    def test_response_schema_fields(self):
        """Test that DocumentEmbeddingsResponse has expected fields"""
        # Create a response with chunks
        response = DocumentEmbeddingsResponse(
            error=None,
            chunks=[
                ChunkMatch(chunk_id="chunk1", score=0.9),
                ChunkMatch(chunk_id="chunk2", score=0.8),
                ChunkMatch(chunk_id="chunk3", score=0.7)
            ]
        )

        # Verify all expected fields exist
        assert hasattr(response, 'error')
        assert hasattr(response, 'chunks')

        # Verify field values
        assert response.error is None
        assert len(response.chunks) == 3
        assert response.chunks[0].chunk_id == "chunk1"
        assert response.chunks[0].score == 0.9

    def test_response_schema_with_error(self):
        """Test response schema with error"""
        error = Error(
            type="query_error",
            message="Database connection failed"
        )

        response = DocumentEmbeddingsResponse(
            error=error,
            chunks=[]
        )

        assert response.error == error
        assert response.chunks == []

    def test_response_translator_encode_with_chunks(self):
        """Test response translator converts Pulsar schema with chunks to dict"""
        translator = DocumentEmbeddingsResponseTranslator()

        response = DocumentEmbeddingsResponse(
            error=None,
            chunks=[
                ChunkMatch(chunk_id="doc1/c1", score=0.95),
                ChunkMatch(chunk_id="doc2/c2", score=0.85),
                ChunkMatch(chunk_id="doc3/c3", score=0.75)
            ]
        )

        result = translator.encode(response)

        assert isinstance(result, dict)
        assert "chunks" in result
        assert len(result["chunks"]) == 3
        assert result["chunks"][0]["chunk_id"] == "doc1/c1"
        assert result["chunks"][0]["score"] == 0.95

    def test_response_translator_encode_with_empty_chunks(self):
        """Test response translator handles empty chunks list"""
        translator = DocumentEmbeddingsResponseTranslator()

        response = DocumentEmbeddingsResponse(
            error=None,
            chunks=[]
        )

        result = translator.encode(response)

        assert isinstance(result, dict)
        assert "chunks" in result
        assert result["chunks"] == []

    def test_response_translator_encode_with_none_chunks(self):
        """Test response translator handles None chunks"""
        translator = DocumentEmbeddingsResponseTranslator()

        response = MagicMock()
        response.chunks = None

        result = translator.encode(response)

        assert isinstance(result, dict)
        assert "chunks" not in result or result.get("chunks") is None

    def test_response_translator_encode_with_completion(self):
        """Test response translator with completion flag"""
        translator = DocumentEmbeddingsResponseTranslator()

        response = DocumentEmbeddingsResponse(
            error=None,
            chunks=[
                ChunkMatch(chunk_id="chunk1", score=0.9),
                ChunkMatch(chunk_id="chunk2", score=0.8)
            ]
        )

        result, is_final = translator.encode_with_completion(response)

        assert isinstance(result, dict)
        assert "chunks" in result
        assert len(result["chunks"]) == 2
        assert result["chunks"][0]["chunk_id"] == "chunk1"
        assert is_final is True  # Document embeddings responses are always final

    def test_response_translator_decode_not_implemented(self):
        """Test that decode raises NotImplementedError for responses"""
        translator = DocumentEmbeddingsResponseTranslator()

        with pytest.raises(NotImplementedError):
            translator.decode({"chunks": [{"chunk_id": "test", "score": 0.9}]})


class TestDocumentEmbeddingsMessageCompatibility:
    """Test compatibility between request and response messages"""

    def test_request_response_flow(self):
        """Test complete request-response flow maintains data integrity"""
        # Create request
        request_data = {
            "vector": [0.1, 0.2, 0.3],
            "limit": 5,
            "user": "test_user",
            "collection": "test_collection"
        }

        # Convert to Pulsar request
        req_translator = DocumentEmbeddingsRequestTranslator()
        pulsar_request = req_translator.decode(request_data)

        # Simulate service processing and creating response
        response = DocumentEmbeddingsResponse(
            error=None,
            chunks=[
                ChunkMatch(chunk_id="doc1/c1", score=0.95),
                ChunkMatch(chunk_id="doc2/c2", score=0.85)
            ]
        )

        # Convert response back to dict
        resp_translator = DocumentEmbeddingsResponseTranslator()
        response_data = resp_translator.encode(response)

        # Verify data integrity
        assert isinstance(pulsar_request, DocumentEmbeddingsRequest)
        assert isinstance(response_data, dict)
        assert "chunks" in response_data
        assert len(response_data["chunks"]) == 2

    def test_error_response_flow(self):
        """Test error response flow"""
        # Create error response
        error = Error(
            type="vector_db_error",
            message="Collection not found"
        )

        response = DocumentEmbeddingsResponse(
            error=error,
            chunks=[]
        )

        # Convert response to dict
        translator = DocumentEmbeddingsResponseTranslator()
        response_data = translator.encode(response)

        # Verify error handling
        assert isinstance(response_data, dict)
        # The translator doesn't include error in the dict, only chunks
        assert "chunks" in response_data
        assert response_data["chunks"] == []
