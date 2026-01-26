# JSONL Prompt Output Technical Specification

## Overview

This specification describes the implementation of JSONL (JSON Lines) output
format for prompt responses in TrustGraph. JSONL enables truncation-resilient
extraction of structured data from LLM responses, addressing critical issues
with JSON array outputs being corrupted when LLM responses hit output token
limits.

This implementation supports the following use cases:

1. **Truncation-Resilient Extraction**: Extract valid partial results even when
   LLM output is truncated mid-response
2. **Large-Scale Extraction**: Handle extraction of many items without risk of
   complete failure due to token limits
3. **Mixed-Type Extraction**: Support extraction of multiple entity types
   (definitions, relationships, entities, attributes) in a single prompt
4. **Streaming-Compatible Output**: Enable future streaming/incremental
   processing of extraction results

## Goals

- **Backward Compatibility**: Existing prompts using `response-type: "text"` and
  `response-type: "json"` continue to work without modification
- **Truncation Resilience**: Partial LLM outputs yield partial valid results
  rather than complete failure
- **Schema Validation**: Support JSON Schema validation for individual objects
- **Discriminated Unions**: Support mixed-type outputs using a `type` field
  discriminator
- **Minimal API Changes**: Extend existing prompt configuration with new
  response type and schema key

## Background

### Current Architecture

The prompt service supports two response types:

1. `response-type: "text"` - Raw text response returned as-is
2. `response-type: "json"` - JSON parsed from response, validated against
   optional `schema`

Current implementation in `trustgraph-flow/trustgraph/template/prompt_manager.py`:

```python
class Prompt:
    def __init__(self, template, response_type = "text", terms=None, schema=None):
        self.template = template
        self.response_type = response_type
        self.terms = terms
        self.schema = schema
```

### Current Limitations

When extraction prompts request output as JSON arrays (`[{...}, {...}, ...]`):

- **Truncation corruption**: If the LLM hits output token limits mid-array, the
  entire response becomes invalid JSON and cannot be parsed
- **All-or-nothing parsing**: Must receive complete output before parsing
- **No partial results**: A truncated response yields zero usable data
- **Unreliable for large extractions**: More extracted items = higher failure risk

This specification addresses these limitations by introducing JSONL format for
extraction prompts, where each extracted item is a complete JSON object on its
own line.

## Technical Design

### Response Type Extension

Add a new response type `"jsonl"` alongside existing `"text"` and `"json"` types.

#### Configuration Changes

**New response type value:**

```
"response-type": "jsonl"
```

**Schema interpretation:**

The existing `"schema"` key is used for both `"json"` and `"jsonl"` response
types. The interpretation depends on the response type:

- `"json"`: Schema describes the entire response (typically an array or object)
- `"jsonl"`: Schema describes each individual line/object

```json
{
  "response-type": "jsonl",
  "schema": {
    "type": "object",
    "properties": {
      "entity": { "type": "string" },
      "definition": { "type": "string" }
    },
    "required": ["entity", "definition"]
  }
}
```

This avoids changes to prompt configuration tooling and editors.

### JSONL Format Specification

#### Simple Extraction

For prompts extracting a single type of object (definitions, relationships,
topics, rows), the output is one JSON object per line with no wrapper:

**Prompt output format:**
```
{"entity": "photosynthesis", "definition": "Process by which plants convert sunlight"}
{"entity": "chlorophyll", "definition": "Green pigment in plants"}
{"entity": "mitochondria", "definition": "Powerhouse of the cell"}
```

**Contrast with previous JSON array format:**
```json
[
  {"entity": "photosynthesis", "definition": "Process by which plants convert sunlight"},
  {"entity": "chlorophyll", "definition": "Green pigment in plants"},
  {"entity": "mitochondria", "definition": "Powerhouse of the cell"}
]
```

If the LLM truncates after line 2, the JSON array format yields invalid JSON,
while JSONL yields two valid objects.

#### Mixed-Type Extraction (Discriminated Unions)

For prompts extracting multiple types of objects (e.g., both definitions and
relationships, or entities, relationships, and attributes), use a `"type"`
field as discriminator:

**Prompt output format:**
```
{"type": "definition", "entity": "DNA", "definition": "Molecule carrying genetic instructions"}
{"type": "relationship", "subject": "DNA", "predicate": "located_in", "object": "cell nucleus", "object-entity": true}
{"type": "definition", "entity": "RNA", "definition": "Molecule that carries genetic information"}
{"type": "relationship", "subject": "RNA", "predicate": "transcribed_from", "object": "DNA", "object-entity": true}
```

**Schema for discriminated unions uses `oneOf`:**
```json
{
  "response-type": "jsonl",
  "schema": {
    "oneOf": [
      {
        "type": "object",
        "properties": {
          "type": { "const": "definition" },
          "entity": { "type": "string" },
          "definition": { "type": "string" }
        },
        "required": ["type", "entity", "definition"]
      },
      {
        "type": "object",
        "properties": {
          "type": { "const": "relationship" },
          "subject": { "type": "string" },
          "predicate": { "type": "string" },
          "object": { "type": "string" },
          "object-entity": { "type": "boolean" }
        },
        "required": ["type", "subject", "predicate", "object", "object-entity"]
      }
    ]
  }
}
```

#### Ontology Extraction

For ontology-based extraction with entities, relationships, and attributes:

**Prompt output format:**
```
{"type": "entity", "entity": "Cornish pasty", "entity_type": "fo/Recipe"}
{"type": "entity", "entity": "beef", "entity_type": "fo/Food"}
{"type": "relationship", "subject": "Cornish pasty", "subject_type": "fo/Recipe", "relation": "fo/has_ingredient", "object": "beef", "object_type": "fo/Food"}
{"type": "attribute", "entity": "Cornish pasty", "entity_type": "fo/Recipe", "attribute": "fo/serves", "value": "4 people"}
```

### Implementation Details

#### Prompt Class Changes

Extend the `Prompt` class to support the new schema key:

```python
class Prompt:
    def __init__(
        self,
        template,
        response_type="text",
        terms=None,
        schema=None,
        object_schema=None
    ):
        self.template = template
        self.response_type = response_type
        self.terms = terms
        self.schema = schema              # For "json" response type
        self.object_schema = object_schema  # For "jsonl" response type
```

#### PromptManager.load_config Changes

Update configuration loading to handle the new `object-schema` key:

```python
for k in ix:
    pc = config[f"template.{k}"]
    data = json.loads(pc)

    prompt = data.get("prompt")
    rtype = data.get("response-type", "text")
    schema = data.get("schema", None)
    object_schema = data.get("object-schema", None)

    prompts[k] = Prompt(
        template=prompt,
        response_type=rtype,
        schema=schema,
        object_schema=object_schema,
        terms={}
    )
```

#### JSONL Parsing

Add a new parsing method for JSONL responses:

```python
def parse_jsonl(self, text):
    """
    Parse JSONL response, returning list of valid objects.

    Invalid lines (malformed JSON, empty lines) are skipped with warnings.
    This provides truncation resilience - partial output yields partial results.
    """
    results = []

    for line_num, line in enumerate(text.strip().split('\n'), 1):
        line = line.strip()

        # Skip empty lines
        if not line:
            continue

        # Skip markdown code fence markers if present
        if line.startswith('```'):
            continue

        try:
            obj = json.loads(line)
            results.append(obj)
        except json.JSONDecodeError as e:
            # Log warning but continue - this provides truncation resilience
            logger.warning(f"JSONL parse error on line {line_num}: {e}")

    return results
```

#### PromptManager.invoke Changes

Extend the invoke method to handle the new response type:

```python
async def invoke(self, id, input, llm):
    logger.debug("Invoking prompt template...")

    terms = self.terms | self.prompts[id].terms | input
    resp_type = self.prompts[id].response_type

    prompt = {
        "system": self.system_template.render(terms),
        "prompt": self.render(id, input)
    }

    resp = await llm(**prompt)

    if resp_type == "text":
        return resp

    if resp_type == "json":
        try:
            obj = self.parse_json(resp)
        except:
            logger.error(f"JSON parse failed: {resp}")
            raise RuntimeError("JSON parse fail")

        if self.prompts[id].schema:
            try:
                validate(instance=obj, schema=self.prompts[id].schema)
                logger.debug("Schema validation successful")
            except Exception as e:
                raise RuntimeError(f"Schema validation fail: {e}")

        return obj

    if resp_type == "jsonl":
        objects = self.parse_jsonl(resp)

        if not objects:
            logger.warning("JSONL parse returned no valid objects")
            return []

        # Validate each object against object-schema if provided
        if self.prompts[id].object_schema:
            validated = []
            for i, obj in enumerate(objects):
                try:
                    validate(instance=obj, schema=self.prompts[id].object_schema)
                    validated.append(obj)
                except Exception as e:
                    logger.warning(f"Object {i} failed schema validation: {e}")
            return validated

        return objects

    raise RuntimeError(f"Response type {resp_type} not known")
```

### Affected Prompts

The following prompts should be migrated to JSONL format:

| Prompt ID | Description | Type Field |
|-----------|-------------|------------|
| `extract-definitions` | Entity/definition extraction | No (single type) |
| `extract-relationships` | Relationship extraction | No (single type) |
| `extract-topics` | Topic/definition extraction | No (single type) |
| `extract-rows` | Structured row extraction | No (single type) |
| `agent-kg-extract` | Combined definition + relationship extraction | Yes: `"definition"`, `"relationship"` |
| `extract-with-ontologies` / `ontology-extract` | Ontology-based extraction | Yes: `"entity"`, `"relationship"`, `"attribute"` |

### API Changes

#### Return Value

For `response-type: "jsonl"`, the `invoke()` method returns a `list[dict]`
containing all successfully parsed and validated objects, rather than a single
object or the raw text.

Callers expecting JSON array output should require minimal changes since both
return a list.

#### Error Handling

- Empty results: Returns empty list `[]` with warning log
- Partial parse failure: Returns list of successfully parsed objects with
  warning logs for failures
- Complete parse failure: Returns empty list `[]` with warning logs

This differs from `response-type: "json"` which raises `RuntimeError` on
parse failure. The lenient behavior for JSONL is intentional to provide
truncation resilience.

### Configuration Example

Complete prompt configuration example:

```json
{
  "prompt": "Extract all entities and their definitions from the following text. Output one JSON object per line.\n\nText:\n{{text}}\n\nOutput format per line:\n{\"entity\": \"<name>\", \"definition\": \"<definition>\"}",
  "response-type": "jsonl",
  "object-schema": {
    "type": "object",
    "properties": {
      "entity": {
        "type": "string",
        "description": "The entity name"
      },
      "definition": {
        "type": "string",
        "description": "A clear definition of the entity"
      }
    },
    "required": ["entity", "definition"]
  }
}
```

## Security Considerations

- **Input Validation**: JSON parsing uses standard `json.loads()` which is safe
  against injection attacks
- **Schema Validation**: Uses `jsonschema.validate()` for schema enforcement
- **No New Attack Surface**: JSONL parsing is strictly safer than JSON array
  parsing due to line-by-line processing

## Performance Considerations

- **Memory**: Line-by-line parsing uses less peak memory than loading full JSON
  arrays
- **Latency**: Parsing performance is comparable to JSON array parsing
- **Validation**: Schema validation runs per-object, which adds overhead but
  enables partial results on validation failure

## Testing Strategy

### Unit Tests

- JSONL parsing with valid input
- JSONL parsing with empty lines
- JSONL parsing with markdown code fences
- JSONL parsing with truncated final line
- JSONL parsing with invalid JSON lines interspersed
- Schema validation with `oneOf` discriminated unions
- Backward compatibility: existing `"text"` and `"json"` prompts unchanged

### Integration Tests

- End-to-end extraction with JSONL prompts
- Extraction with simulated truncation (artificially limited response)
- Mixed-type extraction with type discriminator
- Ontology extraction with all three types

### Extraction Quality Tests

- Compare extraction results: JSONL vs JSON array format
- Verify truncation resilience: JSONL yields partial results where JSON fails

## Migration Plan

### Phase 1: Implementation

1. Extend `Prompt` class with `object_schema` field
2. Update `PromptManager.load_config()` to parse `object-schema`
3. Implement `parse_jsonl()` method
4. Extend `invoke()` to handle `response-type: "jsonl"`
5. Add unit tests

### Phase 2: Prompt Migration

1. Update `extract-definitions` prompt and configuration
2. Update `extract-relationships` prompt and configuration
3. Update `extract-topics` prompt and configuration
4. Update `extract-rows` prompt and configuration
5. Update `agent-kg-extract` prompt and configuration
6. Update `extract-with-ontologies` prompt and configuration

### Phase 3: Downstream Updates

1. Update any code consuming extraction results to handle list return type
2. Update code that categorizes mixed-type extractions by `type` field
3. Update tests that assert on extraction output format

## Open Questions

None at this time.

## References

- Current implementation: `trustgraph-flow/trustgraph/template/prompt_manager.py`
- JSON Lines specification: https://jsonlines.org/
- JSON Schema `oneOf`: https://json-schema.org/understanding-json-schema/reference/combining.html#oneof
- Related specification: Streaming LLM Responses (`docs/tech-specs/streaming-llm-responses.md`)
