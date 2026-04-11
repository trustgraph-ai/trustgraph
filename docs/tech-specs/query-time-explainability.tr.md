# Sorgu Zamanı Açıklanabilirlik

## Durum

Uygulandı

## Genel Bakış

Bu özellik, GraphRAG'ın sorgu yürütülmesi sırasında açıklanabilirlik verilerini nasıl kaydettiğini ve ilettiğini açıklamaktadır. Amaç, nihai cevaptan başlayarak, seçilen kenarlara ve kaynak belgelere kadar tam bir izlenebilirlik sağlamaktır.

Sorgu zamanı açıklanabilirliği, GraphRAG boru hattının akıl yürütme sırasında neler yaptığını yakalar. Bu, bilginin nereden geldiğini kaydeden, çıkarma zamanı köken bilgilerine bağlanır.

## Terminoloji

| Terim | Tanım |
|------|------------|
| **Açıklanabilirlik** | Bir sonucun nasıl elde edildiğinin kaydı |
| **Oturum** | Tek bir GraphRAG sorgu yürütmesi |
| **Kenar Seçimi** | Akıl yürütmeyle ilgili kenarların LLM tarafından seçilmesi |
| **Köken Zinciri** | Kenar → parça → sayfa → belge yolu |

## Mimari

### Açıklanabilirlik Akışı

```
GraphRAG Query
    │
    ├─► Session Activity
    │       └─► Query text, timestamp
    │
    ├─► Retrieval Entity
    │       └─► All edges retrieved from subgraph
    │
    ├─► Selection Entity
    │       └─► Selected edges with LLM reasoning
    │           └─► Each edge links to extraction provenance
    │
    └─► Answer Entity
            └─► Reference to synthesized response (in librarian)
```

### İki Aşamalı GraphRAG İşlem Hattı

1. **Kenar Seçimi**: LLM, alt grafikten ilgili kenarları seçer ve her biri için bir gerekçe sunar.
2. **Sentez**: LLM, yalnızca seçilen kenarlardan cevap oluşturur.

Bu ayrım, açıklanabilirliği sağlar - hangi kenarların katkıda bulunduğunu tam olarak biliyoruz.

### Depolama

Açıklanabilirlik üçlüleri, yapılandırılabilir bir koleksiyonda saklanır (varsayılan: `explainability`).
Kaynak ilişkileri için PROV-O ontolojisi kullanılır.
Kenar referansları için RDF-star yeniden tanımlaması.
Cevap içeriği, kütüphaneci hizmetinde saklanır (satır içi değil - çok büyük).

### Gerçek Zamanlı Akış

Açıklanabilirlik olayları, sorgu yürütüldüğü sırada istemciye akış olarak gönderilir:

1. Oturum oluşturuldu → olay gönderildi.
2. Kenarlar alındı → olay gönderildi.
3. Gerekçeyle birlikte kenarlar seçildi → olay gönderildi.
4. Cevap oluşturuldu → olay gönderildi.

İstemci, `explain_id` ve `explain_collection`'i tam ayrıntıları almak için kullanır.

## URI Yapısı

Tüm URI'ler, UUID'lerle birlikte `urn:trustgraph:` ad alanını kullanır:

| Varlık | URI Kalıbı |
|--------|-------------|
| Oturum | `urn:trustgraph:session:{uuid}` |
| Alma | `urn:trustgraph:prov:retrieval:{uuid}` |
| Seçim | `urn:trustgraph:prov:selection:{uuid}` |
| Cevap | `urn:trustgraph:prov:answer:{uuid}` |
| Kenar Seçimi | `urn:trustgraph:prov:edge:{uuid}:{index}` |

## RDF Modeli (PROV-O)

### Oturum Etkinliği

```turtle
<session-uri> a prov:Activity ;
    rdfs:label "GraphRAG query session" ;
    prov:startedAtTime "2024-01-15T10:30:00Z" ;
    tg:query "What was the War on Terror?" .
```

### Veri Alma Varlığı

```turtle
<retrieval-uri> a prov:Entity ;
    rdfs:label "Retrieved edges" ;
    prov:wasGeneratedBy <session-uri> ;
    tg:edgeCount 50 .
```

### Seçim Varlığı

```turtle
<selection-uri> a prov:Entity ;
    rdfs:label "Selected edges" ;
    prov:wasDerivedFrom <retrieval-uri> ;
    tg:selectedEdge <edge-sel-0> ;
    tg:selectedEdge <edge-sel-1> .

<edge-sel-0> tg:edge << <s> <p> <o> >> ;
    tg:reasoning "This edge establishes the key relationship..." .
```

### Cevap Varlığı

```turtle
<answer-uri> a prov:Entity ;
    rdfs:label "GraphRAG answer" ;
    prov:wasDerivedFrom <selection-uri> ;
    tg:document <urn:trustgraph:answer:{uuid}> .
```

`tg:document`, kütüphaneci hizmetinde saklanan cevabı referans alır.

## Ad Alanı Sabitleri

`trustgraph-base/trustgraph/provenance/namespaces.py` içinde tanımlanmıştır:

| Sabit | URI |
|----------|-----|
| `TG_QUERY` | `https://trustgraph.ai/ns/query` |
| `TG_EDGE_COUNT` | `https://trustgraph.ai/ns/edgeCount` |
| `TG_SELECTED_EDGE` | `https://trustgraph.ai/ns/selectedEdge` |
| `TG_EDGE` | `https://trustgraph.ai/ns/edge` |
| `TG_REASONING` | `https://trustgraph.ai/ns/reasoning` |
| `TG_CONTENT` | `https://trustgraph.ai/ns/content` |
| `TG_DOCUMENT` | `https://trustgraph.ai/ns/document` |

## GraphRagResponse Şeması

```python
@dataclass
class GraphRagResponse:
    error: Error | None = None
    response: str = ""
    end_of_stream: bool = False
    explain_id: str | None = None
    explain_collection: str | None = None
    message_type: str = ""  # "chunk" or "explain"
    end_of_session: bool = False
```

### Mesaj Türleri

| mesaj_türü | Amaç |
|--------------|---------|
| `chunk` | Yanıt metni (akış veya son) |
| `explain` | IRI referansıyla açıklanabilirlik olayı |

### Oturum Yaşam Döngüsü

1. Birden fazla `explain` mesajı (oturum, alma, seçim, yanıt)
2. Birden fazla `chunk` mesajı (akış yanıtı)
3. `end_of_session=True` ile birlikte son `chunk`

## Kenar Seçim Formatı

LLM, seçilen kenarlarla birlikte JSONL döndürür:

```jsonl
{"id": "edge-hash-1", "reasoning": "This edge shows the key relationship..."}
{"id": "edge-hash-2", "reasoning": "Provides supporting evidence..."}
```

`id`, `(labeled_s, labeled_p, labeled_o)`'nin `edge_id()` tarafından hesaplanan bir karma değeridir.

## URI'nin Korunması

### Sorun

GraphRAG, LLM'ye okunabilir etiketler gösterir, ancak açıklanabilirlik, köken takibi için orijinal URI'lere ihtiyaç duyar.

### Çözüm

`get_labelgraph()`, şunları döndürür:
`labeled_edges`: LLM için `(label_s, label_p, label_o)` listesi
`uri_map`: `edge_id(labels)` → `(uri_s, uri_p, uri_o)` eşlemesini içeren sözlük

Açıklanabilirlik verilerini saklarken, `uri_map`'dan gelen URI'ler kullanılır.

## Köken Takibi

### Kaynaktan Kenara

Seçilen kenarlar, kaynak belgelere kadar izlenebilir:

1. İçeren alt grafiği sorgulayın: `?subgraph tg:contains <<s p o>>`
2. Kök belgeye kadar `prov:wasDerivedFrom` zincirini izleyin
3. Zincirdeki her adım: parça → sayfa → belge

### Cassandra Tırnaklı Üçlü Desteği

Cassandra sorgu hizmeti, tırnaklı üçlüleri eşleştirmeyi destekler:

```python
# In get_term_value():
elif term.type == TRIPLE:
    return serialize_triple(term.triple)
```

Bu, şu tür sorguları mümkün kılar:
```
?subgraph tg:contains <<http://example.org/s http://example.org/p "value">>
```

## CLI Kullanımı

```bash
tg-invoke-graph-rag --explainable -q "What was the War on Terror?"
```

### Çıktı Formatı

```
[session] urn:trustgraph:session:abc123

[retrieval] urn:trustgraph:prov:retrieval:abc123

[selection] urn:trustgraph:prov:selection:abc123
    Selected 12 edge(s)
      Edge: (Guantanamo, definition, A detention facility...)
        Reason: Directly connects Guantanamo to the War on Terror
        Source: Chunk 1 → Page 2 → Beyond the Vigilant State

[answer] urn:trustgraph:prov:answer:abc123

Based on the provided knowledge statements...
```

### Özellikler

Sorgu sırasında gerçek zamanlı açıklanabilirlik olayları
`rdfs:label` aracılığıyla kenar bileşenleri için etiket çözümü
`prov:wasDerivedFrom` aracılığıyla kaynak zinciri takibi
Tekrarlanan sorguları önlemek için etiket önbelleği

## Uygulanan Dosyalar

| Dosya | Amaç |
|------|---------|
| `trustgraph-base/trustgraph/provenance/uris.py` | URI oluşturucular |
| `trustgraph-base/trustgraph/provenance/namespaces.py` | RDF ad alanı sabitleri |
| `trustgraph-base/trustgraph/provenance/triples.py` | Üçlü oluşturucular |
| `trustgraph-base/trustgraph/schema/services/retrieval.py` | GraphRagResponse şeması |
| `trustgraph-flow/trustgraph/retrieval/graph_rag/graph_rag.py` | URI korumasıyla temel GraphRAG |
| `trustgraph-flow/trustgraph/retrieval/graph_rag/rag.py` | Kütüphaneci entegrasyonlu hizmet |
| `trustgraph-flow/trustgraph/query/triples/cassandra/service.py` | Tırnaklı üçlü sorgu desteği |
| `trustgraph-cli/trustgraph/cli/invoke_graph_rag.py` | Açıklanabilirlik gösterimiyle CLI |

## Referanslar

PROV-O (W3C Provenance Ontology): https://www.w3.org/TR/prov-o/
RDF-star: https://w3c.github.io/rdf-star/
Çıkarma zamanı kökeni: `docs/tech-specs/extraction-time-provenance.md`
