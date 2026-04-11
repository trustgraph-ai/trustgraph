# 结构化数据描述符规范

## 概述

结构化数据描述符是一种基于 JSON 的配置语言，用于描述如何解析、转换和导入结构化数据到 TrustGraph 中。它提供了一种声明式的数据导入方法，支持多种输入格式和复杂的转换流程，而无需自定义代码。

## 核心概念

### 1. 格式定义
描述输入文件类型和解析选项。确定要使用的解析器以及如何解释源数据。

### 2. 字段映射
将源路径映射到目标字段，并进行转换。定义数据如何从输入源流向输出模式字段。

### 3. 转换流程
一系列应用于字段值的转换，包括：
数据清洗（修剪、标准化）
格式转换（日期解析、类型转换）
计算（算术运算、字符串操作）
查找（引用表、替换）

### 4. 验证规则
应用于确保数据完整性的数据质量检查：
类型验证
范围检查
模式匹配（正则表达式）
必填字段验证
自定义验证逻辑

### 5. 全局设置
适用于整个导入过程的配置：
用于数据增强的查找表
全局变量和常量
输出格式规范
错误处理策略

## 实施策略

导入器的实现遵循以下流程：

1. **解析配置** - 加载和验证 JSON 描述符
2. **初始化解析器** - 根据 `format.type` 加载适当的解析器（CSV、XML、JSON 等）
3. **应用预处理** - 执行全局过滤器和转换
4. **处理记录** - 对于每个输入记录：
   使用源路径（JSONPath、XPath、列名）提取数据
   按照顺序应用字段级别的转换
   根据定义的规则验证结果
   为缺失数据应用默认值
5. **应用后处理** - 执行去重、聚合等操作
6. **生成输出** - 以指定的目标格式生成数据

## 路径表达式支持

不同的输入格式使用适当的路径表达式语言：

**CSV**: 列名或索引（`"column_name"` 或 `"[2]"`）
**JSON**: JSONPath 语法（`"$.user.profile.email"`）
**XML**: XPath 表达式（`"//product[@id='123']/price"`）
**定宽**: 来自字段定义的字段名

## 优点

**单一代码库** - 一个导入器处理多种输入格式
**用户友好** - 非技术用户可以创建配置
**可重用** - 可以共享和版本控制配置
**灵活** - 无需自定义代码即可进行复杂的转换
**健壮** - 内置验证和全面的错误处理
**可维护** - 声明式方法减少了实施复杂性

## 语言规范

结构化数据描述符使用基于 JSON 的配置格式，其顶级结构如下：

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

### 格式定义

描述输入数据格式和解析选项：

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

#### CSV 格式选项
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

#### JSON 格式选项
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

#### XML 格式选项
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

### 全局设置

定义查找表、变量和全局配置：

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

### 字段映射

定义如何将源数据映射到目标字段，并进行转换：

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

### 转换类型

可用的转换函数：

#### 字符串转换
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

#### 类型转换
```json
{"type": "to_string"},
{"type": "to_int"},
{"type": "to_float"},
{"type": "to_bool"},
{"type": "to_date", "format": "YYYY-MM-DD"},
{"type": "parse_json"}
```

#### 数据操作
```json
{"type": "default", "value": "default_value"},
{"type": "lookup", "table": "table_name"},
{"type": "concat", "values": ["field1", " - ", "field2"]},
{"type": "calculate", "expression": "${field1} + ${field2}"},
{"type": "conditional", "condition": "${age} > 18", "true_value": "adult", "false_value": "minor"}
```

### 验证规则

数据质量检查，具有可配置的错误处理：

#### 基础验证
```json
{"type": "required"},
{"type": "not_null"},
{"type": "min_length", "value": 5},
{"type": "max_length", "value": 100},
{"type": "range", "min": 0, "max": 1000},
{"type": "pattern", "value": "^[A-Z]{2,3}$"},
{"type": "in_list", "values": ["active", "inactive", "pending"]}
```

#### 自定义验证
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

### 预处理和后处理

在字段映射之前/之后应用的全局操作：

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

### 输出配置

定义如何输出处理后的数据：

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

## 完整示例

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

## 用于描述符生成的 LLM 提示

以下提示可用于让 LLM 分析样本数据并生成描述符配置：

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

### 示例用法提示

```
I need you to analyze the provided data sample and create a Structured Data Descriptor configuration in JSON format.

[Standard instructions from above...]

DATA SAMPLE:
```csv
客户ID,姓名,电子邮件,年龄,国家,状态,加入日期,总购买额
1001,"Smith, John",john.smith@email.com,35,美国,1,2023-01-15,5420.50
1002,"doe, jane",JANE.DOE@GMAIL.COM,28,加拿大,1,2023-03-22,3200.00
1003,"Bob Johnson",bob@,62,英国,0,2022-11-01,0
1004,"Alice Chen","alice.chen@company.org",41,美国,1,2023-06-10,8900.25
1005,,invalid-email,25,XX,1,2024-01-01,100
```

ADDITIONAL CONTEXT:
- Target schema name: customer
- Business rules: Email should be valid and lowercase, names should be title case
- Data quality issues: Some emails are invalid, some names are missing, country codes need mapping
```

### 用于分析现有数据而无需样本的提示

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