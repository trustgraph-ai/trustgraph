# Tool Services: Dynamically Pluggable Agent Tools

## Status

Implemented

## Overview

This specification defines a mechanism for dynamically pluggable agent tools called "tool services". Unlike the existing built-in tool types (`KnowledgeQueryImpl`, `McpToolImpl`, etc.), tool services allow new tools to be introduced by:

1. Deploying a new Pulsar-based service
2. Adding a configuration descriptor that tells the agent how to invoke it

This enables extensibility without modifying the core agent-react framework.

## Terminology

| Term | Definition |
|------|------------|
| **Built-in Tool** | Existing tool types with hardcoded implementations in `tools.py` |
| **Tool Service** | A Pulsar service that can be invoked as an agent tool, defined by a service descriptor |
| **Tool** | A configured instance that references a tool service, exposed to the agent/LLM |

This is a two-tier model, analogous to MCP tools:
- MCP: MCP server defines the tool interface → Tool config references it
- Tool Services: Tool service defines the Pulsar interface → Tool config references it

## Current Architecture

### Existing Tool Implementation

Tools are currently defined in `trustgraph-flow/trustgraph/agent/react/tools.py` with typed implementations:

```python
class KnowledgeQueryImpl:
    async def invoke(self, question):
        client = self.context("graph-rag-request")
        return await client.rag(question, self.collection)
```

Each tool type:
- Has a hardcoded Pulsar service it calls (e.g., `graph-rag-request`)
- Knows the exact method to call on the client (e.g., `client.rag()`)
- Has typed arguments defined in the implementation

### Tool Registration (service.py:105-214)

Tools are loaded from config with a `type` field that maps to an implementation:

```python
if impl_id == "knowledge-query":
    impl = functools.partial(KnowledgeQueryImpl, collection=data.get("collection"))
elif impl_id == "text-completion":
    impl = TextCompletionImpl
# ... etc
```

## Proposed Architecture

### Two-Tier Model

#### Tier 1: Tool Service Descriptor

A tool service defines a Pulsar service interface. It declares:
- The Pulsar queues for request/response
- Configuration parameters it requires from tools that use it

```json
{
  "id": "custom-rag",
  "request-queue": "non-persistent://tg/request/custom-rag",
  "response-queue": "non-persistent://tg/response/custom-rag",
  "config-params": [
    {"name": "collection", "required": true}
  ]
}
```

A tool service that needs no configuration parameters:

```json
{
  "id": "calculator",
  "request-queue": "non-persistent://tg/request/calc",
  "response-queue": "non-persistent://tg/response/calc",
  "config-params": []
}
```

#### Tier 2: Tool Descriptor

A tool references a tool service and provides:
- Config parameter values (satisfying the service's requirements)
- Tool metadata for the agent (name, description)
- Argument definitions for the LLM

```json
{
  "type": "tool-service",
  "name": "query-customers",
  "description": "Query the customer knowledge base",
  "service": "custom-rag",
  "collection": "customers",
  "arguments": [
    {
      "name": "question",
      "type": "string",
      "description": "The question to ask about customers"
    }
  ]
}
```

Multiple tools can reference the same service with different configurations:

```json
{
  "type": "tool-service",
  "name": "query-products",
  "description": "Query the product knowledge base",
  "service": "custom-rag",
  "collection": "products",
  "arguments": [
    {
      "name": "question",
      "type": "string",
      "description": "The question to ask about products"
    }
  ]
}
```

### Request Format

When a tool is invoked, the request to the tool service includes:
- `user`: From the agent request (multi-tenancy)
- Config values: From the tool descriptor (e.g., `collection`)
- `arguments`: From the LLM

```json
{
  "user": "alice",
  "collection": "customers",
  "arguments": {
    "question": "What are the top customer complaints?"
  }
}
```

### Generic Tool Service Implementation

A `ToolServiceImpl` class invokes tool services based on configuration:

```python
class ToolServiceImpl:
    def __init__(self, service_topic, config_values, context):
        self.service_topic = service_topic
        self.config_values = config_values  # e.g., {"collection": "customers"}
        self.context = context

    async def invoke(self, user, **arguments):
        client = self.context(self.service_topic)
        request = {
            "user": user,
            **self.config_values,
            "arguments": arguments,
        }
        response = await client.call(request)
        if isinstance(response, str):
            return response
        else:
            return json.dumps(response)
```

## Design Decisions

### Two-Tier Configuration Model

Tool services follow a two-tier model similar to MCP tools:

1. **Tool Service**: Defines the Pulsar service interface (topic, required config params)
2. **Tool**: References a tool service, provides config values, defines LLM arguments

This separation allows:
- One tool service to be used by multiple tools with different configurations
- Clear distinction between service interface and tool configuration
- Reusability of service definitions

### Request Mapping: Pass-Through with Envelope

The request to a tool service is a structured envelope containing:
- `user`: Propagated from the agent request for multi-tenancy
- Config values: From the tool descriptor (e.g., `collection`)
- `arguments`: LLM-provided arguments, passed through as a dict

The agent manager parses the LLM's response into `act.arguments` as a dict (`agent_manager.py:117-154`). This dict is included in the request envelope.

### Schema Handling: Untyped

Requests and responses use untyped dicts. No schema validation at the agent level - the tool service is responsible for validating its inputs. This provides maximum flexibility for defining new services.

### Client Interface: Direct Pulsar Topics

Tool services use direct Pulsar topics without requiring flow configuration. The tool-service descriptor specifies the full queue names:

```json
{
  "id": "joke-service",
  "request-queue": "non-persistent://tg/request/joke",
  "response-queue": "non-persistent://tg/response/joke",
  "config-params": [...]
}
```

This allows services to be hosted in any namespace.

### Error Handling: Standard Error Convention

Tool service responses follow the existing schema convention with an `error` field:

```python
@dataclass
class Error:
    type: str = ""
    message: str = ""
```

Response structure:
- Success: `error` is `None`, response contains result
- Error: `error` is populated with `type` and `message`

This matches the pattern used throughout existing service schemas (e.g., `PromptResponse`, `QueryResponse`, `AgentResponse`).

### Request/Response Correlation

Requests and responses are correlated using an `id` in Pulsar message properties:

- Request includes `id` in properties: `properties={"id": id}`
- Response(s) include the same `id`: `properties={"id": id}`

This follows the existing pattern used throughout the codebase (e.g., `agent_service.py`, `llm_service.py`).

### Streaming Support

Tool services can return streaming responses:

- Multiple response messages with the same `id` in properties
- Each response includes `end_of_message: bool` field
- Final response has `end_of_message: True`

This matches the pattern used in `AgentResponse` and other streaming services.

### Response Handling: String Return

All existing tools follow the same pattern: **receive arguments as a dict, return observation as a string**.

| Tool | Response Handling |
|------|------------------|
| `KnowledgeQueryImpl` | Returns `client.rag()` directly (string) |
| `TextCompletionImpl` | Returns `client.question()` directly (string) |
| `McpToolImpl` | Returns string, or `json.dumps(output)` if not string |
| `StructuredQueryImpl` | Formats result to string |
| `PromptImpl` | Returns `client.prompt()` directly (string) |

Tool services follow the same contract:
- The service returns a string response (the observation)
- If the response is not a string, it is converted via `json.dumps()`
- No extraction configuration needed in the descriptor

This keeps the descriptor simple and places responsibility on the service to return an appropriate text response for the agent.

## Implementation

### Schema

Request and response types in `trustgraph-base/trustgraph/schema/services/tool_service.py`:

```python
@dataclass
class ToolServiceRequest:
    user: str = ""           # User context for multi-tenancy
    config: str = ""         # JSON-encoded config values from tool descriptor
    arguments: str = ""      # JSON-encoded arguments from LLM

@dataclass
class ToolServiceResponse:
    error: Error | None = None
    response: str = ""       # String response (the observation)
    end_of_stream: bool = False
```

### Server-Side: DynamicToolService

Base class in `trustgraph-base/trustgraph/base/dynamic_tool_service.py`:

```python
class DynamicToolService(AsyncProcessor):
    """Base class for implementing tool services."""

    def __init__(self, **params):
        topic = params.get("topic", default_topic)
        # Constructs topics: non-persistent://tg/request/{topic}, non-persistent://tg/response/{topic}
        # Sets up Consumer and Producer

    async def invoke(self, user, config, arguments):
        """Override this method to implement the tool's logic."""
        raise NotImplementedError()
```

### Client-Side: ToolServiceImpl

Implementation in `trustgraph-flow/trustgraph/agent/react/tools.py`:

```python
class ToolServiceImpl:
    def __init__(self, context, request_queue, response_queue, config_values, arguments, processor):
        # Uses the provided queue paths directly
        # Creates ToolServiceClient on first use

    async def invoke(self, **arguments):
        client = await self._get_or_create_client()
        response = await client.call(user, config_values, arguments)
        return response if isinstance(response, str) else json.dumps(response)
```

### Configuration Structure

Two config sections:

```
tool-service/
  joke-service: {"id": "joke-service", "request-queue": "non-persistent://tg/request/joke", "response-queue": "non-persistent://tg/response/joke", "config-params": [...]}

tool/
  tell-joke: {"type": "tool-service", "service": "joke-service", ...}
```

### Files

| File | Purpose |
|------|---------|
| `trustgraph-base/trustgraph/schema/services/tool_service.py` | Request/response schemas |
| `trustgraph-base/trustgraph/base/tool_service_client.py` | Client for invoking services |
| `trustgraph-base/trustgraph/base/dynamic_tool_service.py` | Base class for service implementation |
| `trustgraph-flow/trustgraph/agent/react/tools.py` | `ToolServiceImpl` class |
| `trustgraph-flow/trustgraph/agent/react/service.py` | Config loading |

### Example: Joke Service

An example service in `trustgraph-flow/trustgraph/tool_service/joke/`:

```python
class Processor(DynamicToolService):
    async def invoke(self, user, config, arguments):
        style = config.get("style", "pun")
        topic = arguments.get("topic", "")
        joke = pick_joke(topic, style)
        return f"Hey {user}! Here's a {style} for you:\n\n{joke}"
```

Tool service config:
```json
{
  "id": "joke-service",
  "request-queue": "non-persistent://tg/request/joke",
  "response-queue": "non-persistent://tg/response/joke",
  "config-params": [{"name": "style", "required": false}]
}
```

Tool config:
```json
{
  "type": "tool-service",
  "name": "tell-joke",
  "description": "Tell a joke on a given topic",
  "service": "joke-service",
  "style": "pun",
  "arguments": [
    {"name": "topic", "type": "string", "description": "The topic for the joke"}
  ]
}
```

### Backward Compatibility

- Existing built-in tool types continue to work unchanged
- `tool-service` is a new tool type alongside existing types (`knowledge-query`, `mcp-tool`, etc.)

## Future Considerations

### Self-Announcing Services

A future enhancement could allow services to publish their own descriptors:

- Services publish to a well-known `tool-descriptors` topic on startup
- Agent subscribes and dynamically registers tools
- Enables true plug-and-play without config changes

This is out of scope for the initial implementation.

## References

- Current tool implementation: `trustgraph-flow/trustgraph/agent/react/tools.py`
- Tool registration: `trustgraph-flow/trustgraph/agent/react/service.py:105-214`
- Agent schemas: `trustgraph-base/trustgraph/schema/services/agent.py`
