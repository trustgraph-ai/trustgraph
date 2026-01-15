"""
TrustGraph API Client

Core API client for interacting with TrustGraph services via REST and WebSocket protocols.
"""

import requests
import json
import base64
import time
from typing import Optional

from . library import Library
from . flow import Flow
from . config import Config
from . knowledge import Knowledge
from . collection import Collection
from . exceptions import *
from . types import *

def check_error(response):

    if "error" in response:

        try:
            msg = response["error"]["message"]
            tp = response["error"]["type"]
        except:
            raise ApplicationException(response["error"])

        raise ApplicationException(f"{tp}: {msg}")

class Api:
    """
    Main TrustGraph API client for synchronous and asynchronous operations.

    This class provides access to all TrustGraph services including flow management,
    knowledge graph operations, document processing, RAG queries, and more. It supports
    both REST-based and WebSocket-based communication patterns.

    The client can be used as a context manager for automatic resource cleanup:
        ```python
        with Api(url="http://localhost:8088/") as api:
            result = api.flow().id("default").graph_rag(query="test")
        ```

    Attributes:
        url: Base URL for the TrustGraph API endpoint
        timeout: Request timeout in seconds
        token: Optional bearer token for authentication
    """

    def __init__(self, url="http://localhost:8088/", timeout=60, token: Optional[str] = None):
        """
        Initialize the TrustGraph API client.

        Args:
            url: Base URL for TrustGraph API (default: "http://localhost:8088/")
            timeout: Request timeout in seconds (default: 60)
            token: Optional bearer token for authentication

        Example:
            ```python
            # Local development
            api = Api()

            # Production with authentication
            api = Api(
                url="https://trustgraph.example.com/",
                timeout=120,
                token="your-api-token"
            )
            ```
        """

        self.url = url

        if not url.endswith("/"):
            self.url += "/"

        self.url += "api/v1/"

        self.timeout = timeout
        self.token = token

        # Lazy initialization for new clients
        self._socket_client = None
        self._bulk_client = None
        self._async_flow = None
        self._async_socket_client = None
        self._async_bulk_client = None
        self._metrics = None
        self._async_metrics = None

    def flow(self):
        """
        Get a Flow client for managing and interacting with flows.

        Flows are the primary execution units in TrustGraph, providing access to
        services like agents, RAG queries, embeddings, and document processing.

        Returns:
            Flow: Flow management client

        Example:
            ```python
            flow_client = api.flow()

            # List available blueprints
            blueprints = flow_client.list_blueprints()

            # Get a specific flow instance
            flow_instance = flow_client.id("default")
            response = flow_instance.text_completion(
                system="You are helpful",
                prompt="Hello"
            )
            ```
        """
        return Flow(api=self)

    def config(self):
        """
        Get a Config client for managing configuration settings.

        Returns:
            Config: Configuration management client

        Example:
            ```python
            config = api.config()

            # Get configuration values
            values = config.get([ConfigKey(type="llm", key="model")])

            # Set configuration
            config.put([ConfigValue(type="llm", key="model", value="gpt-4")])
            ```
        """
        return Config(api=self)

    def knowledge(self):
        """
        Get a Knowledge client for managing knowledge graph cores.

        Returns:
            Knowledge: Knowledge graph management client

        Example:
            ```python
            knowledge = api.knowledge()

            # List available KG cores
            cores = knowledge.list_kg_cores(user="trustgraph")

            # Load a KG core
            knowledge.load_kg_core(id="core-123", user="trustgraph")
            ```
        """
        return Knowledge(api=self)

    def request(self, path, request):
        """
        Make a low-level REST API request.

        This method is primarily for internal use but can be used for direct
        API access when needed.

        Args:
            path: API endpoint path (relative to base URL)
            request: Request payload as a dictionary

        Returns:
            dict: Response object

        Raises:
            ProtocolException: If the response status is not 200 or response is not JSON
            ApplicationException: If the response contains an error

        Example:
            ```python
            response = api.request("flow", {
                "operation": "list-flows"
            })
            ```
        """

        url = f"{self.url}{path}"

        headers = {}
        if self.token:
            headers["Authorization"] = f"Bearer {self.token}"

        # Invoke the API, input is passed as JSON
        resp = requests.post(url, json=request, timeout=self.timeout, headers=headers)

        # Should be a 200 status code
        if resp.status_code != 200:
            raise ProtocolException(f"Status code {resp.status_code}")

        try:
            # Parse the response as JSON
            object = resp.json()
        except:
            raise ProtocolException(f"Expected JSON response")

        check_error(object)

        return object

    def library(self):
        """
        Get a Library client for document management.

        The library provides document storage, metadata management, and
        processing workflow coordination.

        Returns:
            Library: Document library management client

        Example:
            ```python
            library = api.library()

            # Add a document
            library.add_document(
                document=b"Document content",
                id="doc-123",
                metadata=[],
                user="trustgraph",
                title="My Document",
                comments="Test document"
            )

            # List documents
            docs = library.get_documents(user="trustgraph")
            ```
        """
        return Library(self)

    def collection(self):
        """
        Get a Collection client for managing data collections.

        Collections organize documents and knowledge graph data into
        logical groupings for isolation and access control.

        Returns:
            Collection: Collection management client

        Example:
            ```python
            collection = api.collection()

            # List collections
            colls = collection.list_collections(user="trustgraph")

            # Update collection metadata
            collection.update_collection(
                user="trustgraph",
                collection="default",
                name="Default Collection",
                description="Main data collection"
            )
            ```
        """
        return Collection(self)

    # New synchronous methods
    def socket(self):
        """
        Get a synchronous WebSocket client for streaming operations.

        WebSocket connections provide streaming support for real-time responses
        from agents, RAG queries, and text completions. This method returns a
        synchronous wrapper around the WebSocket protocol.

        Returns:
            SocketClient: Synchronous WebSocket client

        Example:
            ```python
            socket = api.socket()
            flow = socket.flow("default")

            # Stream agent responses
            for chunk in flow.agent(
                question="Explain quantum computing",
                user="trustgraph",
                streaming=True
            ):
                if hasattr(chunk, 'content'):
                    print(chunk.content, end='', flush=True)
            ```
        """
        if self._socket_client is None:
            from . socket_client import SocketClient
            # Extract base URL (remove api/v1/ suffix)
            base_url = self.url.rsplit("api/v1/", 1)[0].rstrip("/")
            self._socket_client = SocketClient(base_url, self.timeout, self.token)
        return self._socket_client

    def bulk(self):
        """
        Get a synchronous bulk operations client for import/export.

        Bulk operations allow efficient transfer of large datasets via WebSocket
        connections, including triples, embeddings, entity contexts, and objects.

        Returns:
            BulkClient: Synchronous bulk operations client

        Example:
            ```python
            bulk = api.bulk()

            # Export triples
            for triple in bulk.export_triples(flow="default"):
                print(f"{triple.s} {triple.p} {triple.o}")

            # Import triples
            def triple_generator():
                yield Triple(s="subj", p="pred", o="obj")
                # ... more triples

            bulk.import_triples(flow="default", triples=triple_generator())
            ```
        """
        if self._bulk_client is None:
            from . bulk_client import BulkClient
            # Extract base URL (remove api/v1/ suffix)
            base_url = self.url.rsplit("api/v1/", 1)[0].rstrip("/")
            self._bulk_client = BulkClient(base_url, self.timeout, self.token)
        return self._bulk_client

    def metrics(self):
        """
        Get a synchronous metrics client for monitoring.

        Retrieves Prometheus-formatted metrics from the TrustGraph service
        for monitoring and observability.

        Returns:
            Metrics: Synchronous metrics client

        Example:
            ```python
            metrics = api.metrics()
            prometheus_text = metrics.get()
            print(prometheus_text)
            ```
        """
        if self._metrics is None:
            from . metrics import Metrics
            # Extract base URL (remove api/v1/ suffix)
            base_url = self.url.rsplit("api/v1/", 1)[0].rstrip("/")
            self._metrics = Metrics(base_url, self.timeout, self.token)
        return self._metrics

    # New asynchronous methods
    def async_flow(self):
        """
        Get an asynchronous REST-based flow client.

        Provides async/await style access to flow operations. This is preferred
        for async Python applications and frameworks (FastAPI, aiohttp, etc.).

        Returns:
            AsyncFlow: Asynchronous flow client

        Example:
            ```python
            async_flow = api.async_flow()

            # List flows
            flow_ids = await async_flow.list()

            # Execute operations
            instance = async_flow.id("default")
            result = await instance.text_completion(
                system="You are helpful",
                prompt="Hello"
            )
            ```
        """
        if self._async_flow is None:
            from . async_flow import AsyncFlow
            self._async_flow = AsyncFlow(self.url, self.timeout, self.token)
        return self._async_flow

    def async_socket(self):
        """
        Get an asynchronous WebSocket client for streaming operations.

        Provides async/await style WebSocket access with streaming support.
        This is the preferred method for async streaming in Python.

        Returns:
            AsyncSocketClient: Asynchronous WebSocket client

        Example:
            ```python
            async_socket = api.async_socket()
            flow = async_socket.flow("default")

            # Stream agent responses
            async for chunk in flow.agent(
                question="Explain quantum computing",
                user="trustgraph",
                streaming=True
            ):
                if hasattr(chunk, 'content'):
                    print(chunk.content, end='', flush=True)
            ```
        """
        if self._async_socket_client is None:
            from . async_socket_client import AsyncSocketClient
            # Extract base URL (remove api/v1/ suffix)
            base_url = self.url.rsplit("api/v1/", 1)[0].rstrip("/")
            self._async_socket_client = AsyncSocketClient(base_url, self.timeout, self.token)
        return self._async_socket_client

    def async_bulk(self):
        """
        Get an asynchronous bulk operations client.

        Provides async/await style bulk import/export operations via WebSocket
        for efficient handling of large datasets.

        Returns:
            AsyncBulkClient: Asynchronous bulk operations client

        Example:
            ```python
            async_bulk = api.async_bulk()

            # Export triples asynchronously
            async for triple in async_bulk.export_triples(flow="default"):
                print(f"{triple.s} {triple.p} {triple.o}")

            # Import with async generator
            async def triple_gen():
                yield Triple(s="subj", p="pred", o="obj")
                # ... more triples

            await async_bulk.import_triples(
                flow="default",
                triples=triple_gen()
            )
            ```
        """
        if self._async_bulk_client is None:
            from . async_bulk_client import AsyncBulkClient
            # Extract base URL (remove api/v1/ suffix)
            base_url = self.url.rsplit("api/v1/", 1)[0].rstrip("/")
            self._async_bulk_client = AsyncBulkClient(base_url, self.timeout, self.token)
        return self._async_bulk_client

    def async_metrics(self):
        """
        Get an asynchronous metrics client.

        Provides async/await style access to Prometheus metrics.

        Returns:
            AsyncMetrics: Asynchronous metrics client

        Example:
            ```python
            async_metrics = api.async_metrics()
            prometheus_text = await async_metrics.get()
            print(prometheus_text)
            ```
        """
        if self._async_metrics is None:
            from . async_metrics import AsyncMetrics
            # Extract base URL (remove api/v1/ suffix)
            base_url = self.url.rsplit("api/v1/", 1)[0].rstrip("/")
            self._async_metrics = AsyncMetrics(base_url, self.timeout, self.token)
        return self._async_metrics

    # Resource management
    def close(self):
        """
        Close all synchronous client connections.

        This method closes WebSocket and bulk operation connections.
        It is automatically called when exiting a context manager.

        Example:
            ```python
            api = Api()
            socket = api.socket()
            # ... use socket
            api.close()  # Clean up connections

            # Or use context manager (automatic cleanup)
            with Api() as api:
                socket = api.socket()
                # ... use socket
            # Automatically closed
            ```
        """
        if self._socket_client:
            self._socket_client.close()
        if self._bulk_client:
            self._bulk_client.close()

    async def aclose(self):
        """
        Close all asynchronous client connections.

        This method closes async WebSocket, bulk operation, and flow connections.
        It is automatically called when exiting an async context manager.

        Example:
            ```python
            api = Api()
            async_socket = api.async_socket()
            # ... use async_socket
            await api.aclose()  # Clean up connections

            # Or use async context manager (automatic cleanup)
            async with Api() as api:
                async_socket = api.async_socket()
                # ... use async_socket
            # Automatically closed
            ```
        """
        if self._async_socket_client:
            await self._async_socket_client.aclose()
        if self._async_bulk_client:
            await self._async_bulk_client.aclose()
        if self._async_flow:
            await self._async_flow.aclose()

    # Context manager support
    def __enter__(self):
        """Enter synchronous context manager."""
        return self

    def __exit__(self, *args):
        """Exit synchronous context manager and close connections."""
        self.close()

    async def __aenter__(self):
        """Enter asynchronous context manager."""
        return self

    async def __aexit__(self, *args):
        """Exit asynchronous context manager and close connections."""
        await self.aclose()
