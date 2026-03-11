# Extraction Flows

This document describes how data flows through the TrustGraph extraction pipeline, from document submission through to storage in knowledge stores.

## Overview

```
┌──────────┐     ┌─────────────┐     ┌─────────┐     ┌────────────────────┐
│ Librarian│────▶│ PDF Decoder │────▶│ Chunker │────▶│ Knowledge          │
│          │     │ (PDF only)  │     │         │     │ Extraction         │
│          │────────────────────────▶│         │     │                    │
└──────────┘     └─────────────┘     └─────────┘     └────────────────────┘
                                          │                    │
                                          │                    ├──▶ Triples
                                          │                    ├──▶ Entity Contexts
                                          │                    └──▶ Rows
                                          │
                                          └──▶ Document Embeddings
```

## Content Storage

### Blob Storage (S3/Minio)

Document content is stored in S3-compatible blob storage:
- Path format: `doc/{object_id}` where object_id is a UUID
- All document types stored here: source documents, pages, chunks

### Metadata Storage (Cassandra)

Document metadata stored in Cassandra includes:
- Document ID, title, kind (MIME type)
- `object_id` reference to blob storage
- `parent_id` for child documents (pages, chunks)
- `document_type`: "source", "page", "chunk", "answer"

### Inline vs Streaming Threshold

Content transmission uses a size-based strategy:
- **< 2MB**: Content included inline in message (base64-encoded)
- **≥ 2MB**: Only `document_id` sent; processor fetches via librarian API

## Stage 1: Document Submission (Librarian)

### Entry Point

Documents enter the system via librarian's `add-document` operation:
1. Content uploaded to blob storage
2. Metadata record created in Cassandra
3. Returns document ID

### Triggering Extraction

The `add-processing` operation triggers extraction:
- Specifies `document_id`, `flow` (pipeline ID), `collection` (target store)
- Librarian's `load_document()` fetches content and publishes to flow input queue

### Schema: Document

```
Document
├── metadata: Metadata
│   ├── id: str              # Document identifier
│   ├── user: str            # Tenant/user ID
│   ├── collection: str      # Target collection
│   └── metadata: list[Triple]  # (largely unused, historical)
├── data: bytes              # PDF content (base64, if inline)
└── document_id: str         # Librarian reference (if streaming)
```

**Routing**: Based on `kind` field:
- `application/pdf` → `document-load` queue → PDF Decoder
- `text/plain` → `text-load` queue → Chunker

## Stage 2: PDF Decoder

Converts PDF documents into text pages.

### Process

1. Fetch content (inline `data` or via `document_id` from librarian)
2. Extract pages using PyPDF
3. For each page:
   - Save as child document in librarian (`{doc_id}/p{page_num}`)
   - Emit provenance triples (page derived from document)
   - Forward to chunker

### Schema: TextDocument

```
TextDocument
├── metadata: Metadata
│   ├── id: str              # Page URI (e.g., https://trustgraph.ai/doc/xxx/p1)
│   ├── user: str
│   ├── collection: str
│   └── metadata: list[Triple]
├── text: bytes              # Page text content (if inline)
└── document_id: str         # Librarian reference (e.g., "doc123/p1")
```

## Stage 3: Chunker

Splits text into chunks at configured size.

### Parameters (flow-configurable)

- `chunk_size`: Target chunk size in characters (default: 2000)
- `chunk_overlap`: Overlap between chunks (default: 100)

### Process

1. Fetch text content (inline or via librarian)
2. Split using recursive character splitter
3. For each chunk:
   - Save as child document in librarian (`{parent_id}/c{index}`)
   - Emit provenance triples (chunk derived from page/document)
   - Forward to extraction processors

### Schema: Chunk

```
Chunk
├── metadata: Metadata
│   ├── id: str              # Chunk URI
│   ├── user: str
│   ├── collection: str
│   └── metadata: list[Triple]
├── chunk: bytes             # Chunk text content
└── document_id: str         # Librarian chunk ID (e.g., "doc123/p1/c3")
```

### Document ID Hierarchy

Child documents encode their lineage in the ID:
- Source: `doc123`
- Page: `doc123/p5`
- Chunk from page: `doc123/p5/c2`
- Chunk from text: `doc123/c2`

## Stage 4: Knowledge Extraction

Multiple extraction patterns available, selected by flow configuration.

### Pattern A: Basic GraphRAG

Two parallel processors:

**kg-extract-definitions**
- Input: Chunk
- Output: Triples (entity definitions), EntityContexts
- Extracts: entity labels, definitions

**kg-extract-relationships**
- Input: Chunk
- Output: Triples (relationships), EntityContexts
- Extracts: subject-predicate-object relationships

### Pattern B: Ontology-Driven (kg-extract-ontology)

- Input: Chunk
- Output: Triples, EntityContexts
- Uses configured ontology to guide extraction

### Pattern C: Agent-Based (kg-extract-agent)

- Input: Chunk
- Output: Triples, EntityContexts
- Uses agent framework for extraction

### Pattern D: Row Extraction (kg-extract-rows)

- Input: Chunk
- Output: Rows (structured data, not triples)
- Uses schema definition to extract structured records

### Schema: Triples

```
Triples
├── metadata: Metadata
│   ├── id: str
│   ├── user: str
│   ├── collection: str
│   └── metadata: list[Triple]  # (set to [] by extractors)
└── triples: list[Triple]
    └── Triple
        ├── s: Term              # Subject
        ├── p: Term              # Predicate
        ├── o: Term              # Object
        └── g: str | None        # Named graph
```

### Schema: EntityContexts

```
EntityContexts
├── metadata: Metadata
└── entities: list[EntityContext]
    └── EntityContext
        ├── entity: Term         # Entity identifier (IRI)
        ├── context: str         # Textual description for embedding
        └── chunk_id: str        # Source chunk ID (provenance)
```

### Schema: Rows

```
Rows
├── metadata: Metadata
├── row_schema: RowSchema
│   ├── name: str
│   ├── description: str
│   └── fields: list[Field]
└── rows: list[dict[str, str]]   # Extracted records
```

## Stage 5: Embeddings Generation

### Graph Embeddings

Converts entity contexts into vector embeddings.

**Process:**
1. Receive EntityContexts
2. Call embeddings service with context text
3. Output GraphEmbeddings (entity → vector mapping)

**Schema: GraphEmbeddings**

```
GraphEmbeddings
├── metadata: Metadata
└── entities: list[EntityEmbeddings]
    └── EntityEmbeddings
        ├── entity: Term         # Entity identifier
        ├── vector: list[float]  # Embedding vector
        └── chunk_id: str        # Source chunk (provenance)
```

### Document Embeddings

Converts chunk text directly into vector embeddings.

**Process:**
1. Receive Chunk
2. Call embeddings service with chunk text
3. Output DocumentEmbeddings

**Schema: DocumentEmbeddings**

```
DocumentEmbeddings
├── metadata: Metadata
└── chunks: list[ChunkEmbeddings]
    └── ChunkEmbeddings
        ├── chunk_id: str        # Chunk identifier
        └── vector: list[float]  # Embedding vector
```

### Row Embeddings

Converts row index fields into vector embeddings.

**Process:**
1. Receive Rows
2. Embed configured index fields
3. Output to row vector store

## Stage 6: Storage

### Triple Store

- Receives: Triples
- Storage: Cassandra (entity-centric tables)
- Named graphs separate core knowledge from provenance:
  - `""` (default): Core knowledge facts
  - `urn:graph:source`: Extraction provenance
  - `urn:graph:retrieval`: Query-time explainability

### Vector Store (Graph Embeddings)

- Receives: GraphEmbeddings
- Storage: Qdrant, Milvus, or Pinecone
- Indexed by: entity IRI
- Metadata: chunk_id for provenance

### Vector Store (Document Embeddings)

- Receives: DocumentEmbeddings
- Storage: Qdrant, Milvus, or Pinecone
- Indexed by: chunk_id

### Row Store

- Receives: Rows
- Storage: Cassandra
- Schema-driven table structure

### Row Vector Store

- Receives: Row embeddings
- Storage: Vector DB
- Indexed by: row index fields

## Metadata Field Analysis

### Actively Used Fields

| Field | Usage |
|-------|-------|
| `metadata.id` | Document/chunk identifier, logging, provenance |
| `metadata.user` | Multi-tenancy, storage routing |
| `metadata.collection` | Target collection selection |
| `document_id` | Librarian reference, provenance linking |
| `chunk_id` | Provenance tracking through pipeline |

### Potentially Redundant Fields

| Field | Status |
|-------|--------|
| `metadata.metadata` | Set to `[]` by all extractors; document-level metadata now handled by librarian at submission time |

### Bytes Fields Pattern

All content fields (`data`, `text`, `chunk`) are `bytes` but immediately decoded to UTF-8 strings by all processors. No processor uses raw bytes.

## Flow Configuration

Flows are defined externally and provided to librarian via config service. Each flow specifies:

- Input queues (`text-load`, `document-load`)
- Processor chain
- Parameters (chunk size, extraction method, etc.)

Example flow patterns:
- `pdf-graphrag`: PDF → Decoder → Chunker → Definitions + Relationships → Embeddings
- `text-graphrag`: Text → Chunker → Definitions + Relationships → Embeddings
- `pdf-ontology`: PDF → Decoder → Chunker → Ontology Extraction → Embeddings
- `text-rows`: Text → Chunker → Row Extraction → Row Store
