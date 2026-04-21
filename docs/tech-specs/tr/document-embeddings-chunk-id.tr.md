---
layout: default
title: "Belge Gömme Parçası Kimliği"
parent: "Turkish (Beta)"
---

# Belge Gömme Parçası Kimliği

> **Beta Translation:** This document was translated via Machine Learning and as such may not be 100% accurate. All non-English languages are currently classified as Beta.

## Genel Bakış

Belge gömme depolaması şu anda parça metnini doğrudan vektör deposu yüküne kaydederek, Garage'da bulunan verilerin çoğaltılmasına neden oluyor. Bu özellik, parça metni depolamasını `chunk_id` referanslarıyla değiştirmektedir.

## Mevcut Durum

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

Vektör depolama yükü:
```python
payload={"doc": chunk}  # Duplicates Garage content
```

## Tasarım

### Şema Değişiklikleri

**ChunkEmbeddings** - chunk'ı chunk_id ile değiştirin:
```python
@dataclass
class ChunkEmbeddings:
    chunk_id: str = ""
    vectors: list[list[float]] = field(default_factory=list)
```

**DocumentEmbeddingsResponse** - parçalar yerine chunk_id'leri döndür:
```python
@dataclass
class DocumentEmbeddingsResponse:
    error: Error | None = None
    chunk_ids: list[str] = field(default_factory=list)
```

### Vektör Depolama Veri Yapısı

Tüm depolar (Qdrant, Milvus, Pinecone):
```python
payload={"chunk_id": chunk_id}
```

### Belge RAG Değişiklikleri

Belge RAG işlemcisi, parça içeriğini Garage'dan alır:

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

### API/SDK Değişiklikleri

**DocumentEmbeddingsClient**, `chunk_ids` değerini döndürür:
```python
return resp.chunk_ids  # Changed from resp.chunks
```

**Kablolu format** (DocumentEmbeddingsResponseTranslator):
```python
result["chunk_ids"] = obj.chunk_ids  # Changed from chunks
```

### CLI Değişiklikleri

CLI aracı, chunk_id'leri gösterir (çağrıcılar, gerekirse içeriği ayrı olarak alabilir).

## Değiştirilecek Dosyalar

### Şema
`trustgraph-base/trustgraph/schema/knowledge/embeddings.py` - ChunkEmbeddings
`trustgraph-base/trustgraph/schema/services/query.py` - DocumentEmbeddingsResponse

### Mesajlaşma/Çeviriciler
`trustgraph-base/trustgraph/messaging/translators/embeddings_query.py` - DocumentEmbeddingsResponseTranslator

### İstemci
`trustgraph-base/trustgraph/base/document_embeddings_client.py` - chunk_id'leri döndür

### Python SDK/API
`trustgraph-base/trustgraph/api/flow.py` - document_embeddings_query
`trustgraph-base/trustgraph/api/socket_client.py` - document_embeddings_query
`trustgraph-base/trustgraph/api/async_flow.py` - eğer uygunsa
`trustgraph-base/trustgraph/api/bulk_client.py` - belge gömülerinin içe/dışa aktarımı
`trustgraph-base/trustgraph/api/async_bulk_client.py` - belge gömülerinin içe/dışa aktarımı

### Gömme Hizmeti
`trustgraph-flow/trustgraph/embeddings/document_embeddings/embeddings.py` - chunk_id'yi ilet

### Depolama Yazıcıları
`trustgraph-flow/trustgraph/storage/doc_embeddings/qdrant/write.py`
`trustgraph-flow/trustgraph/storage/doc_embeddings/milvus/write.py`
`trustgraph-flow/trustgraph/storage/doc_embeddings/pinecone/write.py`

### Sorgu Hizmetleri
`trustgraph-flow/trustgraph/query/doc_embeddings/qdrant/service.py`
`trustgraph-flow/trustgraph/query/doc_embeddings/milvus/service.py`
`trustgraph-flow/trustgraph/query/doc_embeddings/pinecone/service.py`

### Ağ Geçidi
`trustgraph-flow/trustgraph/gateway/dispatch/document_embeddings_query.py`
`trustgraph-flow/trustgraph/gateway/dispatch/document_embeddings_export.py`
`trustgraph-flow/trustgraph/gateway/dispatch/document_embeddings_import.py`

### Belge RAG
`trustgraph-flow/trustgraph/retrieval/document_rag/rag.py` - librarian istemcisini ekle
`trustgraph-flow/trustgraph/retrieval/document_rag/document_rag.py` - Garage'dan al

### CLI
`trustgraph-cli/trustgraph/cli/invoke_document_embeddings.py`
`trustgraph-cli/trustgraph/cli/save_doc_embeds.py`
`trustgraph-cli/trustgraph/cli/load_doc_embeds.py`

## Faydalar

1. Tek kaynaklı doğruluk - chunk metni yalnızca Garage'da bulunur.
2. Vektör depolama alanında azalma.
3. chunk_id aracılığıyla sorgu zamanı köken bilgisini sağlar.
