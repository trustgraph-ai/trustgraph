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
- [RowsQueryError](#rowsqueryerror)
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

### `__init__(self, url='http://localhost:8088/', timeout=60, token: str | None = None)`

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

### `document_embeddings_query(self, text, user, collection, limit=10)`

Query document chunks using semantic similarity.

Finds document chunks whose content is semantically similar to the
input text, using vector embeddings.

**Arguments:**

- `text`: Query text for semantic search
- `user`: User/keyspace identifier
- `collection`: Collection identifier
- `limit`: Maximum number of results (default: 10)

**Returns:** dict: Query results with chunks containing chunk_id and score

**Example:**

```python
flow = api.flow().id("default")
results = flow.document_embeddings_query(
    text="machine learning algorithms",
    user="trustgraph",
    collection="research-papers",
    limit=5
)
# results contains {"chunks": [{"chunk_id": "doc1/p0/c0", "score": 0.95}, ...]}
```

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

### `embeddings(self, texts)`

Generate vector embeddings for one or more texts.

Converts texts into dense vector representations suitable for semantic
search and similarity comparison.

**Arguments:**

- `texts`: List of input texts to embed

**Returns:** list[list[list[float]]]: Vector embeddings, one set per input text

**Example:**

```python
flow = api.flow().id("default")
vectors = flow.embeddings(["quantum computing"])
print(f"Embedding dimension: {len(vectors[0][0])}")
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
# results contains {"entities": [{"entity": {...}, "score": 0.95}, ...]}
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

### `row_embeddings_query(self, text, schema_name, user='trustgraph', collection='default', index_name=None, limit=10)`

Query row data using semantic similarity on indexed fields.

Finds rows whose indexed field values are semantically similar to the
input text, using vector embeddings. This enables fuzzy/semantic matching
on structured data.

**Arguments:**

- `text`: Query text for semantic search
- `schema_name`: Schema name to search within
- `user`: User/keyspace identifier (default: "trustgraph")
- `collection`: Collection identifier (default: "default")
- `index_name`: Optional index name to filter search to specific index
- `limit`: Maximum number of results (default: 10)

**Returns:** dict: Query results with matches containing index_name, index_value, text, and score

**Example:**

```python
flow = api.flow().id("default")

# Search for customers by name similarity
results = flow.row_embeddings_query(
    text="John Smith",
    schema_name="customers",
    user="trustgraph",
    collection="sales",
    limit=5
)

# Filter to specific index
results = flow.row_embeddings_query(
    text="machine learning engineer",
    schema_name="employees",
    index_name="job_title",
    limit=10
)
```

### `rows_query(self, query, user='trustgraph', collection='default', variables=None, operation_name=None)`

Execute a GraphQL query against structured rows in the knowledge graph.

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
result = flow.rows_query(
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
result = flow.rows_query(
    query=query,
    variables={"name": "Marie Curie"}
)
```

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

Asynchronous flow management client using REST API.

Provides async/await based flow management operations including listing,
starting, stopping flows, and managing flow class definitions. Also provides
access to flow-scoped services like agents, RAG, and queries via non-streaming
REST endpoints.

Note: For streaming support, use AsyncSocketClient instead.

### Methods

### `__init__(self, url: str, timeout: int, token: str | None) -> None`

Initialize async flow client.

**Arguments:**

- `url`: Base URL for TrustGraph API
- `timeout`: Request timeout in seconds
- `token`: Optional bearer token for authentication

### `aclose(self) -> None`

Close async client and cleanup resources.

Note: Cleanup is handled automatically by aiohttp session context managers.
This method is provided for consistency with other async clients.

### `delete_class(self, class_name: str)`

Delete a flow class definition.

Removes a flow class blueprint from the system. Does not affect
running flow instances.

**Arguments:**

- `class_name`: Flow class name to delete

**Example:**

```python
async_flow = await api.async_flow()

# Delete a flow class
await async_flow.delete_class("old-flow-class")
```

### `get(self, id: str) -> Dict[str, Any]`

Get flow definition.

Retrieves the complete flow configuration including its class name,
description, and parameters.

**Arguments:**

- `id`: Flow identifier

**Returns:** dict: Flow definition object

**Example:**

```python
async_flow = await api.async_flow()

# Get flow definition
flow_def = await async_flow.get("default")
print(f"Flow class: {flow_def.get('class-name')}")
print(f"Description: {flow_def.get('description')}")
```

### `get_class(self, class_name: str) -> Dict[str, Any]`

Get flow class definition.

Retrieves the blueprint definition for a flow class, including its
configuration schema and service bindings.

**Arguments:**

- `class_name`: Flow class name

**Returns:** dict: Flow class definition object

**Example:**

```python
async_flow = await api.async_flow()

# Get flow class definition
class_def = await async_flow.get_class("default")
print(f"Services: {class_def.get('services')}")
```

### `id(self, flow_id: str)`

Get an async flow instance client.

Returns a client for interacting with a specific flow's services
(agent, RAG, queries, embeddings, etc.).

**Arguments:**

- `flow_id`: Flow identifier

**Returns:** AsyncFlowInstance: Client for flow-specific operations

**Example:**

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

### `list(self) -> List[str]`

List all flow identifiers.

Retrieves IDs of all flows currently deployed in the system.

**Returns:** list[str]: List of flow identifiers

**Example:**

```python
async_flow = await api.async_flow()

# List all flows
flows = await async_flow.list()
print(f"Available flows: {flows}")
```

### `list_classes(self) -> List[str]`

List all flow class names.

Retrieves names of all flow classes (blueprints) available in the system.

**Returns:** list[str]: List of flow class names

**Example:**

```python
async_flow = await api.async_flow()

# List available flow classes
classes = await async_flow.list_classes()
print(f"Available flow classes: {classes}")
```

### `put_class(self, class_name: str, definition: Dict[str, Any])`

Create or update a flow class definition.

Stores a flow class blueprint that can be used to instantiate flows.

**Arguments:**

- `class_name`: Flow class name
- `definition`: Flow class definition object

**Example:**

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

### `request(self, path: str, request_data: Dict[str, Any]) -> Dict[str, Any]`

Make async HTTP POST request to Gateway API.

Internal method for making authenticated requests to the TrustGraph API.

**Arguments:**

- `path`: API endpoint path (relative to base URL)
- `request_data`: Request payload dictionary

**Returns:** dict: Response object from API

**Raises:**

- `ProtocolException`: If HTTP status is not 200 or response is not valid JSON
- `ApplicationException`: If API returns an error response

### `start(self, class_name: str, id: str, description: str, parameters: Dict | None = None)`

Start a new flow instance.

Creates and starts a flow from a flow class definition with the specified
parameters.

**Arguments:**

- `class_name`: Flow class name to instantiate
- `id`: Identifier for the new flow instance
- `description`: Human-readable description of the flow
- `parameters`: Optional configuration parameters for the flow

**Example:**

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

### `stop(self, id: str)`

Stop a running flow.

Stops and removes a flow instance, freeing its resources.

**Arguments:**

- `id`: Flow identifier to stop

**Example:**

```python
async_flow = await api.async_flow()

# Stop a flow
await async_flow.stop("my-flow")
```


---

## `AsyncFlowInstance`

```python
from trustgraph.api import AsyncFlowInstance
```

Asynchronous flow instance client.

Provides async/await access to flow-scoped services including agents,
RAG queries, embeddings, and graph queries. All operations return complete
responses (non-streaming).

Note: For streaming support, use AsyncSocketFlowInstance instead.

### Methods

### `__init__(self, flow: trustgraph.api.async_flow.AsyncFlow, flow_id: str)`

Initialize async flow instance.

**Arguments:**

- `flow`: Parent AsyncFlow client
- `flow_id`: Flow identifier

### `agent(self, question: str, user: str, state: Dict | None = None, group: str | None = None, history: List | None = None, **kwargs: Any) -> Dict[str, Any]`

Execute an agent operation (non-streaming).

Runs an agent to answer a question, with optional conversation state and
history. Returns the complete response after the agent has finished
processing.

Note: This method does not support streaming. For real-time agent thoughts
and observations, use AsyncSocketFlowInstance.agent() instead.

**Arguments:**

- `question`: User question or instruction
- `user`: User identifier
- `state`: Optional state dictionary for conversation context
- `group`: Optional group identifier for session management
- `history`: Optional conversation history list
- `**kwargs`: Additional service-specific parameters

**Returns:** dict: Complete agent response including answer and metadata

**Example:**

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

### `document_rag(self, query: str, user: str, collection: str, doc_limit: int = 10, **kwargs: Any) -> str`

Execute document-based RAG query (non-streaming).

Performs Retrieval-Augmented Generation using document embeddings.
Retrieves relevant document chunks via semantic search, then generates
a response grounded in the retrieved documents. Returns complete response.

Note: This method does not support streaming. For streaming RAG responses,
use AsyncSocketFlowInstance.document_rag() instead.

**Arguments:**

- `query`: User query text
- `user`: User identifier
- `collection`: Collection identifier containing documents
- `doc_limit`: Maximum number of document chunks to retrieve (default: 10)
- `**kwargs`: Additional service-specific parameters

**Returns:** str: Complete generated response grounded in document data

**Example:**

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

### `embeddings(self, texts: list, **kwargs: Any)`

Generate embeddings for input texts.

Converts texts into numerical vector representations using the flow's
configured embedding model. Useful for semantic search and similarity
comparisons.

**Arguments:**

- `texts`: List of input texts to embed
- `**kwargs`: Additional service-specific parameters

**Returns:** dict: Response containing embedding vectors

**Example:**

```python
async_flow = await api.async_flow()
flow = async_flow.id("default")

# Generate embeddings
result = await flow.embeddings(texts=["Sample text to embed"])
vectors = result.get("vectors")
print(f"Embedding dimension: {len(vectors[0][0])}")
```

### `graph_embeddings_query(self, text: str, user: str, collection: str, limit: int = 10, **kwargs: Any)`

Query graph embeddings for semantic entity search.

Performs semantic search over graph entity embeddings to find entities
most relevant to the input text. Returns entities ranked by similarity.

**Arguments:**

- `text`: Query text for semantic search
- `user`: User identifier
- `collection`: Collection identifier containing graph embeddings
- `limit`: Maximum number of results to return (default: 10)
- `**kwargs`: Additional service-specific parameters

**Returns:** dict: Response containing ranked entity matches with similarity scores

**Example:**

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

### `graph_rag(self, query: str, user: str, collection: str, max_subgraph_size: int = 1000, max_subgraph_count: int = 5, max_entity_distance: int = 3, **kwargs: Any) -> str`

Execute graph-based RAG query (non-streaming).

Performs Retrieval-Augmented Generation using knowledge graph data.
Identifies relevant entities and their relationships, then generates a
response grounded in the graph structure. Returns complete response.

Note: This method does not support streaming. For streaming RAG responses,
use AsyncSocketFlowInstance.graph_rag() instead.

**Arguments:**

- `query`: User query text
- `user`: User identifier
- `collection`: Collection identifier containing the knowledge graph
- `max_subgraph_size`: Maximum number of triples per subgraph (default: 1000)
- `max_subgraph_count`: Maximum number of subgraphs to retrieve (default: 5)
- `max_entity_distance`: Maximum graph distance for entity expansion (default: 3)
- `**kwargs`: Additional service-specific parameters

**Returns:** str: Complete generated response grounded in graph data

**Example:**

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

### `request(self, service: str, request_data: Dict[str, Any]) -> Dict[str, Any]`

Make request to a flow-scoped service.

Internal method for calling services within this flow instance.

**Arguments:**

- `service`: Service name (e.g., "agent", "graph-rag", "triples")
- `request_data`: Service request payload

**Returns:** dict: Service response object

**Raises:**

- `ProtocolException`: If request fails or response is invalid
- `ApplicationException`: If service returns an error

### `row_embeddings_query(self, text: str, schema_name: str, user: str = 'trustgraph', collection: str = 'default', index_name: str | None = None, limit: int = 10, **kwargs: Any)`

Query row embeddings for semantic search on structured data.

Performs semantic search over row index embeddings to find rows whose
indexed field values are most similar to the input text. Enables
fuzzy/semantic matching on structured data.

**Arguments:**

- `text`: Query text for semantic search
- `schema_name`: Schema name to search within
- `user`: User identifier (default: "trustgraph")
- `collection`: Collection identifier (default: "default")
- `index_name`: Optional index name to filter search to specific index
- `limit`: Maximum number of results to return (default: 10)
- `**kwargs`: Additional service-specific parameters

**Returns:** dict: Response containing matches with index_name, index_value, text, and score

**Example:**

```python
async_flow = await api.async_flow()
flow = async_flow.id("default")

# Search for customers by name similarity
results = await flow.row_embeddings_query(
    text="John Smith",
    schema_name="customers",
    user="trustgraph",
    collection="sales",
    limit=5
)

for match in results.get("matches", []):
    print(f"{match['index_name']}: {match['index_value']} (score: {match['score']})")
```

### `rows_query(self, query: str, user: str, collection: str, variables: Dict | None = None, operation_name: str | None = None, **kwargs: Any)`

Execute a GraphQL query on stored rows.

Queries structured data rows using GraphQL syntax. Supports complex
queries with variables and named operations.

**Arguments:**

- `query`: GraphQL query string
- `user`: User identifier
- `collection`: Collection identifier containing rows
- `variables`: Optional GraphQL query variables
- `operation_name`: Optional operation name for multi-operation queries
- `**kwargs`: Additional service-specific parameters

**Returns:** dict: GraphQL response with data and/or errors

**Example:**

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

result = await flow.rows_query(
    query=query,
    user="trustgraph",
    collection="users",
    variables={"status": "active"}
)

for user in result.get("data", {}).get("users", []):
    print(f"{user['name']}: {user['email']}")
```

### `text_completion(self, system: str, prompt: str, **kwargs: Any) -> str`

Generate text completion (non-streaming).

Generates a text response from an LLM given a system prompt and user prompt.
Returns the complete response text.

Note: This method does not support streaming. For streaming text generation,
use AsyncSocketFlowInstance.text_completion() instead.

**Arguments:**

- `system`: System prompt defining the LLM's behavior
- `prompt`: User prompt or question
- `**kwargs`: Additional service-specific parameters

**Returns:** str: Complete generated text response

**Example:**

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

### `triples_query(self, s=None, p=None, o=None, user=None, collection=None, limit=100, **kwargs: Any)`

Query RDF triples using pattern matching.

Searches for triples matching the specified subject, predicate, and/or
object patterns. Patterns use None as a wildcard to match any value.

**Arguments:**

- `s`: Subject pattern (None for wildcard)
- `p`: Predicate pattern (None for wildcard)
- `o`: Object pattern (None for wildcard)
- `user`: User identifier (None for all users)
- `collection`: Collection identifier (None for all collections)
- `limit`: Maximum number of triples to return (default: 100)
- `**kwargs`: Additional service-specific parameters

**Returns:** dict: Response containing matching triples

**Example:**

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


---

## `SocketClient`

```python
from trustgraph.api import SocketClient
```

Synchronous WebSocket client for streaming operations.

Provides a synchronous interface to WebSocket-based TrustGraph services,
wrapping async websockets library with synchronous generators for ease of use.
Supports streaming responses from agents, RAG queries, and text completions.

Note: This is a synchronous wrapper around async WebSocket operations. For
true async support, use AsyncSocketClient instead.

### Methods

### `__init__(self, url: str, timeout: int, token: str | None) -> None`

Initialize synchronous WebSocket client.

**Arguments:**

- `url`: Base URL for TrustGraph API (HTTP/HTTPS will be converted to WS/WSS)
- `timeout`: WebSocket timeout in seconds
- `token`: Optional bearer token for authentication

### `close(self) -> None`

Close WebSocket connections.

Note: Cleanup is handled automatically by context managers in async code.

### `flow(self, flow_id: str) -> 'SocketFlowInstance'`

Get a flow instance for WebSocket streaming operations.

**Arguments:**

- `flow_id`: Flow identifier

**Returns:** SocketFlowInstance: Flow instance with streaming methods

**Example:**

```python
socket = api.socket()
flow = socket.flow("default")

# Stream agent responses
for chunk in flow.agent(question="Hello", user="trustgraph", streaming=True):
    print(chunk.content, end='', flush=True)
```


---

## `SocketFlowInstance`

```python
from trustgraph.api import SocketFlowInstance
```

Synchronous WebSocket flow instance for streaming operations.

Provides the same interface as REST FlowInstance but with WebSocket-based
streaming support for real-time responses. All methods support an optional
`streaming` parameter to enable incremental result delivery.

### Methods

### `__init__(self, client: trustgraph.api.socket_client.SocketClient, flow_id: str) -> None`

Initialize socket flow instance.

**Arguments:**

- `client`: Parent SocketClient
- `flow_id`: Flow identifier

### `agent(self, question: str, user: str, state: Dict[str, Any] | None = None, group: str | None = None, history: List[Dict[str, Any]] | None = None, streaming: bool = False, **kwargs: Any) -> Dict[str, Any] | Iterator[trustgraph.api.types.StreamingChunk]`

Execute an agent operation with streaming support.

Agents can perform multi-step reasoning with tool use. This method always
returns streaming chunks (thoughts, observations, answers) even when
streaming=False, to show the agent's reasoning process.

**Arguments:**

- `question`: User question or instruction
- `user`: User identifier
- `state`: Optional state dictionary for stateful conversations
- `group`: Optional group identifier for multi-user contexts
- `history`: Optional conversation history as list of message dicts
- `streaming`: Enable streaming mode (default: False)
- `**kwargs`: Additional parameters passed to the agent service

**Returns:** Iterator[StreamingChunk]: Stream of agent thoughts, observations, and answers

**Example:**

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

### `agent_explain(self, question: str, user: str, collection: str, state: Dict[str, Any] | None = None, group: str | None = None, history: List[Dict[str, Any]] | None = None, **kwargs: Any) -> Iterator[trustgraph.api.types.StreamingChunk | trustgraph.api.types.ProvenanceEvent]`

Execute an agent operation with explainability support.

Streams both content chunks (AgentThought, AgentObservation, AgentAnswer)
and provenance events (ProvenanceEvent). Provenance events contain URIs
that can be fetched using ExplainabilityClient to get detailed information
about the agent's reasoning process.

Agent trace consists of:
- Session: The initial question and session metadata
- Iterations: Each thought/action/observation cycle
- Conclusion: The final answer

**Arguments:**

- `question`: User question or instruction
- `user`: User identifier
- `collection`: Collection identifier for provenance storage
- `state`: Optional state dictionary for stateful conversations
- `group`: Optional group identifier for multi-user contexts
- `history`: Optional conversation history as list of message dicts
- `**kwargs`: Additional parameters passed to the agent service
- `Yields`: 
- `Union[StreamingChunk, ProvenanceEvent]`: Agent chunks and provenance events

**Example:**

```python
from trustgraph.api import Api, ExplainabilityClient, ProvenanceEvent
from trustgraph.api import AgentThought, AgentObservation, AgentAnswer

socket = api.socket()
flow = socket.flow("default")
explain_client = ExplainabilityClient(flow)

provenance_ids = []
for item in flow.agent_explain(
    question="What is the capital of France?",
    user="trustgraph",
    collection="default"
):
    if isinstance(item, AgentThought):
        print(f"[Thought] {item.content}")
    elif isinstance(item, AgentObservation):
        print(f"[Observation] {item.content}")
    elif isinstance(item, AgentAnswer):
        print(f"[Answer] {item.content}")
    elif isinstance(item, ProvenanceEvent):
        provenance_ids.append(item.explain_id)

# Fetch session trace after completion
if provenance_ids:
    trace = explain_client.fetch_agent_trace(
        provenance_ids[0],  # Session URI is first
        graph="urn:graph:retrieval",
        user="trustgraph",
        collection="default"
    )
```

### `document_embeddings_query(self, text: str, user: str, collection: str, limit: int = 10, **kwargs: Any) -> Dict[str, Any]`

Query document chunks using semantic similarity.

**Arguments:**

- `text`: Query text for semantic search
- `user`: User/keyspace identifier
- `collection`: Collection identifier
- `limit`: Maximum number of results (default: 10)
- `**kwargs`: Additional parameters passed to the service

**Returns:** dict: Query results with chunk_ids of matching document chunks

**Example:**

```python
socket = api.socket()
flow = socket.flow("default")

results = flow.document_embeddings_query(
    text="machine learning algorithms",
    user="trustgraph",
    collection="research-papers",
    limit=5
)
# results contains {"chunks": [{"chunk_id": "...", "score": 0.95}, ...]}
```

### `document_rag(self, query: str, user: str, collection: str, doc_limit: int = 10, streaming: bool = False, **kwargs: Any) -> str | Iterator[str]`

Execute document-based RAG query with optional streaming.

Uses vector embeddings to find relevant document chunks, then generates
a response using an LLM. Streaming mode delivers results incrementally.

**Arguments:**

- `query`: Natural language query
- `user`: User/keyspace identifier
- `collection`: Collection identifier
- `doc_limit`: Maximum document chunks to retrieve (default: 10)
- `streaming`: Enable streaming mode (default: False)
- `**kwargs`: Additional parameters passed to the service

**Returns:** Union[str, Iterator[str]]: Complete response or stream of text chunks

**Example:**

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

### `document_rag_explain(self, query: str, user: str, collection: str, doc_limit: int = 10, **kwargs: Any) -> Iterator[trustgraph.api.types.RAGChunk | trustgraph.api.types.ProvenanceEvent]`

Execute document-based RAG query with explainability support.

Streams both content chunks (RAGChunk) and provenance events (ProvenanceEvent).
Provenance events contain URIs that can be fetched using ExplainabilityClient
to get detailed information about how the response was generated.

Document RAG trace consists of:
- Question: The user's query
- Exploration: Chunks retrieved from document store (chunk_count)
- Synthesis: The generated answer

**Arguments:**

- `query`: Natural language query
- `user`: User/keyspace identifier
- `collection`: Collection identifier
- `doc_limit`: Maximum document chunks to retrieve (default: 10)
- `**kwargs`: Additional parameters passed to the service
- `Yields`: 
- `Union[RAGChunk, ProvenanceEvent]`: Content chunks and provenance events

**Example:**

```python
from trustgraph.api import Api, ExplainabilityClient, RAGChunk, ProvenanceEvent

socket = api.socket()
flow = socket.flow("default")
explain_client = ExplainabilityClient(flow)

for item in flow.document_rag_explain(
    query="Summarize the key findings",
    user="trustgraph",
    collection="research-papers",
    doc_limit=5
):
    if isinstance(item, RAGChunk):
        print(item.content, end='', flush=True)
    elif isinstance(item, ProvenanceEvent):
        # Fetch entity details
        entity = explain_client.fetch_entity(
            item.explain_id,
            graph=item.explain_graph,
            user="trustgraph",
            collection="research-papers"
        )
        print(f"Event: {entity}", file=sys.stderr)
```

### `embeddings(self, texts: list, **kwargs: Any) -> Dict[str, Any]`

Generate vector embeddings for one or more texts.

**Arguments:**

- `texts`: List of input texts to embed
- `**kwargs`: Additional parameters passed to the service

**Returns:** dict: Response containing vectors (one set per input text)

**Example:**

```python
socket = api.socket()
flow = socket.flow("default")

result = flow.embeddings(["quantum computing"])
vectors = result.get("vectors", [])
```

### `graph_embeddings_query(self, text: str, user: str, collection: str, limit: int = 10, **kwargs: Any) -> Dict[str, Any]`

Query knowledge graph entities using semantic similarity.

**Arguments:**

- `text`: Query text for semantic search
- `user`: User/keyspace identifier
- `collection`: Collection identifier
- `limit`: Maximum number of results (default: 10)
- `**kwargs`: Additional parameters passed to the service

**Returns:** dict: Query results with similar entities

**Example:**

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

### `graph_rag(self, query: str, user: str, collection: str, max_subgraph_size: int = 1000, max_subgraph_count: int = 5, max_entity_distance: int = 3, streaming: bool = False, **kwargs: Any) -> str | Iterator[str]`

Execute graph-based RAG query with optional streaming.

Uses knowledge graph structure to find relevant context, then generates
a response using an LLM. Streaming mode delivers results incrementally.

**Arguments:**

- `query`: Natural language query
- `user`: User/keyspace identifier
- `collection`: Collection identifier
- `max_subgraph_size`: Maximum total triples in subgraph (default: 1000)
- `max_subgraph_count`: Maximum number of subgraphs (default: 5)
- `max_entity_distance`: Maximum traversal depth (default: 3)
- `streaming`: Enable streaming mode (default: False)
- `**kwargs`: Additional parameters passed to the service

**Returns:** Union[str, Iterator[str]]: Complete response or stream of text chunks

**Example:**

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

### `graph_rag_explain(self, query: str, user: str, collection: str, max_subgraph_size: int = 1000, max_subgraph_count: int = 5, max_entity_distance: int = 3, **kwargs: Any) -> Iterator[trustgraph.api.types.RAGChunk | trustgraph.api.types.ProvenanceEvent]`

Execute graph-based RAG query with explainability support.

Streams both content chunks (RAGChunk) and provenance events (ProvenanceEvent).
Provenance events contain URIs that can be fetched using ExplainabilityClient
to get detailed information about how the response was generated.

**Arguments:**

- `query`: Natural language query
- `user`: User/keyspace identifier
- `collection`: Collection identifier
- `max_subgraph_size`: Maximum total triples in subgraph (default: 1000)
- `max_subgraph_count`: Maximum number of subgraphs (default: 5)
- `max_entity_distance`: Maximum traversal depth (default: 3)
- `**kwargs`: Additional parameters passed to the service
- `Yields`: 
- `Union[RAGChunk, ProvenanceEvent]`: Content chunks and provenance events

**Example:**

```python
from trustgraph.api import Api, ExplainabilityClient, RAGChunk, ProvenanceEvent

socket = api.socket()
flow = socket.flow("default")
explain_client = ExplainabilityClient(flow)

provenance_ids = []
response_text = ""

for item in flow.graph_rag_explain(
    query="Tell me about Marie Curie",
    user="trustgraph",
    collection="scientists"
):
    if isinstance(item, RAGChunk):
        response_text += item.content
        print(item.content, end='', flush=True)
    elif isinstance(item, ProvenanceEvent):
        provenance_ids.append(item.provenance_id)

# Fetch explainability details
for prov_id in provenance_ids:
    entity = explain_client.fetch_entity(
        prov_id,
        graph="urn:graph:retrieval",
        user="trustgraph",
        collection="scientists"
    )
    print(f"Entity: {entity}")
```

### `mcp_tool(self, name: str, parameters: Dict[str, Any], **kwargs: Any) -> Dict[str, Any]`

Execute a Model Context Protocol (MCP) tool.

**Arguments:**

- `name`: Tool name/identifier
- `parameters`: Tool parameters dictionary
- `**kwargs`: Additional parameters passed to the service

**Returns:** dict: Tool execution result

**Example:**

```python
socket = api.socket()
flow = socket.flow("default")

result = flow.mcp_tool(
    name="search-web",
    parameters={"query": "latest AI news", "limit": 5}
)
```

### `prompt(self, id: str, variables: Dict[str, str], streaming: bool = False, **kwargs: Any) -> str | Iterator[str]`

Execute a prompt template with optional streaming.

**Arguments:**

- `id`: Prompt template identifier
- `variables`: Dictionary of variable name to value mappings
- `streaming`: Enable streaming mode (default: False)
- `**kwargs`: Additional parameters passed to the service

**Returns:** Union[str, Iterator[str]]: Complete response or stream of text chunks

**Example:**

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

### `row_embeddings_query(self, text: str, schema_name: str, user: str = 'trustgraph', collection: str = 'default', index_name: str | None = None, limit: int = 10, **kwargs: Any) -> Dict[str, Any]`

Query row data using semantic similarity on indexed fields.

Finds rows whose indexed field values are semantically similar to the
input text, using vector embeddings. This enables fuzzy/semantic matching
on structured data.

**Arguments:**

- `text`: Query text for semantic search
- `schema_name`: Schema name to search within
- `user`: User/keyspace identifier (default: "trustgraph")
- `collection`: Collection identifier (default: "default")
- `index_name`: Optional index name to filter search to specific index
- `limit`: Maximum number of results (default: 10)
- `**kwargs`: Additional parameters passed to the service

**Returns:** dict: Query results with matches containing index_name, index_value, text, and score

**Example:**

```python
socket = api.socket()
flow = socket.flow("default")

# Search for customers by name similarity
results = flow.row_embeddings_query(
    text="John Smith",
    schema_name="customers",
    user="trustgraph",
    collection="sales",
    limit=5
)

# Filter to specific index
results = flow.row_embeddings_query(
    text="machine learning engineer",
    schema_name="employees",
    index_name="job_title",
    limit=10
)
```

### `rows_query(self, query: str, user: str, collection: str, variables: Dict[str, Any] | None = None, operation_name: str | None = None, **kwargs: Any) -> Dict[str, Any]`

Execute a GraphQL query against structured rows.

**Arguments:**

- `query`: GraphQL query string
- `user`: User/keyspace identifier
- `collection`: Collection identifier
- `variables`: Optional query variables dictionary
- `operation_name`: Optional operation name for multi-operation documents
- `**kwargs`: Additional parameters passed to the service

**Returns:** dict: GraphQL response with data, errors, and/or extensions

**Example:**

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
result = flow.rows_query(
    query=query,
    user="trustgraph",
    collection="scientists"
)
```

### `text_completion(self, system: str, prompt: str, streaming: bool = False, **kwargs) -> str | Iterator[str]`

Execute text completion with optional streaming.

**Arguments:**

- `system`: System prompt defining the assistant's behavior
- `prompt`: User prompt/question
- `streaming`: Enable streaming mode (default: False)
- `**kwargs`: Additional parameters passed to the service

**Returns:** Union[str, Iterator[str]]: Complete response or stream of text chunks

**Example:**

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

### `triples_query(self, s: str | Dict[str, Any] | None = None, p: str | Dict[str, Any] | None = None, o: str | Dict[str, Any] | None = None, g: str | None = None, user: str | None = None, collection: str | None = None, limit: int = 100, **kwargs: Any) -> List[Dict[str, Any]]`

Query knowledge graph triples using pattern matching.

**Arguments:**

- `s`: Subject filter - URI string, Term dict, or None for wildcard
- `p`: Predicate filter - URI string, Term dict, or None for wildcard
- `o`: Object filter - URI/literal string, Term dict, or None for wildcard
- `g`: Named graph filter - URI string or None for all graphs
- `user`: User/keyspace identifier (optional)
- `collection`: Collection identifier (optional)
- `limit`: Maximum results to return (default: 100)
- `**kwargs`: Additional parameters passed to the service

**Returns:** List[Dict]: List of matching triples in wire format

**Example:**

```python
socket = api.socket()
flow = socket.flow("default")

# Find all triples about a specific subject
triples = flow.triples_query(
    s="http://example.org/person/marie-curie",
    user="trustgraph",
    collection="scientists"
)

# Query with named graph filter
triples = flow.triples_query(
    s="urn:trustgraph:session:abc123",
    g="urn:graph:retrieval",
    user="trustgraph",
    collection="default"
)
```

### `triples_query_stream(self, s: str | Dict[str, Any] | None = None, p: str | Dict[str, Any] | None = None, o: str | Dict[str, Any] | None = None, g: str | None = None, user: str | None = None, collection: str | None = None, limit: int = 100, batch_size: int = 20, **kwargs: Any) -> Iterator[List[Dict[str, Any]]]`

Query knowledge graph triples with streaming batches.

Yields batches of triples as they arrive, reducing time-to-first-result
and memory overhead for large result sets.

**Arguments:**

- `s`: Subject filter - URI string, Term dict, or None for wildcard
- `p`: Predicate filter - URI string, Term dict, or None for wildcard
- `o`: Object filter - URI/literal string, Term dict, or None for wildcard
- `g`: Named graph filter - URI string or None for all graphs
- `user`: User/keyspace identifier (optional)
- `collection`: Collection identifier (optional)
- `limit`: Maximum results to return (default: 100)
- `batch_size`: Triples per batch (default: 20)
- `**kwargs`: Additional parameters passed to the service
- `Yields`: 
- `List[Dict]`: Batches of triples in wire format

**Example:**

```python
socket = api.socket()
flow = socket.flow("default")

for batch in flow.triples_query_stream(
    user="trustgraph",
    collection="default"
):
    for triple in batch:
        print(triple["s"], triple["p"], triple["o"])
```


---

## `AsyncSocketClient`

```python
from trustgraph.api import AsyncSocketClient
```

Asynchronous WebSocket client

### Methods

### `__init__(self, url: str, timeout: int, token: str | None)`

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

### `agent(self, question: str, user: str, state: Dict[str, Any] | None = None, group: str | None = None, history: list | None = None, streaming: bool = False, **kwargs) -> Dict[str, Any] | AsyncIterator`

Agent with optional streaming

### `document_rag(self, query: str, user: str, collection: str, doc_limit: int = 10, streaming: bool = False, **kwargs)`

Document RAG with optional streaming

### `embeddings(self, texts: list, **kwargs)`

Generate text embeddings

### `graph_embeddings_query(self, text: str, user: str, collection: str, limit: int = 10, **kwargs)`

Query graph embeddings for semantic search

### `graph_rag(self, query: str, user: str, collection: str, max_subgraph_size: int = 1000, max_subgraph_count: int = 5, max_entity_distance: int = 3, streaming: bool = False, **kwargs)`

Graph RAG with optional streaming

### `mcp_tool(self, name: str, parameters: Dict[str, Any], **kwargs)`

Execute MCP tool

### `prompt(self, id: str, variables: Dict[str, str], streaming: bool = False, **kwargs)`

Execute prompt with optional streaming

### `row_embeddings_query(self, text: str, schema_name: str, user: str = 'trustgraph', collection: str = 'default', index_name: str | None = None, limit: int = 10, **kwargs)`

Query row embeddings for semantic search on structured data

### `rows_query(self, query: str, user: str, collection: str, variables: Dict | None = None, operation_name: str | None = None, **kwargs)`

GraphQL query against structured rows

### `text_completion(self, system: str, prompt: str, streaming: bool = False, **kwargs)`

Text completion with optional streaming

### `triples_query(self, s=None, p=None, o=None, user=None, collection=None, limit=100, **kwargs)`

Triple pattern query


---

### `build_term(value: Any, term_type: str | None = None, datatype: str | None = None, language: str | None = None) -> Dict[str, Any] | None`

Build wire-format Term dict from a value.

Auto-detection rules (when term_type is None):
  - Already a dict with 't' key -> return as-is (already a Term)
  - Starts with http://, https://, urn: -> IRI
  - Wrapped in <> (e.g., <http://...>) -> IRI (angle brackets stripped)
  - Anything else -> literal

**Arguments:**

- `value`: The term value (string, dict, or None)
- `term_type`: One of 'iri', 'literal', or None for auto-detect
- `datatype`: Datatype for literal objects (e.g., xsd:integer)
- `language`: Language tag for literal objects (e.g., en)

**Returns:** dict: Wire-format Term dict, or None if value is None


---

## `BulkClient`

```python
from trustgraph.api import BulkClient
```

Synchronous bulk operations client for import/export.

Provides efficient bulk data transfer via WebSocket for large datasets.
Wraps async WebSocket operations with synchronous generators for ease of use.

Note: For true async support, use AsyncBulkClient instead.

### Methods

### `__init__(self, url: str, timeout: int, token: str | None) -> None`

Initialize synchronous bulk client.

**Arguments:**

- `url`: Base URL for TrustGraph API (HTTP/HTTPS will be converted to WS/WSS)
- `timeout`: WebSocket timeout in seconds
- `token`: Optional bearer token for authentication

### `close(self) -> None`

Close connections

### `export_document_embeddings(self, flow: str, **kwargs: Any) -> Iterator[Dict[str, Any]]`

Bulk export document embeddings from a flow.

Efficiently downloads all document chunk embeddings via WebSocket streaming.

**Arguments:**

- `flow`: Flow identifier
- `**kwargs`: Additional parameters (reserved for future use)

**Returns:** Iterator[Dict[str, Any]]: Stream of embedding dictionaries

**Example:**

```python
bulk = api.bulk()

# Export and process document embeddings
for embedding in bulk.export_document_embeddings(flow="default"):
    chunk_id = embedding.get("chunk_id")
    vector = embedding.get("embedding")
    print(f"{chunk_id}: {len(vector)} dimensions")
```

### `export_entity_contexts(self, flow: str, **kwargs: Any) -> Iterator[Dict[str, Any]]`

Bulk export entity contexts from a flow.

Efficiently downloads all entity context information via WebSocket streaming.

**Arguments:**

- `flow`: Flow identifier
- `**kwargs`: Additional parameters (reserved for future use)

**Returns:** Iterator[Dict[str, Any]]: Stream of context dictionaries

**Example:**

```python
bulk = api.bulk()

# Export and process entity contexts
for context in bulk.export_entity_contexts(flow="default"):
    entity = context.get("entity")
    text = context.get("context")
    print(f"{entity}: {text[:100]}...")
```

### `export_graph_embeddings(self, flow: str, **kwargs: Any) -> Iterator[Dict[str, Any]]`

Bulk export graph embeddings from a flow.

Efficiently downloads all graph entity embeddings via WebSocket streaming.

**Arguments:**

- `flow`: Flow identifier
- `**kwargs`: Additional parameters (reserved for future use)

**Returns:** Iterator[Dict[str, Any]]: Stream of embedding dictionaries

**Example:**

```python
bulk = api.bulk()

# Export and process embeddings
for embedding in bulk.export_graph_embeddings(flow="default"):
    entity = embedding.get("entity")
    vector = embedding.get("embedding")
    print(f"{entity}: {len(vector)} dimensions")
```

### `export_triples(self, flow: str, **kwargs: Any) -> Iterator[trustgraph.api.types.Triple]`

Bulk export RDF triples from a flow.

Efficiently downloads all triples via WebSocket streaming.

**Arguments:**

- `flow`: Flow identifier
- `**kwargs`: Additional parameters (reserved for future use)

**Returns:** Iterator[Triple]: Stream of Triple objects

**Example:**

```python
bulk = api.bulk()

# Export and process triples
for triple in bulk.export_triples(flow="default"):
    print(f"{triple.s} -> {triple.p} -> {triple.o}")
```

### `import_document_embeddings(self, flow: str, embeddings: Iterator[Dict[str, Any]], **kwargs: Any) -> None`

Bulk import document embeddings into a flow.

Efficiently uploads document chunk embeddings via WebSocket streaming
for use in document RAG queries.

**Arguments:**

- `flow`: Flow identifier
- `embeddings`: Iterator yielding embedding dictionaries
- `**kwargs`: Additional parameters (reserved for future use)

**Example:**

```python
bulk = api.bulk()

# Generate document embeddings to import
def doc_embedding_generator():
    yield {"chunk_id": "doc1/p0/c0", "embedding": [0.1, 0.2, ...]}
    yield {"chunk_id": "doc1/p0/c1", "embedding": [0.3, 0.4, ...]}
    # ... more embeddings

bulk.import_document_embeddings(
    flow="default",
    embeddings=doc_embedding_generator()
)
```

### `import_entity_contexts(self, flow: str, contexts: Iterator[Dict[str, Any]], metadata: Dict[str, Any] | None = None, batch_size: int = 100, **kwargs: Any) -> None`

Bulk import entity contexts into a flow.

Efficiently uploads entity context information via WebSocket streaming.
Entity contexts provide additional textual context about graph entities
for improved RAG performance.

**Arguments:**

- `flow`: Flow identifier
- `contexts`: Iterator yielding context dictionaries
- `metadata`: Metadata dict with id, metadata, user, collection
- `batch_size`: Number of contexts per batch (default 100)
- `**kwargs`: Additional parameters (reserved for future use)

**Example:**

```python
bulk = api.bulk()

# Generate entity contexts to import
def context_generator():
    yield {"entity": {"v": "entity1", "e": True}, "context": "Description..."}
    yield {"entity": {"v": "entity2", "e": True}, "context": "Description..."}
    # ... more contexts

bulk.import_entity_contexts(
    flow="default",
    contexts=context_generator(),
    metadata={"id": "doc1", "metadata": [], "user": "user1", "collection": "default"}
)
```

### `import_graph_embeddings(self, flow: str, embeddings: Iterator[Dict[str, Any]], **kwargs: Any) -> None`

Bulk import graph embeddings into a flow.

Efficiently uploads graph entity embeddings via WebSocket streaming.

**Arguments:**

- `flow`: Flow identifier
- `embeddings`: Iterator yielding embedding dictionaries
- `**kwargs`: Additional parameters (reserved for future use)

**Example:**

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

### `import_rows(self, flow: str, rows: Iterator[Dict[str, Any]], **kwargs: Any) -> None`

Bulk import structured rows into a flow.

Efficiently uploads structured data rows via WebSocket streaming
for use in GraphQL queries.

**Arguments:**

- `flow`: Flow identifier
- `rows`: Iterator yielding row dictionaries
- `**kwargs`: Additional parameters (reserved for future use)

**Example:**

```python
bulk = api.bulk()

# Generate rows to import
def row_generator():
    yield {"id": "row1", "name": "Row 1", "value": 100}
    yield {"id": "row2", "name": "Row 2", "value": 200}
    # ... more rows

bulk.import_rows(
    flow="default",
    rows=row_generator()
)
```

### `import_triples(self, flow: str, triples: Iterator[trustgraph.api.types.Triple], metadata: Dict[str, Any] | None = None, batch_size: int = 100, **kwargs: Any) -> None`

Bulk import RDF triples into a flow.

Efficiently uploads large numbers of triples via WebSocket streaming.

**Arguments:**

- `flow`: Flow identifier
- `triples`: Iterator yielding Triple objects
- `metadata`: Metadata dict with id, metadata, user, collection
- `batch_size`: Number of triples per batch (default 100)
- `**kwargs`: Additional parameters (reserved for future use)

**Example:**

```python
from trustgraph.api import Triple

bulk = api.bulk()

# Generate triples to import
def triple_generator():
    yield Triple(s="subj1", p="pred", o="obj1")
    yield Triple(s="subj2", p="pred", o="obj2")
    # ... more triples

# Import triples
bulk.import_triples(
    flow="default",
    triples=triple_generator(),
    metadata={"id": "doc1", "metadata": [], "user": "user1", "collection": "default"}
)
```


---

## `AsyncBulkClient`

```python
from trustgraph.api import AsyncBulkClient
```

Asynchronous bulk operations client

### Methods

### `__init__(self, url: str, timeout: int, token: str | None) -> None`

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

### `import_rows(self, flow: str, rows: AsyncIterator[Dict[str, Any]], **kwargs: Any) -> None`

Bulk import rows via WebSocket

### `import_triples(self, flow: str, triples: AsyncIterator[trustgraph.api.types.Triple], **kwargs: Any) -> None`

Bulk import triples via WebSocket


---

## `Metrics`

```python
from trustgraph.api import Metrics
```

Synchronous metrics client

### Methods

### `__init__(self, url: str, timeout: int, token: str | None) -> None`

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

### `__init__(self, url: str, timeout: int, token: str | None) -> None`

Initialize self.  See help(type(self)) for accurate signature.

### `aclose(self) -> None`

Close connections

### `get(self) -> str`

Get Prometheus metrics as text


---

## `ExplainabilityClient`

```python
from trustgraph.api import ExplainabilityClient
```

Client for fetching explainability entities with eventual consistency handling.

Uses quiescence detection: fetch, wait, fetch again, compare.
If results are the same, data is stable.

### Methods

### `__init__(self, flow_instance, retry_delay: float = 0.2, max_retries: int = 10)`

Initialize explainability client.

**Arguments:**

- `flow_instance`: A SocketFlowInstance for querying triples
- `retry_delay`: Delay between retries in seconds (default: 0.2)
- `max_retries`: Maximum retry attempts (default: 10)

### `detect_session_type(self, session_uri: str, graph: str | None = None, user: str | None = None, collection: str | None = None) -> str`

Detect whether a session is GraphRAG or Agent type.

**Arguments:**

- `session_uri`: The session/question URI
- `graph`: Named graph
- `user`: User/keyspace identifier
- `collection`: Collection identifier

**Returns:** "graphrag" or "agent"

### `fetch_agent_trace(self, session_uri: str, graph: str | None = None, user: str | None = None, collection: str | None = None, api: Any = None, max_content: int = 10000) -> Dict[str, Any]`

Fetch the complete Agent trace starting from a session URI.

Follows the provenance chain: Question -> Analysis(s) -> Conclusion

**Arguments:**

- `session_uri`: The agent session/question URI
- `graph`: Named graph (default: urn:graph:retrieval)
- `user`: User/keyspace identifier
- `collection`: Collection identifier
- `api`: TrustGraph Api instance for librarian access (optional)
- `max_content`: Maximum content length for conclusion

**Returns:** Dict with question, iterations (Analysis list), conclusion entities

### `fetch_docrag_trace(self, question_uri: str, graph: str | None = None, user: str | None = None, collection: str | None = None, api: Any = None, max_content: int = 10000) -> Dict[str, Any]`

Fetch the complete DocumentRAG trace starting from a question URI.

Follows the provenance chain:
    Question -> Grounding -> Exploration -> Synthesis

**Arguments:**

- `question_uri`: The question entity URI
- `graph`: Named graph (default: urn:graph:retrieval)
- `user`: User/keyspace identifier
- `collection`: Collection identifier
- `api`: TrustGraph Api instance for librarian access (optional)
- `max_content`: Maximum content length for synthesis

**Returns:** Dict with question, grounding, exploration, synthesis entities

### `fetch_document_content(self, document_uri: str, api: Any, user: str | None = None, max_content: int = 10000) -> str`

Fetch content from the librarian by document URI.

**Arguments:**

- `document_uri`: The document URI in the librarian
- `api`: TrustGraph Api instance for librarian access
- `user`: User identifier for librarian
- `max_content`: Maximum content length to return

**Returns:** The document content as a string

### `fetch_edge_selection(self, uri: str, graph: str | None = None, user: str | None = None, collection: str | None = None) -> trustgraph.api.explainability.EdgeSelection | None`

Fetch an edge selection entity (used by Focus).

**Arguments:**

- `uri`: The edge selection URI
- `graph`: Named graph to query
- `user`: User/keyspace identifier
- `collection`: Collection identifier

**Returns:** EdgeSelection or None if not found

### `fetch_entity(self, uri: str, graph: str | None = None, user: str | None = None, collection: str | None = None) -> trustgraph.api.explainability.ExplainEntity | None`

Fetch an explainability entity by URI with eventual consistency handling.

Uses quiescence detection:
1. Fetch triples for URI
2. If zero results, retry
3. If non-zero results, wait and fetch again
4. If same results, data is stable - parse and return
5. If different results, data still being written - retry

**Arguments:**

- `uri`: The entity URI to fetch
- `graph`: Named graph to query (e.g., "urn:graph:retrieval")
- `user`: User/keyspace identifier
- `collection`: Collection identifier

**Returns:** ExplainEntity subclass or None if not found

### `fetch_focus_with_edges(self, uri: str, graph: str | None = None, user: str | None = None, collection: str | None = None) -> trustgraph.api.explainability.Focus | None`

Fetch a Focus entity and all its edge selections.

**Arguments:**

- `uri`: The Focus entity URI
- `graph`: Named graph to query
- `user`: User/keyspace identifier
- `collection`: Collection identifier

**Returns:** Focus with populated edge_selections, or None

### `fetch_graphrag_trace(self, question_uri: str, graph: str | None = None, user: str | None = None, collection: str | None = None, api: Any = None, max_content: int = 10000) -> Dict[str, Any]`

Fetch the complete GraphRAG trace starting from a question URI.

Follows the provenance chain: Question -> Grounding -> Exploration -> Focus -> Synthesis

**Arguments:**

- `question_uri`: The question entity URI
- `graph`: Named graph (default: urn:graph:retrieval)
- `user`: User/keyspace identifier
- `collection`: Collection identifier
- `api`: TrustGraph Api instance for librarian access (optional)
- `max_content`: Maximum content length for synthesis

**Returns:** Dict with question, grounding, exploration, focus, synthesis entities

### `list_sessions(self, graph: str | None = None, user: str | None = None, collection: str | None = None, limit: int = 50) -> List[trustgraph.api.explainability.Question]`

List all explainability sessions (questions) in a collection.

**Arguments:**

- `graph`: Named graph (default: urn:graph:retrieval)
- `user`: User/keyspace identifier
- `collection`: Collection identifier
- `limit`: Maximum number of sessions to return

**Returns:** List of Question entities sorted by timestamp (newest first)

### `resolve_edge_labels(self, edge: Dict[str, str], user: str | None = None, collection: str | None = None) -> Tuple[str, str, str]`

Resolve labels for all components of an edge triple.

**Arguments:**

- `edge`: Dict with "s", "p", "o" keys
- `user`: User/keyspace identifier
- `collection`: Collection identifier

**Returns:** Tuple of (s_label, p_label, o_label)

### `resolve_label(self, uri: str, user: str | None = None, collection: str | None = None) -> str`

Resolve rdfs:label for a URI, with caching.

**Arguments:**

- `uri`: The URI to get label for
- `user`: User/keyspace identifier
- `collection`: Collection identifier

**Returns:** The label if found, otherwise the URI itself


---

## `ExplainEntity`

```python
from trustgraph.api import ExplainEntity
```

Base class for explainability entities.

**Fields:**

- `uri`: <class 'str'>
- `entity_type`: <class 'str'>

### Methods

### `__init__(self, uri: str, entity_type: str = '') -> None`

Initialize self.  See help(type(self)) for accurate signature.


---

## `Question`

```python
from trustgraph.api import Question
```

Question entity - the user's query that started the session.

**Fields:**

- `uri`: <class 'str'>
- `entity_type`: <class 'str'>
- `query`: <class 'str'>
- `timestamp`: <class 'str'>
- `question_type`: <class 'str'>

### Methods

### `__init__(self, uri: str, entity_type: str = '', query: str = '', timestamp: str = '', question_type: str = '') -> None`

Initialize self.  See help(type(self)) for accurate signature.


---

## `Exploration`

```python
from trustgraph.api import Exploration
```

Exploration entity - edges/chunks retrieved from the knowledge store.

**Fields:**

- `uri`: <class 'str'>
- `entity_type`: <class 'str'>
- `edge_count`: <class 'int'>
- `chunk_count`: <class 'int'>
- `entities`: typing.List[str]

### Methods

### `__init__(self, uri: str, entity_type: str = '', edge_count: int = 0, chunk_count: int = 0, entities: List[str] = <factory>) -> None`

Initialize self.  See help(type(self)) for accurate signature.


---

## `Focus`

```python
from trustgraph.api import Focus
```

Focus entity - selected edges with LLM reasoning (GraphRAG only).

**Fields:**

- `uri`: <class 'str'>
- `entity_type`: <class 'str'>
- `selected_edge_uris`: typing.List[str]
- `edge_selections`: typing.List[trustgraph.api.explainability.EdgeSelection]

### Methods

### `__init__(self, uri: str, entity_type: str = '', selected_edge_uris: List[str] = <factory>, edge_selections: List[trustgraph.api.explainability.EdgeSelection] = <factory>) -> None`

Initialize self.  See help(type(self)) for accurate signature.


---

## `Synthesis`

```python
from trustgraph.api import Synthesis
```

Synthesis entity - the final answer.

**Fields:**

- `uri`: <class 'str'>
- `entity_type`: <class 'str'>
- `document`: <class 'str'>

### Methods

### `__init__(self, uri: str, entity_type: str = '', document: str = '') -> None`

Initialize self.  See help(type(self)) for accurate signature.


---

## `Analysis`

```python
from trustgraph.api import Analysis
```

Analysis entity - one think/act/observe cycle (Agent only).

**Fields:**

- `uri`: <class 'str'>
- `entity_type`: <class 'str'>
- `action`: <class 'str'>
- `arguments`: <class 'str'>
- `thought`: <class 'str'>
- `observation`: <class 'str'>

### Methods

### `__init__(self, uri: str, entity_type: str = '', action: str = '', arguments: str = '', thought: str = '', observation: str = '') -> None`

Initialize self.  See help(type(self)) for accurate signature.


---

## `Conclusion`

```python
from trustgraph.api import Conclusion
```

Conclusion entity - final answer (Agent only).

**Fields:**

- `uri`: <class 'str'>
- `entity_type`: <class 'str'>
- `document`: <class 'str'>

### Methods

### `__init__(self, uri: str, entity_type: str = '', document: str = '') -> None`

Initialize self.  See help(type(self)) for accurate signature.


---

## `EdgeSelection`

```python
from trustgraph.api import EdgeSelection
```

A selected edge with reasoning from GraphRAG Focus step.

**Fields:**

- `uri`: <class 'str'>
- `edge`: typing.Dict[str, str] | None
- `reasoning`: <class 'str'>

### Methods

### `__init__(self, uri: str, edge: Dict[str, str] | None = None, reasoning: str = '') -> None`

Initialize self.  See help(type(self)) for accurate signature.


---

### `wire_triples_to_tuples(wire_triples: List[Dict[str, Any]]) -> List[Tuple[str, str, Any]]`

Convert wire-format triples to (s, p, o) tuples.


---

### `extract_term_value(term: Dict[str, Any]) -> Any`

Extract value from a wire-format Term dict.


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

## `Uri`

```python
from trustgraph.api import Uri
```

str(object='') -> str
str(bytes_or_buffer[, encoding[, errors]]) -> str

Create a new string object from the given object. If encoding or
errors is specified, then the object must expose a data buffer
that will be decoded using the given encoding and error handler.
Otherwise, returns the result of object.__str__() (if defined)
or repr(object).
encoding defaults to 'utf-8'.
errors defaults to 'strict'.

### Methods

### `is_literal(self)`

### `is_triple(self)`

### `is_uri(self)`


---

## `Literal`

```python
from trustgraph.api import Literal
```

str(object='') -> str
str(bytes_or_buffer[, encoding[, errors]]) -> str

Create a new string object from the given object. If encoding or
errors is specified, then the object must expose a data buffer
that will be decoded using the given encoding and error handler.
Otherwise, returns the result of object.__str__() (if defined)
or repr(object).
encoding defaults to 'utf-8'.
errors defaults to 'strict'.

### Methods

### `is_literal(self)`

### `is_triple(self)`

### `is_uri(self)`


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

**Attributes:**

- `parent_id: Parent document ID for child documents (empty for top`: level docs)

**Fields:**

- `id`: <class 'str'>
- `time`: <class 'datetime.datetime'>
- `kind`: <class 'str'>
- `title`: <class 'str'>
- `comments`: <class 'str'>
- `metadata`: typing.List[trustgraph.api.types.Triple]
- `user`: <class 'str'>
- `tags`: typing.List[str]
- `parent_id`: <class 'str'>
- `document_type`: <class 'str'>

### Methods

### `__init__(self, id: str, time: datetime.datetime, kind: str, title: str, comments: str, metadata: List[trustgraph.api.types.Triple], user: str, tags: List[str], parent_id: str = '', document_type: str = 'source') -> None`

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
- `error`: typing.Dict[str, str] | None

### Methods

### `__init__(self, content: str, end_of_message: bool = False, chunk_type: str = 'rag', end_of_stream: bool = False, error: Dict[str, str] | None = None) -> None`

Initialize self.  See help(type(self)) for accurate signature.


---

## `ProvenanceEvent`

```python
from trustgraph.api import ProvenanceEvent
```

Provenance event for explainability.

Emitted during GraphRAG queries when explainable mode is enabled.
Each event represents a provenance node created during query processing.

**Fields:**

- `explain_id`: <class 'str'>
- `explain_graph`: <class 'str'>
- `event_type`: <class 'str'>

### Methods

### `__init__(self, explain_id: str, explain_graph: str = '', event_type: str = '') -> None`

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

## `RowsQueryError`

```python
from trustgraph.api import RowsQueryError
```

Rows query service error


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

