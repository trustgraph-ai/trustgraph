"""
Tests for row embeddings query service: collection naming, query execution,
index filtering, result conversion, and error handling.
"""

import pytest
from unittest.mock import MagicMock, AsyncMock, patch

from trustgraph.schema import (
    RowEmbeddingsRequest, RowEmbeddingsResponse,
    RowIndexMatch, Error,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_processor(qdrant_client=None):
    """Create a Processor without full FlowProcessor init."""
    from trustgraph.query.row_embeddings.qdrant.service import Processor
    proc = Processor.__new__(Processor)
    proc.qdrant = qdrant_client or MagicMock()
    return proc


def _make_request(vector=None, collection="test-col",
                  schema_name="customers", limit=10, index_name=None):
    return RowEmbeddingsRequest(
        vector=vector or [0.1, 0.2, 0.3],
        collection=collection,
        schema_name=schema_name,
        limit=limit,
        index_name=index_name or "",
    )


def _make_flow(workspace="test-workspace", pub=None):
    """Make a mock flow object that is callable and has .workspace."""
    flow = MagicMock()
    flow.return_value = pub if pub is not None else AsyncMock()
    flow.workspace = workspace
    return flow


def _make_search_point(index_name, index_value, text, score):
    point = MagicMock()
    point.payload = {
        "index_name": index_name,
        "index_value": index_value,
        "text": text,
    }
    point.score = score
    return point


# ---------------------------------------------------------------------------
# sanitize_name
# ---------------------------------------------------------------------------

class TestSanitizeName:

    def test_simple_name(self):
        proc = _make_processor()
        assert proc.sanitize_name("customers") == "customers"

    def test_special_chars_replaced(self):
        proc = _make_processor()
        assert proc.sanitize_name("my-schema.v2") == "my_schema_v2"

    def test_leading_digit_prefixed(self):
        proc = _make_processor()
        result = proc.sanitize_name("123schema")
        assert result.startswith("r_")
        assert "123schema" in result

    def test_uppercase_lowercased(self):
        proc = _make_processor()
        assert proc.sanitize_name("MySchema") == "myschema"

    def test_spaces_replaced(self):
        proc = _make_processor()
        assert proc.sanitize_name("my schema") == "my_schema"


# ---------------------------------------------------------------------------
# find_collection
# ---------------------------------------------------------------------------

class TestFindCollection:

    def test_finds_matching_collection(self):
        proc = _make_processor()
        mock_coll = MagicMock()
        mock_coll.name = "rows_test_workspace_test_col_customers_384"

        mock_collections = MagicMock()
        mock_collections.collections = [mock_coll]
        proc.qdrant.get_collections.return_value = mock_collections

        result = proc.find_collection("test-workspace", "test-col", "customers")

        assert result == "rows_test_workspace_test_col_customers_384"

    def test_returns_none_when_no_match(self):
        proc = _make_processor()
        mock_coll = MagicMock()
        mock_coll.name = "rows_other_workspace_other_col_schema_768"

        mock_collections = MagicMock()
        mock_collections.collections = [mock_coll]
        proc.qdrant.get_collections.return_value = mock_collections

        result = proc.find_collection("test-workspace", "test-col", "customers")
        assert result is None

    def test_returns_none_on_error(self):
        proc = _make_processor()
        proc.qdrant.get_collections.side_effect = Exception("connection error")

        result = proc.find_collection("workspace", "col", "schema")
        assert result is None


# ---------------------------------------------------------------------------
# query_row_embeddings
# ---------------------------------------------------------------------------

class TestQueryRowEmbeddings:

    @pytest.mark.asyncio
    async def test_empty_vector_returns_empty(self):
        proc = _make_processor()
        request = _make_request(vector=[])

        result = await proc.query_row_embeddings("test-workspace", request)
        assert result == []

    @pytest.mark.asyncio
    async def test_no_collection_returns_empty(self):
        proc = _make_processor()
        proc.find_collection = MagicMock(return_value=None)
        request = _make_request()

        result = await proc.query_row_embeddings("test-workspace", request)
        assert result == []

    @pytest.mark.asyncio
    async def test_successful_query_returns_matches(self):
        proc = _make_processor()
        proc.find_collection = MagicMock(return_value="rows_w_c_s_384")

        points = [
            _make_search_point("name", ["Alice Smith"], "Alice Smith", 0.95),
            _make_search_point("address", ["123 Main St"], "123 Main St", 0.82),
        ]
        mock_result = MagicMock()
        mock_result.points = points
        proc.qdrant.query_points.return_value = mock_result

        request = _make_request()
        result = await proc.query_row_embeddings("test-workspace", request)

        assert len(result) == 2
        assert isinstance(result[0], RowIndexMatch)
        assert result[0].index_name == "name"
        assert result[0].index_value == ["Alice Smith"]
        assert result[0].score == 0.95
        assert result[1].index_name == "address"

    @pytest.mark.asyncio
    async def test_index_name_filter_applied(self):
        """When index_name is specified, a Qdrant filter should be used."""
        proc = _make_processor()
        proc.find_collection = MagicMock(return_value="rows_w_c_s_384")

        mock_result = MagicMock()
        mock_result.points = []
        proc.qdrant.query_points.return_value = mock_result

        request = _make_request(index_name="address")
        await proc.query_row_embeddings("test-workspace", request)

        call_kwargs = proc.qdrant.query_points.call_args[1]
        assert call_kwargs["query_filter"] is not None

    @pytest.mark.asyncio
    async def test_no_index_name_no_filter(self):
        """When index_name is empty, no filter should be applied."""
        proc = _make_processor()
        proc.find_collection = MagicMock(return_value="rows_w_c_s_384")

        mock_result = MagicMock()
        mock_result.points = []
        proc.qdrant.query_points.return_value = mock_result

        request = _make_request(index_name="")
        await proc.query_row_embeddings("test-workspace", request)

        call_kwargs = proc.qdrant.query_points.call_args[1]
        assert call_kwargs["query_filter"] is None

    @pytest.mark.asyncio
    async def test_missing_payload_fields_default(self):
        """Points with missing payload fields should use defaults."""
        proc = _make_processor()
        proc.find_collection = MagicMock(return_value="rows_w_c_s_384")

        point = MagicMock()
        point.payload = {}  # Empty payload
        point.score = 0.5

        mock_result = MagicMock()
        mock_result.points = [point]
        proc.qdrant.query_points.return_value = mock_result

        request = _make_request()
        result = await proc.query_row_embeddings("test-workspace", request)

        assert len(result) == 1
        assert result[0].index_name == ""
        assert result[0].index_value == []
        assert result[0].text == ""

    @pytest.mark.asyncio
    async def test_qdrant_error_propagates(self):
        proc = _make_processor()
        proc.find_collection = MagicMock(return_value="rows_w_c_s_384")
        proc.qdrant.query_points.side_effect = Exception("qdrant down")

        request = _make_request()

        with pytest.raises(Exception, match="qdrant down"):
            await proc.query_row_embeddings("test-workspace", request)


# ---------------------------------------------------------------------------
# on_message handler
# ---------------------------------------------------------------------------

class TestOnMessage:

    @pytest.mark.asyncio
    async def test_successful_message_sends_response(self):
        proc = _make_processor()
        proc.query_row_embeddings = AsyncMock(return_value=[
            RowIndexMatch(index_name="name", index_value=["Alice"],
                          text="Alice", score=0.9),
        ])

        mock_pub = AsyncMock()
        flow = _make_flow(pub=mock_pub)

        msg = MagicMock()
        msg.value.return_value = _make_request()
        msg.properties.return_value = {"id": "req-1"}

        await proc.on_message(msg, MagicMock(), flow)

        sent = mock_pub.send.call_args[0][0]
        assert isinstance(sent, RowEmbeddingsResponse)
        assert sent.error is None
        assert len(sent.matches) == 1

    @pytest.mark.asyncio
    async def test_error_sends_error_response(self):
        proc = _make_processor()
        proc.query_row_embeddings = AsyncMock(
            side_effect=Exception("query failed")
        )

        mock_pub = AsyncMock()
        flow = _make_flow(pub=mock_pub)

        msg = MagicMock()
        msg.value.return_value = _make_request()
        msg.properties.return_value = {"id": "req-2"}

        await proc.on_message(msg, MagicMock(), flow)

        sent = mock_pub.send.call_args[0][0]
        assert sent.error is not None
        assert sent.error.type == "row-embeddings-query-error"
        assert "query failed" in sent.error.message
        assert sent.matches == []

    @pytest.mark.asyncio
    async def test_message_id_preserved(self):
        proc = _make_processor()
        proc.query_row_embeddings = AsyncMock(return_value=[])

        mock_pub = AsyncMock()
        flow = _make_flow(pub=mock_pub)

        msg = MagicMock()
        msg.value.return_value = _make_request()
        msg.properties.return_value = {"id": "unique-42"}

        await proc.on_message(msg, MagicMock(), flow)

        props = mock_pub.send.call_args[1]["properties"]
        assert props["id"] == "unique-42"
