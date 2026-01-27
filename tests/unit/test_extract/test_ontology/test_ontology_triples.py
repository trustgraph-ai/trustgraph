"""
Unit tests for ontology triple generation.

Tests that ontology elements (classes and properties) are properly converted
to RDF triples with labels, comments, domains, and ranges so they appear in
the knowledge graph.
"""

import pytest
from trustgraph.extract.kg.ontology.extract import Processor
from trustgraph.extract.kg.ontology.ontology_selector import OntologySubset
from trustgraph.schema.core.primitives import Triple, Term, IRI, LITERAL


@pytest.fixture
def extractor():
    """Create a Processor instance for testing."""
    extractor = object.__new__(Processor)
    return extractor


@pytest.fixture
def sample_ontology_subset():
    """Create a sample ontology subset with classes and properties."""
    return OntologySubset(
        ontology_id="food",
        classes={
            "Recipe": {
                "uri": "http://purl.org/ontology/fo/Recipe",
                "type": "owl:Class",
                "labels": [{"value": "Recipe", "lang": "en-gb"}],
                "comment": "A Recipe is a combination of ingredients and a method.",
                "subclass_of": None
            },
            "Ingredient": {
                "uri": "http://purl.org/ontology/fo/Ingredient",
                "type": "owl:Class",
                "labels": [{"value": "Ingredient", "lang": "en-gb"}],
                "comment": "An Ingredient combines a quantity and a food.",
                "subclass_of": None
            },
            "Food": {
                "uri": "http://purl.org/ontology/fo/Food",
                "type": "owl:Class",
                "labels": [{"value": "Food", "lang": "en-gb"}],
                "comment": "A Food is something that can be eaten.",
                "subclass_of": None
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


class TestOntologyTripleGeneration:
    """Test suite for ontology triple generation."""

    def test_generates_class_type_triples(self, extractor, sample_ontology_subset):
        """Test that classes get rdf:type owl:Class triples."""
        triples = extractor.build_ontology_triples(sample_ontology_subset)

        # Find type triples for Recipe class
        recipe_type_triples = [
            t for t in triples
            if t.s.iri == "http://purl.org/ontology/fo/Recipe"
            and t.p.iri == "http://www.w3.org/1999/02/22-rdf-syntax-ns#type"
        ]

        assert len(recipe_type_triples) == 1, "Should generate exactly one type triple per class"
        assert recipe_type_triples[0].o.iri == "http://www.w3.org/2002/07/owl#Class", \
            "Class type should be owl:Class"

    def test_generates_class_labels(self, extractor, sample_ontology_subset):
        """Test that classes get rdfs:label triples."""
        triples = extractor.build_ontology_triples(sample_ontology_subset)

        # Find label triples for Recipe class
        recipe_label_triples = [
            t for t in triples
            if t.s.iri == "http://purl.org/ontology/fo/Recipe"
            and t.p.iri == "http://www.w3.org/2000/01/rdf-schema#label"
        ]

        assert len(recipe_label_triples) == 1, "Should generate label triple for class"
        assert recipe_label_triples[0].o.value == "Recipe", \
            "Label should match class label from ontology"
        assert recipe_label_triples[0].o.type == LITERAL, \
            "Label should be a literal, not URI"

    def test_generates_class_comments(self, extractor, sample_ontology_subset):
        """Test that classes get rdfs:comment triples."""
        triples = extractor.build_ontology_triples(sample_ontology_subset)

        # Find comment triples for Recipe class
        recipe_comment_triples = [
            t for t in triples
            if t.s.iri == "http://purl.org/ontology/fo/Recipe"
            and t.p.iri == "http://www.w3.org/2000/01/rdf-schema#comment"
        ]

        assert len(recipe_comment_triples) == 1, "Should generate comment triple for class"
        assert "combination of ingredients and a method" in recipe_comment_triples[0].o.value, \
            "Comment should match class description from ontology"

    def test_generates_object_property_type_triples(self, extractor, sample_ontology_subset):
        """Test that object properties get rdf:type owl:ObjectProperty triples."""
        triples = extractor.build_ontology_triples(sample_ontology_subset)

        # Find type triples for ingredients property
        ingredients_type_triples = [
            t for t in triples
            if t.s.iri == "http://purl.org/ontology/fo/ingredients"
            and t.p.iri == "http://www.w3.org/1999/02/22-rdf-syntax-ns#type"
        ]

        assert len(ingredients_type_triples) == 1, \
            "Should generate exactly one type triple per object property"
        assert ingredients_type_triples[0].o.iri == "http://www.w3.org/2002/07/owl#ObjectProperty", \
            "Object property type should be owl:ObjectProperty"

    def test_generates_object_property_labels(self, extractor, sample_ontology_subset):
        """Test that object properties get rdfs:label triples."""
        triples = extractor.build_ontology_triples(sample_ontology_subset)

        # Find label triples for ingredients property
        ingredients_label_triples = [
            t for t in triples
            if t.s.iri == "http://purl.org/ontology/fo/ingredients"
            and t.p.iri == "http://www.w3.org/2000/01/rdf-schema#label"
        ]

        assert len(ingredients_label_triples) == 1, \
            "Should generate label triple for object property"
        assert ingredients_label_triples[0].o.value == "ingredients", \
            "Label should match property label from ontology"

    def test_generates_object_property_domain(self, extractor, sample_ontology_subset):
        """Test that object properties get rdfs:domain triples."""
        triples = extractor.build_ontology_triples(sample_ontology_subset)

        # Find domain triples for ingredients property
        ingredients_domain_triples = [
            t for t in triples
            if t.s.iri == "http://purl.org/ontology/fo/ingredients"
            and t.p.iri == "http://www.w3.org/2000/01/rdf-schema#domain"
        ]

        assert len(ingredients_domain_triples) == 1, \
            "Should generate domain triple for object property"
        assert ingredients_domain_triples[0].o.iri == "http://purl.org/ontology/fo/Recipe", \
            "Domain should be Recipe class URI"
        assert ingredients_domain_triples[0].o.type == IRI, \
            "Domain should be a URI reference"

    def test_generates_object_property_range(self, extractor, sample_ontology_subset):
        """Test that object properties get rdfs:range triples."""
        triples = extractor.build_ontology_triples(sample_ontology_subset)

        # Find range triples for produces property
        produces_range_triples = [
            t for t in triples
            if t.s.iri == "http://purl.org/ontology/fo/produces"
            and t.p.iri == "http://www.w3.org/2000/01/rdf-schema#range"
        ]

        assert len(produces_range_triples) == 1, \
            "Should generate range triple for object property"
        assert produces_range_triples[0].o.iri == "http://purl.org/ontology/fo/Food", \
            "Range should be Food class URI"

    def test_generates_datatype_property_type_triples(self, extractor, sample_ontology_subset):
        """Test that datatype properties get rdf:type owl:DatatypeProperty triples."""
        triples = extractor.build_ontology_triples(sample_ontology_subset)

        # Find type triples for serves property
        serves_type_triples = [
            t for t in triples
            if t.s.iri == "http://purl.org/ontology/fo/serves"
            and t.p.iri == "http://www.w3.org/1999/02/22-rdf-syntax-ns#type"
        ]

        assert len(serves_type_triples) == 1, \
            "Should generate exactly one type triple per datatype property"
        assert serves_type_triples[0].o.iri == "http://www.w3.org/2002/07/owl#DatatypeProperty", \
            "Datatype property type should be owl:DatatypeProperty"

    def test_generates_datatype_property_range(self, extractor, sample_ontology_subset):
        """Test that datatype properties get rdfs:range triples with XSD types."""
        triples = extractor.build_ontology_triples(sample_ontology_subset)

        # Find range triples for serves property
        serves_range_triples = [
            t for t in triples
            if t.s.iri == "http://purl.org/ontology/fo/serves"
            and t.p.iri == "http://www.w3.org/2000/01/rdf-schema#range"
        ]

        assert len(serves_range_triples) == 1, \
            "Should generate range triple for datatype property"
        assert serves_range_triples[0].o.value == "http://www.w3.org/2001/XMLSchema#string", \
            "Range should be XSD type URI (xsd:string expanded)"

    def test_generates_triples_for_all_classes(self, extractor, sample_ontology_subset):
        """Test that triples are generated for all classes in the subset."""
        triples = extractor.build_ontology_triples(sample_ontology_subset)

        # Count unique class subjects
        class_subjects = set(
            t.s.iri for t in triples
            if t.p.iri == "http://www.w3.org/1999/02/22-rdf-syntax-ns#type"
            and t.o.value == "http://www.w3.org/2002/07/owl#Class"
        )

        assert len(class_subjects) == 3, \
            "Should generate triples for all 3 classes (Recipe, Ingredient, Food)"

    def test_generates_triples_for_all_properties(self, extractor, sample_ontology_subset):
        """Test that triples are generated for all properties in the subset."""
        triples = extractor.build_ontology_triples(sample_ontology_subset)

        # Count unique property subjects (object + datatype properties)
        property_subjects = set(
            t.s.iri for t in triples
            if t.p.iri == "http://www.w3.org/1999/02/22-rdf-syntax-ns#type"
            and ("ObjectProperty" in t.o.value or "DatatypeProperty" in t.o.value)
        )

        assert len(property_subjects) == 3, \
            "Should generate triples for all 3 properties (ingredients, produces, serves)"

    def test_uses_dict_field_names_not_rdf_names(self, extractor, sample_ontology_subset):
        """Test that triple generation works with dict field names (labels, comment, domain, range).

        This is critical - the ontology subset has dicts with Python field names,
        not RDF property names.
        """
        # Verify the subset uses dict field names
        recipe_def = sample_ontology_subset.classes["Recipe"]
        assert isinstance(recipe_def, dict), "Class definitions should be dicts"
        assert "labels" in recipe_def, "Should use 'labels' not 'rdfs:label'"
        assert "comment" in recipe_def, "Should use 'comment' not 'rdfs:comment'"

        # Now verify triple generation works
        triples = extractor.build_ontology_triples(sample_ontology_subset)

        # Should still generate proper RDF triples despite dict field names
        label_triples = [
            t for t in triples
            if t.p.iri == "http://www.w3.org/2000/01/rdf-schema#label"
        ]
        assert len(label_triples) > 0, \
            "Should generate rdfs:label triples from dict 'labels' field"

    def test_total_triple_count_is_reasonable(self, extractor, sample_ontology_subset):
        """Test that we generate a reasonable number of triples."""
        triples = extractor.build_ontology_triples(sample_ontology_subset)

        # Each class gets: type, label, comment (3 triples)
        # Each object property gets: type, label, comment, domain, range (5 triples)
        # Each datatype property gets: type, label, comment, domain, range (5 triples)
        # Expected: 3 classes * 3 + 2 object props * 5 + 1 datatype prop * 5 = 9 + 10 + 5 = 24

        assert len(triples) >= 20, \
            "Should generate substantial number of triples for ontology elements"
        assert len(triples) < 50, \
            "Should not generate excessive duplicate triples"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
