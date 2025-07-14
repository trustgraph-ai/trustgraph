# Unit Testing Strategy for TrustGraph Microservices

## Overview

This document outlines the unit testing strategy for the TrustGraph microservices architecture. The approach focuses on testing business logic while mocking external infrastructure to ensure fast, reliable, and maintainable tests.

## 1. Test Framework: pytest + pytest-asyncio

- **pytest**: Standard Python testing framework with excellent fixture support
- **pytest-asyncio**: Essential for testing async processors
- **pytest-mock**: Built-in mocking capabilities

## 2. Core Testing Patterns

### Service Layer Testing

```python
@pytest.mark.asyncio
async def test_text_completion_service():
    # Test the core business logic, not external APIs
    processor = TextCompletionProcessor(model="test-model")
    
    # Mock external dependencies
    with patch('processor.llm_client') as mock_client:
        mock_client.generate.return_value = "test response"
        
        result = await processor.process_message(test_message)
        assert result.content == "test response"
```

### Message Processing Testing

```python
@pytest.fixture
def mock_pulsar_consumer():
    return AsyncMock(spec=pulsar.Consumer)

@pytest.fixture  
def mock_pulsar_producer():
    return AsyncMock(spec=pulsar.Producer)

async def test_message_flow(mock_consumer, mock_producer):
    # Test message handling without actual Pulsar
    processor = FlowProcessor(consumer=mock_consumer, producer=mock_producer)
    # Test message processing logic
```

## 3. Mock Strategy

### Mock External Services (Not Infrastructure)

- ✅ **Mock**: LLM APIs, Vector DBs, Graph DBs
- ❌ **Don't Mock**: Core business logic, data transformations
- ✅ **Mock**: Pulsar clients (infrastructure)
- ❌ **Don't Mock**: Message validation, processing logic

### Dependency Injection Pattern

```python
class TextCompletionProcessor:
    def __init__(self, llm_client=None, **kwargs):
        self.llm_client = llm_client or create_default_client()
        
# In tests
processor = TextCompletionProcessor(llm_client=mock_client)
```

## 4. Test Categories

### Unit Tests (70%)
- Individual service business logic
- Message processing functions
- Data transformation logic
- Configuration parsing
- Error handling

### Integration Tests (20%)
- Service-to-service communication patterns
- Database operations with test containers
- End-to-end message flows

### Contract Tests (10%)
- Pulsar message schemas
- API response formats
- Service interface contracts

## 5. Test Structure

```
tests/
├── unit/
│   ├── test_text_completion/
│   ├── test_embeddings/
│   ├── test_storage/
│   └── test_utils/
├── integration/
│   ├── test_flows/
│   └── test_databases/
├── fixtures/
│   ├── messages.py
│   ├── configs.py
│   └── mocks.py
└── conftest.py
```

## 6. Key Testing Tools

- **testcontainers**: For database integration tests
- **responses**: Mock HTTP APIs
- **freezegun**: Time-based testing
- **factory-boy**: Test data generation

## 7. Service-Specific Testing Approaches

### Text Completion Services
- Mock LLM provider APIs (OpenAI, Claude, Ollama)
- Test prompt construction and response parsing
- Verify rate limiting and error handling
- Test token counting and metrics collection

### Embeddings Services
- Mock embedding providers (FastEmbed, Ollama)
- Test vector dimension consistency
- Verify batch processing logic
- Test embedding storage operations

### Storage Services
- Use testcontainers for database integration tests
- Mock database clients for unit tests
- Test query construction and result parsing
- Verify data persistence and retrieval logic

### Query Services
- Mock vector similarity search operations
- Test graph traversal logic
- Verify result ranking and filtering
- Test query optimization

## 8. Best Practices

### Test Isolation
- Each test should be independent
- Use fixtures for common setup
- Clean up resources after tests
- Avoid test order dependencies

### Async Testing
- Use `@pytest.mark.asyncio` for async tests
- Mock async dependencies properly
- Test concurrent operations
- Handle timeout scenarios

### Error Handling
- Test both success and failure scenarios
- Verify proper exception handling
- Test retry mechanisms
- Validate error response formats

### Configuration Testing
- Test different configuration scenarios
- Verify parameter validation
- Test environment variable handling
- Test configuration defaults

## 9. Example Test Implementation

```python
# tests/unit/test_text_completion/test_openai_processor.py
import pytest
from unittest.mock import AsyncMock, patch
from trustgraph.model.text_completion.openai import Processor

@pytest.fixture
def mock_openai_client():
    return AsyncMock()

@pytest.fixture
def processor(mock_openai_client):
    return Processor(client=mock_openai_client, model="gpt-4")

@pytest.mark.asyncio
async def test_process_message_success(processor, mock_openai_client):
    # Arrange
    mock_openai_client.chat.completions.create.return_value = AsyncMock(
        choices=[AsyncMock(message=AsyncMock(content="Test response"))]
    )
    
    message = {
        "id": "test-id",
        "prompt": "Test prompt",
        "temperature": 0.7
    }
    
    # Act
    result = await processor.process_message(message)
    
    # Assert
    assert result.content == "Test response"
    mock_openai_client.chat.completions.create.assert_called_once()

@pytest.mark.asyncio
async def test_process_message_rate_limit(processor, mock_openai_client):
    # Arrange
    mock_openai_client.chat.completions.create.side_effect = RateLimitError("Rate limited")
    
    message = {"id": "test-id", "prompt": "Test prompt"}
    
    # Act & Assert
    with pytest.raises(RateLimitError):
        await processor.process_message(message)
```

## 10. Running Tests

```bash
# Run all tests
pytest

# Run unit tests only
pytest tests/unit/

# Run with coverage
pytest --cov=trustgraph --cov-report=html

# Run async tests
pytest -v tests/unit/test_text_completion/

# Run specific test file
pytest tests/unit/test_text_completion/test_openai_processor.py
```

## 11. Continuous Integration

- Run tests on every commit
- Enforce minimum code coverage (80%+)
- Run tests against multiple Python versions
- Include integration tests in CI pipeline
- Generate test reports and coverage metrics

## Conclusion

This testing strategy ensures that TrustGraph microservices are thoroughly tested without relying on external infrastructure. By focusing on business logic and mocking external dependencies, we achieve fast, reliable tests that provide confidence in code quality while maintaining development velocity.

