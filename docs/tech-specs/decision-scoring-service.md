---
layout: default
title: "Decision Scoring Service Technical Specification"
parent: "Tech Specs"
---

# Decision Scoring Service Technical Specification

## Problem

TrustGraph currently relies on LLM text-completion services for all
decision-making, including tasks that require only a simple judgment:
choosing between options, scoring relevance, or making a yes/no call.
These are not generative tasks — they need discrimination, not prose.

Using an LLM for these decisions has three costs:

1. **Latency**. A full text-completion round-trip for a decision that
   could be expressed as a single number or a selection from a short
   list.

2. **Token cost**. Input and output tokens are consumed for every
   decision, regardless of complexity. High-frequency decisions —
   per-query routing, per-chunk scoring, per-candidate filtering —
   accumulate cost with no corresponding value from the LLM's
   generative capability.

3. **Brittleness**. Extracting a structured decision from free-text
   LLM output requires parsing, validation, and fallback handling.
   The failure modes are disproportionate to the simplicity of the
   task.

A new class of models has emerged that targets exactly this gap.
Models such as Laya (open) and Jev (commercial) are purpose-built for
fast, structured decision-making — not generation. They accept an
input and a specification of the desired output, and produce one of
three result types:

- **Choice** — select one option from a provided set
- **Score** — given a set of ordered levels (e.g. 0=unrelated,
  1=adjacent, 2=some direct, 3=deep direct), the model produces a
  probability distribution across the levels. The output is the
  expected value (weighted sum of level × probability) and a
  confidence (the highest individual probability).
- **Noul** — a binary confidence value from 0.0 (no) to 1.0 (yes)

A single request can specify multiple outputs, each independently
configured as choice, score, or noul. For example, a single call might
ask for a topic choice, a relevance score, and a yes/no safety noul —
all evaluated together against the same input.

These models are designed for System 1 thinking: fast, automatic
pattern-matching rather than slow deliberative reasoning. Multiple
models now support this approach, and more are expected. TrustGraph
needs a service layer that can integrate them.

## Solution

A new TrustGraph service — `decision-scoring-laya` — that wraps the
Laya open model behind the standard request/response pattern. The
service name follows the existing convention (e.g.
`text-completion-openai`): `decision-scoring` is the abstract service
kind, `-laya` identifies the backend. Additional backends (e.g.
`decision-scoring-jev`) can follow the same pattern.

### Output Specification

Each request includes the input text and an output specification — a
map of named outputs, each independently configured. The specification
is caller-defined: criteria are arbitrary user-provided strings, not a
fixed vocabulary.

```json
{
    "department": {
        "type": "choice",
        "instructions": "Which team should handle this ticket?",
        "criteria": [
            "billing",
            "technical",
            "sales"
        ]
    },
    "urgency": {
        "type": "score",
        "instructions": "How urgent is this request?",
        "criteria": [
            "none",
            "low",
            "medium",
            "high",
            "critical"
        ]
    },
    "refund_requested": {
        "type": "noul",
        "instructions": "Does the customer explicitly request a refund?"
    }
}
```

- **Choice** outputs require `criteria` — the set of options to select
  from. The result is the selected option and a confidence.
- **Score** outputs require `criteria` — an ordered list of levels. The
  model produces a probability distribution across the levels; the
  result is the expected value (weighted sum) and a confidence. Level
  ordering is positional (index 0 is lowest).
- **Noul** outputs take no criteria. The result is a single value from
  0.0 (no) to 1.0 (yes).

Each output has `instructions` — natural language guidance telling the
model what to evaluate.

The decision scoring service does not replace existing LLM-based
decision-making. It is another tool in the armoury — a lightweight,
fast option that sits alongside text-completion services. Some decisions
will always need the full generative capability of an LLM; others are
better served by a purpose-built decision model. The choice of which to
use for a given task is a design decision, not a migration.

## Technical Design

### Laya Integration

The service loads the Laya `Router` in-process with preloaded
checkpoints. Inference is ~35ms per call — no external API round-trip.

```python
from laya import Router
router = Router(preload=True)
```

Laya auto-routes to the appropriate model variant based on input
language: ModernBERT-large for English, mmBERT-base for multilingual.
The service can also accept an explicit model override via flow
parameter.

### Request/Response Data Shapes

#### Request

```python
@dataclass
class DecisionScoringRequest:
    state: dict = field(default_factory=dict)
    questions: dict = field(default_factory=dict)
```

- **state** — freeform input data. Can be any structure: a simple
  string, a dict with fields like `from`, `subject`, `body`, or any
  application-specific shape. This is what the model evaluates.
- **questions** — the output specification map, as described in the
  Solution section. Each key is an output name, each value specifies
  type, instructions, and criteria.

Note: for **choice** outputs, criteria can be either a list of options
or a dict mapping options to descriptions that guide the model:

```json
{
    "criteria": {
        "billing": "invoices, payments, refunds",
        "technical": "bugs, outages, system errors",
        "sales": "pricing, new contracts"
    }
}
```

#### Response

```python
@dataclass
class DecisionScoringResponse:
    error: Error | None = None
    answers: dict = field(default_factory=dict)
    model: str = ""
```

- **answers** — a map keyed by the same output names as the request's
  questions. Each entry contains type-specific results:

  For **choice**:
  ```json
  {
      "department": {
          "type": "choice",
          "choice": "billing",
          "confidence": 0.94
      }
  }
  ```

  For **score**:
  ```json
  {
      "urgency": {
          "type": "score",
          "score": 1.85,
          "confidence": 0.72,
          "distribution": [0.05, 0.23, 0.72]
      }
  }
  ```

  For **noul**:
  ```json
  {
      "refund_requested": {
          "type": "noul",
          "value": 0.92
      }
  }
  ```

- **model** — which Laya model variant handled the request (e.g.
  `english`, `multilingual`).

#### Queues

```python
decision_scoring_request_queue = queue('decision-scoring', cls='request')
decision_scoring_response_queue = queue('decision-scoring', cls='response')
```

#### Gateway Integration

A `DecisionScoringRequestor` is added to the gateway's dispatcher
mapping:

```python
request_response_dispatchers = {
    ...
    "decision-scoring": DecisionScoringRequestor,
}
```

Translators are registered in the translator registry:

```python
TranslatorRegistry.register_service(
    "decision-scoring",
    DecisionScoringRequestTranslator(),
    DecisionScoringResponseTranslator(),
)
```

### Service Shape

The service extends `FlowProcessor`. Unlike the cloze model service,
it does not train — Laya's models are pre-trained checkpoints loaded
at startup. The service is stateless beyond the loaded model weights.

```python
class DecisionScoringService(FlowProcessor):
    def __init__(self, **params):
        super().__init__(**params)

        self.register_specification(
            ParameterSpec(name="model")
        )

        self.register_specification(
            ConsumerSpec(
                name="request",
                schema=DecisionScoringRequest,
                handler=self.on_request,
            )
        )

        self.register_specification(
            ProducerSpec(
                name="response",
                schema=DecisionScoringResponse,
            )
        )
```

The `model` parameter is optional. If set, it overrides Laya's
auto-routing and forces a specific checkpoint (e.g.
`typed-decisions`). If omitted, Laya selects the appropriate model
based on the input language.

### Concurrency

Laya's `Router` exposes a threads setting, suggesting it supports
concurrent inference. The service should configure `ConsumerSpec`
concurrency and the Router's thread count to match, allowing multiple
requests to be processed in parallel.

### CLI Tooling

A command-line tool (e.g. `tg-decision-score`) for interactive testing
of the decision scoring service. Takes state and a questions
specification, submits to the service, and prints the results. Useful
for validating question specifications and debugging scoring behaviour
during development.
