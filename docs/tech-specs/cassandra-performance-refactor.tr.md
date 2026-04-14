---
layout: default
title: "Teknik Özellikler: Cassandra Bilgi Tabanı Performans Yenilemesi"
parent: "Turkish (Beta)"
---

# Teknik Özellikler: Cassandra Bilgi Tabanı Performans Yenilemesi

> **Beta Translation:** This document was translated via Machine Learning and as such may not be 100% accurate. All non-English languages are currently classified as Beta.

**Durum:** Taslak
**Yazar:** Yardımcı
**Tarih:** 2025-09-18

## Genel Bakış

Bu özellik, TrustGraph Cassandra bilgi tabanı uygulamasındaki performans sorunlarına değinmekte ve RDF üçlü depolama ve sorgulama için optimizasyonlar önermektedir.

## Mevcut Uygulama

### Şema Tasarımı

Mevcut uygulama, `trustgraph-flow/trustgraph/direct/cassandra_kg.py`'da tek bir tablo tasarımı kullanmaktadır:

```sql
CREATE TABLE triples (
    collection text,
    s text,
    p text,
    o text,
    PRIMARY KEY (collection, s, p, o)
);
```

**İkincil İndeksler:**
`triples_s` ON `s` (özne)
`triples_p` ON `p` (yüklem)
`triples_o` ON `o` (nesne)

### Sorgu Desenleri

Mevcut uygulama, 8 farklı sorgu desenini desteklemektedir:

1. **get_all(collection, limit=50)** - Bir koleksiyon için tüm üçlüleri getirir.
   ```sql
   SELECT s, p, o FROM triples WHERE collection = ? LIMIT 50
   ```

2. **get_s(collection, s, limit=10)** - Konuya göre sorgulama
   ```sql
   SELECT p, o FROM triples WHERE collection = ? AND s = ? LIMIT 10
   ```

3. **get_p(collection, p, limit=10)** - Öznitelik kullanarak sorgulama
   ```sql
   SELECT s, o FROM triples WHERE collection = ? AND p = ? LIMIT 10
   ```

4. **get_o(collection, o, limit=10)** - Nesneye göre sorgulama
   ```sql
   SELECT s, p FROM triples WHERE collection = ? AND o = ? LIMIT 10
   ```

5. **get_sp(collection, s, p, limit=10)** - Konu + yüklem ile sorgulama
   ```sql
   SELECT o FROM triples WHERE collection = ? AND s = ? AND p = ? LIMIT 10
   ```

6. **get_po(collection, p, o, limit=10)** - Öznitelik + nesneye göre sorgulama ⚠️
   ```sql
   SELECT s FROM triples WHERE collection = ? AND p = ? AND o = ? LIMIT 10 ALLOW FILTERING
   ```

7. **get_os(collection, o, s, limit=10)** - Nesne + konu ile sorgulama ⚠️
   ```sql
   SELECT p FROM triples WHERE collection = ? AND o = ? AND s = ? LIMIT 10 ALLOW FILTERING
   ```

8. **get_spo(collection, s, p, o, limit=10)** - Tam üçlü eşleşme
   ```sql
   SELECT s as x FROM triples WHERE collection = ? AND s = ? AND p = ? AND o = ? LIMIT 10
   ```

### Mevcut Mimari

**Dosya: `trustgraph-flow/trustgraph/direct/cassandra_kg.py`**
Tüm işlemleri yöneten tek `KnowledgeGraph` sınıfı
Küresel `_active_clusters` listesi aracılığıyla bağlantı havuzu
Sabit tablo adı: `"triples"`
Kullanıcı modeli başına keyspace
Faktörü 1 olan SimpleStrategy replikasyonu

**Entegrasyon Noktaları:**
**Yazma Yolu:** `trustgraph-flow/trustgraph/storage/triples/cassandra/write.py`
**Sorgu Yolu:** `trustgraph-flow/trustgraph/query/triples/cassandra/service.py`
**Bilgi Deposu:** `trustgraph-flow/trustgraph/tables/knowledge.py`

## Tespit Edilen Performans Sorunları

### Şema Seviyesi Sorunlar

1. **Verimsiz Birincil Anahtar Tasarımı**
   Mevcut: `PRIMARY KEY (collection, s, p, o)`
   Sık erişim kalıpları için zayıf kümelenmeye neden olur
   Pahalı ikincil indeks kullanımını zorlar

2. **İkincil İndeks Aşırı Kullanımı** ⚠️
   Yüksek kardinaliteli sütunlarda (s, p, o) üç ikincil indeks
   Cassandra'daki ikincil indeksler pahalıdır ve iyi ölçeklenmez
   6 ve 7 numaralı sorgular `ALLOW FILTERING` gerektirir, bu da zayıf veri modellemesini gösterir

3. **Sıcak Bölüm Riski**
   Tek bölüm anahtarı `collection`, sıcak bölümlere neden olabilir
   Büyük koleksiyonlar tek düğümlere yoğunlaşacaktır
   Yük dengeleme için dağıtım stratejisi yoktur

### Sorgu Seviyesi Sorunlar

1. **ALLOW FILTERING Kullanımı** ⚠️
   İki sorgu türü (get_po, get_os) `ALLOW FILTERING` gerektirir
   Bu sorgular birden fazla bölümü tarar ve son derece pahalıdır
   Performans, veri boyutuyla doğrusal olarak düşer

2. **Verimsiz Erişim Kalıpları**
   Yaygın RDF sorgu kalıpları için optimizasyon yoktur
   Sık sorgu kombinasyonları için bileşik indeksler eksiktir
   Grafik geçiş kalıpları dikkate alınmamıştır

3. **Sorgu Optimizasyonu Eksikliği**
   Hazırlanmış ifade önbelleği yok
   Sorgu ipuçları veya optimizasyon stratejileri yok
   Basit LIMIT'in ötesinde sayfalama dikkate alınmamıştır

## Problem Tanımı

Mevcut Cassandra bilgi tabanı uygulaması, iki kritik performans darboğazına sahiptir:

### 1. Verimsiz get_po Sorgusu Performansı

`get_po(collection, p, o)` sorgusu, `ALLOW FILTERING` gerektirdiği için son derece verimsizdir:

```sql
SELECT s FROM triples WHERE collection = ? AND p = ? AND o = ? LIMIT 10 ALLOW FILTERING
```

**Neden bunun sorunlu olduğu:**
`ALLOW FILTERING`, Cassandra'nın koleksiyon içindeki tüm bölümleri taramasını zorlar.
Performans, veri boyutuyla doğrusal olarak düşer.
Bu, yaygın bir RDF sorgu desenidir (belirli bir öznelik-nesne ilişkisine sahip konuları bulmak).
Veri büyüdükçe kümede önemli bir yük oluşturur.

### 2. Kötü Kümeleme Stratejisi

Mevcut birincil anahtar `PRIMARY KEY (collection, s, p, o)`, minimum kümeleme faydası sağlar:

**Mevcut kümeleme ile ilgili sorunlar:**
Bölüm anahtarı olarak `collection`, verileri etkili bir şekilde dağıtmaz.
Çoğu koleksiyon, kümelemeyi etkisiz hale getiren çeşitli veriler içerir.
RDF sorgularındaki yaygın erişim kalıpları dikkate alınmamıştır.
Büyük koleksiyonlar, tek düğümlerde "sıcak" bölümler oluşturur.
Kümeleme sütunları (s, p, o), tipik grafik geçiş kalıpları için optimize edilmemiştir.

**Etkisi:**
Sorgular, veri yerelliğinden faydalanmaz.
Kötü önbellek kullanımı.
Küme düğümleri arasında düzensiz yük dağılımı.
Koleksiyonlar büyüdükçe ölçeklenebilirlik darboğazları.

## Önerilen Çözüm: 4-Tablolu Normalizasyon Stratejisi

### Genel Bakış

Tek `triples` tablosunu, belirli sorgu kalıpları için optimize edilmiş dört özel amaçlı tabloyla değiştirin. Bu, ikincil dizinlere ve ALLOW FILTERING'e olan ihtiyacı ortadan kaldırırken, tüm sorgu türleri için optimum performans sağlar. Dördüncü tablo, bileşik bölüm anahtarlarına rağmen verimli koleksiyon silme olanağı sağlar.

### Yeni Şema Tasarımı

**Tablo 1: Konu Odaklı Sorgular (triples_s)**
```sql
CREATE TABLE triples_s (
    collection text,
    s text,
    p text,
    o text,
    PRIMARY KEY ((collection, s), p, o)
);
```
**Optimize eder:** get_s, get_sp, get_os
**Bölüm Anahtarı:** (collection, s) - Yalnızca collection'dan daha iyi dağılım sağlar
**Kümeleme:** (p, o) - Bir konu için verimli öznelik/nesne aramalarını sağlar

**Tablo 2: Öznelik-Nesne Sorguları (triples_p)**
```sql
CREATE TABLE triples_p (
    collection text,
    p text,
    o text,
    s text,
    PRIMARY KEY ((collection, p), o, s)
);
```
**Optimize eder:** get_p, get_po (ALLOW FILTERING özelliğini ortadan kaldırır!)
**Bölüm Anahtarı:** (collection, p) - Öznitelik yoluyla doğrudan erişim
**Kümeleme:** (o, s) - Verimli nesne-özne geçişi

**Tablo 3: Nesne Odaklı Sorgular (triples_o)**
```sql
CREATE TABLE triples_o (
    collection text,
    o text,
    s text,
    p text,
    PRIMARY KEY ((collection, o), s, p)
);
```
**Optimize eder:** get_o
**Bölüm Anahtarı:** (collection, o) - Nesneye doğrudan erişim
**Kümeleme:** (s, p) - Verimli özne-yüklem geçişi

**Tablo 4: Koleksiyon Yönetimi ve SPO Sorguları (triples_collection)**
```sql
CREATE TABLE triples_collection (
    collection text,
    s text,
    p text,
    o text,
    PRIMARY KEY (collection, s, p, o)
);
```
**Optimize eder:** get_spo, delete_collection
**Bölüm Anahtarı:** sadece koleksiyon - Verimli koleksiyon seviyesindeki işlemleri sağlar.
**Kümeleme:** (s, p, o) - Standart üçlü sıralama
**Amaç:** Hem tam SPO aramaları için hem de silme indeksi olarak çift amaçlı kullanım.

### Sorgu Eşlemesi

| Orijinal Sorgu | Hedef Tablo | Performans İyileştirmesi |
|----------------|-------------|------------------------|
| get_all(collection) | triples_s | FİLTRELEME İZNİ VERİLEBİLİR (taramaya uygun) |
| get_s(collection, s) | triples_s | Doğrudan bölüm erişimi |
| get_p(collection, p) | triples_p | Doğrudan bölüm erişimi |
| get_o(collection, o) | triples_o | Doğrudan bölüm erişimi |
| get_sp(collection, s, p) | triples_s | Bölüm + kümeleme |
| get_po(collection, p, o) | triples_p | **Artık FİLTRELEME İZNİ YOK!** |
| get_os(collection, o, s) | triples_o | Bölüm + kümeleme |
| get_spo(collection, s, p, o) | triples_collection | Tam anahtar araması |
| delete_collection(collection) | triples_collection | İndeksi oku, tümünü toplu olarak sil |

### Koleksiyon Silme Stratejisi

Birleşik bölüm anahtarlarıyla, `DELETE FROM table WHERE collection = ?`'ı doğrudan çalıştıramayız. Bunun yerine:

1. **Okuma Aşaması:** Tüm üçlüleri saymak için `triples_collection` sorgusunu kullanın:
   ```sql
   SELECT s, p, o FROM triples_collection WHERE collection = ?
   ```
   Bu, `collection`'ın bu tablo için bölümleme anahtarı olması nedeniyle verimlidir.

2. **Silme Aşaması:** Her (s, p, o) üçlüsü için, tüm 4 tablodan, tam bölümleme anahtarlarını kullanarak silin:
   ```sql
   DELETE FROM triples_s WHERE collection = ? AND s = ? AND p = ? AND o = ?
   DELETE FROM triples_p WHERE collection = ? AND p = ? AND o = ? AND s = ?
   DELETE FROM triples_o WHERE collection = ? AND o = ? AND s = ? AND p = ?
   DELETE FROM triples_collection WHERE collection = ? AND s = ? AND p = ? AND o = ?
   ```
   Verimlilik için 100'lük gruplar halinde işlenir.

**Ayrılık Analizi:**
✅ Dağıtılmış bölümlerle optimum sorgu performansını korur.
✅ Büyük koleksiyonlar için "sıcak" bölümler yoktur.
❌ Daha karmaşık silme mantığı (okuyup sonra sil).
❌ Silme süresi, koleksiyon boyutuna orantılıdır.

### Avantajlar

1. **ALLOW FILTERING'i ortadan kaldırır** - Her sorgunun optimum bir erişim yolu vardır (get_all taraması hariç).
2. **İkincil İndeks Yok** - Her tablo, kendi sorgu deseninin indeksidir.
3. **Daha İyi Veri Dağılımı** - Bileşik bölüm anahtarları, yükü etkili bir şekilde dağıtır.
4. **Öngörülebilir Performans** - Sorgu süresi, toplam veriye değil, sonuç boyutuna orantılıdır.
5. **Cassandra'nın Güçlerinden Yararlanır** - Cassandra'nın mimarisi için tasarlanmıştır.
6. **Koleksiyon Silme İşlemini Etkinleştirir** - triples_collection, silme indeksi olarak hizmet eder.

## Uygulama Planı

### Değiştirilmesi Gereken Dosyalar

#### Birincil Uygulama Dosyası

**`trustgraph-flow/trustgraph/direct/cassandra_kg.py`** - Tamamen yeniden yazılması gerekir.

**Yeniden Düzenlenmesi Gereken Mevcut Yöntemler:**
```python
# Schema initialization
def init(self) -> None  # Replace single table with three tables

# Insert operations
def insert(self, collection, s, p, o) -> None  # Write to all three tables

# Query operations (API unchanged, implementation optimized)
def get_all(self, collection, limit=50)      # Use triples_by_subject
def get_s(self, collection, s, limit=10)     # Use triples_by_subject
def get_p(self, collection, p, limit=10)     # Use triples_by_po
def get_o(self, collection, o, limit=10)     # Use triples_by_object
def get_sp(self, collection, s, p, limit=10) # Use triples_by_subject
def get_po(self, collection, p, o, limit=10) # Use triples_by_po (NO ALLOW FILTERING!)
def get_os(self, collection, o, s, limit=10) # Use triples_by_subject
def get_spo(self, collection, s, p, o, limit=10) # Use triples_by_subject

# Collection management
def delete_collection(self, collection) -> None  # Delete from all three tables
```

#### Entegrasyon Dosyaları (Herhangi Bir Mantıksal Değişiklik Gerekmiyor)

**`trustgraph-flow/trustgraph/storage/triples/cassandra/write.py`**
Herhangi bir değişiklik gerekmiyor - mevcut KnowledgeGraph API'sini kullanır.
Performans iyileştirmelerinden otomatik olarak faydalanır.

**`trustgraph-flow/trustgraph/query/triples/cassandra/service.py`**
Herhangi bir değişiklik gerekmiyor - mevcut KnowledgeGraph API'sini kullanır.
Performans iyileştirmelerinden otomatik olarak faydalanır.

### Güncelleme Gerektiren Test Dosyaları

#### Birim Testleri
**`tests/unit/test_storage/test_triples_cassandra_storage.py`**
Şema değişiklikleri için test beklentilerini güncelleyin.
Çok tablolu tutarlılık için testler ekleyin.
Sorgu planlarında ALLOW FILTERING kullanımını doğrulayın.

**`tests/unit/test_query/test_triples_cassandra_query.py`**
Performans doğrulama ifadelerini güncelleyin.
Tüm 8 sorgu desenini yeni tablolara karşı test edin.
Sorgu yönlendirmesinin doğru tablolara yapıldığını doğrulayın.

#### Entegrasyon Testleri
**`tests/integration/test_cassandra_integration.py`**
Yeni şemayla uçtan uca testler.
Performans karşılaştırma ölçümleri.
Tablolar arasındaki veri tutarlılığının doğrulanması.

**`tests/unit/test_storage/test_cassandra_config_integration.py`**
Şema doğrulama testlerini güncelleyin.
Geçiş senaryolarını test edin.

### Uygulama Stratejisi

#### 1. Aşama: Şema ve Temel Yöntemler
1. **`init()` yöntemini yeniden yazın** - Dört tablo oluşturun, bir yerine.
2. **`insert()` yöntemini yeniden yazın** - Tüm dört tabloya toplu yazma işlemleri.
3. **Hazırlanmış ifadeleri uygulayın** - Optimum performans için.
4. **Tablo yönlendirme mantığını ekleyin** - Sorguları en uygun tablolara yönlendirin.
5. **Toplu silme işlemini uygulayın** - triples_collection'dan okuyun, tüm tablolardan toplu olarak silin.

#### 2. Aşama: Sorgu Yöntemi Optimizasyonu
1. **Her get_* yöntemini yeniden yazın** - En uygun tabloyu kullanmak için.
2. **Tüm ALLOW FILTERING kullanımını kaldırın**.
3. **Verimli kümeleme anahtar kullanımı uygulayın**.
4. **Sorgu performansını kaydetme özelliğini ekleyin**.

#### 3. Aşama: Koleksiyon Yönetimi
1. **`delete_collection()`'ı güncelleyin** - Tüm üç tablodan kaldırın.
2. **Tutarlılık doğrulamasını ekleyin** - Tüm tabloların senkronize kalmasını sağlayın.
3. **Toplu işlemleri uygulayın** - Atomik çok tablolu işlemler için.

### Önemli Uygulama Detayları

#### Toplu Yazma Stratejisi
```python
def insert(self, collection, s, p, o):
    batch = BatchStatement()

    # Insert into all four tables
    batch.add(self.insert_subject_stmt, (collection, s, p, o))
    batch.add(self.insert_po_stmt, (collection, p, o, s))
    batch.add(self.insert_object_stmt, (collection, o, s, p))
    batch.add(self.insert_collection_stmt, (collection, s, p, o))

    self.session.execute(batch)
```

#### Sorgu Yönlendirme Mantığı
```python
def get_po(self, collection, p, o, limit=10):
    # Route to triples_p table - NO ALLOW FILTERING!
    return self.session.execute(
        self.get_po_stmt,
        (collection, p, o, limit)
    )

def get_spo(self, collection, s, p, o, limit=10):
    # Route to triples_collection table for exact SPO lookup
    return self.session.execute(
        self.get_spo_stmt,
        (collection, s, p, o, limit)
    )
```

#### Koleksiyon Silme Mantığı
```python
def delete_collection(self, collection):
    # Step 1: Read all triples from collection table
    rows = self.session.execute(
        f"SELECT s, p, o FROM {self.collection_table} WHERE collection = %s",
        (collection,)
    )

    # Step 2: Batch delete from all 4 tables
    batch = BatchStatement()
    count = 0

    for row in rows:
        s, p, o = row.s, row.p, row.o

        # Delete using full partition keys for each table
        batch.add(SimpleStatement(
            f"DELETE FROM {self.subject_table} WHERE collection = ? AND s = ? AND p = ? AND o = ?"
        ), (collection, s, p, o))

        batch.add(SimpleStatement(
            f"DELETE FROM {self.po_table} WHERE collection = ? AND p = ? AND o = ? AND s = ?"
        ), (collection, p, o, s))

        batch.add(SimpleStatement(
            f"DELETE FROM {self.object_table} WHERE collection = ? AND o = ? AND s = ? AND p = ?"
        ), (collection, o, s, p))

        batch.add(SimpleStatement(
            f"DELETE FROM {self.collection_table} WHERE collection = ? AND s = ? AND p = ? AND o = ?"
        ), (collection, s, p, o))

        count += 1

        # Execute every 100 triples to avoid oversized batches
        if count % 100 == 0:
            self.session.execute(batch)
            batch = BatchStatement()

    # Execute remaining deletions
    if count % 100 != 0:
        self.session.execute(batch)

    logger.info(f"Deleted {count} triples from collection {collection}")
```

#### Hazırlanmış İfade Optimizasyonu
```python
def prepare_statements(self):
    # Cache prepared statements for better performance
    self.insert_subject_stmt = self.session.prepare(
        f"INSERT INTO {self.subject_table} (collection, s, p, o) VALUES (?, ?, ?, ?)"
    )
    self.insert_po_stmt = self.session.prepare(
        f"INSERT INTO {self.po_table} (collection, p, o, s) VALUES (?, ?, ?, ?)"
    )
    self.insert_object_stmt = self.session.prepare(
        f"INSERT INTO {self.object_table} (collection, o, s, p) VALUES (?, ?, ?, ?)"
    )
    self.insert_collection_stmt = self.session.prepare(
        f"INSERT INTO {self.collection_table} (collection, s, p, o) VALUES (?, ?, ?, ?)"
    )
    # ... query statements
```

## Göç Stratejisi

### Veri Göç Yaklaşımı

#### Seçenek 1: Mavi-Yeşil Dağıtım (Önerilen)
1. **Yeni şemayı mevcut olanın yanında dağıtın** - Geçici olarak farklı tablo adları kullanın
2. **Çift yazma dönemi** - Geçiş sırasında hem eski hem de yeni şemalara yazın
3. **Arka planda veri taşıma** - Mevcut verileri yeni tablolara kopyalayın
4. **Okuma yönlendirmesini değiştirin** - Veriler taşındıktan sonra sorguları yeni tablolara yönlendirin
5. **Eski tabloları kaldırın** - Doğrulama süresinden sonra

#### Seçenek 2: Yerinde Göç
1. **Şema ekleme** - Yeni tabloları mevcut anahtar uzayında oluşturun
2. **Veri taşıma betiği** - Eski tablodan yeni tablolara toplu olarak veri kopyalayın
3. **Uygulama güncellemesi** - Göç tamamlandıktan sonra yeni kodu dağıtın
4. **Eski tablo temizliği** - Eski tabloyu ve indeksleri kaldırın

### Geriye Dönük Uyumluluk

#### Dağıtım Stratejisi
```python
# Environment variable to control table usage during migration
USE_LEGACY_TABLES = os.getenv('CASSANDRA_USE_LEGACY', 'false').lower() == 'true'

class KnowledgeGraph:
    def __init__(self, ...):
        if USE_LEGACY_TABLES:
            self.init_legacy_schema()
        else:
            self.init_optimized_schema()
```

#### Göç Script'i
```python
def migrate_data():
    # Read from old table
    old_triples = session.execute("SELECT collection, s, p, o FROM triples")

    # Batch write to new tables
    for batch in batched(old_triples, 100):
        batch_stmt = BatchStatement()
        for row in batch:
            # Add to all three new tables
            batch_stmt.add(insert_subject_stmt, row)
            batch_stmt.add(insert_po_stmt, (row.collection, row.p, row.o, row.s))
            batch_stmt.add(insert_object_stmt, (row.collection, row.o, row.s, row.p))
        session.execute(batch_stmt)
```

### Doğrulama Stratejisi

#### Veri Tutarlılık Kontrolleri
```python
def validate_migration():
    # Count total records in old vs new tables
    old_count = session.execute("SELECT COUNT(*) FROM triples WHERE collection = ?", (collection,))
    new_count = session.execute("SELECT COUNT(*) FROM triples_by_subject WHERE collection = ?", (collection,))

    assert old_count == new_count, f"Record count mismatch: {old_count} vs {new_count}"

    # Spot check random samples
    sample_queries = generate_test_queries()
    for query in sample_queries:
        old_result = execute_legacy_query(query)
        new_result = execute_optimized_query(query)
        assert old_result == new_result, f"Query results differ for {query}"
```

## Test Stratejisi

### Performans Testi

#### Benchmark Senaryoları
1. **Sorgu Performansı Karşılaştırması**
   Tüm 8 sorgu türü için performans metrikleri (önce/sonra)
   get_po performans iyileştirmesine odaklanın (ALLOW FILTERING'i kaldırın)
   Çeşitli veri boyutları altında sorgu gecikmesini ölçün

2. **Yük Testi**
   Eşzamanlı sorgu yürütme
   Toplu işlemlerle yazma hızı
   Bellek ve CPU kullanımı

3. **Ölçeklenebilirlik Testi**
   Artan koleksiyon boyutlarıyla performans
   Çoklu koleksiyon sorgu dağıtımı
   Küme düğümü kullanımı

#### Test Veri Kümeleri
**Küçük:** Koleksiyon başına 10K üçlü
**Orta:** Koleksiyon başına 100K üçlü
**Büyük:** Koleksiyon başına 1M+ üçlü
**Çoklu koleksiyonlar:** Test bölüm dağıtımı

### Fonksiyonel Test

#### Birim Testi Güncellemeleri
```python
# Example test structure for new implementation
class TestCassandraKGPerformance:
    def test_get_po_no_allow_filtering(self):
        # Verify get_po queries don't use ALLOW FILTERING
        with patch('cassandra.cluster.Session.execute') as mock_execute:
            kg.get_po('test_collection', 'predicate', 'object')
            executed_query = mock_execute.call_args[0][0]
            assert 'ALLOW FILTERING' not in executed_query

    def test_multi_table_consistency(self):
        # Verify all tables stay in sync
        kg.insert('test', 's1', 'p1', 'o1')

        # Check all tables contain the triple
        assert_triple_exists('triples_by_subject', 'test', 's1', 'p1', 'o1')
        assert_triple_exists('triples_by_po', 'test', 'p1', 'o1', 's1')
        assert_triple_exists('triples_by_object', 'test', 'o1', 's1', 'p1')
```

#### Entegrasyon Testi Güncellemeleri
```python
class TestCassandraIntegration:
    def test_query_performance_regression(self):
        # Ensure new implementation is faster than old
        old_time = benchmark_legacy_get_po()
        new_time = benchmark_optimized_get_po()
        assert new_time < old_time * 0.5  # At least 50% improvement

    def test_end_to_end_workflow(self):
        # Test complete write -> query -> delete cycle
        # Verify no performance degradation in integration
```

### Geri Alma Planı

#### Hızlı Geri Alma Stratejisi
1. **Ortam değişkeni geçişi** - Eski tablolara hemen geri dönün.
2. **Eski tablolara devam edin** - Performans kanıtlanana kadar silmeyin.
3. **İzleme uyarıları** - Hata oranlarına/gecikmelere göre otomatik geri alma tetikleyicileri.

#### Geri Alma Doğrulama
```python
def rollback_to_legacy():
    # Set environment variable
    os.environ['CASSANDRA_USE_LEGACY'] = 'true'

    # Restart services to pick up change
    restart_cassandra_services()

    # Validate functionality
    run_smoke_tests()
```

## Riskler ve Dikkat Edilmesi Gerekenler

### Performans Riskleri
**Yazma gecikmesi artışı** - Her eklemeye 4 yazma işlemi (3 tablolu yaklaşıma göre %33 daha fazla)
**Depolama alanı kullanımı** - 4 kat daha fazla depolama alanı gereksinimi (3 tablolu yaklaşıma göre %33 daha fazla)
**Toplu yazma hataları** - Uygun hata yönetimi gereklidir
**Silme karmaşıklığı** - Koleksiyon silme işlemi, okuma-sonra-silme döngüsü gerektirir

### İşletim Riskleri
**Geçiş karmaşıklığı** - Büyük veri kümeleri için veri geçişi
**Tutarlılık sorunları** - Tüm tabloların senkronize olduğundan emin olmak
**İzleme eksiklikleri** - Çok tablolu işlemler için yeni metrikler gereklidir

### Azaltma Stratejileri
1. **Aşamalı dağıtım** - Küçük koleksiyonlarla başlayın
2. **Kapsamlı izleme** - Tüm performans metriklerini takip edin
3. **Otomatik doğrulama** - Sürekli tutarlılık kontrolü
4. **Hızlı geri alma yeteneği** - Ortam tabanlı tablo seçimi

## Başarı Kriterleri

### Performans İyileştirmeleri
[ ] **ALLOW FILTERING'i ortadan kaldırın** - get_po ve get_os sorguları filtreleme olmadan çalışır
[ ] **Sorgu gecikmesi azaltma** - Sorgu yanıt sürelerinde %50 veya daha fazla iyileşme
[ ] **Daha iyi yük dağılımı** - Hiçbir "sıcak" bölüm yok, küme düğümleri arasında eşit yük dağılımı
[ ] **Ölçeklenebilir performans** - Sorgu süresi, toplam veri miktarı yerine sonuç büyüklüğüne orantılı

### Fonksiyonel Gereksinimler
[ ] **API uyumluluğu** - Tüm mevcut kod, herhangi bir değişiklik olmadan çalışmaya devam eder
[ ] **Veri tutarlılığı** - Tüm üç tablo senkronize kalır
[ ] **Sıfır veri kaybı** - Geçiş, tüm mevcut üçlüleri korur
[ ] **Geriye dönme uyumluluğu** - Eski şemaya geri dönme yeteneği

### İşletim Gereksinimleri
[ ] **Güvenli geçiş** - Geri alma yeteneği olan mavi-yeşil dağıtım
[ ] **İzleme kapsamı** - Çok tablolu işlemler için kapsamlı metrikler
[ ] **Test kapsamı** - Tüm sorgu kalıpları, performans kıyaslamalarıyla test edilmiştir
[ ] **Belgeleme** - Güncellenmiş dağıtım ve işletim prosedürleri

## Zaman Çizelgesi

### 1. Aşama: Uygulama
[ ] `cassandra_kg.py`'ı çok tablolu şemayla yeniden yazın
[ ] Toplu yazma işlemlerini uygulayın
[ ] Hazırlanmış ifade optimizasyonunu ekleyin
[ ] Birim testlerini güncelleyin

### 2. Aşama: Entegrasyon Testi
[ ] Entegrasyon testlerini güncelleyin
[ ] Performans kıyaslaması
[ ] Gerçekçi veri hacimleriyle yük testi
[ ] Veri tutarlılığı için doğrulama betikleri

### 3. Aşama: Geçiş Planlaması
[ ] Mavi-yeşil dağıtım betikleri
[ ] Veri geçiş araçları
[ ] İzleme panosu güncellemeleri
[ ] Geri alma prosedürleri

### 4. Aşama: Üretim Dağıtımı
[ ] Üretime aşamalı dağıtım
[ ] Performans izleme ve doğrulama
[ ] Eski tabloların temizlenmesi
[ ] Belgeleme güncellemeleri

## Sonuç

Bu çok tablolu normalleştirme stratejisi, doğrudan iki kritik performans darboğazını ele almaktadır:

1. **Pahalı ALLOW FILTERING'i ortadan kaldırır** ve her sorgu kalıbı için optimum tablo yapıları sağlar.
2. **Kompozit bölüm anahtarları aracılığıyla kümeleme etkinliğini artırır** ve yükü düzgün bir şekilde dağıtır.

Bu yaklaşım, Cassandra'nın güçlü yönlerinden yararlanırken, mevcut kodun performans iyileştirmelerinden otomatik olarak yararlanmasını sağlayan tam API uyumluluğunu korur.
