"""
Tests for DocumentRAG retrieval implementation
"""

import pytest
from unittest.mock import MagicMock, AsyncMock

from trustgraph.retrieval.document_rag.document_rag import DocumentRag, Query


class TestDocumentRag:
    """Test cases for DocumentRag class"""

    def test_document_rag_initialization_with_defaults(self):
        """Test DocumentRag initialization with default verbose setting"""
        # Create mock clients
        mock_prompt_client = MagicMock()
        mock_embeddings_client = MagicMock()
        mock_doc_embeddings_client = MagicMock()
        
        # Initialize DocumentRag
        document_rag = DocumentRag(
            prompt_client=mock_prompt_client,
            embeddings_client=mock_embeddings_client,
            doc_embeddings_client=mock_doc_embeddings_client
        )
        
        # Verify initialization
        assert document_rag.prompt_client == mock_prompt_client
        assert document_rag.embeddings_client == mock_embeddings_client
        assert document_rag.doc_embeddings_client == mock_doc_embeddings_client
        assert document_rag.verbose is False  # Default value

    def test_document_rag_initialization_with_verbose(self):
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
            verbose=True
        )
        
        # Verify initialization
        assert document_rag.prompt_client == mock_prompt_client
        assert document_rag.embeddings_client == mock_embeddings_client
        assert document_rag.doc_embeddings_client == mock_doc_embeddings_client
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
        
        # Mock the embed method to return test vectors
        expected_vectors = [[0.1, 0.2, 0.3], [0.4, 0.5, 0.6]]
        mock_embeddings_client.embed.return_value = expected_vectors
        
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
        
        # Verify embeddings client was called correctly
        mock_embeddings_client.embed.assert_called_once_with(test_query)
        
        # Verify result matches expected vectors
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
        
        # Mock the embedding and document query responses
        test_vectors = [[0.1, 0.2, 0.3]]
        mock_embeddings_client.embed.return_value = test_vectors
        
        # Mock document results
        test_docs = ["Document 1 content", "Document 2 content"]
        mock_doc_embeddings_client.query.return_value = test_docs
        
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
        
        # Verify embeddings client was called
        mock_embeddings_client.embed.assert_called_once_with(test_query)
        
        # Verify doc embeddings client was called correctly
        mock_doc_embeddings_client.query.assert_called_once_with(
            test_vectors,
            limit=15,
            user="test_user",
            collection="test_collection"
        )
        
        # Verify result is list of documents
        assert result == test_docs

    @pytest.mark.asyncio
    async def test_document_rag_query_method(self):
        """Test DocumentRag.query method orchestrates full document RAG pipeline"""
        # Create mock clients
        mock_prompt_client = AsyncMock()
        mock_embeddings_client = AsyncMock()
        mock_doc_embeddings_client = AsyncMock()
        
        # Mock embeddings and document responses
        test_vectors = [[0.1, 0.2, 0.3]]
        test_docs = ["Relevant document content", "Another document"]
        expected_response = "This is the document RAG response"
        
        mock_embeddings_client.embed.return_value = test_vectors
        mock_doc_embeddings_client.query.return_value = test_docs
        mock_prompt_client.document_prompt.return_value = expected_response
        
        # Initialize DocumentRag
        document_rag = DocumentRag(
            prompt_client=mock_prompt_client,
            embeddings_client=mock_embeddings_client,
            doc_embeddings_client=mock_doc_embeddings_client,
            verbose=False
        )
        
        # Call DocumentRag.query
        result = await document_rag.query(
            query="test query",
            user="test_user",
            collection="test_collection",
            doc_limit=10
        )
        
        # Verify embeddings client was called
        mock_embeddings_client.embed.assert_called_once_with("test query")
        
        # Verify doc embeddings client was called
        mock_doc_embeddings_client.query.assert_called_once_with(
            test_vectors,
            limit=10,
            user="test_user",
            collection="test_collection"
        )
        
        # Verify prompt client was called with documents and query
        mock_prompt_client.document_prompt.assert_called_once_with(
            query="test query",
            documents=test_docs
        )
        
        # Verify result
        assert result == expected_response

    @pytest.mark.asyncio
    async def test_document_rag_query_with_defaults(self):
        """Test DocumentRag.query method with default parameters"""
        # Create mock clients
        mock_prompt_client = AsyncMock()
        mock_embeddings_client = AsyncMock()
        mock_doc_embeddings_client = AsyncMock()
        
        # Mock responses
        mock_embeddings_client.embed.return_value = [[0.1, 0.2]]
        mock_doc_embeddings_client.query.return_value = ["Default doc"]
        mock_prompt_client.document_prompt.return_value = "Default response"
        
        # Initialize DocumentRag
        document_rag = DocumentRag(
            prompt_client=mock_prompt_client,
            embeddings_client=mock_embeddings_client,
            doc_embeddings_client=mock_doc_embeddings_client
        )
        
        # Call DocumentRag.query with minimal parameters
        result = await document_rag.query("simple query")
        
        # Verify default parameters were used
        mock_doc_embeddings_client.query.assert_called_once_with(
            [[0.1, 0.2]],
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
        
        # Mock responses
        mock_embeddings_client.embed.return_value = [[0.7, 0.8]]
        mock_doc_embeddings_client.query.return_value = ["Verbose test doc"]
        
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
        
        # Verify calls were made
        mock_embeddings_client.embed.assert_called_once_with("verbose test")
        mock_doc_embeddings_client.query.assert_called_once()
        
        # Verify result
        assert result == ["Verbose test doc"]

    @pytest.mark.asyncio
    async def test_document_rag_query_with_verbose(self):
        """Test DocumentRag.query method with verbose logging enabled"""
        # Create mock clients
        mock_prompt_client = AsyncMock()
        mock_embeddings_client = AsyncMock()
        mock_doc_embeddings_client = AsyncMock()
        
        # Mock responses
        mock_embeddings_client.embed.return_value = [[0.3, 0.4]]
        mock_doc_embeddings_client.query.return_value = ["Verbose doc content"]
        mock_prompt_client.document_prompt.return_value = "Verbose RAG response"
        
        # Initialize DocumentRag with verbose=True
        document_rag = DocumentRag(
            prompt_client=mock_prompt_client,
            embeddings_client=mock_embeddings_client,
            doc_embeddings_client=mock_doc_embeddings_client,
            verbose=True
        )
        
        # Call DocumentRag.query
        result = await document_rag.query("verbose query test")
        
        # Verify all clients were called
        mock_embeddings_client.embed.assert_called_once_with("verbose query test")
        mock_doc_embeddings_client.query.assert_called_once()
        mock_prompt_client.document_prompt.assert_called_once_with(
            query="verbose query test",
            documents=["Verbose doc content"]
        )
        
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
        
        # Mock responses - empty document list
        mock_embeddings_client.embed.return_value = [[0.1, 0.2]]
        mock_doc_embeddings_client.query.return_value = []  # No documents found
        
        # Initialize Query
        query = Query(
            rag=mock_rag,
            user="test_user",
            collection="test_collection",
            verbose=False
        )
        
        # Call get_docs
        result = await query.get_docs("query with no results")
        
        # Verify calls were made
        mock_embeddings_client.embed.assert_called_once_with("query with no results")
        mock_doc_embeddings_client.query.assert_called_once()
        
        # Verify empty result is returned
        assert result == []

    @pytest.mark.asyncio
    async def test_document_rag_query_with_empty_documents(self):
        """Test DocumentRag.query method when no documents are retrieved"""
        # Create mock clients
        mock_prompt_client = AsyncMock()
        mock_embeddings_client = AsyncMock()
        mock_doc_embeddings_client = AsyncMock()
        
        # Mock responses - no documents found
        mock_embeddings_client.embed.return_value = [[0.5, 0.6]]
        mock_doc_embeddings_client.query.return_value = []  # Empty document list
        mock_prompt_client.document_prompt.return_value = "No documents found response"
        
        # Initialize DocumentRag
        document_rag = DocumentRag(
            prompt_client=mock_prompt_client,
            embeddings_client=mock_embeddings_client,
            doc_embeddings_client=mock_doc_embeddings_client,
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
        
        # Mock the embed method
        expected_vectors = [[0.9, 1.0, 1.1]]
        mock_embeddings_client.embed.return_value = expected_vectors
        
        # Initialize Query with verbose=True
        query = Query(
            rag=mock_rag,
            user="test_user",
            collection="test_collection",
            verbose=True
        )
        
        # Call get_vector
        result = await query.get_vector("verbose vector test")
        
        # Verify embeddings client was called
        mock_embeddings_client.embed.assert_called_once_with("verbose vector test")
        
        # Verify result
        assert result == expected_vectors

    @pytest.mark.asyncio
    async def test_document_rag_integration_flow(self):
        """Test complete DocumentRag integration with realistic data flow"""
        # Create mock clients
        mock_prompt_client = AsyncMock()
        mock_embeddings_client = AsyncMock()
        mock_doc_embeddings_client = AsyncMock()
        
        # Mock realistic responses
        query_text = "What is machine learning?"
        query_vectors = [[0.1, 0.2, 0.3, 0.4, 0.5]]
        retrieved_docs = [
            "Machine learning is a subset of artificial intelligence...",
            "ML algorithms learn patterns from data to make predictions...",
            "Common ML techniques include supervised and unsupervised learning..."
        ]
        final_response = "Machine learning is a field of AI that enables computers to learn and improve from experience without being explicitly programmed."
        
        mock_embeddings_client.embed.return_value = query_vectors
        mock_doc_embeddings_client.query.return_value = retrieved_docs
        mock_prompt_client.document_prompt.return_value = final_response
        
        # Initialize DocumentRag
        document_rag = DocumentRag(
            prompt_client=mock_prompt_client,
            embeddings_client=mock_embeddings_client,
            doc_embeddings_client=mock_doc_embeddings_client,
            verbose=False
        )
        
        # Execute full pipeline
        result = await document_rag.query(
            query=query_text,
            user="research_user", 
            collection="ml_knowledge",
            doc_limit=25
        )
        
        # Verify complete pipeline execution
        mock_embeddings_client.embed.assert_called_once_with(query_text)
        
        mock_doc_embeddings_client.query.assert_called_once_with(
            query_vectors,
            limit=25,
            user="research_user",
            collection="ml_knowledge"
        )
        
        mock_prompt_client.document_prompt.assert_called_once_with(
            query=query_text,
            documents=retrieved_docs
        )
        
        # Verify final result
        assert result == final_response