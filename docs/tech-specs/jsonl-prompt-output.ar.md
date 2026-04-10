# المواصفات الفنية للإخراج بتنسيق JSONL

## نظرة عامة

تصف هذه المواصفات تطبيق تنسيق JSONL (JSON Lines) للإخراج
في TrustGraph. يتيح JSONL استخراجًا مقاومًا للتقطيع للبيانات المنظمة من
استجابات نماذج اللغة الكبيرة (LLM)، مما يعالج المشكلات الهامة المتعلقة
بتلف مخرجات JSON array عندما تصل استجابات نماذج اللغة الكبيرة إلى حدود
الرموز المميزة للإخراج.

يدعم هذا التطبيق حالات الاستخدام التالية:

1. **الاستخراج المقاوم للتقطيع**: استخراج نتائج جزئية صالحة حتى عندما
   يتم اقتطاع إخراج نموذج اللغة الكبيرة في منتصف الاستجابة.
2. **الاستخراج على نطاق واسع**: التعامل مع استخراج العديد من العناصر دون
   خطر الفشل التام بسبب حدود الرموز المميزة.
3. **الاستخراج بأنواع متعددة**: دعم استخراج أنواع متعددة من الكيانات
   (التعريفات، والعلاقات، والكيانات، والسمات) في طلب واحد.
4. **الإخراج المتوافق مع التدفق**: تمكين المعالجة المستقبلية التدريجية/المتزايدة
   لنتائج الاستخراج.

## الأهداف

**التوافق مع الإصدارات السابقة**: تظل الطلبات الحالية التي تستخدم `response-type: "text"` و
  `response-type: "json"` تعمل دون تعديل.
**مقاومة التقطيع**: تؤدي مخرجات نماذج اللغة الكبيرة الجزئية إلى نتائج
  جزئية صالحة بدلاً من الفشل التام.
**التحقق من المخطط**: دعم التحقق من مخطط JSON للكائنات الفردية.
**الاتحادات المميزة**: دعم المخرجات ذات الأنواع المختلطة باستخدام حقل `type`
  مميز.
**تغييرات API الحد الأدنى**: توسيع تكوين الطلب الحالي بنوع استجابة جديد
  ومفتاح مخطط.

## الخلفية

### البنية الحالية

يدعم خدمة الطلبات نوعين من الاستجابات:

1. `response-type: "text"` - استجابة نصية خام يتم إرجاعها كما هي.
2. `response-type: "json"` - JSON يتم تحليله من الاستجابة، ويتم التحقق منه مقابل
   `schema` اختياري.

التنفيذ الحالي في `trustgraph-flow/trustgraph/template/prompt_manager.py`:

```python
class Prompt:
    def __init__(self, template, response_type = "text", terms=None, schema=None):
        self.template = template
        self.response_type = response_type
        self.terms = terms
        self.schema = schema
```

### القيود الحالية

عندما تطلب مطالبات الاستخراج إخراجًا بتنسيق مصفوفات JSON (`[{...}, {...}, ...]`):

**تلف بسبب الاقتطاع**: إذا وصلت LLM إلى حدود رموز الإخراج أثناء المصفوفة، يصبح
  الرد بأكمله JSON غير صالح ولا يمكن تحليله.
**التحليل الكل أو لا شيء**: يجب استقبال الإخراج الكامل قبل التحليل.
**لا توجد نتائج جزئية**: يؤدي الرد المقتطع إلى عدم وجود بيانات قابلة للاستخدام.
**غير موثوق به للاستخراج الكبير**: كلما زاد عدد العناصر المستخرجة، زاد خطر الفشل.

تعالج هذه المواصفات هذه القيود من خلال تقديم تنسيق JSONL لمطالبات
الاستخراج، حيث يكون كل عنصر مستخرج كائن JSON كامل في سطر منفصل.


## التصميم الفني

### إضافة نوع استجابة جديد

أضف نوع استجابة جديد `"jsonl"` بالإضافة إلى الأنواع الموجودة `"text"` و `"json"`.

#### تغييرات التكوين

**قيمة نوع الاستجابة الجديدة:**

```
"response-type": "jsonl"
```

**تفسير المخطط:**

يتم استخدام المفتاح `"schema"` الموجود لكل من نوعي الاستجابة `"json"` و `"jsonl"`.
يعتمد التفسير على نوع الاستجابة:

`"json"`: يصف المخطط الاستجابة بأكملها (عادةً ما يكون مصفوفة أو كائن).
`"jsonl"`: يصف المخطط كل سطر/كائن فردي.

```json
{
  "response-type": "jsonl",
  "schema": {
    "type": "object",
    "properties": {
      "entity": { "type": "string" },
      "definition": { "type": "string" }
    },
    "required": ["entity", "definition"]
  }
}
```

هذا يمنع التغييرات في أدوات تكوين المطالبات والمحررات.

### مواصفات تنسيق JSONL

#### الاستخراج البسيط

بالنسبة للمطالبات التي تستخرج نوعًا واحدًا من الكائنات (التعريفات، العلاقات،
الموضوعات، الصفوف)، يكون الإخراج عبارة عن كائن JSON واحد لكل سطر بدون أي غلاف:

**تنسيق إخراج المطالبة:**
```
{"entity": "photosynthesis", "definition": "Process by which plants convert sunlight"}
{"entity": "chlorophyll", "definition": "Green pigment in plants"}
{"entity": "mitochondria", "definition": "Powerhouse of the cell"}
```

**مقارنة مع تنسيق مصفوفة JSON السابق:**
```json
[
  {"entity": "photosynthesis", "definition": "Process by which plants convert sunlight"},
  {"entity": "chlorophyll", "definition": "Green pigment in plants"},
  {"entity": "mitochondria", "definition": "Powerhouse of the cell"}
]
```

إذا قام نموذج اللغة الكبير بقطع النص بعد السطر الثاني، فإن تنسيق مصفوفة JSON ينتج عنه JSON غير صالح،
بينما ينتج عن JSONL كائنان صالحان.

#### استخراج أنواع مختلطة (الاتحادات المميزة)

بالنسبة إلى التعليمات التي تستخرج أنواعًا متعددة من الكائنات (مثل التعريفات والأمثلة).
العلاقات، أو الكيانات، والعلاقات، والخصائص)، استخدم `"type"`
الحقل كعامل تمييز:

**تنسيق إخراج التعليمات:**
```
{"type": "definition", "entity": "DNA", "definition": "Molecule carrying genetic instructions"}
{"type": "relationship", "subject": "DNA", "predicate": "located_in", "object": "cell nucleus", "object-entity": true}
{"type": "definition", "entity": "RNA", "definition": "Molecule that carries genetic information"}
{"type": "relationship", "subject": "RNA", "predicate": "transcribed_from", "object": "DNA", "object-entity": true}
```

**مخطط للاتحادات المميّزة يستخدم `oneOf`:**
```json
{
  "response-type": "jsonl",
  "schema": {
    "oneOf": [
      {
        "type": "object",
        "properties": {
          "type": { "const": "definition" },
          "entity": { "type": "string" },
          "definition": { "type": "string" }
        },
        "required": ["type", "entity", "definition"]
      },
      {
        "type": "object",
        "properties": {
          "type": { "const": "relationship" },
          "subject": { "type": "string" },
          "predicate": { "type": "string" },
          "object": { "type": "string" },
          "object-entity": { "type": "boolean" }
        },
        "required": ["type", "subject", "predicate", "object", "object-entity"]
      }
    ]
  }
}
```

#### استخراج علم المفاهيم

لاستخراج علم المفاهيم بناءً على الكيانات والعلاقات والخصائص:

**تنسيق إخراج التعليمات البرمجية:**
```
{"type": "entity", "entity": "Cornish pasty", "entity_type": "fo/Recipe"}
{"type": "entity", "entity": "beef", "entity_type": "fo/Food"}
{"type": "relationship", "subject": "Cornish pasty", "subject_type": "fo/Recipe", "relation": "fo/has_ingredient", "object": "beef", "object_type": "fo/Food"}
{"type": "attribute", "entity": "Cornish pasty", "entity_type": "fo/Recipe", "attribute": "fo/serves", "value": "4 people"}
```

### تفاصيل التنفيذ

#### فئة المطالبة (Prompt Class)

لا تتطلب الفئة الحالية `Prompt` أي تغييرات. يتم إعادة استخدام الحقل `schema`
لـ JSONL، ويتم تحديد تفسيره بواسطة `response_type`:

```python
class Prompt:
    def __init__(self, template, response_type="text", terms=None, schema=None):
        self.template = template
        self.response_type = response_type
        self.terms = terms
        self.schema = schema  # Interpretation depends on response_type
```

#### PromptManager.load_config

لا توجد تغييرات مطلوبة - عملية تحميل التكوين الحالية تتعامل بالفعل مع
`schema`.

#### تحليل JSONL

إضافة طريقة تحليل جديدة لنتائج JSONL:

```python
def parse_jsonl(self, text):
    """
    Parse JSONL response, returning list of valid objects.

    Invalid lines (malformed JSON, empty lines) are skipped with warnings.
    This provides truncation resilience - partial output yields partial results.
    """
    results = []

    for line_num, line in enumerate(text.strip().split('\n'), 1):
        line = line.strip()

        # Skip empty lines
        if not line:
            continue

        # Skip markdown code fence markers if present
        if line.startswith('```'):
            continue

        try:
            obj = json.loads(line)
            results.append(obj)
        except json.JSONDecodeError as e:
            # Log warning but continue - this provides truncation resilience
            logger.warning(f"JSONL parse error on line {line_num}: {e}")

    return results
```

#### تغييرات في PromptManager.invoke

قم بتوسيع طريقة "invoke" للتعامل مع نوع الاستجابة الجديد:

```python
async def invoke(self, id, input, llm):
    logger.debug("Invoking prompt template...")

    terms = self.terms | self.prompts[id].terms | input
    resp_type = self.prompts[id].response_type

    prompt = {
        "system": self.system_template.render(terms),
        "prompt": self.render(id, input)
    }

    resp = await llm(**prompt)

    if resp_type == "text":
        return resp

    if resp_type == "json":
        try:
            obj = self.parse_json(resp)
        except:
            logger.error(f"JSON parse failed: {resp}")
            raise RuntimeError("JSON parse fail")

        if self.prompts[id].schema:
            try:
                validate(instance=obj, schema=self.prompts[id].schema)
                logger.debug("Schema validation successful")
            except Exception as e:
                raise RuntimeError(f"Schema validation fail: {e}")

        return obj

    if resp_type == "jsonl":
        objects = self.parse_jsonl(resp)

        if not objects:
            logger.warning("JSONL parse returned no valid objects")
            return []

        # Validate each object against schema if provided
        if self.prompts[id].schema:
            validated = []
            for i, obj in enumerate(objects):
                try:
                    validate(instance=obj, schema=self.prompts[id].schema)
                    validated.append(obj)
                except Exception as e:
                    logger.warning(f"Object {i} failed schema validation: {e}")
            return validated

        return objects

    raise RuntimeError(f"Response type {resp_type} not known")
```

### المطالبات المتأثرة

يجب ترحيل المطالبات التالية إلى تنسيق JSONL:

| معرف المطالبة | الوصف | حقل النوع |
|-----------|-------------|------------|
| `extract-definitions` | استخراج الكيانات/التعريفات | لا (نوع واحد) |
| `extract-relationships` | استخراج العلاقات | لا (نوع واحد) |
| `extract-topics` | استخراج الموضوعات/التعريفات | لا (نوع واحد) |
| `extract-rows` | استخراج الصفوف المنظمة | لا (نوع واحد) |
| `agent-kg-extract` | استخراج التعريفات والعلاقات المجمعة | نعم: `"definition"`، `"relationship"` |
| `extract-with-ontologies` / `ontology-extract` | الاستخراج القائم على علم الوجود | نعم: `"entity"`، `"relationship"`، `"attribute"` |

### تغييرات واجهة برمجة التطبيقات (API)

#### من وجهة نظر العميل

تحليل JSONL شفاف لمستخدمي واجهة برمجة التطبيقات (API) لخدمة المطالبات. يتم التحليل
من جانب الخادم في خدمة المطالبات، ويتم إرجاع الاستجابة عبر الحقل القياسي
`PromptResponse.object` كمصفوفة JSON مسلسلة.

عندما يستدعي العملاء خدمة المطالبات (عبر `PromptClient.prompt()` أو ما شابه):

**`response-type: "json"`** مع مخطط المصفوفة → يتلقى العميل كائن Python `list`
**`response-type: "jsonl"`** → يتلقى العميل كائن Python `list`

من وجهة نظر العميل، فإن كلا الخيارين يُرجِعان هياكل بيانات متطابقة.
الفرق يكمن بالكامل في كيفية تحليل مخرجات نموذج اللغة الكبير (LLM) من جهة الخادم:

تنسيق مصفوفة JSON: استدعاء واحد لـ `json.loads()`؛ يفشل تمامًا إذا تم اقتطاعه.
تنسيق JSONL: تحليل سطريًا؛ ينتج عنه نتائج جزئية إذا تم اقتطاعه.

هذا يعني أن التعليمات البرمجية للعميل الحالية التي تتوقع قائمة من مطالبات الاستخراج
لا تتطلب أي تغييرات عند ترحيل المطالبات من تنسيق JSON إلى تنسيق JSONL.

#### القيمة المُرجَعة من الخادم

بالنسبة لـ `response-type: "jsonl"`، تُرجع الطريقة `PromptManager.invoke()`
`list[dict]` تحتوي على جميع الكائنات التي تم تحليلها والتحقق من صحتها بنجاح. يتم بعد ذلك تسلسل هذه
القائمة إلى JSON لحقل `PromptResponse.object`.

#### معالجة الأخطاء

نتائج فارغة: تُرجع قائمة فارغة `[]` مع سجل تحذير.
فشل جزئي في التحليل: تُرجع قائمة بالكائنات التي تم تحليلها بنجاح مع
  سجلات تحذير للأخطاء.
فشل كامل في التحليل: تُرجع قائمة فارغة `[]` مع سجلات تحذير.

هذا يختلف عن `response-type: "json"` الذي يثير `RuntimeError` في حالة
فشل التحليل. السلوك المتسامح لـ JSONL مقصود لتوفير مقاومة للاقتطاع.


### مثال على التكوين

مثال كامل لتكوين المطالبة:

```json
{
  "prompt": "Extract all entities and their definitions from the following text. Output one JSON object per line.\n\nText:\n{{text}}\n\nOutput format per line:\n{\"entity\": \"<name>\", \"definition\": \"<definition>\"}",
  "response-type": "jsonl",
  "schema": {
    "type": "object",
    "properties": {
      "entity": {
        "type": "string",
        "description": "The entity name"
      },
      "definition": {
        "type": "string",
        "description": "A clear definition of the entity"
      }
    },
    "required": ["entity", "definition"]
  }
}
```

## اعتبارات الأمان

**التحقق من صحة الإدخال**: يستخدم تحليل JSON معيار `json.loads()` وهو آمن
  ضد هجمات الحقن.
**التحقق من صحة المخطط**: يستخدم `jsonschema.validate()` لفرض المخطط.
**لا توجد مساحة هجومية جديدة**: تحليل JSONL أكثر أمانًا بشكل صارم من تحليل مصفوفة JSON
  بسبب المعالجة سطرًا بسطر.

## اعتبارات الأداء

**الذاكرة**: يستخدم التحليل سطرًا بسطر ذاكرة قصوى أقل من تحميل مصفوفات JSON كاملة.
  **زمن الوصول**: أداء التحليل مماثل لأداء تحليل مصفوفة JSON.
**التحقق من الصحة**: يتم تشغيل التحقق من صحة المخطط لكل كائن، مما يضيف حملًا إضافيًا ولكنه
يمكّن النتائج الجزئية في حالة فشل التحقق من الصحة.
  
## استراتيجية الاختبار

### اختبارات الوحدة


تحليل JSONL مع إدخال صالح.
تحليل JSONL مع أسطر فارغة.
تحليل JSONL مع أقسام التعليمات البرمجية بتنسيق Markdown.
تحليل JSONL مع سطر نهائي مقطوع.
تحليل JSONL مع أسطر JSON غير صالحة متداخلة.
التحقق من صحة المخطط مع اتحاد `oneOf` المميّز.
التوافق مع الإصدارات السابقة: تظل المطالبات `"text"` و `"json"` الحالية دون تغيير.

### اختبارات التكامل

استخراج شامل مع مطالبات JSONL.
الاستخراج مع محاكاة القطع (استجابة محدودة بشكل مصطنع).
الاستخراج المختلط الأنواع مع مميز النوع.
استخراج علم الوجود مع الأنواع الثلاثة.

### اختبارات جودة الاستخراج.

مقارنة نتائج الاستخراج: تنسيق JSONL مقابل تنسيق مصفوفة JSON.
التحقق من قدرة تحمل التقصير: ينتج عن تنسيق JSONL نتائج جزئية في الحالات التي يفشل فيها تنسيق JSON.

## خطة الترحيل

### المرحلة الأولى: التنفيذ

1. تنفيذ الطريقة `parse_jsonl()` في `PromptManager`.
2. توسيع `invoke()` للتعامل مع `response-type: "jsonl"`.
3. إضافة اختبارات الوحدة.

### المرحلة الثانية: ترحيل المطالبات

1. تحديث المطالبة `extract-definitions` والإعدادات.
2. تحديث المطالبة `extract-relationships` والإعدادات.
3. تحديث المطالبة `extract-topics` والإعدادات.
4. تحديث المطالبة `extract-rows` والإعدادات.
5. تحديث المطالبة `agent-kg-extract` والإعدادات.
6. تحديث المطالبة `extract-with-ontologies` والإعدادات.

### المرحلة الثالثة: التحديثات اللاحقة

1. تحديث أي كود يستهلك نتائج الاستخراج للتعامل مع نوع الإرجاع القائمة.
2. تحديث الكود الذي يصنف الاستخراجات ذات الأنواع المختلطة باستخدام الحقل `type`.
3. تحديث الاختبارات التي تؤكد على تنسيق إخراج الاستخراج.

## أسئلة مفتوحة

لا يوجد حاليًا.

## المراجع

التنفيذ الحالي: `trustgraph-flow/trustgraph/template/prompt_manager.py`.
مواصفات JSON Lines: https://jsonlines.org/.
مخطط JSON `oneOf`: https://json-schema.org/understanding-json-schema/reference/combining.html#oneof.
المواصفة ذات الصلة: Streaming LLM Responses (`docs/tech-specs/streaming-llm-responses.md`).
