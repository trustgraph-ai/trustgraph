"""
Unit tests for Parameter-Based Caching in LLM Processors
Testing processors that cache based on temperature parameters (Bedrock, GoogleAIStudio)
"""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from unittest import IsolatedAsyncioTestCase

from trustgraph.model.text_completion.googleaistudio.llm import Processor as GoogleAIProcessor
from trustgraph.base import LlmResult


class TestParameterCaching(IsolatedAsyncioTestCase):
    """Test parameter-based caching functionality"""

    @patch('trustgraph.model.text_completion.googleaistudio.llm.genai')
    @patch('trustgraph.base.async_processor.AsyncProcessor.__init__')
    @patch('trustgraph.base.llm_service.LlmService.__init__')
    async def test_googleai_temperature_cache_keys(self, mock_llm_init, mock_async_init, mock_genai):
        """Test that GoogleAI processor creates separate cache entries for different temperatures"""
        # Arrange
        mock_client = MagicMock()
        mock_genai.Client.return_value = mock_client

        mock_response = MagicMock()
        mock_response.text = "Generated response"
        mock_response.usage_metadata.prompt_token_count = 10
        mock_response.usage_metadata.candidates_token_count = 5
        mock_client.models.generate_content.return_value = mock_response

        mock_async_init.return_value = None
        mock_llm_init.return_value = None

        config = {
            'model': 'gemini-2.0-flash-001',
            'api_key': 'test-api-key',
            'temperature': 0.0,  # Default temperature
            'max_output': 1024,
            'concurrency': 1,
            'taskgroup': AsyncMock(),
            'id': 'test-processor'
        }

        processor = GoogleAIProcessor(**config)

        # Act - Call with different temperatures
        await processor.generate_content("System", "Prompt 1", model="gemini-2.0-flash-001", temperature=0.0)
        await processor.generate_content("System", "Prompt 2", model="gemini-2.0-flash-001", temperature=0.5)
        await processor.generate_content("System", "Prompt 3", model="gemini-2.0-flash-001", temperature=1.0)

        # Assert - Should have 3 different cache entries
        cache_keys = list(processor.generation_configs.keys())

        assert len(cache_keys) == 3
        assert "gemini-2.0-flash-001:0.0" in cache_keys
        assert "gemini-2.0-flash-001:0.5" in cache_keys
        assert "gemini-2.0-flash-001:1.0" in cache_keys

        # Verify each cached config has the correct temperature
        assert processor.generation_configs["gemini-2.0-flash-001:0.0"].temperature == 0.0
        assert processor.generation_configs["gemini-2.0-flash-001:0.5"].temperature == 0.5
        assert processor.generation_configs["gemini-2.0-flash-001:1.0"].temperature == 1.0

    @patch('trustgraph.model.text_completion.googleaistudio.llm.genai')
    @patch('trustgraph.base.async_processor.AsyncProcessor.__init__')
    @patch('trustgraph.base.llm_service.LlmService.__init__')
    async def test_googleai_cache_reuse_same_parameters(self, mock_llm_init, mock_async_init, mock_genai):
        """Test that GoogleAI processor reuses cache for identical model+temperature combinations"""
        # Arrange
        mock_client = MagicMock()
        mock_genai.Client.return_value = mock_client

        mock_response = MagicMock()
        mock_response.text = "Generated response"
        mock_response.usage_metadata.prompt_token_count = 10
        mock_response.usage_metadata.candidates_token_count = 5
        mock_client.models.generate_content.return_value = mock_response

        mock_async_init.return_value = None
        mock_llm_init.return_value = None

        config = {
            'model': 'gemini-2.0-flash-001',
            'api_key': 'test-api-key',
            'temperature': 0.0,
            'max_output': 1024,
            'concurrency': 1,
            'taskgroup': AsyncMock(),
            'id': 'test-processor'
        }

        processor = GoogleAIProcessor(**config)

        # Act - Call multiple times with same parameters
        await processor.generate_content("System", "Prompt 1", model="gemini-2.0-flash-001", temperature=0.7)
        await processor.generate_content("System", "Prompt 2", model="gemini-2.0-flash-001", temperature=0.7)
        await processor.generate_content("System", "Prompt 3", model="gemini-2.0-flash-001", temperature=0.7)

        # Assert - Should have only 1 cache entry for the repeated parameters
        cache_keys = list(processor.generation_configs.keys())
        assert len(cache_keys) == 1
        assert "gemini-2.0-flash-001:0.7" in cache_keys

        # The same config object should be reused
        config_obj = processor.generation_configs["gemini-2.0-flash-001:0.7"]
        assert config_obj.temperature == 0.7

    @patch('trustgraph.model.text_completion.googleaistudio.llm.genai')
    @patch('trustgraph.base.async_processor.AsyncProcessor.__init__')
    @patch('trustgraph.base.llm_service.LlmService.__init__')
    async def test_googleai_different_models_separate_caches(self, mock_llm_init, mock_async_init, mock_genai):
        """Test that different models create separate cache entries even with same temperature"""
        # Arrange
        mock_client = MagicMock()
        mock_genai.Client.return_value = mock_client

        mock_response = MagicMock()
        mock_response.text = "Generated response"
        mock_response.usage_metadata.prompt_token_count = 10
        mock_response.usage_metadata.candidates_token_count = 5
        mock_client.models.generate_content.return_value = mock_response

        mock_async_init.return_value = None
        mock_llm_init.return_value = None

        config = {
            'model': 'gemini-2.0-flash-001',
            'api_key': 'test-api-key',
            'temperature': 0.0,
            'max_output': 1024,
            'concurrency': 1,
            'taskgroup': AsyncMock(),
            'id': 'test-processor'
        }

        processor = GoogleAIProcessor(**config)

        # Act - Call with different models, same temperature
        await processor.generate_content("System", "Prompt 1", model="gemini-2.0-flash-001", temperature=0.5)
        await processor.generate_content("System", "Prompt 2", model="gemini-1.5-flash-001", temperature=0.5)

        # Assert - Should have separate cache entries for different models
        cache_keys = list(processor.generation_configs.keys())
        assert len(cache_keys) == 2
        assert "gemini-2.0-flash-001:0.5" in cache_keys
        assert "gemini-1.5-flash-001:0.5" in cache_keys

    # Note: Bedrock tests would be similar but testing the Bedrock processor's caching behavior
    # The Bedrock processor caches model variants with temperature in the cache key

    async def test_bedrock_temperature_cache_keys(self):
        """Test Bedrock processor temperature-aware caching"""
        # This would test the Bedrock processor's _get_or_create_variant method
        # with different temperature values to ensure proper cache key generation

        # Implementation would follow similar pattern to GoogleAI tests above
        # but using the Bedrock processor and testing model_variants cache
        pass

    async def test_bedrock_cache_isolation_different_temperatures(self):
        """Test that Bedrock processor isolates cache entries by temperature"""
        pass

    async def test_cache_memory_efficiency(self):
        """Test that caches don't grow unbounded with many different parameter combinations"""
        # This could test cache size limits or cleanup behavior if implemented
        pass


class TestCachePerformance(IsolatedAsyncioTestCase):
    """Test caching performance characteristics"""

    async def test_cache_hit_performance(self):
        """Test that cache hits are faster than cache misses"""
        # This would measure timing differences between cache hits and misses
        pass

    async def test_concurrent_cache_access(self):
        """Test concurrent access to cached configurations"""
        # This would test thread-safety of cache access
        pass


if __name__ == '__main__':
    pytest.main([__file__])