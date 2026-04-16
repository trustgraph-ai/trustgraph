"""
TrustGraph Synchronous WebSocket Client

This module provides synchronous WebSocket-based access to TrustGraph services with
streaming support for real-time responses from agents, RAG queries, and text completions.

Uses a persistent WebSocket connection with a background reader task that
multiplexes requests by ID.
"""

import json
import asyncio
import websockets
from typing import Optional, Dict, Any, Iterator, Union, List
from threading import Lock

from . types import AgentThought, AgentObservation, AgentAnswer, RAGChunk, StreamingChunk, ProvenanceEvent, TextCompletionResult
from . exceptions import ProtocolException, raise_from_error_dict


def build_term(value: Any, term_type: Optional[str] = None,
               datatype: Optional[str] = None, language: Optional[str] = None) -> Optional[Dict[str, Any]]:
    """
    Build wire-format Term dict from a value.

    Auto-detection rules (when term_type is None):
      - Already a dict with 't' key -> return as-is (already a Term)
      - Starts with http://, https://, urn: -> IRI
      - Wrapped in <> (e.g., <http://...>) -> IRI (angle brackets stripped)
      - Anything else -> literal

    Args:
        value: The term value (string, dict, or None)
        term_type: One of 'iri', 'literal', or None for auto-detect
        datatype: Datatype for literal objects (e.g., xsd:integer)
        language: Language tag for literal objects (e.g., en)

    Returns:
        dict: Wire-format Term dict, or None if value is None
    """
    if value is None:
        return None

    # If already a Term dict, return as-is
    if isinstance(value, dict) and "t" in value:
        return value

    # Convert to string for processing
    value = str(value)

    # Auto-detect type if not specified
    if term_type is None:
        if value.startswith("<") and value.endswith(">") and not value.startswith("<<"):
            # Angle-bracket wrapped IRI: <http://...>
            value = value[1:-1]  # Strip < and >
            term_type = "iri"
        elif value.startswith(("http://", "https://", "urn:")):
            term_type = "iri"
        else:
            term_type = "literal"

    if term_type == "iri":
        # Strip angle brackets if present
        if value.startswith("<") and value.endswith(">"):
            value = value[1:-1]
        return {"t": "i", "i": value}
    elif term_type == "literal":
        result = {"t": "l", "v": value}
        if datatype:
            result["dt"] = datatype
        if language:
            result["ln"] = language
        return result
    else:
        raise ValueError(f"Unknown term type: {term_type}")


class SocketClient:
    """
    Synchronous WebSocket client with persistent connection.

    Maintains a single websocket connection and multiplexes requests
    by ID via a background reader task. Provides synchronous generators
    for streaming responses.
    """

    def __init__(self, url: str, timeout: int, token: Optional[str]) -> None:
        self.url: str = self._convert_to_ws_url(url)
        self.timeout: int = timeout
        self.token: Optional[str] = token
        self._request_counter: int = 0
        self._lock: Lock = Lock()
        self._loop: Optional[asyncio.AbstractEventLoop] = None
        self._socket = None
        self._connect_cm = None
        self._reader_task = None
        self._pending: Dict[str, asyncio.Queue] = {}
        self._connected: bool = False

    def _convert_to_ws_url(self, url: str) -> str:
        if url.startswith("http://"):
            return url.replace("http://", "ws://", 1)
        elif url.startswith("https://"):
            return url.replace("https://", "wss://", 1)
        elif url.startswith("ws://") or url.startswith("wss://"):
            return url
        else:
            return f"ws://{url}"

    def _build_ws_url(self):
        ws_url = f"{self.url.rstrip('/')}/api/v1/socket"
        if self.token:
            ws_url = f"{ws_url}?token={self.token}"
        return ws_url

    def _get_loop(self):
        """Get or create the event loop, reusing across calls."""
        if self._loop is None or self._loop.is_closed():
            try:
                loop = asyncio.get_event_loop()
                if loop.is_running():
                    loop = asyncio.new_event_loop()
                    asyncio.set_event_loop(loop)
            except RuntimeError:
                loop = asyncio.new_event_loop()
                asyncio.set_event_loop(loop)
            self._loop = loop
        return self._loop

    async def _ensure_connected(self):
        """Lazily establish the persistent websocket connection."""
        if self._connected:
            return

        ws_url = self._build_ws_url()
        self._connect_cm = websockets.connect(
            ws_url, ping_interval=20, ping_timeout=self.timeout
        )
        self._socket = await self._connect_cm.__aenter__()
        self._connected = True
        self._reader_task = asyncio.create_task(self._reader())

    async def _reader(self):
        """Background task to read responses and route by request ID."""
        try:
            async for raw_message in self._socket:
                response = json.loads(raw_message)
                request_id = response.get("id")

                if request_id and request_id in self._pending:
                    await self._pending[request_id].put(response)

        except websockets.exceptions.ConnectionClosed:
            pass
        except Exception as e:
            for queue in self._pending.values():
                try:
                    await queue.put({"error": str(e)})
                except:
                    pass
        finally:
            self._connected = False

    def _next_request_id(self):
        with self._lock:
            self._request_counter += 1
            return f"req-{self._request_counter}"

    def flow(self, flow_id: str) -> "SocketFlowInstance":
        return SocketFlowInstance(self, flow_id)

    def _send_request_sync(
        self,
        service: str,
        flow: Optional[str],
        request: Dict[str, Any],
        streaming: bool = False,
        streaming_raw: bool = False,
        include_provenance: bool = False
    ) -> Union[Dict[str, Any], Iterator[StreamingChunk], Iterator[Dict[str, Any]]]:
        """Synchronous wrapper around async WebSocket communication."""
        loop = self._get_loop()

        if streaming_raw:
            return self._streaming_generator_raw(service, flow, request, loop)
        elif streaming:
            return self._streaming_generator(service, flow, request, loop, include_provenance)
        else:
            return loop.run_until_complete(self._send_request_async(service, flow, request))

    def _streaming_generator(
        self,
        service: str,
        flow: Optional[str],
        request: Dict[str, Any],
        loop: asyncio.AbstractEventLoop,
        include_provenance: bool = False
    ) -> Iterator[StreamingChunk]:
        """Generator that yields streaming chunks."""
        async_gen = self._send_request_async_streaming(service, flow, request, include_provenance)

        try:
            while True:
                try:
                    chunk = loop.run_until_complete(async_gen.__anext__())
                    yield chunk
                except StopAsyncIteration:
                    break
        finally:
            try:
                loop.run_until_complete(async_gen.aclose())
            except:
                pass

    def _streaming_generator_raw(
        self,
        service: str,
        flow: Optional[str],
        request: Dict[str, Any],
        loop: asyncio.AbstractEventLoop
    ) -> Iterator[Dict[str, Any]]:
        """Generator that yields raw response dicts."""
        async_gen = self._send_request_async_streaming_raw(service, flow, request)

        try:
            while True:
                try:
                    data = loop.run_until_complete(async_gen.__anext__())
                    yield data
                except StopAsyncIteration:
                    break
        finally:
            try:
                loop.run_until_complete(async_gen.aclose())
            except:
                pass

    async def _send_request_async_streaming_raw(
        self,
        service: str,
        flow: Optional[str],
        request: Dict[str, Any]
    ) -> Iterator[Dict[str, Any]]:
        """Async streaming that yields raw response dicts."""
        await self._ensure_connected()

        request_id = self._next_request_id()
        queue = asyncio.Queue()
        self._pending[request_id] = queue

        try:
            message = {
                "id": request_id,
                "service": service,
                "request": request
            }
            if flow:
                message["flow"] = flow

            await self._socket.send(json.dumps(message))

            while True:
                response = await queue.get()

                if "error" in response:
                    raise_from_error_dict(response["error"])

                if "response" in response:
                    yield response["response"]

                    if response.get("complete"):
                        break

        finally:
            self._pending.pop(request_id, None)

    async def _send_request_async(
        self,
        service: str,
        flow: Optional[str],
        request: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Async non-streaming request over persistent connection."""
        await self._ensure_connected()

        request_id = self._next_request_id()
        queue = asyncio.Queue()
        self._pending[request_id] = queue

        try:
            message = {
                "id": request_id,
                "service": service,
                "request": request
            }
            if flow:
                message["flow"] = flow

            await self._socket.send(json.dumps(message))

            response = await queue.get()

            if "error" in response:
                raise_from_error_dict(response["error"])

            if "response" not in response:
                raise ProtocolException("Missing response in message")

            return response["response"]

        finally:
            self._pending.pop(request_id, None)

    async def _send_request_async_streaming(
        self,
        service: str,
        flow: Optional[str],
        request: Dict[str, Any],
        include_provenance: bool = False
    ) -> Iterator[StreamingChunk]:
        """Async streaming request over persistent connection."""
        await self._ensure_connected()

        request_id = self._next_request_id()
        queue = asyncio.Queue()
        self._pending[request_id] = queue

        try:
            message = {
                "id": request_id,
                "service": service,
                "request": request
            }
            if flow:
                message["flow"] = flow

            await self._socket.send(json.dumps(message))

            while True:
                response = await queue.get()

                if "error" in response:
                    raise_from_error_dict(response["error"])

                if "response" in response:
                    resp = response["response"]

                    if "error" in resp:
                        raise_from_error_dict(resp["error"])

                    chunk = self._parse_chunk(resp, include_provenance=include_provenance)
                    if chunk is not None:
                        yield chunk

                    if resp.get("end_of_session") or resp.get("end_of_dialog") or response.get("complete"):
                        break

        finally:
            self._pending.pop(request_id, None)

    def _parse_chunk(self, resp: Dict[str, Any], include_provenance: bool = False) -> Optional[StreamingChunk]:
        """Parse response chunk into appropriate type. Returns None for non-content messages."""
        message_type = resp.get("message_type")

        if message_type == "explain":
            if include_provenance:
                return self._build_provenance_event(resp)
            return None

        if message_type == "thought":
            return AgentThought(
                content=resp.get("content", ""),
                end_of_message=resp.get("end_of_message", False),
                message_id=resp.get("message_id", ""),
            )
        elif message_type == "observation":
            return AgentObservation(
                content=resp.get("content", ""),
                end_of_message=resp.get("end_of_message", False),
                message_id=resp.get("message_id", ""),
            )
        elif message_type == "answer" or message_type == "final-answer":
            return AgentAnswer(
                content=resp.get("content", ""),
                end_of_message=resp.get("end_of_message", False),
                end_of_dialog=resp.get("end_of_dialog", False),
                message_id=resp.get("message_id", ""),
                in_token=resp.get("in_token"),
                out_token=resp.get("out_token"),
                model=resp.get("model"),
            )
        elif message_type == "action":
            return AgentThought(
                content=resp.get("content", ""),
                end_of_message=resp.get("end_of_message", False)
            )
        else:
            content = resp.get("response", resp.get("chunk", resp.get("text", "")))
            return RAGChunk(
                content=content,
                end_of_stream=resp.get("end_of_stream", False),
                error=None,
                in_token=resp.get("in_token"),
                out_token=resp.get("out_token"),
                model=resp.get("model"),
            )

    def _build_provenance_event(self, resp: Dict[str, Any]) -> ProvenanceEvent:
        """Build a ProvenanceEvent from a response dict, parsing inline triples
        into an ExplainEntity if available."""
        explain_id = resp.get("explain_id", "")
        explain_graph = resp.get("explain_graph", "")
        raw_triples = resp.get("explain_triples", [])

        entity = None
        if raw_triples:
            try:
                from .explainability import ExplainEntity
                # Convert wire-format triple dicts to (s, p, o) tuples
                parsed = []
                for t in raw_triples:
                    s = t.get("s", {}).get("i", "") if t.get("s") else ""
                    p = t.get("p", {}).get("i", "") if t.get("p") else ""
                    o_term = t.get("o", {})
                    if o_term:
                        if o_term.get("t") == "i":
                            o = o_term.get("i", "")
                        else:
                            o = o_term.get("v", "")
                    else:
                        o = ""
                    parsed.append((s, p, o))
                entity = ExplainEntity.from_triples(explain_id, parsed)
            except Exception:
                pass

        return ProvenanceEvent(
            explain_id=explain_id,
            explain_graph=explain_graph,
            entity=entity,
            triples=raw_triples,
        )

    def close(self) -> None:
        """Close the persistent WebSocket connection."""
        if self._loop and not self._loop.is_closed():
            try:
                self._loop.run_until_complete(self._close_async())
            except:
                pass

    async def _close_async(self):
        # Cancel reader task
        if self._reader_task:
            self._reader_task.cancel()
            try:
                await self._reader_task
            except asyncio.CancelledError:
                pass
            self._reader_task = None

        # Exit the websockets context manager — this cleanly shuts down
        # the connection and its keepalive task
        if self._connect_cm:
            try:
                await self._connect_cm.__aexit__(None, None, None)
            except Exception:
                pass
            self._connect_cm = None

        self._socket = None
        self._connected = False
        self._pending.clear()


class SocketFlowInstance:
    """
    Synchronous WebSocket flow instance for streaming operations.

    Provides the same interface as REST FlowInstance but with WebSocket-based
    streaming support for real-time responses.
    """

    def __init__(self, client: SocketClient, flow_id: str) -> None:
        self.client: SocketClient = client
        self.flow_id: str = flow_id

    def agent(
        self,
        question: str,
        user: str,
        state: Optional[Dict[str, Any]] = None,
        group: Optional[str] = None,
        history: Optional[List[Dict[str, Any]]] = None,
        streaming: bool = False,
        **kwargs: Any
    ) -> Union[Dict[str, Any], Iterator[StreamingChunk]]:
        """Execute an agent operation with streaming support."""
        request = {
            "question": question,
            "user": user,
            "streaming": streaming
        }
        if state is not None:
            request["state"] = state
        if group is not None:
            request["group"] = group
        if history is not None:
            request["history"] = history
        request.update(kwargs)

        return self.client._send_request_sync("agent", self.flow_id, request, streaming=True)

    def agent_explain(
        self,
        question: str,
        user: str,
        collection: str,
        state: Optional[Dict[str, Any]] = None,
        group: Optional[str] = None,
        history: Optional[List[Dict[str, Any]]] = None,
        **kwargs: Any
    ) -> Iterator[Union[StreamingChunk, ProvenanceEvent]]:
        """Execute an agent operation with explainability support."""
        request = {
            "question": question,
            "user": user,
            "collection": collection,
            "streaming": True
        }
        if state is not None:
            request["state"] = state
        if group is not None:
            request["group"] = group
        if history is not None:
            request["history"] = history
        request.update(kwargs)

        return self.client._send_request_sync(
            "agent", self.flow_id, request,
            streaming=True, include_provenance=True
        )

    def text_completion(self, system: str, prompt: str, streaming: bool = False, **kwargs) -> Union[TextCompletionResult, Iterator[RAGChunk]]:
        """Execute text completion with optional streaming.

        Non-streaming: returns a TextCompletionResult with text and token counts.
        Streaming: returns an iterator of RAGChunk (with token counts on the final chunk).
        """
        request = {
            "system": system,
            "prompt": prompt,
            "streaming": streaming
        }
        request.update(kwargs)

        result = self.client._send_request_sync("text-completion", self.flow_id, request, streaming)

        if streaming:
            return self._text_completion_generator(result)
        else:
            return TextCompletionResult(
                text=result.get("response", ""),
                in_token=result.get("in_token"),
                out_token=result.get("out_token"),
                model=result.get("model"),
            )

    def _text_completion_generator(self, result: Iterator[StreamingChunk]) -> Iterator[RAGChunk]:
        for chunk in result:
            if isinstance(chunk, RAGChunk):
                yield chunk

    def graph_rag(
        self,
        query: str,
        user: str,
        collection: str,
        entity_limit: int = 50,
        triple_limit: int = 30,
        max_subgraph_size: int = 1000,
        max_path_length: int = 2,
        edge_score_limit: int = 30,
        edge_limit: int = 25,
        streaming: bool = False,
        **kwargs: Any
    ) -> Union[TextCompletionResult, Iterator[RAGChunk]]:
        """Execute graph-based RAG query with optional streaming.

        Non-streaming: returns a TextCompletionResult with text and token counts.
        Streaming: returns an iterator of RAGChunk (with token counts on the final chunk).
        """
        request = {
            "query": query,
            "user": user,
            "collection": collection,
            "entity-limit": entity_limit,
            "triple-limit": triple_limit,
            "max-subgraph-size": max_subgraph_size,
            "max-path-length": max_path_length,
            "edge-score-limit": edge_score_limit,
            "edge-limit": edge_limit,
            "streaming": streaming
        }
        request.update(kwargs)

        result = self.client._send_request_sync("graph-rag", self.flow_id, request, streaming)

        if streaming:
            return self._rag_generator(result)
        else:
            return TextCompletionResult(
                text=result.get("response", ""),
                in_token=result.get("in_token"),
                out_token=result.get("out_token"),
                model=result.get("model"),
            )

    def graph_rag_explain(
        self,
        query: str,
        user: str,
        collection: str,
        entity_limit: int = 50,
        triple_limit: int = 30,
        max_subgraph_size: int = 1000,
        max_path_length: int = 2,
        edge_score_limit: int = 30,
        edge_limit: int = 25,
        **kwargs: Any
    ) -> Iterator[Union[RAGChunk, ProvenanceEvent]]:
        """Execute graph-based RAG query with explainability support."""
        request = {
            "query": query,
            "user": user,
            "collection": collection,
            "entity-limit": entity_limit,
            "triple-limit": triple_limit,
            "max-subgraph-size": max_subgraph_size,
            "max-path-length": max_path_length,
            "edge-score-limit": edge_score_limit,
            "edge-limit": edge_limit,
            "streaming": True,
            "explainable": True,
        }
        request.update(kwargs)

        return self.client._send_request_sync(
            "graph-rag", self.flow_id, request,
            streaming=True, include_provenance=True
        )

    def document_rag(
        self,
        query: str,
        user: str,
        collection: str,
        doc_limit: int = 10,
        streaming: bool = False,
        **kwargs: Any
    ) -> Union[TextCompletionResult, Iterator[RAGChunk]]:
        """Execute document-based RAG query with optional streaming.

        Non-streaming: returns a TextCompletionResult with text and token counts.
        Streaming: returns an iterator of RAGChunk (with token counts on the final chunk).
        """
        request = {
            "query": query,
            "user": user,
            "collection": collection,
            "doc-limit": doc_limit,
            "streaming": streaming
        }
        request.update(kwargs)

        result = self.client._send_request_sync("document-rag", self.flow_id, request, streaming)

        if streaming:
            return self._rag_generator(result)
        else:
            return TextCompletionResult(
                text=result.get("response", ""),
                in_token=result.get("in_token"),
                out_token=result.get("out_token"),
                model=result.get("model"),
            )

    def document_rag_explain(
        self,
        query: str,
        user: str,
        collection: str,
        doc_limit: int = 10,
        **kwargs: Any
    ) -> Iterator[Union[RAGChunk, ProvenanceEvent]]:
        """Execute document-based RAG query with explainability support."""
        request = {
            "query": query,
            "user": user,
            "collection": collection,
            "doc-limit": doc_limit,
            "streaming": True,
            "explainable": True,
        }
        request.update(kwargs)

        return self.client._send_request_sync(
            "document-rag", self.flow_id, request,
            streaming=True, include_provenance=True
        )

    def _rag_generator(self, result: Iterator[StreamingChunk]) -> Iterator[RAGChunk]:
        for chunk in result:
            if isinstance(chunk, RAGChunk):
                yield chunk

    def prompt(
        self,
        id: str,
        variables: Dict[str, str],
        streaming: bool = False,
        **kwargs: Any
    ) -> Union[TextCompletionResult, Iterator[RAGChunk]]:
        """Execute a prompt template with optional streaming.

        Non-streaming: returns a TextCompletionResult with text and token counts.
        Streaming: returns an iterator of RAGChunk (with token counts on the final chunk).
        """
        request = {
            "id": id,
            "variables": variables,
            "streaming": streaming
        }
        request.update(kwargs)

        result = self.client._send_request_sync("prompt", self.flow_id, request, streaming)

        if streaming:
            return self._rag_generator(result)
        else:
            return TextCompletionResult(
                text=result.get("text", result.get("response", "")),
                in_token=result.get("in_token"),
                out_token=result.get("out_token"),
                model=result.get("model"),
            )

    def graph_embeddings_query(
        self,
        text: str,
        user: str,
        collection: str,
        limit: int = 10,
        **kwargs: Any
    ) -> Dict[str, Any]:
        """Query knowledge graph entities using semantic similarity."""
        emb_result = self.embeddings(texts=[text])
        vector = emb_result.get("vectors", [[]])[0]

        request = {
            "vector": vector,
            "user": user,
            "collection": collection,
            "limit": limit
        }
        request.update(kwargs)

        return self.client._send_request_sync("graph-embeddings", self.flow_id, request, False)

    def document_embeddings_query(
        self,
        text: str,
        user: str,
        collection: str,
        limit: int = 10,
        **kwargs: Any
    ) -> Dict[str, Any]:
        """Query document chunks using semantic similarity."""
        emb_result = self.embeddings(texts=[text])
        vector = emb_result.get("vectors", [[]])[0]

        request = {
            "vector": vector,
            "user": user,
            "collection": collection,
            "limit": limit
        }
        request.update(kwargs)

        return self.client._send_request_sync("document-embeddings", self.flow_id, request, False)

    def embeddings(self, texts: list, **kwargs: Any) -> Dict[str, Any]:
        """Generate vector embeddings for one or more texts."""
        request = {"texts": texts}
        request.update(kwargs)

        return self.client._send_request_sync("embeddings", self.flow_id, request, False)

    def triples_query(
        self,
        s: Optional[Union[str, Dict[str, Any]]] = None,
        p: Optional[Union[str, Dict[str, Any]]] = None,
        o: Optional[Union[str, Dict[str, Any]]] = None,
        g: Optional[str] = None,
        user: Optional[str] = None,
        collection: Optional[str] = None,
        limit: int = 100,
        **kwargs: Any
    ) -> List[Dict[str, Any]]:
        """Query knowledge graph triples using pattern matching."""
        request = {"limit": limit}

        s_term = build_term(s)
        p_term = build_term(p)
        o_term = build_term(o)

        if s_term is not None:
            request["s"] = s_term
        if p_term is not None:
            request["p"] = p_term
        if o_term is not None:
            request["o"] = o_term
        if g is not None:
            request["g"] = g
        if user is not None:
            request["user"] = user
        if collection is not None:
            request["collection"] = collection
        request.update(kwargs)

        result = self.client._send_request_sync("triples", self.flow_id, request, False)
        if isinstance(result, dict) and "response" in result:
            return result["response"]
        return result

    def triples_query_stream(
        self,
        s: Optional[Union[str, Dict[str, Any]]] = None,
        p: Optional[Union[str, Dict[str, Any]]] = None,
        o: Optional[Union[str, Dict[str, Any]]] = None,
        g: Optional[str] = None,
        user: Optional[str] = None,
        collection: Optional[str] = None,
        limit: int = 100,
        batch_size: int = 20,
        **kwargs: Any
    ) -> Iterator[List[Dict[str, Any]]]:
        """Query knowledge graph triples with streaming batches."""
        request = {
            "limit": limit,
            "streaming": True,
            "batch-size": batch_size,
        }

        s_term = build_term(s)
        p_term = build_term(p)
        o_term = build_term(o)

        if s_term is not None:
            request["s"] = s_term
        if p_term is not None:
            request["p"] = p_term
        if o_term is not None:
            request["o"] = o_term
        if g is not None:
            request["g"] = g
        if user is not None:
            request["user"] = user
        if collection is not None:
            request["collection"] = collection
        request.update(kwargs)

        for response in self.client._send_request_sync("triples", self.flow_id, request, streaming_raw=True):
            if isinstance(response, dict) and "response" in response:
                yield response["response"]
            else:
                yield response

    def sparql_query_stream(
        self,
        query: str,
        user: str = "trustgraph",
        collection: str = "default",
        limit: int = 10000,
        batch_size: int = 20,
        **kwargs: Any
    ) -> Iterator[Dict[str, Any]]:
        """Execute a SPARQL query with streaming batches."""
        request = {
            "query": query,
            "user": user,
            "collection": collection,
            "limit": limit,
            "streaming": True,
            "batch-size": batch_size,
        }
        request.update(kwargs)

        for response in self.client._send_request_sync(
            "sparql", self.flow_id, request, streaming_raw=True
        ):
            yield response

    def rows_query(
        self,
        query: str,
        user: str,
        collection: str,
        variables: Optional[Dict[str, Any]] = None,
        operation_name: Optional[str] = None,
        **kwargs: Any
    ) -> Dict[str, Any]:
        """Execute a GraphQL query against structured rows."""
        request = {
            "query": query,
            "user": user,
            "collection": collection
        }
        if variables:
            request["variables"] = variables
        if operation_name:
            request["operationName"] = operation_name
        request.update(kwargs)

        return self.client._send_request_sync("rows", self.flow_id, request, False)

    def mcp_tool(
        self,
        name: str,
        parameters: Dict[str, Any],
        **kwargs: Any
    ) -> Dict[str, Any]:
        """Execute a Model Context Protocol (MCP) tool."""
        request = {
            "name": name,
            "parameters": parameters
        }
        request.update(kwargs)

        return self.client._send_request_sync("mcp-tool", self.flow_id, request, False)

    def row_embeddings_query(
        self,
        text: str,
        schema_name: str,
        user: str = "trustgraph",
        collection: str = "default",
        index_name: Optional[str] = None,
        limit: int = 10,
        **kwargs: Any
    ) -> Dict[str, Any]:
        """Query row data using semantic similarity on indexed fields."""
        emb_result = self.embeddings(texts=[text])
        vector = emb_result.get("vectors", [[]])[0]

        request = {
            "vector": vector,
            "schema_name": schema_name,
            "user": user,
            "collection": collection,
            "limit": limit
        }
        if index_name:
            request["index_name"] = index_name
        request.update(kwargs)

        return self.client._send_request_sync("row-embeddings", self.flow_id, request, False)
