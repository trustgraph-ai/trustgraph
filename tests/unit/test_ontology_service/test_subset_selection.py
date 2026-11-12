"""
Unit tests for Processor._handle_subset — the core subset selection
logic. Uses a real InMemoryVectorStore with synthetic embeddings to
test the full selection path including bypass, similarity search,
and dependency resolution.
"""

import asyncio
import json
import numpy as np
import pytest
from unittest.mock import AsyncMock, MagicMock, patch

from trustgraph.ontology.service import (
    OntologyElement, ParsedOntology, OntologyState, Processor,
)
from trustgraph.extract.kg.ontology.vector_store import InMemoryVectorStore
from trustgraph.schema import OntologyRequest


DIMENSION = 8


def _random_vector():
    v = np.random.randn(DIMENSION).astype(np.float32)
    return v / np.linalg.norm(v)


def _make_element(eid, etype, uri, domain="", range_val=""):
    return OntologyElement(
        element_id=eid, element_type=etype, uri=uri,
        labels=[{"value": eid, "lang": "en"}],
        domain=domain, range=range_val,
    )


def _build_ontology():
    ont = ParsedOntology(
        ontology_id="test", namespace="http://example.org/"
    )
    ont.classes["Animal"] = _make_element(
        "Animal", "class", "http://example.org/Animal"
    )
    ont.classes["Dog"] = _make_element(
        "Dog", "class", "http://example.org/Dog"
    )
    ont.classes["Cat"] = _make_element(
        "Cat", "class", "http://example.org/Cat"
    )
    ont.classes["Person"] = _make_element(
        "Person", "class", "http://example.org/Person"
    )
    ont.classes["Vet"] = _make_element(
        "Vet", "class", "http://example.org/Vet"
    )
    ont.classes["Clinic"] = _make_element(
        "Clinic", "class", "http://example.org/Clinic"
    )
    ont.object_properties["owns"] = _make_element(
        "owns", "objectProperty", "http://example.org/owns",
        domain="Person", range_val="Dog",
    )
    ont.object_properties["treats"] = _make_element(
        "treats", "objectProperty", "http://example.org/treats",
        domain="Vet", range_val="Animal",
    )
    ont.datatype_properties["name"] = _make_element(
        "name", "datatypeProperty", "http://example.org/name",
        domain="Person", range_val="string",
    )
    return ont


def _build_vector_store(ontology):
    store = InMemoryVectorStore(dimension=DIMENSION, index_type='flat')

    vectors = {}
    all_elements = []

    for cid, cls in ontology.classes.items():
        eid = f"test:class:{cid}"
        vec = _random_vector()
        vectors[cid] = vec
        all_elements.append((eid, vec, {
            "type": "class",
            "ontology": "test",
            "element": cid,
            "definition": cls.to_dict(),
        }))

    for pid, prop in ontology.object_properties.items():
        eid = f"test:objectProperty:{pid}"
        vec = _random_vector()
        vectors[pid] = vec
        all_elements.append((eid, vec, {
            "type": "objectProperty",
            "ontology": "test",
            "element": pid,
            "definition": prop.to_dict(),
        }))

    for pid, prop in ontology.datatype_properties.items():
        eid = f"test:datatypeProperty:{pid}"
        vec = _random_vector()
        vectors[pid] = vec
        all_elements.append((eid, vec, {
            "type": "datatypeProperty",
            "ontology": "test",
            "element": pid,
            "definition": prop.to_dict(),
        }))

    ids = [e[0] for e in all_elements]
    vecs = np.array([e[1] for e in all_elements])
    metadata = [e[2] for e in all_elements]
    store.add_batch(ids, vecs, metadata)

    return store, vectors


@pytest.fixture
def setup():
    ontology = _build_ontology()
    store, vectors = _build_vector_store(ontology)

    p = object.__new__(Processor)
    p.top_k = 3
    p.similarity_threshold = 0.0
    p.bypass_selector_below = 5
    p.ontology_states = {
        "ws": {"test": OntologyState(ontology=ontology, state="ready")}
    }
    p.vector_stores = {"ws": store}
    p.ready_events = {"ws": asyncio.Event()}
    p.ready_events["ws"].set()

    return p, ontology, vectors


class TestSubsetBypass:

    @pytest.mark.asyncio
    async def test_bypasses_when_below_threshold(self, setup):
        processor, ontology, vectors = setup
        processor.bypass_selector_below = 100

        flow = MagicMock()
        flow.workspace = "ws"

        request = OntologyRequest(
            operation="subset", text="dogs",
        )

        response = await processor._handle_subset(flow, request)

        assert response.error is None
        assert len(response.classes) == len(ontology.classes)
        assert len(response.object_properties) == len(
            ontology.object_properties
        )
        assert len(response.datatype_properties) == len(
            ontology.datatype_properties
        )


class TestSubsetNoOntology:

    @pytest.mark.asyncio
    async def test_returns_error_when_no_ontologies(self):
        p = object.__new__(Processor)
        p.ontology_states = {"ws": {}}
        p.ready_events = {"ws": asyncio.Event()}
        p.ready_events["ws"].set()

        flow = MagicMock()
        flow.workspace = "ws"

        request = OntologyRequest(operation="subset", text="anything")
        response = await p._handle_subset(flow, request)

        assert response.error is not None
        assert response.error.type == "no-ontology"

    @pytest.mark.asyncio
    async def test_returns_error_when_all_errored(self):
        p = object.__new__(Processor)
        ont = ParsedOntology(ontology_id="bad", namespace="")
        p.ontology_states = {
            "ws": {"bad": OntologyState(
                ontology=ont, state="error",
                error_message="parse failed"
            )}
        }
        p.ready_events = {"ws": asyncio.Event()}
        p.ready_events["ws"].set()

        flow = MagicMock()
        flow.workspace = "ws"

        request = OntologyRequest(operation="subset", text="anything")
        response = await p._handle_subset(flow, request)

        assert response.error is not None


class TestSubsetSimilaritySearch:

    @pytest.mark.asyncio
    async def test_returns_subset_via_similarity(self, setup):
        processor, ontology, vectors = setup
        processor.bypass_selector_below = 0

        dog_vector = vectors["Dog"]

        mock_client = AsyncMock()
        mock_client.embed = AsyncMock(
            return_value=[dog_vector.tolist()]
        )

        flow = MagicMock()
        flow.workspace = "ws"
        flow.return_value = mock_client

        request = OntologyRequest(
            operation="subset", text="dogs",
            top_k=2, similarity_threshold=0.0,
        )

        response = await processor._handle_subset(flow, request)

        assert response.error is None
        assert response.operation == "subset"
        assert response.ontology_id == "test"
        assert response.namespace == "http://example.org/"
        assert len(response.classes) > 0

    @pytest.mark.asyncio
    async def test_embedding_failure_returns_error(self, setup):
        processor, ontology, vectors = setup
        processor.bypass_selector_below = 0

        mock_client = AsyncMock()
        mock_client.embed = AsyncMock(side_effect=RuntimeError("boom"))

        flow = MagicMock()
        flow.workspace = "ws"
        flow.return_value = mock_client

        request = OntologyRequest(
            operation="subset", text="dogs",
        )

        response = await processor._handle_subset(flow, request)

        assert response.error is not None
        assert response.error.type == "embedding-failed"

    @pytest.mark.asyncio
    async def test_uses_request_top_k(self, setup):
        processor, ontology, vectors = setup
        processor.bypass_selector_below = 0
        processor.top_k = 1

        query_vec = _random_vector()
        mock_client = AsyncMock()
        mock_client.embed = AsyncMock(
            return_value=[query_vec.tolist()]
        )

        flow = MagicMock()
        flow.workspace = "ws"
        flow.return_value = mock_client

        request = OntologyRequest(
            operation="subset", text="test",
            top_k=2, similarity_threshold=0.0,
        )

        response = await processor._handle_subset(flow, request)

        assert response.error is None

    @pytest.mark.asyncio
    async def test_falls_back_to_full_when_no_results(self, setup):
        processor, ontology, vectors = setup
        processor.bypass_selector_below = 0

        query_vec = _random_vector()
        mock_client = AsyncMock()
        mock_client.embed = AsyncMock(
            return_value=[query_vec.tolist()]
        )

        flow = MagicMock()
        flow.workspace = "ws"
        flow.return_value = mock_client

        request = OntologyRequest(
            operation="subset", text="test",
            top_k=3, similarity_threshold=0.999,
        )

        response = await processor._handle_subset(flow, request)

        assert response.error is None
        assert len(response.classes) == len(ontology.classes)
