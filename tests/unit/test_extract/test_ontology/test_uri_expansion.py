"""
Unit tests for URI expansion functionality.

Tests that URIs are properly expanded using ontology definitions instead of
constructed fallback URIs.
"""

import pytest
from trustgraph.extract.kg.ontology.extract import Processor
from trustgraph.extract.kg.ontology.ontology_selector import OntologySubset


class MockParams:
    """Mock parameters for Processor."""
    def get(self, key, default=None):
        return default


@pytest.fixture
def extractor():
    """Create a Processor instance for testing."""
    params = MockParams()
    # We only need the expand_uri method, so minimal initialization
    extractor = object.__new__(Processor)
    extractor.URI_PREFIXES = {
        "rdf:": "http://www.w3.org/1999/02/22-rdf-syntax-ns#",
        "rdfs:": "http://www.w3.org/2000/01/rdf-schema#",
        "owl:": "http://www.w3.org/2002/07/owl#",
        "xsd:": "http://www.w3.org/2001/XMLSchema#",
    }
    return extractor


@pytest.fixture
def ontology_subset_with_uris():
    """Create an ontology subset with proper URIs defined."""
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
                "domain": "Recipe",
                "range": "IngredientList"
            },
            "food": {
                "uri": "http://purl.org/ontology/fo/food",
                "type": "owl:ObjectProperty",
                "labels": [{"value": "food", "lang": "en-gb"}],
                "domain": "Ingredient",
                "range": "Food"
            },
            "produces": {
                "uri": "http://purl.org/ontology/fo/produces",
                "type": "owl:ObjectProperty",
                "labels": [{"value": "produces", "lang": "en-gb"}],
                "domain": "Recipe",
                "range": "Food"
            }
        },
        datatype_properties={
            "serves": {
                "uri": "http://purl.org/ontology/fo/serves",
                "type": "owl:DatatypeProperty",
                "labels": [{"value": "serves", "lang": "en-gb"}],
                "domain": "Recipe",
                "range": "xsd:string"
            }
        },
        metadata={
            "name": "Food Ontology",
            "namespace": "http://purl.org/ontology/fo/"
        }
    )


class TestURIExpansion:
    """Test suite for URI expansion functionality."""

    def test_expand_class_uri_from_ontology(self, extractor, ontology_subset_with_uris):
        """Test that class names are expanded to their ontology URIs."""
        result = extractor.expand_uri("Recipe", ontology_subset_with_uris, "food")

        assert result == "http://purl.org/ontology/fo/Recipe", \
            "Recipe should expand to its ontology URI"

    def test_expand_object_property_uri_from_ontology(self, extractor, ontology_subset_with_uris):
        """Test that object properties are expanded to their ontology URIs."""
        result = extractor.expand_uri("ingredients", ontology_subset_with_uris, "food")

        assert result == "http://purl.org/ontology/fo/ingredients", \
            "ingredients property should expand to its ontology URI"

    def test_expand_datatype_property_uri_from_ontology(self, extractor, ontology_subset_with_uris):
        """Test that datatype properties are expanded to their ontology URIs."""
        result = extractor.expand_uri("serves", ontology_subset_with_uris, "food")

        assert result == "http://purl.org/ontology/fo/serves", \
            "serves property should expand to its ontology URI"

    def test_expand_multiple_classes(self, extractor, ontology_subset_with_uris):
        """Test expansion of multiple different classes."""
        recipe_uri = extractor.expand_uri("Recipe", ontology_subset_with_uris, "food")
        ingredient_uri = extractor.expand_uri("Ingredient", ontology_subset_with_uris, "food")
        food_uri = extractor.expand_uri("Food", ontology_subset_with_uris, "food")

        assert recipe_uri == "http://purl.org/ontology/fo/Recipe"
        assert ingredient_uri == "http://purl.org/ontology/fo/Ingredient"
        assert food_uri == "http://purl.org/ontology/fo/Food"

    def test_expand_rdf_prefix(self, extractor, ontology_subset_with_uris):
        """Test that standard RDF prefixes are expanded."""
        result = extractor.expand_uri("rdf:type", ontology_subset_with_uris, "food")

        assert result == "http://www.w3.org/1999/02/22-rdf-syntax-ns#type", \
            "rdf:type should expand to full RDF namespace URI"

    def test_expand_rdfs_prefix(self, extractor, ontology_subset_with_uris):
        """Test that RDFS prefixes are expanded."""
        result = extractor.expand_uri("rdfs:label", ontology_subset_with_uris, "food")

        assert result == "http://www.w3.org/2000/01/rdf-schema#label", \
            "rdfs:label should expand to full RDFS namespace URI"

    def test_expand_owl_prefix(self, extractor, ontology_subset_with_uris):
        """Test that OWL prefixes are expanded."""
        result = extractor.expand_uri("owl:Class", ontology_subset_with_uris, "food")

        assert result == "http://www.w3.org/2002/07/owl#Class", \
            "owl:Class should expand to full OWL namespace URI"

    def test_expand_xsd_prefix(self, extractor, ontology_subset_with_uris):
        """Test that XSD prefixes are expanded."""
        result = extractor.expand_uri("xsd:string", ontology_subset_with_uris, "food")

        assert result == "http://www.w3.org/2001/XMLSchema#string", \
            "xsd:string should expand to full XSD namespace URI"

    def test_fallback_uri_for_instance(self, extractor, ontology_subset_with_uris):
        """Test that entity instances get constructed URIs when not in ontology."""
        result = extractor.expand_uri("recipe:cornish-pasty", ontology_subset_with_uris, "food")

        # Should construct a URI for the instance
        assert result.startswith("https://trustgraph.ai/food/"), \
            "Entity instance should get constructed URI under trustgraph.ai domain"
        assert "cornish-pasty" in result.lower(), \
            "Instance URI should include normalized entity name"

    def test_already_full_uri_unchanged(self, extractor, ontology_subset_with_uris):
        """Test that full URIs are returned unchanged."""
        full_uri = "http://example.com/custom/entity"
        result = extractor.expand_uri(full_uri, ontology_subset_with_uris, "food")

        assert result == full_uri, \
            "Full URIs should be returned unchanged"

    def test_https_uri_unchanged(self, extractor, ontology_subset_with_uris):
        """Test that HTTPS URIs are returned unchanged."""
        full_uri = "https://example.com/custom/entity"
        result = extractor.expand_uri(full_uri, ontology_subset_with_uris, "food")

        assert result == full_uri, \
            "HTTPS URIs should be returned unchanged"

    def test_class_without_uri_gets_fallback(self, extractor):
        """Test that classes without URI definitions get constructed fallback URIs."""
        # Create subset with class that has no URI
        subset_no_uri = OntologySubset(
            ontology_id="test",
            classes={
                "SomeClass": {
                    "type": "owl:Class",
                    "labels": [{"value": "Some Class"}],
                    # No 'uri' field
                }
            },
            object_properties={},
            datatype_properties={},
            metadata={}
        )

        result = extractor.expand_uri("SomeClass", subset_no_uri, "test")

        assert result == "https://trustgraph.ai/ontology/test#SomeClass", \
            "Class without URI should get fallback constructed URI"

    def test_property_without_uri_gets_fallback(self, extractor):
        """Test that properties without URI definitions get constructed fallback URIs."""
        subset_no_uri = OntologySubset(
            ontology_id="test",
            classes={},
            object_properties={
                "someProperty": {
                    "type": "owl:ObjectProperty",
                    # No 'uri' field
                }
            },
            datatype_properties={},
            metadata={}
        )

        result = extractor.expand_uri("someProperty", subset_no_uri, "test")

        assert result == "https://trustgraph.ai/ontology/test#someProperty", \
            "Property without URI should get fallback constructed URI"

    def test_entity_normalization_in_constructed_uri(self, extractor, ontology_subset_with_uris):
        """Test that entity names are normalized when constructing URIs."""
        # Entity with spaces and mixed case
        result = extractor.expand_uri("Cornish Pasty Recipe", ontology_subset_with_uris, "food")

        # Should be normalized: lowercase, spaces to hyphens
        assert result == "https://trustgraph.ai/food/cornish-pasty-recipe", \
            "Entity names should be normalized (lowercase, spaces to hyphens)"

    def test_dict_access_not_object_attribute(self, extractor, ontology_subset_with_uris):
        """Test that URI expansion works with dict access (not object attributes).

        This is the key fix - ontology_selector stores cls.__dict__ which means
        we get dicts, not objects, so we must use dict key access.
        """
        # The ontology_subset_with_uris uses dicts (with 'uri' key)
        # This test verifies we can access it correctly
        class_def = ontology_subset_with_uris.classes["Recipe"]

        # Verify it's a dict
        assert isinstance(class_def, dict), "Class definitions should be dicts"
        assert "uri" in class_def, "Dict should have 'uri' key"

        # Now test expansion works
        result = extractor.expand_uri("Recipe", ontology_subset_with_uris, "food")
        assert result == class_def["uri"], \
            "URI expansion must work with dict access (not object attributes)"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
