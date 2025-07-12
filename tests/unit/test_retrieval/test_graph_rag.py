"""
Tests for GraphRAG retrieval implementation
"""

import pytest
from unittest.mock import MagicMock

from trustgraph.retrieval.graph_rag.graph_rag import GraphRag


class TestGraphRag:
    """Test cases for GraphRag class"""

    def test_graph_rag_initialization_with_defaults(self):
        """Test GraphRag initialization with default verbose setting"""
        # Create mock clients
        mock_prompt_client = MagicMock()
        mock_embeddings_client = MagicMock()
        mock_graph_embeddings_client = MagicMock()
        mock_triples_client = MagicMock()
        
        # Initialize GraphRag
        graph_rag = GraphRag(
            prompt_client=mock_prompt_client,
            embeddings_client=mock_embeddings_client,
            graph_embeddings_client=mock_graph_embeddings_client,
            triples_client=mock_triples_client
        )
        
        # Verify initialization
        assert graph_rag.prompt_client == mock_prompt_client
        assert graph_rag.embeddings_client == mock_embeddings_client
        assert graph_rag.graph_embeddings_client == mock_graph_embeddings_client
        assert graph_rag.triples_client == mock_triples_client
        assert graph_rag.verbose is False  # Default value
        assert graph_rag.label_cache == {}  # Empty cache initially

    def test_graph_rag_initialization_with_verbose(self):
        """Test GraphRag initialization with verbose enabled"""
        # Create mock clients
        mock_prompt_client = MagicMock()
        mock_embeddings_client = MagicMock()
        mock_graph_embeddings_client = MagicMock()
        mock_triples_client = MagicMock()
        
        # Initialize GraphRag with verbose=True
        graph_rag = GraphRag(
            prompt_client=mock_prompt_client,
            embeddings_client=mock_embeddings_client,
            graph_embeddings_client=mock_graph_embeddings_client,
            triples_client=mock_triples_client,
            verbose=True
        )
        
        # Verify initialization
        assert graph_rag.prompt_client == mock_prompt_client
        assert graph_rag.embeddings_client == mock_embeddings_client
        assert graph_rag.graph_embeddings_client == mock_graph_embeddings_client
        assert graph_rag.triples_client == mock_triples_client
        assert graph_rag.verbose is True
        assert graph_rag.label_cache == {}  # Empty cache initially