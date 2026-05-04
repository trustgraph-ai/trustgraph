"""
Tests for pipeline metadata preservation: DocumentMetadata and
ProcessingMetadata round-trip through translators, field preservation,
and default handling.
"""

import pytest

from trustgraph.schema import DocumentMetadata, ProcessingMetadata, Triple, Term, IRI
from trustgraph.messaging.translators.metadata import (
    DocumentMetadataTranslator,
    ProcessingMetadataTranslator,
)


# ---------------------------------------------------------------------------
# DocumentMetadata translator
# ---------------------------------------------------------------------------

class TestDocumentMetadataTranslator:

    def setup_method(self):
        self.tx = DocumentMetadataTranslator()

    def test_full_round_trip(self):
        data = {
            "id": "doc-123",
            "time": 1710000000,
            "kind": "application/pdf",
            "title": "Test Document",
            "comments": "No comments",
            "metadata": [],
            "tags": ["finance", "q4"],
            "parent-id": "doc-100",
            "document-type": "page",
        }
        obj = self.tx.decode(data)
        assert obj.id == "doc-123"
        assert obj.time == 1710000000
        assert obj.kind == "application/pdf"
        assert obj.title == "Test Document"
        assert obj.tags == ["finance", "q4"]
        assert obj.parent_id == "doc-100"
        assert obj.document_type == "page"

        wire = self.tx.encode(obj)
        assert wire["id"] == "doc-123"
        assert wire["parent-id"] == "doc-100"
        assert wire["document-type"] == "page"

    def test_defaults_for_missing_fields(self):
        obj = self.tx.decode({})
        assert obj.parent_id == ""
        assert obj.document_type == "source"

    def test_metadata_triples_preserved(self):
        triple_wire = [{
            "s": {"t": "i", "i": "http://example.org/s"},
            "p": {"t": "i", "i": "http://example.org/p"},
            "o": {"t": "i", "i": "http://example.org/o"},
        }]
        data = {"metadata": triple_wire}
        obj = self.tx.decode(data)
        assert len(obj.metadata) == 1
        assert obj.metadata[0].s.iri == "http://example.org/s"

    def test_none_metadata_handled(self):
        data = {"metadata": None}
        obj = self.tx.decode(data)
        assert obj.metadata == []

    def test_empty_tags_preserved(self):
        data = {"tags": []}
        obj = self.tx.decode(data)
        wire = self.tx.encode(obj)
        assert wire["tags"] == []

    def test_falsy_fields_omitted_from_wire(self):
        """Empty string fields should be omitted from wire format."""
        obj = DocumentMetadata(id="", time=0)
        wire = self.tx.encode(obj)
        assert "id" not in wire


# ---------------------------------------------------------------------------
# ProcessingMetadata translator
# ---------------------------------------------------------------------------

class TestProcessingMetadataTranslator:

    def setup_method(self):
        self.tx = ProcessingMetadataTranslator()

    def test_full_round_trip(self):
        data = {
            "id": "proc-1",
            "document-id": "doc-123",
            "time": 1710000000,
            "flow": "default",
            "collection": "my-collection",
            "tags": ["tag1"],
        }
        obj = self.tx.decode(data)
        assert obj.id == "proc-1"
        assert obj.document_id == "doc-123"
        assert obj.flow == "default"
        assert obj.collection == "my-collection"
        assert obj.tags == ["tag1"]

        wire = self.tx.encode(obj)
        assert wire["id"] == "proc-1"
        assert wire["document-id"] == "doc-123"
        assert wire["collection"] == "my-collection"

    def test_missing_fields_use_defaults(self):
        obj = self.tx.decode({})
        assert obj.id is None
        assert obj.collection is None

    def test_tags_none_omitted(self):
        obj = ProcessingMetadata(tags=None)
        wire = self.tx.encode(obj)
        assert "tags" not in wire

    def test_tags_empty_list_preserved(self):
        obj = ProcessingMetadata(tags=[])
        wire = self.tx.encode(obj)
        assert wire["tags"] == []

    def test_collection_preserved(self):
        """Core pipeline routing fields must survive round-trip."""
        data = {"collection": "research"}
        obj = self.tx.decode(data)
        wire = self.tx.encode(obj)
        assert wire["collection"] == "research"
