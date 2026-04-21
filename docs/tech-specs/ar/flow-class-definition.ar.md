---
layout: default
title: "مواصفات تعريف مخطط التدفق"
parent: "Arabic (Beta)"
---

<<<<<<< HEAD
# مواصفات تعريف مخطط التدفق

> **Beta Translation:** This document was translated via Machine Learning and as such may not be 100% accurate. All non-English languages are currently classified as Beta.
=======
# تعريف مواصفات مخطط التدفق
>>>>>>> 82edf2d (New md files from RunPod)

## نظرة عامة

يحدد مخطط التدفق قالبًا كاملاً لنمط تدفق البيانات في نظام TrustGraph. عند تنفيذه، فإنه ينشئ شبكة مترابطة من المعالجات التي تتعامل مع استيعاب البيانات ومعالجتها وتخزينها والاستعلام عنها كنظام موحد.

## الهيكل

يتكون تعريف مخطط التدفق من خمسة أقسام رئيسية:

### 1. قسم الفئة
يحدد معالجات الخدمات المشتركة التي يتم إنشاؤها مرة واحدة لكل مخطط تدفق. تتعامل هذه المعالجات مع الطلبات من جميع مثيلات التدفق لهذه الفئة.

```json
"class": {
  "service-name:{class}": {
    "request": "queue-pattern:{class}",
    "response": "queue-pattern:{class}",
    "settings": {
      "setting-name": "fixed-value",
      "parameterized-setting": "{parameter-name}"
    }
  }
}
```

**الخصائص:**
مشتركة عبر جميع مثيلات التدفق من نفس الفئة.
عادةً ما تكون خدمات مكلفة أو غير تعتمد على الحالة (نماذج لغوية كبيرة، نماذج تضمين).
استخدم متغير القالب `{class}` لتسمية قائمة الانتظار.
يمكن أن تكون الإعدادات قيمًا ثابتة أو مُعَلمة باستخدام صيغة `{parameter-name}`.
أمثلة: `embeddings:{class}`، `text-completion:{class}`، `graph-rag:{class}`.

### 2. قسم التدفق
يحدد المعالجات الخاصة بالتدفق والتي يتم إنشاؤها لكل مثيل تدفق فردي. يحصل كل تدفق على مجموعة معزولة خاصة به من هذه المعالجات.

```json
"flow": {
  "processor-name:{id}": {
    "input": "queue-pattern:{id}",
    "output": "queue-pattern:{id}",
    "settings": {
      "setting-name": "fixed-value",
      "parameterized-setting": "{parameter-name}"
    }
  }
}
```

**الخصائص:**
نسخة فريدة لكل تدفق.
التعامل مع البيانات والحالة الخاصة بالتدفق.
استخدام متغير القالب `{id}` لأسماء قوائم الانتظار.
يمكن أن تكون الإعدادات قيمًا ثابتة أو مُعَلمة باستخدام صيغة `{parameter-name}`.
أمثلة: `chunker:{id}`، `pdf-decoder:{id}`، `kg-extract-relationships:{id}`.

### القسم 3: الواجهات
يحدد نقاط الدخول وعقود التفاعل للتدفق. تشكل هذه الواجهة البرمجية (API) للأنظمة الخارجية وتواصل المكونات الداخلية.

يمكن أن تتخذ الواجهات شكلين:

**نمط الإرسال والإهمال** (قائمة انتظار واحدة):
```json
"interfaces": {
  "document-load": "persistent://tg/flow/document-load:{id}",
  "triples-store": "persistent://tg/flow/triples-store:{id}"
}
```

**نمط الطلب/الاستجابة** (كائن يحتوي على حقول الطلب/الاستجابة):
```json
"interfaces": {
  "embeddings": {
    "request": "non-persistent://tg/request/embeddings:{class}",
    "response": "non-persistent://tg/response/embeddings:{class}"
  }
}
```

**أنواع الواجهات:**
**نقاط الدخول:** الأماكن التي تقوم الأنظمة الخارجية بإدخال البيانات (`document-load`، `agent`)
**واجهات الخدمات:** أنماط الطلب/الاستجابة للخدمات (`embeddings`، `text-completion`)
**واجهات البيانات:** نقاط اتصال تدفق البيانات من نوع "أرسل وانتهى" (`triples-store`، `entity-contexts-load`)

### القسم الرابع: معلمات
يربط أسماء المعلمات الخاصة بالتدفق بتعريفات المعلمات المخزنة مركزيًا:

```json
"parameters": {
  "model": "llm-model",
  "temp": "temperature",
  "chunk": "chunk-size"
}
```

**الخصائص:**
المفاتيح هي أسماء المعلمات المستخدمة في إعدادات المعالج (مثل: `{model}`)
القيم تشير إلى تعريفات المعلمات المخزنة في schema/config
يتيح إعادة استخدام تعريفات المعلمات الشائعة عبر التدفقات.
يقلل من تكرار مخططات المعلمات.

### 5. البيانات الوصفية
معلومات إضافية حول مخطط التدفق:

```json
"description": "Human-readable description",
"tags": ["capability-1", "capability-2"]
```

## متغيرات القالب

### متغيرات النظام

#### {id}
يتم استبدالها بمعرّف مثيل التدفق الفريد.
<<<<<<< HEAD
تقوم بإنشاء موارد معزولة لكل تدفق.
=======
تنشئ موارد معزولة لكل تدفق.
>>>>>>> 82edf2d (New md files from RunPod)
مثال: `flow-123`، `customer-A-flow`

#### {class}
يتم استبدالها باسم مخطط التدفق.
<<<<<<< HEAD
تقوم بإنشاء موارد مشتركة عبر التدفقات من نفس الفئة.
=======
تنشئ موارد مشتركة عبر التدفقات من نفس الفئة.
>>>>>>> 82edf2d (New md files from RunPod)
مثال: `standard-rag`، `enterprise-rag`

### متغيرات المعلمات

#### {parameter-name}
معلمات مخصصة يتم تعريفها في وقت بدء التدفق.
تتطابق أسماء المعلمات مع المفاتيح الموجودة في قسم `parameters` الخاص بالتدفق.
تُستخدم في إعدادات المعالج لتخصيص السلوك.
أمثلة: `{model}`، `{temp}`، `{chunk}`
يتم استبدالها بالقيم المقدمة عند بدء التدفق.
يتم التحقق من صحتها مقابل تعريفات المعلمات المخزنة مركزيًا.

## إعدادات المعالج

توفر الإعدادات قيم التكوين للمعالجات في وقت الإنشاء. يمكن أن تكون:

### إعدادات ثابتة
قيم مباشرة لا تتغير:
```json
"settings": {
  "model": "gemma3:12b",
  "temperature": 0.7,
  "max_retries": 3
}
```

### الإعدادات ذات المعلمات
القيم التي تستخدم معلمات يتم توفيرها عند بدء تشغيل التدفق:
```json
"settings": {
  "model": "{model}",
  "temperature": "{temp}",
  "endpoint": "https://{region}.api.example.com"
}
```

تتوافق أسماء المعلمات في الإعدادات مع المفاتيح في قسم `parameters` الخاص بالتدفق.

### أمثلة للإعدادات

**معالج نماذج اللغة الكبيرة مع المعلمات:**
```json
// In parameters section:
"parameters": {
  "model": "llm-model",
  "temp": "temperature",
  "tokens": "max-tokens",
  "key": "openai-api-key"
}

// In processor definition:
"text-completion:{class}": {
  "request": "non-persistent://tg/request/text-completion:{class}",
  "response": "non-persistent://tg/response/text-completion:{class}",
  "settings": {
    "model": "{model}",
    "temperature": "{temp}",
    "max_tokens": "{tokens}",
    "api_key": "{key}"
  }
}
```

**تقسيم النص بإعدادات ثابتة ومعلمات:**
```json
// In parameters section:
"parameters": {
  "chunk": "chunk-size"
}

// In processor definition:
"chunker:{id}": {
  "input": "persistent://tg/flow/chunk:{id}",
  "output": "persistent://tg/flow/chunk-load:{id}",
  "settings": {
    "chunk_size": "{chunk}",
    "chunk_overlap": 100,
    "encoding": "utf-8"
  }
}
```

<<<<<<< HEAD
## أنماط قائمة الانتظار (بالمسر)

تستخدم مخططات التدفق Apache Pulsar للرسائل. تتبع أسماء قوائم الانتظار تنسيق بالمسر:
=======
## أنماط قائمة الانتظار (بالمار)

تستخدم مخططات التدفق Apache Pulsar للرسائل. تتبع أسماء قوائم الانتظار تنسيق بالمار:
>>>>>>> 82edf2d (New md files from RunPod)
```
<persistence>://<tenant>/<namespace>/<topic>
```

### المكونات:
**الاستمرارية**: `persistent` أو `non-persistent` (وضع استمرارية Pulsar)
**المستأجر**: `tg` لتعريفات مخطط التدفق المقدمة من TrustGraph
**مساحة الاسم**: تشير إلى نمط الرسائل
  `flow`: خدمات الإرسال والاستقبال
  `request`: الجزء الطلب من خدمات الطلب/الاستجابة
  `response`: الجزء الاستجابة من خدمات الطلب/الاستجابة
**الموضوع**: اسم قائمة الانتظار/الموضوع المحدد مع متغيرات القالب

### قوائم الانتظار الدائمة
النمط: `persistent://tg/flow/<topic>:{id}`
تستخدم لخدمات الإرسال والاستقبال وتدفق البيانات المتينة
تظل البيانات في تخزين Pulsar عبر عمليات إعادة التشغيل
مثال: `persistent://tg/flow/chunk-load:{id}`

### قوائم الانتظار غير الدائمة
النمط: `non-persistent://tg/request/<topic>:{class}` أو `non-persistent://tg/response/<topic>:{class}`
تستخدم لأنماط الرسائل الطلب/الاستجابة
مؤقتة، ولا يتم حفظها على القرص بواسطة Pulsar
زمن انتقال أقل، ومناسبة للاتصالات على غرار RPC
مثال: `non-persistent://tg/request/embeddings:{class}`

## بنية تدفق البيانات

ينشئ مخطط التدفق تدفق بيانات موحد حيث:

1. **مسار معالجة المستندات**: يبدأ من الاستيعاب ويمر بالتحويل إلى التخزين
2. **خدمات الاستعلام**: معالجات مدمجة تستعلم عن نفس مخازن البيانات والخدمات
3. **الخدمات المشتركة**: معالجات مركزية يمكن لجميع التدفقات استخدامها
4. **كتابة التخزين**: تحفظ البيانات المعالجة في المخازن المناسبة

<<<<<<< HEAD
تعمل جميع المعالجات (سواء `{id}` و `{class}`) معًا كرسوم بيانية لتدفق بيانات متماسك، وليس كأنظمة منفصلة.
=======
تعمل جميع المعالجات (سواء `{id}` و `{class}`) معًا كرسوم بيانية لتدفق البيانات المتكاملة، وليس كأنظمة منفصلة.
>>>>>>> 82edf2d (New md files from RunPod)

## مثال على إنشاء التدفق

المعطيات:
معرف مثيل التدفق: `customer-A-flow`
مخطط التدفق: `standard-rag`
تعيينات معلمات التدفق:
  `"model": "llm-model"`
  `"temp": "temperature"`
  `"chunk": "chunk-size"`
المعلمات المقدمة من المستخدم:
  `model`: `gpt-4`
  `temp`: `0.5`
  `chunk`: `512`

<<<<<<< HEAD
التوسعات القالبية:
=======
توسعات القالب:
>>>>>>> 82edf2d (New md files from RunPod)
`persistent://tg/flow/chunk-load:{id}` → `persistent://tg/flow/chunk-load:customer-A-flow`
`non-persistent://tg/request/embeddings:{class}` → `non-persistent://tg/request/embeddings:standard-rag`
`"model": "{model}"` → `"model": "gpt-4"`
`"temperature": "{temp}"` → `"temperature": "0.5"`
`"chunk_size": "{chunk}"` → `"chunk_size": "512"`

هذا ينشئ:
مسار معالجة مستندات معزول لـ `customer-A-flow`
خدمة تضمين مشتركة لجميع تدفقات `standard-rag`
تدفق بيانات كامل من استيعاب المستندات إلى الاستعلام
المعالجات مُكوَّنة بقيم المعلمات المقدمة

## المزايا

1. **كفاءة الموارد**: يتم مشاركة الخدمات المكلفة عبر التدفقات
2. **عزل التدفق**: يحتوي كل تدفق على مسار معالجة بيانات خاص به
3. **قابلية التوسع**: يمكن إنشاء مثيلات متعددة من نفس القالب
4. **النمطية**: فصل واضح بين المكونات المشتركة والمكونات الخاصة بالتدفق
5. **بنية موحدة**: الاستعلام والمعالجة جزء من تدفق البيانات نفسه
