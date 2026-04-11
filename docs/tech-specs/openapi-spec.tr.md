# OpenAPI Özellikleri - Teknik Belge

## Amaç

TrustGraph REST API Gateway için kapsamlı, modüler bir OpenAPI 3.1 spesifikasyonu oluşturmak, bu spesifikasyon şunları sağlamalıdır:
Tüm REST uç noktalarını belgelemelidir
Modülerlik ve bakım kolaylığı için harici `$ref` kullanmalıdır
Doğrudan mesaj çevirici koduna eşlenmelidir
Doğru istek/yanıt şemaları sağlamalıdır

## Doğru Kaynak

API aşağıdaki öğeler tarafından tanımlanır:
**Mesaj Çeviriciler**: `trustgraph-base/trustgraph/messaging/translators/*.py`
**Dağıtıcı Yöneticisi**: `trustgraph-flow/trustgraph/gateway/dispatch/manager.py`
**Uç Nokta Yöneticisi**: `trustgraph-flow/trustgraph/gateway/endpoint/manager.py`

## Dizin Yapısı

```
openapi/
├── openapi.yaml                          # Main entry point
├── paths/
│   ├── config.yaml                       # Global services
│   ├── flow.yaml
│   ├── librarian.yaml
│   ├── knowledge.yaml
│   ├── collection-management.yaml
│   ├── flow-services/                    # Flow-hosted services
│   │   ├── agent.yaml
│   │   ├── document-rag.yaml
│   │   ├── graph-rag.yaml
│   │   ├── text-completion.yaml
│   │   ├── prompt.yaml
│   │   ├── embeddings.yaml
│   │   ├── mcp-tool.yaml
│   │   ├── triples.yaml
│   │   ├── objects.yaml
│   │   ├── nlp-query.yaml
│   │   ├── structured-query.yaml
│   │   ├── structured-diag.yaml
│   │   ├── graph-embeddings.yaml
│   │   ├── document-embeddings.yaml
│   │   ├── text-load.yaml
│   │   └── document-load.yaml
│   ├── import-export/
│   │   ├── core-import.yaml
│   │   ├── core-export.yaml
│   │   └── flow-import-export.yaml      # WebSocket import/export
│   ├── websocket.yaml
│   └── metrics.yaml
├── components/
│   ├── schemas/
│   │   ├── config/
│   │   ├── flow/
│   │   ├── librarian/
│   │   ├── knowledge/
│   │   ├── collection/
│   │   ├── ai-services/
│   │   ├── common/
│   │   └── errors/
│   ├── parameters/
│   ├── responses/
│   └── examples/
└── security/
    └── bearerAuth.yaml
```

## Hizmet Eşlemesi

### Küresel Hizmetler (`/api/v1/{kind}`)
`config` - Yapılandırma yönetimi
`flow` - Akış yaşam döngüsü
`librarian` - Belge kütüphanesi
`knowledge` - Bilgi çekirdekleri
`collection-management` - Koleksiyon meta verileri

### Akışa Dayalı Hizmetler (`/api/v1/flow/{flow}/service/{kind}`)

**İstek/Yanıt:**
`agent`, `text-completion`, `prompt`, `mcp-tool`
`graph-rag`, `document-rag`
`embeddings`, `graph-embeddings`, `document-embeddings`
`triples`, `objects`, `nlp-query`, `structured-query`, `structured-diag`

**Gönder ve Unut:**
`text-load`, `document-load`

### İçe/Dışa Aktarma
`/api/v1/import-core` (POST)
`/api/v1/export-core` (GET)
`/api/v1/flow/{flow}/import/{kind}` (WebSocket)
`/api/v1/flow/{flow}/export/{kind}` (WebSocket)

### Diğer
`/api/v1/socket` (WebSocket çoklama)
`/api/metrics` (Prometheus)

## Yaklaşım

### Aşama 1: Kurulum
1. Dizin yapısını oluşturun
2. Ana `openapi.yaml` dosyasını meta veriler, sunucular, güvenlik ile birlikte oluşturun
3. Yeniden kullanılabilir bileşenleri (hatalar, ortak parametreler, güvenlik şemaları) oluşturun

### Aşama 2: Ortak Şemalar
Hizmetler arasında kullanılan ortak şemaları oluşturun:
`RdfValue`, `Triple` - RDF/üçlü yapılar
`ErrorObject` - Hata yanıtı
`DocumentMetadata`, `ProcessingMetadata` - Meta veri yapıları
Ortak parametreler: `FlowId`, `User`, `Collection`

### Aşama 3: Küresel Hizmetler
Her küresel hizmet için (yapılandırma, akış, kütüphaneci, bilgi, koleksiyon yönetimi):
1. `paths/` içinde bir yol dosyası oluşturun
2. `components/schemas/{service}/` içinde bir istek şeması oluşturun
3. Bir yanıt şeması oluşturun
4. Örnekler ekleyin
5. Ana `openapi.yaml` dosyasından referans alın

### Aşama 4: Akışa Dayalı Hizmetler
Her akışa dayalı hizmet için:
1. `paths/flow-services/` içinde bir yol dosyası oluşturun
2. `components/schemas/ai-services/` içinde istek/yanıt şemalarını oluşturun
3. Gerekli durumlarda akış düzeyi akış bayrak dokümantasyonunu ekleyin
4. Ana `openapi.yaml` dosyasından referans alın

### Aşama 5: İçe/Dışa Aktarma & WebSocket
1. Temel içe/dışa aktarma uç noktalarını belgeleyin
2. WebSocket protokol kalıplarını belgeleyin
3. Akış düzeyindeki içe/dışa aktarma WebSocket uç noktalarını belgeleyin

### Aşama 6: Doğrulama
1. OpenAPI doğrulama araçlarıyla doğrulayın
2. Swagger UI ile test edin
3. Tüm çeviricilerin kapsandığından emin olun

## Alan Adlandırma Kuralları

Tüm JSON alanları **kebab-case** kullanır:
`flow-id`, `blueprint-name`, `doc-limit`, `entity-limit`, vb.

## Şema Dosyaları Oluşturma

Her çevirici için `trustgraph-base/trustgraph/messaging/translators/` içinde:

1. **Çevirici `to_pulsar()` yöntemini okuyun** - İstek şemasını tanımlar
2. **Çevirici `from_pulsar()` yöntemini okuyun** - Yanıt şemasını tanımlar
3. **Alan adlarını ve türlerini çıkarın**
4. Aşağıdakilerle bir OpenAPI şeması oluşturun:
   Alan adları (kebab-case)
   Türler (string, integer, boolean, object, array)
   Gerekli alanlar
   Varsayılanlar
   Açıklamalar

### Örnek Eşleme Süreci

```python
# From retrieval.py DocumentRagRequestTranslator
def to_pulsar(self, data: Dict[str, Any]) -> DocumentRagQuery:
    return DocumentRagQuery(
        query=data["query"],                              # required string
        user=data.get("user", "trustgraph"),             # optional string, default "trustgraph"
        collection=data.get("collection", "default"),     # optional string, default "default"
        doc_limit=int(data.get("doc-limit", 20)),        # optional integer, default 20
        streaming=data.get("streaming", False)            # optional boolean, default false
    )
```

Çevrilir:

```yaml
# components/schemas/ai-services/DocumentRagRequest.yaml
type: object
required:
  - query
properties:
  query:
    type: string
    description: Search query
  user:
    type: string
    default: trustgraph
  collection:
    type: string
    default: default
  doc-limit:
    type: integer
    default: 20
    description: Maximum number of documents to retrieve
  streaming:
    type: boolean
    default: false
    description: Enable streaming responses
```

## Akışlı Yanıtlar

Akışlı yanıtları destekleyen hizmetler, `end_of_stream` bayrağı ile birden fazla yanıt döndürür:
`agent`, `text-completion`, `prompt`
`document-rag`, `graph-rag`

Bu kalıbı, her hizmetin yanıt şemasında belgeleyin.

## Hata Yanıtları

Tüm hizmetler aşağıdaki yanıtları döndürebilir:
```yaml
error:
  oneOf:
    - type: string
    - $ref: '#/components/schemas/ErrorObject'
```

`ErrorObject` ifadesi nerede bulunuyor:
```yaml
type: object
properties:
  type:
    type: string
  message:
    type: string
```

## Referanslar

Çevirenler: `trustgraph-base/trustgraph/messaging/translators/`
Dağıtım eşlemesi: `trustgraph-flow/trustgraph/gateway/dispatch/manager.py`
Uç nokta yönlendirmesi: `trustgraph-flow/trustgraph/gateway/endpoint/manager.py`
Hizmet özeti: `API_SERVICES_SUMMARY.md`
