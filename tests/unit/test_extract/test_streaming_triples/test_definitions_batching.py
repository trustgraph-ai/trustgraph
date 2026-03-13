"""
Tests for streaming triple and entity context batching in the definitions
KG extractor.

Covers: triples batch splitting, entity context batch splitting,
metadata preservation, provenance, and empty/null filtering.
"""

import pytest
from unittest.mock import AsyncMock, MagicMock

from trustgraph.extract.kg.definitions.extract import (
    Processor, default_triples_batch_size, default_entity_batch_size,
)
from trustgraph.schema import (
    Chunk, Triples, EntityContexts, Triple, Metadata, Term, IRI, LITERAL,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_processor(triples_batch_size=default_triples_batch_size,
                    entity_batch_size=default_entity_batch_size):
    proc = Processor.__new__(Processor)
    proc.triples_batch_size = triples_batch_size
    proc.entity_batch_size = entity_batch_size
    return proc


def _make_defn(entity, definition):
    return {"entity": entity, "definition": definition}


def _make_chunk_msg(text, meta_id="chunk-1", root="root-1",
                    user="user-1", collection="col-1", document_id=""):
    chunk = Chunk(
        metadata=Metadata(
            id=meta_id, root=root, user=user, collection=collection,
        ),
        chunk=text.encode("utf-8"),
        document_id=document_id,
    )
    msg = MagicMock()
    msg.value.return_value = chunk
    return msg


def _make_flow(prompt_result, llm_model="test-llm", ontology_uri="test-onto"):
    mock_triples_pub = AsyncMock()
    mock_ecs_pub = AsyncMock()
    mock_prompt_client = AsyncMock()
    mock_prompt_client.extract_definitions = AsyncMock(
        return_value=prompt_result
    )

    def flow(name):
        if name == "prompt-request":
            return mock_prompt_client
        if name == "triples":
            return mock_triples_pub
        if name == "entity-contexts":
            return mock_ecs_pub
        if name == "llm-model":
            return llm_model
        if name == "ontology":
            return ontology_uri
        return MagicMock()

    return flow, mock_triples_pub, mock_ecs_pub, mock_prompt_client


def _sent_triples(mock_pub):
    return [call.args[0] for call in mock_pub.send.call_args_list]


def _sent_ecs(mock_pub):
    return [call.args[0] for call in mock_pub.send.call_args_list]


def _all_triples_flat(mock_pub):
    result = []
    for triples_msg in _sent_triples(mock_pub):
        result.extend(triples_msg.triples)
    return result


def _all_entities_flat(mock_pub):
    result = []
    for ecs_msg in _sent_ecs(mock_pub):
        result.extend(ecs_msg.entities)
    return result


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------

class TestDefaults:

    def test_default_triples_batch_size(self):
        assert default_triples_batch_size == 50

    def test_default_entity_batch_size(self):
        assert default_entity_batch_size == 5


class TestTriplesBatching:

    @pytest.mark.asyncio
    async def test_single_batch_when_under_limit(self):
        proc = _make_processor(triples_batch_size=100)
        defs = [_make_defn("Cat", "A feline animal")]
        flow, triples_pub, _, _ = _make_flow(defs)
        msg = _make_chunk_msg("text")

        await proc.on_message(msg, MagicMock(), flow)

        assert triples_pub.send.call_count == 1

    @pytest.mark.asyncio
    async def test_multiple_triples_batches(self):
        proc = _make_processor(triples_batch_size=2)
        defs = [
            _make_defn("Cat", "A feline"),
            _make_defn("Dog", "A canine"),
        ]
        flow, triples_pub, _, _ = _make_flow(defs)
        msg = _make_chunk_msg("text")

        await proc.on_message(msg, MagicMock(), flow)

        # 2 defs → 2 labels + 2 definitions = 4 triples + provenance
        # With batch_size=2, should produce multiple batches
        assert triples_pub.send.call_count > 1

    @pytest.mark.asyncio
    async def test_triples_batch_sizes_within_limit(self):
        batch_size = 3
        proc = _make_processor(triples_batch_size=batch_size)
        defs = [
            _make_defn("A", "def A"),
            _make_defn("B", "def B"),
            _make_defn("C", "def C"),
        ]
        flow, triples_pub, _, _ = _make_flow(defs)
        msg = _make_chunk_msg("text")

        await proc.on_message(msg, MagicMock(), flow)

        for triples_msg in _sent_triples(triples_pub):
            assert len(triples_msg.triples) <= batch_size


class TestEntityContextBatching:

    @pytest.mark.asyncio
    async def test_single_entity_batch_when_under_limit(self):
        proc = _make_processor(entity_batch_size=100)
        defs = [_make_defn("Cat", "A feline")]
        flow, _, ecs_pub, _ = _make_flow(defs)
        msg = _make_chunk_msg("text")

        await proc.on_message(msg, MagicMock(), flow)

        # 1 def → 2 entity contexts (name + definition)
        assert ecs_pub.send.call_count == 1

    @pytest.mark.asyncio
    async def test_multiple_entity_batches(self):
        proc = _make_processor(entity_batch_size=2)
        defs = [
            _make_defn("Cat", "A feline"),
            _make_defn("Dog", "A canine"),
        ]
        flow, _, ecs_pub, _ = _make_flow(defs)
        msg = _make_chunk_msg("text")

        await proc.on_message(msg, MagicMock(), flow)

        # 2 defs → 4 entity contexts, batch_size=2 → 2 batches
        assert ecs_pub.send.call_count == 2

    @pytest.mark.asyncio
    async def test_entity_batch_sizes_within_limit(self):
        batch_size = 3
        proc = _make_processor(entity_batch_size=batch_size)
        defs = [
            _make_defn("A", "def A"),
            _make_defn("B", "def B"),
            _make_defn("C", "def C"),
        ]
        flow, _, ecs_pub, _ = _make_flow(defs)
        msg = _make_chunk_msg("text")

        await proc.on_message(msg, MagicMock(), flow)

        for ecs_msg in _sent_ecs(ecs_pub):
            assert len(ecs_msg.entities) <= batch_size

    @pytest.mark.asyncio
    async def test_entity_contexts_have_name_and_definition(self):
        """Each definition produces 2 entity contexts: name and definition."""
        proc = _make_processor(entity_batch_size=100)
        defs = [_make_defn("Cat", "A feline animal")]
        flow, _, ecs_pub, _ = _make_flow(defs)
        msg = _make_chunk_msg("text")

        await proc.on_message(msg, MagicMock(), flow)

        entities = _all_entities_flat(ecs_pub)
        assert len(entities) == 2
        contexts = {e.context for e in entities}
        assert "Cat" in contexts
        assert "A feline animal" in contexts


class TestMetadataPreservation:

    @pytest.mark.asyncio
    async def test_triples_metadata(self):
        proc = _make_processor(triples_batch_size=2)
        defs = [_make_defn("X", "def X")]
        flow, triples_pub, _, _ = _make_flow(defs)
        msg = _make_chunk_msg(
            "text", meta_id="c-1", root="r-1",
            user="u-1", collection="coll-1",
        )

        await proc.on_message(msg, MagicMock(), flow)

        for triples_msg in _sent_triples(triples_pub):
            assert triples_msg.metadata.id == "c-1"
            assert triples_msg.metadata.root == "r-1"
            assert triples_msg.metadata.user == "u-1"
            assert triples_msg.metadata.collection == "coll-1"

    @pytest.mark.asyncio
    async def test_entity_contexts_metadata(self):
        proc = _make_processor(entity_batch_size=1)
        defs = [_make_defn("X", "def X")]
        flow, _, ecs_pub, _ = _make_flow(defs)
        msg = _make_chunk_msg(
            "text", meta_id="c-2", root="r-2",
            user="u-2", collection="coll-2",
        )

        await proc.on_message(msg, MagicMock(), flow)

        for ecs_msg in _sent_ecs(ecs_pub):
            assert ecs_msg.metadata.id == "c-2"
            assert ecs_msg.metadata.root == "r-2"


class TestEmptyAndNullFiltering:

    @pytest.mark.asyncio
    async def test_empty_entity_skipped(self):
        proc = _make_processor()
        defs = [
            _make_defn("", "some definition"),
            _make_defn("Valid", "a valid definition"),
        ]
        flow, triples_pub, ecs_pub, _ = _make_flow(defs)
        msg = _make_chunk_msg("text")

        await proc.on_message(msg, MagicMock(), flow)

        all_t = _all_triples_flat(triples_pub)
        all_e = _all_entities_flat(ecs_pub)
        # Only "Valid" should be present
        entity_iris = {t.s.iri for t in all_t if hasattr(t.s, "iri")}
        assert any("valid" in iri for iri in entity_iris)
        assert len(all_e) == 2  # name + definition for "Valid" only

    @pytest.mark.asyncio
    async def test_empty_definition_skipped(self):
        proc = _make_processor()
        defs = [
            _make_defn("Entity", ""),
            _make_defn("Good", "good definition"),
        ]
        flow, triples_pub, _, _ = _make_flow(defs)
        msg = _make_chunk_msg("text")

        await proc.on_message(msg, MagicMock(), flow)

        all_t = _all_triples_flat(triples_pub)
        entity_iris = {t.s.iri for t in all_t if hasattr(t.s, "iri")}
        assert any("good" in iri for iri in entity_iris)
        # "Entity" with empty def should have been skipped
        assert not any("entity" in iri and "good" not in iri for iri in entity_iris)

    @pytest.mark.asyncio
    async def test_none_fields_skipped(self):
        proc = _make_processor()
        defs = [
            _make_defn(None, "some definition"),
            _make_defn("Entity", None),
        ]
        flow, triples_pub, ecs_pub, _ = _make_flow(defs)
        msg = _make_chunk_msg("text")

        await proc.on_message(msg, MagicMock(), flow)

        assert triples_pub.send.call_count == 0
        assert ecs_pub.send.call_count == 0

    @pytest.mark.asyncio
    async def test_all_filtered_no_output(self):
        proc = _make_processor()
        defs = [_make_defn("", ""), _make_defn(None, None)]
        flow, triples_pub, ecs_pub, _ = _make_flow(defs)
        msg = _make_chunk_msg("text")

        await proc.on_message(msg, MagicMock(), flow)

        assert triples_pub.send.call_count == 0
        assert ecs_pub.send.call_count == 0

    @pytest.mark.asyncio
    async def test_empty_prompt_response(self):
        proc = _make_processor()
        flow, triples_pub, ecs_pub, _ = _make_flow([])
        msg = _make_chunk_msg("text")

        await proc.on_message(msg, MagicMock(), flow)

        assert triples_pub.send.call_count == 0
        assert ecs_pub.send.call_count == 0


class TestProvenanceInclusion:

    @pytest.mark.asyncio
    async def test_provenance_triples_present(self):
        proc = _make_processor(triples_batch_size=200)
        defs = [_make_defn("Cat", "A feline")]
        flow, triples_pub, _, _ = _make_flow(defs)
        msg = _make_chunk_msg("text")

        await proc.on_message(msg, MagicMock(), flow)

        all_t = _all_triples_flat(triples_pub)
        # 1 def → 1 label + 1 definition = 2 content triples
        # Provenance adds more
        assert len(all_t) > 2


class TestErrorHandling:

    @pytest.mark.asyncio
    async def test_prompt_error_caught(self):
        proc = _make_processor()
        flow, triples_pub, ecs_pub, prompt = _make_flow([])
        prompt.extract_definitions = AsyncMock(
            side_effect=RuntimeError("LLM error")
        )
        msg = _make_chunk_msg("text")

        await proc.on_message(msg, MagicMock(), flow)

        assert triples_pub.send.call_count == 0
        assert ecs_pub.send.call_count == 0

    @pytest.mark.asyncio
    async def test_non_list_response_caught(self):
        proc = _make_processor()
        flow, triples_pub, ecs_pub, prompt = _make_flow("not a list")
        msg = _make_chunk_msg("text")

        await proc.on_message(msg, MagicMock(), flow)

        assert triples_pub.send.call_count == 0
        assert ecs_pub.send.call_count == 0


class TestDocumentIdProvenance:

    @pytest.mark.asyncio
    async def test_document_id_used_for_chunk_id(self):
        """When document_id is set, entity contexts should use it as chunk_id."""
        proc = _make_processor(entity_batch_size=100)
        defs = [_make_defn("Cat", "A feline")]
        flow, _, ecs_pub, _ = _make_flow(defs)
        msg = _make_chunk_msg("text", document_id="doc-123")

        await proc.on_message(msg, MagicMock(), flow)

        entities = _all_entities_flat(ecs_pub)
        for e in entities:
            assert e.chunk_id == "doc-123"

    @pytest.mark.asyncio
    async def test_metadata_id_fallback_for_chunk_id(self):
        """When document_id is empty, metadata.id is used as chunk_id."""
        proc = _make_processor(entity_batch_size=100)
        defs = [_make_defn("Cat", "A feline")]
        flow, _, ecs_pub, _ = _make_flow(defs)
        msg = _make_chunk_msg("text", meta_id="chunk-42", document_id="")

        await proc.on_message(msg, MagicMock(), flow)

        entities = _all_entities_flat(ecs_pub)
        for e in entities:
            assert e.chunk_id == "chunk-42"
