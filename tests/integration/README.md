# Integration Test Pattern for TrustGraph

This directory contains integration tests that verify the coordination between multiple TrustGraph services and components, following the patterns outlined in [TEST_STRATEGY.md](../../TEST_STRATEGY.md).

## Integration Test Approach

Integration tests focus on **service-to-service communication patterns** and **end-to-end message flows** while still using mocks for external infrastructure.

### Key Principles

1. **Test Service Coordination**: Verify that services work together correctly
2. **Mock External Dependencies**: Use mocks for databases, APIs, and infrastructure
3. **Real Business Logic**: Exercise actual service logic and data transformations
4. **Error Propagation**: Test how errors flow through the system
5. **Configuration Testing**: Verify services respond correctly to different configurations

## Test Structure

### Fixtures (conftest.py)

Common fixtures for integration tests:
- `mock_pulsar_client`: Mock Pulsar messaging client
- `mock_flow_context`: Mock flow context for service coordination
- `integration_config`: Standard configuration for integration tests
- `sample_documents`: Test document collections
- `sample_embeddings`: Test embedding vectors
- `sample_queries`: Test query sets

### Test Patterns

#### 1. End-to-End Flow Testing

```python
@pytest.mark.integration
@pytest.mark.asyncio
async def test_service_end_to_end_flow(self, service_instance, mock_clients):
    """Test complete service pipeline from input to output"""
    # Arrange - Set up realistic test data
    # Act - Execute the full service workflow
    # Assert - Verify coordination between all components
```

#### 2. Error Propagation Testing

```python
@pytest.mark.integration
@pytest.mark.asyncio
async def test_service_error_handling(self, service_instance, mock_clients):
    """Test how errors propagate through service coordination"""
    # Arrange - Set up failure scenarios
    # Act - Execute service with failing dependency
    # Assert - Verify proper error handling and cleanup
```

#### 3. Configuration Testing

```python
@pytest.mark.integration
@pytest.mark.asyncio
async def test_service_configuration_scenarios(self, service_instance):
    """Test service behavior with different configurations"""
    # Test multiple configuration scenarios
    # Verify service adapts correctly to each configuration
```

## Running Integration Tests

### Run All Integration Tests
```bash
pytest tests/integration/ -m integration
```

### Run Specific Test
```bash
pytest tests/integration/test_document_rag_integration.py::TestDocumentRagIntegration::test_document_rag_end_to_end_flow -v
```

### Run with Coverage (Skip Coverage Requirement)
```bash
pytest tests/integration/ -m integration --cov=trustgraph --cov-fail-under=0
```

### Run Slow Tests
```bash
pytest tests/integration/ -m "integration and slow"
```

### Skip Slow Tests
```bash
pytest tests/integration/ -m "integration and not slow"
```

## Examples: Integration Test Implementations

### 1. Document RAG Integration Test

The `test_document_rag_integration.py` demonstrates the integration test pattern:

### What It Tests
- **Service Coordination**: Embeddings → Document Retrieval → Prompt Generation
- **Error Handling**: Failure scenarios for each service dependency
- **Configuration**: Different document limits, users, and collections
- **Performance**: Large document set handling

### Key Features
- **Realistic Data Flow**: Uses actual service logic with mocked dependencies
- **Multiple Scenarios**: Success, failure, and edge cases
- **Verbose Logging**: Tests logging functionality
- **Multi-User Support**: Tests user and collection isolation

### Test Coverage
- ✅ End-to-end happy path
- ✅ No documents found scenario
- ✅ Service failure scenarios (embeddings, documents, prompt)
- ✅ Configuration variations
- ✅ Multi-user isolation
- ✅ Performance testing
- ✅ Verbose logging

### 2. Text Completion Integration Test

The `test_text_completion_integration.py` demonstrates external API integration testing:

### What It Tests
- **External API Integration**: OpenAI API connectivity and authentication
- **Rate Limiting**: Proper handling of API rate limits and retries
- **Error Handling**: API failures, connection timeouts, and error propagation
- **Token Tracking**: Accurate input/output token counting and metrics
- **Configuration**: Different model parameters and settings
- **Concurrency**: Multiple simultaneous API requests

### Key Features
- **Realistic Mock Responses**: Uses actual OpenAI API response structures
- **Authentication Testing**: API key validation and base URL configuration
- **Error Scenarios**: Rate limits, connection failures, invalid requests
- **Performance Metrics**: Timing and token usage validation
- **Model Flexibility**: Tests different GPT models and parameters

### Test Coverage
- ✅ Successful text completion generation
- ✅ Multiple model configurations (GPT-3.5, GPT-4, GPT-4-turbo)
- ✅ Rate limit handling (RateLimitError → TooManyRequests)
- ✅ API error handling and propagation
- ✅ Token counting accuracy
- ✅ Prompt construction and parameter validation
- ✅ Authentication patterns and API key validation
- ✅ Concurrent request processing
- ✅ Response content extraction and validation
- ✅ Performance timing measurements

### 3. Agent Manager Integration Test

The `test_agent_manager_integration.py` demonstrates complex service coordination testing:

### What It Tests
- **ReAct Pattern**: Think-Act-Observe cycles with multi-step reasoning
- **Tool Coordination**: Selection and execution of different tools (knowledge query, text completion, MCP tools)
- **Conversation State**: Management of conversation history and context
- **Multi-Service Integration**: Coordination between prompt, graph RAG, and tool services
- **Error Handling**: Tool failures, unknown tools, and error propagation
- **Configuration Management**: Dynamic tool loading and configuration

### Key Features
- **Complex Coordination**: Tests agent reasoning with multiple tool options
- **Stateful Processing**: Maintains conversation history across interactions
- **Dynamic Tool Selection**: Tests tool selection based on context and reasoning
- **Callback Pattern**: Tests think/observe callback mechanisms
- **JSON Serialization**: Handles complex data structures in prompts
- **Performance Testing**: Large conversation history handling

### Test Coverage
- ✅ Basic reasoning cycle with tool selection
- ✅ Final answer generation (ending ReAct cycle)
- ✅ Full ReAct cycle with tool execution
- ✅ Conversation history management
- ✅ Multiple tool coordination and selection
- ✅ Tool argument validation and processing
- ✅ Error handling (unknown tools, execution failures)
- ✅ Context integration and additional prompting
- ✅ Empty tool configuration handling
- ✅ Tool response processing and cleanup
- ✅ Performance with large conversation history
- ✅ JSON serialization in complex prompts

### 4. Knowledge Graph Extract → Store Pipeline Integration Test

The `test_kg_extract_store_integration.py` demonstrates multi-stage pipeline testing:

### What It Tests
- **Text-to-Graph Transformation**: Complete pipeline from text chunks to graph triples
- **Entity Extraction**: Definition extraction with proper URI generation
- **Relationship Extraction**: Subject-predicate-object relationship extraction
- **Graph Database Integration**: Storage coordination with Cassandra knowledge store
- **Data Validation**: Entity filtering, validation, and consistency checks
- **Pipeline Coordination**: Multi-stage processing with proper data flow

### Key Features
- **Multi-Stage Pipeline**: Tests definitions → relationships → storage coordination
- **Graph Data Structures**: RDF triples, entity contexts, and graph embeddings
- **URI Generation**: Consistent entity URI creation across pipeline stages
- **Data Transformation**: Complex text analysis to structured graph data
- **Batch Processing**: Large document set processing performance
- **Error Resilience**: Graceful handling of extraction failures

### Test Coverage
- ✅ Definitions extraction pipeline (text → entities + definitions)
- ✅ Relationships extraction pipeline (text → subject-predicate-object)
- ✅ URI generation consistency between processors
- ✅ Triple generation from definitions and relationships
- ✅ Knowledge store integration (triples and embeddings storage)
- ✅ End-to-end pipeline coordination
- ✅ Error handling in extraction services
- ✅ Empty and invalid extraction results handling
- ✅ Entity filtering and validation
- ✅ Large batch processing performance
- ✅ Metadata propagation through pipeline stages

## Best Practices

### Test Organization
- Group related tests in classes
- Use descriptive test names that explain the scenario
- Follow the Arrange-Act-Assert pattern
- Use appropriate pytest markers (`@pytest.mark.integration`, `@pytest.mark.slow`)

### Mock Strategy
- Mock external services (databases, APIs, message brokers)
- Use real service logic and data transformations
- Create realistic mock responses that match actual service behavior
- Reset mocks between tests to ensure isolation

### Test Data
- Use realistic test data that reflects actual usage patterns
- Create reusable fixtures for common test scenarios
- Test with various data sizes and edge cases
- Include both success and failure scenarios

### Error Testing
- Test each dependency failure scenario
- Verify proper error propagation and cleanup
- Test timeout and retry mechanisms
- Validate error response formats

### Performance Testing
- Mark performance tests with `@pytest.mark.slow`
- Test with realistic data volumes
- Set reasonable performance expectations
- Monitor resource usage during tests

## Adding New Integration Tests

1. **Identify Service Dependencies**: Map out which services your target service coordinates with
2. **Create Mock Fixtures**: Set up mocks for each dependency in conftest.py
3. **Design Test Scenarios**: Plan happy path, error cases, and edge conditions
4. **Implement Tests**: Follow the established patterns in this directory
5. **Add Documentation**: Update this README with your new test patterns

## Test Markers

- `@pytest.mark.integration`: Marks tests as integration tests
- `@pytest.mark.slow`: Marks tests that take longer to run
- `@pytest.mark.asyncio`: Required for async test functions

## Future Enhancements

- Add tests with real test containers for database integration
- Implement contract testing for service interfaces
- Add performance benchmarking for critical paths
- Create integration test templates for common service patterns