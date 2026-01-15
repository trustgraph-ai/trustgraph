"""
TrustGraph Synchronous Bulk Operations Client

This module provides synchronous bulk import/export operations via WebSocket
for efficient transfer of large datasets including triples, embeddings,
entity contexts, and objects.
"""

import json
import asyncio
import websockets
from typing import Optional, Iterator, Dict, Any, Coroutine

from . types import Triple
from . exceptions import ProtocolException


class BulkClient:
    """
    Synchronous bulk operations client for import/export.

    Provides efficient bulk data transfer via WebSocket for large datasets.
    Wraps async WebSocket operations with synchronous generators for ease of use.

    Note: For true async support, use AsyncBulkClient instead.
    """

    def __init__(self, url: str, timeout: int, token: Optional[str]) -> None:
        """
        Initialize synchronous bulk client.

        Args:
            url: Base URL for TrustGraph API (HTTP/HTTPS will be converted to WS/WSS)
            timeout: WebSocket timeout in seconds
            token: Optional bearer token for authentication
        """
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

    def _run_async(self, coro: Coroutine[Any, Any, Any]) -> Any:
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

    def import_triples(self, flow: str, triples: Iterator[Triple], **kwargs: Any) -> None:
        """
        Bulk import RDF triples into a flow.

        Efficiently uploads large numbers of triples via WebSocket streaming.

        Args:
            flow: Flow identifier
            triples: Iterator yielding Triple objects
            **kwargs: Additional parameters (reserved for future use)

        Example:
            ```python
            from trustgraph.api import Triple

            bulk = api.bulk()

            # Generate triples to import
            def triple_generator():
                yield Triple(s="subj1", p="pred", o="obj1")
                yield Triple(s="subj2", p="pred", o="obj2")
                # ... more triples

            # Import triples
            bulk.import_triples(flow="default", triples=triple_generator())
            ```
        """
        self._run_async(self._import_triples_async(flow, triples))

    async def _import_triples_async(self, flow: str, triples: Iterator[Triple]) -> None:
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

    def export_triples(self, flow: str, **kwargs: Any) -> Iterator[Triple]:
        """
        Bulk export RDF triples from a flow.

        Efficiently downloads all triples via WebSocket streaming.

        Args:
            flow: Flow identifier
            **kwargs: Additional parameters (reserved for future use)

        Returns:
            Iterator[Triple]: Stream of Triple objects

        Example:
            ```python
            bulk = api.bulk()

            # Export and process triples
            for triple in bulk.export_triples(flow="default"):
                print(f"{triple.s} -> {triple.p} -> {triple.o}")
            ```
        """
        async_gen = self._export_triples_async(flow)

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
                    triple = loop.run_until_complete(async_gen.__anext__())
                    yield triple
                except StopAsyncIteration:
                    break
        finally:
            try:
                loop.run_until_complete(async_gen.aclose())
            except:
                pass

    async def _export_triples_async(self, flow: str) -> Iterator[Triple]:
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

    def import_graph_embeddings(self, flow: str, embeddings: Iterator[Dict[str, Any]], **kwargs: Any) -> None:
        """
        Bulk import graph embeddings into a flow.

        Efficiently uploads graph entity embeddings via WebSocket streaming.

        Args:
            flow: Flow identifier
            embeddings: Iterator yielding embedding dictionaries
            **kwargs: Additional parameters (reserved for future use)

        Example:
            ```python
            bulk = api.bulk()

            # Generate embeddings to import
            def embedding_generator():
                yield {"entity": "entity1", "embedding": [0.1, 0.2, ...]}
                yield {"entity": "entity2", "embedding": [0.3, 0.4, ...]}
                # ... more embeddings

            bulk.import_graph_embeddings(
                flow="default",
                embeddings=embedding_generator()
            )
            ```
        """
        self._run_async(self._import_graph_embeddings_async(flow, embeddings))

    async def _import_graph_embeddings_async(self, flow: str, embeddings: Iterator[Dict[str, Any]]) -> None:
        """Async implementation of graph embeddings import"""
        ws_url = f"{self.url}/api/v1/flow/{flow}/import/graph-embeddings"
        if self.token:
            ws_url = f"{ws_url}?token={self.token}"

        async with websockets.connect(ws_url, ping_interval=20, ping_timeout=self.timeout) as websocket:
            for embedding in embeddings:
                await websocket.send(json.dumps(embedding))

    def export_graph_embeddings(self, flow: str, **kwargs: Any) -> Iterator[Dict[str, Any]]:
        """
        Bulk export graph embeddings from a flow.

        Efficiently downloads all graph entity embeddings via WebSocket streaming.

        Args:
            flow: Flow identifier
            **kwargs: Additional parameters (reserved for future use)

        Returns:
            Iterator[Dict[str, Any]]: Stream of embedding dictionaries

        Example:
            ```python
            bulk = api.bulk()

            # Export and process embeddings
            for embedding in bulk.export_graph_embeddings(flow="default"):
                entity = embedding.get("entity")
                vector = embedding.get("embedding")
                print(f"{entity}: {len(vector)} dimensions")
            ```
        """
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

    async def _export_graph_embeddings_async(self, flow: str) -> Iterator[Dict[str, Any]]:
        """Async implementation of graph embeddings export"""
        ws_url = f"{self.url}/api/v1/flow/{flow}/export/graph-embeddings"
        if self.token:
            ws_url = f"{ws_url}?token={self.token}"

        async with websockets.connect(ws_url, ping_interval=20, ping_timeout=self.timeout) as websocket:
            async for raw_message in websocket:
                yield json.loads(raw_message)

    def import_document_embeddings(self, flow: str, embeddings: Iterator[Dict[str, Any]], **kwargs: Any) -> None:
        """
        Bulk import document embeddings into a flow.

        Efficiently uploads document chunk embeddings via WebSocket streaming
        for use in document RAG queries.

        Args:
            flow: Flow identifier
            embeddings: Iterator yielding embedding dictionaries
            **kwargs: Additional parameters (reserved for future use)

        Example:
            ```python
            bulk = api.bulk()

            # Generate document embeddings to import
            def doc_embedding_generator():
                yield {"id": "doc1-chunk1", "embedding": [0.1, 0.2, ...]}
                yield {"id": "doc1-chunk2", "embedding": [0.3, 0.4, ...]}
                # ... more embeddings

            bulk.import_document_embeddings(
                flow="default",
                embeddings=doc_embedding_generator()
            )
            ```
        """
        self._run_async(self._import_document_embeddings_async(flow, embeddings))

    async def _import_document_embeddings_async(self, flow: str, embeddings: Iterator[Dict[str, Any]]) -> None:
        """Async implementation of document embeddings import"""
        ws_url = f"{self.url}/api/v1/flow/{flow}/import/document-embeddings"
        if self.token:
            ws_url = f"{ws_url}?token={self.token}"

        async with websockets.connect(ws_url, ping_interval=20, ping_timeout=self.timeout) as websocket:
            for embedding in embeddings:
                await websocket.send(json.dumps(embedding))

    def export_document_embeddings(self, flow: str, **kwargs: Any) -> Iterator[Dict[str, Any]]:
        """
        Bulk export document embeddings from a flow.

        Efficiently downloads all document chunk embeddings via WebSocket streaming.

        Args:
            flow: Flow identifier
            **kwargs: Additional parameters (reserved for future use)

        Returns:
            Iterator[Dict[str, Any]]: Stream of embedding dictionaries

        Example:
            ```python
            bulk = api.bulk()

            # Export and process document embeddings
            for embedding in bulk.export_document_embeddings(flow="default"):
                doc_id = embedding.get("id")
                vector = embedding.get("embedding")
                print(f"{doc_id}: {len(vector)} dimensions")
            ```
        """
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

    async def _export_document_embeddings_async(self, flow: str) -> Iterator[Dict[str, Any]]:
        """Async implementation of document embeddings export"""
        ws_url = f"{self.url}/api/v1/flow/{flow}/export/document-embeddings"
        if self.token:
            ws_url = f"{ws_url}?token={self.token}"

        async with websockets.connect(ws_url, ping_interval=20, ping_timeout=self.timeout) as websocket:
            async for raw_message in websocket:
                yield json.loads(raw_message)

    def import_entity_contexts(self, flow: str, contexts: Iterator[Dict[str, Any]], **kwargs: Any) -> None:
        """
        Bulk import entity contexts into a flow.

        Efficiently uploads entity context information via WebSocket streaming.
        Entity contexts provide additional textual context about graph entities
        for improved RAG performance.

        Args:
            flow: Flow identifier
            contexts: Iterator yielding context dictionaries
            **kwargs: Additional parameters (reserved for future use)

        Example:
            ```python
            bulk = api.bulk()

            # Generate entity contexts to import
            def context_generator():
                yield {"entity": "entity1", "context": "Description of entity1..."}
                yield {"entity": "entity2", "context": "Description of entity2..."}
                # ... more contexts

            bulk.import_entity_contexts(
                flow="default",
                contexts=context_generator()
            )
            ```
        """
        self._run_async(self._import_entity_contexts_async(flow, contexts))

    async def _import_entity_contexts_async(self, flow: str, contexts: Iterator[Dict[str, Any]]) -> None:
        """Async implementation of entity contexts import"""
        ws_url = f"{self.url}/api/v1/flow/{flow}/import/entity-contexts"
        if self.token:
            ws_url = f"{ws_url}?token={self.token}"

        async with websockets.connect(ws_url, ping_interval=20, ping_timeout=self.timeout) as websocket:
            for context in contexts:
                await websocket.send(json.dumps(context))

    def export_entity_contexts(self, flow: str, **kwargs: Any) -> Iterator[Dict[str, Any]]:
        """
        Bulk export entity contexts from a flow.

        Efficiently downloads all entity context information via WebSocket streaming.

        Args:
            flow: Flow identifier
            **kwargs: Additional parameters (reserved for future use)

        Returns:
            Iterator[Dict[str, Any]]: Stream of context dictionaries

        Example:
            ```python
            bulk = api.bulk()

            # Export and process entity contexts
            for context in bulk.export_entity_contexts(flow="default"):
                entity = context.get("entity")
                text = context.get("context")
                print(f"{entity}: {text[:100]}...")
            ```
        """
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

    async def _export_entity_contexts_async(self, flow: str) -> Iterator[Dict[str, Any]]:
        """Async implementation of entity contexts export"""
        ws_url = f"{self.url}/api/v1/flow/{flow}/export/entity-contexts"
        if self.token:
            ws_url = f"{ws_url}?token={self.token}"

        async with websockets.connect(ws_url, ping_interval=20, ping_timeout=self.timeout) as websocket:
            async for raw_message in websocket:
                yield json.loads(raw_message)

    def import_objects(self, flow: str, objects: Iterator[Dict[str, Any]], **kwargs: Any) -> None:
        """
        Bulk import structured objects into a flow.

        Efficiently uploads structured data objects via WebSocket streaming
        for use in GraphQL queries.

        Args:
            flow: Flow identifier
            objects: Iterator yielding object dictionaries
            **kwargs: Additional parameters (reserved for future use)

        Example:
            ```python
            bulk = api.bulk()

            # Generate objects to import
            def object_generator():
                yield {"id": "obj1", "name": "Object 1", "value": 100}
                yield {"id": "obj2", "name": "Object 2", "value": 200}
                # ... more objects

            bulk.import_objects(
                flow="default",
                objects=object_generator()
            )
            ```
        """
        self._run_async(self._import_objects_async(flow, objects))

    async def _import_objects_async(self, flow: str, objects: Iterator[Dict[str, Any]]) -> None:
        """Async implementation of objects import"""
        ws_url = f"{self.url}/api/v1/flow/{flow}/import/objects"
        if self.token:
            ws_url = f"{ws_url}?token={self.token}"

        async with websockets.connect(ws_url, ping_interval=20, ping_timeout=self.timeout) as websocket:
            for obj in objects:
                await websocket.send(json.dumps(obj))

    def close(self) -> None:
        """Close connections"""
        # Cleanup handled by context managers
        pass
