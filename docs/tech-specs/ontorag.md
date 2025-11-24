# OntoRAG: Ontology-Based Knowledge Extraction and Query Technical Specification

## Overview

OntoRAG is an ontology-driven knowledge extraction and query system that enforces strict semantic consistency during both the extraction of knowledge triples from unstructured text and the querying of the resulting knowledge graph. Similar to GraphRAG but with formal ontology constraints, OntoRAG ensures all extracted triples conform to predefined ontological structures and provides semantically-aware querying capabilities.

The system uses vector similarity matching to dynamically select relevant ontology subsets for both extraction and query operations, enabling focused and contextually appropriate processing while maintaining semantic validity.

**Service Name**: `kg-extract-ontology`

## Goals

- **Ontology-Conformant Extraction**: Ensure all extracted triples strictly conform to loaded ontologies
- **Dynamic Context Selection**: Use embeddings to select relevant ontology subsets for each chunk
- **Semantic Consistency**: Maintain class hierarchies, property domains/ranges, and constraints
- **Efficient Processing**: Use in-memory vector stores for fast ontology element matching
- **Scalable Architecture**: Support multiple concurrent ontologies with different domains

## Background

Current knowledge extraction services (`kg-extract-definitions`, `kg-extract-relationships`) operate without formal constraints, potentially producing inconsistent or incompatible triples. OntoRAG addresses this by:

1. Loading formal ontologies that define valid classes and properties
2. Using embeddings to match text content with relevant ontology elements
3. Constraining extraction to only produce ontology-conformant triples
4. Providing semantic validation of extracted knowledge

This approach combines the flexibility of neural extraction with the rigor of formal knowledge representation.

## Technical Design

### Architecture

The OntoRAG system consists of the following components:

```
┌─────────────────┐
│  Configuration  │
│    Service      │
└────────┬────────┘
         │ Ontologies
         ▼
┌─────────────────┐      ┌──────────────┐
│ kg-extract-     │────▶│  Embedding   │
│   ontology      │      │   Service    │
└────────┬────────┘      └──────────────┘
         │                      │
         ▼                      ▼
┌─────────────────┐      ┌──────────────┐
│   In-Memory     │◀────│   Ontology   │
│  Vector Store   │      │   Embedder   │
└────────┬────────┘      └──────────────┘
         │
         ▼
┌─────────────────┐      ┌──────────────┐
│    Sentence     │────▶│   Chunker    │
│    Splitter     │      │   Service    │
└────────┬────────┘      └──────────────┘
         │
         ▼
┌─────────────────┐      ┌──────────────┐
│    Ontology     │────▶│   Vector     │
│    Selector     │      │   Search     │
└────────┬────────┘      └──────────────┘
         │
         ▼
┌─────────────────┐      ┌──────────────┐
│    Prompt       │────▶│   Prompt     │
│   Constructor   │      │   Service    │
└────────┬────────┘      └──────────────┘
         │
         ▼
┌─────────────────┐
│  Triple Output  │
└─────────────────┘
```

### Component Details

#### 1. Ontology Loader

**Purpose**: Retrieves and parses ontology configurations from the configuration service using event-driven updates.

**Implementation**:
The Ontology Loader uses TrustGraph's ConfigPush queue to receive event-driven ontology configuration updates. When a configuration element of type "ontology" is added or modified, the loader receives the update via the config-update queue and parses the JSON structure containing metadata, classes, object properties, and datatype properties. These parsed ontologies are stored in memory as structured objects that can be efficiently accessed during the extraction process.

**Key Operations**:
- Subscribe to config-update queue for ontology-type configurations
- Parse JSON ontology structures into OntologyClass and OntologyProperty objects
- Validate ontology structure and consistency
- Cache parsed ontologies in memory for fast access
- Handle per-flow processing with flow-specific vector stores

**Implementation Location**: `trustgraph-flow/trustgraph/extract/kg/ontology/ontology_loader.py`

#### 2. Ontology Embedder

**Purpose**: Creates vector embeddings for all ontology elements to enable semantic similarity matching.

**Implementation**:
The Ontology Embedder processes each element in the loaded ontologies (classes, object properties, and datatype properties) and generates vector embeddings using the EmbeddingsClientSpec service. For each element, it combines the element's identifier, labels, and description (comment) to create a text representation. This text is then converted to a high-dimensional vector embedding that captures its semantic meaning. These embeddings are stored in a per-flow in-memory FAISS vector store along with metadata about the element type, source ontology, and full definition. The embedder automatically detects the embedding dimension from the first embedding response.

**Key Operations**:
- Create text representations from element IDs, labels, and comments
- Generate embeddings via EmbeddingsClientSpec (using asyncio.gather for batch processing)
- Store embeddings with comprehensive metadata in FAISS vector store
- Index by ontology, element type, and element ID for efficient retrieval
- Auto-detect embedding dimensions for vector store initialization
- Handle per-flow embedding models with independent vector stores

**Implementation Location**: `trustgraph-flow/trustgraph/extract/kg/ontology/ontology_embedder.py`

#### 3. Text Processor (Sentence Splitter)

**Purpose**: Decomposes text chunks into fine-grained segments for precise ontology matching.

**Implementation**:
The Text Processor uses NLTK for sentence tokenization and POS tagging to break down incoming text chunks into sentences. It handles NLTK version compatibility by attempting to download `punkt_tab` and `averaged_perceptron_tagger_eng` with fallbacks to older versions if needed. Each text chunk is split into individual sentences that can be independently matched against ontology elements.

**Key Operations**:
- Split text into sentences using NLTK sentence tokenization
- Handle NLTK version compatibility (punkt_tab vs punkt)
- Create TextSegment objects with text and position information
- Support both complete sentences and individual chunks

**Implementation Location**: `trustgraph-flow/trustgraph/extract/kg/ontology/text_processor.py`

#### 4. Ontology Selector

**Purpose**: Identifies the most relevant subset of ontology elements for the current text chunk.

**Implementation**:
The Ontology Selector performs semantic matching between text segments and ontology elements using FAISS vector similarity search. For each sentence from the text chunk, it generates an embedding and searches the vector store for the most similar ontology elements using cosine similarity with a configurable threshold (default 0.3). After collecting all relevant elements, it performs comprehensive dependency resolution: if a class is selected, its parent classes are included; if a property is selected, its domain and range classes are added. Additionally, for each selected class, it automatically includes **all properties that reference that class** in their domain or range. This ensures the extraction has access to all relevant relationship properties.

**Key Operations**:
- Generate embeddings for each text segment (sentences)
- Perform k-nearest neighbor search in FAISS vector store (top_k=10, threshold=0.3)
- Apply similarity threshold to filter weak matches
- Resolve dependencies (parent classes, domains, ranges)
- **Auto-include all properties related to selected classes** (domain/range matching)
- Construct coherent ontology subset with all required relationships
- Deduplicate elements appearing multiple times

**Implementation Location**: `trustgraph-flow/trustgraph/extract/kg/ontology/ontology_selector.py`

#### 5. Prompt Construction

**Purpose**: Creates structured prompts that guide the LLM to extract only ontology-conformant triples.

**Implementation**:
The extraction service uses a Jinja2 template loaded from `ontology-prompt.md` which formats the ontology subset and text for LLM extraction. The template dynamically iterates over classes, object properties, and datatype properties using Jinja2 syntax, presenting each with their descriptions, domains, ranges, and hierarchical relationships. The prompt includes strict rules about using only the provided ontology elements and requests JSON output format for consistent parsing.

**Key Operations**:
- Use Jinja2 template with loops over ontology elements
- Format classes with parent relationships (subclass_of) and comments
- Format properties with domain/range constraints and comments
- Include explicit extraction rules and output format requirements
- Call prompt service with template ID "extract-with-ontologies"

**Template Location**: `ontology-prompt.md`
**Implementation Location**: `trustgraph-flow/trustgraph/extract/kg/ontology/extract.py` (build_extraction_variables method)

#### 6. Main Extractor Service

**Purpose**: Coordinates all components to perform end-to-end ontology-based triple extraction.

**Implementation**:
The Main Extractor Service (KgExtractOntology) is the orchestration layer that manages the complete extraction workflow. It uses TrustGraph's FlowProcessor pattern with per-flow component initialization. When an ontology configuration update arrives, it initializes or updates the flow-specific components (ontology loader, embedder, text processor, selector). When a text chunk arrives for processing, it coordinates the pipeline: splitting the text into segments, finding relevant ontology elements through vector search, constructing a constrained prompt, calling the prompt service, parsing and validating the response, generating ontology definition triples, and emitting both content triples and entity contexts.

**Extraction Pipeline**:
1. Receive text chunk via chunks-input queue
2. Initialize flow components if needed (on first chunk or config update)
3. Split text into sentences using NLTK
4. Search FAISS vector store to find relevant ontology concepts
5. Build ontology subset with automatic property inclusion
6. Construct Jinja2-templated prompt variables
7. Call prompt service with extract-with-ontologies template
8. Parse JSON response into structured triples
9. Validate triples and expand URIs to full ontology URIs
10. Generate ontology definition triples (classes and properties with labels/comments/domains/ranges)
11. Build entity contexts from all triples
12. Emit to triples and entity-contexts queues

**Key Features**:
- Per-flow vector stores supporting different embedding models
- Event-driven ontology updates via config-update queue
- Automatic URI expansion using ontology URIs
- Ontology elements added to knowledge graph with full metadata
- Entity contexts include both content and ontology elements

**Implementation Location**: `trustgraph-flow/trustgraph/extract/kg/ontology/extract.py`

### Configuration

The service uses TrustGraph's standard configuration approach with command-line arguments:

```bash
kg-extract-ontology \
  --id kg-extract-ontology \
  --pulsar-host localhost:6650 \
  --input-queue chunks \
  --config-input-queue config-update \
  --output-queue triples \
  --entity-contexts-output-queue entity-contexts
```

**Key Configuration Parameters**:
- `similarity_threshold`: 0.3 (default, configurable in code)
- `top_k`: 10 (number of ontology elements to retrieve per segment)
- `vector_store`: Per-flow FAISS IndexFlatIP with auto-detected dimensions
- `text_processor`: NLTK with punkt_tab sentence tokenization
- `prompt_template`: "extract-with-ontologies" (Jinja2 template)

**Ontology Configuration**:
Ontologies are loaded dynamically via the config-update queue with type="ontology".

### Data Flow

1. **Initialisation Phase** (per flow):
   - Receive ontology configuration via config-update queue
   - Parse ontology JSON into OntologyClass and OntologyProperty objects
   - Generate embeddings for all ontology elements using EmbeddingsClientSpec
   - Store embeddings in per-flow FAISS vector store
   - Auto-detect embedding dimensions from first response

2. **Extraction Phase** (per chunk):
   - Receive chunk from chunks-input queue
   - Split chunk into sentences using NLTK
   - Compute embeddings for each sentence
   - Search FAISS vector store for relevant ontology elements
   - Build ontology subset with automatic property inclusion
   - Construct Jinja2 template variables with text and ontology
   - Call prompt service with extract-with-ontologies template
   - Parse JSON response and validate triples
   - Expand URIs using ontology URIs
   - Generate ontology definition triples
   - Build entity contexts from all triples
   - Emit to triples and entity-contexts queues

### In-Memory Vector Store

**Purpose**: Provides fast, memory-based similarity search for ontology element matching.

**Implementation: FAISS**

The system uses **FAISS (Facebook AI Similarity Search)** with IndexFlatIP for exact cosine similarity search. Key features:

- **IndexFlatIP**: Exact cosine similarity search using inner product
- **Auto-detection**: Dimension determined from first embedding response
- **Per-flow stores**: Each flow has independent vector store for different embedding models
- **Normalization**: All vectors normalized before indexing
- **Batch operations**: Efficient batch add for initial ontology loading

**Implementation Location**: `trustgraph-flow/trustgraph/extract/kg/ontology/vector_store.py`

### Ontology Subset Selection Algorithm

**Purpose**: Dynamically selects the minimal relevant portion of the ontology for each text chunk.

**Detailed Algorithm Steps**:

1. **Text Segmentation**:
   - Split the input chunk into sentences using NLP sentence detection
   - Extract noun phrases, verb phrases, and named entities from each sentence
   - Create a hierarchical structure of segments preserving context

2. **Embedding Generation**:
   - Generate vector embeddings for each text segment (sentences and phrases)
   - Use the same embedding model as used for ontology elements
   - Cache embeddings for repeated segments to improve performance

3. **Similarity Search**:
   - For each text segment embedding, search the vector store
   - Retrieve top-k (e.g., 10) most similar ontology elements
   - Apply similarity threshold (e.g., 0.7) to filter weak matches
   - Aggregate results across all segments, tracking match frequencies

4. **Dependency Resolution**:
   - For each selected class, recursively include all parent classes up to root
   - For each selected property, include its domain and range classes
   - For inverse properties, ensure both directions are included
   - Add equivalent classes if they exist in the ontology

5. **Subset Construction**:
   - Deduplicate collected elements while preserving relationships
   - Organise into classes, object properties, and datatype properties
   - Ensure all constraints and relationships are preserved
   - Create a self-contained mini-ontology that is valid and complete

**Example Walkthrough**:
Given text: "The brown dog chased the white cat up the tree."
- Segments: ["brown dog", "white cat", "tree", "chased"]
- Matched elements: [dog (class), cat (class), animal (parent), chases (property)]
- Dependencies: [animal (parent of dog and cat), lifeform (parent of animal)]
- Final subset: Complete mini-ontology with animal hierarchy and chase relationship

### Triple Validation

**Purpose**: Ensures all extracted triples strictly conform to ontology constraints.

**Validation Algorithm**:

1. **Class Validation**:
   - Verify that subjects are instances of classes defined in the ontology subset
   - For object properties, verify that objects are also valid class instances
   - Check class names against the ontology's class dictionary
   - Handle class hierarchies - instances of subclasses are valid for parent class constraints

2. **Property Validation**:
   - Confirm predicates correspond to properties in the ontology subset
   - Distinguish between object properties (entity-to-entity) and datatype properties (entity-to-literal)
   - Verify property names match exactly (considering namespace if present)

3. **Domain/Range Checking**:
   - For each property used as predicate, retrieve its domain and range
   - Verify the subject's type matches or inherits from the property's domain
   - Verify the object's type matches or inherits from the property's range
   - For datatype properties, verify the object is a literal of the correct XSD type

4. **Cardinality Validation**:
   - Track property usage counts per subject
   - Check minimum cardinality - ensure required properties are present
   - Check maximum cardinality - ensure property isn't used too many times
   - For functional properties, ensure at most one value per subject

5. **Datatype Validation**:
   - Parse literal values according to their declared XSD types
   - Validate integers are valid numbers, dates are properly formatted, etc.
   - Check string patterns if regex constraints are defined
   - Ensure URIs are well-formed for xsd:anyURI types

**Validation Example**:
Triple: ("Buddy", "has-owner", "John")
- Check "Buddy" is typed as a class that can have "has-owner" property
- Check "has-owner" exists in the ontology
- Verify domain constraint: subject must be of type "Pet" or subclass
- Verify range constraint: object must be of type "Person" or subclass
- If valid, add to output; if invalid, log violation and skip

## Performance Considerations

### Optimisation Strategies

1. **Embedding Caching**: Cache embeddings for frequently used text segments
2. **Batch Processing**: Process multiple segments in parallel
3. **Vector Store Indexing**: Use approximate nearest neighbor algorithms for large ontologies
4. **Prompt Optimisation**: Minimise prompt size by including only essential ontology elements
5. **Result Caching**: Cache extraction results for identical chunks

### Scalability

- **Horizontal Scaling**: Multiple extractor instances with shared ontology cache
- **Ontology Partitioning**: Split large ontologies by domain
- **Streaming Processing**: Process chunks as they arrive without batching
- **Memory Management**: Periodic cleanup of unused embeddings

## Error Handling

### Failure Scenarios

1. **Missing Ontologies**: Fallback to unconstrained extraction
2. **Embedding Service Failure**: Use cached embeddings or skip semantic matching
3. **Prompt Service Timeout**: Retry with exponential backoff
4. **Invalid Triple Format**: Log and skip malformed triples
5. **Ontology Inconsistencies**: Report conflicts and use most specific valid elements

### Monitoring

Key metrics to track:

- Ontology load time and memory usage
- Embedding generation latency
- Vector search performance
- Prompt service response time
- Triple extraction accuracy
- Ontology conformance rate

## Migration Path

### From Existing Extractors

1. **Parallel Operation**: Run alongside existing extractors initially
2. **Gradual Rollout**: Start with specific document types
3. **Quality Comparison**: Compare output quality with existing extractors
4. **Full Migration**: Replace existing extractors once quality verified

### Ontology Development

1. **Bootstrap from Existing**: Generate initial ontologies from existing knowledge
2. **Iterative Refinement**: Refine based on extraction patterns
3. **Domain Expert Review**: Validate with subject matter experts
4. **Continuous Improvement**: Update based on extraction feedback

## Ontology-Sensitive Query Service

### Overview

The ontology-sensitive query service provides multiple query paths to support different backend graph stores. It leverages ontology knowledge for precise, semantically-aware question answering across both Cassandra (via SPARQL) and Cypher-based graph stores (Neo4j, Memgraph, FalkorDB).

**Service Components**:
- `onto-query-sparql`: Converts natural language to SPARQL for Cassandra
- `sparql-cassandra`: SPARQL query layer for Cassandra using rdflib
- `onto-query-cypher`: Converts natural language to Cypher for graph databases
- `cypher-executor`: Cypher query execution for Neo4j/Memgraph/FalkorDB

### Architecture

```
                    ┌─────────────────┐
                    │   User Query    │
                    └────────┬────────┘
                             │
                             ▼
                    ┌─────────────────┐      ┌──────────────┐
                    │   Question      │────▶│   Sentence   │
                    │   Analyser      │      │   Splitter   │
                    └────────┬────────┘      └──────────────┘
                             │
                             ▼
                    ┌─────────────────┐      ┌──────────────┐
                    │   Ontology      │────▶│   Vector     │
                    │   Matcher       │      │    Store     │
                    └────────┬────────┘      └──────────────┘
                             │
                             ▼
                    ┌─────────────────┐
                    │ Backend Router  │
                    └────────┬────────┘
                             │
                 ┌───────────┴───────────┐
                 │                       │
                 ▼                       ▼
    ┌─────────────────┐          ┌─────────────────┐
    │ onto-query-     │          │ onto-query-     │
    │    sparql       │          │    cypher       │
    └────────┬────────┘          └────────┬────────┘
             │                            │
             ▼                            ▼
    ┌─────────────────┐          ┌─────────────────┐
    │   SPARQL        │          │   Cypher        │
    │  Generator      │          │  Generator      │
    └────────┬────────┘          └────────┬────────┘
             │                            │
             ▼                            ▼
    ┌─────────────────┐          ┌─────────────────┐
    │ sparql-         │          │ cypher-         │
    │ cassandra       │          │ executor        │
    └────────┬────────┘          └────────┬────────┘
             │                            │
             ▼                            ▼
    ┌─────────────────┐          ┌─────────────────┐
    │   Cassandra     │          │ Neo4j/Memgraph/ │
    │                 │          │   FalkorDB      │
    └────────┬────────┘          └────────┬────────┘
             │                            │
             └────────────┬───────────────┘
                          │
                          ▼
                 ┌─────────────────┐      ┌──────────────┐
                 │   Answer        │────▶│   Prompt     │
                 │  Generator      │      │   Service    │
                 └────────┬────────┘      └──────────────┘
                          │
                          ▼
                 ┌─────────────────┐
                 │  Final Answer   │
                 └─────────────────┘
```

### Query Processing Pipeline

#### 1. Question Analyser

**Purpose**: Decomposes user questions into semantic components for ontology matching.

**Algorithm Description**:
The Question Analyser takes the incoming natural language question and breaks it down into meaningful segments using the same sentence splitting approach as the extraction pipeline. It identifies key entities, relationships, and constraints mentioned in the question. Each segment is analysed for question type (factual, aggregation, comparison, etc.) and the expected answer format. This decomposition helps identify which parts of the ontology are most relevant for answering the question.

**Key Operations**:
- Split question into sentences and phrases
- Identify question type and intent
- Extract mentioned entities and relationships
- Detect constraints and filters in the question
- Determine expected answer format

#### 2. Ontology Matcher for Queries

**Purpose**: Identifies the relevant ontology subset needed to answer the question.

**Algorithm Description**:
Similar to the extraction pipeline's Ontology Selector, but optimised for question answering. The matcher generates embeddings for question segments and searches the vector store for relevant ontology elements. However, it focuses on finding concepts that would be useful for query construction rather than extraction. It expands the selection to include related properties that might be traversed during graph exploration, even if not explicitly mentioned in the question. For example, if asked about "employees," it might include properties like "works-for," "manages," and "reports-to" that could be relevant for finding employee information.

**Matching Strategy**:
- Embed question segments
- Find directly mentioned ontology concepts
- Include properties that connect mentioned classes
- Add inverse and related properties for traversal
- Include parent/child classes for hierarchical queries
- Build query-focused ontology partition

#### 3. Backend Router

**Purpose**: Routes queries to the appropriate backend-specific query path based on configuration.

**Algorithm Description**:
The Backend Router examines the system configuration to determine which graph backend is active (Cassandra or Cypher-based). It routes the question and ontology partition to the appropriate query generation service. The router can also support load balancing across multiple backends or fallback mechanisms if the primary backend is unavailable.

**Routing Logic**:
- Check configured backend type from system settings
- Route to `onto-query-sparql` for Cassandra backends
- Route to `onto-query-cypher` for Neo4j/Memgraph/FalkorDB
- Support multi-backend configurations with query distribution
- Handle failover and load balancing scenarios

#### 4. SPARQL Query Generation (`onto-query-sparql`)

**Purpose**: Converts natural language questions to SPARQL queries for Cassandra execution.

**Algorithm Description**:
The SPARQL query generator takes the question and ontology partition and constructs a SPARQL query optimised for execution against the Cassandra backend. It uses the prompt service with a SPARQL-specific template that includes RDF/OWL semantics. The generator understands SPARQL patterns like property paths, optional clauses, and filters that can efficiently translate to Cassandra operations.

**SPARQL Generation Prompt Template**:
```
Generate a SPARQL query for the following question using the provided ontology.

ONTOLOGY CLASSES:
{classes}

ONTOLOGY PROPERTIES:
{properties}

RULES:
- Use proper RDF/OWL semantics
- Include relevant prefixes
- Use property paths for hierarchical queries
- Add FILTER clauses for constraints
- Optimise for Cassandra backend

QUESTION: {question}

SPARQL QUERY:
```

#### 5. Cypher Query Generation (`onto-query-cypher`)

**Purpose**: Converts natural language questions to Cypher queries for graph databases.

**Algorithm Description**:
The Cypher query generator creates native Cypher queries optimised for Neo4j, Memgraph, and FalkorDB. It maps ontology classes to node labels and properties to relationships, using Cypher's pattern matching syntax. The generator includes Cypher-specific optimisations like relationship direction hints, index usage, and query planning hints.

**Cypher Generation Prompt Template**:
```
Generate a Cypher query for the following question using the provided ontology.

NODE LABELS (from classes):
{classes}

RELATIONSHIP TYPES (from properties):
{properties}

RULES:
- Use MATCH patterns for graph traversal
- Include WHERE clauses for filters
- Use aggregation functions when needed
- Optimise for graph database performance
- Consider index hints for large datasets

QUESTION: {question}

CYPHER QUERY:
```

#### 6. SPARQL-Cassandra Query Engine (`sparql-cassandra`)

**Purpose**: Executes SPARQL queries against Cassandra using Python rdflib.

**Algorithm Description**:
The SPARQL-Cassandra engine implements a SPARQL processor using Python's rdflib library with a custom Cassandra backend store. It translates SPARQL graph patterns into appropriate Cassandra CQL queries, handling joins, filters, and aggregations. The engine maintains an RDF-to-Cassandra mapping that preserves the semantic structure while optimising for Cassandra's column-family storage model.

**Implementation Features**:
- rdflib Store interface implementation for Cassandra
- SPARQL 1.1 query support with common patterns
- Efficient translation of triple patterns to CQL
- Support for property paths and hierarchical queries
- Result streaming for large datasets
- Connection pooling and query caching

**Example Translation**:
```sparql
SELECT ?animal WHERE {
  ?animal rdf:type :Animal .
  ?animal :hasOwner "John" .
}
```
Translates to optimised Cassandra queries leveraging indexes and partition keys.

#### 7. Cypher Query Executor (`cypher-executor`)

**Purpose**: Executes Cypher queries against Neo4j, Memgraph, and FalkorDB.

**Algorithm Description**:
The Cypher executor provides a unified interface for executing Cypher queries across different graph databases. It handles database-specific connection protocols, query optimisation hints, and result format normalisation. The executor includes retry logic, connection pooling, and transaction management appropriate for each database type.

**Multi-Database Support**:
- **Neo4j**: Bolt protocol, transaction functions, index hints
- **Memgraph**: Custom protocol, streaming results, analytical queries
- **FalkorDB**: Redis protocol adaptation, in-memory optimisations

**Execution Features**:
- Database-agnostic connection management
- Query validation and syntax checking
- Timeout and resource limit enforcement
- Result pagination and streaming
- Performance monitoring per database type
- Automatic failover between database instances

#### 8. Answer Generator

**Purpose**: Synthesises a natural language answer from query results.

**Algorithm Description**:
The Answer Generator takes the structured query results and the original question, then uses the prompt service to generate a comprehensive answer. Unlike simple template-based responses, it uses an LLM to interpret the graph data in the context of the question, handling complex relationships, aggregations, and inferences. The generator can explain its reasoning by referencing the ontology structure and the specific triples retrieved from the graph.

**Answer Generation Process**:
- Format query results into structured context
- Include relevant ontology definitions for clarity
- Construct prompt with question and results
- Generate natural language answer via LLM
- Validate answer against query intent
- Add citations to specific graph entities if needed

### Integration with Existing Services

#### Relationship with GraphRAG

- **Complementary**: onto-query provides semantic precision while GraphRAG provides broad coverage
- **Shared Infrastructure**: Both use the same knowledge graph and prompt services
- **Query Routing**: System can route queries to most appropriate service based on question type
- **Hybrid Mode**: Can combine both approaches for comprehensive answers

#### Relationship with OntoRAG Extraction

- **Shared Ontologies**: Uses same ontology configurations loaded by kg-extract-ontology
- **Shared Vector Store**: Reuses the in-memory embeddings from extraction service
- **Consistent Semantics**: Queries operate on graphs built with same ontological constraints

### Query Examples

#### Example 1: Simple Entity Query
**Question**: "What animals are mammals?"
**Ontology Match**: [animal, mammal, subClassOf]
**Generated Query**:
```cypher
MATCH (a:animal)-[:subClassOf*]->(m:mammal)
RETURN a.name
```

#### Example 2: Relationship Query
**Question**: "Which documents were authored by John Smith?"
**Ontology Match**: [document, person, has-author]
**Generated Query**:
```cypher
MATCH (d:document)-[:has-author]->(p:person {name: "John Smith"})
RETURN d.title, d.date
```

#### Example 3: Aggregation Query
**Question**: "How many legs do cats have?"
**Ontology Match**: [cat, number-of-legs (datatype property)]
**Generated Query**:
```cypher
MATCH (c:cat)
RETURN c.name, c.number_of_legs
```

### Configuration

```yaml
onto-query:
  embedding_model: "text-embedding-3-small"
  vector_store:
    shared_with_extractor: true  # Reuse kg-extract-ontology's store
  query_builder:
    model: "gpt-4"
    temperature: 0.1
    max_query_length: 1000
  graph_executor:
    timeout: 30000  # ms
    max_results: 1000
  answer_generator:
    model: "gpt-4"
    temperature: 0.3
    max_tokens: 500
```

### Performance Optimisations

#### Query Optimisation

- **Ontology Pruning**: Only include necessary ontology elements in prompts
- **Query Caching**: Cache frequently asked questions and their queries
- **Result Caching**: Store results for identical queries within time window
- **Batch Processing**: Handle multiple related questions in single graph traversal

#### Scalability Considerations

- **Distributed Execution**: Parallelise subqueries across graph partitions
- **Incremental Results**: Stream results for large datasets
- **Load Balancing**: Distribute query load across multiple service instances
- **Resource Pools**: Manage connection pools to graph databases

### Error Handling

#### Failure Scenarios

1. **Invalid Query Generation**: Fallback to GraphRAG or simple keyword search
2. **Ontology Mismatch**: Expand search to broader ontology subset
3. **Query Timeout**: Simplify query or increase timeout
4. **Empty Results**: Suggest query reformulation or related questions
5. **LLM Service Failure**: Use cached queries or template-based responses

### Monitoring Metrics

- Question complexity distribution
- Ontology partition sizes
- Query generation success rate
- Graph query execution time
- Answer quality scores
- Cache hit rates
- Error frequencies by type

## Future Enhancements

1. **Ontology Learning**: Automatically extend ontologies based on extraction patterns
2. **Confidence Scoring**: Assign confidence scores to extracted triples
3. **Explanation Generation**: Provide reasoning for triple extraction
4. **Active Learning**: Request human validation for uncertain extractions

## Security Considerations

1. **Prompt Injection Prevention**: Sanitise chunk text before prompt construction
2. **Resource Limits**: Cap memory usage for vector store
3. **Rate Limiting**: Limit extraction requests per client
4. **Audit Logging**: Track all extraction requests and results

## Testing Strategy

### Unit Testing

- Ontology loader with various formats
- Embedding generation and storage
- Sentence splitting algorithms
- Vector similarity calculations
- Triple parsing and validation

### Integration Testing

- End-to-end extraction pipeline
- Configuration service integration
- Prompt service interaction
- Concurrent extraction handling

### Performance Testing

- Large ontology handling (1000+ classes)
- High-volume chunk processing
- Memory usage under load
- Latency benchmarks

## Delivery Plan

### Overview

The OntoRAG system will be delivered in four major phases, with each phase providing incremental value while building toward the complete system. The plan focuses on establishing core extraction capabilities first, then adding query functionality, followed by optimizations and advanced features.

### Phase 1: Foundation and Core Extraction

**Goal**: Establish the basic ontology-driven extraction pipeline with simple vector matching.

#### Step 1.1: Ontology Management Foundation
- Implement ontology configuration loader (`OntologyLoader`)
- Parse and validate ontology JSON structures
- Create in-memory ontology storage and access patterns
- Implement ontology refresh mechanism

**Success Criteria**:
- Successfully load and parse ontology configurations
- Validate ontology structure and consistency
- Handle multiple concurrent ontologies

#### Step 1.2: Vector Store Implementation
- Implement simple NumPy-based vector store as initial prototype
- Add FAISS vector store implementation
- Create vector store interface abstraction
- Implement similarity search with configurable thresholds

**Success Criteria**:
- Store and retrieve embeddings efficiently
- Perform similarity search with <100ms latency
- Support both NumPy and FAISS backends

#### Step 1.3: Ontology Embedding Pipeline
- Integrate with embedding service
- Implement `OntologyEmbedder` component
- Generate embeddings for all ontology elements
- Store embeddings with metadata in vector store

**Success Criteria**:
- Generate embeddings for classes and properties
- Store embeddings with proper metadata
- Rebuild embeddings on ontology updates

#### Step 1.4: Text Processing Components
- Implement sentence splitter using NLTK/spaCy
- Extract phrases and named entities
- Create text segment hierarchy
- Generate embeddings for text segments

**Success Criteria**:
- Accurately split text into sentences
- Extract meaningful phrases
- Maintain context relationships

#### Step 1.5: Ontology Selection Algorithm
- Implement similarity matching between text and ontology
- Build dependency resolution for ontology elements
- Create minimal coherent ontology subsets
- Optimize subset generation performance

**Success Criteria**:
- Select relevant ontology elements with >80% precision
- Include all necessary dependencies
- Generate subsets in <500ms

#### Step 1.6: Basic Extraction Service
- Implement prompt construction for extraction
- Integrate with prompt service
- Parse and validate triple responses
- Create `kg-extract-ontology` service endpoint

**Success Criteria**:
- Extract ontology-conformant triples
- Validate all triples against ontology
- Handle extraction errors gracefully

### Phase 2: Query System Implementation

**Goal**: Add ontology-aware query capabilities with support for multiple backends.

#### Step 2.1: Query Foundation Components
- Implement question analyzer
- Create ontology matcher for queries
- Adapt vector search for query context
- Build backend router component

**Success Criteria**:
- Analyze questions into semantic components
- Match questions to relevant ontology elements
- Route queries to appropriate backend

#### Step 2.2: SPARQL Path Implementation
- Implement `onto-query-sparql` service
- Create SPARQL query generator using LLM
- Develop prompt templates for SPARQL generation
- Validate generated SPARQL syntax

**Success Criteria**:
- Generate valid SPARQL queries
- Use appropriate SPARQL patterns
- Handle complex query types

#### Step 2.3: SPARQL-Cassandra Engine
- Implement rdflib Store interface for Cassandra
- Create CQL query translator
- Optimize triple pattern matching
- Handle SPARQL result formatting

**Success Criteria**:
- Execute SPARQL queries on Cassandra
- Support common SPARQL patterns
- Return results in standard format

#### Step 2.4: Cypher Path Implementation
- Implement `onto-query-cypher` service
- Create Cypher query generator using LLM
- Develop prompt templates for Cypher generation
- Validate generated Cypher syntax

**Success Criteria**:
- Generate valid Cypher queries
- Use appropriate graph patterns
- Support Neo4j, Memgraph, FalkorDB

#### Step 2.5: Cypher Executor
- Implement multi-database Cypher executor
- Support Bolt protocol (Neo4j/Memgraph)
- Support Redis protocol (FalkorDB)
- Handle result normalization

**Success Criteria**:
- Execute Cypher on all target databases
- Handle database-specific differences
- Maintain connection pools efficiently

#### Step 2.6: Answer Generation
- Implement answer generator component
- Create prompts for answer synthesis
- Format query results for LLM consumption
- Generate natural language answers

**Success Criteria**:
- Generate accurate answers from query results
- Maintain context from original question
- Provide clear, concise responses

### Phase 3: Optimization and Robustness

**Goal**: Optimize performance, add caching, improve error handling, and enhance reliability.

#### Step 3.1: Performance Optimization
- Implement embedding caching
- Add query result caching
- Optimize vector search with FAISS IVF indexes
- Implement batch processing for embeddings

**Success Criteria**:
- Reduce average query latency by 50%
- Support 10x more concurrent requests
- Maintain sub-second response times

#### Step 3.2: Advanced Error Handling
- Implement comprehensive error recovery
- Add fallback mechanisms between query paths
- Create retry logic with exponential backoff
- Improve error logging and diagnostics

**Success Criteria**:
- Gracefully handle all failure scenarios
- Automatic failover between backends
- Detailed error reporting for debugging

#### Step 3.3: Monitoring and Observability
- Add performance metrics collection
- Implement query tracing
- Create health check endpoints
- Add resource usage monitoring

**Success Criteria**:
- Track all key performance indicators
- Identify bottlenecks quickly
- Monitor system health in real-time

#### Step 3.4: Configuration Management
- Implement dynamic configuration updates
- Add configuration validation
- Create configuration templates
- Support environment-specific settings

**Success Criteria**:
- Update configuration without restart
- Validate all configuration changes
- Support multiple deployment environments

### Phase 4: Advanced Features

**Goal**: Add sophisticated capabilities for production deployment and enhanced functionality.

#### Step 4.1: Multi-Ontology Support
- Implement ontology selection logic
- Support cross-ontology queries
- Handle ontology versioning
- Create ontology merge capabilities

**Success Criteria**:
- Query across multiple ontologies
- Handle ontology conflicts
- Support ontology evolution

#### Step 4.2: Intelligent Query Routing
- Implement performance-based routing
- Add query complexity analysis
- Create adaptive routing algorithms
- Support A/B testing for paths

**Success Criteria**:
- Route queries optimally
- Learn from query performance
- Improve routing over time

#### Step 4.3: Advanced Extraction Features
- Add confidence scoring for triples
- Implement explanation generation
- Create feedback loops for improvement
- Support incremental learning

**Success Criteria**:
- Provide confidence scores
- Explain extraction decisions
- Continuously improve accuracy

#### Step 4.4: Production Hardening
- Add rate limiting
- Implement authentication/authorization
- Create deployment automation
- Add backup and recovery

**Success Criteria**:
- Production-ready security
- Automated deployment pipeline
- Disaster recovery capability

### Delivery Milestones

1. **Milestone 1** (End of Phase 1): Basic ontology-driven extraction operational
2. **Milestone 2** (End of Phase 2): Full query system with both SPARQL and Cypher paths
3. **Milestone 3** (End of Phase 3): Optimized, robust system ready for staging
4. **Milestone 4** (End of Phase 4): Production-ready system with advanced features

### Risk Mitigation

#### Technical Risks
- **Vector Store Scalability**: Start with NumPy, migrate to FAISS gradually
- **Query Generation Accuracy**: Implement validation and fallback mechanisms
- **Backend Compatibility**: Test extensively with each database type
- **Performance Bottlenecks**: Profile early and often, optimize iteratively

#### Operational Risks
- **Ontology Quality**: Implement validation and consistency checking
- **Service Dependencies**: Add circuit breakers and fallbacks
- **Resource Constraints**: Monitor and set appropriate limits
- **Data Consistency**: Implement proper transaction handling

### Success Metrics

#### Phase 1 Success Metrics
- Extraction accuracy: >90% ontology conformance
- Processing speed: <1 second per chunk
- Ontology load time: <10 seconds
- Vector search latency: <100ms

#### Phase 2 Success Metrics
- Query success rate: >95%
- Query latency: <2 seconds end-to-end
- Backend compatibility: 100% for target databases
- Answer accuracy: >85% based on available data

#### Phase 3 Success Metrics
- System uptime: >99.9%
- Error recovery rate: >95%
- Cache hit rate: >60%
- Concurrent users: >100

#### Phase 4 Success Metrics
- Multi-ontology queries: Fully supported
- Routing optimization: 30% latency reduction
- Confidence scoring accuracy: >90%
- Production deployment: Zero-downtime updates

## References

- [OWL 2 Web Ontology Language](https://www.w3.org/TR/owl2-overview/)
- [GraphRAG Architecture](https://github.com/microsoft/graphrag)
- [Sentence Transformers](https://www.sbert.net/)
- [FAISS Vector Search](https://github.com/facebookresearch/faiss)
- [spaCy NLP Library](https://spacy.io/)
- [rdflib Documentation](https://rdflib.readthedocs.io/)
- [Neo4j Bolt Protocol](https://neo4j.com/docs/bolt/current/)
