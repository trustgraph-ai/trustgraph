"""
Tests for TripleConverter domain/range enforcement and
OntologySelector bypass for small ontologies.

Covers fixes for #908 (bypass_selector_below) and #920 (domain/range validation).
"""

import pytest
from unittest.mock import Mock, AsyncMock

from trustgraph.extract.kg.ontology.triple_converter import TripleConverter
from trustgraph.extract.kg.ontology.ontology_selector import (
    OntologySelector,
    OntologySubset,
)
from trustgraph.extract.kg.ontology.ontology_loader import (
    Ontology,
    OntologyClass,
    OntologyProperty,
)
from trustgraph.extract.kg.ontology.simplified_parser import (
    Relationship,
    Attribute,
)
from trustgraph.extract.kg.ontology.text_processor import TextSegment


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture
def ontology_subset():
    """Ontology subset with classes, hierarchy, and constrained properties."""
    return OntologySubset(
        ontology_id="test",
        classes={
            "Person": {
                "uri": "http://example.org/Person",
                "type": "owl:Class",
                "labels": [{"value": "Person"}],
                "subclass_of": None,
            },
            "Employee": {
                "uri": "http://example.org/Employee",
                "type": "owl:Class",
                "labels": [{"value": "Employee"}],
                "subclass_of": "Person",
            },
            "Manager": {
                "uri": "http://example.org/Manager",
                "type": "owl:Class",
                "labels": [{"value": "Manager"}],
                "subclass_of": "Employee",
            },
            "Company": {
                "uri": "http://example.org/Company",
                "type": "owl:Class",
                "labels": [{"value": "Company"}],
                "subclass_of": None,
            },
            "Product": {
                "uri": "http://example.org/Product",
                "type": "owl:Class",
                "labels": [{"value": "Product"}],
                "subclass_of": None,
            },
        },
        object_properties={
            "worksFor": {
                "uri": "http://example.org/worksFor",
                "type": "owl:ObjectProperty",
                "labels": [{"value": "works for"}],
                "domain": "Person",
                "range": "Company",
            },
            "manages": {
                "uri": "http://example.org/manages",
                "type": "owl:ObjectProperty",
                "labels": [{"value": "manages"}],
                "domain": "Manager",
                "range": "Employee",
            },
            "relatedTo": {
                "uri": "http://example.org/relatedTo",
                "type": "owl:ObjectProperty",
                "labels": [{"value": "related to"}],
                "domain": None,
                "range": None,
            },
        },
        datatype_properties={
            "employeeId": {
                "uri": "http://example.org/employeeId",
                "type": "owl:DatatypeProperty",
                "labels": [{"value": "employee ID"}],
                "domain": "Employee",
            },
            "description": {
                "uri": "http://example.org/description",
                "type": "owl:DatatypeProperty",
                "labels": [{"value": "description"}],
                "domain": None,
            },
        },
        metadata={"name": "Test Ontology"},
    )


@pytest.fixture
def converter(ontology_subset):
    return TripleConverter(ontology_subset=ontology_subset, ontology_id="test")


# ---------------------------------------------------------------------------
# Domain/range enforcement — relationships
# ---------------------------------------------------------------------------

class TestRelationshipDomainRange:

    def test_valid_domain_and_range(self, converter):
        rel = Relationship(
            subject="Alice", subject_type="Person",
            relation="worksFor",
            object="Acme Corp", object_type="Company",
        )
        triple = converter.convert_relationship(rel)
        assert triple is not None

    def test_domain_violation_rejected(self, converter):
        rel = Relationship(
            subject="Widget", subject_type="Product",
            relation="worksFor",
            object="Acme Corp", object_type="Company",
        )
        assert converter.convert_relationship(rel) is None

    def test_range_violation_rejected(self, converter):
        rel = Relationship(
            subject="Alice", subject_type="Person",
            relation="worksFor",
            object="Widget", object_type="Product",
        )
        assert converter.convert_relationship(rel) is None

    def test_both_domain_and_range_violated(self, converter):
        rel = Relationship(
            subject="Widget", subject_type="Product",
            relation="worksFor",
            object="Gadget", object_type="Product",
        )
        assert converter.convert_relationship(rel) is None


# ---------------------------------------------------------------------------
# Subclass acceptance
# ---------------------------------------------------------------------------

class TestSubclassAcceptance:

    def test_direct_subclass_matches_domain(self, converter):
        """Employee is subclass of Person; worksFor domain is Person."""
        rel = Relationship(
            subject="Bob", subject_type="Employee",
            relation="worksFor",
            object="Acme Corp", object_type="Company",
        )
        assert converter.convert_relationship(rel) is not None

    def test_transitive_subclass_matches_domain(self, converter):
        """Manager → Employee → Person; worksFor domain is Person."""
        rel = Relationship(
            subject="Carol", subject_type="Manager",
            relation="worksFor",
            object="Acme Corp", object_type="Company",
        )
        assert converter.convert_relationship(rel) is not None

    def test_subclass_matches_range(self, converter):
        """manages range is Employee; Manager is subclass of Employee."""
        rel = Relationship(
            subject="Carol", subject_type="Manager",
            relation="manages",
            object="Dave", object_type="Manager",
        )
        assert converter.convert_relationship(rel) is not None

    def test_superclass_does_not_match_subclass_constraint(self, converter):
        """manages domain is Manager; Person is NOT a subclass of Manager."""
        rel = Relationship(
            subject="Alice", subject_type="Person",
            relation="manages",
            object="Bob", object_type="Employee",
        )
        assert converter.convert_relationship(rel) is None


# ---------------------------------------------------------------------------
# Polymorphic properties (no domain/range)
# ---------------------------------------------------------------------------

class TestPolymorphicProperties:

    def test_no_domain_no_range_allows_anything(self, converter):
        rel = Relationship(
            subject="Alice", subject_type="Person",
            relation="relatedTo",
            object="Acme Corp", object_type="Company",
        )
        assert converter.convert_relationship(rel) is not None

    def test_polymorphic_with_unrelated_types(self, converter):
        rel = Relationship(
            subject="Widget", subject_type="Product",
            relation="relatedTo",
            object="Bob", object_type="Employee",
        )
        assert converter.convert_relationship(rel) is not None


# ---------------------------------------------------------------------------
# Datatype property domain enforcement
# ---------------------------------------------------------------------------

class TestAttributeDomainValidation:

    def test_valid_domain(self, converter):
        attr = Attribute(
            entity="Bob", entity_type="Employee",
            attribute="employeeId", value="E-1234",
        )
        assert converter.convert_attribute(attr) is not None

    def test_subclass_matches_domain(self, converter):
        """Manager is subclass of Employee; employeeId domain is Employee."""
        attr = Attribute(
            entity="Carol", entity_type="Manager",
            attribute="employeeId", value="M-5678",
        )
        assert converter.convert_attribute(attr) is not None

    def test_domain_violation_rejected(self, converter):
        attr = Attribute(
            entity="Acme Corp", entity_type="Company",
            attribute="employeeId", value="E-0000",
        )
        assert converter.convert_attribute(attr) is None

    def test_no_domain_allows_anything(self, converter):
        attr = Attribute(
            entity="Widget", entity_type="Product",
            attribute="description", value="A useful widget",
        )
        assert converter.convert_attribute(attr) is not None


# ---------------------------------------------------------------------------
# OntologySelector bypass for small ontologies (#908)
# ---------------------------------------------------------------------------

def _make_ontology(n_classes, n_obj_props=0, n_dt_props=0):
    classes = {
        f"C{i}": OntologyClass(uri=f"http://example.org/C{i}")
        for i in range(n_classes)
    }
    obj_props = {
        f"op{i}": OntologyProperty(
            uri=f"http://example.org/op{i}", type="owl:ObjectProperty"
        )
        for i in range(n_obj_props)
    }
    dt_props = {
        f"dp{i}": OntologyProperty(
            uri=f"http://example.org/dp{i}", type="owl:DatatypeProperty"
        )
        for i in range(n_dt_props)
    }
    return Ontology(
        id="tiny",
        metadata={"name": "Tiny"},
        classes=classes,
        object_properties=obj_props,
        datatype_properties=dt_props,
    )


def _make_loader(ontology):
    loader = Mock()
    loader.get_ontology.return_value = ontology
    loader.get_all_ontologies.return_value = {"tiny": ontology}
    return loader


class TestBypassSelectorBelow:

    async def test_bypass_returns_full_ontology(self):
        """With 3 elements and bypass_selector_below=5, selector is bypassed."""
        ont = _make_ontology(2, 1, 0)
        loader = _make_loader(ont)
        embedder = Mock()

        selector = OntologySelector(
            ontology_embedder=embedder,
            ontology_loader=loader,
            bypass_selector_below=5,
        )

        segments = [TextSegment(text="some text", type="sentence", position=0)]
        subsets = await selector.select_ontology_subset(segments)

        assert len(subsets) == 1
        assert subsets[0].ontology_id == "tiny"
        assert len(subsets[0].classes) == 2
        assert len(subsets[0].object_properties) == 1
        assert subsets[0].relevance_score == 1.0
        # Embedder should never be called
        embedder.embed_text.assert_not_called()

    async def test_no_bypass_when_above_threshold(self):
        """With 10 elements and bypass_selector_below=5, selector runs normally."""
        ont = _make_ontology(6, 3, 1)
        loader = _make_loader(ont)

        embedder = Mock()
        embedder.embed_text = AsyncMock(return_value=[0.1, 0.2])
        vector_store = Mock()
        vector_store.size.return_value = 10
        vector_store.search.return_value = []
        embedder.get_vector_store.return_value = vector_store

        selector = OntologySelector(
            ontology_embedder=embedder,
            ontology_loader=loader,
            bypass_selector_below=5,
        )

        segments = [TextSegment(text="some text", type="sentence", position=0)]
        subsets = await selector.select_ontology_subset(segments)

        # Vector store was consulted (selector ran normally)
        vector_store.size.assert_called_once()

    async def test_bypass_at_exact_threshold_not_triggered(self):
        """With exactly 5 elements and bypass_selector_below=5, selector runs (< not <=)."""
        ont = _make_ontology(3, 1, 1)  # total = 5
        loader = _make_loader(ont)

        embedder = Mock()
        embedder.embed_text = AsyncMock(return_value=[0.1, 0.2])
        vector_store = Mock()
        vector_store.size.return_value = 5
        vector_store.search.return_value = []
        embedder.get_vector_store.return_value = vector_store

        selector = OntologySelector(
            ontology_embedder=embedder,
            ontology_loader=loader,
            bypass_selector_below=5,
        )

        segments = [TextSegment(text="some text", type="sentence", position=0)]
        subsets = await selector.select_ontology_subset(segments)

        # Should NOT bypass — 5 is not < 5
        vector_store.size.assert_called_once()

    async def test_bypass_zero_disables(self):
        """bypass_selector_below=0 means bypass never triggers."""
        ont = _make_ontology(0, 0, 0)  # empty ontology
        loader = _make_loader(ont)

        embedder = Mock()
        embedder.embed_text = AsyncMock(return_value=[0.1])
        vector_store = Mock()
        vector_store.size.return_value = 0
        vector_store.search.return_value = []
        embedder.get_vector_store.return_value = vector_store

        selector = OntologySelector(
            ontology_embedder=embedder,
            ontology_loader=loader,
            bypass_selector_below=0,
        )

        segments = [TextSegment(text="some text", type="sentence", position=0)]
        subsets = await selector.select_ontology_subset(segments)

        # 0 is not < 0, so bypass doesn't trigger
        vector_store.size.assert_called_once()
