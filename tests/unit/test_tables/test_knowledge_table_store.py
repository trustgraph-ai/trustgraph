"""
Unit tests for KnowledgeTableStore row deserialization.

Regression coverage: a previous version of get_graph_embeddings constructed
EntityEmbeddings(vectors=ent[1]) — the schema field is `vector` (singular),
so any real Cassandra row would crash on read. These tests bypass the live
Cassandra connection entirely and exercise the row -> schema conversion
with hand-built fake rows.
"""

import pytest
from unittest.mock import Mock

from trustgraph.tables.knowledge import KnowledgeTableStore
from trustgraph.schema import (
    EntityEmbeddings,
    GraphEmbeddings,
    Triples,
    Triple,
    Metadata,
    IRI,
    LITERAL,
)


def _make_store():
    """
    Build a KnowledgeTableStore without invoking __init__ (which connects
    to Cassandra). Tests inject only the attributes the method under test
    actually touches.
    """
    return KnowledgeTableStore.__new__(KnowledgeTableStore)


class TestGetGraphEmbeddings:

    @pytest.mark.asyncio
    async def test_row_converts_to_entity_embeddings_with_singular_vector(self):
        """
        Cassandra rows return entities as a list of [entity_tuple, vector]
        pairs in row[3]. The deserializer must construct EntityEmbeddings
        with `vector=` (singular) — the schema field name. A previous
        version used `vectors=` and TypeError'd at runtime.
        """
        # Arrange — fake row matching the get_triples_stmt result shape:
        #   row[0..2] are unused by the method, row[3] is the entities blob
        fake_row = (
            None, None, None,
            [
                # ((value, is_uri), vector)
                (("http://example.org/alice", True), [0.1, 0.2, 0.3]),
                (("http://example.org/bob", True), [0.4, 0.5, 0.6]),
                (("a literal entity", False), [0.7, 0.8, 0.9]),
            ],
        )

        store = _make_store()
        store.cassandra = Mock()
        store.cassandra.execute = Mock(return_value=[fake_row])
        store.get_graph_embeddings_stmt = Mock()

        received = []

        async def receiver(msg):
            received.append(msg)

        # Act
        await store.get_graph_embeddings(
            user="alice",
            document_id="doc-1",
            receiver=receiver,
        )

        # Assert
        store.cassandra.execute.assert_called_once_with(
            store.get_graph_embeddings_stmt,
            ("alice", "doc-1"),
        )

        assert len(received) == 1
        ge = received[0]
        assert isinstance(ge, GraphEmbeddings)
        assert isinstance(ge.metadata, Metadata)
        assert ge.metadata.id == "doc-1"
        assert ge.metadata.user == "alice"

        assert len(ge.entities) == 3
        assert all(isinstance(e, EntityEmbeddings) for e in ge.entities)

        # Vectors land in the singular `vector` field — this is the
        # explicit regression assertion for the original bug.
        assert ge.entities[0].vector == [0.1, 0.2, 0.3]
        assert ge.entities[1].vector == [0.4, 0.5, 0.6]
        assert ge.entities[2].vector == [0.7, 0.8, 0.9]

        # Term type round-trips through tuple_to_term
        assert ge.entities[0].entity.type == IRI
        assert ge.entities[0].entity.iri == "http://example.org/alice"
        assert ge.entities[1].entity.type == IRI
        assert ge.entities[1].entity.iri == "http://example.org/bob"
        assert ge.entities[2].entity.type == LITERAL
        assert ge.entities[2].entity.value == "a literal entity"

    @pytest.mark.asyncio
    async def test_empty_entities_blob_yields_empty_list(self):
        """row[3] being None / empty must produce a GraphEmbeddings with
        no entities, not raise."""
        fake_row = (None, None, None, None)

        store = _make_store()
        store.cassandra = Mock()
        store.cassandra.execute = Mock(return_value=[fake_row])
        store.get_graph_embeddings_stmt = Mock()

        received = []

        async def receiver(msg):
            received.append(msg)

        await store.get_graph_embeddings("u", "d", receiver)

        assert len(received) == 1
        assert received[0].entities == []

    @pytest.mark.asyncio
    async def test_multiple_rows_each_emit_one_message(self):
        fake_rows = [
            (None, None, None, [
                (("http://example.org/a", True), [1.0]),
            ]),
            (None, None, None, [
                (("http://example.org/b", True), [2.0]),
            ]),
        ]

        store = _make_store()
        store.cassandra = Mock()
        store.cassandra.execute = Mock(return_value=fake_rows)
        store.get_graph_embeddings_stmt = Mock()

        received = []

        async def receiver(msg):
            received.append(msg)

        await store.get_graph_embeddings("u", "d", receiver)

        assert len(received) == 2
        assert received[0].entities[0].entity.iri == "http://example.org/a"
        assert received[0].entities[0].vector == [1.0]
        assert received[1].entities[0].entity.iri == "http://example.org/b"
        assert received[1].entities[0].vector == [2.0]


class TestGetTriples:
    """Bonus: the sibling get_triples path uses the same row[3] shape and
    the same Metadata construction. Cover it for parity."""

    @pytest.mark.asyncio
    async def test_row_converts_to_triples(self):
        # row[3] is a list of (s_val, s_uri, p_val, p_uri, o_val, o_uri)
        fake_row = (
            None, None, None,
            [
                (
                    "http://example.org/alice", True,
                    "http://example.org/knows", True,
                    "http://example.org/bob", True,
                ),
            ],
        )

        store = _make_store()
        store.cassandra = Mock()
        store.cassandra.execute = Mock(return_value=[fake_row])
        store.get_triples_stmt = Mock()

        received = []

        async def receiver(msg):
            received.append(msg)

        await store.get_triples("alice", "doc-1", receiver)

        assert len(received) == 1
        triples_msg = received[0]
        assert isinstance(triples_msg, Triples)
        assert isinstance(triples_msg.metadata, Metadata)
        assert triples_msg.metadata.id == "doc-1"
        assert triples_msg.metadata.user == "alice"

        assert len(triples_msg.triples) == 1
        t = triples_msg.triples[0]
        assert isinstance(t, Triple)
        assert t.s.iri == "http://example.org/alice"
        assert t.p.iri == "http://example.org/knows"
        assert t.o.iri == "http://example.org/bob"
