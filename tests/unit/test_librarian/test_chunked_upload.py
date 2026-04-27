"""
Tests for librarian chunked upload operations:
begin_upload, upload_chunk, complete_upload, abort_upload, get_upload_status,
list_uploads, and stream_document.
"""

import base64
import json
import math
import pytest
from unittest.mock import AsyncMock, MagicMock, patch

from trustgraph.librarian.librarian import Librarian, DEFAULT_CHUNK_SIZE
from trustgraph.exceptions import RequestError


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_librarian(min_chunk_size=1):
    """Create a Librarian with mocked blob_store and table_store."""
    lib = Librarian.__new__(Librarian)
    lib.blob_store = MagicMock()
    lib.blob_store.create_multipart_upload = AsyncMock()
    lib.blob_store.upload_part = AsyncMock()
    lib.blob_store.complete_multipart_upload = AsyncMock()
    lib.blob_store.abort_multipart_upload = AsyncMock()
    lib.table_store = AsyncMock()
    lib.load_document = AsyncMock()
    lib.min_chunk_size = min_chunk_size
    return lib


def _make_doc_metadata(
    doc_id="doc-1", kind="application/pdf", workspace="alice", title="Test Doc"
):
    meta = MagicMock()
    meta.id = doc_id
    meta.kind = kind
    meta.workspace = workspace
    meta.title = title
    meta.time = 1700000000
    meta.comments = ""
    meta.tags = []
    return meta


def _make_begin_request(
    doc_id="doc-1", kind="application/pdf", workspace="alice",
    total_size=10_000_000, chunk_size=0
):
    req = MagicMock()
    req.document_metadata = _make_doc_metadata(doc_id=doc_id, kind=kind, workspace=workspace)
    req.total_size = total_size
    req.chunk_size = chunk_size
    return req


def _make_upload_chunk_request(upload_id="up-1", chunk_index=0, workspace="alice", content=b"data"):
    req = MagicMock()
    req.upload_id = upload_id
    req.chunk_index = chunk_index
    req.workspace = workspace
    req.content = base64.b64encode(content)
    return req


def _make_session(
    workspace="alice", total_chunks=5, chunk_size=2_000_000,
    total_size=10_000_000, chunks_received=None, object_id="obj-1",
    s3_upload_id="s3-up-1", document_metadata=None, document_id="doc-1",
):
    if chunks_received is None:
        chunks_received = {}
    if document_metadata is None:
        document_metadata = json.dumps({
            "id": document_id, "kind": "application/pdf",
            "workspace": workspace, "title": "Test", "time": 1700000000,
            "comments": "", "tags": [],
        })
    return {
        "workspace": workspace,
        "total_chunks": total_chunks,
        "chunk_size": chunk_size,
        "total_size": total_size,
        "chunks_received": chunks_received,
        "object_id": object_id,
        "s3_upload_id": s3_upload_id,
        "document_metadata": document_metadata,
        "document_id": document_id,
    }


# ---------------------------------------------------------------------------
# begin_upload
# ---------------------------------------------------------------------------

class TestBeginUpload:

    @pytest.mark.asyncio
    async def test_creates_session(self):
        lib = _make_librarian()
        lib.table_store.document_exists.return_value = False
        lib.blob_store.create_multipart_upload.return_value = "s3-upload-id"

        req = _make_begin_request(total_size=10_000_000)
        resp = await lib.begin_upload(req)

        assert resp.error is None
        assert resp.upload_id is not None
        assert resp.total_chunks == math.ceil(10_000_000 / DEFAULT_CHUNK_SIZE)
        assert resp.chunk_size == DEFAULT_CHUNK_SIZE

    @pytest.mark.asyncio
    async def test_custom_chunk_size(self):
        lib = _make_librarian()
        lib.table_store.document_exists.return_value = False
        lib.blob_store.create_multipart_upload.return_value = "s3-id"

        req = _make_begin_request(total_size=10_000, chunk_size=3000)
        resp = await lib.begin_upload(req)

        assert resp.chunk_size == 3000
        assert resp.total_chunks == math.ceil(10_000 / 3000)

    @pytest.mark.asyncio
    async def test_rejects_empty_kind(self):
        lib = _make_librarian()
        req = _make_begin_request(kind="")

        with pytest.raises(RequestError, match="MIME type.*required"):
            await lib.begin_upload(req)

    @pytest.mark.asyncio
    async def test_rejects_duplicate_document(self):
        lib = _make_librarian()
        lib.table_store.document_exists.return_value = True

        req = _make_begin_request()
        with pytest.raises(RequestError, match="already exists"):
            await lib.begin_upload(req)

    @pytest.mark.asyncio
    async def test_rejects_zero_size(self):
        lib = _make_librarian()
        lib.table_store.document_exists.return_value = False

        req = _make_begin_request(total_size=0)
        with pytest.raises(RequestError, match="positive"):
            await lib.begin_upload(req)

    @pytest.mark.asyncio
    async def test_rejects_chunk_below_minimum(self):
        lib = _make_librarian(min_chunk_size=1024)
        lib.table_store.document_exists.return_value = False

        req = _make_begin_request(total_size=10_000, chunk_size=512)
        with pytest.raises(RequestError, match="below minimum"):
            await lib.begin_upload(req)

    @pytest.mark.asyncio
    async def test_calls_s3_create_multipart(self):
        lib = _make_librarian()
        lib.table_store.document_exists.return_value = False
        lib.blob_store.create_multipart_upload.return_value = "s3-id"

        req = _make_begin_request(kind="application/pdf")
        await lib.begin_upload(req)

        lib.blob_store.create_multipart_upload.assert_called_once()
        # create_multipart_upload(object_id, kind) — positional args
        args = lib.blob_store.create_multipart_upload.call_args[0]
        assert args[1] == "application/pdf"

    @pytest.mark.asyncio
    async def test_stores_session_in_cassandra(self):
        lib = _make_librarian()
        lib.table_store.document_exists.return_value = False
        lib.blob_store.create_multipart_upload.return_value = "s3-id"

        req = _make_begin_request(total_size=5_000_000)
        resp = await lib.begin_upload(req)

        lib.table_store.create_upload_session.assert_called_once()
        kwargs = lib.table_store.create_upload_session.call_args[1]
        assert kwargs["upload_id"] == resp.upload_id
        assert kwargs["total_size"] == 5_000_000
        assert kwargs["total_chunks"] == resp.total_chunks

    @pytest.mark.asyncio
    async def test_accepts_text_plain(self):
        lib = _make_librarian()
        lib.table_store.document_exists.return_value = False
        lib.blob_store.create_multipart_upload.return_value = "s3-id"

        req = _make_begin_request(kind="text/plain", total_size=1000)
        resp = await lib.begin_upload(req)
        assert resp.error is None


# ---------------------------------------------------------------------------
# upload_chunk
# ---------------------------------------------------------------------------

class TestUploadChunk:

    @pytest.mark.asyncio
    async def test_successful_chunk_upload(self):
        lib = _make_librarian()
        session = _make_session(total_chunks=5, chunks_received={})
        lib.table_store.get_upload_session.return_value = session
        lib.blob_store.upload_part.return_value = "etag-1"

        req = _make_upload_chunk_request(chunk_index=0, content=b"chunk data")
        resp = await lib.upload_chunk(req)

        assert resp.error is None
        assert resp.chunk_index == 0
        assert resp.total_chunks == 5
        # The chunk is added to the dict (len=1), then +1 applied => 2
        assert resp.chunks_received == 2

    @pytest.mark.asyncio
    async def test_s3_part_number_is_1_indexed(self):
        lib = _make_librarian()
        session = _make_session()
        lib.table_store.get_upload_session.return_value = session
        lib.blob_store.upload_part.return_value = "etag"

        req = _make_upload_chunk_request(chunk_index=0)
        await lib.upload_chunk(req)

        kwargs = lib.blob_store.upload_part.call_args[1]
        assert kwargs["part_number"] == 1  # 0-indexed chunk → 1-indexed part

    @pytest.mark.asyncio
    async def test_chunk_index_3_becomes_part_4(self):
        lib = _make_librarian()
        session = _make_session()
        lib.table_store.get_upload_session.return_value = session
        lib.blob_store.upload_part.return_value = "etag"

        req = _make_upload_chunk_request(chunk_index=3)
        await lib.upload_chunk(req)

        kwargs = lib.blob_store.upload_part.call_args[1]
        assert kwargs["part_number"] == 4

    @pytest.mark.asyncio
    async def test_rejects_expired_session(self):
        lib = _make_librarian()
        lib.table_store.get_upload_session.return_value = None

        req = _make_upload_chunk_request()
        with pytest.raises(RequestError, match="not found"):
            await lib.upload_chunk(req)

    @pytest.mark.asyncio
    async def test_rejects_wrong_user(self):
        lib = _make_librarian()
        session = _make_session(workspace="alice")
        lib.table_store.get_upload_session.return_value = session

        req = _make_upload_chunk_request(workspace="bob")
        with pytest.raises(RequestError, match="Not authorized"):
            await lib.upload_chunk(req)

    @pytest.mark.asyncio
    async def test_rejects_negative_chunk_index(self):
        lib = _make_librarian()
        session = _make_session(total_chunks=5)
        lib.table_store.get_upload_session.return_value = session

        req = _make_upload_chunk_request(chunk_index=-1)
        with pytest.raises(RequestError, match="Invalid chunk index"):
            await lib.upload_chunk(req)

    @pytest.mark.asyncio
    async def test_rejects_out_of_range_chunk_index(self):
        lib = _make_librarian()
        session = _make_session(total_chunks=5)
        lib.table_store.get_upload_session.return_value = session

        req = _make_upload_chunk_request(chunk_index=5)
        with pytest.raises(RequestError, match="Invalid chunk index"):
            await lib.upload_chunk(req)

    @pytest.mark.asyncio
    async def test_progress_tracking(self):
        lib = _make_librarian()
        session = _make_session(
            total_chunks=4, chunk_size=1000, total_size=3500,
            chunks_received={0: "e1", 1: "e2"},
        )
        lib.table_store.get_upload_session.return_value = session
        lib.blob_store.upload_part.return_value = "e3"

        req = _make_upload_chunk_request(chunk_index=2)
        resp = await lib.upload_chunk(req)

        # Dict gets chunk 2 added (len=3), then +1 => 4
        assert resp.chunks_received == 4
        assert resp.total_chunks == 4
        assert resp.total_bytes == 3500

    @pytest.mark.asyncio
    async def test_bytes_capped_at_total_size(self):
        """bytes_received should not exceed total_size for the final chunk."""
        lib = _make_librarian()
        session = _make_session(
            total_chunks=2, chunk_size=3000, total_size=5000,
            chunks_received={0: "e1"},
        )
        lib.table_store.get_upload_session.return_value = session
        lib.blob_store.upload_part.return_value = "e2"

        req = _make_upload_chunk_request(chunk_index=1)
        resp = await lib.upload_chunk(req)

        # 3 chunks × 3000 = 9000 > 5000, so capped
        assert resp.bytes_received <= 5000

    @pytest.mark.asyncio
    async def test_base64_decodes_content(self):
        lib = _make_librarian()
        session = _make_session()
        lib.table_store.get_upload_session.return_value = session
        lib.blob_store.upload_part.return_value = "etag"

        raw = b"hello world binary data"
        req = _make_upload_chunk_request(content=raw)
        await lib.upload_chunk(req)

        kwargs = lib.blob_store.upload_part.call_args[1]
        assert kwargs["data"] == raw


# ---------------------------------------------------------------------------
# complete_upload
# ---------------------------------------------------------------------------

class TestCompleteUpload:

    @pytest.mark.asyncio
    async def test_successful_completion(self):
        lib = _make_librarian()
        session = _make_session(
            total_chunks=3,
            chunks_received={0: "e1", 1: "e2", 2: "e3"},
        )
        lib.table_store.get_upload_session.return_value = session

        req = MagicMock()
        req.upload_id = "up-1"
        req.workspace = "alice"

        resp = await lib.complete_upload(req)

        assert resp.error is None
        assert resp.document_id == "doc-1"
        lib.blob_store.complete_multipart_upload.assert_called_once()
        lib.table_store.add_document.assert_called_once()
        lib.table_store.delete_upload_session.assert_called_once_with("up-1")

    @pytest.mark.asyncio
    async def test_parts_sorted_by_index(self):
        lib = _make_librarian()
        # Chunks received out of order
        session = _make_session(
            total_chunks=3,
            chunks_received={2: "e3", 0: "e1", 1: "e2"},
        )
        lib.table_store.get_upload_session.return_value = session

        req = MagicMock()
        req.upload_id = "up-1"
        req.workspace = "alice"

        await lib.complete_upload(req)

        parts = lib.blob_store.complete_multipart_upload.call_args[1]["parts"]
        part_numbers = [p[0] for p in parts]
        assert part_numbers == [1, 2, 3]  # Sorted, 1-indexed

    @pytest.mark.asyncio
    async def test_rejects_missing_chunks(self):
        lib = _make_librarian()
        session = _make_session(
            total_chunks=3,
            chunks_received={0: "e1", 2: "e3"},  # chunk 1 missing
        )
        lib.table_store.get_upload_session.return_value = session

        req = MagicMock()
        req.upload_id = "up-1"
        req.workspace = "alice"

        with pytest.raises(RequestError, match="Missing chunks"):
            await lib.complete_upload(req)

    @pytest.mark.asyncio
    async def test_rejects_expired_session(self):
        lib = _make_librarian()
        lib.table_store.get_upload_session.return_value = None

        req = MagicMock()
        req.upload_id = "up-gone"
        req.workspace = "alice"

        with pytest.raises(RequestError, match="not found"):
            await lib.complete_upload(req)

    @pytest.mark.asyncio
    async def test_rejects_wrong_user(self):
        lib = _make_librarian()
        session = _make_session(workspace="alice")
        lib.table_store.get_upload_session.return_value = session

        req = MagicMock()
        req.upload_id = "up-1"
        req.workspace = "bob"

        with pytest.raises(RequestError, match="Not authorized"):
            await lib.complete_upload(req)


# ---------------------------------------------------------------------------
# abort_upload
# ---------------------------------------------------------------------------

class TestAbortUpload:

    @pytest.mark.asyncio
    async def test_aborts_and_cleans_up(self):
        lib = _make_librarian()
        session = _make_session()
        lib.table_store.get_upload_session.return_value = session

        req = MagicMock()
        req.upload_id = "up-1"
        req.workspace = "alice"

        resp = await lib.abort_upload(req)

        assert resp.error is None
        lib.blob_store.abort_multipart_upload.assert_called_once_with(
            object_id="obj-1", upload_id="s3-up-1"
        )
        lib.table_store.delete_upload_session.assert_called_once_with("up-1")

    @pytest.mark.asyncio
    async def test_rejects_expired_session(self):
        lib = _make_librarian()
        lib.table_store.get_upload_session.return_value = None

        req = MagicMock()
        req.upload_id = "up-gone"
        req.workspace = "alice"

        with pytest.raises(RequestError, match="not found"):
            await lib.abort_upload(req)

    @pytest.mark.asyncio
    async def test_rejects_wrong_user(self):
        lib = _make_librarian()
        session = _make_session(workspace="alice")
        lib.table_store.get_upload_session.return_value = session

        req = MagicMock()
        req.upload_id = "up-1"
        req.workspace = "bob"

        with pytest.raises(RequestError, match="Not authorized"):
            await lib.abort_upload(req)


# ---------------------------------------------------------------------------
# get_upload_status
# ---------------------------------------------------------------------------

class TestGetUploadStatus:

    @pytest.mark.asyncio
    async def test_in_progress_status(self):
        lib = _make_librarian()
        session = _make_session(
            total_chunks=5, chunk_size=2000, total_size=10_000,
            chunks_received={0: "e1", 2: "e3", 4: "e5"},
        )
        lib.table_store.get_upload_session.return_value = session

        req = MagicMock()
        req.upload_id = "up-1"
        req.workspace = "alice"

        resp = await lib.get_upload_status(req)

        assert resp.upload_state == "in-progress"
        assert resp.chunks_received == 3
        assert resp.total_chunks == 5
        assert sorted(resp.received_chunks) == [0, 2, 4]
        assert sorted(resp.missing_chunks) == [1, 3]
        assert resp.total_bytes == 10_000

    @pytest.mark.asyncio
    async def test_expired_session(self):
        lib = _make_librarian()
        lib.table_store.get_upload_session.return_value = None

        req = MagicMock()
        req.upload_id = "up-expired"
        req.workspace = "alice"

        resp = await lib.get_upload_status(req)

        assert resp.upload_state == "expired"

    @pytest.mark.asyncio
    async def test_all_chunks_received(self):
        lib = _make_librarian()
        session = _make_session(
            total_chunks=3, chunk_size=1000, total_size=2500,
            chunks_received={0: "e1", 1: "e2", 2: "e3"},
        )
        lib.table_store.get_upload_session.return_value = session

        req = MagicMock()
        req.upload_id = "up-1"
        req.workspace = "alice"

        resp = await lib.get_upload_status(req)

        assert resp.missing_chunks == []
        assert resp.chunks_received == 3
        # 3 * 1000 = 3000 > 2500, so capped
        assert resp.bytes_received <= 2500

    @pytest.mark.asyncio
    async def test_rejects_wrong_user(self):
        lib = _make_librarian()
        session = _make_session(workspace="alice")
        lib.table_store.get_upload_session.return_value = session

        req = MagicMock()
        req.upload_id = "up-1"
        req.workspace = "bob"

        with pytest.raises(RequestError, match="Not authorized"):
            await lib.get_upload_status(req)


# ---------------------------------------------------------------------------
# stream_document
# ---------------------------------------------------------------------------

class TestStreamDocument:

    @pytest.mark.asyncio
    async def test_streams_chunks_with_progress(self):
        lib = _make_librarian()
        lib.table_store.get_document_object_id.return_value = "obj-1"
        lib.blob_store.get_size = AsyncMock(return_value=5000)
        lib.blob_store.get_range = AsyncMock(return_value=b"x" * 2000)

        req = MagicMock()
        req.workspace = "alice"
        req.document_id = "doc-1"
        req.chunk_size = 2000

        chunks = []
        async for resp in lib.stream_document(req):
            chunks.append(resp)

        assert len(chunks) == 3  # ceil(5000/2000)
        assert chunks[0].chunk_index == 0
        assert chunks[0].total_chunks == 3
        assert chunks[0].is_final is False
        assert chunks[-1].is_final is True
        assert chunks[-1].chunk_index == 2

    @pytest.mark.asyncio
    async def test_single_chunk_document(self):
        lib = _make_librarian()
        lib.table_store.get_document_object_id.return_value = "obj-1"
        lib.blob_store.get_size = AsyncMock(return_value=500)
        lib.blob_store.get_range = AsyncMock(return_value=b"x" * 500)

        req = MagicMock()
        req.workspace = "alice"
        req.document_id = "doc-1"
        req.chunk_size = 2000

        chunks = []
        async for resp in lib.stream_document(req):
            chunks.append(resp)

        assert len(chunks) == 1
        assert chunks[0].is_final is True
        assert chunks[0].bytes_received == 500
        assert chunks[0].total_bytes == 500

    @pytest.mark.asyncio
    async def test_byte_ranges_correct(self):
        lib = _make_librarian()
        lib.table_store.get_document_object_id.return_value = "obj-1"
        lib.blob_store.get_size = AsyncMock(return_value=5000)
        lib.blob_store.get_range = AsyncMock(return_value=b"x" * 100)

        req = MagicMock()
        req.workspace = "alice"
        req.document_id = "doc-1"
        req.chunk_size = 2000

        chunks = []
        async for resp in lib.stream_document(req):
            chunks.append(resp)

        # Verify the byte ranges passed to get_range
        calls = lib.blob_store.get_range.call_args_list
        assert calls[0][0] == ("obj-1", 0, 2000)
        assert calls[1][0] == ("obj-1", 2000, 2000)
        assert calls[2][0] == ("obj-1", 4000, 1000)  # Last chunk: 5000-4000

    @pytest.mark.asyncio
    async def test_default_chunk_size(self):
        lib = _make_librarian()
        lib.table_store.get_document_object_id.return_value = "obj-1"
        lib.blob_store.get_size = AsyncMock(return_value=2_000_000)
        lib.blob_store.get_range = AsyncMock(return_value=b"x")

        req = MagicMock()
        req.workspace = "alice"
        req.document_id = "doc-1"
        req.chunk_size = 0  # Should use default 1MB

        chunks = []
        async for resp in lib.stream_document(req):
            chunks.append(resp)

        assert len(chunks) == 2  # ceil(2MB / 1MB)

    @pytest.mark.asyncio
    async def test_content_is_base64_encoded(self):
        lib = _make_librarian()
        lib.table_store.get_document_object_id.return_value = "obj-1"
        lib.blob_store.get_size = AsyncMock(return_value=100)
        raw = b"hello world"
        lib.blob_store.get_range = AsyncMock(return_value=raw)

        req = MagicMock()
        req.workspace = "alice"
        req.document_id = "doc-1"
        req.chunk_size = 1000

        chunks = []
        async for resp in lib.stream_document(req):
            chunks.append(resp)

        assert chunks[0].content == base64.b64encode(raw)

    @pytest.mark.asyncio
    async def test_rejects_chunk_below_minimum(self):
        lib = _make_librarian(min_chunk_size=1024)
        lib.table_store.get_document_object_id.return_value = "obj-1"
        lib.blob_store.get_size = AsyncMock(return_value=5000)

        req = MagicMock()
        req.workspace = "alice"
        req.document_id = "doc-1"
        req.chunk_size = 512

        with pytest.raises(RequestError, match="below minimum"):
            async for _ in lib.stream_document(req):
                pass


# ---------------------------------------------------------------------------
# list_uploads
# ---------------------------------------------------------------------------

class TestListUploads:

    @pytest.mark.asyncio
    async def test_returns_sessions(self):
        lib = _make_librarian()
        lib.table_store.list_upload_sessions.return_value = [
            {
                "upload_id": "up-1",
                "document_id": "doc-1",
                "document_metadata": '{"id":"doc-1"}',
                "total_size": 10000,
                "chunk_size": 2000,
                "total_chunks": 5,
                "chunks_received": {0: "e1", 1: "e2"},
                "created_at": "2024-01-01",
            },
        ]

        req = MagicMock()
        req.workspace = "alice"

        resp = await lib.list_uploads(req)

        assert resp.error is None
        assert len(resp.upload_sessions) == 1
        assert resp.upload_sessions[0].upload_id == "up-1"
        assert resp.upload_sessions[0].total_chunks == 5

    @pytest.mark.asyncio
    async def test_empty_uploads(self):
        lib = _make_librarian()
        lib.table_store.list_upload_sessions.return_value = []

        req = MagicMock()
        req.workspace = "alice"

        resp = await lib.list_uploads(req)

        assert resp.upload_sessions == []
