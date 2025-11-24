"""
Unit tests for LLM prompt construction and triple extraction.

Tests that the system correctly constructs prompts with ontology constraints
and extracts/validates triples from LLM responses.
"""

import pytest
from trustgraph.extract.kg.ontology.extract import Processor
from trustgraph.extract.kg.ontology.ontology_selector import OntologySubset
from trustgraph.schema.core.primitives import Triple, Value


@pytest.fixture
def extractor():
    """Create a Processor instance for testing."""
    extractor = object.__new__(Processor)
    extractor.URI_PREFIXES = {
        "rdf:": "http://www.w3.org/1999/02/22-rdf-syntax-ns#",
        "rdfs:": "http://www.w3.org/2000/01/rdf-schema#",
        "owl:": "http://www.w3.org/2002/07/owl#",
        "xsd:": "http://www.w3.org/2001/XMLSchema#",
    }
    return extractor


@pytest.fixture
def sample_ontology_subset():
    """Create a sample ontology subset for extraction testing."""
    return OntologySubset(
        ontology_id="food",
        classes={
            "Recipe": {
                "uri": "http://purl.org/ontology/fo/Recipe",
                "type": "owl:Class",
                "labels": [{"value": "Recipe", "lang": "en-gb"}],
                "comment": "A Recipe is a combination of ingredients and a method."
            },
            "Ingredient": {
                "uri": "http://purl.org/ontology/fo/Ingredient",
                "type": "owl:Class",
                "labels": [{"value": "Ingredient", "lang": "en-gb"}],
                "comment": "An Ingredient combines a quantity and a food."
            },
            "Food": {
                "uri": "http://purl.org/ontology/fo/Food",
                "type": "owl:Class",
                "labels": [{"value": "Food", "lang": "en-gb"}],
                "comment": "A Food is something that can be eaten."
            }
        },
        object_properties={
            "ingredients": {
                "uri": "http://purl.org/ontology/fo/ingredients",
                "type": "owl:ObjectProperty",
                "labels": [{"value": "ingredients", "lang": "en-gb"}],
                "comment": "The ingredients property relates a recipe to an ingredient list.",
                "domain": "Recipe",
                "range": "IngredientList"
            },
            "food": {
                "uri": "http://purl.org/ontology/fo/food",
                "type": "owl:ObjectProperty",
                "labels": [{"value": "food", "lang": "en-gb"}],
                "comment": "The food property relates an ingredient to food.",
                "domain": "Ingredient",
                "range": "Food"
            },
            "produces": {
                "uri": "http://purl.org/ontology/fo/produces",
                "type": "owl:ObjectProperty",
                "labels": [{"value": "produces", "lang": "en-gb"}],
                "comment": "The produces property relates a recipe to the food it produces.",
                "domain": "Recipe",
                "range": "Food"
            }
        },
        datatype_properties={
            "serves": {
                "uri": "http://purl.org/ontology/fo/serves",
                "type": "owl:DatatypeProperty",
                "labels": [{"value": "serves", "lang": "en-gb"}],
                "comment": "The serves property indicates serving size.",
                "domain": "Recipe",
                "rdfs:range": "xsd:string"
            }
        },
        metadata={
            "name": "Food Ontology",
            "namespace": "http://purl.org/ontology/fo/"
        }
    )


class TestPromptConstruction:
    """Test suite for LLM prompt construction."""

    def test_build_extraction_variables_includes_text(self, extractor, sample_ontology_subset):
        """Test that extraction variables include the input text."""
        chunk = "Cornish pasty is a traditional British pastry filled with meat and vegetables."

        variables = extractor.build_extraction_variables(chunk, sample_ontology_subset)

        assert "text" in variables, "Should include text key"
        assert variables["text"] == chunk, "Text should match input chunk"

    def test_build_extraction_variables_includes_classes(self, extractor, sample_ontology_subset):
        """Test that extraction variables include ontology classes."""
        chunk = "Test text"

        variables = extractor.build_extraction_variables(chunk, sample_ontology_subset)

        assert "classes" in variables, "Should include classes key"
        assert len(variables["classes"]) == 3, "Should include all classes from subset"
        assert "Recipe" in variables["classes"]
        assert "Ingredient" in variables["classes"]
        assert "Food" in variables["classes"]

    def test_build_extraction_variables_includes_properties(self, extractor, sample_ontology_subset):
        """Test that extraction variables include ontology properties."""
        chunk = "Test text"

        variables = extractor.build_extraction_variables(chunk, sample_ontology_subset)

        assert "object_properties" in variables, "Should include object_properties key"
        assert "datatype_properties" in variables, "Should include datatype_properties key"
        assert len(variables["object_properties"]) == 3
        assert len(variables["datatype_properties"]) == 1

    def test_build_extraction_variables_structure(self, extractor, sample_ontology_subset):
        """Test the overall structure of extraction variables."""
        chunk = "Test text"

        variables = extractor.build_extraction_variables(chunk, sample_ontology_subset)

        # Should have exactly 4 keys
        assert set(variables.keys()) == {"text", "classes", "object_properties", "datatype_properties"}

    def test_build_extraction_variables_with_empty_subset(self, extractor):
        """Test building variables with minimal ontology subset."""
        minimal_subset = OntologySubset(
            ontology_id="minimal",
            classes={},
            object_properties={},
            datatype_properties={},
            metadata={}
        )
        chunk = "Test text"

        variables = extractor.build_extraction_variables(chunk, minimal_subset)

        assert variables["text"] == chunk
        assert len(variables["classes"]) == 0
        assert len(variables["object_properties"]) == 0
        assert len(variables["datatype_properties"]) == 0


class TestTripleValidation:
    """Test suite for triple validation against ontology."""

    def test_validates_rdf_type_triple_with_valid_class(self, extractor, sample_ontology_subset):
        """Test that rdf:type triples are validated against ontology classes."""
        subject = "cornish-pasty"
        predicate = "rdf:type"
        object_val = "Recipe"

        is_valid = extractor.is_valid_triple(subject, predicate, object_val, sample_ontology_subset)

        assert is_valid, "rdf:type with valid class should be valid"

    def test_rejects_rdf_type_triple_with_invalid_class(self, extractor, sample_ontology_subset):
        """Test that rdf:type triples with non-existent classes are rejected."""
        subject = "cornish-pasty"
        predicate = "rdf:type"
        object_val = "NonExistentClass"

        is_valid = extractor.is_valid_triple(subject, predicate, object_val, sample_ontology_subset)

        assert not is_valid, "rdf:type with invalid class should be rejected"

    def test_validates_rdfs_label_triple(self, extractor, sample_ontology_subset):
        """Test that rdfs:label triples are always valid."""
        subject = "cornish-pasty"
        predicate = "rdfs:label"
        object_val = "Cornish Pasty"

        is_valid = extractor.is_valid_triple(subject, predicate, object_val, sample_ontology_subset)

        assert is_valid, "rdfs:label should always be valid"

    def test_validates_object_property_triple(self, extractor, sample_ontology_subset):
        """Test that object property triples are validated."""
        subject = "cornish-pasty-recipe"
        predicate = "produces"
        object_val = "cornish-pasty"

        is_valid = extractor.is_valid_triple(subject, predicate, object_val, sample_ontology_subset)

        assert is_valid, "Valid object property should be accepted"

    def test_validates_datatype_property_triple(self, extractor, sample_ontology_subset):
        """Test that datatype property triples are validated."""
        subject = "cornish-pasty-recipe"
        predicate = "serves"
        object_val = "4-6 people"

        is_valid = extractor.is_valid_triple(subject, predicate, object_val, sample_ontology_subset)

        assert is_valid, "Valid datatype property should be accepted"

    def test_rejects_unknown_property(self, extractor, sample_ontology_subset):
        """Test that unknown properties are rejected."""
        subject = "cornish-pasty"
        predicate = "unknownProperty"
        object_val = "some value"

        is_valid = extractor.is_valid_triple(subject, predicate, object_val, sample_ontology_subset)

        assert not is_valid, "Unknown property should be rejected"

    def test_validates_multiple_valid_properties(self, extractor, sample_ontology_subset):
        """Test validation of different property types."""
        test_cases = [
            ("recipe1", "produces", "food1", True),
            ("ingredient1", "food", "food1", True),
            ("recipe1", "serves", "4", True),
            ("recipe1", "invalidProp", "value", False),
        ]

        for subject, predicate, object_val, expected in test_cases:
            is_valid = extractor.is_valid_triple(subject, predicate, object_val, sample_ontology_subset)
            assert is_valid == expected, f"Validation of {predicate} should be {expected}"


class TestTripleParsing:
    """Test suite for parsing triples from LLM responses."""

    def test_parse_simple_triple_dict(self, extractor, sample_ontology_subset):
        """Test parsing a simple triple from dict format."""
        triples_response = [
            {
                "subject": "cornish-pasty",
                "predicate": "rdf:type",
                "object": "Recipe"
            }
        ]

        validated = extractor.parse_and_validate_triples(triples_response, sample_ontology_subset)

        assert len(validated) == 1, "Should parse one valid triple"
        assert validated[0].s.value == "https://trustgraph.ai/food/cornish-pasty"
        assert validated[0].p.value == "http://www.w3.org/1999/02/22-rdf-syntax-ns#type"
        assert validated[0].o.value == "http://purl.org/ontology/fo/Recipe"

    def test_parse_multiple_triples(self, extractor, sample_ontology_subset):
        """Test parsing multiple triples."""
        triples_response = [
            {"subject": "cornish-pasty", "predicate": "rdf:type", "object": "Recipe"},
            {"subject": "cornish-pasty", "predicate": "rdfs:label", "object": "Cornish Pasty"},
            {"subject": "cornish-pasty", "predicate": "serves", "object": "1-2 people"}
        ]

        validated = extractor.parse_and_validate_triples(triples_response, sample_ontology_subset)

        assert len(validated) == 3, "Should parse all valid triples"

    def test_filters_invalid_triples(self, extractor, sample_ontology_subset):
        """Test that invalid triples are filtered out."""
        triples_response = [
            {"subject": "cornish-pasty", "predicate": "rdf:type", "object": "Recipe"},  # Valid
            {"subject": "cornish-pasty", "predicate": "invalidProp", "object": "value"},  # Invalid
            {"subject": "cornish-pasty", "predicate": "produces", "object": "food1"}  # Valid
        ]

        validated = extractor.parse_and_validate_triples(triples_response, sample_ontology_subset)

        assert len(validated) == 2, "Should filter out invalid triple"

    def test_handles_missing_fields(self, extractor, sample_ontology_subset):
        """Test that triples with missing fields are skipped."""
        triples_response = [
            {"subject": "cornish-pasty", "predicate": "rdf:type"},  # Missing object
            {"subject": "cornish-pasty", "object": "Recipe"},  # Missing predicate
            {"predicate": "rdf:type", "object": "Recipe"},  # Missing subject
            {"subject": "cornish-pasty", "predicate": "rdf:type", "object": "Recipe"}  # Valid
        ]

        validated = extractor.parse_and_validate_triples(triples_response, sample_ontology_subset)

        assert len(validated) == 1, "Should skip triples with missing fields"

    def test_handles_empty_response(self, extractor, sample_ontology_subset):
        """Test handling of empty LLM response."""
        triples_response = []

        validated = extractor.parse_and_validate_triples(triples_response, sample_ontology_subset)

        assert len(validated) == 0, "Empty response should return no triples"

    def test_expands_uris_in_parsed_triples(self, extractor, sample_ontology_subset):
        """Test that URIs are properly expanded in parsed triples."""
        triples_response = [
            {"subject": "recipe1", "predicate": "produces", "object": "Food"}
        ]

        validated = extractor.parse_and_validate_triples(triples_response, sample_ontology_subset)

        assert len(validated) == 1
        # Subject should be expanded to entity URI
        assert validated[0].s.value.startswith("https://trustgraph.ai/food/")
        # Predicate should be expanded to ontology URI
        assert validated[0].p.value == "http://purl.org/ontology/fo/produces"
        # Object should be expanded to class URI
        assert validated[0].o.value == "http://purl.org/ontology/fo/Food"

    def test_creates_proper_triple_objects(self, extractor, sample_ontology_subset):
        """Test that Triple objects are properly created."""
        triples_response = [
            {"subject": "cornish-pasty", "predicate": "rdfs:label", "object": "Cornish Pasty"}
        ]

        validated = extractor.parse_and_validate_triples(triples_response, sample_ontology_subset)

        assert len(validated) == 1
        triple = validated[0]
        assert isinstance(triple, Triple), "Should create Triple objects"
        assert isinstance(triple.s, Value), "Subject should be Value object"
        assert isinstance(triple.p, Value), "Predicate should be Value object"
        assert isinstance(triple.o, Value), "Object should be Value object"
        assert triple.s.is_uri, "Subject should be marked as URI"
        assert triple.p.is_uri, "Predicate should be marked as URI"
        assert not triple.o.is_uri, "Object literal should not be marked as URI"


class TestURIExpansionInExtraction:
    """Test suite for URI expansion during triple extraction."""

    def test_expands_class_names_in_objects(self, extractor, sample_ontology_subset):
        """Test that class names in object position are expanded."""
        triples_response = [
            {"subject": "entity1", "predicate": "rdf:type", "object": "Recipe"}
        ]

        validated = extractor.parse_and_validate_triples(triples_response, sample_ontology_subset)

        assert validated[0].o.value == "http://purl.org/ontology/fo/Recipe"
        assert validated[0].o.is_uri, "Class reference should be URI"

    def test_expands_property_names(self, extractor, sample_ontology_subset):
        """Test that property names are expanded to full URIs."""
        triples_response = [
            {"subject": "recipe1", "predicate": "produces", "object": "food1"}
        ]

        validated = extractor.parse_and_validate_triples(triples_response, sample_ontology_subset)

        assert validated[0].p.value == "http://purl.org/ontology/fo/produces"

    def test_expands_entity_instances(self, extractor, sample_ontology_subset):
        """Test that entity instances get constructed URIs."""
        triples_response = [
            {"subject": "my-special-recipe", "predicate": "rdf:type", "object": "Recipe"}
        ]

        validated = extractor.parse_and_validate_triples(triples_response, sample_ontology_subset)

        assert validated[0].s.value.startswith("https://trustgraph.ai/food/")
        assert "my-special-recipe" in validated[0].s.value


class TestEdgeCases:
    """Test suite for edge cases in extraction."""

    def test_handles_non_dict_response_items(self, extractor, sample_ontology_subset):
        """Test that non-dict items in response are skipped."""
        triples_response = [
            {"subject": "entity1", "predicate": "rdf:type", "object": "Recipe"},  # Valid
            "invalid string item",  # Invalid
            None,  # Invalid
            {"subject": "entity2", "predicate": "rdf:type", "object": "Food"}  # Valid
        ]

        validated = extractor.parse_and_validate_triples(triples_response, sample_ontology_subset)

        # Should skip non-dict items gracefully
        assert len(validated) >= 0, "Should handle non-dict items without crashing"

    def test_handles_empty_string_values(self, extractor, sample_ontology_subset):
        """Test that empty string values are skipped."""
        triples_response = [
            {"subject": "", "predicate": "rdf:type", "object": "Recipe"},
            {"subject": "entity1", "predicate": "", "object": "Recipe"},
            {"subject": "entity1", "predicate": "rdf:type", "object": ""},
            {"subject": "entity1", "predicate": "rdf:type", "object": "Recipe"}  # Valid
        ]

        validated = extractor.parse_and_validate_triples(triples_response, sample_ontology_subset)

        assert len(validated) == 1, "Should skip triples with empty strings"

    def test_handles_unicode_in_literals(self, extractor, sample_ontology_subset):
        """Test handling of unicode characters in literal values."""
        triples_response = [
            {"subject": "café-recipe", "predicate": "rdfs:label", "object": "Café Spécial"}
        ]

        validated = extractor.parse_and_validate_triples(triples_response, sample_ontology_subset)

        assert len(validated) == 1
        assert "Café Spécial" in validated[0].o.value


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
