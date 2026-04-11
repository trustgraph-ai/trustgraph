---
layout: default
title: "المواصفات الفنية لمعالجة الدفعات لخدمة التضمينات (Embeddings)"
parent: "Arabic (Beta)"
---

# المواصفات الفنية لمعالجة الدفعات لخدمة التضمينات (Embeddings)

> **Beta Translation:** This document was translated via Machine Learning and as such may not be 100% accurate. All non-English languages are currently classified as Beta.

## نظرة عامة

تصف هذه المواصفات التحسينات التي ستُجرى على خدمة التضمينات لدعم معالجة الدفعات لعدد كبير من النصوص في طلب واحد. تعالج التنفيذ الحالي النص الواحد في كل مرة، مما يفوّت المزايا الكبيرة في الأداء التي توفرها نماذج التضمين عند معالجة الدفعات.

1. **عدم كفاءة معالجة النصوص الفردية**: يغلف التنفيذ الحالي النصوص الفردية في قائمة، مما يؤدي إلى عدم الاستفادة الكاملة من قدرات الدفعات في FastEmbed.
2. **العبء الزائد لكل طلب نص**: يتطلب كل نص رسالة Pulsar منفصلة، مما يتطلب جولة ذهاب وإياب.
3. **عدم كفاءة استنتاج النموذج**: نماذج التضمين لها عبء ثابت لكل دفعة؛ فإن الدفعات الصغيرة تهدر موارد وحدة معالجة الرسومات (GPU) ووحدة المعالجة المركزية (CPU).
4. **المعالجة التسلسلية في التطبيقات**: تقوم الخدمات الرئيسية بالتكرار على العناصر واستدعاء التضمينات واحدًا تلو الآخر.

## الأهداف

**دعم واجهة برمجة تطبيقات (API) للدفعات**: تمكين معالجة نصوص متعددة في طلب واحد.
**التوافق مع الإصدارات السابقة**: الحفاظ على دعم الطلبات التي تتضمن نصًا واحدًا فقط.
**تحسين كبير في الإنتاجية**: استهداف تحسين في الإنتاجية يتراوح بين 5 إلى 10 مرات للعمليات الجماعية.
**تقليل زمن الوصول لكل نص**: تقليل زمن الوصول المتوسط عند تضمين نصوص متعددة.
**كفاءة الذاكرة**: معالجة الدفعات دون استهلاك مفرط للذاكرة.
**الاستقلالية عن المزود**: دعم التجميع عبر FastEmbed و Ollama ومزودين آخرين.
**تحديث التطبيقات**: تحديث جميع تطبيقات التضمين لاستخدام واجهة برمجة تطبيقات الدفعات عند الإمكان.

## الخلفية

### التنفيذ الحالي - خدمة التضمينات

يُظهر تطبيق التضمينات في `trustgraph-flow/trustgraph/embeddings/fastembed/processor.py` عدم كفاءة كبيرة في الأداء:

```python
# fastembed/processor.py line 56
async def on_embeddings(self, text, model=None):
    use_model = model or self.default_model
    self._load_model(use_model)

    vecs = self.embeddings.embed([text])  # Single text wrapped in list

    return [v.tolist() for v in vecs]
```

**المشاكل:**

1. **حجم الدفعة 1**: طريقة `embed()` في FastEmbed مُحسّنة للمعالجة الدفعية، ولكننا نستدعيها دائمًا مع `[text]` - دفعة بحجم 1.

2. **التكلفة لكل طلب**: كل طلب تضمين يتضمن:
   تسلسل/إلغاء تسلسل رسالة Pulsar.
   زمن انتقال الشبكة.
   تكلفة بدء تشغيل الاستدلال للنموذج.
   تكلفة جدولة المهام غير المتزامنة في Python.

3. **قيود المخطط**: مخطط `EmbeddingsRequest` يدعم نصًا واحدًا فقط:
   ```python
   @dataclass
   class EmbeddingsRequest:
       text: str = ""  # Single text only
   ```

### المستخدمون الحاليون - المعالجة التسلسلية

#### 1. بوابة واجهة برمجة التطبيقات (API Gateway)

**الملف:** `trustgraph-flow/trustgraph/gateway/dispatch/embeddings.py`

تقبل البوابة طلبات تضمين النصوص الفردية عبر HTTP/WebSocket وتوجهها إلى خدمة التضمين. حاليًا، لا يوجد نقطة نهاية للدفعات.

```python
class EmbeddingsRequestor(ServiceRequestor):
    # Handles single EmbeddingsRequest -> EmbeddingsResponse
    request_schema=EmbeddingsRequest,  # Single text only
    response_schema=EmbeddingsResponse,
```

**التأثير:** يجب على العملاء الخارجيين (تطبيقات الويب، النصوص البرمجية) إجراء N طلب HTTP لتضمين N نص.

#### 2. خدمة تضمين المستندات

**الملف:** `trustgraph-flow/trustgraph/embeddings/document_embeddings/embeddings.py`

يعالج أجزاء المستندات واحدة تلو الأخرى:

```python
async def on_message(self, msg, consumer, flow):
    v = msg.value()

    # Single chunk per request
    resp = await flow("embeddings-request").request(
        EmbeddingsRequest(text=v.chunk)
    )
    vectors = resp.vectors
```

**التأثير:** تتطلب كل جزء من المستند استدعاءً منفصلاً لعملية التضمين. المستند الذي يتكون من 100 جزء = 100 طلب تضمين.

#### 3. خدمة تضمين الرسوم البيانية

**الملف:** `trustgraph-flow/trustgraph/embeddings/graph_embeddings/embeddings.py`

يتكرر على الكيانات ويقوم بتضمين كل منها بالتسلسل:

```python
async def on_message(self, msg, consumer, flow):
    for entity in v.entities:
        # Serial embedding - one entity at a time
        vectors = await flow("embeddings-request").embed(
            text=entity.context
        )
        entities.append(EntityEmbeddings(
            entity=entity.entity,
            vectors=vectors,
            chunk_id=entity.chunk_id,
        ))
```

**التأثير:** رسالة تحتوي على 50 كيانًا = 50 طلب تضمين تسلسلي. هذا يمثل عنق زجاجة رئيسي أثناء بناء الرسم البياني المعرفي.

#### 4. خدمة تضمين الصفوف

**الملف:** `trustgraph-flow/trustgraph/embeddings/row_embeddings/embeddings.py`

يتكرر على النصوص الفريدة ويضمّن كل منها بشكل تسلسلي:

```python
async def on_message(self, msg, consumer, flow):
    for text, (index_name, index_value) in texts_to_embed.items():
        # Serial embedding - one text at a time
        vectors = await flow("embeddings-request").embed(text=text)

        embeddings_list.append(RowIndexEmbedding(
            index_name=index_name,
            index_value=index_value,
            text=text,
            vectors=vectors
        ))
```

**التأثير:** معالجة جدول يحتوي على 100 قيمة فريدة مفهرسة = 100 طلب تضمين متسلسل.

#### 5. EmbeddingsClient (العميل الأساسي)

**الملف:** `trustgraph-base/trustgraph/base/embeddings_client.py`

العميل المستخدم من قبل جميع معالجات التدفق يدعم فقط تضمين النصوص الفردية:

```python
class EmbeddingsClient(RequestResponse):
    async def embed(self, text, timeout=30):
        resp = await self.request(
            EmbeddingsRequest(text=text),  # Single text
            timeout=timeout
        )
        return resp.vectors
```

**التأثير:** جميع المستخدمين الذين يعتمدون على هذا البرنامج يقتصرون على العمليات النصية البسيطة.

#### 6. أدوات سطر الأوامر

**الملف:** `trustgraph-cli/trustgraph/cli/invoke_embeddings.py`

أداة سطر الأوامر تقبل وسيط نصي واحد:

```python
def query(url, flow_id, text, token=None):
    result = flow.embeddings(text=text)  # Single text
    vectors = result.get("vectors", [])
```

**التأثير:** لا يمكن للمستخدمين إجراء تضمين مجمّع من سطر الأوامر. يتطلب معالجة ملف من النصوص عدد N من الاستدعاءات.

#### 7. حزمة تطوير البرمجيات (SDK) الخاصة بـ Python

توفر حزمة تطوير البرمجيات الخاصة بـ Python فئتين من العملاء للتفاعل مع خدمات TrustGraph. تدعم كلتاهما فقط التضمين لنص واحد.

**الملف:** `trustgraph-base/trustgraph/api/flow.py`

```python
class FlowInstance:
    def embeddings(self, text):
        """Get embeddings for a single text"""
        input = {"text": text}
        return self.request("service/embeddings", input)["vectors"]
```

**الملف:** `trustgraph-base/trustgraph/api/socket_client.py`

```python
class SocketFlowInstance:
    def embeddings(self, text: str, **kwargs: Any) -> Dict[str, Any]:
        """Get embeddings for a single text via WebSocket"""
        request = {"text": text}
        return self.client._send_request_sync(
            "embeddings", self.flow_id, request, False
        )
```

**التأثير:** يجب على مطوري بايثون الذين يستخدمون مجموعة تطوير البرامج (SDK) المرور على النصوص وإجراء مكالمات واجهة برمجة التطبيقات (API) منفصلة. لا يوجد دعم لعمليات الدمج المجمعة لمستخدمي مجموعة تطوير البرامج.

### تأثير الأداء

بالنسبة لاستيعاب المستندات النموذجي (1000 جزء نصي):
**الحالي:** 1000 طلب منفصل، و1000 استدعاء لنموذج الاستدلال.
**مجمعة (batch_size=32):** 32 طلبًا، و32 استدعاء لنموذج الاستدلال (انخفاض بنسبة 96.8٪).

بالنسبة لدمج الرسم البياني (رسالة تحتوي على 50 كيانًا):
**الحالي:** 50 استدعاء انتظار متسلسل، من 5 إلى 10 ثوانٍ تقريبًا.
**مجمعة:** 1-2 استدعاء مجمع، من 0.5 إلى 1 ثانية تقريبًا (تحسين بمقدار 5-10 مرات).

تحقق مكتبات FastEmbed والمكتبات المماثلة تقريبًا من قابلية التوسع الخطية في الإنتاجية مع حجم الدفعة حتى حدود الأجهزة (عادةً ما تكون 32-128 نصًا لكل دفعة).

## التصميم الفني

### البنية

يتطلب تحسين معالجة الدفعات لإنشاء تضمينات تغييرات في المكونات التالية:

#### 1. **تحسين المخطط**
   قم بتوسيع `EmbeddingsRequest` لدعم نصوص متعددة.
   قم بتوسيع `EmbeddingsResponse` لإرجاع مجموعات متجهات متعددة.
   حافظ على التوافق مع الإصدارات السابقة مع طلبات النص الواحد.

   الوحدة: `trustgraph-base/trustgraph/schema/services/llm.py`

#### 2. **تحسين الخدمة الأساسية**
   قم بتحديث `EmbeddingsService` للتعامل مع الطلبات المجمعة.
   أضف تكوين حجم الدفعة.
   قم بتنفيذ معالجة الطلبات الواعية بالدفعة.

   الوحدة: `trustgraph-base/trustgraph/base/embeddings_service.py`

#### 3. **تحديثات معالج المزود**
   قم بتحديث معالج FastEmbed لتمرير الدفعة الكاملة إلى `embed()`.
   قم بتحديث معالج Ollama للتعامل مع الدفعات (إذا تم الدعم).
   أضف معالجة تسلسلية احتياطية للمزودين الذين لا يدعمون الدفعات.

   الوحدات:
   `trustgraph-flow/trustgraph/embeddings/fastembed/processor.py`
   `trustgraph-flow/trustgraph/embeddings/ollama/processor.py`

#### 4. **تحسين العميل**
   أضف طريقة إنشاء تضمينات مجمعة إلى `EmbeddingsClient`.
   دعم كل من واجهات برمجة التطبيقات الفردية والمجمعة.
   أضف تجميعًا تلقائيًا للمدخلات الكبيرة.

   الوحدة: `trustgraph-base/trustgraph/base/embeddings_client.py`

#### 5. **تحديثات المتصل - معالجات التدفق**
   قم بتحديث `graph_embeddings` لتجميع سياقات الكيانات.
   قم بتحديث `row_embeddings` لتجميع نصوص الفهرس.
   قم بتحديث `document_embeddings` إذا كان تجميع الرسائل ممكنًا.

   الوحدات:
   `trustgraph-flow/trustgraph/embeddings/graph_embeddings/embeddings.py`
   `trustgraph-flow/trustgraph/embeddings/row_embeddings/embeddings.py`
   `trustgraph-flow/trustgraph/embeddings/document_embeddings/embeddings.py`

#### 6. **تحسين بوابة واجهة برمجة التطبيقات**
   أضف نقطة نهاية لإنشاء تضمينات مجمعة.
   دعم مصفوفة من النصوص في نص الطلب.

   الوحدة: `trustgraph-flow/trustgraph/gateway/dispatch/embeddings.py`

#### 7. **تحسين أداة سطر الأوامر**
   أضف دعمًا للنصوص المتعددة أو إدخال الملف.
   أضف معلمة حجم الدفعة.

   الوحدة: `trustgraph-cli/trustgraph/cli/invoke_embeddings.py`

#### 8. **تحسين مجموعة تطوير البرامج (SDK) الخاصة بـ Python**
   أضف طريقة `embeddings_batch()` إلى `FlowInstance`.
   أضف طريقة `embeddings_batch()` إلى `SocketFlowInstance`.
   دعم كل من واجهات برمجة التطبيقات الفردية والمجمعة لمستخدمي مجموعة تطوير البرامج.

   الوحدات:
   `trustgraph-base/trustgraph/api/flow.py`
   `trustgraph-base/trustgraph/api/socket_client.py`

### نماذج البيانات

#### EmbeddingsRequest

```python
@dataclass
class EmbeddingsRequest:
    texts: list[str] = field(default_factory=list)
```

الاستخدام:
نص مفرد: `EmbeddingsRequest(texts=["hello world"])`
دفعة: `EmbeddingsRequest(texts=["text1", "text2", "text3"])`

#### EmbeddingsResponse

```python
@dataclass
class EmbeddingsResponse:
    error: Error | None = None
    vectors: list[list[list[float]]] = field(default_factory=list)
```

هيكل الاستجابة:
`vectors[i]` يحتوي على مجموعة المتجهات لـ `texts[i]`
كل مجموعة متجهات هي `list[list[float]]` (قد تُرجع النماذج عدة متجهات لكل نص)
مثال: 3 نصوص → `vectors` يحتوي على 3 إدخالات، كل منها يحتوي على تضمينات هذا النص

### واجهات برمجة التطبيقات (APIs)

#### EmbeddingsClient

```python
class EmbeddingsClient(RequestResponse):
    async def embed(
        self,
        texts: list[str],
        timeout: float = 300,
    ) -> list[list[list[float]]]:
        """
        Embed one or more texts in a single request.

        Args:
            texts: List of texts to embed
            timeout: Timeout for the operation

        Returns:
            List of vector sets, one per input text
        """
        resp = await self.request(
            EmbeddingsRequest(texts=texts),
            timeout=timeout
        )
        if resp.error:
            raise RuntimeError(resp.error.message)
        return resp.vectors
```

#### نقطة نهاية تضمين بوابة واجهة برمجة التطبيقات (API Gateway).

تم تحديث نقطة النهاية لدعم التضمين الفردي أو الدفعي:

```
POST /api/v1/embeddings
Content-Type: application/json

{
    "texts": ["text1", "text2", "text3"],
    "flow_id": "default"
}

Response:
{
    "vectors": [
        [[0.1, 0.2, ...]],
        [[0.3, 0.4, ...]],
        [[0.5, 0.6, ...]]
    ]
}
```

### تفاصيل التنفيذ

#### المرحلة الأولى: تغييرات المخطط

**EmbeddingsRequest:**
```python
@dataclass
class EmbeddingsRequest:
    texts: list[str] = field(default_factory=list)
```

**الاستجابة المضمنة:**
```python
@dataclass
class EmbeddingsResponse:
    error: Error | None = None
    vectors: list[list[list[float]]] = field(default_factory=list)
```

**تم تحديث `EmbeddingsService.on_request`:**
```python
async def on_request(self, msg, consumer, flow):
    request = msg.value()
    id = msg.properties()["id"]
    model = flow("model")

    vectors = await self.on_embeddings(request.texts, model=model)
    response = EmbeddingsResponse(error=None, vectors=vectors)

    await flow("response").send(response, properties={"id": id})
```

#### المرحلة الثانية: تحديث معالج FastEmbed

**الحالي (غير فعال):**
```python
async def on_embeddings(self, text, model=None):
    use_model = model or self.default_model
    self._load_model(use_model)
    vecs = self.embeddings.embed([text])  # Batch of 1
    return [v.tolist() for v in vecs]
```

**تحديث:**
```python
async def on_embeddings(self, texts: list[str], model=None):
    """Embed texts - processes all texts in single model call"""
    if not texts:
        return []

    use_model = model or self.default_model
    self._load_model(use_model)

    # FastEmbed handles the full batch efficiently
    all_vecs = list(self.embeddings.embed(texts))

    # Return list of vector sets, one per input text
    return [[v.tolist()] for v in all_vecs]
```

#### المرحلة الثالثة: تحديث خدمة تضمين الرسوم البيانية

**الحالي (التسلسلي):**
```python
async def on_message(self, msg, consumer, flow):
    entities = []
    for entity in v.entities:
        vectors = await flow("embeddings-request").embed(text=entity.context)
        entities.append(EntityEmbeddings(...))
```

**تحديث (مجموعة):**
```python
async def on_message(self, msg, consumer, flow):
    # Collect all contexts
    contexts = [entity.context for entity in v.entities]

    # Single batch embedding call
    all_vectors = await flow("embeddings-request").embed(texts=contexts)

    # Pair results with entities
    entities = [
        EntityEmbeddings(
            entity=entity.entity,
            vectors=vectors[0],  # First vector from the set
            chunk_id=entity.chunk_id,
        )
        for entity, vectors in zip(v.entities, all_vectors)
    ]
```

#### المرحلة الرابعة: تحديث خدمة تضمين الصفوف

**الحالي (تسلسلي):**
```python
for text, (index_name, index_value) in texts_to_embed.items():
    vectors = await flow("embeddings-request").embed(text=text)
    embeddings_list.append(RowIndexEmbedding(...))
```

**تحديث (مجموعة):**
```python
# Collect texts and metadata
texts = list(texts_to_embed.keys())
metadata = list(texts_to_embed.values())

# Single batch embedding call
all_vectors = await flow("embeddings-request").embed(texts=texts)

# Pair results
embeddings_list = [
    RowIndexEmbedding(
        index_name=meta[0],
        index_value=meta[1],
        text=text,
        vectors=vectors[0]  # First vector from the set
    )
    for text, meta, vectors in zip(texts, metadata, all_vectors)
]
```

#### المرحلة الخامسة: تحسين أداة سطر الأوامر.

**سطر الأوامر المحدث:**
```python
def main():
    parser = argparse.ArgumentParser(...)

    parser.add_argument(
        'text',
        nargs='*',  # Zero or more texts
        help='Text(s) to convert to embedding vectors',
    )

    parser.add_argument(
        '-f', '--file',
        help='File containing texts (one per line)',
    )

    parser.add_argument(
        '--batch-size',
        type=int,
        default=32,
        help='Batch size for processing (default: 32)',
    )
```

الاستخدام:
```bash
# Single text (existing)
tg-invoke-embeddings "hello world"

# Multiple texts
tg-invoke-embeddings "text one" "text two" "text three"

# From file
tg-invoke-embeddings -f texts.txt --batch-size 64
```

#### المرحلة السادسة: تحسين حزمة تطوير البرمجيات (SDK) الخاصة بـ Python

**FlowInstance (عميل HTTP):**

```python
class FlowInstance:
    def embeddings(self, texts: list[str]) -> list[list[list[float]]]:
        """
        Get embeddings for one or more texts.

        Args:
            texts: List of texts to embed

        Returns:
            List of vector sets, one per input text
        """
        input = {"texts": texts}
        return self.request("service/embeddings", input)["vectors"]
```

**مثيل SocketFlow (عميل WebSocket):**

```python
class SocketFlowInstance:
    def embeddings(self, texts: list[str], **kwargs: Any) -> list[list[list[float]]]:
        """
        Get embeddings for one or more texts via WebSocket.

        Args:
            texts: List of texts to embed

        Returns:
            List of vector sets, one per input text
        """
        request = {"texts": texts}
        response = self.client._send_request_sync(
            "embeddings", self.flow_id, request, False
        )
        return response["vectors"]
```

**أمثلة على استخدام الـ SDK:**

```python
# Single text
vectors = flow.embeddings(["hello world"])
print(f"Dimensions: {len(vectors[0][0])}")

# Batch embedding
texts = ["text one", "text two", "text three"]
all_vectors = flow.embeddings(texts)

# Process results
for text, vecs in zip(texts, all_vectors):
    print(f"{text}: {len(vecs[0])} dimensions")
```

## اعتبارات الأمان

**حدود حجم الطلب**: فرض الحد الأقصى لحجم الدفعة لمنع استنزاف الموارد.
**معالجة انتهاء المهلة**: قم بتعيين قيم انتهاء المهلة بشكل مناسب لحجم الدفعة.
**حدود الذاكرة**: راقب استخدام الذاكرة للدفعات الكبيرة.
**التحقق من صحة الإدخال**: تحقق من صحة جميع النصوص في الدفعة قبل المعالجة.

## اعتبارات الأداء

### التحسينات المتوقعة

**معدل الإنتاجية:**
نص واحد: ~10-50 نصًا/ثانية (حسب النموذج)
دفعة (حجم 32): ~200-500 نص/ثانية (تحسين بمقدار 5-10 مرات)

**زمن الوصول لكل نص:**
نص واحد: 50-200 مللي ثانية لكل نص
دفعة (حجم 32): 5-20 مللي ثانية لكل نص (متوسط)

**التحسينات الخاصة بالخدمة:**

| الخدمة | الحالي | الدفعات | التحسين |
|---------|---------|---------|-------------|
| تضمينات الرسم البياني (50 كيانًا) | 5-10 ثوانٍ | 0.5-1 ثانية | 5-10 مرات |
| تضمينات الصفوف (100 نص) | 10-20 ثانية | 1-2 ثانية | 5-10 مرات |
| استيعاب المستندات (1000 جزء) | 100-200 ثانية | 10-30 ثانية | 5-10 مرات |

### معلمات التكوين

```python
# Recommended defaults
DEFAULT_BATCH_SIZE = 32
MAX_BATCH_SIZE = 128
BATCH_TIMEOUT_MULTIPLIER = 2.0
```

## استراتيجية الاختبار

### اختبار الوحدات
تضمين نص واحد (التوافق مع الإصدارات السابقة)
معالجة الدُفعات الفارغة
فرض الحد الأقصى لحجم الدفعة
معالجة الأخطاء في حالة فشل بعض عناصر الدفعة

### اختبار التكامل
تضمين الدُفعات من البداية إلى النهاية عبر Pulsar
معالجة الدُفعات لخدمة تضمينات الرسم البياني
معالجة الدُفعات لخدمة تضمينات الصفوف
نقطة نهاية الدُفعات لبوابة واجهة برمجة التطبيقات

### اختبار الأداء
قياس الإنتاجية الفردية مقابل الإنتاجية عند استخدام الدُفعات
استخدام الذاكرة تحت أحجام دفعات مختلفة
تحليل توزيع زمن الاستجابة

## خطة الترحيل

هذا إصدار يتضمن تغييرات جذرية. يتم تنفيذ جميع المراحل معًا.

### المرحلة الأولى: تغييرات المخطط
استبدال `text: str` بـ `texts: list[str]` في EmbeddingsRequest
تغيير نوع `vectors` إلى `list[list[list[float]]]` في EmbeddingsResponse

### المرحلة الثانية: تحديثات المعالج
تحديث توقيع `on_embeddings` في معالجات FastEmbed و Ollama
معالجة الدفعة بأكملها في استدعاء واحد للنموذج

### المرحلة الثالثة: تحديثات العميل
تحديث `EmbeddingsClient.embed()` لقبول `texts: list[str]`

### المرحلة الرابعة: تحديثات المستخدم
تحديث graph_embeddings لمعالجة سياقات الكيانات على شكل دفعات
تحديث row_embeddings لمعالجة نصوص الفهرس على شكل دفعات
تحديث document_embeddings لاستخدام المخطط الجديد
تحديث أداة سطر الأوامر

### المرحلة الخامسة: بوابة واجهة برمجة التطبيقات
تحديث نقطة نهاية تضمين للمخطط الجديد

### المرحلة السادسة: حزمة تطوير البرمجيات بلغة بايثون
تحديث توقيع `FlowInstance.embeddings()`
تحديث توقيع `SocketFlowInstance.embeddings()`

## أسئلة مفتوحة

**معالجة الدُفعات الكبيرة جدًا**: هل يجب أن ندعم إرجاع النتائج على شكل دفعات صغيرة جدًا للدُفعات الكبيرة جدًا (أكثر من 100 نص)؟
**القيود الخاصة بالمزودين**: كيف يجب أن نتعامل مع المزودين الذين لديهم أحجام دفعات قصوى مختلفة؟
**معالجة حالات الفشل الجزئية**: إذا فشل أحد النصوص في الدفعة، فهل يجب أن نفشل الدفعة بأكملها أم أن نرجع النتائج الجزئية؟
**تجميع تضمينات المستندات**: هل يجب أن نقوم بتجميع البيانات عبر رسائل Chunk متعددة أم أن نحافظ على المعالجة لكل رسالة؟

## المراجع

[وثائق FastEmbed](https://github.com/qdrant/fastembed)
[واجهة برمجة تطبيقات Ollama Embeddings](https://github.com/ollama/ollama)
[تنفيذ EmbeddingsService](trustgraph-base/trustgraph/base/embeddings_service.py)
[تحسين أداء GraphRAG](graphrag-performance-optimization.md)
