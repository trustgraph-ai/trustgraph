"""
Tests for provenance vocabulary bootstrap.
"""

import pytest

from trustgraph.schema import Triple, Term, IRI, LITERAL

from trustgraph.provenance.vocabulary import (
    get_vocabulary_triples,
    PROV_CLASS_LABELS,
    PROV_PREDICATE_LABELS,
    DC_PREDICATE_LABELS,
    SCHEMA_LABELS,
    SKOS_LABELS,
    TG_CLASS_LABELS,
    TG_PREDICATE_LABELS,
)

from trustgraph.provenance.namespaces import (
    RDFS_LABEL,
    PROV_ENTITY, PROV_ACTIVITY, PROV_AGENT,
    PROV_WAS_DERIVED_FROM, PROV_WAS_GENERATED_BY,
    PROV_USED, PROV_WAS_ASSOCIATED_WITH, PROV_STARTED_AT_TIME,
    DC_TITLE, DC_SOURCE, DC_DATE, DC_CREATOR,
    TG_DOCUMENT_TYPE, TG_PAGE_TYPE, TG_CHUNK_TYPE, TG_SUBGRAPH_TYPE,
)


class TestVocabularyTriples:
    """Tests for the vocabulary bootstrap function."""

    def test_returns_list_of_triples(self):
        result = get_vocabulary_triples()
        assert isinstance(result, list)
        assert len(result) > 0
        for t in result:
            assert isinstance(t, Triple)

    def test_all_triples_are_label_triples(self):
        """Every vocabulary triple should use rdfs:label as predicate."""
        for t in get_vocabulary_triples():
            assert t.p.type == IRI
            assert t.p.iri == RDFS_LABEL

    def test_all_subjects_are_iris(self):
        for t in get_vocabulary_triples():
            assert t.s.type == IRI
            assert len(t.s.iri) > 0

    def test_all_objects_are_literals(self):
        for t in get_vocabulary_triples():
            assert t.o.type == LITERAL
            assert len(t.o.value) > 0

    def test_no_duplicate_subjects(self):
        subjects = [t.s.iri for t in get_vocabulary_triples()]
        assert len(subjects) == len(set(subjects))

    def test_includes_prov_classes(self):
        subjects = {t.s.iri for t in get_vocabulary_triples()}
        assert PROV_ENTITY in subjects
        assert PROV_ACTIVITY in subjects
        assert PROV_AGENT in subjects

    def test_includes_prov_predicates(self):
        subjects = {t.s.iri for t in get_vocabulary_triples()}
        assert PROV_WAS_DERIVED_FROM in subjects
        assert PROV_WAS_GENERATED_BY in subjects
        assert PROV_USED in subjects
        assert PROV_WAS_ASSOCIATED_WITH in subjects
        assert PROV_STARTED_AT_TIME in subjects

    def test_includes_dc_predicates(self):
        subjects = {t.s.iri for t in get_vocabulary_triples()}
        assert DC_TITLE in subjects
        assert DC_SOURCE in subjects
        assert DC_DATE in subjects
        assert DC_CREATOR in subjects

    def test_includes_tg_classes(self):
        subjects = {t.s.iri for t in get_vocabulary_triples()}
        assert TG_DOCUMENT_TYPE in subjects
        assert TG_PAGE_TYPE in subjects
        assert TG_CHUNK_TYPE in subjects
        assert TG_SUBGRAPH_TYPE in subjects

    def test_component_lists_sum_to_total(self):
        total = get_vocabulary_triples()
        components = (
            PROV_CLASS_LABELS +
            PROV_PREDICATE_LABELS +
            DC_PREDICATE_LABELS +
            SCHEMA_LABELS +
            SKOS_LABELS +
            TG_CLASS_LABELS +
            TG_PREDICATE_LABELS
        )
        assert len(total) == len(components)

    def test_idempotent(self):
        """Calling twice should return equivalent triples."""
        r1 = get_vocabulary_triples()
        r2 = get_vocabulary_triples()
        assert len(r1) == len(r2)
        for t1, t2 in zip(r1, r2):
            assert t1.s.iri == t2.s.iri
            assert t1.o.value == t2.o.value


class TestNamespaceConstants:
    """Verify namespace constants are well-formed IRIs."""

    def test_prov_namespace_prefix(self):
        assert PROV_ENTITY.startswith("http://www.w3.org/ns/prov#")

    def test_dc_namespace_prefix(self):
        assert DC_TITLE.startswith("http://purl.org/dc/elements/1.1/")

    def test_tg_namespace_prefix(self):
        assert TG_DOCUMENT_TYPE.startswith("https://trustgraph.ai/ns/")

    def test_rdfs_label_iri(self):
        assert RDFS_LABEL == "http://www.w3.org/2000/01/rdf-schema#label"
