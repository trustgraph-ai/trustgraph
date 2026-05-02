---
layout: default
title: "Data Ownership and Information Separation"
parent: "Tech Specs"
---

# Data Ownership and Information Separation

## Purpose

This document defines the logical ownership model for data in
TrustGraph: what the artefacts are, who owns them, and how they relate
to each other.

The IAM spec ([iam.md](iam.md)) describes authentication and
authorisation mechanics. This spec addresses the prior question: what
are the boundaries around data, and who owns what?

## Concepts

### Workspace

A workspace is the primary isolation boundary. It represents an
organisation, team, or independent operating unit. All data belongs to
exactly one workspace.

Cross-workspace access through the API is gated by the IAM regime
(see [`iam-contract.md`](iam-contract.md)). In the OSS distribution,
the role table defined in [`capabilities.md`](capabilities.md)
permits cross-workspace operation only to the `admin` role; the
`reader` and `writer` roles are constrained to a single assigned
workspace per credential. Other regimes can model the relationship
between identity and workspace differently — the gateway makes no
assumption.

A workspace owns:
- Source documents
- Flows (processing pipeline definitions)
- Knowledge cores (stored extraction output)
- Collections (organisational units for extracted knowledge)

### Collection

A collection is an organisational unit within a workspace. It groups
extracted knowledge produced from source documents. A workspace can
have multiple collections, allowing:

- Processing the same documents with different parameters or models.
- Maintaining separate knowledge bases for different purposes.
- Deleting extracted knowledge without deleting source documents.

Collections do not own source documents. A source document exists at the
workspace level and can be processed into multiple collections.

### Source document

A source document (PDF, text file, etc.) is raw input uploaded to the
system. Documents belong to the workspace, not to a specific collection.

This is intentional. A document is an asset that exists independently
of how it is processed. The same PDF might be processed into multiple
collections with different chunking parameters or extraction models.
Tying a document to a single collection would force re-upload for each
collection.

### Flow

A flow defines a processing pipeline: which models to use, what
parameters to apply (chunk size, temperature, etc.), and how processing
services are connected. Flows belong to a workspace.

The processing services themselves (document-decoder, chunker,
embeddings, LLM completion, etc.) are shared infrastructure — they serve
all workspaces. Each flow has its own queues, keeping data from
different workspaces and flows separate as it moves through the
pipeline.

Different workspaces can define different flows. Workspace A might use
GPT-5.2 with a chunk size of 2000, while workspace B uses Claude with a
chunk size of 1000.

### Prompts

Prompts are templates that control how the LLM behaves during knowledge
extraction and query answering. They belong to a workspace, allowing
different workspaces to have different extraction strategies, response
styles, or domain-specific instructions.

### Ontology

An ontology defines the concepts, entities, and relationships that the
extraction pipeline looks for in source documents. Ontologies belong to
a workspace. A medical workspace might define ontologies around diseases,
symptoms, and treatments, while a legal workspace defines ontologies
around statutes, precedents, and obligations.

### Schemas

Schemas define structured data types for extraction. They specify what
fields to extract, their types, and how they relate. Schemas belong to
a workspace, as different workspaces extract different structured
information from their documents.

### Tools, tool services, and MCP tools

Tools define capabilities available to agents: what actions they can
take, what external services they can call. Tool services configure how
tools connect to backend services. MCP tools configure connections to
remote MCP servers, including authentication tokens. All belong to a
workspace.

### Agent patterns and agent task types

Agent patterns define agent behaviour strategies (how an agent reasons,
what steps it follows). Agent task types define the kinds of tasks
agents can perform. Both belong to a workspace, as different workspaces
may have different agent configurations.

### Token costs

Token cost definitions specify pricing for LLM token usage per model.
These belong to a workspace since different workspaces may use different
models or have different billing arrangements.

### Flow blueprints

Flow blueprints are templates for creating flows. They define the
default pipeline structure and parameters. Blueprints belong to a
workspace, allowing workspaces to define custom processing templates.

### Parameter types

Parameter types define the kinds of parameters that flows accept (e.g.
"llm-model", "temperature"), including their defaults and validation
rules. They belong to a workspace since workspaces that define custom
flows need to define the parameter types those flows use.

### Interface descriptions

Interface descriptions define the connection points of a flow — what
queues and topics it uses. They belong to a workspace since they
describe workspace-owned flows.

### Knowledge core

A knowledge core is a stored snapshot of extracted knowledge (triples
and graph embeddings). Knowledge cores belong to a workspace and can be
loaded into any collection within that workspace.

Knowledge cores serve as a portable extraction output. You process
documents through a flow, the pipeline produces triples and embeddings,
and the results can be stored as a knowledge core. That core can later
be loaded into a different collection or reloaded after a collection is
cleared.

### Extracted knowledge

Extracted knowledge is the live, queryable content within a collection:
triples in the knowledge graph, graph embeddings, and document
embeddings. It is the product of processing source documents through a
flow into a specific collection.

Extracted knowledge is scoped to a workspace and a collection. It
cannot exist without both.

### Processing record

A processing record tracks which source document was processed, through
which flow, into which collection. It links the source document
(workspace-scoped) to the extracted knowledge (workspace + collection
scoped).

## Ownership summary

| Artefact | Owned by | Shared across collections? |
|----------|----------|---------------------------|
| Workspaces | Global (platform) | N/A |
| User accounts | Global (platform) | N/A |
| API keys | Global (platform) | N/A |
| Source documents | Workspace | Yes |
| Flows | Workspace | N/A |
| Flow blueprints | Workspace | N/A |
| Prompts | Workspace | N/A |
| Ontologies | Workspace | N/A |
| Schemas | Workspace | N/A |
| Tools | Workspace | N/A |
| Tool services | Workspace | N/A |
| MCP tools | Workspace | N/A |
| Agent patterns | Workspace | N/A |
| Agent task types | Workspace | N/A |
| Token costs | Workspace | N/A |
| Parameter types | Workspace | N/A |
| Interface descriptions | Workspace | N/A |
| Knowledge cores | Workspace | Yes — can be loaded into any collection |
| Collections | Workspace | N/A |
| Extracted knowledge | Workspace + collection | No |
| Processing records | Workspace + collection | No |

## Scoping summary

### Global (system-level)

A small number of artefacts exist outside any workspace:

- **Workspace registry** — the list of workspaces itself
- **User accounts** — users reference a workspace but are not owned by
  one
- **API keys** — belong to users, not workspaces

These are managed by the IAM layer and exist at the platform level.

### Workspace-owned

All other configuration and data is workspace-owned:

- Flow definitions and parameters
- Flow blueprints
- Prompts
- Ontologies
- Schemas
- Tools, tool services, and MCP tools
- Agent patterns and agent task types
- Token costs
- Parameter types
- Interface descriptions
- Collection definitions
- Knowledge cores
- Source documents
- Collections and their extracted knowledge

## Relationship between artefacts

```
Platform (global)
 |
 +-- Workspaces
 |    |
 +-- User accounts (each assigned to a workspace)
 |    |
 +-- API keys (belong to users)

Workspace
 |
 +-- Source documents (uploaded, unprocessed)
 |
 +-- Flows (pipeline definitions: models, parameters, queues)
 |
 +-- Flow blueprints (templates for creating flows)
 |
 +-- Prompts (LLM instruction templates)
 |
 +-- Ontologies (entity and relationship definitions)
 |
 +-- Schemas (structured data type definitions)
 |
 +-- Tools, tool services, MCP tools (agent capabilities)
 |
 +-- Agent patterns and agent task types (agent behaviour)
 |
 +-- Token costs (LLM pricing per model)
 |
 +-- Parameter types (flow parameter definitions)
 |
 +-- Interface descriptions (flow connection points)
 |
 +-- Knowledge cores (stored extraction snapshots)
 |
 +-- Collections
      |
      +-- Extracted knowledge (triples, embeddings)
      |
      +-- Processing records (links documents to collections)
```

A typical workflow:

1. A source document is uploaded to the workspace.
2. A flow defines how to process it (which models, what parameters).
3. The document is processed through the flow into a collection.
4. Processing records track what was processed.
5. Extracted knowledge (triples, embeddings) is queryable within the
   collection.
6. Optionally, the extracted knowledge is stored as a knowledge core
   for later reuse.

## Implementation notes

The current codebase uses a `user` field in message metadata and storage
partition keys to identify the workspace. The `collection` field
identifies the collection within that workspace.

The gateway is the single point at which workspace gets stamped onto
outbound pub/sub messages.  An incoming credential authenticates to a
workspace (the credential's binding, not a user-to-workspace lookup —
see [`iam-contract.md`](iam-contract.md) and the *Identity surface*
section of [`iam.md`](iam.md)); any caller-supplied workspace on the
request is reconciled against the authenticated identity by the IAM
regime; the resolved value is what the gateway writes into outgoing
messages and the storage layers' partition keys.  Backend services
trust the workspace they receive — defense-in-depth happens at the
gateway, not at the bus.

For details on how each storage backend implements this scoping, see:

- [Entity-Centric Graph](entity-centric-graph.md) — Cassandra KG schema
- [Neo4j User Collection Isolation](neo4j-user-collection-isolation.md)
- [Collection Management](collection-management.md)

### Known inconsistencies in current implementation

- **Pipeline intermediate tables** do not include collection in their
  partition keys. Re-processing the same document into a different
  collection may overwrite intermediate state.
- **Processing metadata** stores collection in the row payload but not
  in the partition key, making collection-based queries inefficient.
- **Upload sessions** are keyed by upload ID, not workspace. The
  gateway should validate workspace ownership before allowing
  operations on upload sessions.

## References

- [IAM Contract](iam-contract.md) — gateway↔IAM regime abstraction.
- [Identity and Access Management](iam.md) — gateway-side framing.
- [Capability Vocabulary](capabilities.md) — capability strings and
  the OSS role bundles that decide cross-workspace eligibility.
- [Collection Management](collection-management.md)
- [Entity-Centric Graph](entity-centric-graph.md)
- [Neo4j User Collection Isolation](neo4j-user-collection-isolation.md)
- [Multi-Tenant Support](multi-tenant-support.md)
