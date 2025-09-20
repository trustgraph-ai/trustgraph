"""
Unit tests for NLP Query service
Following TEST_STRATEGY.md approach for service testing
"""

import pytest
import json
from unittest.mock import AsyncMock, MagicMock, patch
from typing import Dict, Any

from trustgraph.schema import (
    QuestionToStructuredQueryRequest, QuestionToStructuredQueryResponse,
    PromptRequest, PromptResponse, Error, RowSchema, Field as SchemaField
)
from trustgraph.retrieval.nlp_query.service import Processor


@pytest.fixture
def mock_prompt_client():
    """Mock prompt service client"""
    return AsyncMock()


@pytest.fixture
def mock_pulsar_client():
    """Mock Pulsar client"""
    return AsyncMock()


@pytest.fixture
def sample_schemas():
    """Sample schemas for testing"""
    return {
        "customers": RowSchema(
            name="customers",
            description="Customer data",
            fields=[
                SchemaField(name="id", type="string", primary=True),
                SchemaField(name="name", type="string"),
                SchemaField(name="email", type="string"),
                SchemaField(name="state", type="string")
            ]
        ),
        "orders": RowSchema(
            name="orders", 
            description="Order data",
            fields=[
                SchemaField(name="order_id", type="string", primary=True),
                SchemaField(name="customer_id", type="string"),
                SchemaField(name="total", type="float"),
                SchemaField(name="status", type="string")
            ]
        )
    }


@pytest.fixture
def processor(mock_pulsar_client, sample_schemas):
    """Create processor with mocked dependencies"""
    proc = Processor(
        taskgroup=MagicMock(),
        pulsar_client=mock_pulsar_client,
        config_type="schema"
    )
    
    # Set up schemas
    proc.schemas = sample_schemas
    
    # Mock the client method
    proc.client = MagicMock()
    
    return proc


@pytest.mark.asyncio
class TestNLPQueryProcessor:
    """Test NLP Query service processor"""

    async def test_phase1_select_schemas_success(self, processor, mock_prompt_client):
        """Test successful schema selection (Phase 1)"""
        # Arrange
        question = "Show me customers from California"
        expected_schemas = ["customers"]
        
        mock_response = PromptResponse(
            text=json.dumps(expected_schemas),
            error=None
        )
        
        # Mock flow context
        flow = MagicMock()
        mock_prompt_service = AsyncMock()
        mock_prompt_service.request = AsyncMock(return_value=mock_response)
        flow.side_effect = lambda service_name: mock_prompt_service if service_name == "prompt-request" else AsyncMock()
        
        # Act
        result = await processor.phase1_select_schemas(question, flow)
        
        # Assert
        assert result == expected_schemas
        mock_prompt_service.request.assert_called_once()

    async def test_phase1_select_schemas_prompt_error(self, processor):
        """Test schema selection with prompt service error"""
        # Arrange
        question = "Show me customers"
        error = Error(type="prompt-error", message="Template not found")
        mock_response = PromptResponse(text="", error=error)
        
        # Mock flow context
        flow = MagicMock()
        mock_prompt_service = AsyncMock()
        mock_prompt_service.request = AsyncMock(return_value=mock_response)
        flow.side_effect = lambda service_name: mock_prompt_service if service_name == "prompt-request" else AsyncMock()
        
        # Act & Assert
        with pytest.raises(Exception, match="Prompt service error"):
            await processor.phase1_select_schemas(question, flow)

    async def test_phase2_generate_graphql_success(self, processor):
        """Test successful GraphQL generation (Phase 2)"""
        # Arrange
        question = "Show me customers from California"
        selected_schemas = ["customers"]
        expected_result = {
            "query": "query { customers(where: {state: {eq: \"California\"}}) { id name email state } }",
            "variables": {},
            "confidence": 0.95
        }
        
        mock_response = PromptResponse(
            text=json.dumps(expected_result),
            error=None
        )
        
        # Mock flow context
        flow = MagicMock()
        mock_prompt_service = AsyncMock()
        mock_prompt_service.request = AsyncMock(return_value=mock_response)
        flow.side_effect = lambda service_name: mock_prompt_service if service_name == "prompt-request" else AsyncMock()
        
        # Act
        result = await processor.phase2_generate_graphql(question, selected_schemas, flow)
        
        # Assert
        assert result == expected_result
        mock_prompt_service.request.assert_called_once()

    async def test_phase2_generate_graphql_prompt_error(self, processor):
        """Test GraphQL generation with prompt service error"""
        # Arrange
        question = "Show me customers"
        selected_schemas = ["customers"]
        error = Error(type="prompt-error", message="Generation failed")
        mock_response = PromptResponse(text="", error=error)
        
        # Mock flow context
        flow = MagicMock()
        mock_prompt_service = AsyncMock()
        mock_prompt_service.request = AsyncMock(return_value=mock_response)
        flow.side_effect = lambda service_name: mock_prompt_service if service_name == "prompt-request" else AsyncMock()
        
        # Act & Assert
        with pytest.raises(Exception, match="Prompt service error"):
            await processor.phase2_generate_graphql(question, selected_schemas, flow)

    async def test_on_message_full_flow_success(self, processor):
        """Test complete message processing flow"""
        # Arrange
        request = QuestionToStructuredQueryRequest(
            question="Show me customers from California", 
            max_results=100
        )
        
        msg = MagicMock()
        msg.value.return_value = request
        msg.properties.return_value = {"id": "test-123"}
        
        consumer = MagicMock()
        flow = MagicMock()
        flow_response = AsyncMock()
        flow.return_value = flow_response
        
        # Mock Phase 1 response
        phase1_response = PromptResponse(
            text=json.dumps(["customers"]),
            error=None
        )
        
        # Mock Phase 2 response
        phase2_response = PromptResponse(
            text=json.dumps({
                "query": "query { customers(where: {state: {eq: \"California\"}}) { id name email } }",
                "variables": {},
                "confidence": 0.9
            }),
            error=None
        )
        
        # Mock flow context to return prompt service responses
        mock_prompt_service = AsyncMock()
        mock_prompt_service.request = AsyncMock(
            side_effect=[phase1_response, phase2_response]
        )
        flow.side_effect = lambda service_name: mock_prompt_service if service_name == "prompt-request" else flow_response if service_name == "response" else AsyncMock()
        
        # Act
        await processor.on_message(msg, consumer, flow)
        
        # Assert
        assert mock_prompt_service.request.call_count == 2
        flow_response.send.assert_called_once()
        
        # Verify response structure
        response_call = flow_response.send.call_args
        response = response_call[0][0]  # First argument is the response object
        
        assert isinstance(response, QuestionToStructuredQueryResponse)
        assert response.error is None
        assert "customers" in response.graphql_query
        assert response.detected_schemas == ["customers"]
        assert response.confidence == 0.9

    async def test_on_message_phase1_error(self, processor):
        """Test message processing with Phase 1 failure"""
        # Arrange
        request = QuestionToStructuredQueryRequest(
            question="Show me customers", 
            max_results=100
        )
        
        msg = MagicMock()
        msg.value.return_value = request
        msg.properties.return_value = {"id": "test-123"}
        
        consumer = MagicMock()
        flow = MagicMock()
        flow_response = AsyncMock()
        flow.return_value = flow_response
        
        # Mock Phase 1 error
        phase1_response = PromptResponse(
            text="",
            error=Error(type="template-error", message="Template not found")
        )
        
        processor.client.return_value.request = AsyncMock(return_value=phase1_response)
        
        # Act
        await processor.on_message(msg, consumer, flow)
        
        # Assert
        flow_response.send.assert_called_once()
        
        # Verify error response
        response_call = flow_response.send.call_args
        response = response_call[0][0]
        
        assert isinstance(response, QuestionToStructuredQueryResponse)
        assert response.error is not None
        assert response.error.type == "nlp-query-error"
        assert "Prompt service error" in response.error.message

    async def test_schema_config_loading(self, processor):
        """Test schema configuration loading"""
        # Arrange
        config = {
            "schema": {
                "test_schema": json.dumps({
                    "name": "test_schema",
                    "description": "Test schema", 
                    "fields": [
                        {
                            "name": "id",
                            "type": "string",
                            "primary_key": True,
                            "required": True
                        },
                        {
                            "name": "name", 
                            "type": "string",
                            "description": "User name"
                        }
                    ]
                })
            }
        }
        
        # Act
        await processor.on_schema_config(config, "v1")
        
        # Assert
        assert "test_schema" in processor.schemas
        schema = processor.schemas["test_schema"]
        assert schema.name == "test_schema"
        assert schema.description == "Test schema"
        assert len(schema.fields) == 2
        assert schema.fields[0].name == "id"
        assert schema.fields[0].primary == True
        assert schema.fields[1].name == "name"

    async def test_schema_config_loading_invalid_json(self, processor):
        """Test schema configuration loading with invalid JSON"""
        # Arrange
        config = {
            "schema": {
                "bad_schema": "invalid json{"
            }
        }
        
        # Act
        await processor.on_schema_config(config, "v1")
        
        # Assert - bad schema should be ignored
        assert "bad_schema" not in processor.schemas

    def test_processor_initialization(self, mock_pulsar_client):
        """Test processor initialization with correct specifications"""
        # Act
        processor = Processor(
            taskgroup=MagicMock(),
            pulsar_client=mock_pulsar_client,
            schema_selection_template="custom-schema-select",
            graphql_generation_template="custom-graphql-gen"
        )
        
        # Assert
        assert processor.schema_selection_template == "custom-schema-select"
        assert processor.graphql_generation_template == "custom-graphql-gen"
        assert processor.config_key == "schema"
        assert processor.schemas == {}

    def test_add_args(self):
        """Test command-line argument parsing"""
        import argparse
        
        parser = argparse.ArgumentParser()
        Processor.add_args(parser)
        
        # Test default values
        args = parser.parse_args([])
        assert args.config_type == "schema"
        assert args.schema_selection_template == "schema-selection"
        assert args.graphql_generation_template == "graphql-generation"
        
        # Test custom values
        args = parser.parse_args([
            "--config-type", "custom",
            "--schema-selection-template", "my-selector",
            "--graphql-generation-template", "my-generator"
        ])
        assert args.config_type == "custom"
        assert args.schema_selection_template == "my-selector"
        assert args.graphql_generation_template == "my-generator"


@pytest.mark.unit
class TestNLPQueryHelperFunctions:
    """Test helper functions and data transformations"""
    
    def test_schema_info_formatting(self, sample_schemas):
        """Test schema info formatting for prompts"""
        # This would test any helper functions for formatting schema data
        # Currently the formatting is inline, but good to test if extracted
        
        customers_schema = sample_schemas["customers"]
        expected_fields = ["id", "name", "email", "state"]
        
        actual_fields = [f.name for f in customers_schema.fields]
        assert actual_fields == expected_fields
        
        # Test primary key detection
        primary_fields = [f.name for f in customers_schema.fields if f.primary]
        assert primary_fields == ["id"]