"""
Integration test: run a full DocumentRag.query() with mocked subsidiary
clients and verify the explain_callback receives the complete provenance
chain in the correct order with correct structure.

Document-RAG provenance chain (4 stages):
    question → grounding → exploration → synthesis
"""

import pytest
from unittest.mock import AsyncMock
from dataclasses import dataclass

from trustgraph.retrieval.document_rag.document_rag import DocumentRag

from trustgraph.provenance.namespaces import (
    RDF_TYPE, PROV_ENTITY, PROV_WAS_DERIVED_FROM,
    TG_DOC_RAG_QUESTION, TG_GROUNDING, TG_EXPLORATION,
    TG_SYNTHESIS, TG_ANSWER_TYPE,
    TG_QUERY, TG_CONCEPT,
    TG_CHUNK_COUNT, TG_SELECTED_CHUNK,
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


@dataclass
class ChunkMatch:
    """Mimics the result from doc_embeddings_client.query()."""
    chunk_id: str


# ---------------------------------------------------------------------------
# Mock setup
# ---------------------------------------------------------------------------

CHUNK_A = "urn:chunk:policy-doc-1:chunk-0"
CHUNK_B = "urn:chunk:policy-doc-1:chunk-1"
CHUNK_A_CONTENT = "Customers may return items within 30 days of purchase."
CHUNK_B_CONTENT = "Refunds are processed to the original payment method."


def build_mock_clients():
    """
    Build mock clients for a document-rag query.

    Client call sequence during query():
      1. prompt_client.prompt("extract-concepts", ...) -> concepts
      2. embeddings_client.embed(concepts) -> vectors
      3. doc_embeddings_client.query(vector, ...) -> chunk matches
      4. fetch_chunk(chunk_id, user) -> chunk content
      5. prompt_client.document_prompt(query, documents) -> answer
    """
    prompt_client = AsyncMock()
    embeddings_client = AsyncMock()
    doc_embeddings_client = AsyncMock()
    fetch_chunk = AsyncMock()

    # 1. Concept extraction
    async def mock_prompt(template_id, variables=None, **kwargs):
        if template_id == "extract-concepts":
            return "return policy\nrefund"
        return ""

    prompt_client.prompt.side_effect = mock_prompt

    # 2. Embedding vectors
    embeddings_client.embed.return_value = [[0.1, 0.2], [0.3, 0.4]]

    # 3. Chunk matching
    doc_embeddings_client.query.return_value = [
        ChunkMatch(chunk_id=CHUNK_A),
        ChunkMatch(chunk_id=CHUNK_B),
    ]

    # 4. Chunk content
    async def mock_fetch(chunk_id, user):
        return {
            CHUNK_A: CHUNK_A_CONTENT,
            CHUNK_B: CHUNK_B_CONTENT,
        }[chunk_id]

    fetch_chunk.side_effect = mock_fetch

    # 5. Synthesis
    prompt_client.document_prompt.return_value = (
        "Items can be returned within 30 days for a full refund."
    )

    return prompt_client, embeddings_client, doc_embeddings_client, fetch_chunk


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------

class TestDocumentRagQueryProvenance:
    """
    Run a real DocumentRag.query() and verify the provenance chain emitted
    via explain_callback.
    """

    @pytest.mark.asyncio
    async def test_explain_callback_receives_four_events(self):
        """query() should emit exactly 4 explain events."""
        clients = build_mock_clients()
        rag = DocumentRag(*clients)

        events = []

        async def explain_callback(triples, explain_id):
            events.append({"triples": triples, "explain_id": explain_id})

        await rag.query(
            query="What is the return policy?",
            explain_callback=explain_callback,
        )

        assert len(events) == 4, (
            f"Expected 4 explain events (question, grounding, exploration, "
            f"synthesis), got {len(events)}"
        )

    @pytest.mark.asyncio
    async def test_events_have_correct_types_in_order(self):
        """
        Events should arrive as:
        question, grounding, exploration, synthesis.
        """
        clients = build_mock_clients()
        rag = DocumentRag(*clients)

        events = []

        async def explain_callback(triples, explain_id):
            events.append({"triples": triples, "explain_id": explain_id})

        await rag.query(
            query="What is the return policy?",
            explain_callback=explain_callback,
        )

        expected_types = [
            TG_DOC_RAG_QUESTION,
            TG_GROUNDING,
            TG_EXPLORATION,
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
        question → (none)
        grounding → question
        exploration → grounding
        synthesis → exploration
        """
        clients = build_mock_clients()
        rag = DocumentRag(*clients)

        events = []

        async def explain_callback(triples, explain_id):
            events.append({"triples": triples, "explain_id": explain_id})

        await rag.query(
            query="What is the return policy?",
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

        # synthesis → exploration
        assert derived_from(all_triples, uris[3]) == uris[2]

    @pytest.mark.asyncio
    async def test_question_carries_query_text(self):
        """The question event should contain the original query string."""
        clients = build_mock_clients()
        rag = DocumentRag(*clients)

        events = []

        async def explain_callback(triples, explain_id):
            events.append({"triples": triples, "explain_id": explain_id})

        await rag.query(
            query="What is the return policy?",
            explain_callback=explain_callback,
        )

        q_uri = events[0]["explain_id"]
        q_triples = events[0]["triples"]
        t = find_triple(q_triples, TG_QUERY, q_uri)
        assert t is not None
        assert t.o.value == "What is the return policy?"

    @pytest.mark.asyncio
    async def test_grounding_carries_concepts(self):
        """The grounding event should list extracted concepts."""
        clients = build_mock_clients()
        rag = DocumentRag(*clients)

        events = []

        async def explain_callback(triples, explain_id):
            events.append({"triples": triples, "explain_id": explain_id})

        await rag.query(
            query="What is the return policy?",
            explain_callback=explain_callback,
        )

        gnd_uri = events[1]["explain_id"]
        gnd_triples = events[1]["triples"]
        concepts = find_triples(gnd_triples, TG_CONCEPT, gnd_uri)
        concept_values = {t.o.value for t in concepts}
        assert "return policy" in concept_values
        assert "refund" in concept_values

    @pytest.mark.asyncio
    async def test_exploration_has_chunk_count(self):
        """The exploration event should report the number of chunks retrieved."""
        clients = build_mock_clients()
        rag = DocumentRag(*clients)

        events = []

        async def explain_callback(triples, explain_id):
            events.append({"triples": triples, "explain_id": explain_id})

        await rag.query(
            query="What is the return policy?",
            explain_callback=explain_callback,
        )

        exp_uri = events[2]["explain_id"]
        exp_triples = events[2]["triples"]
        t = find_triple(exp_triples, TG_CHUNK_COUNT, exp_uri)
        assert t is not None
        assert int(t.o.value) == 2

    @pytest.mark.asyncio
    async def test_exploration_has_selected_chunks(self):
        """The exploration event should list the chunk IDs that were fetched."""
        clients = build_mock_clients()
        rag = DocumentRag(*clients)

        events = []

        async def explain_callback(triples, explain_id):
            events.append({"triples": triples, "explain_id": explain_id})

        await rag.query(
            query="What is the return policy?",
            explain_callback=explain_callback,
        )

        exp_uri = events[2]["explain_id"]
        exp_triples = events[2]["triples"]
        chunks = find_triples(exp_triples, TG_SELECTED_CHUNK, exp_uri)
        chunk_iris = {t.o.iri for t in chunks}
        assert CHUNK_A in chunk_iris
        assert CHUNK_B in chunk_iris

    @pytest.mark.asyncio
    async def test_synthesis_is_answer_type(self):
        """The synthesis event should have tg:Synthesis and tg:Answer types."""
        clients = build_mock_clients()
        rag = DocumentRag(*clients)

        events = []

        async def explain_callback(triples, explain_id):
            events.append({"triples": triples, "explain_id": explain_id})

        await rag.query(
            query="What is the return policy?",
            explain_callback=explain_callback,
        )

        syn_uri = events[3]["explain_id"]
        syn_triples = events[3]["triples"]
        assert has_type(syn_triples, syn_uri, TG_SYNTHESIS)
        assert has_type(syn_triples, syn_uri, TG_ANSWER_TYPE)

    @pytest.mark.asyncio
    async def test_query_returns_answer_text(self):
        """query() should return the synthesised answer."""
        clients = build_mock_clients()
        rag = DocumentRag(*clients)

        result = await rag.query(
            query="What is the return policy?",
            explain_callback=AsyncMock(),
        )

        assert result == "Items can be returned within 30 days for a full refund."

    @pytest.mark.asyncio
    async def test_no_explain_callback_still_works(self):
        """query() without explain_callback should return answer normally."""
        clients = build_mock_clients()
        rag = DocumentRag(*clients)

        result = await rag.query(query="What is the return policy?")
        assert result == "Items can be returned within 30 days for a full refund."

    @pytest.mark.asyncio
    async def test_all_triples_in_retrieval_graph(self):
        """All emitted triples should be in the urn:graph:retrieval graph."""
        clients = build_mock_clients()
        rag = DocumentRag(*clients)

        events = []

        async def explain_callback(triples, explain_id):
            events.append({"triples": triples, "explain_id": explain_id})

        await rag.query(
            query="What is the return policy?",
            explain_callback=explain_callback,
        )

        for event in events:
            for t in event["triples"]:
                assert t.g == "urn:graph:retrieval", (
                    f"Triple {t.s.iri} {t.p.iri} should be in "
                    f"urn:graph:retrieval, got {t.g}"
                )
