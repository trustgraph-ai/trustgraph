---
layout: default
title: "Ontology Service Technical Specification"
parent: "Tech Specs"
---

# Ontology Service Technical Specification

## Problem Statement

Ontology handling in TrustGraph has three problems.

### Non-standard ontology format at the API boundary

Ontologies are loaded as a custom JSON structure with keys like
`classes`, `objectProperties`, and `datatypeProperties`. This format
maps closely to OWL concepts but is not a recognised standard. Anyone
loading an ontology must convert from whatever format they have (Turtle,
OWL/XML, JSON-LD, Protégé export) into this bespoke schema. There is no
tooling ecosystem for it, no validators, and no documentation outside
this project.

Standard serialisations already exist for exactly this data: JSON-LD
and Turtle are both W3C standards, widely supported by tools like
rdflib, and can represent the same OWL classes, properties, domains,
ranges, and hierarchies that the custom format carries. Accepting a
standard format at the API boundary would eliminate the conversion step
and let users work with familiar tooling.

### Ontology management is embedded in the extract processor

The ontology extract processor (`extract.py`, ~1,090 lines) directly
owns ontology loading, embedding, subset selection, URI expansion,
triple validation, and ontology triple generation. The query side has
its own parallel implementation (`query/ontology/`) that was scaffolded
but never completed or integrated.

This coupling means:

- Ontology logic cannot be reused by other consumers (e.g. a
  NL-to-SPARQL query service) without duplicating it.
- The extract processor is responsible for both text extraction and
  ontology management, making it harder to reason about and test.
- Changes to ontology handling (format support, validation rules,
  embedding strategy) require modifying the extract processor.

A separate ontology service would own parsing, validation, storage,
embedding, and subset selection, exposing these capabilities to any
consumer that needs ontology context.

### No natural-language-to-SPARQL query path

TrustGraph has a SPARQL query service that evaluates SPARQL against the
knowledge graph, but there is no way to get from a natural language
question to a SPARQL query. The scaffolded `query/ontology/` package
includes a `SPARQLGenerator` but it was never tested or integrated — its
host service (`OntoRAGQueryService`) does not even start.

A key obstacle was entity resolution: translating a natural language
mention like "Apple" into the correct knowledge graph URI. Without that,
generated SPARQL can only use string matching or hope that entity names
match graph identifiers exactly.

Typed graph embeddings now solve this. Entity embeddings stored in
Qdrant carry `rdf_type` metadata, so a semantic search for "Apple"
filtered to type `Organization` returns the correct entity URI. This
makes a viable NL-to-SPARQL path possible:

1. Use the ontology schema to help an LLM identify entities, their
   likely types, and the relationships being asked about.
2. Resolve each entity mention to a knowledge graph URI via typed
   graph embedding lookup.
3. Construct SPARQL using the resolved URIs and ontology properties.

This path requires ontology context (the schema) to be available as a
service, reinforcing the need for the ontology service described above.

## Goals

- **Standard ontology formats**: accept JSON-LD and Turtle at the API
  boundary, parsed via rdflib. Retire the custom JSON format.
- **Ontology service**: a separate service that owns ontology parsing,
  validation, embedding, and subset selection, available to any
  consumer over pub/sub.
- **NL-to-SPARQL query path**: a service that translates natural
  language questions to SPARQL queries, using ontology context for
  schema awareness and typed graph embeddings for entity resolution.
- **Extract processor simplification**: the ontology extract processor
  becomes a client of the ontology service rather than owning ontology
  management directly.
- **No breaking changes to extraction output**: the knowledge graph
  triples and entity contexts produced by extraction remain the same.

### Future goals

- **Ontology-guided GraphRAG**: use ontology context to automatically
  derive guided traversal constraints (hop types, relationship filters)
  from a natural language question, so that GraphRAG queries benefit
  from schema awareness without the caller specifying guidance manually.

## Design Decisions

- **JSON-LD as internal canonical format**: ontologies are stored and
  transmitted as JSON-LD. Turtle is accepted at the ingestion boundary
  and converted on arrival — a lossless, trivial conversion via rdflib.
- **rdflib for parsing and validation**: already a dependency; handles
  format conversion and gives OWL/RDFS validation for free.
- **Pub/sub FlowProcessor pattern**: the ontology service and
  NL-to-SPARQL service follow the standard FlowProcessor pattern,
  consistent with the rest of the architecture.
- **LLM-based SPARQL generation**: the LLM receives ontology schema
  context and resolved entity URIs. The scaffolded template approach
  was too brittle for real use.
- **Entity resolution via existing typed graph embeddings**: reuse the
  Qdrant infrastructure with `rdf_type` filtering rather than building
  a parallel entity resolver.
- **Retire the `query/ontology/` scaffold**: replace entirely rather
  than retrofit; it was never tested or integrated.
- **Python API SDK and CLI support**: new services get SDK bindings and
  CLI utilities so that users can interact with the ontology service
  and NL-to-SPARQL service directly for experimentation and debugging.

## Services

### New services

- **Ontology service**: owns ingestion (JSON-LD/Turtle parsing),
  validation, embedding, and subset selection. Serves ontology context
  to any consumer over pub/sub.
- **NL-to-SPARQL translation service**: takes a natural language
  question, calls the ontology service for schema context, resolves
  entities via typed graph embeddings, and uses an LLM to generate
  SPARQL. Callable directly for debugging and experimentation.
- **SPARQL query orchestration service**: chains the NL-to-SPARQL
  translation service with the existing SPARQL query service to go
  from question to results in one call.

### Modified services

- **Ontology extract processor**: simplified to be a client of the
  ontology service for subset selection and validation, rather than
  owning that logic itself.

### Retired

- **`query/ontology/` package**: replaced by the NL-to-SPARQL service.
- **Custom JSON ontology format**: replaced by JSON-LD/Turtle.

## Technical Design

### Ontology service

The ontology service is a FlowProcessor that subscribes to `ontology`
config events and serves ontology context to consumers over pub/sub.

**Ingestion**: on config event, the service receives ontology data as
JSON-LD (or Turtle, converted at the boundary). It parses via rdflib
into an in-memory RDF graph, validates OWL structure (class hierarchy,
domain/range references), and embeds ontology elements (classes,
properties) using the embeddings service. The parsed and embedded
ontology is held in memory, keyed by workspace and ontology ID.

**Subset selection**: consumers send a request containing text (or
keywords) and receive back the relevant ontology subset — classes,
object properties, and datatype properties that are semantically
relevant to the text. This is the same capability currently embedded
in the extract processor, extracted into a standalone request/response
interface.

**Schemas**:

A single request/response queue supports multiple operations via an
`operation` field, avoiding the need for separate queues per function.

```python
@dataclass
class OntologyRequest:
    operation: str = ""  # "subset" or "status"

    # For "subset" operation
    text: str = ""
    top_k: int = 10
    similarity_threshold: float = 0.3

@dataclass
class OntologyResponse:
    error: Error | None = None
    operation: str = ""

    # For "subset" operation
    ontology_id: str = ""
    classes: dict[str, str] = field(default_factory=dict)
    object_properties: dict[str, str] = field(default_factory=dict)
    datatype_properties: dict[str, str] = field(default_factory=dict)
    namespace: str = ""

    # For "status" operation
    loaded: bool = False
    ontology_ids: list[str] = field(default_factory=list)
    element_count: int = 0
```

The dict values in the subset response are JSON-LD serialisations of
each element, so consumers work with standard RDF representations
rather than a bespoke structure.

**Config type**: ontologies continue to use the `ontology` config type.
The config value changes from the custom JSON format to JSON-LD. This
is a breaking change to the config format but not to the config
delivery mechanism.

### NL-to-SPARQL translation service

Following the pattern established by the structured query services
(`nlp-query` for NL-to-GraphQL translation, `structured-query` for
orchestration), the SPARQL path is split into two services:

**NL-to-SPARQL translation** (`nl-sparql-query`): takes a natural
language question and returns the generated SPARQL without executing
it. This is directly callable for debugging and experimentation —
users can inspect the generated SPARQL, refine their question, or
hand-edit the query before execution.

**Flow**:

1. Receive natural language question.
2. Call the ontology service to get the relevant ontology subset for
   the question text.
3. Call the graph embeddings service with entity mentions from the
   question, filtered by `rdf_type`, to resolve entity URIs.
4. Build a prompt containing the ontology schema (classes, properties,
   namespaces) and the resolved entity URIs. Call the prompt service
   to have the LLM generate SPARQL.
5. Return the generated SPARQL to the caller.

**Schemas**:

```python
@dataclass
class QuestionToSparqlRequest:
    question: str = ""
    collection: str = ""
    rdf_type_hint: str = ""
    limit: int = 10

@dataclass
class QuestionToSparqlResponse:
    error: Error | None = None
    sparql: str = ""
    variables: list[str] = field(default_factory=list)
    resolved_entities: dict[str, str] = field(default_factory=dict)
```

The response includes the resolved entity mappings (mention → URI) so
the caller can see how entity resolution was performed.

**Client specs**: OntologyClientSpec, GraphEmbeddingsClientSpec,
PromptClientSpec.

### SPARQL query orchestration service

**SPARQL query orchestration** (`sparql-nl-query`): takes a natural
language question, calls the NL-to-SPARQL translation service, then
passes the generated SPARQL to the existing SPARQL query service for
execution. Returns both the generated SPARQL and the result bindings.

This mirrors the `structured-query` service which chains `nlp-query`
→ `rows-query`.

**Schemas**:

```python
@dataclass
class SparqlNLQueryRequest:
    question: str = ""
    collection: str = ""
    rdf_type_hint: str = ""
    limit: int = 10

@dataclass
class SparqlNLQueryResponse:
    error: Error | None = None
    sparql: str = ""
    variables: list[str] = field(default_factory=list)
    bindings: list[SparqlBinding] = field(default_factory=list)
```

**Client specs**: RequestResponseSpec for the NL-to-SPARQL translation
service, SparqlClientSpec for the existing SPARQL query service.

### Extract processor changes

The ontology extract processor drops its internal OntologyLoader,
OntologyEmbedder, OntologySelector, and the `build_ontology_triples`
/ `expand_uri` / `is_valid_triple` methods. In their place it uses an
OntologyClientSpec to request an ontology subset from the ontology
service for each chunk.

The extraction prompt, triple conversion, and entity context generation
remain in the extract processor — those are extraction concerns, not
ontology concerns.

## Design Resolutions

### Extraction during ontology loading

The ontology service blocks on requests until the ontology is loaded
and ready. Consumers do not need special handling — a subset request
simply takes longer if it arrives during loading.

### External ontology references

`owl:imports` is not supported. The ontology service works only with
what is explicitly provided in the configuration. This matches current
behaviour and avoids network dependencies. Can be revisited later.

### Ontology loading lifecycle

The ontology service subscribes to config push events for the
`ontology` config type. On receiving an update it begins parsing,
validation, and embedding. The service supports concurrent subset
requests during normal operation. Requests that arrive while loading
is in progress block until loading completes.

Callers can query loading state without blocking by sending a request
with `operation="status"` on the same request/response queue.

### Ontology matching strategy

Retain the current embedding-similarity approach for subset selection.
The ontology service interface is agnostic to the matching algorithm,
so this can evolve (e.g. adding reranking) without changing consumers.
