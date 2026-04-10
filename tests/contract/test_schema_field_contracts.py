"""
Contract tests for schema dataclass field sets.

These pin the *field names* of small, widely-constructed schema dataclasses
so that any rename, removal, or accidental addition fails CI loudly instead
of waiting for a runtime TypeError on the next websocket message.

Background: in v2.2 the `Metadata` dataclass dropped a `metadata: list[Triple]`
field but several call sites kept passing `Metadata(metadata=...)`. The bug
was only discovered when a websocket import dispatcher received its first
real message in production. A trivial structural assertion of the kind
below would have caught it at unit-test time.

Add to this file whenever a schema rename burns you. The cost of a frozen
field set is a one-line update when you intentionally evolve the schema; the
benefit is that every call site is forced to come along for the ride.
"""

import dataclasses
import pytest

from trustgraph.schema import (
    Metadata,
    EntityContext,
    EntityEmbeddings,
    ChunkEmbeddings,
)


def _field_names(dc):
    return {f.name for f in dataclasses.fields(dc)}


@pytest.mark.contract
class TestSchemaFieldContracts:
    """Pin the field set of dataclasses that get constructed all over the
    codebase. If you intentionally change one of these, update the
    expected set in the same commit — that diff will surface every call
    site that needs to come along."""

    def test_metadata_fields(self):
        # NOTE: there is no `metadata` field. A previous regression
        # constructed Metadata(metadata=...) and crashed at runtime.
        assert _field_names(Metadata) == {
            "id",
            "root",
            "user",
            "collection",
        }

    def test_entity_embeddings_fields(self):
        # NOTE: the embedding field is `vector` (singular, list[float]).
        # There is no `vectors` field. Several call sites historically
        # passed `vectors=` and crashed at runtime.
        assert _field_names(EntityEmbeddings) == {
            "entity",
            "vector",
            "chunk_id",
        }

    def test_chunk_embeddings_fields(self):
        # Same `vector` (singular) convention as EntityEmbeddings.
        assert _field_names(ChunkEmbeddings) == {
            "chunk_id",
            "vector",
        }

    def test_entity_context_fields(self):
        assert _field_names(EntityContext) == {
            "entity",
            "context",
            "chunk_id",
        }
