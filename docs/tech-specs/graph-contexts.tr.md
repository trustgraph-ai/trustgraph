# Graph Contexts Technical Specification

## Overview

Bu özellik, TrustGraph'ın temel grafik yapılarına yapılan değişiklikleri tanımlar ve
RDF 1.2 ile uyumlu olacak ve tam RDF Dataset semantiğini destekleyecek şekilde tasarlanmıştır. Bu, 2.x yayın serisi için önemli bir değişikliktir.


### Versioning

**2.0**: Erken benimseyen sürüm. Temel özellikler mevcut, ancak henüz tamamen
  üretim ortamına hazır olmayabilir.
**2.1 / 2.2**: Üretim sürümü. Kararlılık ve eksiksizlik doğrulandı.

Olgunluk konusundaki esneklik kasıtlıdır; erken benimseyenler, tüm özellikler
üretim ortamına hazır hale gelmeden önce yeni yeteneklere erişebilir.

## Goals

Bu çalışmanın temel hedefleri, gerçekler/ifadeler hakkında meta veri sağlamaktır:

**Zaman bilgisi**: Gerçekleri zamanla ilgili bilgilerle ilişkilendirme
  Bir gerçeğin doğru olduğu düşünüldüğü zaman
  Bir gerçeğin doğru hale geldiği zaman
  Bir gerçeğin yanlış olduğu tespit edildiği zaman

**Kaynak/Köken**: Bir gerçeği destekleyen kaynakları izleme
  "Bu gerçek, X kaynağı tarafından desteklenmektedir"
  Gerçekleri, köken belgelerine bağlama

**Doğruluk/Güven**: Gerçekler hakkındaki iddiaları kaydetme
  "Kişi P, bunun doğru olduğunu iddia etti"
  "Kişi Q, bunun yanlış olduğunu iddia ediyor"
  Güven puanlamasını ve çakışma tespitini etkinleştirme

**Hipotez**: Yeniden tanımlama (RDF-star / tırnak işaretli üçlüler), bu sonuçları
elde etmek için temel mekanizmadır, çünkü bunların hepsi ifadeler hakkında ifadeler yapmayı gerektirir.

## Background

"Alice'in Bob'u tanıdığı" gerçeğinin "2024-01-15" tarihinde keşfedildiğini veya
"X kaynağının (Y'nin Z'ye neden olduğu) iddiasını desteklediğini" ifade etmek için,
bir kenara bir şey olarak başvurmanız ve bu kenar hakkında ifadeler yapabilmeniz gerekir. Standart üçlüler bunu desteklemez.

### Current Limitations

Mevcut `Value` sınıfı `trustgraph-base/trustgraph/schema/core/primitives.py` içinde
şunları temsil edebilir:
URI düğümleri (`is_uri=True`)
Literal değerler (`is_uri=False`)

`type` alanı mevcuttur, ancak XSD veri türlerini temsil etmek için kullanılmaz.

## Technical Design

### RDF Features to Support

#### Core Features (Related to Reification Goals)

Bu özellikler, zaman, kaynak ve doğruluk hedefleriyle doğrudan ilgilidir:

1. **RDF 1.2 Quoted Triples (RDF-star)**
Diğer kenarlara işaret eden kenarlar
   Bir Üçlü, başka bir Üçlünün konusu veya nesnesi olabilir
   İfadeler hakkında ifadeler yapmayı sağlar (yeniden tanımlama)
   Bireysel gerçekleri açıklamak için temel mekanizma
   
2. **RDF Dataset / Named Graphs**
Bir veri kümesi içindeki birden fazla adlandırılmış grafik için destek
   Her grafik bir IRI ile tanımlanır
   Üçlülerden (s, p, o) dörtlülere (s, p, o, g) geçiş
   Bir varsayılan grafik ve sıfır veya daha fazla adlandırılmış grafik içerir
   Grafik IRI'si, ifadelerin konusu olabilir, örneğin:
   Grafik IRI'si, ifadelerde bir özne olabilir, örneğin:
     ```
     <graph-source-A> <discoveredOn> "2024-01-15"
     <graph-source-A> <hasVeracity> "high"
     ```
   Not: Adlandırılmış grafikler, somutlaştırmadan ayrı bir özelliktir. Bunlar,
     yalnızca ifade açıklamasının ötesinde kullanımlara sahiptir (bölümleme, erişim kontrolü, veri kümesi
     organizasyonu) ve ayrı bir yetenek olarak ele alınmalıdır.

3. **Anonim Düğümler** (Sınırlı Destek)
   Küresel bir URI'ye sahip olmayan anonim düğümler
   Dış RDF verilerini yüklerken uyumluluk için desteklenir
   **Sınırlı durum:** Yükleme işleminden sonra kararlı bir kimlik konusunda hiçbir garanti yoktur
   Bunları jokerli sorgular aracılığıyla bulun (bağlantılara göre, kimliğe göre değil)
   Birincil bir özellik değildir - kesin anonim düğüm işleme özelliğine güvenmeyin

#### Fırsatçı Düzeltmeler (2.0'ın Kırıcı Değişikliği)

Bu özellikler, somutlaştırma hedefleriyle doğrudan ilişkili değildir, ancak
kırıcı değişiklikler yaparken dahil edilmesi değerli olan iyileştirmelerdir:

4. **Literal Veri Tipleri**
   XSD veri tipleri için `type` alanını doğru şekilde kullanın
   Örnekler: xsd:string, xsd:integer, xsd:dateTime, vb.
   Mevcut sınırlamayı düzeltir: tarihleri veya tamsayıları düzgün bir şekilde temsil edilemez

5. **Dil Etiketleri**
   Dize literal değerleri üzerinde dil öznitelikleri desteği (@en, @fr, vb.)
   Not: Bir literal değerin ya bir dil etiketi YA da bir veri tipi vardır, ikisi birden değil
     (rdf:langString hariç)
   Yapay zeka/çok dilli kullanım senaryoları için önemlidir

### Veri Modelleri

#### Terim (Value adından değiştirildi)

`Value` sınıfı, RDF terminolojisini daha iyi yansıtmak için `Term` olarak yeniden adlandırılacaktır.
Bu yeniden adlandırma iki amaca hizmet etmektedir:
1. İsimlendirmeyi RDF kavramlarıyla uyumlu hale getirmek (bir "Terim", bir IRI, literal, boş
   düğüm veya tırnak içindeki üçlü olabilir - sadece bir "değer" değildir).
2. Değişikliklere neden olan arayüzde kod incelemesini zorlamak - hala
   `Value`'a referans veren herhangi bir kod, açıkça hatalıdır ve güncellenmesi gerekir.

Bir Terim şunları temsil edebilir:

**IRI/URI** - Adlandırılmış bir düğüm/kaynak
**Boş Düğüm** - Yerel kapsamı olan anonim bir düğüm
**Literal (Değer)** - Ya bir veri türü (XSD türü) veya
  Bir dil etiketi
  **Tırnak İçine Alınmış Üçlü** - Bir terim olarak kullanılan bir üçlü (RDF 1.2)


##### Seçilen Yaklaşım: Tip Ayırıcısı Olan Tek Sınıf

Serileştirme gereksinimleri yapıyı belirler - bir tür ayrımcısına ihtiyaç vardır.
Python gösteriminden bağımsız olarak, kablo formatında bir tür ayrımcısına ihtiyaç vardır.
Tek bir sınıf ve bir tür alanı, doğal bir çözümdür ve mevcut `Value` kalıbıyla uyumludur.

Tek karakterli tür kodları, kompakt serileştirme sağlar:

```python
from dataclasses import dataclass

# Term type constants
IRI = "i"      # IRI/URI node
BLANK = "b"    # Blank node
LITERAL = "l"  # Literal value
TRIPLE = "t"   # Quoted triple (RDF-star)

@dataclass
class Term:
    type: str = ""  # One of: IRI, BLANK, LITERAL, TRIPLE

    # For IRI terms (type == IRI)
    iri: str = ""

    # For blank nodes (type == BLANK)
    id: str = ""

    # For literals (type == LITERAL)
    value: str = ""
    datatype: str = ""   # XSD datatype URI (mutually exclusive with language)
    language: str = ""   # Language tag (mutually exclusive with datatype)

    # For quoted triples (type == TRIPLE)
    triple: "Triple | None" = None
```

Kullanım örnekleri:

```python
# IRI term
node = Term(type=IRI, iri="http://example.org/Alice")

# Literal with datatype
age = Term(type=LITERAL, value="42", datatype="xsd:integer")

# Literal with language tag
label = Term(type=LITERAL, value="Hello", language="en")

# Blank node
anon = Term(type=BLANK, id="_:b1")

# Quoted triple (statement about a statement)
inner = Triple(
    s=Term(type=IRI, iri="http://example.org/Alice"),
    p=Term(type=IRI, iri="http://example.org/knows"),
    o=Term(type=IRI, iri="http://example.org/Bob"),
)
reified = Term(type=TRIPLE, triple=inner)
```

##### Alternatifler

**B Seçeneği: Özel sınıfların birleşimi** (`Term = IRI | BlankNode | Literal | QuotedTriple`)
Reddedildi: Seri hale getirme işlemi hala bir tür belirleyici gerektirecek, bu da karmaşıklığı artıracaktır.

**C Seçeneği: Alt sınıflara sahip temel sınıf**
Reddedildi: Aynı seri hale getirme sorunu, ayrıca dataclass miras özellikleriyle ilgili sorunlar.

#### Üçlü / Dörtlü

`Triple` sınıfı, isteğe bağlı bir grafik alanı kazanarak dörtlü bir yapıya dönüşebilir:

```python
@dataclass
class Triple:
    s: Term | None = None    # Subject
    p: Term | None = None    # Predicate
    o: Term | None = None    # Object
    g: str | None = None     # Graph name (IRI), None = default graph
```

Tasarım kararları:
**Alan adı**: `g`, `s`, `p` ve `o` ile tutarlılık için.
**İsteğe bağlı**: `None`, varsayılan grafiği (isim belirtilmemiş) ifade eder.
**Tip**: Terim yerine düz bir dize (IRI).
  Grafik adları her zaman IRI'lerdir.
  Boş düğümlerin grafik adı olarak kullanılması reddedildi (çok kafa karıştırıcı).
  Tam Terim mekanizmasına ihtiyaç yok.

Not: Sınıf adı teknik olarak bir dörtlü olsa bile `Triple` olarak kalır.
Bu, karmaşayı önler ve "üçlü" terimi hala s/p/o kısmı için yaygın olarak kullanılan bir terimdir. Grafik bağlamı, üçlünün nerede bulunduğu hakkında meta veridir.


### Olası Sorgu Desenleri

Mevcut sorgu motoru, S, P, O terimlerinin kombinasyonlarını kabul eder. Tırnak içinde belirtilen
üçlüler, bir üçlünün kendisi bu konumlarda geçerli bir terim haline gelir. Aşağıda,
orijinal hedefleri destekleyen olası sorgu desenleri bulunmaktadır.

#### Grafik Parametre Anlamları

Geriye dönük uyumluluk için SPARQL kurallarına uygun olarak:

**`g` belirtilmemiş / Yok**: Yalnızca varsayılan grafiği sorgula.
**`g` = belirli bir IRI**: Yalnızca o adlandırılmış grafiği sorgula.
**`g` = joker karakter / `*`**: Tüm grafikler arasında sorgu yap (SPARQL ile eşdeğer
  `GRAPH ?g { ... }`).

Bu, basit sorguları basit tutar ve adlandırılmış grafik sorgularını isteğe bağlı hale getirir.

Grafik arası sorgular (g=joker karakter), tamamen desteklenir. Cassandra şeması,
g'nin bir kümeleme sütunu olduğu (bölüm anahtarı olmadığı) özel tabloları içerir (SPOG, POSG, OSPG),
bu da tüm grafikler arasında verimli sorgular yapmayı sağlar.

#### Zamansal Sorgular

**Belirli bir tarihten sonra keşfedilen tüm bilgileri bul:**
```
S: ?                                    # any quoted triple
P: <discoveredOn>
O: > "2024-01-15"^^xsd:date             # date comparison
```

**Belirli bir bilginin ne zaman doğru olduğuna inanıldığı bulun:**
```
S: << <Alice> <knows> <Bob> >>          # quoted triple as subject
P: <believedTrueFrom>
O: ?                                    # returns the date
```

**Yanlış hale gelen bilgileri bulun:**
```
S: ?                                    # any quoted triple
P: <discoveredFalseOn>
O: ?                                    # has any value (exists)
```

#### Kaynak Sorguları

**Belirli bir kaynağa dayanan tüm bilgileri bulun:**
```
S: ?                                    # any quoted triple
P: <supportedBy>
O: <source:document-123>
```

**Belirli bir gerçeği destekleyen kaynakları bulun:**
```
S: << <DrugA> <treats> <DiseaseB> >>    # quoted triple as subject
P: <supportedBy>
O: ?                                    # returns source IRIs
```

#### Doğruluk Sorguları

**Bir kişinin doğru olarak işaretlediği ifadeleri bulun:**
```
S: ?                                    # any quoted triple
P: <assertedTrueBy>
O: <person:Alice>
```

**Çelişkili ifadeleri bulun (aynı gerçek, farklı doğruluk):**
```
# First query: facts asserted true
S: ?
P: <assertedTrueBy>
O: ?

# Second query: facts asserted false
S: ?
P: <assertedFalseBy>
O: ?

# Application logic: find intersection of subjects
```

**Güvenilirlik puanı eşik değerinin altında olan bilgileri bulun:**
```
S: ?                                    # any quoted triple
P: <trustScore>
O: < 0.5                                # numeric comparison
```

### Mimari

Birden çok bileşende önemli değişiklikler gereklidir:

#### Bu Depo (trustgraph)

**Şema ilkel öğeleri** (`trustgraph-base/trustgraph/schema/core/primitives.py`)
  Değer → Terim yeniden adlandırması
  Tip ayrımcısına sahip yeni Terim yapısı
  Üçlü, grafik bağlamı için `g` alanı kazanır

**Mesaj çeviricileri** (`trustgraph-base/trustgraph/messaging/translators/`)
  Yeni Terim/Üçlü yapıları için güncelleme
  Yeni alanlar için serileştirme/deserileştirme

**Geçit bileşenleri**
  Yeni Terim ve dörtlü yapılarını işleyin

**Bilgi çekirdekleri**
  Dörtlüleri ve yeniden tanımlamayı desteklemek için çekirdek değişiklikleri

**Bilgi yöneticisi**
  Şema değişiklikleri burada yayılır

**Depolama katmanları**
  Cassandra: Şema yeniden tasarımı (Ayrıntılar için Uygulama Ayrıntılarına bakın)
  Diğer arka uçlar: Daha sonraki aşamalara ertelenmiştir

**Komut satırı araçları**
  Yeni veri yapıları için güncelleme

**REST API dokümantasyonu**
  OpenAPI spesifikasyonunda güncellemeler

#### Harici Depolar

**Python API'si** (bu depo)
  Yeni yapılar için istemci kitaplığı güncellemeleri

**TypeScript API'leri** (ayrı depo)
  İstemci kitaplığı güncellemeleri

**Çalışma alanı** (ayrı depo)
  Önemli durum yönetimi değişiklikleri

### API'ler

#### REST API

OpenAPI spesifikasyonunda belgelenmiştir
Yeni Terim/Üçlü yapıları için güncellenmesi gerekecektir
Grafik bağlamı işlemleri için yeni uç noktaları gerekebilir

#### Python API'si (bu depo)

Yeni ilkel öğelerle eşleşen istemci kitaplığı değişiklikleri
Terim (önceden Değer) ve Üçlü için bozucu değişiklikler

#### TypeScript API'si (ayrı depo)

Python API'sine paralel değişiklikler
Ayrı sürüm koordinasyonu

#### Çalışma alanı (ayrı depo)

Önemli durum yönetimi değişiklikleri
Grafik bağlamı özellikleriyle ilgili kullanıcı arayüzü güncellemeleri

### Uygulama Ayrıntıları

#### Aşamalı Depolama Uygulaması

Birden çok grafik depolama arka ucu (Cassandra, Neo4j, vb.) vardır. Uygulama
aşağıdaki aşamalarda gerçekleştirilecektir:

1. **1. Aşama: Cassandra**
   Yerel Cassandra deposuyla başlayın
   Depolama katmanı üzerinde tam kontrol, hızlı yinelemeyi sağlar
   Şema, dörtlüler + yeniden tanımlama için sıfırdan yeniden tasarlanacaktır
   Veri modelini ve sorgu kalıplarını gerçek kullanım durumlarına göre doğrulayın

#### Cassandra Şema Tasarımı

Cassandra, farklı sorgu erişim modellerini desteklemek için birden fazla tablo gerektirir
(her tablo, bölüm anahtarı + kümeleme sütunları aracılığıyla verimli bir şekilde sorgulanır).

##### Sorgu Modelleri

"quads" (g, s, p, o) ile, her konum belirtilebilir veya joker karakter olabilir ve bu da
16 olası sorgu modeli oluşturur:

| # | g | s | p | o | Açıklama |
|---|---|---|---|---|-------------|
| 1 | ? | ? | ? | ? | Tüm "quads" |
| 2 | ? | ? | ? | o | Nesneye göre |
| 3 | ? | ? | p | ? | Özneye göre |
| 4 | ? | ? | p | o | Özne + nesneye göre |
| 5 | ? | s | ? | ? | Konuya göre |
| 6 | ? | s | ? | o | Konu + nesneye göre |
| 7 | ? | s | p | ? | Konu + öneye göre |
| 8 | ? | s | p | o | Tam üçlü (hangi grafikler?) |
| 9 | g | ? | ? | ? | Grafiğe göre |
| 10 | g | ? | ? | o | Grafik + nesneye göre |
| 11 | g | ? | p | ? | Grafik + öneye göre |
| 12 | g | ? | p | o | Grafik + öne + nesneye göre |
| 13 | g | s | ? | ? | Grafik + konuya göre |
| 14 | g | s | ? | o | Grafik + konu + nesneye göre |
| 15 | g | s | p | ? | Grafik + konu + öneye göre |
| 16 | g | s | p | o | Tam "quad" |

##### Tablo Tasarımı

Cassandra kısıtlaması: Yalnızca bölüm anahtarına göre verimli bir şekilde sorgulayabilirsiniz, ardından
kümeleme sütunları üzerinde soldan sağa filtreleme yapabilirsiniz. "g" joker karakterli sorgular için, "g" bir
kümeleme sütunu olmalıdır. "g" belirtilmiş sorgular için, bölüm anahtarında bulunan "g" daha
verimlidir.

**İki tablo ailesi gereklidir:**

**A Ailesi: "g" joker karakterli sorgular** ("g" kümeleme sütunlarında)

| Tablo | Bölüm | Kümeleme | Desteklenen modeller |
|-------|-----------|------------|-------------------|
| SPOG | (kullanıcı, koleksiyon, s) | p, o, g | 5, 7, 8 |
| POSG | (kullanıcı, koleksiyon, p) | o, s, g | 3, 4 |
| OSPG | (kullanıcı, koleksiyon, o) | s, p, g | 2, 6 |

**B Ailesi: "g" belirtilmiş sorgular** ("g" bölüm anahtarında)

| Tablo | Bölüm | Kümeleme | Desteklenen modeller |
|-------|-----------|------------|-------------------|
| GSPO | (kullanıcı, koleksiyon, g, s) | p, o | 9, 13, 15, 16 |
| GPOS | (kullanıcı, koleksiyon, g, p) | o, s | 11, 12 |
| GOSP | (kullanıcı, koleksiyon, g, o) | s, p | 10, 14 |

**Koleksiyon tablosu** (döngüleme ve toplu silme için)

| Tablo | Bölüm | Kümeleme | Amaç |
|-------|-----------|------------|---------|
| COLL | (kullanıcı, koleksiyon) | g, s, p, o | Koleksiyondaki tüm "quad"ları numaralandır |

##### Yazma ve Silme Yolları

**Yazma yolu**: Tüm 7 tabloya ekleyin.

**Koleksiyon silme yolu**:
1. `(user, collection)` için COLL tablosunu yineleyin
2. Her "quad" için, tüm 6 sorgu tablosundan silin
3. COLL tablosundan silin (veya aralık silme)

**Tek bir "quad" silme yolu**: Tüm 7 tabloya doğrudan silin.

##### Depolama Maliyeti

Her "quad" 7 kez depolanır. Bu, esnek sorgulama ile
verimli koleksiyon silme birleşiminin maliyetidir.

##### Depolamada Alıntılanmış Üçlüler

Konu veya nesne kendisi bir üçlü olabilir. Seçenekler:

**A Seçeneği: Alıntılanmış üçlüleri standart bir dizeye seri hale getirin**
```
S: "<<http://ex/Alice|http://ex/knows|http://ex/Bob>>"
P: http://ex/discoveredOn
O: "2024-01-15"
G: null
```
Tırnak içinde belirtilen üçlüleri, seri hale getirilmiş bir dize olarak S veya O sütunlarında saklayın.
Seri hale getirilmiş forma göre tam eşleşme ile sorgulayın.
Artı: Basit, mevcut indeks kalıplarına uyuyor.
Eksileri: "Tırnak içinde belirtilen öznenin yüklemesinin X olduğu üçlüleri bul" gibi sorguları yapmak mümkün değil.

**B Seçeneği: Üçlü Kimlikleri / Hash'leri**
```
Triple table:
  id: hash(s,p,o,g)
  s, p, o, g: ...

Metadata table:
  subject_triple_id: <hash>
  p: http://ex/discoveredOn
  o: "2024-01-15"
```
Her üçlüye bir kimlik (bileşenlerin karma değeri) atayın.
Örnek meta veri referansları, kimlik numarasıyla üçlüleri belirtir.
Artı: Temiz bir ayrım, üçlü kimlik numaralarının indekslenmesini sağlar.
Eksileri: Üçlü kimliğinin hesaplanmasını/yönetilmesini gerektirir, iki aşamalı aramalar.

**Öneri**: Basitlik için A seçeneğiyle (serileştirilmiş dizeler) başlayın.
B seçeneği, tırnak içinde belirtilen üçlü bileşenleri üzerinde gelişmiş sorgu desenleri gerekiyorsa gerekebilir.

ÇIKTI SÖZLEŞMESİ (tam olarak aşağıdaki formatı takip etmelidir):
2. **2. Aşama+: Diğer Altyapılar**
   Neo4j ve diğer depolama sistemleri, sonraki aşamalarda uygulanmıştır.
   Cassandra'dan edinilen deneyimler, bu uygulamaları etkilemiştir.

Bu yaklaşım, tamamen kontrol altında olan bir altyapıda doğrulama yaparak tasarım riskini azaltır.
Tüm depolama sistemlerine yönelik uygulamalara başlamadan önce bu doğrulama yapılır.

#### Değer → Terim Yeniden Adlandırma

`Value` sınıfı, `Term` olarak yeniden adlandırılacaktır. Bu, kod tabanındaki yaklaşık 78 dosyayı etkilemektedir.
Yeniden adlandırma, bir zorlama işlevi olarak görev görmektedir: hala ⟦CODE_0⟧'ı kullanan herhangi bir kod...
`Value`, 2.0 ile uyumluluk açısından gözden geçirilmesi/güncellenmesi gereken bir alan olarak hemen belirlenebilir.


## Güvenlik Hususları

Adlandırılmış grafikler bir güvenlik özelliği değildir. Kullanıcılar ve koleksiyonlar,
güvenlik sınırlarıdır. Adlandırılmış grafikler tamamen veri organizasyonu ve
somutlaştırma desteği içindir.

## Performans Hususları

Tırnak işaretli üçlüler, iç içe derinliğini artırır - sorgu performansını etkileyebilir.
Verimli grafik kapsamlı sorgular için adlandırılmış grafik indeksleme stratejilerine ihtiyaç vardır.
Cassandra şema tasarımı, dörtlü depolamayı verimli bir şekilde karşılayacak şekilde tasarlanmalıdır.

### Vektör Depolama Sınırı

Vektör depoları her zaman yalnızca IRI'lere başvurur:
Asla kenarlar (tırnak işaretli üçlüler)
Asla literal değerler
Asla boş düğümler

Bu, vektör deposunu basit tutar; adlandırılmış varlıkların semantik benzerliğini işler. Grafik yapısı, ilişkileri, somutlaştırmayı ve meta verileri yönetir.
Tırnak içinde belirtilen üçlüler ve adlandırılmış grafikler, vektör işlemlerini karmaşıklaştırmaz.

## Test Stratejisi

Mevcut test stratejisini kullanın. Bu, önemli bir değişiklik olduğundan, yeni yapıların tüm bileşenlerde doğru şekilde çalıştığını doğrulamak için uçtan uca test paketine kapsamlı bir şekilde odaklanılmalıdır.

## Geçiş Planı

2.0, önemli bir değişiklik içeren bir sürümdür; geriye dönük uyumluluk gerekmemektedir.
Mevcut verilerin, yeni şemaya aktarılması gerekebilir (son tasarım bazında belirlenecektir).
Mevcut üçlüleri dönüştürmek için geçiş araçlarını göz önünde bulundurun.

## Açık Sorular


## Açık Sorular

**Boş düğümler**: Sınırlı destek doğrulandı. Boş düğümler için bir skolemleştirme stratejisi belirlemek gerekebilir (yükleme sırasında IRI'lar oluşturmak veya boş düğüm kimliklerini korumak).
  **Sorgu sözdizimi**: Alıntılanmış üçlüleri sorgularda belirtmek için somut sözdizimi nedir? Sorgu API'sini tanımlamak gerekiyor.
~~**Önerme sözlüğü**~~: Çözüldü. Herhangi bir geçerli RDF önermesi izin verilir, kullanıcı tanımlı olanlar dahil. RDF geçerliliği hakkında minimum varsayımlar.
  Çok az sabit değer (örneğin, bazı yerlerde kullanılan ⟦CODE_0⟧).
~~**Önerme sözlüğü**:~~ Çözüldü. Herhangi bir geçerli RDF özneli kabul edilebilir,
  kullanıcı tarafından tanımlanmış özel özneler de dahil. RDF geçerliliği hakkında çok az varsayım.
  Çok az sabit değer (örneğin, bazı yerlerde kullanılan `rdfs:label`).
  Strateji: Mümkün olduğunca hiçbir şeyi kilitlememeye özen gösterin.
~~**Vektör depolama etkisi**~~: Çözüldü. Vektör depoları her zaman IRI'lere işaret eder.
  sadece - asla kenarlara, literal değerlere veya boş düğümlere işaret etmez. Tırnak işaretli üçlüler ve
  yeniden tanımlama, vektör deposunu etkilemez.
~~**Adlandırılmış grafik semantiği**~~: Çözüldü. Sorgular varsayılan olarak
  grafiğe yöneliktir (SPARQL davranışıyla eşleşir, geriye dönük uyumlu). Adlandırılmış grafiklere veya tüm
  grafiklere sorgu yapmak için açık bir grafik parametresi gereklidir.

## Referanslar

[RDF 1.2 Kavramları](https://www.w3.org/TR/rdf12-concepts/)
[RDF-star ve SPARQL-star](https://w3c.github.io/rdf-star/)
[RDF Veri Kümesi](https://www.w3.org/TR/rdf11-concepts/#section-dataset)
