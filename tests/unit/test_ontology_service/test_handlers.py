"""
Unit tests for Processor._handle_list and Processor._full_subset_response.
These build OntologyResponse objects from internal state.
"""

import json
import pytest
from unittest.mock import MagicMock
from trustgraph.ontology.service import (
    OntologyElement, ParsedOntology, OntologyState, Processor,
)


def _make_ontology(ont_id, namespace, num_classes=2, num_obj=1, num_dt=1):
    ont = ParsedOntology(ontology_id=ont_id, namespace=namespace)
    for i in range(num_classes):
        cid = f"{ont_id}_Class{i}"
        ont.classes[cid] = OntologyElement(
            element_id=cid, element_type="class",
            uri=f"{namespace}{cid}",
            labels=[{"value": cid, "lang": "en"}],
            comment=f"Description of {cid}",
        )
    for i in range(num_obj):
        pid = f"{ont_id}_objProp{i}"
        ont.object_properties[pid] = OntologyElement(
            element_id=pid, element_type="objectProperty",
            uri=f"{namespace}{pid}",
            domain=f"{ont_id}_Class0" if num_classes > 0 else "",
            range=f"{ont_id}_Class1" if num_classes > 1 else "",
        )
    for i in range(num_dt):
        pid = f"{ont_id}_dtProp{i}"
        ont.datatype_properties[pid] = OntologyElement(
            element_id=pid, element_type="datatypeProperty",
            uri=f"{namespace}{pid}",
            domain=f"{ont_id}_Class0" if num_classes > 0 else "",
            range="string",
        )
    return ont


@pytest.fixture
def processor():
    p = object.__new__(Processor)
    p.ontology_states = {}
    return p


class TestHandleList:

    def test_empty_workspace(self, processor):
        flow = MagicMock()
        flow.workspace = "default"

        response = processor._handle_list(flow)

        assert response.operation == "list"
        assert response.ontologies == []
        assert response.error is None

    def test_lists_ready_ontology(self, processor):
        ont = _make_ontology("food", "http://food.org/", 3, 2, 1)
        state = OntologyState(
            ontology=ont, state="ready", elements_embedded=6
        )
        processor.ontology_states["ws1"] = {"food": state}

        flow = MagicMock()
        flow.workspace = "ws1"

        response = processor._handle_list(flow)

        assert len(response.ontologies) == 1
        info = response.ontologies[0]
        assert info.ontology_id == "food"
        assert info.state == "ready"
        assert info.classes_total == 3
        assert info.properties_total == 3  # 2 obj + 1 dt
        assert info.elements_embedded == 6

    def test_lists_error_ontology(self, processor):
        ont = ParsedOntology(ontology_id="bad", namespace="")
        state = OntologyState(
            ontology=ont, state="error",
            error_message="Parse failed",
        )
        processor.ontology_states["ws1"] = {"bad": state}

        flow = MagicMock()
        flow.workspace = "ws1"

        response = processor._handle_list(flow)

        info = response.ontologies[0]
        assert info.state == "error"
        assert info.error_message == "Parse failed"

    def test_lists_multiple_ontologies(self, processor):
        ont1 = _make_ontology("a", "http://a/", 1, 0, 0)
        ont2 = _make_ontology("b", "http://b/", 2, 1, 0)
        processor.ontology_states["ws1"] = {
            "a": OntologyState(ontology=ont1, state="ready"),
            "b": OntologyState(ontology=ont2, state="loading"),
        }

        flow = MagicMock()
        flow.workspace = "ws1"

        response = processor._handle_list(flow)

        assert len(response.ontologies) == 2
        ids = {o.ontology_id for o in response.ontologies}
        assert ids == {"a", "b"}


class TestFullSubsetResponse:

    def test_returns_all_elements(self, processor):
        ont = _make_ontology("food", "http://food.org/", 2, 1, 1)
        ready = {"food": OntologyState(ontology=ont, state="ready")}

        response = processor._full_subset_response(ready)

        assert response.operation == "subset"
        assert response.ontology_id == "food"
        assert response.namespace == "http://food.org/"
        assert len(response.classes) == 2
        assert len(response.object_properties) == 1
        assert len(response.datatype_properties) == 1

    def test_classes_are_json_encoded(self, processor):
        ont = _make_ontology("food", "http://food.org/", 1, 0, 0)
        ready = {"food": OntologyState(ontology=ont, state="ready")}

        response = processor._full_subset_response(ready)

        for cid, val in response.classes.items():
            parsed = json.loads(val)
            assert "uri" in parsed

    def test_merges_multiple_ontologies(self, processor):
        ont1 = _make_ontology("a", "http://a/", 1, 0, 0)
        ont2 = _make_ontology("b", "http://b/", 2, 1, 0)
        ready = {
            "a": OntologyState(ontology=ont1, state="ready"),
            "b": OntologyState(ontology=ont2, state="ready"),
        }

        response = processor._full_subset_response(ready)

        assert len(response.classes) == 3  # 1 + 2
        assert len(response.object_properties) == 1

    def test_empty_ready_states(self, processor):
        response = processor._full_subset_response({})

        assert response.ontology_id == ""
        assert response.classes == {}
        assert response.object_properties == {}
        assert response.datatype_properties == {}
