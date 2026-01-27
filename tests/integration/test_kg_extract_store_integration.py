"""
Integration tests for Knowledge Graph Extract → Store Pipeline

These tests verify the end-to-end functionality of the knowledge graph extraction
and storage pipeline, testing text-to-graph transformation, entity extraction,
relationship extraction, and graph database storage.
Following the TEST_STRATEGY.md approach for integration testing.
"""

import pytest
import json
import urllib.parse
from unittest.mock import AsyncMock, MagicMock, patch

from trustgraph.extract.kg.definitions.extract import Processor as DefinitionsProcessor
from trustgraph.extract.kg.relationships.extract import Processor as RelationshipsProcessor
from trustgraph.storage.knowledge.store import Processor as KnowledgeStoreProcessor
from trustgraph.schema import Chunk, Triple, Triples, Metadata, Term, Error, IRI, LITERAL
from trustgraph.schema import EntityContext, EntityContexts, GraphEmbeddings
from trustgraph.rdf import TRUSTGRAPH_ENTITIES, DEFINITION, RDF_LABEL, SUBJECT_OF


@pytest.mark.integration
class TestKnowledgeGraphPipelineIntegration:
    """Integration tests for Knowledge Graph Extract → Store Pipeline"""

    @pytest.fixture
    def mock_flow_context(self):
        """Mock flow context for service coordination"""
        context = MagicMock()
        
        # Mock prompt client for definitions extraction
        prompt_client = AsyncMock()
        prompt_client.extract_definitions.return_value = [
            {
                "entity": "Machine Learning",
                "definition": "A subset of artificial intelligence that enables computers to learn from data without explicit programming."
            },
            {
                "entity": "Neural Networks",
                "definition": "Computing systems inspired by biological neural networks that process information."
            }
        ]
        
        # Mock prompt client for relationships extraction
        prompt_client.extract_relationships.return_value = [
            {
                "subject": "Machine Learning",
                "predicate": "is_subset_of",
                "object": "Artificial Intelligence",
                "object-entity": True
            },
            {
                "subject": "Neural Networks",
                "predicate": "is_used_in",
                "object": "Machine Learning",
                "object-entity": True
            }
        ]
        
        # Mock producers for output streams
        triples_producer = AsyncMock()
        entity_contexts_producer = AsyncMock()
        
        # Configure context routing
        def context_router(service_name):
            if service_name == "prompt-request":
                return prompt_client
            elif service_name == "triples":
                return triples_producer
            elif service_name == "entity-contexts":
                return entity_contexts_producer
            else:
                return AsyncMock()
        
        context.side_effect = context_router
        return context

    @pytest.fixture
    def mock_cassandra_store(self):
        """Mock Cassandra knowledge table store"""
        store = AsyncMock()
        store.add_triples.return_value = None
        store.add_graph_embeddings.return_value = None
        return store

    @pytest.fixture
    def sample_chunk(self):
        """Sample text chunk for processing"""
        return Chunk(
            metadata=Metadata(
                id="doc-123",
                user="test_user",
                collection="test_collection",
                metadata=[]
            ),
            chunk=b"Machine Learning is a subset of Artificial Intelligence. Neural Networks are used in Machine Learning to process complex patterns."
        )

    @pytest.fixture
    def sample_definitions_response(self):
        """Sample definitions extraction response"""
        return [
            {
                "entity": "Machine Learning",
                "definition": "A subset of artificial intelligence that enables computers to learn from data."
            },
            {
                "entity": "Artificial Intelligence",
                "definition": "The simulation of human intelligence in machines."
            },
            {
                "entity": "Neural Networks",
                "definition": "Computing systems inspired by biological neural networks."
            }
        ]

    @pytest.fixture
    def sample_relationships_response(self):
        """Sample relationships extraction response"""
        return [
            {
                "subject": "Machine Learning",
                "predicate": "is_subset_of",
                "object": "Artificial Intelligence",
                "object-entity": True
            },
            {
                "subject": "Neural Networks",
                "predicate": "is_used_in",
                "object": "Machine Learning",
                "object-entity": True
            },
            {
                "subject": "Machine Learning",
                "predicate": "processes",
                "object": "data patterns",
                "object-entity": False
            }
        ]

    @pytest.fixture
    def definitions_processor(self):
        """Create definitions processor with minimal configuration"""
        processor = MagicMock()
        processor.to_uri = DefinitionsProcessor.to_uri.__get__(processor, DefinitionsProcessor)
        processor.emit_triples = DefinitionsProcessor.emit_triples.__get__(processor, DefinitionsProcessor)
        processor.emit_ecs = DefinitionsProcessor.emit_ecs.__get__(processor, DefinitionsProcessor)
        processor.on_message = DefinitionsProcessor.on_message.__get__(processor, DefinitionsProcessor)
        return processor

    @pytest.fixture
    def relationships_processor(self):
        """Create relationships processor with minimal configuration"""
        processor = MagicMock()
        processor.to_uri = RelationshipsProcessor.to_uri.__get__(processor, RelationshipsProcessor)
        processor.emit_triples = RelationshipsProcessor.emit_triples.__get__(processor, RelationshipsProcessor)
        processor.on_message = RelationshipsProcessor.on_message.__get__(processor, RelationshipsProcessor)
        return processor

    @pytest.mark.asyncio
    async def test_definitions_extraction_pipeline(self, definitions_processor, mock_flow_context, sample_chunk):
        """Test definitions extraction from text chunk to graph triples"""
        # Arrange
        mock_msg = MagicMock()
        mock_msg.value.return_value = sample_chunk
        mock_consumer = MagicMock()

        # Act
        await definitions_processor.on_message(mock_msg, mock_consumer, mock_flow_context)

        # Assert
        # Verify prompt client was called for definitions extraction
        prompt_client = mock_flow_context("prompt-request")
        prompt_client.extract_definitions.assert_called_once()
        call_args = prompt_client.extract_definitions.call_args
        assert "Machine Learning" in call_args.kwargs['text']
        assert "Neural Networks" in call_args.kwargs['text']

        # Verify triples producer was called
        triples_producer = mock_flow_context("triples")
        triples_producer.send.assert_called_once()
        
        # Verify entity contexts producer was called
        entity_contexts_producer = mock_flow_context("entity-contexts")
        entity_contexts_producer.send.assert_called_once()

    @pytest.mark.asyncio
    async def test_relationships_extraction_pipeline(self, relationships_processor, mock_flow_context, sample_chunk):
        """Test relationships extraction from text chunk to graph triples"""
        # Arrange
        mock_msg = MagicMock()
        mock_msg.value.return_value = sample_chunk
        mock_consumer = MagicMock()

        # Act
        await relationships_processor.on_message(mock_msg, mock_consumer, mock_flow_context)

        # Assert
        # Verify prompt client was called for relationships extraction
        prompt_client = mock_flow_context("prompt-request")
        prompt_client.extract_relationships.assert_called_once()
        call_args = prompt_client.extract_relationships.call_args
        assert "Machine Learning" in call_args.kwargs['text']

        # Verify triples producer was called
        triples_producer = mock_flow_context("triples")
        triples_producer.send.assert_called_once()

    @pytest.mark.asyncio
    async def test_uri_generation_consistency(self, definitions_processor, relationships_processor):
        """Test URI generation consistency between processors"""
        # Arrange
        test_entities = [
            "Machine Learning",
            "Artificial Intelligence",
            "Neural Networks",
            "Deep Learning",
            "Natural Language Processing"
        ]

        # Act & Assert
        for entity in test_entities:
            def_uri = definitions_processor.to_uri(entity)
            rel_uri = relationships_processor.to_uri(entity)
            
            # URIs should be identical between processors
            assert def_uri == rel_uri
            
            # URI should be properly encoded
            assert def_uri.startswith(TRUSTGRAPH_ENTITIES)
            assert " " not in def_uri
            assert def_uri.endswith(urllib.parse.quote(entity.replace(" ", "-").lower().encode("utf-8")))

    @pytest.mark.asyncio
    async def test_definitions_triple_generation(self, definitions_processor, sample_definitions_response):
        """Test triple generation from definitions extraction"""
        # Arrange
        metadata = Metadata(
            id="test-doc",
            user="test_user",
            collection="test_collection",
            metadata=[]
        )

        # Act
        triples = []
        entities = []
        
        for defn in sample_definitions_response:
            s = defn["entity"]
            o = defn["definition"]
            
            if s and o:
                s_uri = definitions_processor.to_uri(s)
                s_term = Term(type=IRI, iri=str(s_uri))
                o_term = Term(type=LITERAL, value=str(o))

                # Generate triples as the processor would
                triples.append(Triple(
                    s=s_term,
                    p=Term(type=IRI, iri=RDF_LABEL),
                    o=Term(type=LITERAL, value=s)
                ))

                triples.append(Triple(
                    s=s_term,
                    p=Term(type=IRI, iri=DEFINITION),
                    o=o_term
                ))

                entities.append(EntityContext(
                    entity=s_term,
                    context=defn["definition"]
                ))

        # Assert
        assert len(triples) == 6  # 2 triples per entity * 3 entities
        assert len(entities) == 3  # 1 entity context per entity
        
        # Verify triple structure
        label_triples = [t for t in triples if t.p.iri == RDF_LABEL]
        definition_triples = [t for t in triples if t.p.iri == DEFINITION]

        assert len(label_triples) == 3
        assert len(definition_triples) == 3

        # Verify entity contexts
        for entity in entities:
            assert entity.entity.type == IRI
            assert entity.entity.iri.startswith(TRUSTGRAPH_ENTITIES)
            assert len(entity.context) > 0

    @pytest.mark.asyncio
    async def test_relationships_triple_generation(self, relationships_processor, sample_relationships_response):
        """Test triple generation from relationships extraction"""
        # Arrange
        metadata = Metadata(
            id="test-doc",
            user="test_user",
            collection="test_collection",
            metadata=[]
        )

        # Act
        triples = []
        
        for rel in sample_relationships_response:
            s = rel["subject"]
            p = rel["predicate"]
            o = rel["object"]

            if s and p and o:
                s_uri = relationships_processor.to_uri(s)
                s_term = Term(type=IRI, iri=str(s_uri))

                p_uri = relationships_processor.to_uri(p)
                p_term = Term(type=IRI, iri=str(p_uri))

                if rel["object-entity"]:
                    o_uri = relationships_processor.to_uri(o)
                    o_term = Term(type=IRI, iri=str(o_uri))
                else:
                    o_term = Term(type=LITERAL, value=str(o))

                # Main relationship triple
                triples.append(Triple(s=s_term, p=p_term, o=o_term))

                # Label triples
                triples.append(Triple(
                    s=s_term,
                    p=Term(type=IRI, iri=RDF_LABEL),
                    o=Term(type=LITERAL, value=str(s))
                ))

                triples.append(Triple(
                    s=p_term,
                    p=Term(type=IRI, iri=RDF_LABEL),
                    o=Term(type=LITERAL, value=str(p))
                ))

                if rel["object-entity"]:
                    triples.append(Triple(
                        s=o_term,
                        p=Term(type=IRI, iri=RDF_LABEL),
                        o=Term(type=LITERAL, value=str(o))
                    ))

        # Assert
        assert len(triples) > 0
        
        # Verify relationship triples exist
        relationship_triples = [t for t in triples if t.p.iri.endswith("is_subset_of") or t.p.iri.endswith("is_used_in")]
        assert len(relationship_triples) >= 2

        # Verify label triples
        label_triples = [t for t in triples if t.p.iri == RDF_LABEL]
        assert len(label_triples) > 0

    @pytest.mark.asyncio
    async def test_knowledge_store_triples_storage(self, mock_cassandra_store):
        """Test knowledge store triples storage integration"""
        # Arrange
        processor = MagicMock()
        processor.table_store = mock_cassandra_store
        processor.on_triples = KnowledgeStoreProcessor.on_triples.__get__(processor, KnowledgeStoreProcessor)
        
        sample_triples = Triples(
            metadata=Metadata(
                id="test-doc",
                user="test_user",
                collection="test_collection",
                metadata=[]
            ),
            triples=[
                Triple(
                    s=Term(type=IRI, iri="http://trustgraph.ai/e/machine-learning"),
                    p=Term(type=IRI, iri=DEFINITION),
                    o=Term(type=LITERAL, value="A subset of AI")
                )
            ]
        )
        
        mock_msg = MagicMock()
        mock_msg.value.return_value = sample_triples

        # Act
        await processor.on_triples(mock_msg, None, None)

        # Assert
        mock_cassandra_store.add_triples.assert_called_once_with(sample_triples)

    @pytest.mark.asyncio
    async def test_knowledge_store_graph_embeddings_storage(self, mock_cassandra_store):
        """Test knowledge store graph embeddings storage integration"""
        # Arrange
        processor = MagicMock()
        processor.table_store = mock_cassandra_store
        processor.on_graph_embeddings = KnowledgeStoreProcessor.on_graph_embeddings.__get__(processor, KnowledgeStoreProcessor)
        
        sample_embeddings = GraphEmbeddings(
            metadata=Metadata(
                id="test-doc",
                user="test_user",
                collection="test_collection",
                metadata=[]
            ),
            entities=[]
        )
        
        mock_msg = MagicMock()
        mock_msg.value.return_value = sample_embeddings

        # Act
        await processor.on_graph_embeddings(mock_msg, None, None)

        # Assert
        mock_cassandra_store.add_graph_embeddings.assert_called_once_with(sample_embeddings)

    @pytest.mark.asyncio
    async def test_end_to_end_pipeline_coordination(self, definitions_processor, relationships_processor, 
                                                   mock_flow_context, sample_chunk):
        """Test end-to-end pipeline coordination from chunk to storage"""
        # Arrange
        mock_msg = MagicMock()
        mock_msg.value.return_value = sample_chunk
        mock_consumer = MagicMock()

        # Act - Process through definitions extractor
        await definitions_processor.on_message(mock_msg, mock_consumer, mock_flow_context)
        
        # Act - Process through relationships extractor
        await relationships_processor.on_message(mock_msg, mock_consumer, mock_flow_context)

        # Assert
        # Verify both extractors called prompt service
        prompt_client = mock_flow_context("prompt-request")
        prompt_client.extract_definitions.assert_called_once()
        prompt_client.extract_relationships.assert_called_once()
        
        # Verify triples were produced from both extractors
        triples_producer = mock_flow_context("triples")
        assert triples_producer.send.call_count == 2  # One from each extractor
        
        # Verify entity contexts were produced from definitions extractor
        entity_contexts_producer = mock_flow_context("entity-contexts")
        entity_contexts_producer.send.assert_called_once()

    @pytest.mark.asyncio
    async def test_error_handling_in_definitions_extraction(self, definitions_processor, mock_flow_context, sample_chunk):
        """Test error handling in definitions extraction"""
        # Arrange
        mock_flow_context("prompt-request").extract_definitions.side_effect = Exception("Prompt service unavailable")
        
        mock_msg = MagicMock()
        mock_msg.value.return_value = sample_chunk
        mock_consumer = MagicMock()

        # Act & Assert
        # Should not raise exception, but should handle it gracefully
        await definitions_processor.on_message(mock_msg, mock_consumer, mock_flow_context)
        
        # Verify prompt was attempted
        prompt_client = mock_flow_context("prompt-request")
        prompt_client.extract_definitions.assert_called_once()

    @pytest.mark.asyncio
    async def test_error_handling_in_relationships_extraction(self, relationships_processor, mock_flow_context, sample_chunk):
        """Test error handling in relationships extraction"""
        # Arrange
        mock_flow_context("prompt-request").extract_relationships.side_effect = Exception("Prompt service unavailable")
        
        mock_msg = MagicMock()
        mock_msg.value.return_value = sample_chunk
        mock_consumer = MagicMock()

        # Act & Assert
        # Should not raise exception, but should handle it gracefully
        await relationships_processor.on_message(mock_msg, mock_consumer, mock_flow_context)
        
        # Verify prompt was attempted
        prompt_client = mock_flow_context("prompt-request")
        prompt_client.extract_relationships.assert_called_once()

    @pytest.mark.asyncio
    async def test_empty_extraction_results_handling(self, definitions_processor, mock_flow_context, sample_chunk):
        """Test handling of empty extraction results"""
        # Arrange
        mock_flow_context("prompt-request").extract_definitions.return_value = []
        
        mock_msg = MagicMock()
        mock_msg.value.return_value = sample_chunk
        mock_consumer = MagicMock()

        # Act
        await definitions_processor.on_message(mock_msg, mock_consumer, mock_flow_context)

        # Assert
        # Should still call producers but with empty results
        triples_producer = mock_flow_context("triples")
        entity_contexts_producer = mock_flow_context("entity-contexts")
        
        triples_producer.send.assert_called_once()
        entity_contexts_producer.send.assert_called_once()

    @pytest.mark.asyncio
    async def test_invalid_extraction_format_handling(self, definitions_processor, mock_flow_context, sample_chunk):
        """Test handling of invalid extraction response format"""
        # Arrange
        mock_flow_context("prompt-request").extract_definitions.return_value = "invalid format"  # Should be list
        
        mock_msg = MagicMock()
        mock_msg.value.return_value = sample_chunk
        mock_consumer = MagicMock()

        # Act & Assert
        # Should handle invalid format gracefully
        await definitions_processor.on_message(mock_msg, mock_consumer, mock_flow_context)
        
        # Verify prompt was attempted
        prompt_client = mock_flow_context("prompt-request")
        prompt_client.extract_definitions.assert_called_once()

    @pytest.mark.asyncio
    async def test_entity_filtering_and_validation(self, definitions_processor, mock_flow_context):
        """Test entity filtering and validation in extraction"""
        # Arrange
        mock_flow_context("prompt-request").extract_definitions.return_value = [
            {"entity": "Valid Entity", "definition": "Valid definition"},
            {"entity": "", "definition": "Empty entity"},  # Should be filtered
            {"entity": "Valid Entity 2", "definition": ""},  # Should be filtered
            {"entity": None, "definition": "None entity"},  # Should be filtered
            {"entity": "Valid Entity 3", "definition": None},  # Should be filtered
        ]
        
        sample_chunk = Chunk(
            metadata=Metadata(id="test", user="user", collection="collection", metadata=[]),
            chunk=b"Test chunk"
        )
        
        mock_msg = MagicMock()
        mock_msg.value.return_value = sample_chunk
        mock_consumer = MagicMock()

        # Act
        await definitions_processor.on_message(mock_msg, mock_consumer, mock_flow_context)

        # Assert
        # Should only process valid entities
        triples_producer = mock_flow_context("triples")
        entity_contexts_producer = mock_flow_context("entity-contexts")
        
        triples_producer.send.assert_called_once()
        entity_contexts_producer.send.assert_called_once()

    @pytest.mark.asyncio
    @pytest.mark.slow
    async def test_large_batch_processing_performance(self, definitions_processor, relationships_processor, 
                                                     mock_flow_context):
        """Test performance with large batch of chunks"""
        # Arrange
        large_chunk_batch = [
            Chunk(
                metadata=Metadata(id=f"doc-{i}", user="user", collection="collection", metadata=[]),
                chunk=f"Document {i} contains machine learning and AI content.".encode("utf-8")
            )
            for i in range(100)  # Large batch
        ]
        
        mock_consumer = MagicMock()

        # Act
        import time
        start_time = time.time()
        
        for chunk in large_chunk_batch:
            mock_msg = MagicMock()
            mock_msg.value.return_value = chunk
            
            # Process through both extractors
            await definitions_processor.on_message(mock_msg, mock_consumer, mock_flow_context)
            await relationships_processor.on_message(mock_msg, mock_consumer, mock_flow_context)
        
        end_time = time.time()
        execution_time = end_time - start_time

        # Assert
        assert execution_time < 30.0  # Should complete within reasonable time
        
        # Verify all chunks were processed
        prompt_client = mock_flow_context("prompt-request")
        assert prompt_client.extract_definitions.call_count == 100
        assert prompt_client.extract_relationships.call_count == 100

    @pytest.mark.asyncio
    async def test_metadata_propagation_through_pipeline(self, definitions_processor, mock_flow_context):
        """Test metadata propagation through the pipeline"""
        # Arrange
        original_metadata = Metadata(
            id="test-doc-123",
            user="test_user",
            collection="test_collection",
            metadata=[
                Triple(
                    s=Term(type=IRI, iri="doc:test"),
                    p=Term(type=IRI, iri="dc:title"),
                    o=Term(type=LITERAL, value="Test Document")
                )
            ]
        )
        
        sample_chunk = Chunk(
            metadata=original_metadata,
            chunk=b"Test content for metadata propagation"
        )
        
        mock_msg = MagicMock()
        mock_msg.value.return_value = sample_chunk
        mock_consumer = MagicMock()

        # Act
        await definitions_processor.on_message(mock_msg, mock_consumer, mock_flow_context)

        # Assert
        # Verify metadata was propagated to output
        triples_producer = mock_flow_context("triples")
        entity_contexts_producer = mock_flow_context("entity-contexts")
        
        triples_producer.send.assert_called_once()
        entity_contexts_producer.send.assert_called_once()
        
        # Check that metadata was included in the calls
        triples_call = triples_producer.send.call_args[0][0]
        entity_contexts_call = entity_contexts_producer.send.call_args[0][0]
        
        assert triples_call.metadata.id == "test-doc-123"
        assert triples_call.metadata.user == "test_user"
        assert triples_call.metadata.collection == "test_collection"
        
        assert entity_contexts_call.metadata.id == "test-doc-123"
        assert entity_contexts_call.metadata.user == "test_user"
        assert entity_contexts_call.metadata.collection == "test_collection"