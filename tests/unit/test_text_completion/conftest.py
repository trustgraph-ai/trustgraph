"""
Pytest configuration and fixtures for text completion tests
"""

import pytest
from unittest.mock import MagicMock, AsyncMock
from trustgraph.base.types import TextCompletionRequest, TextCompletionResponse, LlmResult


@pytest.fixture
def mock_vertexai_credentials():
    """Mock Google Cloud service account credentials"""
    return MagicMock()


@pytest.fixture
def mock_vertexai_model():
    """Mock VertexAI GenerativeModel"""
    mock_model = MagicMock()
    mock_response = MagicMock()
    mock_response.text = "Test response"
    mock_response.usage_metadata.prompt_token_count = 10
    mock_response.usage_metadata.candidates_token_count = 5
    mock_model.generate_content.return_value = mock_response
    return mock_model


@pytest.fixture
def sample_text_completion_request():
    """Sample TextCompletionRequest for testing"""
    return TextCompletionRequest(
        id="test-request-id",
        prompt="Test prompt",
        system="Test system prompt",
        temperature=0.7,
        max_output=1024
    )


@pytest.fixture
def sample_text_completion_response():
    """Sample TextCompletionResponse for testing"""
    return TextCompletionResponse(
        id="test-response-id",
        response="Test response",
        in_token=10,
        out_token=5,
        model="gemini-2.0-flash-001"
    )


@pytest.fixture
def sample_llm_result():
    """Sample LlmResult for testing"""
    return LlmResult(
        text="Test response",
        in_token=10,
        out_token=5
    )


@pytest.fixture
def vertexai_processor_config():
    """Default configuration for VertexAI processor"""
    return {
        'region': 'us-central1',
        'model': 'gemini-2.0-flash-001',
        'temperature': 0.0,
        'max_output': 8192,
        'private_key': 'private.json',
        'concurrency': 1
    }


@pytest.fixture
def mock_prometheus_metrics():
    """Mock Prometheus metrics"""
    mock_metric = MagicMock()
    mock_metric.labels.return_value.time.return_value = MagicMock()
    return mock_metric


@pytest.fixture
def mock_pulsar_consumer():
    """Mock Pulsar consumer for integration testing"""
    return AsyncMock()


@pytest.fixture
def mock_pulsar_producer():
    """Mock Pulsar producer for integration testing"""
    return AsyncMock()


@pytest.fixture
def mock_flow_processor_config():
    """Mock flow processor configuration"""
    return {
        'service_id': 'test-vertexai-service',
        'flow_name': 'test-flow',
        'consumer_name': 'test-consumer'
    }


@pytest.fixture
def mock_safety_settings():
    """Mock safety settings for VertexAI"""
    from unittest.mock import MagicMock
    
    safety_settings = []
    for i in range(4):  # 4 safety categories
        setting = MagicMock()
        setting.category = f"HARM_CATEGORY_{i}"
        setting.threshold = "BLOCK_MEDIUM_AND_ABOVE"
        safety_settings.append(setting)
    
    return safety_settings


@pytest.fixture
def mock_generation_config():
    """Mock generation configuration for VertexAI"""
    config = MagicMock()
    config.temperature = 0.0
    config.max_output_tokens = 8192
    config.top_p = 1.0
    config.top_k = 10
    config.candidate_count = 1
    return config


@pytest.fixture
def mock_vertexai_exception():
    """Mock VertexAI exceptions"""
    from google.api_core.exceptions import ResourceExhausted
    return ResourceExhausted("Test resource exhausted error")


@pytest.fixture(autouse=True)
def mock_env_vars(monkeypatch):
    """Mock environment variables for testing"""
    monkeypatch.setenv("GOOGLE_CLOUD_PROJECT", "test-project")
    monkeypatch.setenv("GOOGLE_APPLICATION_CREDENTIALS", "/path/to/test-credentials.json")


@pytest.fixture
def mock_async_context_manager():
    """Mock async context manager for testing"""
    class MockAsyncContextManager:
        def __init__(self, return_value):
            self.return_value = return_value
        
        async def __aenter__(self):
            return self.return_value
        
        async def __aexit__(self, exc_type, exc_val, exc_tb):
            pass
    
    return MockAsyncContextManager