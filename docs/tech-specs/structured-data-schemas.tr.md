# Yapılandırılmış Veri Pulsar Şema Değişiklikleri

## Genel Bakış

STRUCTURED_DATA.md spesifikasyonuna dayanarak, bu belge, TrustGraph'ta yapılandırılmış veri yeteneklerini desteklemek için gerekli olan Pulsar şema eklemelerini ve değişikliklerini önermektedir.

## Gerekli Şema Değişiklikleri

### 1. Temel Şema Geliştirmeleri

#### Gelişmiş Alan Tanımı
`core/primitives.py` içindeki mevcut `Field` sınıfı, ek özelliklere ihtiyaç duymaktadır:

```python
class Field(Record):
    name = String()
    type = String()  # int, string, long, bool, float, double, timestamp
    size = Integer()
    primary = Boolean()
    description = String()
    # NEW FIELDS:
    required = Boolean()  # Whether field is required
    enum_values = Array(String())  # For enum type fields
    indexed = Boolean()  # Whether field should be indexed
```

### 2. Yeni Bilgi Şemaları

#### 2.1 Yapılandırılmış Veri Gönderimi
Yeni dosya: `knowledge/structured.py`

```python
from pulsar.schema import Record, String, Bytes, Map
from ..core.metadata import Metadata

class StructuredDataSubmission(Record):
    metadata = Metadata()
    format = String()  # "json", "csv", "xml"
    schema_name = String()  # Reference to schema in config
    data = Bytes()  # Raw data to ingest
    options = Map(String())  # Format-specific options
```

### 3. Yeni Hizmet Şemaları

#### 3.1 Doğal Dil İşleme'den Yapılandırılmış Sorgu Hizmeti
Yeni dosya: `services/nlp_query.py`

```python
from pulsar.schema import Record, String, Array, Map, Integer, Double
from ..core.primitives import Error

class NLPToStructuredQueryRequest(Record):
    natural_language_query = String()
    max_results = Integer()
    context_hints = Map(String())  # Optional context for query generation

class NLPToStructuredQueryResponse(Record):
    error = Error()
    graphql_query = String()  # Generated GraphQL query
    variables = Map(String())  # GraphQL variables if any
    detected_schemas = Array(String())  # Which schemas the query targets
    confidence = Double()
```

#### 3.2 Yapılandırılmış Sorgu Hizmeti
Yeni dosya: `services/structured_query.py`

```python
from pulsar.schema import Record, String, Map, Array
from ..core.primitives import Error

class StructuredQueryRequest(Record):
    query = String()  # GraphQL query
    variables = Map(String())  # GraphQL variables
    operation_name = String()  # Optional operation name for multi-operation documents

class StructuredQueryResponse(Record):
    error = Error()
    data = String()  # JSON-encoded GraphQL response data
    errors = Array(String())  # GraphQL errors if any
```

#### 2.2 Nesne Çıkarımı Çıktısı
Yeni dosya: `knowledge/object.py`

```python
from pulsar.schema import Record, String, Map, Double
from ..core.metadata import Metadata

class ExtractedObject(Record):
    metadata = Metadata()
    schema_name = String()  # Which schema this object belongs to
    values = Map(String())  # Field name -> value
    confidence = Double()
    source_span = String()  # Text span where object was found
```

### 4. Gelişmiş Bilgi Şemaları

#### 4.1 Nesne Gömme İyileştirmeleri
`knowledge/embeddings.py`'ı, yapılandırılmış nesne gömmelerini daha iyi destekleyecek şekilde güncelleyin:

```python
class StructuredObjectEmbedding(Record):
    metadata = Metadata()
    vectors = Array(Array(Double()))
    schema_name = String()
    object_id = String()  # Primary key value
    field_embeddings = Map(Array(Double()))  # Per-field embeddings
```

## Entegrasyon Noktaları

### Akış Entegrasyonu

Bu şemalar, yeni akış modülleri tarafından kullanılacaktır:
`trustgraph-flow/trustgraph/decoding/structured` - StructuredDataSubmission'ı kullanır
`trustgraph-flow/trustgraph/query/nlp_query/cassandra` - NLP sorgu şemalarını kullanır
`trustgraph-flow/trustgraph/query/objects/cassandra` - Yapılandırılmış sorgu şemalarını kullanır
`trustgraph-flow/trustgraph/extract/object/row/` - Chunk'ı tüketir, ExtractedObject üretir
`trustgraph-flow/trustgraph/storage/objects/cassandra` - Rows şemasını kullanır
`trustgraph-flow/trustgraph/embeddings/object_embeddings/qdrant` - Nesne gömme şemalarını kullanır

## Uygulama Notları

1. **Şema Sürümleme**: Gelecekteki geçiş desteği için RowSchema'ya bir `version` alanı eklemeyi düşünün.
2. **Tip Sistemi**: `Field.type`, tüm Cassandra yerel türlerini desteklemelidir.
3. **Toplu İşlemler**: Çoğu hizmet, hem tekil hem de toplu işlemleri desteklemelidir.
4. **Hata Yönetimi**: Tüm yeni hizmetlerde tutarlı hata raporlama.
5. **Geriye Uyumluluk**: Mevcut şemalar, küçük alan geliştirmeleri dışında değişmeden kalacaktır.

## Sonraki Adımlar

1. Şema dosyalarını yeni yapıya göre uygulayın.
2. Mevcut hizmetleri, yeni şema türlerini tanıyacak şekilde güncelleyin.
3. Bu şemaları kullanan akış modüllerini uygulayın.
4. Yeni hizmetler için ağ geçidi/geri ağ geçidi uç noktaları ekleyin.
5. Şema doğrulaması için birim testleri oluşturun.
