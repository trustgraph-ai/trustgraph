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
    async def test_extract_concepts(self):
        """Test Query.extract_concepts extracts concepts from query"""
        mock_rag = MagicMock()
        mock_prompt_client = AsyncMock()
        mock_rag.prompt_client = mock_prompt_client

        # Mock the prompt response with concept lines
        mock_prompt_client.prompt.return_value = "machine learning\nartificial intelligence\ndata patterns"

        query = Query(
            rag=mock_rag,
            user="test_user",
            collection="test_collection",
            verbose=False
        )

        result = await query.extract_concepts("What is machine learning?")

        mock_prompt_client.prompt.assert_called_once_with(
            "extract-concepts",
            variables={"query": "What is machine learning?"}
        )
        assert result == ["machine learning", "artificial intelligence", "data patterns"]

    @pytest.mark.asyncio
    async def test_extract_concepts_fallback_to_raw_query(self):
        """Test Query.extract_concepts falls back to raw query when no concepts extracted"""
        mock_rag = MagicMock()
        mock_prompt_client = AsyncMock()
        mock_rag.prompt_client = mock_prompt_client

        # Mock empty response
        mock_prompt_client.prompt.return_value = ""

        query = Query(
            rag=mock_rag,
            user="test_user",
            collection="test_collection",
            verbose=False
        )

        result = await query.extract_concepts("What is ML?")

        assert result == ["What is ML?"]

    @pytest.mark.asyncio
    async def test_get_vectors_method(self):
        """Test Query.get_vectors method calls embeddings client correctly"""
        mock_rag = MagicMock()
        mock_embeddings_client = AsyncMock()
        mock_rag.embeddings_client = mock_embeddings_client

        # Mock the embed method - returns vectors for each concept
        expected_vectors = [[0.1, 0.2, 0.3], [0.4, 0.5, 0.6]]
        mock_embeddings_client.embed.return_value = expected_vectors

        query = Query(
            rag=mock_rag,
            user="test_user",
            collection="test_collection",
            verbose=False
        )

        concepts = ["machine learning", "data patterns"]
        result = await query.get_vectors(concepts)

        mock_embeddings_client.embed.assert_called_once_with(concepts)
        assert result == expected_vectors

    @pytest.mark.asyncio
    async def test_get_docs_method(self):
        """Test Query.get_docs method retrieves documents correctly"""
        mock_rag = MagicMock()
        mock_embeddings_client = AsyncMock()
        mock_doc_embeddings_client = AsyncMock()
        mock_rag.embeddings_client = mock_embeddings_client
        mock_rag.doc_embeddings_client = mock_doc_embeddings_client

        # Mock fetch_chunk function
        async def mock_fetch(chunk_id, user):
            return CHUNK_CONTENT.get(chunk_id, f"Content for {chunk_id}")
        mock_rag.fetch_chunk = mock_fetch

        # Mock embeddings - one vector per concept
        mock_embeddings_client.embed.return_value = [[0.1, 0.2, 0.3]]

        # Mock document embeddings returns ChunkMatch objects
        mock_match1 = MagicMock()
        mock_match1.chunk_id = "doc/c1"
        mock_match1.score = 0.95
        mock_match2 = MagicMock()
        mock_match2.chunk_id = "doc/c2"
        mock_match2.score = 0.85
        mock_doc_embeddings_client.query.return_value = [mock_match1, mock_match2]

        query = Query(
            rag=mock_rag,
            user="test_user",
            collection="test_collection",
            verbose=False,
            doc_limit=15
        )

        # Call get_docs with concepts list
        concepts = ["test concept"]
        result = await query.get_docs(concepts)

        # Verify embeddings client was called with concepts
        mock_embeddings_client.embed.assert_called_once_with(concepts)

        # Verify doc embeddings client was called
        mock_doc_embeddings_client.query.assert_called_once_with(
            vector=[0.1, 0.2, 0.3],
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
        mock_prompt_client = AsyncMock()
        mock_embeddings_client = AsyncMock()
        mock_doc_embeddings_client = AsyncMock()

        # Mock concept extraction
        mock_prompt_client.prompt.return_value = "test concept"

        # Mock embeddings - one vector per concept
        test_vectors = [[0.1, 0.2, 0.3]]
        mock_embeddings_client.embed.return_value = test_vectors

        mock_match1 = MagicMock()
        mock_match1.chunk_id = "doc/c3"
        mock_match1.score = 0.9
        mock_match2 = MagicMock()
        mock_match2.chunk_id = "doc/c4"
        mock_match2.score = 0.8
        expected_response = "This is the document RAG response"

        mock_doc_embeddings_client.query.return_value = [mock_match1, mock_match2]
        mock_prompt_client.document_prompt.return_value = expected_response

        document_rag = DocumentRag(
            prompt_client=mock_prompt_client,
            embeddings_client=mock_embeddings_client,
            doc_embeddings_client=mock_doc_embeddings_client,
            fetch_chunk=mock_fetch_chunk,
            verbose=False
        )

        result = await document_rag.query(
            query="test query",
            user="test_user",
            collection="test_collection",
            doc_limit=10
        )

        # Verify concept extraction was called
        mock_prompt_client.prompt.assert_called_once_with(
            "extract-concepts",
            variables={"query": "test query"}
        )

        # Verify embeddings called with extracted concepts
        mock_embeddings_client.embed.assert_called_once_with(["test concept"])

        # Verify doc embeddings client was called
        mock_doc_embeddings_client.query.assert_called_once_with(
            vector=[0.1, 0.2, 0.3],
            limit=10,
            user="test_user",
            collection="test_collection"
        )

        # Verify prompt client was called with fetched documents and query
        mock_prompt_client.document_prompt.assert_called_once()
        call_args = mock_prompt_client.document_prompt.call_args
        assert call_args.kwargs["query"] == "test query"
        docs = call_args.kwargs["documents"]
        assert "Relevant document content" in docs
        assert "Another document" in docs

        assert result == expected_response

    @pytest.mark.asyncio
    async def test_document_rag_query_with_defaults(self, mock_fetch_chunk):
        """Test DocumentRag.query method with default parameters"""
        mock_prompt_client = AsyncMock()
        mock_embeddings_client = AsyncMock()
        mock_doc_embeddings_client = AsyncMock()

        # Mock concept extraction fallback (empty → raw query)
        mock_prompt_client.prompt.return_value = ""

        # Mock responses
        mock_embeddings_client.embed.return_value = [[[0.1, 0.2]]]
        mock_match = MagicMock()
        mock_match.chunk_id = "doc/c5"
        mock_match.score = 0.9
        mock_doc_embeddings_client.query.return_value = [mock_match]
        mock_prompt_client.document_prompt.return_value = "Default response"

        document_rag = DocumentRag(
            prompt_client=mock_prompt_client,
            embeddings_client=mock_embeddings_client,
            doc_embeddings_client=mock_doc_embeddings_client,
            fetch_chunk=mock_fetch_chunk
        )

        result = await document_rag.query("simple query")

        # Verify default parameters were used
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
        mock_rag = MagicMock()
        mock_embeddings_client = AsyncMock()
        mock_doc_embeddings_client = AsyncMock()
        mock_rag.embeddings_client = mock_embeddings_client
        mock_rag.doc_embeddings_client = mock_doc_embeddings_client

        # Mock fetch_chunk
        async def mock_fetch(chunk_id, user):
            return CHUNK_CONTENT.get(chunk_id, f"Content for {chunk_id}")
        mock_rag.fetch_chunk = mock_fetch

        # Mock responses - one vector per concept
        mock_embeddings_client.embed.return_value = [[[0.7, 0.8]]]
        mock_match = MagicMock()
        mock_match.chunk_id = "doc/c6"
        mock_match.score = 0.88
        mock_doc_embeddings_client.query.return_value = [mock_match]

        query = Query(
            rag=mock_rag,
            user="test_user",
            collection="test_collection",
            verbose=True,
            doc_limit=5
        )

        # Call get_docs with concepts
        result = await query.get_docs(["verbose test"])

        mock_embeddings_client.embed.assert_called_once_with(["verbose test"])
        mock_doc_embeddings_client.query.assert_called_once()

        docs, chunk_ids = result
        assert "Verbose test doc" in docs
        assert "doc/c6" in chunk_ids

    @pytest.mark.asyncio
    async def test_document_rag_query_with_verbose(self, mock_fetch_chunk):
        """Test DocumentRag.query method with verbose logging enabled"""
        mock_prompt_client = AsyncMock()
        mock_embeddings_client = AsyncMock()
        mock_doc_embeddings_client = AsyncMock()

        # Mock concept extraction
        mock_prompt_client.prompt.return_value = "verbose query test"

        # Mock responses
        mock_embeddings_client.embed.return_value = [[[0.3, 0.4]]]
        mock_match = MagicMock()
        mock_match.chunk_id = "doc/c7"
        mock_match.score = 0.92
        mock_doc_embeddings_client.query.return_value = [mock_match]
        mock_prompt_client.document_prompt.return_value = "Verbose RAG response"

        document_rag = DocumentRag(
            prompt_client=mock_prompt_client,
            embeddings_client=mock_embeddings_client,
            doc_embeddings_client=mock_doc_embeddings_client,
            fetch_chunk=mock_fetch_chunk,
            verbose=True
        )

        result = await document_rag.query("verbose query test")

        mock_embeddings_client.embed.assert_called_once()
        mock_doc_embeddings_client.query.assert_called_once()

        call_args = mock_prompt_client.document_prompt.call_args
        assert call_args.kwargs["query"] == "verbose query test"
        assert "Verbose doc content" in call_args.kwargs["documents"]

        assert result == "Verbose RAG response"

    @pytest.mark.asyncio
    async def test_get_docs_with_empty_results(self):
        """Test Query.get_docs method when no documents are found"""
        mock_rag = MagicMock()
        mock_embeddings_client = AsyncMock()
        mock_doc_embeddings_client = AsyncMock()
        mock_rag.embeddings_client = mock_embeddings_client
        mock_rag.doc_embeddings_client = mock_doc_embeddings_client

        async def mock_fetch(chunk_id, user):
            return f"Content for {chunk_id}"
        mock_rag.fetch_chunk = mock_fetch

        # Mock responses - empty results
        mock_embeddings_client.embed.return_value = [[[0.1, 0.2]]]
        mock_doc_embeddings_client.query.return_value = []

        query = Query(
            rag=mock_rag,
            user="test_user",
            collection="test_collection",
            verbose=False
        )

        result = await query.get_docs(["query with no results"])

        mock_embeddings_client.embed.assert_called_once_with(["query with no results"])
        mock_doc_embeddings_client.query.assert_called_once()

        assert result == ([], [])

    @pytest.mark.asyncio
    async def test_document_rag_query_with_empty_documents(self, mock_fetch_chunk):
        """Test DocumentRag.query method when no documents are retrieved"""
        mock_prompt_client = AsyncMock()
        mock_embeddings_client = AsyncMock()
        mock_doc_embeddings_client = AsyncMock()

        # Mock concept extraction
        mock_prompt_client.prompt.return_value = "query with no matching docs"

        mock_embeddings_client.embed.return_value = [[[0.5, 0.6]]]
        mock_doc_embeddings_client.query.return_value = []
        mock_prompt_client.document_prompt.return_value = "No documents found response"

        document_rag = DocumentRag(
            prompt_client=mock_prompt_client,
            embeddings_client=mock_embeddings_client,
            doc_embeddings_client=mock_doc_embeddings_client,
            fetch_chunk=mock_fetch_chunk,
            verbose=False
        )

        result = await document_rag.query("query with no matching docs")

        mock_prompt_client.document_prompt.assert_called_once_with(
            query="query with no matching docs",
            documents=[]
        )

        assert result == "No documents found response"

    @pytest.mark.asyncio
    async def test_get_vectors_with_verbose(self):
        """Test Query.get_vectors method with verbose logging"""
        mock_rag = MagicMock()
        mock_embeddings_client = AsyncMock()
        mock_rag.embeddings_client = mock_embeddings_client

        expected_vectors = [[0.9, 1.0, 1.1]]
        mock_embeddings_client.embed.return_value = expected_vectors

        query = Query(
            rag=mock_rag,
            user="test_user",
            collection="test_collection",
            verbose=True
        )

        result = await query.get_vectors(["verbose vector test"])

        mock_embeddings_client.embed.assert_called_once_with(["verbose vector test"])
        assert result == expected_vectors

    @pytest.mark.asyncio
    async def test_document_rag_integration_flow(self, mock_fetch_chunk):
        """Test complete DocumentRag integration with realistic data flow"""
        mock_prompt_client = AsyncMock()
        mock_embeddings_client = AsyncMock()
        mock_doc_embeddings_client = AsyncMock()

        query_text = "What is machine learning?"
        final_response = "Machine learning is a field of AI that enables computers to learn and improve from experience without being explicitly programmed."

        # Mock concept extraction
        mock_prompt_client.prompt.return_value = "machine learning\nartificial intelligence"

        # Mock embeddings - one vector per concept
        query_vectors = [[0.1, 0.2, 0.3, 0.4, 0.5], [0.6, 0.7, 0.8, 0.9, 1.0]]
        mock_embeddings_client.embed.return_value = query_vectors

        # Each concept query returns some matches
        mock_matches_1 = [
            MagicMock(chunk_id="doc/ml1", score=0.9),
            MagicMock(chunk_id="doc/ml2", score=0.85),
        ]
        mock_matches_2 = [
            MagicMock(chunk_id="doc/ml2", score=0.88),  # duplicate
            MagicMock(chunk_id="doc/ml3", score=0.82),
        ]
        mock_doc_embeddings_client.query.side_effect = [mock_matches_1, mock_matches_2]
        mock_prompt_client.document_prompt.return_value = final_response

        document_rag = DocumentRag(
            prompt_client=mock_prompt_client,
            embeddings_client=mock_embeddings_client,
            doc_embeddings_client=mock_doc_embeddings_client,
            fetch_chunk=mock_fetch_chunk,
            verbose=False
        )

        result = await document_rag.query(
            query=query_text,
            user="research_user",
            collection="ml_knowledge",
            doc_limit=25
        )

        # Verify concept extraction
        mock_prompt_client.prompt.assert_called_once_with(
            "extract-concepts",
            variables={"query": query_text}
        )

        # Verify embeddings called with concepts
        mock_embeddings_client.embed.assert_called_once_with(
            ["machine learning", "artificial intelligence"]
        )

        # Verify two per-concept queries were made (25 // 2 = 12 per concept)
        assert mock_doc_embeddings_client.query.call_count == 2

        # Verify prompt client was called with fetched document content
        mock_prompt_client.document_prompt.assert_called_once()
        call_args = mock_prompt_client.document_prompt.call_args
        assert call_args.kwargs["query"] == query_text

        # Verify documents were fetched and deduplicated
        docs = call_args.kwargs["documents"]
        assert "Machine learning is a subset of artificial intelligence..." in docs
        assert "ML algorithms learn patterns from data to make predictions..." in docs
        assert "Common ML techniques include supervised and unsupervised learning..." in docs
        assert len(docs) == 3  # doc/ml2 deduplicated

        assert result == final_response

    @pytest.mark.asyncio
    async def test_get_docs_deduplicates_across_concepts(self):
        """Test that get_docs deduplicates chunks across multiple concepts"""
        mock_rag = MagicMock()
        mock_embeddings_client = AsyncMock()
        mock_doc_embeddings_client = AsyncMock()
        mock_rag.embeddings_client = mock_embeddings_client
        mock_rag.doc_embeddings_client = mock_doc_embeddings_client

        async def mock_fetch(chunk_id, user):
            return CHUNK_CONTENT.get(chunk_id, f"Content for {chunk_id}")
        mock_rag.fetch_chunk = mock_fetch

        # Two concepts → two vectors
        mock_embeddings_client.embed.return_value = [[0.1, 0.2], [0.3, 0.4]]

        # Both queries return overlapping chunks
        match_a = MagicMock(chunk_id="doc/c1", score=0.9)
        match_b = MagicMock(chunk_id="doc/c2", score=0.8)
        match_c = MagicMock(chunk_id="doc/c1", score=0.85)  # duplicate
        mock_doc_embeddings_client.query.side_effect = [
            [match_a, match_b],
            [match_c],
        ]

        query = Query(
            rag=mock_rag,
            user="test_user",
            collection="test_collection",
            verbose=False,
            doc_limit=10
        )

        docs, chunk_ids = await query.get_docs(["concept A", "concept B"])

        assert len(chunk_ids) == 2  # doc/c1 only counted once
        assert "doc/c1" in chunk_ids
        assert "doc/c2" in chunk_ids
