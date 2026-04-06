# Identificador de fragmento de incrustaciones de documentos

## Resumen

Actualmente, el almacenamiento de incrustaciones de documentos almacena directamente el texto del fragmento en la carga útil de la base de datos vectorial, duplicando datos que existen en Garage. Esta especificación reemplaza el almacenamiento del texto del fragmento con referencias `chunk_id`.

## Estado actual

```python
@dataclass
class ChunkEmbeddings:
    chunk: bytes = b""
    vectors: list[list[float]] = field(default_factory=list)

@dataclass
class DocumentEmbeddingsResponse:
    error: Error | None = None
    chunks: list[str] = field(default_factory=list)
```

Carga útil del almacén de vectores:
```python
payload={"doc": chunk}  # Duplicates Garage content
```

## Diseño

### Cambios en el esquema

**ChunkEmbeddings** - reemplazar "chunk" con "chunk_id":
```python
@dataclass
class ChunkEmbeddings:
    chunk_id: str = ""
    vectors: list[list[float]] = field(default_factory=list)
```

**DocumentEmbeddingsResponse** - devolver `chunk_ids` en lugar de `chunks`:
```python
@dataclass
class DocumentEmbeddingsResponse:
    error: Error | None = None
    chunk_ids: list[str] = field(default_factory=list)
```

### Carga útil del almacén de vectores

Todos los almacenes (Qdrant, Milvus, Pinecone):
```python
payload={"chunk_id": chunk_id}
```

### Cambios en el Documento RAG

El procesador de documentos RAG recupera el contenido de los fragmentos de Garage:

```python
# Get chunk_ids from embeddings store
chunk_ids = await self.rag.doc_embeddings_client.query(...)

# Fetch chunk content from Garage
docs = []
for chunk_id in chunk_ids:
    content = await self.rag.librarian_client.get_document_content(
        chunk_id, self.user
    )
    docs.append(content)
```

### Cambios en la API/SDK

**DocumentEmbeddingsClient** devuelve chunk_ids:
```python
return resp.chunk_ids  # Changed from resp.chunks
```

**Formato de cable** (DocumentEmbeddingsResponseTranslator):
```python
result["chunk_ids"] = obj.chunk_ids  # Changed from chunks
```

### Cambios en la CLI

La herramienta de la CLI muestra los chunk_ids (los usuarios pueden obtener el contenido por separado si es necesario).

## Archivos a Modificar

### Esquema
`trustgraph-base/trustgraph/schema/knowledge/embeddings.py` - ChunkEmbeddings
`trustgraph-base/trustgraph/schema/services/query.py` - DocumentEmbeddingsResponse

### Mensajería/Traductores
`trustgraph-base/trustgraph/messaging/translators/embeddings_query.py` - DocumentEmbeddingsResponseTranslator

### Cliente
`trustgraph-base/trustgraph/base/document_embeddings_client.py` - return chunk_ids

### SDK/API de Python
`trustgraph-base/trustgraph/api/flow.py` - document_embeddings_query
`trustgraph-base/trustgraph/api/socket_client.py` - document_embeddings_query
`trustgraph-base/trustgraph/api/async_flow.py` - if applicable
`trustgraph-base/trustgraph/api/bulk_client.py` - import/export document embeddings
`trustgraph-base/trustgraph/api/async_bulk_client.py` - import/export document embeddings

### Servicio de Embeddings
`trustgraph-flow/trustgraph/embeddings/document_embeddings/embeddings.py` - pass chunk_id

### Escritores de Almacenamiento
`trustgraph-flow/trustgraph/storage/doc_embeddings/qdrant/write.py`
`trustgraph-flow/trustgraph/storage/doc_embeddings/milvus/write.py`
`trustgraph-flow/trustgraph/storage/doc_embeddings/pinecone/write.py`

### Servicios de Consulta
`trustgraph-flow/trustgraph/query/doc_embeddings/qdrant/service.py`
`trustgraph-flow/trustgraph/query/doc_embeddings/milvus/service.py`
`trustgraph-flow/trustgraph/query/doc_embeddings/pinecone/service.py`

### Gateway
`trustgraph-flow/trustgraph/gateway/dispatch/document_embeddings_query.py`
`trustgraph-flow/trustgraph/gateway/dispatch/document_embeddings_export.py`
`trustgraph-flow/trustgraph/gateway/dispatch/document_embeddings_import.py`

### Document RAG
`trustgraph-flow/trustgraph/retrieval/document_rag/rag.py` - add librarian client
`trustgraph-flow/trustgraph/retrieval/document_rag/document_rag.py` - fetch from Garage

### CLI
`trustgraph-cli/trustgraph/cli/invoke_document_embeddings.py`
`trustgraph-cli/trustgraph/cli/save_doc_embeds.py`
`trustgraph-cli/trustgraph/cli/load_doc_embeds.py`

## Beneficios

1. Única fuente de verdad: solo el texto de los chunks en Garage.
2. Almacenamiento de vectores reducido.
3. Permite el rastreo de origen en tiempo de consulta a través del chunk_id.
