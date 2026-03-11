"""
Tests for DocumentRAG retrieval implementation
"""

import pytest
from unittest.mock import MagicMock, AsyncMock

from trustgraph.retrieval.document_rag.document_rag import DocumentRag, Query


# Sample chunk content mapping for tests
CHUNK_CONTENT = {
    "doc/c1": "Document 1 content",
    "doc/c2": "Document 2 content",
    "doc/c3": "Relevant document content",
    "doc/c4": "Another document",
    "doc/c5": "Default doc",
    "doc/c6": "Verbose test doc",
    "doc/c7": "Verbose doc content",
    "doc/ml1": "Machine learning is a subset of artificial intelligence...",
    "doc/ml2": "ML algorithms learn patterns from data to make predictions...",
    "doc/ml3": "Common ML techniques include supervised and unsupervised learning...",
}


@pytest.fixture
def mock_fetch_chunk():
    """Create a mock fetch_chunk function"""
    async def fetch(chunk_id, user):
        return CHUNK_CONTENT.get(chunk_id, f"Content for {chunk_id}")
    return fetch


class TestDocumentRag:
    """Test cases for DocumentRag class"""

    def test_document_rag_initialization_with_defaults(self, mock_fetch_chunk):
        """Test DocumentRag initialization with default verbose setting"""
        # Create mock clients
        mock_prompt_client = MagicMock()
        mock_embeddings_client = MagicMock()
        mock_doc_embeddings_client = MagicMock()

        # Initialize DocumentRag
        document_rag = DocumentRag(
            prompt_client=mock_prompt_client,
            embeddings_client=mock_embeddings_client,
            doc_embeddings_client=mock_doc_embeddings_client,
            fetch_chunk=mock_fetch_chunk
        )

        # Verify initialization
        assert document_rag.prompt_client == mock_prompt_client
        assert document_rag.embeddings_client == mock_embeddings_client
        assert document_rag.doc_embeddings_client == mock_doc_embeddings_client
        assert document_rag.fetch_chunk == mock_fetch_chunk
        assert document_rag.verbose is False  # Default value

    def test_document_rag_initialization_with_verbose(self, mock_fetch_chunk):
        """Test DocumentRag initialization with verbose enabled"""
        # Create mock clients
        mock_prompt_client = MagicMock()
        mock_embeddings_client = MagicMock()
        mock_doc_embeddings_client = MagicMock()

        # Initialize DocumentRag with verbose=True
        document_rag = DocumentRag(
            prompt_client=mock_prompt_client,
            embeddings_client=mock_embeddings_client,
            doc_embeddings_client=mock_doc_embeddings_client,
            fetch_chunk=mock_fetch_chunk,
            verbose=True
        )

        # Verify initialization
        assert document_rag.prompt_client == mock_prompt_client
        assert document_rag.embeddings_client == mock_embeddings_client
        assert document_rag.doc_embeddings_client == mock_doc_embeddings_client
        assert document_rag.fetch_chunk == mock_fetch_chunk
        assert document_rag.verbose is True


class TestQuery:
    """Test cases for Query class"""

    def test_query_initialization_with_defaults(self):
        """Test Query initialization with default parameters"""
        # Create mock DocumentRag
        mock_rag = MagicMock()

        # Initialize Query with defaults
        query = Query(
            rag=mock_rag,
            user="test_user",
            collection="test_collection",
            verbose=False
        )

        # Verify initialization
        assert query.rag == mock_rag
        assert query.user == "test_user"
        assert query.collection == "test_collection"
        assert query.verbose is False
        assert query.doc_limit == 20  # Default value

    def test_query_initialization_with_custom_doc_limit(self):
        """Test Query initialization with custom doc_limit"""
        # Create mock DocumentRag
        mock_rag = MagicMock()

        # Initialize Query with custom doc_limit
        query = Query(
            rag=mock_rag,
            user="custom_user",
            collection="custom_collection",
            verbose=True,
            doc_limit=50
        )

        # Verify initialization
        assert query.rag == mock_rag
        assert query.user == "custom_user"
        assert query.collection == "custom_collection"
        assert query.verbose is True
        assert query.doc_limit == 50

    @pytest.mark.asyncio
    async def test_get_vector_method(self):
        """Test Query.get_vector method calls embeddings client correctly"""
        # Create mock DocumentRag with embeddings client
        mock_rag = MagicMock()
        mock_embeddings_client = AsyncMock()
        mock_rag.embeddings_client = mock_embeddings_client

        # Mock the embed method to return test vectors in batch format
        # New format: [[[vectors_for_text1]]] - returns first text's vector set
        expected_vectors = [[0.1, 0.2, 0.3], [0.4, 0.5, 0.6]]
        mock_embeddings_client.embed.return_value = [expected_vectors]

        # Initialize Query
        query = Query(
            rag=mock_rag,
            user="test_user",
            collection="test_collection",
            verbose=False
        )

        # Call get_vector
        test_query = "What documents are relevant?"
        result = await query.get_vector(test_query)

        # Verify embeddings client was called correctly (now expects list)
        mock_embeddings_client.embed.assert_called_once_with([test_query])

        # Verify result matches expected vectors (extracted from batch)
        assert result == expected_vectors

    @pytest.mark.asyncio
    async def test_get_docs_method(self):
        """Test Query.get_docs method retrieves documents correctly"""
        # Create mock DocumentRag with clients
        mock_rag = MagicMock()
        mock_embeddings_client = AsyncMock()
        mock_doc_embeddings_client = AsyncMock()
        mock_rag.embeddings_client = mock_embeddings_client
        mock_rag.doc_embeddings_client = mock_doc_embeddings_client

        # Mock fetch_chunk function
        async def mock_fetch(chunk_id, user):
            return CHUNK_CONTENT.get(chunk_id, f"Content for {chunk_id}")
        mock_rag.fetch_chunk = mock_fetch

        # Mock the embedding and document query responses
        # New batch format: [[[vectors]]] - get_vector extracts [0]
        test_vectors = [[0.1, 0.2, 0.3]]
        mock_embeddings_client.embed.return_value = [test_vectors]

        # Mock document embeddings returns ChunkMatch objects
        mock_match1 = MagicMock()
        mock_match1.chunk_id = "doc/c1"
        mock_match1.score = 0.95
        mock_match2 = MagicMock()
        mock_match2.chunk_id = "doc/c2"
        mock_match2.score = 0.85
        mock_doc_embeddings_client.query.return_value = [mock_match1, mock_match2]

        # Initialize Query
        query = Query(
            rag=mock_rag,
            user="test_user",
            collection="test_collection",
            verbose=False,
            doc_limit=15
        )

        # Call get_docs
        test_query = "Find relevant documents"
        result = await query.get_docs(test_query)

        # Verify embeddings client was called (now expects list)
        mock_embeddings_client.embed.assert_called_once_with([test_query])

        # Verify doc embeddings client was called correctly (with extracted vector)
        mock_doc_embeddings_client.query.assert_called_once_with(
            vector=test_vectors,
            limit=15,
            user="test_user",
            collection="test_collection"
        )

        # Verify result is tuple of (docs, chunk_ids)
        docs, chunk_ids = result
        assert "Document 1 content" in docs
        assert "Document 2 content" in docs
        assert "doc/c1" in chunk_ids
        assert "doc/c2" in chunk_ids

    @pytest.mark.asyncio
    async def test_document_rag_query_method(self, mock_fetch_chunk):
        """Test DocumentRag.query method orchestrates full document RAG pipeline"""
        # Create mock clients
        mock_prompt_client = AsyncMock()
        mock_embeddings_client = AsyncMock()
        mock_doc_embeddings_client = AsyncMock()

        # Mock embeddings and document embeddings responses
        # New batch format: [[[vectors]]] - get_vector extracts [0]
        test_vectors = [[0.1, 0.2, 0.3]]
        mock_match1 = MagicMock()
        mock_match1.chunk_id = "doc/c3"
        mock_match1.score = 0.9
        mock_match2 = MagicMock()
        mock_match2.chunk_id = "doc/c4"
        mock_match2.score = 0.8
        expected_response = "This is the document RAG response"

        mock_embeddings_client.embed.return_value = [test_vectors]
        mock_doc_embeddings_client.query.return_value = [mock_match1, mock_match2]
        mock_prompt_client.document_prompt.return_value = expected_response

        # Initialize DocumentRag
        document_rag = DocumentRag(
            prompt_client=mock_prompt_client,
            embeddings_client=mock_embeddings_client,
            doc_embeddings_client=mock_doc_embeddings_client,
            fetch_chunk=mock_fetch_chunk,
            verbose=False
        )

        # Call DocumentRag.query
        result = await document_rag.query(
            query="test query",
            user="test_user",
            collection="test_collection",
            doc_limit=10
        )

        # Verify embeddings client was called (now expects list)
        mock_embeddings_client.embed.assert_called_once_with(["test query"])

        # Verify doc embeddings client was called (with extracted vector)
        mock_doc_embeddings_client.query.assert_called_once_with(
            vector=test_vectors,
            limit=10,
            user="test_user",
            collection="test_collection"
        )

        # Verify prompt client was called with fetched documents and query
        mock_prompt_client.document_prompt.assert_called_once()
        call_args = mock_prompt_client.document_prompt.call_args
        assert call_args.kwargs["query"] == "test query"
        # Documents should be fetched content, not chunk_ids
        docs = call_args.kwargs["documents"]
        assert "Relevant document content" in docs
        assert "Another document" in docs

        # Verify result
        assert result == expected_response

    @pytest.mark.asyncio
    async def test_document_rag_query_with_defaults(self, mock_fetch_chunk):
        """Test DocumentRag.query method with default parameters"""
        # Create mock clients
        mock_prompt_client = AsyncMock()
        mock_embeddings_client = AsyncMock()
        mock_doc_embeddings_client = AsyncMock()

        # Mock responses (batch format)
        mock_embeddings_client.embed.return_value = [[[0.1, 0.2]]]
        mock_match = MagicMock()
        mock_match.chunk_id = "doc/c5"
        mock_match.score = 0.9
        mock_doc_embeddings_client.query.return_value = [mock_match]
        mock_prompt_client.document_prompt.return_value = "Default response"

        # Initialize DocumentRag
        document_rag = DocumentRag(
            prompt_client=mock_prompt_client,
            embeddings_client=mock_embeddings_client,
            doc_embeddings_client=mock_doc_embeddings_client,
            fetch_chunk=mock_fetch_chunk
        )

        # Call DocumentRag.query with minimal parameters
        result = await document_rag.query("simple query")

        # Verify default parameters were used (vector extracted from batch)
        mock_doc_embeddings_client.query.assert_called_once_with(
            vector=[[0.1, 0.2]],
            limit=20,  # Default doc_limit
            user="trustgraph",  # Default user
            collection="default"  # Default collection
        )

        assert result == "Default response"

    @pytest.mark.asyncio
    async def test_get_docs_with_verbose_output(self):
        """Test Query.get_docs method with verbose logging"""
        # Create mock DocumentRag with clients
        mock_rag = MagicMock()
        mock_embeddings_client = AsyncMock()
        mock_doc_embeddings_client = AsyncMock()
        mock_rag.embeddings_client = mock_embeddings_client
        mock_rag.doc_embeddings_client = mock_doc_embeddings_client

        # Mock fetch_chunk
        async def mock_fetch(chunk_id, user):
            return CHUNK_CONTENT.get(chunk_id, f"Content for {chunk_id}")
        mock_rag.fetch_chunk = mock_fetch

        # Mock responses (batch format)
        mock_embeddings_client.embed.return_value = [[[0.7, 0.8]]]
        mock_match = MagicMock()
        mock_match.chunk_id = "doc/c6"
        mock_match.score = 0.88
        mock_doc_embeddings_client.query.return_value = [mock_match]

        # Initialize Query with verbose=True
        query = Query(
            rag=mock_rag,
            user="test_user",
            collection="test_collection",
            verbose=True,
            doc_limit=5
        )

        # Call get_docs
        result = await query.get_docs("verbose test")

        # Verify calls were made (now expects list)
        mock_embeddings_client.embed.assert_called_once_with(["verbose test"])
        mock_doc_embeddings_client.query.assert_called_once()

        # Verify result is tuple of (docs, chunk_ids) with fetched content
        docs, chunk_ids = result
        assert "Verbose test doc" in docs
        assert "doc/c6" in chunk_ids

    @pytest.mark.asyncio
    async def test_document_rag_query_with_verbose(self, mock_fetch_chunk):
        """Test DocumentRag.query method with verbose logging enabled"""
        # Create mock clients
        mock_prompt_client = AsyncMock()
        mock_embeddings_client = AsyncMock()
        mock_doc_embeddings_client = AsyncMock()

        # Mock responses (batch format)
        mock_embeddings_client.embed.return_value = [[[0.3, 0.4]]]
        mock_match = MagicMock()
        mock_match.chunk_id = "doc/c7"
        mock_match.score = 0.92
        mock_doc_embeddings_client.query.return_value = [mock_match]
        mock_prompt_client.document_prompt.return_value = "Verbose RAG response"

        # Initialize DocumentRag with verbose=True
        document_rag = DocumentRag(
            prompt_client=mock_prompt_client,
            embeddings_client=mock_embeddings_client,
            doc_embeddings_client=mock_doc_embeddings_client,
            fetch_chunk=mock_fetch_chunk,
            verbose=True
        )

        # Call DocumentRag.query
        result = await document_rag.query("verbose query test")

        # Verify all clients were called (now expects list)
        mock_embeddings_client.embed.assert_called_once_with(["verbose query test"])
        mock_doc_embeddings_client.query.assert_called_once()

        # Verify prompt client was called with fetched content
        call_args = mock_prompt_client.document_prompt.call_args
        assert call_args.kwargs["query"] == "verbose query test"
        assert "Verbose doc content" in call_args.kwargs["documents"]

        assert result == "Verbose RAG response"

    @pytest.mark.asyncio
    async def test_get_docs_with_empty_results(self):
        """Test Query.get_docs method when no documents are found"""
        # Create mock DocumentRag with clients
        mock_rag = MagicMock()
        mock_embeddings_client = AsyncMock()
        mock_doc_embeddings_client = AsyncMock()
        mock_rag.embeddings_client = mock_embeddings_client
        mock_rag.doc_embeddings_client = mock_doc_embeddings_client

        # Mock fetch_chunk (won't be called if no chunk_ids)
        async def mock_fetch(chunk_id, user):
            return f"Content for {chunk_id}"
        mock_rag.fetch_chunk = mock_fetch

        # Mock responses - empty chunk_id list (batch format)
        mock_embeddings_client.embed.return_value = [[[0.1, 0.2]]]
        mock_doc_embeddings_client.query.return_value = []  # No chunk_ids found

        # Initialize Query
        query = Query(
            rag=mock_rag,
            user="test_user",
            collection="test_collection",
            verbose=False
        )

        # Call get_docs
        result = await query.get_docs("query with no results")

        # Verify calls were made (now expects list)
        mock_embeddings_client.embed.assert_called_once_with(["query with no results"])
        mock_doc_embeddings_client.query.assert_called_once()

        # Verify empty result is returned (tuple of empty lists)
        assert result == ([], [])

    @pytest.mark.asyncio
    async def test_document_rag_query_with_empty_documents(self, mock_fetch_chunk):
        """Test DocumentRag.query method when no documents are retrieved"""
        # Create mock clients
        mock_prompt_client = AsyncMock()
        mock_embeddings_client = AsyncMock()
        mock_doc_embeddings_client = AsyncMock()

        # Mock responses - no chunk_ids found (batch format)
        mock_embeddings_client.embed.return_value = [[[0.5, 0.6]]]
        mock_doc_embeddings_client.query.return_value = []  # Empty chunk_id list
        mock_prompt_client.document_prompt.return_value = "No documents found response"

        # Initialize DocumentRag
        document_rag = DocumentRag(
            prompt_client=mock_prompt_client,
            embeddings_client=mock_embeddings_client,
            doc_embeddings_client=mock_doc_embeddings_client,
            fetch_chunk=mock_fetch_chunk,
            verbose=False
        )

        # Call DocumentRag.query
        result = await document_rag.query("query with no matching docs")

        # Verify prompt client was called with empty document list
        mock_prompt_client.document_prompt.assert_called_once_with(
            query="query with no matching docs",
            documents=[]
        )

        assert result == "No documents found response"

    @pytest.mark.asyncio
    async def test_get_vector_with_verbose(self):
        """Test Query.get_vector method with verbose logging"""
        # Create mock DocumentRag with embeddings client
        mock_rag = MagicMock()
        mock_embeddings_client = AsyncMock()
        mock_rag.embeddings_client = mock_embeddings_client

        # Mock the embed method (batch format)
        expected_vectors = [[0.9, 1.0, 1.1]]
        mock_embeddings_client.embed.return_value = [expected_vectors]

        # Initialize Query with verbose=True
        query = Query(
            rag=mock_rag,
            user="test_user",
            collection="test_collection",
            verbose=True
        )

        # Call get_vector
        result = await query.get_vector("verbose vector test")

        # Verify embeddings client was called (now expects list)
        mock_embeddings_client.embed.assert_called_once_with(["verbose vector test"])

        # Verify result (extracted from batch)
        assert result == expected_vectors

    @pytest.mark.asyncio
    async def test_document_rag_integration_flow(self, mock_fetch_chunk):
        """Test complete DocumentRag integration with realistic data flow"""
        # Create mock clients
        mock_prompt_client = AsyncMock()
        mock_embeddings_client = AsyncMock()
        mock_doc_embeddings_client = AsyncMock()

        # Mock realistic responses (batch format)
        query_text = "What is machine learning?"
        query_vectors = [[0.1, 0.2, 0.3, 0.4, 0.5]]
        retrieved_chunk_ids = ["doc/ml1", "doc/ml2", "doc/ml3"]
        final_response = "Machine learning is a field of AI that enables computers to learn and improve from experience without being explicitly programmed."

        mock_embeddings_client.embed.return_value = [query_vectors]
        mock_matches = []
        for chunk_id in retrieved_chunk_ids:
            mock_match = MagicMock()
            mock_match.chunk_id = chunk_id
            mock_match.score = 0.9
            mock_matches.append(mock_match)
        mock_doc_embeddings_client.query.return_value = mock_matches
        mock_prompt_client.document_prompt.return_value = final_response

        # Initialize DocumentRag
        document_rag = DocumentRag(
            prompt_client=mock_prompt_client,
            embeddings_client=mock_embeddings_client,
            doc_embeddings_client=mock_doc_embeddings_client,
            fetch_chunk=mock_fetch_chunk,
            verbose=False
        )

        # Execute full pipeline
        result = await document_rag.query(
            query=query_text,
            user="research_user",
            collection="ml_knowledge",
            doc_limit=25
        )

        # Verify complete pipeline execution (now expects list)
        mock_embeddings_client.embed.assert_called_once_with([query_text])

        mock_doc_embeddings_client.query.assert_called_once_with(
            vector=query_vectors,
            limit=25,
            user="research_user",
            collection="ml_knowledge"
        )

        # Verify prompt client was called with fetched document content
        mock_prompt_client.document_prompt.assert_called_once()
        call_args = mock_prompt_client.document_prompt.call_args
        assert call_args.kwargs["query"] == query_text

        # Verify documents were fetched from chunk_ids
        docs = call_args.kwargs["documents"]
        assert "Machine learning is a subset of artificial intelligence..." in docs
        assert "ML algorithms learn patterns from data to make predictions..." in docs
        assert "Common ML techniques include supervised and unsupervised learning..." in docs

        # Verify final result
        assert result == final_response
