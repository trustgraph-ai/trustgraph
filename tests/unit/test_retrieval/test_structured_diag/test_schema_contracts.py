"""
Contract tests for structured-diag service schemas
"""

import pytest
import json
from pulsar.schema import JsonSchema
from trustgraph.schema.services.diagnosis import (
    StructuredDataDiagnosisRequest,
    StructuredDataDiagnosisResponse
)


class TestStructuredDiagnosisSchemaContract:
    """Contract tests for structured diagnosis message schemas"""

    def test_request_schema_basic_fields(self):
        """Test basic request schema fields"""
        request = StructuredDataDiagnosisRequest(
            operation="detect-type",
            sample="test data"
        )

        assert request.operation == "detect-type"
        assert request.sample == "test data"
        assert request.type == ""  # Optional, defaults to empty string
        assert request.schema_name == ""  # Optional, defaults to empty string
        assert request.options == {}  # Optional, defaults to empty dict

    def test_request_schema_all_operations(self):
        """Test request schema supports all operations"""
        operations = ["detect-type", "generate-descriptor", "diagnose", "schema-selection"]

        for op in operations:
            request = StructuredDataDiagnosisRequest(
                operation=op,
                sample="test data"
            )
            assert request.operation == op

    def test_request_schema_with_options(self):
        """Test request schema with options"""
        options = {"delimiter": ",", "has_header": "true"}
        request = StructuredDataDiagnosisRequest(
            operation="generate-descriptor",
            sample="test data",
            type="csv",
            schema_name="products",
            options=options
        )

        assert request.options == options
        assert request.type == "csv"
        assert request.schema_name == "products"

    def test_response_schema_basic_fields(self):
        """Test basic response schema fields"""
        response = StructuredDataDiagnosisResponse(
            operation="detect-type",
            detected_type="xml",
            confidence=0.9,
            error=None  # Explicitly set to None
        )

        assert response.operation == "detect-type"
        assert response.detected_type == "xml"
        assert response.confidence == 0.9
        assert response.error is None
        assert response.descriptor == ""  # Defaults to empty string
        assert response.metadata == {}  # Defaults to empty dict
        assert response.schema_matches == []  # Defaults to empty list

    def test_response_schema_with_error(self):
        """Test response schema with error"""
        from trustgraph.schema.core.primitives import Error

        error = Error(
            type="ServiceError",
            message="Service unavailable"
        )
        response = StructuredDataDiagnosisResponse(
            operation="schema-selection",
            error=error
        )

        assert response.error == error
        assert response.error.type == "ServiceError"
        assert response.error.message == "Service unavailable"

    def test_response_schema_with_schema_matches(self):
        """Test response schema with schema_matches array"""
        matches = ["products", "inventory", "catalog"]
        response = StructuredDataDiagnosisResponse(
            operation="schema-selection",
            schema_matches=matches
        )

        assert response.operation == "schema-selection"
        assert response.schema_matches == matches
        assert len(response.schema_matches) == 3

    def test_response_schema_empty_schema_matches(self):
        """Test response schema with empty schema_matches array"""
        response = StructuredDataDiagnosisResponse(
            operation="schema-selection",
            schema_matches=[]
        )

        assert response.schema_matches == []
        assert isinstance(response.schema_matches, list)

    def test_response_schema_with_descriptor(self):
        """Test response schema with descriptor"""
        descriptor = {
            "mapping": {
                "field1": "column1",
                "field2": "column2"
            }
        }
        response = StructuredDataDiagnosisResponse(
            operation="generate-descriptor",
            descriptor=json.dumps(descriptor)
        )

        assert response.descriptor == json.dumps(descriptor)
        parsed = json.loads(response.descriptor)
        assert parsed["mapping"]["field1"] == "column1"

    def test_response_schema_with_metadata(self):
        """Test response schema with metadata"""
        metadata = {
            "csv_options": json.dumps({"delimiter": ","}),
            "field_count": "5"
        }
        response = StructuredDataDiagnosisResponse(
            operation="diagnose",
            metadata=metadata
        )

        assert response.metadata == metadata
        assert response.metadata["field_count"] == "5"

    @pytest.mark.skip(reason="JsonSchema requires Pulsar Record types, not dataclasses")
    def test_schema_serialization(self):
        """Test that schemas can be serialized and deserialized correctly"""
        # Test request serialization
        request = StructuredDataDiagnosisRequest(
            operation="schema-selection",
            sample="test data",
            options={"key": "value"}
        )

        # Simulate Pulsar JsonSchema serialization
        schema = JsonSchema(StructuredDataDiagnosisRequest)
        serialized = schema.encode(request)
        deserialized = schema.decode(serialized)

        assert deserialized.operation == request.operation
        assert deserialized.sample == request.sample
        assert deserialized.options == request.options

    @pytest.mark.skip(reason="JsonSchema requires Pulsar Record types, not dataclasses")
    def test_response_serialization_with_schema_matches(self):
        """Test response serialization with schema_matches array"""
        response = StructuredDataDiagnosisResponse(
            operation="schema-selection",
            schema_matches=["schema1", "schema2"],
            confidence=0.85
        )

        # Simulate Pulsar JsonSchema serialization
        schema = JsonSchema(StructuredDataDiagnosisResponse)
        serialized = schema.encode(response)
        deserialized = schema.decode(serialized)

        assert deserialized.operation == response.operation
        assert deserialized.schema_matches == response.schema_matches
        assert deserialized.confidence == response.confidence

    def test_backwards_compatibility(self):
        """Test that old clients can still use the service without schema_matches"""
        # Old response without schema_matches should still work
        response = StructuredDataDiagnosisResponse(
            operation="detect-type",
            detected_type="json",
            confidence=0.95
        )

        # Verify default value for new field
        assert response.schema_matches == []  # Defaults to empty list when not set

        # Verify old fields still work
        assert response.detected_type == "json"
        assert response.confidence == 0.95

    def test_schema_selection_operation_contract(self):
        """Test complete contract for schema-selection operation"""
        # Request
        request = StructuredDataDiagnosisRequest(
            operation="schema-selection",
            sample="product_id,name,price\n1,Widget,9.99"
        )

        assert request.operation == "schema-selection"
        assert request.sample != ""

        # Response with matches
        response = StructuredDataDiagnosisResponse(
            operation="schema-selection",
            schema_matches=["products", "inventory"]
        )

        assert response.operation == "schema-selection"
        assert isinstance(response.schema_matches, list)
        assert len(response.schema_matches) == 2
        assert all(isinstance(s, str) for s in response.schema_matches)

        # Response with error
        from trustgraph.schema.core.primitives import Error
        error_response = StructuredDataDiagnosisResponse(
            operation="schema-selection",
            error=Error(type="PromptServiceError", message="Service unavailable")
        )

        assert error_response.error is not None
        assert error_response.schema_matches == []  # Default empty list when not set

    def test_all_operations_supported(self):
        """Verify all operations are properly supported in the contract"""
        supported_operations = {
            "detect-type": {
                "required_request": ["sample"],
                "expected_response": ["detected_type", "confidence"]
            },
            "generate-descriptor": {
                "required_request": ["sample", "type", "schema_name"],
                "expected_response": ["descriptor"]
            },
            "diagnose": {
                "required_request": ["sample"],
                "expected_response": ["detected_type", "confidence", "descriptor"]
            },
            "schema-selection": {
                "required_request": ["sample"],
                "expected_response": ["schema_matches"]
            }
        }

        for operation, contract in supported_operations.items():
            # Test request creation
            request_data = {"operation": operation}
            for field in contract["required_request"]:
                request_data[field] = "test_value"

            request = StructuredDataDiagnosisRequest(**request_data)
            assert request.operation == operation

            # Test response creation
            response = StructuredDataDiagnosisResponse(operation=operation)
            assert response.operation == operation