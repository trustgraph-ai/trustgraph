# المواصفات التقنية لهيكل علم الأنطولوجيا

## نظرة عامة

تصف هذه المواصفات الهيكل والتنسيق الخاص بعلم الأنطولوجيا داخل نظام TrustGraph. توفر الأنطولوجيا نماذج معرفية رسمية تحدد الفئات والخصائص والعلاقات، مما يدعم قدرات الاستدلال والاستنتاج. يستخدم النظام تنسيقًا مستوحى من OWL، والذي يمثل على نطاق واسع مفاهيم OWL/RDFS، مع تحسينه لتلبية متطلبات TrustGraph.

**اتفاقية التسمية:** يستخدم هذا المشروع نمط "kebab-case" لجميع المعرفات (مفاتيح التكوين، ونقاط نهاية واجهة برمجة التطبيقات، وأسماء الوحدات، إلخ) بدلاً من نمط "snake_case".

## الأهداف

- **إدارة الفئات والخصائص:** تحديد فئات تشبه OWL مع خصائص ومجالات ونطاقات وقيود النوع.
- **دعم دلالي غني:** تمكين خصائص RDFS/OWL شاملة بما في ذلك التسميات ودعم لغات متعددة والقيود الرسمية.
- **دعم أنطولوجيا متعددة:** السماح لعدة أنطولوجيا بالوجود والتفاعل مع بعضها البعض.
- **التحقق والاستدلال:** ضمان توافق الأنطولوجيا مع معايير تشبه OWL مع التحقق من الاتساق ودعم الاستدلال.
- **التوافق مع المعايير:** دعم الاستيراد/التصدير بتنسيقات قياسية (Turtle، RDF/XML، OWL/XML) مع الحفاظ على التحسين الداخلي.

## الخلفية

يخزن نظام TrustGraph الأنطولوجيا كعناصر تكوين في نظام مرن من المفاتيح والقيم. على الرغم من أن التنسيق مستوحى من OWL (Web Ontology Language)، إلا أنه مُحسَّن لحالات الاستخدام المحددة لـ TrustGraph ولا يلتزم بشكل صارم بجميع مواصفات OWL.

تُمكّن الأنطولوجيا في TrustGraph:
- تعريف أنواع الكائنات الرسمية وخصائصها.
- تحديد نطاقات وقيود أنواع الخصائص.
- الاستدلال والاستنتاج المنطقي.
- علاقات معقدة وقيود التعددية.
- دعم لغات متعددة للترجمة.

## هيكل الأنطولوجيا

### تخزين التكوين

يتم تخزين الأنطولوجيا كعناصر تكوين بالنمط التالي:
- **النوع:** `ontology`
- **المفتاح:** معرف الأنطولوجيا الفريد (على سبيل المثال، `natural-world`، `domain-model`).
- **القيمة:** الأنطولوجيا بأكملها بتنسيق JSON.

### هيكل JSON

يتكون تنسيق JSON للأنطولوجيا من أربعة أقسام رئيسية:

#### 1. البيانات الوصفية (Metadata)

يحتوي على معلومات إدارية ووصفية حول الأنطولوجيا:

```json
{
  "metadata": {
    "name": "العالم الطبيعي",
    "description": "أنطولوجيا تغطي النظام الطبيعي",
    "version": "1.0.0",
    "created": "2025-09-20T12:07:37.068Z",
    "modified": "2025-09-20T12:12:20.725Z",
    "creator": "current-user",
    "namespace": "http://trustgraph.ai/ontologies/natural-world",
    "imports": ["http://www.w3.org/2002/07/owl#"]
  }
}
```

**الحقول:**
- `name`: الاسم القابل للقراءة البشرية للأنطولوجيا.
- `description`: وصف موجز لغرض الأنطولوجيا.
- `version`: رقم الإصدار الدلالي.
- `created`: طابع زمني ISO 8601 للإعداد.
- `modified`: طابع زمني ISO 8601 للتعديل الأخير.
- `creator`: معرف المستخدم/النظام الذي قام بإنشاء الأنطولوجيا.
- `namespace`: عنوان URI الأساسي لعناصر الأنطولوجيا.
- `imports`: مصفوفة من عناوين URI للأنطولوجيا المستوردة.

#### 2. الفئات (Classes)

تحدد أنواع الكائنات والعلاقات الهرمية بينها:

```json
{
  "classes": {
    "animal": {
      "uri": "http://trustgraph.ai/ontologies/natural-world#animal",
      "type": "owl:Class",
      "rdfs:label": [{"value": "حيوان", "lang": "en"}],
      "rdfs:comment": "حيوان",
      "rdfs:subClassOf": "lifeform",
      "owl:equivalentClass": ["cat", "dog"],
      "owl:disjointWith": ["cat"]
    },
    "lifeform": {
      "uri": "http://trustgraph.ai/ontologies/natural-world#lifeform",
      "type": "owl:Class",
      "rdfs:label": [{"value": "كائن حي", "lang": "en"}],
      "rdfs:comment": "كائن حي"
    },
    "cat": {
      "uri": "http://trustgraph.ai/ontologies/natural-world#cat",
      "type": "owl:Class",
      "rdfs:label": [{"value": "قط", "lang": "en"}],
      "rdfs:comment": "قط",
      "rdfs:subClassOf": "animal"
    },
    "dog": {
      "uri": "http://trustgraph.ai/ontologies/natural-world#dog",
      "type": "owl:Class",
      "rdfs:label": [{"value": "كلب", "lang": "en"}],
      "rdfs:comment": "كلب",
      "rdfs:subClassOf": "animal",
      "owl:disjointWith": ["cat"]
    }
  }
}
```

#### 3. الخصائص (Object Properties)

تحدد العلاقات بين الفئات:

```json
{
  "objectProperties": {}
}
```

#### 4. خصائص البيانات (Data Properties)

تحدد الخصائص التي تربط الكائنات ببيانات:

```json
{
  "datatypeProperties": {
    "number-of-legs": {
      "uri": "http://trustgraph.ai/ontologies/natural-world#number-of-legs",
      "type": "owl:DatatypeProperty",
      "rdfs:label": [{"value": "عدد الأرجل", "lang": "en"}],
      "rdfs:comment": "عدد أرجل الحيوان",
      "rdfs:range": "xsd:nonNegativeInteger",
      "rdfs:domain": "animal"
    }
  }
}
```

## قواعد التحقق

### التحقق الهيكلي

1. **اتساق URI:** يجب أن تتبع جميع عناوين URI النمط `{namespace}#{identifier}`.
2. **هرمية الفئات:** لا توجد علاقات إرثية دائرية في `rdfs:subClassOf`.
3. **نطاقات وقيود أنواع الخصائص:** يجب أن تشير إلى فئات موجودة أو أنواع XSD صالحة.
4. **فئات متباينة:** لا يمكن أن تكون فئة فرعية من فئة أخرى.
5. **خصائص عكسية:** يجب أن تكون ثنائية الاتجاه إذا تم تحديدها.

### التحقق الدلالي

1. **معرفات فريدة:** يجب أن تكون معرّفات الفئات والخصائص فريدة داخل أنطولوجيا واحدة.
2. **علامات اللغة:** يجب أن تتبع تنسيق علامة اللغة BCP 47.
3. **قيود التعددية:** يجب أن يكون `minCardinality` ≤ `maxCardinality` عند تحديد كليهما.
4. **خصائص وظيفية:** لا يمكن أن يكون لها `maxCardinality` > 1.

## دعم تنسيق الاستيراد/التصدير

في حين أن التنسيق الداخلي هو JSON، يدعم النظام التحويل إلى/من تنسيقات الأنطولوجيا القياسية:

- **Turtle (.ttl):** تسلسل RDF مضغوط.
- **RDF/XML (.rdf، .owl):** تنسيق W3C قياسي.
- **OWL/XML (.owx):** تنسيق XML خاص بـ OWL.
- **JSON-LD (.jsonld):** JSON للبيانات المرتبطة.

## المراجع

- [OWL 2 Web Ontology Language](https://www.w3.org/TR/owl2-overview/)
- [RDF Schema 1.1](https://www.w3.org/TR/rdf-schema/)
- [XML Schema Datatypes](https://www.w3.org/TR/xmlschema-2/)
- [BCP 47 Language Tags](https://tools.ietf.org/html/bcp47)