# Çıkarma Kaynağı: Alt Grafik Modeli

## Sorun

Çıkarma zamanı köken bilgisi şu anda her
çıkarılan üçlü için tam bir somutlaştırma oluşturur: benzersiz bir `stmt_uri`, `activity_uri` ve ilgili
PROV-O meta verileri, her bir bilgi parçası için. Bir parça işlenirken
ve bu parça 20 ilişki üretiyorsa, yaklaşık 220 köken bilgisi üçlüsü, bunun üzerine
yaklaşık 20 bilgi üçlüsü bulunur; bu da yaklaşık 10:1'lik bir ek yük demektir.

Bu hem pahalıdır (depolama, indeksleme, iletim) hem de anlamsal olarak
yanlıştır. Her bir parça, tek bir LLM çağrısı ile işlenir ve bu çağrı,
tüm üçlemelerini tek bir işlemde üretir. Mevcut üçleme bazlı model,
20 bağımsız çıkarma olayının yanılsamasını yaratarak bunu gizler.


Ayrıca, dört çıkarma işlemcisinden ikisi (kg-extract-ontology,
kg-extract-agent), hiçbir kaynak bilgisini içermemektedir, bu da denetim
izinde boşluklara neden olmaktadır.

## Çözüm

Her üçlü için yapılan somutlaştırmayı, **bir alt grafik modeli** ile değiştirin: her bir parça çıkarımı için bir köken kaydı, bu parçadan üretilen tüm üçlüler arasında paylaşılan.



### Terminoloji Değişikliği

| Eski | Yeni |
|-----|-----|
| `stmt_uri` (`https://trustgraph.ai/stmt/{uuid}`) | `subgraph_uri` (`https://trustgraph.ai/subgraph/{uuid}`) |
| `statement_uri()` | `subgraph_uri()` |
| `tg:reifies` (1:1, eşlik) | `tg:contains` (1:çok, içerik) |

### Hedef Yapı

Tüm köken bilgisi üçlüleri, `urn:graph:source` adlı grafikte yer alır.

```
# Subgraph contains each extracted triple (RDF-star quoted triples)
<subgraph> tg:contains <<s1 p1 o1>> .
<subgraph> tg:contains <<s2 p2 o2>> .
<subgraph> tg:contains <<s3 p3 o3>> .

# Derivation from source chunk
<subgraph> prov:wasDerivedFrom <chunk_uri> .
<subgraph> prov:wasGeneratedBy <activity> .

# Activity: one per chunk extraction
<activity> rdf:type          prov:Activity .
<activity> rdfs:label        "{component_name} extraction" .
<activity> prov:used         <chunk_uri> .
<activity> prov:wasAssociatedWith <agent> .
<activity> prov:startedAtTime "2026-03-13T10:00:00Z" .
<activity> tg:componentVersion "0.25.0" .
<activity> tg:llmModel       "gpt-4" .          # if available
<activity> tg:ontology        <ontology_uri> .   # if available

# Agent: stable per component
<agent> rdf:type   prov:Agent .
<agent> rdfs:label "{component_name}" .
```

### Hacim Karşılaştırması

N sayıda çıkarılan üçlü üreten bir parça için:

| | Eski (üçlü başına) | Yeni (alt grafik) |
|---|---|---|
| `tg:contains` / `tg:reifies` | N | N |
| Aktivite üçlüleri | ~9 x N | ~9 |
| Ajan üçlüleri | 2 x N | 2 |
| İfade/alt grafik meta verileri | 2 x N | 2 |
| **Toplam kaynak üçlüleri** | **~13N** | **N + 13** |
| **Örnek (N=20)** | **~260** | **33** |

## Kapsam

### Güncellenecek İşlemciler (mevcut kaynak, üçlü başına)

**kg-extract-definitions**
(`trustgraph-flow/trustgraph/extract/kg/definitions/extract.py`)

Şu anda her bir tanım döngüsü içinde `statement_uri()` + `triple_provenance_triples()`'i çağırıyor.


Değişiklikler:
`subgraph_uri()` ve `activity_uri()` oluşturmayı döngüden önce taşıyın
`tg:contains` üçlülerini döngü içinde toplayın
Paylaşılan aktivite/ajan/türetme bloğunu döngüden sonra bir kez yayınlayın

**kg-extract-relationships**
(`trustgraph-flow/trustgraph/extract/kg/relationships/extract.py`)

Tanımlarla aynı desen. Aynı değişiklikler.

### Kaynak Eklenmesi Gereken İşlemciler (şu anda eksik)

**kg-extract-ontology**
(`trustgraph-flow/trustgraph/extract/kg/ontology/extract.py`)

Şu anda, herhangi bir kaynak bilgisi olmadan üçlüler oluşturuluyor. Alt grafik kaynak bilgisini ekleyin.
Aynı kalıbı kullanarak: her parça için bir alt grafik, her çıkarılan üçlü için `tg:contains`.


**kg-extract-agent**
(`trustgraph-flow/trustgraph/extract/kg/agent/extract.py`)

Şu anda, herhangi bir kaynak bilgisi olmadan üçlüler oluşturuluyor. Alt grafik kaynak bilgisini aynı kalıbı kullanarak ekleyin.


### Paylaşılan Kaynak Bilgisi Kütüphanesi Değişiklikleri

**`trustgraph-base/trustgraph/provenance/triples.py`**

`triple_provenance_triples()`'ı `subgraph_provenance_triples()` ile değiştirin.
Yeni fonksiyon, tek bir üçlü yerine çıkarılan üçlülerin bir listesini kabul ediyor.
Her üçlü için bir `tg:contains` oluşturuyor, paylaşılan etkinlik/ajan bloğu.
Eski `triple_provenance_triples()`'ı kaldırın.

**`trustgraph-base/trustgraph/provenance/uris.py`**

`statement_uri()`'ı `subgraph_uri()` ile değiştirin.

**`trustgraph-base/trustgraph/provenance/namespaces.py`**

`TG_REIFIES`'ı `TG_CONTAINS` ile değiştirin.

### Kapsam Dışında

**kg-extract-topics**: eski tip işlemci, şu anda standart akışlarda kullanılmıyor.
  **kg-extract-rows**: satırlar üretiyor, üçlüler değil, farklı bir köken modeline sahip.
**Çalışma zamanı köken bilgisi** (⟦CODE_0⟧): ayrı bir konu.
  model
**Çalışma zamanı veri kaynağı bilgisi** (`urn:graph:retrieval`): ayrı bir konu,
  zaten farklı bir kalıp kullanıyor (soru/keşif/odaklanma/sentez).
**Belge/sayfa/parça kaynağı** (PDF çözücü, parçalayıcı): zaten kullanılıyor.
  `derived_entity_triples()` ki bu, her bir varlık için, her bir üçlü için değil; yani bir sorun yok.
  gereksiz veri sorunu yok.

## Uygulama Notları

### İşlemci Döngüsü Yeniden Yapılandırması

Önce (her üçlü için, ilişkilerde):
```python
for rel in rels:
    # ... build relationship_triple ...
    stmt_uri = statement_uri()
    prov_triples = triple_provenance_triples(
        stmt_uri=stmt_uri,
        extracted_triple=relationship_triple,
        ...
    )
    triples.extend(set_graph(prov_triples, GRAPH_SOURCE))
```

(Alt grafik):
```python
sg_uri = subgraph_uri()

for rel in rels:
    # ... build relationship_triple ...
    extracted_triples.append(relationship_triple)

prov_triples = subgraph_provenance_triples(
    subgraph_uri=sg_uri,
    extracted_triples=extracted_triples,
    chunk_uri=chunk_uri,
    component_name=default_ident,
    component_version=COMPONENT_VERSION,
    llm_model=llm_model,
    ontology_uri=ontology_uri,
)
triples.extend(set_graph(prov_triples, GRAPH_SOURCE))
```

### Yeni Yardımcı İmza

```python
def subgraph_provenance_triples(
    subgraph_uri: str,
    extracted_triples: List[Triple],
    chunk_uri: str,
    component_name: str,
    component_version: str,
    llm_model: Optional[str] = None,
    ontology_uri: Optional[str] = None,
    timestamp: Optional[str] = None,
) -> List[Triple]:
    """
    Build provenance triples for a subgraph of extracted knowledge.

    Creates:
    - tg:contains link for each extracted triple (RDF-star quoted)
    - One prov:wasDerivedFrom link to source chunk
    - One activity with agent metadata
    """
```

### Önemli Değişiklik

Bu, köken modeli için önemli bir değişikliktir. Köken henüz yayınlanmadığı için, herhangi bir geçiş işlemine gerek yoktur. Eski ⟦CODE_0⟧ /
`tg:reifies` kodu tamamen kaldırılabilir.
`statement_uri` kodu tamamen kaldırılabilir.
