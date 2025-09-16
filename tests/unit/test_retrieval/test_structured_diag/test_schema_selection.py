"""
Unit tests for structured-diag service schema-selection operation
"""

import pytest
import json
from unittest.mock import AsyncMock, MagicMock, patch
from trustgraph.retrieval.structured_diag.service import Processor
from trustgraph.schema.services.diagnosis import StructuredDataDiagnosisRequest, StructuredDataDiagnosisResponse
from trustgraph.schema import RowSchema, Field as SchemaField, Error


@pytest.fixture
def mock_schemas():
    """Create mock schemas for testing"""
    schemas = {
        "products": RowSchema(
            name="products",
            description="Product catalog schema",
            fields=[
                SchemaField(
                    name="product_id",
                    type="string",
                    description="Product identifier",
                    required=True,
                    primary=True,
                    indexed=True
                ),
                SchemaField(
                    name="name",
                    type="string",
                    description="Product name",
                    required=True
                ),
                SchemaField(
                    name="price",
                    type="number",
                    description="Product price",
                    required=True
                )
            ]
        ),
        "customers": RowSchema(
            name="customers",
            description="Customer database schema",
            fields=[
                SchemaField(
                    name="customer_id",
                    type="string",
                    description="Customer identifier",
                    required=True,
                    primary=True
                ),
                SchemaField(
                    name="name",
                    type="string",
                    description="Customer name",
                    required=True
                ),
                SchemaField(
                    name="email",
                    type="string",
                    description="Customer email",
                    required=True
                )
            ]
        ),
        "orders": RowSchema(
            name="orders",
            description="Order management schema",
            fields=[
                SchemaField(
                    name="order_id",
                    type="string",
                    description="Order identifier",
                    required=True,
                    primary=True
                ),
                SchemaField(
                    name="customer_id",
                    type="string",
                    description="Customer identifier",
                    required=True
                ),
                SchemaField(
                    name="total",
                    type="number",
                    description="Order total",
                    required=True
                )
            ]
        )
    }
    return schemas


@pytest.fixture
def service(mock_schemas):
    """Create service instance with mock configuration"""
    service = Processor(
        taskgroup=MagicMock(),
        id="test-processor"
    )
    service.schemas = mock_schemas
    return service


@pytest.fixture
def mock_flow():
    """Create mock flow with prompt service"""
    flow = MagicMock()
    prompt_request_flow = AsyncMock()
    flow.return_value.request = prompt_request_flow
    return flow, prompt_request_flow


@pytest.mark.asyncio
async def test_schema_selection_success(service, mock_flow):
    """Test successful schema selection"""
    flow, prompt_request_flow = mock_flow

    # Mock prompt service response with matching schemas
    mock_response = MagicMock()
    mock_response.error = None
    mock_response.text = '["products", "orders"]'
    prompt_request_flow.return_value = mock_response

    # Create request
    request = StructuredDataDiagnosisRequest(
        operation="schema-selection",
        sample="product_id,name,price,quantity\nPROD001,Widget,19.99,5"
    )

    # Execute operation
    response = await service.schema_selection_operation(request, flow)

    # Verify response
    assert response.error is None
    assert response.operation == "schema-selection"
    assert response.schema_matches == ["products", "orders"]

    # Verify prompt service was called correctly
    prompt_request_flow.assert_called_once()
    call_args = prompt_request_flow.call_args[0][0]
    assert call_args.id == "schema-selection"

    # Check that all schemas were passed to prompt
    terms = call_args.terms
    schemas_data = json.loads(terms["schemas"])
    assert len(schemas_data) == 3  # All 3 schemas
    assert any(s["name"] == "products" for s in schemas_data)
    assert any(s["name"] == "customers" for s in schemas_data)
    assert any(s["name"] == "orders" for s in schemas_data)


@pytest.mark.asyncio
async def test_schema_selection_empty_response(service, mock_flow):
    """Test handling of empty prompt service response"""
    flow, prompt_request_flow = mock_flow

    # Mock empty response from prompt service
    mock_response = MagicMock()
    mock_response.error = None
    mock_response.text = ""
    prompt_request_flow.return_value = mock_response

    # Create request
    request = StructuredDataDiagnosisRequest(
        operation="schema-selection",
        sample="test data"
    )

    # Execute operation
    response = await service.schema_selection_operation(request, flow)

    # Verify error response
    assert response.error is not None
    assert response.error.type == "PromptServiceError"
    assert "Empty response" in response.error.message
    assert response.operation == "schema-selection"


@pytest.mark.asyncio
async def test_schema_selection_prompt_error(service, mock_flow):
    """Test handling of prompt service error"""
    flow, prompt_request_flow = mock_flow

    # Mock error response from prompt service
    mock_response = MagicMock()
    mock_response.error = Error(
        type="ServiceError",
        message="Prompt service unavailable"
    )
    mock_response.text = None
    prompt_request_flow.return_value = mock_response

    # Create request
    request = StructuredDataDiagnosisRequest(
        operation="schema-selection",
        sample="test data"
    )

    # Execute operation
    response = await service.schema_selection_operation(request, flow)

    # Verify error response
    assert response.error is not None
    assert response.error.type == "PromptServiceError"
    assert "Failed to select schemas" in response.error.message
    assert response.operation == "schema-selection"


@pytest.mark.asyncio
async def test_schema_selection_invalid_json(service, mock_flow):
    """Test handling of invalid JSON response from prompt service"""
    flow, prompt_request_flow = mock_flow

    # Mock invalid JSON response
    mock_response = MagicMock()
    mock_response.error = None
    mock_response.text = "not valid json"
    prompt_request_flow.return_value = mock_response

    # Create request
    request = StructuredDataDiagnosisRequest(
        operation="schema-selection",
        sample="test data"
    )

    # Execute operation
    response = await service.schema_selection_operation(request, flow)

    # Verify error response
    assert response.error is not None
    assert response.error.type == "ParseError"
    assert "Failed to parse schema selection response" in response.error.message
    assert response.operation == "schema-selection"


@pytest.mark.asyncio
async def test_schema_selection_non_array_response(service, mock_flow):
    """Test handling of non-array JSON response from prompt service"""
    flow, prompt_request_flow = mock_flow

    # Mock non-array JSON response
    mock_response = MagicMock()
    mock_response.error = None
    mock_response.text = '{"schema": "products"}'  # Object instead of array
    prompt_request_flow.return_value = mock_response

    # Create request
    request = StructuredDataDiagnosisRequest(
        operation="schema-selection",
        sample="test data"
    )

    # Execute operation
    response = await service.schema_selection_operation(request, flow)

    # Verify error response
    assert response.error is not None
    assert response.error.type == "ParseError"
    assert "Failed to parse schema selection response" in response.error.message
    assert response.operation == "schema-selection"


@pytest.mark.asyncio
async def test_schema_selection_with_options(service, mock_flow):
    """Test schema selection with additional options"""
    flow, prompt_request_flow = mock_flow

    # Mock successful response
    mock_response = MagicMock()
    mock_response.error = None
    mock_response.text = '["products"]'
    prompt_request_flow.return_value = mock_response

    # Create request with options
    request = StructuredDataDiagnosisRequest(
        operation="schema-selection",
        sample="test data",
        options={"filter": "catalog", "confidence": "high"}
    )

    # Execute operation
    response = await service.schema_selection_operation(request, flow)

    # Verify response
    assert response.error is None
    assert response.schema_matches == ["products"]

    # Verify options were passed to prompt
    call_args = prompt_request_flow.call_args[0][0]
    terms = call_args.terms
    options = json.loads(terms["options"])
    assert options["filter"] == "catalog"
    assert options["confidence"] == "high"


@pytest.mark.asyncio
async def test_schema_selection_exception_handling(service, mock_flow):
    """Test handling of unexpected exceptions"""
    flow, prompt_request_flow = mock_flow

    # Mock exception during prompt service call
    prompt_request_flow.side_effect = Exception("Unexpected error")

    # Create request
    request = StructuredDataDiagnosisRequest(
        operation="schema-selection",
        sample="test data"
    )

    # Execute operation
    response = await service.schema_selection_operation(request, flow)

    # Verify error response
    assert response.error is not None
    assert response.error.type == "PromptServiceError"
    assert "Failed to select schemas" in response.error.message
    assert response.operation == "schema-selection"


@pytest.mark.asyncio
async def test_schema_selection_empty_schemas(service, mock_flow):
    """Test schema selection with no schemas configured"""
    flow, prompt_request_flow = mock_flow

    # Clear schemas
    service.schemas = {}

    # Mock response (shouldn't be reached)
    mock_response = MagicMock()
    mock_response.error = None
    mock_response.text = '[]'
    prompt_request_flow.return_value = mock_response

    # Create request
    request = StructuredDataDiagnosisRequest(
        operation="schema-selection",
        sample="test data"
    )

    # Execute operation
    response = await service.schema_selection_operation(request, flow)

    # Should still succeed but with empty schemas array passed to prompt
    assert response.error is None
    assert response.schema_matches == []

    # Verify empty schemas array was passed
    call_args = prompt_request_flow.call_args[0][0]
    terms = call_args.terms
    schemas_data = json.loads(terms["schemas"])
    assert len(schemas_data) == 0