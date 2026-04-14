---
layout: default
title: "استخراج المعرفة من علم الوجود - المرحلة الثانية، إعادة هيكلة"
parent: "Arabic (Beta)"
---

# استخراج المعرفة من علم الوجود - المرحلة الثانية، إعادة هيكلة

> **Beta Translation:** This document was translated via Machine Learning and as such may not be 100% accurate. All non-English languages are currently classified as Beta.

**الحالة**: مسودة
**المؤلف**: جلسة التحليل بتاريخ 2025-12-03
**مرتبط بـ**: `ontology.md`، `ontorag.md`

## نظرة عامة

يحدد هذا المستند التناقضات الموجودة في نظام استخراج المعرفة الحالي القائم على علم الوجود ويقترح إعادة هيكلة لتحسين أداء نماذج اللغة الكبيرة وتقليل فقدان المعلومات.

## التنفيذ الحالي

### كيف يعمل الآن

1. **تحميل علم الوجود** (`ontology_loader.py`)
   يقوم بتحميل ملف JSON الخاص بعلم الوجود باستخدام مفاتيح مثل `"fo/Recipe"`، `"fo/Food"`، `"fo/produces"`
   تتضمن معرفات الفئات بادئة مساحة الاسم في المفتاح نفسه.
   مثال من `food.ontology`:
     ```json
     "classes": {
       "fo/Recipe": {
         "uri": "http://purl.org/ontology/fo/Recipe",
         "rdfs:comment": "A Recipe is a combination..."
       }
     }
     ```

2. **بناء المطالبة** (`extract.py:299-307`، `ontology-prompt.md`)
   يتلقى النموذج `classes`، `object_properties`، `datatype_properties` (قواميس).
   يتكرر النموذج: `{% for class_id, class_def in classes.items() %}`
   يرى نموذج اللغة الكبيرة (LLM): `**fo/Recipe**: A Recipe is a combination...`
   يوضح تنسيق الإخراج النموذجي:
     ```json
     {"subject": "recipe:cornish-pasty", "predicate": "rdf:type", "object": "Recipe"}
     {"subject": "recipe:cornish-pasty", "predicate": "has_ingredient", "object": "ingredient:flour"}
     ```

3. **تحليل الاستجابة** (`extract.py:382-428`)
   يتوقع مصفوفة JSON: `[{"subject": "...", "predicate": "...", "object": "..."}]`
   يتحقق من الصحة مقابل مجموعة فرعية من علم الوجود.
   يوسع الـ URIs عبر `expand_uri()` (extract.py:473-521)

4. **توسيع الـ URI** (`extract.py:473-521`)
   يتحقق مما إذا كانت القيمة موجودة في قاموس `ontology_subset.classes`.
   إذا تم العثور عليها، يتم استخراج الـ URI من تعريف الفئة.
   إذا لم يتم العثور عليها، يتم إنشاء الـ URI: `f"https://trustgraph.ai/ontology/{ontology_id}#{value}"`

### مثال تدفق البيانات

**JSON لعلم الوجود → المحمل → المطالبة:**
```
"fo/Recipe" → classes["fo/Recipe"] → LLM sees "**fo/Recipe**"
```

**نموذج اللغة الكبير → المحلل → الإخراج:**
```
"Recipe" → not in classes["fo/Recipe"] → constructs URI → LOSES original URI
"fo/Recipe" → found in classes → uses original URI → PRESERVES URI
```

## المشكلات التي تم تحديدها

### 1. **أمثلة غير متسقة في التعليمات**

**المشكلة**: قالب التعليمات يعرض معرفات الفئات مع بادئات (`fo/Recipe`) ولكن الإخراج النموذجي يستخدم أسماء فئات بدون بادئات (`Recipe`).

**الموقع**: `ontology-prompt.md:5-52`

```markdown
## Ontology Classes:
- **fo/Recipe**: A Recipe is...

## Example Output:
{"subject": "recipe:cornish-pasty", "predicate": "rdf:type", "object": "Recipe"}
```

**التأثير:** يتلقى نموذج اللغة الكبير إشارات متضاربة حول التنسيق الذي يجب استخدامه.

### 2. **فقدان المعلومات في توسيع عنوان URL**

**المشكلة:** عندما يقوم نموذج اللغة الكبير بإرجاع أسماء الفئات غير المسبوقة بعد المثال، لا يمكن لـ `expand_uri()` العثور عليها في قاموس الأونطولوجيا ويقوم بإنشاء عناوين URI احتياطية، مما يؤدي إلى فقدان عناوين URI الأصلية الصحيحة.

**الموقع:** `extract.py:494-500`

```python
if value in ontology_subset.classes:  # Looks for "Recipe"
    class_def = ontology_subset.classes[value]  # But key is "fo/Recipe"
    if isinstance(class_def, dict) and 'uri' in class_def:
        return class_def['uri']  # Never reached!
return f"https://trustgraph.ai/ontology/{ontology_id}#{value}"  # Fallback
```

**التأثير:**
عنوان URI الأصلي: `http://purl.org/ontology/fo/Recipe`
عنوان URI المُنشأ: `https://trustgraph.ai/ontology/food#Recipe`
فقدان المعنى الدلالي، مما يعيق التوافقية.

### 3. **تنسيق مثيل الكيان الغامض**

**المشكلة:** لا توجد إرشادات واضحة حول تنسيق عنوان URI لمثيل الكيان.

**أمثلة في التعليمات:**
`"recipe:cornish-pasty"` (بادئة تشبه مساحة الاسم)
`"ingredient:flour"` (بادئة مختلفة)

**السلوك الفعلي** (extract.py:517-520):
```python
# Treat as entity instance - construct unique URI
normalized = value.replace(" ", "-").lower()
return f"https://trustgraph.ai/{ontology_id}/{normalized}"
```

**التأثير**: يجب على نموذج اللغة الكبير تخمين اتفاقية البادئات بدون أي سياق دلالي.

### 4. **لا توجد إرشادات حول بادئات النطاقات**.

**المشكلة**: يحتوي ملف JSON الخاص بالدلالة على تعريفات النطاقات (السطر 10-25 في food.ontology):
```json
"namespaces": {
  "fo": "http://purl.org/ontology/fo/",
  "rdf": "http://www.w3.org/1999/02/22-rdf-syntax-ns#",
  ...
}
```

ولكن هذه العناصر لا يتم إرسالها أبدًا إلى نموذج اللغة الكبير (LLM). نموذج اللغة الكبير لا يعرف:
ما الذي تعنيه كلمة "fo"
ما هو البادئة التي يجب استخدامها للكائنات
أي مساحة اسم تنطبق على أي عناصر

### 5. **التسميات غير المستخدمة في المطالبة**

**المشكلة:** كل فئة لديها `rdfs:label` حقول (مثل `{"value": "Recipe", "lang": "en-gb"}`)، ولكن قالب المطالبة لا يستخدمها.

**الحالي:** يعرض فقط `class_id` و `comment`
```jinja
- **{{class_id}}**{% if class_def.comment %}: {{class_def.comment}}{% endif %}
```

**متاح ولكنه غير مستخدم:**
```python
"rdfs:label": [{"value": "Recipe", "lang": "en-gb"}]
```

**التأثير**: يمكن أن يوفر أسماءً قابلة للقراءة من قبل الإنسان جنبًا إلى جنب مع المعرفات التقنية.

## الحلول المقترحة

### الخيار أ: التوحيد إلى معرفات غير مُسبقة

**النهج**: إزالة البادئات من معرفات الفئات قبل عرضها لنظام LLM.

**التغييرات**:
1. تعديل `build_extraction_variables()` لتحويل المفاتيح:
   ```python
   classes_for_prompt = {
       k.split('/')[-1]: v  # "fo/Recipe" → "Recipe"
       for k, v in ontology_subset.classes.items()
   }
   ```

2. تحديث مثال المطالبة ليتطابق (يستخدم بالفعل أسماء غير مسبوقة).

3. تعديل `expand_uri()` للتعامل مع كلا التنسيقين:
   ```python
   # Try exact match first
   if value in ontology_subset.classes:
       return ontology_subset.classes[value]['uri']

   # Try with prefix
   for prefix in ['fo/', 'rdf:', 'rdfs:']:
       prefixed = f"{prefix}{value}"
       if prefixed in ontology_subset.classes:
           return ontology_subset.classes[prefixed]['uri']
   ```

**المزايا:**
أنظف وأكثر قابلية للقراءة من قبل البشر.
تتوافق مع أمثلة المطالبات الحالية.
تعمل نماذج اللغات الكبيرة بشكل أفضل مع الرموز الأبسط.

**العيوب:**
تعارض أسماء الفئات إذا كانت هناك العديد من الأنطولوجيات لها نفس اسم الفئة.
تفقد معلومات مساحة الاسم.
تتطلب منطقًا احتياطيًا للبحث.

### الخيار ب: استخدام المعرفات الكاملة المسبوقة باستمرار

**الطريقة:** تحديث الأمثلة لاستخدام المعرفات المسبوقة التي تتطابق مع ما هو موضح في قائمة الفئات.

**التغييرات:**
1. تحديث مثال المطالبة (ontology-prompt.md:46-52):
   ```json
   [
     {"subject": "recipe:cornish-pasty", "predicate": "rdf:type", "object": "fo/Recipe"},
     {"subject": "recipe:cornish-pasty", "predicate": "rdfs:label", "object": "Cornish Pasty"},
     {"subject": "recipe:cornish-pasty", "predicate": "fo/produces", "object": "food:cornish-pasty"},
     {"subject": "food:cornish-pasty", "predicate": "rdf:type", "object": "fo/Food"}
   ]
   ```

2. أضف شرحًا لمساحة الاسم إلى التعليمات:
   ```markdown
   ## Namespace Prefixes:
   - **fo/**: Food Ontology (http://purl.org/ontology/fo/)
   - **rdf:**: RDF Schema
   - **rdfs:**: RDF Schema

   Use these prefixes exactly as shown when referencing classes and properties.
   ```

3. احتفظ بـ `expand_uri()` كما هو (يعمل بشكل صحيح عند العثور على تطابقات).

**المزايا:**
اتساق الإدخال والإخراج.
عدم وجود فقدان للمعلومات.
يحافظ على دلالات مساحة الاسم.
يعمل مع العديد من الأنطولوجيات.

**العيوب:**
رموز أكثر تفصيلاً لنظام LLM.
يتطلب من نظام LLM تتبع البادئات.

### الخيار ج: هجين - عرض كل من التسمية والمعرف

**النهج:** قم بتحسين المطالبة لعرض كل من التسميات المقروءة من قبل الإنسان والمعرفات التقنية.

**التغييرات:**
1. تحديث قالب المطالبة:
   ```jinja
   {% for class_id, class_def in classes.items() %}
   - **{{class_id}}** (label: "{{class_def.labels[0].value if class_def.labels else class_id}}"){% if class_def.comment %}: {{class_def.comment}}{% endif %}
   {% endfor %}
   ```

   الناتج النموذجي:
   ```markdown
   - **fo/Recipe** (label: "Recipe"): A Recipe is a combination...
   ```

2. تعليمات التحديث:
   ```markdown
   When referencing classes:
   - Use the full prefixed ID (e.g., "fo/Recipe") in JSON output
   - The label (e.g., "Recipe") is for human understanding only
   ```

**المزايا:**
الأوضح لنماذج اللغة الكبيرة (LLM)
يحافظ على جميع المعلومات
يوضح بشكل صريح ما يجب استخدامه

**العيوب:**
طلب أطول
قالب أكثر تعقيدًا

## النهج المطبق

**تنسيق مبسط للعلاقة بين الكيانات والخصائص** - يحل محل التنسيق القديم القائم على الثلاثيات تمامًا.

تم اختيار النهج الجديد لأنه:

1. **لا يوجد فقدان للمعلومات**: يتم الحفاظ على عناوين URI الأصلية بشكل صحيح.
2. **منطق أبسط**: لا توجد حاجة إلى أي تحويل، تعمل عمليات البحث المباشرة في القواميس.
3. **أمان مساحة الاسم**: يتعامل مع العديد من الأنطولوجيات دون حدوث تعارضات.
4. **الصحة الدلالية**: يحافظ على الدلالات الخاصة بـ RDF/OWL.

## التنفيذ مكتمل

### ما تم بناؤه:

1. **قالب طلب جديد** (`prompts/ontology-extract-v2.txt`)
   ✅ أقسام واضحة: أنواع الكيانات، العلاقات، الخصائص.
   ✅ مثال باستخدام معرفات النوع الكاملة (`fo/Recipe`، `fo/has_ingredient`).
   ✅ تعليمات لاستخدام المعرفات الدقيقة من المخطط.
   ✅ تنسيق JSON جديد مع مصفوفات الكيانات/العلاقات/الخصائص.

2. **تسوية الكيانات** (`entity_normalizer.py`)
   ✅ `normalize_entity_name()` - يحول الأسماء إلى تنسيق آمن لـ URI.
   ✅ `normalize_type_identifier()` - يتعامل مع الشرطات المائلة في الأنواع (`fo/Recipe` → `fo-recipe`).
   ✅ `build_entity_uri()` - ينشئ عناوين URI فريدة باستخدام زوج (الاسم، النوع).
   ✅ `EntityRegistry` - يتتبع الكيانات لتجنب التكرار.

3. **محلل JSON** (`simplified_parser.py`)
   ✅ يحلل التنسيق الجديد: `{entities: [...], relationships: [...], attributes: [...]}`.
   ✅ يدعم أسماء الحقول بتنسيق kebab-case و snake_case.
   ✅ يُرجع فئات بيانات منظمة.
   ✅ معالجة أخطاء سلسة مع التسجيل.

4. **محول الثلاثيات** (`triple_converter.py`)
   ✅ `convert_entity()` - ينشئ ثلاثيات النوع + التسمية تلقائيًا.
   ✅ `convert_relationship()` - يربط عناوين URI للكيانات عبر الخصائص.
   ✅ `convert_attribute()` - يضيف القيم الحرفية.
   ✅ يبحث عن عناوين URI الكاملة من تعريفات الأنطولوجيا.

5. **المعالج الرئيسي المحدث** (`extract.py`)
   ✅ تمت إزالة كود الاستخراج القديم القائم على الثلاثيات.
   ✅ تمت إضافة `extract_with_simplified_format()`.
   ✅ يستخدم الآن التنسيق المبسط الجديد فقط.
   ✅ يستدعي الطلب بمعرف `extract-with-ontologies-v2`.

## حالات الاختبار

### الاختبار 1: الحفاظ على عنوان URI
```python
# Given ontology class
classes = {"fo/Recipe": {"uri": "http://purl.org/ontology/fo/Recipe", ...}}

# When LLM returns
llm_output = {"subject": "x", "predicate": "rdf:type", "object": "fo/Recipe"}

# Then expanded URI should be
assert expanded == "http://purl.org/ontology/fo/Recipe"
# Not: "https://trustgraph.ai/ontology/food#Recipe"
```

### الاختبار 2: التصادم متعدد الأنطولوجيا
```python
# Given two ontologies
ont1 = {"fo/Recipe": {...}}
ont2 = {"cooking/Recipe": {...}}

# LLM should use full prefix to disambiguate
llm_output = {"object": "fo/Recipe"}  # Not just "Recipe"
```

### الاختبار رقم 3: تنسيق مثيل الكيان
```python
# Given prompt with food ontology
# LLM should create instances like
{"subject": "recipe:cornish-pasty"}  # Namespace-style
{"subject": "food:beef"}              # Consistent prefix
```

## أسئلة مفتوحة

1. **هل يجب أن تستخدم حالات الكيانات بادئات النطاق؟**
   الحالي: `"recipe:cornish-pasty"` (عشوائي)
   بديل: استخدام بادئة الأونطولوجيا `"fo:cornish-pasty"`؟
   بديل: بدون بادئة، التوسع في URI `"cornish-pasty"` → URI كامل؟

2. **كيفية التعامل مع النطاق/المدى في المطالبة؟**
   يعرض حاليًا: `(Recipe → Food)`
   هل يجب أن يكون: `(fo/Recipe → fo/Food)`؟

3. **هل يجب علينا التحقق من صحة قيود النطاق/المدى؟**
   ملاحظة TODO في extract.py:470
   سيكتشف المزيد من الأخطاء ولكنه أكثر تعقيدًا

4. **ماذا عن الخصائص العكسية والتكافؤات؟**
   تحتوي الأونطولوجيا على `owl:inverseOf`، `owl:equivalentClass`
   لا يتم استخدامه حاليًا في الاستخراج
   هل يجب أن يتم استخدامه؟

## مقاييس النجاح

✅ عدم وجود فقدان لمعلومات URI (100٪ للحفاظ على URIs الأصلية)
✅ تنسيق إخراج LLM يطابق تنسيق الإدخال
✅ لا توجد أمثلة غامضة في المطالبة
✅ اجتياز الاختبارات مع العديد من الأونطولوجيات
✅ تحسين جودة الاستخراج (يتم قياسه بالنسبة المئوية للثلاثيات الصالحة)

## نهج بديل: تنسيق استخراج مبسط

### الفلسفة

بدلاً من مطالبة LLM بفهم دلالات RDF/OWL، اطلب منه فعل ما هو جيد فيه: **العثور على الكيانات والعلاقات في النص**.

دع الكود يتعامل مع بناء URI، وتحويل RDF، والشؤون الرسمية للويب الدلالي.

### مثال: تصنيف الكيانات

**النص المدخل:**
```
Cornish pasty is a traditional British pastry filled with meat and vegetables.
```

**مخطط علم الوجود (يُعرض على نموذج اللغة الكبير):**
```markdown
## Entity Types:
- Recipe: A recipe is a combination of ingredients and a method
- Food: A food is something that can be eaten
- Ingredient: An ingredient combines a quantity and a food
```

**ماذا يُرجع نموذج اللغة الكبير (JSON بسيط):**
```json
{
  "entities": [
    {
      "entity": "Cornish pasty",
      "type": "Recipe"
    }
  ]
}
```

**ما الذي ينتجه الكود (ثلاثيات RDF):**
```python
# 1. Normalize entity name + type to ID (type prevents collisions)
entity_id = "recipe-cornish-pasty"  # normalize("Cornish pasty", "Recipe")
entity_uri = "https://trustgraph.ai/food/recipe-cornish-pasty"

# Note: Same name, different type = different URI
# "Cornish pasty" (Recipe) → recipe-cornish-pasty
# "Cornish pasty" (Food) → food-cornish-pasty

# 2. Generate triples
triples = [
    # Type triple
    Triple(
        s=Value(value=entity_uri, is_uri=True),
        p=Value(value="http://www.w3.org/1999/02/22-rdf-syntax-ns#type", is_uri=True),
        o=Value(value="http://purl.org/ontology/fo/Recipe", is_uri=True)
    ),
    # Label triple (automatic)
    Triple(
        s=Value(value=entity_uri, is_uri=True),
        p=Value(value="http://www.w3.org/2000/01/rdf-schema#label", is_uri=True),
        o=Value(value="Cornish pasty", is_uri=False)
    )
]
```

### المزايا

1. **نموذج اللغة الكبير (LLM) لا يحتاج إلى:**
   فهم بناء جمل URI
   اختراع بادئات المعرفات (`recipe:`، `ingredient:`)
   معرفة عن `rdf:type` أو `rdfs:label`
   إنشاء معرفات الويب الدلالي

2. **نموذج اللغة الكبير (LLM) يحتاج فقط إلى:**
   العثور على الكيانات في النص
   ربطها بفئات علم الوجود
   استخراج العلاقات والسمات

3. **الكود يتعامل مع:**
   تطبيع وبناء URI
   توليد ثلاثيات RDF
   تعيين تسميات تلقائيًا
   إدارة مساحات الأسماء

### لماذا هذا أفضل

**موجه أبسط** = تقليل الارتباك = تقليل الأخطاء
**معرفات متسقة** = الكود يتحكم في قواعد التطبيع
**تسميات مُولدة تلقائيًا** = لا توجد ثلاثيات rdfs:label مفقودة
**يركز نموذج اللغة الكبير على الاستخراج** = وهو ما يتقنه بالفعل

### مثال: علاقات الكيانات

**النص المدخل:**
```
Cornish pasty is a traditional British pastry filled with beef and potatoes.
```

**مخطط علم الوجود (معروض للنموذج اللغوي الكبير):**
```markdown
## Entity Types:
- Recipe: A recipe is a combination of ingredients and a method
- Food: A food is something that can be eaten
- Ingredient: An ingredient combines a quantity and a food

## Relationships:
- has_ingredient: Relates a recipe to an ingredient it uses (Recipe → Ingredient)
- food: Relates an ingredient to the food that is required (Ingredient → Food)
```

**ماذا يُرجع نموذج اللغة الكبير (JSON بسيط):**
```json
{
  "entities": [
    {
      "entity": "Cornish pasty",
      "type": "Recipe"
    },
    {
      "entity": "beef",
      "type": "Food"
    },
    {
      "entity": "potatoes",
      "type": "Food"
    }
  ],
  "relationships": [
    {
      "subject": "Cornish pasty",
      "subject-type": "Recipe",
      "relation": "has_ingredient",
      "object": "beef",
      "object-type": "Food"
    },
    {
      "subject": "Cornish pasty",
      "subject-type": "Recipe",
      "relation": "has_ingredient",
      "object": "potatoes",
      "object-type": "Food"
    }
  ]
}
```

**ما الذي ينتجه الكود (ثلاثيات RDF):**
```python
# Normalize entity names to URIs
cornish_pasty_uri = "https://trustgraph.ai/food/cornish-pasty"
beef_uri = "https://trustgraph.ai/food/beef"
potatoes_uri = "https://trustgraph.ai/food/potatoes"

# Look up relation URI from ontology
has_ingredient_uri = "http://purl.org/ontology/fo/ingredients"  # from fo/has_ingredient

triples = [
    # Entity type triples (as before)
    Triple(s=cornish_pasty_uri, p=rdf_type, o="http://purl.org/ontology/fo/Recipe"),
    Triple(s=cornish_pasty_uri, p=rdfs_label, o="Cornish pasty"),

    Triple(s=beef_uri, p=rdf_type, o="http://purl.org/ontology/fo/Food"),
    Triple(s=beef_uri, p=rdfs_label, o="beef"),

    Triple(s=potatoes_uri, p=rdf_type, o="http://purl.org/ontology/fo/Food"),
    Triple(s=potatoes_uri, p=rdfs_label, o="potatoes"),

    # Relationship triples
    Triple(
        s=Value(value=cornish_pasty_uri, is_uri=True),
        p=Value(value=has_ingredient_uri, is_uri=True),
        o=Value(value=beef_uri, is_uri=True)
    ),
    Triple(
        s=Value(value=cornish_pasty_uri, is_uri=True),
        p=Value(value=has_ingredient_uri, is_uri=True),
        o=Value(value=potatoes_uri, is_uri=True)
    )
]
```

**النقاط الرئيسية:**
تقوم نماذج اللغة الكبيرة بإرجاع أسماء الكيانات باللغة الطبيعية: `"Cornish pasty"`، `"beef"`، `"potatoes"`
تتضمن نماذج اللغة الكبيرة أنواعًا لتوضيح المعنى: `subject-type`، `object-type`
تستخدم نماذج اللغة الكبيرة اسم العلاقة من المخطط: `"has_ingredient"`
تستخدم الشيفرة معرّفات متسقة باستخدام (الاسم، النوع): `("Cornish pasty", "Recipe")` → `recipe-cornish-pasty`
تبحث الشيفرة عن عنوان URI للعلاقة من علم الوجود: `fo/has_ingredient` → عنوان URI الكامل
دائمًا ما تحصل المجموعة نفسها (الاسم، النوع) على نفس عنوان URI (إزالة التكرار)

### مثال: التمييز بين أسماء الكيانات

**المشكلة:** يمكن أن يشير نفس الاسم إلى أنواع مختلفة من الكيانات.

**حالة واقعية:**
```
"Cornish pasty" can be:
- A Recipe (instructions for making it)
- A Food (the dish itself)
```

**كيف يتم التعامل معها:**

يقوم نموذج اللغة الكبير بإرجاع كليهما ككيانات منفصلة:
```json
{
  "entities": [
    {"entity": "Cornish pasty", "type": "Recipe"},
    {"entity": "Cornish pasty", "type": "Food"}
  ],
  "relationships": [
    {
      "subject": "Cornish pasty",
      "subject-type": "Recipe",
      "relation": "produces",
      "object": "Cornish pasty",
      "object-type": "Food"
    }
  ]
}
```

**حل التعليمات البرمجية:**
```python
# Different types → different URIs
recipe_uri = normalize("Cornish pasty", "Recipe")
# → "https://trustgraph.ai/food/recipe-cornish-pasty"

food_uri = normalize("Cornish pasty", "Food")
# → "https://trustgraph.ai/food/food-cornish-pasty"

# Relationship connects them correctly
triple = Triple(
    s=recipe_uri,  # The Recipe
    p="http://purl.org/ontology/fo/produces",
    o=food_uri     # The Food
)
```

**لماذا هذا يعمل:**
يتم تضمين النوع في جميع المراجع (الكيانات، والعلاقات، والسمات).
يستخدم الكود `(name, type)` كـ "مجموعة" (tuple) كمفتاح للبحث.
لا يوجد غموض، ولا توجد تعارضات.

### مثال: سمات الكيان

**النص المدخل:**
```
This Cornish pasty recipe serves 4-6 people and takes 45 minutes to prepare.
```

**مخطط علم الوجود (يُعرض على نموذج اللغة الكبير):**
```markdown
## Entity Types:
- Recipe: A recipe is a combination of ingredients and a method

## Attributes:
- serves: Indicates what the recipe is intended to serve (Recipe → text)
- preparation_time: Time needed to prepare the recipe (Recipe → text)
```

**ماذا يُرجع نموذج اللغة الكبير (JSON بسيط):**
```json
{
  "entities": [
    {
      "entity": "Cornish pasty recipe",
      "type": "Recipe"
    }
  ],
  "attributes": [
    {
      "entity": "Cornish pasty recipe",
      "entity-type": "Recipe",
      "attribute": "serves",
      "value": "4-6 people"
    },
    {
      "entity": "Cornish pasty recipe",
      "entity-type": "Recipe",
      "attribute": "preparation_time",
      "value": "45 minutes"
    }
  ]
}
```

**ما الذي ينتجه الكود (ثلاثيات RDF):**
```python
# Normalize entity name to URI
recipe_uri = "https://trustgraph.ai/food/cornish-pasty-recipe"

# Look up attribute URIs from ontology
serves_uri = "http://purl.org/ontology/fo/serves"  # from fo/serves
prep_time_uri = "http://purl.org/ontology/fo/preparation_time"  # from fo/preparation_time

triples = [
    # Entity type triple
    Triple(
        s=Value(value=recipe_uri, is_uri=True),
        p=Value(value=rdf_type, is_uri=True),
        o=Value(value="http://purl.org/ontology/fo/Recipe", is_uri=True)
    ),

    # Label triple (automatic)
    Triple(
        s=Value(value=recipe_uri, is_uri=True),
        p=Value(value=rdfs_label, is_uri=True),
        o=Value(value="Cornish pasty recipe", is_uri=False)
    ),

    # Attribute triples (objects are literals, not URIs)
    Triple(
        s=Value(value=recipe_uri, is_uri=True),
        p=Value(value=serves_uri, is_uri=True),
        o=Value(value="4-6 people", is_uri=False)  # Literal value!
    ),
    Triple(
        s=Value(value=recipe_uri, is_uri=True),
        p=Value(value=prep_time_uri, is_uri=True),
        o=Value(value="45 minutes", is_uri=False)  # Literal value!
    )
]
```

**النقاط الرئيسية:**
يستخرج نموذج اللغة الكبير القيم الحرفية: `"4-6 people"`، `"45 minutes"`
يتضمن نموذج اللغة الكبير نوع الكيان لتوضيح المعنى: `entity-type`
يستخدم نموذج اللغة الكبير اسم الخاصية من المخطط: `"serves"`، `"preparation_time"`
يبحث الكود عن عنوان URI للخاصية من خصائص نوع البيانات في علم الوجود.
**الكائن هو قيمة حرفية** (`is_uri=False`)، وليس مرجع URI.
تظل القيم كنص طبيعي، ولا تحتاج إلى تطبيع.

**الفرق عن العلاقات:**
العلاقات: كل من الموضوع والمفعول به هما كيانات (URIs).
الخصائص: الموضوع هو كيان (URI)، والمفعول به هو قيمة حرفية (نص/رقم).

### مثال كامل: الكيانات + العلاقات + الخصائص

**النص المدخل:**
```
Cornish pasty is a savory pastry filled with beef and potatoes.
This recipe serves 4 people.
```

**ماذا يُرجع نموذج اللغة الكبير:**
```json
{
  "entities": [
    {
      "entity": "Cornish pasty",
      "type": "Recipe"
    },
    {
      "entity": "beef",
      "type": "Food"
    },
    {
      "entity": "potatoes",
      "type": "Food"
    }
  ],
  "relationships": [
    {
      "subject": "Cornish pasty",
      "subject-type": "Recipe",
      "relation": "has_ingredient",
      "object": "beef",
      "object-type": "Food"
    },
    {
      "subject": "Cornish pasty",
      "subject-type": "Recipe",
      "relation": "has_ingredient",
      "object": "potatoes",
      "object-type": "Food"
    }
  ],
  "attributes": [
    {
      "entity": "Cornish pasty",
      "entity-type": "Recipe",
      "attribute": "serves",
      "value": "4 people"
    }
  ]
}
```

**النتيجة:** تم توليد 11 ثلاثية RDF:
3 ثلاثيات لنوع الكيان (rdf:type)
3 ثلاثيات لملصق الكيان (rdfs:label) - تلقائي
2 ثلاثية للعلاقة (has_ingredient)
1 ثلاثية للخاصية (serves)

كل ذلك من خلال استخلاص بسيط وسهل من اللغة الطبيعية بواسطة نموذج اللغة الكبير!

## المراجع

التنفيذ الحالي: `trustgraph-flow/trustgraph/extract/kg/ontology/extract.py`
قالب التعليمات: `ontology-prompt.md`
حالات الاختبار: `tests/unit/test_extract/test_ontology/`
مثال على علم الوجود: `e2e/test-data/food.ontology`
