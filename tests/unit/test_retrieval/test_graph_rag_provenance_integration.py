"""
Integration test: run a full GraphRag.query() with mocked subsidiary clients
and verify the explain_callback receives the complete provenance chain
in the correct order with correct structure.

This tests the real query() method end-to-end, not just the triple builders.
"""

import json
import pytest
from unittest.mock import AsyncMock, MagicMock
from dataclasses import dataclass

from trustgraph.retrieval.graph_rag.graph_rag import GraphRag
from trustgraph.schema import (
    Triple as SchemaTriple, Term, IRI, LITERAL, TRIPLE,
    KnowledgeRetrievalResponse, RetrievedEdge,
)
from trustgraph.base import PromptResult
from trustgraph.base.triples_client import Triple as ClientTriple
from trustgraph.knowledge import Uri, Literal

from trustgraph.provenance.namespaces import (
    RDF_TYPE, PROV_ENTITY, PROV_WAS_DERIVED_FROM,
    TG_GRAPH_RAG_QUESTION, TG_GROUNDING, TG_EXPLORATION,
    TG_FOCUS, TG_SYNTHESIS, TG_ANSWER_TYPE,
    TG_QUERY, TG_CONCEPT, TG_ENTITY, TG_EDGE_COUNT,
    TG_SELECTED_EDGE, TG_EDGE, TG_SCORE, TG_EDGE_SELECTION,
    TG_CONTAINS, DC_TITLE, RDFS_LABEL,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def find_triple(triples, predicate, subject=None):
    for t in triples:
        if t.p.iri == predicate:
            if subject is None or t.s.iri == subject:
                return t
    return None


def find_triples(triples, predicate, subject=None):
    return [
        t for t in triples
        if t.p.iri == predicate
        and (subject is None or t.s.iri == subject)
    ]


def has_type(triples, subject, rdf_type):
    return any(
        t.s.iri == subject and t.p.iri == RDF_TYPE and t.o.iri == rdf_type
        for t in triples
    )


def derived_from(triples, subject):
    t = find_triple(triples, PROV_WAS_DERIVED_FROM, subject)
    return t.o.iri if t else None


# ---------------------------------------------------------------------------
# Mock setup
# ---------------------------------------------------------------------------

# A tiny knowledge graph: 2 entities, 3 edges
ENTITY_A = "http://example.com/QuantumComputing"
ENTITY_B = "http://example.com/Physics"
EDGE_1 = (ENTITY_A, "http://schema.org/relatedTo", ENTITY_B)
EDGE_2 = (ENTITY_A, "http://schema.org/name", "urn:literal:quantum-computing")
EDGE_3 = (ENTITY_B, "http://schema.org/name", "urn:literal:physics")


def build_mock_clients():
    """
    Build mock clients that simulate a small knowledge graph query.

    Client call sequence during query():
      1. concept_extraction_client.extract(query) -> concepts
      2. knowledge_retrieval_client.retrieve(concepts, ...) -> edges
      3. triples_client.query(o=quoted, p=TG_CONTAINS, ...) -> doc tracing
      4. prompt_client.prompt("kg-synthesis", ...) -> final answer
    """
    concept_extraction_client = AsyncMock()
    concept_extraction_client.extract.return_value = [
        "quantum computing", "physics",
    ]

    knowledge_retrieval_client = AsyncMock()
    knowledge_retrieval_client.retrieve.return_value = KnowledgeRetrievalResponse(
        edges=[
            RetrievedEdge(
                s=EDGE_1[0], p=EDGE_1[1], o=EDGE_1[2],
                s_label="Quantum Computing", p_label="related to",
                o_label="Physics", score=0.9, concept="quantum computing",
            ),
            RetrievedEdge(
                s=EDGE_2[0], p=EDGE_2[1], o=EDGE_2[2],
                s_label="Quantum Computing", p_label="name",
                o_label="Quantum Computing", score=0.8,
                concept="quantum computing",
            ),
            RetrievedEdge(
                s=EDGE_3[0], p=EDGE_3[1], o=EDGE_3[2],
                s_label="Physics", p_label="name",
                o_label="Physics", score=0.7, concept="physics",
            ),
        ],
        seed_entities=[ENTITY_A, ENTITY_B],
    )

    triples_client = AsyncMock()
    triples_client.query.return_value = []

    prompt_client = AsyncMock()
    synthesis_answer = "Quantum computing applies physics principles to computation."

    async def mock_prompt(template_id, variables=None, **kwargs):
        if template_id == "kg-synthesis":
            return PromptResult(
                response_type="text",
                text=synthesis_answer,
            )
        return PromptResult(response_type="text", text="")

    prompt_client.prompt.side_effect = mock_prompt

    return (concept_extraction_client, knowledge_retrieval_client,
            triples_client, prompt_client)


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------

class TestGraphRagQueryProvenance:
    """
    Run a real GraphRag.query() and verify the provenance chain emitted
    via explain_callback.
    """

    @pytest.mark.asyncio
    async def test_explain_callback_receives_five_events(self):
        """query() should emit exactly 5 explain events."""
        clients = build_mock_clients()
        rag = GraphRag(*clients)

        events = []

        async def explain_callback(triples, explain_id):
            events.append({"triples": triples, "explain_id": explain_id})

        await rag.query(
            query="What is quantum computing?",
            explain_callback=explain_callback,

        )

        assert len(events) == 5, (
            f"Expected 5 explain events (question, grounding, exploration, "
            f"focus, synthesis), got {len(events)}"
        )

    @pytest.mark.asyncio
    async def test_events_have_correct_types_in_order(self):
        """
        Events should arrive as:
        question, grounding, exploration, focus, synthesis.
        """
        clients = build_mock_clients()
        rag = GraphRag(*clients)

        events = []

        async def explain_callback(triples, explain_id):
            events.append({"triples": triples, "explain_id": explain_id})

        await rag.query(
            query="What is quantum computing?",
            explain_callback=explain_callback,

        )

        expected_types = [
            TG_GRAPH_RAG_QUESTION,
            TG_GROUNDING,
            TG_EXPLORATION,
            TG_FOCUS,
            TG_SYNTHESIS,
        ]

        for i, expected_type in enumerate(expected_types):
            uri = events[i]["explain_id"]
            triples = events[i]["triples"]
            assert has_type(triples, uri, expected_type), (
                f"Event {i} (uri={uri}) should have type {expected_type}"
            )

    @pytest.mark.asyncio
    async def test_derivation_chain_links_correctly(self):
        """
        Each event's URI should link to the previous via wasDerivedFrom:
        grounding → question → (none)
        exploration → grounding
        focus → exploration
        synthesis → focus
        """
        clients = build_mock_clients()
        rag = GraphRag(*clients)

        events = []

        async def explain_callback(triples, explain_id):
            events.append({"triples": triples, "explain_id": explain_id})

        await rag.query(
            query="What is quantum computing?",
            explain_callback=explain_callback,

        )

        uris = [e["explain_id"] for e in events]
        all_triples = []
        for e in events:
            all_triples.extend(e["triples"])

        # question has no parent
        assert derived_from(all_triples, uris[0]) is None

        # grounding → question
        assert derived_from(all_triples, uris[1]) == uris[0]

        # exploration → grounding
        assert derived_from(all_triples, uris[2]) == uris[1]

        # focus → exploration
        assert derived_from(all_triples, uris[3]) == uris[2]

        # synthesis → focus
        assert derived_from(all_triples, uris[4]) == uris[3]

    @pytest.mark.asyncio
    async def test_question_event_carries_query_text(self):
        """The question event should contain the original query string."""
        clients = build_mock_clients()
        rag = GraphRag(*clients)

        events = []

        async def explain_callback(triples, explain_id):
            events.append({"triples": triples, "explain_id": explain_id})

        await rag.query(
            query="What is quantum computing?",
            explain_callback=explain_callback,

        )

        q_uri = events[0]["explain_id"]
        q_triples = events[0]["triples"]
        t = find_triple(q_triples, TG_QUERY, q_uri)
        assert t is not None
        assert t.o.value == "What is quantum computing?"

    @pytest.mark.asyncio
    async def test_grounding_carries_concepts(self):
        """The grounding event should list extracted concepts."""
        clients = build_mock_clients()
        rag = GraphRag(*clients)

        events = []

        async def explain_callback(triples, explain_id):
            events.append({"triples": triples, "explain_id": explain_id})

        await rag.query(
            query="What is quantum computing?",
            explain_callback=explain_callback,

        )

        gnd_uri = events[1]["explain_id"]
        gnd_triples = events[1]["triples"]
        concepts = find_triples(gnd_triples, TG_CONCEPT, gnd_uri)
        concept_values = {t.o.value for t in concepts}
        assert "quantum computing" in concept_values
        assert "physics" in concept_values

    @pytest.mark.asyncio
    async def test_exploration_has_edge_count(self):
        """The exploration event should report how many edges were found."""
        clients = build_mock_clients()
        rag = GraphRag(*clients)

        events = []

        async def explain_callback(triples, explain_id):
            events.append({"triples": triples, "explain_id": explain_id})

        await rag.query(
            query="What is quantum computing?",
            explain_callback=explain_callback,

        )

        exp_uri = events[2]["explain_id"]
        exp_triples = events[2]["triples"]
        t = find_triple(exp_triples, TG_EDGE_COUNT, exp_uri)
        assert t is not None
        assert int(t.o.value) > 0

    @pytest.mark.asyncio
    async def test_focus_has_selected_edges_with_concept_and_score(self):
        """
        The focus event should carry selected edges as quoted triples
        with cross-encoder concept and score metadata.
        """
        clients = build_mock_clients()
        rag = GraphRag(*clients)

        events = []

        async def explain_callback(triples, explain_id):
            events.append({"triples": triples, "explain_id": explain_id})

        await rag.query(
            query="What is quantum computing?",
            explain_callback=explain_callback,
        )

        foc_uri = events[3]["explain_id"]
        foc_triples = events[3]["triples"]

        # Should have selected edges
        selected = find_triples(foc_triples, TG_SELECTED_EDGE, foc_uri)
        assert len(selected) > 0, "Focus should have at least one selected edge"

        # Each edge selection should have a quoted triple
        edge_t = find_triples(foc_triples, TG_EDGE)
        assert len(edge_t) > 0, "Focus should have tg:edge with quoted triples"
        for t in edge_t:
            assert t.o.triple is not None, "tg:edge object must be a quoted triple"

        # Edge selections should be typed as EdgeSelection
        edge_sel_uris = [t.o.iri for t in selected]
        for uri in edge_sel_uris:
            assert has_type(foc_triples, uri, TG_EDGE_SELECTION)

        # Should have concept and score
        concepts = find_triples(foc_triples, TG_CONCEPT)
        assert len(concepts) > 0, "Focus should have tg:concept for selected edges"

        scores = find_triples(foc_triples, TG_SCORE)
        assert len(scores) > 0, "Focus should have tg:score for selected edges"
        for t in scores:
            float(t.o.value)  # Should be parseable as float

    @pytest.mark.asyncio
    async def test_synthesis_is_answer_type(self):
        """The synthesis event should have tg:Answer type."""
        clients = build_mock_clients()
        rag = GraphRag(*clients)

        events = []

        async def explain_callback(triples, explain_id):
            events.append({"triples": triples, "explain_id": explain_id})

        await rag.query(
            query="What is quantum computing?",
            explain_callback=explain_callback,

        )

        syn_uri = events[4]["explain_id"]
        syn_triples = events[4]["triples"]
        assert has_type(syn_triples, syn_uri, TG_SYNTHESIS)
        assert has_type(syn_triples, syn_uri, TG_ANSWER_TYPE)

    @pytest.mark.asyncio
    async def test_query_returns_answer_text(self):
        """query() should still return the synthesised answer."""
        clients = build_mock_clients()
        rag = GraphRag(*clients)

        events = []

        async def explain_callback(triples, explain_id):
            events.append({"triples": triples, "explain_id": explain_id})

        result_text, usage, sources = await rag.query(
            query="What is quantum computing?",
            explain_callback=explain_callback,

        )

        assert result_text == "Quantum computing applies physics principles to computation."

    @pytest.mark.asyncio
    async def test_parent_uri_links_question_to_parent(self):
        """When parent_uri is provided, question should derive from it."""
        clients = build_mock_clients()
        rag = GraphRag(*clients)

        events = []

        async def explain_callback(triples, explain_id):
            events.append({"triples": triples, "explain_id": explain_id})

        parent = "urn:trustgraph:agent:iteration:xyz"
        await rag.query(
            query="What is quantum computing?",
            explain_callback=explain_callback,

            parent_uri=parent,
        )

        q_uri = events[0]["explain_id"]
        q_triples = events[0]["triples"]
        assert derived_from(q_triples, q_uri) == parent

    @pytest.mark.asyncio
    async def test_no_explain_callback_still_works(self):
        """query() without explain_callback should return answer normally."""
        clients = build_mock_clients()
        rag = GraphRag(*clients)

        result_text, usage, sources = await rag.query(
            query="What is quantum computing?",

        )

        assert result_text == "Quantum computing applies physics principles to computation."

    @pytest.mark.asyncio
    async def test_all_triples_in_retrieval_graph(self):
        """All emitted triples should be in the urn:graph:retrieval graph."""
        clients = build_mock_clients()
        rag = GraphRag(*clients)

        events = []

        async def explain_callback(triples, explain_id):
            events.append({"triples": triples, "explain_id": explain_id})

        await rag.query(
            query="What is quantum computing?",
            explain_callback=explain_callback,

        )

        for event in events:
            for t in event["triples"]:
                assert t.g == "urn:graph:retrieval", (
                    f"Triple {t.s.iri} {t.p.iri} should be in "
                    f"urn:graph:retrieval, got {t.g}"
                )


# ---------------------------------------------------------------------------
# Source document tracing
# ---------------------------------------------------------------------------

# Provenance chains served by the mock triples client:
#   EDGE_1, EDGE_2 -> SUBGRAPH_A -> chunk/a -> page/a -> DOC_ALPHA
#   EDGE_3         -> SUBGRAPH_B -> chunk/b -> page/b -> DOC_BETA + DOC_GAMMA
SUBGRAPH_A = "http://trustgraph.ai/sg/aaa"
SUBGRAPH_B = "http://trustgraph.ai/sg/bbb"
DOC_ALPHA = "urn:document:alpha"
DOC_BETA = "urn:document:beta"
DOC_GAMMA = "urn:document:gamma"
TG_MIME_TYPE = "http://trustgraph.ai/ns/provenance/mimeType"

DERIVATIONS = {
    SUBGRAPH_A: ["http://trustgraph.ai/chunk/a"],
    "http://trustgraph.ai/chunk/a": ["http://trustgraph.ai/page/a"],
    "http://trustgraph.ai/page/a": [DOC_ALPHA],
    SUBGRAPH_B: ["http://trustgraph.ai/chunk/b"],
    "http://trustgraph.ai/chunk/b": ["http://trustgraph.ai/page/b"],
    "http://trustgraph.ai/page/b": [DOC_BETA, DOC_GAMMA],
}

# alpha has both dc:title and rdfs:label (dc:title preferred), beta has
# only rdfs:label (fallback), gamma has no title at all (empty string)
DOC_METADATA = {
    DOC_ALPHA: [
        ClientTriple(Uri(DOC_ALPHA), Uri(RDFS_LABEL),
                     Literal("alpha label")),
        ClientTriple(Uri(DOC_ALPHA), Uri(DC_TITLE),
                     Literal("Quantum Mechanics Primer")),
        ClientTriple(Uri(DOC_ALPHA), Uri(TG_MIME_TYPE),
                     Literal("application/pdf")),
    ],
    DOC_BETA: [
        ClientTriple(Uri(DOC_BETA), Uri(RDFS_LABEL),
                     Literal("Physics Notes")),
    ],
    DOC_GAMMA: [
        ClientTriple(Uri(DOC_GAMMA), Uri(TG_MIME_TYPE),
                     Literal("text/plain")),
    ],
}

EXPECTED_SOURCES = sorted([
    {"uri": DOC_ALPHA, "title": "Quantum Mechanics Primer"},
    {"uri": DOC_BETA, "title": "Physics Notes"},
    {"uri": DOC_GAMMA, "title": ""},
], key=lambda s: s["uri"])

# Total triples_client.query calls query() makes against the graph above:
# 3 tg:contains + 9 wasDerivedFrom + 3 doc metadata = 15.
# (No label lookups — labels are pre-resolved by the knowledge retrieval
# service and returned on RetrievedEdge.)
EXPECTED_TRIPLES_QUERY_CALLS = 15


def build_source_tracing_clients(fail_tracing=False):
    """Like build_mock_clients, but the triples client also serves the
    tg:contains + prov:wasDerivedFrom chains and document metadata."""
    (concept_extraction_client, knowledge_retrieval_client,
     triples_client, prompt_client) = build_mock_clients()

    def subgraph_for(quoted):
        t = quoted.triple
        if t.p.iri == "http://schema.org/relatedTo":
            return SUBGRAPH_A
        return SUBGRAPH_A if t.s.iri == ENTITY_A else SUBGRAPH_B

    async def mock_query(s=None, p=None, o=None, limit=1,
                         collection=None, g=None,
                         user_context=None):
        if p == TG_CONTAINS and o is not None:
            if fail_tracing:
                raise RuntimeError("triple store unavailable")
            sg = subgraph_for(o)
            return [ClientTriple(Uri(sg), Uri(TG_CONTAINS), o)]
        if p == PROV_WAS_DERIVED_FROM:
            return [
                ClientTriple(Uri(str(s)), Uri(PROV_WAS_DERIVED_FROM),
                             Uri(target))
                for target in DERIVATIONS.get(str(s), [])
            ]
        if p is None and str(s) in DOC_METADATA:
            return DOC_METADATA[str(s)]
        return []

    triples_client.query.side_effect = mock_query

    return (concept_extraction_client, knowledge_retrieval_client,
            triples_client, prompt_client)


class TestGraphRagSourceTracing:
    """query() should return structured source references built from the
    provenance walk it already performs."""

    @pytest.mark.asyncio
    async def test_query_returns_sources(self):
        """Sources are deduplicated, uri-sorted, titled where possible."""
        clients = build_source_tracing_clients()
        rag = GraphRag(*clients)

        resp, usage, sources = await rag.query(
            query="What is quantum computing?",
        )

        assert resp == (
            "Quantum computing applies physics principles to computation."
        )
        assert sorted(sources, key=lambda s: s["uri"]) == EXPECTED_SOURCES

    @pytest.mark.asyncio
    async def test_sources_add_zero_triple_queries(self):
        """Building sources must not add any triple-store queries."""
        clients = build_source_tracing_clients()
        triples_client = clients[2]
        rag = GraphRag(*clients)

        resp, usage, sources = await rag.query(
            query="What is quantum computing?",
        )

        assert sorted(sources, key=lambda s: s["uri"]) == EXPECTED_SOURCES
        assert triples_client.query.call_count == (
            EXPECTED_TRIPLES_QUERY_CALLS
        )

    @pytest.mark.asyncio
    async def test_doc_metadata_still_reaches_synthesis_prompt(self):
        """The kg-synthesis prompt context keeps the document edges."""
        clients = build_source_tracing_clients()
        prompt_client = clients[3]
        rag = GraphRag(*clients)

        await rag.query(query="What is quantum computing?")

        synthesis_calls = [
            c for c in prompt_client.prompt.call_args_list
            if c.args[0] == "kg-synthesis"
        ]
        assert len(synthesis_calls) == 1
        knowledge = synthesis_calls[0].kwargs["variables"]["knowledge"]
        assert {
            "s": DOC_ALPHA, "p": DC_TITLE,
            "o": "Quantum Mechanics Primer",
        } in knowledge

    @pytest.mark.asyncio
    async def test_tracing_failure_degrades_to_empty_sources(self):
        """A failing walk yields empty sources, answer unaffected."""
        clients = build_source_tracing_clients(fail_tracing=True)
        rag = GraphRag(*clients)

        resp, usage, sources = await rag.query(
            query="What is quantum computing?",
        )

        assert resp == (
            "Quantum computing applies physics principles to computation."
        )
        assert sources == []
