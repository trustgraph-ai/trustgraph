# TrustGraph Test Suite

This document provides instructions for running and maintaining the TrustGraph test suite.

## Overview

The TrustGraph test suite follows the testing strategy outlined in [TEST_STRATEGY.md](TEST_STRATEGY.md) and implements the test cases defined in [TEST_CASES.md](TEST_CASES.md). The tests are organized into unit tests, integration tests, and performance tests.

## Test Structure

```
tests/
├── unit/
│   ├── test_text_completion/
│   │   ├── test_vertexai_processor.py
│   │   ├── conftest.py
│   │   └── __init__.py
│   ├── test_embeddings/
│   ├── test_storage/
│   └── test_query/
├── integration/
│   ├── test_flows/
│   └── test_databases/
├── fixtures/
│   ├── messages.py
│   ├── configs.py
│   └── mocks.py
├── requirements.txt
├── pytest.ini
└── conftest.py
```

## Prerequisites

### Install TrustGraph Packages

The tests require TrustGraph packages to be installed. You can use the provided scripts:

#### Option 1: Automated Setup (Recommended)
```bash
# From the project root directory - runs all setup steps
./run_tests.sh
```

#### Option 2: Step-by-step Setup
```bash
# Check what imports are working
./check_imports.py

# Install TrustGraph packages
./install_packages.sh

# Verify imports work
./check_imports.py

# Install test dependencies
cd tests/
pip install -r requirements.txt
cd ..
```

#### Option 3: Manual Installation
```bash
# Install base package first (required by others)
cd trustgraph-base
pip install -e .
cd ..

# Install vertexai package (depends on base)
cd trustgraph-vertexai  
pip install -e .
cd ..

# Install flow package (for additional components)
cd trustgraph-flow
pip install -e .
cd ..
```

### Install Test Dependencies

```bash
cd tests/
pip install -r requirements.txt
```

### Required Dependencies

- `pytest>=7.0.0` - Testing framework
- `pytest-asyncio>=0.21.0` - Async testing support
- `pytest-mock>=3.10.0` - Mocking utilities
- `pytest-cov>=4.0.0` - Coverage reporting
- `google-cloud-aiplatform>=1.25.0` - Google Cloud dependencies
- `google-auth>=2.17.0` - Authentication
- `google-api-core>=2.11.0` - API core
- `pulsar-client>=3.0.0` - Pulsar messaging
- `prometheus-client>=0.16.0` - Metrics

## Running Tests

### Basic Test Execution

```bash
# Run all tests
pytest

# Run tests with verbose output
pytest -v

# Run specific test file
pytest tests/unit/test_text_completion/test_vertexai_processor.py

# Run specific test class
pytest tests/unit/test_text_completion/test_vertexai_processor.py::TestVertexAIProcessorInitialization

# Run specific test method
pytest tests/unit/test_text_completion/test_vertexai_processor.py::TestVertexAIProcessorInitialization::test_processor_initialization_with_valid_credentials
```

### Test Categories

```bash
# Run only unit tests
pytest -m unit

# Run only integration tests
pytest -m integration

# Run only VertexAI tests
pytest -m vertexai

# Exclude slow tests
pytest -m "not slow"
```

### Coverage Reports

```bash
# Run tests with coverage
pytest --cov=trustgraph

# Generate HTML coverage report
pytest --cov=trustgraph --cov-report=html

# Generate terminal coverage report
pytest --cov=trustgraph --cov-report=term-missing

# Fail if coverage is below 80%
pytest --cov=trustgraph --cov-fail-under=80
```

## VertexAI Text Completion Tests

### Test Implementation

The VertexAI text completion service tests are located in:
- **Main test file**: `tests/unit/test_text_completion/test_vertexai_processor.py`
- **Fixtures**: `tests/unit/test_text_completion/conftest.py`

### Test Coverage

The VertexAI tests include **139 test cases** covering:

#### 1. Processor Initialization Tests (6 tests)
- Service account credential loading
- Model configuration (Gemini models)
- Custom parameters (temperature, max_output, region)
- Generation config and safety settings

```bash
# Run initialization tests
pytest tests/unit/test_text_completion/test_vertexai_processor.py::TestVertexAIProcessorInitialization -v
```

#### 2. Message Processing Tests (5 tests)
- Simple text completion
- System instructions handling
- Long context processing
- Empty prompt handling

```bash
# Run message processing tests
pytest tests/unit/test_text_completion/test_vertexai_processor.py::TestVertexAIMessageProcessing -v
```

#### 3. Safety Filtering Tests (2 tests)
- Safety settings configuration
- Blocked content handling

```bash
# Run safety filtering tests
pytest tests/unit/test_text_completion/test_vertexai_processor.py::TestVertexAISafetyFiltering -v
```

#### 4. Error Handling Tests (7 tests)
- Rate limiting (`ResourceExhausted` → `TooManyRequests`)
- Authentication errors
- Generic exceptions
- Model not found errors
- Quota exceeded errors
- Token limit errors

```bash
# Run error handling tests
pytest tests/unit/test_text_completion/test_vertexai_processor.py::TestVertexAIErrorHandling -v
```

#### 5. Metrics Collection Tests (4 tests)
- Token usage tracking
- Request duration measurement
- Error rate collection
- Cost calculation basis

```bash
# Run metrics collection tests
pytest tests/unit/test_text_completion/test_vertexai_processor.py::TestVertexAIMetricsCollection -v
```

### Running All VertexAI Tests

```bash
# Run all VertexAI tests
pytest tests/unit/test_text_completion/test_vertexai_processor.py -v

# Run with coverage
pytest tests/unit/test_text_completion/test_vertexai_processor.py --cov=trustgraph.model.text_completion.vertexai

# Run with detailed output
pytest tests/unit/test_text_completion/test_vertexai_processor.py -v -s
```

## Test Configuration

### Pytest Configuration

The test suite uses the following configuration in `pytest.ini`:

```ini
[tool:pytest]
testpaths = tests
python_files = test_*.py
python_classes = Test*
python_functions = test_*
addopts = 
    -v
    --tb=short
    --strict-markers
    --disable-warnings
    --cov=trustgraph
    --cov-report=html
    --cov-report=term-missing
    --cov-fail-under=80
asyncio_mode = auto
markers =
    slow: marks tests as slow (deselect with '-m "not slow"')
    integration: marks tests as integration tests
    unit: marks tests as unit tests
    vertexai: marks tests as vertex ai specific tests
```

### Test Markers

Use pytest markers to categorize and filter tests:

```python
@pytest.mark.unit
@pytest.mark.vertexai
async def test_vertexai_functionality():
    pass

@pytest.mark.integration
@pytest.mark.slow
async def test_end_to_end_flow():
    pass
```

## Test Development Guidelines

### Following TEST_STRATEGY.md

1. **Mock External Dependencies**: Always mock external services (APIs, databases, Pulsar)
2. **Test Business Logic**: Focus on testing your code, not external infrastructure
3. **Use Dependency Injection**: Make services testable by injecting dependencies
4. **Async Testing**: Use proper async test patterns for async services
5. **Comprehensive Coverage**: Test success paths, error paths, and edge cases

### Test Structure Example

```python
class TestServiceName(IsolatedAsyncioTestCase):
    """Test service functionality"""

    def setUp(self):
        """Set up test fixtures"""
        self.config = {...}

    @patch('external.dependency')
    async def test_success_case(self, mock_dependency):
        """Test successful operation"""
        # Arrange
        mock_dependency.return_value = expected_result
        
        # Act
        result = await service.method()
        
        # Assert
        assert result == expected_result
        mock_dependency.assert_called_once()
```

### Fixture Usage

Use fixtures from `conftest.py` to reduce code duplication:

```python
async def test_with_fixtures(self, mock_vertexai_model, sample_text_completion_request):
    """Test using shared fixtures"""
    # Fixtures are automatically injected
    result = await processor.process(sample_text_completion_request)
    assert result.text == "Test response"
```

## Debugging Tests

### Running Tests with Debug Information

```bash
# Run with debug output
pytest -v -s tests/unit/test_text_completion/test_vertexai_processor.py

# Run with pdb on failures
pytest --pdb tests/unit/test_text_completion/test_vertexai_processor.py

# Run with detailed tracebacks
pytest --tb=long tests/unit/test_text_completion/test_vertexai_processor.py
```

### Common Issues and Solutions

#### 1. Import Errors

**Symptom**: `ModuleNotFoundError: No module named 'trustgraph'` or similar import errors

**Solution**:
```bash
# First, check what's working
./check_imports.py

# Install the required packages
./install_packages.sh

# Verify installation worked
./check_imports.py

# If still having issues, check Python path
echo $PYTHONPATH
export PYTHONPATH=/home/mark/work/trustgraph.ai/trustgraph:$PYTHONPATH

# Try running tests from project root
cd /home/mark/work/trustgraph.ai/trustgraph
pytest tests/unit/test_text_completion/test_vertexai_processor.py -v
```

**Common causes**:
- TrustGraph packages not installed (`pip install -e .` in each package directory)
- Wrong working directory (should be in project root)
- Python path not set correctly
- Missing dependencies (install with `pip install -r tests/requirements.txt`)

#### 2. Async Test Issues
```python
# Use IsolatedAsyncioTestCase for async tests
class TestAsyncService(IsolatedAsyncioTestCase):
    async def test_async_method(self):
        result = await service.async_method()
        assert result is not None
```

#### 3. Mock Issues
```python
# Use proper async mocks for async methods
mock_client = AsyncMock()
mock_client.async_method.return_value = expected_result

# Use MagicMock for sync methods
mock_client = MagicMock()
mock_client.sync_method.return_value = expected_result
```

## Continuous Integration

### Running Tests in CI

```bash
# Install dependencies
pip install -r tests/requirements.txt

# Run tests with coverage
pytest --cov=trustgraph --cov-report=xml --cov-fail-under=80

# Run tests in parallel (if using pytest-xdist)
pytest -n auto
```

### Test Reports

The test suite generates several types of reports:

1. **Coverage Reports**: HTML and XML coverage reports
2. **Test Results**: JUnit XML format for CI integration
3. **Performance Reports**: For performance and load tests

```bash
# Generate all reports
pytest --cov=trustgraph --cov-report=html --cov-report=xml --junitxml=test-results.xml
```

## Adding New Tests

### 1. Create Test File

```python
# tests/unit/test_new_service/test_new_processor.py
import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from unittest import IsolatedAsyncioTestCase

from trustgraph.new_service.processor import Processor

class TestNewProcessor(IsolatedAsyncioTestCase):
    """Test new processor functionality"""
    
    def setUp(self):
        self.config = {...}
    
    @patch('trustgraph.new_service.processor.external_dependency')
    async def test_processor_method(self, mock_dependency):
        """Test processor method"""
        # Arrange
        mock_dependency.return_value = expected_result
        processor = Processor(**self.config)
        
        # Act
        result = await processor.method()
        
        # Assert
        assert result == expected_result
```

### 2. Create Fixtures

```python
# tests/unit/test_new_service/conftest.py
import pytest
from unittest.mock import MagicMock

@pytest.fixture
def mock_new_service_client():
    """Mock client for new service"""
    return MagicMock()

@pytest.fixture
def sample_request():
    """Sample request object"""
    return RequestObject(id="test", data="test data")
```

### 3. Update pytest.ini

```ini
markers =
    new_service: marks tests as new service specific tests
```

## Performance Testing

### Load Testing

```bash
# Run performance tests
pytest -m performance tests/performance/

# Run with custom parameters
pytest -m performance --count=100 --concurrent=10
```

### Memory Testing

```bash
# Run with memory profiling
pytest --profile tests/unit/test_text_completion/test_vertexai_processor.py
```

## Best Practices

### 1. Test Naming
- Use descriptive test names that explain what is being tested
- Follow the pattern: `test_<method>_<scenario>_<expected_result>`

### 2. Test Organization
- Group related tests in classes
- Use meaningful class names that describe the component being tested
- Keep tests focused on a single aspect of functionality

### 3. Mock Strategy
- Mock external dependencies, not internal business logic
- Use the most specific mock type (AsyncMock for async, MagicMock for sync)
- Verify mock calls to ensure proper interaction

### 4. Assertions
- Use specific assertions that clearly indicate what went wrong
- Test both positive and negative cases
- Include edge cases and boundary conditions

### 5. Test Data
- Use fixtures for reusable test data
- Keep test data simple and focused
- Avoid hardcoded values when possible

## Troubleshooting

### Common Test Failures

1. **Import Errors**: Check PYTHONPATH and module structure
2. **Async Issues**: Ensure proper async/await usage and AsyncMock
3. **Mock Failures**: Verify mock setup and expected call patterns
4. **Coverage Issues**: Check for untested code paths

### Getting Help

- Check the [TEST_STRATEGY.md](TEST_STRATEGY.md) for testing patterns
- Review [TEST_CASES.md](TEST_CASES.md) for comprehensive test scenarios
- Examine existing tests for examples and patterns
- Use pytest's built-in help: `pytest --help`

## Future Enhancements

### Planned Test Additions

1. **Integration Tests**: End-to-end flow testing
2. **Performance Tests**: Load and stress testing
3. **Security Tests**: Input validation and authentication
4. **Contract Tests**: API contract verification

### Test Infrastructure Improvements

1. **Parallel Test Execution**: Using pytest-xdist
2. **Test Data Management**: Better fixture organization
3. **Reporting**: Enhanced test reporting and metrics
4. **CI Integration**: Automated test execution and reporting

---

This testing guide provides comprehensive instructions for running and maintaining the TrustGraph test suite. Follow the patterns and guidelines to ensure consistent, reliable, and maintainable tests across all services.