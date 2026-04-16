---
layout: default
title: "Açıklanabilirlik CLI Teknik Özellikleri"
parent: "Turkish (Beta)"
---

# Açıklanabilirlik CLI Teknik Özellikleri

> **Beta Translation:** This document was translated via Machine Learning and as such may not be 100% accurate. All non-English languages are currently classified as Beta.

## Durum

Taslak

## Genel Bakış

Bu özellik, TrustGraph'ta açıklanabilirlik verilerini hata ayıklamak ve incelemek için kullanılan CLI araçlarını tanımlar. Bu araçlar, kullanıcıların cevapların nasıl elde edildiğini izlemesini ve kenarlardan kaynak belgelere kadar olan köken zincirini hata ayıklamasını sağlar.

Üç CLI aracı:

1. **`tg-show-document-hierarchy`** - Belge → sayfa → parça → kenar hiyerarşisini gösterir
2. **`tg-list-explain-traces`** - Tüm GraphRAG oturumlarını sorularla birlikte listeler
3. **`tg-show-explain-trace`** - Bir oturum için tam açıklanabilirlik izini gösterir

## Hedefler

**Hata Ayıklama**: Geliştiricilerin belge işleme sonuçlarını incelemesini sağlar
**Denetlenebilirlik**: Herhangi bir çıkarılan gerçeği kaynak belgesine kadar izleme
**Şeffaflık**: GraphRAG'ın bir cevabı tam olarak nasıl elde ettiğini gösterme
**Kullanılabilirlik**: Akıllı varsayılanlarla basit bir CLI arayüzü

## Arka Plan

TrustGraph'un iki köken sistemi vardır:

1. **Çıkarma zamanı kökeni** (bkz. `extraction-time-provenance.md`): Yükleme sırasında belge → sayfa → parça → kenar ilişkilerini kaydeder. `urn:graph:source` adlı grafte saklanır ve `prov:wasDerivedFrom` kullanılarak oluşturulur.

2. **Sorgu zamanı açıklanabilirliği** (bkz. `query-time-explainability.md`): GraphRAG sorguları sırasında soru → keşif → odak → sentez zincirini kaydeder. `urn:graph:retrieval` adlı grafte saklanır.

Mevcut sınırlamalar:
İşleme sonrası belge hiyerarşisini görselleştirmenin kolay bir yolu yok
Açıklanabilirlik verilerini görmek için üçlüleri manuel olarak sorgulamak gerekiyor
Bir GraphRAG oturumunun konsolide bir görünümü yok

## Teknik Tasarım

### Araç 1: tg-show-document-hierarchy

**Amaç**: Bir belge kimliği verildiğinde, türetilen tüm varlıkları gezinerek ve görüntüleyerek.

**Kullanım**:
```bash
tg-show-document-hierarchy "urn:trustgraph:doc:abc123"
tg-show-document-hierarchy --show-content --max-content 500 "urn:trustgraph:doc:abc123"
```

**Argümanlar**:
| Arg | Açıklama |
|-----|-------------|
| `document_id` | Belge URI'si (konumsal) |
| `-u/--api-url` | Ağ geçidi URL'si (varsayılan: `$TRUSTGRAPH_URL`) |
| `-t/--token` | Kimlik doğrulama belirteci (varsayılan: `$TRUSTGRAPH_TOKEN`) |
| `-U/--user` | Kullanıcı Kimliği (varsayılan: `trustgraph`) |
| `-C/--collection` | Koleksiyon (varsayılan: `default`) |
| `--show-content` | Blob/belge içeriğini dahil et |
| `--max-content` | Blob başına maksimum karakter sayısı (varsayılan: 200) |
| `--format` | Çıktı: `tree` (varsayılan), `json` |

**Uygulama**:
1. Üçlüleri sorgula: `?child prov:wasDerivedFrom <document_id>` içinde `urn:graph:source`
2. Her sonucun çocuklarını yinelemeli olarak sorgula
3. Ağaç yapısını oluştur: Belge → Sayfalar → Parçalar
4. Eğer `--show-content` ise, içeriği kütüphaneci API'sinden al
5. Girintili bir ağaç veya JSON olarak göster

**Çıktı Örneği**:
```
Document: urn:trustgraph:doc:abc123
  Title: "Sample PDF"
  Type: application/pdf

  └── Page 1: urn:trustgraph:doc:abc123/p1
      ├── Chunk 0: urn:trustgraph:doc:abc123/p1/c0
      │   Content: "The quick brown fox..." [truncated]
      └── Chunk 1: urn:trustgraph:doc:abc123/p1/c1
          Content: "Machine learning is..." [truncated]
```

### Araç 2: tg-list-explain-traces

**Amaç**: Bir koleksiyondaki tüm GraphRAG oturumlarını (soruları) listelemek.

**Kullanım**:
```bash
tg-list-explain-traces
tg-list-explain-traces --limit 20 --format json
```

**Argümanlar**:
| Arg | Açıklama |
|-----|-------------|
| `-u/--api-url` | Ağ geçidi URL'si |
| `-t/--token` | Yetkilendirme belirteci |
| `-U/--user` | Kullanıcı Kimliği |
| `-C/--collection` | Koleksiyon |
| `--limit` | Maksimum sonuç sayısı (varsayılan: 50) |
| `--format` | Çıktı: `table` (varsayılan), `json` |

**Uygulama**:
1. Sorgu: `?session tg:query ?text` içinde `urn:graph:retrieval`
2. Sorgu zaman damgaları: `?session prov:startedAtTime ?time`
3. Tablo olarak göster

**Çıktı Örneği**:
```
Session ID                                    | Question                        | Time
----------------------------------------------|--------------------------------|---------------------
urn:trustgraph:question:abc123                | What was the War on Terror?    | 2024-01-15 10:30:00
urn:trustgraph:question:def456                | Who founded OpenAI?            | 2024-01-15 09:15:00
```

### Araç 3: tg-show-explain-trace

**Amaç**: Bir GraphRAG oturumu için tam açıklanabilirlik zincirini gösterir.

**Kullanım**:
```bash
tg-show-explain-trace "urn:trustgraph:question:abc123"
tg-show-explain-trace --max-answer 1000 --show-provenance "urn:trustgraph:question:abc123"
```

**Argümanlar**:
| Arg | Açıklama |
|-----|-------------|
| `question_id` | Soru URI'si (konumsal) |
| `-u/--api-url` | Ağ geçidi URL'si |
| `-t/--token` | Kimlik doğrulama belirteci |
| `-U/--user` | Kullanıcı Kimliği |
| `-C/--collection` | Koleksiyon |
| `--max-answer` | Cevap için maksimum karakter sayısı (varsayılan: 500) |
| `--show-provenance` | Kaynak belgelere kadar kenarları izle |
| `--format` | Çıktı: `text` (varsayılan), `json` |

**Uygulama**:
1. `tg:query` özniteliğinden soru metnini al.
2. Keşfi bul: `?exp prov:wasGeneratedBy <question_id>`
3. Odak noktasını bul: `?focus prov:wasDerivedFrom <exploration_id>`
4. Seçilen kenarları al: `<focus_id> tg:selectedEdge ?edge`
5. Her kenar için, `tg:edge` (alıntılanmış üçlü) ve `tg:reasoning`'i al.
6. Sentezi bul: `?synth prov:wasDerivedFrom <focus_id>`
7. Cevabı `tg:document` aracılığıyla kütüphaneciden al.
8. Eğer `--show-provenance` ise, kaynak belgelere kadar kenarları izle.

**Çıktı Örneği**:
```
=== GraphRAG Session: urn:trustgraph:question:abc123 ===

Question: What was the War on Terror?
Time: 2024-01-15 10:30:00

--- Exploration ---
Retrieved 50 edges from knowledge graph

--- Focus (Edge Selection) ---
Selected 12 edges:

  1. (War on Terror, definition, "A military campaign...")
     Reasoning: Directly defines the subject of the query
     Source: chunk → page 2 → "Beyond the Vigilant State"

  2. (Guantanamo Bay, part_of, War on Terror)
     Reasoning: Shows key component of the campaign

--- Synthesis ---
Answer:
  The War on Terror was a military campaign initiated...
  [truncated at 500 chars]
```

## Oluşturulacak Dosyalar

| Dosya | Amaç |
|------|---------|
| `trustgraph-cli/trustgraph/cli/show_document_hierarchy.py` | Araç 1 |
| `trustgraph-cli/trustgraph/cli/list_explain_traces.py` | Araç 2 |
| `trustgraph-cli/trustgraph/cli/show_explain_trace.py` | Araç 3 |

## Değiştirilecek Dosyalar

| Dosya | Değişiklik |
|------|--------|
| `trustgraph-cli/setup.py` | console_scripts girişlerini ekle |

## Uygulama Notları

1. **İkili içerik güvenliği**: UTF-8 ile çözmeyi deneyin; başarısız olursa `[Binary: {size} bytes]` gösterin.
2. **Kısaltma**: `--max-content`/`--max-answer` ile `[truncated]` göstergesine saygı gösterin.
3. **Tırnak işaretli üçlüler**: `tg:edge` önekinden RDF-star formatını ayrıştırın.
4. **Desenler**: `query_graph.py`'dan mevcut CLI desenlerini izleyin.

## Güvenlik Hususları

Tüm sorgular, kullanıcı/koleksiyon sınırlarına saygı gösterir.
`--token` veya `$TRUSTGRAPH_TOKEN` aracılığıyla token kimlik doğrulaması desteklenir.

## Test Stratejisi

Örnek verilerle manuel doğrulama:
```bash
# Load a test document
tg-load-pdf -f test.pdf -c test-collection

# Verify hierarchy
tg-show-document-hierarchy "urn:trustgraph:doc:test"

# Run a GraphRAG query with explainability
tg-invoke-graph-rag --explainable -q "Test question"

# List and inspect traces
tg-list-explain-traces
tg-show-explain-trace "urn:trustgraph:question:xxx"
```

## Referanslar

Sorgu zamanı açıklanabilirlik: `docs/tech-specs/query-time-explainability.md`
Çıkarım zamanı köken bilgisi: `docs/tech-specs/extraction-time-provenance.md`
Mevcut komut satırı örneği: `trustgraph-cli/trustgraph/cli/invoke_graph_rag.py`
