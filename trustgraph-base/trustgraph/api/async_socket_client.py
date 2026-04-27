
import json
import asyncio
import websockets
from typing import Optional, Dict, Any, AsyncIterator, Union

from . types import AgentThought, AgentObservation, AgentAnswer, RAGChunk, TextCompletionResult
from . exceptions import ProtocolException, ApplicationException


class AsyncSocketClient:
    """Asynchronous WebSocket client with persistent connection.

    Maintains a single websocket connection and multiplexes requests
    by ID, routing responses via a background reader task.

    Use as an async context manager for proper lifecycle management:

        async with AsyncSocketClient(url, timeout, token) as client:
            result = await client._send_request(...)

    Or call connect()/aclose() manually.
    """

    def __init__(
        self, url: str, timeout: int, token: Optional[str],
        workspace: str = "default",
    ):
        self.url = self._convert_to_ws_url(url)
        self.timeout = timeout
        self.token = token
        self.workspace = workspace
        self._request_counter = 0
        self._socket = None
        self._connect_cm = None
        self._reader_task = None
        self._pending = {}  # request_id -> asyncio.Queue
        self._connected = False

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

    def _build_ws_url(self):
        ws_url = f"{self.url.rstrip('/')}/api/v1/socket"
        if self.token:
            ws_url = f"{ws_url}?token={self.token}"
        return ws_url

    async def connect(self):
        """Establish the persistent websocket connection."""
        if self._connected:
            return

        ws_url = self._build_ws_url()
        self._connect_cm = websockets.connect(
            ws_url, ping_interval=20, ping_timeout=self.timeout
        )
        self._socket = await self._connect_cm.__aenter__()
        self._connected = True
        self._reader_task = asyncio.create_task(self._reader())

    async def __aenter__(self):
        await self.connect()
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        await self.aclose()

    async def _ensure_connected(self):
        """Lazily connect if not already connected."""
        if not self._connected:
            await self.connect()

    async def _reader(self):
        """Background task to read responses and route by request ID."""
        try:
            async for raw_message in self._socket:
                response = json.loads(raw_message)
                request_id = response.get("id")

                if request_id and request_id in self._pending:
                    await self._pending[request_id].put(response)
                # Ignore messages for unknown request IDs

        except websockets.exceptions.ConnectionClosed:
            pass
        except Exception as e:
            # Signal error to all pending requests
            for queue in self._pending.values():
                try:
                    await queue.put({"error": str(e)})
                except:
                    pass
        finally:
            self._connected = False

    def _next_request_id(self):
        self._request_counter += 1
        return f"req-{self._request_counter}"

    def flow(self, flow_id: str):
        """Get async flow instance for WebSocket operations"""
        return AsyncSocketFlowInstance(self, flow_id)

    async def _send_request(self, service: str, flow: Optional[str], request: Dict[str, Any]):
        """Send a request and wait for a single response."""
        await self._ensure_connected()

        request_id = self._next_request_id()
        queue = asyncio.Queue()
        self._pending[request_id] = queue

        try:
            message = {
                "id": request_id,
                "workspace": self.workspace,
                "service": service,
                "request": request
            }
            if flow:
                message["flow"] = flow

            await self._socket.send(json.dumps(message))

            response = await queue.get()

            if "error" in response:
                raise ApplicationException(response["error"])

            if "response" not in response:
                raise ProtocolException("Missing response in message")

            return response["response"]

        finally:
            self._pending.pop(request_id, None)

    async def _send_request_streaming(self, service: str, flow: Optional[str], request: Dict[str, Any]):
        """Send a request and yield streaming response chunks."""
        await self._ensure_connected()

        request_id = self._next_request_id()
        queue = asyncio.Queue()
        self._pending[request_id] = queue

        try:
            message = {
                "id": request_id,
                "workspace": self.workspace,
                "service": service,
                "request": request
            }
            if flow:
                message["flow"] = flow

            await self._socket.send(json.dumps(message))

            while True:
                response = await queue.get()

                if "error" in response:
                    raise ApplicationException(response["error"])

                if "response" in response:
                    resp = response["response"]

                    chunk = self._parse_chunk(resp)
                    if chunk is not None:
                        yield chunk

                    if resp.get("end_of_session") or resp.get("end_of_dialog") or response.get("complete"):
                        break

        finally:
            self._pending.pop(request_id, None)

    def _parse_chunk(self, resp: Dict[str, Any]):
        """Parse response chunk into appropriate type. Returns None for non-content messages."""
        message_type = resp.get("message_type")

        # Handle new GraphRAG message format with message_type
        if message_type == "provenance":
            return None

        if message_type == "thought":
            return AgentThought(
                content=resp.get("content", ""),
                end_of_message=resp.get("end_of_message", False)
            )
        elif message_type == "observation":
            return AgentObservation(
                content=resp.get("content", ""),
                end_of_message=resp.get("end_of_message", False)
            )
        elif message_type == "answer" or message_type == "final-answer":
            return AgentAnswer(
                content=resp.get("content", ""),
                end_of_message=resp.get("end_of_message", False),
                end_of_dialog=resp.get("end_of_dialog", False),
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

    async def aclose(self):
        """Close the persistent WebSocket connection cleanly."""
        # Wait for reader to finish (socket close will cause it to exit)
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


class AsyncSocketFlowInstance:
    """Asynchronous WebSocket flow instance"""

    def __init__(self, client: AsyncSocketClient, flow_id: str):
        self.client = client
        self.flow_id = flow_id

    async def agent(self, question: str, state: Optional[Dict[str, Any]] = None,
                    group: Optional[str] = None, history: Optional[list] = None,
                    streaming: bool = False, **kwargs) -> Union[Dict[str, Any], AsyncIterator]:
        """Agent with optional streaming"""
        request = {
            "question": question,
            "streaming": streaming
        }
        if state is not None:
            request["state"] = state
        if group is not None:
            request["group"] = group
        if history is not None:
            request["history"] = history
        request.update(kwargs)

        if streaming:
            return self.client._send_request_streaming("agent", self.flow_id, request)
        else:
            return await self.client._send_request("agent", self.flow_id, request)

    async def text_completion(self, system: str, prompt: str, streaming: bool = False, **kwargs):
        """Text completion with optional streaming.

        Non-streaming: returns a TextCompletionResult with text and token counts.
        Streaming: returns an async iterator of RAGChunk (with token counts on the final chunk).
        """
        request = {
            "system": system,
            "prompt": prompt,
            "streaming": streaming
        }
        request.update(kwargs)

        if streaming:
            return self._text_completion_streaming(request)
        else:
            result = await self.client._send_request("text-completion", self.flow_id, request)
            return TextCompletionResult(
                text=result.get("response", ""),
                in_token=result.get("in_token"),
                out_token=result.get("out_token"),
                model=result.get("model"),
            )

    async def _text_completion_streaming(self, request):
        """Helper for streaming text completion. Yields RAGChunk objects."""
        async for chunk in self.client._send_request_streaming("text-completion", self.flow_id, request):
            if isinstance(chunk, RAGChunk):
                yield chunk

    async def graph_rag(self, query: str, collection: str,
                        max_subgraph_size: int = 1000, max_subgraph_count: int = 5,
                        max_entity_distance: int = 3, streaming: bool = False, **kwargs):
        """Graph RAG with optional streaming"""
        request = {
            "query": query,
            "collection": collection,
            "max-subgraph-size": max_subgraph_size,
            "max-subgraph-count": max_subgraph_count,
            "max-entity-distance": max_entity_distance,
            "streaming": streaming
        }
        request.update(kwargs)

        if streaming:
            return self._graph_rag_streaming(request)
        else:
            result = await self.client._send_request("graph-rag", self.flow_id, request)
            return result.get("response", "")

    async def _graph_rag_streaming(self, request):
        """Helper for streaming graph RAG"""
        async for chunk in self.client._send_request_streaming("graph-rag", self.flow_id, request):
            if hasattr(chunk, 'content'):
                yield chunk.content

    async def document_rag(self, query: str, collection: str,
                           doc_limit: int = 10, streaming: bool = False, **kwargs):
        """Document RAG with optional streaming"""
        request = {
            "query": query,
            "collection": collection,
            "doc-limit": doc_limit,
            "streaming": streaming
        }
        request.update(kwargs)

        if streaming:
            return self._document_rag_streaming(request)
        else:
            result = await self.client._send_request("document-rag", self.flow_id, request)
            return result.get("response", "")

    async def _document_rag_streaming(self, request):
        """Helper for streaming document RAG"""
        async for chunk in self.client._send_request_streaming("document-rag", self.flow_id, request):
            if hasattr(chunk, 'content'):
                yield chunk.content

    async def prompt(self, id: str, variables: Dict[str, str], streaming: bool = False, **kwargs):
        """Execute prompt with optional streaming"""
        request = {
            "id": id,
            "variables": variables,
            "streaming": streaming
        }
        request.update(kwargs)

        if streaming:
            return self._prompt_streaming(request)
        else:
            result = await self.client._send_request("prompt", self.flow_id, request)
            return result.get("response", "")

    async def _prompt_streaming(self, request):
        """Helper for streaming prompt"""
        async for chunk in self.client._send_request_streaming("prompt", self.flow_id, request):
            if hasattr(chunk, 'content'):
                yield chunk.content

    async def graph_embeddings_query(self, text: str, collection: str, limit: int = 10, **kwargs):
        """Query graph embeddings for semantic search"""
        emb_result = await self.embeddings(texts=[text])
        vector = emb_result.get("vectors", [[]])[0]

        request = {
            "vector": vector,
            "collection": collection,
            "limit": limit
        }
        request.update(kwargs)

        return await self.client._send_request("graph-embeddings", self.flow_id, request)

    async def embeddings(self, texts: list, **kwargs):
        """Generate text embeddings"""
        request = {"texts": texts}
        request.update(kwargs)

        return await self.client._send_request("embeddings", self.flow_id, request)

    async def triples_query(self, s=None, p=None, o=None, collection=None, limit=100, **kwargs):
        """Triple pattern query"""
        request = {"limit": limit}
        if s is not None:
            request["s"] = str(s)
        if p is not None:
            request["p"] = str(p)
        if o is not None:
            request["o"] = str(o)
        if collection is not None:
            request["collection"] = collection
        request.update(kwargs)

        return await self.client._send_request("triples", self.flow_id, request)

    async def rows_query(self, query: str, collection: str, variables: Optional[Dict] = None,
                         operation_name: Optional[str] = None, **kwargs):
        """GraphQL query against structured rows"""
        request = {
            "query": query,
            "collection": collection
        }
        if variables:
            request["variables"] = variables
        if operation_name:
            request["operationName"] = operation_name
        request.update(kwargs)

        return await self.client._send_request("rows", self.flow_id, request)

    async def mcp_tool(self, name: str, parameters: Dict[str, Any], **kwargs):
        """Execute MCP tool"""
        request = {
            "name": name,
            "parameters": parameters
        }
        request.update(kwargs)

        return await self.client._send_request("mcp-tool", self.flow_id, request)

    async def row_embeddings_query(
        self, text: str, schema_name: str,
        collection: str = "default", index_name: Optional[str] = None,
        limit: int = 10, **kwargs
    ):
        """Query row embeddings for semantic search on structured data"""
        emb_result = await self.embeddings(texts=[text])
        vector = emb_result.get("vectors", [[]])[0]

        request = {
            "vector": vector,
            "schema_name": schema_name,
            "collection": collection,
            "limit": limit
        }
        if index_name:
            request["index_name"] = index_name
        request.update(kwargs)

        return await self.client._send_request("row-embeddings", self.flow_id, request)
