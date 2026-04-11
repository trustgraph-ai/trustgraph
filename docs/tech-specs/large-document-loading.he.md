# מפרט טכני לטעינת מסמכים גדולים

## סקירה כללית

מפרט זה עוסק בבעיות של יכולת התרחבות וחוויית משתמש כאשר טוענים
מסמכים גדולים ל-TrustGraph. הארכיטקטורה הנוכחית מתייחסת להעלאת מסמכים
כפעולה אטומית אחת, דבר הגורם ללחץ זיכרון במספר נקודות במערכת
ואינו מספק משוב או אפשרויות התאוששות למשתמשים.

יישום זה מכוון למקרים הבאים:

1. **עיבוד PDF גדול**: העלאה ועיבוד של קבצי PDF בגודל מאות מגה-בייטים
   מבלי למצות את הזיכרון
2. **העלאות ניתנות לחידוש**: אפשרות להמשיך העלאות שהופסקו מאותה נקודה
   במקום להתחיל מחדש
3. **משוב התקדמות**: מתן למשתמשים תצוגה חיה של התקדמות ההעלאה
   והעיבוד
4. **עיבוד חסכוני בזיכרון**: עיבוד מסמכים בצורה רציפה
   מבלי לשמור את כל הקבצים בזיכרון

## מטרות

**העלאה הדרגתית**: תמיכה בהעלאה מקוטעת של מסמכים באמצעות REST ו-WebSocket
**העברות ניתנות לחידוש**: אפשרות להתאושש מהעלאות שהופסקו
**נראות של התקדמות**: מתן משוב על התקדמות ההעלאה/עיבוד ללקוחות
**יעילות זיכרון**: ביטול אחסון מלא של מסמכים לאורך כל המערכת
**תאימות לאחור**: זרימות עבודה קיימות עבור מסמכים קטנים ממשיכות לפעול ללא שינוי
**עיבוד רציף**: פענוח PDF וחלוקת טקסט מתבצעות על זרמים

## רקע

### ארכיטקטורה נוכחית

זרימת הגשת מסמכים עוברת דרך הנתיב הבא:

1. **לקוח** מגיש מסמך באמצעות REST (`POST /api/v1/librarian`) או WebSocket
2. **שער API** מקבל בקשה שלמה עם תוכן המסמך מקודד ב-base64
3. **LibrarianRequestor** מתרגם את הבקשה להודעת Pulsar
4. **שירות Librarian** מקבל את ההודעה, מפענח את המסמך לזיכרון
5. **BlobStore** מעלה את המסמך ל-Garage/S3
6. **Cassandra** שומר מטא-דאטה עם הפניה לאובייקט
7. לצורך עיבוד: המסמך נשלף מ-S3, מפענח, מחולק - הכל בזיכרון

קבצים מרכזיים:
נקודת כניסה REST/WebSocket: `trustgraph-flow/trustgraph/gateway/service.py`
ליבה של Librarian: `trustgraph-flow/trustgraph/librarian/librarian.py`
אחסון Blob: `trustgraph-flow/trustgraph/librarian/blob_store.py`
טבלאות Cassandra: `trustgraph-flow/trustgraph/tables/library.py`
סכימת API: `trustgraph-base/trustgraph/schema/services/library.py`

### מגבלות נוכחיות

לעיצוב הנוכחי יש מספר בעיות מורכבות של זיכרון וחוויית משתמש:

1. **פעולת העלאה אטומית**: יש להעביר את כל המסמך בבקשה אחת.
   מסמכים גדולים דורשים בקשות ארוכות עם אינדיקציה מועטה להתקדמות
   וללא מנגנון ניסיון חוזר אם החיבור נכשל.

2. **עיצוב API**: גם ממשקי REST וגם WebSocket מצפים לקבל את כל המסמך
   בהודעה אחת. הסכימה (`LibrarianRequest`) כוללת שדה `content`
   יחיד המכיל את תוכן המסמך המקודד ב-base64.

3. **זיכרון של Librarian**: שירות ה-librarian מפענח את כל המסמך
   לזיכרון לפני העלאתו ל-S3. עבור קובץ PDF בגודל 500 מגה-בייטים,
   זה אומר שמירת 500 מגה-בייטים+ בזיכרון התהליך.

4. **זיכרון של מפענח PDF**: כאשר העיבוד מתחיל, מפענח ה-PDF טוען את
   ה-PDF כולו לזיכרון כדי לחלץ טקסט. ספריות כמו PyPDF דורשות
   בדרך כלל גישה מלאה למסמך.

5. **זיכרון של חולק הטקסט**: החולק של הטקסט מקבל את הטקסט
   שחולץ ומחזיק אותו בזיכרון תוך יצירת חלקים.

**דוגמה להשפעה על הזיכרון** (PDF בגודל 500 מגה-בייטים):
Gateway: ~700 מגה-בייטים (עקב קידוד base64)
Librarian: ~500 מגה-בייטים (בייטים מפוענחים)
מפענח PDF: ~500 מגה-בייטים + חוצצים לחילוץ
חולק: טקסט שחולץ (משתנה, פוטנציאלית 100 מגה-בייטים+)

הזיכרון המקסימלי יכול לעלות על 2 ג'יגה-בייטים עבור מסמך גדול יחיד.

## עיצוב טכני

### עקרונות עיצוב

1. **ממשק API**: כל האינטראקציות עם הלקוח עוברות דרך ה-API של ה-librarian.
   ללקוחות אין גישה ישירה או ידע לגבי אחסון S3/Garage הבסיסי.

2. **העלאה מרובת חלקים של S3**: שימוש בהעלאה מרובת חלקים סטנדרטית של S3.
   זה נתמך באופן נרחב במערכות התואמות ל-S3 (AWS S3, MinIO, Garage,
   Ceph, DigitalOcean Spaces, Backblaze B2 וכו') ומבטיח ניידות.

3. **השלמה אטומית**: העלאות מרובות חלקים של S3 הן מטבען אטומיות - חלקים שהועלו
   אינם גלויים עד ש-`CompleteMultipartUpload` נקרא. אין צורך בקבצים זמניים או פעולות
   שינוי שם.

4. **מצב הניתן למעקב**: סשנים של העלאה נרשמים ב-Cassandra ומאפשרים
   התאוששות במקרה של כשל.



```
Client                    Librarian API                   S3/Garage
  │                            │                              │
  │── begin-upload ───────────►│                              │
  │   (metadata, size)         │── CreateMultipartUpload ────►│
  │                            │◄── s3_upload_id ─────────────│
  │◄── upload_id ──────────────│   (store session in          │
  │                            │    Cassandra)                │
  │                            │                              │
  │── upload-chunk ───────────►│                              │
  │   (upload_id, index, data) │── UploadPart ───────────────►│
  │                            │◄── etag ─────────────────────│
  │◄── ack + progress ─────────│   (store etag in session)    │
  │         ⋮                  │         ⋮                    │
  │   (repeat for all chunks)  │                              │
  │                            │                              │
  │── complete-upload ────────►│                              │
  │   (upload_id)              │── CompleteMultipartUpload ──►│
  │                            │   (parts coalesced by S3)    │
  │                            │── store doc metadata ───────►│ Cassandra
  │◄── document_id ────────────│   (delete session)           │
```

הלקוח לעולם אינו מתקשר ישירות עם S3. הספרן מתרגם בין
ממשק ההעלאה המקוטעת שלנו לפעולות ה-multipart של S3 באופן פנימי.

### פעולות ממשק ה-API של הספרן

#### `begin-upload`

אתחול סשן העלאה מקוטעת.

בקשה:
```json
{
  "operation": "begin-upload",
  "document-metadata": {
    "id": "doc-123",
    "kind": "application/pdf",
    "title": "Large Document",
    "user": "user-id",
    "tags": ["tag1", "tag2"]
  },
  "total-size": 524288000,
  "chunk-size": 5242880
}
```

תגובה:
```json
{
  "upload-id": "upload-abc-123",
  "chunk-size": 5242880,
  "total-chunks": 100
}
```

הספרן:
1. מייצר `upload_id` ו-`object_id` ייחודיים (UUID עבור אחסון בלובים).
2. קורא ל-S3 `CreateMultipartUpload`, מקבל `s3_upload_id`.
3. יוצר רשומת סשן ב-Cassandra.
4. מחזיר `upload_id` ללקוח.

#### `upload-chunk`

העלאת מקטע בודד.

בקשה:
```json
{
  "operation": "upload-chunk",
  "upload-id": "upload-abc-123",
  "chunk-index": 0,
  "content": "<base64-encoded-chunk>"
}
```

תגובה:
```json
{
  "upload-id": "upload-abc-123",
  "chunk-index": 0,
  "chunks-received": 1,
  "total-chunks": 100,
  "bytes-received": 5242880,
  "total-bytes": 524288000
}
```

הספרן:
1. מחפש את הסשן לפי `upload_id`
2. מאמת בעלות (המשתמש חייב להתאים ליוצר הסשן)
3. קורא ל-S3 `UploadPart` עם נתוני החלק, מקבל `etag`
4. מעדכן את רשומת הסשן עם אינדקס החלק ו-etag
5. מחזיר התקדמות ללקוח

חלקים שנכשלו ניתנים לניסיון חוזר - פשוט שלחו שוב את `chunk-index`.

#### `complete-upload`

השלמת ההעלאה ויצירת המסמך.

בקשה:
```json
{
  "operation": "complete-upload",
  "upload-id": "upload-abc-123"
}
```

תגובה:
```json
{
  "document-id": "doc-123",
  "object-id": "550e8400-e29b-41d4-a716-446655440000"
}
```

הספרן:
1. מחפש את הסשן, מוודא שכל החלקים התקבלו.
2. קורא ל-S3 `CompleteMultipartUpload` עם תגיות חלק (S3 ממזגת חלקים
   באופן פנימי - אין עלות זיכרון לספרן).
3. יוצר רשומת מסמך ב-Cassandra עם מטא-דאטה והפניה לאובייקט.
4. מוחק את רשומת סשן ההעלאה.
5. מחזיר את מזהה המסמך ללקוח.

#### `abort-upload`

ביטול העלאה בתהליך.

בקשה:
```json
{
  "operation": "abort-upload",
  "upload-id": "upload-abc-123"
}
```

הספרן:
1. מתקשר ל-S3 `AbortMultipartUpload` כדי לנקות חלקים.
2. מוחק את רשומת הסשן מ-Cassandra.

#### `get-upload-status`

בדיקת סטטוס של העלאה (לצורך אפשרות המשך).

בקשה:
```json
{
  "operation": "get-upload-status",
  "upload-id": "upload-abc-123"
}
```

תגובה:
```json
{
  "upload-id": "upload-abc-123",
  "state": "in-progress",
  "chunks-received": [0, 1, 2, 5, 6],
  "missing-chunks": [3, 4, 7, 8],
  "total-chunks": 100,
  "bytes-received": 36700160,
  "total-bytes": 524288000
}
```

#### `list-uploads`

הצגת רשימה של העלאות חסרות השלמה עבור משתמש.

בקשה:
```json
{
  "operation": "list-uploads"
}
```

תגובה:
```json
{
  "uploads": [
    {
      "upload-id": "upload-abc-123",
      "document-metadata": { "title": "Large Document", ... },
      "progress": { "chunks-received": 43, "total-chunks": 100 },
      "created-at": "2024-01-15T10:30:00Z"
    }
  ]
}
```

### אחסון סשן העלאה

מעקב אחר העלאות בתהליך ב-Cassandra:

```sql
CREATE TABLE upload_session (
    upload_id text PRIMARY KEY,
    user text,
    document_id text,
    document_metadata text,      -- JSON: title, kind, tags, comments, etc.
    s3_upload_id text,           -- internal, for S3 operations
    object_id uuid,              -- target blob ID
    total_size bigint,
    chunk_size int,
    total_chunks int,
    chunks_received map<int, text>,  -- chunk_index → etag
    created_at timestamp,
    updated_at timestamp
) WITH default_time_to_live = 86400;  -- 24 hour TTL

CREATE INDEX upload_session_user ON upload_session (user);
```

**התנהגות TTL:**
סשנים פוקעים לאחר 24 שעות אם לא הושלמו.
כאשר TTL של Cassandra פוקע, רשומת הסשן נמחקת.
חלקים של S3 שנותרו מאחור מנוקים על ידי מדיניות מחזור חיים של S3 (יש להגדיר על ה-bucket).

### טיפול בכשלים ואטומיות

**כשל בהעלאת חלק:**
הלקוח מנסה שוב את החלק שנכשל (באמצעות אותו `upload_id` ו-`chunk-index`).
`UploadPart` של S3 היא פעולה אידempotent עבור אותו מספר חלק.
הסשן עוקב אחר אילו חלקים הצליחו.

**ניתוק לקוח במהלך העלאה:**
הסשן נשאר ב-Cassandra עם החלקים שהתקבלו.
הלקוח יכול לקרוא ל-`get-upload-status` כדי לראות מה חסר.
ניתן לחדש על ידי העלאת רק החלקים החסרים, ולאחר מכן `complete-upload`.

**כשל בהעלאה מלאה:**
`CompleteMultipartUpload` של S3 היא פעולה אטומית - או מצליחה לחלוטין או נכשלת.
במקרה של כשל, החלקים נשארים והלקוח יכול לנסות שוב את `complete-upload`.
לא ניתן לראות מסמך חלקי.

**תפוגת הסשן:**
TTL של Cassandra מוחקת את רשומת הסשן לאחר 24 שעות.
מדיניות מחזור חיים של bucket ב-S3 מנקה העלאות מרובות חלקים לא שלמות.
אין צורך בניקוי ידני.

### אטומיות של העלאות מרובות חלקים ב-S3

העלאות מרובות חלקים ב-S3 מספקות אטומיות מובנית:

1. **חלקים אינם גלויים**: חלקים שהועלו לא ניתנים לגישה כאובייקטים.
   הם קיימים רק כחלקים של העלאה מרובת חלקים לא שלמה.

2. **השלמה אטומית**: `CompleteMultipartUpload` מצליחה (האובייקט
   מופיע באופן אטומי) או נכשלת (לא נוצר אובייקט). אין מצב חלקי.

3. **אין צורך בשינוי שם**: המפתח של האובייקט הסופי מצוין בזמן
   `CreateMultipartUpload`. החלקים משולבים ישירות למפתח זה.

4. **שילוב בצד השרת**: S3 משלבת חלקים באופן פנימי. ה-librarian
   לעולם לא קורא בחזרה חלקים - אין עומס זיכרון ללא קשר לגודל המסמך.

### הרחבות BlobStore

**קובץ:** `trustgraph-flow/trustgraph/librarian/blob_store.py`

הוספת שיטות העלאה מרובות חלקים:

```python
class BlobStore:
    # Existing methods...

    def create_multipart_upload(self, object_id: UUID, kind: str) -> str:
        """Initialize multipart upload, return s3_upload_id."""
        # minio client: create_multipart_upload()

    def upload_part(
        self, object_id: UUID, s3_upload_id: str,
        part_number: int, data: bytes
    ) -> str:
        """Upload a single part, return etag."""
        # minio client: upload_part()
        # Note: S3 part numbers are 1-indexed

    def complete_multipart_upload(
        self, object_id: UUID, s3_upload_id: str,
        parts: List[Tuple[int, str]]  # [(part_number, etag), ...]
    ) -> None:
        """Finalize multipart upload."""
        # minio client: complete_multipart_upload()

    def abort_multipart_upload(
        self, object_id: UUID, s3_upload_id: str
    ) -> None:
        """Cancel multipart upload, clean up parts."""
        # minio client: abort_multipart_upload()
```

### שיקולי גודל מקטע

**מינימום עבור S3**: 5MB לכל חלק (למעט החלק האחרון)
**מקסימום עבור S3**: 10,000 חלקים לכל העלאה
**ערך ברירת מחדל מעשי**: מקטעים בגודל 5MB
  מסמך בגודל 500MB = 100 מקטעים
  מסמך בגודל 5GB = 1,000 מקטעים
**גרנולריות של התקדמות**: מקטעים קטנים יותר = עדכוני התקדמות מדויקים יותר
**יעילות רשת**: מקטעים גדולים יותר = פחות מעברים

גודל המקטע יכול להיות מוגדר על ידי הלקוח בטווח מסוים (5MB - 100MB).

### עיבוד מסמכים: אחזור סטרימינג

זרימת ההעלאה מטפלת בהעברת מסמכים לאחסון בצורה יעילה. זרימת העיבוד מטפלת בחילוץ ופיצול מסמכים מבלי לטעון
אותם כולם לזיכרון.


#### עקרון עיצוב: מזהה, לא תוכן

כיום, כאשר עיבוד מופעל, תוכן המסמך זורם באמצעות הודעות Pulsar. זה טוען מסמכים שלמים לזיכרון. במקום זאת:


הודעות Pulsar נושאות רק את **מזהה המסמך**
מעבדים שולפים תוכן מסמך ישירות מהספרן (librarian)
השליפה מתבצעת כ**זרם לקובץ זמני**
ניתוח ספציפי למסמך (PDF, טקסט, וכו') עובד עם קבצים, ולא עם מאגרי זיכרון

זה שומר על כך שהספרן אינו תלוי במבנה המסמך. ניתוח PDF, חילוץ טקסט, ולוגיקה ספציפית אחרת לפורמט נשארים בדקודינג המתאים.


#### זרימת עיבוד

```
Pulsar              PDF Decoder                Librarian              S3
  │                      │                          │                  │
  │── doc-id ───────────►│                          │                  │
  │  (processing msg)    │                          │                  │
  │                      │                          │                  │
  │                      │── stream-document ──────►│                  │
  │                      │   (doc-id)               │── GetObject ────►│
  │                      │                          │                  │
  │                      │◄── chunk ────────────────│◄── stream ───────│
  │                      │   (write to temp file)   │                  │
  │                      │◄── chunk ────────────────│◄── stream ───────│
  │                      │   (append to temp file)  │                  │
  │                      │         ⋮                │         ⋮        │
  │                      │◄── EOF ──────────────────│                  │
  │                      │                          │                  │
  │                      │   ┌──────────────────────────┐              │
  │                      │   │ temp file on disk        │              │
  │                      │   │ (memory stays bounded)   │              │
  │                      │   └────────────┬─────────────┘              │
  │                      │                │                            │
  │                      │   PDF library opens file                    │
  │                      │   extract page 1 text ──►  chunker          │
  │                      │   extract page 2 text ──►  chunker          │
  │                      │         ⋮                                   │
  │                      │   close file                                │
  │                      │   delete temp file                          │
```

#### ממשק API של ספריות

הוספת פעולת שליפה של מסמכים בסטרימינג:

**`stream-document`**

בקשה:
```json
{
  "operation": "stream-document",
  "document-id": "doc-123"
}
```

תגובה: מקטעי נתונים בינאריים (ולא תגובה יחידה).

עבור ממשק API REST, זה מחזיר תגובה סטרימינג עם `Transfer-Encoding: chunked`.

עבור שיחות פנימיות בין שירותים (ממעבד לספרן), זה יכול להיות:
סטרימינג ישיר מ-S3 באמצעות כתובת URL חתומה מראש (אם רשת פנימית מאפשרת זאת).
תגובות מחולקות באמצעות פרוטוקול השירות.
נקודת קצה ייעודית לסטרימינג.

הדרישה העיקרית: הנתונים זורמים במקטעים, ואינם מאוחסנים באופן מלא בזיכרון בספרן.

#### שינויים במפענח PDF

**יישום נוכחי** (דורש משאבים רבים בזיכרון):

```python
def decode_pdf(document_content: bytes) -> str:
    reader = PdfReader(BytesIO(document_content))  # full doc in memory
    text = ""
    for page in reader.pages:
        text += page.extract_text()  # accumulating
    return text  # full text in memory
```

**יישום חדש** (קובץ זמני, מצטבר):

```python
def decode_pdf_streaming(doc_id: str, librarian_client) -> Iterator[str]:
    """Yield extracted text page by page."""

    with tempfile.NamedTemporaryFile(delete=True, suffix='.pdf') as tmp:
        # Stream document to temp file
        for chunk in librarian_client.stream_document(doc_id):
            tmp.write(chunk)
        tmp.flush()

        # Open PDF from file (not memory)
        reader = PdfReader(tmp.name)

        # Yield pages incrementally
        for page in reader.pages:
            yield page.extract_text()

        # tmp file auto-deleted on context exit
```

פרופיל זיכרון:
קובץ זמני בדיסק: גודל קובץ ה-PDF (דיסק זול).
בזיכרון: עמוד טקסט אחד בכל פעם.
שיא זיכרון: מוגבל, בלתי תלוי בגודל המסמך.

#### שינויים במפענח מסמכי טקסט

עבור מסמכי טקסט רגילים, זה אפילו פשוט יותר - אין צורך בקובץ זמני:

```python
def decode_text_streaming(doc_id: str, librarian_client) -> Iterator[str]:
    """Yield text in chunks as it streams from storage."""

    buffer = ""
    for chunk in librarian_client.stream_document(doc_id):
        buffer += chunk.decode('utf-8')

        # Yield complete lines/paragraphs as they arrive
        while '\n\n' in buffer:
            paragraph, buffer = buffer.split('\n\n', 1)
            yield paragraph + '\n\n'

    # Yield remaining buffer
    if buffer:
        yield buffer
```

מסמכי טקסט יכולים לעבור סטרימינג ישירות ללא קובץ זמני מכיוון שהם
בנויים בצורה ליניארית.

#### שילוב עם מודול חלוקה (Chunker)

המודול חלוקה מקבל איטרטור של טקסט (עמודים או פסקאות) ומייצר
חלקים באופן הדרגתי:

```python
class StreamingChunker:
    def __init__(self, chunk_size: int, overlap: int):
        self.chunk_size = chunk_size
        self.overlap = overlap

    def process(self, text_stream: Iterator[str]) -> Iterator[str]:
        """Yield chunks as text arrives."""
        buffer = ""

        for text_segment in text_stream:
            buffer += text_segment

            while len(buffer) >= self.chunk_size:
                chunk = buffer[:self.chunk_size]
                yield chunk
                # Keep overlap for context continuity
                buffer = buffer[self.chunk_size - self.overlap:]

        # Yield remaining buffer as final chunk
        if buffer.strip():
            yield buffer
```

#### צינור עיבוד מקצה לקצה

```python
async def process_document(doc_id: str, librarian_client, embedder):
    """Process document with bounded memory."""

    # Get document metadata to determine type
    metadata = await librarian_client.get_document_metadata(doc_id)

    # Select decoder based on document type
    if metadata.kind == 'application/pdf':
        text_stream = decode_pdf_streaming(doc_id, librarian_client)
    elif metadata.kind == 'text/plain':
        text_stream = decode_text_streaming(doc_id, librarian_client)
    else:
        raise UnsupportedDocumentType(metadata.kind)

    # Chunk incrementally
    chunker = StreamingChunker(chunk_size=1000, overlap=100)

    # Process each chunk as it's produced
    for chunk in chunker.process(text_stream):
        # Generate embeddings, store in vector DB, etc.
        embedding = await embedder.embed(chunk)
        await store_chunk(doc_id, chunk, embedding)
```

בשום שלב לא נשמר המסמך השלם או הטקסט החלץ בזיכרון.

#### שיקולים לגבי קבצי זמניים

**מיקום**: יש להשתמש בספריית הזמנים של המערכת (`/tmp` או מקביל). עבור
פריסות מבוססות קונטיינרים, ודאו שספריית הזמנים מכילה מספיק מקום
ושנמצאת באחסון מהיר (לא מחובר לרשת, אם אפשר).

**ניקוי**: יש להשתמש במנהלי הקשר (context managers) (`with tempfile...`) כדי להבטיח ניקוי
גם במקרה של חריגות.

**עיבוד מקבילי**: כל משימת עיבוד מקבלת קובץ זמני משלה.
אין התנגשויות בין עיבוד מקבילי של מסמכים.

**שטח דיסק**: קבצים זמניים הם קצרי טווח (משך העיבוד). עבור
קובץ PDF בגודל 500MB, נדרש שטח זמני של 500MB במהלך העיבוד. ניתן
לאכוף מגבלת גודל בזמן ההעלאה אם יש מגבלות על שטח הדיסק.

### ממשק עיבוד מאוחד: מסמכים משניים

חילוץ PDF ועיבוד מסמכי טקסט צריכים להזין לאותו
צינור עיבוד המשכיות (chunker → embeddings → storage). כדי להשיג זאת עם
ממשק "שליפה לפי מזהה" עקבי, חלקי טקסט חלצים מאוחסנים בחזרה
ל-librarian כמסמכים משניים.

#### זרימת עיבוד עם מסמכים משניים

```
PDF Document                                         Text Document
     │                                                     │
     ▼                                                     │
pdf-extractor                                              │
     │                                                     │
     │ (stream PDF from librarian)                         │
     │ (extract page 1 text)                               │
     │ (store as child doc → librarian)                    │
     │ (extract page 2 text)                               │
     │ (store as child doc → librarian)                    │
     │         ⋮                                           │
     ▼                                                     ▼
[child-doc-id, child-doc-id, ...]                    [doc-id]
     │                                                     │
     └─────────────────────┬───────────────────────────────┘
                           ▼
                       chunker
                           │
                           │ (receives document ID)
                           │ (streams content from librarian)
                           │ (chunks incrementally)
                           ▼
                    [chunks → embedding → storage]
```

למודול החלוקה יש ממשק אחיד אחד:
קבלת מזהה מסמך (דרך Pulsar)
קבלת תוכן מהספרן
חלוקת התוכן לחלקים

הוא לא יודע או אכפת לו האם המזהה מתייחס ל:
מסמך טקסט שהועלה על ידי משתמש
פיסת טקסט שחולצה מעמוד PDF
כל סוג מסמך עתידי

#### מטא-נתונים של מסמכים משניים

הרחבת הסכימה של המסמך כדי לעקוב אחר קשרים הוריים/משניים:

```sql
-- Add columns to document table
ALTER TABLE document ADD parent_id text;
ALTER TABLE document ADD document_type text;

-- Index for finding children of a parent
CREATE INDEX document_parent ON document (parent_id);
```

**סוגי מסמכים:**

| `document_type` | תיאור |
|-----------------|-------------|
| `source` | מסמך שהועלה על ידי משתמש (PDF, טקסט, וכו') |
| `extracted` | נגזר ממסמך מקור (לדוגמה, טקסט של עמוד PDF) |

**שדות מטא-דאטה:**

| שדה | מסמך מקור | מסמך משני |
|-------|-----------------|-----------------|
| `id` | שסופק על ידי המשתמש או נוצר | נוצר (לדוגמה, `{parent-id}-page-{n}`) |
| `parent_id` | `NULL` | מזהה מסמך הורה |
| `document_type` | `source` | `extracted` |
| `kind` | `application/pdf`, וכו' | `text/plain` |
| `title` | שסופק על ידי המשתמש | נוצר (לדוגמה, "עמוד 3 של Report.pdf") |
| `user` | משתמש מאומת | זהה למסמך הורה |

#### ממשק API של הספרן עבור מסמכים משניים

**יצירת מסמכים משניים** (פנימי, בשימוש על ידי pdf-extractor):

```json
{
  "operation": "add-child-document",
  "parent-id": "doc-123",
  "document-metadata": {
    "id": "doc-123-page-1",
    "kind": "text/plain",
    "title": "Page 1"
  },
  "content": "<base64-encoded-text>"
}
```

עבור טקסט קצר שחולץ (טקסט עמוד טיפוסי הוא פחות מ-100KB), העלאה בפעולה אחת מקובלת. עבור חילוצי טקסט גדולים מאוד, ניתן להשתמש בהעלאה מחולקת.

**רשימת מסמכים משניים** (לצרכי ניפוי באגים/ניהול):

**הצגת מסמכים משניים** (לצרכי ניפוי באגים/ניהול):

```json
{
  "operation": "list-children",
  "parent-id": "doc-123"
}
```

תגובה:
```json
{
  "children": [
    { "id": "doc-123-page-1", "title": "Page 1", "kind": "text/plain" },
    { "id": "doc-123-page-2", "title": "Page 2", "kind": "text/plain" },
    ...
  ]
}
```

#### התנהגות מול המשתמש

**התנהגות ברירת מחדל `list-documents`:**

```sql
SELECT * FROM document WHERE user = ? AND parent_id IS NULL;
```

רק מסמכים ברמה העליונה (מקור) מופיעים ברשימת המסמכים של המשתמש.
מסמכים משניים מסוננים כברירת מחדל.

**דגל "הכללה של תת-מסמכים" אופציונלי** (למנהל/דיבוג):

```json
{
  "operation": "list-documents",
  "include-children": true
}
```

#### מחיקה מדורגת

כאשר מסמך הורה נמחק, יש למחוק את כל הצאצאים:

```python
def delete_document(doc_id: str):
    # Find all children
    children = query("SELECT id, object_id FROM document WHERE parent_id = ?", doc_id)

    # Delete child blobs from S3
    for child in children:
        blob_store.delete(child.object_id)

    # Delete child metadata from Cassandra
    execute("DELETE FROM document WHERE parent_id = ?", doc_id)

    # Delete parent blob and metadata
    parent = get_document(doc_id)
    blob_store.delete(parent.object_id)
    execute("DELETE FROM document WHERE id = ? AND user = ?", doc_id, user)
```

#### שיקולי אחסון

קטעי טקסט שחולצו מכפילים תוכן:
קובץ PDF מקורי מאוחסן ב-"Garage"
טקסט שחולץ לכל עמוד מאוחסן גם ב-"Garage"

פשרה זו מאפשרת:
**ממשק "חיתוך" אחיד**: "חיתוך" תמיד שולף לפי מזהה
**התחלה מחדש/ניסיון חוזר**: ניתן להתחיל בשלב ה-"חיתוך" מבלי לחלץ מחדש את קובץ ה-PDF
**ניפוי שגיאות**: ניתן לבדוק את הטקסט שחולץ
**הפרדת אחריות**: שירות חילוץ ה-PDF ושירות ה-"חיתוך" הם שירותים עצמאיים

עבור קובץ PDF בגודל 500MB עם 200 עמודים, כאשר בממוצע יש 5KB טקסט לעמוד:
אחסון קובץ PDF: 500MB
אחסון טקסט שחולץ: כ-1MB בסך הכל
תקורה: זניחה

#### פלט של מופע חילוץ PDF

מופע חילוץ ה-PDF, לאחר עיבוד מסמך:

1. מוריד את קובץ ה-PDF מה-"librarian" לקובץ זמני
2. מחלץ טקסט עמוד אחר עמוד
3. עבור כל עמוד, שומר את הטקסט שחולץ כמסמך משני דרך ה-"librarian"
4. שולח מזהי מסמכים משניים לתור ה-"chunker"
פלט חוזה (יש לעקוב אחר הפורמט המדויק).
```python
async def extract_pdf(doc_id: str, librarian_client, output_queue):
    """Extract PDF pages and store as child documents."""

    with tempfile.NamedTemporaryFile(delete=True, suffix='.pdf') as tmp:
        # Stream PDF to temp file
        for chunk in librarian_client.stream_document(doc_id):
            tmp.write(chunk)
        tmp.flush()

        # Extract pages
        reader = PdfReader(tmp.name)
        for page_num, page in enumerate(reader.pages, start=1):
            text = page.extract_text()

            # Store as child document
            child_id = f"{doc_id}-page-{page_num}"
            await librarian_client.add_child_document(
                parent_id=doc_id,
                document_id=child_id,
                kind="text/plain",
                title=f"Page {page_num}",
                content=text.encode('utf-8')
            )

            # Send to chunker queue
            await output_queue.send(child_id)
```

המודול שמחלק את הטקסט מקבל את מזהי הילדים הללו ומעבד אותם באופן זהה
לאופן שבו הוא היה מעבד מסמך טקסט שהועלה על ידי משתמש.

### עדכונים עבור הלקוח

#### ערכת פיתוח תוכנה (SDK) עבור Python

ערכת הפיתוח תוכנה (`trustgraph-base/trustgraph/api/library.py`) עבור Python צריכה לטפל
בהעלאות מחולקות בצורה שקופה. הממשק הציבורי נשאר ללא שינוי:

```python
# Existing interface - no change for users
library.add_document(
    id="doc-123",
    title="Large Report",
    kind="application/pdf",
    content=large_pdf_bytes,  # Can be hundreds of MB
    tags=["reports"]
)
```

מבפנים, ה-SDK מזהה את גודל המסמך ועובר לאסטרטגיה אחרת:

```python
class Library:
    CHUNKED_UPLOAD_THRESHOLD = 2 * 1024 * 1024  # 2MB

    def add_document(self, id, title, kind, content, tags=None, ...):
        if len(content) < self.CHUNKED_UPLOAD_THRESHOLD:
            # Small document: single operation (existing behavior)
            return self._add_document_single(id, title, kind, content, tags)
        else:
            # Large document: chunked upload
            return self._add_document_chunked(id, title, kind, content, tags)

    def _add_document_chunked(self, id, title, kind, content, tags):
        # 1. begin-upload
        session = self._begin_upload(
            document_metadata={...},
            total_size=len(content),
            chunk_size=5 * 1024 * 1024
        )

        # 2. upload-chunk for each chunk
        for i, chunk in enumerate(self._chunk_bytes(content, session.chunk_size)):
            self._upload_chunk(session.upload_id, i, chunk)

        # 3. complete-upload
        return self._complete_upload(session.upload_id)
```

**החזרות התקדמות** (שיפור אופציונלי):

```python
def add_document(self, ..., on_progress=None):
    """
    on_progress: Optional callback(bytes_sent, total_bytes)
    """
```

זה מאפשר לממשקים גרפיים להציג את התקדמות ההעלאה מבלי לשנות את ממשק ה-API הבסיסי.

#### כלים עבור שורת הפקודה

**`tg-add-library-document`** ממשיך לעבוד ללא שינוי:

```bash
# Works transparently for any size - SDK handles chunking internally
tg-add-library-document --file large-report.pdf --title "Large Report"
```

ניתן להוסיף תצוגת התקדמות אופציונלית:

```bash
tg-add-library-document --file large-report.pdf --title "Large Report" --progress
# Output:
# Uploading: 45% (225MB / 500MB)
```

**כלים מיושנים הוסרו:**

`tg-load-pdf` - מיושן, השתמשו ב-`tg-add-library-document`
`tg-load-text` - מיושן, השתמשו ב-`tg-add-library-document`

**פקודות ניהול/דיבוג** (אופציונלי, בעדיפות נמוכה):

```bash
# List incomplete uploads (admin troubleshooting)
tg-add-library-document --list-pending

# Resume specific upload (recovery scenario)
tg-add-library-document --resume upload-abc-123 --file large-report.pdf
```

אלו יכולות להיות דגלים בפקודה הקיימת ולא כלים נפרדים.

#### עדכוני מפרט API

יש לעדכן את מפרט OpenAPI (`specs/api/paths/librarian.yaml`) עבור:

**פעולות חדשות:**

`begin-upload` - אתחול סשן העלאה מקוטעת
`upload-chunk` - העלאת חלק בודד
`complete-upload` - השלמת העלאה
`abort-upload` - ביטול העלאה
`get-upload-status` - שאילתת התקדמות העלאה
`list-uploads` - הצגת רשימת העלאות חלקיות עבור משתמש
`stream-document` - אחזור מסמך בסטרימינג
`add-child-document` - אחסון טקסט חילוץ (פנימי)
`list-children` - הצגת רשימת מסמכים ילדים (מנהל מערכת)

**פעולות ששונו:**

`list-documents` - הוספת פרמטר `include-children`

**סכימות חדשות:**

`ChunkedUploadBeginRequest`
`ChunkedUploadBeginResponse`
`ChunkedUploadChunkRequest`
`ChunkedUploadChunkResponse`
`UploadSession`
`UploadProgress`

**עדכוני מפרט WebSocket** (`specs/websocket/`):

שכפול הפעולות REST עבור לקוחות WebSocket, המאפשר עדכונים בזמן אמת
במהלך ההעלאה.

#### שיקולי UX

עדכוני מפרט ה-API מאפשרים שיפורים בחזית המשתמש:

**ממשק התקדמות העלאה:**
סרגל התקדמות המציג חלקים שהועלו
זמן משוער שנותר
אפשרות השהיה/המשך

**התאוששות משגיאות:**
אפשרות "המשך העלאה" עבור העלאות שהופרעו
רשימת העלאות תלויות לאחר חיבור מחדש

**טיפול בקבצים גדולים:**
זיהוי גודל קובץ בצד הלקוח
העלאה מקוטעת אוטומטית עבור קבצים גדולים
משוב ברור במהלך העלאות ארוכות

שיפורי UX אלו דורשים עבודה בצד החזית המשתמש, המונחית על ידי מפרט ה-API המעודכן.
