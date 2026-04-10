# Çıkarma Zamanı Köken Bilgisi: Kaynak Katmanı

## Genel Bakış

Bu belge, gelecekteki özelliklendirme çalışmaları için çıkarma zamanı köken bilgisi üzerine notları içermektedir. Çıkarma zamanı köken bilgisi kayıtları, verilerin başlangıçta nereden geldiğini, nasıl çıkarıldığını ve dönüştürüldüğünü gösteren "kaynak katmanını" kaydeder.

Bu, ajan muhakemesini kaydeden sorgu zamanı köken bilgisinden (bkz. `query-time-provenance.md`) farklıdır.

## Problem Tanımı

### Mevcut Uygulama

Şu anda köken bilgisi aşağıdaki şekilde çalışmaktadır:
Belge meta verileri, bilgi grafiğinde RDF üçlüleri olarak saklanır.
Bir belge kimliği, meta verileri belgeyle ilişkilendirir, böylece belge grafikte bir düğüm olarak görünür.
Belgelerden kenarlar (ilişkiler/gerçekler) çıkarıldığında, çıkarılan kenarı kaynak belgeye bağlayan bir `subjectOf` ilişkisi bulunur.

### Mevcut Yaklaşımla İlgili Sorunlar

1. **Tekrarlayan meta veri yüklemesi:** Belge meta verileri, o belgeden çıkarılan her üçlü grubuyla birlikte tekrar tekrar paketlenir ve yüklenir. Bu, israf ve gereksizdir - aynı meta veriler her çıkarma çıktısıyla birlikte yük taşımacılığı yapar.

2. **Yüzeysel köken bilgisi:** Mevcut `subjectOf` ilişkisi yalnızca gerçekleri doğrudan en üst düzey belgeyle ilişkilendirir. Dönüşüm zinciri hakkında hiçbir görünürlük yoktur - gerçek hangi sayfadan geldi, hangi parçadan, hangi çıkarma yöntemi kullanıldı.

### İstediğimiz Durum

1. **Meta verileri yalnızca bir kez yükleyin:** Belge meta verileri, her üçlü grubuyla tekrarlanmak yerine, yalnızca bir kez yüklenmeli ve en üst düzey belge düğümüne eklenmelidir.

2. **Zengin köken bilgisi DAG'ı:** Kaynak belgeden başlayarak tüm ara öğeler aracılığıyla çıkarılan gerçeklere kadar olan tüm dönüşüm zincirini yakalayın. Örneğin, bir PDF belgesi dönüşümü:

   ```
   PDF file (source document with metadata)
     → Page 1 (decoded text)
       → Chunk 1
         → Extracted edge/fact (via subjectOf)
         → Extracted edge/fact
       → Chunk 2
         → Extracted edge/fact
     → Page 2
       → Chunk 3
         → ...
   ```

3. **Birleşik depolama:** Kaynak bilgisi DAG'ı, çıkarılan bilgiyle aynı bilgi grafiğinde saklanır. Bu, kaynak bilgisinin, herhangi bir gerçeğin tam kaynak konumuna doğru zincir boyunca geri izlenerek, bilgi gibi aynı şekilde sorgulanabilmesini sağlar.

4. **Sabit Kimlikler:** Her ara öğe (sayfa, parça) grafikte bir düğüm olarak sabit bir kimliğe sahiptir.

5. **Ebeveyn-çocuk bağlantısı:** Türetilmiş belgeler, tutarlı ilişki türleri kullanılarak, en üst düzey kaynak belgeye kadar ebeveynlerine bağlanır.

6. **Hassas gerçek ataması:** Çıkarılan kenarlardaki `subjectOf` ilişkisi, doğrudan ebeveyne (parçaya), en üst düzey belgeye değil, işaret eder. Tam kaynak bilgisi, DAG boyunca yukarı doğru gezilerek elde edilir.

## Kullanım Senaryoları

### KS1: GraphRAG Yanıtlarında Kaynak Ataması

**Senaryo:** Bir kullanıcı bir GraphRAG sorgusu çalıştırır ve ajandan bir yanıt alır.

**Süreç:**
1. Kullanıcı, GraphRAG ajanıyla bir sorgu gönderir.
2. Ajan, bir yanıt oluşturmak için ilgili gerçekleri bilgi grafiğinden alır.
3. Sorgu zamanı kaynak bilgisi spesifikasyonuna göre, ajan yanıtı oluşturan gerçekleri bildirir.
4. Her gerçek, kaynak bilgisi DAG'ı aracılığıyla kaynak parçasına bağlanır.
5. Parçalar, sayfalara bağlanır, sayfalar kaynak belgelere bağlanır.

**Kullanıcı Deneyimi Sonucu:** Arayüz, LLM yanıtını kaynak atamasıyla birlikte gösterir. Kullanıcı şunları yapabilir:
Yanıtı destekleyen gerçekleri görebilir.
Gerçeklerden → parçalara → sayfalara → belgelere kadar ayrıntılara inebilir.
İddiaları doğrulamak için orijinal kaynak belgelerine göz atabilir.
Bir gerçekin tam olarak bir belgenin (hangi sayfa, hangi bölüm) neresinden geldiğini anlayabilir.

**Değer:** Kullanıcılar, yapay zeka tarafından oluşturulan yanıtlara birincil kaynaklara göre doğrulama yaparak güven oluşturabilir ve doğrulama yapabilir.

### KS2: Çıkarma Kalitesinin Hata Ayıklaması

Bir gerçek yanlış görünüyor. Orijinal metni görmek için parça → sayfa → belge yoluyla geriye doğru izleyin. Bu kötü bir çıkarma mıydı, yoksa kaynak mı yanlıştı?

### KS3: Artımlı Yeniden Çıkarma

Kaynak belge güncellendi. Bu belgeden hangi parçalar/gerçekler türetildi? Sadece bunları geçersiz kılın ve yeniden oluşturun, her şeyi yeniden işlemek yerine.

### KS4: Veri Silme / Bilinme Hakkı

Bir kaynak belge kaldırılmalıdır (GDPR, yasal, vb.). Türetilmiş tüm gerçekleri bulmak ve kaldırmak için DAG'ı izleyin.

### KS5: Çatışma Çözümü

İki gerçek birbiriyle çelişiyor. Nedenini anlamak ve hangisine güveneceğe karar vermek için her ikisini de kaynaklarına kadar izleyin (daha yetkili kaynak, daha yeni, vb.).

### KS6: Kaynak Yetki Ağırlığı

Bazı kaynaklar diğerlerinden daha yetkilidir. Gerçekler, kaynak belgelerinin yetki/kalitesine göre ağırlıklandırılabilir veya filtrelenebilir.

### KS7: Çıkarma Boru Hattı Karşılaştırması

Farklı çıkarma yöntemlerinin/sürümlerinin çıktılarını karşılaştırın. Aynı kaynaktan daha iyi gerçekler üreten hangi çıkarıcıydı?

## Entegrasyon Noktaları

### Kütüphaneci

Kütüphaneci bileşeni, zaten benzersiz belge kimlikleriyle belge depolama imkanı sunmaktadır. Kaynak sistemi, bu mevcut altyapıyla entegre olmaktadır.

#### Mevcut Yetenekler (zaten uygulanan)

**Ebeveyn-Çocuk Belge Bağlantısı:**
`parent_id` alanı - `DocumentMetadata` içinde - çocuk belgeyi ebeveyn belgeye bağlar
`document_type` alanı - değerler: `"source"` (orijinal) veya `"extracted"` (türetilmiş)
`add-child-document` API'si - otomatik `document_type = "extracted"` ile çocuk belge oluşturur
`list-children` API'si - bir ebeveyn belgenin tüm çocuklarını alır
Zincirleme silme - bir ebeveynin silinmesi, otomatik olarak tüm çocuk belgelerin silinmesine neden olur

**Belge Tanımlama:**
Belge kimlikleri, istemci tarafından belirtilir (otomatik olarak oluşturulmaz)
Belgeler, Cassandra'da bileşik `(user, document_id)` ile indekslenir
Nesne kimlikleri (UUID'ler), blob depolama için dahili olarak oluşturulur

**Meta Veri Desteği:**
`metadata: list[Triple]` alanı - yapılandırılmış meta veriler için RDF üçlüleri
`title`, `comments`, `tags` - temel belge meta verileri
`time` - zaman damgası, `kind` - MIME türü

**Depolama Mimarisi:**
Meta veriler, Cassandra'da saklanır (`librarian` anahtar alanı, `document` tablo)
İçerik, MinIO/S3 blob depolamasında saklanır (`library` bucket)
Akıllı içerik dağıtımı: 2 MB'den küçük belgeler yerleştirilir, daha büyük belgeler akışla iletilir

#### Önemli Dosyalar

`trustgraph-flow/trustgraph/librarian/librarian.py` - Temel kütüphaneci işlemleri
`trustgraph-flow/trustgraph/librarian/service.py` - Hizmet işlemcisi, belge yükleme
`trustgraph-flow/trustgraph/tables/library.py` - Cassandra tablo deposu
`trustgraph-base/trustgraph/schema/services/library.py` - Şema tanımları

#### Giderilmesi Gereken Eksiklikler

Kütüphaneci, temel yapı taşlarına sahip olmasına rağmen şu anda:
1. Ebeveyn-çocuk bağlantısı tek düzeylidir - çok düzeyli DAG (Yönlendirilmiş Döngüsel Grafik) gezinme yardımcıları yoktur
2. Standart bir ilişki türü sözlüğü yoktur (örneğin, `derivedFrom`, `extractedFrom`)
3. Kaynak meta verileri (çıkarma yöntemi, güven, parça konumu) standartlaştırılmamıştır
4. Bir gerçeğe geri dönen kaynaklara kadar tüm kaynak zincirini izlemek için bir sorgu API'si yoktur

## Uçtan Uca Akış Tasarımı

Boru hattındaki her işlemci, tutarlı bir kalıbı izler:
Yukarı akıştan belge kimliğini alır
Kütüphaneciden içeriği alır
Çocuk öğeler oluşturur
Her çocuk için: kütüphaneciye kaydeder, grafiğe bir kenar yollar, kimliği aşağı akışa iletir

### İşlem Akışları

Belge türüne bağlı olarak iki akış vardır:

#### PDF Belge Akışı

```
┌─────────────────────────────────────────────────────────────────────────┐
│ Librarian (initiate processing)                                         │
│   1. Emit root document metadata to knowledge graph (once)              │
│   2. Send root document ID to PDF extractor                             │
└─────────────────────────────────────────────────────────────────────────┘
                                    │
                                    ▼
┌─────────────────────────────────────────────────────────────────────────┐
│ PDF Extractor (per page)                                                │
│   1. Fetch PDF content from librarian using document ID                 │
│   2. Extract pages as text                                              │
│   3. For each page:                                                     │
│      a. Save page as child document in librarian (parent = root doc)   │
│      b. Emit parent-child edge to knowledge graph                       │
│      c. Send page document ID to chunker                                │
└─────────────────────────────────────────────────────────────────────────┘
                                    │
                                    ▼
┌─────────────────────────────────────────────────────────────────────────┐
│ Chunker (per chunk)                                                     │
│   1. Fetch page content from librarian using document ID                │
│   2. Split text into chunks                                             │
│   3. For each chunk:                                                    │
│      a. Save chunk as child document in librarian (parent = page)      │
│      b. Emit parent-child edge to knowledge graph                       │
│      c. Send chunk document ID + chunk content to next processor        │
└─────────────────────────────────────────────────────────────────────────┘
                                    │
                                    ▼
          ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─
          Post-chunker optimization: messages carry both
          chunk ID (for provenance) and content (to avoid
          librarian round-trip). Chunks are small (2-4KB).
          ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─
                                    │
                                    ▼
┌─────────────────────────────────────────────────────────────────────────┐
│ Knowledge Extractor (per chunk)                                         │
│   1. Receive chunk ID + content directly (no librarian fetch needed)   │
│   2. Extract facts/triples and embeddings from chunk content            │
│   3. For each triple:                                                   │
│      a. Emit triple to knowledge graph                                  │
│      b. Emit reified edge linking triple → chunk ID (edge pointing     │
│         to edge - first use of reification support)                     │
│   4. For each embedding:                                                │
│      a. Emit embedding with its entity ID                               │
│      b. Link entity ID → chunk ID in knowledge graph                   │
└─────────────────────────────────────────────────────────────────────────┘
```

#### Metin Belgesi Akışı

Metin belgeleri, PDF ayıklayıcıyı atlayarak doğrudan parçalayıcıya (chunker) gider:

```
┌─────────────────────────────────────────────────────────────────────────┐
│ Librarian (initiate processing)                                         │
│   1. Emit root document metadata to knowledge graph (once)              │
│   2. Send root document ID directly to chunker (skip PDF extractor)    │
└─────────────────────────────────────────────────────────────────────────┘
                                    │
                                    ▼
┌─────────────────────────────────────────────────────────────────────────┐
│ Chunker (per chunk)                                                     │
│   1. Fetch text content from librarian using document ID                │
│   2. Split text into chunks                                             │
│   3. For each chunk:                                                    │
│      a. Save chunk as child document in librarian (parent = root doc) │
│      b. Emit parent-child edge to knowledge graph                       │
│      c. Send chunk document ID + chunk content to next processor        │
└─────────────────────────────────────────────────────────────────────────┘
                                    │
                                    ▼
┌─────────────────────────────────────────────────────────────────────────┐
│ Knowledge Extractor                                                     │
│   (same as PDF flow)                                                    │
└─────────────────────────────────────────────────────────────────────────┘
```

Elde edilen DAG, bir seviye daha kısadır:

```
PDF:  Document → Pages → Chunks → Triples/Embeddings
Text: Document → Chunks → Triples/Embeddings
```

Tasarım, her iki durumu da destekler çünkü parçalayıcı (chunker), girdisini genel olarak işler; aldığı belge kimliği, kaynak belge mi yoksa bir sayfa mı olduğunu dikkate almadan, bunu üst belge olarak kullanır.

### Metaveri Şeması (PROV-O)

Kaynak metaverileri, W3C PROV-O ontolojisini kullanır. Bu, standart bir sözlük sağlar ve çıkarılan verilerin gelecekteki imzalanmasını/doğrulanmasını mümkün kılar.

#### PROV-O Temel Kavramları

| PROV-O Tipi | TrustGraph Kullanımı |
|-------------|------------------|
| `prov:Entity` | Belge, Sayfa, Parça, Üçlü, Gömme |
| `prov:Activity` | Çıkarma işlemlerinin örnekleri |
| `prov:Agent` | TG bileşenleri (PDF ayıklayıcı, parçalayıcı, vb.) ve versiyonları |

#### PROV-O İlişkileri

| Özne | Anlamı | Örnek |
|-----------|---------|---------|
| `prov:wasDerivedFrom` | Başka bir varlıktan türetilen varlık | Sayfa, Belgeden Türetildi |
| `prov:wasGeneratedBy` | Bir etkinlik tarafından oluşturulan varlık | Sayfa, PDFÇıkarmaEtkinliği Tarafından Oluşturuldu |
| `prov:used` | Bir etkinliğin bir varlığı girdi olarak kullandığı | PDFÇıkarmaEtkinliği, Belgeyi Kullandı |
| `prov:wasAssociatedWith` | Bir etkinliğin bir ajan tarafından gerçekleştirildiği | PDFÇıkarmaEtkinliği, tg:PDFÇıkarıcı ile İlişkiliydi |

#### Her Seviyedeki Metaveriler

**Kaynak Belge (Librarian tarafından oluşturulan):**
```
doc:123 a prov:Entity .
doc:123 dc:title "Research Paper" .
doc:123 dc:source <https://example.com/paper.pdf> .
doc:123 dc:date "2024-01-15" .
doc:123 dc:creator "Author Name" .
doc:123 tg:pageCount 42 .
doc:123 tg:mimeType "application/pdf" .
```

**Sayfa (PDF Çıkarıcı tarafından oluşturulmuştur):**
```
page:123-1 a prov:Entity .
page:123-1 prov:wasDerivedFrom doc:123 .
page:123-1 prov:wasGeneratedBy activity:pdf-extract-456 .
page:123-1 tg:pageNumber 1 .

activity:pdf-extract-456 a prov:Activity .
activity:pdf-extract-456 prov:used doc:123 .
activity:pdf-extract-456 prov:wasAssociatedWith tg:PDFExtractor .
activity:pdf-extract-456 tg:componentVersion "1.2.3" .
activity:pdf-extract-456 prov:startedAtTime "2024-01-15T10:30:00Z" .
```

**Parça (Chunker tarafından üretilen):**
```
chunk:123-1-1 a prov:Entity .
chunk:123-1-1 prov:wasDerivedFrom page:123-1 .
chunk:123-1-1 prov:wasGeneratedBy activity:chunk-789 .
chunk:123-1-1 tg:chunkIndex 1 .
chunk:123-1-1 tg:charOffset 0 .
chunk:123-1-1 tg:charLength 2048 .

activity:chunk-789 a prov:Activity .
activity:chunk-789 prov:used page:123-1 .
activity:chunk-789 prov:wasAssociatedWith tg:Chunker .
activity:chunk-789 tg:componentVersion "1.0.0" .
activity:chunk-789 tg:chunkSize 2048 .
activity:chunk-789 tg:chunkOverlap 200 .
```

**Üçlü (Knowledge Extractor tarafından üretildi):**
```
# The extracted triple (edge)
entity:JohnSmith rel:worksAt entity:AcmeCorp .

# Subgraph containing the extracted triples
subgraph:001 tg:contains <<entity:JohnSmith rel:worksAt entity:AcmeCorp>> .
subgraph:001 prov:wasDerivedFrom chunk:123-1-1 .
subgraph:001 prov:wasGeneratedBy activity:extract-999 .

activity:extract-999 a prov:Activity .
activity:extract-999 prov:used chunk:123-1-1 .
activity:extract-999 prov:wasAssociatedWith tg:KnowledgeExtractor .
activity:extract-999 tg:componentVersion "2.1.0" .
activity:extract-999 tg:llmModel "claude-3" .
activity:extract-999 tg:ontology <http://example.org/ontologies/business-v1> .
```

**Gömme (vektör deposunda saklanır, üçlü depolamada değil):**

Gömme verileri, RDF üçlüleri olarak değil, meta verilerle birlikte vektör deposunda saklanır. Her gömme kaydı şunları içerir:

| Alan | Açıklama | Örnek |
|-------|-------------|---------|
| vektör | Gömme vektörü | [0.123, -0.456, ...] |
| varlık | Gömmenin temsil ettiği düğüm URI'si | `entity:JohnSmith` |
| chunk_id | Kaynak parça (kaynak) | `chunk:123-1-1` |
| model | Kullanılan gömme modeli | `text-embedding-ada-002` |
| component_version | TG gömme sürümü | `1.0.0` |

`entity` alanı, gömmeyi bilgi grafiğine (düğüm URI'si) bağlar. `chunk_id` alanı, orijinal belgeye kadar DAG üzerinde izlemeyi sağlayarak, kaynak parçaya ilişkin bilgileri sağlar.

#### TrustGraph İsim Alanı Genişletmeleri

Çıkarma ile ilgili meta veriler için `tg:` isim alanı altındaki özel önekler:

| Önek | Alan | Açıklama |
|-----------|--------|-------------|
| `tg:contains` | Alt Grafik | Bu çıkarma alt grafiğindeki bir üçlüye işaret eder |
| `tg:pageCount` | Belge | Kaynak belgedeki toplam sayfa sayısı |
| `tg:mimeType` | Belge | Kaynak belgenin MIME türü |
| `tg:pageNumber` | Sayfa | Kaynak belgedeki sayfa numarası |
| `tg:chunkIndex` | Parça | Ebeveyn içindeki parçanın indeksi |
| `tg:charOffset` | Parça | Ebeveyn metnindeki karakter ofseti |
| `tg:charLength` | Parça | Parçanın karakter cinsinden uzunluğu |
| `tg:chunkSize` | Etkinlik | Yapılandırılmış parça boyutu |
| `tg:chunkOverlap` | Etkinlik | Parçalar arasındaki yapılandırılmış örtüşme |
| `tg:componentVersion` | Etkinlik | TG bileşeninin sürümü |
| `tg:llmModel` | Etkinlik | Çıkarma için kullanılan LLM |
| `tg:ontology` | Etkinlik | Çıkarma için kullanılan ontoloji URI'si |
| `tg:embeddingModel` | Etkinlik | Gömme için kullanılan model |
| `tg:sourceText` | İfade | Bir üçlünün çıkarıldığı tam metin |
| `tg:sourceCharOffset` | İfade | Kaynak metnin başladığı parça içindeki karakter ofseti |
| `tg:sourceCharLength` | İfade | Kaynak metnin karakter cinsinden uzunluğu |

#### Sözlük Başlatma (Her Koleksiyon İçin)

Bilgi grafiği, ontolojiye bağımlı olmayan ve başlangıçta boş olan bir yapıdır. Bir koleksiyona PROV-O kaynak verilerini ilk kez yazarken, tüm sınıflar ve önekler için RDF etiketleriyle sözlük başlatılmalıdır. Bu, sorgularda ve kullanıcı arayüzünde okunabilir bir görüntüleme sağlar.

**PROV-O Sınıfları:**
```
prov:Entity rdfs:label "Entity" .
prov:Activity rdfs:label "Activity" .
prov:Agent rdfs:label "Agent" .
```

**PROV-O Yüklemleri:**
```
prov:wasDerivedFrom rdfs:label "was derived from" .
prov:wasGeneratedBy rdfs:label "was generated by" .
prov:used rdfs:label "used" .
prov:wasAssociatedWith rdfs:label "was associated with" .
prov:startedAtTime rdfs:label "started at" .
```

**TrustGraph Önermeleri:**
```
tg:contains rdfs:label "contains" .
tg:pageCount rdfs:label "page count" .
tg:mimeType rdfs:label "MIME type" .
tg:pageNumber rdfs:label "page number" .
tg:chunkIndex rdfs:label "chunk index" .
tg:charOffset rdfs:label "character offset" .
tg:charLength rdfs:label "character length" .
tg:chunkSize rdfs:label "chunk size" .
tg:chunkOverlap rdfs:label "chunk overlap" .
tg:componentVersion rdfs:label "component version" .
tg:llmModel rdfs:label "LLM model" .
tg:ontology rdfs:label "ontology" .
tg:embeddingModel rdfs:label "embedding model" .
tg:sourceText rdfs:label "source text" .
tg:sourceCharOffset rdfs:label "source character offset" .
tg:sourceCharLength rdfs:label "source character length" .
```

**Uygulama notu:** Bu sözlük başlatma işleminin idempotent olması gerekir - yani, çoğaltmalar oluşturmadan birden çok kez çalıştırılabilir. Bu işlem, bir koleksiyondaki ilk belge işleme sırasında veya ayrı bir koleksiyon başlatma adımı olarak tetiklenebilir.

#### Alt Parça Kaynağı (İdeal)

Daha ayrıntılı bir kaynak bilgisi için, bir üçlemenin bir parça içinde tam olarak nereden çıkarıldığı kaydedilmesi değerli olacaktır. Bu, şunları sağlar:

Kullanıcı arayüzünde (UI) tam kaynak metninin vurgulanması
Çıkarma doğruluğunun kaynağa göre doğrulanması
Çıkarma kalitesinin cümle düzeyinde hata ayıklanması

**Konum takibi ile örnek:**
```
# The extracted triple
entity:JohnSmith rel:worksAt entity:AcmeCorp .

# Subgraph with sub-chunk provenance
subgraph:001 tg:contains <<entity:JohnSmith rel:worksAt entity:AcmeCorp>> .
subgraph:001 prov:wasDerivedFrom chunk:123-1-1 .
subgraph:001 tg:sourceText "John Smith has worked at Acme Corp since 2019" .
subgraph:001 tg:sourceCharOffset 1547 .
subgraph:001 tg:sourceCharLength 46 .
```

**Metin aralığı içeren örnek (alternatif):**
```
subgraph:001 tg:contains <<entity:JohnSmith rel:worksAt entity:AcmeCorp>> .
subgraph:001 prov:wasDerivedFrom chunk:123-1-1 .
subgraph:001 tg:sourceRange "1547-1593" .
subgraph:001 tg:sourceText "John Smith has worked at Acme Corp since 2019" .
```

**Uygulama hususları:**

LLM tabanlı çıkarma, doğal olarak karakter konumlarını sağlamayabilir.
LLM'den çıkarılan üçlülerin yanı sıra kaynak cümleyi/ifadeyi de döndürmesi istenebilir.
Alternatif olarak, çıkarılan varlıkları kaynak metne geri eşleştirmek için bir işlem sonrası adımı uygulanabilir.
Çıkarma karmaşıklığı ile kaynak doğruluğu arasındaki denge.
Yapılandırılmış çıkarma yöntemleriyle serbest biçimli LLM çıkarma yöntemlerinden daha kolay uygulanabilir olabilir.

Bu, iddialı bir hedef olarak işaretlenmiştir - temel parça düzeyindeki kaynak bilgisi öncelikle uygulanmalı, alt parça takibi ise uygulanabilirse gelecekteki bir iyileştirme olarak düşünülmelidir.

### Çift Depolama Modeli

Kaynak bilgisi DAG'ı, belgeler boru hattından geçerken kademeli olarak oluşturulur:

| Depo | Neler Saklanır | Amaç |
|-------|---------------|---------|
| Kütüphaneci | Belge içeriği + ebeveyn-çocuk bağlantıları | İçerik alma, kaskad silme |
| Bilgi Grafiği | Ebeveyn-çocuk kenarları + meta veri | Kaynak bilgisi sorguları, gerçek ataması |

Her iki depo da aynı DAG yapısını korur. Kütüphaneci içeriği saklar; grafik ilişkileri saklar ve gezinme sorgularını sağlar.

### Temel Tasarım Prensipleri

1. **Belge Kimliği akış birimi olarak** - İşleyiciler içeriği değil, kimlikleri iletir. İçerik gerektiğinde kütüphaneciden alınır.

2. **Kaynakta bir kez yayınla** - Meta veri, işleme başladığında grafiğe bir kez yazılır, aşağı akışta tekrarlanmaz.

3. **Tutarlı işlemci kalıbı** - Her işlemci aynı alım/alma/üretme/kaydetme/yayınlama/ileri gönderme kalıbını izler.

4. **Kademeli DAG oluşturma** - Her işlemci DAG'a kendi seviyesini ekler. Tam kaynak bilgisi zinciri kademeli olarak oluşturulur.

5. **Parça sonrasındaki optimizasyon** - Parçalama işleminden sonra, mesajlar hem kimliği hem de içeriği taşır. Parçalar küçüktür (2-4KB), bu nedenle içeriği dahil etmek, kütüphaneciye yapılan gereksiz geri dönüşleri önlerken kimlik yoluyla kaynak bilgisini korur.

## Uygulama Görevleri

### Kütüphaneci Değişiklikleri

#### Mevcut Durum

Belge işleme işlemini başlatarak belge kimliğini ilk işlemciye gönderir.
Üçlü depoyla bağlantı yok - meta veri, çıkarma çıktılarıyla birlikte paketlenir.
`add-child-document` tek seviyeli ebeveyn-çocuk bağlantıları oluşturur.
`list-children` yalnızca hemen alt öğeleri döndürür.

#### Gerekli Değişiklikler

**1. Yeni arayüz: Üçlü depo bağlantısı**

Kütüphaneci, işleme başlatıldığında belge meta veri kenarlarını doğrudan bilgi grafiğine yayınlamalıdır.
Kütüphaneci hizmetine üçlü depo istemci/yayınlayıcısı ekleyin.
İşleme başlatıldığında: kök belge meta verilerini grafik kenarları olarak (tek seferlik) yayınlayın.

**2. Belge türü sözlüğü**

Alt belgeler için `document_type` değerlerini standartlaştırın:
`source` - orijinal olarak yüklenen belge
`page` - kaynaktan (PDF, vb.) çıkarılan sayfa
`chunk` - sayfadan veya kaynaktan türetilen metin parçası

#### Arayüz Değişiklikleri Özeti

| Arayüz | Değişiklik |
|-----------|--------|
| Üçlü depo | Yeni dışa dönük bağlantı - belge meta veri kenarlarını yayınlayın |
| İşleme başlatma | Meta veriyi grafiğe yayınlayın, belge kimliğini iletmeden önce |

### PDF Çıkarma Değişiklikleri

#### Mevcut Durum

Belge içeriğini alır (veya büyük belgeleri akış halinde alır)
PDF sayfalarından metin çıkarır
Sayfa içeriğini parçalayıcıya iletir
Kütüphaneci veya üçlü depo ile etkileşimde bulunmaz

#### Gerekli Değişiklikler

**1. Yeni arayüz: Kütüphaneci istemcisi**

PDF çıkarıcı, her sayfayı kütüphanecide bir alt belge olarak kaydetmelidir.
PDF çıkarıcı hizmetine kütüphaneci istemcisi ekleyin
Her sayfa için: ebeveyn = kök belge kimliği ile `add-child-document`'yi çağırın

**2. Yeni arayüz: Üçlü depo bağlantısı**

PDF çıkarıcı, ebeveyn-çocuk kenarlarını bilgi grafiğine yayınlamalıdır.
Üçlü depo istemci/yayınlayıcısı ekleyin
Her sayfa için: sayfa belgesini ebeveyn belgeyle ilişkilendiren bir kenar yayınlayın

**3. Çıktı biçimini değiştirin**

Sayfa içeriğini doğrudan iletmek yerine, sayfa belge kimliğini iletin.
Chunker, içeriği kütüphaneden kimliği kullanarak alacaktır.

#### Arayüz Değişiklikleri Özeti

| Arayüz | Değişiklik |
|-----------|--------|
| Kütüphane | Yeni dışa aktarma - alt belgeleri kaydet |
| Üçlü depolama | Yeni dışa aktarma - ebeveyn-çocuk kenarlarını yayınla |
| Çıkış mesajı | İçerikten belge kimliğine geçiş |

### Chunker Değişiklikleri

#### Mevcut Durum

Sayfa/metin içeriğini alır
Parçalara böler
Parça içeriğini sonraki işleme birimlerine iletir
Kütüphane veya üçlü depolamayla etkileşimde bulunmaz

#### Gerekli Değişiklikler

**1. Giriş işleme şeklini değiştirin**

İçerik yerine belge kimliğini alın, kütüphaneden alın.
Chunker hizmetine kütüphane istemcisini ekleyin
Belge kimliğini kullanarak sayfa içeriğini alın

**2. Yeni arayüz: Kütüphane istemcisi (yazma)**

Her parçayı kütüphanede bir alt belge olarak kaydedin.
Her parça için: ebeveyn = sayfa belge kimliği ile `add-child-document`'ı çağırın

**3. Yeni arayüz: Üçlü depolama bağlantısı**

Ebeveyn-çocuk kenarlarını bilgi grafiğine yayınlayın.
Üçlü depolama istemcisini/yayınlayıcısını ekleyin
Her parça için: parça belgesini sayfa belgesine bağlayan kenarı yayınlayın

**4. Çıkış biçimini değiştirin**

Hem parça belge kimliğini hem de parça içeriğini iletin (parça işleminden sonraki optimizasyon).
Sonraki işleme birimleri, köken bilgisi için kimliği ve çalışmak için içeriği alır

#### Arayüz Değişiklikleri Özeti

| Arayüz | Değişiklik |
|-----------|--------|
| Giriş mesajı | İçerikten belge kimliğine geçiş |
| Kütüphane | Yeni dışa aktarma (okuma + yazma) - içeriği alın, alt belgeleri kaydedin |
| Üçlü depolama | Yeni dışa aktarma - ebeveyn-çocuk kenarlarını yayınla |
| Çıkış mesajı | İçerikten kimliğe + içeriğe geçiş |

### Bilgi Çıkarıcı Değişiklikleri

#### Mevcut Durum

Parça içeriğini alır
Üçlüleri ve gömme değerlerini çıkarır
Üçlü depolamaya ve gömme depolamaya yayınlar
`subjectOf` ilişkisi, en üst düzey belgeye (parçaya değil) işaret eder

#### Gerekli Değişiklikler

**1. Giriş işleme şeklini değiştirin**

Parça belge kimliğini içeriğin yanında alın.
Köken bağlama için parça kimliğini kullanın (içerik zaten optimizasyon kapsamında dahil edilmiştir)

**2. Üçlü kökeni güncelleyin**

Çıkarılan üçlüleri parçaya (en üst düzey belgeye değil) bağlayın.
Kenara işaret eden bir kenar oluşturmak için yeniden tanımlama kullanın
`subjectOf` ilişkisi: üçlü → parça belge kimliği
Mevcut yeniden tanımlama desteğinin ilk kullanımı

**3. Gömme kökenini güncelleyin**

Gömme varlık kimliklerini parçaya bağlayın.
Kenar yayınlayın: gömme varlık kimliği → parça belge kimliği

#### Arayüz Değişiklikleri Özeti

| Arayüz | Değişiklik |
|-----------|--------|
| Giriş mesajı | Parça kimliğini + içeriği bekleyin (sadece içeriği değil) |
| Üçlü depolama | Üçlü → parça kökeni için yeniden tanımlamayı kullanın |
| Gömme kökeni | Varlık kimliğini → parça kimliğine bağlayın |

## Referanslar

Sorgu zamanı kökeni: `docs/tech-specs/query-time-provenance.md`
Köken modellemesi için PROV-O standardı
Bilgi grafiğindeki mevcut kaynak meta verileri (denetlenmesi gerekir)
