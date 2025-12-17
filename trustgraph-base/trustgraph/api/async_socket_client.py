
import json
import websockets
from typing import Optional, Dict, Any, AsyncIterator, Union

from . types import AgentThought, AgentObservation, AgentAnswer, RAGChunk
from . exceptions import ProtocolException, ApplicationException


class AsyncSocketClient:
    """Asynchronous WebSocket client"""

    def __init__(self, url: str, timeout: int, token: Optional[str]):
        self.url = self._convert_to_ws_url(url)
        self.timeout = timeout
        self.token = token
        self._request_counter = 0

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

    def flow(self, flow_id: str):
        """Get async flow instance for WebSocket operations"""
        return AsyncSocketFlowInstance(self, flow_id)

    async def _send_request(self, service: str, flow: Optional[str], request: Dict[str, Any]):
        """Async WebSocket request implementation (non-streaming)"""
        # Generate unique request ID
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
                raise ApplicationException(response["error"])

            if "response" not in response:
                raise ProtocolException(f"Missing response in message")

            return response["response"]

    async def _send_request_streaming(self, service: str, flow: Optional[str], request: Dict[str, Any]):
        """Async WebSocket request implementation (streaming)"""
        # Generate unique request ID
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
                    raise ApplicationException(response["error"])

                if "response" in response:
                    resp = response["response"]

                    # Parse different chunk types
                    chunk = self._parse_chunk(resp)
                    yield chunk

                    # Check if this is the final chunk
                    if resp.get("end_of_stream") or resp.get("end_of_dialog") or response.get("complete"):
                        break

    def _parse_chunk(self, resp: Dict[str, Any]):
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

    async def aclose(self):
        """Close WebSocket connection"""
        # Cleanup handled by context manager
        pass


class AsyncSocketFlowInstance:
    """Asynchronous WebSocket flow instance"""

    def __init__(self, client: AsyncSocketClient, flow_id: str):
        self.client = client
        self.flow_id = flow_id

    async def agent(self, question: str, user: str, state: Optional[Dict[str, Any]] = None,
                    group: Optional[str] = None, history: Optional[list] = None,
                    streaming: bool = False, **kwargs) -> Union[Dict[str, Any], AsyncIterator]:
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

        if streaming:
            return self.client._send_request_streaming("agent", self.flow_id, request)
        else:
            return await self.client._send_request("agent", self.flow_id, request)

    async def text_completion(self, system: str, prompt: str, streaming: bool = False, **kwargs):
        """Text completion with optional streaming"""
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
            return result.get("response", "")

    async def _text_completion_streaming(self, request):
        """Helper for streaming text completion"""
        async for chunk in self.client._send_request_streaming("text-completion", self.flow_id, request):
            if hasattr(chunk, 'content'):
                yield chunk.content

    async def graph_rag(self, query: str, user: str, collection: str,
                        max_subgraph_size: int = 1000, max_subgraph_count: int = 5,
                        max_entity_distance: int = 3, streaming: bool = False, **kwargs):
        """Graph RAG with optional streaming"""
        request = {
            "query": query,
            "user": user,
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

    async def document_rag(self, question: str, user: str, collection: str,
                           doc_limit: int = 10, streaming: bool = False, **kwargs):
        """Document RAG with optional streaming"""
        request = {
            "question": question,
            "user": user,
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

    async def graph_embeddings_query(self, text: str, user: str, collection: str, limit: int = 10, **kwargs):
        """Query graph embeddings for semantic search"""
        request = {
            "text": text,
            "user": user,
            "collection": collection,
            "limit": limit
        }
        request.update(kwargs)

        return await self.client._send_request("graph-embeddings", self.flow_id, request)

    async def embeddings(self, text: str, **kwargs):
        """Generate text embeddings"""
        request = {"text": text}
        request.update(kwargs)

        return await self.client._send_request("embeddings", self.flow_id, request)

    async def triples_query(self, s=None, p=None, o=None, user=None, collection=None, limit=100, **kwargs):
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

        return await self.client._send_request("triples", self.flow_id, request)

    async def objects_query(self, query: str, user: str, collection: str, variables: Optional[Dict] = None,
                            operation_name: Optional[str] = None, **kwargs):
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

        return await self.client._send_request("objects", self.flow_id, request)

    async def mcp_tool(self, name: str, parameters: Dict[str, Any], **kwargs):
        """Execute MCP tool"""
        request = {
            "name": name,
            "parameters": parameters
        }
        request.update(kwargs)

        return await self.client._send_request("mcp-tool", self.flow_id, request)
