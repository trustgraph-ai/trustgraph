# مواصفات فنية لإعادة هيكلة واجهة برمجة التطبيقات (API) الخاصة بـ Python

## نظرة عامة

تصف هذه المواصفات إعادة هيكلة شاملة لمكتبة عميل واجهة برمجة التطبيقات (API) الخاصة بـ Python لـ TrustGraph لتحقيق التوافق مع واجهة برمجة التطبيقات (API) والبوابة وإضافة دعم لأنماط الاتصال في الوقت الفعلي الحديثة.

تعالج عملية إعادة الهيكلة أربعة استخدامات رئيسية:

1. **تفاعلات LLM المتدفقة**: تمكين التدفق في الوقت الفعلي لنتائج LLM (الوكيل، والبحث الدلالي في الرسم البياني، والبحث الدلالي في المستند، وإكمال النص، والموجهات) مع زمن انتقال أقل بنسبة 60 مرة (500 مللي ثانية مقابل 30 ثانية للرمز المميز الأول).
2. **عمليات البيانات المجمعة**: دعم الاستيراد/التصدير المجمع الفعال للثلاثيات، وتضمينات الرسم البياني، وتضمينات المستند لإدارة الرسوم البيانية المعرفية واسعة النطاق.
3. **التوافق مع واجهة برمجة التطبيقات (API)**: التأكد من أن كل نقطة نهاية في واجهة برمجة التطبيقات (API) والبوابة لديها طريقة واجهة برمجة تطبيقات (API) Python مقابلة، بما في ذلك استعلام تضمينات الرسم البياني.
4. **اتصالات مستمرة**: تمكين الاتصال المستند إلى WebSocket للطلبات متعددة المهام وتقليل النفقات العامة للاتصال.

## الأهداف

**التوافق مع واجهة برمجة التطبيقات (API)**: كل خدمة في واجهة برمجة التطبيقات (API) والبوابة لديها طريقة واجهة برمجة تطبيقات (API) Python مقابلة.
**دعم التدفق**: تدعم جميع الخدمات القادرة على التدفق (الوكيل، والبحث الدلالي، وإكمال النص، والموجه) التدفق في واجهة برمجة تطبيقات (API) Python.
**طبقة نقل WebSocket**: إضافة طبقة نقل WebSocket اختيارية للاتصالات المستمرة والتجميع.
**العمليات المجمعة**: إضافة استيراد/تصدير مجمع فعال للثلاثيات، وتضمينات الرسم البياني، وتضمينات المستند.
**دعم كامل غير متزامن**: تطبيق كامل لـ async/await لجميع الواجهات (REST، WebSocket، العمليات المجمعة، المقاييس).
**التوافق مع الإصدارات السابقة**: يستمر الكود الحالي في العمل دون تعديل.
**أمان النوع**: الحفاظ على واجهات آمنة من النوع باستخدام dataclasses وتلميحات النوع.
**التحسين التدريجي**: التدفق وغير المتزامن هما خياران ويمكن تفعيلهما من خلال اختيار الواجهة الصريح.
**الأداء**: تحقيق تحسين بنسبة 60٪ في زمن الانتقال لعمليات التدفق.
**Python حديثة**: دعم كل من نماذج المزامنة وغير المتزامنة لأقصى قدر من المرونة.

## الخلفية

### الحالة الحالية

واجهة برمجة التطبيقات (API) الخاصة بـ Python (`trustgraph-base/trustgraph/api/`) هي مكتبة عميل REST فقط مع الوحدات التالية:

`flow.py`: إدارة التدفق والخدمات ذات النطاق التدريجي (50 طريقة).
`library.py`: عمليات مكتبة المستندات (9 طرق).
`knowledge.py`: إدارة النواة الخاصة بالرسم البياني (4 طرق).
`collection.py`: بيانات وصف المجموعة (3 طرق).
`config.py`: إدارة التكوين (6 طرق).
`types.py`: تعريفات أنواع البيانات (5 dataclasses).

**إجمالي العمليات**: 50/59 (تغطية بنسبة 85٪).

### القيود الحالية

**العمليات المفقودة**:
استعلام تضمينات الرسم البياني (البحث الدلالي عن كيانات الرسم البياني).
استيراد/تصدير مجمع للثلاثيات، وتضمينات الرسم البياني، وتضمينات المستند، وسياقات الكيانات، والكائنات.
نقطة نهاية المقاييس.

**القدرات المفقودة**:
دعم البث لخدمات نماذج اللغة الكبيرة (LLM).
بروتوكول نقل WebSocket.
طلبات متزامنة متعددة.
اتصالات مستمرة.

**مشكلات الأداء**:
زمن انتقال مرتفع لتفاعلات نماذج اللغة الكبيرة (حوالي 30 ثانية للرمز الأول).
نقل بيانات مجمعة غير فعال (طلب REST لكل عنصر).
تكلفة الاتصال لعمليات متسلسلة متعددة.

**مشكلات تجربة المستخدم**:
عدم وجود ملاحظات في الوقت الفعلي أثناء توليد نماذج اللغة الكبيرة.
عدم القدرة على إلغاء العمليات الطويلة الأمد لنماذج اللغة الكبيرة.
قابلية توسع ضعيفة للعمليات المجمعة.

### التأثير

أدى التحسين الذي تم تقديمه في نوفمبر 2024 للبث في واجهة برمجة التطبيقات (API) للـ Gateway إلى تحسين زمن الانتقال بمقدار 60 مرة (500 مللي ثانية مقابل 30 ثانية للرمز الأول) لتفاعلات نماذج اللغة الكبيرة، ولكن مستخدمي واجهة برمجة التطبيقات Python لا يمكنهم الاستفادة من هذه الإمكانية. وهذا يخلق فجوة كبيرة في تجربة المستخدم بين مستخدمي Python وغير مستخدمي Python.

## التصميم التقني

### البنية

تستخدم واجهة برمجة التطبيقات Python المعاد تصميمها **نهج واجهة معيارية** مع كائنات منفصلة لأنماط الاتصال المختلفة. تتوفر جميع الواجهات في كل من الإصدارات **المزامنة وغير المتزامنة**:

1. **واجهة REST** (موجودة، مُحسّنة)
   **المزامنة**: `api.flow()`، `api.library()`، `api.knowledge()`، `api.collection()`، `api.config()`
   **غير متزامنة**: `api.async_flow()`
   طلب/استجابة متزامنة/غير متزامنة.
   نموذج اتصال بسيط.
   الافتراضي للتوافق مع الإصدارات السابقة.

2. **واجهة WebSocket** (جديدة)
   **المزامنة**: `api.socket()`
   **غير متزامنة**: `api.async_socket()`
   اتصال مستمر.
   طلبات متعددة.
   دعم البث.
   نفس توقيعات الأساليب مثل REST حيث تتداخل الوظائف.

3. **واجهة العمليات المجمعة** (جديدة)
   **المزامنة**: `api.bulk()`
   **غير متزامنة**: `api.async_bulk()`
   تعتمد على WebSocket للكفاءة.
   استيراد/تصدير يعتمد على المكرر/AsyncIterator.
   تتعامل مع مجموعات البيانات الكبيرة.

4. **واجهة المقاييس** (جديدة)
   **المزامنة**: `api.metrics()`
   **غير متزامنة**: `api.async_metrics()`
   الوصول إلى مقاييس Prometheus.

```python
import asyncio

# Synchronous interfaces
api = Api(url="http://localhost:8088/")

# REST (existing, unchanged)
flow = api.flow().id("default")
response = flow.agent(question="...", user="...")

# WebSocket (new)
socket_flow = api.socket().flow("default")
response = socket_flow.agent(question="...", user="...")
for chunk in socket_flow.agent(question="...", user="...", streaming=True):
    print(chunk)

# Bulk operations (new)
bulk = api.bulk()
bulk.import_triples(flow="default", triples=triple_generator())

# Asynchronous interfaces
async def main():
    api = Api(url="http://localhost:8088/")

    # Async REST (new)
    flow = api.async_flow().id("default")
    response = await flow.agent(question="...", user="...")

    # Async WebSocket (new)
    socket_flow = api.async_socket().flow("default")
    async for chunk in socket_flow.agent(question="...", streaming=True):
        print(chunk)

    # Async bulk operations (new)
    bulk = api.async_bulk()
    await bulk.import_triples(flow="default", triples=async_triple_generator())

asyncio.run(main())
```

**المبادئ الأساسية للتصميم:**
**نفس عنوان URL لجميع الواجهات:** `Api(url="http://localhost:8088/")` يعمل مع جميع الواجهات.
**التماثل بين المتزامن وغير المتزامن:** كل واجهة لديها إصدارات متزامنة وغير متزامنة مع توقيعات طرق متطابقة.
**توقيعات متطابقة:** حيث تتداخل الوظائف، تكون توقيعات الطرق متطابقة بين REST و WebSocket، والمتزامن وغير المتزامن.
**التحسين التدريجي:** اختر الواجهة بناءً على الاحتياجات (REST للعمليات البسيطة، WebSocket للبث، Bulk لمجموعات البيانات الكبيرة، وغير المتزامن للإطارات الحديثة).
**نية صريحة:** `api.socket()` يشير إلى WebSocket، و `api.async_socket()` يشير إلى WebSocket غير المتزامن.
**متوافق مع الإصدارات السابقة:** الكود الحالي لا يتغير.

### المكونات

#### 1. فئة واجهة برمجة التطبيقات الأساسية (معدلة)

الوحدة: `trustgraph-base/trustgraph/api/api.py`

**فئة واجهة برمجة التطبيقات المحسنة:**

```python
class Api:
    def __init__(self, url: str, timeout: int = 60, token: Optional[str] = None):
        self.url = url
        self.timeout = timeout
        self.token = token  # Optional bearer token for REST, query param for WebSocket
        self._socket_client = None
        self._bulk_client = None
        self._async_flow = None
        self._async_socket_client = None
        self._async_bulk_client = None

    # Existing synchronous methods (unchanged)
    def flow(self) -> Flow:
        """Synchronous REST-based flow interface"""
        pass

    def library(self) -> Library:
        """Synchronous REST-based library interface"""
        pass

    def knowledge(self) -> Knowledge:
        """Synchronous REST-based knowledge interface"""
        pass

    def collection(self) -> Collection:
        """Synchronous REST-based collection interface"""
        pass

    def config(self) -> Config:
        """Synchronous REST-based config interface"""
        pass

    # New synchronous methods
    def socket(self) -> SocketClient:
        """Synchronous WebSocket-based interface for streaming operations"""
        if self._socket_client is None:
            self._socket_client = SocketClient(self.url, self.timeout, self.token)
        return self._socket_client

    def bulk(self) -> BulkClient:
        """Synchronous bulk operations interface for import/export"""
        if self._bulk_client is None:
            self._bulk_client = BulkClient(self.url, self.timeout, self.token)
        return self._bulk_client

    def metrics(self) -> Metrics:
        """Synchronous metrics interface"""
        return Metrics(self.url, self.timeout, self.token)

    # New asynchronous methods
    def async_flow(self) -> AsyncFlow:
        """Asynchronous REST-based flow interface"""
        if self._async_flow is None:
            self._async_flow = AsyncFlow(self.url, self.timeout, self.token)
        return self._async_flow

    def async_socket(self) -> AsyncSocketClient:
        """Asynchronous WebSocket-based interface for streaming operations"""
        if self._async_socket_client is None:
            self._async_socket_client = AsyncSocketClient(self.url, self.timeout, self.token)
        return self._async_socket_client

    def async_bulk(self) -> AsyncBulkClient:
        """Asynchronous bulk operations interface for import/export"""
        if self._async_bulk_client is None:
            self._async_bulk_client = AsyncBulkClient(self.url, self.timeout, self.token)
        return self._async_bulk_client

    def async_metrics(self) -> AsyncMetrics:
        """Asynchronous metrics interface"""
        return AsyncMetrics(self.url, self.timeout, self.token)

    # Resource management
    def close(self) -> None:
        """Close all synchronous connections"""
        if self._socket_client:
            self._socket_client.close()
        if self._bulk_client:
            self._bulk_client.close()

    async def aclose(self) -> None:
        """Close all asynchronous connections"""
        if self._async_socket_client:
            await self._async_socket_client.aclose()
        if self._async_bulk_client:
            await self._async_bulk_client.aclose()
        if self._async_flow:
            await self._async_flow.aclose()

    def __enter__(self):
        return self

    def __exit__(self, *args):
        self.close()

    async def __aenter__(self):
        return self

    async def __aexit__(self, *args):
        await self.aclose()
```

#### 2. عميل WebSocket المتزامن

الوحدة: `trustgraph-base/trustgraph/api/socket_client.py` (جديد)

**فئة SocketClient:**

```python
class SocketClient:
    """Synchronous WebSocket client"""
    def __init__(self, url: str, timeout: int, token: Optional[str]):
        self.url = self._convert_to_ws_url(url)
        self.timeout = timeout
        self.token = token
        self._connection = None
        self._request_counter = 0

    def flow(self, flow_id: str) -> SocketFlowInstance:
        """Get flow instance for WebSocket operations"""
        return SocketFlowInstance(self, flow_id)

    def _connect(self) -> WebSocket:
        """Establish WebSocket connection (lazy)"""
        # Uses asyncio.run() internally to wrap async websockets library
        pass

    def _send_request(
        self,
        service: str,
        flow: Optional[str],
        request: Dict[str, Any],
        streaming: bool = False
    ) -> Union[Dict[str, Any], Iterator[Dict[str, Any]]]:
        """Send request and handle response/streaming"""
        # Synchronous wrapper around async WebSocket calls
        pass

    def close(self) -> None:
        """Close WebSocket connection"""
        pass

class SocketFlowInstance:
    """Synchronous WebSocket flow instance with same interface as REST FlowInstance"""
    def __init__(self, client: SocketClient, flow_id: str):
        self.client = client
        self.flow_id = flow_id

    # Same method signatures as FlowInstance
    def agent(
        self,
        question: str,
        user: str,
        state: Optional[Dict[str, Any]] = None,
        group: Optional[str] = None,
        history: Optional[List[Dict[str, Any]]] = None,
        streaming: bool = False,
        **kwargs
    ) -> Union[Dict[str, Any], Iterator[Dict[str, Any]]]:
        """Agent with optional streaming"""
        pass

    def text_completion(
        self,
        system: str,
        prompt: str,
        streaming: bool = False,
        **kwargs
    ) -> Union[str, Iterator[str]]:
        """Text completion with optional streaming"""
        pass

    # ... similar for graph_rag, document_rag, prompt, etc.
```

**الميزات الرئيسية:**
اتصال كسول (يتصل فقط عند إرسال الطلب الأول)
تعدد الطلبات (حتى 15 طلبًا متزامنًا)
إعادة الاتصال التلقائي عند الانفصال
تحليل الاستجابة المتدفقة
تشغيل آمن للخيوط
غلاف متزامن حول مكتبة WebSocket غير المتزامنة

#### 3. عميل WebSocket غير المتزامن

الوحدة: `trustgraph-base/trustgraph/api/async_socket_client.py` (جديد)

**فئة AsyncSocketClient:**

```python
class AsyncSocketClient:
    """Asynchronous WebSocket client"""
    def __init__(self, url: str, timeout: int, token: Optional[str]):
        self.url = self._convert_to_ws_url(url)
        self.timeout = timeout
        self.token = token
        self._connection = None
        self._request_counter = 0

    def flow(self, flow_id: str) -> AsyncSocketFlowInstance:
        """Get async flow instance for WebSocket operations"""
        return AsyncSocketFlowInstance(self, flow_id)

    async def _connect(self) -> WebSocket:
        """Establish WebSocket connection (lazy)"""
        # Native async websockets library
        pass

    async def _send_request(
        self,
        service: str,
        flow: Optional[str],
        request: Dict[str, Any],
        streaming: bool = False
    ) -> Union[Dict[str, Any], AsyncIterator[Dict[str, Any]]]:
        """Send request and handle response/streaming"""
        pass

    async def aclose(self) -> None:
        """Close WebSocket connection"""
        pass

class AsyncSocketFlowInstance:
    """Asynchronous WebSocket flow instance"""
    def __init__(self, client: AsyncSocketClient, flow_id: str):
        self.client = client
        self.flow_id = flow_id

    # Same method signatures as FlowInstance (but async)
    async def agent(
        self,
        question: str,
        user: str,
        state: Optional[Dict[str, Any]] = None,
        group: Optional[str] = None,
        history: Optional[List[Dict[str, Any]]] = None,
        streaming: bool = False,
        **kwargs
    ) -> Union[Dict[str, Any], AsyncIterator[Dict[str, Any]]]:
        """Agent with optional streaming"""
        pass

    async def text_completion(
        self,
        system: str,
        prompt: str,
        streaming: bool = False,
        **kwargs
    ) -> Union[str, AsyncIterator[str]]:
        """Text completion with optional streaming"""
        pass

    # ... similar for graph_rag, document_rag, prompt, etc.
```

**الميزات الرئيسية:**
دعم أصلي لـ async/await.
فعال للتطبيقات غير المتزامنة (FastAPI, aiohttp).
لا يوجد حظر للخيوط.
نفس الواجهة مثل الإصدار المتزامن.
AsyncIterator للتدفق.

#### 4. عميل العمليات المجمعة المتزامنة

الوحدة: `trustgraph-base/trustgraph/api/bulk_client.py` (جديد)

**فئة BulkClient:**

```python
class BulkClient:
    """Synchronous bulk operations client"""
    def __init__(self, url: str, timeout: int, token: Optional[str]):
        self.url = self._convert_to_ws_url(url)
        self.timeout = timeout
        self.token = token

    def import_triples(
        self,
        flow: str,
        triples: Iterator[Triple],
        **kwargs
    ) -> None:
        """Bulk import triples via WebSocket"""
        pass

    def export_triples(
        self,
        flow: str,
        **kwargs
    ) -> Iterator[Triple]:
        """Bulk export triples via WebSocket"""
        pass

    def import_graph_embeddings(
        self,
        flow: str,
        embeddings: Iterator[Dict[str, Any]],
        **kwargs
    ) -> None:
        """Bulk import graph embeddings via WebSocket"""
        pass

    def export_graph_embeddings(
        self,
        flow: str,
        **kwargs
    ) -> Iterator[Dict[str, Any]]:
        """Bulk export graph embeddings via WebSocket"""
        pass

    # ... similar for document embeddings, entity contexts, objects

    def close(self) -> None:
        """Close connections"""
        pass
```

**الميزات الرئيسية:**
يعتمد على التكرار لاستخدام ذاكرة ثابتة.
اتصالات WebSocket مخصصة لكل عملية.
تتبع التقدم (وظيفة رد اتصال اختيارية).
معالجة الأخطاء مع إمكانية الإبلاغ عن النجاح الجزئي.

#### 5. عميل العمليات المجمعة غير المتزامنة

الوحدة: `trustgraph-base/trustgraph/api/async_bulk_client.py` (جديد)

**فئة AsyncBulkClient:**

```python
class AsyncBulkClient:
    """Asynchronous bulk operations client"""
    def __init__(self, url: str, timeout: int, token: Optional[str]):
        self.url = self._convert_to_ws_url(url)
        self.timeout = timeout
        self.token = token

    async def import_triples(
        self,
        flow: str,
        triples: AsyncIterator[Triple],
        **kwargs
    ) -> None:
        """Bulk import triples via WebSocket"""
        pass

    async def export_triples(
        self,
        flow: str,
        **kwargs
    ) -> AsyncIterator[Triple]:
        """Bulk export triples via WebSocket"""
        pass

    async def import_graph_embeddings(
        self,
        flow: str,
        embeddings: AsyncIterator[Dict[str, Any]],
        **kwargs
    ) -> None:
        """Bulk import graph embeddings via WebSocket"""
        pass

    async def export_graph_embeddings(
        self,
        flow: str,
        **kwargs
    ) -> AsyncIterator[Dict[str, Any]]:
        """Bulk export graph embeddings via WebSocket"""
        pass

    # ... similar for document embeddings, entity contexts, objects

    async def aclose(self) -> None:
        """Close connections"""
        pass
```

**الميزات الرئيسية:**
يعتمد على AsyncIterator للاستهلاك الثابت للذاكرة.
فعال للتطبيقات غير المتزامنة.
دعم أصلي لـ async/await.
نفس الواجهة مثل الإصدار المتزامن.

#### 6. واجهة برمجة تطبيقات REST (متزامنة - دون تغيير)

الوحدة: `trustgraph-base/trustgraph/api/flow.py`

تظل واجهة برمجة تطبيقات REST **دون أي تغيير** لضمان التوافق مع الإصدارات السابقة. جميع الطرق الحالية تظل تعمل:

`Flow.list()`، `Flow.start()`، `Flow.stop()`، إلخ.
`FlowInstance.agent()`، `FlowInstance.text_completion()`، `FlowInstance.graph_rag()`، إلخ.
تم الحفاظ على جميع التوقيعات وأنواع الإرجاع الحالية.

**جديد:** إضافة `graph_embeddings_query()` إلى REST FlowInstance لتحقيق التوافق في الميزات:

```python
class FlowInstance:
    # All existing methods unchanged...

    # New: Graph embeddings query (REST)
    def graph_embeddings_query(
        self,
        text: str,
        user: str,
        collection: str,
        limit: int = 10,
        **kwargs
    ) -> List[Dict[str, Any]]:
        """Query graph embeddings for semantic search"""
        # Calls POST /api/v1/flow/{flow}/service/graph-embeddings
        pass
```

#### 7. واجهة برمجة تطبيقات REST غير المتزامنة

الوحدة: `trustgraph-base/trustgraph/api/async_flow.py` (جديد)

**الفئات AsyncFlow و AsyncFlowInstance:**

```python
class AsyncFlow:
    """Asynchronous REST-based flow interface"""
    def __init__(self, url: str, timeout: int, token: Optional[str]):
        self.url = url
        self.timeout = timeout
        self.token = token

    async def list(self) -> List[Dict[str, Any]]:
        """List all flows"""
        pass

    async def get(self, id: str) -> Dict[str, Any]:
        """Get flow definition"""
        pass

    async def start(self, class_name: str, id: str, description: str, parameters: Dict) -> None:
        """Start a flow"""
        pass

    async def stop(self, id: str) -> None:
        """Stop a flow"""
        pass

    def id(self, flow_id: str) -> AsyncFlowInstance:
        """Get async flow instance"""
        return AsyncFlowInstance(self.url, self.timeout, self.token, flow_id)

    async def aclose(self) -> None:
        """Close connection"""
        pass

class AsyncFlowInstance:
    """Asynchronous REST flow instance"""

    async def agent(
        self,
        question: str,
        user: str,
        state: Optional[Dict[str, Any]] = None,
        group: Optional[str] = None,
        history: Optional[List[Dict[str, Any]]] = None,
        **kwargs
    ) -> Dict[str, Any]:
        """Async agent execution"""
        pass

    async def text_completion(
        self,
        system: str,
        prompt: str,
        **kwargs
    ) -> str:
        """Async text completion"""
        pass

    async def graph_rag(
        self,
        question: str,
        user: str,
        collection: str,
        **kwargs
    ) -> str:
        """Async graph RAG"""
        pass

    # ... all other FlowInstance methods as async versions
```

**الميزات الرئيسية:**
دعم غير متزامن لبروتوكول HTTP باستخدام `aiohttp` أو `httpx`.
نفس توقيعات الأساليب لواجهة برمجة تطبيقات REST المتزامنة.
لا يوجد بث (استخدم `async_socket()` للبث).
فعال للتطبيقات غير المتزامنة.

#### 8. واجهة برمجة تطبيقات المقاييس

الوحدة: `trustgraph-base/trustgraph/api/metrics.py` (جديد).

**المقاييس المتزامنة:**

```python
class Metrics:
    def __init__(self, url: str, timeout: int, token: Optional[str]):
        self.url = url
        self.timeout = timeout
        self.token = token

    def get(self) -> str:
        """Get Prometheus metrics as text"""
        # Call GET /api/metrics
        pass
```

**المقاييس غير المتزامنة:**

```python
class AsyncMetrics:
    def __init__(self, url: str, timeout: int, token: Optional[str]):
        self.url = url
        self.timeout = timeout
        self.token = token

    async def get(self) -> str:
        """Get Prometheus metrics as text"""
        # Call GET /api/metrics
        pass
```

#### 9. الأنواع المحسنة

الوحدة: `trustgraph-base/trustgraph/api/types.py` (معدلة)

**أنواع جديدة:**

```python
from typing import Iterator, Union, Dict, Any
import dataclasses

@dataclasses.dataclass
class StreamingChunk:
    """Base class for streaming chunks"""
    content: str
    end_of_message: bool = False

@dataclasses.dataclass
class AgentThought(StreamingChunk):
    """Agent reasoning chunk"""
    chunk_type: str = "thought"

@dataclasses.dataclass
class AgentObservation(StreamingChunk):
    """Agent tool observation chunk"""
    chunk_type: str = "observation"

@dataclasses.dataclass
class AgentAnswer(StreamingChunk):
    """Agent final answer chunk"""
    chunk_type: str = "final-answer"
    end_of_dialog: bool = False

@dataclasses.dataclass
class RAGChunk(StreamingChunk):
    """RAG streaming chunk"""
    end_of_stream: bool = False
    error: Optional[Dict[str, str]] = None

# Type aliases for clarity
AgentStream = Iterator[Union[AgentThought, AgentObservation, AgentAnswer]]
RAGStream = Iterator[RAGChunk]
CompletionStream = Iterator[str]
```

#### 6. واجهة برمجة التطبيقات (API) للمقاييس

الوحدة: `trustgraph-base/trustgraph/api/metrics.py` (جديد)

```python
class Metrics:
    def __init__(self, url: str, timeout: int, token: Optional[str]):
        self.url = url
        self.timeout = timeout
        self.token = token

    def get(self) -> str:
        """Get Prometheus metrics as text"""
        # Call GET /api/metrics
        pass
```

### نهج التنفيذ

#### المرحلة الأولى: تحسين واجهة برمجة التطبيقات الأساسية (الأسبوع الأول)

1. إضافة طرق `socket()` و `bulk()` و `metrics()` إلى الفئة `Api`
2. تنفيذ التهيئة الكسولة لعملاء WebSocket والكمية الكبيرة
3. إضافة دعم لإدارة السياق (`__enter__`، `__exit__`)
4. إضافة طريقة `close()` للتنظيف
5. إضافة اختبارات وحدة لتحسينات فئة واجهة برمجة التطبيقات
6. التحقق من التوافق مع الإصدارات السابقة

**التوافق مع الإصدارات السابقة**: لا توجد تغييرات تؤثر على الإصدارات السابقة. طرق جديدة فقط.

#### المرحلة الثانية: عميل WebSocket (الأسبوعان الثاني والثالث)

1. تنفيذ الفئة `SocketClient` مع إدارة الاتصال
2. تنفيذ `SocketFlowInstance` بنفس توقيعات الطرق مثل `FlowInstance`
3. إضافة دعم لتقسيم الطلبات (حتى 15 طلبًا متزامنًا)
4. إضافة تحليل استجابة التدفق لأنواع أجزاء مختلفة
5. إضافة منطق إعادة الاتصال التلقائي
6. إضافة اختبارات الوحدة والتكامل
7. توثيق أنماط استخدام WebSocket

**التوافق مع الإصدارات السابقة**: واجهة جديدة فقط. لا يوجد تأثير على التعليمات البرمجية الحالية.

#### المرحلة الثالثة: دعم التدفق (الأسبوعان الثالث والرابع)

1. إضافة فئات أنواع أجزاء التدفق (`AgentThought`، `AgentObservation`، `AgentAnswer`، `RAGChunk`)
2. تنفيذ تحليل استجابة التدفق في `SocketClient`
3. إضافة معلمة التدفق إلى جميع طرق LLM في `SocketFlowInstance`
4. التعامل مع حالات الخطأ أثناء التدفق
5. إضافة اختبارات الوحدة والتكامل للتدفق
6. إضافة أمثلة التدفق إلى الوثائق

**التوافق مع الإصدارات السابقة**: واجهة جديدة فقط. واجهة برمجة تطبيقات REST الحالية لم تتغير.

#### المرحلة الرابعة: العمليات المجمعة (الأسبوعان الرابع والخامس)

1. تنفيذ الفئة `BulkClient`
2. إضافة طرق الاستيراد/التصدير المجمعة للثلاثيات والتضمينات والسياقات والكائنات
3. تنفيذ المعالجة القائمة على المكرر للذاكرة الثابتة
4. إضافة تتبع التقدم (وظيفة رد اتصال اختيارية)
5. إضافة معالجة الأخطاء مع الإبلاغ عن النجاح الجزئي
6. إضافة اختبارات الوحدة والتكامل
7. إضافة أمثلة للعمليات المجمعة

**التوافق مع الإصدارات السابقة**: واجهة جديدة فقط. لا يوجد تأثير على التعليمات البرمجية الحالية.

#### المرحلة الخامسة: تحقيق التكافؤ والتحسين (الأسبوع الخامس)

1. إضافة `graph_embeddings_query()` إلى REST `FlowInstance`
2. تنفيذ الفئة `Metrics`
3. إضافة اختبارات تكامل شاملة
4. قياس الأداء
5. تحديث جميع الوثائق
6. إنشاء دليل ترحيل

**التوافق مع الإصدارات السابقة**: طرق جديدة فقط. لا يوجد تأثير على التعليمات البرمجية الحالية.

### نماذج البيانات

#### اختيار الواجهة

```python
# Single API instance, same URL for all interfaces
api = Api(url="http://localhost:8088/")

# Synchronous interfaces
rest_flow = api.flow().id("default")           # Sync REST
socket_flow = api.socket().flow("default")     # Sync WebSocket
bulk = api.bulk()                               # Sync bulk operations
metrics = api.metrics()                         # Sync metrics

# Asynchronous interfaces
async_rest_flow = api.async_flow().id("default")      # Async REST
async_socket_flow = api.async_socket().flow("default") # Async WebSocket
async_bulk = api.async_bulk()                          # Async bulk operations
async_metrics = api.async_metrics()                    # Async metrics
```

#### أنواع الاستجابة المتدفقة

**تدفق الوكيل (Agent Streaming):**

```python
api = Api(url="http://localhost:8088/")

# REST interface - non-streaming (existing)
rest_flow = api.flow().id("default")
response = rest_flow.agent(question="What is ML?", user="user123")
print(response["response"])

# WebSocket interface - non-streaming (same signature)
socket_flow = api.socket().flow("default")
response = socket_flow.agent(question="What is ML?", user="user123")
print(response["response"])

# WebSocket interface - streaming (new)
for chunk in socket_flow.agent(question="What is ML?", user="user123", streaming=True):
    if isinstance(chunk, AgentThought):
        print(f"Thinking: {chunk.content}")
    elif isinstance(chunk, AgentObservation):
        print(f"Observed: {chunk.content}")
    elif isinstance(chunk, AgentAnswer):
        print(f"Answer: {chunk.content}")
        if chunk.end_of_dialog:
            break
```

**البث المتدفق (RAG Streaming):**

```python
api = Api(url="http://localhost:8088/")

# REST interface - non-streaming (existing)
rest_flow = api.flow().id("default")
response = rest_flow.graph_rag(question="What is Python?", user="user123", collection="default")
print(response)

# WebSocket interface - streaming (new)
socket_flow = api.socket().flow("default")
for chunk in socket_flow.graph_rag(
    question="What is Python?",
    user="user123",
    collection="default",
    streaming=True
):
    print(chunk.content, end="", flush=True)
    if chunk.end_of_stream:
        break
```

**العمليات المجمعة (المزامنة):**

```python
api = Api(url="http://localhost:8088/")

# Bulk import triples
def triple_generator():
    yield Triple(s="http://ex.com/alice", p="http://ex.com/type", o="Person")
    yield Triple(s="http://ex.com/alice", p="http://ex.com/name", o="Alice")
    yield Triple(s="http://ex.com/bob", p="http://ex.com/type", o="Person")

bulk = api.bulk()
bulk.import_triples(flow="default", triples=triple_generator())

# Bulk export triples
for triple in bulk.export_triples(flow="default"):
    print(f"{triple.s} -> {triple.p} -> {triple.o}")
```

**العمليات المجمعة (غير متزامنة):**

```python
import asyncio

async def main():
    api = Api(url="http://localhost:8088/")

    # Async bulk import triples
    async def async_triple_generator():
        yield Triple(s="http://ex.com/alice", p="http://ex.com/type", o="Person")
        yield Triple(s="http://ex.com/alice", p="http://ex.com/name", o="Alice")
        yield Triple(s="http://ex.com/bob", p="http://ex.com/type", o="Person")

    bulk = api.async_bulk()
    await bulk.import_triples(flow="default", triples=async_triple_generator())

    # Async bulk export triples
    async for triple in bulk.export_triples(flow="default"):
        print(f"{triple.s} -> {triple.p} -> {triple.o}")

asyncio.run(main())
```

**مثال REST غير المتزامن:**

```python
import asyncio

async def main():
    api = Api(url="http://localhost:8088/")

    # Async REST flow operations
    flow = api.async_flow().id("default")
    response = await flow.agent(question="What is ML?", user="user123")
    print(response["response"])

asyncio.run(main())
```

**مثال على بث WebSocket غير المتزامن:**

```python
import asyncio

async def main():
    api = Api(url="http://localhost:8088/")

    # Async WebSocket streaming
    socket = api.async_socket()
    flow = socket.flow("default")

    async for chunk in flow.agent(question="What is ML?", user="user123", streaming=True):
        if isinstance(chunk, AgentAnswer):
            print(chunk.content, end="", flush=True)
            if chunk.end_of_dialog:
                break

asyncio.run(main())
```

### واجهات برمجة التطبيقات (APIs)

#### واجهات برمجة تطبيقات جديدة

1. **فئة واجهة برمجة التطبيقات الأساسية (Core API Class)**:
   **متزامن (Synchronous)**:
     `Api.socket()` - الحصول على عميل WebSocket متزامن
     `Api.bulk()` - الحصول على عميل العمليات المجمعة متزامن
     `Api.metrics()` - الحصول على عميل المقاييس متزامن
     `Api.close()` - إغلاق جميع الاتصالات المتزامنة
     دعم مدير السياق (`__enter__`, `__exit__`)
   **غير متزامن (Asynchronous)**:
     `Api.async_flow()` - الحصول على عميل تدفق REST غير متزامن
     `Api.async_socket()` - الحصول على عميل WebSocket غير متزامن
     `Api.async_bulk()` - الحصول على عميل العمليات المجمعة غير متزامن
     `Api.async_metrics()` - الحصول على عميل المقاييس غير متزامن
     `Api.aclose()` - إغلاق جميع الاتصالات غير المتزامنة
     دعم مدير السياق غير المتزامن (`__aenter__`, `__aexit__`)

2. **عميل WebSocket متزامن**:
   `SocketClient.flow(flow_id)` - الحصول على مثيل تدفق WebSocket
   `SocketFlowInstance.agent(..., streaming: bool = False)` - وكيل مع دعم اختياري للتدفق
   `SocketFlowInstance.text_completion(..., streaming: bool = False)` - إكمال النص مع دعم اختياري للتدفق
   `SocketFlowInstance.graph_rag(..., streaming: bool = False)` - استعلام Graph RAG مع دعم اختياري للتدفق
   `SocketFlowInstance.document_rag(..., streaming: bool = False)` - استعلام Document RAG مع دعم اختياري للتدفق
   `SocketFlowInstance.prompt(..., streaming: bool = False)` - استعلام Prompt مع دعم اختياري للتدفق
   `SocketFlowInstance.graph_embeddings_query()` - استعلام تضمينات الرسم البياني
   جميع طرق FlowInstance الأخرى بنفس التوقيعات

3. **عميل WebSocket غير متزامن**:
   `AsyncSocketClient.flow(flow_id)` - الحصول على مثيل تدفق WebSocket غير متزامن
   `AsyncSocketFlowInstance.agent(..., streaming: bool = False)` - وكيل غير متزامن مع دعم اختياري للتدفق
   `AsyncSocketFlowInstance.text_completion(..., streaming: bool = False)` - إكمال نص غير متزامن مع دعم اختياري للتدفق
   `AsyncSocketFlowInstance.graph_rag(..., streaming: bool = False)` - استعلام Graph RAG غير متزامن مع دعم اختياري للتدفق
   `AsyncSocketFlowInstance.document_rag(..., streaming: bool = False)` - استعلام Document RAG غير متزامن مع دعم اختياري للتدفق
   `AsyncSocketFlowInstance.prompt(..., streaming: bool = False)` - استعلام Prompt غير متزامن مع دعم اختياري للتدفق
   `AsyncSocketFlowInstance.graph_embeddings_query()` - استعلام تضمينات الرسم البياني غير المتزامن
   جميع طرق FlowInstance الأخرى كإصدارات غير متزامنة

4. **عميل العمليات المجمعة متزامن**:
   `BulkClient.import_triples(flow, triples)` - استيراد مجمع ثلاثيات
   `BulkClient.export_triples(flow)` - تصدير مجمع ثلاثيات
   `BulkClient.import_graph_embeddings(flow, embeddings)` - استيراد مجمع تضمينات الرسم البياني
   `BulkClient.export_graph_embeddings(flow)` - تصدير مجمع تضمينات الرسم البياني
   `BulkClient.import_document_embeddings(flow, embeddings)` - استيراد مجمع تضمينات المستندات
   `BulkClient.export_document_embeddings(flow)` - تصدير مجمع تضمينات المستندات
   `BulkClient.import_entity_contexts(flow, contexts)` - استيراد مجمع سياقات الكيانات
   `BulkClient.export_entity_contexts(flow)` - تصدير مجمع سياقات الكيانات
   `BulkClient.import_objects(flow, objects)` - استيراد مجمع الكائنات

5. **عميل العمليات المجمعة غير المتزامن**:
   `AsyncBulkClient.import_triples(flow, triples)` - استيراد مجمع ثلاثيات غير متزامن
   `AsyncBulkClient.export_triples(flow)` - تصدير مجمع ثلاثيات غير متزامن
   `AsyncBulkClient.import_graph_embeddings(flow, embeddings)` - استيراد مجمع تضمينات الرسم البياني غير المتزامن
   `AsyncBulkClient.export_graph_embeddings(flow)` - تصدير مجمع تضمينات الرسم البياني غير المتزامن
   `AsyncBulkClient.import_document_embeddings(flow, embeddings)` - استيراد مجمع تضمينات المستندات غير المتزامن
   `AsyncBulkClient.export_document_embeddings(flow)` - تصدير مجمع تضمينات المستندات غير المتزامن
   `AsyncBulkClient.import_entity_contexts(flow, contexts)` - استيراد مجمع سياقات الكيانات غير المتزامن
   `AsyncBulkClient.export_entity_contexts(flow)` - تصدير مجمع سياقات الكيانات غير المتزامن
   `AsyncBulkClient.import_objects(flow, objects)` - استيراد مجمع الكائنات غير المتزامن

6. **عميل تدفق REST غير المتزامن**:
   `AsyncFlow.list()` - سرد جميع التدفقات (غير متزامن)
   `AsyncFlow.get(id)` - الحصول على تعريف التدفق (غير متزامن)
   `AsyncFlow.start(...)` - بدء التدفق (غير متزامن)
   `AsyncFlow.stop(id)` - إيقاف التدفق (غير متزامن)
   `AsyncFlow.id(flow_id)` - الحصول على مثيل تدفق (غير متزامن)
   `AsyncFlowInstance.agent(...)` - تنفيذ الوكيل (غير متزامن)
   `AsyncFlowInstance.text_completion(...)` - إكمال النص (غير متزامن)
   `AsyncFlowInstance.graph_rag(...)` - Graph RAG (غير متزامن)
   جميع طرق FlowInstance الأخرى كإصدارات غير متزامنة

7. **عملاء المقاييس**:
   `Metrics.get()` - مقاييس Prometheus متزامنة
   `AsyncMetrics.get()` - مقاييس Prometheus غير متزامنة

8. **تحسين واجهة برمجة تطبيقات REST للتدفق**:
   `FlowInstance.graph_embeddings_query()` - استعلام تضمينات الرسم البياني (للتوافق مع الميزات المتزامنة)
   `AsyncFlowInstance.graph_embeddings_query()` - استعلام تضمينات الرسم البياني (للتوافق مع الميزات غير المتزامنة)

#### واجهات برمجة تطبيقات معدلة

1. **المنشئ (Constructor)** (تحسين طفيف):
   ```python
   Api(url: str, timeout: int = 60, token: Optional[str] = None)
   ```
   تمت إضافة المعامل `token` (اختياري، للمصادقة).
   إذا لم يتم تحديد `None` (افتراضيًا): لم يتم استخدام أي مصادقة.
   إذا تم تحديده: يتم استخدامه كرمز مميز (bearer token) لواجهة برمجة التطبيقات REST (`Authorization: Bearer <token>`)، ومعامل استعلام لـ WebSocket (`?token=<token>`).
   لا توجد تغييرات أخرى - متوافق تمامًا مع الإصدارات السابقة.

2. **لا توجد تغييرات جذرية**:
   جميع طرق واجهة برمجة التطبيقات REST الحالية لم تتغير.
   تمت الحفاظ على جميع التوقيعات الحالية.
   تمت الحفاظ على جميع أنواع الإرجاع الحالية.

### تفاصيل التنفيذ

#### معالجة الأخطاء

**أخطاء اتصال WebSocket**:
```python
try:
    api = Api(url="http://localhost:8088/")
    socket = api.socket()
    socket_flow = socket.flow("default")
    response = socket_flow.agent(question="...", user="user123")
except ConnectionError as e:
    print(f"WebSocket connection failed: {e}")
    print("Hint: Ensure Gateway is running and WebSocket endpoint is accessible")
```

**العودة السلسة:**
```python
api = Api(url="http://localhost:8088/")

try:
    # Try WebSocket streaming first
    socket_flow = api.socket().flow("default")
    for chunk in socket_flow.agent(question="...", user="...", streaming=True):
        print(chunk.content)
except ConnectionError:
    # Fall back to REST non-streaming
    print("WebSocket unavailable, falling back to REST")
    rest_flow = api.flow().id("default")
    response = rest_flow.agent(question="...", user="...")
    print(response["response"])
```

**أخطاء البث الجزئي:**
```python
api = Api(url="http://localhost:8088/")
socket_flow = api.socket().flow("default")

accumulated = []
try:
    for chunk in socket_flow.graph_rag(question="...", streaming=True):
        accumulated.append(chunk.content)
        if chunk.error:
            print(f"Error occurred: {chunk.error}")
            print(f"Partial response: {''.join(accumulated)}")
            break
except Exception as e:
    print(f"Streaming error: {e}")
    print(f"Partial response: {''.join(accumulated)}")
```

#### إدارة الموارد

**دعم مدير السياق:**
```python
# Automatic cleanup
with Api(url="http://localhost:8088/") as api:
    socket_flow = api.socket().flow("default")
    response = socket_flow.agent(question="...", user="user123")
# All connections automatically closed

# Manual cleanup
api = Api(url="http://localhost:8088/")
try:
    socket_flow = api.socket().flow("default")
    response = socket_flow.agent(question="...", user="user123")
finally:
    api.close()  # Explicitly close all connections (WebSocket, bulk, etc.)
```

#### الترابط والتزامن

**أمان الترابط**:
تحتفظ كل نسخة من `Api` باتصالها الخاص.
يستخدم نقل WebSocket الأقفال لعملية تعدد المهام الآمنة للطلبات.
يمكن للعديد من سلاسل العمل (threads) مشاركة نسخة واحدة من `Api` بأمان.
مُكررات التدفق (streaming iterators) ليست آمنة للترابط (يجب استهلاكها من سلسلة عمل واحدة).

**دعم غير متزامن** (للمستقبل):
```python
# Phase 2 enhancement (not in initial scope)
import asyncio

async def main():
    api = await AsyncApi(url="ws://localhost:8088/")
    flow = api.flow().id("default")

    async for chunk in flow.agent(question="...", streaming=True):
        print(chunk.content)

    await api.close()

asyncio.run(main())
```

## اعتبارات الأمان

### المصادقة

**المعلمة الرمز:**
```python
# No authentication (default)
api = Api(url="http://localhost:8088/")

# With authentication
api = Api(url="http://localhost:8088/", token="mytoken")
```

**نقل REST:**
رمز مميز عبر رأس `Authorization`
يتم تطبيقه تلقائيًا على جميع طلبات REST
التنسيق: `Authorization: Bearer <token>`

**نقل WebSocket:**
رمز مميز عبر معلمة الاستعلام المضافة إلى عنوان URL الخاص بـ WebSocket
يتم تطبيقه تلقائيًا أثناء إنشاء الاتصال
التنسيق: `ws://localhost:8088/api/v1/socket?token=<token>`

**التنفيذ:**
```python
class SocketClient:
    def _connect(self) -> WebSocket:
        # Construct WebSocket URL with optional token
        ws_url = f"{self.url}/api/v1/socket"
        if self.token:
            ws_url = f"{ws_url}?token={self.token}"
        # Connect to WebSocket
        return websocket.connect(ws_url)
```

**مثال:**
```python
# REST with auth
api = Api(url="http://localhost:8088/", token="mytoken")
flow = api.flow().id("default")
# All REST calls include: Authorization: Bearer mytoken

# WebSocket with auth
socket = api.socket()
# Connects to: ws://localhost:8088/api/v1/socket?token=mytoken
```

### الاتصالات الآمنة

يدعم كل من البروتوكولين WS (WebSocket) و WSS (WebSocket Secure).
التحقق من صحة شهادة TLS لاتصالات WSS.
تعطيل اختياري للتحقق من الشهادة لأغراض التطوير (مع تحذير).

### التحقق من صحة البيانات المدخلة

التحقق من صحة مخططات عناوين URL (http، https، ws، wss).
التحقق من صحة قيم معلمات النقل.
التحقق من صحة مجموعات معلمات التدفق.
التحقق من صحة أنواع بيانات الاستيراد المجمعة.

## اعتبارات الأداء

### تحسينات في زمن الاستجابة

**عمليات LLM المتدفقة**:
**الوقت اللازم للحصول على أول رمز**: ~500 مللي ثانية (مقارنة بـ ~30 ثانية بدون تدفق).
**التحسين**: أداء أسرع بمقدار 60 مرة.
**ينطبق على**: الوكيل، و Graph RAG، و Document RAG، وإكمال النص، والموجه.

**الاتصالات المستمرة**:
**تكلفة الاتصال**: يتم إلغاؤها للطلبات اللاحقة.
**مصافحة WebSocket**: تكلفة لمرة واحدة (~100 مللي ثانية).
**ينطبق على**: جميع العمليات عند استخدام نقل WebSocket.

### تحسينات في الإنتاجية

**العمليات المجمعة**:
**استيراد الثلاثيات**: ~10,000 ثلاثية/ثانية (مقارنة بـ ~100/ثانية باستخدام REST لكل عنصر).
**استيراد التضمينات**: ~5,000 تضمين/ثانية (مقارنة بـ ~50/ثانية باستخدام REST لكل عنصر).
**التحسين**: زيادة في الإنتاجية بمقدار 100 مرة للعمليات المجمعة.

**تعدد الطلبات**:
**الطلبات المتزامنة**: تصل إلى 15 طلبًا متزامنًا عبر اتصال واحد.
**إعادة استخدام الاتصال**: لا توجد تكلفة إضافية للاتصال للعمليات المتزامنة.

### اعتبارات الذاكرة

**الاستجابات المتدفقة**:
استخدام ثابت للذاكرة (معالجة أجزاء البيانات عند وصولها).
لا يتم تخزين الاستجابة بأكملها في الذاكرة.
مناسب للإخراجات الطويلة جدًا (>1 ميجابايت).

**العمليات المجمعة**:
معالجة قائمة (استخدام ثابت للذاكرة).
لا يتم تحميل مجموعة البيانات بأكملها في الذاكرة.
مناسب لمجموعات البيانات التي تحتوي على ملايين العناصر.

### المقاييس (المتوقعة)

| العملية | REST (الحالي) | WebSocket (تدفق) | التحسين |
|-----------|----------------|----------------------|-------------|
| الوكيل (الوقت اللازم للحصول على أول رمز) | 30 ثانية | 0.5 ثانية | 60x |
| Graph RAG (الوقت اللازم للحصول على أول رمز) | 25 ثانية | 0.5 ثانية | 50x |
| استيراد 10 آلاف ثلاثية | 100 ثانية | 1 ثانية | 100x |
| استيراد 1 مليون ثلاثية | 10,000 ثانية (2.7 ساعة) | 100 ثانية (1.6 دقيقة) | 100x |
| 10 طلبات صغيرة متزامنة | 5 ثوانٍ (تسلسلي) | 0.5 ثانية (متوازي) | 10x |

## استراتيجية الاختبار

### اختبارات الوحدة

**طبقة النقل** (`test_transport.py`):
اختبار طلب/استجابة النقل REST
اختبار اتصال نقل WebSocket
اختبار إعادة اتصال نقل WebSocket
اختبار تعدد الطلبات
اختبار تحليل الاستجابة المتدفقة
محاكاة خادم WebSocket للاختبارات الحتمية

**طرق واجهة برمجة التطبيقات (API)** (`test_flow.py`، `test_library.py`، إلخ):
اختبار الطرق الجديدة باستخدام النقل المُحاكى
اختبار معالجة المعلمات المتدفقة
اختبار مُكررات العمليات المجمعة
اختبار معالجة الأخطاء

**الأنواع** (`test_types.py`):
اختبار أنواع الشرائح المتدفقة الجديدة
اختبار تسلسل/إلغاء تسلسل الأنواع

### اختبارات التكامل

**REST من طرف إلى طرف** (`test_integration_rest.py`):
اختبار جميع العمليات مقابل البوابة الحقيقية (وضع REST)
التحقق من التوافق مع الإصدارات السابقة
اختبار حالات الخطأ

**WebSocket من طرف إلى طرف** (`test_integration_websocket.py`):
اختبار جميع العمليات مقابل البوابة الحقيقية (وضع WebSocket)
اختبار العمليات المتدفقة
اختبار العمليات المجمعة
اختبار الطلبات المتزامنة
اختبار استعادة الاتصال

**خدمات التدفق** (`test_streaming_integration.py`):
اختبار تدفق الوكيل (الأفكار، والملاحظات، والإجابات)
اختبار تدفق RAG (أجزاء متزايدة)
اختبار تدفق إكمال النص (رمز تلو رمز)
اختبار تدفق المطالبات
اختبار معالجة الأخطاء أثناء التدفق

**العمليات المجمعة** (`test_bulk_integration.py`):
اختبار استيراد/تصدير مجمّع للثلاثيات (1K، 10K، 100K عناصر)
اختبار استيراد/تصدير مجمّع للتضمينات
اختبار استخدام الذاكرة أثناء العمليات المجمعة
اختبار تتبع التقدم

### اختبارات الأداء

**معايير زمن الوصول** (`test_performance_latency.py`):
قياس الوقت اللازم للرمز الأول (تدفق مقابل عدم تدفق)
قياس النفقات العامة للاتصال (REST مقابل WebSocket)
مقارنة بالمعايير المتوقعة

**معايير الإنتاجية** (`test_performance_throughput.py`):
قياس إنتاجية الاستيراد المجمّع
قياس كفاءة تعدد الطلبات
مقارنة بالمعايير المتوقعة

### اختبارات التوافق

**التوافق مع الإصدارات السابقة** (`test_backward_compatibility.py`):
تشغيل مجموعة الاختبار الحالية مقابل واجهة برمجة التطبيقات المعاد هيكلتها
التحقق من عدم وجود تغييرات فاصلة
اختبار مسار الترحيل للأنماط الشائعة

## خطة الترحيل

### المرحلة 1: الترحيل الشفاف (افتراضي)

**لا يلزم إجراء أي تغييرات في التعليمات البرمجية**. يستمر التعليم البرمجي الحالي في العمل:

```python
# Existing code works unchanged
api = Api(url="http://localhost:8088/")
flow = api.flow().id("default")
response = flow.agent(question="What is ML?", user="user123")
```

### المرحلة الثانية: البث الاختياري (بسيط)

**استخدم واجهة `api.socket()` لتمكين البث:**

```python
# Before: Non-streaming REST
api = Api(url="http://localhost:8088/")
rest_flow = api.flow().id("default")
response = rest_flow.agent(question="What is ML?", user="user123")
print(response["response"])

# After: Streaming WebSocket (same parameters!)
api = Api(url="http://localhost:8088/")  # Same URL
socket_flow = api.socket().flow("default")

for chunk in socket_flow.agent(question="What is ML?", user="user123", streaming=True):
    if isinstance(chunk, AgentAnswer):
        print(chunk.content, end="", flush=True)
```

**النقاط الرئيسية:**
نفس عنوان URL لكل من REST و WebSocket.
نفس توقيعات الطرق (سهولة الترحيل).
فقط أضف `.socket()` و `streaming=True`.

### المرحلة الثالثة: العمليات المجمعة (قدرة جديدة).

**استخدم واجهة `api.bulk()`** لمجموعات البيانات الكبيرة:

```python
# Before: Inefficient per-item operations
api = Api(url="http://localhost:8088/")
flow = api.flow().id("default")

for triple in my_large_triple_list:
    # Slow per-item operations
    # (no direct bulk insert in REST API)
    pass

# After: Efficient bulk loading
api = Api(url="http://localhost:8088/")  # Same URL
bulk = api.bulk()

# This is fast (10,000 triples/second)
bulk.import_triples(flow="default", triples=iter(my_large_triple_list))
```

### تحديثات الوثائق

1. **README.md**: إضافة أمثلة للبث و WebSocket
2. **مرجع واجهة برمجة التطبيقات (API Reference)**: توثيق جميع الطرق والمعلمات الجديدة
3. **دليل الترحيل (Migration Guide)**: دليل خطوة بخطوة لتمكين البث
4. **أمثلة (Examples)**: إضافة نصوص برمجية لأمثلة شائعة
5. **دليل الأداء (Performance Guide)**: توثيق التحسينات المتوقعة في الأداء

### سياسة الإيقاف

**لا يوجد إيقاف (No deprecations)**. تظل جميع واجهات برمجة التطبيقات الحالية مدعومة. هذا تحسين خالص.

## الجدول الزمني

### الأسبوع الأول: الأساس
طبقة تجريد النقل
إعادة هيكلة التعليمات البرمجية REST الحالية
اختبارات الوحدة لطبقة النقل
التحقق من التوافق مع الإصدارات السابقة

### الأسبوع الثاني: نقل بيانات WebSocket
تنفيذ نقل بيانات WebSocket
إدارة الاتصال وإعادة الاتصال
تعدد الطلبات
اختبارات الوحدة والتكامل

### الأسبوع الثالث: دعم البث
إضافة معلمة البث إلى طرق LLM
تنفيذ تحليل استجابة البث
إضافة أنواع أجزاء البث
اختبارات تكامل البث

### الأسبوع الرابع: العمليات المجمعة
إضافة طرق الاستيراد/التصدير المجمعة
تنفيذ عمليات قائمة على المكرر
اختبار الأداء
اختبارات تكامل العمليات المجمعة

### الأسبوع الخامس: تكافؤ الميزات والوثائق
إضافة استعلام تضمين الرسم البياني
إضافة واجهة برمجة تطبيقات المقاييس
وثائق شاملة
دليل الترحيل
إصدار مرشح

### الأسبوع السادس: الإصدار
اختبار تكامل نهائي
قياس الأداء
وثائق الإصدار
إعلان للمجتمع

**المدة الإجمالية**: 6 أسابيع

## أسئلة مفتوحة

### أسئلة تصميم واجهة برمجة التطبيقات

1. **دعم غير متزامن (Async Support)**: ✅ **تم الحل (RESOLVED)** - تم تضمين الدعم الكامل غير المتزامن في الإصدار الأولي
   تمت إضافة إصدارات غير متزامنة لجميع الواجهات: `async_flow()`، `async_socket()`، `async_bulk()`، `async_metrics()`
   يوفر تناسقًا كاملاً بين واجهات برمجة التطبيقات المتزامنة وغير المتزامنة
   ضروري لأطر العمل غير المتزامنة الحديثة (FastAPI, aiohttp)

2. **تتبع التقدم (Progress Tracking)**: هل يجب أن تدعم العمليات المجمعة استدعيات رد اتصال للتقدم؟
   ```python
   def progress_callback(processed: int, total: Optional[int]):
       print(f"Processed {processed} items")

   bulk.import_triples(flow="default", triples=triples, on_progress=progress_callback)
   ```
   **التوصية**: أضف في المرحلة الثانية. ليس ضروريًا للإصدار الأولي.

3. **مهلة البث (Streaming Timeout)**: كيف يجب أن نتعامل مع المهلات لعمليات البث؟
   **التوصية**: استخدم نفس المهلة المستخدمة في العمليات غير المباشرة، ولكن أعد ضبطها عند استلام كل جزء.

4. **تخزين الأجزاء مؤقتًا (Chunk Buffering)**: هل يجب علينا تخزين الأجزاء مؤقتًا أم إرجاعها على الفور؟
   **التوصية**: أرجعها على الفور لتقليل زمن الوصول.

5. **الخدمات العامة عبر WebSocket**: هل يجب أن يدعم `api.socket()` الخدمات العامة (المكتبة، المعرفة، المجموعة، التكوين) أم فقط الخدمات الخاصة بالنطاق (flow-scoped)؟
   **التوصية**: ابدأ بالخدمات الخاصة بالنطاق فقط (حيث يكون البث مهمًا). أضف الخدمات العامة إذا لزم الأمر في المرحلة الثانية.

### أسئلة التنفيذ

1. **مكتبة WebSocket**: هل يجب أن نستخدم `websockets`، `websocket-client`، أو `aiohttp`؟
   **التوصية**: `websockets` (غير متزامن، ناضج، مدعوم جيدًا). قم بتغليفه في واجهة متزامنة باستخدام `asyncio.run()`.

2. **تجميع الاتصالات (Connection Pooling)**: هل يجب أن ندعم مثيلات متعددة متزامنة من `Api` تشارك مجموعة اتصالات؟
   **التوصية**: تؤجل إلى المرحلة الثانية. كل مثيل من `Api` لديه اتصالات خاصة به في البداية.

3. **إعادة استخدام الاتصال (Connection Reuse)**: هل يجب أن تشارك `SocketClient` و `BulkClient` نفس اتصال WebSocket، أم تستخدم اتصالات منفصلة؟
   **التوصية**: اتصالات منفصلة. تطبيق أبسط، وفصل واضح للمسؤوليات.

4. **الاتصال الكسول مقابل الاتصال الحماسي (Lazy vs Eager Connection)**: هل يجب إنشاء اتصال WebSocket في `api.socket()` أم عند الطلب الأول؟
   **التوصية**: كسول (عند الطلب الأول). يتجنب تكلفة الاتصال إذا كان المستخدم يستخدم فقط طرق REST.

### أسئلة الاختبار

1. **بوابة وهمية (Mock Gateway)**: هل يجب علينا إنشاء بوابة وهمية خفيفة الوزن للاختبار، أم الاختبار مقابل البوابة الحقيقية؟
   **التوصية**: كلاهما. استخدم الوهميات للاختبارات الوحدوية، والبوابة الحقيقية للاختبارات التكاملية.

2. **اختبارات الانحدار في الأداء (Performance Regression Tests)**: هل يجب علينا إضافة اختبارات أداء انحدار آلية إلى CI؟
   **التوصية**: نعم، ولكن مع حدود سماح كبيرة لمراعاة تباين بيئة CI.

## المراجع

### المواصفات التقنية ذات الصلة
`docs/tech-specs/streaming-llm-responses.md` - تطبيق البث في البوابة
`docs/tech-specs/rag-streaming-support.md` - دعم البث لـ RAG

### ملفات التنفيذ
`trustgraph-base/trustgraph/api/` - مصدر واجهة برمجة التطبيقات (API) بلغة Python
`trustgraph-flow/trustgraph/gateway/` - مصدر البوابة
`trustgraph-flow/trustgraph/gateway/dispatch/mux.py` - تطبيق مرجعي لتقسيم WebSocket

### التوثيق
`docs/apiSpecification.md` - مرجع API كامل
`docs/api-status-summary.md` - ملخص حالة API
`README.websocket` - توثيق بروتوكول WebSocket
`STREAMING-IMPLEMENTATION-NOTES.txt` - ملاحظات حول تطبيق البث

### المكتبات الخارجية
`websockets` - مكتبة WebSocket بلغة Python (https://websockets.readthedocs.io/)
`requests` - مكتبة HTTP بلغة Python (موجودة)
