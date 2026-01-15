"""
TrustGraph Asynchronous Flow Management

This module provides async/await based interfaces for managing and interacting
with TrustGraph flows using REST API calls. Unlike async_socket_client which
provides streaming support, this module is focused on non-streaming operations
that return complete responses.

For streaming support (e.g., real-time agent responses, streaming RAG), use
AsyncSocketClient instead.
"""

import aiohttp
import json
from typing import Optional, Dict, Any, List

from . exceptions import ProtocolException, ApplicationException


def check_error(response):
    if "error" in response:
        try:
            msg = response["error"]["message"]
            tp = response["error"]["type"]
        except:
            raise ApplicationException(response["error"])

        raise ApplicationException(f"{tp}: {msg}")


class AsyncFlow:
    """
    Asynchronous flow management client using REST API.

    Provides async/await based flow management operations including listing,
    starting, stopping flows, and managing flow class definitions. Also provides
    access to flow-scoped services like agents, RAG, and queries via non-streaming
    REST endpoints.

    Note: For streaming support, use AsyncSocketClient instead.
    """

    def __init__(self, url: str, timeout: int, token: Optional[str]) -> None:
        """
        Initialize async flow client.

        Args:
            url: Base URL for TrustGraph API
            timeout: Request timeout in seconds
            token: Optional bearer token for authentication
        """
        self.url: str = url
        self.timeout: int = timeout
        self.token: Optional[str] = token

    async def request(self, path: str, request_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Make async HTTP POST request to Gateway API.

        Internal method for making authenticated requests to the TrustGraph API.

        Args:
            path: API endpoint path (relative to base URL)
            request_data: Request payload dictionary

        Returns:
            dict: Response object from API

        Raises:
            ProtocolException: If HTTP status is not 200 or response is not valid JSON
            ApplicationException: If API returns an error response
        """
        url = f"{self.url}{path}"

        headers = {"Content-Type": "application/json"}
        if self.token:
            headers["Authorization"] = f"Bearer {self.token}"

        timeout = aiohttp.ClientTimeout(total=self.timeout)

        async with aiohttp.ClientSession(timeout=timeout) as session:
            async with session.post(url, json=request_data, headers=headers) as resp:
                if resp.status != 200:
                    raise ProtocolException(f"Status code {resp.status}")

                try:
                    obj = await resp.json()
                except:
                    raise ProtocolException(f"Expected JSON response")

                check_error(obj)
                return obj

    async def list(self) -> List[str]:
        """
        List all flow identifiers.

        Retrieves IDs of all flows currently deployed in the system.

        Returns:
            list[str]: List of flow identifiers

        Example:
            ```python
            async_flow = await api.async_flow()

            # List all flows
            flows = await async_flow.list()
            print(f"Available flows: {flows}")
            ```
        """
        result = await self.request("flow", {"operation": "list-flows"})
        return result.get("flow-ids", [])

    async def get(self, id: str) -> Dict[str, Any]:
        """
        Get flow definition.

        Retrieves the complete flow configuration including its class name,
        description, and parameters.

        Args:
            id: Flow identifier

        Returns:
            dict: Flow definition object

        Example:
            ```python
            async_flow = await api.async_flow()

            # Get flow definition
            flow_def = await async_flow.get("default")
            print(f"Flow class: {flow_def.get('class-name')}")
            print(f"Description: {flow_def.get('description')}")
            ```
        """
        result = await self.request("flow", {
            "operation": "get-flow",
            "flow-id": id
        })
        return json.loads(result.get("flow", "{}"))

    async def start(self, class_name: str, id: str, description: str, parameters: Optional[Dict] = None):
        """
        Start a new flow instance.

        Creates and starts a flow from a flow class definition with the specified
        parameters.

        Args:
            class_name: Flow class name to instantiate
            id: Identifier for the new flow instance
            description: Human-readable description of the flow
            parameters: Optional configuration parameters for the flow

        Example:
            ```python
            async_flow = await api.async_flow()

            # Start a flow from a class
            await async_flow.start(
                class_name="default",
                id="my-flow",
                description="Custom flow instance",
                parameters={"model": "claude-3-opus"}
            )
            ```
        """
        request_data = {
            "operation": "start-flow",
            "flow-id": id,
            "class-name": class_name,
            "description": description
        }
        if parameters:
            request_data["parameters"] = json.dumps(parameters)

        await self.request("flow", request_data)

    async def stop(self, id: str):
        """
        Stop a running flow.

        Stops and removes a flow instance, freeing its resources.

        Args:
            id: Flow identifier to stop

        Example:
            ```python
            async_flow = await api.async_flow()

            # Stop a flow
            await async_flow.stop("my-flow")
            ```
        """
        await self.request("flow", {
            "operation": "stop-flow",
            "flow-id": id
        })

    async def list_classes(self) -> List[str]:
        """
        List all flow class names.

        Retrieves names of all flow classes (blueprints) available in the system.

        Returns:
            list[str]: List of flow class names

        Example:
            ```python
            async_flow = await api.async_flow()

            # List available flow classes
            classes = await async_flow.list_classes()
            print(f"Available flow classes: {classes}")
            ```
        """
        result = await self.request("flow", {"operation": "list-classes"})
        return result.get("class-names", [])

    async def get_class(self, class_name: str) -> Dict[str, Any]:
        """
        Get flow class definition.

        Retrieves the blueprint definition for a flow class, including its
        configuration schema and service bindings.

        Args:
            class_name: Flow class name

        Returns:
            dict: Flow class definition object

        Example:
            ```python
            async_flow = await api.async_flow()

            # Get flow class definition
            class_def = await async_flow.get_class("default")
            print(f"Services: {class_def.get('services')}")
            ```
        """
        result = await self.request("flow", {
            "operation": "get-class",
            "class-name": class_name
        })
        return json.loads(result.get("class-definition", "{}"))

    async def put_class(self, class_name: str, definition: Dict[str, Any]):
        """
        Create or update a flow class definition.

        Stores a flow class blueprint that can be used to instantiate flows.

        Args:
            class_name: Flow class name
            definition: Flow class definition object

        Example:
            ```python
            async_flow = await api.async_flow()

            # Create a custom flow class
            class_def = {
                "services": {
                    "agent": {"module": "agent", "config": {...}},
                    "graph-rag": {"module": "graph-rag", "config": {...}}
                }
            }
            await async_flow.put_class("custom-flow", class_def)
            ```
        """
        await self.request("flow", {
            "operation": "put-class",
            "class-name": class_name,
            "class-definition": json.dumps(definition)
        })

    async def delete_class(self, class_name: str):
        """
        Delete a flow class definition.

        Removes a flow class blueprint from the system. Does not affect
        running flow instances.

        Args:
            class_name: Flow class name to delete

        Example:
            ```python
            async_flow = await api.async_flow()

            # Delete a flow class
            await async_flow.delete_class("old-flow-class")
            ```
        """
        await self.request("flow", {
            "operation": "delete-class",
            "class-name": class_name
        })

    def id(self, flow_id: str):
        """
        Get an async flow instance client.

        Returns a client for interacting with a specific flow's services
        (agent, RAG, queries, embeddings, etc.).

        Args:
            flow_id: Flow identifier

        Returns:
            AsyncFlowInstance: Client for flow-specific operations

        Example:
            ```python
            async_flow = await api.async_flow()

            # Get flow instance
            flow = async_flow.id("default")

            # Use flow services
            result = await flow.graph_rag(
                query="What is TrustGraph?",
                user="trustgraph",
                collection="default"
            )
            ```
        """
        return AsyncFlowInstance(self, flow_id)

    async def aclose(self) -> None:
        """
        Close async client and cleanup resources.

        Note: Cleanup is handled automatically by aiohttp session context managers.
        This method is provided for consistency with other async clients.
        """
        pass


class AsyncFlowInstance:
    """
    Asynchronous flow instance client.

    Provides async/await access to flow-scoped services including agents,
    RAG queries, embeddings, and graph queries. All operations return complete
    responses (non-streaming).

    Note: For streaming support, use AsyncSocketFlowInstance instead.
    """

    def __init__(self, flow: AsyncFlow, flow_id: str):
        """
        Initialize async flow instance.

        Args:
            flow: Parent AsyncFlow client
            flow_id: Flow identifier
        """
        self.flow = flow
        self.flow_id = flow_id

    async def request(self, service: str, request_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Make request to a flow-scoped service.

        Internal method for calling services within this flow instance.

        Args:
            service: Service name (e.g., "agent", "graph-rag", "triples")
            request_data: Service request payload

        Returns:
            dict: Service response object

        Raises:
            ProtocolException: If request fails or response is invalid
            ApplicationException: If service returns an error
        """
        return await self.flow.request(f"flow/{self.flow_id}/service/{service}", request_data)

    async def agent(self, question: str, user: str, state: Optional[Dict] = None,
                    group: Optional[str] = None, history: Optional[List] = None, **kwargs: Any) -> Dict[str, Any]:
        """
        Execute an agent operation (non-streaming).

        Runs an agent to answer a question, with optional conversation state and
        history. Returns the complete response after the agent has finished
        processing.

        Note: This method does not support streaming. For real-time agent thoughts
        and observations, use AsyncSocketFlowInstance.agent() instead.

        Args:
            question: User question or instruction
            user: User identifier
            state: Optional state dictionary for conversation context
            group: Optional group identifier for session management
            history: Optional conversation history list
            **kwargs: Additional service-specific parameters

        Returns:
            dict: Complete agent response including answer and metadata

        Example:
            ```python
            async_flow = await api.async_flow()
            flow = async_flow.id("default")

            # Execute agent
            result = await flow.agent(
                question="What is the capital of France?",
                user="trustgraph"
            )
            print(f"Answer: {result.get('response')}")
            ```
        """
        request_data = {
            "question": question,
            "user": user,
            "streaming": False  # REST doesn't support streaming
        }
        if state is not None:
            request_data["state"] = state
        if group is not None:
            request_data["group"] = group
        if history is not None:
            request_data["history"] = history
        request_data.update(kwargs)

        return await self.request("agent", request_data)

    async def text_completion(self, system: str, prompt: str, **kwargs: Any) -> str:
        """
        Generate text completion (non-streaming).

        Generates a text response from an LLM given a system prompt and user prompt.
        Returns the complete response text.

        Note: This method does not support streaming. For streaming text generation,
        use AsyncSocketFlowInstance.text_completion() instead.

        Args:
            system: System prompt defining the LLM's behavior
            prompt: User prompt or question
            **kwargs: Additional service-specific parameters

        Returns:
            str: Complete generated text response

        Example:
            ```python
            async_flow = await api.async_flow()
            flow = async_flow.id("default")

            # Generate text
            response = await flow.text_completion(
                system="You are a helpful assistant.",
                prompt="Explain quantum computing in simple terms."
            )
            print(response)
            ```
        """
        request_data = {
            "system": system,
            "prompt": prompt,
            "streaming": False
        }
        request_data.update(kwargs)

        result = await self.request("text-completion", request_data)
        return result.get("response", "")

    async def graph_rag(self, query: str, user: str, collection: str,
                        max_subgraph_size: int = 1000, max_subgraph_count: int = 5,
                        max_entity_distance: int = 3, **kwargs: Any) -> str:
        """
        Execute graph-based RAG query (non-streaming).

        Performs Retrieval-Augmented Generation using knowledge graph data.
        Identifies relevant entities and their relationships, then generates a
        response grounded in the graph structure. Returns complete response.

        Note: This method does not support streaming. For streaming RAG responses,
        use AsyncSocketFlowInstance.graph_rag() instead.

        Args:
            query: User query text
            user: User identifier
            collection: Collection identifier containing the knowledge graph
            max_subgraph_size: Maximum number of triples per subgraph (default: 1000)
            max_subgraph_count: Maximum number of subgraphs to retrieve (default: 5)
            max_entity_distance: Maximum graph distance for entity expansion (default: 3)
            **kwargs: Additional service-specific parameters

        Returns:
            str: Complete generated response grounded in graph data

        Example:
            ```python
            async_flow = await api.async_flow()
            flow = async_flow.id("default")

            # Query knowledge graph
            response = await flow.graph_rag(
                query="What are the relationships between these entities?",
                user="trustgraph",
                collection="medical-kb",
                max_subgraph_count=3
            )
            print(response)
            ```
        """
        request_data = {
            "query": query,
            "user": user,
            "collection": collection,
            "max-subgraph-size": max_subgraph_size,
            "max-subgraph-count": max_subgraph_count,
            "max-entity-distance": max_entity_distance,
            "streaming": False
        }
        request_data.update(kwargs)

        result = await self.request("graph-rag", request_data)
        return result.get("response", "")

    async def document_rag(self, query: str, user: str, collection: str,
                           doc_limit: int = 10, **kwargs: Any) -> str:
        """
        Execute document-based RAG query (non-streaming).

        Performs Retrieval-Augmented Generation using document embeddings.
        Retrieves relevant document chunks via semantic search, then generates
        a response grounded in the retrieved documents. Returns complete response.

        Note: This method does not support streaming. For streaming RAG responses,
        use AsyncSocketFlowInstance.document_rag() instead.

        Args:
            query: User query text
            user: User identifier
            collection: Collection identifier containing documents
            doc_limit: Maximum number of document chunks to retrieve (default: 10)
            **kwargs: Additional service-specific parameters

        Returns:
            str: Complete generated response grounded in document data

        Example:
            ```python
            async_flow = await api.async_flow()
            flow = async_flow.id("default")

            # Query documents
            response = await flow.document_rag(
                query="What does the documentation say about authentication?",
                user="trustgraph",
                collection="docs",
                doc_limit=5
            )
            print(response)
            ```
        """
        request_data = {
            "query": query,
            "user": user,
            "collection": collection,
            "doc-limit": doc_limit,
            "streaming": False
        }
        request_data.update(kwargs)

        result = await self.request("document-rag", request_data)
        return result.get("response", "")

    async def graph_embeddings_query(self, text: str, user: str, collection: str, limit: int = 10, **kwargs: Any):
        """
        Query graph embeddings for semantic entity search.

        Performs semantic search over graph entity embeddings to find entities
        most relevant to the input text. Returns entities ranked by similarity.

        Args:
            text: Query text for semantic search
            user: User identifier
            collection: Collection identifier containing graph embeddings
            limit: Maximum number of results to return (default: 10)
            **kwargs: Additional service-specific parameters

        Returns:
            dict: Response containing ranked entity matches with similarity scores

        Example:
            ```python
            async_flow = await api.async_flow()
            flow = async_flow.id("default")

            # Find related entities
            results = await flow.graph_embeddings_query(
                text="machine learning algorithms",
                user="trustgraph",
                collection="tech-kb",
                limit=5
            )

            for entity in results.get("entities", []):
                print(f"{entity['name']}: {entity['score']}")
            ```
        """
        request_data = {
            "text": text,
            "user": user,
            "collection": collection,
            "limit": limit
        }
        request_data.update(kwargs)

        return await self.request("graph-embeddings", request_data)

    async def embeddings(self, text: str, **kwargs: Any):
        """
        Generate embeddings for input text.

        Converts text into a numerical vector representation using the flow's
        configured embedding model. Useful for semantic search and similarity
        comparisons.

        Args:
            text: Input text to embed
            **kwargs: Additional service-specific parameters

        Returns:
            dict: Response containing embedding vector and metadata

        Example:
            ```python
            async_flow = await api.async_flow()
            flow = async_flow.id("default")

            # Generate embeddings
            result = await flow.embeddings(text="Sample text to embed")
            vector = result.get("embedding")
            print(f"Embedding dimension: {len(vector)}")
            ```
        """
        request_data = {"text": text}
        request_data.update(kwargs)

        return await self.request("embeddings", request_data)

    async def triples_query(self, s=None, p=None, o=None, user=None, collection=None, limit=100, **kwargs: Any):
        """
        Query RDF triples using pattern matching.

        Searches for triples matching the specified subject, predicate, and/or
        object patterns. Patterns use None as a wildcard to match any value.

        Args:
            s: Subject pattern (None for wildcard)
            p: Predicate pattern (None for wildcard)
            o: Object pattern (None for wildcard)
            user: User identifier (None for all users)
            collection: Collection identifier (None for all collections)
            limit: Maximum number of triples to return (default: 100)
            **kwargs: Additional service-specific parameters

        Returns:
            dict: Response containing matching triples

        Example:
            ```python
            async_flow = await api.async_flow()
            flow = async_flow.id("default")

            # Find all triples with a specific predicate
            results = await flow.triples_query(
                p="knows",
                user="trustgraph",
                collection="social",
                limit=50
            )

            for triple in results.get("triples", []):
                print(f"{triple['s']} knows {triple['o']}")
            ```
        """
        request_data = {"limit": limit}
        if s is not None:
            request_data["s"] = str(s)
        if p is not None:
            request_data["p"] = str(p)
        if o is not None:
            request_data["o"] = str(o)
        if user is not None:
            request_data["user"] = user
        if collection is not None:
            request_data["collection"] = collection
        request_data.update(kwargs)

        return await self.request("triples", request_data)

    async def objects_query(self, query: str, user: str, collection: str, variables: Optional[Dict] = None,
                            operation_name: Optional[str] = None, **kwargs: Any):
        """
        Execute a GraphQL query on stored objects.

        Queries structured data objects using GraphQL syntax. Supports complex
        queries with variables and named operations.

        Args:
            query: GraphQL query string
            user: User identifier
            collection: Collection identifier containing objects
            variables: Optional GraphQL query variables
            operation_name: Optional operation name for multi-operation queries
            **kwargs: Additional service-specific parameters

        Returns:
            dict: GraphQL response with data and/or errors

        Example:
            ```python
            async_flow = await api.async_flow()
            flow = async_flow.id("default")

            # Execute GraphQL query
            query = '''
                query GetUsers($status: String!) {
                    users(status: $status) {
                        id
                        name
                        email
                    }
                }
            '''

            result = await flow.objects_query(
                query=query,
                user="trustgraph",
                collection="users",
                variables={"status": "active"}
            )

            for user in result.get("data", {}).get("users", []):
                print(f"{user['name']}: {user['email']}")
            ```
        """
        request_data = {
            "query": query,
            "user": user,
            "collection": collection
        }
        if variables:
            request_data["variables"] = variables
        if operation_name:
            request_data["operationName"] = operation_name
        request_data.update(kwargs)

        return await self.request("objects", request_data)
