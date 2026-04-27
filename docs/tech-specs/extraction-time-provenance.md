---
layout: default
title: "Extraction-Time Provenance: Source Layer"
parent: "Tech Specs"
---

# Extraction-Time Provenance: Source Layer

## Overview

This document captures notes on extraction-time provenance for future specification work. Extraction-time provenance records the "source layer" - where data came from originally, how it was extracted and transformed.

This is separate from query-time provenance (see `query-time-provenance.md`) which records agent reasoning.

## Problem Statement

### Current Implementation

Provenance currently works as follows:
- Document metadata is stored as RDF triples in the knowledge graph
- A document ID ties metadata to the document, so the document appears as a node in the graph
- When edges (relationships/facts) are extracted from documents, a `subjectOf` relationship links the extracted edge back to the source document

### Problems with Current Approach

1. **Repetitive metadata loading:** Document metadata is bundled and loaded repeatedly with every batch of triples extracted from that document. This is wasteful and redundant - the same metadata travels as cargo with every extraction output.

2. **Shallow provenance:** The current `subjectOf` relationship only links facts directly to the top-level document. There is no visibility into the transformation chain - which page the fact came from, which chunk, what extraction method was used.

### Desired State

1. **Load metadata once:** Document metadata should be loaded once and attached to the top-level document node, not repeated with every triple batch.

2. **Rich provenance DAG:** Capture the full transformation chain from source document through all intermediate artifacts down to extracted facts. For example, a PDF document transformation:

   ```
   PDF file (source document with metadata)
     → Page 1 (decoded text)
       → Chunk 1
         → Extracted edge/fact (via subjectOf)
         → Extracted edge/fact
       → Chunk 2
         → Extracted edge/fact
     → Page 2
       → Chunk 3
         → ...
   ```

3. **Unified storage:** The provenance DAG is stored in the same knowledge graph as the extracted knowledge. This allows provenance to be queried the same way as knowledge - following edges back up the chain from any fact to its exact source location.

4. **Stable IDs:** Each intermediate artifact (page, chunk) has a stable ID as a node in the graph.

5. **Parent-child linking:** Derived documents are linked to their parents all the way up to the top-level source document using consistent relationship types.

6. **Precise fact attribution:** The `subjectOf` relationship on extracted edges points to the immediate parent (chunk), not the top-level document. Full provenance is recovered by traversing up the DAG.

## Use Cases

### UC1: Source Attribution in GraphRAG Responses

**Scenario:** A user runs a GraphRAG query and receives a response from the agent.

**Flow:**
1. User submits a query to the GraphRAG agent
2. Agent retrieves relevant facts from the knowledge graph to formulate a response
3. Per the query-time provenance spec, the agent reports which facts contributed to the response
4. Each fact links to its source chunk via the provenance DAG
5. Chunks link to pages, pages link to source documents

**UX Outcome:** The interface displays the LLM response alongside source attribution. The user can:
- See which facts supported the response
- Drill down from facts → chunks → pages → documents
- Peruse the original source documents to verify claims
- Understand exactly where in a document (which page, which section) a fact originated

**Value:** Users can verify AI-generated responses against primary sources, building trust and enabling fact-checking.

### UC2: Debugging Extraction Quality

A fact looks wrong. Trace back through chunk → page → document to see the original text. Was it a bad extraction, or was the source itself wrong?

### UC3: Incremental Re-extraction

Source document gets updated. Which chunks/facts were derived from it? Invalidate and regenerate just those, rather than re-processing everything.

### UC4: Data Deletion / Right to be Forgotten

A source document must be removed (GDPR, legal, etc.). Traverse the DAG to find and remove all derived facts.

### UC5: Conflict Resolution

Two facts contradict each other. Trace both back to their sources to understand why and decide which to trust (more authoritative source, more recent, etc.).

### UC6: Source Authority Weighting

Some sources are more authoritative than others. Facts can be weighted or filtered based on the authority/quality of their origin documents.

### UC7: Extraction Pipeline Comparison

Compare outputs from different extraction methods/versions. Which extractor produced better facts from the same source?

## Integration Points

### Librarian

The librarian component already provides document storage with unique document IDs. The provenance system integrates with this existing infrastructure.

#### Existing Capabilities (already implemented)

**Parent-Child Document Linking:**
- `parent_id` field in `DocumentMetadata` - links child to parent document
- `document_type` field - values: `"source"` (original) or `"extracted"` (derived)
- `add-child-document` API - creates child document with automatic `document_type = "extracted"`
- `list-children` API - retrieves all children of a parent document
- Cascade deletion - removing a parent automatically deletes all child documents

**Document Identification:**
- Document IDs are client-specified (not auto-generated)
- Documents keyed by composite `(user, document_id)` in Cassandra
- Object IDs (UUIDs) generated internally for blob storage

**Metadata Support:**
- `metadata: list[Triple]` field - RDF triples for structured metadata
- `title`, `comments`, `tags` - basic document metadata
- `time` - timestamp, `kind` - MIME type

**Storage Architecture:**
- Metadata stored in Cassandra (`librarian` keyspace, `document` table)
- Content stored in MinIO/S3 blob storage (`library` bucket)
- Smart content delivery: documents < 2MB embedded, larger documents streamed

#### Key Files

- `trustgraph-flow/trustgraph/librarian/librarian.py` - Core librarian operations
- `trustgraph-flow/trustgraph/librarian/service.py` - Service processor, document loading
- `trustgraph-flow/trustgraph/tables/library.py` - Cassandra table store
- `trustgraph-base/trustgraph/schema/services/library.py` - Schema definitions

#### Gaps to Address

The librarian has the building blocks but currently:
1. Parent-child linking is one level deep - no multi-level DAG traversal helpers
2. No standard relationship type vocabulary (e.g., `derivedFrom`, `extractedFrom`)
3. Provenance metadata (extraction method, confidence, chunk position) not standardized
4. No query API to traverse the full provenance chain from a fact back to source

## End-to-End Flow Design

Each processor in the pipeline follows a consistent pattern:
- Receive document ID from upstream
- Fetch content from librarian
- Produce child artifacts
- For each child: save to librarian, emit edge to graph, forward ID downstream

### Processing Flows

There are two flows depending on document type:

#### PDF Document Flow

```
┌─────────────────────────────────────────────────────────────────────────┐
│ Librarian (initiate processing)                                         │
│   1. Emit root document metadata to knowledge graph (once)              │
│   2. Send root document ID to PDF extractor                             │
└─────────────────────────────────────────────────────────────────────────┘
                                    │
                                    ▼
┌─────────────────────────────────────────────────────────────────────────┐
│ PDF Extractor (per page)                                                │
│   1. Fetch PDF content from librarian using document ID                 │
│   2. Extract pages as text                                              │
│   3. For each page:                                                     │
│      a. Save page as child document in librarian (parent = root doc)   │
│      b. Emit parent-child edge to knowledge graph                       │
│      c. Send page document ID to chunker                                │
└─────────────────────────────────────────────────────────────────────────┘
                                    │
                                    ▼
┌─────────────────────────────────────────────────────────────────────────┐
│ Chunker (per chunk)                                                     │
│   1. Fetch page content from librarian using document ID                │
│   2. Split text into chunks                                             │
│   3. For each chunk:                                                    │
│      a. Save chunk as child document in librarian (parent = page)      │
│      b. Emit parent-child edge to knowledge graph                       │
│      c. Send chunk document ID + chunk content to next processor        │
└─────────────────────────────────────────────────────────────────────────┘
                                    │
                                    ▼
          ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─
          Post-chunker optimization: messages carry both
          chunk ID (for provenance) and content (to avoid
          librarian round-trip). Chunks are small (2-4KB).
          ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─
                                    │
                                    ▼
┌─────────────────────────────────────────────────────────────────────────┐
│ Knowledge Extractor (per chunk)                                         │
│   1. Receive chunk ID + content directly (no librarian fetch needed)   │
│   2. Extract facts/triples and embeddings from chunk content            │
│   3. For each triple:                                                   │
│      a. Emit triple to knowledge graph                                  │
│      b. Emit reified edge linking triple → chunk ID (edge pointing     │
│         to edge - first use of reification support)                     │
│   4. For each embedding:                                                │
│      a. Emit embedding with its entity ID                               │
│      b. Link entity ID → chunk ID in knowledge graph                   │
└─────────────────────────────────────────────────────────────────────────┘
```

#### Text Document Flow

Text documents skip the PDF extractor and go directly to the chunker:

```
┌─────────────────────────────────────────────────────────────────────────┐
│ Librarian (initiate processing)                                         │
│   1. Emit root document metadata to knowledge graph (once)              │
│   2. Send root document ID directly to chunker (skip PDF extractor)    │
└─────────────────────────────────────────────────────────────────────────┘
                                    │
                                    ▼
┌─────────────────────────────────────────────────────────────────────────┐
│ Chunker (per chunk)                                                     │
│   1. Fetch text content from librarian using document ID                │
│   2. Split text into chunks                                             │
│   3. For each chunk:                                                    │
│      a. Save chunk as child document in librarian (parent = root doc) │
│      b. Emit parent-child edge to knowledge graph                       │
│      c. Send chunk document ID + chunk content to next processor        │
└─────────────────────────────────────────────────────────────────────────┘
                                    │
                                    ▼
┌─────────────────────────────────────────────────────────────────────────┐
│ Knowledge Extractor                                                     │
│   (same as PDF flow)                                                    │
└─────────────────────────────────────────────────────────────────────────┘
```

The resulting DAG is one level shorter:

```
PDF:  Document → Pages → Chunks → Triples/Embeddings
Text: Document → Chunks → Triples/Embeddings
```

The design accommodates both because the chunker treats its input generically - it uses whatever document ID it receives as the parent, regardless of whether that's a source document or a page.

### Metadata Schema (PROV-O)

Provenance metadata uses the W3C PROV-O ontology. This provides a standard vocabulary and enables future signing/authentication of extraction outputs.

#### PROV-O Core Concepts

| PROV-O Type | TrustGraph Usage |
|-------------|------------------|
| `prov:Entity` | Document, Page, Chunk, Triple, Embedding |
| `prov:Activity` | Instances of extraction operations |
| `prov:Agent` | TG components (PDF extractor, chunker, etc.) with versions |

#### PROV-O Relationships

| Predicate | Meaning | Example |
|-----------|---------|---------|
| `prov:wasDerivedFrom` | Entity derived from another entity | Page wasDerivedFrom Document |
| `prov:wasGeneratedBy` | Entity generated by an activity | Page wasGeneratedBy PDFExtractionActivity |
| `prov:used` | Activity used an entity as input | PDFExtractionActivity used Document |
| `prov:wasAssociatedWith` | Activity performed by an agent | PDFExtractionActivity wasAssociatedWith tg:PDFExtractor |

#### Metadata at Each Level

**Source Document (emitted by Librarian):**
```
doc:123 a prov:Entity .
doc:123 dc:title "Research Paper" .
doc:123 dc:source <https://example.com/paper.pdf> .
doc:123 dc:date "2024-01-15" .
doc:123 dc:creator "Author Name" .
doc:123 tg:pageCount 42 .
doc:123 tg:mimeType "application/pdf" .
```

**Page (emitted by PDF Extractor):**
```
page:123-1 a prov:Entity .
page:123-1 prov:wasDerivedFrom doc:123 .
page:123-1 prov:wasGeneratedBy activity:pdf-extract-456 .
page:123-1 tg:pageNumber 1 .

activity:pdf-extract-456 a prov:Activity .
activity:pdf-extract-456 prov:used doc:123 .
activity:pdf-extract-456 prov:wasAssociatedWith tg:PDFExtractor .
activity:pdf-extract-456 tg:componentVersion "1.2.3" .
activity:pdf-extract-456 prov:startedAtTime "2024-01-15T10:30:00Z" .
```

**Chunk (emitted by Chunker):**
```
chunk:123-1-1 a prov:Entity .
chunk:123-1-1 prov:wasDerivedFrom page:123-1 .
chunk:123-1-1 prov:wasGeneratedBy activity:chunk-789 .
chunk:123-1-1 tg:chunkIndex 1 .
chunk:123-1-1 tg:charOffset 0 .
chunk:123-1-1 tg:charLength 2048 .

activity:chunk-789 a prov:Activity .
activity:chunk-789 prov:used page:123-1 .
activity:chunk-789 prov:wasAssociatedWith tg:Chunker .
activity:chunk-789 tg:componentVersion "1.0.0" .
activity:chunk-789 tg:chunkSize 2048 .
activity:chunk-789 tg:chunkOverlap 200 .
```

**Triple (emitted by Knowledge Extractor):**
```
# The extracted triple (edge)
entity:JohnSmith rel:worksAt entity:AcmeCorp .

# Subgraph containing the extracted triples
subgraph:001 tg:contains <<entity:JohnSmith rel:worksAt entity:AcmeCorp>> .
subgraph:001 prov:wasDerivedFrom chunk:123-1-1 .
subgraph:001 prov:wasGeneratedBy activity:extract-999 .

activity:extract-999 a prov:Activity .
activity:extract-999 prov:used chunk:123-1-1 .
activity:extract-999 prov:wasAssociatedWith tg:KnowledgeExtractor .
activity:extract-999 tg:componentVersion "2.1.0" .
activity:extract-999 tg:llmModel "claude-3" .
activity:extract-999 tg:ontology <http://example.org/ontologies/business-v1> .
```

**Embedding (stored in vector store, not triple store):**

Embeddings are stored in the vector store with metadata, not as RDF triples. Each embedding record contains:

| Field | Description | Example |
|-------|-------------|---------|
| vector | The embedding vector | [0.123, -0.456, ...] |
| entity | Node URI the embedding represents | `entity:JohnSmith` |
| chunk_id | Source chunk (provenance) | `chunk:123-1-1` |
| model | Embedding model used | `text-embedding-ada-002` |
| component_version | TG embedder version | `1.0.0` |

The `entity` field links the embedding to the knowledge graph (node URI). The `chunk_id` field provides provenance back to the source chunk, enabling traversal up the DAG to the original document.

#### TrustGraph Namespace Extensions

Custom predicates under the `tg:` namespace for extraction-specific metadata:

| Predicate | Domain | Description |
|-----------|--------|-------------|
| `tg:contains` | Subgraph | Points at a triple contained in this extraction subgraph |
| `tg:pageCount` | Document | Total number of pages in source document |
| `tg:mimeType` | Document | MIME type of source document |
| `tg:pageNumber` | Page | Page number in source document |
| `tg:chunkIndex` | Chunk | Index of chunk within parent |
| `tg:charOffset` | Chunk | Character offset in parent text |
| `tg:charLength` | Chunk | Length of chunk in characters |
| `tg:chunkSize` | Activity | Configured chunk size |
| `tg:chunkOverlap` | Activity | Configured overlap between chunks |
| `tg:componentVersion` | Activity | Version of TG component |
| `tg:llmModel` | Activity | LLM used for extraction |
| `tg:ontology` | Activity | Ontology URI used to guide extraction |
| `tg:embeddingModel` | Activity | Model used for embeddings |
| `tg:sourceText` | Statement | Exact text from which a triple was extracted |
| `tg:sourceCharOffset` | Statement | Character offset within chunk where source text starts |
| `tg:sourceCharLength` | Statement | Length of source text in characters |

#### Vocabulary Bootstrap (Per Collection)

The knowledge graph is ontology-neutral and initialises empty. When writing PROV-O provenance data to a collection for the first time, the vocabulary must be bootstrapped with RDF labels for all classes and predicates. This ensures human-readable display in queries and UI.

**PROV-O Classes:**
```
prov:Entity rdfs:label "Entity" .
prov:Activity rdfs:label "Activity" .
prov:Agent rdfs:label "Agent" .
```

**PROV-O Predicates:**
```
prov:wasDerivedFrom rdfs:label "was derived from" .
prov:wasGeneratedBy rdfs:label "was generated by" .
prov:used rdfs:label "used" .
prov:wasAssociatedWith rdfs:label "was associated with" .
prov:startedAtTime rdfs:label "started at" .
```

**TrustGraph Predicates:**
```
tg:contains rdfs:label "contains" .
tg:pageCount rdfs:label "page count" .
tg:mimeType rdfs:label "MIME type" .
tg:pageNumber rdfs:label "page number" .
tg:chunkIndex rdfs:label "chunk index" .
tg:charOffset rdfs:label "character offset" .
tg:charLength rdfs:label "character length" .
tg:chunkSize rdfs:label "chunk size" .
tg:chunkOverlap rdfs:label "chunk overlap" .
tg:componentVersion rdfs:label "component version" .
tg:llmModel rdfs:label "LLM model" .
tg:ontology rdfs:label "ontology" .
tg:embeddingModel rdfs:label "embedding model" .
tg:sourceText rdfs:label "source text" .
tg:sourceCharOffset rdfs:label "source character offset" .
tg:sourceCharLength rdfs:label "source character length" .
```

**Implementation note:** This vocabulary bootstrap should be idempotent - safe to run multiple times without creating duplicates. Could be triggered on first document processing in a collection, or as a separate collection initialisation step.

#### Sub-Chunk Provenance (Aspirational)

For finer-grained provenance, it would be valuable to record exactly where within a chunk a triple was extracted from. This enables:

- Highlighting the exact source text in the UI
- Verifying extraction accuracy against source
- Debugging extraction quality at the sentence level

**Example with position tracking:**
```
# The extracted triple
entity:JohnSmith rel:worksAt entity:AcmeCorp .

# Subgraph with sub-chunk provenance
subgraph:001 tg:contains <<entity:JohnSmith rel:worksAt entity:AcmeCorp>> .
subgraph:001 prov:wasDerivedFrom chunk:123-1-1 .
subgraph:001 tg:sourceText "John Smith has worked at Acme Corp since 2019" .
subgraph:001 tg:sourceCharOffset 1547 .
subgraph:001 tg:sourceCharLength 46 .
```

**Example with text range (alternative):**
```
subgraph:001 tg:contains <<entity:JohnSmith rel:worksAt entity:AcmeCorp>> .
subgraph:001 prov:wasDerivedFrom chunk:123-1-1 .
subgraph:001 tg:sourceRange "1547-1593" .
subgraph:001 tg:sourceText "John Smith has worked at Acme Corp since 2019" .
```

**Implementation considerations:**

- LLM-based extraction may not naturally provide character positions
- Could prompt the LLM to return the source sentence/phrase alongside extracted triples
- Alternatively, post-process to fuzzy-match extracted entities back to source text
- Trade-off between extraction complexity and provenance granularity
- May be easier to achieve with structured extraction methods than free-form LLM extraction

This is marked as aspirational - the basic chunk-level provenance should be implemented first, with sub-chunk tracking as a future enhancement if feasible.

### Dual Storage Model

The provenance DAG is built progressively as documents flow through the pipeline:

| Store | What's Stored | Purpose |
|-------|---------------|---------|
| Librarian | Document content + parent-child links | Content retrieval, cascade deletion |
| Knowledge Graph | Parent-child edges + metadata | Provenance queries, fact attribution |

Both stores maintain the same DAG structure. The librarian holds content; the graph holds relationships and enables traversal queries.

### Key Design Principles

1. **Document ID as the unit of flow** - Processors pass IDs, not content. Content is fetched from librarian when needed.

2. **Emit once at source** - Metadata is written to the graph once when processing begins, not repeated downstream.

3. **Consistent processor pattern** - Every processor follows the same receive/fetch/produce/save/emit/forward pattern.

4. **Progressive DAG construction** - Each processor adds its level to the DAG. The full provenance chain is built incrementally.

5. **Post-chunker optimization** - After chunking, messages carry both ID and content. Chunks are small (2-4KB), so including content avoids unnecessary librarian round-trips while preserving provenance via the ID.

## Implementation Tasks

### Librarian Changes

#### Current State

- Initiates document processing by sending document ID to first processor
- No connection to triple store - metadata is bundled with extraction outputs
- `add-child-document` creates one-level parent-child links
- `list-children` returns immediate children only

#### Required Changes

**1. New interface: Triple store connection**

Librarian needs to emit document metadata edges directly to the knowledge graph when initiating processing.
- Add triple store client/publisher to librarian service
- On processing initiation: emit root document metadata as graph edges (once)

**2. Document type vocabulary**

Standardize `document_type` values for child documents:
- `source` - original uploaded document
- `page` - page extracted from source (PDF, etc.)
- `chunk` - text chunk derived from page or source

#### Interface Changes Summary

| Interface | Change |
|-----------|--------|
| Triple store | New outbound connection - emit document metadata edges |
| Processing initiation | Emit metadata to graph before forwarding document ID |

### PDF Extractor Changes

#### Current State

- Receives document content (or streams large documents)
- Extracts text from PDF pages
- Forwards page content to chunker
- No interaction with librarian or triple store

#### Required Changes

**1. New interface: Librarian client**

PDF extractor needs to save each page as a child document in librarian.
- Add librarian client to PDF extractor service
- For each page: call `add-child-document` with parent = root document ID

**2. New interface: Triple store connection**

PDF extractor needs to emit parent-child edges to knowledge graph.
- Add triple store client/publisher
- For each page: emit edge linking page document to parent document

**3. Change output format**

Instead of forwarding page content directly, forward page document ID.
- Chunker will fetch content from librarian using the ID

#### Interface Changes Summary

| Interface | Change |
|-----------|--------|
| Librarian | New outbound - save child documents |
| Triple store | New outbound - emit parent-child edges |
| Output message | Change from content to document ID |

### Chunker Changes

#### Current State

- Receives page/text content
- Splits into chunks
- Forwards chunk content to downstream processors
- No interaction with librarian or triple store

#### Required Changes

**1. Change input handling**

Receive document ID instead of content, fetch from librarian.
- Add librarian client to chunker service
- Fetch page content using document ID

**2. New interface: Librarian client (write)**

Save each chunk as a child document in librarian.
- For each chunk: call `add-child-document` with parent = page document ID

**3. New interface: Triple store connection**

Emit parent-child edges to knowledge graph.
- Add triple store client/publisher
- For each chunk: emit edge linking chunk document to page document

**4. Change output format**

Forward both chunk document ID and chunk content (post-chunker optimization).
- Downstream processors receive ID for provenance + content to work with

#### Interface Changes Summary

| Interface | Change |
|-----------|--------|
| Input message | Change from content to document ID |
| Librarian | New outbound (read + write) - fetch content, save child documents |
| Triple store | New outbound - emit parent-child edges |
| Output message | Change from content-only to ID + content |

### Knowledge Extractor Changes

#### Current State

- Receives chunk content
- Extracts triples and embeddings
- Emits to triple store and embedding store
- `subjectOf` relationship points to top-level document (not chunk)

#### Required Changes

**1. Change input handling**

Receive chunk document ID alongside content.
- Use chunk ID for provenance linking (content already included per optimization)

**2. Update triple provenance**

Link extracted triples to chunk (not top-level document).
- Use reification to create edge pointing to edge
- `subjectOf` relationship: triple → chunk document ID
- First use of existing reification support

**3. Update embedding provenance**

Link embedding entity IDs to chunk.
- Emit edge: embedding entity ID → chunk document ID

#### Interface Changes Summary

| Interface | Change |
|-----------|--------|
| Input message | Expect chunk ID + content (not content only) |
| Triple store | Use reification for triple → chunk provenance |
| Embedding provenance | Link entity ID → chunk ID |

## Vocabulary Reference

The full OWL ontology covering all extraction and query-time classes and predicates is at `specs/ontology/trustgraph.ttl`.

## References

- Query-time provenance: `docs/tech-specs/query-time-explainability.md`
- Agent explainability: `docs/tech-specs/agent-explainability.md`
- PROV-O standard for provenance modeling
- Existing source metadata in knowledge graph (needs audit)
