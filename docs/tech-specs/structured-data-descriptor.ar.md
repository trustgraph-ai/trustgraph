# مواصفات محدد البيانات المنظمة

## نظرة عامة

محدد البيانات المنظمة هو لغة تكوين تعتمد على JSON تصف كيفية تحليل وتحويل واستيراد البيانات المنظمة إلى TrustGraph. يوفر نهجًا تصريحيًا لاستيعاب البيانات، مما يدعم تنسيقات إدخال متعددة وقنوات تحويل معقدة دون الحاجة إلى تعليمات برمجية مخصصة.

## المفاهيم الأساسية

### 1. تعريف التنسيق
يصف نوع ملف الإدخال وخيارات التحليل. يحدد أي محلل لاستخدامه وكيفية تفسير البيانات المصدر.

### 2. تعيينات الحقول
يربط مسارات المصدر بحقول الهدف مع التحويلات. يحدد كيفية تدفق البيانات من مصادر الإدخال إلى حقول مخطط الإخراج.

### 3. سلسلة التحويل
سلسلة من تحويلات البيانات التي يمكن تطبيقها على قيم الحقول، بما في ذلك:
تنظيف البيانات (التقليم، التسوية)
تحويل التنسيق (تحليل التاريخ، تحويل النوع)
العمليات الحسابية (العمليات الحسابية، معالجة السلاسل)
عمليات البحث (جداول مرجعية، استبدالات)

### 4. قواعد التحقق من الصحة
عمليات فحص جودة البيانات المطبقة لضمان سلامة البيانات:
التحقق من النوع
عمليات التحقق من النطاق
مطابقة الأنماط (regex)
التحقق من صحة الحقول المطلوبة
منطق التحقق المخصص

### 5. الإعدادات العامة
التكوين الذي ينطبق على عملية الاستيراد بأكملها:
جداول البحث لإثراء البيانات
المتغيرات والثوابت العامة
مواصفات تنسيق الإخراج
سياسات معالجة الأخطاء

## استراتيجية التنفيذ

يتبع تطبيق المستورد هذا المسار:

1. **تحليل التكوين** - تحميل والتحقق من صحة الوصف JSON
2. **تهيئة المحلل** - تحميل المحلل المناسب (CSV، XML، JSON، إلخ) بناءً على `format.type`
3. **تطبيق المعالجة المسبقة** - تنفيذ المرشحات والتحويلات العامة
4. **معالجة السجلات** - لكل سجل إدخال:
   استخراج البيانات باستخدام مسارات المصدر (JSONPath، XPath، أسماء الأعمدة)
   تطبيق التحويلات الخاصة بالحقل بالتسلسل
   التحقق من صحة النتائج مقابل القواعد المحددة
   تطبيق القيم الافتراضية للبيانات المفقودة
5. **تطبيق المعالجة اللاحقة** - تنفيذ إزالة التكرار، التجميع، إلخ.
6. **إنشاء الإخراج** - إنتاج البيانات بالتنسيق المستهدف المحدد

## دعم تعبيرات المسار

تستخدم تنسيقات الإدخال المختلفة لغات تعبيرات المسار المناسبة:

**CSV**: أسماء الأعمدة أو الفهارس (`"column_name"` أو `"[2]"`)
**JSON**: بناء جملة JSONPath (`"$.user.profile.email"`)
**XML**: تعبيرات XPath (`"//product[@id='123']/price"`)
**العرض الثابت**: أسماء الحقول من تعريفات الحقول

## المزايا

**قاعدة تعليمات برمجية واحدة** - يقوم مستورد واحد بمعالجة تنسيقات إدخال متعددة
**سهل الاستخدام** - يمكن للمستخدمين غير التقنيين إنشاء تكوينات
**قابلة لإعادة الاستخدام** - يمكن مشاركة التكوينات وتنسيق الإصدارات
**مرنة** - تحويلات معقدة بدون ترميز مخصص
**قوية** - تحقق مدمج ومعالجة شاملة للأخطاء
**قابلة للصيانة** - يوفر النهج التصريحي تقليل تعقيد التنفيذ

## مواصفات اللغة

يستخدم محدد البيانات المنظمة تنسيق تكوين JSON مع البنية العامة التالية:

```json
{
  "version": "1.0",
  "metadata": {
    "name": "Configuration Name",
    "description": "Description of what this config does",
    "author": "Author Name",
    "created": "2024-01-01T00:00:00Z"
  },
  "format": { ... },
  "globals": { ... },
  "preprocessing": [ ... ],
  "mappings": [ ... ],
  "postprocessing": [ ... ],
  "output": { ... }
}
```

### تعريف التنسيق

يصف تنسيق البيانات المدخلة وخيارات التحليل:

```json
{
  "format": {
    "type": "csv|json|xml|fixed-width|excel|parquet",
    "encoding": "utf-8",
    "options": {
      // Format-specific options
    }
  }
}
```

### خيارات تنسيق CSV
```json
{
  "format": {
    "type": "csv",
    "options": {
      "delimiter": ",",
      "quote_char": "\"",
      "escape_char": "\\",
      "skip_rows": 1,
      "has_header": true,
      "null_values": ["", "NULL", "null", "N/A"]
    }
  }
}
```

#### خيارات تنسيق JSON
```json
{
  "format": {
    "type": "json",
    "options": {
      "root_path": "$.data",
      "array_mode": "records|single",
      "flatten": false
    }
  }
}
```

#### خيارات تنسيق XML
```json
{
  "format": {
    "type": "xml",
    "options": {
      "root_element": "//records/record",
      "namespaces": {
        "ns": "http://example.com/namespace"
      }
    }
  }
}
```

### الإعدادات العامة

تحديد الجداول المرجعية والمتغيرات والتكوين العام:

```json
{
  "globals": {
    "variables": {
      "current_date": "2024-01-01",
      "batch_id": "BATCH_001",
      "default_confidence": 0.8
    },
    "lookup_tables": {
      "country_codes": {
        "US": "United States",
        "UK": "United Kingdom",
        "CA": "Canada"
      },
      "status_mapping": {
        "1": "active",
        "0": "inactive"
      }
    },
    "constants": {
      "source_system": "legacy_crm",
      "import_type": "full"
    }
  }
}
```

### تعيينات الحقول

حدد كيفية تعيين البيانات المصدر إلى الحقول المستهدفة مع التحويلات:

```json
{
  "mappings": [
    {
      "target_field": "person_name",
      "source": "$.name",
      "transforms": [
        {"type": "trim"},
        {"type": "title_case"},
        {"type": "required"}
      ],
      "validation": [
        {"type": "min_length", "value": 2},
        {"type": "max_length", "value": 100},
        {"type": "pattern", "value": "^[A-Za-z\\s]+$"}
      ]
    },
    {
      "target_field": "age",
      "source": "$.age",
      "transforms": [
        {"type": "to_int"},
        {"type": "default", "value": 0}
      ],
      "validation": [
        {"type": "range", "min": 0, "max": 150}
      ]
    },
    {
      "target_field": "country",
      "source": "$.country_code",
      "transforms": [
        {"type": "lookup", "table": "country_codes"},
        {"type": "default", "value": "Unknown"}
      ]
    }
  ]
}
```

### أنواع التحويل

الوظائف المتاحة للتحويل:

#### تحويلات السلاسل النصية
```json
{"type": "trim"},
{"type": "upper"},
{"type": "lower"},
{"type": "title_case"},
{"type": "replace", "pattern": "old", "replacement": "new"},
{"type": "regex_replace", "pattern": "\\d+", "replacement": "XXX"},
{"type": "substring", "start": 0, "end": 10},
{"type": "pad_left", "length": 10, "char": "0"}
```

#### تحويلات الأنواع
```json
{"type": "to_string"},
{"type": "to_int"},
{"type": "to_float"},
{"type": "to_bool"},
{"type": "to_date", "format": "YYYY-MM-DD"},
{"type": "parse_json"}
```

#### العمليات على البيانات
```json
{"type": "default", "value": "default_value"},
{"type": "lookup", "table": "table_name"},
{"type": "concat", "values": ["field1", " - ", "field2"]},
{"type": "calculate", "expression": "${field1} + ${field2}"},
{"type": "conditional", "condition": "${age} > 18", "true_value": "adult", "false_value": "minor"}
```

### قواعد التحقق

عمليات فحص جودة البيانات مع معالجة أخطاء قابلة للتكوين:

#### عمليات التحقق الأساسية
```json
{"type": "required"},
{"type": "not_null"},
{"type": "min_length", "value": 5},
{"type": "max_length", "value": 100},
{"type": "range", "min": 0, "max": 1000},
{"type": "pattern", "value": "^[A-Z]{2,3}$"},
{"type": "in_list", "values": ["active", "inactive", "pending"]}
```

#### التحقق من الصحة المخصصة
```json
{
  "type": "custom",
  "expression": "${age} >= 18 && ${country} == 'US'",
  "message": "Must be 18+ and in US"
},
{
  "type": "cross_field",
  "fields": ["start_date", "end_date"],
  "expression": "${start_date} < ${end_date}",
  "message": "Start date must be before end date"
}
```

### المعالجة الأولية والمعالجة اللاحقة

العمليات العامة المطبقة قبل/بعد تعيين الحقول:

```json
{
  "preprocessing": [
    {
      "type": "filter",
      "condition": "${status} != 'deleted'"
    },
    {
      "type": "sort",
      "field": "created_date",
      "order": "asc"
    }
  ],
  "postprocessing": [
    {
      "type": "deduplicate",
      "key_fields": ["email", "phone"]
    },
    {
      "type": "aggregate",
      "group_by": ["country"],
      "functions": {
        "total_count": {"type": "count"},
        "avg_age": {"type": "avg", "field": "age"}
      }
    }
  ]
}
```

### إعدادات الإخراج

حدد كيفية إخراج البيانات المعالجة:

```json
{
  "output": {
    "format": "trustgraph-objects",
    "schema_name": "person",
    "options": {
      "batch_size": 1000,
      "confidence": 0.9,
      "source_span_field": "raw_text",
      "metadata": {
        "source": "crm_import",
        "version": "1.0"
      }
    },
    "error_handling": {
      "on_validation_error": "skip|fail|log",
      "on_transform_error": "skip|fail|default",
      "max_errors": 100,
      "error_output": "errors.json"
    }
  }
}
```

## مثال كامل

```json
{
  "version": "1.0",
  "metadata": {
    "name": "Customer Import from CRM CSV",
    "description": "Imports customer data from legacy CRM system",
    "author": "Data Team",
    "created": "2024-01-01T00:00:00Z"
  },
  "format": {
    "type": "csv",
    "encoding": "utf-8",
    "options": {
      "delimiter": ",",
      "has_header": true,
      "skip_rows": 1
    }
  },
  "globals": {
    "variables": {
      "import_date": "2024-01-01",
      "default_confidence": 0.85
    },
    "lookup_tables": {
      "country_codes": {
        "US": "United States",
        "CA": "Canada",
        "UK": "United Kingdom"
      }
    }
  },
  "preprocessing": [
    {
      "type": "filter",
      "condition": "${status} == 'active'"
    }
  ],
  "mappings": [
    {
      "target_field": "full_name",
      "source": "customer_name",
      "transforms": [
        {"type": "trim"},
        {"type": "title_case"}
      ],
      "validation": [
        {"type": "required"},
        {"type": "min_length", "value": 2}
      ]
    },
    {
      "target_field": "email",
      "source": "email_address",
      "transforms": [
        {"type": "trim"},
        {"type": "lower"}
      ],
      "validation": [
        {"type": "pattern", "value": "^[\\w.-]+@[\\w.-]+\\.[a-zA-Z]{2,}$"}
      ]
    },
    {
      "target_field": "age",
      "source": "age",
      "transforms": [
        {"type": "to_int"},
        {"type": "default", "value": 0}
      ],
      "validation": [
        {"type": "range", "min": 0, "max": 120}
      ]
    },
    {
      "target_field": "country",
      "source": "country_code",
      "transforms": [
        {"type": "lookup", "table": "country_codes"},
        {"type": "default", "value": "Unknown"}
      ]
    }
  ],
  "output": {
    "format": "trustgraph-objects",
    "schema_name": "customer",
    "options": {
      "confidence": "${default_confidence}",
      "batch_size": 500
    },
    "error_handling": {
      "on_validation_error": "log",
      "max_errors": 50
    }
  }
}
```

## موجه نموذج اللغة الكبير لإنشاء الوصف

يمكن استخدام الموجه التالي لجعل نموذج لغة كبير يحلل بيانات عينة وينشئ تكوينًا للوصف:

```
I need you to analyze the provided data sample and create a Structured Data Descriptor configuration in JSON format.

The descriptor should follow this specification:
- version: "1.0"
- metadata: Configuration name, description, author, and creation date
- format: Input format type and parsing options
- globals: Variables, lookup tables, and constants
- preprocessing: Filters and transformations applied before mapping
- mappings: Field-by-field mapping from source to target with transformations and validations
- postprocessing: Operations like deduplication or aggregation
- output: Target format and error handling configuration

ANALYZE THE DATA:
1. Identify the format (CSV, JSON, XML, etc.)
2. Detect delimiters, encodings, and structure
3. Find data types for each field
4. Identify patterns and constraints
5. Look for fields that need cleaning or transformation
6. Find relationships between fields
7. Identify lookup opportunities (codes that map to values)
8. Detect required vs optional fields

CREATE THE DESCRIPTOR:
For each field in the sample data:
- Map it to an appropriate target field name
- Add necessary transformations (trim, case conversion, type casting)
- Include appropriate validations (required, patterns, ranges)
- Set defaults for missing values

Include preprocessing if needed:
- Filters to exclude invalid records
- Sorting requirements

Include postprocessing if beneficial:
- Deduplication on key fields
- Aggregation for summary data

Configure output for TrustGraph:
- format: "trustgraph-objects"
- schema_name: Based on the data entity type
- Appropriate error handling

DATA SAMPLE:
[Insert data sample here]

ADDITIONAL CONTEXT (optional):
- Target schema name: [if known]
- Business rules: [any specific requirements]
- Data quality issues to address: [known problems]

Generate a complete, valid Structured Data Descriptor configuration that will properly import this data into TrustGraph. Include comments explaining key decisions.
```

### مثال للاستخدام

```
I need you to analyze the provided data sample and create a Structured Data Descriptor configuration in JSON format.

[Standard instructions from above...]

DATA SAMPLE:
```csv
CustomerID، الاسم، البريد الإلكتروني، العمر، البلد، الحالة، تاريخ الانضمام، إجمالي المشتريات
1001، "Smith, John"، john.smith@email.com، 35، الولايات المتحدة الأمريكية، 1، 2023-01-15، 5420.50
1002، "doe, jane"، JANE.DOE@GMAIL.COM، 28، كندا، 1، 2023-03-22، 3200.00
1003، "Bob Johnson"، bob@، 62، المملكة المتحدة، 0، 2022-11-01، 0
1004، "Alice Chen"، alice.chen@company.org، 41، الولايات المتحدة الأمريكية، 1، 2023-06-10، 8900.25
1005، ، invalid-email، 25، XX، 1، 2024-01-01، 100
```

ADDITIONAL CONTEXT:
- Target schema name: customer
- Business rules: Email should be valid and lowercase, names should be title case
- Data quality issues: Some emails are invalid, some names are missing, country codes need mapping
```

### طلب لتحليل البيانات الحالية بدون عينة

```
I need you to help me create a Structured Data Descriptor configuration for importing [data type] data.

The source data has these characteristics:
- Format: [CSV/JSON/XML/etc]
- Fields: [list the fields]
- Data quality issues: [describe any known issues]
- Volume: [approximate number of records]

Requirements:
- [List any specific transformation needs]
- [List any validation requirements]
- [List any business rules]

Please generate a Structured Data Descriptor configuration that will:
1. Parse the input format correctly
2. Clean and standardize the data
3. Validate according to the requirements
4. Handle errors gracefully
5. Output in TrustGraph ExtractedObject format

Focus on making the configuration robust and reusable.
```