# Universal Document Decoder

## Headline

Universal document decoder powered by `unstructured` — ingest any common
document format through a single service with full provenance and librarian
integration, recording source positions as knowledge graph metadata for
end-to-end traceability.

## Problem

TrustGraph currently has a PDF-specific decoder. Supporting additional
formats (DOCX, XLSX, HTML, Markdown, plain text, PPTX, etc.) requires
either writing a new decoder per format or adopting a universal extraction
library. Each format has different structure — some are page-based, some
aren't — and the provenance chain must record where in the original
document each piece of extracted text originated.

## Approach

### Library: `unstructured`

Use `unstructured.partition.auto.partition()` which auto-detects format
from mime type or file extension and extracts structured elements
(Title, NarrativeText, Table, ListItem, etc.). Each element carries
metadata including:

- `page_number` (for page-based formats like PDF, PPTX)
- `element_id` (unique per element)
- `coordinates` (bounding box for PDFs)
- `text` (the extracted text content)
- `category` (element type: Title, NarrativeText, Table, etc.)

### Element Types

`unstructured` extracts typed elements from documents. Each element has
a category and associated metadata:

**Text elements:**
- `Title` — section headings
- `NarrativeText` — body paragraphs
- `ListItem` — bullet/numbered list items
- `Header`, `Footer` — page headers/footers
- `FigureCaption` — captions for figures/images
- `Formula` — mathematical expressions
- `Address`, `EmailAddress` — contact information
- `CodeSnippet` — code blocks (from markdown)

**Tables:**
- `Table` — structured tabular data. `unstructured` provides both
  `element.text` (plain text) and `element.metadata.text_as_html`
  (full HTML `<table>` with rows, columns, and headers preserved).
  For formats with explicit table structure (DOCX, XLSX, HTML), the
  extraction is highly reliable. For PDFs, table detection depends on
  the `hi_res` strategy with layout analysis.

**Images:**
- `Image` — embedded images detected via layout analysis (requires
  `hi_res` strategy). With `extract_image_block_to_payload=True`,
  returns the image data as base64 in `element.metadata.image_base64`.
  OCR text from the image is available in `element.text`.

### Table Handling

Tables are a first-class output. When the decoder encounters a `Table`
element, it preserves the HTML structure rather than flattening to
plain text. This gives the downstream LLM extractor much better input
for pulling structured knowledge out of tabular data.

The page/section text is assembled as follows:
- Text elements: plain text, joined with newlines
- Table elements: HTML table markup from `text_as_html`, wrapped in a
  `<table>` marker so the LLM can distinguish tables from narrative

For example, a page with a heading, paragraph, and table produces:

```
Financial Overview

Revenue grew 15% year-over-year driven by enterprise adoption.

<table>
<tr><th>Quarter</th><th>Revenue</th><th>Growth</th></tr>
<tr><td>Q1</td><td>$12M</td><td>12%</td></tr>
<tr><td>Q2</td><td>$14M</td><td>17%</td></tr>
</table>
```

This preserves table structure through chunking and into the extraction
pipeline, where the LLM can extract relationships directly from
structured cells rather than guessing at column alignment from
whitespace.

### Image Handling

Images are extracted and stored in the librarian as child documents
with `document_type="image"` and a `urn:image:{uuid}` ID. They get
provenance triples with type `tg:Image`, linked to their parent
page/section via `prov:wasDerivedFrom`. Image metadata (coordinates,
dimensions, element_id) is recorded in provenance.

**Crucially, images are NOT emitted as TextDocument outputs.** They are
stored only — not sent downstream to the chunker or any text processing
pipeline. This is intentional:

1. There is no image processing pipeline yet (vision model integration
   is future work)
2. Feeding base64 image data or OCR fragments into the text extraction
   pipeline would produce garbage KG triples

Images are also excluded from the assembled page text — any `Image`
elements are silently skipped when concatenating element texts for a
page/section. The provenance chain records that images exist and where
they appeared in the document, so they can be picked up by a future
image processing pipeline without re-ingesting the document.

#### Future work

- Route `tg:Image` entities to a vision model for description,
  diagram interpretation, or chart data extraction
- Store image descriptions as text child documents that feed into
  the standard chunking/extraction pipeline
- Link extracted knowledge back to source images via provenance

### Section Strategies

For page-based formats (PDF, PPTX, XLSX), elements are always grouped
by page/slide/sheet first. For non-page formats (DOCX, HTML, Markdown,
etc.), the decoder needs a strategy for splitting the document into
sections. This is runtime-configurable via `--section-strategy`.

Each strategy is a grouping function over the list of `unstructured`
elements. The output is a list of element groups; the rest of the
pipeline (text assembly, librarian storage, provenance, TextDocument
emission) is identical regardless of strategy.

#### `whole-document` (default)

Emit the entire document as a single section. Let the downstream
chunker handle all splitting.

- Simplest approach, good baseline
- May produce very large TextDocument for big files, but the chunker
  handles that
- Best when you want maximum context per section

#### `heading`

Split at heading elements (`Title`). Each section is a heading plus
all content until the next heading of equal or higher level. Nested
headings create nested sections.

- Produces topically coherent units
- Works well for structured documents (reports, manuals, specs)
- Gives the extraction LLM heading context alongside content
- Falls back to `whole-document` if no headings are found

#### `element-type`

Split when the element type changes significantly — specifically,
start a new section at transitions between narrative text and tables.
Consecutive elements of the same broad category (text, text, text or
table, table) stay grouped.

- Keeps tables as standalone sections
- Good for documents with mixed content (reports with data tables)
- Tables get dedicated extraction attention

#### `count`

Group a fixed number of elements per section. Configurable via
`--section-element-count` (default: 20).

- Simple and predictable
- Doesn't respect document structure
- Useful as a fallback or for experimentation

#### `size`

Accumulate elements until a character limit is reached, then start a
new section. Respects element boundaries — never splits mid-element.
Configurable via `--section-max-size` (default: 4000 characters).

- Produces roughly uniform section sizes
- Respects element boundaries (unlike the downstream chunker)
- Good compromise between structure and size control
- If a single element exceeds the limit, it becomes its own section

#### Page-based format interaction

For page-based formats, the page grouping always takes priority.
Section strategies can optionally apply *within* a page if it's very
large (e.g. a PDF page with an enormous table), controlled by
`--section-within-pages` (default: false). When false, each page is
always one section regardless of size.

### Format Detection

The decoder needs to know the document's mime type to pass to
`unstructured`'s `partition()`. Two paths:

- **Librarian path** (`document_id` set): fetch document metadata
  from the librarian first — this gives us the `kind` (mime type)
  that was recorded at upload time. Then fetch document content.
  Two librarian calls, but the metadata fetch is lightweight.
- **Inline path** (backward compat, `data` set): no metadata
  available on the message. Use `python-magic` to detect format
  from content bytes as a fallback.

No changes to the `Document` schema are needed — the librarian
already stores the mime type.

### Architecture

A single `universal-decoder` service that:

1. Receives a `Document` message (inline or via librarian reference)
2. If librarian path: fetch document metadata (get mime type), then
   fetch content. If inline path: detect format from content bytes.
3. Calls `partition()` to extract elements
4. Groups elements: by page for page-based formats, by configured
   section strategy for non-page formats
5. For each page/section:
   - Generates a `urn:page:{uuid}` or `urn:section:{uuid}` ID
   - Assembles page text: narrative as plain text, tables as HTML,
     images skipped
   - Computes character offsets for each element within the page text
   - Saves to librarian as child document
   - Emits provenance triples with positional metadata
   - Sends `TextDocument` downstream for chunking
6. For each image element:
   - Generates a `urn:image:{uuid}` ID
   - Saves image data to librarian as child document
   - Emits provenance triples (stored only, not sent downstream)

### Format Handling

| Format   | Mime Type                          | Page-based | Notes                          |
|----------|------------------------------------|------------|--------------------------------|
| PDF      | application/pdf                    | Yes        | Per-page grouping              |
| DOCX     | application/vnd.openxmlformats...  | No         | Uses section strategy          |
| PPTX     | application/vnd.openxmlformats...  | Yes        | Per-slide grouping             |
| XLSX/XLS | application/vnd.openxmlformats...  | Yes        | Per-sheet grouping             |
| HTML     | text/html                          | No         | Uses section strategy          |
| Markdown | text/markdown                      | No         | Uses section strategy          |
| Plain    | text/plain                         | No         | Uses section strategy          |
| CSV      | text/csv                           | No         | Uses section strategy          |
| RST      | text/x-rst                         | No         | Uses section strategy          |
| RTF      | application/rtf                    | No         | Uses section strategy          |
| ODT      | application/vnd.oasis...           | No         | Uses section strategy          |
| TSV      | text/tab-separated-values          | No         | Uses section strategy          |

### Provenance Metadata

Each page/section entity records positional metadata as provenance
triples in `GRAPH_SOURCE`, enabling full traceability from KG triples
back to source document positions.

#### Existing fields (already in `derived_entity_triples`)

- `page_number` — page/sheet/slide number (1-indexed, page-based only)
- `char_offset` — character offset of this page/section within the
  full document text
- `char_length` — character length of this page/section's text

#### New fields (extend `derived_entity_triples`)

- `mime_type` — original document format (e.g. `application/pdf`)
- `element_types` — comma-separated list of `unstructured` element
  categories found in this page/section (e.g. "Title,NarrativeText,Table")
- `table_count` — number of tables in this page/section
- `image_count` — number of images in this page/section

These require new TG namespace predicates:

```
TG_SECTION_TYPE  = "https://trustgraph.ai/ns/Section"
TG_IMAGE_TYPE    = "https://trustgraph.ai/ns/Image"
TG_ELEMENT_TYPES = "https://trustgraph.ai/ns/elementTypes"
TG_TABLE_COUNT   = "https://trustgraph.ai/ns/tableCount"
TG_IMAGE_COUNT   = "https://trustgraph.ai/ns/imageCount"
```

Image URN scheme: `urn:image:{uuid}`

(`TG_MIME_TYPE` already exists.)

#### New entity type

For non-page formats (DOCX, HTML, Markdown, etc.) where the decoder
emits the whole document as a single unit rather than splitting by
page, the entity gets a new type:

```
TG_SECTION_TYPE = "https://trustgraph.ai/ns/Section"
```

This distinguishes sections from pages when querying provenance:

| Entity   | Type                        | When used                              |
|----------|-----------------------------|----------------------------------------|
| Document | `tg:Document`               | Original uploaded file                 |
| Page     | `tg:Page`                   | Page-based formats (PDF, PPTX, XLSX)   |
| Section  | `tg:Section`                | Non-page formats (DOCX, HTML, MD, etc) |
| Image    | `tg:Image`                  | Embedded images (stored, not processed)|
| Chunk    | `tg:Chunk`                  | Output of chunker                      |
| Subgraph | `tg:Subgraph`              | KG extraction output                   |

The type is set by the decoder based on whether it's grouping by page
or emitting a whole-document section. `derived_entity_triples` gains
an optional `section` boolean parameter — when true, the entity is
typed as `tg:Section` instead of `tg:Page`.

#### Full provenance chain

```
KG triple
  → subgraph (extraction provenance)
    → chunk (char_offset, char_length within page)
      → page/section (page_number, char_offset, char_length within doc, mime_type, element_types)
        → document (original file in librarian)
```

Every link is a set of triples in the `GRAPH_SOURCE` named graph.

### Service Configuration

Command-line arguments:

```
--strategy              Partitioning strategy: auto, hi_res, fast (default: auto)
--languages             Comma-separated OCR language codes (default: eng)
--section-strategy      Section grouping: whole-document, heading, element-type,
                        count, size (default: whole-document)
--section-element-count Elements per section for 'count' strategy (default: 20)
--section-max-size      Max chars per section for 'size' strategy (default: 4000)
--section-within-pages  Apply section strategy within pages too (default: false)
```

Plus the standard `FlowProcessor` and librarian queue arguments.

### Flow Integration

The universal decoder occupies the same position in the processing flow
as the current PDF decoder:

```
Document → [universal-decoder] → TextDocument → [chunker] → Chunk → ...
```

It registers:
- `input` consumer (Document schema)
- `output` producer (TextDocument schema)
- `triples` producer (Triples schema)
- Librarian request/response (for fetch and child document storage)

### Deployment

- New container: `trustgraph-flow-universal-decoder`
- Dependency: `unstructured[all-docs]` (includes PDF, DOCX, PPTX, etc.)
- Can run alongside or replace the existing PDF decoder depending on
  flow configuration
- The existing PDF decoder remains available for environments where
  `unstructured` dependencies are too heavy

### What Changes

| Component                    | Change                                         |
|------------------------------|-------------------------------------------------|
| `provenance/namespaces.py`   | Add `TG_SECTION_TYPE`, `TG_IMAGE_TYPE`, `TG_ELEMENT_TYPES`, `TG_TABLE_COUNT`, `TG_IMAGE_COUNT` |
| `provenance/triples.py`      | Add `mime_type`, `element_types`, `table_count`, `image_count` kwargs |
| `provenance/__init__.py`     | Export new constants                            |
| New: `decoding/universal/`   | New decoder service module                      |
| `setup.cfg` / `pyproject`    | Add `unstructured[all-docs]` dependency         |
| Docker                       | New container image                             |
| Flow definitions             | Wire universal-decoder as document input        |

### What Doesn't Change

- Chunker (receives TextDocument, works as before)
- Downstream extractors (receive Chunk, unchanged)
- Librarian (stores child documents, unchanged)
- Schema (Document, TextDocument, Chunk unchanged)
- Query-time provenance (unchanged)

## Risks

- `unstructured[all-docs]` has heavy dependencies (poppler, tesseract,
  libreoffice for some formats). Container image will be larger.
  Mitigation: offer a `[light]` variant without OCR/office deps.
- Some formats may produce poor text extraction (scanned PDFs without
  OCR, complex XLSX layouts). Mitigation: configurable `strategy`
  parameter, and the existing Mistral OCR decoder remains available
  for high-quality PDF OCR.
- `unstructured` version updates may change element metadata.
  Mitigation: pin version, test extraction quality per format.
