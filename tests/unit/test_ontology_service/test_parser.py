"""
Unit tests for OntologyParser: JSON-LD parsing, local_name extraction,
and element construction.
"""

import json
import pytest
from trustgraph.ontology.service import OntologyParser


FOOD_ONTOLOGY_JSONLD = json.dumps({
    "@context": {
        "owl": "http://www.w3.org/2002/07/owl#",
        "rdfs": "http://www.w3.org/2000/01/rdf-schema#",
        "rdf": "http://www.w3.org/1999/02/22-rdf-syntax-ns#",
        "xsd": "http://www.w3.org/2001/XMLSchema#",
        "fo": "http://purl.org/ontology/fo/",
    },
    "@graph": [
        {
            "@id": "fo:Recipe",
            "@type": "owl:Class",
            "rdfs:label": {"@value": "Recipe", "@language": "en"},
            "rdfs:comment": "A combination of ingredients and a method.",
            "rdfs:subClassOf": {"@id": "fo:Food"},
        },
        {
            "@id": "fo:Food",
            "@type": "owl:Class",
            "rdfs:label": {"@value": "Food", "@language": "en"},
            "rdfs:comment": "Something that can be eaten.",
        },
        {
            "@id": "fo:ingredients",
            "@type": "owl:ObjectProperty",
            "rdfs:label": {"@value": "ingredients", "@language": "en"},
            "rdfs:comment": "Relates a recipe to its ingredients.",
            "rdfs:domain": {"@id": "fo:Recipe"},
            "rdfs:range": {"@id": "fo:Food"},
        },
        {
            "@id": "fo:inverseIngredients",
            "@type": "owl:ObjectProperty",
            "rdfs:label": {"@value": "inverse ingredients", "@language": "en"},
            "owl:inverseOf": {"@id": "fo:ingredients"},
        },
        {
            "@id": "fo:hasPrimaryIngredient",
            "@type": ["owl:ObjectProperty", "owl:FunctionalProperty"],
            "rdfs:label": {"@value": "has primary ingredient", "@language": "en"},
            "rdfs:domain": {"@id": "fo:Recipe"},
            "rdfs:range": {"@id": "fo:Food"},
        },
        {
            "@id": "fo:serves",
            "@type": "owl:DatatypeProperty",
            "rdfs:label": {"@value": "serves", "@language": "en"},
            "rdfs:comment": "Number of servings.",
            "rdfs:domain": {"@id": "fo:Recipe"},
            "rdfs:range": {"@id": "xsd:integer"},
        },
    ]
})


class TestLocalName:

    def test_hash_uri(self):
        assert OntologyParser.local_name(
            "http://example.org/ontology#Recipe"
        ) == "Recipe"

    def test_slash_uri(self):
        assert OntologyParser.local_name(
            "http://example.org/ontology/Recipe"
        ) == "Recipe"

    def test_hash_takes_precedence(self):
        assert OntologyParser.local_name(
            "http://example.org/path/to#Name"
        ) == "Name"

    def test_no_separator(self):
        assert OntologyParser.local_name("Recipe") == "Recipe"


class TestParseJsonld:

    @pytest.fixture
    def parsed(self):
        return OntologyParser.parse_jsonld("food", FOOD_ONTOLOGY_JSONLD)

    def test_ontology_id(self, parsed):
        assert parsed.ontology_id == "food"

    def test_namespace_detected(self, parsed):
        assert parsed.namespace != ""

    def test_classes_parsed(self, parsed):
        assert "Recipe" in parsed.classes
        assert "Food" in parsed.classes
        assert len(parsed.classes) == 2

    def test_class_uri(self, parsed):
        assert parsed.classes["Recipe"].uri == "http://purl.org/ontology/fo/Recipe"

    def test_class_labels(self, parsed):
        labels = parsed.classes["Recipe"].labels
        assert len(labels) == 1
        assert labels[0]["value"] == "Recipe"
        assert labels[0]["lang"] == "en"

    def test_class_comment(self, parsed):
        assert "combination of ingredients" in parsed.classes["Recipe"].comment

    def test_class_subclass_of(self, parsed):
        assert parsed.classes["Recipe"].subclass_of == "Food"

    def test_class_no_subclass(self, parsed):
        assert parsed.classes["Food"].subclass_of == ""

    def test_object_properties_parsed(self, parsed):
        assert "ingredients" in parsed.object_properties
        assert "inverseIngredients" in parsed.object_properties
        assert "hasPrimaryIngredient" in parsed.object_properties

    def test_object_property_domain_range(self, parsed):
        prop = parsed.object_properties["ingredients"]
        assert prop.domain == "Recipe"
        assert prop.range == "Food"

    def test_object_property_inverse_of(self, parsed):
        prop = parsed.object_properties["inverseIngredients"]
        assert prop.inverse_of == "ingredients"

    def test_object_property_functional(self, parsed):
        assert parsed.object_properties["hasPrimaryIngredient"].functional is True
        assert parsed.object_properties["ingredients"].functional is False

    def test_datatype_properties_parsed(self, parsed):
        assert "serves" in parsed.datatype_properties
        assert len(parsed.datatype_properties) == 1

    def test_datatype_property_domain(self, parsed):
        assert parsed.datatype_properties["serves"].domain == "Recipe"

    def test_datatype_property_range(self, parsed):
        assert parsed.datatype_properties["serves"].range == "integer"

    def test_datatype_property_comment(self, parsed):
        assert "servings" in parsed.datatype_properties["serves"].comment

    def test_total_elements(self, parsed):
        assert parsed.total_elements == 2 + 3 + 1  # classes + obj + dt


class TestParseJsonldEdgeCases:

    def test_empty_graph(self):
        jsonld = json.dumps({"@context": {}, "@graph": []})
        parsed = OntologyParser.parse_jsonld("empty", jsonld)
        assert parsed.total_elements == 0
        assert parsed.ontology_id == "empty"

    def test_class_without_label(self):
        jsonld = json.dumps({
            "@context": {
                "owl": "http://www.w3.org/2002/07/owl#",
                "rdf": "http://www.w3.org/1999/02/22-rdf-syntax-ns#",
            },
            "@graph": [
                {
                    "@id": "http://example.org/Unlabeled",
                    "@type": "owl:Class",
                }
            ]
        })
        parsed = OntologyParser.parse_jsonld("test", jsonld)
        assert "Unlabeled" in parsed.classes
        assert parsed.classes["Unlabeled"].labels == []
        assert parsed.classes["Unlabeled"].comment == ""

    def test_property_without_domain_range(self):
        jsonld = json.dumps({
            "@context": {
                "owl": "http://www.w3.org/2002/07/owl#",
                "rdf": "http://www.w3.org/1999/02/22-rdf-syntax-ns#",
            },
            "@graph": [
                {
                    "@id": "http://example.org/bare",
                    "@type": "owl:ObjectProperty",
                }
            ]
        })
        parsed = OntologyParser.parse_jsonld("test", jsonld)
        prop = parsed.object_properties["bare"]
        assert prop.domain == ""
        assert prop.range == ""
