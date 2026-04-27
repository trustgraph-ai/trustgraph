---
layout: default
title: "Veri Çıkarma Akışları"
parent: "Turkish (Beta)"
---

# Veri Çıkarma Akışları

> **Beta Translation:** This document was translated via Machine Learning and as such may not be 100% accurate. All non-English languages are currently classified as Beta.

Bu belge, verilerin TrustGraph veri çıkarma işlem hattı üzerinden nasıl aktığını, belge gönderiminden başlayarak bilgi depolarına kaydedilmesine kadar olan süreci açıklamaktadır.

## Genel Bakış

```
┌──────────┐     ┌─────────────┐     ┌─────────┐     ┌────────────────────┐
│ Librarian│────▶│ PDF Decoder │────▶│ Chunker │────▶│ Knowledge          │
│          │     │ (PDF only)  │     │         │     │ Extraction         │
│          │────────────────────────▶│         │     │                    │
└──────────┘     └─────────────┘     └─────────┘     └────────────────────┘
                                          │                    │
                                          │                    ├──▶ Triples
                                          │                    ├──▶ Entity Contexts
                                          │                    └──▶ Rows
                                          │
                                          └──▶ Document Embeddings
```

## İçerik Depolama

### Blob Depolama (S3/Minio)

Belge içeriği, S3 uyumlu blob depolama alanında saklanır:
Yol formatı: `doc/{object_id}`, burada object_id bir UUID'dir.
Tüm belge türleri burada saklanır: kaynak belgeler, sayfalar, parçalar.

### Metaveri Depolama (Cassandra)

Cassandra'da saklanan belge metaverileri şunları içerir:
Belge ID'si, başlık, tür (MIME türü).
Blob depolama alanına `object_id` referansı.
Alt belgelere (sayfalar, parçalar) ait `parent_id`.
`document_type`: "kaynak", "sayfa", "parça", "cevap".

### İçerik vs. Akış Eşiği

İçerik iletimi, boyuta dayalı bir strateji kullanır:
**< 2MB**: İçerik, mesaj içinde (base64 ile kodlanmış) yer alır.
**≥ 2MB**: Yalnızca `document_id` gönderilir; işlemci, kütüphaneci API'si aracılığıyla içeriği alır.

## 1. Aşama: Belge Gönderimi (Kütüphaneci)

### Giriş Noktası

Belgeler, kütüphanecinin `add-document` işlemi aracılığıyla sisteme girer:
1. İçerik, blob depolama alanına yüklenir.
2. Cassandra'da bir metaveri kaydı oluşturulur.
3. Belge ID'si döndürülür.

### Çıkarım Tetikleme

`add-processing` işlemi, çıkarımı tetikler:
`document_id`, `flow` (işlem hattı ID'si) ve `collection` (hedef depolama alanı) belirtir.
Kütüphanecinin `load_document()` işlemi, içeriği alır ve akış giriş kuyruğuna yayınlar.

### Şema: Belge

```
Document
├── metadata: Metadata
│   ├── id: str              # Document identifier
│   ├── user: str            # Tenant/user ID
│   ├── collection: str      # Target collection
│   └── metadata: list[Triple]  # (largely unused, historical)
├── data: bytes              # PDF content (base64, if inline)
└── document_id: str         # Librarian reference (if streaming)
```

**Yönlendirme**: `kind` alanına göre:
`application/pdf` → `document-load` kuyruğu → PDF Kod Çözücü
`text/plain` → `text-load` kuyruğu → Parçalayıcı

## 2. Aşama: PDF Kod Çözücü

PDF belgelerini metin sayfalarına dönüştürür.

### İşlem

1. İçeriği al (doğrudan `data` veya `document_id` üzerinden kütüphaneciden)
2. Sayfaları PyPDF kullanarak çıkar
3. Her sayfa için:
   Kütüphanecide alt belge olarak kaydet (`{doc_id}/p{page_num}`)
   Kaynak üçlülerini yayınla (sayfa, belgeden türetilmiştir)
   Parçalayıcıya ilet

### Şema: TextDocument

```
TextDocument
├── metadata: Metadata
│   ├── id: str              # Page URI (e.g., https://trustgraph.ai/doc/xxx/p1)
│   ├── user: str
│   ├── collection: str
│   └── metadata: list[Triple]
├── text: bytes              # Page text content (if inline)
└── document_id: str         # Librarian reference (e.g., "doc123/p1")
```

## 3. Aşama: Parçalayıcı (Chunker)

Metni, yapılandırılmış boyutta parçalara ayırır.

### Parametreler (akışa bağımlı olarak yapılandırılabilir)

`chunk_size`: Karakter cinsinden hedef parça boyutu (varsayılan: 2000)
`chunk_overlap`: Parçalar arasındaki örtüşme (varsayılan: 100)

### İşlem

1. Metin içeriğini alın (doğrudan veya kütüphaneci aracılığıyla)
2. Özyinelemeli karakter ayırıcı kullanarak parçalara ayırın
3. Her parça için:
   Kütüphanecide alt belge olarak kaydedin (`{parent_id}/c{index}`)
   Kaynak bilgilerini yayınlayın (parça, sayfadan/belgeden türetilmiştir)
   Çıkarma işleme modüllerine yönlendirin

### Şema: Parça (Chunk)

```
Chunk
├── metadata: Metadata
│   ├── id: str              # Chunk URI
│   ├── user: str
│   ├── collection: str
│   └── metadata: list[Triple]
├── chunk: bytes             # Chunk text content
└── document_id: str         # Librarian chunk ID (e.g., "doc123/p1/c3")
```

### Belge Kimlik Hiyerarşisi

Alt belgeler, kimlik içinde kendi kökenlerini kodlar:
Kaynak: `doc123`
Sayfa: `doc123/p5`
Sayfadan parça: `doc123/p5/c2`
Metinden parça: `doc123/c2`

## 4. Aşama: Bilgi Çıkarımı

Kullanılabilir çoklu çıkarma kalıpları, akış yapılandırması tarafından seçilir.

### Kalıp A: Temel GraphRAG

İki paralel işlemci:

**kg-extract-definitions**
Giriş: Parça
Çıkış: Üçlüler (varlık tanımları), Varlık Bağlamları
Çıkarır: varlık etiketleri, tanımlar

**kg-extract-relationships**
Giriş: Parça
Çıkış: Üçlüler (ilişkiler), Varlık Bağlamları
Çıkarır: özne-yüklem-nesne ilişkileri

### Kalıp B: Ontoloji Odaklı (kg-extract-ontology)

Giriş: Parça
Çıkış: Üçlüler, Varlık Bağlamları
Çıkarımı yönlendirmek için yapılandırılmış bir ontoloji kullanır

### Kalıp C: Ajan Tabanlı (kg-extract-agent)

Giriş: Parça
Çıkış: Üçlüler, Varlık Bağlamları
Çıkarım için ajan çerçevesini kullanır

### Kalıp D: Satır Çıkarımı (kg-extract-rows)

Giriş: Parça
Çıkış: Satırlar (üçlüler değil, yapılandırılmış veri)
Yapılandırılmış kayıtları çıkarmak için şema tanımını kullanır

### Şema: Üçlüler

```
Triples
├── metadata: Metadata
│   ├── id: str
│   ├── user: str
│   ├── collection: str
│   └── metadata: list[Triple]  # (set to [] by extractors)
└── triples: list[Triple]
    └── Triple
        ├── s: Term              # Subject
        ├── p: Term              # Predicate
        ├── o: Term              # Object
        └── g: str | None        # Named graph
```

### Şema: Varlık Bağlamları

```
EntityContexts
├── metadata: Metadata
└── entities: list[EntityContext]
    └── EntityContext
        ├── entity: Term         # Entity identifier (IRI)
        ├── context: str         # Textual description for embedding
        └── chunk_id: str        # Source chunk ID (provenance)
```

### Şema: Satırlar

```
Rows
├── metadata: Metadata
├── row_schema: RowSchema
│   ├── name: str
│   ├── description: str
│   └── fields: list[Field]
└── rows: list[dict[str, str]]   # Extracted records
```

## 5. Aşama: Gömme (Embedding) Oluşturma

### Grafik Gömme (Graph Embeddings)

Varlık bağlamlarını vektör gömmelerine dönüştürür.

**Süreç:**
1. Varlık Bağlamlarını Alın
2. Bağlam metniyle gömme hizmetini çağırın
3. GrafikGömme'leri Çıktılayın (varlık → vektör eşlemesi)

**Şema: GrafikGömme (GraphEmbeddings)**

```
GraphEmbeddings
├── metadata: Metadata
└── entities: list[EntityEmbeddings]
    └── EntityEmbeddings
        ├── entity: Term         # Entity identifier
        ├── vector: list[float]  # Embedding vector
        └── chunk_id: str        # Source chunk (provenance)
```

### Belge Gömme (Document Embeddings)

Parça metnini doğrudan vektör gömmelerine dönüştürür.

**Süreç:**
1. Parçayı Al
2. Parça metniyle gömme hizmetini çağır
3. DocumentEmbeddings çıktısını ver

**Şema: DocumentEmbeddings**

```
DocumentEmbeddings
├── metadata: Metadata
└── chunks: list[ChunkEmbeddings]
    └── ChunkEmbeddings
        ├── chunk_id: str        # Chunk identifier
        └── vector: list[float]  # Embedding vector
```

### Satır Gömme (Row Embeddings)

Satır indeks alanlarını vektör gömmelerine dönüştürür.

**İşlem:**
1. Satırları Al
2. Yapılandırılmış indeks alanlarını göm
3. Satır vektör deposuna çıktı ver

## 6. Aşama: Depolama

### Üçlü Depo (Triple Store)

Gelen: Üçlüler
Depolama: Cassandra (varlık odaklı tablolar)
İsimlendirilmiş grafikler, temel bilgiyi köken bilgisinden ayırır:
  `""` (varsayılan): Temel bilgi gerçekleri
  `urn:graph:source`: Çıkarma kökeni
  `urn:graph:retrieval`: Sorgu zamanı açıklanabilirliği

### Vektör Deposu (Grafik Gömme)

Gelen: GrafikGömme (GraphEmbeddings)
Depolama: Qdrant, Milvus veya Pinecone
Dizin: Varlık IRI'si ile
Metaveri: Köken için chunk_id

### Vektör Deposu (Belge Gömme)

Gelen: BelgeGömme (DocumentEmbeddings)
Depolama: Qdrant, Milvus veya Pinecone
Dizin: chunk_id ile

### Satır Deposu (Row Store)

Gelen: Satırlar
Depolama: Cassandra
Şema odaklı tablo yapısı

### Satır Vektör Deposu

Gelen: Satır gömmeleri
Depolama: Vektör Veritabanı
Dizin: Satır indeks alanları ile

## Metaveri Alanı Analizi

### Aktif Olarak Kullanılan Alanlar

| Alan | Kullanım |
|-------|-------|
| `metadata.id` | Belge/parça tanımlayıcı, günlükleme, köken |
| `metadata.user` | Çoklu kiracılık, depolama yönlendirme |
| `metadata.collection` | Hedef koleksiyon seçimi |
| `document_id` | Kütüphaneci referansı, köken bağlantısı |
| `chunk_id` | İşlem hattı boyunca köken takibi |

<<<<<<< HEAD
### Potansiyel Olarak Gereksiz Alanlar

| Alan | Durum |
|-------|--------|
| `metadata.metadata` | Tüm çıkarıcılar tarafından `[]` olarak ayarlanır; belge düzeyindeki metaveri artık gönderim zamanında kütüphaneci tarafından işlenir |
=======
### Kaldırılan Alanlar

| Alan | Durum |
|-------|--------|
| `metadata.metadata` | `Metadata` sınıfından kaldırıldı. Belge düzeyindeki metaveri üçlüleri artık kütüphaneci tarafından doğrudan üçlü depoya gönderim zamanında gönderilir, çıkarma hattı üzerinden taşınmaz. |
>>>>>>> e3bcbf73 (The metadata field (list of triples) in the pipeline Metadata class)

### Bayt Alanı Modeli

Tüm içerik alanları (`data`, `text`, `chunk`) `bytes`'tür, ancak tüm işlemciler tarafından hemen UTF-8 dizelerine kod çözülür. İşlemci tarafından ham bayt kullanılmaz.

## Akış Yapılandırması

Akışlar harici olarak tanımlanır ve kütüphaneci aracılığıyla yapılandırma hizmetinden sağlanır. Her akış şunları belirtir:

Giriş kuyrukları (`text-load`, `document-load`)
İşlemci zinciri
Parametreler (parça boyutu, çıkarma yöntemi, vb.)

Örnek akış modelleri:
`pdf-graphrag`: PDF → Kod Çözücü → Parçalayıcı → Tanımlar + İlişkiler → Gömme
`text-graphrag`: Metin → Parçalayıcı → Tanımlar + İlişkiler → Gömme
`pdf-ontology`: PDF → Kod Çözücü → Parçalayıcı → Ontoloji Çıkarma → Gömme
`text-rows`: Metin → Parçalayıcı → Satır Çıkarma → Satır Deposu
