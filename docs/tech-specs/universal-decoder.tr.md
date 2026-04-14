---
layout: default
title: "Evrensel Belge Kodlayıcı"
parent: "Turkish (Beta)"
---

# Evrensel Belge Kodlayıcı

> **Beta Translation:** This document was translated via Machine Learning and as such may not be 100% accurate. All non-English languages are currently classified as Beta.

## Başlık

`unstructured` tarafından desteklenen evrensel belge kodlayıcı — tüm kaynak konumlarını, uçtan uca izlenebilirlik için bilgi grafiği meta verisi olarak kaydederek, tam kökenli ve kütüphaneci entegrasyonu ile herhangi bir yaygın belge formatını tek bir hizmet aracılığıyla işleyin.




## Sorun

TrustGraph şu anda PDF'ye özel bir çözücüye (decoder) sahip. Ek
formatları (DOCX, XLSX, HTML, Markdown, düz metin, PPTX, vb.) desteklemek,
ya her format için yeni bir çözücü yazmayı veya evrensel bir çıkarma
kütüphanesini kullanmayı gerektirir. Her formatın farklı bir yapısı vardır — bazıları sayfa tabanlıyken, bazıları değildir — ve köken zinciri, çıkarılan her metin parçasının orijinal
belgede nereden geldiğini kaydetmelidir.

## Yaklaşım
## Yaklaşım

### Kütüphane: `unstructured`

`unstructured.partition.auto.partition()`'ı kullanın, bu, formatı otomatik olarak algılar
MIME türünden veya dosya uzantısından yapılandırılmış öğeleri ayıklar
(Başlık, AnlatıMetni, Tablo, Madde, vb.). Her öğe aşağıdaki bilgileri içerir:


`page_number` (sayfa tabanlı formatlar için, örneğin PDF, PPTX)
`element_id` (her öğe için benzersiz)
`coordinates` (PDF'ler için sınırlayıcı kutu)
`text` (çıkarılan metin içeriği)
`category` (öğe türü: Başlık, AnlatıMetni, Tablo, vb.)

### Öğe Türleri

`unstructured`, belgelerden türlenmiş öğeleri çıkarır. Her öğenin bir kategorisi ve ilişkili meta verileri vardır:


**Metin öğeleri:**
`Title` — bölüm başlıkları
`NarrativeText` — ana metin paragrafları
`ListItem` — madde işaretli/numaralandırılmış liste öğeleri
`Header`, `Footer` — sayfa başlıkları/altbilgileri
`FigureCaption` — şekiller/görseller için başlıklar
`Formula` — matematiksel ifadeler
`Address`, `EmailAddress` — iletişim bilgileri
`CodeSnippet` — kod blokları (markdown'dan)

**Tablolar:**
`Table` — yapılandırılmış tablo verileri. `unstructured`, hem
  `element.text` (düz metin) hem de `element.metadata.text_as_html`
  (satırlar, sütunlar ve başlıklar korunmuş, tam HTML `<table>`) sağlar.
  Açık tablo yapısına sahip formatlar (DOCX, XLSX, HTML) için,
  çıkarma işlemi son derece güvenilirdir. PDF'ler için, tablo tespiti,
  düzen analizini içeren `hi_res` stratejisine bağlıdır.

**Görseller:**
`Image` — düzen analizi yoluyla algılanan yerleşik görseller (gerektirir
  `hi_res` stratejisi). `extract_image_block_to_payload=True` ile,
  görüntü verilerini `element.metadata.image_base64` içinde base64 olarak döndürür.
  Görüntüden elde edilen OCR metni `element.text` içinde mevcuttur.

### Tablo İşleme

Tablolar, birincil bir çıktı türüdür. Kod çözücü, bir `Table`
öğesiyle karşılaştığında, düz metne dönüştürmek yerine HTML yapısını korur.
Bu, aşağı akış LLM çıkarıcısının, yapılandırılmış verileri içeren
tablo verilerinden daha iyi bilgi almasını sağlar.

Sayfa/bölüm metni aşağıdaki gibi birleştirilir:
Metin öğeleri: yeni satırlarla birleştirilmiş düz metin
Tablo öğeleri: `text_as_html`'dan HTML tablo işaretlemesi, bir
  `<table>` işaretinin içine sarılır, böylece LLM tabloları, anlatıdan
ayırt edebilir.
Örneğin, bir başlık, paragraf ve tablo içeren bir sayfa şu şekilde üretilir:

```
Financial Overview

Revenue grew 15% year-over-year driven by enterprise adoption.

<table>
<tr><th>Quarter</th><th>Revenue</th><th>Growth</th></tr>
<tr><td>Q1</td><td>$12M</td><td>12%</td></tr>
<tr><td>Q2</td><td>$14M</td><td>17%</td></tr>
</table>
```

Bu, tablo yapısını parçalara ayırarak ve çıkarma işlemine aktararak korur.
Bu sayede, LLM (Büyük Dil Modeli), sütun hizalamasını boşluklardan tahmin etmek yerine, doğrudan yapılandırılmış hücrelerden ilişkileri çıkarabilir.


### Resim İşleme


Görüntüler çıkarılır ve kütüphanede alt belgeler olarak saklanır.
`document_type="image"` ile ve `urn:image:{uuid}` kimlik numarasına sahip. Bunlar
`tg:Image` türündeki köken bilgisi üçlülerini içerir ve bunlar, ebeveynlerine bağlanmıştır.
sayfa/bölüm, `prov:wasDerivedFrom` aracılığıyla. Görüntü meta verileri (koordinatlar,
boyutlar, element_id) provenians kısmında kaydedilir.

**Önemli olarak, resimler, TextDocument çıktıları olarak YAYINLANMAMAKTIR.**
Bunlar yalnızca saklanır; parçalayıcıya veya herhangi bir metin işleme
işlem hattına gönderilmez. Bu kasıtlıdır:

1. Henüz bir resim işleme işlem hattı yoktur (görsel model entegrasyonu
   gelecekteki bir çalışmadır)
2. Base64 resim verilerini veya OCR parçalarını metin çıkarma
   işlem hattına vermek, hatalı KG üçlüleri üretir.

Görüntüler de birleştirilmiş sayfa metninden hariç tutulur; herhangi bir `Image`
öğesi, bir sayfa/bölüm için öğe metinlerini birleştirirken sessizce atlanır.
Kaynak zinciri, görüntülerin var olduğunu ve belgede nerede
bulunduğunu kaydeder, böylece gelecekte bir görüntü işleme hattı tarafından
belgenin yeniden yüklenmesi olmadan da alınabilirler.

#### Gelecek çalışmalar

`tg:Image` varlıklarını, açıklama,
  diyagram yorumlama veya grafik veri çıkarma için bir görsel modele yönlendirin.
Görüntü açıklamalarını, standart parçalama/çıkarma işlem hattına beslenen metin alt belgeleri olarak kaydedin.
  Çıkarılan bilgileri, kaynak görüntüleriyle köken bilgisi aracılığıyla ilişkilendirin.


### Bölüm Stratejileri

Sayfa tabanlı formatlar (PDF, PPTX, XLSX) için, öğeler her zaman önce sayfa/slayt/sayfa içinde gruplandırılır.
Sayfa tabanlı olmayan formatlar (DOCX, HTML, Markdown,
vb.) için, kodlayıcının belgeyi bölümlere ayırmak için bir stratejiye ihtiyacı vardır.
Bu, çalışma zamanında `--section-strategy` aracılığıyla yapılandırılabilir.

Her strateji, `unstructured` öğelerinin listesi üzerinde bir gruplama fonksiyonudur.
Çıktı, öğe gruplarının bir listesidir; geri kalan işlem hattı (metin birleştirme, kütüphane depolama, köken, TextDocument
oluşturma) stratejiden bağımsız olarak aynıdır.


#### `whole-document` (varsayılan)

Tüm belgeyi tek bir bölüm olarak yayınlayın. Bölme işlemlerinin tümü, sonraki
parçalayıcı tarafından gerçekleştirilir.

En basit yaklaşım, iyi bir başlangıç noktası.
Büyük dosyalar için çok büyük TextDocument'ler oluşturabilir, ancak parçalayıcı
  bunu yönetir.
Her bölüm için maksimum bağlam istediğinizde en iyisidir.

#### `heading`

Başlık öğelerinde (`Title`) bölün. Her bölüm, bir başlık ve bir sonraki
aynı veya daha yüksek seviyedeki başlığa kadar olan tüm içeriktir. İç içe
başlıklar, iç içe bölümler oluşturur.

Konuyla ilgili tutarlı birimler oluşturur.
Yapılandırılmış belgeler (raporlar, kılavuzlar, teknik özellikler) için iyi çalışır.
Çıkarma LLM'sine, içerikle birlikte başlık bağlamı sağlar.
Başlık bulunamazsa `whole-document`'a geri döner.

#### `element-type`

Eleman türü önemli ölçüde değiştiğinde bölmeyi yapın — özellikle,
anlatısal metin ile tablolar arasındaki geçişlerde yeni bir bölüm başlatın.
Aynı geniş kategoriye ait ardışık öğeler (metin, metin, metin veya
tablo, tablo) gruplandırılır.

Tabloları bağımsız bölümler olarak tutar
Karışık içerikli belgeler için uygundur (veri tabloları içeren raporlar)
Tablolar, özel bir çıkarma işlemine tabi tutulur

#### `count`

Bir bölümdeki öğe sayısını sabit bir sayıda gruplandırın. ⟦CODE_0⟧ aracılığıyla yapılandırılabilir (varsayılan: 20).
`--section-element-count` (varsayılan: 20).

Basit ve öngörülebilir
Belge yapısını dikkate almaz
Yedek çözüm olarak veya deneme yapmak için kullanışlıdır

#### `size`

Öğeleri, bir karakter limiti dolana kadar biriktirin, ardından yeni bir bölüm başlatın. Öğeler arasındaki sınırları dikkate alır; hiçbir zaman bir öğenin ortasında bölünme yapmaz.
⟦CODE_0⟧ gibi yer tutucuları veya ⟦URL_0⟧ gibi URL'leri çevirmeyin; bunları olduğu gibi bırakın.
`--section-max-size` aracılığıyla yapılandırılabilir (varsayılan: 4000 karakter).

Yaklaşık olarak homojen bölüm boyutları üretir.
Eleman sınırlarına saygı gösterir (aşağıdaki parçalayıcıdan farklı olarak).
Yapı ve boyut kontrolü arasında iyi bir denge sağlar.
Tek bir eleman limiti aşarsa, kendi bölümü haline gelir.

#### Sayfa tabanlı format etkileşimi

Sayfa tabanlı formatlar için, sayfa gruplandırması her zaman önceliklidir.
Bölüm stratejileri, isteğe bağlı olarak, çok büyükse (örneğin, devasa bir tablo içeren bir PDF sayfası) bir sayfa *içinde* uygulanabilir, bu durum ⟦CODE_0⟧ ile kontrol edilir (varsayılan: false). Yanlış olduğunda, her sayfa boyuttan bağımsız olarak her zaman bir bölümdür.

`--section-within-pages` (varsayılan: false).


### Biçim Algılama

Kodlayıcının, belgeyi ⟦CODE_0⟧'ın ⟦CODE_1⟧'ine iletebilmesi için belgenin MIME türünü bilmesi gerekir. İki yol:
`unstructured`'ın `partition()`'i.

**Kütüphaneci yolu** (`document_id` ayarı): belge meta verilerini alın.
  Öncelikle kütüphaneciden belge meta verilerini alın — bu, `kind` (mime türü) değerini verir.
  Ardından belge içeriğini alın.
  İki kütüphaneci çağrısı, ancak meta veri alma işlemi hafiftir.
**Satır içi yol** (geriye dönük uyumluluk, `data` ayarı): mesaj üzerinde herhangi bir meta veri bulunmamaktadır.
  Biçimi tespit etmek için `python-magic`'ı kullanın.
  Bu, içerik baytlarından biçimi algılamak için bir yedek yöntemdir.

`Document` şemasına herhangi bir değişiklik yapılmasına gerek yok — kütüphaneci zaten MIME türünü saklar.


### Mimari

Tek bir `universal-decoder` hizmeti:

1. Bir `Document` mesajı alır (doğrudan veya kütüphaneci referansı aracılığıyla)
2. Kütüphaneci yoluysa: belge meta verilerini alır (MIME türünü alır), ardından
   içeriği alır. Doğrudan yol ise: içeriğin baytlarından formatı algılar.
3. Öğeleri çıkarmak için `partition()`'ı çağırır
4. Öğeleri gruplandırır: sayfa tabanlı formatlar için sayfalara göre, sayfa dışı formatlar için yapılandırılmış
   bölüm stratejisine göre
5. Her sayfa/bölüm için:
   Bir `urn:page:{uuid}` veya `urn:section:{uuid}` kimliği oluşturur
   Sayfa metnini birleştirir: anlatı düz metin olarak, tablolar HTML olarak,
     resimler atlanır
   Sayfa metnindeki her öğe için karakter ofsetlerini hesaplar
   Kütüphaneciye alt belge olarak kaydeder
   Konumsal meta verilerle birlikte kaynak üçlüleri yayınlar
   Parçalama için `TextDocument`'ı aşağı akışa gönderir
6. Her resim öğesi için:
   Bir `urn:image:{uuid}` kimliği oluşturur
   Resim verilerini kütüphaneciye alt belge olarak kaydeder
   Kaynak üçlülerini yayınlar (sadece saklanır, aşağı akışa gönderilmez)

### Biçimlendirme İşlemi

| Biçim   | MIME Tipi                          | Sayfa Tabanlı | Notlar                          |
|----------|------------------------------------|------------|--------------------------------|
| PDF      | application/pdf                    | Evet        | Sayfaya göre gruplandırma              |
| DOCX     | application/vnd.openxmlformats...  | Hayır         | Bölüm stratejisi kullanır          |
| PPTX     | application/vnd.openxmlformats...  | Evet        | Slayda göre gruplandırma             |
| XLSX/XLS | application/vnd.openxmlformats...  | Evet        | Sayfaya göre gruplandırma             |
| HTML     | text/html                          | Hayır         | Bölüm stratejisi kullanır          |
| Markdown | text/markdown                      | Hayır         | Bölüm stratejisi kullanır          |
| Düz Metin    | text/plain                         | Hayır         | Bölüm stratejisi kullanır          |
| CSV      | text/csv                           | Hayır         | Bölüm stratejisi kullanır          |
| RST      | text/x-rst                         | Hayır         | Bölüm stratejisi kullanır          |
| RTF      | application/rtf                    | Hayır         | Bölüm stratejisi kullanır          |
| ODT      | application/vnd.oasis...           | Hayır         | Bölüm stratejisi kullanır          |
| TSV      | text/tab-separated-values          | Hayır         | Bölüm stratejisi kullanır          |

### Kaynak Veri Meta Verileri

Her sayfa/bölüm öğesi, köken bilgisi olarak konum bilgisi meta verilerini kaydeder.
`GRAPH_SOURCE` içindeki üçlüler, KG üçlülerinden tam bir izlenebilirlik sağlamaktadır.
Kaynak belge konumlarına geri dönme.

#### Mevcut alanlar (zaten `derived_entity_triples` içinde)

`page_number` — sayfa/tablo/slayt numarası (1'den başlayarak, yalnızca sayfa tabanlı)
`char_offset` — bu sayfa/bölümün,
  tam belge metni içindeki karakter ofseti
`char_length` — bu sayfa/bölümün metninin karakter uzunluğu

#### Yeni alanlar (`derived_entity_triples`'ı genişletin)

`mime_type` — orijinal belge formatı (örneğin, `application/pdf`)
`element_types` — `unstructured` öğelerinden oluşan virgülle ayrılmış liste
  bu sayfada/bölümde bulunan kategoriler (örneğin, "Başlık,AnlatıMetni,Tablo")
`table_count` — bu sayfada/bölümdeki tablo sayısı
`image_count` — bu sayfada/bölümdeki resim sayısı

Bunlar, yeni TG ad alanı özniteliklerini gerektirir:

```
TG_SECTION_TYPE  = "https://trustgraph.ai/ns/Section"
TG_IMAGE_TYPE    = "https://trustgraph.ai/ns/Image"
TG_ELEMENT_TYPES = "https://trustgraph.ai/ns/elementTypes"
TG_TABLE_COUNT   = "https://trustgraph.ai/ns/tableCount"
TG_IMAGE_COUNT   = "https://trustgraph.ai/ns/imageCount"
```

Görüntü URN şeması: `urn:image:{uuid}`

(`TG_MIME_TYPE` zaten mevcut.)

#### Yeni varlık türü

Sayfa formatı olmayan (DOCX, HTML, Markdown, vb.) belgeler için,
kodlayıcı, belgeyi sayfalara ayırmak yerine tek bir birim olarak yayınladığında,
varlığa yeni bir tür atanır:

```
TG_SECTION_TYPE = "https://trustgraph.ai/ns/Section"
```

Bu, sorgulama sırasında kökeni belirlerken bölümleri sayfalardan ayırır:

| Varlık   | Tür                        | Ne zaman kullanılır                             |
|----------|-----------------------------|----------------------------------------|
| Belge   | `tg:Document`               | Orijinal yüklenen dosya                 |
| Sayfa    | `tg:Page`                   | Sayfaya dayalı formatlar (PDF, PPTX, XLSX)   |
| Bölüm   | `tg:Section`                | Sayfaya dayalı olmayan formatlar (DOCX, HTML, MD, vb.) |
| Resim    | `tg:Image`                  | Gömülü resimler (saklanan, işlenmeyen) |
| Parça    | `tg:Chunk`                  | Parçalayıcının çıktısı                      |
| Alt Grafik | `tg:Subgraph`              | KG çıkarma çıktısı                   |

Tür, kodlayıcı tarafından, sayfalara göre gruplandırılıp gruplandırılmadığına veya tüm belge bölümünün gönderilip gönderilmediğine bağlı olarak belirlenir. ⟦CODE_0⟧ elde edilir.
veya tüm belge bölümünün gönderilip gönderilmediğine bağlı olarak belirlenir. `derived_entity_triples` kazanır.
isteğe bağlı bir `section` boolean parametresi — doğru olduğunda, bu, varlığı belirtir.
`tg:Section` olarak yazılmış, `tg:Page` yerine.

#### Tam kaynak zinciri

```
KG triple
  → subgraph (extraction provenance)
    → chunk (char_offset, char_length within page)
      → page/section (page_number, char_offset, char_length within doc, mime_type, element_types)
        → document (original file in librarian)
```

Her bağlantı, `GRAPH_SOURCE` adlı grafikte tanımlanan üçlülerden oluşan bir kümedir.

### Hizmet Yapılandırması

Komut satırı argümanları:

```
--strategy              Partitioning strategy: auto, hi_res, fast (default: auto)
--languages             Comma-separated OCR language codes (default: eng)
--section-strategy      Section grouping: whole-document, heading, element-type,
                        count, size (default: whole-document)
--section-element-count Elements per section for 'count' strategy (default: 20)
--section-max-size      Max chars per section for 'size' strategy (default: 4000)
--section-within-pages  Apply section strategy within pages too (default: false)
```

Ayrıca standart `FlowProcessor` ve kütüphaneci kuyruk argümanlarını da içerir.

### Akış Entegrasyonu

Evrensel kod çözücü, işleme akışında mevcut PDF kod çözücünün bulunduğu aynı konumu işgal eder:


```
Document → [universal-decoder] → TextDocument → [chunker] → Chunk → ...
```

Aşağıdakileri kaydeder:
`input` tüketici (Belge şeması)
`output` üretici (MetinBelgesi şeması)
`triples` üretici (Üçlüler şeması)
Kütüphaneci isteği/yanıtı (veri çekme ve alt belge depolama için)

### Dağıtım

Yeni kapsayıcı: `trustgraph-flow-universal-decoder`
Bağımlılık: `unstructured[all-docs]` (PDF, DOCX, PPTX vb. içerir)
Mevcut PDF çözücüyü tamamlayıcı olarak veya onun yerine çalışabilir.
  akış yapılandırması
Mevcut PDF çözücü, ortamlar için kullanılabilir durumda kalacaktır.
  `unstructured` bağımlılıkları çok ağır.

### Değişiklikler

| Bileşen                        | Değişiklik                                         |
|------------------------------|-------------------------------------------------|
| `provenance/namespaces.py`   | `TG_SECTION_TYPE`, `TG_IMAGE_TYPE`, `TG_ELEMENT_TYPES`, `TG_TABLE_COUNT`, `TG_IMAGE_COUNT` ekleyin |
| `provenance/triples.py`      | `mime_type`, `element_types`, `table_count`, `image_count` argümanlarını ekleyin |
| `provenance/__init__.py`     | Yeni sabit değerleri dışa aktarın                            |
| Yeni: `decoding/universal/`   | Yeni bir kod çözücü hizmet modülü                      |
| `setup.cfg` / `pyproject`    | `unstructured[all-docs]` bağımlılığını ekleyin         |
| Docker                       | Yeni bir konteyner imajı                             |
| Akış tanımları             | Evrensel kod çözücüyü belge girişi olarak kullanın        |

### Değişmeyenler

Chunker (MetinBelgesi'ni alır, önceki gibi çalışır)
Aşağı akış ayıklayıcıları (Parçayı alır, değişmeden)
Kütüphaneci (çocuk belgeleri saklar, değişmeden)
Şema (Belge, MetinBelgesi, Parça değişmeden)
Sorgu zamanı köken bilgisi (değişmeden)

## Riskler

`unstructured[all-docs]`, önemli bağımlılıklara sahiptir (poppler, tesseract,
  libreoffice, bazı formatlar için). Container imajı daha büyük olacaktır.
  Çözüm: OCR/ofis bağımlılıkları olmadan `[light]`'ın bir varyantını sunun.
Bazı formatlar, zayıf metin çıkarma sonuçları verebilir (OCR uygulanmamış PDF'ler,
  OCR, karmaşık XLSX düzenleri). Çözüm: yapılandırılabilir `strategy`
  parametresi ve mevcut Mistral OCR çözücü kullanılabilir durumda.
  Yüksek kaliteli PDF OCR için.
`unstructured` sürüm güncellemeleri, öğe meta verilerini değiştirebilir.
  Çözüm: sürümü sabitleyin, her format için çıkarma kalitesini test edin.
