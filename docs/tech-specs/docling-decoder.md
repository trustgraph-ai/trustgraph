---
layout: default
title: "Docling Document Decoder"
parent: "Tech Specs"
---

# Docling Document Decoder

## Problem Statement

The current universal document decoder is built on the `unstructured`
library.  While functional, it has significant operational problems:

- **Heavyweight.**  `unstructured` pulls in PyTorch and a large
  dependency tree.  Container images are bloated (~2 GB+) and slow
  to build.

- **Fragile processing strategies.**  `unstructured`'s internal
  strategies (e.g. `is_pdf_too_complex`) change between releases in
  ways that alter output for the same input document.  This makes
  decoder behaviour unpredictable across upgrades.

- **Flat element model.**  `unstructured` returns a flat list of
  elements with no structural hierarchy.  The decoder must manually
  reconstruct page/section boundaries using custom grouping
  strategies (`strategies.py`), which is brittle and loses the
  document's semantic structure.

- **Temp file dance.**  `unstructured` requires files on disk,
  forcing the decoder to write blobs to temp files, parse, then
  clean up.

- **Table reconstruction.**  Table extraction relies on a hidden
  `text_as_html` metadata attribute that is inconsistently
  populated, requiring fallback logic.

## Approach

Replace `unstructured` with [Docling](https://github.com/DS4SD/docling),
a document conversion library from IBM Research that provides:

- A unified `DoclingDocument` schema across all input formats
- Preserved semantic hierarchy (headings, sections, lists, tables)
- Native table reconstruction to Markdown or structured output
- In-memory stream processing (no temp files)
- Built-in `HybridChunker` for semantic chunking
- Lighter dependency footprint

## Requirements

The decoder is a critical part of the provenance chain.  Every
piece of text that enters the knowledge graph must be traceable
back to its source document, and the decoder is where that chain
begins.  Docling must support the following:

### Source provenance

Each output (page, section, or chunk) must carry enough metadata
to trace it back to the source document:

- **Parent document ID.**  Every emitted page/section/chunk links
  to its source document via `prov:wasDerivedFrom`.  The
  explainability UI walks this chain to show users exactly which
  document produced a given piece of knowledge.

- **Page numbers.**  For page-based formats (PDF, PPTX), each
  output must record which page it came from.  Docling must
  expose page numbers in its document model so the decoder can
  propagate them into provenance triples.

- **Character offsets and lengths.**  The downstream chunker
  records character offset and length for each chunk relative
  to its parent section/page.  In hybrid mode, the decoder
  must provide equivalent positional metadata so chunks can be
  mapped back to their location within the source text.

- **Structural context.**  Docling's hierarchical model
  (heading path, section nesting) should be preserved where
  possible.  This supports future explainability features
  that show users not just which page, but which section of
  the document a fact came from.

### Content fidelity

- **Tables as markup.**  Tables must be preserved as structured
  content (HTML or Markdown), not flattened to plain text.
  Downstream extractors rely on table structure to correctly
  identify relationships between cells.

- **Image separation.**  Images must be extractable and stored
  separately in the librarian with their own provenance, but
  must not be injected into the text pipeline.  The provenance
  chain links each image to its source page/document.

- **Text ordering.**  Elements must be emitted in reading order.
  Docling's layout analysis handles multi-column and complex
  layouts — the decoder must preserve that ordering.

### Operational

- **Format coverage.**  Must handle at minimum: PDF, DOCX, XLSX,
  PPTX, HTML, Markdown, plain text.  These cover the majority
  of enterprise document ingestion.

- **In-memory processing.**  No temp files.  The decoder runs in
  a container processing documents from Pulsar — temp file
  management adds failure modes and cleanup complexity.

- **Deterministic output.**  The same document must produce the
  same output across library upgrades.  This is a key
  motivation for moving away from unstructured, whose
  processing strategies change between releases.

## Architecture

### Separate package

The Docling decoder ships as `trustgraph-docling`, a new package
alongside the existing `trustgraph-unstructured`.  Users choose
which decoder to deploy — both produce the same downstream
interface (`TextDocument` or `Chunk` messages over Pulsar).

Package structure mirrors `trustgraph-unstructured`:

```
trustgraph-docling/
  pyproject.toml
  trustgraph/
    docling_version.py
    decoding/
      docling/
        __init__.py
        __main__.py
        processor.py
```

### Two chunking modes

The decoder supports two modes via `--chunking-mode`:

**`page` (default)** — drop-in replacement for the unstructured
decoder.  Docling converts the document, the decoder groups
output by page (for page-based formats) or emits as a single
section (for non-page formats).  Emits `TextDocument` messages
for the existing downstream chunker to split further.

**`hybrid`** — Docling's `HybridChunker` performs semantic
chunking natively, respecting document hierarchy (headings,
tables, lists).  Emits `Chunk` messages directly, bypassing
the downstream chunker.  This mode produces higher-quality
chunks because the chunker understands document structure
rather than splitting on character count.

### Pipeline interface

Both modes use the same `FlowProcessor` base class and the same
input schema (`Document`).  The output schema depends on mode:

- `page` mode: `TextDocument` (same as unstructured decoder)
- `hybrid` mode: `Chunk` (same as downstream chunker output)

Provenance and librarian integration work identically to the
unstructured decoder — each page/section/chunk gets a URI,
provenance triples linking it to the source document, and
content saved to the librarian.

### Image handling

Same as the unstructured decoder: images are stored in the
librarian with provenance but are not sent to the text pipeline.

### Document conversion

Docling's `DocumentConverter` handles format detection and
conversion.  The decoder accepts the document as bytes plus an
optional mime type hint, wraps it in a `DocumentStream`, and
calls `converter.convert()`.  No temp files.

### What we don't need

- `strategies.py` — Docling's hierarchical document model and
  `HybridChunker` replace all five custom grouping strategies.
- Mime-to-extension mapping — Docling uses `InputFormat` enums,
  not file extensions.
- Manual page grouping logic — Docling tracks page numbers
  natively in its document model.

## Configuration

| Flag | Default | Description |
|---|---|---|
| `--chunking-mode` | `page` | `page` or `hybrid` |
| `--languages` | `eng` | OCR language codes (comma-separated) |
| `--chunk-max-tokens` | `512` | Max tokens per chunk (hybrid mode) |

## Open Questions

- **OCR configuration.**  Docling has its own OCR pipeline
  (EasyOCR, Tesseract).  Need to verify language configuration
  maps cleanly.
- **Format coverage.**  Verify Docling handles all formats
  currently supported by the unstructured decoder (CSV, TSV,
  RST, RTF, ODT).  Some niche formats may need fallback.
- **Performance.**  Docling uses AI models for layout analysis.
  Need to benchmark against unstructured on representative
  documents to confirm comparable or better throughput.
