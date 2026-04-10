# API Ağ Geçidi Değişiklikleri: v1.8'den v2.1'e

## Özet

API ağ geçidi, gömülü sorgular için yeni WebSocket hizmet yönlendiricileri, belge içeriği için yeni bir REST akış uç noktası kazandı ve ⟦CODE_0⟧'dan ⟦CODE_1⟧'e önemli bir veri formatı değişikliğine uğradı. "objects" hizmeti "rows" olarak yeniden adlandırıldı.
sorguları, belge içeriği için yeni bir REST akış uç noktası ve aşağıdaki değişiklikleri içerdi:
önemli bir tel format değişikliği, `Value`'dan `Term`'e geçiş. "Nesneler"


--

## Yeni WebSocket Hizmet Yönlendiricileri

Bunlar, WebSocket üzerinden sunulan yeni istek/yanıt servisleridir.
`/api/v1/socket` adresindeki çoklayıcı (akış kapsamlı):

| Servis Anahtarı | Açıklama |
|-------------|-------------|
| `document-embeddings` | Metin benzerliği ile belge parçalarını sorgular. İstek/yanıt, `DocumentEmbeddingsRequest`/`DocumentEmbeddingsResponse` şemalarını kullanır. |
| `row-embeddings` | İndekslenmiş alanlarda metin benzerliği ile yapılandırılmış veri satırlarını sorgular. İstek/yanıt, `RowEmbeddingsRequest`/`RowEmbeddingsResponse` şemalarını kullanır. |

Bunlar, mevcut `graph-embeddings` dağıtım aracına (v1.8'de zaten
bulunan ancak güncellenmiş olabilecek) eklenir.

### WebSocket akış hizmeti dağıtım araçlarının tam listesi (v2.1)

İstek/yanıt hizmetleri (`/api/v1/flow/{flow}/service/{kind}` veya
WebSocket çoklayıcısı aracılığıyla):

`agent`, `text-completion`, `prompt`, `mcp-tool`
`graph-rag`, `document-rag`
`embeddings`, `graph-embeddings`, `document-embeddings`
`triples`, `rows`, `nlp-query`, `structured-query`, `structured-diag`
`row-embeddings`

--

## Yeni REST Uç Noktası

| Yöntem | Yol | Açıklama |
|--------|------|-------------|
| `GET` | `/api/v1/document-stream` | Kütüphaneden belge içeriğini ham baytlar olarak aktarır. Sorgu parametreleri: `user` (gerekli), `document-id` (gerekli), `chunk-size` (isteğe bağlı, varsayılan 1MB). Belge içeriğini, dahili olarak base64'ten çözülmüş olarak, parçalı aktarım kodlamasıyla döndürür. |

--

## Yeniden Adlandırılan Hizmet: "objects" -> "rows"

| v1.8 | v2.1 | Notlar |
|------|------|-------|
| `objects_query.py` / `ObjectsQueryRequestor` | `rows_query.py` / `RowsQueryRequestor` | Şema, `ObjectsQueryRequest`/`ObjectsQueryResponse`'den `RowsQueryRequest`/`RowsQueryResponse`'ye dönüştürüldü. |
| `objects_import.py` / `ObjectsImport` | `rows_import.py` / `RowsImport` | Yapılandırılmış veri için import yöneticisi. |

WebSocket hizmet anahtarı `"objects"`'dan `"rows"`'e değişti ve
import yöneticisi anahtarı da benzer şekilde `"objects"`'dan `"rows"`'e değişti.

--

## Kablo Formatındaki Değişiklik: Değerden Terime

Seri hale getirme katmanı (`serialize.py`), yeni `Term`'i kullanmak üzere yeniden yazıldı.
eski `Value` türünün yerine bu türü kullanın.

### Eski format (v1.8 — `Value`)

```json
{"v": "http://example.org/entity", "e": true}
```

`v`: değer (string)
`e`: değerin bir URI olup olmadığını gösteren boolean işaretleyici

### Yeni format (v2.1 — `Term`)

IRIs:
```json
{"t": "i", "i": "http://example.org/entity"}
```

Sabitler:
```json
{"t": "l", "v": "some text", "d": "datatype-uri", "l": "en"}
```

Tırnak içinde belirtilen üçlüler (RDF-star):
```json
{"t": "r", "r": {"s": {...}, "p": {...}, "o": {...}}}
```

`t`: tür belirleyici — `"i"` (IRI), `"l"` (literal), `"r"` (tırnak içinde belirtilmiş üçlü), `"b"` (boş düğüm)
Serileştirme artık `trustgraph.messaging.translators.primitives`'den `TermTranslator` ve `TripleTranslator`'e devrediliyor.

### Diğer serileştirme değişiklikleri

| Alan | v1.8 | v2.1 |
|-------|------|------|
| Meta veri | `metadata.metadata` (alt grafik) | `metadata.root` (basit değer) |
| Grafik gömme varlığı | `entity.vectors` (çoğul) | `entity.vector` (tekil) |
| Belge gömme parçası | `chunk.vectors` + `chunk.chunk` (metin) | `chunk.vector` + `chunk.chunk_id` (ID referansı) |

--

## Uyumsuz Değişiklikler

**`Value`'dan `Term`'e kablo formatı**: Ağ geçidi üzerinden üçlü, gömme veya varlık bağlamı gönderen/alan tüm istemcilerin, yeni Terim formatına güncellenmesi gerekir.
**`objects`'dan `rows`'e yeniden adlandırma**: WebSocket hizmet anahtarı ve içe aktarma anahtarı değiştirildi.
**Meta veri alanı değişikliği**: `metadata.metadata` (serileştirilmiş bir alt grafik), `metadata.root` (basit bir değer) ile değiştirildi.
**Gömme alanı değişiklikleri**: `vectors` (çoğul), `vector` (tekil) haline geldi; belge gömmeleri artık iç içe `chunk` metni yerine `chunk_id`'yi referans alıyor.
**Yeni `/api/v1/document-stream` uç noktası**: Uyumsuz değil, eklemeli.
