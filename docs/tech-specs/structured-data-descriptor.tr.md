# Yapılandırılmış Veri Tanımlayıcı Özellikleri

## Genel Bakış

Yapılandırılmış Veri Tanımlayıcı, JSON tabanlı bir yapılandırma dilidir ve TrustGraph'a yapılandırılmış verilerin nasıl ayrıştırıldığı, dönüştürüldüğü ve içe aktarıldığını tanımlar. Veri içe aktarma için deklaratif bir yaklaşım sunar, çoklu giriş formatlarını ve özel kod gerektirmeden karmaşık dönüşüm süreçlerini destekler.

## Temel Kavramlar

### 1. Format Tanımı
Giriş dosya türünü ve ayrıştırma seçeneklerini tanımlar. Hangi ayrıştırıcının kullanılacağını ve kaynak verilerin nasıl yorumlanacağını belirler.

### 2. Alan Eşlemeleri
Kaynak yollarını hedef alanlarla dönüşümlerle eşler. Verilerin kaynaklardan çıktı şema alanlarına nasıl aktığını tanımlar.

### 3. Dönüşüm Süreci
Alan değerlerine uygulanabilecek veri dönüşüm zinciri. Şunları içerir:
Veri temizleme (boşlukları kaldırma, normalleştirme)
Biçim dönüştürme (tarih ayrıştırma, tür dönüştürme)
Hesaplamalar (aritmetik işlemler, dize manipülasyonu)
Arama tabloları (referans tabloları, eşleştirmeler)

### 4. Doğrulama Kuralları
Veri bütünlüğünü sağlamak için uygulanan veri kalitesi kontrolleri:
Tür doğrulama
Aralık kontrolleri
Desen eşleştirme (regex)
Gerekli alan doğrulama
Özel doğrulama mantığı

### 5. Genel Ayarlar
Tüm içe aktarma sürecine uygulanan yapılandırma:
Veri zenginleştirme için arama tabloları
Küresel değişkenler ve sabitler
Çıktı biçimi özellikleri
Hata işleme politikaları

## Uygulama Stratejisi

İçe aktarıcı uygulaması aşağıdaki süreci izler:

1. **Yapılandırmayı Ayrıştır** - JSON tanımlayıcısını yükleyin ve doğrulayın
2. **Ayrıştırıcıyı Başlat** - `format.type`'a göre uygun ayrıştırıcıyı yükleyin (CSV, XML, JSON, vb.)
3. **Ön İşleme Uygula** - Küresel filtreleri ve dönüşümleri çalıştırın
4. **Kayıtları İşle** - Her giriş kaydı için:
   Kaynak yollarını (JSONPath, XPath, sütun adları) kullanarak verileri çıkarın
   Alan düzeyindeki dönüşümleri sırayla uygulayın
   Sonuçları tanımlı kurallara göre doğrulayın
   Eksik veriler için varsayılan değerleri uygulayın
5. **Son İşleme Uygula** - Tekilleştirme, birleştirme, vb. işlemlerini gerçekleştirin
6. **Çıktıyı Oluştur** - Verileri belirtilen hedef biçimde oluşturun

## Yol İfadesi Desteği

Farklı giriş formatları, uygun yol ifadesi dillerini kullanır:

**CSV**: Sütun adları veya indeksler (`"column_name"` veya `"[2]"`)
**JSON**: JSONPath sözdizimi (`"$.user.profile.email"`)
**XML**: XPath ifadeleri (`"//product[@id='123']/price"`)
**Sabit genişlik**: Alan tanımlarından alan adları

## Avantajlar

**Tek Kod Tabanı** - Tek bir içe aktarıcı, çoklu giriş formatlarını işler
**Kullanıcı Dostu** - Teknik olmayan kullanıcılar, yapılandırmalar oluşturabilir
**Yeniden Kullanılabilir** - Yapılandırmalar paylaşılabilir ve sürüm kontrolüne tabi tutulabilir
**Esnek** - Özel kodlama olmadan karmaşık dönüşümler
**Sağlam** - Yerleşik doğrulama ve kapsamlı hata işleme
**Bakımı Kolay** - Deklaratif yaklaşım, uygulama karmaşıklığını azaltır

## Dil Özellikleri

Yapılandırılmış Veri Tanımlayıcı, aşağıdaki üst düzey yapıya sahip bir JSON yapılandırma biçimi kullanır:

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

### Biçim Tanımı

Giriş verisi biçimini ve ayrıştırma seçeneklerini açıklar:

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

#### CSV Format Seçenekleri
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

#### JSON Formatı Seçenekleri
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

#### XML Formatı Seçenekleri
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

### Küresel Ayarlar

Arama tablolarını, değişkenleri ve genel yapılandırmayı tanımlayın:

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

### Alan Eşlemeleri

Dönüşümlerle birlikte kaynak verilerinin hedef alanlara nasıl eşlendiğini tanımlayın:

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

### Dönüşüm Türleri

Kullanılabilir dönüşüm fonksiyonları:

#### String Dönüşümleri
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

#### Tür Dönüşümleri
```json
{"type": "to_string"},
{"type": "to_int"},
{"type": "to_float"},
{"type": "to_bool"},
{"type": "to_date", "format": "YYYY-MM-DD"},
{"type": "parse_json"}
```

#### Veri İşlemleri
```json
{"type": "default", "value": "default_value"},
{"type": "lookup", "table": "table_name"},
{"type": "concat", "values": ["field1", " - ", "field2"]},
{"type": "calculate", "expression": "${field1} + ${field2}"},
{"type": "conditional", "condition": "${age} > 18", "true_value": "adult", "false_value": "minor"}
```

### Doğrulama Kuralları

Yapılandırılabilir hata yönetimi ile veri kalitesi kontrolleri:

#### Temel Doğrulamalar
```json
{"type": "required"},
{"type": "not_null"},
{"type": "min_length", "value": 5},
{"type": "max_length", "value": 100},
{"type": "range", "min": 0, "max": 1000},
{"type": "pattern", "value": "^[A-Z]{2,3}$"},
{"type": "in_list", "values": ["active", "inactive", "pending"]}
```

#### Özel Doğrulamalar
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

### Ön İşleme ve Son İşleme

Alan eşlemesi öncesinde/sonrasında uygulanan genel işlemler:

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

### Çıktı Yapılandırması

İşlenmiş verilerin nasıl çıktı olarak verilmesi gerektiğini tanımlayın:

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

## Tam Bir Örnek

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

## Açıklayıcı Oluşturma İçin LLM İstem

Aşağıdaki istem, bir LLM'nin örnek verileri analiz etmesi ve bir açıklayıcı yapılandırma oluşturması için kullanılabilir:

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

### Örnek Kullanım İsteği

```
I need you to analyze the provided data sample and create a Structured Data Descriptor configuration in JSON format.

[Standard instructions from above...]

DATA SAMPLE:
```csv
MüşteriID,Ad,E-posta,Yaş,Ülke,Durum,KayıtTarihi,ToplamSatınAlımlar
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

### Mevcut Verileri Örnek Olmadan Analiz Etme İsteği

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