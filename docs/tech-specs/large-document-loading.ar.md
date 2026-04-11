# المواصفات الفنية لتحميل المستندات الكبيرة

## نظرة عامة

تتناول هذه المواصفات مشكلات قابلية التوسع وتجربة المستخدم عند تحميل
المستندات الكبيرة في TrustGraph. تعالج البنية الحالية تحميل المستندات
كعملية ذرية واحدة، مما يتسبب في ضغط الذاكرة في نقاط متعددة في
المسار ولا يوفر أي ملاحظات أو خيارات استرداد للمستخدمين.

تستهدف هذه التنفيذ حالات الاستخدام التالية:

1. **معالجة ملفات PDF الكبيرة**: تحميل ومعالجة ملفات PDF متعددة الميجابايت
   دون استنفاد الذاكرة
2. **التحميل القابل للاستئناف**: السماح للتحميلات المتقطعة بمواصلة من حيث
   توقفت بدلاً من إعادة البدء
3. **ملاحظات التقدم**: تزويد المستخدمين برؤية في الوقت الفعلي لعملية التحميل
   والمعالجة
4. **معالجة فعالة للذاكرة**: معالجة المستندات بطريقة متدفقة
   دون الاحتفاظ بملفات كاملة في الذاكرة

## الأهداف

**التحميل التدريجي**: دعم تحميل المستندات على شكل أجزاء عبر REST و WebSocket
**التحويلات القابلة للاستئناف**: تمكين الاسترداد من التحميلات المتقطعة
**رؤية التقدم**: توفير ملاحظات حول تقدم التحميل/المعالجة للعملاء
**كفاءة الذاكرة**: القضاء على التخزين المؤقت للمستند بأكمله في جميع أنحاء المسار
**التوافق مع الإصدارات السابقة**: تظل سير العمل الحالية للمستندات الصغيرة دون تغيير
**المعالجة المتدفقة**: تعمل فك ترميز PDF وتقطيع النص على التدفقات

## الخلفية

### البنية الحالية

يمر تدفق إرسال المستندات عبر المسار التالي:

1. يرسل **العميل** المستند عبر REST (`POST /api/v1/librarian`) أو WebSocket
2. يتلقى **بوابة API** الطلب الكامل مع محتوى المستند المشفر بـ base64
3. يترجم **LibrarianRequestor** الطلب إلى رسالة Pulsar
4. يتلقى **خدمة Librarian** الرسالة، ويفك تشفير المستند في الذاكرة
5. يقوم **BlobStore** بتحميل المستند إلى Garage/S3
6. تخزن **Cassandra** البيانات الوصفية مع مرجع الكائن
7. للمعالجة: يتم استرداد المستند من S3، وفك ترميزه، وتقطيعه - كل ذلك في الذاكرة

الملفات الرئيسية:
نقطة الدخول REST/WebSocket: `trustgraph-flow/trustgraph/gateway/service.py`
النواة الأساسية لـ Librarian: `trustgraph-flow/trustgraph/librarian/librarian.py`
تخزين الكائنات الثنائية: `trustgraph-flow/trustgraph/librarian/blob_store.py`
جداول Cassandra: `trustgraph-flow/trustgraph/tables/library.py`
مخطط API: `trustgraph-base/trustgraph/schema/services/library.py`

### القيود الحالية

تحتوي التصميم الحالي على عدة مشكلات مركبة في الذاكرة وتجربة المستخدم:

1. **عملية تحميل ذرية**: يجب إرسال المستند بأكمله في
   طلب واحد. تتطلب المستندات الكبيرة طلبات طويلة الأمد بدون
   مؤشر للتقدم ولا توجد آلية لإعادة المحاولة في حالة فشل الاتصال.

2. **تصميم API**: تتوقع كل من واجهات برمجة تطبيقات REST و WebSocket المستند
   بأكمله في رسالة واحدة. يحتوي المخطط (`LibrarianRequest`) على `content`
   حقل واحد يحتوي على المستند المشفر بـ base64 بأكمله.

3. **ذاكرة Librarian**: تقوم خدمة Librarian بفك تشفير المستند بأكمله
   في الذاكرة قبل تحميله إلى S3. بالنسبة لملف PDF بحجم 500 ميجابايت، هذا يعني
   الاحتفاظ بـ 500 ميجابايت + في ذاكرة العملية.

4. **ذاكرة فك ترميز PDF**: عند بدء المعالجة، يقوم فك ترميز PDF بتحميل
   ملف PDF بأكمله في الذاكرة لاستخراج النص. تتطلب مكتبات PyPDF وما شابه ذلك
   عادةً الوصول إلى المستند بأكمله.

5. **ذاكرة القطع**: يتلقى برنامج القطع النص المستخرج بالكامل
   ويحتفظ به في الذاكرة أثناء إنتاج الأجزاء.

**مثال على تأثير الذاكرة** (ملف PDF بحجم 500 ميجابايت):
البوابة: ~700 ميجابايت (نفقات ترميز base64)
Librarian: ~500 ميجابايت (بايت مُفككة)
فك ترميز PDF: ~500 ميجابايت + مخازن مؤقتة للاستخراج
القطع: نص مستخرج (متغير، قد يصل إلى 100 ميجابايت +)

يمكن أن تتجاوز الذاكرة القصوى لملف مستند كبير واحد 2 جيجابايت.

## التصميم الفني

### مبادئ التصميم

1. **واجهة API**: يمر كل تفاعل عميل من خلال واجهة برمجة تطبيقات Librarian. العملاء
   ليس لديهم وصول مباشر أو معرفة بالتخزين الأساسي S3/Garage.

2. **تحميل متعدد الأجزاء لـ S3**: استخدم تحميل متعدد الأجزاء قياسي لـ S3.
   هذا مدعوم على نطاق واسع في الأنظمة المتوافقة مع S3 (AWS S3، MinIO، Garage،
   Ceph، DigitalOcean Spaces، Backblaze B2، إلخ) مما يضمن إمكانية النقل.

3. **الإكمال الذري**: عمليات تحميل متعددة الأجزاء لـ S3 ذرية بطبيعتها - يتم تحميل
   الأجزاء التي تم تحميلها والتي لا تظهر حتى يتم استدعاء `CompleteMultipartUpload`. لا توجد
   ملفات مؤقتة أو عمليات إعادة تسمية مطلوبة.

4. **حالة قابلة للتتبع**: يتم تتبع جلسات التحميل في Cassandra، مما يوفر
   رؤية للتحميلات غير المكتملة ويمكنه تمكين إمكانية الاستئناف.

### تدفق التحميل المقسم

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

العميل لا يتفاعل أبدًا مع S3 مباشرةً. يقوم المكتبار بترجمة البيانات بين
واجهة برمجة التطبيقات الخاصة بنا لتحميل البيانات على أجزاء و عمليات S3 متعددة الأجزاء داخليًا.

### عمليات واجهة برمجة التطبيقات الخاصة بالمكتبار

#### `begin-upload`

تهيئة جلسة تحميل بيانات على أجزاء.

الطلب:
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

الرد:
```json
{
  "upload-id": "upload-abc-123",
  "chunk-size": 5242880,
  "total-chunks": 100
}
```

أمين المكتبة:
1. يقوم بإنشاء رمز فريد `upload_id` و `object_id` (معرف فريد لتخزين الكائنات)
2. يستدعي S3 `CreateMultipartUpload`، ويتلقى `s3_upload_id`
3. يقوم بإنشاء سجل جلسة في Cassandra
4. يعيد `upload_id` إلى العميل

#### `upload-chunk`

تحميل جزء واحد.

الطلب:
```json
{
  "operation": "upload-chunk",
  "upload-id": "upload-abc-123",
  "chunk-index": 0,
  "content": "<base64-encoded-chunk>"
}
```

الرد:
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

أمين المكتبة:
1. البحث عن الجلسة باستخدام `upload_id`
2. التحقق من الملكية (يجب أن يتطابق المستخدم مع منشئ الجلسة)
3. استدعاء S3 `UploadPart` مع بيانات الجزء، وتلقي `etag`
4. تحديث سجل الجلسة بفهرس الجزء وعلامة etag
5. إرجاع التقدم إلى العميل

يمكن إعادة محاولة الأجزاء الفاشلة - فقط أرسل `chunk-index` مرة أخرى.

#### `complete-upload`

إنهاء التحميل وإنشاء المستند.

الطلب:
```json
{
  "operation": "complete-upload",
  "upload-id": "upload-abc-123"
}
```

الرد:
```json
{
  "document-id": "doc-123",
  "object-id": "550e8400-e29b-41d4-a716-446655440000"
}
```

أمين المكتبة:
1. يبحث عن الجلسة، ويتحقق من استلام جميع الأجزاء.
2. يستدعي S3 `CompleteMultipartUpload` مع علامات الجزء (S3 تدمج الأجزاء داخليًا - لا توجد تكلفة ذاكرة لأمين المكتبة).
   3. ينشئ سجل مستند في Cassandra مع البيانات الوصفية وإشارة الكائن.
4. يحذف سجل جلسة التحميل.
5. يعيد معرف المستند إلى العميل.
6.

#### `abort-upload`

إلغاء عملية تحميل قيد التقدم.

الطلب:
```json
{
  "operation": "abort-upload",
  "upload-id": "upload-abc-123"
}
```

أمين المكتبة:
1. يستدعي `AbortMultipartUpload` لتنظيف الأجزاء.
2. يحذف سجل الجلسة من Cassandra.

#### `get-upload-status`

حالة استعلام عن عملية تحميل (لإمكانية الاستئناف).

الطلب:
```json
{
  "operation": "get-upload-status",
  "upload-id": "upload-abc-123"
}
```

الرد:
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

عرض قائمة التحميلات غير المكتملة لمستخدم.

الطلب:
```json
{
  "operation": "list-uploads"
}
```

الرد:
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

### تخزين جلسات التحميل

تتبع عمليات التحميل الجارية في Cassandra:

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

**سلوك TTL:**
تنتهي الجلسات بعد 24 ساعة إذا لم تكتمل.
عندما تنتهي صلاحية TTL في Cassandra، يتم حذف سجل الجلسة.
يتم تنظيف أجزاء S3 المهجورة بواسطة سياسة دورة حياة S3 (يتم التكوين على الحاوية).

### معالجة الأخطاء والتماسك

**فشل تحميل الأجزاء:**
يحاول العميل إعادة تحميل الجزء الذي فشل (بنفس `upload_id` و `chunk-index`).
عملية S3 `UploadPart` متسقة لنفس رقم الجزء.
تتتبع الجلسة الأجزاء التي نجحت.

**انقطاع اتصال العميل أثناء التحميل:**
تظل الجلسة موجودة في Cassandra مع تسجيل الأجزاء المستلمة.
يمكن للعميل استدعاء `get-upload-status` لمعرفة ما هو مفقود.
يمكن استئناف التحميل عن طريق تحميل الأجزاء المفقودة فقط، ثم `complete-upload`.

**فشل التحميل الكامل:**
عملية S3 `CompleteMultipartUpload` ذرية - إما أنها تنجح بالكامل أو تفشل.
في حالة الفشل، تظل الأجزاء موجودة ويمكن للعميل إعادة محاولة `complete-upload`.
لا يمكن رؤية أي مستند جزئي على الإطلاق.

**انتهاء صلاحية الجلسة:**
تحذف Cassandra سجل الجلسة بعد 24 ساعة.
تقوم سياسة دورة حياة حاوية S3 بتنظيف عمليات التحميل متعددة الأجزاء غير المكتملة.
لا يلزم أي تنظيف يدوي.

### تماسك S3 متعدد الأجزاء

توفر عمليات تحميل S3 متعددة الأجزاء تماسكًا مدمجًا:

1. **الأجزاء غير مرئية**: لا يمكن الوصول إلى الأجزاء التي تم تحميلها ككائنات.
   إنها موجودة فقط كأجزاء من عملية تحميل متعددة الأجزاء غير مكتملة.

2. **الإكمال الذري**: `CompleteMultipartUpload` إما أنها تنجح (يظهر الكائن بشكل ذري) أو تفشل (لا يتم إنشاء كائن). لا توجد حالة جزئية.
   

3. **لا حاجة لإعادة التسمية**: يتم تحديد مفتاح الكائن النهائي في وقت
   `CreateMultipartUpload`. يتم دمج الأجزاء مباشرة في هذا المفتاح.

4. **الدمج من جانب الخادم**: تقوم S3 بدمج الأجزاء داخليًا. لا يقرأ أمين المكتبة
   الأجزاء مرة أخرى - لا توجد تكلفة إضافية للذاكرة بغض النظر عن حجم المستند.

### امتدادات BlobStore

**الملف:** `trustgraph-flow/trustgraph/librarian/blob_store.py`

أضف طرق التحميل متعددة الأجزاء:

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

### اعتبارات حجم الجزء

**الحد الأدنى لـ S3**: 5 ميجابايت لكل جزء (باستثناء الجزء الأخير)
**الحد الأقصى لـ S3**: 10,000 جزء لكل عملية تحميل
**الإعداد الافتراضي العملي**: أجزاء بحجم 5 ميجابايت
  مستند بحجم 500 ميجابايت = 100 جزء
  مستند بحجم 5 جيجابايت = 1,000 جزء
**دقة التقدم**: أجزاء أصغر = تحديثات تقدم أكثر دقة
**كفاءة الشبكة**: أجزاء أكبر = عدد أقل من عمليات الإرسال

يمكن تكوين حجم الجزء من قبل العميل ضمن الحدود (5 ميجابايت - 100 ميجابايت).

### معالجة المستندات: الاسترجاع المتدفق

يهدف سير عمل التحميل إلى إدخال المستندات إلى التخزين بكفاءة. يهدف سير عمل المعالجة إلى استخراج وتقسيم المستندات دون تحميلها بالكامل في الذاكرة.


#### مبدأ التصميم: المعرف، وليس المحتوى


حاليًا، عند بدء المعالجة، يتدفق محتوى المستند عبر رسائل Pulsar. يؤدي هذا إلى تحميل المستندات بأكملها في الذاكرة. بدلاً من ذلك:


تحمل رسائل Pulsar فقط **معرف المستند**
تقوم المعالجات باسترداد محتوى المستند مباشرة من المكتبة
يتم الاسترداد كـ **تدفق إلى ملف مؤقت**
يعمل التحليل الخاص بالمستند (PDF، نص، إلخ) مع الملفات، وليس مخازن الذاكرة

هذا يجعل المكتبة غير معتمدة على هيكل المستند. يظل تحليل PDF واستخراج النص ومنطق محدد التنسيق الأخرى في فك التشفير الخاص بها.


#### سير المعالجة

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

#### واجهة برمجة تطبيقات (API) لخدمة أمين المكتبة.

إضافة عملية استرجاع مستندات متدفقة:

**`stream-document`**

الطلب:
```json
{
  "operation": "stream-document",
  "document-id": "doc-123"
}
```

الاستجابة: أجزاء ثنائية متدفقة (وليست استجابة واحدة).

بالنسبة لواجهة برمجة التطبيقات REST، فإن هذا يُرجع استجابة متدفقة مع `Transfer-Encoding: chunked`.

بالنسبة للمكالمات الداخلية بين الخدمات (من المعالج إلى أمين المكتبة)، يمكن أن يكون ذلك:
بث مباشر من S3 عبر عنوان URL مسبق التوقيع (إذا سمحت الشبكة الداخلية بذلك).
استجابات مقسمة عبر بروتوكول الخدمة.
نقطة نهاية مخصصة للبث.

المتطلب الأساسي: تتدفق البيانات في أجزاء، ولا يتم تخزينها بالكامل مؤقتًا في أمين المكتبة.

#### تغييرات في فك ترميز PDF.

**التنفيذ الحالي** (يستهلك الكثير من الذاكرة):

```python
def decode_pdf(document_content: bytes) -> str:
    reader = PdfReader(BytesIO(document_content))  # full doc in memory
    text = ""
    for page in reader.pages:
        text += page.extract_text()  # accumulating
    return text  # full text in memory
```

**تنفيذ جديد** (ملف مؤقت، تدريجي):

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

ملف تعريف الذاكرة:
ملف مؤقت على القرص: حجم ملف PDF (القرص رخيص).
في الذاكرة: صفحة واحدة من النص في كل مرة.
أقصى استخدام للذاكرة: محدود، ولا يعتمد على حجم المستند.

#### تغييرات في وحدة فك ترميز المستندات النصية.

بالنسبة للمستندات النصية العادية، الأمر أبسط حتى - لا حاجة لملف مؤقت:

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

يمكن لملفات النصوص أن تُرسل مباشرةً دون الحاجة إلى ملف مؤقت نظرًا لأنها
مُنظمة بشكل خطي.

#### تكامل وحدة تقسيم البيانات (Chunker).

تتلقى وحدة تقسيم البيانات مُكررًا للنصوص (صفحات أو فقرات) وتُنتج
أجزاء بشكل تدريجي:

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

#### خط أنابيب المعالجة الشاملة

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

في أي نقطة، لا يتم الاحتفاظ بالمستند الكامل أو النص المستخرج بالكامل في الذاكرة.

#### اعتبارات ملفات مؤقتة

**الموقع**: استخدم دليل النظام المؤقت (`/tmp` أو ما يعادله). بالنسبة إلى
عمليات النشر في حاويات، تأكد من أن الدليل المؤقت لديه مساحة كافية
وأنه موجود على مساحة تخزين سريعة (وليس مثبتًا على الشبكة إن أمكن).

**التنظيف**: استخدم مديري السياق (`with tempfile...`) لضمان التنظيف
حتى في حالة حدوث استثناءات.

**المعالجة المتزامنة**: تحصل كل مهمة معالجة على ملف مؤقت خاص بها.
لا توجد تعارضات بين معالجة المستندات المتوازية.

**مساحة القرص**: الملفات المؤقتة قصيرة الأجل (مدة المعالجة). بالنسبة إلى
ملف PDF بحجم 500 ميجابايت، يلزم وجود مساحة مؤقتة تبلغ 500 ميجابايت أثناء المعالجة. يمكن
تطبيق حد الحجم في وقت التحميل إذا كانت مساحة القرص محدودة.

### واجهة المعالجة الموحدة: المستندات الفرعية

يجب أن تساهم عملية استخراج PDF ومعالجة المستندات النصية في نفس
خط المعالجة اللاحق (تقسيم إلى أجزاء → تضمينات → تخزين). لتحقيق ذلك باستخدام
واجهة "جلب حسب المعرف" متسقة، يتم تخزين كتل النص المستخرجة مرة أخرى
في المكتبة كمستندات فرعية.

#### سير العمل مع المستندات الفرعية

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

تمتلك وحدة التقسيم واجهة موحدة واحدة:
استقبال معرف المستند (عبر Pulsar)
تدفق المحتوى من أمين المكتبة
تقسيم المحتوى

لا تعرف أو تهتم ما إذا كان المعرف يشير إلى:
مستند نصي تم تحميله بواسطة المستخدم
جزء نصي مستخرج من صفحة PDF
أي نوع مستند مستقبلي

#### بيانات وصفية للمستندات الفرعية

قم بتوسيع مخطط المستند لتتبع العلاقات بين المستندات الرئيسية والفرعية:

```sql
-- Add columns to document table
ALTER TABLE document ADD parent_id text;
ALTER TABLE document ADD document_type text;

-- Index for finding children of a parent
CREATE INDEX document_parent ON document (parent_id);
```

**أنواع المستندات:**

| `document_type` | الوصف |
|-----------------|-------------|
| `source` | مستند تم تحميله بواسطة المستخدم (PDF، نص، إلخ) |
| `extracted` | مشتق من مستند مصدر (مثل نص صفحة PDF) |

**حقول البيانات الوصفية:**

| الحقل | المستند المصدر | المستند الفرعي المستخرج |
|-------|-----------------|-----------------|
| `id` | مقدم من المستخدم أو تم إنشاؤه | تم إنشاؤه (مثل `{parent-id}-page-{n}`) |
| `parent_id` | `NULL` | معرف المستند الأصل |
| `document_type` | `source` | `extracted` |
| `kind` | `application/pdf`، إلخ. | `text/plain` |
| `title` | مقدم من المستخدم | تم إنشاؤه (مثل "الصفحة 3 من Report.pdf") |
| `user` | مستخدم مصرح له | نفس المستند الأصل |

#### واجهة برمجة تطبيقات أمين المكتبة للمستندات الفرعية

**إنشاء المستندات الفرعية** (داخلي، يستخدم بواسطة pdf-extractor):

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

بالنسبة للنصوص الصغيرة المستخرجة (عادةً ما يكون نص الصفحة أقل من 100 كيلوبايت)، فإن التحميل في عملية واحدة مقبول. بالنسبة لاستخراج النصوص الكبيرة جدًا، يمكن استخدام التحميل المقسم.

**عرض المستندات الفرعية** (لأغراض التصحيح/الإدارة):

**عرض المستندات الفرعية** (لأغراض التصحيح/الإدارة):

```json
{
  "operation": "list-children",
  "parent-id": "doc-123"
}
```

الرد:
```json
{
  "children": [
    { "id": "doc-123-page-1", "title": "Page 1", "kind": "text/plain" },
    { "id": "doc-123-page-2", "title": "Page 2", "kind": "text/plain" },
    ...
  ]
}
```

#### السلوك الظاهر للمستخدم

**السلوك الافتراضي `list-documents`:**

```sql
SELECT * FROM document WHERE user = ? AND parent_id IS NULL;
```

تظهر فقط المستندات الرئيسية (المصدر) في قائمة المستندات الخاصة بالمستخدم.
يتم استبعاد المستندات الفرعية افتراضيًا.

**علامة "include-children" اختيارية** (للمسؤولين/تصحيح الأخطاء):

```json
{
  "operation": "list-documents",
  "include-children": true
}
```

#### حذف متسلسل

عندما يتم حذف مستند رئيسي، يجب حذف جميع العناصر التابعة له:

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

#### اعتبارات التخزين

النصوص المستخرجة قد تتضمن تكرارًا للمحتوى:
ملف PDF الأصلي مُخزن في "Garage".
النص المستخرج لكل صفحة مُخزن أيضًا في "Garage".

هذا الحل يتيح:
**واجهة موحدة للتقطيع**: يقوم "Chunker" دائمًا باسترداد البيانات بمعرف (ID).
**الاستئناف/إعادة المحاولة**: يمكن إعادة تشغيل العملية في مرحلة "Chunker" دون إعادة استخراج ملف PDF.
**تصحيح الأخطاء**: يمكن فحص النص المستخرج.
**فصل المهام**: خدمة استخراج ملف PDF وخدمة "Chunker" هما خدمتان مستقلتان.

بالنسبة لملف PDF بحجم 500 ميجابايت و200 صفحة بمتوسط 5 كيلوبايت من النص لكل صفحة:
تخزين ملف PDF: 500 ميجابايت.
تخزين النص المستخرج: حوالي 1 ميجابايت إجمالاً.
التكلفة الإضافية: ضئيلة.

#### مخرجات مُستخرج ملف PDF

يقوم مُستخرج ملف PDF (pdf-extractor)، بعد معالجة المستند:

1. يقوم بتحميل ملف PDF من "librarian" إلى ملف مؤقت.
2. يستخرج النص صفحةً تلو الأخرى.
3. لكل صفحة، يقوم بتخزين النص المستخرج كمستند فرعي عبر "librarian".
4. يرسل معرفات المستندات الفرعية إلى قائمة انتظار "Chunker".

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

يتلقى المعالج هذه المعرفات الفرعية ويقوم بمعالجتها بنفس الطريقة التي يعالج بها مستند نصي تم تحميله بواسطة المستخدم.
كيف كان سيعالجها.

### تحديثات العميل

#### حزمة تطوير البرمجيات (SDK) بلغة بايثون

يجب أن تتعامل حزمة تطوير البرمجيات (SDK) بلغة بايثون (`trustgraph-base/trustgraph/api/library.py`) مع عمليات التحميل المقسمة بشفافية. يظل الواجهة العامة دون تغيير:


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

داخليًا، يكتشف الـ SDK حجم المستند ويغير الاستراتيجية:

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

**استدعاءات ردود الأفعال للتقدم** (تحسين اختياري):

```python
def add_document(self, ..., on_progress=None):
    """
    on_progress: Optional callback(bytes_sent, total_bytes)
    """
```

هذا يسمح لواجهات المستخدم بعرض تقدم التحميل دون تغيير واجهة برمجة التطبيقات الأساسية.

#### أدوات سطر الأوامر

**`tg-add-library-document`** يستمر في العمل دون تغيير:

```bash
# Works transparently for any size - SDK handles chunking internally
tg-add-library-document --file large-report.pdf --title "Large Report"
```

يمكن إضافة عرض اختياري للتقدم:

```bash
tg-add-library-document --file large-report.pdf --title "Large Report" --progress
# Output:
# Uploading: 45% (225MB / 500MB)
```

**تمت إزالة الأدوات القديمة:**

`tg-load-pdf` - قديمة، استخدم `tg-add-library-document`
`tg-load-text` - قديمة، استخدم `tg-add-library-document`

**أوامر الإدارة/التصحيح** (اختياري، أولوية منخفضة):

```bash
# List incomplete uploads (admin troubleshooting)
tg-add-library-document --list-pending

# Resume specific upload (recovery scenario)
tg-add-library-document --resume upload-abc-123 --file large-report.pdf
```

قد تكون هذه خيارات في الأمر الحالي بدلاً من أدوات منفصلة.

#### تحديثات مواصفات واجهة برمجة التطبيقات (API)

تحتاج مواصفات OpenAPI (`specs/api/paths/librarian.yaml`) إلى تحديثات فيما يلي:

**عمليات جديدة:**

`begin-upload` - تهيئة جلسة تحميل مقسمة
`upload-chunk` - تحميل جزء فردي
`complete-upload` - إنهاء التحميل
`abort-upload` - إلغاء التحميل
`get-upload-status` - الاستعلام عن تقدم التحميل
`list-uploads` - قائمة بالتحميلات غير المكتملة للمستخدم
`stream-document` - استرجاع المستندات المتدفقة
`add-child-document` - تخزين النص المستخرج (داخلي)
`list-children` - قائمة بالمستندات الفرعية (للمسؤول)

**عمليات معدلة:**

`list-documents` - إضافة معلمة `include-children`

**مخططات جديدة:**

`ChunkedUploadBeginRequest`
`ChunkedUploadBeginResponse`
`ChunkedUploadChunkRequest`
`ChunkedUploadChunkResponse`
`UploadSession`
`UploadProgress`

**تحديثات مواصفات WebSocket** (`specs/websocket/`):

قم بمحاكاة العمليات REST لعملاء WebSocket، مما يتيح تحديثات التقدم في الوقت الفعلي
أثناء التحميل.

#### اعتبارات تجربة المستخدم (UX)

تتيح تحديثات مواصفات واجهة برمجة التطبيقات (API) تحسينات في الواجهة الأمامية:

**واجهة مستخدم لتقدم التحميل:**
شريط تقدم يوضح الأجزاء التي تم تحميلها
الوقت المقدر المتبقي
إمكانية الإيقاف المؤقت/الاستئناف

**استعادة الأخطاء:**
خيار "استئناف التحميل" للتحميلات المتقطعة
قائمة بالتحميلات المعلقة عند إعادة الاتصال

**التعامل مع الملفات الكبيرة:**
اكتشاف حجم الملف من جانب العميل
تحميل مقسم تلقائي للملفات الكبيرة
ملاحظات واضحة أثناء عمليات التحميل الطويلة

تتطلب هذه التحسينات في تجربة المستخدم (UX) عملًا في الواجهة الأمامية يتم توجيهه بواسطة مواصفات واجهة برمجة التطبيقات (API) المحدثة.
