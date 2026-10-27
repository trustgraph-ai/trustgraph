---
layout: default
title: "Field Extraction Service Technical Specification"
parent: "Tech Specs"
---

# Field Extraction Service Technical Specification

## Problem

TrustGraph currently relies on LLM text-completion services for
extracting structured fields from unstructured text. Tasks like
pulling an invoice number, a date, or a company name from a document
are framed as generative prompts — the LLM reads the text, follows an
instruction, and produces the extracted value as free-form output.

Using an LLM for extraction has three costs:

1. **Latency**. A full text-completion round-trip for each extraction,
   even when the answer is a substring of the input that requires no
   generation.

2. **Token cost**. Input and output tokens are consumed for every field
   extracted. Multi-field extraction multiplies this — each field
   typically requires its own prompt turn or a complex multi-extraction
   prompt with parsing overhead.

3. **Brittleness**. The LLM may paraphrase, reformat, or hallucinate
   values that don't appear in the source text. Extracting
   "3 March 2025" might return "March 3rd, 2025" or "2025-03-03" —
   correct in meaning but not a faithful span extraction. Worse, the
   LLM can fabricate values that appear nowhere in the input.

A different class of model targets this gap. Span-extraction models
use BIO (Begin/Inside/Outside) tagging to identify exact text spans
that match a given instruction. The model doesn't generate — it points
at substrings of the input. This guarantees that extracted values are
verbatim from the source text, eliminates hallucination of non-existent
content, and runs in milliseconds on CPU via ONNX Runtime.

A single forward pass can extract multiple fields in parallel: each
field has its own instruction, and the model processes all
(instruction, text) pairs as a batch. The output is a map of field
names to lists of extracted spans — multiple spans per field when the
text contains several matches (e.g. multiple company names).

## Solution

A new TrustGraph service — `field-extraction-span` — that wraps an
ONNX span-extraction model behind the standard request/response
pattern. The service name follows the existing convention:
`field-extraction` is the abstract service kind, `-span` identifies
the backend technique.

The service loads an ONNX model and tokenizer from a HuggingFace
repository at startup. The repository ID is a flow parameter,
defaulting to `tasksource/UltraBERT-150M-clairic-extraction`. This
allows operators to swap in alternative span-extraction models without
code changes.

The field extraction service does not replace existing LLM-based
extraction. It is another tool in the armoury — a lightweight, fast
option for cases where faithful span extraction is sufficient. When
extraction requires inference, paraphrasing, or synthesis beyond what
appears in the source text, an LLM remains the right choice. The
choice of which to use for a given task is a design decision, not a
migration.

## Technical Design

### Model Loading

The service downloads and caches the ONNX model and tokenizer from
HuggingFace Hub at startup:

```python
from huggingface_hub import hf_hub_download
from tokenizers import Tokenizer
import onnxruntime as ort

model_path = hf_hub_download(
    repo_id=model_repo, filename="onnx/model_quantized.onnx",
)
tokenizer_path = hf_hub_download(
    repo_id=model_repo, filename="tokenizer.json",
)

session = ort.InferenceSession(
    model_path, providers=["CPUExecutionProvider"],
)
tokenizer = Tokenizer.from_file(tokenizer_path)
tokenizer.no_padding()
```

The `model_repo` value comes from the `model` flow parameter.

### Flow Parameters

- **model** — HuggingFace repository ID for the ONNX model. Default:
  `tasksource/UltraBERT-150M-clairic-extraction`.
- **max-length** — Maximum token sequence length per (instruction, text)
  pair. Inputs exceeding this are truncated (text portion only —
  instruction tokens and special tokens are preserved). Default: `512`.

### Inference

Each request contains text and a set of field specifications. The
service encodes each (instruction, text) pair using the tokenizer's
pair encoding:

```
[CLS] instruction [SEP] text [EOS] [PAD...]
```

All pairs are batched into a single ONNX forward pass. The model
produces BIO logits for each token position; argmax yields tag
sequences. Spans tagged as B (begin) followed by I (inside) tokens
are decoded back to character offsets in the original text.

The text portion is truncated to fit within `max-length` tokens
(accounting for instruction tokens and special tokens). Truncation is
silent — the caller is responsible for chunking long documents.

### Span Decoding

BIO tags use three values: O (outside, 0), B (begin, 1), I (inside, 2).
Only tokens in the text sequence (not the instruction) are considered
for span extraction. A span starts at a B tag and continues through
consecutive I tags. The character offsets from the tokenizer map tags
back to substrings of the original text.

When a field matches multiple disjoint spans in the text, all are
returned. For example, extracting "companies" from a text mentioning
both "Acme Corp" and "Globex" returns both as separate spans.

### Request/Response Data Shapes

#### Request

```python
@dataclass
class FieldExtractionRequest:
    state: dict = field(default_factory=dict)
    fields: dict = field(default_factory=dict)
```

- **state** — freeform input data, matching the decision-scoring
  convention. Can be any structure: a simple string, a dict with
  fields like `title`, `body`, or any application-specific shape.
  This is the text the model extracts from.
- **fields** — a map of field names to instruction strings. Each
  instruction tells the model what to extract.

```json
{
    "state": "Invoice INV-2291 from Acme Corp to Globex, issued 3 March 2025. Total due: $1,240.50.",
    "fields": {
        "invoice_number": "The invoice number.",
        "companies": "Every company mentioned in the text, as written.",
        "total": "The total amount due.",
        "date": "The date the invoice was issued."
    }
}
```

#### Response

```python
@dataclass
class FieldExtractionResponse:
    error: Error | None = None
    answers: dict = field(default_factory=dict)
    model: str = ""
```

- **answers** — a map keyed by the same field names as the request.
  Each entry is a list of extracted spans (strings). Multiple spans
  per field when the text contains several matches.

  ```json
  {
      "answers": {
          "invoice_number": ["INV-2291"],
          "companies": ["Acme Corp", "Globex"],
          "total": ["$1,240.50"],
          "date": ["3 March 2025"]
      }
  }
  ```

  Spans are verbatim substrings of the input text — the model does
  not generate or paraphrase.

- **model** — the HuggingFace repository ID of the model that handled
  the request.

#### Queues

```python
field_extraction_request_queue = queue('field-extraction', cls='request')
field_extraction_response_queue = queue('field-extraction', cls='response')
```

#### Gateway Integration

A `FieldExtractionRequestor` is added to the gateway's dispatcher
mapping:

```python
request_response_dispatchers = {
    ...
    "field-extraction": FieldExtractionRequestor,
}
```

Translators are registered in the translator registry:

```python
TranslatorRegistry.register_service(
    "field-extraction",
    FieldExtractionRequestTranslator(),
    FieldExtractionResponseTranslator(),
)
```

### Service Shape

The service extends `FlowProcessor`. Like the decision-scoring
service, it loads pre-trained model weights at startup and is stateless
beyond those weights — no training, no config-driven model lifecycle.

```python
class FieldExtractionService(FlowProcessor):
    def __init__(self, **params):
        super().__init__(**params)

        self.register_specification(
            ParameterSpec(name="model")
        )

        self.register_specification(
            ParameterSpec(name="max-length")
        )

        self.register_specification(
            ConsumerSpec(
                name="request",
                schema=FieldExtractionRequest,
                handler=self.on_request,
            )
        )

        self.register_specification(
            ProducerSpec(
                name="response",
                schema=FieldExtractionResponse,
            )
        )
```

### Concurrency

ONNX Runtime supports concurrent inference sessions. The service
should configure `ConsumerSpec` concurrency to allow multiple requests
to be processed in parallel.

### CLI Tooling

A command-line tool (`tg-invoke-field-extract`) for interactive
testing of the field extraction service. Takes text and a fields
specification, submits to the service, and prints the extracted spans.
Useful for validating field instructions and debugging extraction
behaviour during development.
