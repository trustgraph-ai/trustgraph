# מזהה מקטע של הטמעות מסמכים

## סקירה כללית

אחסון הטמעות מסמכים מאחסן כרגע את הטקסט של המקטעים ישירות בתוך מטען ה-vector store, מה שמשכפל נתונים הקיימים ב-Garage. מפרט זה מחליף את אחסון הטקסט של המקטעים עם הפניות ל-`chunk_id`.

## מצב נוכחי

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

מטען אחסון וקטורים:
```python
payload={"doc": chunk}  # Duplicates Garage content
```

## עיצוב

### שינויים בסכימה

**ChunkEmbeddings** - החלפת "chunk" ב-"chunk_id":
```python
@dataclass
class ChunkEmbeddings:
    chunk_id: str = ""
    vectors: list[list[float]] = field(default_factory=list)
```

**תגובת DocumentEmbeddingsResponse** - החזרת מזהי חלקים (chunk_ids) במקום חלקים (chunks):
```python
@dataclass
class DocumentEmbeddingsResponse:
    error: Error | None = None
    chunk_ids: list[str] = field(default_factory=list)
```

### מטען של אחסון וקטורים

כל האחסונים (Qdrant, Milvus, Pinecone):
```python
payload={"chunk_id": chunk_id}
```

### שינויים במסמך RAG

מעבד מסמכי ה-RAG שולף תוכן מקטעים מ-Garage:

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

### שינויים ב-API/SDK

**DocumentEmbeddingsClient** מחזיר את chunk_ids:
```python
return resp.chunk_ids  # Changed from resp.chunks
```

**פורמט של נתונים** (DocumentEmbeddingsResponseTranslator):
```python
result["chunk_ids"] = obj.chunk_ids  # Changed from chunks
```

### שינויים בממשק שורת הפקודה (CLI)

כלי ה-CLI מציג מזהי חלקים (chunk_ids) (המשתמשים יכולים לשלוף את התוכן בנפרד אם יש צורך).

## קבצים לשינוי

### סכימה (Schema)
`trustgraph-base/trustgraph/schema/knowledge/embeddings.py` - ChunkEmbeddings
`trustgraph-base/trustgraph/schema/services/query.py` - DocumentEmbeddingsResponse

### הודעות/מתרגמים
`trustgraph-base/trustgraph/messaging/translators/embeddings_query.py` - DocumentEmbeddingsResponseTranslator

### לקוח (Client)
`trustgraph-base/trustgraph/base/document_embeddings_client.py` - החזרת מזהי חלקים (chunk_ids)

### ערכת פיתוח תוכנה (SDK) / API בפייתון
`trustgraph-base/trustgraph/api/flow.py` - document_embeddings_query
`trustgraph-base/trustgraph/api/socket_client.py` - document_embeddings_query
`trustgraph-base/trustgraph/api/async_flow.py` - אם רלוונטי
`trustgraph-base/trustgraph/api/bulk_client.py` - ייבוא/ייצוא של הטמעות מסמכים (document embeddings)
`trustgraph-base/trustgraph/api/async_bulk_client.py` - ייבוא/ייצוא של הטמעות מסמכים (document embeddings)

### שירות הטמעות
`trustgraph-flow/trustgraph/embeddings/document_embeddings/embeddings.py` - העברת מזהה חלק (chunk_id)

### כותבי אחסון
`trustgraph-flow/trustgraph/storage/doc_embeddings/qdrant/write.py`
`trustgraph-flow/trustgraph/storage/doc_embeddings/milvus/write.py`
`trustgraph-flow/trustgraph/storage/doc_embeddings/pinecone/write.py`

### שירותי שאילתות
`trustgraph-flow/trustgraph/query/doc_embeddings/qdrant/service.py`
`trustgraph-flow/trustgraph/query/doc_embeddings/milvus/service.py`
`trustgraph-flow/trustgraph/query/doc_embeddings/pinecone/service.py`

### שער (Gateway)
`trustgraph-flow/trustgraph/gateway/dispatch/document_embeddings_query.py`
`trustgraph-flow/trustgraph/gateway/dispatch/document_embeddings_export.py`
`trustgraph-flow/trustgraph/gateway/dispatch/document_embeddings_import.py`

### אחזור מידע ממסמכים (Document RAG)
`trustgraph-flow/trustgraph/retrieval/document_rag/rag.py` - הוספת לקוח של "ספרן" (librarian)
`trustgraph-flow/trustgraph/retrieval/document_rag/document_rag.py` - שליפה מ-"Garage"

### ממשק שורת הפקודה (CLI)
`trustgraph-cli/trustgraph/cli/invoke_document_embeddings.py`
`trustgraph-cli/trustgraph/cli/save_doc_embeds.py`
`trustgraph-cli/trustgraph/cli/load_doc_embeds.py`

## יתרונות

1. מקור יחיד לאמת - טקסט החלקים נמצא רק ב-"Garage".
2. הפחתת נפח האחסון של מאגר הווקטורים.
3. מאפשר מעקב אחר מקור המידע בזמן השאילתה באמצעות מזהה החלק (chunk_id).
