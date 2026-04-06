from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock, patch
import base64

import pytest

from trustgraph.mcp_server.mcp import McpServer, encode_document_content


class TestEncodeDocumentContent:
    def test_encodes_text_payloads(self):
        encoded = encode_document_content("hello world", "text/plain")
        assert encoded == base64.b64encode(b"hello world").decode("utf-8")

    def test_passes_through_binary_payloads(self):
        pdf_payload = "JVBERi0xLjQKJcTl8uXrpA=="
        assert encode_document_content(pdf_payload, "application/pdf") == pdf_payload


@pytest.mark.asyncio
class TestLoadDocument:
    @patch("trustgraph.mcp_server.mcp.get_socket_manager")
    async def test_load_document_base64_encodes_text_content(self, mock_get_socket_manager):
        server = McpServer()

        manager = MagicMock()
        manager.request.return_value = self._single_response()
        mock_get_socket_manager.return_value = manager

        ctx = SimpleNamespace(
            request_id="req-123",
            session=SimpleNamespace(send_log_message=AsyncMock()),
        )

        await server.load_document(
            document="plain text body",
            document_id="doc-1",
            mime_type="text/plain",
            title="Example",
            user="trustgraph",
            ctx=ctx,
        )

        manager.request.assert_called_once()
        _, request_data, _ = manager.request.call_args.args
        assert request_data["content"] == base64.b64encode(b"plain text body").decode("utf-8")

    async def _single_response(self):
        yield {}
