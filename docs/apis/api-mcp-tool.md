# TrustGraph MCP Tool API

This is a higher-level interface to the MCP (Model Control Protocol) tool service. The input
specifies an MCP tool by name and parameters to pass to the tool.

## Request/response

### Request

The request contains the following fields:
- `name`: The MCP tool name
- `parameters`: A set of key/values describing the tool parameters

### Response

The response contains either of these fields:
- `text`: A plain text response
- `object`: A structured object response

## REST service

The REST service accepts `name` and `parameters` fields, with parameters
encoded as a JSON object.

e.g.

In this example, the MCP tool takes parameters and returns a
structured response in the `object` field.

Request:
```
{
    "name": "file-reader",
    "parameters": {
        "path": "/path/to/file.txt"
    }
}
```

Response:

```
{
    "object": {"content": "file contents here", "size": 1024}
}
```

## Websocket

Requests have `name` and `parameters` fields.

e.g.

Request:

```
{
    "id": "akshfkiehfkseffh-142",
    "service": "mcp-tool",
    "flow": "default",
    "request": {
        "name": "file-reader",
        "parameters": {
            "path": "/path/to/file.txt"
        }
    }
}
```

Responses:

```
{
    "id": "akshfkiehfkseffh-142",
    "response": {
        "object": {"content": "file contents here", "size": 1024}
    },
    "complete": true
}
```

e.g.

An example which returns plain text

Request:

```
{
    "id": "akshfkiehfkseffh-141",
    "service": "mcp-tool",
    "request": {
        "name": "calculator",
        "parameters": {
            "expression": "2 + 2"
        }
    }
}
```

Response:

```
{
    "id": "akshfkiehfkseffh-141",
    "response": {
        "text": "4"
    },
    "complete": true
}
```


## Pulsar

The Pulsar schema for the MCP Tool API is defined in Python code here:

https://github.com/trustgraph-ai/trustgraph/blob/master/trustgraph-base/trustgraph/schema/mcp_tool.py

Default request queue:
`non-persistent://tg/request/mcp-tool`

Default response queue:
`non-persistent://tg/response/mcp-tool`

Request schema:
`trustgraph.schema.McpToolRequest`

Response schema:
`trustgraph.schema.McpToolResponse`

## Pulsar Python client

The client class is
`trustgraph.clients.McpToolClient`

https://github.com/trustgraph-ai/trustgraph/blob/master/trustgraph-base/trustgraph/clients/mcp_tool_client.py
