"""
Tests for streaming triple batching in the relationships KG extractor.

Covers: batch size configuration, output splitting, metadata preservation,
provenance inclusion, empty/null filtering, and error propagation.
"""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch

from trustgraph.extract.kg.relationships.extract import (
    Processor, default_triples_batch_size,
)
from trustgraph.schema import (
    Chunk, Triples, Triple, Metadata, Term, IRI, LITERAL,
)
from trustgraph.base import PromptResult


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_processor(triples_batch_size=default_triples_batch_size):
    """Create a Processor without triggering FlowProcessor.__init__."""
    proc = Processor.__new__(Processor)
    proc.triples_batch_size = triples_batch_size
    return proc


def _make_rel(subject, predicate, obj, object_entity=True):
    """Build a relationship dict as returned by the prompt client."""
    return {
        "subject": subject,
        "predicate": predicate,
        "object": obj,
        "object-entity": object_entity,
    }


def _make_chunk_msg(text, meta_id="chunk-1", root="root-1", collection="col-1", document_id=""):
    """Build a mock message wrapping a Chunk."""
    chunk = Chunk(
        metadata=Metadata(
            id=meta_id, root=root, collection=collection,
        ),
        chunk=text.encode("utf-8"),
        document_id=document_id,
    )
    msg = MagicMock()
    msg.value.return_value = chunk
    return msg


def _make_flow(prompt_result, llm_model="test-llm", ontology_uri="test-onto"):
    """Build a mock flow callable that provides prompt client, triples
    producer, and parameter specs."""
    mock_triples_pub = AsyncMock()
    mock_prompt_client = AsyncMock()
    mock_prompt_client.extract_relationships = AsyncMock(
        return_value=PromptResult(
            response_type="jsonl",
            objects=prompt_result,
        )
    )

    def flow(name):
        if name == "prompt-request":
            return mock_prompt_client
        if name == "triples":
            return mock_triples_pub
        if name == "llm-model":
            return llm_model
        if name == "ontology":
            return ontology_uri
        return MagicMock()

    return flow, mock_triples_pub, mock_prompt_client


def _sent_triples(mock_pub):
    """Collect all Triples objects sent to a mock publisher."""
    return [call.args[0] for call in mock_pub.send.call_args_list]


def _all_triples_flat(mock_pub):
    """Flatten all batches into one list of Triple objects."""
    result = []
    for triples_msg in _sent_triples(mock_pub):
        result.extend(triples_msg.triples)
    return result


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------

class TestDefaultBatchSize:

    def test_default_is_50(self):
        assert default_triples_batch_size == 50

    def test_processor_uses_default(self):
        proc = _make_processor()
        assert proc.triples_batch_size == 50


class TestBatchSplitting:

    @pytest.mark.asyncio
    async def test_single_batch_when_under_limit(self):
        """Few triples → single send call."""
        proc = _make_processor(triples_batch_size=50)
        rels = [_make_rel("A", "knows", "B")]
        flow, pub, _ = _make_flow(rels)
        msg = _make_chunk_msg("some text")

        await proc.on_message(msg, MagicMock(), flow)

        # One relationship produces: rel triple + 3 labels + provenance
        # All should fit in one batch of 50
        assert pub.send.call_count == 1

    @pytest.mark.asyncio
    async def test_multiple_batches_with_small_batch_size(self):
        """With batch_size=3 and many triples, multiple batches are sent."""
        proc = _make_processor(triples_batch_size=3)
        # 2 relationships → 2 rel triples + 6 labels = 8 triples + provenance
        rels = [
            _make_rel("A", "knows", "B"),
            _make_rel("C", "likes", "D"),
        ]
        flow, pub, _ = _make_flow(rels)
        msg = _make_chunk_msg("some text")

        await proc.on_message(msg, MagicMock(), flow)

        # Should have more than one batch
        assert pub.send.call_count > 1

    @pytest.mark.asyncio
    async def test_batch_sizes_respect_limit(self):
        """No batch should exceed the configured batch size."""
        batch_size = 3
        proc = _make_processor(triples_batch_size=batch_size)
        rels = [
            _make_rel("A", "knows", "B"),
            _make_rel("C", "likes", "D"),
            _make_rel("E", "has", "F"),
        ]
        flow, pub, _ = _make_flow(rels)
        msg = _make_chunk_msg("text")

        await proc.on_message(msg, MagicMock(), flow)

        for triples_msg in _sent_triples(pub):
            assert len(triples_msg.triples) <= batch_size

    @pytest.mark.asyncio
    async def test_all_triples_present_across_batches(self):
        """Total triples across batches equals expected count."""
        proc = _make_processor(triples_batch_size=2)
        # 1 relationship with object-entity=True → 1 rel + 3 labels = 4 triples
        # + provenance triples
        rels = [_make_rel("A", "knows", "B", object_entity=True)]
        flow, pub, _ = _make_flow(rels)
        msg = _make_chunk_msg("text")

        await proc.on_message(msg, MagicMock(), flow)

        all_t = _all_triples_flat(pub)
        # At minimum: 1 rel + 3 labels = 4 content triples
        assert len(all_t) >= 4

    @pytest.mark.asyncio
    async def test_custom_batch_size(self):
        """Processor respects custom triples_batch_size parameter."""
        proc = _make_processor(triples_batch_size=100)
        assert proc.triples_batch_size == 100


class TestMetadataPreservation:

    @pytest.mark.asyncio
    async def test_metadata_forwarded_to_all_batches(self):
        """Every batch should carry the original chunk metadata."""
        proc = _make_processor(triples_batch_size=2)
        rels = [_make_rel("X", "rel", "Y")]
        flow, pub, _ = _make_flow(rels)
        msg = _make_chunk_msg(
            "text", meta_id="c-1", root="r-1", collection="coll-1",
        )

        await proc.on_message(msg, MagicMock(), flow)

        for triples_msg in _sent_triples(pub):
            assert triples_msg.metadata.id == "c-1"
            assert triples_msg.metadata.root == "r-1"
            assert triples_msg.metadata.collection == "coll-1"


class TestRelationshipTriples:

    @pytest.mark.asyncio
    async def test_entity_object_produces_iri(self):
        """object-entity=True → object is an IRI, with label triple."""
        proc = _make_processor(triples_batch_size=200)
        rels = [_make_rel("Alice", "knows", "Bob", object_entity=True)]
        flow, pub, _ = _make_flow(rels)
        msg = _make_chunk_msg("text")

        await proc.on_message(msg, MagicMock(), flow)

        all_t = _all_triples_flat(pub)
        # Find the relationship triple (not a label)
        rel_triples = [
            t for t in all_t
            if t.o.type == IRI and "bob" in t.o.iri
        ]
        assert len(rel_triples) >= 1

    @pytest.mark.asyncio
    async def test_literal_object_produces_literal(self):
        """object-entity=False → object is a LITERAL, no label for object."""
        proc = _make_processor(triples_batch_size=200)
        rels = [_make_rel("Alice", "age", "30", object_entity=False)]
        flow, pub, _ = _make_flow(rels)
        msg = _make_chunk_msg("text")

        await proc.on_message(msg, MagicMock(), flow)

        all_t = _all_triples_flat(pub)
        # Find the relationship triple with literal object
        lit_triples = [
            t for t in all_t
            if t.o.type == LITERAL and t.o.value == "30"
        ]
        assert len(lit_triples) == 1

    @pytest.mark.asyncio
    async def test_labels_emitted_for_subject_and_predicate(self):
        """Every relationship should produce label triples for s and p."""
        proc = _make_processor(triples_batch_size=200)
        rels = [_make_rel("Alice", "knows", "Bob")]
        flow, pub, _ = _make_flow(rels)
        msg = _make_chunk_msg("text")

        await proc.on_message(msg, MagicMock(), flow)

        all_t = _all_triples_flat(pub)
        label_triples = [
            t for t in all_t
            if t.p.type == IRI and "label" in t.p.iri.lower()
        ]
        labels = {t.o.value for t in label_triples}
        assert "Alice" in labels
        assert "knows" in labels
        assert "Bob" in labels  # object-entity default is True


class TestEmptyAndNullFiltering:

    @pytest.mark.asyncio
    async def test_empty_string_fields_skipped(self):
        """Relationships with empty string s/p/o are skipped."""
        proc = _make_processor(triples_batch_size=200)
        rels = [
            _make_rel("", "knows", "Bob"),
            _make_rel("Alice", "", "Bob"),
            _make_rel("Alice", "knows", ""),
            _make_rel("Good", "triple", "Here"),
        ]
        flow, pub, _ = _make_flow(rels)
        msg = _make_chunk_msg("text")

        await proc.on_message(msg, MagicMock(), flow)

        all_t = _all_triples_flat(pub)
        # Only the "Good triple Here" relationship should produce content triples
        rel_iris = {t.s.iri for t in all_t if hasattr(t.s, "iri") and t.s.iri}
        assert any("good" in iri for iri in rel_iris)
        assert not any("alice" in iri for iri in rel_iris)

    @pytest.mark.asyncio
    async def test_none_fields_skipped(self):
        """Relationships with None s/p/o are skipped."""
        proc = _make_processor(triples_batch_size=200)
        rels = [
            _make_rel(None, "knows", "Bob"),
            _make_rel("Alice", None, "Bob"),
            _make_rel("Alice", "knows", None),
            _make_rel("Valid", "rel", "Here"),
        ]
        flow, pub, _ = _make_flow(rels)
        msg = _make_chunk_msg("text")

        await proc.on_message(msg, MagicMock(), flow)

        all_t = _all_triples_flat(pub)
        rel_iris = {t.s.iri for t in all_t if hasattr(t.s, "iri") and t.s.iri}
        assert any("valid" in iri for iri in rel_iris)
        assert not any("alice" in iri for iri in rel_iris)

    @pytest.mark.asyncio
    async def test_all_filtered_produces_no_output(self):
        """If all relationships are empty/null, nothing is emitted."""
        proc = _make_processor(triples_batch_size=200)
        rels = [
            _make_rel("", "", ""),
            _make_rel(None, None, None),
        ]
        flow, pub, _ = _make_flow(rels)
        msg = _make_chunk_msg("text")

        await proc.on_message(msg, MagicMock(), flow)

        assert pub.send.call_count == 0

    @pytest.mark.asyncio
    async def test_empty_prompt_response_produces_no_output(self):
        """Empty relationship list from prompt → no triples emitted."""
        proc = _make_processor()
        flow, pub, _ = _make_flow([])
        msg = _make_chunk_msg("text")

        await proc.on_message(msg, MagicMock(), flow)

        assert pub.send.call_count == 0


class TestProvenanceInclusion:

    @pytest.mark.asyncio
    async def test_provenance_triples_present(self):
        """Extracted relationships should include provenance triples."""
        proc = _make_processor(triples_batch_size=200)
        rels = [_make_rel("A", "knows", "B")]
        flow, pub, _ = _make_flow(rels)
        msg = _make_chunk_msg("text")

        await proc.on_message(msg, MagicMock(), flow)

        all_t = _all_triples_flat(pub)
        # Provenance triples use GRAPH_SOURCE graph context
        # They contain terms referencing prov: namespace or subgraph URIs
        # We just check that total count > 4 (1 rel + 3 labels)
        assert len(all_t) > 4

    @pytest.mark.asyncio
    async def test_no_provenance_when_no_extracted_triples(self):
        """Empty relationships → no provenance generated."""
        proc = _make_processor()
        flow, pub, _ = _make_flow([_make_rel("", "x", "y")])
        msg = _make_chunk_msg("text")

        await proc.on_message(msg, MagicMock(), flow)

        assert pub.send.call_count == 0


class TestErrorPropagation:

    @pytest.mark.asyncio
    async def test_prompt_error_is_caught(self):
        """Errors from the prompt client are caught (logged, not raised)."""
        proc = _make_processor()
        flow, pub, prompt = _make_flow([])
        prompt.extract_relationships = AsyncMock(
            side_effect=RuntimeError("LLM unavailable")
        )
        msg = _make_chunk_msg("text")

        # The outer try/except in on_message catches and logs
        await proc.on_message(msg, MagicMock(), flow)

        assert pub.send.call_count == 0

    @pytest.mark.asyncio
    async def test_non_list_response_is_caught(self):
        """Non-list prompt response triggers RuntimeError, caught by handler."""
        proc = _make_processor()
        flow, pub, prompt = _make_flow("not a list")
        msg = _make_chunk_msg("text")

        await proc.on_message(msg, MagicMock(), flow)

        assert pub.send.call_count == 0


class TestToUri:

    def test_spaces_replaced_with_hyphens(self):
        proc = _make_processor()
        uri = proc.to_uri("hello world")
        assert "hello-world" in uri

    def test_lowercased(self):
        proc = _make_processor()
        uri = proc.to_uri("Hello World")
        assert "hello-world" in uri

    def test_special_chars_encoded(self):
        proc = _make_processor()
        # urllib.parse.quote keeps / as safe by default
        uri = proc.to_uri("a/b")
        assert "a/b" in uri
        # Characters like spaces are encoded (handled via replace → hyphen)
        uri2 = proc.to_uri("hello world")
        assert " " not in uri2
