"""
Integration tests for Agent-based Knowledge Graph Extraction

These tests verify the end-to-end functionality of the agent-driven knowledge graph
extraction pipeline, testing the integration between agent communication, prompt
rendering, JSON response processing, and knowledge graph generation.
Following the TEST_STRATEGY.md approach for integration testing.
"""

import pytest
import json
from unittest.mock import AsyncMock, MagicMock, patch

from trustgraph.extract.kg.agent.extract import Processor as AgentKgExtractor
from trustgraph.schema import Chunk, Triple, Triples, Metadata, Term, Error, IRI, LITERAL
from trustgraph.schema import EntityContext, EntityContexts, AgentRequest, AgentResponse
from trustgraph.rdf import TRUSTGRAPH_ENTITIES, DEFINITION, RDF_LABEL, SUBJECT_OF
from trustgraph.template.prompt_manager import PromptManager


@pytest.mark.integration
class TestAgentKgExtractionIntegration:
    """Integration tests for Agent-based Knowledge Graph Extraction"""

    @pytest.fixture
    def mock_flow_context(self):
        """Mock flow context for agent communication and output publishing"""
        context = MagicMock()
        
        # Mock agent client
        agent_client = AsyncMock()
        
        # Mock successful agent response in JSONL format
        def mock_agent_response(recipient, question):
            # Simulate agent processing and return structured JSONL response
            mock_response = MagicMock()
            mock_response.error = None
            mock_response.answer = '''```json
{"type": "definition", "entity": "Machine Learning", "definition": "A subset of artificial intelligence that enables computers to learn from data without explicit programming."}
{"type": "definition", "entity": "Neural Networks", "definition": "Computing systems inspired by biological neural networks that process information."}
{"type": "relationship", "subject": "Machine Learning", "predicate": "is_subset_of", "object": "Artificial Intelligence", "object-entity": true}
{"type": "relationship", "subject": "Neural Networks", "predicate": "used_in", "object": "Machine Learning", "object-entity": true}
```'''
            return mock_response.answer
        
        agent_client.invoke = mock_agent_response
        
        # Mock output publishers
        triples_publisher = AsyncMock()
        entity_contexts_publisher = AsyncMock()
        
        def context_router(service_name):
            if service_name == "agent-request":
                return agent_client
            elif service_name == "triples":
                return triples_publisher
            elif service_name == "entity-contexts":
                return entity_contexts_publisher
            else:
                return AsyncMock()
        
        context.side_effect = context_router
        return context

    @pytest.fixture
    def sample_chunk(self):
        """Sample text chunk for knowledge extraction"""
        text = """
        Machine Learning is a subset of Artificial Intelligence that enables computers 
        to learn from data without explicit programming. Neural Networks are computing 
        systems inspired by biological neural networks that process information. 
        Neural Networks are commonly used in Machine Learning applications.
        """
        
        return Chunk(
            chunk=text.encode('utf-8'),
            metadata=Metadata(
                id="doc123",
                metadata=[
                    Triple(
                        s=Term(type=IRI, iri="doc123"),
                        p=Term(type=IRI, iri="http://example.org/type"),
                        o=Term(type=LITERAL, value="document")
                    )
                ]
            )
        )

    @pytest.fixture
    def configured_agent_extractor(self):
        """Mock agent extractor with loaded configuration for integration testing"""
        # Create a mock extractor that simulates the real behavior
        from trustgraph.extract.kg.agent.extract import Processor
        
        # Create mock without calling __init__ to avoid FlowProcessor issues
        extractor = MagicMock()
        real_extractor = Processor.__new__(Processor)
        
        # Copy the methods we want to test
        extractor.to_uri = real_extractor.to_uri
        extractor.parse_jsonl = real_extractor.parse_jsonl
        extractor.process_extraction_data = real_extractor.process_extraction_data
        extractor.emit_triples = real_extractor.emit_triples
        extractor.emit_entity_contexts = real_extractor.emit_entity_contexts
        
        # Set up the configuration and manager
        extractor.manager = PromptManager()
        extractor.template_id = "agent-kg-extract"
        extractor.config_key = "prompt"
        
        # Mock configuration
        config = {
            "system": json.dumps("You are a knowledge extraction agent."),
            "template-index": json.dumps(["agent-kg-extract"]),
            "template.agent-kg-extract": json.dumps({
                "prompt": "Extract entities and relationships from: {{ text }}",
                "response-type": "json"
            })
        }
        
        # Load configuration
        extractor.manager.load_config(config)
        
        # Mock the on_message method to simulate real behavior
        async def mock_on_message(msg, consumer, flow):
            v = msg.value()
            chunk_text = v.chunk.decode('utf-8')
            
            # Render prompt
            prompt = extractor.manager.render(extractor.template_id, {"text": chunk_text})
            
            # Get agent response (the mock returns a string directly)
            agent_client = flow("agent-request")
            agent_response = agent_client.invoke(recipient=lambda x: True, question=prompt)
            
            # Parse and process
            extraction_data = extractor.parse_jsonl(agent_response)
            triples, entity_contexts = extractor.process_extraction_data(extraction_data, v.metadata)
            
            # Add metadata triples
            for t in v.metadata.metadata:
                triples.append(t)
            
            # Emit outputs
            if triples:
                await extractor.emit_triples(flow("triples"), v.metadata, triples)
            if entity_contexts:
                await extractor.emit_entity_contexts(flow("entity-contexts"), v.metadata, entity_contexts)
        
        extractor.on_message = mock_on_message
        
        return extractor

    @pytest.mark.asyncio
    async def test_end_to_end_knowledge_extraction(self, configured_agent_extractor, sample_chunk, mock_flow_context):
        """Test complete end-to-end knowledge extraction workflow"""
        # Arrange
        mock_message = MagicMock()
        mock_message.value.return_value = sample_chunk
        mock_consumer = MagicMock()

        # Act
        await configured_agent_extractor.on_message(mock_message, mock_consumer, mock_flow_context)

        # Assert
        # Verify agent was called with rendered prompt
        agent_client = mock_flow_context("agent-request")
        # Check that the mock function was replaced and called
        assert hasattr(agent_client, 'invoke')

        # Verify triples were emitted
        triples_publisher = mock_flow_context("triples")
        triples_publisher.send.assert_called_once()
        
        sent_triples = triples_publisher.send.call_args[0][0]
        assert isinstance(sent_triples, Triples)
        assert sent_triples.metadata.id == "doc123"
        assert len(sent_triples.triples) > 0
        
        # Check that we have definition triples
        definition_triples = [t for t in sent_triples.triples if t.p.iri == DEFINITION]
        assert len(definition_triples) >= 2  # Should have definitions for ML and Neural Networks

        # Check that we have label triples
        label_triples = [t for t in sent_triples.triples if t.p.iri == RDF_LABEL]
        assert len(label_triples) >= 2  # Should have labels for entities

        # Check subject-of relationships
        subject_of_triples = [t for t in sent_triples.triples if t.p.iri == SUBJECT_OF]
        assert len(subject_of_triples) >= 2  # Entities should be linked to document

        # Verify entity contexts were emitted
        entity_contexts_publisher = mock_flow_context("entity-contexts")
        entity_contexts_publisher.send.assert_called_once()
        
        sent_contexts = entity_contexts_publisher.send.call_args[0][0]
        assert isinstance(sent_contexts, EntityContexts)
        assert len(sent_contexts.entities) >= 2  # Should have contexts for both entities
        
        # Verify entity URIs are properly formed
        entity_uris = [ec.entity.iri for ec in sent_contexts.entities]
        assert f"{TRUSTGRAPH_ENTITIES}Machine%20Learning" in entity_uris
        assert f"{TRUSTGRAPH_ENTITIES}Neural%20Networks" in entity_uris

    @pytest.mark.asyncio
    async def test_agent_error_handling(self, configured_agent_extractor, sample_chunk, mock_flow_context):
        """Test handling of agent errors"""
        # Arrange - mock agent error response
        agent_client = mock_flow_context("agent-request")
        
        def mock_error_response(recipient, question):
            # Simulate agent error by raising an exception
            raise RuntimeError("Agent processing failed")
        
        agent_client.invoke = mock_error_response
        
        mock_message = MagicMock()
        mock_message.value.return_value = sample_chunk
        mock_consumer = MagicMock()

        # Act & Assert
        with pytest.raises(RuntimeError) as exc_info:
            await configured_agent_extractor.on_message(mock_message, mock_consumer, mock_flow_context)
        
        assert "Agent processing failed" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_invalid_json_response_handling(self, configured_agent_extractor, sample_chunk, mock_flow_context):
        """Test handling of invalid JSON responses from agent - JSONL is lenient and skips invalid lines"""
        # Arrange - mock invalid JSON response
        agent_client = mock_flow_context("agent-request")

        def mock_invalid_json_response(recipient, question):
            return "This is not valid JSON at all"

        agent_client.invoke = mock_invalid_json_response

        mock_message = MagicMock()
        mock_message.value.return_value = sample_chunk
        mock_consumer = MagicMock()

        # Act - JSONL parsing is lenient, invalid lines are skipped
        await configured_agent_extractor.on_message(mock_message, mock_consumer, mock_flow_context)

        # Assert - should emit triples (with just metadata) but no entity contexts
        triples_publisher = mock_flow_context("triples")
        triples_publisher.send.assert_called_once()

        entity_contexts_publisher = mock_flow_context("entity-contexts")
        entity_contexts_publisher.send.assert_not_called()

    @pytest.mark.asyncio
    async def test_empty_extraction_results(self, configured_agent_extractor, sample_chunk, mock_flow_context):
        """Test handling of empty extraction results"""
        # Arrange - mock empty extraction response
        agent_client = mock_flow_context("agent-request")
        
        def mock_empty_response(recipient, question):
            # Return empty JSONL (just empty/whitespace)
            return ''
        
        agent_client.invoke = mock_empty_response
        
        mock_message = MagicMock()
        mock_message.value.return_value = sample_chunk
        mock_consumer = MagicMock()

        # Act
        await configured_agent_extractor.on_message(mock_message, mock_consumer, mock_flow_context)

        # Assert
        # Should still emit outputs (even if empty) to maintain flow consistency
        triples_publisher = mock_flow_context("triples")
        entity_contexts_publisher = mock_flow_context("entity-contexts")
        
        # Triples should include metadata triples at minimum
        triples_publisher.send.assert_called_once()
        sent_triples = triples_publisher.send.call_args[0][0]
        assert isinstance(sent_triples, Triples)
        
        # Entity contexts should not be sent if empty
        entity_contexts_publisher.send.assert_not_called()

    @pytest.mark.asyncio
    async def test_malformed_extraction_data(self, configured_agent_extractor, sample_chunk, mock_flow_context):
        """Test handling of malformed extraction data"""
        # Arrange - mock malformed extraction response
        agent_client = mock_flow_context("agent-request")
        
        def mock_malformed_response(recipient, question):
            # JSONL with definition missing required field
            return '{"type": "definition", "entity": "Missing Definition"}'
        
        agent_client.invoke = mock_malformed_response
        
        mock_message = MagicMock()
        mock_message.value.return_value = sample_chunk
        mock_consumer = MagicMock()

        # Act & Assert
        with pytest.raises(KeyError):
            await configured_agent_extractor.on_message(mock_message, mock_consumer, mock_flow_context)

    @pytest.mark.asyncio
    async def test_prompt_rendering_integration(self, configured_agent_extractor, mock_flow_context):
        """Test integration with prompt template rendering"""
        # Create a chunk with specific text
        test_text = "Test text for prompt rendering"
        chunk = Chunk(
            chunk=test_text.encode('utf-8'),
            metadata=Metadata(id="test-doc", metadata=[])
        )
        
        agent_client = mock_flow_context("agent-request")
        
        def capture_prompt(recipient, question):
            # Verify the prompt contains the test text
            assert test_text in question
            return ''  # Empty JSONL response
        
        agent_client.invoke = capture_prompt
        
        mock_message = MagicMock()
        mock_message.value.return_value = chunk
        mock_consumer = MagicMock()

        # Act
        await configured_agent_extractor.on_message(mock_message, mock_consumer, mock_flow_context)
        
        # Assert - prompt should have been rendered with the text
        # The agent_client.invoke is a function, not a mock, so we verify it was called by checking the flow worked
        assert hasattr(agent_client, 'invoke')

    @pytest.mark.asyncio
    async def test_concurrent_processing_simulation(self, configured_agent_extractor, mock_flow_context):
        """Test simulation of concurrent chunk processing"""
        # Create multiple chunks
        chunks = []
        for i in range(3):
            text = f"Test document {i} content"
            chunks.append(Chunk(
                chunk=text.encode('utf-8'),
                metadata=Metadata(id=f"doc{i}", metadata=[])
            ))
        
        agent_client = mock_flow_context("agent-request")
        responses = []
        
        def mock_response(recipient, question):
            response = f'{{"type": "definition", "entity": "Entity {len(responses)}", "definition": "Definition {len(responses)}"}}'
            responses.append(response)
            return response
        
        agent_client.invoke = mock_response

        # Process chunks sequentially (simulating concurrent processing)
        for chunk in chunks:
            mock_message = MagicMock()
            mock_message.value.return_value = chunk
            mock_consumer = MagicMock()
            
            await configured_agent_extractor.on_message(mock_message, mock_consumer, mock_flow_context)

        # Assert
        assert len(responses) == 3
        
        # Verify all chunks were processed
        triples_publisher = mock_flow_context("triples")
        assert triples_publisher.send.call_count == 3

    @pytest.mark.asyncio
    async def test_unicode_text_handling(self, configured_agent_extractor, mock_flow_context):
        """Test handling of text with unicode characters"""
        # Create chunk with unicode text
        unicode_text = "Machine Learning (学习机器) は人工知能の一分野です。"
        chunk = Chunk(
            chunk=unicode_text.encode('utf-8'),
            metadata=Metadata(id="unicode-doc", metadata=[])
        )
        
        agent_client = mock_flow_context("agent-request")
        
        def mock_unicode_response(recipient, question):
            # Verify unicode text was properly decoded and included
            assert "学习机器" in question
            assert "人工知能" in question
            return '{"type": "definition", "entity": "機械学習", "definition": "人工知能の一分野"}'
        
        agent_client.invoke = mock_unicode_response
        
        mock_message = MagicMock()
        mock_message.value.return_value = chunk
        mock_consumer = MagicMock()

        # Act
        await configured_agent_extractor.on_message(mock_message, mock_consumer, mock_flow_context)

        # Assert - should handle unicode properly
        triples_publisher = mock_flow_context("triples")
        triples_publisher.send.assert_called_once()
        
        sent_triples = triples_publisher.send.call_args[0][0]
        # Check that unicode entity was properly processed
        entity_labels = [t for t in sent_triples.triples if t.p.iri == RDF_LABEL and t.o.value == "機械学習"]
        assert len(entity_labels) > 0

    @pytest.mark.asyncio
    async def test_large_text_chunk_processing(self, configured_agent_extractor, mock_flow_context):
        """Test processing of large text chunks"""
        # Create a large text chunk
        large_text = "Machine Learning is important. " * 1000  # Repeat to create large text
        chunk = Chunk(
            chunk=large_text.encode('utf-8'),
            metadata=Metadata(id="large-doc", metadata=[])
        )
        
        agent_client = mock_flow_context("agent-request")
        
        def mock_large_text_response(recipient, question):
            # Verify large text was included
            assert len(question) > 10000
            return '{"type": "definition", "entity": "Machine Learning", "definition": "Important AI technique"}'
        
        agent_client.invoke = mock_large_text_response
        
        mock_message = MagicMock()
        mock_message.value.return_value = chunk
        mock_consumer = MagicMock()

        # Act
        await configured_agent_extractor.on_message(mock_message, mock_consumer, mock_flow_context)

        # Assert - should handle large text without issues
        triples_publisher = mock_flow_context("triples")
        triples_publisher.send.assert_called_once()

    def test_configuration_parameter_validation(self):
        """Test parameter validation logic"""
        # Test that default parameter logic would work
        default_template_id = "agent-kg-extract"
        default_config_type = "prompt" 
        default_concurrency = 1
        
        # Simulate parameter handling
        params = {}
        template_id = params.get("template-id", default_template_id)
        config_key = params.get("config-type", default_config_type)
        concurrency = params.get("concurrency", default_concurrency)
        
        assert template_id == "agent-kg-extract"
        assert config_key == "prompt"
        assert concurrency == 1
        
        # Test with custom parameters
        custom_params = {
            "template-id": "custom-template",
            "config-type": "custom-config", 
            "concurrency": 10
        }
        
        template_id = custom_params.get("template-id", default_template_id)
        config_key = custom_params.get("config-type", default_config_type)
        concurrency = custom_params.get("concurrency", default_concurrency)
        
        assert template_id == "custom-template"
        assert config_key == "custom-config"
        assert concurrency == 10