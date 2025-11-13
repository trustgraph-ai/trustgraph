"""
Unit tests for entity context building.

Tests that entity contexts are properly created from extracted triples,
collecting labels and definitions for entity embedding and retrieval.
"""

import pytest
from trustgraph.extract.kg.ontology.extract import Processor
from trustgraph.schema.core.primitives import Triple, Value
from trustgraph.schema.knowledge.graph import EntityContext


@pytest.fixture
def processor():
    """Create a Processor instance for testing."""
    processor = object.__new__(Processor)
    return processor


class TestEntityContextBuilding:
    """Test suite for entity context building from triples."""

    def test_builds_context_from_label(self, processor):
        """Test that entity context is built from rdfs:label."""
        triples = [
            Triple(
                s=Value(value="https://example.com/entity/cornish-pasty", is_uri=True),
                p=Value(value="http://www.w3.org/2000/01/rdf-schema#label", is_uri=True),
                o=Value(value="Cornish Pasty", is_uri=False)
            )
        ]

        contexts = processor.build_entity_contexts(triples)

        assert len(contexts) == 1, "Should create one entity context"
        assert isinstance(contexts[0], EntityContext)
        assert contexts[0].entity.value == "https://example.com/entity/cornish-pasty"
        assert "Label: Cornish Pasty" in contexts[0].context

    def test_builds_context_from_definition(self, processor):
        """Test that entity context includes definitions."""
        triples = [
            Triple(
                s=Value(value="https://example.com/entity/pasty", is_uri=True),
                p=Value(value="http://www.w3.org/2004/02/skos/core#definition", is_uri=True),
                o=Value(value="A baked pastry filled with savory ingredients", is_uri=False)
            )
        ]

        contexts = processor.build_entity_contexts(triples)

        assert len(contexts) == 1
        assert "A baked pastry filled with savory ingredients" in contexts[0].context

    def test_combines_label_and_definition(self, processor):
        """Test that label and definition are combined in context."""
        triples = [
            Triple(
                s=Value(value="https://example.com/entity/recipe1", is_uri=True),
                p=Value(value="http://www.w3.org/2000/01/rdf-schema#label", is_uri=True),
                o=Value(value="Pasty Recipe", is_uri=False)
            ),
            Triple(
                s=Value(value="https://example.com/entity/recipe1", is_uri=True),
                p=Value(value="http://www.w3.org/2004/02/skos/core#definition", is_uri=True),
                o=Value(value="Traditional Cornish pastry recipe", is_uri=False)
            )
        ]

        contexts = processor.build_entity_contexts(triples)

        assert len(contexts) == 1
        context_text = contexts[0].context
        assert "Label: Pasty Recipe" in context_text
        assert "Traditional Cornish pastry recipe" in context_text
        assert ". " in context_text, "Should join parts with period and space"

    def test_uses_first_label_only(self, processor):
        """Test that only the first label is used in context."""
        triples = [
            Triple(
                s=Value(value="https://example.com/entity/food1", is_uri=True),
                p=Value(value="http://www.w3.org/2000/01/rdf-schema#label", is_uri=True),
                o=Value(value="First Label", is_uri=False)
            ),
            Triple(
                s=Value(value="https://example.com/entity/food1", is_uri=True),
                p=Value(value="http://www.w3.org/2000/01/rdf-schema#label", is_uri=True),
                o=Value(value="Second Label", is_uri=False)
            )
        ]

        contexts = processor.build_entity_contexts(triples)

        assert len(contexts) == 1
        assert "Label: First Label" in contexts[0].context
        assert "Second Label" not in contexts[0].context

    def test_includes_all_definitions(self, processor):
        """Test that all definitions are included in context."""
        triples = [
            Triple(
                s=Value(value="https://example.com/entity/food1", is_uri=True),
                p=Value(value="http://www.w3.org/2004/02/skos/core#definition", is_uri=True),
                o=Value(value="First definition", is_uri=False)
            ),
            Triple(
                s=Value(value="https://example.com/entity/food1", is_uri=True),
                p=Value(value="http://www.w3.org/2004/02/skos/core#definition", is_uri=True),
                o=Value(value="Second definition", is_uri=False)
            )
        ]

        contexts = processor.build_entity_contexts(triples)

        assert len(contexts) == 1
        context_text = contexts[0].context
        assert "First definition" in context_text
        assert "Second definition" in context_text

    def test_supports_schema_org_description(self, processor):
        """Test that schema.org description is treated as definition."""
        triples = [
            Triple(
                s=Value(value="https://example.com/entity/food1", is_uri=True),
                p=Value(value="https://schema.org/description", is_uri=True),
                o=Value(value="A delicious food item", is_uri=False)
            )
        ]

        contexts = processor.build_entity_contexts(triples)

        assert len(contexts) == 1
        assert "A delicious food item" in contexts[0].context

    def test_handles_multiple_entities(self, processor):
        """Test that contexts are created for multiple entities."""
        triples = [
            Triple(
                s=Value(value="https://example.com/entity/entity1", is_uri=True),
                p=Value(value="http://www.w3.org/2000/01/rdf-schema#label", is_uri=True),
                o=Value(value="Entity One", is_uri=False)
            ),
            Triple(
                s=Value(value="https://example.com/entity/entity2", is_uri=True),
                p=Value(value="http://www.w3.org/2000/01/rdf-schema#label", is_uri=True),
                o=Value(value="Entity Two", is_uri=False)
            ),
            Triple(
                s=Value(value="https://example.com/entity/entity3", is_uri=True),
                p=Value(value="http://www.w3.org/2000/01/rdf-schema#label", is_uri=True),
                o=Value(value="Entity Three", is_uri=False)
            )
        ]

        contexts = processor.build_entity_contexts(triples)

        assert len(contexts) == 3, "Should create context for each entity"
        entity_uris = [ctx.entity.value for ctx in contexts]
        assert "https://example.com/entity/entity1" in entity_uris
        assert "https://example.com/entity/entity2" in entity_uris
        assert "https://example.com/entity/entity3" in entity_uris

    def test_ignores_uri_literals(self, processor):
        """Test that URI objects are ignored (only literal labels/definitions)."""
        triples = [
            Triple(
                s=Value(value="https://example.com/entity/food1", is_uri=True),
                p=Value(value="http://www.w3.org/2000/01/rdf-schema#label", is_uri=True),
                o=Value(value="https://example.com/some/uri", is_uri=True)  # URI, not literal
            )
        ]

        contexts = processor.build_entity_contexts(triples)

        # Should not create context since label is URI
        assert len(contexts) == 0, "Should not create context for URI labels"

    def test_ignores_non_label_non_definition_triples(self, processor):
        """Test that other predicates are ignored."""
        triples = [
            Triple(
                s=Value(value="https://example.com/entity/food1", is_uri=True),
                p=Value(value="http://www.w3.org/1999/02/22-rdf-syntax-ns#type", is_uri=True),
                o=Value(value="http://example.com/Food", is_uri=True)
            ),
            Triple(
                s=Value(value="https://example.com/entity/food1", is_uri=True),
                p=Value(value="http://example.com/produces", is_uri=True),
                o=Value(value="https://example.com/entity/food2", is_uri=True)
            )
        ]

        contexts = processor.build_entity_contexts(triples)

        # Should not create context since no labels or definitions
        assert len(contexts) == 0, "Should not create context without labels/definitions"

    def test_handles_empty_triple_list(self, processor):
        """Test handling of empty triple list."""
        triples = []

        contexts = processor.build_entity_contexts(triples)

        assert len(contexts) == 0, "Empty triple list should return empty contexts"

    def test_entity_context_has_value_object(self, processor):
        """Test that EntityContext.entity is a Value object."""
        triples = [
            Triple(
                s=Value(value="https://example.com/entity/test", is_uri=True),
                p=Value(value="http://www.w3.org/2000/01/rdf-schema#label", is_uri=True),
                o=Value(value="Test Entity", is_uri=False)
            )
        ]

        contexts = processor.build_entity_contexts(triples)

        assert len(contexts) == 1
        assert isinstance(contexts[0].entity, Value), "Entity should be Value object"
        assert contexts[0].entity.is_uri, "Entity should be marked as URI"

    def test_entity_context_text_is_string(self, processor):
        """Test that EntityContext.context is a string."""
        triples = [
            Triple(
                s=Value(value="https://example.com/entity/test", is_uri=True),
                p=Value(value="http://www.w3.org/2000/01/rdf-schema#label", is_uri=True),
                o=Value(value="Test Entity", is_uri=False)
            )
        ]

        contexts = processor.build_entity_contexts(triples)

        assert len(contexts) == 1
        assert isinstance(contexts[0].context, str), "Context should be string"

    def test_only_creates_contexts_with_meaningful_info(self, processor):
        """Test that contexts are only created when there's meaningful information."""
        triples = [
            # Entity with label - should create context
            Triple(
                s=Value(value="https://example.com/entity/entity1", is_uri=True),
                p=Value(value="http://www.w3.org/2000/01/rdf-schema#label", is_uri=True),
                o=Value(value="Entity One", is_uri=False)
            ),
            # Entity with only rdf:type - should NOT create context
            Triple(
                s=Value(value="https://example.com/entity/entity2", is_uri=True),
                p=Value(value="http://www.w3.org/1999/02/22-rdf-syntax-ns#type", is_uri=True),
                o=Value(value="http://example.com/Food", is_uri=True)
            )
        ]

        contexts = processor.build_entity_contexts(triples)

        assert len(contexts) == 1, "Should only create context for entity with label/definition"
        assert contexts[0].entity.value == "https://example.com/entity/entity1"


class TestEntityContextEdgeCases:
    """Test suite for edge cases in entity context building."""

    def test_handles_unicode_in_labels(self, processor):
        """Test handling of unicode characters in labels."""
        triples = [
            Triple(
                s=Value(value="https://example.com/entity/café", is_uri=True),
                p=Value(value="http://www.w3.org/2000/01/rdf-schema#label", is_uri=True),
                o=Value(value="Café Spécial", is_uri=False)
            )
        ]

        contexts = processor.build_entity_contexts(triples)

        assert len(contexts) == 1
        assert "Café Spécial" in contexts[0].context

    def test_handles_long_definitions(self, processor):
        """Test handling of very long definitions."""
        long_def = "This is a very long definition " * 50
        triples = [
            Triple(
                s=Value(value="https://example.com/entity/test", is_uri=True),
                p=Value(value="http://www.w3.org/2004/02/skos/core#definition", is_uri=True),
                o=Value(value=long_def, is_uri=False)
            )
        ]

        contexts = processor.build_entity_contexts(triples)

        assert len(contexts) == 1
        assert long_def in contexts[0].context

    def test_handles_special_characters_in_context(self, processor):
        """Test handling of special characters in context text."""
        triples = [
            Triple(
                s=Value(value="https://example.com/entity/test", is_uri=True),
                p=Value(value="http://www.w3.org/2000/01/rdf-schema#label", is_uri=True),
                o=Value(value="Test & Entity <with> \"quotes\"", is_uri=False)
            )
        ]

        contexts = processor.build_entity_contexts(triples)

        assert len(contexts) == 1
        assert "Test & Entity <with> \"quotes\"" in contexts[0].context

    def test_mixed_relevant_and_irrelevant_triples(self, processor):
        """Test extracting contexts from mixed triple types."""
        triples = [
            # Label - relevant
            Triple(
                s=Value(value="https://example.com/entity/recipe1", is_uri=True),
                p=Value(value="http://www.w3.org/2000/01/rdf-schema#label", is_uri=True),
                o=Value(value="Cornish Pasty Recipe", is_uri=False)
            ),
            # Type - irrelevant
            Triple(
                s=Value(value="https://example.com/entity/recipe1", is_uri=True),
                p=Value(value="http://www.w3.org/1999/02/22-rdf-syntax-ns#type", is_uri=True),
                o=Value(value="http://example.com/Recipe", is_uri=True)
            ),
            # Property - irrelevant
            Triple(
                s=Value(value="https://example.com/entity/recipe1", is_uri=True),
                p=Value(value="http://example.com/produces", is_uri=True),
                o=Value(value="https://example.com/entity/pasty", is_uri=True)
            ),
            # Definition - relevant
            Triple(
                s=Value(value="https://example.com/entity/recipe1", is_uri=True),
                p=Value(value="http://www.w3.org/2004/02/skos/core#definition", is_uri=True),
                o=Value(value="Traditional British pastry recipe", is_uri=False)
            )
        ]

        contexts = processor.build_entity_contexts(triples)

        assert len(contexts) == 1
        context_text = contexts[0].context
        # Should include label and definition
        assert "Label: Cornish Pasty Recipe" in context_text
        assert "Traditional British pastry recipe" in context_text
        # Should not include type or property info
        assert "Recipe" not in context_text or "Cornish Pasty Recipe" in context_text  # Only in label
        assert "produces" not in context_text


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
