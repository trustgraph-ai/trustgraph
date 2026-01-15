# Table of Contents

* [trustgraph.api.api](#trustgraph.api.api)
  * [check\_error](#trustgraph.api.api.check_error)
  * [Api](#trustgraph.api.api.Api)
    * [\_\_init\_\_](#trustgraph.api.api.Api.__init__)
    * [flow](#trustgraph.api.api.Api.flow)
    * [config](#trustgraph.api.api.Api.config)
    * [knowledge](#trustgraph.api.api.Api.knowledge)
    * [request](#trustgraph.api.api.Api.request)
    * [library](#trustgraph.api.api.Api.library)
    * [collection](#trustgraph.api.api.Api.collection)
    * [socket](#trustgraph.api.api.Api.socket)
    * [bulk](#trustgraph.api.api.Api.bulk)
    * [metrics](#trustgraph.api.api.Api.metrics)
    * [async\_flow](#trustgraph.api.api.Api.async_flow)
    * [async\_socket](#trustgraph.api.api.Api.async_socket)
    * [async\_bulk](#trustgraph.api.api.Api.async_bulk)
    * [async\_metrics](#trustgraph.api.api.Api.async_metrics)
    * [close](#trustgraph.api.api.Api.close)
    * [aclose](#trustgraph.api.api.Api.aclose)
    * [\_\_enter\_\_](#trustgraph.api.api.Api.__enter__)
    * [\_\_exit\_\_](#trustgraph.api.api.Api.__exit__)
    * [\_\_aenter\_\_](#trustgraph.api.api.Api.__aenter__)
    * [\_\_aexit\_\_](#trustgraph.api.api.Api.__aexit__)
* [trustgraph.api.flow](#trustgraph.api.flow)
  * [Triple](#trustgraph.api.flow.Triple)
  * [to\_value](#trustgraph.api.flow.to_value)
  * [FlowInstance](#trustgraph.api.flow.FlowInstance)
    * [\_\_init\_\_](#trustgraph.api.flow.FlowInstance.__init__)
    * [request](#trustgraph.api.flow.FlowInstance.request)
    * [text\_completion](#trustgraph.api.flow.FlowInstance.text_completion)
    * [agent](#trustgraph.api.flow.FlowInstance.agent)
    * [graph\_rag](#trustgraph.api.flow.FlowInstance.graph_rag)
    * [document\_rag](#trustgraph.api.flow.FlowInstance.document_rag)
    * [embeddings](#trustgraph.api.flow.FlowInstance.embeddings)
    * [graph\_embeddings\_query](#trustgraph.api.flow.FlowInstance.graph_embeddings_query)
    * [prompt](#trustgraph.api.flow.FlowInstance.prompt)
    * [mcp\_tool](#trustgraph.api.flow.FlowInstance.mcp_tool)
    * [triples\_query](#trustgraph.api.flow.FlowInstance.triples_query)
    * [load\_document](#trustgraph.api.flow.FlowInstance.load_document)
    * [load\_text](#trustgraph.api.flow.FlowInstance.load_text)
    * [objects\_query](#trustgraph.api.flow.FlowInstance.objects_query)
    * [nlp\_query](#trustgraph.api.flow.FlowInstance.nlp_query)
    * [structured\_query](#trustgraph.api.flow.FlowInstance.structured_query)
    * [detect\_type](#trustgraph.api.flow.FlowInstance.detect_type)
    * [generate\_descriptor](#trustgraph.api.flow.FlowInstance.generate_descriptor)
    * [diagnose\_data](#trustgraph.api.flow.FlowInstance.diagnose_data)
    * [schema\_selection](#trustgraph.api.flow.FlowInstance.schema_selection)
* [trustgraph.api.types](#trustgraph.api.types)
  * [Triple](#trustgraph.api.types.Triple)
    * [s](#trustgraph.api.types.Triple.s)
    * [p](#trustgraph.api.types.Triple.p)
    * [o](#trustgraph.api.types.Triple.o)
  * [ConfigKey](#trustgraph.api.types.ConfigKey)
    * [type](#trustgraph.api.types.ConfigKey.type)
    * [key](#trustgraph.api.types.ConfigKey.key)
  * [ConfigValue](#trustgraph.api.types.ConfigValue)
    * [type](#trustgraph.api.types.ConfigValue.type)
    * [key](#trustgraph.api.types.ConfigValue.key)
    * [value](#trustgraph.api.types.ConfigValue.value)
  * [DocumentMetadata](#trustgraph.api.types.DocumentMetadata)
    * [id](#trustgraph.api.types.DocumentMetadata.id)
    * [kind](#trustgraph.api.types.DocumentMetadata.kind)
    * [title](#trustgraph.api.types.DocumentMetadata.title)
    * [comments](#trustgraph.api.types.DocumentMetadata.comments)
    * [metadata](#trustgraph.api.types.DocumentMetadata.metadata)
    * [user](#trustgraph.api.types.DocumentMetadata.user)
    * [tags](#trustgraph.api.types.DocumentMetadata.tags)
  * [ProcessingMetadata](#trustgraph.api.types.ProcessingMetadata)
    * [id](#trustgraph.api.types.ProcessingMetadata.id)
    * [document\_id](#trustgraph.api.types.ProcessingMetadata.document_id)
    * [flow](#trustgraph.api.types.ProcessingMetadata.flow)
    * [user](#trustgraph.api.types.ProcessingMetadata.user)
    * [collection](#trustgraph.api.types.ProcessingMetadata.collection)
    * [tags](#trustgraph.api.types.ProcessingMetadata.tags)
  * [CollectionMetadata](#trustgraph.api.types.CollectionMetadata)
    * [user](#trustgraph.api.types.CollectionMetadata.user)
    * [collection](#trustgraph.api.types.CollectionMetadata.collection)
    * [name](#trustgraph.api.types.CollectionMetadata.name)
    * [description](#trustgraph.api.types.CollectionMetadata.description)
    * [tags](#trustgraph.api.types.CollectionMetadata.tags)
  * [StreamingChunk](#trustgraph.api.types.StreamingChunk)
    * [content](#trustgraph.api.types.StreamingChunk.content)
    * [end\_of\_message](#trustgraph.api.types.StreamingChunk.end_of_message)
  * [AgentThought](#trustgraph.api.types.AgentThought)
    * [chunk\_type](#trustgraph.api.types.AgentThought.chunk_type)
  * [AgentObservation](#trustgraph.api.types.AgentObservation)
    * [chunk\_type](#trustgraph.api.types.AgentObservation.chunk_type)
  * [AgentAnswer](#trustgraph.api.types.AgentAnswer)
    * [chunk\_type](#trustgraph.api.types.AgentAnswer.chunk_type)
    * [end\_of\_dialog](#trustgraph.api.types.AgentAnswer.end_of_dialog)
  * [RAGChunk](#trustgraph.api.types.RAGChunk)
    * [chunk\_type](#trustgraph.api.types.RAGChunk.chunk_type)
    * [end\_of\_stream](#trustgraph.api.types.RAGChunk.end_of_stream)
    * [error](#trustgraph.api.types.RAGChunk.error)
* [trustgraph.api.exceptions](#trustgraph.api.exceptions)
  * [TrustGraphException](#trustgraph.api.exceptions.TrustGraphException)
    * [\_\_init\_\_](#trustgraph.api.exceptions.TrustGraphException.__init__)
  * [AgentError](#trustgraph.api.exceptions.AgentError)
  * [ConfigError](#trustgraph.api.exceptions.ConfigError)
  * [DocumentRagError](#trustgraph.api.exceptions.DocumentRagError)
  * [FlowError](#trustgraph.api.exceptions.FlowError)
  * [GatewayError](#trustgraph.api.exceptions.GatewayError)
  * [GraphRagError](#trustgraph.api.exceptions.GraphRagError)
  * [LLMError](#trustgraph.api.exceptions.LLMError)
  * [LoadError](#trustgraph.api.exceptions.LoadError)
  * [LookupError](#trustgraph.api.exceptions.LookupError)
  * [NLPQueryError](#trustgraph.api.exceptions.NLPQueryError)
  * [ObjectsQueryError](#trustgraph.api.exceptions.ObjectsQueryError)
  * [RequestError](#trustgraph.api.exceptions.RequestError)
  * [StructuredQueryError](#trustgraph.api.exceptions.StructuredQueryError)
  * [UnexpectedError](#trustgraph.api.exceptions.UnexpectedError)
  * [ERROR\_TYPE\_MAPPING](#trustgraph.api.exceptions.ERROR_TYPE_MAPPING)
  * [raise\_from\_error\_dict](#trustgraph.api.exceptions.raise_from_error_dict)
* [trustgraph.api.socket\_client](#trustgraph.api.socket_client)
  * [Lock](#trustgraph.api.socket_client.Lock)
  * [AgentThought](#trustgraph.api.socket_client.AgentThought)
  * [AgentObservation](#trustgraph.api.socket_client.AgentObservation)
  * [AgentAnswer](#trustgraph.api.socket_client.AgentAnswer)
  * [RAGChunk](#trustgraph.api.socket_client.RAGChunk)
  * [StreamingChunk](#trustgraph.api.socket_client.StreamingChunk)
  * [raise\_from\_error\_dict](#trustgraph.api.socket_client.raise_from_error_dict)
  * [SocketClient](#trustgraph.api.socket_client.SocketClient)
    * [\_\_init\_\_](#trustgraph.api.socket_client.SocketClient.__init__)
    * [flow](#trustgraph.api.socket_client.SocketClient.flow)
    * [close](#trustgraph.api.socket_client.SocketClient.close)
  * [SocketFlowInstance](#trustgraph.api.socket_client.SocketFlowInstance)
    * [\_\_init\_\_](#trustgraph.api.socket_client.SocketFlowInstance.__init__)
    * [agent](#trustgraph.api.socket_client.SocketFlowInstance.agent)
    * [text\_completion](#trustgraph.api.socket_client.SocketFlowInstance.text_completion)
    * [graph\_rag](#trustgraph.api.socket_client.SocketFlowInstance.graph_rag)
    * [document\_rag](#trustgraph.api.socket_client.SocketFlowInstance.document_rag)
    * [prompt](#trustgraph.api.socket_client.SocketFlowInstance.prompt)
    * [graph\_embeddings\_query](#trustgraph.api.socket_client.SocketFlowInstance.graph_embeddings_query)
    * [embeddings](#trustgraph.api.socket_client.SocketFlowInstance.embeddings)
    * [triples\_query](#trustgraph.api.socket_client.SocketFlowInstance.triples_query)
    * [objects\_query](#trustgraph.api.socket_client.SocketFlowInstance.objects_query)
    * [mcp\_tool](#trustgraph.api.socket_client.SocketFlowInstance.mcp_tool)
* [trustgraph.api.async\_socket\_client](#trustgraph.api.async_socket_client)
  * [AgentThought](#trustgraph.api.async_socket_client.AgentThought)
  * [AgentObservation](#trustgraph.api.async_socket_client.AgentObservation)
  * [AgentAnswer](#trustgraph.api.async_socket_client.AgentAnswer)
  * [RAGChunk](#trustgraph.api.async_socket_client.RAGChunk)
  * [AsyncSocketClient](#trustgraph.api.async_socket_client.AsyncSocketClient)
    * [\_\_init\_\_](#trustgraph.api.async_socket_client.AsyncSocketClient.__init__)
    * [flow](#trustgraph.api.async_socket_client.AsyncSocketClient.flow)
    * [aclose](#trustgraph.api.async_socket_client.AsyncSocketClient.aclose)
  * [AsyncSocketFlowInstance](#trustgraph.api.async_socket_client.AsyncSocketFlowInstance)
    * [\_\_init\_\_](#trustgraph.api.async_socket_client.AsyncSocketFlowInstance.__init__)
    * [agent](#trustgraph.api.async_socket_client.AsyncSocketFlowInstance.agent)
    * [text\_completion](#trustgraph.api.async_socket_client.AsyncSocketFlowInstance.text_completion)
    * [graph\_rag](#trustgraph.api.async_socket_client.AsyncSocketFlowInstance.graph_rag)
    * [document\_rag](#trustgraph.api.async_socket_client.AsyncSocketFlowInstance.document_rag)
    * [prompt](#trustgraph.api.async_socket_client.AsyncSocketFlowInstance.prompt)
    * [graph\_embeddings\_query](#trustgraph.api.async_socket_client.AsyncSocketFlowInstance.graph_embeddings_query)
    * [embeddings](#trustgraph.api.async_socket_client.AsyncSocketFlowInstance.embeddings)
    * [triples\_query](#trustgraph.api.async_socket_client.AsyncSocketFlowInstance.triples_query)
    * [objects\_query](#trustgraph.api.async_socket_client.AsyncSocketFlowInstance.objects_query)
    * [mcp\_tool](#trustgraph.api.async_socket_client.AsyncSocketFlowInstance.mcp_tool)
* [trustgraph.api.bulk\_client](#trustgraph.api.bulk_client)
  * [Triple](#trustgraph.api.bulk_client.Triple)
  * [BulkClient](#trustgraph.api.bulk_client.BulkClient)
    * [\_\_init\_\_](#trustgraph.api.bulk_client.BulkClient.__init__)
    * [import\_triples](#trustgraph.api.bulk_client.BulkClient.import_triples)
    * [export\_triples](#trustgraph.api.bulk_client.BulkClient.export_triples)
    * [import\_graph\_embeddings](#trustgraph.api.bulk_client.BulkClient.import_graph_embeddings)
    * [export\_graph\_embeddings](#trustgraph.api.bulk_client.BulkClient.export_graph_embeddings)
    * [import\_document\_embeddings](#trustgraph.api.bulk_client.BulkClient.import_document_embeddings)
    * [export\_document\_embeddings](#trustgraph.api.bulk_client.BulkClient.export_document_embeddings)
    * [import\_entity\_contexts](#trustgraph.api.bulk_client.BulkClient.import_entity_contexts)
    * [export\_entity\_contexts](#trustgraph.api.bulk_client.BulkClient.export_entity_contexts)
    * [import\_objects](#trustgraph.api.bulk_client.BulkClient.import_objects)
    * [close](#trustgraph.api.bulk_client.BulkClient.close)
* [trustgraph.api.async\_bulk\_client](#trustgraph.api.async_bulk_client)
  * [Triple](#trustgraph.api.async_bulk_client.Triple)
  * [AsyncBulkClient](#trustgraph.api.async_bulk_client.AsyncBulkClient)
    * [\_\_init\_\_](#trustgraph.api.async_bulk_client.AsyncBulkClient.__init__)
    * [import\_triples](#trustgraph.api.async_bulk_client.AsyncBulkClient.import_triples)
    * [export\_triples](#trustgraph.api.async_bulk_client.AsyncBulkClient.export_triples)
    * [import\_graph\_embeddings](#trustgraph.api.async_bulk_client.AsyncBulkClient.import_graph_embeddings)
    * [export\_graph\_embeddings](#trustgraph.api.async_bulk_client.AsyncBulkClient.export_graph_embeddings)
    * [import\_document\_embeddings](#trustgraph.api.async_bulk_client.AsyncBulkClient.import_document_embeddings)
    * [export\_document\_embeddings](#trustgraph.api.async_bulk_client.AsyncBulkClient.export_document_embeddings)
    * [import\_entity\_contexts](#trustgraph.api.async_bulk_client.AsyncBulkClient.import_entity_contexts)
    * [export\_entity\_contexts](#trustgraph.api.async_bulk_client.AsyncBulkClient.export_entity_contexts)
    * [import\_objects](#trustgraph.api.async_bulk_client.AsyncBulkClient.import_objects)
    * [aclose](#trustgraph.api.async_bulk_client.AsyncBulkClient.aclose)
* [trustgraph.api.metrics](#trustgraph.api.metrics)
  * [Metrics](#trustgraph.api.metrics.Metrics)
    * [\_\_init\_\_](#trustgraph.api.metrics.Metrics.__init__)
    * [get](#trustgraph.api.metrics.Metrics.get)
* [trustgraph.api.async\_metrics](#trustgraph.api.async_metrics)
  * [AsyncMetrics](#trustgraph.api.async_metrics.AsyncMetrics)
    * [\_\_init\_\_](#trustgraph.api.async_metrics.AsyncMetrics.__init__)
    * [get](#trustgraph.api.async_metrics.AsyncMetrics.get)
    * [aclose](#trustgraph.api.async_metrics.AsyncMetrics.aclose)
* [trustgraph.api.async\_flow](#trustgraph.api.async_flow)
  * [check\_error](#trustgraph.api.async_flow.check_error)
  * [AsyncFlow](#trustgraph.api.async_flow.AsyncFlow)
    * [\_\_init\_\_](#trustgraph.api.async_flow.AsyncFlow.__init__)
    * [request](#trustgraph.api.async_flow.AsyncFlow.request)
    * [list](#trustgraph.api.async_flow.AsyncFlow.list)
    * [get](#trustgraph.api.async_flow.AsyncFlow.get)
    * [start](#trustgraph.api.async_flow.AsyncFlow.start)
    * [stop](#trustgraph.api.async_flow.AsyncFlow.stop)
    * [list\_classes](#trustgraph.api.async_flow.AsyncFlow.list_classes)
    * [get\_class](#trustgraph.api.async_flow.AsyncFlow.get_class)
    * [put\_class](#trustgraph.api.async_flow.AsyncFlow.put_class)
    * [delete\_class](#trustgraph.api.async_flow.AsyncFlow.delete_class)
    * [id](#trustgraph.api.async_flow.AsyncFlow.id)
    * [aclose](#trustgraph.api.async_flow.AsyncFlow.aclose)
  * [AsyncFlowInstance](#trustgraph.api.async_flow.AsyncFlowInstance)
    * [\_\_init\_\_](#trustgraph.api.async_flow.AsyncFlowInstance.__init__)
    * [request](#trustgraph.api.async_flow.AsyncFlowInstance.request)
    * [agent](#trustgraph.api.async_flow.AsyncFlowInstance.agent)
    * [text\_completion](#trustgraph.api.async_flow.AsyncFlowInstance.text_completion)
    * [graph\_rag](#trustgraph.api.async_flow.AsyncFlowInstance.graph_rag)
    * [document\_rag](#trustgraph.api.async_flow.AsyncFlowInstance.document_rag)
    * [graph\_embeddings\_query](#trustgraph.api.async_flow.AsyncFlowInstance.graph_embeddings_query)
    * [embeddings](#trustgraph.api.async_flow.AsyncFlowInstance.embeddings)
    * [triples\_query](#trustgraph.api.async_flow.AsyncFlowInstance.triples_query)
    * [objects\_query](#trustgraph.api.async_flow.AsyncFlowInstance.objects_query)

<a id="trustgraph.api.api"></a>

# trustgraph.api.api

TrustGraph API Client

Core API client for interacting with TrustGraph services via REST and WebSocket protocols.

<a id="trustgraph.api.api.check_error"></a>

#### check\_error

```python
def check_error(response)
```

<a id="trustgraph.api.api.Api"></a>

## Api Objects

```python
class Api()
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

**Attributes**:

- `url` - Base URL for the TrustGraph API endpoint
- `timeout` - Request timeout in seconds
- `token` - Optional bearer token for authentication

<a id="trustgraph.api.api.Api.__init__"></a>

#### \_\_init\_\_

```python
def __init__(url="http://localhost:8088/",
             timeout=60,
             token: Optional[str] = None)
```

Initialize the TrustGraph API client.

**Arguments**:

- `url` - Base URL for TrustGraph API (default: "http://localhost:8088/")
- `timeout` - Request timeout in seconds (default: 60)
- `token` - Optional bearer token for authentication
  

**Example**:

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

<a id="trustgraph.api.api.Api.flow"></a>

#### flow

```python
def flow()
```

Get a Flow client for managing and interacting with flows.

Flows are the primary execution units in TrustGraph, providing access to
services like agents, RAG queries, embeddings, and document processing.

**Returns**:

- `Flow` - Flow management client
  

**Example**:

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

<a id="trustgraph.api.api.Api.config"></a>

#### config

```python
def config()
```

Get a Config client for managing configuration settings.

**Returns**:

- `Config` - Configuration management client
  

**Example**:

    ```python
    config = api.config()

    # Get configuration values
    values = config.get([ConfigKey(type="llm", key="model")])

    # Set configuration
    config.put([ConfigValue(type="llm", key="model", value="gpt-4")])
    ```

<a id="trustgraph.api.api.Api.knowledge"></a>

#### knowledge

```python
def knowledge()
```

Get a Knowledge client for managing knowledge graph cores.

**Returns**:

- `Knowledge` - Knowledge graph management client
  

**Example**:

    ```python
    knowledge = api.knowledge()

    # List available KG cores
    cores = knowledge.list_kg_cores(user="trustgraph")

    # Load a KG core
    knowledge.load_kg_core(id="core-123", user="trustgraph")
    ```

<a id="trustgraph.api.api.Api.request"></a>

#### request

```python
def request(path, request)
```

Make a low-level REST API request.

This method is primarily for internal use but can be used for direct
API access when needed.

**Arguments**:

- `path` - API endpoint path (relative to base URL)
- `request` - Request payload as a dictionary
  

**Returns**:

- `dict` - Response object
  

**Raises**:

- `ProtocolException` - If the response status is not 200 or response is not JSON
- `ApplicationException` - If the response contains an error
  

**Example**:

    ```python
    response = api.request("flow", {
        "operation": "list-flows"
    })
    ```

<a id="trustgraph.api.api.Api.library"></a>

#### library

```python
def library()
```

Get a Library client for document management.

The library provides document storage, metadata management, and
processing workflow coordination.

**Returns**:

- `Library` - Document library management client
  

**Example**:

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

<a id="trustgraph.api.api.Api.collection"></a>

#### collection

```python
def collection()
```

Get a Collection client for managing data collections.

Collections organize documents and knowledge graph data into
logical groupings for isolation and access control.

**Returns**:

- `Collection` - Collection management client
  

**Example**:

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

<a id="trustgraph.api.api.Api.socket"></a>

#### socket

```python
def socket()
```

Get a synchronous WebSocket client for streaming operations.

WebSocket connections provide streaming support for real-time responses
from agents, RAG queries, and text completions. This method returns a
synchronous wrapper around the WebSocket protocol.

**Returns**:

- `SocketClient` - Synchronous WebSocket client
  

**Example**:

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

<a id="trustgraph.api.api.Api.bulk"></a>

#### bulk

```python
def bulk()
```

Get a synchronous bulk operations client for import/export.

Bulk operations allow efficient transfer of large datasets via WebSocket
connections, including triples, embeddings, entity contexts, and objects.

**Returns**:

- `BulkClient` - Synchronous bulk operations client
  

**Example**:

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

<a id="trustgraph.api.api.Api.metrics"></a>

#### metrics

```python
def metrics()
```

Get a synchronous metrics client for monitoring.

Retrieves Prometheus-formatted metrics from the TrustGraph service
for monitoring and observability.

**Returns**:

- `Metrics` - Synchronous metrics client
  

**Example**:

    ```python
    metrics = api.metrics()
    prometheus_text = metrics.get()
    print(prometheus_text)
    ```

<a id="trustgraph.api.api.Api.async_flow"></a>

#### async\_flow

```python
def async_flow()
```

Get an asynchronous REST-based flow client.

Provides async/await style access to flow operations. This is preferred
for async Python applications and frameworks (FastAPI, aiohttp, etc.).

**Returns**:

- `AsyncFlow` - Asynchronous flow client
  

**Example**:

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

<a id="trustgraph.api.api.Api.async_socket"></a>

#### async\_socket

```python
def async_socket()
```

Get an asynchronous WebSocket client for streaming operations.

Provides async/await style WebSocket access with streaming support.
This is the preferred method for async streaming in Python.

**Returns**:

- `AsyncSocketClient` - Asynchronous WebSocket client
  

**Example**:

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

<a id="trustgraph.api.api.Api.async_bulk"></a>

#### async\_bulk

```python
def async_bulk()
```

Get an asynchronous bulk operations client.

Provides async/await style bulk import/export operations via WebSocket
for efficient handling of large datasets.

**Returns**:

- `AsyncBulkClient` - Asynchronous bulk operations client
  

**Example**:

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

<a id="trustgraph.api.api.Api.async_metrics"></a>

#### async\_metrics

```python
def async_metrics()
```

Get an asynchronous metrics client.

Provides async/await style access to Prometheus metrics.

**Returns**:

- `AsyncMetrics` - Asynchronous metrics client
  

**Example**:

    ```python
    async_metrics = api.async_metrics()
    prometheus_text = await async_metrics.get()
    print(prometheus_text)
    ```

<a id="trustgraph.api.api.Api.close"></a>

#### close

```python
def close()
```

Close all synchronous client connections.

This method closes WebSocket and bulk operation connections.
It is automatically called when exiting a context manager.

**Example**:

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

<a id="trustgraph.api.api.Api.aclose"></a>

#### aclose

```python
async def aclose()
```

Close all asynchronous client connections.

This method closes async WebSocket, bulk operation, and flow connections.
It is automatically called when exiting an async context manager.

**Example**:

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

<a id="trustgraph.api.api.Api.__enter__"></a>

#### \_\_enter\_\_

```python
def __enter__()
```

Enter synchronous context manager.

<a id="trustgraph.api.api.Api.__exit__"></a>

#### \_\_exit\_\_

```python
def __exit__(*args)
```

Exit synchronous context manager and close connections.

<a id="trustgraph.api.api.Api.__aenter__"></a>

#### \_\_aenter\_\_

```python
async def __aenter__()
```

Enter asynchronous context manager.

<a id="trustgraph.api.api.Api.__aexit__"></a>

#### \_\_aexit\_\_

```python
async def __aexit__(*args)
```

Exit asynchronous context manager and close connections.

<a id="trustgraph.api.flow"></a>

# trustgraph.api.flow

TrustGraph Flow Management

This module provides interfaces for managing and executing TrustGraph flows.
Flows are the primary execution units that provide access to various services
including LLM operations, RAG queries, knowledge graph management, and more.

<a id="trustgraph.api.flow.Triple"></a>

## Triple

<a id="trustgraph.api.flow.to_value"></a>

#### to\_value

```python
def to_value(x)
```

<a id="trustgraph.api.flow.FlowInstance"></a>

## FlowInstance Objects

```python
class FlowInstance()
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

<a id="trustgraph.api.flow.FlowInstance.__init__"></a>

#### \_\_init\_\_

```python
def __init__(api, id)
```

Initialize FlowInstance.

**Arguments**:

- `api` - Parent Flow client
- `id` - Flow instance identifier

<a id="trustgraph.api.flow.FlowInstance.request"></a>

#### request

```python
def request(path, request)
```

Make a service request on this flow instance.

**Arguments**:

- `path` - Service path (e.g., "service/text-completion")
- `request` - Request payload dictionary
  

**Returns**:

- `dict` - Service response

<a id="trustgraph.api.flow.FlowInstance.text_completion"></a>

#### text\_completion

```python
def text_completion(system, prompt)
```

Execute text completion using the flow's LLM.

**Arguments**:

- `system` - System prompt defining the assistant's behavior
- `prompt` - User prompt/question
  

**Returns**:

- `str` - Generated response text
  

**Example**:

    ```python
    flow = api.flow().id("default")
    response = flow.text_completion(
        system="You are a helpful assistant",
        prompt="What is quantum computing?"
    )
    print(response)
    ```

<a id="trustgraph.api.flow.FlowInstance.agent"></a>

#### agent

```python
def agent(question, user="trustgraph", state=None, group=None, history=None)
```

Execute an agent operation with reasoning and tool use capabilities.

Agents can perform multi-step reasoning, use tools, and maintain conversation
state across interactions. This is a synchronous non-streaming version.

**Arguments**:

- `question` - User question or instruction
- `user` - User identifier (default: "trustgraph")
- `state` - Optional state dictionary for stateful conversations
- `group` - Optional group identifier for multi-user contexts
- `history` - Optional conversation history as list of message dicts
  

**Returns**:

- `str` - Agent's final answer
  

**Example**:

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

<a id="trustgraph.api.flow.FlowInstance.graph_rag"></a>

#### graph\_rag

```python
def graph_rag(query,
              user="trustgraph",
              collection="default",
              entity_limit=50,
              triple_limit=30,
              max_subgraph_size=150,
              max_path_length=2)
```

Execute graph-based Retrieval-Augmented Generation (RAG) query.

Graph RAG uses knowledge graph structure to find relevant context by
traversing entity relationships, then generates a response using an LLM.

**Arguments**:

- `query` - Natural language query
- `user` - User/keyspace identifier (default: "trustgraph")
- `collection` - Collection identifier (default: "default")
- `entity_limit` - Maximum entities to retrieve (default: 50)
- `triple_limit` - Maximum triples per entity (default: 30)
- `max_subgraph_size` - Maximum total triples in subgraph (default: 150)
- `max_path_length` - Maximum traversal depth (default: 2)
  

**Returns**:

- `str` - Generated response incorporating graph context
  

**Example**:

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

<a id="trustgraph.api.flow.FlowInstance.document_rag"></a>

#### document\_rag

```python
def document_rag(query, user="trustgraph", collection="default", doc_limit=10)
```

Execute document-based Retrieval-Augmented Generation (RAG) query.

Document RAG uses vector embeddings to find relevant document chunks,
then generates a response using an LLM with those chunks as context.

**Arguments**:

- `query` - Natural language query
- `user` - User/keyspace identifier (default: "trustgraph")
- `collection` - Collection identifier (default: "default")
- `doc_limit` - Maximum document chunks to retrieve (default: 10)
  

**Returns**:

- `str` - Generated response incorporating document context
  

**Example**:

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

<a id="trustgraph.api.flow.FlowInstance.embeddings"></a>

#### embeddings

```python
def embeddings(text)
```

Generate vector embeddings for text.

Converts text into dense vector representations suitable for semantic
search and similarity comparison.

**Arguments**:

- `text` - Input text to embed
  

**Returns**:

- `list[float]` - Vector embedding
  

**Example**:

    ```python
    flow = api.flow().id("default")
    vectors = flow.embeddings("quantum computing")
    print(f"Embedding dimension: {len(vectors)}")
    ```

<a id="trustgraph.api.flow.FlowInstance.graph_embeddings_query"></a>

#### graph\_embeddings\_query

```python
def graph_embeddings_query(text, user, collection, limit=10)
```

Query knowledge graph entities using semantic similarity.

Finds entities in the knowledge graph whose descriptions are semantically
similar to the input text, using vector embeddings.

**Arguments**:

- `text` - Query text for semantic search
- `user` - User/keyspace identifier
- `collection` - Collection identifier
- `limit` - Maximum number of results (default: 10)
  

**Returns**:

- `dict` - Query results with similar entities
  

**Example**:

    ```python
    flow = api.flow().id("default")
    results = flow.graph_embeddings_query(
        text="physicist who discovered radioactivity",
        user="trustgraph",
        collection="scientists",
        limit=5
    )
    ```

<a id="trustgraph.api.flow.FlowInstance.prompt"></a>

#### prompt

```python
def prompt(id, variables)
```

Execute a prompt template with variable substitution.

Prompt templates allow reusable prompt patterns with dynamic variable
substitution, useful for consistent prompt engineering.

**Arguments**:

- `id` - Prompt template identifier
- `variables` - Dictionary of variable name to value mappings
  

**Returns**:

  str or dict: Rendered prompt result (text or structured object)
  

**Raises**:

- `ProtocolException` - If response format is invalid
  

**Example**:

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

<a id="trustgraph.api.flow.FlowInstance.mcp_tool"></a>

#### mcp\_tool

```python
def mcp_tool(name, parameters={})
```

Execute a Model Context Protocol (MCP) tool.

MCP tools provide extensible functionality for agents and workflows,
allowing integration with external systems and services.

**Arguments**:

- `name` - Tool name/identifier
- `parameters` - Tool parameters dictionary (default: {})
  

**Returns**:

  str or dict: Tool execution result
  

**Raises**:

- `ProtocolException` - If response format is invalid
  

**Example**:

    ```python
    flow = api.flow().id("default")

    # Execute a tool
    result = flow.mcp_tool(
        name="search-web",
        parameters={"query": "latest AI news", "limit": 5}
    )
    ```

<a id="trustgraph.api.flow.FlowInstance.triples_query"></a>

#### triples\_query

```python
def triples_query(s=None,
                  p=None,
                  o=None,
                  user=None,
                  collection=None,
                  limit=10000)
```

Query knowledge graph triples using pattern matching.

Searches for RDF triples matching the given subject, predicate, and/or
object patterns. Unspecified parameters act as wildcards.

**Arguments**:

- `s` - Subject URI (optional, use None for wildcard)
- `p` - Predicate URI (optional, use None for wildcard)
- `o` - Object URI or Literal (optional, use None for wildcard)
- `user` - User/keyspace identifier (optional)
- `collection` - Collection identifier (optional)
- `limit` - Maximum results to return (default: 10000)
  

**Returns**:

- `list[Triple]` - List of matching Triple objects
  

**Raises**:

- `RuntimeError` - If s or p is not a Uri, or o is not Uri/Literal
  

**Example**:

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

<a id="trustgraph.api.flow.FlowInstance.load_document"></a>

#### load\_document

```python
def load_document(document,
                  id=None,
                  metadata=None,
                  user=None,
                  collection=None)
```

Load a binary document for processing.

Uploads a document (PDF, DOCX, images, etc.) for extraction and
processing through the flow's document pipeline.

**Arguments**:

- `document` - Document content as bytes
- `id` - Optional document identifier (auto-generated if None)
- `metadata` - Optional metadata (list of Triples or object with emit method)
- `user` - User/keyspace identifier (optional)
- `collection` - Collection identifier (optional)
  

**Returns**:

- `dict` - Processing response
  

**Raises**:

- `RuntimeError` - If metadata is provided without id
  

**Example**:

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

<a id="trustgraph.api.flow.FlowInstance.load_text"></a>

#### load\_text

```python
def load_text(text,
              id=None,
              metadata=None,
              charset="utf-8",
              user=None,
              collection=None)
```

Load text content for processing.

Uploads text content for extraction and processing through the flow's
text pipeline.

**Arguments**:

- `text` - Text content as bytes
- `id` - Optional document identifier (auto-generated if None)
- `metadata` - Optional metadata (list of Triples or object with emit method)
- `charset` - Character encoding (default: "utf-8")
- `user` - User/keyspace identifier (optional)
- `collection` - Collection identifier (optional)
  

**Returns**:

- `dict` - Processing response
  

**Raises**:

- `RuntimeError` - If metadata is provided without id
  

**Example**:

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

<a id="trustgraph.api.flow.FlowInstance.objects_query"></a>

#### objects\_query

```python
def objects_query(query,
                  user="trustgraph",
                  collection="default",
                  variables=None,
                  operation_name=None)
```

Execute a GraphQL query against structured objects in the knowledge graph.

Queries structured data using GraphQL syntax, allowing complex queries
with filtering, aggregation, and relationship traversal.

**Arguments**:

- `query` - GraphQL query string
- `user` - User/keyspace identifier (default: "trustgraph")
- `collection` - Collection identifier (default: "default")
- `variables` - Optional query variables dictionary
- `operation_name` - Optional operation name for multi-operation documents
  

**Returns**:

- `dict` - GraphQL response with 'data', 'errors', and/or 'extensions' fields
  

**Raises**:

- `ProtocolException` - If system-level error occurs
  

**Example**:

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

<a id="trustgraph.api.flow.FlowInstance.nlp_query"></a>

#### nlp\_query

```python
def nlp_query(question, max_results=100)
```

Convert a natural language question to a GraphQL query.

**Arguments**:

- `question` - Natural language question
- `max_results` - Maximum number of results to return (default: 100)
  

**Returns**:

  dict with graphql_query, variables, detected_schemas, confidence

<a id="trustgraph.api.flow.FlowInstance.structured_query"></a>

#### structured\_query

```python
def structured_query(question, user="trustgraph", collection="default")
```

Execute a natural language question against structured data.
Combines NLP query conversion and GraphQL execution.

**Arguments**:

- `question` - Natural language question
- `user` - Cassandra keyspace identifier (default: "trustgraph")
- `collection` - Data collection identifier (default: "default")
  

**Returns**:

  dict with data and optional errors

<a id="trustgraph.api.flow.FlowInstance.detect_type"></a>

#### detect\_type

```python
def detect_type(sample)
```

Detect the data type of a structured data sample.

**Arguments**:

- `sample` - Data sample to analyze (string content)
  

**Returns**:

  dict with detected_type, confidence, and optional metadata

<a id="trustgraph.api.flow.FlowInstance.generate_descriptor"></a>

#### generate\_descriptor

```python
def generate_descriptor(sample, data_type, schema_name, options=None)
```

Generate a descriptor for structured data mapping to a specific schema.

**Arguments**:

- `sample` - Data sample to analyze (string content)
- `data_type` - Data type (csv, json, xml)
- `schema_name` - Target schema name for descriptor generation
- `options` - Optional parameters (e.g., delimiter for CSV)
  

**Returns**:

  dict with descriptor and metadata

<a id="trustgraph.api.flow.FlowInstance.diagnose_data"></a>

#### diagnose\_data

```python
def diagnose_data(sample, schema_name=None, options=None)
```

Perform combined data diagnosis: detect type and generate descriptor.

**Arguments**:

- `sample` - Data sample to analyze (string content)
- `schema_name` - Optional target schema name for descriptor generation
- `options` - Optional parameters (e.g., delimiter for CSV)
  

**Returns**:

  dict with detected_type, confidence, descriptor, and metadata

<a id="trustgraph.api.flow.FlowInstance.schema_selection"></a>

#### schema\_selection

```python
def schema_selection(sample, options=None)
```

Select matching schemas for a data sample using prompt analysis.

**Arguments**:

- `sample` - Data sample to analyze (string content)
- `options` - Optional parameters
  

**Returns**:

  dict with schema_matches array and metadata

<a id="trustgraph.api.types"></a>

# trustgraph.api.types

TrustGraph API Type Definitions

Data classes and type definitions for TrustGraph API objects including knowledge
graph elements, metadata structures, and streaming response chunks.

<a id="trustgraph.api.types.Triple"></a>

## Triple Objects

```python
@dataclasses.dataclass
class Triple()
```

RDF triple representing a knowledge graph statement.

**Attributes**:

- `s` - Subject (entity URI or value)
- `p` - Predicate (relationship URI)
- `o` - Object (entity URI, literal value, or typed value)

<a id="trustgraph.api.types.Triple.s"></a>

#### s

<a id="trustgraph.api.types.Triple.p"></a>

#### p

<a id="trustgraph.api.types.Triple.o"></a>

#### o

<a id="trustgraph.api.types.ConfigKey"></a>

## ConfigKey Objects

```python
@dataclasses.dataclass
class ConfigKey()
```

Configuration key identifier.

**Attributes**:

- `type` - Configuration type/category (e.g., "llm", "embedding")
- `key` - Specific configuration key within the type

<a id="trustgraph.api.types.ConfigKey.type"></a>

#### type

<a id="trustgraph.api.types.ConfigKey.key"></a>

#### key

<a id="trustgraph.api.types.ConfigValue"></a>

## ConfigValue Objects

```python
@dataclasses.dataclass
class ConfigValue()
```

Configuration key-value pair.

**Attributes**:

- `type` - Configuration type/category
- `key` - Specific configuration key
- `value` - Configuration value as string

<a id="trustgraph.api.types.ConfigValue.type"></a>

#### type

<a id="trustgraph.api.types.ConfigValue.key"></a>

#### key

<a id="trustgraph.api.types.ConfigValue.value"></a>

#### value

<a id="trustgraph.api.types.DocumentMetadata"></a>

## DocumentMetadata Objects

```python
@dataclasses.dataclass
class DocumentMetadata()
```

Metadata for a document in the library.

**Attributes**:

- `id` - Unique document identifier
- `time` - Document creation/upload timestamp
- `kind` - Document MIME type (e.g., "application/pdf", "text/plain")
- `title` - Document title
- `comments` - Additional comments or description
- `metadata` - List of RDF triples providing structured metadata
- `user` - User/owner identifier
- `tags` - List of tags for categorization

<a id="trustgraph.api.types.DocumentMetadata.id"></a>

#### id

<a id="trustgraph.api.types.DocumentMetadata.kind"></a>

#### kind

<a id="trustgraph.api.types.DocumentMetadata.title"></a>

#### title

<a id="trustgraph.api.types.DocumentMetadata.comments"></a>

#### comments

<a id="trustgraph.api.types.DocumentMetadata.metadata"></a>

#### metadata

<a id="trustgraph.api.types.DocumentMetadata.user"></a>

#### user

<a id="trustgraph.api.types.DocumentMetadata.tags"></a>

#### tags

<a id="trustgraph.api.types.ProcessingMetadata"></a>

## ProcessingMetadata Objects

```python
@dataclasses.dataclass
class ProcessingMetadata()
```

Metadata for an active document processing job.

**Attributes**:

- `id` - Unique processing job identifier
- `document_id` - ID of the document being processed
- `time` - Processing start timestamp
- `flow` - Flow instance handling the processing
- `user` - User identifier
- `collection` - Target collection for processed data
- `tags` - List of tags for categorization

<a id="trustgraph.api.types.ProcessingMetadata.id"></a>

#### id

<a id="trustgraph.api.types.ProcessingMetadata.document_id"></a>

#### document\_id

<a id="trustgraph.api.types.ProcessingMetadata.flow"></a>

#### flow

<a id="trustgraph.api.types.ProcessingMetadata.user"></a>

#### user

<a id="trustgraph.api.types.ProcessingMetadata.collection"></a>

#### collection

<a id="trustgraph.api.types.ProcessingMetadata.tags"></a>

#### tags

<a id="trustgraph.api.types.CollectionMetadata"></a>

## CollectionMetadata Objects

```python
@dataclasses.dataclass
class CollectionMetadata()
```

Metadata for a data collection.

Collections provide logical grouping and isolation for documents and
knowledge graph data.

**Attributes**:

- `user` - User/owner identifier
- `collection` - Collection identifier
- `name` - Human-readable collection name
- `description` - Collection description
- `tags` - List of tags for categorization

<a id="trustgraph.api.types.CollectionMetadata.user"></a>

#### user

<a id="trustgraph.api.types.CollectionMetadata.collection"></a>

#### collection

<a id="trustgraph.api.types.CollectionMetadata.name"></a>

#### name

<a id="trustgraph.api.types.CollectionMetadata.description"></a>

#### description

<a id="trustgraph.api.types.CollectionMetadata.tags"></a>

#### tags

<a id="trustgraph.api.types.StreamingChunk"></a>

## StreamingChunk Objects

```python
@dataclasses.dataclass
class StreamingChunk()
```

Base class for streaming response chunks.

Used for WebSocket-based streaming operations where responses are delivered
incrementally as they are generated.

**Attributes**:

- `content` - The text content of this chunk
- `end_of_message` - True if this is the final chunk of a message segment

<a id="trustgraph.api.types.StreamingChunk.content"></a>

#### content

<a id="trustgraph.api.types.StreamingChunk.end_of_message"></a>

#### end\_of\_message

<a id="trustgraph.api.types.AgentThought"></a>

## AgentThought Objects

```python
@dataclasses.dataclass
class AgentThought(StreamingChunk)
```

Agent reasoning/thought process chunk.

Represents the agent's internal reasoning or planning steps during execution.
These chunks show how the agent is thinking about the problem.

**Attributes**:

- `content` - Agent's thought text
- `end_of_message` - True if this completes the current thought
- `chunk_type` - Always "thought"

<a id="trustgraph.api.types.AgentThought.chunk_type"></a>

#### chunk\_type

<a id="trustgraph.api.types.AgentObservation"></a>

## AgentObservation Objects

```python
@dataclasses.dataclass
class AgentObservation(StreamingChunk)
```

Agent tool execution observation chunk.

Represents the result or observation from executing a tool or action.
These chunks show what the agent learned from using tools.

**Attributes**:

- `content` - Observation text describing tool results
- `end_of_message` - True if this completes the current observation
- `chunk_type` - Always "observation"

<a id="trustgraph.api.types.AgentObservation.chunk_type"></a>

#### chunk\_type

<a id="trustgraph.api.types.AgentAnswer"></a>

## AgentAnswer Objects

```python
@dataclasses.dataclass
class AgentAnswer(StreamingChunk)
```

Agent final answer chunk.

Represents the agent's final response to the user's query after completing
its reasoning and tool use.

**Attributes**:

- `content` - Answer text
- `end_of_message` - True if this completes the current answer segment
- `end_of_dialog` - True if this completes the entire agent interaction
- `chunk_type` - Always "final-answer"

<a id="trustgraph.api.types.AgentAnswer.chunk_type"></a>

#### chunk\_type

<a id="trustgraph.api.types.AgentAnswer.end_of_dialog"></a>

#### end\_of\_dialog

<a id="trustgraph.api.types.RAGChunk"></a>

## RAGChunk Objects

```python
@dataclasses.dataclass
class RAGChunk(StreamingChunk)
```

RAG (Retrieval-Augmented Generation) streaming chunk.

Used for streaming responses from graph RAG, document RAG, text completion,
and other generative services.

**Attributes**:

- `content` - Generated text content
- `end_of_stream` - True if this is the final chunk of the stream
- `error` - Optional error information if an error occurred
- `chunk_type` - Always "rag"

<a id="trustgraph.api.types.RAGChunk.chunk_type"></a>

#### chunk\_type

<a id="trustgraph.api.types.RAGChunk.end_of_stream"></a>

#### end\_of\_stream

<a id="trustgraph.api.types.RAGChunk.error"></a>

#### error

<a id="trustgraph.api.exceptions"></a>

# trustgraph.api.exceptions

TrustGraph API Exceptions

Exception hierarchy for errors returned by TrustGraph services.
Each service error type maps to a specific exception class.

<a id="trustgraph.api.exceptions.TrustGraphException"></a>

## TrustGraphException Objects

```python
class TrustGraphException(Exception)
```

Base class for all TrustGraph service errors

<a id="trustgraph.api.exceptions.TrustGraphException.__init__"></a>

#### \_\_init\_\_

```python
def __init__(message: str, error_type: str = None)
```

<a id="trustgraph.api.exceptions.AgentError"></a>

## AgentError Objects

```python
class AgentError(TrustGraphException)
```

Agent service error

<a id="trustgraph.api.exceptions.ConfigError"></a>

## ConfigError Objects

```python
class ConfigError(TrustGraphException)
```

Configuration service error

<a id="trustgraph.api.exceptions.DocumentRagError"></a>

## DocumentRagError Objects

```python
class DocumentRagError(TrustGraphException)
```

Document RAG retrieval error

<a id="trustgraph.api.exceptions.FlowError"></a>

## FlowError Objects

```python
class FlowError(TrustGraphException)
```

Flow management error

<a id="trustgraph.api.exceptions.GatewayError"></a>

## GatewayError Objects

```python
class GatewayError(TrustGraphException)
```

API Gateway error

<a id="trustgraph.api.exceptions.GraphRagError"></a>

## GraphRagError Objects

```python
class GraphRagError(TrustGraphException)
```

Graph RAG retrieval error

<a id="trustgraph.api.exceptions.LLMError"></a>

## LLMError Objects

```python
class LLMError(TrustGraphException)
```

LLM service error

<a id="trustgraph.api.exceptions.LoadError"></a>

## LoadError Objects

```python
class LoadError(TrustGraphException)
```

Data loading error

<a id="trustgraph.api.exceptions.LookupError"></a>

## LookupError Objects

```python
class LookupError(TrustGraphException)
```

Lookup/search error

<a id="trustgraph.api.exceptions.NLPQueryError"></a>

## NLPQueryError Objects

```python
class NLPQueryError(TrustGraphException)
```

NLP query service error

<a id="trustgraph.api.exceptions.ObjectsQueryError"></a>

## ObjectsQueryError Objects

```python
class ObjectsQueryError(TrustGraphException)
```

Objects query service error

<a id="trustgraph.api.exceptions.RequestError"></a>

## RequestError Objects

```python
class RequestError(TrustGraphException)
```

Request processing error

<a id="trustgraph.api.exceptions.StructuredQueryError"></a>

## StructuredQueryError Objects

```python
class StructuredQueryError(TrustGraphException)
```

Structured query service error

<a id="trustgraph.api.exceptions.UnexpectedError"></a>

## UnexpectedError Objects

```python
class UnexpectedError(TrustGraphException)
```

Unexpected/unknown error

<a id="trustgraph.api.exceptions.ERROR_TYPE_MAPPING"></a>

#### ERROR\_TYPE\_MAPPING

<a id="trustgraph.api.exceptions.raise_from_error_dict"></a>

#### raise\_from\_error\_dict

```python
def raise_from_error_dict(error_dict: dict) -> None
```

Raise appropriate exception from TrustGraph error dictionary.

**Arguments**:

- `error_dict` - Dictionary with 'type' and 'message' keys
  

**Raises**:

  Appropriate TrustGraphException subclass based on error type

<a id="trustgraph.api.socket_client"></a>

# trustgraph.api.socket\_client

<a id="trustgraph.api.socket_client.Lock"></a>

## Lock

<a id="trustgraph.api.socket_client.AgentThought"></a>

## AgentThought

<a id="trustgraph.api.socket_client.AgentObservation"></a>

## AgentObservation

<a id="trustgraph.api.socket_client.AgentAnswer"></a>

## AgentAnswer

<a id="trustgraph.api.socket_client.RAGChunk"></a>

## RAGChunk

<a id="trustgraph.api.socket_client.StreamingChunk"></a>

## StreamingChunk

<a id="trustgraph.api.socket_client.raise_from_error_dict"></a>

## raise\_from\_error\_dict

<a id="trustgraph.api.socket_client.SocketClient"></a>

## SocketClient Objects

```python
class SocketClient()
```

Synchronous WebSocket client (wraps async websockets library)

<a id="trustgraph.api.socket_client.SocketClient.__init__"></a>

#### \_\_init\_\_

```python
def __init__(url: str, timeout: int, token: Optional[str]) -> None
```

<a id="trustgraph.api.socket_client.SocketClient.flow"></a>

#### flow

```python
def flow(flow_id: str) -> "SocketFlowInstance"
```

Get flow instance for WebSocket operations

<a id="trustgraph.api.socket_client.SocketClient.close"></a>

#### close

```python
def close() -> None
```

Close WebSocket connection

<a id="trustgraph.api.socket_client.SocketFlowInstance"></a>

## SocketFlowInstance Objects

```python
class SocketFlowInstance()
```

Synchronous WebSocket flow instance with same interface as REST FlowInstance

<a id="trustgraph.api.socket_client.SocketFlowInstance.__init__"></a>

#### \_\_init\_\_

```python
def __init__(client: SocketClient, flow_id: str) -> None
```

<a id="trustgraph.api.socket_client.SocketFlowInstance.agent"></a>

#### agent

```python
def agent(question: str,
          user: str,
          state: Optional[Dict[str, Any]] = None,
          group: Optional[str] = None,
          history: Optional[List[Dict[str, Any]]] = None,
          streaming: bool = False,
          **kwargs: Any) -> Union[Dict[str, Any], Iterator[StreamingChunk]]
```

Agent with optional streaming

<a id="trustgraph.api.socket_client.SocketFlowInstance.text_completion"></a>

#### text\_completion

```python
def text_completion(system: str,
                    prompt: str,
                    streaming: bool = False,
                    **kwargs) -> Union[str, Iterator[str]]
```

Text completion with optional streaming

<a id="trustgraph.api.socket_client.SocketFlowInstance.graph_rag"></a>

#### graph\_rag

```python
def graph_rag(query: str,
              user: str,
              collection: str,
              max_subgraph_size: int = 1000,
              max_subgraph_count: int = 5,
              max_entity_distance: int = 3,
              streaming: bool = False,
              **kwargs: Any) -> Union[str, Iterator[str]]
```

Graph RAG with optional streaming

<a id="trustgraph.api.socket_client.SocketFlowInstance.document_rag"></a>

#### document\_rag

```python
def document_rag(query: str,
                 user: str,
                 collection: str,
                 doc_limit: int = 10,
                 streaming: bool = False,
                 **kwargs: Any) -> Union[str, Iterator[str]]
```

Document RAG with optional streaming

<a id="trustgraph.api.socket_client.SocketFlowInstance.prompt"></a>

#### prompt

```python
def prompt(id: str,
           variables: Dict[str, str],
           streaming: bool = False,
           **kwargs: Any) -> Union[str, Iterator[str]]
```

Execute prompt with optional streaming

<a id="trustgraph.api.socket_client.SocketFlowInstance.graph_embeddings_query"></a>

#### graph\_embeddings\_query

```python
def graph_embeddings_query(text: str,
                           user: str,
                           collection: str,
                           limit: int = 10,
                           **kwargs: Any) -> Dict[str, Any]
```

Query graph embeddings for semantic search

<a id="trustgraph.api.socket_client.SocketFlowInstance.embeddings"></a>

#### embeddings

```python
def embeddings(text: str, **kwargs: Any) -> Dict[str, Any]
```

Generate text embeddings

<a id="trustgraph.api.socket_client.SocketFlowInstance.triples_query"></a>

#### triples\_query

```python
def triples_query(s: Optional[str] = None,
                  p: Optional[str] = None,
                  o: Optional[str] = None,
                  user: Optional[str] = None,
                  collection: Optional[str] = None,
                  limit: int = 100,
                  **kwargs: Any) -> Dict[str, Any]
```

Triple pattern query

<a id="trustgraph.api.socket_client.SocketFlowInstance.objects_query"></a>

#### objects\_query

```python
def objects_query(query: str,
                  user: str,
                  collection: str,
                  variables: Optional[Dict[str, Any]] = None,
                  operation_name: Optional[str] = None,
                  **kwargs: Any) -> Dict[str, Any]
```

GraphQL query

<a id="trustgraph.api.socket_client.SocketFlowInstance.mcp_tool"></a>

#### mcp\_tool

```python
def mcp_tool(name: str, parameters: Dict[str, Any],
             **kwargs: Any) -> Dict[str, Any]
```

Execute MCP tool

<a id="trustgraph.api.async_socket_client"></a>

# trustgraph.api.async\_socket\_client

<a id="trustgraph.api.async_socket_client.AgentThought"></a>

## AgentThought

<a id="trustgraph.api.async_socket_client.AgentObservation"></a>

## AgentObservation

<a id="trustgraph.api.async_socket_client.AgentAnswer"></a>

## AgentAnswer

<a id="trustgraph.api.async_socket_client.RAGChunk"></a>

## RAGChunk

<a id="trustgraph.api.async_socket_client.AsyncSocketClient"></a>

## AsyncSocketClient Objects

```python
class AsyncSocketClient()
```

Asynchronous WebSocket client

<a id="trustgraph.api.async_socket_client.AsyncSocketClient.__init__"></a>

#### \_\_init\_\_

```python
def __init__(url: str, timeout: int, token: Optional[str])
```

<a id="trustgraph.api.async_socket_client.AsyncSocketClient.flow"></a>

#### flow

```python
def flow(flow_id: str)
```

Get async flow instance for WebSocket operations

<a id="trustgraph.api.async_socket_client.AsyncSocketClient.aclose"></a>

#### aclose

```python
async def aclose()
```

Close WebSocket connection

<a id="trustgraph.api.async_socket_client.AsyncSocketFlowInstance"></a>

## AsyncSocketFlowInstance Objects

```python
class AsyncSocketFlowInstance()
```

Asynchronous WebSocket flow instance

<a id="trustgraph.api.async_socket_client.AsyncSocketFlowInstance.__init__"></a>

#### \_\_init\_\_

```python
def __init__(client: AsyncSocketClient, flow_id: str)
```

<a id="trustgraph.api.async_socket_client.AsyncSocketFlowInstance.agent"></a>

#### agent

```python
async def agent(question: str,
                user: str,
                state: Optional[Dict[str, Any]] = None,
                group: Optional[str] = None,
                history: Optional[list] = None,
                streaming: bool = False,
                **kwargs) -> Union[Dict[str, Any], AsyncIterator]
```

Agent with optional streaming

<a id="trustgraph.api.async_socket_client.AsyncSocketFlowInstance.text_completion"></a>

#### text\_completion

```python
async def text_completion(system: str,
                          prompt: str,
                          streaming: bool = False,
                          **kwargs)
```

Text completion with optional streaming

<a id="trustgraph.api.async_socket_client.AsyncSocketFlowInstance.graph_rag"></a>

#### graph\_rag

```python
async def graph_rag(query: str,
                    user: str,
                    collection: str,
                    max_subgraph_size: int = 1000,
                    max_subgraph_count: int = 5,
                    max_entity_distance: int = 3,
                    streaming: bool = False,
                    **kwargs)
```

Graph RAG with optional streaming

<a id="trustgraph.api.async_socket_client.AsyncSocketFlowInstance.document_rag"></a>

#### document\_rag

```python
async def document_rag(query: str,
                       user: str,
                       collection: str,
                       doc_limit: int = 10,
                       streaming: bool = False,
                       **kwargs)
```

Document RAG with optional streaming

<a id="trustgraph.api.async_socket_client.AsyncSocketFlowInstance.prompt"></a>

#### prompt

```python
async def prompt(id: str,
                 variables: Dict[str, str],
                 streaming: bool = False,
                 **kwargs)
```

Execute prompt with optional streaming

<a id="trustgraph.api.async_socket_client.AsyncSocketFlowInstance.graph_embeddings_query"></a>

#### graph\_embeddings\_query

```python
async def graph_embeddings_query(text: str,
                                 user: str,
                                 collection: str,
                                 limit: int = 10,
                                 **kwargs)
```

Query graph embeddings for semantic search

<a id="trustgraph.api.async_socket_client.AsyncSocketFlowInstance.embeddings"></a>

#### embeddings

```python
async def embeddings(text: str, **kwargs)
```

Generate text embeddings

<a id="trustgraph.api.async_socket_client.AsyncSocketFlowInstance.triples_query"></a>

#### triples\_query

```python
async def triples_query(s=None,
                        p=None,
                        o=None,
                        user=None,
                        collection=None,
                        limit=100,
                        **kwargs)
```

Triple pattern query

<a id="trustgraph.api.async_socket_client.AsyncSocketFlowInstance.objects_query"></a>

#### objects\_query

```python
async def objects_query(query: str,
                        user: str,
                        collection: str,
                        variables: Optional[Dict] = None,
                        operation_name: Optional[str] = None,
                        **kwargs)
```

GraphQL query

<a id="trustgraph.api.async_socket_client.AsyncSocketFlowInstance.mcp_tool"></a>

#### mcp\_tool

```python
async def mcp_tool(name: str, parameters: Dict[str, Any], **kwargs)
```

Execute MCP tool

<a id="trustgraph.api.bulk_client"></a>

# trustgraph.api.bulk\_client

<a id="trustgraph.api.bulk_client.Triple"></a>

## Triple

<a id="trustgraph.api.bulk_client.BulkClient"></a>

## BulkClient Objects

```python
class BulkClient()
```

Synchronous bulk operations client

<a id="trustgraph.api.bulk_client.BulkClient.__init__"></a>

#### \_\_init\_\_

```python
def __init__(url: str, timeout: int, token: Optional[str]) -> None
```

<a id="trustgraph.api.bulk_client.BulkClient.import_triples"></a>

#### import\_triples

```python
def import_triples(flow: str, triples: Iterator[Triple],
                   **kwargs: Any) -> None
```

Bulk import triples via WebSocket

<a id="trustgraph.api.bulk_client.BulkClient.export_triples"></a>

#### export\_triples

```python
def export_triples(flow: str, **kwargs: Any) -> Iterator[Triple]
```

Bulk export triples via WebSocket

<a id="trustgraph.api.bulk_client.BulkClient.import_graph_embeddings"></a>

#### import\_graph\_embeddings

```python
def import_graph_embeddings(flow: str, embeddings: Iterator[Dict[str, Any]],
                            **kwargs: Any) -> None
```

Bulk import graph embeddings via WebSocket

<a id="trustgraph.api.bulk_client.BulkClient.export_graph_embeddings"></a>

#### export\_graph\_embeddings

```python
def export_graph_embeddings(flow: str,
                            **kwargs: Any) -> Iterator[Dict[str, Any]]
```

Bulk export graph embeddings via WebSocket

<a id="trustgraph.api.bulk_client.BulkClient.import_document_embeddings"></a>

#### import\_document\_embeddings

```python
def import_document_embeddings(flow: str, embeddings: Iterator[Dict[str, Any]],
                               **kwargs: Any) -> None
```

Bulk import document embeddings via WebSocket

<a id="trustgraph.api.bulk_client.BulkClient.export_document_embeddings"></a>

#### export\_document\_embeddings

```python
def export_document_embeddings(flow: str,
                               **kwargs: Any) -> Iterator[Dict[str, Any]]
```

Bulk export document embeddings via WebSocket

<a id="trustgraph.api.bulk_client.BulkClient.import_entity_contexts"></a>

#### import\_entity\_contexts

```python
def import_entity_contexts(flow: str, contexts: Iterator[Dict[str, Any]],
                           **kwargs: Any) -> None
```

Bulk import entity contexts via WebSocket

<a id="trustgraph.api.bulk_client.BulkClient.export_entity_contexts"></a>

#### export\_entity\_contexts

```python
def export_entity_contexts(flow: str,
                           **kwargs: Any) -> Iterator[Dict[str, Any]]
```

Bulk export entity contexts via WebSocket

<a id="trustgraph.api.bulk_client.BulkClient.import_objects"></a>

#### import\_objects

```python
def import_objects(flow: str, objects: Iterator[Dict[str, Any]],
                   **kwargs: Any) -> None
```

Bulk import objects via WebSocket

<a id="trustgraph.api.bulk_client.BulkClient.close"></a>

#### close

```python
def close() -> None
```

Close connections

<a id="trustgraph.api.async_bulk_client"></a>

# trustgraph.api.async\_bulk\_client

<a id="trustgraph.api.async_bulk_client.Triple"></a>

## Triple

<a id="trustgraph.api.async_bulk_client.AsyncBulkClient"></a>

## AsyncBulkClient Objects

```python
class AsyncBulkClient()
```

Asynchronous bulk operations client

<a id="trustgraph.api.async_bulk_client.AsyncBulkClient.__init__"></a>

#### \_\_init\_\_

```python
def __init__(url: str, timeout: int, token: Optional[str]) -> None
```

<a id="trustgraph.api.async_bulk_client.AsyncBulkClient.import_triples"></a>

#### import\_triples

```python
async def import_triples(flow: str, triples: AsyncIterator[Triple],
                         **kwargs: Any) -> None
```

Bulk import triples via WebSocket

<a id="trustgraph.api.async_bulk_client.AsyncBulkClient.export_triples"></a>

#### export\_triples

```python
async def export_triples(flow: str, **kwargs: Any) -> AsyncIterator[Triple]
```

Bulk export triples via WebSocket

<a id="trustgraph.api.async_bulk_client.AsyncBulkClient.import_graph_embeddings"></a>

#### import\_graph\_embeddings

```python
async def import_graph_embeddings(flow: str,
                                  embeddings: AsyncIterator[Dict[str, Any]],
                                  **kwargs: Any) -> None
```

Bulk import graph embeddings via WebSocket

<a id="trustgraph.api.async_bulk_client.AsyncBulkClient.export_graph_embeddings"></a>

#### export\_graph\_embeddings

```python
async def export_graph_embeddings(
        flow: str, **kwargs: Any) -> AsyncIterator[Dict[str, Any]]
```

Bulk export graph embeddings via WebSocket

<a id="trustgraph.api.async_bulk_client.AsyncBulkClient.import_document_embeddings"></a>

#### import\_document\_embeddings

```python
async def import_document_embeddings(flow: str,
                                     embeddings: AsyncIterator[Dict[str, Any]],
                                     **kwargs: Any) -> None
```

Bulk import document embeddings via WebSocket

<a id="trustgraph.api.async_bulk_client.AsyncBulkClient.export_document_embeddings"></a>

#### export\_document\_embeddings

```python
async def export_document_embeddings(
        flow: str, **kwargs: Any) -> AsyncIterator[Dict[str, Any]]
```

Bulk export document embeddings via WebSocket

<a id="trustgraph.api.async_bulk_client.AsyncBulkClient.import_entity_contexts"></a>

#### import\_entity\_contexts

```python
async def import_entity_contexts(flow: str, contexts: AsyncIterator[Dict[str,
                                                                         Any]],
                                 **kwargs: Any) -> None
```

Bulk import entity contexts via WebSocket

<a id="trustgraph.api.async_bulk_client.AsyncBulkClient.export_entity_contexts"></a>

#### export\_entity\_contexts

```python
async def export_entity_contexts(
        flow: str, **kwargs: Any) -> AsyncIterator[Dict[str, Any]]
```

Bulk export entity contexts via WebSocket

<a id="trustgraph.api.async_bulk_client.AsyncBulkClient.import_objects"></a>

#### import\_objects

```python
async def import_objects(flow: str, objects: AsyncIterator[Dict[str, Any]],
                         **kwargs: Any) -> None
```

Bulk import objects via WebSocket

<a id="trustgraph.api.async_bulk_client.AsyncBulkClient.aclose"></a>

#### aclose

```python
async def aclose() -> None
```

Close connections

<a id="trustgraph.api.metrics"></a>

# trustgraph.api.metrics

<a id="trustgraph.api.metrics.Metrics"></a>

## Metrics Objects

```python
class Metrics()
```

Synchronous metrics client

<a id="trustgraph.api.metrics.Metrics.__init__"></a>

#### \_\_init\_\_

```python
def __init__(url: str, timeout: int, token: Optional[str]) -> None
```

<a id="trustgraph.api.metrics.Metrics.get"></a>

#### get

```python
def get() -> str
```

Get Prometheus metrics as text

<a id="trustgraph.api.async_metrics"></a>

# trustgraph.api.async\_metrics

<a id="trustgraph.api.async_metrics.AsyncMetrics"></a>

## AsyncMetrics Objects

```python
class AsyncMetrics()
```

Asynchronous metrics client

<a id="trustgraph.api.async_metrics.AsyncMetrics.__init__"></a>

#### \_\_init\_\_

```python
def __init__(url: str, timeout: int, token: Optional[str]) -> None
```

<a id="trustgraph.api.async_metrics.AsyncMetrics.get"></a>

#### get

```python
async def get() -> str
```

Get Prometheus metrics as text

<a id="trustgraph.api.async_metrics.AsyncMetrics.aclose"></a>

#### aclose

```python
async def aclose() -> None
```

Close connections

<a id="trustgraph.api.async_flow"></a>

# trustgraph.api.async\_flow

<a id="trustgraph.api.async_flow.check_error"></a>

#### check\_error

```python
def check_error(response)
```

<a id="trustgraph.api.async_flow.AsyncFlow"></a>

## AsyncFlow Objects

```python
class AsyncFlow()
```

Asynchronous REST-based flow interface

<a id="trustgraph.api.async_flow.AsyncFlow.__init__"></a>

#### \_\_init\_\_

```python
def __init__(url: str, timeout: int, token: Optional[str]) -> None
```

<a id="trustgraph.api.async_flow.AsyncFlow.request"></a>

#### request

```python
async def request(path: str, request_data: Dict[str, Any]) -> Dict[str, Any]
```

Make async HTTP request to Gateway API

<a id="trustgraph.api.async_flow.AsyncFlow.list"></a>

#### list

```python
async def list() -> List[str]
```

List all flows

<a id="trustgraph.api.async_flow.AsyncFlow.get"></a>

#### get

```python
async def get(id: str) -> Dict[str, Any]
```

Get flow definition

<a id="trustgraph.api.async_flow.AsyncFlow.start"></a>

#### start

```python
async def start(class_name: str,
                id: str,
                description: str,
                parameters: Optional[Dict] = None)
```

Start a flow

<a id="trustgraph.api.async_flow.AsyncFlow.stop"></a>

#### stop

```python
async def stop(id: str)
```

Stop a flow

<a id="trustgraph.api.async_flow.AsyncFlow.list_classes"></a>

#### list\_classes

```python
async def list_classes() -> List[str]
```

List flow classes

<a id="trustgraph.api.async_flow.AsyncFlow.get_class"></a>

#### get\_class

```python
async def get_class(class_name: str) -> Dict[str, Any]
```

Get flow class definition

<a id="trustgraph.api.async_flow.AsyncFlow.put_class"></a>

#### put\_class

```python
async def put_class(class_name: str, definition: Dict[str, Any])
```

Create/update flow class

<a id="trustgraph.api.async_flow.AsyncFlow.delete_class"></a>

#### delete\_class

```python
async def delete_class(class_name: str)
```

Delete flow class

<a id="trustgraph.api.async_flow.AsyncFlow.id"></a>

#### id

```python
def id(flow_id: str)
```

Get async flow instance

<a id="trustgraph.api.async_flow.AsyncFlow.aclose"></a>

#### aclose

```python
async def aclose() -> None
```

Close connection (cleanup handled by aiohttp session)

<a id="trustgraph.api.async_flow.AsyncFlowInstance"></a>

## AsyncFlowInstance Objects

```python
class AsyncFlowInstance()
```

Asynchronous REST flow instance

<a id="trustgraph.api.async_flow.AsyncFlowInstance.__init__"></a>

#### \_\_init\_\_

```python
def __init__(flow: AsyncFlow, flow_id: str)
```

<a id="trustgraph.api.async_flow.AsyncFlowInstance.request"></a>

#### request

```python
async def request(service: str, request_data: Dict[str,
                                                   Any]) -> Dict[str, Any]
```

Make request to flow-scoped service

<a id="trustgraph.api.async_flow.AsyncFlowInstance.agent"></a>

#### agent

```python
async def agent(question: str,
                user: str,
                state: Optional[Dict] = None,
                group: Optional[str] = None,
                history: Optional[List] = None,
                **kwargs: Any) -> Dict[str, Any]
```

Execute agent (non-streaming, use async_socket for streaming)

<a id="trustgraph.api.async_flow.AsyncFlowInstance.text_completion"></a>

#### text\_completion

```python
async def text_completion(system: str, prompt: str, **kwargs: Any) -> str
```

Text completion (non-streaming, use async_socket for streaming)

<a id="trustgraph.api.async_flow.AsyncFlowInstance.graph_rag"></a>

#### graph\_rag

```python
async def graph_rag(query: str,
                    user: str,
                    collection: str,
                    max_subgraph_size: int = 1000,
                    max_subgraph_count: int = 5,
                    max_entity_distance: int = 3,
                    **kwargs: Any) -> str
```

Graph RAG (non-streaming, use async_socket for streaming)

<a id="trustgraph.api.async_flow.AsyncFlowInstance.document_rag"></a>

#### document\_rag

```python
async def document_rag(query: str,
                       user: str,
                       collection: str,
                       doc_limit: int = 10,
                       **kwargs: Any) -> str
```

Document RAG (non-streaming, use async_socket for streaming)

<a id="trustgraph.api.async_flow.AsyncFlowInstance.graph_embeddings_query"></a>

#### graph\_embeddings\_query

```python
async def graph_embeddings_query(text: str,
                                 user: str,
                                 collection: str,
                                 limit: int = 10,
                                 **kwargs: Any)
```

Query graph embeddings for semantic search

<a id="trustgraph.api.async_flow.AsyncFlowInstance.embeddings"></a>

#### embeddings

```python
async def embeddings(text: str, **kwargs: Any)
```

Generate text embeddings

<a id="trustgraph.api.async_flow.AsyncFlowInstance.triples_query"></a>

#### triples\_query

```python
async def triples_query(s=None,
                        p=None,
                        o=None,
                        user=None,
                        collection=None,
                        limit=100,
                        **kwargs: Any)
```

Triple pattern query

<a id="trustgraph.api.async_flow.AsyncFlowInstance.objects_query"></a>

#### objects\_query

```python
async def objects_query(query: str,
                        user: str,
                        collection: str,
                        variables: Optional[Dict] = None,
                        operation_name: Optional[str] = None,
                        **kwargs: Any)
```

GraphQL query

