# Incorporações de Documentos - ID do Trecho

## Visão Geral

Atualmente, o armazenamento de incorporações de documentos armazena o texto do trecho diretamente no payload do armazenamento vetorial, duplicando dados que já existem no Garage. Esta especificação substitui o armazenamento do texto do trecho por referências `chunk_id`.

## Estado Atual

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

Payload do armazenamento vetorial:
```python
payload={"doc": chunk}  # Duplicates Garage content
```

## Design

### Schema Changes

**ChunkEmbeddings** - substituir "chunk" por "chunk_id":
```python
@dataclass
class ChunkEmbeddings:
    chunk_id: str = ""
    vectors: list[list[float]] = field(default_factory=list)
```

**DocumentEmbeddingsResponse** - retornar chunk_ids em vez de chunks:
```python
@dataclass
class DocumentEmbeddingsResponse:
    error: Error | None = None
    chunk_ids: list[str] = field(default_factory=list)
```

### Carga Útil do Armazenamento Vetorial

Todos os armazenamentos (Qdrant, Milvus, Pinecone):
```python
payload={"chunk_id": chunk_id}
```

### Alterações no Processador de Documentos RAG

O processador de documentos RAG busca o conteúdo dos fragmentos do Garage:

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

### Alterações na API/SDK

**DocumentEmbeddingsClient** retorna chunk_ids:
```python
return resp.chunk_ids  # Changed from resp.chunks
```

**Formato de dados** (DocumentEmbeddingsResponseTranslator):
```python
result["chunk_ids"] = obj.chunk_ids  # Changed from chunks
```

### Alterações na CLI

A ferramenta CLI exibe os chunk_ids (os chamadores podem buscar o conteúdo separadamente, se necessário).

## Arquivos a serem modificados

### Schema
`trustgraph-base/trustgraph/schema/knowledge/embeddings.py` - ChunkEmbeddings
`trustgraph-base/trustgraph/schema/services/query.py` - DocumentEmbeddingsResponse

### Mensagens/Tradutores
`trustgraph-base/trustgraph/messaging/translators/embeddings_query.py` - DocumentEmbeddingsResponseTranslator

### Cliente
`trustgraph-base/trustgraph/base/document_embeddings_client.py` - retornar chunk_ids

### SDK/API Python
`trustgraph-base/trustgraph/api/flow.py` - document_embeddings_query
`trustgraph-base/trustgraph/api/socket_client.py` - document_embeddings_query
`trustgraph-base/trustgraph/api/async_flow.py` - se aplicável
`trustgraph-base/trustgraph/api/bulk_client.py` - importar/exportar embeddings de documentos
`trustgraph-base/trustgraph/api/async_bulk_client.py` - importar/exportar embeddings de documentos

### Serviço de Embeddings
`trustgraph-flow/trustgraph/embeddings/document_embeddings/embeddings.py` - passar chunk_id

### Escritores de Armazenamento
`trustgraph-flow/trustgraph/storage/doc_embeddings/qdrant/write.py`
`trustgraph-flow/trustgraph/storage/doc_embeddings/milvus/write.py`
`trustgraph-flow/trustgraph/storage/doc_embeddings/pinecone/write.py`

### Serviços de Consulta
`trustgraph-flow/trustgraph/query/doc_embeddings/qdrant/service.py`
`trustgraph-flow/trustgraph/query/doc_embeddings/milvus/service.py`
`trustgraph-flow/trustgraph/query/doc_embeddings/pinecone/service.py`

### Gateway
`trustgraph-flow/trustgraph/gateway/dispatch/document_embeddings_query.py`
`trustgraph-flow/trustgraph/gateway/dispatch/document_embeddings_export.py`
`trustgraph-flow/trustgraph/gateway/dispatch/document_embeddings_import.py`

### Document RAG
`trustgraph-flow/trustgraph/retrieval/document_rag/rag.py` - adicionar cliente librarian
`trustgraph-flow/trustgraph/retrieval/document_rag/document_rag.py` - buscar do Garage

### CLI
`trustgraph-cli/trustgraph/cli/invoke_document_embeddings.py`
`trustgraph-cli/trustgraph/cli/save_doc_embeds.py`
`trustgraph-cli/trustgraph/cli/load_doc_embeds.py`

## Benefícios

1. Única fonte de verdade - texto do chunk apenas no Garage
2. Redução do armazenamento do vetor
3. Permite a rastreabilidade em tempo de consulta via chunk_id
