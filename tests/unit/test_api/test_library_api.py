"""
Tests for the Library API wrapper round-trip behavior.
Covers the get_documents → update_document path and edge cases
from issue #893.
"""

import datetime
import pytest
from unittest.mock import MagicMock, patch

from trustgraph.api.library import Library, to_value, from_value
from trustgraph.api.types import DocumentMetadata, Triple
from trustgraph.knowledge import Uri, Literal


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_library(response=None):
    api = MagicMock()
    api.workspace = "default"
    api.request.return_value = response or {}
    lib = Library(api)
    return lib, api


def _wire_triple(s_iri, p_iri, o_val):
    return {
        "s": {"t": "i", "i": s_iri},
        "p": {"t": "i", "i": p_iri},
        "o": {"t": "l", "v": o_val},
    }


def _doc_wire(id="doc-1", time=1700000000, title="Test Doc",
              kind="text/plain", comments="", tags=None,
              metadata=None, parent_id="", document_type="source",
              include_title=True):
    doc = {
        "id": id,
        "time": time,
        "kind": kind,
        "comments": comments,
        "metadata": metadata or [],
        "tags": tags or [],
        "parent-id": parent_id,
        "document-type": document_type,
    }
    if include_title:
        doc["title"] = title
    return doc


# ---------------------------------------------------------------------------
# Bug 1: get_documents tolerates missing title
# ---------------------------------------------------------------------------

class TestGetDocumentsMissingTitle:

    def test_missing_title_defaults_to_empty(self):
        doc = _doc_wire(include_title=False)
        lib, api = _make_library({"document-metadatas": [doc]})

        result = lib.get_documents()

        assert len(result) == 1
        assert result[0].title == ""

    def test_present_title_preserved(self):
        doc = _doc_wire(title="My Title")
        lib, api = _make_library({"document-metadatas": [doc]})

        result = lib.get_documents()

        assert result[0].title == "My Title"


# ---------------------------------------------------------------------------
# Bug 2: update_document handles Triple objects (attribute access)
# ---------------------------------------------------------------------------

class TestUpdateDocumentTripleAccess:

    def test_triple_objects_serialized_correctly(self):
        lib, api = _make_library({})

        metadata = DocumentMetadata(
            id="doc-1",
            time=datetime.datetime.fromtimestamp(1700000000),
            kind="text/plain",
            title="Test",
            comments="",
            metadata=[
                Triple(
                    s=Uri("http://example.org/entity/alice"),
                    p=Uri("http://example.org/rel/knows"),
                    o=Literal("Bob"),
                ),
            ],
            tags=["test"],
        )

        lib.update_document(id="doc-1", metadata=metadata)

        call_args = api.request.call_args[0][1]
        triples = call_args["document-metadata"]["metadata"]

        assert len(triples) == 1
        assert triples[0]["s"]["i"] == "http://example.org/entity/alice"
        assert triples[0]["p"]["i"] == "http://example.org/rel/knows"
        assert triples[0]["o"]["v"] == "Bob"

    def test_empty_metadata_list(self):
        lib, api = _make_library({})

        metadata = DocumentMetadata(
            id="doc-1",
            time=datetime.datetime.fromtimestamp(1700000000),
            kind="text/plain",
            title="Test",
            comments="",
            metadata=[],
            tags=[],
        )

        lib.update_document(id="doc-1", metadata=metadata)

        call_args = api.request.call_args[0][1]
        assert call_args["document-metadata"]["metadata"] == []


# ---------------------------------------------------------------------------
# Bug 3: update_document serializes datetime to int seconds
# ---------------------------------------------------------------------------

class TestUpdateDocumentTimeSerialization:

    def test_datetime_serialized_to_int(self):
        lib, api = _make_library({})

        ts = 1700000000
        metadata = DocumentMetadata(
            id="doc-1",
            time=datetime.datetime.fromtimestamp(ts),
            kind="text/plain",
            title="Test",
            comments="",
            metadata=[],
            tags=[],
        )

        lib.update_document(id="doc-1", metadata=metadata)

        call_args = api.request.call_args[0][1]
        wire_time = call_args["document-metadata"]["time"]

        assert isinstance(wire_time, int)
        assert wire_time == ts

    def test_int_time_passed_through(self):
        lib, api = _make_library({})

        metadata = DocumentMetadata(
            id="doc-1",
            time=1700000000,
            kind="text/plain",
            title="Test",
            comments="",
            metadata=[],
            tags=[],
        )

        lib.update_document(id="doc-1", metadata=metadata)

        call_args = api.request.call_args[0][1]
        assert call_args["document-metadata"]["time"] == 1700000000


# ---------------------------------------------------------------------------
# Bug 4: update_document handles empty server response
# ---------------------------------------------------------------------------

class TestUpdateDocumentEmptyResponse:

    def test_empty_response_returns_input_metadata(self):
        lib, api = _make_library({})

        metadata = DocumentMetadata(
            id="doc-1",
            time=datetime.datetime.fromtimestamp(1700000000),
            kind="text/plain",
            title="Updated Title",
            comments="notes",
            metadata=[],
            tags=["a"],
        )

        result = lib.update_document(id="doc-1", metadata=metadata)

        assert result is metadata

    def test_full_response_parsed(self):
        response_doc = _doc_wire(
            id="doc-1", title="Server Title", tags=["b"],
        )
        lib, api = _make_library({"document-metadata": response_doc})

        metadata = DocumentMetadata(
            id="doc-1",
            time=datetime.datetime.fromtimestamp(1700000000),
            kind="text/plain",
            title="Client Title",
            comments="",
            metadata=[],
            tags=["a"],
        )

        result = lib.update_document(id="doc-1", metadata=metadata)

        assert result.title == "Server Title"
        assert result.tags == ["b"]


# ---------------------------------------------------------------------------
# Bug 5: update_document sends both id and document-id
# ---------------------------------------------------------------------------

class TestUpdateDocumentIdKeys:

    def test_both_id_keys_sent(self):
        lib, api = _make_library({})

        metadata = DocumentMetadata(
            id="doc-1",
            time=datetime.datetime.fromtimestamp(1700000000),
            kind="text/plain",
            title="Test",
            comments="",
            metadata=[],
            tags=[],
        )

        lib.update_document(id="doc-1", metadata=metadata)

        call_args = api.request.call_args[0][1]
        doc_meta = call_args["document-metadata"]

        assert doc_meta["id"] == "doc-1"
        assert doc_meta["document-id"] == "doc-1"


# ---------------------------------------------------------------------------
# Round-trip: get_documents → update_document
# ---------------------------------------------------------------------------

class TestGetUpdateRoundTrip:

    def test_full_round_trip(self):
        wire_doc = _doc_wire(
            id="doc-42",
            title="Original",
            tags=["v1"],
            metadata=[_wire_triple(
                "http://example.org/e/1",
                "http://example.org/r/type",
                "report",
            )],
        )

        lib, api = _make_library({"document-metadatas": [wire_doc]})

        docs = lib.get_documents()
        assert len(docs) == 1

        doc = docs[0]
        doc.title = "Updated"
        doc.tags.append("v2")

        # Server returns empty on update
        api.request.return_value = {}
        result = lib.update_document(id=doc.id, metadata=doc)

        # Should not raise, should return the input metadata
        assert result.title == "Updated"
        assert "v2" in result.tags

        # Verify the wire format sent
        call_args = api.request.call_args[0][1]
        doc_meta = call_args["document-metadata"]

        assert doc_meta["id"] == "doc-42"
        assert doc_meta["title"] == "Updated"
        assert isinstance(doc_meta["time"], int)
        assert len(doc_meta["metadata"]) == 1
        assert doc_meta["metadata"][0]["o"]["v"] == "report"
