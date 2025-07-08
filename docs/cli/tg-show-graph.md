# tg-show-graph

Displays knowledge graph triples (edges) from the TrustGraph system.

## Synopsis

```bash
tg-show-graph [options]
```

## Description

The `tg-show-graph` command queries the knowledge graph and displays up to 10,000 triples (subject-predicate-object relationships) in a human-readable format. This is useful for exploring knowledge graph contents, debugging knowledge loading, and understanding the structure of stored knowledge.

Each triple represents a fact or relationship in the knowledge graph, showing how entities are connected through various predicates.

## Options

- `-u, --api-url URL`: TrustGraph API URL (default: `$TRUSTGRAPH_URL` or `http://localhost:8088/`)
- `-f, --flow-id FLOW`: Flow ID to query (default: `default`)
- `-U, --user USER`: User identifier (default: `trustgraph`)
- `-C, --collection COLLECTION`: Collection identifier (default: `default`)

## Examples

### Display All Graph Triples
```bash
tg-show-graph
```

### Query Specific Flow
```bash
tg-show-graph -f research-flow
```

### Query User's Collection
```bash
tg-show-graph -U researcher -C medical-papers
```

### Using Custom API URL
```bash
tg-show-graph -u http://production:8088/
```

## Output Format

The command displays triples in subject-predicate-object format:

```
<Person1> <hasName> "John Doe"
<Person1> <worksAt> <Organization1>
<Organization1> <hasName> "Acme Corporation"
<Organization1> <locatedIn> <City1>
<City1> <hasName> "New York"
<Document1> <createdBy> <Person1>
<Document1> <hasTitle> "Research Report"
<Document1> <publishedIn> "2024"
```

### Triple Components

- **Subject**: The entity the statement is about (usually a URI)
- **Predicate**: The relationship or property (usually a URI)
- **Object**: The value or target entity (can be URI or literal)

### URI vs Literal Values

- **URIs**: Enclosed in angle brackets `<Entity1>`
- **Literals**: Enclosed in quotes `"Literal Value"`

### Common Predicates

- `<hasName>`: Entity names
- `<hasTitle>`: Document titles
- `<createdBy>`: Authorship relationships
- `<worksAt>`: Employment relationships
- `<locatedIn>`: Location relationships
- `<publishedIn>`: Publication information
- `<dc:creator>`: Dublin Core creator
- `<foaf:name>`: Friend of a Friend name

## Data Limitations

### 10,000 Triple Limit
The command displays up to 10,000 triples to prevent overwhelming output. For larger graphs:

```bash
# Use graph export for complete data
tg-graph-to-turtle -o complete-graph.ttl

# Use targeted queries for specific data
tg-invoke-graph-rag -q "Show me information about specific entities"
```

### Collection Scope
Results are limited to the specified user and collection. To see all data:

```bash
# Query different collections
tg-show-graph -C collection1
tg-show-graph -C collection2
```

## Knowledge Graph Structure

### Entity Types
Common entity types in the output:
- **Documents**: Research papers, reports, manuals
- **People**: Authors, researchers, employees
- **Organizations**: Companies, institutions, publishers
- **Concepts**: Technical terms, topics, categories
- **Events**: Publications, meetings, processes

### Relationship Types
Common relationship types:
- **Authorship**: Who created what
- **Membership**: Who belongs to what organization
- **Hierarchical**: Parent-child relationships
- **Temporal**: When things happened
- **Topical**: What topics are related

## Error Handling

### Flow Not Available
```bash
Exception: Invalid flow
```
**Solution**: Verify the flow exists and is running with `tg-show-flows`.

### No Data Available
```bash
# Empty output (no triples displayed)
```
**Solution**: Check if knowledge has been loaded using `tg-show-kg-cores` and `tg-load-kg-core`.

### Connection Errors
```bash
Exception: Connection refused
```
**Solution**: Check the API URL and ensure TrustGraph is running.

### Permission Errors
```bash
Exception: Access denied
```
**Solution**: Verify user permissions for the specified collection.

## Environment Variables

- `TRUSTGRAPH_URL`: Default API URL

## Related Commands

- [`tg-graph-to-turtle`](tg-graph-to-turtle.md) - Export graph to Turtle format
- [`tg-load-kg-core`](tg-load-kg-core.md) - Load knowledge into graph
- [`tg-show-kg-cores`](tg-show-kg-cores.md) - List available knowledge cores
- [`tg-invoke-graph-rag`](tg-invoke-graph-rag.md) - Query graph with natural language
- [`tg-load-turtle`](tg-load-turtle.md) - Import RDF data from Turtle files

## API Integration

This command uses the [Triples Query API](../apis/api-triples-query.md) to retrieve knowledge graph triples with no filtering constraints.

## Use Cases

### Knowledge Exploration
```bash
# Explore what knowledge is available
tg-show-graph | head -50

# Look for specific entities
tg-show-graph | grep "Einstein"
```

### Data Verification
```bash
# Verify knowledge loading worked correctly
tg-load-kg-core --kg-core-id "research-data" --flow-id "research-flow"
tg-show-graph -f research-flow | wc -l
```

### Debugging Knowledge Issues
```bash
# Check if specific relationships exist
tg-show-graph | grep "hasName"
tg-show-graph | grep "createdBy"
```

### Graph Analysis
```bash
# Count different relationship types
tg-show-graph | awk '{print $2}' | sort | uniq -c

# Find most connected entities
tg-show-graph | awk '{print $1}' | sort | uniq -c | sort -nr
```

### Data Quality Assessment
```bash
# Check for malformed triples
tg-show-graph | grep -v "^<.*> <.*>"

# Verify URI patterns
tg-show-graph | grep "http://" | head -20
```

## Output Processing

### Filter by Predicate
```bash
# Show only name relationships
tg-show-graph | grep "hasName"

# Show only authorship
tg-show-graph | grep "createdBy"
```

### Extract Entities
```bash
# List all subjects (entities)
tg-show-graph | awk '{print $1}' | sort | uniq

# List all predicates (relationships)
tg-show-graph | awk '{print $2}' | sort | uniq
```

### Export Subsets
```bash
# Save specific relationships
tg-show-graph | grep "Organization" > organization-data.txt

# Save person-related triples
tg-show-graph | grep "Person" > person-data.txt
```

## Performance Considerations

### Large Graphs
For graphs with many triples:
- Command may take time to retrieve 10,000 triples
- Consider using filtered queries for specific data
- Use `tg-graph-to-turtle` for complete export

### Memory Usage
- Output is streamed, so memory usage is manageable
- Piping to other commands processes data incrementally

## Best Practices

1. **Start Small**: Begin with small collections to understand structure
2. **Use Filters**: Pipe output through grep/awk for specific data
3. **Regular Inspection**: Periodically check graph contents
4. **Data Validation**: Verify expected relationships exist
5. **Performance Monitoring**: Monitor query time for large graphs
6. **Collection Organization**: Use collections to organize different domains

## Integration Examples

### With Other Tools
```bash
# Convert to different formats
tg-show-graph | sed 's/[<>"]//g' > simple-triples.txt

# Create entity lists
tg-show-graph | awk '{print $1}' | sort | uniq > entities.txt

# Generate statistics
tg-show-graph | wc -l
echo "Total triples in graph"
```

### Graph Exploration Workflow
```bash
# 1. Check available knowledge
tg-show-kg-cores

# 2. Load knowledge into flow
tg-load-kg-core --kg-core-id "my-knowledge" --flow-id "my-flow"

# 3. Explore the graph
tg-show-graph -f my-flow

# 4. Query specific information
tg-invoke-graph-rag -q "What entities are in the graph?" -f my-flow
```