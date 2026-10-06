---
layout: default
title: "Model Listing"
parent: "Tech Specs"
---

# Model Listing

## Status

Draft

## Problem Statement

TrustGraph's text-completion service currently requires callers to know
the exact model identifier upfront.  There is no way to discover which
models are available from the configured LLM backend, their
capabilities, context limits, or pricing.  This forces users to consult
external documentation for every provider and makes it impossible for
UIs or agents to present a model picker dynamically.

TrustGraph already has a model listing feature, but it is based on a
static configuration file served by the config service.  This is
manually maintained and can drift out of sync with what the backend
actually offers.

Many LLM providers already expose a model listing endpoint (OpenAI
`GET /v1/models`, Ollama `client.list()`, Google GenAI
`list_models()`, Bedrock `list_foundation_models()`).  TrustGraph
should surface this information through a unified interface.

In a subsequent phase, the live model listing could be used to
automate generation or validation of the static config file, but
that is out of scope here.

## Goals

- Allow callers to discover available models from the configured LLM
  backend via the existing text-completion service.
- Return a normalised superset of model metadata covering the common
  fields across providers: identifier, display name, context window,
  output limits, modalities, features, and pricing.
- Fields that a provider does not supply are returned as null/missing.
- Backends that do not support model listing return a
  "not-implemented" error rather than silently failing.
- No new Pulsar topics or service containers — the operation is
  multiplexed onto the existing text-completion request/response
  channel via an `operation` field.

## Background

The standard OpenAI `GET /v1/models` response is the de facto schema
for model listing:

```json
{
  "object": "list",
  "data": [
    {
      "id": "gpt-4o",
      "object": "model",
      "created": 1715368132,
      "owned_by": "system"
    }
  ]
}
```

OpenAI-compatible aggregators (Near AI, OpenRouter, DeepInfra, LiteLLM)
extend this with pricing, context limits, modality, and feature
metadata.  Local runtimes (Ollama, LM Studio, vLLM) add hardware and
format details (`family`, `parameter_size`, `quantization_level`).

The TrustGraph schema captures a useful superset.  Missing information
is simply omitted.

## Technical Design

### Operation Multiplexing

The `TextCompletionRequest` gains an `operation` field that selects
what the service should do:

| Operation        | Behaviour                              |
|------------------|----------------------------------------|
| `"completion"`   | Standard text completion (default)     |
| `"list-models"`  | Return available models                |

When `operation` is absent or `"completion"`, behaviour is identical
to today — full backward compatibility.

### Data Model

#### ModelInfo

A normalised model descriptor returned in the response:

```python
@dataclass
class ModelInfo:
    id: str = ""                              # Model identifier for API calls
    name: str | None = None                   # Human-readable display name
    owned_by: str | None = None               # Owner / organisation
    created: int | None = None                # Unix timestamp
    description: str | None = None            # Model overview

    # Limits
    context_length: int | None = None         # Max context window (tokens)
    max_output_length: int | None = None      # Max generation length (tokens)

    # Capabilities
    input_modalities: list[str] = field(default_factory=list)   # e.g. ["text", "image"]
    output_modalities: list[str] = field(default_factory=list)  # e.g. ["text"]
    supported_features: list[str] = field(default_factory=list) # e.g. ["tools", "structured_outputs", "reasoning"]

    # Pricing (per million tokens, USD)
    input_price: float | None = None
    output_price: float | None = None

    # Local runtime metadata
    family: str | None = None                 # e.g. "llama", "qwen"
    parameter_size: str | None = None         # e.g. "7B", "70B"
    quantization: str | None = None           # e.g. "Q4_K_M", "FP16"
    format: str | None = None                 # e.g. "gguf", "safetensors"
```

#### Schema Changes

`TextCompletionRequest` adds:

```python
@dataclass
class TextCompletionRequest:
    operation: str = "completion"   # "completion" or "list-models"
    system: str = ""
    prompt: str = ""
    streaming: bool = False
    response_format: str | None = None
    schema: dict | None = None
```

`TextCompletionResponse` adds:

```python
@dataclass
class TextCompletionResponse:
    error: Error | None = None
    response: str = ""
    in_token: int | None = None
    out_token: int | None = None
    model: str | None = None
    end_of_stream: bool = False
    models: list[ModelInfo] = field(default_factory=list)  # Populated for list-models
```

When `operation="list-models"`, the `system`, `prompt`, `streaming`,
`response_format`, and `schema` fields are ignored.  The response
carries the model list in `models` with `response` empty.

### LlmService Base Class

Add a default `list_models` method:

```python
async def list_models(self):
    """Return available models. Override in backends that support it."""
    raise NotImplementedError("list-models")
```

The `on_request` handler dispatches on `operation`:

```python
if request.operation == "list-models":
    try:
        models = await self.list_models()
        # send response with models=models
    except NotImplementedError:
        # send error response: type="not-implemented",
        # message="This backend does not support model listing"
```

### Backend Implementations

| Backend        | SDK Call                                     | Status    |
|----------------|----------------------------------------------|-----------|
| OpenAI         | `client.models.list()`                       | Supported |
| Ollama         | `client.list()`                              | Supported |
| Google GenAI   | `genai.models.list()`                        | Supported |
| VertexAI       | `genai.models.list()`                        | Supported |
| Bedrock        | `client.list_foundation_models()`            | Supported |
| Mistral        | SDK models endpoint (if available)           | TBD       |
| vLLM           | `GET /v1/models` (OpenAI-compatible)         | Supported |
| LM Studio      | `GET /v1/models` (OpenAI-compatible)         | Supported |
| TGI            | `GET /v1/models` or `GET /info`              | TBD       |
| LlamaFile      | `GET /v1/models` (OpenAI-compatible)         | Supported |
| Claude         | `client.models.list()`                       | Supported |
| Azure OpenAI   | Deployment-scoped, no generic listing        | Not supported |
| Azure Serverless | No standard listing                        | Not supported |
| Cohere         | No listing API                               | Not supported |

Backends marked "Not supported" return the `not-implemented` error.

Each supported backend maps provider-specific fields to `ModelInfo`.
For example, the OpenAI backend maps `id`, `created`, `owned_by`
directly and leaves `context_length`, `description`, etc. as None
unless the provider's response includes extended fields (as Near AI
does).  Ollama maps `details.family`, `details.parameter_size`,
`details.quantization_level` to the local runtime fields.

### Translator Changes

`TextCompletionRequestTranslator.decode` adds:

```python
operation=data.get("operation", "completion"),
```

`TextCompletionResponseTranslator.encode` adds:

```python
if obj.models:
    result["models"] = [dataclass_to_dict(m) for m in obj.models]
```

### Gateway / API

The existing `text-completion` service dispatch path handles both
operations without change — the gateway already forwards the full
request payload.  Callers send a `text-completion` request with
`{"operation": "list-models"}` and receive the model list in the
response.

### CLI

Add a new command `tg-list-models` (or extend `tg-invoke-text-completion`
with a `--list-models` flag) that sends a `list-models` operation and
prints the results as a table or JSON.

## Security Considerations

Model listing is read-only and exposes no sensitive data beyond what
the LLM provider already makes public.  Existing IAM capability checks
on the `text-completion` service apply — callers need the `llm`
capability.

## Performance Considerations

Model listing is a cold metadata call, not a hot path.  No caching is
required initially; if providers rate-limit the endpoint, a TTL cache
can be added in the base class later.

## Testing Strategy

- Unit tests for each backend's `list_models()` mapping, mocking the
  SDK response.
- Unit test for the `on_request` dispatch: `operation="list-models"`
  routes correctly, unknown operations return an error.
- Unit test for `not-implemented` error from backends that don't
  support it.
- Translator round-trip test for the new fields.
- Integration test: call via the gateway API and verify the response
  schema.

## Design Decisions

- **No server-side filtering** — the full model list is returned and
  callers filter client-side.
- **No default model field** — the response is a pure model list;
  default model selection is the caller's concern.
- **No loaded/available distinction** — some local runtimes only
  return loaded models; this is acceptable and no additional status
  field is needed.
