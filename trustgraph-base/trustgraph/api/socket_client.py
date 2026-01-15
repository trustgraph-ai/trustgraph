"""
TrustGraph Synchronous WebSocket Client

This module provides synchronous WebSocket-based access to TrustGraph services with
streaming support for real-time responses from agents, RAG queries, and text completions.
"""

import json
import asyncio
import websockets
from typing import Optional, Dict, Any, Iterator, Union, List
from threading import Lock

from . types import AgentThought, AgentObservation, AgentAnswer, RAGChunk, StreamingChunk
from . exceptions import ProtocolException, raise_from_error_dict


class SocketClient:
    """
    Synchronous WebSocket client for streaming operations.

    Provides a synchronous interface to WebSocket-based TrustGraph services,
    wrapping async websockets library with synchronous generators for ease of use.
    Supports streaming responses from agents, RAG queries, and text completions.

    Note: This is a synchronous wrapper around async WebSocket operations. For
    true async support, use AsyncSocketClient instead.
    """

    def __init__(self, url: str, timeout: int, token: Optional[str]) -> None:
        """
        Initialize synchronous WebSocket client.

        Args:
            url: Base URL for TrustGraph API (HTTP/HTTPS will be converted to WS/WSS)
            timeout: WebSocket timeout in seconds
            token: Optional bearer token for authentication
        """
        self.url: str = self._convert_to_ws_url(url)
        self.timeout: int = timeout
        self.token: Optional[str] = token
        self._connection: Optional[Any] = None
        self._request_counter: int = 0
        self._lock: Lock = Lock()
        self._loop: Optional[asyncio.AbstractEventLoop] = None

    def _convert_to_ws_url(self, url: str) -> str:
        """
        Convert HTTP URL to WebSocket URL.

        Args:
            url: HTTP/HTTPS or WS/WSS URL

        Returns:
            str: WebSocket URL (ws:// or wss://)
        """
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
        """
        Get a flow instance for WebSocket streaming operations.

        Args:
            flow_id: Flow identifier

        Returns:
            SocketFlowInstance: Flow instance with streaming methods

        Example:
            ```python
            socket = api.socket()
            flow = socket.flow("default")

            # Stream agent responses
            for chunk in flow.agent(question="Hello", user="trustgraph", streaming=True):
                print(chunk.content, end='', flush=True)
            ```
        """
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
        # Non-streaming agent format: chunk_type is empty but has thought/observation/answer fields
        elif resp.get("thought"):
            return AgentThought(
                content=resp.get("thought", ""),
                end_of_message=resp.get("end_of_message", False)
            )
        elif resp.get("observation"):
            return AgentObservation(
                content=resp.get("observation", ""),
                end_of_message=resp.get("end_of_message", False)
            )
        elif resp.get("answer"):
            return AgentAnswer(
                content=resp.get("answer", ""),
                end_of_message=resp.get("end_of_message", False),
                end_of_dialog=resp.get("end_of_dialog", False)
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
        """
        Close WebSocket connections.

        Note: Cleanup is handled automatically by context managers in async code.
        """
        # Cleanup handled by context manager in async code
        pass


class SocketFlowInstance:
    """
    Synchronous WebSocket flow instance for streaming operations.

    Provides the same interface as REST FlowInstance but with WebSocket-based
    streaming support for real-time responses. All methods support an optional
    `streaming` parameter to enable incremental result delivery.
    """

    def __init__(self, client: SocketClient, flow_id: str) -> None:
        """
        Initialize socket flow instance.

        Args:
            client: Parent SocketClient
            flow_id: Flow identifier
        """
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
        """
        Execute an agent operation with streaming support.

        Agents can perform multi-step reasoning with tool use. This method always
        returns streaming chunks (thoughts, observations, answers) even when
        streaming=False, to show the agent's reasoning process.

        Args:
            question: User question or instruction
            user: User identifier
            state: Optional state dictionary for stateful conversations
            group: Optional group identifier for multi-user contexts
            history: Optional conversation history as list of message dicts
            streaming: Enable streaming mode (default: False)
            **kwargs: Additional parameters passed to the agent service

        Returns:
            Iterator[StreamingChunk]: Stream of agent thoughts, observations, and answers

        Example:
            ```python
            socket = api.socket()
            flow = socket.flow("default")

            # Stream agent reasoning
            for chunk in flow.agent(
                question="What is quantum computing?",
                user="trustgraph",
                streaming=True
            ):
                if isinstance(chunk, AgentThought):
                    print(f"[Thinking] {chunk.content}")
                elif isinstance(chunk, AgentObservation):
                    print(f"[Observation] {chunk.content}")
                elif isinstance(chunk, AgentAnswer):
                    print(f"[Answer] {chunk.content}")
            ```
        """
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

        # Agents always use multipart messaging (multiple complete messages)
        # regardless of streaming flag, so always use the streaming code path
        return self.client._send_request_sync("agent", self.flow_id, request, streaming=True)

    def text_completion(self, system: str, prompt: str, streaming: bool = False, **kwargs) -> Union[str, Iterator[str]]:
        """
        Execute text completion with optional streaming.

        Args:
            system: System prompt defining the assistant's behavior
            prompt: User prompt/question
            streaming: Enable streaming mode (default: False)
            **kwargs: Additional parameters passed to the service

        Returns:
            Union[str, Iterator[str]]: Complete response or stream of text chunks

        Example:
            ```python
            socket = api.socket()
            flow = socket.flow("default")

            # Non-streaming
            response = flow.text_completion(
                system="You are helpful",
                prompt="Explain quantum computing",
                streaming=False
            )
            print(response)

            # Streaming
            for chunk in flow.text_completion(
                system="You are helpful",
                prompt="Explain quantum computing",
                streaming=True
            ):
                print(chunk, end='', flush=True)
            ```
        """
        request = {
            "system": system,
            "prompt": prompt,
            "streaming": streaming
        }
        request.update(kwargs)

        result = self.client._send_request_sync("text-completion", self.flow_id, request, streaming)

        if streaming:
            # For text completion, return generator that yields content
            return self._text_completion_generator(result)
        else:
            return result.get("response", "")

    def _text_completion_generator(self, result: Iterator[StreamingChunk]) -> Iterator[str]:
        """Generator for text completion streaming"""
        for chunk in result:
            if hasattr(chunk, 'content'):
                yield chunk.content

    def graph_rag(
        self,
        query: str,
        user: str,
        collection: str,
        max_subgraph_size: int = 1000,
        max_subgraph_count: int = 5,
        max_entity_distance: int = 3,
        streaming: bool = False,
        **kwargs: Any
    ) -> Union[str, Iterator[str]]:
        """
        Execute graph-based RAG query with optional streaming.

        Uses knowledge graph structure to find relevant context, then generates
        a response using an LLM. Streaming mode delivers results incrementally.

        Args:
            query: Natural language query
            user: User/keyspace identifier
            collection: Collection identifier
            max_subgraph_size: Maximum total triples in subgraph (default: 1000)
            max_subgraph_count: Maximum number of subgraphs (default: 5)
            max_entity_distance: Maximum traversal depth (default: 3)
            streaming: Enable streaming mode (default: False)
            **kwargs: Additional parameters passed to the service

        Returns:
            Union[str, Iterator[str]]: Complete response or stream of text chunks

        Example:
            ```python
            socket = api.socket()
            flow = socket.flow("default")

            # Streaming graph RAG
            for chunk in flow.graph_rag(
                query="Tell me about Marie Curie",
                user="trustgraph",
                collection="scientists",
                streaming=True
            ):
                print(chunk, end='', flush=True)
            ```
        """
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

        result = self.client._send_request_sync("graph-rag", self.flow_id, request, streaming)

        if streaming:
            return self._rag_generator(result)
        else:
            return result.get("response", "")

    def document_rag(
        self,
        query: str,
        user: str,
        collection: str,
        doc_limit: int = 10,
        streaming: bool = False,
        **kwargs: Any
    ) -> Union[str, Iterator[str]]:
        """
        Execute document-based RAG query with optional streaming.

        Uses vector embeddings to find relevant document chunks, then generates
        a response using an LLM. Streaming mode delivers results incrementally.

        Args:
            query: Natural language query
            user: User/keyspace identifier
            collection: Collection identifier
            doc_limit: Maximum document chunks to retrieve (default: 10)
            streaming: Enable streaming mode (default: False)
            **kwargs: Additional parameters passed to the service

        Returns:
            Union[str, Iterator[str]]: Complete response or stream of text chunks

        Example:
            ```python
            socket = api.socket()
            flow = socket.flow("default")

            # Streaming document RAG
            for chunk in flow.document_rag(
                query="Summarize the key findings",
                user="trustgraph",
                collection="research-papers",
                doc_limit=5,
                streaming=True
            ):
                print(chunk, end='', flush=True)
            ```
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
            return result.get("response", "")

    def _rag_generator(self, result: Iterator[StreamingChunk]) -> Iterator[str]:
        """Generator for RAG streaming (graph-rag and document-rag)"""
        for chunk in result:
            if hasattr(chunk, 'content'):
                yield chunk.content

    def prompt(
        self,
        id: str,
        variables: Dict[str, str],
        streaming: bool = False,
        **kwargs: Any
    ) -> Union[str, Iterator[str]]:
        """
        Execute a prompt template with optional streaming.

        Args:
            id: Prompt template identifier
            variables: Dictionary of variable name to value mappings
            streaming: Enable streaming mode (default: False)
            **kwargs: Additional parameters passed to the service

        Returns:
            Union[str, Iterator[str]]: Complete response or stream of text chunks

        Example:
            ```python
            socket = api.socket()
            flow = socket.flow("default")

            # Streaming prompt execution
            for chunk in flow.prompt(
                id="summarize-template",
                variables={"topic": "quantum computing", "length": "brief"},
                streaming=True
            ):
                print(chunk, end='', flush=True)
            ```
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
            return result.get("response", "")

    def graph_embeddings_query(
        self,
        text: str,
        user: str,
        collection: str,
        limit: int = 10,
        **kwargs: Any
    ) -> Dict[str, Any]:
        """
        Query knowledge graph entities using semantic similarity.

        Args:
            text: Query text for semantic search
            user: User/keyspace identifier
            collection: Collection identifier
            limit: Maximum number of results (default: 10)
            **kwargs: Additional parameters passed to the service

        Returns:
            dict: Query results with similar entities

        Example:
            ```python
            socket = api.socket()
            flow = socket.flow("default")

            results = flow.graph_embeddings_query(
                text="physicist who discovered radioactivity",
                user="trustgraph",
                collection="scientists",
                limit=5
            )
            ```
        """
        request = {
            "text": text,
            "user": user,
            "collection": collection,
            "limit": limit
        }
        request.update(kwargs)

        return self.client._send_request_sync("graph-embeddings", self.flow_id, request, False)

    def embeddings(self, text: str, **kwargs: Any) -> Dict[str, Any]:
        """
        Generate vector embeddings for text.

        Args:
            text: Input text to embed
            **kwargs: Additional parameters passed to the service

        Returns:
            dict: Response containing vectors

        Example:
            ```python
            socket = api.socket()
            flow = socket.flow("default")

            result = flow.embeddings("quantum computing")
            vectors = result.get("vectors", [])
            ```
        """
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
        """
        Query knowledge graph triples using pattern matching.

        Args:
            s: Subject URI (optional, use None for wildcard)
            p: Predicate URI (optional, use None for wildcard)
            o: Object URI or Literal (optional, use None for wildcard)
            user: User/keyspace identifier (optional)
            collection: Collection identifier (optional)
            limit: Maximum results to return (default: 100)
            **kwargs: Additional parameters passed to the service

        Returns:
            dict: Query results with matching triples

        Example:
            ```python
            socket = api.socket()
            flow = socket.flow("default")

            # Find all triples about a specific subject
            result = flow.triples_query(
                s="http://example.org/person/marie-curie",
                user="trustgraph",
                collection="scientists"
            )
            ```
        """
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
        """
        Execute a GraphQL query against structured objects.

        Args:
            query: GraphQL query string
            user: User/keyspace identifier
            collection: Collection identifier
            variables: Optional query variables dictionary
            operation_name: Optional operation name for multi-operation documents
            **kwargs: Additional parameters passed to the service

        Returns:
            dict: GraphQL response with data, errors, and/or extensions

        Example:
            ```python
            socket = api.socket()
            flow = socket.flow("default")

            query = '''
            {
              scientists(limit: 10) {
                name
                field
                discoveries
              }
            }
            '''
            result = flow.objects_query(
                query=query,
                user="trustgraph",
                collection="scientists"
            )
            ```
        """
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
        """
        Execute a Model Context Protocol (MCP) tool.

        Args:
            name: Tool name/identifier
            parameters: Tool parameters dictionary
            **kwargs: Additional parameters passed to the service

        Returns:
            dict: Tool execution result

        Example:
            ```python
            socket = api.socket()
            flow = socket.flow("default")

            result = flow.mcp_tool(
                name="search-web",
                parameters={"query": "latest AI news", "limit": 5}
            )
            ```
        """
        request = {
            "name": name,
            "parameters": parameters
        }
        request.update(kwargs)

        return self.client._send_request_sync("mcp-tool", self.flow_id, request, False)
