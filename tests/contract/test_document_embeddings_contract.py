"""
Contract tests for document embeddings message schemas and translators
Ensures that message formats remain consistent across services
"""

import pytest
from unittest.mock import MagicMock

from trustgraph.schema import DocumentEmbeddingsRequest, DocumentEmbeddingsResponse, Error
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
            vectors=[[0.1, 0.2, 0.3], [0.4, 0.5, 0.6]],
            limit=10,
            user="test_user",
            collection="test_collection"
        )

        # Verify all expected fields exist
        assert hasattr(request, 'vectors')
        assert hasattr(request, 'limit')
        assert hasattr(request, 'user')
        assert hasattr(request, 'collection')

        # Verify field values
        assert request.vectors == [[0.1, 0.2, 0.3], [0.4, 0.5, 0.6]]
        assert request.limit == 10
        assert request.user == "test_user"
        assert request.collection == "test_collection"

    def test_request_translator_to_pulsar(self):
        """Test request translator converts dict to Pulsar schema"""
        translator = DocumentEmbeddingsRequestTranslator()

        data = {
            "vectors": [[0.1, 0.2], [0.3, 0.4]],
            "limit": 5,
            "user": "custom_user",
            "collection": "custom_collection"
        }

        result = translator.to_pulsar(data)

        assert isinstance(result, DocumentEmbeddingsRequest)
        assert result.vectors == [[0.1, 0.2], [0.3, 0.4]]
        assert result.limit == 5
        assert result.user == "custom_user"
        assert result.collection == "custom_collection"

    def test_request_translator_to_pulsar_with_defaults(self):
        """Test request translator uses correct defaults"""
        translator = DocumentEmbeddingsRequestTranslator()

        data = {
            "vectors": [[0.1, 0.2]]
            # No limit, user, or collection provided
        }

        result = translator.to_pulsar(data)

        assert isinstance(result, DocumentEmbeddingsRequest)
        assert result.vectors == [[0.1, 0.2]]
        assert result.limit == 10  # Default
        assert result.user == "trustgraph"  # Default
        assert result.collection == "default"  # Default

    def test_request_translator_from_pulsar(self):
        """Test request translator converts Pulsar schema to dict"""
        translator = DocumentEmbeddingsRequestTranslator()

        request = DocumentEmbeddingsRequest(
            vectors=[[0.5, 0.6]],
            limit=20,
            user="test_user",
            collection="test_collection"
        )

        result = translator.from_pulsar(request)

        assert isinstance(result, dict)
        assert result["vectors"] == [[0.5, 0.6]]
        assert result["limit"] == 20
        assert result["user"] == "test_user"
        assert result["collection"] == "test_collection"


class TestDocumentEmbeddingsResponseContract:
    """Test DocumentEmbeddingsResponse schema contract"""

    def test_response_schema_fields(self):
        """Test that DocumentEmbeddingsResponse has expected fields"""
        # Create a response with chunk_ids
        response = DocumentEmbeddingsResponse(
            error=None,
            chunk_ids=["chunk1", "chunk2", "chunk3"]
        )

        # Verify all expected fields exist
        assert hasattr(response, 'error')
        assert hasattr(response, 'chunk_ids')

        # Verify field values
        assert response.error is None
        assert response.chunk_ids == ["chunk1", "chunk2", "chunk3"]

    def test_response_schema_with_error(self):
        """Test response schema with error"""
        error = Error(
            type="query_error",
            message="Database connection failed"
        )

        response = DocumentEmbeddingsResponse(
            error=error,
            chunk_ids=[]
        )

        assert response.error == error
        assert response.chunk_ids == []

    def test_response_translator_from_pulsar_with_chunk_ids(self):
        """Test response translator converts Pulsar schema with chunk_ids to dict"""
        translator = DocumentEmbeddingsResponseTranslator()

        response = DocumentEmbeddingsResponse(
            error=None,
            chunk_ids=["doc1/c1", "doc2/c2", "doc3/c3"]
        )

        result = translator.from_pulsar(response)

        assert isinstance(result, dict)
        assert "chunk_ids" in result
        assert result["chunk_ids"] == ["doc1/c1", "doc2/c2", "doc3/c3"]

    def test_response_translator_from_pulsar_with_empty_chunk_ids(self):
        """Test response translator handles empty chunk_ids list"""
        translator = DocumentEmbeddingsResponseTranslator()

        response = DocumentEmbeddingsResponse(
            error=None,
            chunk_ids=[]
        )

        result = translator.from_pulsar(response)

        assert isinstance(result, dict)
        assert "chunk_ids" in result
        assert result["chunk_ids"] == []

    def test_response_translator_from_pulsar_with_none_chunk_ids(self):
        """Test response translator handles None chunk_ids"""
        translator = DocumentEmbeddingsResponseTranslator()

        response = MagicMock()
        response.chunk_ids = None

        result = translator.from_pulsar(response)

        assert isinstance(result, dict)
        assert "chunk_ids" not in result or result.get("chunk_ids") is None

    def test_response_translator_from_response_with_completion(self):
        """Test response translator with completion flag"""
        translator = DocumentEmbeddingsResponseTranslator()

        response = DocumentEmbeddingsResponse(
            error=None,
            chunk_ids=["chunk1", "chunk2"]
        )

        result, is_final = translator.from_response_with_completion(response)

        assert isinstance(result, dict)
        assert "chunk_ids" in result
        assert result["chunk_ids"] == ["chunk1", "chunk2"]
        assert is_final is True  # Document embeddings responses are always final

    def test_response_translator_to_pulsar_not_implemented(self):
        """Test that to_pulsar raises NotImplementedError for responses"""
        translator = DocumentEmbeddingsResponseTranslator()

        with pytest.raises(NotImplementedError):
            translator.to_pulsar({"chunk_ids": ["test"]})


class TestDocumentEmbeddingsMessageCompatibility:
    """Test compatibility between request and response messages"""

    def test_request_response_flow(self):
        """Test complete request-response flow maintains data integrity"""
        # Create request
        request_data = {
            "vectors": [[0.1, 0.2, 0.3]],
            "limit": 5,
            "user": "test_user",
            "collection": "test_collection"
        }

        # Convert to Pulsar request
        req_translator = DocumentEmbeddingsRequestTranslator()
        pulsar_request = req_translator.to_pulsar(request_data)

        # Simulate service processing and creating response
        response = DocumentEmbeddingsResponse(
            error=None,
            chunk_ids=["doc1/c1", "doc2/c2"]
        )

        # Convert response back to dict
        resp_translator = DocumentEmbeddingsResponseTranslator()
        response_data = resp_translator.from_pulsar(response)

        # Verify data integrity
        assert isinstance(pulsar_request, DocumentEmbeddingsRequest)
        assert isinstance(response_data, dict)
        assert "chunk_ids" in response_data
        assert len(response_data["chunk_ids"]) == 2

    def test_error_response_flow(self):
        """Test error response flow"""
        # Create error response
        error = Error(
            type="vector_db_error",
            message="Collection not found"
        )

        response = DocumentEmbeddingsResponse(
            error=error,
            chunk_ids=[]
        )

        # Convert response to dict
        translator = DocumentEmbeddingsResponseTranslator()
        response_data = translator.from_pulsar(response)

        # Verify error handling
        assert isinstance(response_data, dict)
        # The translator doesn't include error in the dict, only chunk_ids
        assert "chunk_ids" in response_data
        assert response_data["chunk_ids"] == []
