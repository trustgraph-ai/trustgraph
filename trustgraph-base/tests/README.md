# TrustGraph Python API Integration Tests

This directory contains integration tests for the TrustGraph Python API refactor.

## Overview

The integration tests verify the following components:
- **Basic API instantiation** and client creation
- **REST API** functionality (synchronous and asynchronous)
- **WebSocket API** functionality (synchronous and asynchronous)
- **Bulk operations** for data import/export
- **Metrics** endpoints
- **Streaming types** and data structures

## Prerequisites

1. **Python dependencies:**
   ```bash
   pip install pytest pytest-asyncio
   ```

2. **Running TrustGraph Gateway API:**
   - The tests require a running TrustGraph Gateway API server
   - Default URL: `http://localhost:8088/`
   - Configure via environment variables (see below)

## Running the Tests

### Quick Start (No Gateway Required)

To run tests in "skip mode" (validates structure without requiring a running server):

```bash
export SKIP_INTEGRATION_TESTS=true
pytest tests/test_api_integration.py -v
```

### Full Integration Tests (Requires Running Gateway)

1. **Start your TrustGraph Gateway API server**

2. **Configure environment variables:**
   ```bash
   export TRUSTGRAPH_URL=http://localhost:8088/
   export TRUSTGRAPH_TOKEN=your-auth-token-here  # Optional
   export TRUSTGRAPH_TEST_FLOW=test-flow         # Optional
   export SKIP_INTEGRATION_TESTS=false           # Enable tests
   ```

3. **Run the tests:**
   ```bash
   pytest tests/test_api_integration.py -v
   ```

### Running Specific Test Classes

```bash
# Test only REST API
pytest tests/test_api_integration.py::TestRESTAPI -v

# Test only WebSocket API
pytest tests/test_api_integration.py::TestWebSocketAPI -v

# Test only async functionality
pytest tests/test_api_integration.py::TestAsyncRESTAPI -v
pytest tests/test_api_integration.py::TestAsyncWebSocketAPI -v

# Test only bulk operations
pytest tests/test_api_integration.py::TestBulkOperations -v

# Test only metrics
pytest tests/test_api_integration.py::TestMetrics -v
```

### Running with Coverage

```bash
pytest tests/test_api_integration.py --cov=trustgraph.api --cov-report=html
```

## Environment Variables

| Variable | Description | Default |
|----------|-------------|---------|
| `TRUSTGRAPH_URL` | Gateway API URL | `http://localhost:8088/` |
| `TRUSTGRAPH_TOKEN` | Authentication token | `None` |
| `TRUSTGRAPH_TEST_FLOW` | Flow ID for testing | `test-flow` |
| `SKIP_INTEGRATION_TESTS` | Skip tests requiring live server | `false` |

## Test Categories

### 1. Basic Connection Tests (`TestBasicConnection`)
- API instantiation with/without token
- Context manager support
- Lazy initialization of clients

### 2. REST API Tests (`TestRESTAPI`)
- Flow listing
- Flow class listing
- Flow instance creation
- Method existence verification

### 3. Async REST API Tests (`TestAsyncRESTAPI`)
- Async flow operations
- Async context manager
- Async/await patterns

### 4. WebSocket API Tests (`TestWebSocketAPI`)
- WebSocket client creation
- Flow instance creation
- Method availability
- URL conversion (HTTP → WS)

### 5. Async WebSocket API Tests (`TestAsyncWebSocketAPI`)
- Async WebSocket operations
- Streaming support verification
- Method signatures

### 6. Bulk Operations Tests (`TestBulkOperations`)
- Bulk client instantiation
- Import/export methods
- Async bulk operations
- Iterator-based data transfer

### 7. Metrics Tests (`TestMetrics`)
- Metrics endpoint access
- Prometheus format validation
- Async metrics retrieval

### 8. Streaming Types Tests (`TestStreamingTypes`)
- `AgentThought` chunk creation
- `AgentObservation` chunk creation
- `AgentAnswer` chunk creation
- `RAGChunk` creation

### 9. Triple Type Tests (`TestTripleType`)
- Triple data structure validation

## Test Structure

```
tests/
├── __init__.py                  # Test package marker
├── README.md                    # This file
└── test_api_integration.py      # Main integration test suite
```

## Adding New Tests

To add new integration tests:

1. **Create a new test class** in `test_api_integration.py`:
   ```python
   class TestNewFeature:
       """Test new feature functionality"""

       @skip_if_no_gateway
       def test_new_feature(self):
           api = Api(url=GATEWAY_URL, token=AUTH_TOKEN)
           # Your test code here
           assert result is not None
   ```

2. **Add the `@skip_if_no_gateway` decorator** to tests requiring a live server

3. **Use pytest.mark.asyncio** for async tests:
   ```python
   @skip_if_no_gateway
   @pytest.mark.asyncio
   async def test_async_feature(self):
       api = Api(url=GATEWAY_URL, token=AUTH_TOKEN)
       result = await api.async_flow().list()
       assert isinstance(result, list)
   ```

## Continuous Integration

For CI/CD pipelines:

```yaml
# Example GitHub Actions workflow
- name: Run Integration Tests
  env:
    TRUSTGRAPH_URL: http://localhost:8088/
    SKIP_INTEGRATION_TESTS: false
  run: |
    # Start Gateway API in background
    ./start-gateway.sh &
    sleep 10

    # Run tests
    pytest tests/test_api_integration.py -v

    # Stop Gateway API
    ./stop-gateway.sh
```

## Troubleshooting

### Tests are skipped
- Check that `SKIP_INTEGRATION_TESTS` is set to `false`
- Verify the Gateway API is running at the configured URL

### Connection errors
- Verify `TRUSTGRAPH_URL` is correct
- Check that the Gateway API is accessible
- Ensure firewall rules allow connections

### Authentication errors
- Verify `TRUSTGRAPH_TOKEN` is set correctly
- Check token validity with the Gateway API

### Timeout errors
- Increase timeout in Api instantiation
- Check Gateway API performance
- Verify network connectivity

## Future Enhancements

Planned test additions:
- End-to-end streaming tests (requires live LLM)
- Bulk operation performance tests
- Error handling and edge cases
- WebSocket reconnection scenarios
- Token refresh mechanisms
- Multi-flow coordination tests

## Contributing

When adding new API features:
1. Add corresponding integration tests
2. Document environment variables if needed
3. Update this README with new test categories
4. Ensure tests can run in skip mode for CI

## License

Same as TrustGraph project license.
