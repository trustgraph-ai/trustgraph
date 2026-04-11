# संरचित डेटा विवरण विनिर्देश

## अवलोकन

संरचित डेटा विवरण एक JSON-आधारित कॉन्फ़िगरेशन भाषा है जो यह बताती है कि संरचित डेटा को कैसे पार्स, रूपांतरित और ट्रस्टग्राफ में आयात किया जाए। यह डेटा इनग्रेसन के लिए एक घोषणात्मक दृष्टिकोण प्रदान करता है, जो कई इनपुट प्रारूपों और जटिल परिवर्तन पाइपलाइनों का समर्थन करता है, बिना कस्टम कोड की आवश्यकता के।

## मुख्य अवधारणाएँ

### 1. प्रारूप परिभाषा
इनपुट फ़ाइल प्रकार और पार्सिंग विकल्पों का वर्णन करता है। यह निर्धारित करता है कि किस पार्सर का उपयोग करना है और स्रोत डेटा की व्याख्या कैसे करनी है।

### 2. फ़ील्ड मैपिंग
स्रोत पथों को लक्ष्य फ़ील्ड में रूपांतरणों के साथ मैप करता है। यह परिभाषित करता है कि डेटा इनपुट स्रोतों से आउटपुट स्कीमा फ़ील्ड में कैसे प्रवाहित होता है।

### 3. परिवर्तन पाइपलाइन
डेटा रूपांतरणों की श्रृंखला जो फ़ील्ड मानों पर लागू की जा सकती है, जिसमें शामिल हैं:
डेटा सफाई (ट्रिम, सामान्यीकरण)
प्रारूप रूपांतरण (तारीख पार्सिंग, प्रकार कास्टिंग)
गणनाएँ (अंकगणित, स्ट्रिंग हेरफेर)
लुकअप (संदर्भ तालिकाएँ, प्रतिस्थापन)

### 4. सत्यापन नियम
डेटा गुणवत्ता जांच जो डेटा अखंडता सुनिश्चित करने के लिए लागू की जाती हैं:
प्रकार सत्यापन
सीमा जांच
पैटर्न मिलान (रेगेक्स)
आवश्यक फ़ील्ड सत्यापन
कस्टम सत्यापन तर्क

### 5. वैश्विक सेटिंग्स
कॉन्फ़िगरेशन जो संपूर्ण आयात प्रक्रिया पर लागू होता है:
डेटा संवर्धन के लिए लुकअप तालिकाएँ
वैश्विक चर और स्थिरांक
आउटपुट प्रारूप विनिर्देश
त्रुटि हैंडलिंग नीतियां

## कार्यान्वयन रणनीति

इम्पोर्टर कार्यान्वयन निम्नलिखित पाइपलाइन का पालन करता है:

1. **कॉन्फ़िगरेशन पार्स करें** - JSON विवरण लोड करें और मान्य करें
2. **पार्सर आरंभ करें** - उपयुक्त पार्सर लोड करें (CSV, XML, JSON, आदि) `format.type` के आधार पर
3. **पूर्व-प्रसंस्करण लागू करें** - वैश्विक फ़िल्टर और रूपांतरण निष्पादित करें
4. **रिकॉर्ड संसाधित करें** - प्रत्येक इनपुट रिकॉर्ड के लिए:
   स्रोत पथों (JSONPath, XPath, कॉलम नाम) का उपयोग करके डेटा निकालें
   अनुक्रम में फ़ील्ड-स्तरीय रूपांतरण लागू करें
   परिभाषित नियमों के विरुद्ध परिणामों को मान्य करें
   लापता डेटा के लिए डिफ़ॉल्ट मान लागू करें
5. **पोस्ट-प्रोसेसिंग लागू करें** - डुप्लिकेट हटाना, एकत्रीकरण, आदि निष्पादित करें।
6. **आउटपुट उत्पन्न करें** - निर्दिष्ट लक्ष्य प्रारूप में डेटा उत्पन्न करें

## पथ अभिव्यक्ति समर्थन

विभिन्न इनपुट प्रारूप उपयुक्त पथ अभिव्यक्ति भाषाओं का उपयोग करते हैं:

**CSV**: कॉलम नाम या इंडेक्स (`"column_name"` या `"[2]"`)
**JSON**: JSONPath सिंटैक्स (`"$.user.profile.email"`)
**XML**: XPath एक्सप्रेशन (`"//product[@id='123']/price"`)
**फिक्स्ड-विड्थ**: फ़ील्ड परिभाषाओं से फ़ील्ड नाम

## लाभ

**सिंगल कोडबेस** - एक इम्पोर्टर कई इनपुट प्रारूपों को संभालता है
**उपयोगकर्ता के अनुकूल** - गैर-तकनीकी उपयोगकर्ता कॉन्फ़िगरेशन बना सकते हैं
**पुन: प्रयोज्य** - कॉन्फ़िगरेशन साझा और संस्करणित किए जा सकते हैं
**लचीला** - कस्टम कोडिंग के बिना जटिल रूपांतरण
**मजबूत** - अंतर्निहित सत्यापन और व्यापक त्रुटि हैंडलिंग
**रखरखाव योग्य** - घोषणात्मक दृष्टिकोण कार्यान्वयन जटिलता को कम करता है

## भाषा विनिर्देश

संरचित डेटा विवरण एक JSON कॉन्फ़िगरेशन प्रारूप का उपयोग करता है जिसमें निम्नलिखित शीर्ष-स्तरीय संरचना है:

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

### प्रारूप परिभाषा

इनपुट डेटा प्रारूप और पार्सिंग विकल्पों का वर्णन करता है:

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

#### सीएसवी प्रारूप विकल्प
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

#### जेएसओएन प्रारूप विकल्प
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

#### XML प्रारूप विकल्प
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

### वैश्विक सेटिंग्स

लुकअप टेबल, वेरिएबल और वैश्विक कॉन्फ़िगरेशन को परिभाषित करें:

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

### फ़ील्ड मैपिंग

परिभाषित करें कि स्रोत डेटा लक्ष्य फ़ील्ड में कैसे मैप होता है, जिसमें रूपांतरण शामिल हैं:

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

### रूपांतरण प्रकार

उपलब्ध रूपांतरण फ़ंक्शन:

#### स्ट्रिंग रूपांतरण
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

#### प्रकार रूपांतरण
```json
{"type": "to_string"},
{"type": "to_int"},
{"type": "to_float"},
{"type": "to_bool"},
{"type": "to_date", "format": "YYYY-MM-DD"},
{"type": "parse_json"}
```

#### डेटा संचालन
```json
{"type": "default", "value": "default_value"},
{"type": "lookup", "table": "table_name"},
{"type": "concat", "values": ["field1", " - ", "field2"]},
{"type": "calculate", "expression": "${field1} + ${field2}"},
{"type": "conditional", "condition": "${age} > 18", "true_value": "adult", "false_value": "minor"}
```

### सत्यापन नियम

कॉन्फ़िगर करने योग्य त्रुटि प्रबंधन के साथ डेटा गुणवत्ता जांच:

#### बुनियादी सत्यापन
```json
{"type": "required"},
{"type": "not_null"},
{"type": "min_length", "value": 5},
{"type": "max_length", "value": 100},
{"type": "range", "min": 0, "max": 1000},
{"type": "pattern", "value": "^[A-Z]{2,3}$"},
{"type": "in_list", "values": ["active", "inactive", "pending"]}
```

#### कस्टम सत्यापन
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

### पूर्व-प्रसंस्करण और उत्तर-प्रसंस्करण

फ़ील्ड मैपिंग से पहले/बाद लागू किए गए वैश्विक ऑपरेशन:

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

### आउटपुट कॉन्फ़िगरेशन

परिभाषित करें कि संसाधित डेटा को कैसे आउटपुट किया जाना चाहिए:

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

## पूर्ण उदाहरण

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

## एलएलएम प्रॉम्प्ट (LLM Prompt) का उपयोग करके विवरण (डेस्क्रिप्टर) निर्माण

निम्नलिखित प्रॉम्प्ट का उपयोग करके, एक एलएलएम (LLM) नमूना डेटा का विश्लेषण कर सकता है और एक विवरण कॉन्फ़िगरेशन उत्पन्न कर सकता है:

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

### उदाहरण उपयोग संकेत

```
I need you to analyze the provided data sample and create a Structured Data Descriptor configuration in JSON format.

[Standard instructions from above...]

DATA SAMPLE:
```csv
ग्राहक आईडी, नाम, ईमेल, आयु, देश, स्थिति, शामिल होने की तिथि, कुल खरीदारी
1001, "स्मिथ, जॉन", john.smith@email.com, 35, यूएस, 1, 2023-01-15, 5420.50
1002, "डो, जेन", JANE.DOE@GMAIL.COM, 28, कनाडा, 1, 2023-03-22, 3200.00
1003, "बॉब जॉनसन", bob@, 62, यूके, 0, 2022-11-01, 0
1004, "एलिस चेन", "alice.chen@company.org", 41, यूएस, 1, 2023-06-10, 8900.25
1005, , invalid-email, 25, XX, 1, 2024-01-01, 100
```

ADDITIONAL CONTEXT:
- Target schema name: customer
- Business rules: Email should be valid and lowercase, names should be title case
- Data quality issues: Some emails are invalid, some names are missing, country codes need mapping
```

### मौजूदा डेटा का विश्लेषण करने के लिए संकेत (प्रॉम्प्ट) बिना नमूने के

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