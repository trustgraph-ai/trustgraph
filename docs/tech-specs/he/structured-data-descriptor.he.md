---
layout: default
title: "מפרט עבור תיאור נתונים מובנים"
parent: "Hebrew (Beta)"
---

# מפרט עבור תיאור נתונים מובנים

> **Beta Translation:** This document was translated via Machine Learning and as such may not be 100% accurate. All non-English languages are currently classified as Beta.

## סקירה כללית

תיאור הנתונים המובנים הוא שפת תצורה מבוססת JSON המתארת כיצד לנתח, להמיר ולייבא נתונים מובנים ל-TrustGraph. הוא מספק גישה הצהרתית לייבוא נתונים, תוך תמיכה בפורמטים מרובים של קלט וצינורות המרה מורכבים מבלי לדרוש קוד מותאם אישית.

## מושגים מרכזיים

### 1. הגדרת פורמט
מתאר את סוג הקובץ הנכנס ואפשרויות הניתוח. קובע איזה מנתח להשתמש וכיצד לפרש את הנתונים המקור.

### 2. מיפוי שדות
ממפה נתיבים מקור לשדות יעד עם המרות. מגדיר כיצד הנתונים זורמים ממקורות קלט לשדות סכימה בפלט.

### 3. צינור המרה
שרשרת של המרות נתונים שניתן להחיל על ערכי שדות, כולל:
ניקוי נתונים (חיתוך, נרמול)
המרת פורמט (ניתוח תאריכים, המרת טיפוסים)
חישובים (חשבון, מניפולציה של מחרוזות)
חיפושים (טבלאות הפניה, החלפות)

### 4. כללי אימות
בדיקות איכות נתונים המיושמות כדי להבטיח את שלמות הנתונים:
אימות טיפוס
בדיקות טווח
התאמת תבניות (ביטויים רגולריים)
אימות שדות חובה
לוגיקה מותאמת אישית לאימות

### 5. הגדרות גלובליות
תצורה החלה על כל תהליך הייבוא:
טבלאות חיפוש להעשרת נתונים
משתנים וקבועים גלובליים
מפרטי פורמט פלט
מדיניות טיפול בשגיאות

## אסטרטגיית יישום

יישום המייבא עוקב אחר הצינור הבא:

1. **ניתוח תצורה** - טעינה ואימות של תיאור JSON
2. **אתחול מנתח** - טעינת מנתח מתאים (CSV, XML, JSON, וכו') בהתבסס על `format.type`
3. **החלת עיבוד מקדים** - ביצוע פילטרים והמרות גלובליים
4. **עיבוד רשומות** - עבור כל רשומה נכנסת:
   חילוץ נתונים באמצעות נתיבי מקור (JSONPath, XPath, שמות עמודות)
   החלת המרות ברמת השדה בסדר
   אימות תוצאות בהתאם לכללים מוגדרים
   החלת ערכי ברירת מחדל עבור נתונים חסרים
5. **החלת עיבוד לאחר** - ביצוע הסרה כפילות, אגרגציה, וכו'.
6. **יצירת פלט** - יצירת נתונים בפורמט יעד מוגדר

## תמיכה בביטוי נתיב

פורמטים שונים של קלט משתמשים בשפות ביטוי נתיב מתאימות:

**CSV**: שמות עמודות או אינדקסים (`"column_name"` או `"[2]"`)
**JSON**: תחביר JSONPath (`"$.user.profile.email"`)
**XML**: ביטויי XPath (`"//product[@id='123']/price"`)
**רוחב קבוע**: שמות שדות מהגדרות שדות

## יתרונות

**בסיס קוד יחיד** - מייבא אחד מטפל בפורמטים מרובים של קלט
**ידידותי למשתמש** - משתמשים לא טכניים יכולים ליצור תצורות
**ניתן לשימוש חוזר** - ניתן לשתף תצורות ולגרסן
**גמיש** - המרות מורכבות ללא קידוד מותאם אישית
**יציב** - אימות מובנה וטיפול מקיף בשגיאות
**ניתן לתחזוקה** - גישה הצהרתית מפחיתה את מורכבות היישום

## מפרט שפה

תיאור הנתונים המובנים משתמש בפורמט תצורה JSON עם המבנה הבסיסי הבא ברמה העליונה:

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

### הגדרת פורמט

מתאר את פורמט הנתונים הקלט ואפשרויות הניתוח:

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

#### אפשרויות פורמט CSV
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

#### אפשרויות פורמט JSON
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

#### אפשרויות פורמט XML
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

### הגדרות גלובליות

הגדירו טבלאות חיפוש, משתנים ותצורות גלובליות:

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

### מיפוי שדות

הגדירו כיצד נתוני המקור ממופים לשדות היעד עם טרנספורמציות:

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

### סוגי טרנספורמציה

פונקציות טרנספורמציה זמינות:

#### טרנספורמציות מחרוזות
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

#### המרות טיפוסים
```json
{"type": "to_string"},
{"type": "to_int"},
{"type": "to_float"},
{"type": "to_bool"},
{"type": "to_date", "format": "YYYY-MM-DD"},
{"type": "parse_json"}
```

#### פעולות נתונים
```json
{"type": "default", "value": "default_value"},
{"type": "lookup", "table": "table_name"},
{"type": "concat", "values": ["field1", " - ", "field2"]},
{"type": "calculate", "expression": "${field1} + ${field2}"},
{"type": "conditional", "condition": "${age} > 18", "true_value": "adult", "false_value": "minor"}
```

### כללי אימות

בדיקות איכות נתונים עם טיפול בשגיאות הניתן להגדרה:

#### אימותים בסיסיים
```json
{"type": "required"},
{"type": "not_null"},
{"type": "min_length", "value": 5},
{"type": "max_length", "value": 100},
{"type": "range", "min": 0, "max": 1000},
{"type": "pattern", "value": "^[A-Z]{2,3}$"},
{"type": "in_list", "values": ["active", "inactive", "pending"]}
```

#### אימותים מותאמים אישית
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

### עיבוד מקדים ועיבוד סופי

פעולות גלובליות המיושמות לפני/אחרי מיפוי שדות:

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

### הגדרות פלט

הגדירו כיצד יש להוציא את הנתונים שעברו עיבוד:

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

## דוגמה מלאה

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

## הנחיה עבור מודל שפה גדול (LLM) ליצירת תיאור

ניתן להשתמש בהנחיה הבאה כדי לגרום למודל שפה גדול לנתח נתוני דוגמה וליצור תצורת תיאור:

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

### הנחיה לדוגמה לשימוש

```
I need you to analyze the provided data sample and create a Structured Data Descriptor configuration in JSON format.

[Standard instructions from above...]

DATA SAMPLE:
```csv
CustomerID,שם לקוח,כתובת דוא"ל,גיל,מדינה,סטטוס,תאריך הצטרפות,סך רכישות
1001,"Smith, John",john.smith@email.com,35,US,1,2023-01-15,5420.50
1002,"doe, jane",JANE.DOE@GMAIL.COM,28,CA,1,2023-03-22,3200.00
1003,"Bob Johnson",bob@,62,UK,0,2022-11-01,0
1004,"Alice Chen","alice.chen@company.org",41,US,1,2023-06-10,8900.25
1005,,invalid-email,25,XX,1,2024-01-01,100
```

ADDITIONAL CONTEXT:
- Target schema name: customer
- Business rules: Email should be valid and lowercase, names should be title case
- Data quality issues: Some emails are invalid, some names are missing, country codes need mapping
```

### הנחיה לניתוח נתונים קיימים ללא דוגמה

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
