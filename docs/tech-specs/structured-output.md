---
layout: default
title: "Structured Output: LLM-Native JSON Schema Enforcement"
parent: "Tech Specs"
---

# Structured Output: LLM-Native JSON Schema Enforcement

## Problem / Opportunity

TrustGraph's knowledge-graph pipeline relies on LLMs to produce
structured JSON output — entity extractions, relationship triples,
topic classifications, and other schema-governed artefacts.  Today,
the correct structure is requested via natural-language instructions
embedded in the prompt template: the prompt describes the expected
JSON shape, and the system parses the LLM's free-text response,
hoping it conforms.

This approach has several weaknesses:

1. **Fragile parsing.**  LLM responses may include markdown fencing,
   preamble text, trailing commentary, or minor schema violations
   (missing fields, wrong types, extra keys).  Every consumer must
   tolerate or work around these deviations, adding defensive code
   and retry logic.

2. **Wasted tokens and latency.**  A significant portion of each
   prompt is spent describing the output format in prose.  When the
   model deviates, retries consume additional tokens and add
   end-to-end latency.

3. **Silent data-quality issues.**  Malformed responses that pass
   lenient parsing can inject bad data into the knowledge graph —
   wrong types, truncated lists, invented field names — without
   raising errors.

4. **Untapped LLM capability.**  Most modern LLMs (OpenAI, Google
   Gemini, Anthropic Claude, Ollama-hosted models via llama.cpp)
   support *structured output* or *guided decoding*: the caller
   supplies a JSON schema and the model constrains token selection at
   the logit level to guarantee schema-valid output.  TrustGraph
   already defines the required JSON schemas inside its prompt
   definitions but does not pass them through to the LLM backend.

### Opportunity

By threading the existing JSON schemas from prompt definitions
through the text-completion service to each LLM backend's native
structured-output API, TrustGraph can:

- **Guarantee valid output** on every call — no parsing heuristics,
  no retries for format errors.
- **Reduce prompt size** by removing prose format instructions that
  the schema makes redundant.
- **Improve data quality** in the knowledge graph by eliminating an
  entire class of silent ingestion errors.
- **Simplify service code** by removing defensive JSON extraction and
  validation logic from every consumer.

## Scope

Prompt definitions declare a `response-type` of `"text"`, `"json"`,
or `"jsonl"`.  Structured output applies only to prompts that produce
machine-readable output (`"json"` and `"jsonl"`).

JSONL presents a compatibility challenge: LLM structured-output APIs
enforce a single top-level JSON schema, but JSONL prompts ask the
model to emit one JSON object per line — a format that is not itself
valid JSON.  Converting JSONL prompts to request a JSON array would
conflict with the prompt text and sacrifice truncation resilience
(partial JSONL is recoverable line-by-line; a truncated array is
broken JSON).

This spec takes a three-phase approach:

- **Phase 1** — plumb schemas through to LLM backends with automatic
  compatibility detection; non-compliant schemas fall back to the
  current free-text path.
- **Phase 2** — fix up non-compliant schemas so more prompts benefit.
- **Phase 3** — address JSONL prompts.

---

## Phase 1 — Structured Output with Automatic Fallback

### Design

Phase 1 threads the JSON schema from the prompt definition through
the text-completion service to the LLM backend's native
structured-output API.  Only prompts with `response-type: "json"` are
candidates.

Not all existing schemas are compatible with LLM structured-output
APIs.  Rather than require schema changes up front, Phase 1 includes
a **runtime compatibility check**: if a schema passes, structured
output is used; if not, the prompt falls back to the current
free-text path with post-hoc validation.  This makes the feature
safe to deploy immediately.

### Strict-Mode Schema Requirements

LLM providers impose constraints beyond standard JSON Schema
validation.  A schema is considered strict-mode compatible when:

- Every `object` has `additionalProperties: false`.
- Every property defined in `properties` appears in `required`.
  Optional fields use a nullable type (e.g. `"type": ["string", "null"]`)
  instead of omitting the key from `required`.
- No `minimum`, `maximum`, `minLength`, `maxLength`, or `pattern`
  constraints (unsupported by most providers' constrained decoders).
- No open-ended objects (`{"type": "object"}` without `properties`).
- A schema is present and non-null.

### Runtime Compatibility Check

`PromptManager` (or a shared utility) inspects each schema at load
time against the strict-mode rules above.  The result is a boolean
flag per prompt: `structured_output_eligible`.

- **Eligible** — `response_format` and `schema` are set on the
  `TextCompletionRequest`; the LLM enforces the schema at generation
  time.
- **Not eligible** — request is sent without schema fields; the
  current free-text parsing and `jsonschema.validate()` path is used.

This is a per-prompt decision, not a global switch.

### Text-Completion Request Changes

`TextCompletionRequest` gains two optional fields:

```
TextCompletionRequest:
    system:          str
    prompt:          str
    streaming:       bool
    response_format: str | None     # "json" or None (default)
    schema:          dict | None    # JSON Schema object or None
```

When `response_format` is `"json"` and `schema` is provided, the LLM
backend MUST use its native structured-output mechanism.  When either
field is absent or null, behaviour is unchanged.

### LLM Backend Mapping

Each backend maps `response_format` + `schema` to its provider's
native API:

| Backend    | API mechanism                                         |
|------------|-------------------------------------------------------|
| OpenAI     | `response_format={"type": "json_schema", "json_schema": {"name": "...", "schema": ...}}` |
| Claude     | `tool_use` with a single tool whose `input_schema` is the target schema, or the `response_format` parameter when available |
| Gemini     | `response_mime_type="application/json"` + `response_schema=...` |
| Ollama     | `format="json"` + schema in the `format` field (llama.cpp guided decoding) |
| Llamafile  | `response_format={"type": "json_object"}` + schema    |

Backends that do not support schema-level enforcement (e.g. older
Ollama versions) fall back to `response_format=json` without a schema
and rely on post-hoc validation.

### Current Prompt Compatibility

Of the nine `response-type: "json"` prompts, two are strict-mode
compatible today:

| Prompt                   | Status    | Issue                              |
|--------------------------|-----------|------------------------------------|
| `schema-selection`       | Ready     | —                                  |
| `supervisor-decompose`   | Ready     | —                                  |
| `plan-create`            | Fixable   | Optional fields not in `required`  |
| `graphql-generation`     | Blocked   | Open-ended `variables` object; `minimum`/`maximum` on `confidence` |
| `plan-step-execute`      | Blocked   | Open-ended `arguments` object      |
| `diagnose-structured-data` | No schema | —                                |
| `diagnose-xml`           | No schema | —                                  |
| `diagnose-json`          | No schema | —                                  |
| `diagnose-csv`           | No schema | —                                  |

### What Does Not Change

- Prompt templates and their text content.
- The `"text"` and `"jsonl"` response-type paths.
- The `TextCompletionResponse` schema.
- Post-hoc validation (retained as a defence-in-depth measure).

---

## Phase 2 — Schema Remediation

Phase 2 expands structured-output coverage by fixing schemas that
failed the Phase 1 compatibility check.

### Fixable Schemas

**`plan-create`** — `tool_hint` and `depends_on` are optional
(present in `properties` but absent from `required`).  Fix: add both
to `required` and change their types to nullable:

```json
"tool_hint": {"type": ["string", "null"]},
"depends_on": {
    "type": ["array", "null"],
    "items": {"type": "integer"}
}
```

### Schemas Requiring Design Decisions

**`graphql-generation`** — Two issues:

- `variables` is an open-ended object (`"additionalProperties": true`)
  with no fixed properties.  Constrained decoding cannot handle
  arbitrary keys.  Options: remove `variables` from the schema and
  accept it as free-form text within a wrapper, or restructure as a
  JSON-encoded string field.
- `confidence` uses `"minimum": 0.0, "maximum": 1.0`.  Fix: remove
  the numeric bounds; accept any number and clamp in application code
  if needed.

**`plan-step-execute`** — `arguments` is an open-ended object with no
fixed properties.  Same constraint as `graphql-generation.variables`.

### Missing Schemas

The four `diagnose-*` prompts have `response-type: "json"` but no
schema.  Adding schemas for these prompts would bring them into
structured-output scope.  This requires defining the expected
response shape for each diagnostic prompt.

---

## Phase 3 (Future) — Structured Output for JSONL Prompts

JSONL prompts ask the LLM to emit multiple JSON objects, one per
line.  Each object is validated individually against the prompt's
schema.  The current approach is tolerant of truncation and
malformed lines — useful properties for large extractions.

### Options

**Option A — Array wrapper.**  Change the prompt text to request a
JSON array instead of JSONL.  Wrap the schema as
`{"type": "array", "items": <existing-schema>}` and use structured
output.  Trade-off: loses line-by-line truncation resilience; requires
updating every JSONL prompt template.

**Option B — Structured output per chunk.**  Split the input so each
text-completion call produces a single JSON object, then aggregate.
Trade-off: more LLM calls; higher latency and cost; may not suit
prompts that extract variable-length lists from a single chunk.

**Option C — Hybrid.**  Use structured output with the array-wrapped
schema but retain the post-hoc JSONL parser as a fallback for
backends that do not support structured output or when the response
is truncated.  Trade-off: two code paths to maintain.

**Option D — Status quo.**  Leave JSONL prompts on the free-text path
with post-hoc validation.  Structured output for `"json"` prompts
already covers the most schema-sensitive cases; JSONL extraction is
inherently more tolerant of partial results.

Phase 3 design will be selected after earlier phases are deployed and
real-world structured-output behaviour is observed across backends.
