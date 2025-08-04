# Schema Directory Refactoring Proposal

## Current Issues

1. **Flat structure** - All schemas in one directory makes it hard to understand relationships
2. **Mixed concerns** - Core types, domain objects, and API contracts all mixed together
3. **Unclear naming** - Files like "object.py", "types.py", "topic.py" don't clearly indicate their purpose
4. **No clear layering** - Can't easily see what depends on what

## Proposed Structure

```
trustgraph-base/trustgraph/schema/
├── __init__.py
├── core/              # Core primitive types used everywhere
│   ├── __init__.py
│   ├── primitives.py  # Error, Value, Triple, Field, RowSchema
│   ├── metadata.py    # Metadata record
│   └── topic.py       # Topic utilities
│
├── domain/            # Domain-specific data models
│   ├── __init__.py
│   ├── graph.py       # EntityContext, EntityEmbeddings, Triples
│   ├── document.py    # Document, TextDocument, Chunk
│   ├── knowledge.py   # Knowledge extraction types
│   └── embeddings.py  # All embedding-related types (moved from multiple files)
│
├── api/               # API request/response contracts
│   ├── __init__.py
│   ├── llm.py         # TextCompletion, Embeddings, Tool requests/responses
│   ├── retrieval.py   # GraphRAG, DocumentRAG queries/responses
│   ├── query.py       # GraphEmbeddingsRequest/Response, DocumentEmbeddingsRequest/Response
│   ├── agent.py       # Agent requests/responses
│   ├── flow.py        # Flow requests/responses
│   ├── config.py      # Configuration API
│   ├── library.py     # Librarian API
│   └── lookup.py      # Lookup API
│
└── extraction/        # Data extraction schemas
    ├── __init__.py
    └── nlp.py         # Definition, Topic, Relationship, Fact, Prompt types
```

## Key Changes

1. **Hierarchical organization** - Clear separation between core types, domain models, and API contracts
2. **Better naming**:
   - `types.py` → `core/primitives.py` (clearer purpose)
   - `object.py` → Split between appropriate files based on actual content
   - `documents.py` → `domain/document.py` (singular, consistent)
   - `models.py` → `api/llm.py` (clearer what kind of models)
   - `prompt.py` → `extraction/nlp.py` (clearer purpose)

3. **Logical grouping**:
   - All embedding types consolidated in `domain/embeddings.py`
   - All LLM-related APIs in `api/llm.py`
   - Clear separation of request/response pairs in API directory

4. **Dependency clarity**:
   - Core types have no dependencies
   - Domain models depend only on core
   - API contracts can depend on both core and domain
   - Extraction schemas depend on core

## Migration Benefits

1. **Easier navigation** - Developers can quickly find what they need
2. **Better modularity** - Clear boundaries between different concerns
3. **Simpler imports** - More intuitive import paths
4. **Future-proof** - Easy to add new domains or APIs without cluttering

## Example Import Changes

```python
# Before
from trustgraph.schema import Error, Triple, GraphEmbeddings, TextCompletionRequest

# After
from trustgraph.schema.core import Error, Triple
from trustgraph.schema.domain import GraphEmbeddings
from trustgraph.schema.api import TextCompletionRequest
```

## Implementation Notes

1. Keep backward compatibility by maintaining imports in root `__init__.py`
2. Move files gradually, updating imports as needed
3. Consider adding a `legacy.py` that imports everything for transition period
4. Update documentation to reflect new structure

<function_calls>
<invoke name="TodoWrite">
<parameter name="todos">[{"id": "1", "content": "Examine current schema directory structure", "status": "completed", "priority": "high"}, {"id": "2", "content": "Analyze schema files and their purposes", "status": "completed", "priority": "high"}, {"id": "3", "content": "Propose improved naming and structure", "status": "completed", "priority": "high"}]