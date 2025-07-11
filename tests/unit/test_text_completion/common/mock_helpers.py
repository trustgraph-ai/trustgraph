"""
Common mocking utilities for text completion tests
"""

from unittest.mock import AsyncMock, MagicMock


class CommonMocks:
    """Common mock objects used across text completion tests"""
    
    @staticmethod
    def create_mock_async_processor_init():
        """Create mock for AsyncProcessor.__init__"""
        mock = MagicMock()
        mock.return_value = None
        return mock
    
    @staticmethod
    def create_mock_llm_service_init():
        """Create mock for LlmService.__init__"""
        mock = MagicMock()
        mock.return_value = None
        return mock
    
    @staticmethod
    def create_mock_response(text="Test response", prompt_tokens=10, completion_tokens=5):
        """Create a mock response object"""
        response = MagicMock()
        response.text = text
        response.usage_metadata.prompt_token_count = prompt_tokens
        response.usage_metadata.candidates_token_count = completion_tokens
        return response
    
    @staticmethod
    def create_basic_config():
        """Create basic config with required fields"""
        return {
            'concurrency': 1,
            'taskgroup': AsyncMock(),
            'id': 'test-processor'
        }


class MockPatches:
    """Common patch decorators for different services"""
    
    @staticmethod
    def get_base_patches():
        """Get patches that are common to all processors"""
        return [
            'trustgraph.base.async_processor.AsyncProcessor.__init__',
            'trustgraph.base.llm_service.LlmService.__init__'
        ]