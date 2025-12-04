
import json
import asyncio
import websockets
from typing import Optional, Dict, Any, Iterator, Union, List
from threading import Lock

from . types import AgentThought, AgentObservation, AgentAnswer, RAGChunk, StreamingChunk
from . exceptions import ProtocolException, raise_from_error_dict


class SocketClient:
    """Synchronous WebSocket client (wraps async websockets library)"""

    def __init__(self, url: str, timeout: int, token: Optional[str]) -> None:
        self.url: str = self._convert_to_ws_url(url)
        self.timeout: int = timeout
        self.token: Optional[str] = token
        self._connection: Optional[Any] = None
        self._request_counter: int = 0
        self._lock: Lock = Lock()
        self._loop: Optional[asyncio.AbstractEventLoop] = None

    def _convert_to_ws_url(self, url: str) -> str:
        """Convert HTTP URL to WebSocket URL"""
        if url.startswith("http://"):
            return url.replace("http://", "ws://", 1)
        elif url.startswith("https://"):
            return url.replace("https://", "wss://", 1)
        elif url.startswith("ws://") or url.startswith("wss://"):
            return url
        else:
            # Assume ws://
            return f"ws://{url}"

    def flow(self, flow_id: str) -> "SocketFlowInstance":
        """Get flow instance for WebSocket operations"""
        return SocketFlowInstance(self, flow_id)

    def _send_request_sync(
        self,
        service: str,
        flow: Optional[str],
        request: Dict[str, Any],
        streaming: bool = False
    ) -> Union[Dict[str, Any], Iterator[StreamingChunk]]:
        """Synchronous wrapper around async WebSocket communication"""
        # Create event loop if needed
        try:
            loop = asyncio.get_event_loop()
            if loop.is_running():
                # If loop is running (e.g., in Jupyter), create new loop
                loop = asyncio.new_event_loop()
                asyncio.set_event_loop(loop)
        except RuntimeError:
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)

        if streaming:
            # For streaming, we need to return an iterator
            # Create a generator that runs async code
            return self._streaming_generator(service, flow, request, loop)
        else:
            # For non-streaming, just run the async code and return result
            return loop.run_until_complete(self._send_request_async(service, flow, request))

    def _streaming_generator(
        self,
        service: str,
        flow: Optional[str],
        request: Dict[str, Any],
        loop: asyncio.AbstractEventLoop
    ) -> Iterator[StreamingChunk]:
        """Generator that yields streaming chunks"""
        async_gen = self._send_request_async_streaming(service, flow, request)

        try:
            while True:
                try:
                    chunk = loop.run_until_complete(async_gen.__anext__())
                    yield chunk
                except StopAsyncIteration:
                    break
        finally:
            # Clean up async generator
            try:
                loop.run_until_complete(async_gen.aclose())
            except:
                pass

    async def _send_request_async(
        self,
        service: str,
        flow: Optional[str],
        request: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Async implementation of WebSocket request (non-streaming)"""
        # Generate unique request ID
        with self._lock:
            self._request_counter += 1
            request_id = f"req-{self._request_counter}"

        # Build WebSocket URL with optional token
        ws_url = f"{self.url}/api/v1/socket"
        if self.token:
            ws_url = f"{ws_url}?token={self.token}"

        # Build request message
        message = {
            "id": request_id,
            "service": service,
            "request": request
        }
        if flow:
            message["flow"] = flow

        # Connect and send request
        async with websockets.connect(ws_url, ping_interval=20, ping_timeout=self.timeout) as websocket:
            await websocket.send(json.dumps(message))

            # Wait for single response
            raw_message = await websocket.recv()
            response = json.loads(raw_message)

            if response.get("id") != request_id:
                raise ProtocolException(f"Response ID mismatch")

            if "error" in response:
                raise_from_error_dict(response["error"])

            if "response" not in response:
                raise ProtocolException(f"Missing response in message")

            return response["response"]

    async def _send_request_async_streaming(
        self,
        service: str,
        flow: Optional[str],
        request: Dict[str, Any]
    ) -> Iterator[StreamingChunk]:
        """Async implementation of WebSocket request (streaming)"""
        # Generate unique request ID
        with self._lock:
            self._request_counter += 1
            request_id = f"req-{self._request_counter}"

        # Build WebSocket URL with optional token
        ws_url = f"{self.url}/api/v1/socket"
        if self.token:
            ws_url = f"{ws_url}?token={self.token}"

        # Build request message
        message = {
            "id": request_id,
            "service": service,
            "request": request
        }
        if flow:
            message["flow"] = flow

        # Connect and send request
        async with websockets.connect(ws_url, ping_interval=20, ping_timeout=self.timeout) as websocket:
            await websocket.send(json.dumps(message))

            # Yield chunks as they arrive
            async for raw_message in websocket:
                response = json.loads(raw_message)

                if response.get("id") != request_id:
                    continue  # Ignore messages for other requests

                if "error" in response:
                    raise_from_error_dict(response["error"])

                if "response" in response:
                    resp = response["response"]

                    # Check for errors in response chunks
                    if "error" in resp:
                        raise_from_error_dict(resp["error"])

                    # Parse different chunk types
                    chunk = self._parse_chunk(resp)
                    yield chunk

                    # Check if this is the final chunk
                    if resp.get("end_of_stream") or resp.get("end_of_dialog") or response.get("complete"):
                        break

    def _parse_chunk(self, resp: Dict[str, Any]) -> StreamingChunk:
        """Parse response chunk into appropriate type"""
        chunk_type = resp.get("chunk_type")

        if chunk_type == "thought":
            return AgentThought(
                content=resp.get("content", ""),
                end_of_message=resp.get("end_of_message", False)
            )
        elif chunk_type == "observation":
            return AgentObservation(
                content=resp.get("content", ""),
                end_of_message=resp.get("end_of_message", False)
            )
        elif chunk_type == "answer" or chunk_type == "final-answer":
            return AgentAnswer(
                content=resp.get("content", ""),
                end_of_message=resp.get("end_of_message", False),
                end_of_dialog=resp.get("end_of_dialog", False)
            )
        elif chunk_type == "action":
            # Agent action chunks - treat as thoughts for display purposes
            return AgentThought(
                content=resp.get("content", ""),
                end_of_message=resp.get("end_of_message", False)
            )
        else:
            # RAG-style chunk (or generic chunk)
            # Text-completion uses "response" field, RAG uses "chunk" field, Prompt uses "text" field
            content = resp.get("response", resp.get("chunk", resp.get("text", "")))
            return RAGChunk(
                content=content,
                end_of_stream=resp.get("end_of_stream", False),
                error=None  # Errors are always thrown, never stored
            )

    def close(self) -> None:
        """Close WebSocket connection"""
        # Cleanup handled by context manager in async code
        pass


class SocketFlowInstance:
    """Synchronous WebSocket flow instance with same interface as REST FlowInstance"""

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
        """Agent with optional streaming"""
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

        return self.client._send_request_sync("agent", self.flow_id, request, streaming)

    def text_completion(self, system: str, prompt: str, streaming: bool = False, **kwargs) -> Union[str, Iterator[str]]:
        """Text completion with optional streaming"""
        request = {
            "system": system,
            "prompt": prompt,
            "streaming": streaming
        }
        request.update(kwargs)

        result = self.client._send_request_sync("text-completion", self.flow_id, request, streaming)

        if streaming:
            # For text completion, yield just the content
            for chunk in result:
                if hasattr(chunk, 'content'):
                    yield chunk.content
        else:
            return result.get("response", "")

    def graph_rag(
        self,
        question: str,
        user: str,
        collection: str,
        max_subgraph_size: int = 1000,
        max_subgraph_count: int = 5,
        max_entity_distance: int = 3,
        streaming: bool = False,
        **kwargs: Any
    ) -> Union[str, Iterator[str]]:
        """Graph RAG with optional streaming"""
        request = {
            "question": question,
            "user": user,
            "collection": collection,
            "max-subgraph-size": max_subgraph_size,
            "max-subgraph-count": max_subgraph_count,
            "max-entity-distance": max_entity_distance,
            "streaming": streaming
        }
        request.update(kwargs)

        result = self.client._send_request_sync("graph-rag", self.flow_id, request, streaming)

        if streaming:
            for chunk in result:
                if hasattr(chunk, 'content'):
                    yield chunk.content
        else:
            return result.get("response", "")

    def document_rag(
        self,
        question: str,
        user: str,
        collection: str,
        doc_limit: int = 10,
        streaming: bool = False,
        **kwargs: Any
    ) -> Union[str, Iterator[str]]:
        """Document RAG with optional streaming"""
        request = {
            "question": question,
            "user": user,
            "collection": collection,
            "doc-limit": doc_limit,
            "streaming": streaming
        }
        request.update(kwargs)

        result = self.client._send_request_sync("document-rag", self.flow_id, request, streaming)

        if streaming:
            for chunk in result:
                if hasattr(chunk, 'content'):
                    yield chunk.content
        else:
            return result.get("response", "")

    def prompt(
        self,
        id: str,
        variables: Dict[str, str],
        streaming: bool = False,
        **kwargs: Any
    ) -> Union[str, Iterator[str]]:
        """Execute prompt with optional streaming"""
        request = {
            "id": id,
            "variables": variables,
            "streaming": streaming
        }
        request.update(kwargs)

        result = self.client._send_request_sync("prompt", self.flow_id, request, streaming)

        if streaming:
            for chunk in result:
                if hasattr(chunk, 'content'):
                    yield chunk.content
        else:
            return result.get("response", "")

    def graph_embeddings_query(
        self,
        text: str,
        user: str,
        collection: str,
        limit: int = 10,
        **kwargs: Any
    ) -> Dict[str, Any]:
        """Query graph embeddings for semantic search"""
        request = {
            "text": text,
            "user": user,
            "collection": collection,
            "limit": limit
        }
        request.update(kwargs)

        return self.client._send_request_sync("graph-embeddings", self.flow_id, request, False)

    def embeddings(self, text: str, **kwargs: Any) -> Dict[str, Any]:
        """Generate text embeddings"""
        request = {"text": text}
        request.update(kwargs)

        return self.client._send_request_sync("embeddings", self.flow_id, request, False)

    def triples_query(
        self,
        s: Optional[str] = None,
        p: Optional[str] = None,
        o: Optional[str] = None,
        user: Optional[str] = None,
        collection: Optional[str] = None,
        limit: int = 100,
        **kwargs: Any
    ) -> Dict[str, Any]:
        """Triple pattern query"""
        request = {"limit": limit}
        if s is not None:
            request["s"] = str(s)
        if p is not None:
            request["p"] = str(p)
        if o is not None:
            request["o"] = str(o)
        if user is not None:
            request["user"] = user
        if collection is not None:
            request["collection"] = collection
        request.update(kwargs)

        return self.client._send_request_sync("triples", self.flow_id, request, False)

    def objects_query(
        self,
        query: str,
        user: str,
        collection: str,
        variables: Optional[Dict[str, Any]] = None,
        operation_name: Optional[str] = None,
        **kwargs: Any
    ) -> Dict[str, Any]:
        """GraphQL query"""
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

        return self.client._send_request_sync("objects", self.flow_id, request, False)

    def mcp_tool(
        self,
        name: str,
        parameters: Dict[str, Any],
        **kwargs: Any
    ) -> Dict[str, Any]:
        """Execute MCP tool"""
        request = {
            "name": name,
            "parameters": parameters
        }
        request.update(kwargs)

        return self.client._send_request_sync("mcp-tool", self.flow_id, request, False)
