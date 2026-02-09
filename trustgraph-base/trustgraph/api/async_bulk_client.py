
import json
import websockets
from typing import Optional, AsyncIterator, Dict, Any, Iterator

from . types import Triple


class AsyncBulkClient:
    """Asynchronous bulk operations client"""

    def __init__(self, url: str, timeout: int, token: Optional[str]) -> None:
        self.url: str = self._convert_to_ws_url(url)
        self.timeout: int = timeout
        self.token: Optional[str] = token

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

    async def import_triples(self, flow: str, triples: AsyncIterator[Triple], **kwargs: Any) -> None:
        """Bulk import triples via WebSocket"""
        metadata = kwargs.get('metadata')
        ws_url = f"{self.url}/api/v1/flow/{flow}/import/triples"
        if self.token:
            ws_url = f"{ws_url}?token={self.token}"

        async with websockets.connect(ws_url, ping_interval=20, ping_timeout=self.timeout) as websocket:
            async for triple in triples:
                # Format in Value format expected by gateway
                s_is_uri = getattr(triple, 's_is_uri', True)
                p_is_uri = getattr(triple, 'p_is_uri', True)
                o_is_uri = getattr(triple, 'o_is_uri', True)
                message = {
                    "metadata": metadata or {},
                    "triples": [
                        {
                            "s": {"v": triple.s, "e": s_is_uri},
                            "p": {"v": triple.p, "e": p_is_uri},
                            "o": {"v": triple.o, "e": o_is_uri},
                        }
                    ]
                }
                await websocket.send(json.dumps(message))

    async def export_triples(self, flow: str, **kwargs: Any) -> AsyncIterator[Triple]:
        """Bulk export triples via WebSocket"""
        ws_url = f"{self.url}/api/v1/flow/{flow}/export/triples"
        if self.token:
            ws_url = f"{ws_url}?token={self.token}"

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
        ws_url = f"{self.url}/api/v1/flow/{flow}/import/graph-embeddings"
        if self.token:
            ws_url = f"{ws_url}?token={self.token}"

        async with websockets.connect(ws_url, ping_interval=20, ping_timeout=self.timeout) as websocket:
            async for embedding in embeddings:
                await websocket.send(json.dumps(embedding))

    async def export_graph_embeddings(self, flow: str, **kwargs: Any) -> AsyncIterator[Dict[str, Any]]:
        """Bulk export graph embeddings via WebSocket"""
        ws_url = f"{self.url}/api/v1/flow/{flow}/export/graph-embeddings"
        if self.token:
            ws_url = f"{ws_url}?token={self.token}"

        async with websockets.connect(ws_url, ping_interval=20, ping_timeout=self.timeout) as websocket:
            async for raw_message in websocket:
                yield json.loads(raw_message)

    async def import_document_embeddings(self, flow: str, embeddings: AsyncIterator[Dict[str, Any]], **kwargs: Any) -> None:
        """Bulk import document embeddings via WebSocket"""
        ws_url = f"{self.url}/api/v1/flow/{flow}/import/document-embeddings"
        if self.token:
            ws_url = f"{ws_url}?token={self.token}"

        async with websockets.connect(ws_url, ping_interval=20, ping_timeout=self.timeout) as websocket:
            async for embedding in embeddings:
                await websocket.send(json.dumps(embedding))

    async def export_document_embeddings(self, flow: str, **kwargs: Any) -> AsyncIterator[Dict[str, Any]]:
        """Bulk export document embeddings via WebSocket"""
        ws_url = f"{self.url}/api/v1/flow/{flow}/export/document-embeddings"
        if self.token:
            ws_url = f"{ws_url}?token={self.token}"

        async with websockets.connect(ws_url, ping_interval=20, ping_timeout=self.timeout) as websocket:
            async for raw_message in websocket:
                yield json.loads(raw_message)

    async def import_entity_contexts(self, flow: str, contexts: AsyncIterator[Dict[str, Any]], **kwargs: Any) -> None:
        """Bulk import entity contexts via WebSocket"""
        metadata = kwargs.get('metadata')
        ws_url = f"{self.url}/api/v1/flow/{flow}/import/entity-contexts"
        if self.token:
            ws_url = f"{ws_url}?token={self.token}"

        async with websockets.connect(ws_url, ping_interval=20, ping_timeout=self.timeout) as websocket:
            async for context in contexts:
                message = {
                    "metadata": metadata or {},
                    "entities": [context]
                }
                await websocket.send(json.dumps(message))

    async def export_entity_contexts(self, flow: str, **kwargs: Any) -> AsyncIterator[Dict[str, Any]]:
        """Bulk export entity contexts via WebSocket"""
        ws_url = f"{self.url}/api/v1/flow/{flow}/export/entity-contexts"
        if self.token:
            ws_url = f"{ws_url}?token={self.token}"

        async with websockets.connect(ws_url, ping_interval=20, ping_timeout=self.timeout) as websocket:
            async for raw_message in websocket:
                yield json.loads(raw_message)

    async def import_objects(self, flow: str, objects: AsyncIterator[Dict[str, Any]], **kwargs: Any) -> None:
        """Bulk import objects via WebSocket"""
        ws_url = f"{self.url}/api/v1/flow/{flow}/import/objects"
        if self.token:
            ws_url = f"{ws_url}?token={self.token}"

        async with websockets.connect(ws_url, ping_interval=20, ping_timeout=self.timeout) as websocket:
            async for obj in objects:
                await websocket.send(json.dumps(obj))

    async def aclose(self) -> None:
        """Close connections"""
        # Cleanup handled by context managers
        pass
