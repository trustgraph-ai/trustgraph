---
layout: default
title: "Cloze Model Service Technical Specification"
parent: "Tech Specs"
---

# Cloze Model Service Technical Specification

## Problem

TrustGraph currently delegates all decision-making to LLM
text-completion services. This includes simple classification tasks —
tool selection, intent routing, topic categorisation — where the decision
space is small and the mapping from input to label is learnable from
a modest number of examples.

Using an LLM for these decisions has three costs:

1. **Latency**. A round-trip to a text-completion service adds hundreds
   of milliseconds to every decision, even when the answer is a single
   token. In agent flows that chain multiple decisions, this compounds.

2. **Token cost**. Each classification consumes input and output tokens.
   For high-volume decisions (every user query, every extraction step),
   these costs add up with no corresponding value — the LLM's generative
   capability is wasted on a task that requires only discrimination.

3. **Brittleness**. LLM outputs require parsing and validation. A
   classification prompt can return unexpected formats, hallucinated
   labels, or refusals. The failure modes are disproportionate to the
   simplicity of the task.

## Solution

A cloze-style model — trained to predict a masked label given an input
pattern — is a natural fit for these decisions. The model is small,
fast, locally hosted, and deterministic. It produces a label and a
confidence score, with no parsing ambiguity.

The solution has three components:

1. **Cloze model service**. A new TrustGraph service that auto-trains a
   cloze model from labeled examples stored in config. When config
   changes, the model retrains automatically via config push events. The
   service serves the trained model for inference, accepting an input and
   returning a single label with a confidence score.

2. **API support**. A request/response API for submitting inputs and
   receiving classification results, integrated with the existing
   TrustGraph pub/sub and API gateway infrastructure.

3. **CLI tooling**. Command-line tools for managing cloze model training
   data, inspecting model state, and testing classifications
   interactively.

The cloze model service does not replace existing LLM-based
decision-making. It is another tool in the armoury — a lightweight,
fast option that sits alongside text-completion services. Some decisions
will always need the full generative capability of an LLM; others are
better served by a small, purpose-trained classifier. The choice of
which to use for a given task is a design decision, not a migration.

The service generalises beyond any single use case. Tool selection is one
application, but the same service handles any input-to-label
classification: intent routing, topic detection, entity type
discrimination, or flow selection.

This requires a new service shape — the existing text-completion service
pattern assumes an LLM backend and free-form output. The cloze model
service has a different lifecycle (train-then-serve rather than
proxy-to-backend) and a different output contract (label + confidence
rather than generated text).

## Technical Design

### Training Data Model

Training data is stored in the config service and pushed to the cloze
model service via config push events. The configuration has two levels:
top-level training parameters, and per-label example data.

#### Top-Level Parameters

- **min-accuracy** (optional) — minimum evaluation accuracy required
  for the model to be accepted, as a fraction (e.g. `0.96` for 96%).
  If the trained model fails to meet this threshold, the service
  retains the previous model and logs an error. Defaults to no
  threshold.
- **test-split** (optional) — fraction of examples to hold back for
  evaluation, range 0.0–1.0. Defaults to `0.2` (20%). The split is
  stratified so each label contributes proportionally to train and
  test sets.

#### Per-Label Data

Each label provides:

- **token** — a special token name for the label (e.g. `[TOOL_WEATHER]`)
- **seed** — a base vocabulary word used to warm-start the token's
  embedding (e.g. `weather`)
- **examples** — a list of example inputs that should map to this label

```json
{
    "min-accuracy": 0.96,
    "test-split": 0.2,
    "labels": [
        {
            "token": "[TOOL_WEATHER]",
            "seed": "weather",
            "examples": [
                "Is it going to rain in Manchester today?",
                "What's the temperature outside right now?",
                "Give me the 7-day forecast for Tokyo."
            ]
        },
        {
            "token": "[TOOL_CALCULATOR]",
            "seed": "math",
            "examples": [
                "What is the square root of 289?",
                "Compute 15% tip on a bill of $84.20."
            ]
        }
    ]
}
```

The service auto-splits each label's examples into training and
evaluation sets using the `test-split` ratio. After training, it
evaluates the model against the held-out set. If `min-accuracy` is
specified and the model falls short, the service rejects the new model,
retains the previous one, and logs the failure with the achieved
accuracy.

#### Multi-Instance

The cloze service hosts multiple independent model instances. Each
training configuration item in the config service has a key (provided
by the config service infrastructure) which serves as the model
instance name. For example, a config key of `tool-router` produces a
model instance named `tool-router`; a key of `intent-classifier`
produces a separate instance named `intent-classifier`.

When training data changes, only the affected instance retrains. Each
instance has its own model, label set, and accuracy state — they are
fully independent.

The config type for this data is TBD (e.g. `cloze-training`). When the
config service receives a put or delete for this type, the config push
notify triggers the cloze model service to fetch the new training data
and retrain the affected instance.

### Model Lifecycle

1. **Startup**. The service starts with no trained model. It fetches
   training data from the config service via the subscribe-then-fetch
   pattern. If training data exists, it trains immediately.

2. **Config change**. When a config push notify arrives for the
   training data type, the service fetches the updated training data
   and retrains. The previous model continues to serve requests until
   the new model is ready, then swaps atomically.

3. **No training data**. If no training data is configured, the service
   responds to inference requests with an error indicating no model is
   available.

### Model Architecture

The base model is a flow parameter — the service does not hardcode a
specific model. The default is `distilbert-base-uncased`, but any
HuggingFace masked language model can be specified in the flow
definition. The service fine-tunes the configured base model on the
training data:

- Custom special tokens are registered for each label (e.g.
  `[TOOL_WEATHER]`).
- Token embeddings are warm-started by copying vectors from the
  corresponding seed words in the base vocabulary.
- Training uses the cloze pattern: input is formatted as
  `"Query: {input} Tool: [MASK]"` and the model learns to predict the
  correct label token at the mask position.
- Differential learning rates: gentle updates for the pre-trained
  backbone (2e-5), stronger updates for new token embeddings and the
  prediction head (1e-4).

At inference time, prediction is constrained to the registered label
tokens. Softmax over the candidate logits produces a confidence score.

### Request/Response Data Shapes

The cloze model service follows the existing request/response pattern
with dataclass schemas, translators, and queue registration.

#### Request

```python
@dataclass
class ClozeRequest:
    model: str = ""
    query: str = ""
```

- **model** — the name of the model instance to invoke (matches the
  config key, e.g. `tool-router` or `intent-classifier`)
- **query** — the input text to classify

If the named model instance does not exist or has no trained model,
the service returns an error in the response.

#### Response

```python
@dataclass
class ClozeResponse:
    error: Error | None = None
    label: str = ""
    confidence: float = 0.0
```

- **label** — the predicted label token, stripped of brackets
  (e.g. `TOOL_WEATHER` not `[TOOL_WEATHER]`)
- **confidence** — softmax probability over the candidate set,
  range 0.0–1.0

#### Queues

```python
cloze_request_queue = queue('cloze', cls='request')
cloze_response_queue = queue('cloze', cls='response')
```

#### Gateway Integration

A `ClozeRequestor` is added to the gateway's dispatcher mapping,
following the same pattern as `TextCompletionRequestor`:

```python
request_response_dispatchers = {
    ...
    "cloze": ClozeRequestor,
}
```

Translators are registered in the translator registry:

```python
TranslatorRegistry.register_service(
    "cloze",
    ClozeRequestTranslator(),
    ClozeResponseTranslator(),
)
```

### Service Shape

The cloze model service extends `FlowProcessor` but differs from
`LlmService` in one key way: it has an internal model lifecycle. Where
`LlmService` proxies requests to an external LLM backend, the cloze
service owns its model — training it from config data and serving it
directly.

This means the service:

- Registers a config handler for the training data type (like other
  config-driven services).
- Manages model state internally (current model, training in progress,
  no model available).
- Handles request/response on the cloze queues using the standard
  `ConsumerSpec`/`ProducerSpec` pattern.

```python
class ClozeService(FlowProcessor):
    def __init__(self, **params):
        super().__init__(**params)

        self.register_specification(
            ParameterSpec(name="model")
        )

        self.register_config_handler(
            handler=self.on_training_config,
            types=["cloze-training"],
        )

        self.register_specification(
            ConsumerSpec(
                name="request",
                schema=ClozeRequest,
                handler=self.on_request,
            )
        )

        self.register_specification(
            ProducerSpec(
                name="response",
                schema=ClozeResponse,
            )
        )
```
