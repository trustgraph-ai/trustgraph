"""
Tests for provenance triple builder functions (extraction-time and query-time).
"""

import pytest
from unittest.mock import patch

from trustgraph.schema import Triple, Term, IRI, LITERAL, TRIPLE

from trustgraph.provenance.triples import (
    set_graph,
    document_triples,
    derived_entity_triples,
    subgraph_provenance_triples,
    question_triples,
    grounding_triples,
    exploration_triples,
    focus_triples,
    synthesis_triples,
    docrag_question_triples,
    docrag_exploration_triples,
    docrag_synthesis_triples,
)

from trustgraph.provenance.namespaces import (
    RDF_TYPE, RDFS_LABEL,
    PROV_ENTITY, PROV_ACTIVITY, PROV_AGENT,
    PROV_WAS_DERIVED_FROM, PROV_WAS_GENERATED_BY,
    PROV_USED, PROV_WAS_ASSOCIATED_WITH, PROV_STARTED_AT_TIME,
    DC_TITLE, DC_SOURCE, DC_DATE, DC_CREATOR,
    TG_PAGE_COUNT, TG_MIME_TYPE, TG_PAGE_NUMBER,
    TG_CHUNK_INDEX, TG_CHAR_OFFSET, TG_CHAR_LENGTH,
    TG_CHUNK_SIZE, TG_CHUNK_OVERLAP, TG_COMPONENT_VERSION,
    TG_LLM_MODEL, TG_ONTOLOGY, TG_CONTAINS,
    TG_DOCUMENT_TYPE, TG_PAGE_TYPE, TG_CHUNK_TYPE, TG_SUBGRAPH_TYPE,
    TG_QUERY, TG_CONCEPT, TG_ENTITY,
    TG_EDGE_COUNT, TG_SELECTED_EDGE, TG_EDGE, TG_REASONING,
    TG_DOCUMENT,
    TG_CHUNK_COUNT, TG_SELECTED_CHUNK,
    TG_QUESTION, TG_GROUNDING, TG_EXPLORATION, TG_FOCUS, TG_SYNTHESIS,
    TG_ANSWER_TYPE,
    TG_GRAPH_RAG_QUESTION, TG_DOC_RAG_QUESTION,
    GRAPH_SOURCE, GRAPH_RETRIEVAL,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def find_triple(triples, predicate, subject=None):
    """Find first triple matching predicate (and optionally subject)."""
    for t in triples:
        if t.p.iri == predicate:
            if subject is None or t.s.iri == subject:
                return t
    return None


def find_triples(triples, predicate, subject=None):
    """Find all triples matching predicate (and optionally subject)."""
    return [
        t for t in triples
        if t.p.iri == predicate and (subject is None or t.s.iri == subject)
    ]


def has_type(triples, subject, rdf_type):
    """Check if subject has rdf:type rdf_type."""
    for t in triples:
        if (t.s.iri == subject and t.p.iri == RDF_TYPE
                and t.o.type == IRI and t.o.iri == rdf_type):
            return True
    return False


# ---------------------------------------------------------------------------
# set_graph
# ---------------------------------------------------------------------------

class TestSetGraph:

    def test_sets_graph_on_all_triples(self):
        triples = [
            Triple(
                s=Term(type=IRI, iri="urn:s1"),
                p=Term(type=IRI, iri="urn:p1"),
                o=Term(type=LITERAL, value="v1"),
            ),
            Triple(
                s=Term(type=IRI, iri="urn:s2"),
                p=Term(type=IRI, iri="urn:p2"),
                o=Term(type=LITERAL, value="v2"),
            ),
        ]
        result = set_graph(triples, GRAPH_RETRIEVAL)
        assert len(result) == 2
        for t in result:
            assert t.g == GRAPH_RETRIEVAL

    def test_does_not_modify_originals(self):
        original = Triple(
            s=Term(type=IRI, iri="urn:s"),
            p=Term(type=IRI, iri="urn:p"),
            o=Term(type=LITERAL, value="v"),
        )
        result = set_graph([original], "urn:graph:test")
        assert original.g is None
        assert result[0].g == "urn:graph:test"

    def test_empty_list(self):
        result = set_graph([], GRAPH_SOURCE)
        assert result == []

    def test_preserves_spo(self):
        original = Triple(
            s=Term(type=IRI, iri="urn:s"),
            p=Term(type=IRI, iri="urn:p"),
            o=Term(type=LITERAL, value="hello"),
        )
        result = set_graph([original], "urn:g")[0]
        assert result.s.iri == "urn:s"
        assert result.p.iri == "urn:p"
        assert result.o.value == "hello"


# ---------------------------------------------------------------------------
# document_triples
# ---------------------------------------------------------------------------

class TestDocumentTriples:

    DOC_URI = "https://example.com/doc/abc"

    def test_minimal_document(self):
        triples = document_triples(self.DOC_URI)
        assert has_type(triples, self.DOC_URI, PROV_ENTITY)
        assert has_type(triples, self.DOC_URI, TG_DOCUMENT_TYPE)
        assert len(triples) == 2

    def test_with_title(self):
        triples = document_triples(self.DOC_URI, title="My Doc")
        title_t = find_triple(triples, DC_TITLE)
        assert title_t is not None
        assert title_t.o.value == "My Doc"
        # Title also creates an rdfs:label
        label_t = find_triple(triples, RDFS_LABEL)
        assert label_t is not None
        assert label_t.o.value == "My Doc"

    def test_with_source(self):
        triples = document_triples(self.DOC_URI, source="https://source.com/f.pdf")
        source_t = find_triple(triples, DC_SOURCE)
        assert source_t is not None
        assert source_t.o.type == IRI
        assert source_t.o.iri == "https://source.com/f.pdf"

    def test_with_date(self):
        triples = document_triples(self.DOC_URI, date="2024-01-15")
        date_t = find_triple(triples, DC_DATE)
        assert date_t is not None
        assert date_t.o.value == "2024-01-15"

    def test_with_creator(self):
        triples = document_triples(self.DOC_URI, creator="Alice")
        creator_t = find_triple(triples, DC_CREATOR)
        assert creator_t is not None
        assert creator_t.o.value == "Alice"

    def test_with_page_count(self):
        triples = document_triples(self.DOC_URI, page_count=42)
        pc_t = find_triple(triples, TG_PAGE_COUNT)
        assert pc_t is not None
        assert pc_t.o.value == "42"

    def test_with_page_count_zero(self):
        triples = document_triples(self.DOC_URI, page_count=0)
        pc_t = find_triple(triples, TG_PAGE_COUNT)
        assert pc_t is not None
        assert pc_t.o.value == "0"

    def test_with_mime_type(self):
        triples = document_triples(self.DOC_URI, mime_type="application/pdf")
        mt_t = find_triple(triples, TG_MIME_TYPE)
        assert mt_t is not None
        assert mt_t.o.value == "application/pdf"

    def test_all_metadata(self):
        triples = document_triples(
            self.DOC_URI,
            title="Test",
            source="https://s.com",
            date="2024-01-01",
            creator="Bob",
            page_count=10,
            mime_type="application/pdf",
        )
        # 2 type triples + title + label + source + date + creator + page_count + mime_type
        assert len(triples) == 9

    def test_subject_is_doc_uri(self):
        triples = document_triples(self.DOC_URI, title="T")
        for t in triples:
            assert t.s.iri == self.DOC_URI


# ---------------------------------------------------------------------------
# derived_entity_triples
# ---------------------------------------------------------------------------

class TestDerivedEntityTriples:

    ENTITY_URI = "https://example.com/doc/abc/p1"
    PARENT_URI = "https://example.com/doc/abc"

    def test_page_entity_has_page_type(self):
        triples = derived_entity_triples(
            self.ENTITY_URI, self.PARENT_URI,
            "pdf-extractor", "1.0",
            page_number=1,
            timestamp="2024-01-01T00:00:00Z",
        )
        assert has_type(triples, self.ENTITY_URI, PROV_ENTITY)
        assert has_type(triples, self.ENTITY_URI, TG_PAGE_TYPE)

    def test_chunk_entity_has_chunk_type(self):
        triples = derived_entity_triples(
            self.ENTITY_URI, self.PARENT_URI,
            "chunker", "1.0",
            chunk_index=0,
            timestamp="2024-01-01T00:00:00Z",
        )
        assert has_type(triples, self.ENTITY_URI, TG_CHUNK_TYPE)

    def test_no_specific_type_without_page_or_chunk(self):
        triples = derived_entity_triples(
            self.ENTITY_URI, self.PARENT_URI,
            "component", "1.0",
            timestamp="2024-01-01T00:00:00Z",
        )
        assert has_type(triples, self.ENTITY_URI, PROV_ENTITY)
        assert not has_type(triples, self.ENTITY_URI, TG_PAGE_TYPE)
        assert not has_type(triples, self.ENTITY_URI, TG_CHUNK_TYPE)

    def test_was_derived_from_parent(self):
        triples = derived_entity_triples(
            self.ENTITY_URI, self.PARENT_URI,
            "pdf-extractor", "1.0",
            timestamp="2024-01-01T00:00:00Z",
        )
        derived = find_triple(triples, PROV_WAS_DERIVED_FROM, self.ENTITY_URI)
        assert derived is not None
        assert derived.o.iri == self.PARENT_URI

    def test_activity_created(self):
        triples = derived_entity_triples(
            self.ENTITY_URI, self.PARENT_URI,
            "pdf-extractor", "1.0",
            timestamp="2024-01-01T00:00:00Z",
        )
        # Entity was generated by an activity
        gen = find_triple(triples, PROV_WAS_GENERATED_BY, self.ENTITY_URI)
        assert gen is not None
        act_uri = gen.o.iri

        # Activity has correct type and metadata
        assert has_type(triples, act_uri, PROV_ACTIVITY)

        # Activity used the parent
        used = find_triple(triples, PROV_USED, act_uri)
        assert used is not None
        assert used.o.iri == self.PARENT_URI

        # Activity has component version
        version = find_triple(triples, TG_COMPONENT_VERSION, act_uri)
        assert version is not None
        assert version.o.value == "1.0"

    def test_agent_created(self):
        triples = derived_entity_triples(
            self.ENTITY_URI, self.PARENT_URI,
            "pdf-extractor", "1.0",
            timestamp="2024-01-01T00:00:00Z",
        )
        # Find the agent URI via wasAssociatedWith
        gen = find_triple(triples, PROV_WAS_GENERATED_BY, self.ENTITY_URI)
        act_uri = gen.o.iri
        assoc = find_triple(triples, PROV_WAS_ASSOCIATED_WITH, act_uri)
        assert assoc is not None
        agt_uri = assoc.o.iri

        assert has_type(triples, agt_uri, PROV_AGENT)
        label = find_triple(triples, RDFS_LABEL, agt_uri)
        assert label is not None
        assert label.o.value == "pdf-extractor"

    def test_timestamp_recorded(self):
        triples = derived_entity_triples(
            self.ENTITY_URI, self.PARENT_URI,
            "pdf-extractor", "1.0",
            timestamp="2024-06-15T12:30:00Z",
        )
        ts = find_triple(triples, PROV_STARTED_AT_TIME)
        assert ts is not None
        assert ts.o.value == "2024-06-15T12:30:00Z"

    def test_default_timestamp_generated(self):
        triples = derived_entity_triples(
            self.ENTITY_URI, self.PARENT_URI,
            "pdf-extractor", "1.0",
        )
        ts = find_triple(triples, PROV_STARTED_AT_TIME)
        assert ts is not None
        assert len(ts.o.value) > 0

    def test_optional_label(self):
        triples = derived_entity_triples(
            self.ENTITY_URI, self.PARENT_URI,
            "pdf-extractor", "1.0",
            label="Page 1",
            timestamp="2024-01-01T00:00:00Z",
        )
        label = find_triple(triples, RDFS_LABEL, self.ENTITY_URI)
        assert label is not None
        assert label.o.value == "Page 1"

    def test_page_number_recorded(self):
        triples = derived_entity_triples(
            self.ENTITY_URI, self.PARENT_URI,
            "pdf-extractor", "1.0",
            page_number=3,
            timestamp="2024-01-01T00:00:00Z",
        )
        pn = find_triple(triples, TG_PAGE_NUMBER, self.ENTITY_URI)
        assert pn is not None
        assert pn.o.value == "3"

    def test_chunk_metadata_recorded(self):
        triples = derived_entity_triples(
            self.ENTITY_URI, self.PARENT_URI,
            "chunker", "2.0",
            chunk_index=5,
            char_offset=1000,
            char_length=500,
            chunk_size=512,
            chunk_overlap=64,
            timestamp="2024-01-01T00:00:00Z",
        )
        ci = find_triple(triples, TG_CHUNK_INDEX, self.ENTITY_URI)
        assert ci is not None and ci.o.value == "5"

        co = find_triple(triples, TG_CHAR_OFFSET, self.ENTITY_URI)
        assert co is not None and co.o.value == "1000"

        cl = find_triple(triples, TG_CHAR_LENGTH, self.ENTITY_URI)
        assert cl is not None and cl.o.value == "500"

        # chunk_size and chunk_overlap are on the activity, not the entity
        cs = find_triple(triples, TG_CHUNK_SIZE)
        assert cs is not None and cs.o.value == "512"

        ov = find_triple(triples, TG_CHUNK_OVERLAP)
        assert ov is not None and ov.o.value == "64"


# ---------------------------------------------------------------------------
# subgraph_provenance_triples
# ---------------------------------------------------------------------------

class TestSubgraphProvenanceTriples:

    SG_URI = "https://trustgraph.ai/subgraph/test-sg"
    CHUNK_URI = "https://example.com/doc/abc/p1/c0"

    def _make_extracted_triple(self, s="urn:e:Alice", p="urn:r:knows", o="urn:e:Bob"):
        return Triple(
            s=Term(type=IRI, iri=s),
            p=Term(type=IRI, iri=p),
            o=Term(type=IRI, iri=o),
        )

    def test_contains_quoted_triples(self):
        extracted = [self._make_extracted_triple()]
        triples = subgraph_provenance_triples(
            self.SG_URI, extracted, self.CHUNK_URI,
            "kg-extractor", "1.0",
            timestamp="2024-01-01T00:00:00Z",
        )
        contains = find_triples(triples, TG_CONTAINS, self.SG_URI)
        assert len(contains) == 1
        assert contains[0].o.type == TRIPLE
        assert contains[0].o.triple.s.iri == "urn:e:Alice"
        assert contains[0].o.triple.p.iri == "urn:r:knows"
        assert contains[0].o.triple.o.iri == "urn:e:Bob"

    def test_multiple_extracted_triples(self):
        extracted = [
            self._make_extracted_triple("urn:e:A", "urn:r:x", "urn:e:B"),
            self._make_extracted_triple("urn:e:C", "urn:r:y", "urn:e:D"),
            self._make_extracted_triple("urn:e:E", "urn:r:z", "urn:e:F"),
        ]
        triples = subgraph_provenance_triples(
            self.SG_URI, extracted, self.CHUNK_URI,
            "kg-extractor", "1.0",
            timestamp="2024-01-01T00:00:00Z",
        )
        contains = find_triples(triples, TG_CONTAINS, self.SG_URI)
        assert len(contains) == 3

    def test_empty_extracted_triples(self):
        triples = subgraph_provenance_triples(
            self.SG_URI, [], self.CHUNK_URI,
            "kg-extractor", "1.0",
            timestamp="2024-01-01T00:00:00Z",
        )
        contains = find_triples(triples, TG_CONTAINS, self.SG_URI)
        assert len(contains) == 0
        # Should still have subgraph provenance metadata
        assert has_type(triples, self.SG_URI, TG_SUBGRAPH_TYPE)

    def test_subgraph_has_correct_types(self):
        triples = subgraph_provenance_triples(
            self.SG_URI, [], self.CHUNK_URI,
            "kg-extractor", "1.0",
            timestamp="2024-01-01T00:00:00Z",
        )
        assert has_type(triples, self.SG_URI, PROV_ENTITY)
        assert has_type(triples, self.SG_URI, TG_SUBGRAPH_TYPE)

    def test_derived_from_chunk(self):
        triples = subgraph_provenance_triples(
            self.SG_URI, [], self.CHUNK_URI,
            "kg-extractor", "1.0",
            timestamp="2024-01-01T00:00:00Z",
        )
        derived = find_triple(triples, PROV_WAS_DERIVED_FROM, self.SG_URI)
        assert derived is not None
        assert derived.o.iri == self.CHUNK_URI

    def test_activity_and_agent(self):
        triples = subgraph_provenance_triples(
            self.SG_URI, [], self.CHUNK_URI,
            "kg-extractor", "1.0",
            timestamp="2024-01-01T00:00:00Z",
        )
        gen = find_triple(triples, PROV_WAS_GENERATED_BY, self.SG_URI)
        assert gen is not None
        act_uri = gen.o.iri

        assert has_type(triples, act_uri, PROV_ACTIVITY)

        used = find_triple(triples, PROV_USED, act_uri)
        assert used is not None
        assert used.o.iri == self.CHUNK_URI

        version = find_triple(triples, TG_COMPONENT_VERSION, act_uri)
        assert version is not None
        assert version.o.value == "1.0"

    def test_optional_llm_model(self):
        triples = subgraph_provenance_triples(
            self.SG_URI, [], self.CHUNK_URI,
            "kg-extractor", "1.0",
            llm_model="claude-3-opus",
            timestamp="2024-01-01T00:00:00Z",
        )
        llm = find_triple(triples, TG_LLM_MODEL)
        assert llm is not None
        assert llm.o.value == "claude-3-opus"

    def test_no_llm_model_when_omitted(self):
        triples = subgraph_provenance_triples(
            self.SG_URI, [], self.CHUNK_URI,
            "kg-extractor", "1.0",
            timestamp="2024-01-01T00:00:00Z",
        )
        llm = find_triple(triples, TG_LLM_MODEL)
        assert llm is None

    def test_optional_ontology(self):
        triples = subgraph_provenance_triples(
            self.SG_URI, [], self.CHUNK_URI,
            "kg-extractor", "1.0",
            ontology_uri="https://example.com/ontology/v1",
            timestamp="2024-01-01T00:00:00Z",
        )
        ont = find_triple(triples, TG_ONTOLOGY)
        assert ont is not None
        assert ont.o.type == IRI
        assert ont.o.iri == "https://example.com/ontology/v1"


# ---------------------------------------------------------------------------
# GraphRAG query-time triples
# ---------------------------------------------------------------------------

class TestQuestionTriples:

    Q_URI = "urn:trustgraph:question:test-session"

    def test_question_types(self):
        triples = question_triples(self.Q_URI, "What is AI?", "2024-01-01T00:00:00Z")
        assert has_type(triples, self.Q_URI, PROV_ENTITY)
        assert has_type(triples, self.Q_URI, TG_QUESTION)
        assert has_type(triples, self.Q_URI, TG_GRAPH_RAG_QUESTION)

    def test_question_query_text(self):
        triples = question_triples(self.Q_URI, "What is AI?", "2024-01-01T00:00:00Z")
        query = find_triple(triples, TG_QUERY, self.Q_URI)
        assert query is not None
        assert query.o.value == "What is AI?"

    def test_question_timestamp(self):
        triples = question_triples(self.Q_URI, "Q", "2024-06-15T10:00:00Z")
        ts = find_triple(triples, PROV_STARTED_AT_TIME, self.Q_URI)
        assert ts is not None
        assert ts.o.value == "2024-06-15T10:00:00Z"

    def test_question_default_timestamp(self):
        triples = question_triples(self.Q_URI, "Q")
        ts = find_triple(triples, PROV_STARTED_AT_TIME, self.Q_URI)
        assert ts is not None
        assert len(ts.o.value) > 0

    def test_question_label(self):
        triples = question_triples(self.Q_URI, "Q", "2024-01-01T00:00:00Z")
        label = find_triple(triples, RDFS_LABEL, self.Q_URI)
        assert label is not None
        assert label.o.value == "GraphRAG Question"

    def test_question_triple_count(self):
        triples = question_triples(self.Q_URI, "Q", "2024-01-01T00:00:00Z")
        assert len(triples) == 6


class TestGroundingTriples:

    GND_URI = "urn:trustgraph:prov:grounding:test-session"
    Q_URI = "urn:trustgraph:question:test-session"

    def test_grounding_types(self):
        triples = grounding_triples(self.GND_URI, self.Q_URI, ["AI", "ML"])
        assert has_type(triples, self.GND_URI, PROV_ENTITY)
        assert has_type(triples, self.GND_URI, TG_GROUNDING)

    def test_grounding_derived_from_question(self):
        triples = grounding_triples(self.GND_URI, self.Q_URI, ["AI"])
        derived = find_triple(triples, PROV_WAS_DERIVED_FROM, self.GND_URI)
        assert derived is not None
        assert derived.o.iri == self.Q_URI

    def test_grounding_concepts(self):
        triples = grounding_triples(self.GND_URI, self.Q_URI, ["AI", "ML", "robots"])
        concepts = find_triples(triples, TG_CONCEPT, self.GND_URI)
        assert len(concepts) == 3
        values = {t.o.value for t in concepts}
        assert values == {"AI", "ML", "robots"}

    def test_grounding_empty_concepts(self):
        triples = grounding_triples(self.GND_URI, self.Q_URI, [])
        concepts = find_triples(triples, TG_CONCEPT, self.GND_URI)
        assert len(concepts) == 0

    def test_grounding_label(self):
        triples = grounding_triples(self.GND_URI, self.Q_URI, [])
        label = find_triple(triples, RDFS_LABEL, self.GND_URI)
        assert label is not None
        assert label.o.value == "Grounding"


class TestExplorationTriples:

    EXP_URI = "urn:trustgraph:prov:exploration:test-session"
    GND_URI = "urn:trustgraph:prov:grounding:test-session"

    def test_exploration_types(self):
        triples = exploration_triples(self.EXP_URI, self.GND_URI, 15)
        assert has_type(triples, self.EXP_URI, PROV_ENTITY)
        assert has_type(triples, self.EXP_URI, TG_EXPLORATION)

    def test_exploration_derived_from_grounding(self):
        triples = exploration_triples(self.EXP_URI, self.GND_URI, 15)
        derived = find_triple(triples, PROV_WAS_DERIVED_FROM, self.EXP_URI)
        assert derived is not None
        assert derived.o.iri == self.GND_URI

    def test_exploration_edge_count(self):
        triples = exploration_triples(self.EXP_URI, self.GND_URI, 15)
        ec = find_triple(triples, TG_EDGE_COUNT, self.EXP_URI)
        assert ec is not None
        assert ec.o.value == "15"

    def test_exploration_zero_edges(self):
        triples = exploration_triples(self.EXP_URI, self.GND_URI, 0)
        ec = find_triple(triples, TG_EDGE_COUNT, self.EXP_URI)
        assert ec is not None
        assert ec.o.value == "0"

    def test_exploration_with_entities(self):
        entities = ["urn:e:machine-learning", "urn:e:neural-networks"]
        triples = exploration_triples(self.EXP_URI, self.GND_URI, 10, entities=entities)
        ent_triples = find_triples(triples, TG_ENTITY, self.EXP_URI)
        assert len(ent_triples) == 2

    def test_exploration_triple_count(self):
        triples = exploration_triples(self.EXP_URI, self.GND_URI, 10)
        assert len(triples) == 5


class TestFocusTriples:

    FOC_URI = "urn:trustgraph:prov:focus:test-session"
    EXP_URI = "urn:trustgraph:prov:exploration:test-session"
    SESSION_ID = "test-session"

    def test_focus_types(self):
        triples = focus_triples(self.FOC_URI, self.EXP_URI, [], self.SESSION_ID)
        assert has_type(triples, self.FOC_URI, PROV_ENTITY)
        assert has_type(triples, self.FOC_URI, TG_FOCUS)

    def test_focus_derived_from_exploration(self):
        triples = focus_triples(self.FOC_URI, self.EXP_URI, [], self.SESSION_ID)
        derived = find_triple(triples, PROV_WAS_DERIVED_FROM, self.FOC_URI)
        assert derived is not None
        assert derived.o.iri == self.EXP_URI

    def test_focus_no_edges(self):
        triples = focus_triples(self.FOC_URI, self.EXP_URI, [], self.SESSION_ID)
        selected = find_triples(triples, TG_SELECTED_EDGE)
        assert len(selected) == 0

    def test_focus_with_edges_and_reasoning(self):
        edges = [
            {
                "edge": ("urn:e:Alice", "urn:r:knows", "urn:e:Bob"),
                "reasoning": "Alice is connected to Bob",
            },
            {
                "edge": ("urn:e:Bob", "urn:r:worksAt", "urn:e:Acme"),
                "reasoning": "Bob works at Acme",
            },
        ]
        triples = focus_triples(self.FOC_URI, self.EXP_URI, edges, self.SESSION_ID)

        # Two selectedEdge links
        selected = find_triples(triples, TG_SELECTED_EDGE, self.FOC_URI)
        assert len(selected) == 2

        # Each edge selection has a quoted triple
        edge_triples = find_triples(triples, TG_EDGE)
        assert len(edge_triples) == 2
        for et in edge_triples:
            assert et.o.type == TRIPLE

        # Each edge selection has reasoning
        reasoning_triples = find_triples(triples, TG_REASONING)
        assert len(reasoning_triples) == 2

    def test_focus_edge_without_reasoning(self):
        edges = [
            {"edge": ("urn:e:A", "urn:r:x", "urn:e:B"), "reasoning": ""},
        ]
        triples = focus_triples(self.FOC_URI, self.EXP_URI, edges, self.SESSION_ID)
        reasoning = find_triples(triples, TG_REASONING)
        assert len(reasoning) == 0

    def test_focus_edge_without_edge_data(self):
        edges = [
            {"edge": None, "reasoning": "some reasoning"},
        ]
        triples = focus_triples(self.FOC_URI, self.EXP_URI, edges, self.SESSION_ID)
        selected = find_triples(triples, TG_SELECTED_EDGE)
        assert len(selected) == 0

    def test_focus_quoted_triple_content(self):
        edges = [
            {
                "edge": ("urn:e:Alice", "urn:r:knows", "urn:e:Bob"),
                "reasoning": "test",
            },
        ]
        triples = focus_triples(self.FOC_URI, self.EXP_URI, edges, self.SESSION_ID)
        edge_t = find_triple(triples, TG_EDGE)
        qt = edge_t.o.triple
        assert qt.s.iri == "urn:e:Alice"
        assert qt.p.iri == "urn:r:knows"
        assert qt.o.iri == "urn:e:Bob"


class TestSynthesisTriples:

    SYN_URI = "urn:trustgraph:prov:synthesis:test-session"
    FOC_URI = "urn:trustgraph:prov:focus:test-session"

    def test_synthesis_types(self):
        triples = synthesis_triples(self.SYN_URI, self.FOC_URI)
        assert has_type(triples, self.SYN_URI, PROV_ENTITY)
        assert has_type(triples, self.SYN_URI, TG_SYNTHESIS)
        assert has_type(triples, self.SYN_URI, TG_ANSWER_TYPE)

    def test_synthesis_derived_from_focus(self):
        triples = synthesis_triples(self.SYN_URI, self.FOC_URI)
        derived = find_triple(triples, PROV_WAS_DERIVED_FROM, self.SYN_URI)
        assert derived is not None
        assert derived.o.iri == self.FOC_URI

    def test_synthesis_with_document_reference(self):
        triples = synthesis_triples(
            self.SYN_URI, self.FOC_URI,
            document_id="urn:trustgraph:question:abc/answer",
        )
        doc = find_triple(triples, TG_DOCUMENT, self.SYN_URI)
        assert doc is not None
        assert doc.o.type == IRI
        assert doc.o.iri == "urn:trustgraph:question:abc/answer"

    def test_synthesis_no_document(self):
        triples = synthesis_triples(self.SYN_URI, self.FOC_URI)
        doc = find_triple(triples, TG_DOCUMENT, self.SYN_URI)
        assert doc is None


# ---------------------------------------------------------------------------
# DocumentRAG query-time triples
# ---------------------------------------------------------------------------

class TestDocRagQuestionTriples:

    Q_URI = "urn:trustgraph:docrag:test-session"

    def test_docrag_question_types(self):
        triples = docrag_question_triples(self.Q_URI, "Find info", "2024-01-01T00:00:00Z")
        assert has_type(triples, self.Q_URI, PROV_ENTITY)
        assert has_type(triples, self.Q_URI, TG_QUESTION)
        assert has_type(triples, self.Q_URI, TG_DOC_RAG_QUESTION)

    def test_docrag_question_label(self):
        triples = docrag_question_triples(self.Q_URI, "Q", "2024-01-01T00:00:00Z")
        label = find_triple(triples, RDFS_LABEL, self.Q_URI)
        assert label.o.value == "DocumentRAG Question"

    def test_docrag_question_query_text(self):
        triples = docrag_question_triples(self.Q_URI, "search query", "2024-01-01T00:00:00Z")
        query = find_triple(triples, TG_QUERY, self.Q_URI)
        assert query.o.value == "search query"


class TestDocRagExplorationTriples:

    EXP_URI = "urn:trustgraph:docrag:test/exploration"
    GND_URI = "urn:trustgraph:docrag:test/grounding"

    def test_docrag_exploration_types(self):
        triples = docrag_exploration_triples(self.EXP_URI, self.GND_URI, 5)
        assert has_type(triples, self.EXP_URI, PROV_ENTITY)
        assert has_type(triples, self.EXP_URI, TG_EXPLORATION)

    def test_docrag_exploration_derived_from_grounding(self):
        triples = docrag_exploration_triples(self.EXP_URI, self.GND_URI, 5)
        derived = find_triple(triples, PROV_WAS_DERIVED_FROM, self.EXP_URI)
        assert derived.o.iri == self.GND_URI

    def test_docrag_exploration_chunk_count(self):
        triples = docrag_exploration_triples(self.EXP_URI, self.GND_URI, 7)
        cc = find_triple(triples, TG_CHUNK_COUNT, self.EXP_URI)
        assert cc.o.value == "7"

    def test_docrag_exploration_without_chunk_ids(self):
        triples = docrag_exploration_triples(self.EXP_URI, self.GND_URI, 3)
        chunks = find_triples(triples, TG_SELECTED_CHUNK)
        assert len(chunks) == 0

    def test_docrag_exploration_with_chunk_ids(self):
        chunk_ids = ["urn:chunk:1", "urn:chunk:2", "urn:chunk:3"]
        triples = docrag_exploration_triples(self.EXP_URI, self.GND_URI, 3, chunk_ids)
        chunks = find_triples(triples, TG_SELECTED_CHUNK, self.EXP_URI)
        assert len(chunks) == 3
        chunk_uris = {t.o.iri for t in chunks}
        assert chunk_uris == set(chunk_ids)


class TestDocRagSynthesisTriples:

    SYN_URI = "urn:trustgraph:docrag:test/synthesis"
    EXP_URI = "urn:trustgraph:docrag:test/exploration"

    def test_docrag_synthesis_types(self):
        triples = docrag_synthesis_triples(self.SYN_URI, self.EXP_URI)
        assert has_type(triples, self.SYN_URI, PROV_ENTITY)
        assert has_type(triples, self.SYN_URI, TG_SYNTHESIS)

    def test_docrag_synthesis_derived_from_exploration(self):
        """DocRAG skips the focus step — synthesis derives from exploration."""
        triples = docrag_synthesis_triples(self.SYN_URI, self.EXP_URI)
        derived = find_triple(triples, PROV_WAS_DERIVED_FROM, self.SYN_URI)
        assert derived.o.iri == self.EXP_URI

    def test_docrag_synthesis_has_answer_type(self):
        triples = docrag_synthesis_triples(self.SYN_URI, self.EXP_URI)
        assert has_type(triples, self.SYN_URI, TG_ANSWER_TYPE)

    def test_docrag_synthesis_with_document(self):
        triples = docrag_synthesis_triples(
            self.SYN_URI, self.EXP_URI, document_id="urn:doc:ans"
        )
        doc = find_triple(triples, TG_DOCUMENT, self.SYN_URI)
        assert doc.o.iri == "urn:doc:ans"

    def test_docrag_synthesis_no_document(self):
        triples = docrag_synthesis_triples(self.SYN_URI, self.EXP_URI)
        doc = find_triple(triples, TG_DOCUMENT, self.SYN_URI)
        assert doc is None
