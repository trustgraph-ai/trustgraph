
import json
import websockets
from typing import Optional, AsyncIterator, Dict, Any, Iterator

from . types import Triple
from . bulk_client import _string_to_term


class AsyncBulkClient:
    """Asynchronous bulk operations client"""

    def __init__(self, url: str, timeout: int, token: Optional[str], workspace: str = "default") -> None:
        self.url: str = self._convert_to_ws_url(url)
        self.timeout: int = timeout
        self.token: Optional[str] = token
        self.workspace: str = workspace

    def _convert_to_ws_url(self, url: str) -> str:
        """Convert HTTP URL to WebSocket URL"""
        if url.startswith("http://"):
            return url.replace("http://", "ws://", 1)
        elif url.startswith("https://"):
            return url.replace("https://", "wss://", 1)
        elif url.startswith("ws://") or url.startswith("wss://"):
            return url
        else:
            return f"ws://{url}"

    def _build_ws_url(self, path: str) -> str:
        """Build a WebSocket URL with token and workspace query params."""
        ws_url = f"{self.url}{path}"
        params = []
        if self.token:
            params.append(f"token={self.token}")
        if self.workspace:
            params.append(f"workspace={self.workspace}")
        if params:
            ws_url = f"{ws_url}?{'&'.join(params)}"
        return ws_url

    async def import_triples(self, flow: str, triples: AsyncIterator[Triple], **kwargs: Any) -> None:
        """Bulk import triples via WebSocket"""
        ws_url = self._build_ws_url(f"/api/v1/flow/{flow}/import/triples")

        async with websockets.connect(ws_url, ping_interval=20, ping_timeout=self.timeout) as websocket:
            async for triple in triples:
                message = {
                    "s": _string_to_term(triple.s),
                    "p": _string_to_term(triple.p),
                    "o": _string_to_term(
                        triple.o,
                        datatype=triple.o_datatype,
                        language=triple.o_language,
                    ),
                }
                await websocket.send(json.dumps(message))

    async def export_triples(self, flow: str, **kwargs: Any) -> AsyncIterator[Triple]:
        """Bulk export triples via WebSocket"""
        ws_url = self._build_ws_url(f"/api/v1/flow/{flow}/export/triples")

        async with websockets.connect(ws_url, ping_interval=20, ping_timeout=self.timeout) as websocket:
            async for raw_message in websocket:
                data = json.loads(raw_message)
                yield Triple(
                    s=data.get("s", ""),
                    p=data.get("p", ""),
                    o=data.get("o", "")
                )

    async def import_graph_embeddings(self, flow: str, embeddings: AsyncIterator[Dict[str, Any]], **kwargs: Any) -> None:
        """Bulk import graph embeddings via WebSocket"""
        ws_url = self._build_ws_url(f"/api/v1/flow/{flow}/import/graph-embeddings")

        async with websockets.connect(ws_url, ping_interval=20, ping_timeout=self.timeout) as websocket:
            async for embedding in embeddings:
                await websocket.send(json.dumps(embedding))

    async def export_graph_embeddings(self, flow: str, **kwargs: Any) -> AsyncIterator[Dict[str, Any]]:
        """Bulk export graph embeddings via WebSocket"""
        ws_url = self._build_ws_url(f"/api/v1/flow/{flow}/export/graph-embeddings")

        async with websockets.connect(ws_url, ping_interval=20, ping_timeout=self.timeout) as websocket:
            async for raw_message in websocket:
                yield json.loads(raw_message)

    async def import_document_embeddings(self, flow: str, embeddings: AsyncIterator[Dict[str, Any]], **kwargs: Any) -> None:
        """Bulk import document embeddings via WebSocket"""
        ws_url = self._build_ws_url(f"/api/v1/flow/{flow}/import/document-embeddings")

        async with websockets.connect(ws_url, ping_interval=20, ping_timeout=self.timeout) as websocket:
            async for embedding in embeddings:
                await websocket.send(json.dumps(embedding))

    async def export_document_embeddings(self, flow: str, **kwargs: Any) -> AsyncIterator[Dict[str, Any]]:
        """Bulk export document embeddings via WebSocket"""
        ws_url = self._build_ws_url(f"/api/v1/flow/{flow}/export/document-embeddings")

        async with websockets.connect(ws_url, ping_interval=20, ping_timeout=self.timeout) as websocket:
            async for raw_message in websocket:
                yield json.loads(raw_message)

    async def import_entity_contexts(self, flow: str, contexts: AsyncIterator[Dict[str, Any]], **kwargs: Any) -> None:
        """Bulk import entity contexts via WebSocket"""
        ws_url = self._build_ws_url(f"/api/v1/flow/{flow}/import/entity-contexts")

        async with websockets.connect(ws_url, ping_interval=20, ping_timeout=self.timeout) as websocket:
            async for context in contexts:
                await websocket.send(json.dumps(context))

    async def export_entity_contexts(self, flow: str, **kwargs: Any) -> AsyncIterator[Dict[str, Any]]:
        """Bulk export entity contexts via WebSocket"""
        ws_url = self._build_ws_url(f"/api/v1/flow/{flow}/export/entity-contexts")

        async with websockets.connect(ws_url, ping_interval=20, ping_timeout=self.timeout) as websocket:
            async for raw_message in websocket:
                yield json.loads(raw_message)

    async def import_rows(
        self, flow: str, rows: AsyncIterator[Dict[str, Any]],
        batch_size: int = 40,
        **kwargs: Any,
    ) -> None:
        """Bulk import rows via WebSocket"""
        ws_url = self._build_ws_url(f"/api/v1/flow/{flow}/import/rows")

        async with websockets.connect(ws_url, ping_interval=20, ping_timeout=self.timeout) as websocket:
            batch = []
            template = None
            async for row in rows:
                if template is None:
                    template = row
                batch.append(row.get("values", row))
                if len(batch) >= batch_size:
                    message = dict(template)
                    message["values"] = batch
                    await websocket.send(json.dumps(message))
                    batch = []
            if batch:
                message = dict(template)
                message["values"] = batch
                await websocket.send(json.dumps(message))

    async def aclose(self) -> None:
        """Close connections"""
        # Cleanup handled by context managers
        pass
