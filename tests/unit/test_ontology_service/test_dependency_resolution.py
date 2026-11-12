"""
Unit tests for Processor._resolve_dependencies — ensures that when
a subset of ontology elements is selected, related elements (parent
classes, domain/range classes, inverse properties, properties for
selected classes) are pulled in.
"""

import json
import pytest
from trustgraph.ontology.service import (
    OntologyElement, ParsedOntology, OntologyState, Processor,
)


def _make_class(cid, uri, subclass_of=""):
    return OntologyElement(
        element_id=cid,
        element_type="class",
        uri=uri,
        subclass_of=subclass_of,
    )


def _make_obj_prop(pid, uri, domain="", range_val="", inverse_of=""):
    return OntologyElement(
        element_id=pid,
        element_type="objectProperty",
        uri=uri,
        domain=domain,
        range=range_val,
        inverse_of=inverse_of,
    )


def _make_dt_prop(pid, uri, domain="", range_val=""):
    return OntologyElement(
        element_id=pid,
        element_type="datatypeProperty",
        uri=uri,
        domain=domain,
        range=range_val,
    )


@pytest.fixture
def ontology():
    ont = ParsedOntology(
        ontology_id="test",
        namespace="http://example.org/",
    )
    ont.classes["Animal"] = _make_class(
        "Animal", "http://example.org/Animal"
    )
    ont.classes["Dog"] = _make_class(
        "Dog", "http://example.org/Dog", subclass_of="Animal"
    )
    ont.classes["Person"] = _make_class(
        "Person", "http://example.org/Person"
    )
    ont.classes["Breed"] = _make_class(
        "Breed", "http://example.org/Breed"
    )
    ont.object_properties["owns"] = _make_obj_prop(
        "owns", "http://example.org/owns",
        domain="Person", range_val="Dog",
    )
    ont.object_properties["ownedBy"] = _make_obj_prop(
        "ownedBy", "http://example.org/ownedBy",
        domain="Dog", range_val="Person",
        inverse_of="owns",
    )
    ont.object_properties["hasBreed"] = _make_obj_prop(
        "hasBreed", "http://example.org/hasBreed",
        domain="Dog", range_val="Breed",
    )
    ont.datatype_properties["name"] = _make_dt_prop(
        "name", "http://example.org/name",
        domain="Person", range_val="string",
    )
    ont.datatype_properties["age"] = _make_dt_prop(
        "age", "http://example.org/age",
        domain="Dog", range_val="integer",
    )
    return ont


@pytest.fixture
def ready_states(ontology):
    state = OntologyState(ontology=ontology, state="ready")
    return {"test": state}


@pytest.fixture
def processor():
    return object.__new__(Processor)


class TestResolveDependencies:

    def test_adds_parent_class(self, processor, ready_states):
        classes = {"Dog": json.dumps({"uri": "http://example.org/Dog"})}
        obj_props = {}
        dt_props = {}

        processor._resolve_dependencies(
            "test", classes, obj_props, dt_props, ready_states
        )

        assert "Animal" in classes

    def test_adds_domain_class_for_object_property(
        self, processor, ready_states
    ):
        classes = {}
        obj_props = {"owns": json.dumps({"uri": "http://example.org/owns"})}
        dt_props = {}

        processor._resolve_dependencies(
            "test", classes, obj_props, dt_props, ready_states
        )

        assert "Person" in classes
        assert "Dog" in classes

    def test_adds_range_class_for_object_property(
        self, processor, ready_states
    ):
        classes = {"Person": json.dumps({"uri": "http://example.org/Person"})}
        obj_props = {"owns": json.dumps({"uri": "http://example.org/owns"})}
        dt_props = {}

        processor._resolve_dependencies(
            "test", classes, obj_props, dt_props, ready_states
        )

        assert "Dog" in classes

    def test_adds_domain_class_for_datatype_property(
        self, processor, ready_states
    ):
        classes = {}
        obj_props = {}
        dt_props = {"name": json.dumps({"uri": "http://example.org/name"})}

        processor._resolve_dependencies(
            "test", classes, obj_props, dt_props, ready_states
        )

        assert "Person" in classes

    def test_adds_inverse_property(self, processor, ready_states):
        classes = {}
        obj_props = {
            "ownedBy": json.dumps({"uri": "http://example.org/ownedBy"})
        }
        dt_props = {}

        processor._resolve_dependencies(
            "test", classes, obj_props, dt_props, ready_states
        )

        assert "owns" in obj_props

    def test_adds_properties_for_selected_class(
        self, processor, ready_states
    ):
        classes = {"Dog": json.dumps({"uri": "http://example.org/Dog"})}
        obj_props = {}
        dt_props = {}

        processor._resolve_dependencies(
            "test", classes, obj_props, dt_props, ready_states
        )

        assert "owns" in obj_props or "ownedBy" in obj_props
        assert "hasBreed" in obj_props
        assert "age" in dt_props

    def test_adds_classes_for_newly_added_properties(
        self, processor, ready_states
    ):
        classes = {"Dog": json.dumps({"uri": "http://example.org/Dog"})}
        obj_props = {}
        dt_props = {}

        processor._resolve_dependencies(
            "test", classes, obj_props, dt_props, ready_states
        )

        assert "Person" in classes
        assert "Breed" in classes

    def test_unknown_ontology_id_is_noop(self, processor, ready_states):
        classes = {"Dog": json.dumps({"uri": "http://example.org/Dog"})}
        obj_props = {}
        dt_props = {}
        original_classes = dict(classes)

        processor._resolve_dependencies(
            "nonexistent", classes, obj_props, dt_props, ready_states
        )

        assert classes == original_classes
        assert obj_props == {}

    def test_does_not_duplicate_existing_entries(
        self, processor, ready_states
    ):
        classes = {
            "Dog": json.dumps({"uri": "http://example.org/Dog"}),
            "Animal": json.dumps({"uri": "http://example.org/Animal"}),
        }
        obj_props = {}
        dt_props = {}

        processor._resolve_dependencies(
            "test", classes, obj_props, dt_props, ready_states
        )

        values = list(classes.values())
        ids = list(classes.keys())
        assert len(ids) == len(set(ids))
