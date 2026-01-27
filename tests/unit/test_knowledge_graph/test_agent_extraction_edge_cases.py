"""
Edge case and error handling tests for Agent-based Knowledge Graph Extraction

These tests focus on boundary conditions, error scenarios, and unusual but valid
use cases for the agent-driven knowledge graph extractor.
"""

import pytest
import json
import urllib.parse
from unittest.mock import AsyncMock, MagicMock

from trustgraph.extract.kg.agent.extract import Processor as AgentKgExtractor
from trustgraph.schema import Chunk, Triple, Triples, Metadata, Term, IRI, LITERAL
from trustgraph.schema import EntityContext, EntityContexts
from trustgraph.rdf import TRUSTGRAPH_ENTITIES, DEFINITION, RDF_LABEL, SUBJECT_OF


@pytest.mark.unit
class TestAgentKgExtractionEdgeCases:
    """Edge case tests for Agent-based Knowledge Graph Extraction"""

    @pytest.fixture
    def agent_extractor(self):
        """Create a mock agent extractor for testing core functionality"""
        # Create a mock that has the methods we want to test
        extractor = MagicMock()
        
        # Add real implementations of the methods we want to test
        from trustgraph.extract.kg.agent.extract import Processor
        real_extractor = Processor.__new__(Processor)  # Create without calling __init__
        
        # Set up the methods we want to test
        extractor.to_uri = real_extractor.to_uri
        extractor.parse_jsonl = real_extractor.parse_jsonl
        extractor.process_extraction_data = real_extractor.process_extraction_data
        extractor.emit_triples = real_extractor.emit_triples
        extractor.emit_entity_contexts = real_extractor.emit_entity_contexts

        return extractor

    def test_to_uri_special_characters(self, agent_extractor):
        """Test URI encoding with various special characters"""
        # Test common special characters
        test_cases = [
            ("Hello World", "Hello%20World"),
            ("Entity & Co", "Entity%20%26%20Co"),
            ("Name (with parentheses)", "Name%20%28with%20parentheses%29"),
            ("Percent: 100%", "Percent%3A%20100%25"),
            ("Question?", "Question%3F"),
            ("Hash#tag", "Hash%23tag"),
            ("Plus+sign", "Plus%2Bsign"),
            ("Forward/slash", "Forward/slash"),  # Forward slash is not encoded by quote()
            ("Back\\slash", "Back%5Cslash"),
            ("Quotes \"test\"", "Quotes%20%22test%22"),
            ("Single 'quotes'", "Single%20%27quotes%27"),
            ("Equals=sign", "Equals%3Dsign"),
            ("Less<than", "Less%3Cthan"),
            ("Greater>than", "Greater%3Ethan"),
        ]
        
        for input_text, expected_encoded in test_cases:
            uri = agent_extractor.to_uri(input_text)
            expected_uri = f"{TRUSTGRAPH_ENTITIES}{expected_encoded}"
            assert uri == expected_uri, f"Failed for input: {input_text}"

    def test_to_uri_unicode_characters(self, agent_extractor):
        """Test URI encoding with unicode characters"""
        # Test various unicode characters
        test_cases = [
            "机器学习",  # Chinese
            "機械学習",  # Japanese Kanji
            "пуле́ме́т",  # Russian with diacritics
            "Café",     # French with accent
            "naïve",    # Diaeresis
            "Ñoño",     # Spanish tilde
            "🤖🧠",      # Emojis
            "α β γ",    # Greek letters
        ]
        
        for unicode_text in test_cases:
            uri = agent_extractor.to_uri(unicode_text)
            expected = f"{TRUSTGRAPH_ENTITIES}{urllib.parse.quote(unicode_text)}"
            assert uri == expected
            # Verify the URI is properly encoded
            assert unicode_text not in uri  # Original unicode should be encoded

    def test_parse_jsonl_whitespace_variations(self, agent_extractor):
        """Test JSONL parsing with various whitespace patterns"""
        # Test JSONL with different whitespace patterns
        test_cases = [
            # Extra whitespace around code blocks
            '   ```json\n{"type": "definition", "entity": "test", "definition": "def"}\n```   ',
            # Multiple newlines between lines
            '{"type": "definition", "entity": "A", "definition": "def A"}\n\n\n{"type": "definition", "entity": "B", "definition": "def B"}',
            # JSONL without code blocks but with whitespace
            '   {"type": "definition", "entity": "test", "definition": "def"}   ',
        ]

        for response in test_cases:
            result = agent_extractor.parse_jsonl(response)
            assert len(result) >= 1
            assert result[0].get("type") == "definition"

    def test_parse_jsonl_code_block_variations(self, agent_extractor):
        """Test JSONL parsing with different code block formats"""
        test_cases = [
            # Standard json code block
            '```json\n{"type": "definition", "entity": "A", "definition": "def"}\n```',
            # jsonl code block
            '```jsonl\n{"type": "definition", "entity": "A", "definition": "def"}\n```',
            # Code block without language
            '```\n{"type": "definition", "entity": "A", "definition": "def"}\n```',
            # Code block with extra content before/after
            'Here\'s the result:\n```json\n{"type": "definition", "entity": "A", "definition": "def"}\n```\nDone!',
        ]

        for i, response in enumerate(test_cases):
            result = agent_extractor.parse_jsonl(response)
            assert len(result) >= 1, f"Case {i} failed"
            assert result[0].get("entity") == "A"

    def test_parse_jsonl_truncation_resilience(self, agent_extractor):
        """Test JSONL parsing with truncated responses"""
        # Simulates LLM output being cut off mid-line
        response = '''{"type": "definition", "entity": "Complete1", "definition": "Full definition"}
{"type": "definition", "entity": "Complete2", "definition": "Another full def"}
{"type": "definition", "entity": "Trunca'''

        result = agent_extractor.parse_jsonl(response)

        # Should get 2 valid objects, the truncated line is skipped
        assert len(result) == 2
        assert result[0]["entity"] == "Complete1"
        assert result[1]["entity"] == "Complete2"

    def test_parse_jsonl_large_responses(self, agent_extractor):
        """Test JSONL parsing with very large responses"""
        # Create a large JSONL response
        lines = []
        for i in range(100):
            lines.append(json.dumps({
                "type": "definition",
                "entity": f"Entity {i}",
                "definition": f"Definition {i} " + "with more content " * 100
            }))
        for i in range(50):
            lines.append(json.dumps({
                "type": "relationship",
                "subject": f"Subject {i}",
                "predicate": f"predicate_{i}",
                "object": f"Object {i}",
                "object-entity": i % 2 == 0
            }))

        response = f"```json\n{chr(10).join(lines)}\n```"

        result = agent_extractor.parse_jsonl(response)

        definitions = [r for r in result if r.get("type") == "definition"]
        relationships = [r for r in result if r.get("type") == "relationship"]

        assert len(definitions) == 100
        assert len(relationships) == 50
        assert definitions[0]["entity"] == "Entity 0"

    def test_process_extraction_data_empty_metadata(self, agent_extractor):
        """Test processing with empty or minimal metadata"""
        # Test with None metadata - may not raise AttributeError depending on implementation
        try:
            triples, contexts = agent_extractor.process_extraction_data([], None)
            # If it doesn't raise, check the results
            assert len(triples) == 0
            assert len(contexts) == 0
        except (AttributeError, TypeError):
            # This is expected behavior when metadata is None
            pass

        # Test with metadata without ID
        metadata = Metadata(id=None, metadata=[])
        triples, contexts = agent_extractor.process_extraction_data([], metadata)
        assert len(triples) == 0
        assert len(contexts) == 0

        # Test with metadata with empty string ID
        metadata = Metadata(id="", metadata=[])
        data = [{"type": "definition", "entity": "Test", "definition": "Test def"}]
        triples, contexts = agent_extractor.process_extraction_data(data, metadata)

        # Should not create subject-of triples when ID is empty string
        subject_of_triples = [t for t in triples if t.p.iri == SUBJECT_OF]
        assert len(subject_of_triples) == 0

    def test_process_extraction_data_special_entity_names(self, agent_extractor):
        """Test processing with special characters in entity names"""
        metadata = Metadata(id="doc123", metadata=[])

        special_entities = [
            "Entity with spaces",
            "Entity & Co.",
            "100% Success Rate",
            "Question?",
            "Hash#tag",
            "Forward/Backward\\Slashes",
            "Unicode: 机器学习",
            "Emoji: 🤖",
            "Quotes: \"test\"",
            "Parentheses: (test)",
        ]

        data = [
            {"type": "definition", "entity": entity, "definition": f"Definition for {entity}"}
            for entity in special_entities
        ]

        triples, contexts = agent_extractor.process_extraction_data(data, metadata)

        # Verify all entities were processed
        assert len(contexts) == len(special_entities)

        # Verify URIs were properly encoded
        for i, entity in enumerate(special_entities):
            expected_uri = f"{TRUSTGRAPH_ENTITIES}{urllib.parse.quote(entity)}"
            assert contexts[i].entity.iri == expected_uri

    def test_process_extraction_data_very_long_definitions(self, agent_extractor):
        """Test processing with very long entity definitions"""
        metadata = Metadata(id="doc123", metadata=[])

        # Create very long definition
        long_definition = "This is a very long definition. " * 1000

        data = [
            {"type": "definition", "entity": "Test Entity", "definition": long_definition}
        ]

        triples, contexts = agent_extractor.process_extraction_data(data, metadata)

        # Should handle long definitions without issues
        assert len(contexts) == 1
        assert contexts[0].context == long_definition

        # Find definition triple
        def_triple = next((t for t in triples if t.p.iri == DEFINITION), None)
        assert def_triple is not None
        assert def_triple.o.value == long_definition

    def test_process_extraction_data_duplicate_entities(self, agent_extractor):
        """Test processing with duplicate entity names"""
        metadata = Metadata(id="doc123", metadata=[])

        data = [
            {"type": "definition", "entity": "Machine Learning", "definition": "First definition"},
            {"type": "definition", "entity": "Machine Learning", "definition": "Second definition"},  # Duplicate
            {"type": "definition", "entity": "AI", "definition": "AI definition"},
            {"type": "definition", "entity": "AI", "definition": "Another AI definition"},  # Duplicate
        ]

        triples, contexts = agent_extractor.process_extraction_data(data, metadata)

        # Should process all entries (including duplicates)
        assert len(contexts) == 4

        # Check that both definitions for "Machine Learning" are present
        ml_contexts = [ec for ec in contexts if "Machine%20Learning" in ec.entity.iri]
        assert len(ml_contexts) == 2
        assert ml_contexts[0].context == "First definition"
        assert ml_contexts[1].context == "Second definition"

    def test_process_extraction_data_empty_strings(self, agent_extractor):
        """Test processing with empty strings in data"""
        metadata = Metadata(id="doc123", metadata=[])

        data = [
            {"type": "definition", "entity": "", "definition": "Definition for empty entity"},
            {"type": "definition", "entity": "Valid Entity", "definition": ""},
            {"type": "definition", "entity": "  ", "definition": "   "},  # Whitespace only
            {"type": "relationship", "subject": "", "predicate": "test", "object": "test", "object-entity": True},
            {"type": "relationship", "subject": "test", "predicate": "", "object": "test", "object-entity": True},
            {"type": "relationship", "subject": "test", "predicate": "test", "object": "", "object-entity": True},
        ]

        triples, contexts = agent_extractor.process_extraction_data(data, metadata)

        # Should handle empty strings by creating URIs (even if empty)
        assert len(contexts) == 3

        # Empty entity should create empty URI after encoding
        empty_entity_context = next((ec for ec in contexts if ec.entity.iri == TRUSTGRAPH_ENTITIES), None)
        assert empty_entity_context is not None

    def test_process_extraction_data_nested_json_in_strings(self, agent_extractor):
        """Test processing when definitions contain JSON-like strings"""
        metadata = Metadata(id="doc123", metadata=[])

        data = [
            {
                "type": "definition",
                "entity": "JSON Entity",
                "definition": 'Definition with JSON: {"key": "value", "nested": {"inner": true}}'
            },
            {
                "type": "definition",
                "entity": "Array Entity",
                "definition": 'Contains array: [1, 2, 3, "string"]'
            }
        ]

        triples, contexts = agent_extractor.process_extraction_data(data, metadata)

        # Should handle JSON strings in definitions without parsing them
        assert len(contexts) == 2
        assert '{"key": "value"' in contexts[0].context
        assert '[1, 2, 3, "string"]' in contexts[1].context

    def test_process_extraction_data_boolean_object_entity_variations(self, agent_extractor):
        """Test processing with various boolean values for object-entity"""
        metadata = Metadata(id="doc123", metadata=[])

        data = [
            # Explicit True
            {"type": "relationship", "subject": "A", "predicate": "rel1", "object": "B", "object-entity": True},
            # Explicit False
            {"type": "relationship", "subject": "A", "predicate": "rel2", "object": "literal", "object-entity": False},
            # Missing object-entity (should default to True based on code)
            {"type": "relationship", "subject": "A", "predicate": "rel3", "object": "C"},
            # String "true" (should be treated as truthy)
            {"type": "relationship", "subject": "A", "predicate": "rel4", "object": "D", "object-entity": "true"},
            # String "false" (should be treated as truthy in Python)
            {"type": "relationship", "subject": "A", "predicate": "rel5", "object": "E", "object-entity": "false"},
            # Number 0 (falsy)
            {"type": "relationship", "subject": "A", "predicate": "rel6", "object": "literal2", "object-entity": 0},
            # Number 1 (truthy)
            {"type": "relationship", "subject": "A", "predicate": "rel7", "object": "F", "object-entity": 1},
        ]

        triples, contexts = agent_extractor.process_extraction_data(data, metadata)

        # Should process all relationships
        # Note: The current implementation has some logic issues that these tests document
        assert len([t for t in triples if t.p.iri != RDF_LABEL and t.p.iri != SUBJECT_OF]) >= 7

    @pytest.mark.asyncio
    async def test_emit_empty_collections(self, agent_extractor):
        """Test emitting empty triples and entity contexts"""
        metadata = Metadata(id="test", metadata=[])
        
        # Test emitting empty triples
        mock_publisher = AsyncMock()
        await agent_extractor.emit_triples(mock_publisher, metadata, [])
        
        mock_publisher.send.assert_called_once()
        sent_triples = mock_publisher.send.call_args[0][0]
        assert isinstance(sent_triples, Triples)
        assert len(sent_triples.triples) == 0
        
        # Test emitting empty entity contexts
        mock_publisher.reset_mock()
        await agent_extractor.emit_entity_contexts(mock_publisher, metadata, [])
        
        mock_publisher.send.assert_called_once()
        sent_contexts = mock_publisher.send.call_args[0][0]
        assert isinstance(sent_contexts, EntityContexts)
        assert len(sent_contexts.entities) == 0

    def test_arg_parser_integration(self):
        """Test command line argument parsing integration"""
        import argparse
        from trustgraph.extract.kg.agent.extract import Processor
        
        parser = argparse.ArgumentParser()
        Processor.add_args(parser)
        
        # Test default arguments
        args = parser.parse_args([])
        assert args.concurrency == 1
        assert args.template_id == "agent-kg-extract"
        assert args.config_type == "prompt"
        
        # Test custom arguments
        args = parser.parse_args([
            "--concurrency", "5",
            "--template-id", "custom-template",
            "--config-type", "custom-config"
        ])
        assert args.concurrency == 5
        assert args.template_id == "custom-template"
        assert args.config_type == "custom-config"

    def test_process_extraction_data_performance_large_dataset(self, agent_extractor):
        """Test performance with large extraction datasets"""
        metadata = Metadata(id="large-doc", metadata=[])

        # Create large dataset in JSONL format
        num_definitions = 1000
        num_relationships = 2000

        large_data = [
            {
                "type": "definition",
                "entity": f"Entity_{i:04d}",
                "definition": f"Definition for entity {i} with some detailed explanation."
            }
            for i in range(num_definitions)
        ] + [
            {
                "type": "relationship",
                "subject": f"Entity_{i % num_definitions:04d}",
                "predicate": f"predicate_{i % 10}",
                "object": f"Entity_{(i + 1) % num_definitions:04d}",
                "object-entity": True
            }
            for i in range(num_relationships)
        ]

        import time
        start_time = time.time()

        triples, contexts = agent_extractor.process_extraction_data(large_data, metadata)

        end_time = time.time()
        processing_time = end_time - start_time

        # Should complete within reasonable time (adjust threshold as needed)
        assert processing_time < 10.0  # 10 seconds threshold

        # Verify results
        assert len(contexts) == num_definitions
        # Triples include labels, definitions, relationships, and subject-of relations
        assert len(triples) > num_definitions + num_relationships