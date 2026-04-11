# خدمات الأدوات: أدوات وكيل قابلة للتوصيل ديناميكيًا

## الحالة

تم التنفيذ

## نظرة عامة

تحدد هذه المواصفات آلية لأدوات وكيل قابلة للتوصيل ديناميكيًا تسمى "خدمات الأدوات". على عكس أنواع الأدوات المضمنة الحالية (`KnowledgeQueryImpl`، `McpToolImpl`، إلخ)، تسمح خدمات الأدوات بإدخال أدوات جديدة عن طريق:

1. نشر خدمة جديدة تعتمد على Pulsar
2. إضافة وصف تهيئة يخبر الوكيل كيفية استدعائها

يتيح ذلك إمكانية التوسع دون تعديل إطار عمل الاستجابة الأساسي للوكيل.

## المصطلحات

| المصطلح | التعريف |
|------|------------|
| **أداة مضمنة** | أنواع الأدوات الحالية مع تطبيقات مضمنة في `tools.py` |
| **خدمة أداة** | خدمة Pulsar التي يمكن استدعاؤها كأداة وكيل، ويتم تعريفها بواسطة وصف الخدمة |
| **أداة** | نسخة مُكوّنة تشير إلى خدمة أداة، وتُعرض للوكيل/نموذج اللغة الكبير |

هذا نموذج من مستويين، مماثل لأدوات MCP:
MCP: يحدد خادم MCP واجهة الأداة → إعداد الأداة يشير إليها
خدمات الأدوات: تحدد خدمة الأداة واجهة Pulsar → إعداد الأداة يشير إليها

## الخلفية: الأدوات الحالية

### تنفيذ الأداة المضمنة

يتم تعريف الأدوات حاليًا في `trustgraph-flow/trustgraph/agent/react/tools.py` مع تطبيقات مُصنّفة:

```python
class KnowledgeQueryImpl:
    async def invoke(self, question):
        client = self.context("graph-rag-request")
        return await client.rag(question, self.collection)
```

كل نوع أداة:
لديه خدمة Pulsar مُبرمجة مسبقًا والتي يستدعيها (مثل: `graph-rag-request`)
يعرف بالضبط الطريقة التي يجب استدعاؤها على العميل (مثل: `client.rag()`)
لديه وسائط مُعرّفة من النوع في التنفيذ

### تسجيل الأدوات (service.py:105-214)

يتم تحميل الأدوات من ملف التكوين باستخدام حقل `type` والذي يربط بتنفيذ:

```python
if impl_id == "knowledge-query":
    impl = functools.partial(KnowledgeQueryImpl, collection=data.get("collection"))
elif impl_id == "text-completion":
    impl = TextCompletionImpl
# ... etc
```

## العمارة

### نموذج ذو طبقتين

#### الطبقة الأولى: مُعرّف خدمة الأداة

تحدد خدمة الأداة واجهة خدمة Pulsar. وهي تُعلن عن:
قوائم انتظار Pulsar للطلبات/الاستجابات
معلمات التكوين التي تتطلبها من الأدوات التي تستخدمها

```json
{
  "id": "custom-rag",
  "request-queue": "non-persistent://tg/request/custom-rag",
  "response-queue": "non-persistent://tg/response/custom-rag",
  "config-params": [
    {"name": "collection", "required": true}
  ]
}
```

خدمة أداة لا تتطلب أي معلمات تهيئة:

```json
{
  "id": "calculator",
  "request-queue": "non-persistent://tg/request/calc",
  "response-queue": "non-persistent://tg/response/calc",
  "config-params": []
}
```

#### المستوى الثاني: وصف الأداة

تشير الأداة إلى خدمة الأداة وتوفر:
قيم معلمات التكوين (التي تلبي متطلبات الخدمة)
بيانات وصفية للأداة للوكيل (الاسم، الوصف)
تعريفات الوسائط لنموذج اللغة الكبيرة (LLM)

```json
{
  "type": "tool-service",
  "name": "query-customers",
  "description": "Query the customer knowledge base",
  "service": "custom-rag",
  "collection": "customers",
  "arguments": [
    {
      "name": "question",
      "type": "string",
      "description": "The question to ask about customers"
    }
  ]
}
```

يمكن لأدوات متعددة الإشارة إلى نفس الخدمة بتكوينات مختلفة:

```json
{
  "type": "tool-service",
  "name": "query-products",
  "description": "Query the product knowledge base",
  "service": "custom-rag",
  "collection": "products",
  "arguments": [
    {
      "name": "question",
      "type": "string",
      "description": "The question to ask about products"
    }
  ]
}
```

### تنسيق الطلب

عندما يتم استدعاء أداة، يتضمن الطلب المرسل إلى خدمة الأداة ما يلي:
`user`: من طلب الوكيل (دعم تعدد المستأجرين)
`config`: قيم التكوين المشفرة بتنسيق JSON والمستمدة من وصف الأداة
`arguments`: وسائط مشفرة بتنسيق JSON والمستمدة من نموذج اللغة الكبير (LLM)

```json
{
  "user": "alice",
  "config": "{\"collection\": \"customers\"}",
  "arguments": "{\"question\": \"What are the top customer complaints?\"}"
}
```

تتلقى خدمة الأداة هذه البيانات كقاموسات مُحللة في الطريقة `invoke`.

### تطبيق عام لخدمة الأداة

تستدعي فئة `ToolServiceImpl` خدمات الأداة بناءً على التكوين:

```python
class ToolServiceImpl:
    def __init__(self, context, request_queue, response_queue, config_values, arguments, processor):
        self.request_queue = request_queue
        self.response_queue = response_queue
        self.config_values = config_values  # e.g., {"collection": "customers"}
        # ...

    async def invoke(self, **arguments):
        client = await self._get_or_create_client()
        response = await client.call(user, self.config_values, arguments)
        if isinstance(response, str):
            return response
        else:
            return json.dumps(response)
```

## قرارات التصميم

### نموذج التكوين ثنائي الطبقات

تتبع خدمات الأدوات نموذجًا ثنائي الطبقات مشابهًا لأدوات MCP:

1. **خدمة الأداة**: تحدد واجهة خدمة Pulsar (الموضوع، ومعلمات التكوين المطلوبة).
2. **الأداة**: تشير إلى خدمة أداة، وتوفر قيم التكوين، وتحدد وسائط LLM.

يسمح هذا الفصل بما يلي:
يمكن لخدمة أداة واحدة أن تستخدمها أدوات متعددة بتكوينات مختلفة.
تمييز واضح بين واجهة الخدمة وتكوين الأداة.
إمكانية إعادة استخدام تعريفات الخدمة.

### تعيين الطلبات: تمرير مع الغلاف

الطلب إلى خدمة الأداة هو غلاف منظم يحتوي على:
`user`: يتم تمريره من طلب الوكيل لخدمة العملاء المتعددة.
قيم التكوين: من وصف الأداة (مثل `collection`).
`arguments`: وسائط LLM، يتم تمريرها كقاموس.

يقوم مدير الوكيل بتحليل استجابة LLM إلى `act.arguments` كقاموس (`agent_manager.py:117-154`). يتم تضمين هذا القاموس في غلاف الطلب.

### معالجة المخططات: غير مُعَرَّفة الأنواع

تستخدم الطلبات والاستجابات قواميس غير مُعَرَّفة الأنواع. لا يوجد تحقق من صحة المخطط على مستوى الوكيل - خدمة الأداة مسؤولة عن التحقق من صحة مدخلاتها. يوفر هذا أقصى قدر من المرونة لتعريف خدمات جديدة.

### واجهة العميل: مواضيع Pulsar مباشرة

تستخدم خدمات الأدوات مواضيع Pulsar مباشرة دون الحاجة إلى تكوين التدفق. يحدد وصف خدمة الأداة أسماء قائمة الانتظار الكاملة:

```json
{
  "id": "joke-service",
  "request-queue": "non-persistent://tg/request/joke",
  "response-queue": "non-persistent://tg/response/joke",
  "config-params": [...]
}
```

هذا يسمح باستضافة الخدمات في أي مساحة اسم.

### معالجة الأخطاء: الاصطلاح القياسي للأخطاء.

تتبع استجابات خدمات الأدوات الاصطلاح الحالي للمخطط مع حقل `error`:

```python
@dataclass
class Error:
    type: str = ""
    message: str = ""
```

هيكل الاستجابة:
النجاح: إذا كانت `error` تساوي `None`، تحتوي الاستجابة على النتيجة.
الخطأ: يتم ملء `error` بـ `type` و `message`.

هذا يتوافق مع النمط المستخدم في مخططات الخدمة الحالية (مثل: `PromptResponse`، `QueryResponse`، `AgentResponse`).

### الارتباط بين الطلبات والاستجابات

يتم ربط الطلبات والاستجابات باستخدام `id` في خصائص رسائل Pulsar:

يتضمن الطلب `id` في الخصائص: `properties={"id": id}`.
تتضمن الاستجابة (أو الاستجابات) نفس `id`: `properties={"id": id}`.

هذا يتبع النمط الحالي المستخدم في قاعدة التعليمات البرمجية بأكملها (مثل: `agent_service.py`، `llm_service.py`).

### دعم التدفق

يمكن لخدمات الأدوات إرجاع استجابات متدفقة:

رسائل استجابة متعددة بنفس `id` في الخصائص.
تتضمن كل استجابة حقل `end_of_stream: bool`.
تحتوي الاستجابة النهائية على `end_of_stream: True`.

هذا يتوافق مع النمط المستخدم في `AgentResponse` وخدمات التدفق الأخرى.

### معالجة الاستجابة: إرجاع سلسلة نصية

تتبع جميع الأدوات الموجودة نفس النمط: **استقبال الوسائط كقاموس، وإرجاع الملاحظة كسلسلة نصية**.

| الأداة | معالجة الاستجابة |
|------|------------------|
| `KnowledgeQueryImpl` | إرجاع `client.rag()` مباشرة (سلسلة نصية) |
| `TextCompletionImpl` | إرجاع `client.question()` مباشرة (سلسلة نصية) |
| `McpToolImpl` | إرجاع سلسلة نصية، أو `json.dumps(output)` إذا لم تكن سلسلة نصية |
| `StructuredQueryImpl` | تنسيق النتيجة إلى سلسلة نصية |
| `PromptImpl` | إرجاع `client.prompt()` مباشرة (سلسلة نصية) |

تتبع خدمات الأدوات نفس العقد:
تقوم الخدمة بإرجاع استجابة سلسلة نصية (الملاحظة).
إذا لم تكن الاستجابة سلسلة نصية، يتم تحويلها عبر `json.dumps()`.
لا يلزم وجود تكوين استخراج في الوصف.

هذا يبقي الوصف بسيطًا ويضع المسؤولية على الخدمة لإرجاع استجابة نصية مناسبة للوكيل.

## دليل التكوين

لإضافة خدمة أداة جديدة، يلزم وجود عنصرين في التكوين:

### 1. تكوين خدمة الأداة

يتم تخزينها تحت مفتاح التكوين `tool-service`. تحدد قوائم انتظار Pulsar والمعلمات التكوين المتاحة.

| الحقل | مطلوب | الوصف |
|-------|----------|-------------|
| `id` | نعم | معرف فريد لخدمة الأداة |
| `request-queue` | نعم | موضوع Pulsar الكامل للطلبات (مثل: `non-persistent://tg/request/joke`) |
| `response-queue` | نعم | موضوع Pulsar الكامل للاستجابات (مثل: `non-persistent://tg/response/joke`) |
| `config-params` | لا | مصفوفة من معلمات التكوين التي تقبلها الخدمة |

يمكن لكل معلمة تكوين تحديد:
`name`: اسم المعلمة (مطلوب)
`required`: ما إذا كان يجب توفير المعلمة بواسطة الأدوات (افتراضي: خطأ)

مثال:
```json
{
  "id": "joke-service",
  "request-queue": "non-persistent://tg/request/joke",
  "response-queue": "non-persistent://tg/response/joke",
  "config-params": [
    {"name": "style", "required": false}
  ]
}
```

### 2. إعدادات الأداة

يتم تخزينها تحت مفتاح التكوين `tool`. تحدد أداة يمكن للوكيل استخدامها.

| الحقل | مطلوب | الوصف |
|-------|----------|-------------|
| `type` | نعم | يجب أن يكون `"tool-service"` |
| `name` | نعم | اسم الأداة المعروضة لنظام LLM |
| `description` | نعم | وصف لما تفعله الأداة (يُعرض لنظام LLM) |
| `service` | نعم | معرف خدمة الأداة التي سيتم استدعاؤها |
| `arguments` | لا | مصفوفة من تعريفات الوسائط لنظام LLM |
| *(معلمات التكوين)* | يختلف | أي معلمات تكوين معرفة بواسطة الخدمة |

يمكن لكل وسيط تحديد:
`name`: اسم الوسيط (مطلوب)
`type`: نوع البيانات، على سبيل المثال، `"string"` (مطلوب)
`description`: الوصف المعروض لنظام LLM (مطلوب)

مثال:
```json
{
  "type": "tool-service",
  "name": "tell-joke",
  "description": "Tell a joke on a given topic",
  "service": "joke-service",
  "style": "pun",
  "arguments": [
    {
      "name": "topic",
      "type": "string",
      "description": "The topic for the joke (e.g., programming, animals, food)"
    }
  ]
}
```

### تحميل الإعدادات

استخدم `tg-put-config-item` لتحميل الإعدادات:

```bash
# Load tool-service config
tg-put-config-item tool-service/joke-service < joke-service.json

# Load tool config
tg-put-config-item tool/tell-joke < tell-joke.json
```

يجب إعادة تشغيل الوكيل الإداري لاستيعاب التكوينات الجديدة.

## تفاصيل التنفيذ

### المخطط

أنواع الطلبات والاستجابات في `trustgraph-base/trustgraph/schema/services/tool_service.py`:

```python
@dataclass
class ToolServiceRequest:
    user: str = ""           # User context for multi-tenancy
    config: str = ""         # JSON-encoded config values from tool descriptor
    arguments: str = ""      # JSON-encoded arguments from LLM

@dataclass
class ToolServiceResponse:
    error: Error | None = None
    response: str = ""       # String response (the observation)
    end_of_stream: bool = False
```

### الخادم: خدمة DynamicToolService

الفئة الأساسية في `trustgraph-base/trustgraph/base/dynamic_tool_service.py`:

```python
class DynamicToolService(AsyncProcessor):
    """Base class for implementing tool services."""

    def __init__(self, **params):
        topic = params.get("topic", default_topic)
        # Constructs topics: non-persistent://tg/request/{topic}, non-persistent://tg/response/{topic}
        # Sets up Consumer and Producer

    async def invoke(self, user, config, arguments):
        """Override this method to implement the tool's logic."""
        raise NotImplementedError()
```

### جانب العميل: ToolServiceImpl

التنفيذ في `trustgraph-flow/trustgraph/agent/react/tools.py`:

```python
class ToolServiceImpl:
    def __init__(self, context, request_queue, response_queue, config_values, arguments, processor):
        # Uses the provided queue paths directly
        # Creates ToolServiceClient on first use

    async def invoke(self, **arguments):
        client = await self._get_or_create_client()
        response = await client.call(user, config_values, arguments)
        return response if isinstance(response, str) else json.dumps(response)
```

### الملفات

| الملف | الغرض |
|------|---------|
| `trustgraph-base/trustgraph/schema/services/tool_service.py` | مخططات الطلبات والاستجابات |
| `trustgraph-base/trustgraph/base/tool_service_client.py` | عميل لاستدعاء الخدمات |
| `trustgraph-base/trustgraph/base/dynamic_tool_service.py` | الفئة الأساسية لتنفيذ الخدمة |
| `trustgraph-flow/trustgraph/agent/react/tools.py` | فئة `ToolServiceImpl` |
| `trustgraph-flow/trustgraph/agent/react/service.py` | تحميل التكوين |

### مثال: خدمة النكت

مثال لخدمة في `trustgraph-flow/trustgraph/tool_service/joke/`:

```python
class Processor(DynamicToolService):
    async def invoke(self, user, config, arguments):
        style = config.get("style", "pun")
        topic = arguments.get("topic", "")
        joke = pick_joke(topic, style)
        return f"Hey {user}! Here's a {style} for you:\n\n{joke}"
```

تكوين خدمة الأداة:
```json
{
  "id": "joke-service",
  "request-queue": "non-persistent://tg/request/joke",
  "response-queue": "non-persistent://tg/response/joke",
  "config-params": [{"name": "style", "required": false}]
}
```

إعدادات الأداة:
```json
{
  "type": "tool-service",
  "name": "tell-joke",
  "description": "Tell a joke on a given topic",
  "service": "joke-service",
  "style": "pun",
  "arguments": [
    {"name": "topic", "type": "string", "description": "The topic for the joke"}
  ]
}
```

### التوافق مع الإصدارات السابقة

تظل أنواع الأدوات المدمجة الحالية تعمل دون تغيير.
`tool-service` هو نوع أداة جديد بالإضافة إلى الأنواع الموجودة (`knowledge-query`، `mcp-tool`، إلخ).

## اعتبارات مستقبلية

### الخدمات ذات الإعلان الذاتي

يمكن أن تسمح ترقية مستقبلية للخدمات بنشر أوصافها الخاصة:

تنشر الخدمات إلى موضوع `tool-descriptors` معروف عند بدء التشغيل.
يشترك الوكيل ويسجل الأدوات ديناميكيًا.
يتيح ذلك إمكانية التوصيل والتشغيل الحقيقية دون تغييرات في التكوين.

هذا خارج نطاق التنفيذ الأولي.

## المراجع

التنفيذ الحالي للأداة: `trustgraph-flow/trustgraph/agent/react/tools.py`
تسجيل الأداة: `trustgraph-flow/trustgraph/agent/react/service.py:105-214`
مخططات الوكيل: `trustgraph-base/trustgraph/schema/services/agent.py`
