"""
Unit tests for ontology service data classes:
OntologyElement, ParsedOntology, OntologyState.
"""

import pytest
from trustgraph.ontology.service import (
    OntologyElement, ParsedOntology, OntologyState,
)


class TestOntologyElement:

    def test_to_dict_includes_all_fields(self):
        elem = OntologyElement(
            element_id="Recipe",
            element_type="class",
            uri="http://example.org/Recipe",
            labels=[{"value": "Recipe", "lang": "en"}],
            comment="A recipe.",
            subclass_of="Food",
            domain="",
            range="",
            inverse_of="",
            functional=False,
        )
        d = elem.to_dict()
        assert d["uri"] == "http://example.org/Recipe"
        assert d["labels"] == [{"value": "Recipe", "lang": "en"}]
        assert d["comment"] == "A recipe."
        assert d["subclass_of"] == "Food"
        assert d["inverse_of"] == ""
        assert d["functional"] is False

    def test_to_dict_excludes_element_id_and_type(self):
        elem = OntologyElement(
            element_id="Recipe",
            element_type="class",
            uri="http://example.org/Recipe",
        )
        d = elem.to_dict()
        assert "element_id" not in d
        assert "element_type" not in d

    def test_to_dict_defaults(self):
        elem = OntologyElement(
            element_id="X",
            element_type="class",
            uri="http://example.org/X",
        )
        d = elem.to_dict()
        assert d["labels"] == []
        assert d["comment"] == ""
        assert d["subclass_of"] == ""
        assert d["domain"] == ""
        assert d["range"] == ""
        assert d["functional"] is False

    def test_to_dict_functional_property(self):
        elem = OntologyElement(
            element_id="hasParent",
            element_type="objectProperty",
            uri="http://example.org/hasParent",
            functional=True,
        )
        assert elem.to_dict()["functional"] is True


class TestParsedOntology:

    def test_total_elements_empty(self):
        ont = ParsedOntology(ontology_id="test", namespace="http://x/")
        assert ont.total_elements == 0

    def test_total_elements_counts_all_types(self):
        ont = ParsedOntology(ontology_id="test", namespace="http://x/")
        ont.classes["A"] = OntologyElement(
            element_id="A", element_type="class", uri="http://x/A"
        )
        ont.classes["B"] = OntologyElement(
            element_id="B", element_type="class", uri="http://x/B"
        )
        ont.object_properties["p1"] = OntologyElement(
            element_id="p1", element_type="objectProperty", uri="http://x/p1"
        )
        ont.datatype_properties["d1"] = OntologyElement(
            element_id="d1", element_type="datatypeProperty", uri="http://x/d1"
        )
        assert ont.total_elements == 4


class TestOntologyState:

    def test_default_state_is_loading(self):
        ont = ParsedOntology(ontology_id="test", namespace="")
        state = OntologyState(ontology=ont)
        assert state.state == "loading"
        assert state.elements_embedded == 0
        assert state.error_message == ""
