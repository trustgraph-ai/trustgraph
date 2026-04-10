"""
Round-trip unit tests for the core msgpack import/export gateway endpoints.

The kg-core export endpoint receives KnowledgeResponse-shaped dicts from
the responder callback and packs them into msgpack tuples. The kg-core
import endpoint takes msgpack tuples back off the wire and rebuilds
KnowledgeRequest-shaped dicts which it then hands to KnowledgeRequestor
(whose translator decodes them into real dataclasses).

Regression coverage: the previous wire format used `"vectors"` (plural)
in the entity blobs and embedded a stale `"m"` field that referenced the
removed `Metadata.metadata` triples-list field. The export side hit a
KeyError on first message; the import side built dicts that the
KnowledgeRequestTranslator (separately fixed) couldn't decode. These
tests pin both halves of the wire protocol.
"""

import msgpack
import pytest
from unittest.mock import AsyncMock, Mock, patch

from trustgraph.gateway.dispatch.core_export import CoreExport
from trustgraph.gateway.dispatch.core_import import CoreImport


# ---------------------------------------------------------------------------
# Helpers — sample translator-shaped dicts (as KnowledgeResponseTranslator
# would emit). The vector wire key is *singular* on purpose; the export
# side previously read the wrong key and crashed.
# ---------------------------------------------------------------------------


def _ge_response_dict():
    return {
        "graph-embeddings": {
            "metadata": {
                "id": "doc-1",
                "root": "",
                "user": "alice",
                "collection": "testcoll",
            },
            "entities": [
                {
                    "entity": {"t": "i", "i": "http://example.org/alice"},
                    "vector": [0.1, 0.2, 0.3],
                },
                {
                    "entity": {"t": "i", "i": "http://example.org/bob"},
                    "vector": [0.4, 0.5, 0.6],
                },
            ],
        }
    }


def _triples_response_dict():
    return {
        "triples": {
            "metadata": {
                "id": "doc-1",
                "root": "",
                "user": "alice",
                "collection": "testcoll",
            },
            "triples": [
                {
                    "s": {"t": "i", "i": "http://example.org/alice"},
                    "p": {"t": "i", "i": "http://example.org/knows"},
                    "o": {"t": "i", "i": "http://example.org/bob"},
                },
            ],
        }
    }


def _make_request(id_="doc-1", user="alice"):
    request = Mock()
    request.query = {"id": id_, "user": user}
    return request


def _make_data_reader(payload: bytes):
    """Mock the aiohttp StreamReader: returns payload once, then EOF."""
    chunks = [payload, b""]

    data = Mock()

    async def fake_read(n):
        return chunks.pop(0) if chunks else b""

    data.read = fake_read
    return data


# ---------------------------------------------------------------------------
# Export side: translator-shaped dict -> msgpack bytes
# ---------------------------------------------------------------------------


class TestCoreExportWireFormat:

    @pytest.mark.asyncio
    @patch("trustgraph.gateway.dispatch.core_export.KnowledgeRequestor")
    async def test_export_packs_graph_embeddings_with_singular_vector(
        self, mock_kr_class,
    ):
        """The export side must read `ent["vector"]` and emit `v`. The
        previous bug was reading `ent["vectors"]` which KeyErrored against
        the translator output."""
        captured = []

        async def fake_kr_process(req_dict, responder):
            await responder(_ge_response_dict(), True)

        mock_kr = AsyncMock()
        mock_kr.start = AsyncMock()
        mock_kr.stop = AsyncMock()
        mock_kr.process = fake_kr_process
        mock_kr_class.return_value = mock_kr

        response = AsyncMock()

        async def fake_write(b):
            captured.append(b)

        response.write = fake_write
        response.write_eof = AsyncMock()

        ok = AsyncMock(return_value=response)
        error = AsyncMock()

        exporter = CoreExport(backend=Mock())
        await exporter.process(
            data=Mock(),
            error=error,
            ok=ok,
            request=_make_request(),
        )

        # Did not raise, did not call error()
        error.assert_not_called()
        assert len(captured) == 1

        unpacker = msgpack.Unpacker()
        unpacker.feed(captured[0])
        items = list(unpacker)

        assert len(items) == 1
        msg_type, payload = items[0]
        assert msg_type == "ge"

        # Metadata envelope: only id/user/collection — no stale `m["m"]`.
        assert payload["m"] == {
            "i": "doc-1",
            "u": "alice",
            "c": "testcoll",
        }

        # Entities: each carries the *singular* `v` and the term envelope
        assert len(payload["e"]) == 2
        assert payload["e"][0]["v"] == [0.1, 0.2, 0.3]
        assert payload["e"][1]["v"] == [0.4, 0.5, 0.6]
        assert payload["e"][0]["e"]["i"] == "http://example.org/alice"

    @pytest.mark.asyncio
    @patch("trustgraph.gateway.dispatch.core_export.KnowledgeRequestor")
    async def test_export_packs_triples(self, mock_kr_class):
        captured = []

        async def fake_kr_process(req_dict, responder):
            await responder(_triples_response_dict(), True)

        mock_kr = AsyncMock()
        mock_kr.start = AsyncMock()
        mock_kr.stop = AsyncMock()
        mock_kr.process = fake_kr_process
        mock_kr_class.return_value = mock_kr

        response = AsyncMock()

        async def fake_write(b):
            captured.append(b)

        response.write = fake_write
        response.write_eof = AsyncMock()

        ok = AsyncMock(return_value=response)
        error = AsyncMock()

        exporter = CoreExport(backend=Mock())
        await exporter.process(
            data=Mock(), error=error, ok=ok, request=_make_request(),
        )

        error.assert_not_called()
        assert len(captured) == 1

        unpacker = msgpack.Unpacker()
        unpacker.feed(captured[0])
        items = list(unpacker)
        assert len(items) == 1

        msg_type, payload = items[0]
        assert msg_type == "t"
        assert payload["m"] == {
            "i": "doc-1",
            "u": "alice",
            "c": "testcoll",
        }
        assert len(payload["t"]) == 1


# ---------------------------------------------------------------------------
# Import side: msgpack bytes -> translator-shaped dict
# ---------------------------------------------------------------------------


class TestCoreImportWireFormat:

    @pytest.mark.asyncio
    @patch("trustgraph.gateway.dispatch.core_import.KnowledgeRequestor")
    async def test_import_unpacks_graph_embeddings_to_singular_vector(
        self, mock_kr_class,
    ):
        """The import side must build dicts whose entity blobs have the
        singular `vector` key — that's what the KnowledgeRequestTranslator
        decode side reads. Previous bug emitted `vectors`."""
        captured = []

        async def fake_kr_process(req_dict):
            captured.append(req_dict)

        mock_kr = AsyncMock()
        mock_kr.start = AsyncMock()
        mock_kr.stop = AsyncMock()
        mock_kr.process = fake_kr_process
        mock_kr_class.return_value = mock_kr

        # Build a msgpack tuple matching the new wire format
        payload = msgpack.packb((
            "ge",
            {
                "m": {"i": "doc-1", "u": "alice", "c": "testcoll"},
                "e": [
                    {
                        "e": {"t": "i", "i": "http://example.org/alice"},
                        "v": [0.1, 0.2, 0.3],
                    },
                ],
            },
        ))

        ok = AsyncMock(return_value=AsyncMock(write_eof=AsyncMock()))
        error = AsyncMock()

        importer = CoreImport(backend=Mock())
        await importer.process(
            data=_make_data_reader(payload),
            error=error,
            ok=ok,
            request=_make_request(),
        )

        error.assert_not_called()
        assert len(captured) == 1

        req = captured[0]
        assert req["operation"] == "put-kg-core"
        assert req["user"] == "alice"
        assert req["id"] == "doc-1"

        ge = req["graph-embeddings"]
        # Metadata envelope must NOT contain a stale `metadata` key
        # referencing the removed Metadata.metadata field.
        assert "metadata" not in ge["metadata"]
        assert ge["metadata"] == {
            "id": "doc-1",
            "user": "alice",
            "collection": "default",
        }

        # Entity blob carries the singular `vector` key
        assert len(ge["entities"]) == 1
        ent = ge["entities"][0]
        assert ent["vector"] == [0.1, 0.2, 0.3]
        assert "vectors" not in ent

    @pytest.mark.asyncio
    @patch("trustgraph.gateway.dispatch.core_import.KnowledgeRequestor")
    async def test_import_unpacks_triples(self, mock_kr_class):
        captured = []

        async def fake_kr_process(req_dict):
            captured.append(req_dict)

        mock_kr = AsyncMock()
        mock_kr.start = AsyncMock()
        mock_kr.stop = AsyncMock()
        mock_kr.process = fake_kr_process
        mock_kr_class.return_value = mock_kr

        payload = msgpack.packb((
            "t",
            {
                "m": {"i": "doc-1", "u": "alice", "c": "testcoll"},
                "t": [
                    {
                        "s": {"t": "i", "i": "http://example.org/alice"},
                        "p": {"t": "i", "i": "http://example.org/knows"},
                        "o": {"t": "i", "i": "http://example.org/bob"},
                    },
                ],
            },
        ))

        ok = AsyncMock(return_value=AsyncMock(write_eof=AsyncMock()))
        error = AsyncMock()

        importer = CoreImport(backend=Mock())
        await importer.process(
            data=_make_data_reader(payload),
            error=error,
            ok=ok,
            request=_make_request(),
        )

        error.assert_not_called()
        assert len(captured) == 1

        req = captured[0]
        triples = req["triples"]
        assert "metadata" not in triples["metadata"]  # no stale field
        assert len(triples["triples"]) == 1


# ---------------------------------------------------------------------------
# Full round-trip: export bytes feed directly into import
# ---------------------------------------------------------------------------


class TestCoreImportExportRoundTrip:
    """End-to-end: produce bytes via core_export, consume them via
    core_import, and verify the dict that lands at the import-side
    translator is structurally equivalent to what went in. This is the
    test that catches asymmetries between the two halves."""

    @pytest.mark.asyncio
    @patch("trustgraph.gateway.dispatch.core_import.KnowledgeRequestor")
    @patch("trustgraph.gateway.dispatch.core_export.KnowledgeRequestor")
    async def test_graph_embeddings_round_trip(
        self, mock_export_kr_class, mock_import_kr_class,
    ):
        # ----- export side: capture bytes -----
        export_bytes = []

        async def fake_export_process(req_dict, responder):
            await responder(_ge_response_dict(), True)

        export_kr = AsyncMock()
        export_kr.start = AsyncMock()
        export_kr.stop = AsyncMock()
        export_kr.process = fake_export_process
        mock_export_kr_class.return_value = export_kr

        response = AsyncMock()

        async def fake_write(b):
            export_bytes.append(b)

        response.write = fake_write
        response.write_eof = AsyncMock()

        exporter = CoreExport(backend=Mock())
        await exporter.process(
            data=Mock(),
            error=AsyncMock(),
            ok=AsyncMock(return_value=response),
            request=_make_request(),
        )

        assert len(export_bytes) == 1

        # ----- import side: feed those bytes back in -----
        import_captured = []

        async def fake_import_process(req_dict):
            import_captured.append(req_dict)

        import_kr = AsyncMock()
        import_kr.start = AsyncMock()
        import_kr.stop = AsyncMock()
        import_kr.process = fake_import_process
        mock_import_kr_class.return_value = import_kr

        importer = CoreImport(backend=Mock())
        await importer.process(
            data=_make_data_reader(export_bytes[0]),
            error=AsyncMock(),
            ok=AsyncMock(return_value=AsyncMock(write_eof=AsyncMock())),
            request=_make_request(),
        )

        # ----- verify the dict the importer would hand to the translator -----
        assert len(import_captured) == 1
        req = import_captured[0]

        original = _ge_response_dict()["graph-embeddings"]

        ge = req["graph-embeddings"]
        # The import side overrides id/user from the URL query (intentional),
        # so we only round-trip the entity payload itself.
        assert ge["metadata"]["id"] == original["metadata"]["id"]
        assert ge["metadata"]["user"] == original["metadata"]["user"]

        assert len(ge["entities"]) == len(original["entities"])
        for got, want in zip(ge["entities"], original["entities"]):
            assert got["vector"] == want["vector"]
            assert got["entity"] == want["entity"]
