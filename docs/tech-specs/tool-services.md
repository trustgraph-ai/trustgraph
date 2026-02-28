# Tool Services: Dynamically Pluggable Agent Tools

## Status

Draft - Gathering Requirements

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
- The topic to call
- Configuration parameters it requires from tools that use it

```json
{
  "id": "custom-rag",
  "topic": "custom-rag-request",
  "config-params": [
    {"name": "collection", "required": true}
  ]
}
```

A tool service that needs no configuration parameters:

```json
{
  "id": "calculator",
  "topic": "calc-request",
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

### Client Interface: Direct Pulsar

Tool services are invoked via direct Pulsar messaging, not through the existing typed client abstraction. The tool-service descriptor specifies a Pulsar queue name. A base class will be defined for implementing tool services. Implementation details to be determined during development.

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

## Open Questions

### Streaming Support

- Should tool services support streaming responses?
- How would streaming be configured in the descriptor?

## Implementation Considerations

### Configuration Structure

Two new config sections:

```
tool-service/
  custom-rag: {"id": "custom-rag", "topic": "...", "config-params": [...]}
  calculator: {"id": "calculator", "topic": "...", "config-params": []}

tool/
  query-customers: {"type": "tool-service", "service": "custom-rag", ...}
  query-products: {"type": "tool-service", "service": "custom-rag", ...}
```

### Files to Modify

| File | Changes |
|------|---------|
| `trustgraph-flow/trustgraph/agent/react/tools.py` | Add `ToolServiceImpl` |
| `trustgraph-flow/trustgraph/agent/react/service.py` | Load tool-service configs, handle `type: "tool-service"` in tool configs |
| `trustgraph-base/trustgraph/base/` | Add generic client call support |

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
