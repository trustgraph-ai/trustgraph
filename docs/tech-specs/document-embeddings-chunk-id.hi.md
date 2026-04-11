---
layout: default
title: "दस्तावेज़ एम्बेडिंग चंक आईडी"
parent: "Hindi (Beta)"
---

# दस्तावेज़ एम्बेडिंग चंक आईडी

> **Beta Translation:** This document was translated via Machine Learning and as such may not be 100% accurate. All non-English languages are currently classified as Beta.

## अवलोकन

वर्तमान में, दस्तावेज़ एम्बेडिंग स्टोरेज चंक टेक्स्ट को सीधे वेक्टर स्टोर पेलोड में संग्रहीत करता है, जिससे गैरेज में मौजूद डेटा दोहराया जाता है। यह विनिर्देश चंक टेक्स्ट स्टोरेज को `chunk_id` संदर्भों से बदल देता है।

## वर्तमान स्थिति

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

वेक्टर स्टोर पेलोड:
```python
payload={"doc": chunk}  # Duplicates Garage content
```

## डिज़ाइन

### स्कीमा में बदलाव

**ChunkEmbeddings** - "chunk" को "chunk_id" से बदलें:
```python
@dataclass
class ChunkEmbeddings:
    chunk_id: str = ""
    vectors: list[list[float]] = field(default_factory=list)
```

**DocumentEmbeddingsResponse** - चंक्स के बजाय chunk_ids लौटाएं:
```python
@dataclass
class DocumentEmbeddingsResponse:
    error: Error | None = None
    chunk_ids: list[str] = field(default_factory=list)
```

### वेक्टर स्टोर पेलोड

सभी स्टोर (क्यूड्रेंट, मिल्वस, पाइनकोन):
```python
payload={"chunk_id": chunk_id}
```

### दस्तावेज़ आरएजी (RAG) में बदलाव

दस्तावेज़ आरएजी प्रोसेसर, गराज (Garage) से चंक सामग्री प्राप्त करता है:

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

### एपीआई/एसडीके में बदलाव

**DocumentEmbeddingsClient** चंक_आईडी (chunk_ids) लौटाता है:
```python
return resp.chunk_ids  # Changed from resp.chunks
```

**वायर प्रारूप** (DocumentEmbeddingsResponseTranslator):
```python
result["chunk_ids"] = obj.chunk_ids  # Changed from chunks
```

### CLI में बदलाव

CLI टूल `chunk_ids` प्रदर्शित करता है (उपयोगकर्ता आवश्यकता पड़ने पर सामग्री को अलग से प्राप्त कर सकते हैं)।

## संशोधित करने योग्य फाइलें

### स्कीमा
`trustgraph-base/trustgraph/schema/knowledge/embeddings.py` - `ChunkEmbeddings`
`trustgraph-base/trustgraph/schema/services/query.py` - `DocumentEmbeddingsResponse`

### मैसेजिंग/अनुवादक
`trustgraph-base/trustgraph/messaging/translators/embeddings_query.py` - `DocumentEmbeddingsResponseTranslator`

### क्लाइंट
`trustgraph-base/trustgraph/base/document_embeddings_client.py` - `chunk_ids` लौटाएं

### पायथन SDK/API
`trustgraph-base/trustgraph/api/flow.py` - `document_embeddings_query`
`trustgraph-base/trustgraph/api/socket_client.py` - `document_embeddings_query`
`trustgraph-base/trustgraph/api/async_flow.py` - यदि लागू हो
`trustgraph-base/trustgraph/api/bulk_client.py` - दस्तावेज़ एम्बेडिंग का आयात/निर्यात
`trustgraph-base/trustgraph/api/async_bulk_client.py` - दस्तावेज़ एम्बेडिंग का आयात/निर्यात

### एम्बेडिंग सेवा
`trustgraph-flow/trustgraph/embeddings/document_embeddings/embeddings.py` - `chunk_id` पास करें

### स्टोरेज राइटर
`trustgraph-flow/trustgraph/storage/doc_embeddings/qdrant/write.py`
`trustgraph-flow/trustgraph/storage/doc_embeddings/milvus/write.py`
`trustgraph-flow/trustgraph/storage/doc_embeddings/pinecone/write.py`

### क्वेरी सेवाएं
`trustgraph-flow/trustgraph/query/doc_embeddings/qdrant/service.py`
`trustgraph-flow/trustgraph/query/doc_embeddings/milvus/service.py`
`trustgraph-flow/trustgraph/query/doc_embeddings/pinecone/service.py`

### गेटवे
`trustgraph-flow/trustgraph/gateway/dispatch/document_embeddings_query.py`
`trustgraph-flow/trustgraph/gateway/dispatch/document_embeddings_export.py`
`trustgraph-flow/trustgraph/gateway/dispatch/document_embeddings_import.py`

### दस्तावेज़ RAG
`trustgraph-flow/trustgraph/retrieval/document_rag/rag.py` - लाइब्रेरियन क्लाइंट जोड़ें
`trustgraph-flow/trustgraph/retrieval/document_rag/document_rag.py` - गैरेज से प्राप्त करें

### CLI
`trustgraph-cli/trustgraph/cli/invoke_document_embeddings.py`
`trustgraph-cli/trustgraph/cli/save_doc_embeds.py`
`trustgraph-cli/trustgraph/cli/load_doc_embeds.py`

## लाभ

1. सत्य का एकल स्रोत - केवल गैरेज में टेक्स्ट चंक
2. वेक्टर स्टोर स्टोरेज में कमी
3. `chunk_id` के माध्यम से क्वेरी-टाइम उत्पत्ति को सक्षम करता है
