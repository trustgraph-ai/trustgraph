# Cassandra'da Varlık Odaklı Bilgi Grafiği Depolama

## Genel Bakış

Bu belge, Apache Cassandra üzerindeki RDF tarzı bilgi grafiklerinin depolanması için bir model tanımlamaktadır. Model, her varlığın katıldığı her dörtlü hakkında bilgi sahibi olduğu ve oynadığı rolün bilindiği, **varlık odaklı** bir yaklaşım kullanır. Bu, geleneksel çok tablolu SPO permütasyon yaklaşımının yerini sadece iki tabloyla alır.

## Arka Plan ve Motivasyon

### Geleneksel Yaklaşım

Cassandra'daki standart bir RDF dörtlü deposu, sorgu kalıplarını kapsamak için birden fazla denormalize edilmiş tablo gerektirir; tipik olarak, Konu, Özne, Nesne ve Veri Kümesi (SPOD) permütasyonlarının farklı temsillerini içeren 6 veya daha fazla tablo. Her dörtlü, her tabloya yazılır, bu da önemli bir yazma çoğaltmasına, operasyonel yüke ve şema karmaşıklığına yol açar.

Ek olarak, etiket çözümü (varlıklar için okunabilir adların alınması), ayrı gidiş-dönüş sorguları gerektirir ve bu da, etiketlerin LLM bağlamı için önemli olduğu yapay zeka ve GraphRAG kullanım durumlarında özellikle maliyetlidir.

### Varlık Odaklı İçgörü

Her bir dörtlü `(D, S, P, O)`, en fazla 4 varlığı içerir. Her bir varlığın dörtlüdeki katılımını bir satırla belirterek, **en az bir bilinen öğesi olan her sorgunun bir bölüm anahtarını hedefleyeceğinden emin oluruz**. Bu, tek bir veri tablosuyla tüm 16 sorgu desenini kapsar.

Temel avantajlar:

**7'den fazla yerine 2 tablo**
**6'dan fazla yerine, her dörtlü için 4 yazma işlemi**
**Etiket çözümlemesi ücretsiz** — bir varlığın etiketleri, ilişkileriyle birlikte bulunur ve bu da uygulama önbelleğini doğal olarak önceden doldurur.
**Tüm 16 sorgu deseni**, tek bölüm okumalarıyla sağlanır.
**Daha basit işlemler** — ayarlanması, sıkıştırılması ve onarılması gereken tek bir veri tablosu.

## Şema

### Tablo 1: quads_by_entity

Birincil veri tablosu. Her varlığın, katıldığı tüm dörtlüleri içeren bir bölümü vardır. Sorgu desenini yansıtacak şekilde adlandırılmıştır (varlık bazında arama).

```sql
CREATE TABLE quads_by_entity (
    collection text,       -- Collection/tenant scope (always specified)
    entity     text,       -- The entity this row is about
    role       text,       -- 'S', 'P', 'O', 'G' — how this entity participates
    p          text,       -- Predicate of the quad
    otype      text,       -- 'U' (URI), 'L' (literal), 'T' (triple/reification)
    s          text,       -- Subject of the quad
    o          text,       -- Object of the quad
    d          text,       -- Dataset/graph of the quad
    dtype      text,       -- XSD datatype (when otype = 'L'), e.g. 'xsd:string'
    lang       text,       -- Language tag (when otype = 'L'), e.g. 'en', 'fr'
    PRIMARY KEY ((collection, entity), role, p, otype, s, o, d, dtype, lang)
);
```

**Bölüm anahtarı**: `(collection, entity)` — koleksiyona özel, her varlık için bir bölüm.

**Kümeleme sütun sıralama gerekçesi**:

1. **role** — çoğu sorgu, "bu varlık bir konu mu/nesne mi" şeklinde başlar.
2. **p** — en yaygın filtrelerden ikincisi, "bana tüm `knows` ilişkilerini ver".
3. **otype** — URI değeri olan ilişkileri, literal değeri olan ilişkilerden ayırmayı sağlar.
4. **s, o, d** — benzersizlik için kalan sütunlar.
5. **dtype, lang** — aynı değere sahip ancak farklı tür meta verilerine sahip literal değerleri ayırt eder (örneğin, `"thing"` vs `"thing"@en` vs `"thing"^^xsd:string`).

### Tablo 2: quads_by_collection

Koleksiyon seviyesindeki sorguları ve silme işlemlerini destekler. Bir koleksiyona ait olan tüm dörtlülerin bir listesini sağlar. Sorgu desenini yansıtacak şekilde adlandırılmıştır (koleksiyona göre arama).

```sql
CREATE TABLE quads_by_collection (
    collection text,
    d          text,       -- Dataset/graph of the quad
    s          text,       -- Subject of the quad
    p          text,       -- Predicate of the quad
    o          text,       -- Object of the quad
    otype      text,       -- 'U' (URI), 'L' (literal), 'T' (triple/reification)
    dtype      text,       -- XSD datatype (when otype = 'L')
    lang       text,       -- Language tag (when otype = 'L')
    PRIMARY KEY (collection, d, s, p, o, otype, dtype, lang)
);
```

İlk olarak veri kümesi bazında gruplandırılır, bu da silme işleminin ya koleksiyon düzeyinde ya da veri kümesi düzeyinde yapılabilmesini sağlar. `otype`, `dtype` ve `lang` sütunları, aynı değere sahip ancak farklı tür meta verilerine sahip literal değerleri ayırt etmek için kümeleme anahtarına dahil edilmiştir; RDF'de, `"thing"`, `"thing"@en` ve `"thing"^^xsd:string` semantik olarak farklı değerlerdir.

## Yazma Yolu

Her bir koleksiyon içindeki `C` içinde gelen `(D, S, P, O)` dörtlüsü için, **4 satır** `quads_by_entity`'ye ve **1 satır** `quads_by_collection`'e yazın.

### Örnek

Koleksiyon içindeki `tenant1` dörtgeni verildiğinde:

```
Dataset:  https://example.org/graph1
Subject:  https://example.org/Alice
Predicate: https://example.org/knows
Object:   https://example.org/Bob
```

`quads_by_entity`'e 4 satır yazın:

| collection | entity | role | p | otype | s | o | d |
|---|---|---|---|---|---|---|---|
| tenant1 | https://example.org/graph1 | G | https://example.org/knows | U | https://example.org/Alice | https://example.org/Bob | https://example.org/graph1 |
| tenant1 | https://example.org/Alice | S | https://example.org/knows | U | https://example.org/Alice | https://example.org/Bob | https://example.org/graph1 |
| tenant1 | https://example.org/knows | P | https://example.org/knows | U | https://example.org/Alice | https://example.org/Bob | https://example.org/graph1 |
| tenant1 | https://example.org/Bob | O | https://example.org/knows | U | https://example.org/Alice | https://example.org/Bob | https://example.org/graph1 |

`quads_by_collection`'e 1 satır yazın:

| collection | d | s | p | o | otype | dtype | lang |
|---|---|---|---|---|---|---|---|
| tenant1 | https://example.org/graph1 | https://example.org/Alice | https://example.org/knows | https://example.org/Bob | U | | |

### Literal Example

Bir etiket üçlüsü için:

```
Dataset:  https://example.org/graph1
Subject:  https://example.org/Alice
Predicate: http://www.w3.org/2000/01/rdf-schema#label
Object:   "Alice Smith" (lang: en)
```

`otype` değeri `'L'`, `dtype` değeri `'xsd:string'` ve `lang` değeri `'en'`'tir. Literal değer olan `"Alice Smith"`, `o` içinde saklanır. `quads_by_entity`'de yalnızca 3 satır gereklidir; literal, bir varlık olarak bağımsız olarak sorgulanamayan bir şey olduğu için, literal için herhangi bir satır yazılmaz.

## Sorgu Desenleri

### Tüm 16 DSPO Deseni

Aşağıdaki tabloda, "Mükemmel önek", sorgunun kümeleme sütunlarının ardışık bir önekini kullandığı anlamına gelir. "Bölüm taraması + filtre", Cassandra'nın bir bölümün bir dilimini okuduğu ve bellekte filtreleme yaptığı anlamına gelir; bu, verimli olsa da, saf bir önek eşleşmesi değildir.

| # | Bilinen | Varlık | Kümeleme öneki | Verimlilik |
|---|---|---|---|---|
| 1 | D,S,P,O | entity=S, role='S', p=P | Tam eşleşme | Mükemmel önek |
| 2 | D,S,P,? | entity=S, role='S', p=P | D üzerinde filtreleme | Bölüm taraması + filtre |
| 3 | D,S,?,O | entity=S, role='S' | D, O üzerinde filtreleme | Bölüm taraması + filtre |
| 4 | D,?,P,O | entity=O, role='O', p=P | D üzerinde filtreleme | Bölüm taraması + filtre |
| 5 | ?,S,P,O | entity=S, role='S', p=P | O üzerinde filtreleme | Bölüm taraması + filtre |
| 6 | D,S,?,? | entity=S, role='S' | D üzerinde filtreleme | Bölüm taraması + filtre |
| 7 | D,?,P,? | entity=P, role='P' | D üzerinde filtreleme | Bölüm taraması + filtre |
| 8 | D,?,?,O | entity=O, role='O' | D üzerinde filtreleme | Bölüm taraması + filtre |
| 9 | ?,S,P,? | entity=S, role='S', p=P | — | **Mükemmel önek** |
| 10 | ?,S,?,O | entity=S, role='S' | O üzerinde filtreleme | Bölüm taraması + filtre |
| 11 | ?,?,P,O | entity=O, role='O', p=P | — | **Mükemmel önek** |
| 12 | D,?,?,? | entity=D, role='G' | — | **Mükemmel önek** |
| 13 | ?,S,?,? | entity=S, role='S' | — | **Mükemmel önek** |
| 14 | ?,?,P,? | entity=P, role='P' | — | **Mükemmel önek** |
| 15 | ?,?,?,O | entity=O, role='O' | — | **Mükemmel önek** |
| 16 | ?,?,?,? | — | Tam tarama | Yalnızca keşif |

**Önemli sonuç**: 15 önemsiz desenden 7'si mükemmel kümeleme önek eşleşmesidir. Kalan 8 tanesi, bölüm içi filtrelemeyle birlikte tek bölümlü okumalardır. En az bir bilinen öğeye sahip her sorgu, bir bölüm anahtarını etkiler.

Desen 16 (?,?,?,?) pratikte oluşmaz, çünkü koleksiyon her zaman belirtilir ve bu da onu desen 12'ye indirger.

### Yaygın Sorgu Örnekleri

**Bir varlık hakkında her şey:**

```sql
SELECT * FROM quads_by_entity
WHERE collection = 'tenant1' AND entity = 'https://example.org/Alice';
```

**Bir varlık için tüm dış ilişkiler:**

```sql
SELECT * FROM quads_by_entity
WHERE collection = 'tenant1' AND entity = 'https://example.org/Alice'
AND role = 'S';
```

**Bir varlık için özel koşul:**

```sql
SELECT * FROM quads_by_entity
WHERE collection = 'tenant1' AND entity = 'https://example.org/Alice'
AND role = 'S' AND p = 'https://example.org/knows';
```

**Bir varlık için etiket (belirli bir dil):**

```sql
SELECT * FROM quads_by_entity
WHERE collection = 'tenant1' AND entity = 'https://example.org/Alice'
AND role = 'S' AND p = 'http://www.w3.org/2000/01/rdf-schema#label'
AND otype = 'L';
```

Gerekirse, `lang = 'en'` uygulamasının tarafında filtreleme yapın.

**Sadece URI değerine sahip ilişkiler (varlıklar arası bağlantılar):**

```sql
SELECT * FROM quads_by_entity
WHERE collection = 'tenant1' AND entity = 'https://example.org/Alice'
AND role = 'S' AND p = 'https://example.org/knows' AND otype = 'U';
```

**Ters sorgulama — bu varlığa neyin işaret ettiği:**

```sql
SELECT * FROM quads_by_entity
WHERE collection = 'tenant1' AND entity = 'https://example.org/Bob'
AND role = 'O';
```

## Etiket Çözümleme ve Önbellek Isıtma

Varlık odaklı modelin en önemli avantajlarından biri, **etiket çözümlemenin ücretsiz bir yan etki olmasıdır**.

Geleneksel çok tablolu modelde, etiketleri almak ayrı sorgu istekleri gerektirir: üçlüleri alın, sonuçlardaki varlık URI'larını belirleyin ve ardından her biri için `rdfs:label` alın. Bu N+1 deseni maliyetlidir.

Varlık odaklı modelde, bir varlığı sorgulamak, etiketleri, türleri ve diğer özellikleri de içeren **tüm** dörtlülerini döndürür. Uygulama sorgu sonuçlarını önbelleğe aldığında, etiketler herhangi bir şey onlardan istekte bulunmadan önce önceden ısıtılır.

İki kullanım rejimi, bunun pratikte iyi çalıştığını doğrulamaktadır:

**Kullanıcı arayüzüne yönelik sorgular**: doğal olarak küçük sonuç kümeleri, etiketler önemlidir. Varlık okumaları önbelleği önceden ısıtır.
**AI/toplu sorgular**: büyük sonuç kümeleri ve sıkı sınırlar. Etiketler ya gereksizdir ya da önceden önbelleğe alınmış olan varlıkların yalnızca seçilmiş bir alt kümesi için gereklidir.

Çok büyük sonuç kümeleri (örneğin, 30.000 varlık) için etiketleri çözme konusundaki teorik endişe, hiçbir insan veya yapay zeka tüketicisinin o kadar çok etiketi faydalı bir şekilde işlemediği pratik gözlemiyle giderilir. Uygulama düzeyindeki sorgu sınırları, önbellek üzerindeki baskının yönetilebilir kalmasını sağlar.

## Geniş Bölümler ve Somutlaştırma

Somutlaştırma (RDF-star tarzı, ifadeler hakkında ifadeler), kaynak belge gibi merkez varlıkları oluşturur; bu belge, çıkarılan binlerce olguyu destekler. Bu, geniş bölümlere yol açabilir.

Hafifletici faktörler:

**Uygulama düzeyindeki sorgu sınırları**: tüm GraphRAG ve kullanıcı arayüzüne yönelik sorgular, geniş bölümlerin sıcak okuma yolunda asla tamamen taranmamasını sağlayan sıkı sınırlar uygular.
**Cassandra, kısmi okumaları verimli bir şekilde işler**: erken durdurma ile bir küme sütunu taraması, büyük bölümlerde bile hızlıdır.
**Koleksiyon silme** (sadece tüm bölümleri geçebilecek bir işlem), kabul edilebilir bir arka plan işlemidir.

## Koleksiyon Silme

API çağrısı tarafından tetiklenir, arka planda çalışır (eventually consistent).

1. Hedef koleksiyon için `quads_by_collection`'ı okuyun ve tüm dörtlüleri alın.
2. Dörtlülerden benzersiz varlıkları çıkarın (s, p, o, d değerleri).
3. Her benzersiz varlık için, `quads_by_entity`'dan ilgili bölümü silin.
4. `quads_by_collection`'dan satırları silin.

`quads_by_collection` tablosu, tüm varlık bölümlerini tam tablo taraması olmadan bulmak için gereken dizini sağlar. Bölüm düzeyindeki silmeler verimlidir çünkü `(collection, entity)` bölüm anahtarıdır.

## Çok Tablolu Modelden Geçiş Yolu

Varlık odaklı model, geçiş sırasında mevcut çok tablolu modelle birlikte var olabilir:

1. `quads_by_entity` ve `quads_by_collection` tablolarını mevcut tablolara ek olarak dağıtın.
2. Yeni dörtlüleri hem eski hem de yeni tablolara çift yazın.
3. Mevcut verileri yeni tablolara geri yükleyin.
4. Okuma yollarını bir sorgu deseni bir seferinde geçirin.
5. Tüm okumalar geçirildikten sonra eski tabloları devre dışı bırakın.

## Özet

| Yön | Geleneksel (6 tablo) | Varlık odaklı (2 tablo) |
|---|---|---|
| Tablolar | 7+ | 2 |
| Dörtlü başına yazma | 6+ | 5 (4 veri + 1 manifest) |
| Etiket çözümleme | Ayrı sorgu istekleri | Önbellek ısıtma yoluyla ücretsiz |
| Sorgu desenleri | 6 tabloda 16 | 1 tabloda 16 |
| Şema karmaşıklığı | Yüksek | Düşük |
| İşletimsel yük | Ayarlanması/onarılması gereken 6 tablo | 1 veri tablosu |
| Somutlaştırma desteği | Ek karmaşıklık | Doğal uyum |
| Nesne türü filtreleme | Kullanılamaz | Yerel (o tür kümeleme yoluyla) |
ÇIKTI SÖZLEŞMESİ (tam olarak aşağıdaki formatı takip etmelidir):
