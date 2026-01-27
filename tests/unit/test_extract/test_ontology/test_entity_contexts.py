"""
Unit tests for entity context building.

Tests that entity contexts are properly created from extracted triples,
collecting labels and definitions for entity embedding and retrieval.
"""

import pytest
from trustgraph.extract.kg.ontology.extract import Processor
from trustgraph.schema.core.primitives import Triple, Term, IRI, LITERAL
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
                s=Term(type=IRI, iri="https://example.com/entity/cornish-pasty"),
                p=Term(type=IRI, iri="http://www.w3.org/2000/01/rdf-schema#label"),
                o=Term(type=LITERAL, value="Cornish Pasty")
            )
        ]

        contexts = processor.build_entity_contexts(triples)

        assert len(contexts) == 1, "Should create one entity context"
        assert isinstance(contexts[0], EntityContext)
        assert contexts[0].entity.iri == "https://example.com/entity/cornish-pasty"
        assert "Label: Cornish Pasty" in contexts[0].context

    def test_builds_context_from_definition(self, processor):
        """Test that entity context includes definitions."""
        triples = [
            Triple(
                s=Term(type=IRI, iri="https://example.com/entity/pasty"),
                p=Term(type=IRI, iri="http://www.w3.org/2004/02/skos/core#definition"),
                o=Term(type=LITERAL, value="A baked pastry filled with savory ingredients")
            )
        ]

        contexts = processor.build_entity_contexts(triples)

        assert len(contexts) == 1
        assert "A baked pastry filled with savory ingredients" in contexts[0].context

    def test_combines_label_and_definition(self, processor):
        """Test that label and definition are combined in context."""
        triples = [
            Triple(
                s=Term(type=IRI, iri="https://example.com/entity/recipe1"),
                p=Term(type=IRI, iri="http://www.w3.org/2000/01/rdf-schema#label"),
                o=Term(type=LITERAL, value="Pasty Recipe")
            ),
            Triple(
                s=Term(type=IRI, iri="https://example.com/entity/recipe1"),
                p=Term(type=IRI, iri="http://www.w3.org/2004/02/skos/core#definition"),
                o=Term(type=LITERAL, value="Traditional Cornish pastry recipe")
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
                s=Term(type=IRI, iri="https://example.com/entity/food1"),
                p=Term(type=IRI, iri="http://www.w3.org/2000/01/rdf-schema#label"),
                o=Term(type=LITERAL, value="First Label")
            ),
            Triple(
                s=Term(type=IRI, iri="https://example.com/entity/food1"),
                p=Term(type=IRI, iri="http://www.w3.org/2000/01/rdf-schema#label"),
                o=Term(type=LITERAL, value="Second Label")
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
                s=Term(type=IRI, iri="https://example.com/entity/food1"),
                p=Term(type=IRI, iri="http://www.w3.org/2004/02/skos/core#definition"),
                o=Term(type=LITERAL, value="First definition")
            ),
            Triple(
                s=Term(type=IRI, iri="https://example.com/entity/food1"),
                p=Term(type=IRI, iri="http://www.w3.org/2004/02/skos/core#definition"),
                o=Term(type=LITERAL, value="Second definition")
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
                s=Term(type=IRI, iri="https://example.com/entity/food1"),
                p=Term(type=IRI, iri="https://schema.org/description"),
                o=Term(type=LITERAL, value="A delicious food item")
            )
        ]

        contexts = processor.build_entity_contexts(triples)

        assert len(contexts) == 1
        assert "A delicious food item" in contexts[0].context

    def test_handles_multiple_entities(self, processor):
        """Test that contexts are created for multiple entities."""
        triples = [
            Triple(
                s=Term(type=IRI, iri="https://example.com/entity/entity1"),
                p=Term(type=IRI, iri="http://www.w3.org/2000/01/rdf-schema#label"),
                o=Term(type=LITERAL, value="Entity One")
            ),
            Triple(
                s=Term(type=IRI, iri="https://example.com/entity/entity2"),
                p=Term(type=IRI, iri="http://www.w3.org/2000/01/rdf-schema#label"),
                o=Term(type=LITERAL, value="Entity Two")
            ),
            Triple(
                s=Term(type=IRI, iri="https://example.com/entity/entity3"),
                p=Term(type=IRI, iri="http://www.w3.org/2000/01/rdf-schema#label"),
                o=Term(type=LITERAL, value="Entity Three")
            )
        ]

        contexts = processor.build_entity_contexts(triples)

        assert len(contexts) == 3, "Should create context for each entity"
        entity_uris = [ctx.entity.iri for ctx in contexts]
        assert "https://example.com/entity/entity1" in entity_uris
        assert "https://example.com/entity/entity2" in entity_uris
        assert "https://example.com/entity/entity3" in entity_uris

    def test_ignores_uri_literals(self, processor):
        """Test that URI objects are ignored (only literal labels/definitions)."""
        triples = [
            Triple(
                s=Term(type=IRI, iri="https://example.com/entity/food1"),
                p=Term(type=IRI, iri="http://www.w3.org/2000/01/rdf-schema#label"),
                o=Term(type=IRI, iri="https://example.com/some/uri")  # URI, not literal
            )
        ]

        contexts = processor.build_entity_contexts(triples)

        # Should not create context since label is URI
        assert len(contexts) == 0, "Should not create context for URI labels"

    def test_ignores_non_label_non_definition_triples(self, processor):
        """Test that other predicates are ignored."""
        triples = [
            Triple(
                s=Term(type=IRI, iri="https://example.com/entity/food1"),
                p=Term(type=IRI, iri="http://www.w3.org/1999/02/22-rdf-syntax-ns#type"),
                o=Term(type=IRI, iri="http://example.com/Food")
            ),
            Triple(
                s=Term(type=IRI, iri="https://example.com/entity/food1"),
                p=Term(type=IRI, iri="http://example.com/produces"),
                o=Term(type=IRI, iri="https://example.com/entity/food2")
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

    def test_entity_context_has_term_object(self, processor):
        """Test that EntityContext.entity is a Term object."""
        triples = [
            Triple(
                s=Term(type=IRI, iri="https://example.com/entity/test"),
                p=Term(type=IRI, iri="http://www.w3.org/2000/01/rdf-schema#label"),
                o=Term(type=LITERAL, value="Test Entity")
            )
        ]

        contexts = processor.build_entity_contexts(triples)

        assert len(contexts) == 1
        assert isinstance(contexts[0].entity, Term), "Entity should be Term object"
        assert contexts[0].entity.type == IRI, "Entity should be IRI type"

    def test_entity_context_text_is_string(self, processor):
        """Test that EntityContext.context is a string."""
        triples = [
            Triple(
                s=Term(type=IRI, iri="https://example.com/entity/test"),
                p=Term(type=IRI, iri="http://www.w3.org/2000/01/rdf-schema#label"),
                o=Term(type=LITERAL, value="Test Entity")
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
                s=Term(type=IRI, iri="https://example.com/entity/entity1"),
                p=Term(type=IRI, iri="http://www.w3.org/2000/01/rdf-schema#label"),
                o=Term(type=LITERAL, value="Entity One")
            ),
            # Entity with only rdf:type - should NOT create context
            Triple(
                s=Term(type=IRI, iri="https://example.com/entity/entity2"),
                p=Term(type=IRI, iri="http://www.w3.org/1999/02/22-rdf-syntax-ns#type"),
                o=Term(type=IRI, iri="http://example.com/Food")
            )
        ]

        contexts = processor.build_entity_contexts(triples)

        assert len(contexts) == 1, "Should only create context for entity with label/definition"
        assert contexts[0].entity.iri == "https://example.com/entity/entity1"


class TestEntityContextEdgeCases:
    """Test suite for edge cases in entity context building."""

    def test_handles_unicode_in_labels(self, processor):
        """Test handling of unicode characters in labels."""
        triples = [
            Triple(
                s=Term(type=IRI, iri="https://example.com/entity/café"),
                p=Term(type=IRI, iri="http://www.w3.org/2000/01/rdf-schema#label"),
                o=Term(type=LITERAL, value="Café Spécial")
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
                s=Term(type=IRI, iri="https://example.com/entity/test"),
                p=Term(type=IRI, iri="http://www.w3.org/2004/02/skos/core#definition"),
                o=Term(type=LITERAL, value=long_def)
            )
        ]

        contexts = processor.build_entity_contexts(triples)

        assert len(contexts) == 1
        assert long_def in contexts[0].context

    def test_handles_special_characters_in_context(self, processor):
        """Test handling of special characters in context text."""
        triples = [
            Triple(
                s=Term(type=IRI, iri="https://example.com/entity/test"),
                p=Term(type=IRI, iri="http://www.w3.org/2000/01/rdf-schema#label"),
                o=Term(type=LITERAL, value="Test & Entity <with> \"quotes\"")
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
                s=Term(type=IRI, iri="https://example.com/entity/recipe1"),
                p=Term(type=IRI, iri="http://www.w3.org/2000/01/rdf-schema#label"),
                o=Term(type=LITERAL, value="Cornish Pasty Recipe")
            ),
            # Type - irrelevant
            Triple(
                s=Term(type=IRI, iri="https://example.com/entity/recipe1"),
                p=Term(type=IRI, iri="http://www.w3.org/1999/02/22-rdf-syntax-ns#type"),
                o=Term(type=IRI, iri="http://example.com/Recipe")
            ),
            # Property - irrelevant
            Triple(
                s=Term(type=IRI, iri="https://example.com/entity/recipe1"),
                p=Term(type=IRI, iri="http://example.com/produces"),
                o=Term(type=IRI, iri="https://example.com/entity/pasty")
            ),
            # Definition - relevant
            Triple(
                s=Term(type=IRI, iri="https://example.com/entity/recipe1"),
                p=Term(type=IRI, iri="http://www.w3.org/2004/02/skos/core#definition"),
                o=Term(type=LITERAL, value="Traditional British pastry recipe")
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
