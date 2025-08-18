# TrustGraph Flow API

This API provides workflow management for TrustGraph components. It manages flow classes 
(workflow templates) and flow instances (active running workflows) that orchestrate 
complex data processing pipelines.

## Request/response

### Request

The request contains the following fields:
- `operation`: The operation to perform (see operations below)
- `class_name`: Flow class name (for class operations and start-flow)
- `class_definition`: Flow class definition JSON (for put-class)
- `description`: Flow description (for start-flow)
- `flow_id`: Flow instance ID (for flow instance operations)

### Response

The response contains the following fields:
- `class_names`: Array of flow class names (returned by list-classes)
- `flow_ids`: Array of active flow IDs (returned by list-flows)
- `class_definition`: Flow class definition JSON (returned by get-class)
- `flow`: Flow instance JSON (returned by get-flow)
- `description`: Flow description (returned by get-flow)
- `error`: Error information if operation fails

## Operations

### Flow Class Operations

#### LIST-CLASSES - List All Flow Classes

Request:
```json
{
    "operation": "list-classes"
}
```

Response:
```json
{
    "class_names": ["pdf-processor", "text-analyzer", "knowledge-extractor"]
}
```

#### GET-CLASS - Get Flow Class Definition

Request:
```json
{
    "operation": "get-class",
    "class_name": "pdf-processor"
}
```

Response:
```json
{
    "class_definition": "{\"interfaces\": {\"text-completion\": {\"request\": \"persistent://tg/request/text-completion\", \"response\": \"persistent://tg/response/text-completion\"}}, \"description\": \"PDF processing workflow\"}"
}
```

#### PUT-CLASS - Create/Update Flow Class

Request:
```json
{
    "operation": "put-class",
    "class_name": "pdf-processor",
    "class_definition": "{\"interfaces\": {\"text-completion\": {\"request\": \"persistent://tg/request/text-completion\", \"response\": \"persistent://tg/response/text-completion\"}}, \"description\": \"PDF processing workflow\"}"
}
```

Response:
```json
{}
```

#### DELETE-CLASS - Remove Flow Class

Request:
```json
{
    "operation": "delete-class",
    "class_name": "pdf-processor"
}
```

Response:
```json
{}
```

### Flow Instance Operations

#### LIST-FLOWS - List Active Flow Instances

Request:
```json
{
    "operation": "list-flows"
}
```

Response:
```json
{
    "flow_ids": ["flow-123", "flow-456", "flow-789"]
}
```

#### GET-FLOW - Get Flow Instance

Request:
```json
{
    "operation": "get-flow",
    "flow_id": "flow-123"
}
```

Response:
```json
{
    "flow": "{\"interfaces\": {\"text-completion\": {\"request\": \"persistent://tg/request/text-completion-flow-123\", \"response\": \"persistent://tg/response/text-completion-flow-123\"}}}",
    "description": "PDF processing workflow instance"
}
```

#### START-FLOW - Start Flow Instance

Request:
```json
{
    "operation": "start-flow",
    "class_name": "pdf-processor",
    "flow_id": "flow-123",
    "description": "Processing document batch 1"
}
```

Response:
```json
{}
```

#### STOP-FLOW - Stop Flow Instance

Request:
```json
{
    "operation": "stop-flow",
    "flow_id": "flow-123"
}
```

Response:
```json
{}
```

## REST service

The REST service is available at `/api/v1/flow` and accepts the above request formats.

## Websocket

Requests have a `request` object containing the operation fields.
Responses have a `response` object containing the response fields.

Request:
```json
{
    "id": "unique-request-id",
    "service": "flow",
    "request": {
        "operation": "list-classes"
    }
}
```

Response:
```json
{
    "id": "unique-request-id",
    "response": {
        "class_names": ["pdf-processor", "text-analyzer"]
    },
    "complete": true
}
```

## Pulsar

The Pulsar schema for the Flow API is defined in Python code here:

https://github.com/trustgraph-ai/trustgraph/blob/master/trustgraph-base/trustgraph/schema/flows.py

Default request queue:
`non-persistent://tg/request/flow`

Default response queue:
`non-persistent://tg/response/flow`

Request schema:
`trustgraph.schema.FlowRequest`

Response schema:
`trustgraph.schema.FlowResponse`

## Flow Service Methods

Flow instances provide access to various TrustGraph services through flow-specific endpoints:

### MCP Tool Service - Invoke MCP Tools

The `mcp_tool` method allows invoking MCP (Model Control Protocol) tools within a flow context.

Request:
```json
{
    "name": "file-reader",
    "parameters": {
        "path": "/path/to/file.txt"
    }
}
```

Response:
```json
{
    "object": {"content": "file contents here", "size": 1024}
}
```

Or for text responses:
```json
{
    "text": "plain text response"
}
```

### Other Service Methods

Flow instances also provide access to:
- `text_completion` - LLM text completion
- `agent` - Agent question answering
- `graph_rag` - Graph-based RAG queries
- `document_rag` - Document-based RAG queries
- `embeddings` - Text embeddings
- `prompt` - Prompt template processing
- `triples_query` - Knowledge graph queries
- `load_document` - Document loading
- `load_text` - Text loading

## Python SDK

The Python SDK provides convenient access to the Flow API:

```python
from trustgraph.api.flow import FlowClient

client = FlowClient()

# List all flow classes
classes = await client.list_classes()

# Get a flow class definition
definition = await client.get_class("pdf-processor")

# Start a flow instance
await client.start_flow("pdf-processor", "flow-123", "Processing batch 1")

# List active flows
flows = await client.list_flows()

# Stop a flow instance
await client.stop_flow("flow-123")

# Use flow instance services
flow = client.id("flow-123")
result = await flow.mcp_tool("file-reader", {"path": "/path/to/file.txt"})
```

## Features

- **Flow Classes**: Templates that define workflow structure and interfaces
- **Flow Instances**: Active running workflows based on flow classes
- **Dynamic Management**: Flows can be started/stopped dynamically
- **Template Processing**: Uses template replacement for customizing flow instances
- **Integration**: Works with TrustGraph ecosystem for data processing pipelines
- **Persistent Storage**: Flow definitions and instances stored for reliability

## Use Cases

- **Document Processing**: Orchestrating PDF processing through chunking, extraction, and storage
- **Knowledge Extraction**: Managing workflows for relationship and definition extraction
- **Data Pipelines**: Coordinating complex multi-step data processing workflows
- **Resource Management**: Dynamically scaling processing flows based on demand