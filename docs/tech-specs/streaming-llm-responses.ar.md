# المواصفات الفنية لخدمة بث استجابات نماذج اللغة الكبيرة (LLM)

## نظرة عامة

تصف هذه المواصفات تنفيذ دعم البث لاستجابات نماذج اللغة الكبيرة في TrustGraph. يتيح البث التسليم في الوقت الفعلي للرموز (tokens) أثناء إنتاجها بواسطة نموذج اللغة الكبيرة، بدلاً من الانتظار حتى اكتمال توليد الاستجابة.

يدعم هذا التنفيذ حالات الاستخدام التالية:


1. **واجهات مستخدم في الوقت الفعلي**: بث الرموز إلى واجهة المستخدم أثناء إنشائها، مما يوفر ملاحظات مرئية فورية.

2. **تقليل وقت ظهور الرمز الأول**: يرى المستخدمون الإخراج على الفور بدلاً من الانتظار حتى اكتمال التوليد.
   
3. **التعامل مع الاستجابات الطويلة**: التعامل مع المخرجات الطويلة جدًا التي قد تتسبب خلاف ذلك في انتهاء المهلة أو تجاوز حدود الذاكرة.
   
4. **التطبيقات التفاعلية**: تمكين واجهات الدردشة والوكلاء المستجيبة.
   
## الأهداف


**التوافق مع الإصدارات السابقة**: تستمر العملاء الحاليون الذين لا يستخدمون البث في العمل دون تعديل.

  **تصميم واجهة برمجة تطبيقات (API) متسق**: يستخدم البث والواجهات غير المتدفقة نفس أنماط المخططات مع اختلافات قليلة.

  **مرونة مزود الخدمة**: دعم البث عند توفره، مع توفير آلية بديلة سلسة عند عدم توفره.

  **التطبيق المرحلي**: تطبيق تدريجي لتقليل المخاطر.

**دعم شامل**: دعم البث من مزود نموذج اللغة الكبيرة إلى تطبيقات العميل عبر Pulsar و Gateway API و Python API.
  
## الخلفية

### البنية الحالية


تعمل عملية إكمال النص الحالية لنماذج اللغة الكبيرة على النحو التالي:

1. يرسل العميل `TextCompletionRequest` مع حقول `system` و `prompt`.
2. تعالج خدمة نموذج اللغة الكبيرة الطلب وتنتظر اكتمال التوليد.
3. يتم إرجاع `TextCompletionResponse` واحد مع سلسلة `response` كاملة.

المخطط الحالي (`trustgraph-base/trustgraph/schema/services/llm.py`):

```python
class TextCompletionRequest(Record):
    system = String()
    prompt = String()

class TextCompletionResponse(Record):
    error = Error()
    response = String()
    in_token = Integer()
    out_token = Integer()
    model = String()
```

### القيود الحالية

**زمن الوصول (Latency)**: يجب على المستخدمين الانتظار حتى اكتمال الإنشاء قبل رؤية أي نتيجة.
**خطر انتهاء المهلة (Timeout)**: قد تتجاوز عمليات الإنشاء الطويلة حدود انتهاء المهلة الخاصة بالعميل.
**تجربة مستخدم سيئة (Poor UX)**: عدم وجود أي ملاحظات أثناء الإنشاء يخلق انطباعًا بالبطء.
**استخدام الموارد (Resource Usage)**: يجب تخزين الاستجابات الكاملة في الذاكرة.

تعالج هذه المواصفات هذه القيود من خلال تمكين التسليم التدريجي للاستجابة مع الحفاظ على التوافق الكامل مع الإصدارات السابقة.


## التصميم التقني

### المرحلة الأولى: البنية التحتية

تضع المرحلة الأولى الأساس للبث عن طريق تعديل المخططات وواجهات برمجة التطبيقات (APIs) وأدوات سطر الأوامر (CLI).


#### تغييرات المخططات

##### مخطط LLM (`trustgraph-base/trustgraph/schema/services/llm.py`)

**تغييرات الطلبات:**

```python
class TextCompletionRequest(Record):
    system = String()
    prompt = String()
    streaming = Boolean()  # NEW: Default false for backward compatibility
```

`streaming`: عندما `true`، يتم طلب تسليم الاستجابة بتدفق.
الافتراضي: `false` (يتم الحفاظ على السلوك الحالي).

**تغييرات في الاستجابة:**

```python
class TextCompletionResponse(Record):
    error = Error()
    response = String()
    in_token = Integer()
    out_token = Integer()
    model = String()
    end_of_stream = Boolean()  # NEW: Indicates final message
```

`end_of_stream`: عندما `true`، يشير هذا إلى أن هذا هو الرد النهائي (أو الوحيد).
للطلبات غير المتدفقة: رد واحد مع `end_of_stream=true`.
للطلبات المتدفقة: ردود متعددة، جميعها مع `end_of_stream=false`.
  باستثناء الرد النهائي.

##### مخطط المطالبة (`trustgraph-base/trustgraph/schema/services/prompt.py`).

خدمة المطالبة تغلف إكمال النص، وبالتالي فهي تعكس نفس النمط:

**تغييرات الطلب:**

```python
class PromptRequest(Record):
    id = String()
    terms = Map(String())
    streaming = Boolean()  # NEW: Default false
```

**التغييرات في الاستجابة:**

```python
class PromptResponse(Record):
    error = Error()
    text = String()
    object = String()
    end_of_stream = Boolean()  # NEW: Indicates final message
```

#### التغييرات في واجهة برمجة التطبيقات (API) الخاصة بالبوابة.

يجب أن تعرض واجهة برمجة التطبيقات (API) الخاصة بالبوابة إمكانات البث لعملاء HTTP/WebSocket.

**تحديثات واجهة برمجة التطبيقات (API) REST:**

`POST /api/v1/text-completion`: قبول المعامل `streaming` في نص الطلب.
يعتمد سلوك الاستجابة على علامة البث:
  `streaming=false`: استجابة JSON واحدة (السلوك الحالي).
  `streaming=true`: تدفق أحداث من الخادم (SSE) أو رسائل WebSocket.

**تنسيق الاستجابة (البث):**

يتبع كل جزء مُبث نفس هيكل المخطط.
```json
{
  "response": "partial text...",
  "end_of_stream": false,
  "model": "model-name"
}
```

الجزء الأخير:
```json
{
  "response": "final text chunk",
  "end_of_stream": true,
  "in_token": 150,
  "out_token": 500,
  "model": "model-name"
}
```

#### تغييرات في واجهة برمجة التطبيقات (API) الخاصة بـ Python

يجب أن تدعم واجهة برمجة التطبيقات (API) الخاصة بعميل Python كلاً من الأوضاع المتدفقة وغير المتدفقة
مع الحفاظ على التوافق مع الإصدارات السابقة.

**تحديثات لـ LlmClient** (`trustgraph-base/trustgraph/clients/llm_client.py`):

```python
class LlmClient(BaseClient):
    def request(self, system, prompt, timeout=300, streaming=False):
        """
        Non-streaming request (backward compatible).
        Returns complete response string.
        """
        # Existing behavior when streaming=False

    async def request_stream(self, system, prompt, timeout=300):
        """
        Streaming request.
        Yields response chunks as they arrive.
        """
        # New async generator method
```

**تحديثات PromptClient** (`trustgraph-base/trustgraph/base/prompt_client.py`):

نمط مشابه مع المعامل `streaming` وإصدار مولد غير متزامن.

#### تغييرات في أداة سطر الأوامر

**tg-invoke-llm** (`trustgraph-cli/trustgraph/cli/invoke_llm.py`):

```
tg-invoke-llm [system] [prompt] [--no-streaming] [-u URL] [-f flow-id]
```

تفعيل البث افتراضيًا لتحسين تجربة المستخدم التفاعلية.
العلم `--no-streaming` يعطل البث.
عند تفعيل البث: إخراج الرموز إلى الإخراج القياسي (stdout) فور وصولها.
عند عدم تفعيل البث: الانتظار حتى اكتمال الاستجابة، ثم إخراجها.

**tg-invoke-prompt** (`trustgraph-cli/trustgraph/cli/invoke_prompt.py`):

```
tg-invoke-prompt [template-id] [var=value...] [--no-streaming] [-u URL] [-f flow-id]
```

نفس النمط مثل `tg-invoke-llm`.

#### تغييرات في الفئة الأساسية لخدمة نماذج اللغة الكبيرة (LLM).

**LlmService** (`trustgraph-base/trustgraph/base/llm_service.py`):

```python
class LlmService(FlowProcessor):
    async def on_request(self, msg, consumer, flow):
        request = msg.value()
        streaming = getattr(request, 'streaming', False)

        if streaming and self.supports_streaming():
            async for chunk in self.generate_content_stream(...):
                await self.send_response(chunk, end_of_stream=False)
            await self.send_response(final_chunk, end_of_stream=True)
        else:
            response = await self.generate_content(...)
            await self.send_response(response, end_of_stream=True)

    def supports_streaming(self):
        """Override in subclass to indicate streaming support."""
        return False

    async def generate_content_stream(self, system, prompt, model, temperature):
        """Override in subclass to implement streaming."""
        raise NotImplementedError()
```

--

### المرحلة الثانية: إثبات المفهوم لـ VertexAI

تنفذ المرحلة الثانية البث في مزود واحد (VertexAI) للتحقق من صحة
البنية التحتية وتمكين الاختبار الشامل.

#### تنفيذ VertexAI

**الوحدة:** `trustgraph-vertexai/trustgraph/model/text_completion/vertexai/llm.py`

**التغييرات:**

1. تجاوز `supports_streaming()` لإرجاع `True`
2. تنفيذ مُولّد غير متزامن `generate_content_stream()`
3. التعامل مع نماذج Gemini و Claude (عبر واجهة برمجة تطبيقات VertexAI Anthropic)

**البث باستخدام Gemini:**

```python
async def generate_content_stream(self, system, prompt, model, temperature):
    model_instance = self.get_model(model, temperature)
    response = model_instance.generate_content(
        [system, prompt],
        stream=True  # Enable streaming
    )
    for chunk in response:
        yield LlmChunk(
            text=chunk.text,
            in_token=None,  # Available only in final chunk
            out_token=None,
        )
    # Final chunk includes token counts from response.usage_metadata
```

**كلود (عبر VertexAI من شركة Anthropic) - البث:**

```python
async def generate_content_stream(self, system, prompt, model, temperature):
    with self.anthropic_client.messages.stream(...) as stream:
        for text in stream.text_stream:
            yield LlmChunk(text=text)
    # Token counts from stream.get_final_message()
```

#### الاختبار

اختبارات الوحدة لتجميع الاستجابات المتدفقة.
اختبارات التكامل مع VertexAI (Gemini و Claude).
اختبارات شاملة: سطر الأوامر -> البوابة -> Pulsar -> VertexAI -> العودة.
اختبارات التوافق مع الإصدارات السابقة: لا تزال طلبات عدم التدفق تعمل.

--

### المرحلة الثالثة: جميع مزودي نماذج اللغة الكبيرة

تمتد المرحلة الثالثة لدعم التدفق إلى جميع مزودي نماذج اللغة الكبيرة في النظام.

#### حالة تنفيذ المزود

يجب على كل مزود إما:
1. **دعم كامل للتدفق**: تنفيذ `generate_content_stream()`
2. **وضع التوافق**: التعامل مع علامة `end_of_stream` بشكل صحيح
   (إرجاع استجابة واحدة مع `end_of_stream=true`)

| المزود | الحزمة | دعم التدفق |
|----------|---------|-------------------|
| OpenAI | trustgraph-flow | كامل (واجهة برمجة تطبيقات تدفق أصلية) |
| Claude/Anthropic | trustgraph-flow | كامل (واجهة برمجة تطبيقات تدفق أصلية) |
| Ollama | trustgraph-flow | كامل (واجهة برمجة تطبيقات تدفق أصلية) |
| Cohere | trustgraph-flow | كامل (واجهة برمجة تطبيقات تدفق أصلية) |
| Mistral | trustgraph-flow | كامل (واجهة برمجة تطبيقات تدفق أصلية) |
| Azure OpenAI | trustgraph-flow | كامل (واجهة برمجة تطبيقات تدفق أصلية) |
| Google AI Studio | trustgraph-flow | كامل (واجهة برمجة تطبيقات تدفق أصلية) |
| VertexAI | trustgraph-vertexai | كامل (المرحلة الثانية) |
| Bedrock | trustgraph-bedrock | كامل (واجهة برمجة تطبيقات تدفق أصلية) |
| LM Studio | trustgraph-flow | كامل (متوافق مع OpenAI) |
| LlamaFile | trustgraph-flow | كامل (متوافق مع OpenAI) |
| vLLM | trustgraph-flow | كامل (متوافق مع OpenAI) |
| TGI | trustgraph-flow | قيد التحديد |
| Azure | trustgraph-flow | قيد التحديد |

#### نمط التنفيذ

بالنسبة لمزودي نماذج اللغة الكبيرة المتوافقين مع OpenAI (OpenAI، LM Studio، LlamaFile، vLLM):

```python
async def generate_content_stream(self, system, prompt, model, temperature):
    response = await self.client.chat.completions.create(
        model=model,
        messages=[
            {"role": "system", "content": system},
            {"role": "user", "content": prompt}
        ],
        temperature=temperature,
        stream=True
    )
    async for chunk in response:
        if chunk.choices[0].delta.content:
            yield LlmChunk(text=chunk.choices[0].delta.content)
```

--

### المرحلة الرابعة: واجهة برمجة التطبيقات (API) للوكيل

المرحلة الرابعة توسع البث ليشمل واجهة برمجة التطبيقات (API) للوكيل. هذا أكثر تعقيدًا لأن
واجهة برمجة التطبيقات (API) للوكيل هي بالفعل متعددة الرسائل بطبيعتها (فكرة ← إجراء ← ملاحظة
← تكرار ← إجابة نهائية).

#### مخطط الوكيل الحالي

```python
class AgentStep(Record):
    thought = String()
    action = String()
    arguments = Map(String())
    observation = String()
    user = String()

class AgentRequest(Record):
    question = String()
    state = String()
    group = Array(String())
    history = Array(AgentStep())
    user = String()

class AgentResponse(Record):
    answer = String()
    error = Error()
    thought = String()
    observation = String()
```

#### التغييرات المقترحة في مخطط الوكيل.

**طلب التغييرات:**

```python
class AgentRequest(Record):
    question = String()
    state = String()
    group = Array(String())
    history = Array(AgentStep())
    user = String()
    streaming = Boolean()  # NEW: Default false
```

**التغييرات في الاستجابة:**

ينتج الوكيل أنواعًا متعددة من المخرجات خلال دورة التفكير الخاصة به:
الأفكار (التفكير)
الإجراءات (استدعاءات الأدوات)
الملاحظات (نتائج الأدوات)
الإجابة (الاستجابة النهائية)
الأخطاء

نظرًا لأن `chunk_type` يحدد نوع المحتوى الذي يتم إرساله، يمكن دمج الحقول المنفصلة
`answer`، `error`، `thought`، و `observation` في
حقل واحد وهو `content`:

```python
class AgentResponse(Record):
    chunk_type = String()       # "thought", "action", "observation", "answer", "error"
    content = String()          # The actual content (interpretation depends on chunk_type)
    end_of_message = Boolean()  # Current thought/action/observation/answer is complete
    end_of_dialog = Boolean()   # Entire agent dialog is complete
```

**المعاني الدلالية للحقول:**

`chunk_type`: يشير إلى نوع المحتوى الموجود في حقل `content`.
  `"thought"`: تفكير/استنتاج الوكيل.
  `"action"`: الأداة/الإجراء المستخدم.
  `"observation"`: النتيجة من تنفيذ الأداة.
  `"answer"`: الإجابة النهائية لسؤال المستخدم.
  `"error"`: رسالة الخطأ.

`content`: المحتوى المتدفق الفعلي، والذي يتم تفسيره بناءً على `chunk_type`.

`end_of_message`: عندما `true`، يكون نوع الجزء الحالي مكتملًا.
  مثال: تم إرسال جميع الرموز الخاصة بالتفكير الحالي.
  يسمح للعملاء بمعرفة متى ينتقلون إلى المرحلة التالية.

`end_of_dialog`: عندما `true`، يكون التفاعل بأكمله مع الوكيل قد اكتمل.
  هذه هي الرسالة الأخيرة في التدفق.

#### سلوك التدفق الخاص بالوكيل

عندما `streaming=true`:

1. **تدفق الأفكار:**
   أجزاء متعددة مع `chunk_type="thought"`، `end_of_message=false`.
   الجزء الأخير من التفكير يحتوي على `end_of_message=true`.
2. **إشعار الإجراء:**
   جزء واحد مع `chunk_type="action"`، `end_of_message=true`.
3. **الملاحظة:**
   جزء (أجزاء) مع `chunk_type="observation"`، والجزء الأخير يحتوي على `end_of_message=true`.
4. **كرر** الخطوات من 1 إلى 3 أثناء قيام الوكيل بالتفكير.
5. **الإجابة النهائية:**
   `chunk_type="answer"` مع الإجابة النهائية في `content`.
   الجزء الأخير يحتوي على `end_of_message=true`، `end_of_dialog=true`.

**تسلسل التدفق النموذجي:**

```
{chunk_type: "thought", content: "I need to", end_of_message: false, end_of_dialog: false}
{chunk_type: "thought", content: " search for...", end_of_message: true, end_of_dialog: false}
{chunk_type: "action", content: "search", end_of_message: true, end_of_dialog: false}
{chunk_type: "observation", content: "Found: ...", end_of_message: true, end_of_dialog: false}
{chunk_type: "thought", content: "Based on this", end_of_message: false, end_of_dialog: false}
{chunk_type: "thought", content: " I can answer...", end_of_message: true, end_of_dialog: false}
{chunk_type: "answer", content: "The answer is...", end_of_message: true, end_of_dialog: true}
```

عندما `streaming=false`:
الحفاظ على السلوك الحالي
استجابة واحدة مع إجابة كاملة
`end_of_message=true`، `end_of_dialog=true`

#### بوابة وواجهة برمجة تطبيقات بايثون

البوابة: نقطة نهاية SSE/WebSocket جديدة لبث الوكيل
واجهة برمجة تطبيقات بايثون: طريقة مُولِّد غير متزامن جديدة `agent_stream()`

--

## اعتبارات الأمان

**لا توجد نقاط ضعف جديدة**: يستخدم البث نفس آليات المصادقة/التفويض
**تحديد المعدل**: تطبيق حدود معدل لكل رمز أو لكل جزء إذا لزم الأمر
**معالجة الاتصال**: إنهاء التدفقات بشكل صحيح عند قطع اتصال العميل
**إدارة المهلة الزمنية**: تحتاج طلبات البث إلى معالجة مناسبة للمهلة الزمنية

## اعتبارات الأداء

**الذاكرة**: يقلل البث من استخدام الذاكرة القصوى (بدون تخزين مؤقت للاستجابة الكاملة)
**زمن الوصول**: تم تقليل زمن الوصول إلى الرمز الأول بشكل كبير
**نفقات الاتصال**: تحتوي اتصالات SSE/WebSocket على نفقات صيانة الاتصال
**إنتاجية بولسار**: رسائل صغيرة متعددة مقابل رسالة كبيرة واحدة
  مقايضة

## استراتيجية الاختبار

### اختبارات الوحدة
تسلسل/إلغاء تسلسل المخطط مع الحقول الجديدة
التوافق مع الإصدارات السابقة (تستخدم الحقول المفقودة القيم الافتراضية)
منطق تجميع الأجزاء

### اختبارات التكامل
تطبيق كل مزود LLM لتنفيذ البث
نقاط نهاية البث لواجهة برمجة تطبيقات البوابة
طرق البث لعميل بايثون

### اختبارات شاملة
إخراج أداة سطر الأوامر (CLI) للبث
التدفق الكامل: العميل → البوابة → بولسار → LLM → العودة
أحمال عمل مختلطة (بث/غير بث)

### اختبارات التوافق مع الإصدارات السابقة
تعمل العملاء الحاليون دون تعديل
تتصرف طلبات عدم البث بشكل مماثل

## خطة الترحيل

### المرحلة الأولى: البنية التحتية
نشر تغييرات المخطط (متوافقة مع الإصدارات السابقة)
نشر تحديثات واجهة برمجة تطبيقات البوابة
نشر تحديثات واجهة برمجة تطبيقات بايثون
إصدار تحديثات أداة سطر الأوامر (CLI)

### المرحلة الثانية: VertexAI
نشر تطبيق VertexAI للبث.
التحقق من صحته باستخدام أحمال العمل التجريبية.

### المرحلة الثالثة: جميع المزودين.
نشر تحديثات المزودين بشكل تدريجي.
مراقبة المشكلات.

### المرحلة الرابعة: واجهة برمجة تطبيقات الوكيل.
نشر تغييرات مخطط الوكيل.
نشر تطبيق البث للوكيل.
تحديث الوثائق.

## الجدول الزمني.

| المرحلة | الوصف | التبعيات |
|-------|-------------|--------------|
| المرحلة الأولى | البنية التحتية | لا يوجد |
| المرحلة الثانية | نموذج VertexAI الأولي | المرحلة الأولى |
| المرحلة الثالثة | جميع المزودين | المرحلة الثانية |
| المرحلة الرابعة | واجهة برمجة تطبيقات الوكيل | المرحلة الثالثة |

## قرارات التصميم.

تمت معالجة الأسئلة التالية أثناء التحديد:

1. **عدد الرموز في البث**: عدد الرموز هو الفروق، وليس المجاميع التراكمية.
   يمكن للمستهلكين جمعها إذا لزم الأمر. يتطابق هذا مع كيفية قيام معظم المزودين بالإبلاغ
   عن الاستخدام ويبسط التنفيذ.

2. **معالجة الأخطاء في التدفقات**: في حالة حدوث خطأ، يتم ملء الحقل `error`
   ولا يلزم وجود أي حقول أخرى. الخطأ هو دائمًا آخر رسالة - لا يُسمح بإرسال أو استقبال رسائل لاحقة بعد ذلك.
   أو توقعها.
   خطأ. بالنسبة لتدفقات نماذج اللغة الكبيرة/التعليمات، `end_of_stream=true`. بالنسبة لتدفقات الوكلاء،
   `chunk_type="error"` مع `end_of_dialog=true`.

3. **استعادة الاستجابات الجزئية**: بروتوكول المراسلة (Pulsار) يتميز بالمرونة،
   لذلك لا توجد حاجة إلى إعادة محاولة الرسائل على مستوى الرسالة. إذا فقد العميل تتبع التدفق
   أو انقطع الاتصال، فيجب عليه إعادة محاولة الطلب بأكمله من البداية.

4. **خدمة الاستجابة السريعة المتدفقة**: تدعم البث فقط للنصوص (`text`).
   الاستجابات، وليس الاستجابات المنظمة (`object`). تعرف خدمة الاستجابة السريعة في
   البداية ما إذا كانت المخرجات ستكون بتنسيق JSON أو نص بناءً على قالب
   الاستعلام. إذا تم إجراء طلب بث لاستعلام ينتج عنه مخرجات بتنسيق JSON، فإن
   يجب أن يقوم الخدمة إما:
   بإرجاع كائن JSON كامل في استجابة واحدة باستخدام `end_of_stream=true`، أو
   برفض طلب البث مع وجود خطأ.

## الأسئلة المفتوحة

لا يوجد أسئلة في الوقت الحالي.

## المراجع

مخطط نموذج اللغة الكبير الحالي: `trustgraph-base/trustgraph/schema/services/llm.py`
مخطط المطالبة الحالي: `trustgraph-base/trustgraph/schema/services/prompt.py`
مخطط الوكيل الحالي: `trustgraph-base/trustgraph/schema/services/agent.py`
الخدمة الأساسية لنموذج اللغة الكبير: `trustgraph-base/trustgraph/base/llm_service.py`
مزود VertexAI: `trustgraph-vertexai/trustgraph/model/text_completion/vertexai/llm.py`
واجهة برمجة التطبيقات (API) للواجهة: `trustgraph-base/trustgraph/api/`
أدوات سطر الأوامر (CLI): `trustgraph-cli/trustgraph/cli/`
