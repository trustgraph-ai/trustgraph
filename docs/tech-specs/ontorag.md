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
┌─────────────────┐     ┌──────────────┐
│ kg-extract-     │────▶│  Embedding   │
│   ontology      │     │   Service    │
└────────┬────────┘     └──────────────┘
         │                      │
         ▼                      ▼
┌─────────────────┐     ┌──────────────┐
│   In-Memory     │◀────│   Ontology   │
│  Vector Store   │     │   Embedder   │
└────────┬────────┘     └──────────────┘
         │
         ▼
┌─────────────────┐     ┌──────────────┐
│    Sentence     │────▶│   Chunker    │
│    Splitter     │     │   Service    │
└────────┬────────┘     └──────────────┘
         │
         ▼
┌─────────────────┐     ┌──────────────┐
│    Ontology     │────▶│   Vector     │
│    Selector     │     │   Search     │
└────────┬────────┘     └──────────────┘
         │
         ▼
┌─────────────────┐     ┌──────────────┐
│    Prompt       │────▶│   Prompt     │
│   Constructor   │     │   Service    │
└────────┬────────┘     └──────────────┘
         │
         ▼
┌─────────────────┐
│  Triple Output  │
└─────────────────┘
```

### Component Details

#### 1. Ontology Loader

**Purpose**: Retrieves and parses ontology configurations from the configuration service at service startup.

**Algorithm Description**:
The Ontology Loader connects to the configuration service and requests all configuration items of type "ontology". For each ontology configuration found, it parses the JSON structure containing metadata, classes, object properties, and datatype properties. These parsed ontologies are stored in memory as structured objects that can be efficiently accessed during the extraction process. The loader runs once during service initialisation and can optionally refresh ontologies at configured intervals to pick up updates.

**Key Operations**:
- Query configuration service for all ontology-type configurations
- Parse JSON ontology structures into internal object models
- Validate ontology structure and consistency
- Cache parsed ontologies in memory for fast access

Loads ontologies from the configuration service during initialisation:

```python
class OntologyLoader:
    def __init__(self, config_service):
        self.config_service = config_service
        self.ontologies = {}

    async def load_ontologies(self):
        # Fetch all ontology configurations
        configs = await self.config_service.get_configs(type="ontology")

        for config_id, ontology_data in configs:
            self.ontologies[config_id] = Ontology(
                metadata=ontology_data['metadata'],
                classes=ontology_data['classes'],
                object_properties=ontology_data['objectProperties'],
                datatype_properties=ontology_data['datatypeProperties']
            )

        return self.ontologies
```

#### 2. Ontology Embedder

**Purpose**: Creates vector embeddings for all ontology elements to enable semantic similarity matching.

**Algorithm Description**:
The Ontology Embedder processes each element in the loaded ontologies (classes, object properties, and datatype properties) and generates vector embeddings using an embedding service. For each element, it combines the element's identifier with its description (from rdfs:comment) to create a text representation. This text is then converted to a high-dimensional vector embedding that captures its semantic meaning. These embeddings are stored in an in-memory vector store along with metadata about the element type, source ontology, and full definition. This preprocessing step happens once at startup, creating a searchable index of all ontology concepts.

**Key Operations**:
- Concatenate element IDs with their descriptions for rich semantic representation
- Generate embeddings via external embedding service (e.g., text-embedding-3-small)
- Store embeddings with comprehensive metadata in vector store
- Index by ontology, element type, and element ID for efficient retrieval

Generates embeddings for ontology elements and stores them in an in-memory vector store:

```python
class OntologyEmbedder:
    def __init__(self, embedding_service, vector_store):
        self.embedding_service = embedding_service
        self.vector_store = vector_store

    async def embed_ontologies(self, ontologies):
        for onto_id, ontology in ontologies.items():
            # Embed classes
            for class_id, class_def in ontology.classes.items():
                text = f"{class_id} {class_def.get('rdfs:comment', '')}"
                embedding = await self.embedding_service.embed(text)

                self.vector_store.add(
                    id=f"{onto_id}:class:{class_id}",
                    embedding=embedding,
                    metadata={
                        'type': 'class',
                        'ontology': onto_id,
                        'element': class_id,
                        'definition': class_def
                    }
                )

            # Embed properties (object and datatype)
            for prop_type in ['objectProperties', 'datatypeProperties']:
                for prop_id, prop_def in getattr(ontology, prop_type).items():
                    text = f"{prop_id} {prop_def.get('rdfs:comment', '')}"
                    embedding = await self.embedding_service.embed(text)

                    self.vector_store.add(
                        id=f"{onto_id}:{prop_type}:{prop_id}",
                        embedding=embedding,
                        metadata={
                            'type': prop_type,
                            'ontology': onto_id,
                            'element': prop_id,
                            'definition': prop_def
                        }
                    )
```

#### 3. Sentence Splitter

**Purpose**: Decomposes text chunks into fine-grained segments for precise ontology matching.

**Algorithm Description**:
The Sentence Splitter takes incoming text chunks and breaks them down into smaller, more manageable units. First, it uses natural language processing techniques (via NLTK or spaCy) to identify sentence boundaries, handling edge cases like abbreviations and decimal points. Then, for each sentence, it extracts meaningful phrases including noun phrases (e.g., "the red car"), verb phrases (e.g., "quickly ran"), and named entities. This multi-level segmentation ensures that both complete thoughts (sentences) and specific concepts (phrases) can be matched against ontology elements. Each segment is tagged with its type and position information to maintain context.

**Key Operations**:
- Split text into sentences using NLP sentence detection
- Extract noun phrases and verb phrases from each sentence
- Identify named entities and key terms
- Maintain hierarchical relationship between sentences and their phrases
- Preserve positional information for context reconstruction

Breaks incoming chunks into smaller sentences and phrases for granular matching:

```python
class SentenceSplitter:
    def __init__(self):
        # Use NLTK or spaCy for sophisticated splitting
        self.sentence_detector = SentenceDetector()
        self.phrase_extractor = PhraseExtractor()

    def split_chunk(self, chunk_text):
        sentences = self.sentence_detector.split(chunk_text)

        segments = []
        for sentence in sentences:
            # Add full sentence
            segments.append({
                'text': sentence,
                'type': 'sentence',
                'position': len(segments)
            })

            # Extract noun phrases and verb phrases
            phrases = self.phrase_extractor.extract(sentence)
            for phrase in phrases:
                segments.append({
                    'text': phrase,
                    'type': 'phrase',
                    'parent_sentence': sentence,
                    'position': len(segments)
                })

        return segments
```

#### 4. Ontology Selector

**Purpose**: Identifies the most relevant subset of ontology elements for the current text chunk.

**Algorithm Description**:
The Ontology Selector performs semantic matching between text segments and ontology elements using vector similarity search. For each sentence and phrase from the text chunk, it generates an embedding and searches the vector store for the most similar ontology elements. The search uses cosine similarity with a configurable threshold (e.g., 0.7) to find semantically related concepts. After collecting all relevant elements, it performs dependency resolution to ensure completeness - if a class is selected, its parent classes are included; if a property is selected, its domain and range classes are added. This creates a minimal but complete ontology subset that contains all necessary elements for valid triple extraction while avoiding irrelevant concepts that could confuse the extraction process.

**Key Operations**:
- Generate embeddings for each text segment (sentences and phrases)
- Perform k-nearest neighbor search in the vector store
- Apply similarity threshold to filter weak matches
- Resolve dependencies (parent classes, domains, ranges)
- Construct coherent ontology subset with all required relationships
- Deduplicate elements appearing multiple times

Uses vector similarity to find relevant ontology elements for each text segment:

```python
class OntologySelector:
    def __init__(self, embedding_service, vector_store):
        self.embedding_service = embedding_service
        self.vector_store = vector_store

    async def select_ontology_subset(self, segments, top_k=10):
        relevant_elements = set()

        for segment in segments:
            # Get embedding for segment
            embedding = await self.embedding_service.embed(segment['text'])

            # Search for similar ontology elements
            results = self.vector_store.search(
                embedding=embedding,
                top_k=top_k,
                threshold=0.7  # Similarity threshold
            )

            for result in results:
                relevant_elements.add((
                    result['metadata']['ontology'],
                    result['metadata']['type'],
                    result['metadata']['element'],
                    result['metadata']['definition']
                ))

        # Build ontology subset
        return self._build_subset(relevant_elements)

    def _build_subset(self, elements):
        # Include selected elements and their dependencies
        # (parent classes, domain/range references, etc.)
        subset = {
            'classes': {},
            'objectProperties': {},
            'datatypeProperties': {}
        }

        for onto_id, elem_type, elem_id, definition in elements:
            if elem_type == 'class':
                subset['classes'][elem_id] = definition
                # Include parent classes
                if 'rdfs:subClassOf' in definition:
                    parent = definition['rdfs:subClassOf']
                    # Recursively add parent from full ontology
            elif elem_type == 'objectProperties':
                subset['objectProperties'][elem_id] = definition
                # Include domain and range classes
            elif elem_type == 'datatypeProperties':
                subset['datatypeProperties'][elem_id] = definition

        return subset
```

#### 5. Prompt Constructor

**Purpose**: Creates structured prompts that guide the LLM to extract only ontology-conformant triples.

**Algorithm Description**:
The Prompt Constructor assembles a carefully formatted prompt that constrains the LLM's extraction to the selected ontology subset. It takes the relevant classes and properties identified by the Ontology Selector and formats them into clear instructions. Classes are presented with their hierarchical relationships and descriptions. Properties are shown with their domain and range constraints, making explicit what types of entities they can connect. The prompt includes strict rules about using only the provided ontology elements and respecting all constraints. The original text chunk is then appended, and the LLM is instructed to extract triples in the format (subject, predicate, object). This structured approach ensures the LLM understands both what to look for and what constraints to respect.

**Key Operations**:
- Format classes with parent relationships and descriptions
- Format properties with domain/range constraints
- Include explicit extraction rules and constraints
- Specify output format for consistent parsing
- Balance prompt size with completeness of ontology information

Builds prompts for the extraction service with ontology constraints:

```python
class PromptConstructor:
    def __init__(self):
        self.template = """
Extract knowledge triples from the following text using ONLY the provided ontology elements.

ONTOLOGY CLASSES:
{classes}

OBJECT PROPERTIES (connect entities):
{object_properties}

DATATYPE PROPERTIES (entity attributes):
{datatype_properties}

RULES:
1. Only use classes defined above for entity types
2. Only use properties defined above for relationships and attributes
3. Respect domain and range constraints
4. Output format: (subject, predicate, object)

TEXT:
{text}

TRIPLES:
"""

    def build_prompt(self, chunk_text, ontology_subset):
        classes_str = self._format_classes(ontology_subset['classes'])
        obj_props_str = self._format_properties(
            ontology_subset['objectProperties'],
            'object'
        )
        dt_props_str = self._format_properties(
            ontology_subset['datatypeProperties'],
            'datatype'
        )

        return self.template.format(
            classes=classes_str,
            object_properties=obj_props_str,
            datatype_properties=dt_props_str,
            text=chunk_text
        )

    def _format_classes(self, classes):
        lines = []
        for class_id, definition in classes.items():
            comment = definition.get('rdfs:comment', '')
            parent = definition.get('rdfs:subClassOf', 'Thing')
            lines.append(f"- {class_id} (subclass of {parent}): {comment}")
        return '\n'.join(lines)

    def _format_properties(self, properties, prop_type):
        lines = []
        for prop_id, definition in properties.items():
            comment = definition.get('rdfs:comment', '')
            domain = definition.get('rdfs:domain', 'Any')
            range_val = definition.get('rdfs:range', 'Any')
            lines.append(f"- {prop_id} ({domain} -> {range_val}): {comment}")
        return '\n'.join(lines)
```

#### 6. Main Extractor Service

**Purpose**: Coordinates all components to perform end-to-end ontology-based triple extraction.

**Algorithm Description**:
The Main Extractor Service is the orchestration layer that manages the complete extraction workflow. During initialisation, it loads all ontologies and pre-computes their embeddings, creating the searchable vector index. When a text chunk arrives for processing, it coordinates the pipeline: first splitting the text into segments, then finding relevant ontology elements through vector search, constructing a constrained prompt, calling the LLM service, and finally parsing and validating the response. The service ensures that each extracted triple conforms to the ontology by validating that subjects and objects are valid class instances, predicates are valid properties, and all domain/range constraints are satisfied. Only validated triples that fully conform to the ontology are returned.

**Extraction Pipeline**:
1. Receive text chunk for processing
2. Split into sentences and phrases for granular analysis
3. Search vector store to find relevant ontology concepts
4. Build ontology subset including dependencies
5. Construct prompt with ontology constraints and text
6. Call LLM service for triple extraction
7. Parse response into structured triples
8. Validate each triple against ontology rules
9. Return only valid, ontology-conformant triples

Orchestrates the complete extraction pipeline:

```python
class KgExtractOntology:
    def __init__(self, config):
        self.loader = OntologyLoader(config['config_service'])
        self.embedder = OntologyEmbedder(
            config['embedding_service'],
            InMemoryVectorStore()
        )
        self.splitter = SentenceSplitter()
        self.selector = OntologySelector(
            config['embedding_service'],
            self.embedder.vector_store
        )
        self.prompt_builder = PromptConstructor()
        self.prompt_service = config['prompt_service']

    async def initialize(self):
        # Load and embed ontologies at startup
        ontologies = await self.loader.load_ontologies()
        await self.embedder.embed_ontologies(ontologies)

    async def extract(self, chunk):
        # Split chunk into segments
        segments = self.splitter.split_chunk(chunk['text'])

        # Select relevant ontology subset
        ontology_subset = await self.selector.select_ontology_subset(segments)

        # Build extraction prompt
        prompt = self.prompt_builder.build_prompt(
            chunk['text'],
            ontology_subset
        )

        # Call prompt service
        response = await self.prompt_service.generate(prompt)

        # Parse and validate triples
        triples = self.parse_triples(response)
        validated_triples = self.validate_triples(triples, ontology_subset)

        return validated_triples

    def parse_triples(self, response):
        # Parse LLM response into structured triples
        triples = []
        for line in response.split('\n'):
            if line.strip().startswith('(') and line.strip().endswith(')'):
                # Parse (subject, predicate, object)
                parts = line.strip()[1:-1].split(',')
                if len(parts) == 3:
                    triples.append({
                        'subject': parts[0].strip(),
                        'predicate': parts[1].strip(),
                        'object': parts[2].strip()
                    })
        return triples

    def validate_triples(self, triples, ontology_subset):
        # Validate against ontology constraints
        validated = []
        for triple in triples:
            if self._is_valid(triple, ontology_subset):
                validated.append(triple)
        return validated
```

### Configuration

The service loads configuration on startup:

```yaml
kg-extract-ontology:
  embedding_model: "text-embedding-3-small"
  vector_store:
    type: "in-memory"
    similarity_threshold: 0.7
    top_k: 10
  sentence_splitter:
    model: "nltk"
    max_sentence_length: 512
  prompt_service:
    endpoint: "http://prompt-service:8080"
    model: "gpt-4"
    temperature: 0.1
  ontology_refresh_interval: 300  # seconds
```

### Data Flow

1. **Initialisation Phase**:
   - Load ontologies from configuration service
   - Generate embeddings for all ontology elements
   - Store embeddings in in-memory vector store

2. **Extraction Phase** (per chunk):
   - Split chunk into sentences and phrases
   - Compute embeddings for each segment
   - Search vector store for relevant ontology elements
   - Build ontology subset with selected elements
   - Construct prompt with chunk text and ontology subset
   - Call prompt service for extraction
   - Parse and validate returned triples
   - Output conformant triples

### In-Memory Vector Store

**Purpose**: Provides fast, memory-based similarity search for ontology element matching.

**Recommended Implementation: FAISS**

The system should use **FAISS (Facebook AI Similarity Search)** as the primary vector store implementation for the following reasons:

1. **Performance**: Optimised for similarity search with microsecond latency, critical for real-time query processing
2. **Memory Efficiency**: Multiple index types (Flat, IVF, HNSW) allow memory/speed tradeoffs based on ontology size
3. **Scalability**: Efficiently handles hundreds to tens of thousands of ontology elements
4. **Production Ready**: Battle-tested in production environments with excellent stability
5. **Python Integration**: Native Python bindings with numpy compatibility for seamless integration

**FAISS Implementation**:

```python
import faiss
import numpy as np

class FAISSVectorStore:
    def __init__(self, dimension=1536, index_type='flat'):
        """
        Initialize FAISS vector store.

        Args:
            dimension: Embedding dimension (1536 for text-embedding-3-small)
            index_type: 'flat' for exact search, 'ivf' for larger datasets
        """
        self.dimension = dimension
        self.metadata = []
        self.ids = []

        if index_type == 'flat':
            # Exact search - best for ontologies with <10k elements
            self.index = faiss.IndexFlatIP(dimension)
        else:
            # Approximate search - for larger ontologies
            quantizer = faiss.IndexFlatIP(dimension)
            self.index = faiss.IndexIVFFlat(quantizer, dimension, 100)
            self.index.train(np.random.randn(1000, dimension).astype('float32'))

    def add(self, id, embedding, metadata):
        """Add single embedding with metadata."""
        # Normalize for cosine similarity
        embedding = embedding / np.linalg.norm(embedding)
        self.index.add(np.array([embedding], dtype=np.float32))
        self.metadata.append(metadata)
        self.ids.append(id)

    def add_batch(self, ids, embeddings, metadata_list):
        """Batch add for initial ontology loading."""
        # Normalize all embeddings
        norms = np.linalg.norm(embeddings, axis=1, keepdims=True)
        normalized = embeddings / norms
        self.index.add(normalized.astype(np.float32))
        self.metadata.extend(metadata_list)
        self.ids.extend(ids)

    def search(self, embedding, top_k=10, threshold=0.0):
        """Search for similar vectors."""
        # Normalize query
        embedding = embedding / np.linalg.norm(embedding)

        # Search
        scores, indices = self.index.search(
            np.array([embedding], dtype=np.float32),
            min(top_k, self.index.ntotal)
        )

        # Filter by threshold and format results
        results = []
        for score, idx in zip(scores[0], indices[0]):
            if idx >= 0 and score >= threshold:  # FAISS returns -1 for empty slots
                results.append({
                    'id': self.ids[idx],
                    'score': float(score),
                    'metadata': self.metadata[idx]
                })

        return results

    def clear(self):
        """Reset the store."""
        self.index.reset()
        self.metadata = []
        self.ids = []

    def size(self):
        """Return number of stored vectors."""
        return self.index.ntotal
```

**Fallback Implementation (NumPy)**:

For development or small-scale deployments, a simple NumPy implementation can be used:

```python
class SimpleVectorStore:
    """Fallback implementation using NumPy - suitable for <1000 elements."""
    def __init__(self):
        self.embeddings = []
        self.metadata = []
        self.ids = []

    def add(self, id, embedding, metadata):
        self.embeddings.append(embedding / np.linalg.norm(embedding))
        self.metadata.append(metadata)
        self.ids.append(id)

    def search(self, embedding, top_k=10, threshold=0.0):
        if not self.embeddings:
            return []

        # Normalize and compute similarities
        embedding = embedding / np.linalg.norm(embedding)
        similarities = np.dot(self.embeddings, embedding)

        # Get top-k indices
        top_indices = np.argsort(similarities)[::-1][:top_k]

        # Build results
        results = []
        for idx in top_indices:
            if similarities[idx] >= threshold:
                results.append({
                    'id': self.ids[idx],
                    'score': float(similarities[idx]),
                    'metadata': self.metadata[idx]
                })

        return results
```

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
                    ┌─────────────────┐     ┌──────────────┐
                    │   Question      │────▶│   Sentence   │
                    │   Analyser      │     │   Splitter   │
                    └────────┬────────┘     └──────────────┘
                             │
                             ▼
                    ┌─────────────────┐     ┌──────────────┐
                    │   Ontology      │────▶│   Vector     │
                    │   Matcher       │     │    Store     │
                    └────────┬────────┘     └──────────────┘
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
                 ┌─────────────────┐     ┌──────────────┐
                 │   Answer        │────▶│   Prompt     │
                 │  Generator      │     │   Service    │
                 └────────┬────────┘     └──────────────┘
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
