"""
Base test patterns that can be reused across different text completion models
"""

from abc import ABC, abstractmethod
from unittest.mock import AsyncMock, MagicMock, patch
from unittest import IsolatedAsyncioTestCase


class BaseTextCompletionTestCase(IsolatedAsyncioTestCase, ABC):
    """
    Base test class for text completion processors
    Provides common test patterns that can be reused
    """
    
    @abstractmethod
    def get_processor_class(self):
        """Return the processor class to test"""
        pass
    
    @abstractmethod
    def get_base_config(self):
        """Return base configuration for the processor"""
        pass
    
    @abstractmethod
    def get_mock_patches(self):
        """Return list of patch decorators for mocking dependencies"""
        pass
    
    def create_base_config(self, **overrides):
        """Create base config with optional overrides"""
        config = self.get_base_config()
        config.update(overrides)
        return config
    
    def create_mock_llm_result(self, text="Test response", in_token=10, out_token=5):
        """Create a mock LLM result"""
        from trustgraph.base import LlmResult
        return LlmResult(text=text, in_token=in_token, out_token=out_token)


class CommonTestPatterns:
    """
    Common test patterns that can be used across different models
    """
    
    @staticmethod
    def basic_initialization_test_pattern(test_instance):
        """
        Test pattern for basic processor initialization
        test_instance should be a BaseTextCompletionTestCase
        """
        # This would contain the common pattern for initialization testing
        pass
    
    @staticmethod
    def successful_generation_test_pattern(test_instance):
        """
        Test pattern for successful content generation
        """
        pass
    
    @staticmethod
    def error_handling_test_pattern(test_instance):
        """
        Test pattern for error handling
        """
        pass