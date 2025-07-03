# tg-invoke-graph-rag

Uses the Graph RAG service to answer questions using knowledge graph data.

## Synopsis

```bash
tg-invoke-graph-rag -q "question" [options]
```

## Description

The `tg-invoke-graph-rag` command performs graph-based Retrieval Augmented Generation (RAG) to answer questions using structured knowledge from the knowledge graph. It retrieves relevant entities and relationships from the graph and uses them to provide contextually accurate answers.

Graph RAG is particularly effective for questions that require understanding relationships between entities, reasoning over structured knowledge, and providing answers based on factual connections in the data.

## Options

### Required Arguments

- `-q, --question QUESTION`: The question to answer using graph knowledge

### Optional Arguments

- `-u, --url URL`: TrustGraph API URL (default: `$TRUSTGRAPH_URL` or `http://localhost:8088/`)
- `-f, --flow-id FLOW`: Flow ID to use (default: `default`)
- `-U, --user USER`: User identifier (default: `trustgraph`)
- `-C, --collection COLLECTION`: Collection identifier (default: `default`)

### Graph Search Parameters

- `-e, --entity-limit LIMIT`: Maximum entities to retrieve (default: `50`)
- `-t, --triple-limit LIMIT`: Maximum triples to retrieve (default: `30`)
- `-s, --max-subgraph-size SIZE`: Maximum subgraph size (default: `150`)
- `-p, --max-path-length LENGTH`: Maximum path length for graph traversal (default: `2`)

## Examples

### Basic Graph RAG Query
```bash
tg-invoke-graph-rag -q "What is the relationship between AI and machine learning?"
```

### With Custom Parameters
```bash
tg-invoke-graph-rag \
  -q "How are neural networks connected to deep learning?" \
  -e 100 \
  -t 50 \
  -s 200
```

### Using Specific Flow and Collection
```bash
tg-invoke-graph-rag \
  -q "What research papers discuss climate change?" \
  -f research-flow \
  -C scientific-papers \
  -U researcher
```

### Large Graph Exploration
```bash
tg-invoke-graph-rag \
  -q "Explain the connections between quantum computing and cryptography" \
  -e 150 \
  -t 100 \
  -s 300 \
  -p 3
```

## Graph Search Parameters Explained

### Entity Limit (`-e, --entity-limit`)
Controls how many entities are retrieved from the knowledge graph that are relevant to the question. Higher values provide more context but may include less relevant information.

### Triple Limit (`-t, --triple-limit`)
Limits the number of relationship triples (subject-predicate-object) retrieved. These triples define the relationships between entities.

### Max Subgraph Size (`-s, --max-subgraph-size`)
Sets the maximum size of the knowledge subgraph used for answering. Larger subgraphs provide more complete context but require more processing.

### Max Path Length (`-p, --max-path-length`)
Determines how many "hops" through the graph are considered when finding relationships. Higher values can discover more distant but potentially relevant connections.

## Output Format

The command returns a natural language answer based on the retrieved graph knowledge:

```
Neural networks are a fundamental component of deep learning architectures. 
The knowledge graph shows that deep learning is a subset of machine learning 
that specifically utilizes multi-layered neural networks. These networks consist 
of interconnected nodes (neurons) organized in layers, where each layer processes 
and transforms the input data. The relationship between neural networks and deep 
learning is that neural networks provide the computational structure, while deep 
learning represents the training methodologies and architectures that use these 
networks to learn complex patterns from data.
```

## How Graph RAG Works

1. **Query Analysis**: Analyzes the question to identify key entities and concepts
2. **Entity Retrieval**: Finds relevant entities in the knowledge graph
3. **Subgraph Extraction**: Retrieves connected entities and relationships
4. **Context Assembly**: Combines retrieved knowledge into coherent context
5. **Answer Generation**: Uses LLM with graph context to generate accurate answers

## Comparison with Document RAG

### Graph RAG Advantages
- **Structured Knowledge**: Leverages explicit relationships between concepts
- **Reasoning Capability**: Can infer answers from connected facts
- **Consistency**: Provides factually consistent answers based on structured data
- **Relationship Discovery**: Excellent for questions about connections and relationships

### When to Use Graph RAG
- Questions about relationships between entities
- Queries requiring logical reasoning over facts
- When you need to understand connections in complex domains
- For factual questions with precise answers

## Error Handling

### Flow Not Available
```bash
Exception: Invalid flow
```
**Solution**: Verify the flow exists and is running with `tg-show-flows`.

### No Graph Data
```bash
Exception: No relevant knowledge found
```
**Solution**: Ensure knowledge has been loaded into the graph using `tg-load-kg-core` or document processing.

### Connection Errors
```bash
Exception: Connection refused
```
**Solution**: Check the API URL and ensure TrustGraph is running.

### Parameter Errors
```bash
Exception: Invalid parameter value
```
**Solution**: Verify that numeric parameters are within valid ranges.

## Environment Variables

- `TRUSTGRAPH_URL`: Default API URL

## Related Commands

- [`tg-invoke-document-rag`](tg-invoke-document-rag.md) - Document-based RAG queries
- [`tg-invoke-agent`](tg-invoke-agent.md) - Interactive agent with multiple tools
- [`tg-load-kg-core`](tg-load-kg-core.md) - Load knowledge into graph
- [`tg-show-graph`](tg-show-graph.md) - Explore graph contents
- [`tg-show-flows`](tg-show-flows.md) - List available flows

## API Integration

This command uses the [Graph RAG API](../apis/api-graph-rag.md) to perform retrieval augmented generation using knowledge graph data.

## Use Cases

### Research and Academia
```bash
tg-invoke-graph-rag \
  -q "What are the key researchers working on quantum machine learning?" \
  -C academic-papers
```

### Business Intelligence
```bash
tg-invoke-graph-rag \
  -q "How do our products relate to market trends?" \
  -C business-data
```

### Technical Documentation
```bash
tg-invoke-graph-rag \
  -q "What are the dependencies between these software components?" \
  -C technical-docs
```

### Medical Knowledge
```bash
tg-invoke-graph-rag \
  -q "What are the known interactions between these medications?" \
  -C medical-knowledge
```

## Performance Tuning

### For Broad Questions
Increase limits to get comprehensive answers:
```bash
-e 100 -t 80 -s 250 -p 3
```

### For Specific Questions
Use lower limits for faster, focused responses:
```bash
-e 30 -t 20 -s 100 -p 2
```

### For Deep Analysis
Allow longer paths and larger subgraphs:
```bash
-e 150 -t 100 -s 400 -p 4
```

## Best Practices

1. **Parameter Tuning**: Start with defaults and adjust based on question complexity
2. **Question Clarity**: Ask specific questions for better graph retrieval
3. **Knowledge Quality**: Ensure high-quality knowledge is loaded in the graph
4. **Flow Selection**: Use flows with appropriate knowledge domains
5. **Collection Targeting**: Specify relevant collections for focused results