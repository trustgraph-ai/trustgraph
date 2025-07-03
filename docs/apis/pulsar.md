# TrustGraph Pulsar API

Apache Pulsar is the underlying message queue system used by TrustGraph for inter-component communication. Understanding Pulsar queue names is essential for direct integration with TrustGraph services.

## Overview

TrustGraph uses two types of APIs with different queue naming patterns:

1. **Global Services**: Fixed queue names, not dependent on flows
2. **Flow-Hosted Services**: Dynamic queue names that depend on the specific flow configuration

## Global Services (Fixed Queue Names)

These services run independently and have fixed Pulsar queue names:

### Config API
- **Request Queue**: `non-persistent://tg/request/config`
- **Response Queue**: `non-persistent://tg/response/config`
- **Push Queue**: `persistent://tg/config/config`

### Flow API
- **Request Queue**: `non-persistent://tg/request/flow`
- **Response Queue**: `non-persistent://tg/response/flow`

### Knowledge API
- **Request Queue**: `non-persistent://tg/request/knowledge`
- **Response Queue**: `non-persistent://tg/response/knowledge`

### Librarian API
- **Request Queue**: `non-persistent://tg/request/librarian`
- **Response Queue**: `non-persistent://tg/response/librarian`

## Flow-Hosted Services (Dynamic Queue Names)

These services are hosted within specific flows and have queue names that depend on the flow configuration:

- Agent API
- Document RAG API
- Graph RAG API
- Text Completion API
- Prompt API
- Embeddings API
- Graph Embeddings API
- Triples Query API
- Text Load API
- Document Load API

## Discovering Flow-Hosted Queue Names

To find the queue names for flow-hosted services, you need to query the flow configuration using the Config API.

### Method 1: Using the Config API

Query for the flow configuration:

**Request:**
```json
{
    "operation": "get",
    "keys": [
        {
            "type": "flows",
            "key": "your-flow-name"
        }
    ]
}
```

**Response:**
The response will contain a flow definition with an "interfaces" object that lists all queue names.

### Method 2: Using the CLI

Use the TrustGraph CLI to dump the configuration:

```bash
tg-show-config
```

## Flow Interface Types

Flow configurations define two types of service interfaces:

### 1. Request/Response Interfaces

Services that accept a request and return a response:

```json
{
    "graph-rag": {
        "request": "non-persistent://tg/request/graph-rag:document-rag+graph-rag",
        "response": "non-persistent://tg/response/graph-rag:document-rag+graph-rag"
    }
}
```

**Examples**: agent, document-rag, graph-rag, text-completion, prompt, embeddings, graph-embeddings, triples

### 2. Fire-and-Forget Interfaces  

Services that accept data but don't return a response:

```json
{
    "text-load": "persistent://tg/flow/text-document-load:default"
}
```

**Examples**: text-load, document-load, triples-store, graph-embeddings-store, document-embeddings-store, entity-contexts-load

## Example Flow Configuration

Here's an example of a complete flow configuration showing queue names:

```json
{
    "class-name": "document-rag+graph-rag",
    "description": "Default processing flow", 
    "interfaces": {
        "agent": {
            "request": "non-persistent://tg/request/agent:default",
            "response": "non-persistent://tg/response/agent:default"
        },
        "document-rag": {
            "request": "non-persistent://tg/request/document-rag:document-rag+graph-rag",
            "response": "non-persistent://tg/response/document-rag:document-rag+graph-rag"
        },
        "graph-rag": {
            "request": "non-persistent://tg/request/graph-rag:document-rag+graph-rag", 
            "response": "non-persistent://tg/response/graph-rag:document-rag+graph-rag"
        },
        "text-completion": {
            "request": "non-persistent://tg/request/text-completion:document-rag+graph-rag",
            "response": "non-persistent://tg/response/text-completion:document-rag+graph-rag"
        },
        "embeddings": {
            "request": "non-persistent://tg/request/embeddings:document-rag+graph-rag",
            "response": "non-persistent://tg/response/embeddings:document-rag+graph-rag"
        },
        "triples": {
            "request": "non-persistent://tg/request/triples:document-rag+graph-rag",
            "response": "non-persistent://tg/response/triples:document-rag+graph-rag"
        },
        "text-load": "persistent://tg/flow/text-document-load:default",
        "document-load": "persistent://tg/flow/document-load:default",
        "triples-store": "persistent://tg/flow/triples-store:default",
        "graph-embeddings-store": "persistent://tg/flow/graph-embeddings-store:default"
    }
}
```

## Queue Naming Patterns

### Global Services
- **Pattern**: `{persistence}://tg/{namespace}/{service-name}`
- **Example**: `non-persistent://tg/request/config`

### Flow-Hosted Request/Response
- **Pattern**: `{persistence}://tg/{namespace}/{service-name}:{flow-identifier}`
- **Example**: `non-persistent://tg/request/graph-rag:document-rag+graph-rag`

### Flow-Hosted Fire-and-Forget
- **Pattern**: `{persistence}://tg/flow/{service-name}:{flow-identifier}`
- **Example**: `persistent://tg/flow/text-document-load:default`

## Persistence Types

- **non-persistent**: Messages are not persisted to disk, faster but less reliable
- **persistent**: Messages are persisted to disk, slower but more reliable

## Practical Usage

### Python Example

```python
import pulsar
from trustgraph.schema import ConfigRequest, ConfigResponse

# Connect to Pulsar
client = pulsar.Client('pulsar://localhost:6650')

# Create producer for config requests
producer = client.create_producer(
    'non-persistent://tg/request/config',
    schema=pulsar.schema.AvroSchema(ConfigRequest)
)

# Create consumer for config responses  
consumer = client.subscribe(
    'non-persistent://tg/response/config',
    subscription_name='my-subscription',
    schema=pulsar.schema.AvroSchema(ConfigResponse)
)

# Send request
request = ConfigRequest(operation='list-classes')
producer.send(request)

# Receive response
response = consumer.receive()
print(response.value())
```

### Flow Service Example

```python
# First, get the flow configuration to find queue names
config_request = ConfigRequest(
    operation='get',
    keys=[ConfigKey(type='flows', key='my-flow')]
)

# Use the returned interface information to determine queue names
# Then connect to the appropriate queues for the service you need
```

## Best Practices

1. **Query Flow Configuration**: Always query the current flow configuration to get accurate queue names
2. **Handle Dynamic Names**: Flow-hosted service queue names can change when flows are reconfigured
3. **Choose Appropriate Persistence**: Use persistent queues for critical data, non-persistent for performance
4. **Schema Validation**: Use the appropriate Pulsar schema for each service
5. **Error Handling**: Implement proper error handling for queue connection and message failures

## Security Considerations

- Pulsar access should be restricted in production environments
- Use appropriate authentication and authorization mechanisms
- Monitor queue access and message patterns for security anomalies
- Consider encryption for sensitive data in messages