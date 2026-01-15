# TrustGraph Python API Reference

## Installation

```bash
pip install trustgraph
```

## Quick Start

All classes and types are imported from the `trustgraph.api` package:

```python
from trustgraph.api import Api, Triple, ConfigKey

# Create API client
api = Api(url="http://localhost:8088/")

# Get a flow instance
flow = api.flow().id("default")

# Execute a graph RAG query
response = flow.graph_rag(
    query="What are the main topics?",
    user="trustgraph",
    collection="default"
)
```

## Table of Contents

### Core

- [Api](#api)

### Flow Clients

- [Flow](#flow)
- [FlowInstance](#flowinstance)
- [AsyncFlow](#asyncflow)
- [AsyncFlowInstance](#asyncflowinstance)

### WebSocket Clients

- [SocketClient](#socketclient)
- [SocketFlowInstance](#socketflowinstance)
- [AsyncSocketClient](#asyncsocketclient)
- [AsyncSocketFlowInstance](#asyncsocketflowinstance)

### Bulk Operations

- [BulkClient](#bulkclient)
- [AsyncBulkClient](#asyncbulkclient)

### Metrics

- [Metrics](#metrics)
- [AsyncMetrics](#asyncmetrics)

### Data Types

- [Triple](#triple)
- [ConfigKey](#configkey)
- [ConfigValue](#configvalue)
- [DocumentMetadata](#documentmetadata)
- [ProcessingMetadata](#processingmetadata)
- [CollectionMetadata](#collectionmetadata)
- [StreamingChunk](#streamingchunk)
- [AgentThought](#agentthought)
- [AgentObservation](#agentobservation)
- [AgentAnswer](#agentanswer)
- [RAGChunk](#ragchunk)

### Exceptions

- [ProtocolException](#protocolexception)
- [TrustGraphException](#trustgraphexception)
- [AgentError](#agenterror)
- [ConfigError](#configerror)
- [DocumentRagError](#documentragerror)
- [FlowError](#flowerror)
- [GatewayError](#gatewayerror)
- [GraphRagError](#graphragerror)
- [LLMError](#llmerror)
- [LoadError](#loaderror)
- [LookupError](#lookuperror)
- [NLPQueryError](#nlpqueryerror)
- [ObjectsQueryError](#objectsqueryerror)
- [RequestError](#requesterror)
- [StructuredQueryError](#structuredqueryerror)
- [UnexpectedError](#unexpectederror)
- [ApplicationException](#applicationexception)

---

## `Api`

```python
from trustgraph.api import Api
```

Main TrustGraph API client for synchronous and asynchronous operations.

This class provides access to all TrustGraph services including flow management,
knowledge graph operations, document processing, RAG queries, and more. It supports
both REST-based and WebSocket-based communication patterns.

The client can be used as a context manager for automatic resource cleanup:
    ```python
    with Api(url="http://localhost:8088/") as api:
        result = api.flow().id("default").graph_rag(query="test")
    ```

### Methods

### `__aenter__(self)`

Enter asynchronous context manager.

### `__aexit__(self, *args)`

Exit asynchronous context manager and close connections.

### `__enter__(self)`

Enter synchronous context manager.

### `__exit__(self, *args)`

Exit synchronous context manager and close connections.

### `__init__(self, url='http://localhost:8088/', timeout=60, token: Optional[str] = None)`

Initialize the TrustGraph API client.

**Arguments:**

- `url`: Base URL for TrustGraph API (default: "http://localhost:8088/")
- `timeout`: Request timeout in seconds (default: 60)
- `token`: Optional bearer token for authentication

**Example:**

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

### `aclose(self)`

Close all asynchronous client connections.

This method closes async WebSocket, bulk operation, and flow connections.
It is automatically called when exiting an async context manager.

**Example:**

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

### `async_bulk(self)`

Get an asynchronous bulk operations client.

Provides async/await style bulk import/export operations via WebSocket
for efficient handling of large datasets.

**Returns:** AsyncBulkClient: Asynchronous bulk operations client

**Example:**

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

### `async_flow(self)`

Get an asynchronous REST-based flow client.

Provides async/await style access to flow operations. This is preferred
for async Python applications and frameworks (FastAPI, aiohttp, etc.).

**Returns:** AsyncFlow: Asynchronous flow client

**Example:**

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

### `async_metrics(self)`

Get an asynchronous metrics client.

Provides async/await style access to Prometheus metrics.

**Returns:** AsyncMetrics: Asynchronous metrics client

**Example:**

    ```python
    async_metrics = api.async_metrics()
    prometheus_text = await async_metrics.get()
    print(prometheus_text)
    ```

### `async_socket(self)`

Get an asynchronous WebSocket client for streaming operations.

Provides async/await style WebSocket access with streaming support.
This is the preferred method for async streaming in Python.

**Returns:** AsyncSocketClient: Asynchronous WebSocket client

**Example:**

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

### `bulk(self)`

Get a synchronous bulk operations client for import/export.

Bulk operations allow efficient transfer of large datasets via WebSocket
connections, including triples, embeddings, entity contexts, and objects.

**Returns:** BulkClient: Synchronous bulk operations client

**Example:**

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

### `close(self)`

Close all synchronous client connections.

This method closes WebSocket and bulk operation connections.
It is automatically called when exiting a context manager.

**Example:**

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

### `collection(self)`

Get a Collection client for managing data collections.

Collections organize documents and knowledge graph data into
logical groupings for isolation and access control.

**Returns:** Collection: Collection management client

**Example:**

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

### `config(self)`

Get a Config client for managing configuration settings.

**Returns:** Config: Configuration management client

**Example:**

    ```python
    config = api.config()

    # Get configuration values
    values = config.get([ConfigKey(type="llm", key="model")])

    # Set configuration
    config.put([ConfigValue(type="llm", key="model", value="gpt-4")])
    ```

### `flow(self)`

Get a Flow client for managing and interacting with flows.

Flows are the primary execution units in TrustGraph, providing access to
services like agents, RAG queries, embeddings, and document processing.

**Returns:** Flow: Flow management client

**Example:**

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

### `knowledge(self)`

Get a Knowledge client for managing knowledge graph cores.

**Returns:** Knowledge: Knowledge graph management client

**Example:**

    ```python
    knowledge = api.knowledge()

    # List available KG cores
    cores = knowledge.list_kg_cores(user="trustgraph")

    # Load a KG core
    knowledge.load_kg_core(id="core-123", user="trustgraph")
    ```

### `library(self)`

Get a Library client for document management.

The library provides document storage, metadata management, and
processing workflow coordination.

**Returns:** Library: Document library management client

**Example:**

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

### `metrics(self)`

Get a synchronous metrics client for monitoring.

Retrieves Prometheus-formatted metrics from the TrustGraph service
for monitoring and observability.

**Returns:** Metrics: Synchronous metrics client

**Example:**

    ```python
    metrics = api.metrics()
    prometheus_text = metrics.get()
    print(prometheus_text)
    ```

### `request(self, path, request)`

Make a low-level REST API request.

This method is primarily for internal use but can be used for direct
API access when needed.

**Arguments:**

- `path`: API endpoint path (relative to base URL)
- `request`: Request payload as a dictionary

**Returns:** dict: Response object

**Raises:**

- `ProtocolException`: If the response status is not 200 or response is not JSON
- `ApplicationException`: If the response contains an error

**Example:**

    ```python
    response = api.request("flow", {
        "operation": "list-flows"
    })
    ```

### `socket(self)`

Get a synchronous WebSocket client for streaming operations.

WebSocket connections provide streaming support for real-time responses
from agents, RAG queries, and text completions. This method returns a
synchronous wrapper around the WebSocket protocol.

**Returns:** SocketClient: Synchronous WebSocket client

**Example:**

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


---

## `Flow`

```python
from trustgraph.api import Flow
```

Flow management client for blueprint and flow instance operations.

This class provides methods for managing flow blueprints (templates) and
flow instances (running flows). Blueprints define the structure and
parameters of flows, while instances represent active flows that can
execute services.

### Methods

### `__init__(self, api)`

Initialize Flow client.

**Arguments:**

- `api`: Parent Api instance for making requests

### `delete_blueprint(self, blueprint_name)`

Delete a flow blueprint.

**Arguments:**

- `blueprint_name`: Name of the blueprint to delete

**Example:**

    ```python
    api.flow().delete_blueprint("old-blueprint")
    ```

### `get(self, id)`

Get the definition of a running flow instance.

**Arguments:**

- `id`: Flow instance ID

**Returns:** dict: Flow instance definition

**Example:**

    ```python
    flow_def = api.flow().get("default")
    print(flow_def)
    ```

### `get_blueprint(self, blueprint_name)`

Get a flow blueprint definition by name.

**Arguments:**

- `blueprint_name`: Name of the blueprint to retrieve

**Returns:** dict: Blueprint definition as a dictionary

**Example:**

    ```python
    blueprint = api.flow().get_blueprint("default")
    print(blueprint)  # Blueprint configuration
    ```

### `id(self, id='default')`

Get a FlowInstance for executing operations on a specific flow.

**Arguments:**

- `id`: Flow identifier (default: "default")

**Returns:** FlowInstance: Flow instance for service operations

**Example:**

    ```python
    flow = api.flow().id("my-flow")
    response = flow.text_completion(
        system="You are helpful",
        prompt="Hello"
    )
    ```

### `list(self)`

List all active flow instances.

**Returns:** list[str]: List of flow instance IDs

**Example:**

    ```python
    flows = api.flow().list()
    print(flows)  # ['default', 'flow-1', 'flow-2', ...]
    ```

### `list_blueprints(self)`

List all available flow blueprints.

**Returns:** list[str]: List of blueprint names

**Example:**

    ```python
    blueprints = api.flow().list_blueprints()
    print(blueprints)  # ['default', 'custom-flow', ...]
    ```

### `put_blueprint(self, blueprint_name, definition)`

Create or update a flow blueprint.

**Arguments:**

- `blueprint_name`: Name for the blueprint
- `definition`: Blueprint definition dictionary

**Example:**

    ```python
    definition = {
        "services": ["text-completion", "graph-rag"],
        "parameters": {"model": "gpt-4"}
    }
    api.flow().put_blueprint("my-blueprint", definition)
    ```

### `request(self, path=None, request=None)`

Make a flow-scoped API request.

**Arguments:**

- `path`: Optional path suffix for flow endpoints
- `request`: Request payload dictionary

**Returns:** dict: Response object

**Raises:**

- `RuntimeError`: If request parameter is not specified

### `start(self, blueprint_name, id, description, parameters=None)`

Start a new flow instance from a blueprint.

**Arguments:**

- `blueprint_name`: Name of the blueprint to instantiate
- `id`: Unique identifier for the flow instance
- `description`: Human-readable description
- `parameters`: Optional parameters dictionary

**Example:**

    ```python
    api.flow().start(
        blueprint_name="default",
        id="my-flow",
        description="My custom flow",
        parameters={"model": "gpt-4"}
    )
    ```

### `stop(self, id)`

Stop a running flow instance.

**Arguments:**

- `id`: Flow instance ID to stop

**Example:**

    ```python
    api.flow().stop("my-flow")
    ```


---

## `FlowInstance`

```python
from trustgraph.api import FlowInstance
```

Flow instance client for executing services on a specific flow.

This class provides access to all TrustGraph services including:
- Text completion and embeddings
- Agent operations with state management
- Graph and document RAG queries
- Knowledge graph operations (triples, objects)
- Document loading and processing
- Natural language to GraphQL query conversion
- Structured data analysis and schema detection
- MCP tool execution
- Prompt templating

Services are accessed through a running flow instance identified by ID.

### Methods

### `__init__(self, api, id)`

Initialize FlowInstance.

**Arguments:**

- `api`: Parent Flow client
- `id`: Flow instance identifier

### `agent(self, question, user='trustgraph', state=None, group=None, history=None)`

Execute an agent operation with reasoning and tool use capabilities.

Agents can perform multi-step reasoning, use tools, and maintain conversation
state across interactions. This is a synchronous non-streaming version.

**Arguments:**

- `question`: User question or instruction
- `user`: User identifier (default: "trustgraph")
- `state`: Optional state dictionary for stateful conversations
- `group`: Optional group identifier for multi-user contexts
- `history`: Optional conversation history as list of message dicts

**Returns:** str: Agent's final answer

**Example:**

    ```python
    flow = api.flow().id("default")

    # Simple question
    answer = flow.agent(
        question="What is the capital of France?",
        user="trustgraph"
    )

    # With conversation history
    history = [
        {"role": "user", "content": "Hello"},
        {"role": "assistant", "content": "Hi! How can I help?"}
    ]
    answer = flow.agent(
        question="Tell me about Paris",
        user="trustgraph",
        history=history
    )
    ```

### `detect_type(self, sample)`

Detect the data type of a structured data sample.

**Arguments:**

- `sample`: Data sample to analyze (string content)

**Returns:** dict with detected_type, confidence, and optional metadata

### `diagnose_data(self, sample, schema_name=None, options=None)`

Perform combined data diagnosis: detect type and generate descriptor.

**Arguments:**

- `sample`: Data sample to analyze (string content)
- `schema_name`: Optional target schema name for descriptor generation
- `options`: Optional parameters (e.g., delimiter for CSV)

**Returns:** dict with detected_type, confidence, descriptor, and metadata

### `document_rag(self, query, user='trustgraph', collection='default', doc_limit=10)`

Execute document-based Retrieval-Augmented Generation (RAG) query.

Document RAG uses vector embeddings to find relevant document chunks,
then generates a response using an LLM with those chunks as context.

**Arguments:**

- `query`: Natural language query
- `user`: User/keyspace identifier (default: "trustgraph")
- `collection`: Collection identifier (default: "default")
- `doc_limit`: Maximum document chunks to retrieve (default: 10)

**Returns:** str: Generated response incorporating document context

**Example:**

    ```python
    flow = api.flow().id("default")
    response = flow.document_rag(
        query="Summarize the key findings",
        user="trustgraph",
        collection="research-papers",
        doc_limit=5
    )
    print(response)
    ```

### `embeddings(self, text)`

Generate vector embeddings for text.

Converts text into dense vector representations suitable for semantic
search and similarity comparison.

**Arguments:**

- `text`: Input text to embed

**Returns:** list[float]: Vector embedding

**Example:**

    ```python
    flow = api.flow().id("default")
    vectors = flow.embeddings("quantum computing")
    print(f"Embedding dimension: {len(vectors)}")
    ```

### `generate_descriptor(self, sample, data_type, schema_name, options=None)`

Generate a descriptor for structured data mapping to a specific schema.

**Arguments:**

- `sample`: Data sample to analyze (string content)
- `data_type`: Data type (csv, json, xml)
- `schema_name`: Target schema name for descriptor generation
- `options`: Optional parameters (e.g., delimiter for CSV)

**Returns:** dict with descriptor and metadata

### `graph_embeddings_query(self, text, user, collection, limit=10)`

Query knowledge graph entities using semantic similarity.

Finds entities in the knowledge graph whose descriptions are semantically
similar to the input text, using vector embeddings.

**Arguments:**

- `text`: Query text for semantic search
- `user`: User/keyspace identifier
- `collection`: Collection identifier
- `limit`: Maximum number of results (default: 10)

**Returns:** dict: Query results with similar entities

**Example:**

    ```python
    flow = api.flow().id("default")
    results = flow.graph_embeddings_query(
        text="physicist who discovered radioactivity",
        user="trustgraph",
        collection="scientists",
        limit=5
    )
    ```

### `graph_rag(self, query, user='trustgraph', collection='default', entity_limit=50, triple_limit=30, max_subgraph_size=150, max_path_length=2)`

Execute graph-based Retrieval-Augmented Generation (RAG) query.

Graph RAG uses knowledge graph structure to find relevant context by
traversing entity relationships, then generates a response using an LLM.

**Arguments:**

- `query`: Natural language query
- `user`: User/keyspace identifier (default: "trustgraph")
- `collection`: Collection identifier (default: "default")
- `entity_limit`: Maximum entities to retrieve (default: 50)
- `triple_limit`: Maximum triples per entity (default: 30)
- `max_subgraph_size`: Maximum total triples in subgraph (default: 150)
- `max_path_length`: Maximum traversal depth (default: 2)

**Returns:** str: Generated response incorporating graph context

**Example:**

    ```python
    flow = api.flow().id("default")
    response = flow.graph_rag(
        query="Tell me about Marie Curie's discoveries",
        user="trustgraph",
        collection="scientists",
        entity_limit=20,
        max_path_length=3
    )
    print(response)
    ```

### `load_document(self, document, id=None, metadata=None, user=None, collection=None)`

Load a binary document for processing.

Uploads a document (PDF, DOCX, images, etc.) for extraction and
processing through the flow's document pipeline.

**Arguments:**

- `document`: Document content as bytes
- `id`: Optional document identifier (auto-generated if None)
- `metadata`: Optional metadata (list of Triples or object with emit method)
- `user`: User/keyspace identifier (optional)
- `collection`: Collection identifier (optional)

**Returns:** dict: Processing response

**Raises:**

- `RuntimeError`: If metadata is provided without id

**Example:**

    ```python
    flow = api.flow().id("default")

    # Load a PDF document
    with open("research.pdf", "rb") as f:
        result = flow.load_document(
            document=f.read(),
            id="research-001",
            user="trustgraph",
            collection="papers"
        )
    ```

### `load_text(self, text, id=None, metadata=None, charset='utf-8', user=None, collection=None)`

Load text content for processing.

Uploads text content for extraction and processing through the flow's
text pipeline.

**Arguments:**

- `text`: Text content as bytes
- `id`: Optional document identifier (auto-generated if None)
- `metadata`: Optional metadata (list of Triples or object with emit method)
- `charset`: Character encoding (default: "utf-8")
- `user`: User/keyspace identifier (optional)
- `collection`: Collection identifier (optional)

**Returns:** dict: Processing response

**Raises:**

- `RuntimeError`: If metadata is provided without id

**Example:**

    ```python
    flow = api.flow().id("default")

    # Load text content
    text_content = b"This is the document content..."
    result = flow.load_text(
        text=text_content,
        id="text-001",
        charset="utf-8",
        user="trustgraph",
        collection="documents"
    )
    ```

### `mcp_tool(self, name, parameters={})`

Execute a Model Context Protocol (MCP) tool.

MCP tools provide extensible functionality for agents and workflows,
allowing integration with external systems and services.

**Arguments:**

- `name`: Tool name/identifier
- `parameters`: Tool parameters dictionary (default: {})

**Returns:** str or dict: Tool execution result

**Raises:**

- `ProtocolException`: If response format is invalid

**Example:**

    ```python
    flow = api.flow().id("default")

    # Execute a tool
    result = flow.mcp_tool(
        name="search-web",
        parameters={"query": "latest AI news", "limit": 5}
    )
    ```

### `nlp_query(self, question, max_results=100)`

Convert a natural language question to a GraphQL query.

**Arguments:**

- `question`: Natural language question
- `max_results`: Maximum number of results to return (default: 100)

**Returns:** dict with graphql_query, variables, detected_schemas, confidence

### `objects_query(self, query, user='trustgraph', collection='default', variables=None, operation_name=None)`

Execute a GraphQL query against structured objects in the knowledge graph.

Queries structured data using GraphQL syntax, allowing complex queries
with filtering, aggregation, and relationship traversal.

**Arguments:**

- `query`: GraphQL query string
- `user`: User/keyspace identifier (default: "trustgraph")
- `collection`: Collection identifier (default: "default")
- `variables`: Optional query variables dictionary
- `operation_name`: Optional operation name for multi-operation documents

**Returns:** dict: GraphQL response with 'data', 'errors', and/or 'extensions' fields

**Raises:**

- `ProtocolException`: If system-level error occurs

**Example:**

    ```python
    flow = api.flow().id("default")

    # Simple query
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

    # Query with variables
    query = '''
    query GetScientist($name: String!) {
      scientists(name: $name) {
        name
        nobelPrizes
      }
    }
    '''
    result = flow.objects_query(
        query=query,
        variables={"name": "Marie Curie"}
    )
    ```

### `prompt(self, id, variables)`

Execute a prompt template with variable substitution.

Prompt templates allow reusable prompt patterns with dynamic variable
substitution, useful for consistent prompt engineering.

**Arguments:**

- `id`: Prompt template identifier
- `variables`: Dictionary of variable name to value mappings

**Returns:** str or dict: Rendered prompt result (text or structured object)

**Raises:**

- `ProtocolException`: If response format is invalid

**Example:**

    ```python
    flow = api.flow().id("default")

    # Text template
    result = flow.prompt(
        id="summarize-template",
        variables={"topic": "quantum computing", "length": "brief"}
    )

    # Structured template
    result = flow.prompt(
        id="extract-entities",
        variables={"text": "Marie Curie won Nobel Prizes"}
    )
    ```

### `request(self, path, request)`

Make a service request on this flow instance.

**Arguments:**

- `path`: Service path (e.g., "service/text-completion")
- `request`: Request payload dictionary

**Returns:** dict: Service response

### `schema_selection(self, sample, options=None)`

Select matching schemas for a data sample using prompt analysis.

**Arguments:**

- `sample`: Data sample to analyze (string content)
- `options`: Optional parameters

**Returns:** dict with schema_matches array and metadata

### `structured_query(self, question, user='trustgraph', collection='default')`

Execute a natural language question against structured data.
Combines NLP query conversion and GraphQL execution.

**Arguments:**

- `question`: Natural language question
- `user`: Cassandra keyspace identifier (default: "trustgraph")
- `collection`: Data collection identifier (default: "default")

**Returns:** dict with data and optional errors

### `text_completion(self, system, prompt)`

Execute text completion using the flow's LLM.

**Arguments:**

- `system`: System prompt defining the assistant's behavior
- `prompt`: User prompt/question

**Returns:** str: Generated response text

**Example:**

    ```python
    flow = api.flow().id("default")
    response = flow.text_completion(
        system="You are a helpful assistant",
        prompt="What is quantum computing?"
    )
    print(response)
    ```

### `triples_query(self, s=None, p=None, o=None, user=None, collection=None, limit=10000)`

Query knowledge graph triples using pattern matching.

Searches for RDF triples matching the given subject, predicate, and/or
object patterns. Unspecified parameters act as wildcards.

**Arguments:**

- `s`: Subject URI (optional, use None for wildcard)
- `p`: Predicate URI (optional, use None for wildcard)
- `o`: Object URI or Literal (optional, use None for wildcard)
- `user`: User/keyspace identifier (optional)
- `collection`: Collection identifier (optional)
- `limit`: Maximum results to return (default: 10000)

**Returns:** list[Triple]: List of matching Triple objects

**Raises:**

- `RuntimeError`: If s or p is not a Uri, or o is not Uri/Literal

**Example:**

    ```python
    from trustgraph.knowledge import Uri, Literal

    flow = api.flow().id("default")

    # Find all triples about a specific subject
    triples = flow.triples_query(
        s=Uri("http://example.org/person/marie-curie"),
        user="trustgraph",
        collection="scientists"
    )

    # Find all instances of a specific relationship
    triples = flow.triples_query(
        p=Uri("http://example.org/ontology/discovered"),
        limit=100
    )
    ```


---

## `AsyncFlow`

```python
from trustgraph.api import AsyncFlow
```

Asynchronous REST-based flow interface

### Methods

### `__init__(self, url: str, timeout: int, token: Optional[str]) -> None`

Initialize self.  See help(type(self)) for accurate signature.

### `aclose(self) -> None`

Close connection (cleanup handled by aiohttp session)

### `delete_class(self, class_name: str)`

Delete flow class

### `get(self, id: str) -> Dict[str, Any]`

Get flow definition

### `get_class(self, class_name: str) -> Dict[str, Any]`

Get flow class definition

### `id(self, flow_id: str)`

Get async flow instance

### `list(self) -> List[str]`

List all flows

### `list_classes(self) -> List[str]`

List flow classes

### `put_class(self, class_name: str, definition: Dict[str, Any])`

Create/update flow class

### `request(self, path: str, request_data: Dict[str, Any]) -> Dict[str, Any]`

Make async HTTP request to Gateway API

### `start(self, class_name: str, id: str, description: str, parameters: Optional[Dict] = None)`

Start a flow

### `stop(self, id: str)`

Stop a flow


---

## `AsyncFlowInstance`

```python
from trustgraph.api import AsyncFlowInstance
```

Asynchronous REST flow instance

### Methods

### `__init__(self, flow: trustgraph.api.async_flow.AsyncFlow, flow_id: str)`

Initialize self.  See help(type(self)) for accurate signature.

### `agent(self, question: str, user: str, state: Optional[Dict] = None, group: Optional[str] = None, history: Optional[List] = None, **kwargs: Any) -> Dict[str, Any]`

Execute agent (non-streaming, use async_socket for streaming)

### `document_rag(self, query: str, user: str, collection: str, doc_limit: int = 10, **kwargs: Any) -> str`

Document RAG (non-streaming, use async_socket for streaming)

### `embeddings(self, text: str, **kwargs: Any)`

Generate text embeddings

### `graph_embeddings_query(self, text: str, user: str, collection: str, limit: int = 10, **kwargs: Any)`

Query graph embeddings for semantic search

### `graph_rag(self, query: str, user: str, collection: str, max_subgraph_size: int = 1000, max_subgraph_count: int = 5, max_entity_distance: int = 3, **kwargs: Any) -> str`

Graph RAG (non-streaming, use async_socket for streaming)

### `objects_query(self, query: str, user: str, collection: str, variables: Optional[Dict] = None, operation_name: Optional[str] = None, **kwargs: Any)`

GraphQL query

### `request(self, service: str, request_data: Dict[str, Any]) -> Dict[str, Any]`

Make request to flow-scoped service

### `text_completion(self, system: str, prompt: str, **kwargs: Any) -> str`

Text completion (non-streaming, use async_socket for streaming)

### `triples_query(self, s=None, p=None, o=None, user=None, collection=None, limit=100, **kwargs: Any)`

Triple pattern query


---

## `SocketClient`

```python
from trustgraph.api import SocketClient
```

Synchronous WebSocket client (wraps async websockets library)

### Methods

### `__init__(self, url: str, timeout: int, token: Optional[str]) -> None`

Initialize self.  See help(type(self)) for accurate signature.

### `close(self) -> None`

Close WebSocket connection

### `flow(self, flow_id: str) -> 'SocketFlowInstance'`

Get flow instance for WebSocket operations


---

## `SocketFlowInstance`

```python
from trustgraph.api import SocketFlowInstance
```

Synchronous WebSocket flow instance with same interface as REST FlowInstance

### Methods

### `__init__(self, client: trustgraph.api.socket_client.SocketClient, flow_id: str) -> None`

Initialize self.  See help(type(self)) for accurate signature.

### `agent(self, question: str, user: str, state: Optional[Dict[str, Any]] = None, group: Optional[str] = None, history: Optional[List[Dict[str, Any]]] = None, streaming: bool = False, **kwargs: Any) -> Union[Dict[str, Any], Iterator[trustgraph.api.types.StreamingChunk]]`

Agent with optional streaming

### `document_rag(self, query: str, user: str, collection: str, doc_limit: int = 10, streaming: bool = False, **kwargs: Any) -> Union[str, Iterator[str]]`

Document RAG with optional streaming

### `embeddings(self, text: str, **kwargs: Any) -> Dict[str, Any]`

Generate text embeddings

### `graph_embeddings_query(self, text: str, user: str, collection: str, limit: int = 10, **kwargs: Any) -> Dict[str, Any]`

Query graph embeddings for semantic search

### `graph_rag(self, query: str, user: str, collection: str, max_subgraph_size: int = 1000, max_subgraph_count: int = 5, max_entity_distance: int = 3, streaming: bool = False, **kwargs: Any) -> Union[str, Iterator[str]]`

Graph RAG with optional streaming

### `mcp_tool(self, name: str, parameters: Dict[str, Any], **kwargs: Any) -> Dict[str, Any]`

Execute MCP tool

### `objects_query(self, query: str, user: str, collection: str, variables: Optional[Dict[str, Any]] = None, operation_name: Optional[str] = None, **kwargs: Any) -> Dict[str, Any]`

GraphQL query

### `prompt(self, id: str, variables: Dict[str, str], streaming: bool = False, **kwargs: Any) -> Union[str, Iterator[str]]`

Execute prompt with optional streaming

### `text_completion(self, system: str, prompt: str, streaming: bool = False, **kwargs) -> Union[str, Iterator[str]]`

Text completion with optional streaming

### `triples_query(self, s: Optional[str] = None, p: Optional[str] = None, o: Optional[str] = None, user: Optional[str] = None, collection: Optional[str] = None, limit: int = 100, **kwargs: Any) -> Dict[str, Any]`

Triple pattern query


---

## `AsyncSocketClient`

```python
from trustgraph.api import AsyncSocketClient
```

Asynchronous WebSocket client

### Methods

### `__init__(self, url: str, timeout: int, token: Optional[str])`

Initialize self.  See help(type(self)) for accurate signature.

### `aclose(self)`

Close WebSocket connection

### `flow(self, flow_id: str)`

Get async flow instance for WebSocket operations


---

## `AsyncSocketFlowInstance`

```python
from trustgraph.api import AsyncSocketFlowInstance
```

Asynchronous WebSocket flow instance

### Methods

### `__init__(self, client: trustgraph.api.async_socket_client.AsyncSocketClient, flow_id: str)`

Initialize self.  See help(type(self)) for accurate signature.

### `agent(self, question: str, user: str, state: Optional[Dict[str, Any]] = None, group: Optional[str] = None, history: Optional[list] = None, streaming: bool = False, **kwargs) -> Union[Dict[str, Any], AsyncIterator]`

Agent with optional streaming

### `document_rag(self, query: str, user: str, collection: str, doc_limit: int = 10, streaming: bool = False, **kwargs)`

Document RAG with optional streaming

### `embeddings(self, text: str, **kwargs)`

Generate text embeddings

### `graph_embeddings_query(self, text: str, user: str, collection: str, limit: int = 10, **kwargs)`

Query graph embeddings for semantic search

### `graph_rag(self, query: str, user: str, collection: str, max_subgraph_size: int = 1000, max_subgraph_count: int = 5, max_entity_distance: int = 3, streaming: bool = False, **kwargs)`

Graph RAG with optional streaming

### `mcp_tool(self, name: str, parameters: Dict[str, Any], **kwargs)`

Execute MCP tool

### `objects_query(self, query: str, user: str, collection: str, variables: Optional[Dict] = None, operation_name: Optional[str] = None, **kwargs)`

GraphQL query

### `prompt(self, id: str, variables: Dict[str, str], streaming: bool = False, **kwargs)`

Execute prompt with optional streaming

### `text_completion(self, system: str, prompt: str, streaming: bool = False, **kwargs)`

Text completion with optional streaming

### `triples_query(self, s=None, p=None, o=None, user=None, collection=None, limit=100, **kwargs)`

Triple pattern query


---

## `BulkClient`

```python
from trustgraph.api import BulkClient
```

Synchronous bulk operations client

### Methods

### `__init__(self, url: str, timeout: int, token: Optional[str]) -> None`

Initialize self.  See help(type(self)) for accurate signature.

### `close(self) -> None`

Close connections

### `export_document_embeddings(self, flow: str, **kwargs: Any) -> Iterator[Dict[str, Any]]`

Bulk export document embeddings via WebSocket

### `export_entity_contexts(self, flow: str, **kwargs: Any) -> Iterator[Dict[str, Any]]`

Bulk export entity contexts via WebSocket

### `export_graph_embeddings(self, flow: str, **kwargs: Any) -> Iterator[Dict[str, Any]]`

Bulk export graph embeddings via WebSocket

### `export_triples(self, flow: str, **kwargs: Any) -> Iterator[trustgraph.api.types.Triple]`

Bulk export triples via WebSocket

### `import_document_embeddings(self, flow: str, embeddings: Iterator[Dict[str, Any]], **kwargs: Any) -> None`

Bulk import document embeddings via WebSocket

### `import_entity_contexts(self, flow: str, contexts: Iterator[Dict[str, Any]], **kwargs: Any) -> None`

Bulk import entity contexts via WebSocket

### `import_graph_embeddings(self, flow: str, embeddings: Iterator[Dict[str, Any]], **kwargs: Any) -> None`

Bulk import graph embeddings via WebSocket

### `import_objects(self, flow: str, objects: Iterator[Dict[str, Any]], **kwargs: Any) -> None`

Bulk import objects via WebSocket

### `import_triples(self, flow: str, triples: Iterator[trustgraph.api.types.Triple], **kwargs: Any) -> None`

Bulk import triples via WebSocket


---

## `AsyncBulkClient`

```python
from trustgraph.api import AsyncBulkClient
```

Asynchronous bulk operations client

### Methods

### `__init__(self, url: str, timeout: int, token: Optional[str]) -> None`

Initialize self.  See help(type(self)) for accurate signature.

### `aclose(self) -> None`

Close connections

### `export_document_embeddings(self, flow: str, **kwargs: Any) -> AsyncIterator[Dict[str, Any]]`

Bulk export document embeddings via WebSocket

### `export_entity_contexts(self, flow: str, **kwargs: Any) -> AsyncIterator[Dict[str, Any]]`

Bulk export entity contexts via WebSocket

### `export_graph_embeddings(self, flow: str, **kwargs: Any) -> AsyncIterator[Dict[str, Any]]`

Bulk export graph embeddings via WebSocket

### `export_triples(self, flow: str, **kwargs: Any) -> AsyncIterator[trustgraph.api.types.Triple]`

Bulk export triples via WebSocket

### `import_document_embeddings(self, flow: str, embeddings: AsyncIterator[Dict[str, Any]], **kwargs: Any) -> None`

Bulk import document embeddings via WebSocket

### `import_entity_contexts(self, flow: str, contexts: AsyncIterator[Dict[str, Any]], **kwargs: Any) -> None`

Bulk import entity contexts via WebSocket

### `import_graph_embeddings(self, flow: str, embeddings: AsyncIterator[Dict[str, Any]], **kwargs: Any) -> None`

Bulk import graph embeddings via WebSocket

### `import_objects(self, flow: str, objects: AsyncIterator[Dict[str, Any]], **kwargs: Any) -> None`

Bulk import objects via WebSocket

### `import_triples(self, flow: str, triples: AsyncIterator[trustgraph.api.types.Triple], **kwargs: Any) -> None`

Bulk import triples via WebSocket


---

## `Metrics`

```python
from trustgraph.api import Metrics
```

Synchronous metrics client

### Methods

### `__init__(self, url: str, timeout: int, token: Optional[str]) -> None`

Initialize self.  See help(type(self)) for accurate signature.

### `get(self) -> str`

Get Prometheus metrics as text


---

## `AsyncMetrics`

```python
from trustgraph.api import AsyncMetrics
```

Asynchronous metrics client

### Methods

### `__init__(self, url: str, timeout: int, token: Optional[str]) -> None`

Initialize self.  See help(type(self)) for accurate signature.

### `aclose(self) -> None`

Close connections

### `get(self) -> str`

Get Prometheus metrics as text


---

## `Triple`

```python
from trustgraph.api import Triple
```

RDF triple representing a knowledge graph statement.

**Fields:**

- `s`: <class 'str'>
- `p`: <class 'str'>
- `o`: <class 'str'>

### Methods

### `__init__(self, s: str, p: str, o: str) -> None`

Initialize self.  See help(type(self)) for accurate signature.


---

## `ConfigKey`

```python
from trustgraph.api import ConfigKey
```

Configuration key identifier.

**Fields:**

- `type`: <class 'str'>
- `key`: <class 'str'>

### Methods

### `__init__(self, type: str, key: str) -> None`

Initialize self.  See help(type(self)) for accurate signature.


---

## `ConfigValue`

```python
from trustgraph.api import ConfigValue
```

Configuration key-value pair.

**Fields:**

- `type`: <class 'str'>
- `key`: <class 'str'>
- `value`: <class 'str'>

### Methods

### `__init__(self, type: str, key: str, value: str) -> None`

Initialize self.  See help(type(self)) for accurate signature.


---

## `DocumentMetadata`

```python
from trustgraph.api import DocumentMetadata
```

Metadata for a document in the library.

**Fields:**

- `id`: <class 'str'>
- `time`: <class 'datetime.datetime'>
- `kind`: <class 'str'>
- `title`: <class 'str'>
- `comments`: <class 'str'>
- `metadata`: typing.List[trustgraph.api.types.Triple]
- `user`: <class 'str'>
- `tags`: typing.List[str]

### Methods

### `__init__(self, id: str, time: datetime.datetime, kind: str, title: str, comments: str, metadata: List[trustgraph.api.types.Triple], user: str, tags: List[str]) -> None`

Initialize self.  See help(type(self)) for accurate signature.


---

## `ProcessingMetadata`

```python
from trustgraph.api import ProcessingMetadata
```

Metadata for an active document processing job.

**Fields:**

- `id`: <class 'str'>
- `document_id`: <class 'str'>
- `time`: <class 'datetime.datetime'>
- `flow`: <class 'str'>
- `user`: <class 'str'>
- `collection`: <class 'str'>
- `tags`: typing.List[str]

### Methods

### `__init__(self, id: str, document_id: str, time: datetime.datetime, flow: str, user: str, collection: str, tags: List[str]) -> None`

Initialize self.  See help(type(self)) for accurate signature.


---

## `CollectionMetadata`

```python
from trustgraph.api import CollectionMetadata
```

Metadata for a data collection.

Collections provide logical grouping and isolation for documents and
knowledge graph data.

**Attributes:**

- `name: Human`: readable collection name

**Fields:**

- `user`: <class 'str'>
- `collection`: <class 'str'>
- `name`: <class 'str'>
- `description`: <class 'str'>
- `tags`: typing.List[str]

### Methods

### `__init__(self, user: str, collection: str, name: str, description: str, tags: List[str]) -> None`

Initialize self.  See help(type(self)) for accurate signature.


---

## `StreamingChunk`

```python
from trustgraph.api import StreamingChunk
```

Base class for streaming response chunks.

Used for WebSocket-based streaming operations where responses are delivered
incrementally as they are generated.

**Fields:**

- `content`: <class 'str'>
- `end_of_message`: <class 'bool'>

### Methods

### `__init__(self, content: str, end_of_message: bool = False) -> None`

Initialize self.  See help(type(self)) for accurate signature.


---

## `AgentThought`

```python
from trustgraph.api import AgentThought
```

Agent reasoning/thought process chunk.

Represents the agent's internal reasoning or planning steps during execution.
These chunks show how the agent is thinking about the problem.

**Fields:**

- `content`: <class 'str'>
- `end_of_message`: <class 'bool'>
- `chunk_type`: <class 'str'>

### Methods

### `__init__(self, content: str, end_of_message: bool = False, chunk_type: str = 'thought') -> None`

Initialize self.  See help(type(self)) for accurate signature.


---

## `AgentObservation`

```python
from trustgraph.api import AgentObservation
```

Agent tool execution observation chunk.

Represents the result or observation from executing a tool or action.
These chunks show what the agent learned from using tools.

**Fields:**

- `content`: <class 'str'>
- `end_of_message`: <class 'bool'>
- `chunk_type`: <class 'str'>

### Methods

### `__init__(self, content: str, end_of_message: bool = False, chunk_type: str = 'observation') -> None`

Initialize self.  See help(type(self)) for accurate signature.


---

## `AgentAnswer`

```python
from trustgraph.api import AgentAnswer
```

Agent final answer chunk.

Represents the agent's final response to the user's query after completing
its reasoning and tool use.

**Attributes:**

- `chunk_type: Always "final`: answer"

**Fields:**

- `content`: <class 'str'>
- `end_of_message`: <class 'bool'>
- `chunk_type`: <class 'str'>
- `end_of_dialog`: <class 'bool'>

### Methods

### `__init__(self, content: str, end_of_message: bool = False, chunk_type: str = 'final-answer', end_of_dialog: bool = False) -> None`

Initialize self.  See help(type(self)) for accurate signature.


---

## `RAGChunk`

```python
from trustgraph.api import RAGChunk
```

RAG (Retrieval-Augmented Generation) streaming chunk.

Used for streaming responses from graph RAG, document RAG, text completion,
and other generative services.

**Fields:**

- `content`: <class 'str'>
- `end_of_message`: <class 'bool'>
- `chunk_type`: <class 'str'>
- `end_of_stream`: <class 'bool'>
- `error`: typing.Optional[typing.Dict[str, str]]

### Methods

### `__init__(self, content: str, end_of_message: bool = False, chunk_type: str = 'rag', end_of_stream: bool = False, error: Optional[Dict[str, str]] = None) -> None`

Initialize self.  See help(type(self)) for accurate signature.


---

## `ProtocolException`

```python
from trustgraph.api import ProtocolException
```

Raised when WebSocket protocol errors occur


---

## `TrustGraphException`

```python
from trustgraph.api import TrustGraphException
```

Base class for all TrustGraph service errors


---

## `AgentError`

```python
from trustgraph.api import AgentError
```

Agent service error


---

## `ConfigError`

```python
from trustgraph.api import ConfigError
```

Configuration service error


---

## `DocumentRagError`

```python
from trustgraph.api import DocumentRagError
```

Document RAG retrieval error


---

## `FlowError`

```python
from trustgraph.api import FlowError
```

Flow management error


---

## `GatewayError`

```python
from trustgraph.api import GatewayError
```

API Gateway error


---

## `GraphRagError`

```python
from trustgraph.api import GraphRagError
```

Graph RAG retrieval error


---

## `LLMError`

```python
from trustgraph.api import LLMError
```

LLM service error


---

## `LoadError`

```python
from trustgraph.api import LoadError
```

Data loading error


---

## `LookupError`

```python
from trustgraph.api import LookupError
```

Lookup/search error


---

## `NLPQueryError`

```python
from trustgraph.api import NLPQueryError
```

NLP query service error


---

## `ObjectsQueryError`

```python
from trustgraph.api import ObjectsQueryError
```

Objects query service error


---

## `RequestError`

```python
from trustgraph.api import RequestError
```

Request processing error


---

## `StructuredQueryError`

```python
from trustgraph.api import StructuredQueryError
```

Structured query service error


---

## `UnexpectedError`

```python
from trustgraph.api import UnexpectedError
```

Unexpected/unknown error


---

## `ApplicationException`

```python
from trustgraph.api import ApplicationException
```

Base class for all TrustGraph service errors


---

