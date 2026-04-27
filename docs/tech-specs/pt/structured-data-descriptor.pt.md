---
layout: default
title: "Especificação do Descritor de Dados Estruturados"
parent: "Portuguese (Beta)"
---

# Especificação do Descritor de Dados Estruturados

> **Beta Translation:** This document was translated via Machine Learning and as such may not be 100% accurate. All non-English languages are currently classified as Beta.

## Visão Geral

O Descritor de Dados Estruturados é uma linguagem de configuração baseada em JSON que descreve como analisar, transformar e importar dados estruturados para o TrustGraph. Ele fornece uma abordagem declarativa para a ingestão de dados, suportando vários formatos de entrada e pipelines de transformação complexos sem a necessidade de código personalizado.

## Conceitos Principais

### 1. Definição de Formato
Descreve o tipo de arquivo de entrada e as opções de análise. Determina qual analisador usar e como interpretar os dados de origem.

### 2. Mapeamentos de Campos
Mapeia caminhos de origem para campos de destino com transformações. Define como os dados fluem das fontes de entrada para os campos do esquema de saída.

### 3. Pipeline de Transformação
Cadeia de transformações de dados que podem ser aplicadas aos valores dos campos, incluindo:
Limpeza de dados (remover espaços em branco, normalização)
Conversão de formato (análise de data, conversão de tipo)
Cálculos (aritméticos, manipulação de strings)
Consultas (tabelas de referência, substituições)

### 4. Regras de Validação
Verificações de qualidade de dados aplicadas para garantir a integridade dos dados:
Validação de tipo
Verificações de intervalo
Correspondência de padrões (regex)
Validação de campos obrigatórios
Lógica de validação personalizada

### 5. Configurações Globais
Configuração que se aplica a todo o processo de importação:
Tabelas de consulta para enriquecimento de dados
Variáveis e constantes globais
Especificações de formato de saída
Políticas de tratamento de erros

## Estratégia de Implementação

A implementação do importador segue este pipeline:

1. **Analisar Configuração** - Carregar e validar o descritor JSON
2. **Inicializar Analisador** - Carregar o analisador apropriado (CSV, XML, JSON, etc.) com base em `format.type`
3. **Aplicar Pré-processamento** - Executar filtros e transformações globais
4. **Processar Registros** - Para cada registro de entrada:
   Extrair dados usando caminhos de origem (JSONPath, XPath, nomes de coluna)
   Aplicar transformações de nível de campo em sequência
   Validar os resultados em relação às regras definidas
   Aplicar valores padrão para dados ausentes
5. **Aplicar Pós-processamento** - Executar desduplicação, agregação, etc.
6. **Gerar Saída** - Produzir dados no formato de destino especificado

## Suporte a Expressões de Caminho

Diferentes formatos de entrada usam linguagens de expressão de caminho apropriadas:

**CSV**: Nomes de coluna ou índices (`"column_name"` ou `"[2]"`)
**JSON**: Sintaxe JSONPath (`"$.user.profile.email"`)
**XML**: Expressões XPath (`"//product[@id='123']/price"`)
**Largura Fixa**: Nomes de campo das definições de campo

## Benefícios

**Base de Código Única** - Um único importador lida com vários formatos de entrada
**Fácil de Usar** - Usuários não técnicos podem criar configurações
**Reutilizável** - As configurações podem ser compartilhadas e versionadas
**Flexível** - Transformações complexas sem codificação personalizada
**Robusto** - Validação integrada e tratamento de erros abrangente
**Manutenível** - A abordagem declarativa reduz a complexidade da implementação

## Especificação da Linguagem

O Descritor de Dados Estruturados usa um formato de configuração JSON com a seguinte estrutura de nível superior:

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

### Definição do Formato

Descreve o formato dos dados de entrada e as opções de análise:

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

#### Opções de Formato CSV
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

#### Opções de Formato JSON
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

#### Opções de Formato XML
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

### Configurações Globais

Defina tabelas de consulta, variáveis e configuração global:

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

### Mapeamentos de Campos

Defina como os dados de origem são mapeados para os campos de destino, com transformações:

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

### Tipos de Transformação

Funções de transformação disponíveis:

#### Transformações de String
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

#### Conversões de Tipo
```json
{"type": "to_string"},
{"type": "to_int"},
{"type": "to_float"},
{"type": "to_bool"},
{"type": "to_date", "format": "YYYY-MM-DD"},
{"type": "parse_json"}
```

#### Operações com Dados
```json
{"type": "default", "value": "default_value"},
{"type": "lookup", "table": "table_name"},
{"type": "concat", "values": ["field1", " - ", "field2"]},
{"type": "calculate", "expression": "${field1} + ${field2}"},
{"type": "conditional", "condition": "${age} > 18", "true_value": "adult", "false_value": "minor"}
```

### Regras de Validação

Verificações de qualidade de dados com tratamento de erros configurável:

#### Validações Básicas
```json
{"type": "required"},
{"type": "not_null"},
{"type": "min_length", "value": 5},
{"type": "max_length", "value": 100},
{"type": "range", "min": 0, "max": 1000},
{"type": "pattern", "value": "^[A-Z]{2,3}$"},
{"type": "in_list", "values": ["active", "inactive", "pending"]}
```

#### Validações Personalizadas
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

### Pré-processamento e pós-processamento

Operações globais aplicadas antes/depois do mapeamento de campos:

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

### Configuração de Saída

Defina como os dados processados devem ser enviados:

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

## Exemplo Completo

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

## Prompt de LLM para Geração de Descritores

O seguinte prompt pode ser usado para que um LLM analise dados de amostra e gere uma configuração de descritores:

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

### Exemplo de Uso (Prompt)

```
I need you to analyze the provided data sample and create a Structured Data Descriptor configuration in JSON format.

[Standard instructions from above...]

DATA SAMPLE:
```csv
CustomerID,Nome,Email,Idade,País,Status,Data de Adesão,Total de Compras
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

### Solicitação para Análise de Dados Existentes Sem Amostra

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
