
import json
import asyncio
import websockets
from typing import Optional, Iterator, Dict, Any

from . types import Triple
from . exceptions import ProtocolException


class BulkClient:
    """Synchronous bulk operations client"""

    def __init__(self, url: str, timeout: int, token: Optional[str]):
        self.url = self._convert_to_ws_url(url)
        self.timeout = timeout
        self.token = token

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

    def _run_async(self, coro):
        """Run async coroutine synchronously"""
        try:
            loop = asyncio.get_event_loop()
            if loop.is_running():
                loop = asyncio.new_event_loop()
                asyncio.set_event_loop(loop)
        except RuntimeError:
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)

        return loop.run_until_complete(coro)

    def import_triples(self, flow: str, triples: Iterator[Triple], **kwargs) -> None:
        """Bulk import triples via WebSocket"""
        self._run_async(self._import_triples_async(flow, triples))

    async def _import_triples_async(self, flow: str, triples: Iterator[Triple]):
        """Async implementation of triple import"""
        ws_url = f"{self.url}/api/v1/flow/{flow}/import/triples"
        if self.token:
            ws_url = f"{ws_url}?token={self.token}"

        async with websockets.connect(ws_url, ping_interval=20, ping_timeout=self.timeout) as websocket:
            for triple in triples:
                message = {
                    "s": triple.s,
                    "p": triple.p,
                    "o": triple.o
                }
                await websocket.send(json.dumps(message))

    def export_triples(self, flow: str, **kwargs) -> Iterator[Triple]:
        """Bulk export triples via WebSocket"""
        async_gen = self._export_triples_async(flow)

        try:
            loop = asyncio.get_event_loop()
            if loop.is_running():
                loop = asyncio.new_event_loop()
                asyncio.set_event_loop(loop)
        except Runtime

Error:
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)

        try:
            while True:
                try:
                    triple = loop.run_until_complete(async_gen.__anext__())
                    yield triple
                except StopAsyncIteration:
                    break
        finally:
            try:
                loop.run_until_complete(async_gen.aclose())
            except:
                pass

    async def _export_triples_async(self, flow: str):
        """Async implementation of triple export"""
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

    def import_graph_embeddings(self, flow: str, embeddings: Iterator[Dict[str, Any]], **kwargs) -> None:
        """Bulk import graph embeddings via WebSocket"""
        self._run_async(self._import_graph_embeddings_async(flow, embeddings))

    async def _import_graph_embeddings_async(self, flow: str, embeddings: Iterator[Dict[str, Any]]):
        """Async implementation of graph embeddings import"""
        ws_url = f"{self.url}/api/v1/flow/{flow}/import/graph-embeddings"
        if self.token:
            ws_url = f"{ws_url}?token={self.token}"

        async with websockets.connect(ws_url, ping_interval=20, ping_timeout=self.timeout) as websocket:
            for embedding in embeddings:
                await websocket.send(json.dumps(embedding))

    def export_graph_embeddings(self, flow: str, **kwargs) -> Iterator[Dict[str, Any]]:
        """Bulk export graph embeddings via WebSocket"""
        async_gen = self._export_graph_embeddings_async(flow)

        try:
            loop = asyncio.get_event_loop()
            if loop.is_running():
                loop = asyncio.new_event_loop()
                asyncio.set_event_loop(loop)
        except RuntimeError:
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)

        try:
            while True:
                try:
                    embedding = loop.run_until_complete(async_gen.__anext__())
                    yield embedding
                except StopAsyncIteration:
                    break
        finally:
            try:
                loop.run_until_complete(async_gen.aclose())
            except:
                pass

    async def _export_graph_embeddings_async(self, flow: str):
        """Async implementation of graph embeddings export"""
        ws_url = f"{self.url}/api/v1/flow/{flow}/export/graph-embeddings"
        if self.token:
            ws_url = f"{ws_url}?token={self.token}"

        async with websockets.connect(ws_url, ping_interval=20, ping_timeout=self.timeout) as websocket:
            async for raw_message in websocket:
                yield json.loads(raw_message)

    def import_document_embeddings(self, flow: str, embeddings: Iterator[Dict[str, Any]], **kwargs) -> None:
        """Bulk import document embeddings via WebSocket"""
        self._run_async(self._import_document_embeddings_async(flow, embeddings))

    async def _import_document_embeddings_async(self, flow: str, embeddings: Iterator[Dict[str, Any]]):
        """Async implementation of document embeddings import"""
        ws_url = f"{self.url}/api/v1/flow/{flow}/import/document-embeddings"
        if self.token:
            ws_url = f"{ws_url}?token={self.token}"

        async with websockets.connect(ws_url, ping_interval=20, ping_timeout=self.timeout) as websocket:
            for embedding in embeddings:
                await websocket.send(json.dumps(embedding))

    def export_document_embeddings(self, flow: str, **kwargs) -> Iterator[Dict[str, Any]]:
        """Bulk export document embeddings via WebSocket"""
        async_gen = self._export_document_embeddings_async(flow)

        try:
            loop = asyncio.get_event_loop()
            if loop.is_running():
                loop = asyncio.new_event_loop()
                asyncio.set_event_loop(loop)
        except RuntimeError:
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)

        try:
            while True:
                try:
                    embedding = loop.run_until_complete(async_gen.__anext__())
                    yield embedding
                except StopAsyncIteration:
                    break
        finally:
            try:
                loop.run_until_complete(async_gen.aclose())
            except:
                pass

    async def _export_document_embeddings_async(self, flow: str):
        """Async implementation of document embeddings export"""
        ws_url = f"{self.url}/api/v1/flow/{flow}/export/document-embeddings"
        if self.token:
            ws_url = f"{ws_url}?token={self.token}"

        async with websockets.connect(ws_url, ping_interval=20, ping_timeout=self.timeout) as websocket:
            async for raw_message in websocket:
                yield json.loads(raw_message)

    def import_entity_contexts(self, flow: str, contexts: Iterator[Dict[str, Any]], **kwargs) -> None:
        """Bulk import entity contexts via WebSocket"""
        self._run_async(self._import_entity_contexts_async(flow, contexts))

    async def _import_entity_contexts_async(self, flow: str, contexts: Iterator[Dict[str, Any]]):
        """Async implementation of entity contexts import"""
        ws_url = f"{self.url}/api/v1/flow/{flow}/import/entity-contexts"
        if self.token:
            ws_url = f"{ws_url}?token={self.token}"

        async with websockets.connect(ws_url, ping_interval=20, ping_timeout=self.timeout) as websocket:
            for context in contexts:
                await websocket.send(json.dumps(context))

    def export_entity_contexts(self, flow: str, **kwargs) -> Iterator[Dict[str, Any]]:
        """Bulk export entity contexts via WebSocket"""
        async_gen = self._export_entity_contexts_async(flow)

        try:
            loop = asyncio.get_event_loop()
            if loop.is_running():
                loop = asyncio.new_event_loop()
                asyncio.set_event_loop(loop)
        except RuntimeError:
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)

        try:
            while True:
                try:
                    context = loop.run_until_complete(async_gen.__anext__())
                    yield context
                except StopAsyncIteration:
                    break
        finally:
            try:
                loop.run_until_complete(async_gen.aclose())
            except:
                pass

    async def _export_entity_contexts_async(self, flow: str):
        """Async implementation of entity contexts export"""
        ws_url = f"{self.url}/api/v1/flow/{flow}/export/entity-contexts"
        if self.token:
            ws_url = f"{ws_url}?token={self.token}"

        async with websockets.connect(ws_url, ping_interval=20, ping_timeout=self.timeout) as websocket:
            async for raw_message in websocket:
                yield json.loads(raw_message)

    def import_objects(self, flow: str, objects: Iterator[Dict[str, Any]], **kwargs) -> None:
        """Bulk import objects via WebSocket"""
        self._run_async(self._import_objects_async(flow, objects))

    async def _import_objects_async(self, flow: str, objects: Iterator[Dict[str, Any]]):
        """Async implementation of objects import"""
        ws_url = f"{self.url}/api/v1/flow/{flow}/import/objects"
        if self.token:
            ws_url = f"{ws_url}?token={self.token}"

        async with websockets.connect(ws_url, ping_interval=20, ping_timeout=self.timeout) as websocket:
            for obj in objects:
                await websocket.send(json.dumps(obj))

    def close(self):
        """Close connections"""
        # Cleanup handled by context managers
        pass
