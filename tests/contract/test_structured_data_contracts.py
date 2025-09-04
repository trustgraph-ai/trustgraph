"""
Contract tests for Structured Data Pulsar Message Schemas

These tests verify the contracts for all structured data Pulsar message schemas,
ensuring schema compatibility, serialization contracts, and service interface stability.
Following the TEST_STRATEGY.md approach for contract testing.
"""

import pytest
import json
from typing import Dict, Any

from trustgraph.schema import (
    StructuredDataSubmission, ExtractedObject,
    QuestionToStructuredQueryRequest, QuestionToStructuredQueryResponse,
    StructuredQueryRequest, StructuredQueryResponse,
    StructuredObjectEmbedding, Field, RowSchema,
    Metadata, Error, Value
)
from .conftest import serialize_deserialize_test


@pytest.mark.contract
class TestStructuredDataSchemaContracts:
    """Contract tests for structured data schemas"""

    def test_field_schema_contract(self):
        """Test enhanced Field schema contract"""
        # Arrange & Act - create Field instance directly
        field = Field(
            name="customer_id",
            type="string",
            size=0,
            primary=True,
            description="Unique customer identifier",
            required=True,
            enum_values=[],
            indexed=True
        )

        # Assert - test field properties
        assert field.name == "customer_id"
        assert field.type == "string"
        assert field.primary is True
        assert field.indexed is True
        assert isinstance(field.enum_values, list)
        assert len(field.enum_values) == 0
        
        # Test with enum values
        field_with_enum = Field(
            name="status",
            type="string",
            size=0,
            primary=False,
            description="Status field",
            required=False,
            enum_values=["active", "inactive"],
            indexed=True
        )
        
        assert len(field_with_enum.enum_values) == 2
        assert "active" in field_with_enum.enum_values

    def test_row_schema_contract(self):
        """Test RowSchema contract"""
        # Arrange & Act
        field = Field(
            name="email",
            type="string",
            size=255,
            primary=False,
            description="Customer email",
            required=True,
            enum_values=[],
            indexed=True
        )
        
        schema = RowSchema(
            name="customers",
            description="Customer records schema",
            fields=[field]
        )

        # Assert
        assert schema.name == "customers"
        assert schema.description == "Customer records schema"
        assert len(schema.fields) == 1
        assert schema.fields[0].name == "email"
        assert schema.fields[0].indexed is True

    def test_structured_data_submission_contract(self):
        """Test StructuredDataSubmission schema contract"""
        # Arrange
        metadata = Metadata(
            id="structured-data-001",
            user="test_user",
            collection="test_collection",
            metadata=[]
        )
        
        # Act
        submission = StructuredDataSubmission(
            metadata=metadata,
            format="csv",
            schema_name="customer_records",
            data=b"id,name,email\n1,John,john@example.com",
            options={"delimiter": ",", "header": "true"}
        )

        # Assert
        assert submission.format == "csv"
        assert submission.schema_name == "customer_records"
        assert submission.options["delimiter"] == ","
        assert submission.metadata.id == "structured-data-001"
        assert len(submission.data) > 0

    def test_extracted_object_contract(self):
        """Test ExtractedObject schema contract"""
        # Arrange
        metadata = Metadata(
            id="extracted-obj-001",
            user="test_user",
            collection="test_collection",
            metadata=[]
        )
        
        # Act
        obj = ExtractedObject(
            metadata=metadata,
            schema_name="customer_records",
            values={"id": "123", "name": "John Doe", "email": "john@example.com"},
            confidence=0.95,
            source_span="John Doe (john@example.com) customer ID 123"
        )

        # Assert
        assert obj.schema_name == "customer_records"
        assert obj.values["name"] == "John Doe"
        assert obj.confidence == 0.95
        assert len(obj.source_span) > 0
        assert obj.metadata.id == "extracted-obj-001"


@pytest.mark.contract
class TestStructuredQueryServiceContracts:
    """Contract tests for structured query services"""

    def test_nlp_to_structured_query_request_contract(self):
        """Test QuestionToStructuredQueryRequest schema contract"""
        # Act
        request = QuestionToStructuredQueryRequest(
            question="Show me all customers who registered last month",
            max_results=100
        )

        # Assert
        assert "customers" in request.question
        assert request.max_results == 100

    def test_nlp_to_structured_query_response_contract(self):
        """Test QuestionToStructuredQueryResponse schema contract"""
        # Act
        response = QuestionToStructuredQueryResponse(
            error=None,
            graphql_query="query { customers(filter: {registered: {gte: \"2024-01-01\"}}) { id name email } }",
            variables={"start_date": "2024-01-01"},
            detected_schemas=["customers"],
            confidence=0.92
        )

        # Assert
        assert response.error is None
        assert "customers" in response.graphql_query
        assert response.detected_schemas[0] == "customers"
        assert response.confidence > 0.9

    def test_structured_query_request_contract(self):
        """Test StructuredQueryRequest schema contract"""
        # Act
        request = StructuredQueryRequest(
            question="Show me customers with limit 10"
        )

        # Assert
        assert "customers" in request.question

    def test_structured_query_response_contract(self):
        """Test StructuredQueryResponse schema contract"""
        # Act
        response = StructuredQueryResponse(
            error=None,
            data='{"customers": [{"id": "1", "name": "John", "email": "john@example.com"}]}',
            errors=[]
        )

        # Assert
        assert response.error is None
        assert "customers" in response.data
        assert len(response.errors) == 0

    def test_structured_query_response_with_errors_contract(self):
        """Test StructuredQueryResponse with GraphQL errors contract"""
        # Act
        response = StructuredQueryResponse(
            error=None,
            data=None,
            errors=["Field 'invalid_field' not found in schema 'customers'"]
        )

        # Assert
        assert response.data is None
        assert len(response.errors) == 1
        assert "invalid_field" in response.errors[0]


@pytest.mark.contract
class TestStructuredEmbeddingsContracts:
    """Contract tests for structured object embeddings"""

    def test_structured_object_embedding_contract(self):
        """Test StructuredObjectEmbedding schema contract"""
        # Arrange
        metadata = Metadata(
            id="struct-embed-001",
            user="test_user",
            collection="test_collection",
            metadata=[]
        )
        
        # Act
        embedding = StructuredObjectEmbedding(
            metadata=metadata,
            vectors=[[0.1, 0.2, 0.3], [0.4, 0.5, 0.6]],
            schema_name="customer_records",
            object_id="customer_123",
            field_embeddings={
                "name": [0.1, 0.2, 0.3],
                "email": [0.4, 0.5, 0.6]
            }
        )

        # Assert
        assert embedding.schema_name == "customer_records"
        assert embedding.object_id == "customer_123"
        assert len(embedding.vectors) == 2
        assert len(embedding.field_embeddings) == 2
        assert "name" in embedding.field_embeddings


@pytest.mark.contract
class TestStructuredDataSerializationContracts:
    """Contract tests for structured data serialization/deserialization"""

    def test_structured_data_submission_serialization(self):
        """Test StructuredDataSubmission serialization contract"""
        # Arrange
        metadata = Metadata(id="test", user="user", collection="col", metadata=[])
        submission_data = {
            "metadata": metadata,
            "format": "json",
            "schema_name": "test_schema",
            "data": b'{"test": "data"}',
            "options": {"encoding": "utf-8"}
        }

        # Act & Assert
        assert serialize_deserialize_test(StructuredDataSubmission, submission_data)

    def test_extracted_object_serialization(self):
        """Test ExtractedObject serialization contract"""
        # Arrange
        metadata = Metadata(id="test", user="user", collection="col", metadata=[])
        object_data = {
            "metadata": metadata,
            "schema_name": "test_schema",
            "values": {"field1": "value1"},
            "confidence": 0.8,
            "source_span": "test span"
        }

        # Act & Assert
        assert serialize_deserialize_test(ExtractedObject, object_data)

    def test_nlp_query_serialization(self):
        """Test NLP query request/response serialization contract"""
        # Test request
        request_data = {
            "question": "test query",
            "max_results": 10
        }
        assert serialize_deserialize_test(QuestionToStructuredQueryRequest, request_data)

        # Test response
        response_data = {
            "error": None,
            "graphql_query": "query { test }",
            "variables": {},
            "detected_schemas": ["test"],
            "confidence": 0.9
        }
        assert serialize_deserialize_test(QuestionToStructuredQueryResponse, response_data)

    def test_structured_query_serialization(self):
        """Test structured query request/response serialization contract"""
        # Test request
        request_data = {
            "question": "Show me all customers"
        }
        assert serialize_deserialize_test(StructuredQueryRequest, request_data)

        # Test response
        response_data = {
            "error": None,
            "data": '{"customers": [{"id": "1", "name": "John"}]}',
            "errors": []
        }
        assert serialize_deserialize_test(StructuredQueryResponse, response_data)