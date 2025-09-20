# Structured Data Descriptor Specification

## Overview

The Structured Data Descriptor is a JSON-based configuration language that describes how to parse, transform, and import structured data into TrustGraph. It provides a declarative approach to data ingestion, supporting multiple input formats and complex transformation pipelines without requiring custom code.

## Core Concepts

### 1. Format Definition
Describes the input file type and parsing options. Determines which parser to use and how to interpret the source data.

### 2. Field Mappings  
Maps source paths to target fields with transformations. Defines how data flows from input sources to output schema fields.

### 3. Transform Pipeline
Chain of data transformations that can be applied to field values, including:
- Data cleaning (trim, normalize)
- Format conversion (date parsing, type casting)  
- Calculations (arithmetic, string manipulation)
- Lookups (reference tables, substitutions)

### 4. Validation Rules
Data quality checks applied to ensure data integrity:
- Type validation
- Range checks  
- Pattern matching (regex)
- Required field validation
- Custom validation logic

### 5. Global Settings
Configuration that applies across the entire import process:
- Lookup tables for data enrichment
- Global variables and constants
- Output format specifications
- Error handling policies

## Implementation Strategy

The importer implementation follows this pipeline:

1. **Parse Configuration** - Load and validate the JSON descriptor
2. **Initialize Parser** - Load appropriate parser (CSV, XML, JSON, etc.) based on `format.type`  
3. **Apply Preprocessing** - Execute global filters and transformations
4. **Process Records** - For each input record:
   - Extract data using source paths (JSONPath, XPath, column names)
   - Apply field-level transforms in sequence
   - Validate results against defined rules
   - Apply default values for missing data
5. **Apply Postprocessing** - Execute deduplication, aggregation, etc.
6. **Generate Output** - Produce data in specified target format

## Path Expression Support

Different input formats use appropriate path expression languages:

- **CSV**: Column names or indices (`"column_name"` or `"[2]"`)
- **JSON**: JSONPath syntax (`"$.user.profile.email"`)  
- **XML**: XPath expressions (`"//product[@id='123']/price"`)
- **Fixed-width**: Field names from field definitions

## Benefits

- **Single Codebase** - One importer handles multiple input formats
- **User-Friendly** - Non-technical users can create configurations  
- **Reusable** - Configurations can be shared and versioned
- **Flexible** - Complex transformations without custom coding
- **Robust** - Built-in validation and comprehensive error handling
- **Maintainable** - Declarative approach reduces implementation complexity

## Language Specification

The Structured Data Descriptor uses a JSON configuration format with the following top-level structure:

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

### Format Definition

Describes the input data format and parsing options:

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

#### CSV Format Options
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

#### JSON Format Options
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

#### XML Format Options
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

### Global Settings

Define lookup tables, variables, and global configuration:

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

### Field Mappings

Define how source data maps to target fields with transformations:

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

### Transform Types

Available transformation functions:

#### String Transforms
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

#### Type Conversions
```json
{"type": "to_string"},
{"type": "to_int"},
{"type": "to_float"},
{"type": "to_bool"},
{"type": "to_date", "format": "YYYY-MM-DD"},
{"type": "parse_json"}
```

#### Data Operations
```json
{"type": "default", "value": "default_value"},
{"type": "lookup", "table": "table_name"},
{"type": "concat", "values": ["field1", " - ", "field2"]},
{"type": "calculate", "expression": "${field1} + ${field2}"},
{"type": "conditional", "condition": "${age} > 18", "true_value": "adult", "false_value": "minor"}
```

### Validation Rules

Data quality checks with configurable error handling:

#### Basic Validations
```json
{"type": "required"},
{"type": "not_null"},
{"type": "min_length", "value": 5},
{"type": "max_length", "value": 100},
{"type": "range", "min": 0, "max": 1000},
{"type": "pattern", "value": "^[A-Z]{2,3}$"},
{"type": "in_list", "values": ["active", "inactive", "pending"]}
```

#### Custom Validations
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

### Preprocessing and Postprocessing

Global operations applied before/after field mapping:

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

### Output Configuration

Define how processed data should be output:

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

## Complete Example

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

## LLM Prompt for Descriptor Generation

The following prompt can be used to have an LLM analyze sample data and generate a descriptor configuration:

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

### Example Usage Prompt

```
I need you to analyze the provided data sample and create a Structured Data Descriptor configuration in JSON format.

[Standard instructions from above...]

DATA SAMPLE:
```csv
CustomerID,Name,Email,Age,Country,Status,JoinDate,TotalPurchases
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

### Prompt for Analyzing Existing Data Without Sample

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