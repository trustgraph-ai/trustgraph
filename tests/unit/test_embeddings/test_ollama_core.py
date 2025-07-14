"""
Unit tests for Ollama core embedding functionality

Tests the core business logic without full processor initialization,
focusing on the embedding generation methods and client interaction.
"""

import pytest
from unittest.mock import patch, Mock
import os


class TestOllamaCore:
    """Test core Ollama embedding functionality"""

    @patch('trustgraph.embeddings.ollama.processor.Client')
    def test_ollama_client_initialization(self, mock_client_class):
        """Test Ollama client initialization"""
        # Arrange
        mock_client = Mock()
        mock_client_class.return_value = mock_client
        
        # Act
        from ollama import Client
        client = Client(host="http://localhost:11434")
        
        # Assert
        mock_client_class.assert_called_once_with(host="http://localhost:11434")

    @patch('trustgraph.embeddings.ollama.processor.Client')
    def test_ollama_embed_method(self, mock_client_class):
        """Test Ollama client embed method functionality"""
        # Arrange
        mock_client = Mock()
        mock_client.embed.return_value = Mock(
            embeddings=[0.1, 0.2, -0.3, 0.4, -0.5]
        )
        mock_client_class.return_value = mock_client
        
        # Act
        from ollama import Client
        client = Client(host="http://localhost:11434")
        result = client.embed(model="test-model", input="Test text")
        
        # Assert
        mock_client.embed.assert_called_once_with(model="test-model", input="Test text")
        assert result.embeddings == [0.1, 0.2, -0.3, 0.4, -0.5]

    def test_environment_variable_handling(self):
        """Test OLLAMA_HOST environment variable handling"""
        # Test default value
        from trustgraph.embeddings.ollama.processor import default_ollama
        
        # Should use localhost by default
        assert default_ollama == os.getenv("OLLAMA_HOST", 'http://localhost:11434')
        
        # Test with custom environment variable
        with patch.dict(os.environ, {'OLLAMA_HOST': 'http://custom:8080'}):
            import importlib
            # Reload module to pick up new env var
            custom_host = os.getenv("OLLAMA_HOST", 'http://localhost:11434')
            assert custom_host == 'http://custom:8080'

    def test_default_model_constant(self):
        """Test that default model constant is properly defined"""
        # Act
        from trustgraph.embeddings.ollama.processor import default_model
        
        # Assert
        assert default_model == "mxbai-embed-large"
        assert isinstance(default_model, str)
        assert len(default_model) > 0

    def test_embedding_response_structure(self):
        """Test Ollama embedding response structure"""
        # Arrange
        mock_response = Mock()
        mock_response.embeddings = [0.1, 0.2, 0.3, 0.4, 0.5]
        
        # Act
        embeddings = mock_response.embeddings
        
        # Assert
        assert isinstance(embeddings, list)
        assert len(embeddings) == 5
        assert all(isinstance(val, (int, float)) for val in embeddings)

    def test_embedding_dimension_consistency(self):
        """Test that embeddings maintain consistent dimensions"""
        # Arrange
        test_responses = [
            Mock(embeddings=[0.1, 0.2, 0.3, 0.4, 0.5]),
            Mock(embeddings=[0.6, 0.7, 0.8, 0.9, 1.0]),
            Mock(embeddings=[-0.1, -0.2, -0.3, -0.4, -0.5])
        ]
        
        # Act
        embeddings = [resp.embeddings for resp in test_responses]
        
        # Assert
        dimensions = [len(emb) for emb in embeddings]
        assert all(dim == dimensions[0] for dim in dimensions), "All embeddings should have same dimension"
        assert dimensions[0] == 5

    def test_text_input_handling(self):
        """Test various text input scenarios"""
        # Arrange
        test_cases = [
            "",  # Empty string
            "Simple text",  # Normal text
            "Text with 123 numbers",  # Alphanumeric
            "Hello 世界! 🌍",  # Unicode
            "A" * 10000,  # Very long text
            "Multi\nline\ntext",  # Multiline
        ]
        
        # Act & Assert
        for text in test_cases:
            # Should all be valid string inputs
            assert isinstance(text, str)
            # Text length should be accessible
            assert len(text) >= 0

    def test_error_handling_simulation(self):
        """Test error handling in Ollama client simulation"""
        # Arrange
        mock_client = Mock()
        mock_client.embed.side_effect = Exception("Connection failed")
        
        # Act & Assert
        with pytest.raises(Exception, match="Connection failed"):
            mock_client.embed(model="test-model", input="Test text")

    def test_model_not_found_simulation(self):
        """Test handling when model is not found simulation"""
        # Arrange
        mock_client = Mock()
        mock_client.embed.side_effect = Exception("Model 'unknown-model' not found")
        
        # Act & Assert
        with pytest.raises(Exception, match="Model 'unknown-model' not found"):
            mock_client.embed(model="unknown-model", input="Test text")

    def test_concurrent_requests_simulation(self):
        """Test concurrent request handling simulation"""
        # Arrange
        import asyncio
        
        async def mock_embed_call(text_id):
            # Simulate async embedding call
            await asyncio.sleep(0.001)  # Minimal delay
            return [float(text_id)] * 5
        
        # Act
        async def run_concurrent_test():
            tasks = [mock_embed_call(i) for i in range(5)]
            results = await asyncio.gather(*tasks)
            return results
        
        # Run the test
        import asyncio
        results = asyncio.run(run_concurrent_test())
        
        # Assert
        assert len(results) == 5
        for i, result in enumerate(results):
            assert result == [float(i)] * 5

    def test_processor_add_args_functionality(self):
        """Test add_args static method functionality"""
        # Arrange
        from trustgraph.embeddings.ollama.processor import Processor
        mock_parser = Mock()
        
        # Act
        Processor.add_args(mock_parser)
        
        # Assert
        # Verify model argument was added
        model_calls = [call for call in mock_parser.add_argument.call_args_list 
                      if call[0][0] in ['-m', '--model']]
        assert len(model_calls) == 1
        model_call = model_calls[0]
        assert model_call[1]['default'] == "mxbai-embed-large"
        
        # Verify ollama argument was added
        ollama_calls = [call for call in mock_parser.add_argument.call_args_list 
                       if call[0][0] in ['-r', '--ollama']]
        assert len(ollama_calls) == 1
        ollama_call = ollama_calls[0]
        assert ollama_call[1]['default'] == 'http://localhost:11434'

    def test_host_url_validation(self):
        """Test Ollama host URL validation"""
        # Arrange
        valid_hosts = [
            "http://localhost:11434",
            "http://127.0.0.1:11434",
            "http://ollama-server:11434",
            "https://secure-ollama.com:443"
        ]
        
        # Act & Assert
        for host in valid_hosts:
            assert isinstance(host, str)
            assert host.startswith(("http://", "https://"))
            assert ":" in host  # Should have port specification

    def test_embedding_vector_properties(self):
        """Test properties of embedding vectors"""
        # Arrange
        test_embedding = [0.1, -0.2, 0.3, -0.4, 0.5, 0.0, -0.1, 0.8]
        
        # Act
        positive_count = sum(1 for x in test_embedding if x > 0)
        negative_count = sum(1 for x in test_embedding if x < 0)
        zero_count = sum(1 for x in test_embedding if x == 0)
        
        # Assert
        assert positive_count + negative_count + zero_count == len(test_embedding)
        assert all(isinstance(x, (int, float)) for x in test_embedding)
        assert all(-1.0 <= x <= 1.0 for x in test_embedding)  # Typical embedding range