"""
Unit tests for message translation in structured-diag service
"""

import pytest
from trustgraph.messaging.translators.diagnosis import (
    StructuredDataDiagnosisRequestTranslator,
    StructuredDataDiagnosisResponseTranslator
)
from trustgraph.schema.services.diagnosis import (
    StructuredDataDiagnosisRequest,
    StructuredDataDiagnosisResponse
)


class TestRequestTranslation:
    """Test request message translation"""

    def test_translate_schema_selection_request(self):
        """Test translating schema-selection request from API to Pulsar"""
        translator = StructuredDataDiagnosisRequestTranslator()

        # API format (with hyphens)
        api_data = {
            "operation": "schema-selection",
            "sample": "test data sample",
            "options": {"filter": "catalog"}
        }

        # Translate to Pulsar
        pulsar_msg = translator.to_pulsar(api_data)

        assert pulsar_msg.operation == "schema-selection"
        assert pulsar_msg.sample == "test data sample"
        assert pulsar_msg.options == {"filter": "catalog"}

    def test_translate_request_with_all_fields(self):
        """Test translating request with all fields"""
        translator = StructuredDataDiagnosisRequestTranslator()

        api_data = {
            "operation": "generate-descriptor",
            "sample": "csv data",
            "type": "csv",
            "schema-name": "products",
            "options": {"delimiter": ","}
        }

        pulsar_msg = translator.to_pulsar(api_data)

        assert pulsar_msg.operation == "generate-descriptor"
        assert pulsar_msg.sample == "csv data"
        assert pulsar_msg.type == "csv"
        assert pulsar_msg.schema_name == "products"
        assert pulsar_msg.options == {"delimiter": ","}


class TestResponseTranslation:
    """Test response message translation"""

    def test_translate_schema_selection_response(self):
        """Test translating schema-selection response from Pulsar to API"""
        translator = StructuredDataDiagnosisResponseTranslator()

        # Create Pulsar response with schema_matches
        pulsar_response = StructuredDataDiagnosisResponse(
            operation="schema-selection",
            schema_matches=["products", "inventory", "catalog"],
            error=None
        )

        # Translate to API format
        api_data = translator.from_pulsar(pulsar_response)

        assert api_data["operation"] == "schema-selection"
        assert api_data["schema-matches"] == ["products", "inventory", "catalog"]
        assert "error" not in api_data  # None errors shouldn't be included

    def test_translate_empty_schema_matches(self):
        """Test translating response with empty schema_matches"""
        translator = StructuredDataDiagnosisResponseTranslator()

        pulsar_response = StructuredDataDiagnosisResponse(
            operation="schema-selection",
            schema_matches=[],
            error=None
        )

        api_data = translator.from_pulsar(pulsar_response)

        assert api_data["operation"] == "schema-selection"
        assert api_data["schema-matches"] == []

    def test_translate_response_without_schema_matches(self):
        """Test translating response without schema_matches field"""
        translator = StructuredDataDiagnosisResponseTranslator()

        # Old-style response without schema_matches
        pulsar_response = StructuredDataDiagnosisResponse(
            operation="detect-type",
            detected_type="xml",
            confidence=0.9,
            error=None
        )

        api_data = translator.from_pulsar(pulsar_response)

        assert api_data["operation"] == "detect-type"
        assert api_data["detected-type"] == "xml"
        assert api_data["confidence"] == 0.9
        assert "schema-matches" not in api_data  # None values shouldn't be included

    def test_translate_response_with_error(self):
        """Test translating response with error"""
        translator = StructuredDataDiagnosisResponseTranslator()
        from trustgraph.schema.core.primitives import Error

        pulsar_response = StructuredDataDiagnosisResponse(
            operation="schema-selection",
            error=Error(
                type="PromptServiceError",
                message="Service unavailable"
            )
        )

        api_data = translator.from_pulsar(pulsar_response)

        assert api_data["operation"] == "schema-selection"
        # Error objects are typically handled separately by the gateway
        # but the translator shouldn't break on them

    def test_translate_all_response_fields(self):
        """Test translating response with all possible fields"""
        translator = StructuredDataDiagnosisResponseTranslator()
        import json

        descriptor_data = {"mapping": {"field1": "column1"}}

        pulsar_response = StructuredDataDiagnosisResponse(
            operation="diagnose",
            detected_type="csv",
            confidence=0.95,
            descriptor=json.dumps(descriptor_data),
            metadata={"field_count": "5"},
            schema_matches=["schema1", "schema2"],
            error=None
        )

        api_data = translator.from_pulsar(pulsar_response)

        assert api_data["operation"] == "diagnose"
        assert api_data["detected-type"] == "csv"
        assert api_data["confidence"] == 0.95
        assert api_data["descriptor"] == descriptor_data  # Should be parsed from JSON
        assert api_data["metadata"] == {"field_count": "5"}
        assert api_data["schema-matches"] == ["schema1", "schema2"]

    def test_response_completion_flag(self):
        """Test that response includes completion flag"""
        translator = StructuredDataDiagnosisResponseTranslator()

        pulsar_response = StructuredDataDiagnosisResponse(
            operation="schema-selection",
            schema_matches=["products"],
            error=None
        )

        api_data, is_final = translator.from_response_with_completion(pulsar_response)

        assert is_final is True  # Structured-diag responses are always final
        assert api_data["operation"] == "schema-selection"
        assert api_data["schema-matches"] == ["products"]