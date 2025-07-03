# TrustGraph Config API

This API provides centralized configuration management for TrustGraph components.
Configuration data is organized hierarchically by type and key, with support for
persistent storage and push notifications.

## Request/response

### Request

The request contains the following fields:
- `operation`: The operation to perform (`get`, `list`, `getvalues`, `put`, `delete`, `config`)
- `keys`: Array of ConfigKey objects (for `get`, `delete` operations)
- `type`: Configuration type (for `list`, `getvalues` operations)
- `values`: Array of ConfigValue objects (for `put` operation)

### Response

The response contains the following fields:
- `version`: Version number for tracking changes
- `values`: Array of ConfigValue objects returned by operations
- `directory`: Array of key names returned by `list` operation
- `config`: Full configuration map returned by `config` operation
- `error`: Error information if operation fails

## Operations

### PUT - Store Configuration Values

Request:
```json
{
    "operation": "put",
    "values": [
        {
            "type": "test",
            "key": "key1",
            "value": "value1"
        }
    ]
}
```

Response:
```json
{
    "version": 123
}
```

### GET - Retrieve Configuration Values

Request:
```json
{
    "operation": "get",
    "keys": [
        {
            "type": "test",
            "key": "key1"
        }
    ]
}
```

Response:
```json
{
    "version": 123,
    "values": [
        {
            "type": "test",
            "key": "key1",
            "value": "value1"
        }
    ]
}
```

### LIST - List Keys by Type

Request:
```json
{
    "operation": "list",
    "type": "test"
}
```

Response:
```json
{
    "version": 123,
    "directory": ["key1", "key2", "key3"]
}
```

### GETVALUES - Get All Values by Type

Request:
```json
{
    "operation": "getvalues",
    "type": "test"
}
```

Response:
```json
{
    "version": 123,
    "values": [
        {
            "type": "test",
            "key": "key1",
            "value": "value1"
        },
        {
            "type": "test",
            "key": "key2",
            "value": "value2"
        }
    ]
}
```

### CONFIG - Get Entire Configuration

Request:
```json
{
    "operation": "config"
}
```

Response:
```json
{
    "version": 123,
    "config": {
        "test": {
            "key1": "value1",
            "key2": "value2"
        }
    }
}
```

### DELETE - Remove Configuration Values

Request:
```json
{
    "operation": "delete",
    "keys": [
        {
            "type": "test",
            "key": "key1"
        }
    ]
}
```

Response:
```json
{
    "version": 124
}
```

## REST service

The REST service is available at `/api/v1/config` and accepts the above request formats.

## Websocket

Requests have a `request` object containing the operation fields.
Responses have a `response` object containing the response fields.

Request:
```json
{
    "id": "unique-request-id",
    "service": "config",
    "request": {
        "operation": "get",
        "keys": [
            {
                "type": "test",
                "key": "key1"
            }
        ]
    }
}
```

Response:
```json
{
    "id": "unique-request-id",
    "response": {
        "version": 123,
        "values": [
            {
                "type": "test",
                "key": "key1",
                "value": "value1"
            }
        ]
    },
    "complete": true
}
```

## Pulsar

The Pulsar schema for the Config API is defined in Python code here:

https://github.com/trustgraph-ai/trustgraph/blob/master/trustgraph-base/trustgraph/schema/config.py

Default request queue:
`non-persistent://tg/request/config`

Default response queue:
`non-persistent://tg/response/config`

Request schema:
`trustgraph.schema.ConfigRequest`

Response schema:
`trustgraph.schema.ConfigResponse`

## Python SDK

The Python SDK provides convenient access to the Config API:

```python
from trustgraph.api.config import ConfigClient

client = ConfigClient()

# Put a value
await client.put("test", "key1", "value1")

# Get a value
value = await client.get("test", "key1")

# List keys
keys = await client.list("test")

# Get all values for a type
values = await client.get_values("test")
```

## Features

- **Hierarchical Organization**: Configuration organized by type and key
- **Versioning**: Each operation returns a version number for change tracking
- **Persistent Storage**: Data stored in Cassandra for persistence
- **Push Notifications**: Configuration changes pushed to subscribers
- **Multiple Access Methods**: Available via Pulsar, REST, WebSocket, and Python SDK