"""
Pytest configuration and fixtures for text completion tests
"""

import pytest
from unittest.mock import MagicMock, AsyncMock
from trustgraph.base import LlmResult


# === Common Fixtures for All Text Completion Models ===

@pytest.fixture
def base_processor_config():
    """Base configuration required by all processors"""
    return {
        'concurrency': 1,
        'taskgroup': AsyncMock(),
        'id': 'test-processor'
    }


@pytest.fixture
def sample_llm_result():
    """Sample LlmResult for testing"""
    return LlmResult(
        text="Test response",
        in_token=10,
        out_token=5
    )


@pytest.fixture
def mock_async_processor_init():
    """Mock AsyncProcessor.__init__ to avoid infrastructure requirements"""
    mock = MagicMock()
    mock.return_value = None
    return mock


@pytest.fixture
def mock_llm_service_init():
    """Mock LlmService.__init__ to avoid infrastructure requirements"""
    mock = MagicMock()
    mock.return_value = None
    return mock


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


# === VertexAI Specific Fixtures ===

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
def vertexai_processor_config(base_processor_config):
    """Default configuration for VertexAI processor"""
    config = base_processor_config.copy()
    config.update({
        'region': 'us-central1',
        'model': 'gemini-2.0-flash-001',
        'temperature': 0.0,
        'max_output': 8192,
        'private_key': 'private.json'
    })
    return config


@pytest.fixture
def mock_safety_settings():
    """Mock safety settings for VertexAI"""
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


# === Ollama Specific Fixtures ===

@pytest.fixture
def ollama_processor_config(base_processor_config):
    """Default configuration for Ollama processor"""
    config = base_processor_config.copy()
    config.update({
        'model': 'llama2',
        'temperature': 0.0,
        'max_output': 8192,
        'host': 'localhost',
        'port': 11434
    })
    return config


@pytest.fixture
def mock_ollama_client():
    """Mock Ollama client"""
    mock_client = MagicMock()
    mock_response = {
        'response': 'Test response from Ollama',
        'done': True,
        'eval_count': 5,
        'prompt_eval_count': 10
    }
    mock_client.generate.return_value = mock_response
    return mock_client


# === OpenAI Specific Fixtures ===

@pytest.fixture
def openai_processor_config(base_processor_config):
    """Default configuration for OpenAI processor"""
    config = base_processor_config.copy()
    config.update({
        'model': 'gpt-3.5-turbo',
        'api_key': 'test-api-key',
        'url': 'https://api.openai.com/v1',
        'temperature': 0.0,
        'max_output': 4096
    })
    return config


@pytest.fixture
def mock_openai_client():
    """Mock OpenAI client"""
    mock_client = MagicMock()
    
    # Mock the response structure
    mock_response = MagicMock()
    mock_response.choices = [MagicMock()]
    mock_response.choices[0].message.content = "Test response from OpenAI"
    mock_response.usage.prompt_tokens = 15
    mock_response.usage.completion_tokens = 8
    
    mock_client.chat.completions.create.return_value = mock_response
    return mock_client


@pytest.fixture
def mock_openai_rate_limit_error():
    """Mock OpenAI rate limit error"""
    from openai import RateLimitError
    return RateLimitError("Rate limit exceeded", response=MagicMock(), body=None)


# === Azure OpenAI Specific Fixtures ===

@pytest.fixture
def azure_openai_processor_config(base_processor_config):
    """Default configuration for Azure OpenAI processor"""
    config = base_processor_config.copy()
    config.update({
        'model': 'gpt-4',
        'endpoint': 'https://test.openai.azure.com/',
        'token': 'test-token',
        'api_version': '2024-12-01-preview',
        'temperature': 0.0,
        'max_output': 4192
    })
    return config


@pytest.fixture
def mock_azure_openai_client():
    """Mock Azure OpenAI client"""
    mock_client = MagicMock()
    
    # Mock the response structure
    mock_response = MagicMock()
    mock_response.choices = [MagicMock()]
    mock_response.choices[0].message.content = "Test response from Azure OpenAI"
    mock_response.usage.prompt_tokens = 20
    mock_response.usage.completion_tokens = 10
    
    mock_client.chat.completions.create.return_value = mock_response
    return mock_client


@pytest.fixture
def mock_azure_openai_rate_limit_error():
    """Mock Azure OpenAI rate limit error"""
    from openai import RateLimitError
    return RateLimitError("Rate limit exceeded", response=MagicMock(), body=None)


# === Azure Specific Fixtures ===

@pytest.fixture
def azure_processor_config(base_processor_config):
    """Default configuration for Azure processor"""
    config = base_processor_config.copy()
    config.update({
        'endpoint': 'https://test.inference.ai.azure.com/v1/chat/completions',
        'token': 'test-token',
        'temperature': 0.0,
        'max_output': 4192
    })
    return config


@pytest.fixture
def mock_azure_requests():
    """Mock requests for Azure processor"""
    mock_requests = MagicMock()
    
    # Mock successful response
    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.json.return_value = {
        'choices': [{
            'message': {
                'content': 'Test response from Azure'
            }
        }],
        'usage': {
            'prompt_tokens': 18,
            'completion_tokens': 9
        }
    }
    mock_requests.post.return_value = mock_response
    return mock_requests


@pytest.fixture
def mock_azure_rate_limit_response():
    """Mock Azure rate limit response"""
    mock_response = MagicMock()
    mock_response.status_code = 429
    return mock_response