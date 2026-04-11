# تضمينات المستندات - مُعرّف الجزء

## نظرة عامة

تخزين تضمينات المستندات يخزن حاليًا نص الجزء مباشرةً في حمولة مخزن المتجهات، مما يكرر البيانات الموجودة في Garage. يحل هذا المخطط تخزين نص الجزء باستخدام مراجع `chunk_id`.

## الحالة الحالية

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

حمولة تخزين المتجهات:
```python
payload={"doc": chunk}  # Duplicates Garage content
```

## التصميم

### تغييرات المخطط

**ChunkEmbeddings** - استبدال "chunk" بـ "chunk_id":
```python
@dataclass
class ChunkEmbeddings:
    chunk_id: str = ""
    vectors: list[list[float]] = field(default_factory=list)
```

**DocumentEmbeddingsResponse** - إرجاع معرفات الأجزاء (chunk_ids) بدلاً من الأجزاء نفسها:
```python
@dataclass
class DocumentEmbeddingsResponse:
    error: Error | None = None
    chunk_ids: list[str] = field(default_factory=list)
```

### حمولة مستودع المتجهات

جميع المستودعات (Qdrant، Milvus، Pinecone):
```python
payload={"chunk_id": chunk_id}
```

### التغييرات في معالج مستند RAG

يقوم معالج مستند RAG باسترداد محتوى الأجزاء من نظام Garage:

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

### التغييرات في واجهة برمجة التطبيقات (API) / مجموعة تطوير البرمجيات (SDK)

**DocumentEmbeddingsClient** تُرجع `chunk_ids`:
```python
return resp.chunk_ids  # Changed from resp.chunks
```

**تنسيق البيانات** (DocumentEmbeddingsResponseTranslator):
```python
result["chunk_ids"] = obj.chunk_ids  # Changed from chunks
```

### تغييرات واجهة سطر الأوامر (CLI)

تعرض أداة واجهة سطر الأوامر (CLI) معرفات الأجزاء (يمكن للمستخدمين استرداد المحتوى بشكل منفصل إذا لزم الأمر).

## الملفات التي يجب تعديلها

### المخطط (Schema)
`trustgraph-base/trustgraph/schema/knowledge/embeddings.py` - ChunkEmbeddings
`trustgraph-base/trustgraph/schema/services/query.py` - DocumentEmbeddingsResponse

### الرسائل/المترجمات
`trustgraph-base/trustgraph/messaging/translators/embeddings_query.py` - DocumentEmbeddingsResponseTranslator

### العميل (Client)
`trustgraph-base/trustgraph/base/document_embeddings_client.py` - إرجاع معرفات الأجزاء

### حزمة تطوير البرمجيات (SDK) / واجهة برمجة التطبيقات (API) بلغة بايثون
`trustgraph-base/trustgraph/api/flow.py` - document_embeddings_query
`trustgraph-base/trustgraph/api/socket_client.py` - document_embeddings_query
`trustgraph-base/trustgraph/api/async_flow.py` - إذا كان ذلك ممكنًا
`trustgraph-base/trustgraph/api/bulk_client.py` - استيراد/تصدير تضمينات المستندات
`trustgraph-base/trustgraph/api/async_bulk_client.py` - استيراد/تصدير تضمينات المستندات

### خدمة التضمينات
`trustgraph-flow/trustgraph/embeddings/document_embeddings/embeddings.py` - تمرير معرف الجزء

### أدوات الكتابة في التخزين
`trustgraph-flow/trustgraph/storage/doc_embeddings/qdrant/write.py`
`trustgraph-flow/trustgraph/storage/doc_embeddings/milvus/write.py`
`trustgraph-flow/trustgraph/storage/doc_embeddings/pinecone/write.py`

### خدمات الاستعلام
`trustgraph-flow/trustgraph/query/doc_embeddings/qdrant/service.py`
`trustgraph-flow/trustgraph/query/doc_embeddings/milvus/service.py`
`trustgraph-flow/trustgraph/query/doc_embeddings/pinecone/service.py`

### البوابة (Gateway)
`trustgraph-flow/trustgraph/gateway/dispatch/document_embeddings_query.py`
`trustgraph-flow/trustgraph/gateway/dispatch/document_embeddings_export.py`
`trustgraph-flow/trustgraph/gateway/dispatch/document_embeddings_import.py`

### استرجاع المعلومات من المستندات (Document RAG)
`trustgraph-flow/trustgraph/retrieval/document_rag/rag.py` - إضافة عميل أمين المكتبة
`trustgraph-flow/trustgraph/retrieval/document_rag/document_rag.py` - الاسترداد من Garage

### واجهة سطر الأوامر (CLI)
`trustgraph-cli/trustgraph/cli/invoke_document_embeddings.py`
`trustgraph-cli/trustgraph/cli/save_doc_embeds.py`
`trustgraph-cli/trustgraph/cli/load_doc_embeds.py`

## الفوائد

1. مصدر واحد للحقيقة - نص الأجزاء فقط في Garage
2. تقليل مساحة التخزين في مخزن المتجهات
3. يتيح تتبع مصدر المعلومات في وقت الاستعلام عبر معرف الجزء.
