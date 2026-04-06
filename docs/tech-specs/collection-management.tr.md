# Koleksiyon Yönetimi Teknik Özellikleri

## Genel Bakış

Bu özellik, TrustGraph için koleksiyon yönetimi yeteneklerini tanımlar ve açık koleksiyon oluşturulmasını gerektirir ve koleksiyon yaşam döngüsü üzerinde doğrudan kontrol sağlar. Koleksiyonlar, uygun veri ambarı ve tüm depolama arka uçları arasındaki senkronizasyonu sağlamak için kullanmadan önce açıkça oluşturulmalıdır. Bu özellik, dört birincil kullanım senaryosunu destekler:

1. **Koleksiyon Oluşturma**: Veri depolamadan önce koleksiyonları açıkça oluşturun
2. **Koleksiyon Listeleme**: Sistemdeki mevcut tüm koleksiyonları görüntüleyin
3. **Koleksiyon Meta Veri Yönetimi**: Koleksiyon adlarını, açıklamalarını ve etiketlerini güncelleyin
4. **Koleksiyon Silme**: Koleksiyonları ve bunlara bağlı verileri tüm depolama türlerinden kaldırın

## Hedefler

**Açık Koleksiyon Oluşturma**: Verilerin depolanabilmesi için koleksiyonların oluşturulmasını gerektirir
**Depolama Senkronizasyonu**: Koleksiyonların tüm depolama arka uçlarında (vektörler, nesneler, üçlüler) mevcut olduğundan emin olun
**Koleksiyon Görünürlüğü**: Kullanıcıların ortamlarındaki tüm koleksiyonları listelemesini ve incelemesini sağlayın
**Koleksiyon Temizleme**: Artık gerekli olmayan koleksiyonların silinmesine izin verin
**Koleksiyon Organizasyonu**: Daha iyi koleksiyon takibi ve keşfi için etiketleri ve kategorileri destekleyin
**Meta Veri Yönetimi**: İşletimsel açıklık için koleksiyonlarla anlamlı meta verileri ilişkilendirin
**Koleksiyon Keşfi**: Filtreleme ve arama yoluyla belirli koleksiyonları bulmayı kolaylaştırın
**İşletim Şeffaflığı**: Koleksiyon yaşam döngüsü ve kullanımı hakkında net görünürlük sağlayın
**Kaynak Yönetimi**: Kullanılmayan koleksiyonları temizleyerek kaynak kullanımını optimize etmeyi sağlayın
**Veri Bütünlüğü**: Meta veri takibi olmadan depolamada yetim koleksiyonların oluşmasını önleyin

## Arka Plan

Geçmişte, TrustGraph'taki koleksiyonlar, veri yükleme işlemleri sırasında örtülü olarak oluşturuluyordu ve bu da koleksiyonların depolama arka uçlarında, ancak kütüphanecide ilgili meta verilere sahip olmadan var olabileceği senkronizasyon sorunlarına yol açıyordu. Bu durum, yönetim zorlukları ve potansiyel olarak yetim veri sorunları yaratmıştır.

Açık koleksiyon oluşturma modeli, bu sorunları aşağıdaki şekilde ele alır:
Koleksiyonların `tg-set-collection` aracılığıyla kullanmadan önce oluşturulmasını gerektirir
Koleksiyon oluşturmayı tüm depolama arka uçlarına yayınlar
Kütüphaneci meta verileri ile depolama arasındaki senkronize durumu korur
Var olmayan koleksiyonlara yazmayı engeller
Açık koleksiyon yaşam döngüsü yönetimi sağlar

Bu özellik, açık koleksiyon yönetimi modelini tanımlar. Açık koleksiyon oluşturmayı gerektirerek, TrustGraph şunları sağlar:
Koleksiyonlar, oluşturulmadan itibaren kütüphaneci meta verilerinde takip edilir
Tüm depolama arka uçları, verileri almadan önce koleksiyonların varlığından haberdardır
Depolamada yetim koleksiyonların oluşması engellenir
Koleksiyon yaşam döngüsü üzerinde açık işletimsel görünürlük ve kontrol sağlanır
Var olmayan koleksiyonlara yapılan işlemlerde tutarlı hata işleme sağlanır

## Teknik Tasarım

### Mimari

Koleksiyon yönetimi sistemi, mevcut TrustGraph altyapısının içinde uygulanacaktır:

1. **Kütüphaneci Hizmeti Entegrasyonu**
   Koleksiyon yönetimi işlemleri, mevcut kütüphaneci hizmetine eklenecektir
   Yeni bir hizmet gerektirmez - mevcut kimlik doğrulama ve erişim kalıplarından yararlanır
   Koleksiyon listeleme, silme ve meta veri yönetimi işlemlerini işler

   Modül: trustgraph-librarian

2. **Cassandra Koleksiyon Meta Veri Tablosu**
   Mevcut kütüphaneci anahtar alanındaki yeni bir tablo
   Kullanıcı kapsamlı erişim ile koleksiyon meta verilerini depolar
   Birincil anahtar: Doğru çoklu kiracılık için (user_id, collection_id)

   Modül: trustgraph-librarian

3. **Koleksiyon Yönetimi CLI**
   Koleksiyon işlemleri için komut satırı arayüzü
   Listeleme, silme, etiketleme ve etiket yönetimi komutları sağlar
   Mevcut CLI çerçevesiyle entegre olur

   Modül: trustgraph-cli

### Veri Modelleri

#### Cassandra Koleksiyon Meta Veri Tablosu

Koleksiyon meta verileri, kütüphaneci anahtar alanındaki yapılandırılmış bir Cassandra tablosunda saklanacaktır:

```sql
CREATE TABLE collections (
    user text,
    collection text,
    name text,
    description text,
    tags set<text>,
    created_at timestamp,
    updated_at timestamp,
    PRIMARY KEY (user, collection)
);
```

Tablo yapısı:
**user**: **collection**: Birincil bileşik anahtar, kullanıcı yalıtımını sağlar
**name**: İnsan tarafından okunabilir koleksiyon adı
**description**: Koleksiyonun amacının ayrıntılı açıklaması
**tags**: Kategorizasyon ve filtreleme için etiket kümesi
**created_at**: Koleksiyon oluşturma zaman damgası
**updated_at**: Son değişiklik zaman damgası

Bu yaklaşım şunları sağlar:
Kullanıcı yalıtımı ile çoklu kiracılı koleksiyon yönetimi
Kullanıcı ve koleksiyon bazında verimli sorgulama
Düzenleme için esnek etiketleme sistemi
İşletimsel bilgiler için yaşam döngüsü takibi

#### Koleksiyon Yaşam Döngüsü

Koleksiyonlar, veri işlemlerine başlamadan önce kütüphanede açıkça oluşturulmalıdır:

1. **Koleksiyon Oluşturma** (İki Yol):

   **Yol A: Kullanıcı Tarafından Başlatılan Oluşturma** `tg-set-collection` aracılığıyla:
   Kullanıcı, koleksiyon kimliği, adı, açıklaması ve etiketleri sağlar
   Kütüphane, `collections` tablosunda bir meta veri kaydı oluşturur
   Kütüphane, tüm depolama arka uçlarına "create-collection" mesajını gönderir
   Tüm depolama işlemcileri, koleksiyonu oluşturur ve başarıyı onaylar
   Koleksiyon artık veri işlemleri için hazırdır

   **Yol B: Belge Gönderimi Üzerinde Otomatik Oluşturma**:
   Kullanıcı, bir koleksiyon kimliği belirten bir belge gönderir
   Kütüphane, koleksiyonun meta veri tablosunda mevcut olup olmadığını kontrol eder
   Yoksa: Kütüphane, varsayılanlarla (ad=koleksiyon_kimliği, boş açıklama/etiketler) bir meta veri oluşturur
   Kütüphane, tüm depolama arka uçlarına "create-collection" mesajını gönderir
   Tüm depolama işlemcileri, koleksiyonu oluşturur ve başarıyı onaylar
   Belge işleme, koleksiyonun artık oluşturulduğu şekilde devam eder

   Her iki yol da, veri işlemlerine izin verilmeden önce koleksiyonun kütüphane meta verilerinde VE tüm depolama arka uçlarında mevcut olmasını sağlar.

2. **Depolama Doğrulama**: Yazma işlemleri, koleksiyonun mevcut olup olmadığını doğrular:
   Depolama işlemcileri, yazmayı kabul etmeden önce koleksiyonun durumunu kontrol eder
   Mevcut olmayan koleksiyonlara yapılan yazılar hata döndürür
   Bu, doğrudan yazmaların kütüphanenin koleksiyon oluşturma mantığını atlamasını engeller

3. **Sorgu Davranışı**: Sorgu işlemleri, mevcut olmayan koleksiyonları zarif bir şekilde işler:
   Mevcut olmayan koleksiyonlara yapılan sorgular boş sonuçlar döndürür
   Sorgu işlemleri için hata oluşmaz
   Koleksiyonun mevcut olması gerekmeksizin keşfetmeye olanak tanır

4. **Meta Veri Güncellemeleri**: Kullanıcılar, koleksiyon oluşturulduktan sonra koleksiyon meta verilerini güncelleyebilir:
   Adı, açıklamasını ve etiketleri `tg-set-collection` aracılığıyla güncelleyin
   Güncellemeler yalnızca kütüphane meta verilerine uygulanır
   Depolama arka uçları koleksiyonu korur, ancak meta veri güncellemeleri yayılmaz

5. **Açık Silme**: Kullanıcılar, koleksiyonları `tg-delete-collection` aracılığıyla siler:
   Kütüphane, tüm depolama arka uçlarına "delete-collection" mesajını gönderir
   Tüm depolama işlemcilerinden onay bekler
   Depolama temizliği tamamlandıktan SONRA yalnızca kütüphane meta veri kaydını siler
   Depoda hiçbir verinin kaybolmamasını sağlar

**Temel İlke**: Kütüphane, koleksiyon oluşturma için tek kontrol noktasıdır. Kullanıcı komutu veya belge gönderimi ile başlatılıp başlatılmadığına bakılmaksızın, kütüphane, veri işlemlerine izin vermeden önce uygun meta veri takibi ve depolama arka uç senkronizasyonunu sağlar.

Gerekli işlemler:
**Koleksiyon Oluşturma**: `tg-set-collection` aracılığıyla kullanıcı işlemi VEYA belge gönderimi üzerine otomatik
**Koleksiyon Meta Verilerini Güncelleme**: Adı, açıklaması ve etiketleri değiştirmek için kullanıcı işlemi
**Koleksiyonu Silme**: Koleksiyonu ve tüm depolarda verilerini kaldırmak için kullanıcı işlemi
**Koleksiyonları Listeleme**: Etiketlere göre filtreleme ile koleksiyonları görüntülemek için kullanıcı işlemi

#### Çoklu Depo Koleksiyon Yönetimi

Koleksiyonlar, TrustGraph'ta birden çok depolama arka uçunda bulunur:
**Vektör Depoları** (Qdrant, Milvus, Pinecone): Gömme ve vektör verilerini depolar
**Nesne Depoları** (Cassandra): Belge ve dosya verilerini depolar
**Üçlü Depolar** (Cassandra, Neo4j, Memgraph, FalkorDB): Grafik/RDF verilerini depolar

Her bir mağaza türü aşağıdaki işlemleri uygular:
**Koleksiyon Durumu Takibi**: Hangi koleksiyonların mevcut olduğunu takip etme
**Koleksiyon Oluşturma**: "koleksiyon oluştur" işlemlerini kabul etme ve işleme alma
**Koleksiyon Doğrulama**: Yazma işlemlerini kabul etmeden önce koleksiyonun varlığını kontrol etme
**Koleksiyon Silme**: Belirtilen koleksiyon için tüm verileri silme

Kütüphaneci hizmeti, tüm mağaza türleri arasında koleksiyon işlemlerini koordine ederek şunları sağlar:
Koleksiyonlar, kullanmadan önce tüm arka uçlarda oluşturulur
Tüm arka uçlar, oluşturma işleminden sonra başarıyı doğrular
Depolama türleri arasında senkronize koleksiyon yaşam döngüsü
Koleksiyonlar mevcut olmadığında tutarlı hata işleme

#### Depolama Türüne Göre Koleksiyon Durumu Takibi

Her depolama arka ucu, yeteneklerine bağlı olarak koleksiyon durumunu farklı şekilde takip eder:

**Cassandra Üçlü Deposu:**
Mevcut `triples_collection` tablosunu kullanır
Koleksiyon oluşturulduğunda sistem işaretleyici üçlüsü oluşturur
Sorgu: `SELECT collection FROM triples_collection WHERE collection = ? LIMIT 1`
Koleksiyonun varlığı için verimli tek bölüm kontrolü

**Qdrant/Milvus/Pinecone Vektör Depoları:**
Yerel koleksiyon API'leri, varlık kontrolü sağlar
Koleksiyonlar, uygun vektör yapılandırmasıyla oluşturulur
`collection_exists()` yöntemi, depolama API'sini kullanır
Koleksiyon oluşturma, boyut gereksinimlerini doğrular

**Neo4j/Memgraph/FalkorDB Grafik Depoları:**
Koleksiyonları takip etmek için `:CollectionMetadata` düğümlerini kullanır
Düğüm özellikleri: `{user, collection, created_at}`
Sorgu: `MATCH (c:CollectionMetadata {user: $user, collection: $collection})`
Veri düğümlerinden ayrı olarak, temiz bir ayrım sağlar
Koleksiyon listeleme ve doğrulama için verimli bir yol sağlar

**Cassandra Nesne Deposu:**
Koleksiyon meta veri tablosunu veya işaretçi satırlarını kullanır
Üçlü depoya benzer bir desen
Veri yazmadan önce koleksiyonu doğrular

### API'ler

Koleksiyon Yönetimi API'leri (Kütüphaneci):
**Koleksiyon Oluşturma/Güncelleme**: Yeni bir koleksiyon oluşturma veya mevcut meta verileri `tg-set-collection` aracılığıyla güncelleme
**Koleksiyonları Listeleme**: İsteğe bağlı etiket filtrelemesiyle bir kullanıcı için koleksiyonları alma
**Koleksiyon Silme**: Koleksiyonu ve ilişkili verileri silme, tüm mağaza türlerine kadar yayılma

Depolama Yönetimi API'leri (Tüm Depolama İşlemcileri):
**Koleksiyon Oluşturma**: "koleksiyon oluştur" işlemini işleme, depolamada koleksiyonu oluşturma
**Koleksiyon Silme**: "koleksiyon sil" işlemini işleme, tüm koleksiyon verilerini silme
**Koleksiyon Varlığı Kontrolü**: Yazma işlemlerini kabul etmeden önce iç doğrulama

Veri İşlemleri API'leri (Değiştirilmiş Davranış):
**Yazma API'leri**: Veriyi kabul etmeden önce koleksiyonun varlığını doğrulama, mevcut değilse hata döndürme
**Sorgu API'leri**: Hata olmadan mevcut olmayan koleksiyonlar için boş sonuçlar döndürme

### Uygulama Ayrıntıları

Uygulama, hizmet entegrasyonu ve CLI komut yapısı için mevcut TrustGraph desenlerini takip edecektir.

#### Koleksiyon Silme Yayılımı

Bir kullanıcı, kütüphaneci hizmeti aracılığıyla koleksiyon silme işlemini başlattığında:

1. **Meta Veri Doğrulama**: Koleksiyonun var olduğunu ve kullanıcının silme izni olup olmadığını doğrulayın
2. **Depolama Yayılımı**: Kütüphaneci, tüm depolama yazıcıları arasında silme işlemini koordine eder:
   Vektör depolama yazıcısı: Kullanıcı ve koleksiyon için gömülmeleri ve vektör indekslerini kaldırır
   Nesne depolama yazıcısı: Kullanıcı ve koleksiyon için belgeleri ve dosyaları kaldırır
   Üçlü depolama yazıcısı: Kullanıcı ve koleksiyon için grafik verilerini ve üçlüleri kaldırır
3. **Meta Veri Temizleme**: Cassandra'dan koleksiyon meta veri kaydını kaldırır
4. **Hata İşleme**: Herhangi bir depolama silme işlemi başarısız olursa, geri alma veya yeniden deneme mekanizmaları aracılığıyla tutarlılığı koruyun

#### Koleksiyon Yönetimi Arayüzü

**⚠️ ESKİ YAKLAŞIM - YAPILANDIRMA TEMELLİ DESENE DEĞİŞTİRİLDİ**

Aşağıda açıklanan kuyruk tabanlı mimari, `CollectionConfigHandler` kullanarak bir yapılandırma tabanlı yaklaşımla değiştirilmiştir. Tüm depolama arka uçları artık özel yönetim kuyrukları yerine yapılandırma itme mesajları aracılığıyla koleksiyon güncellemeleri alır.

~~Tüm depolama yazıcıları, ortak bir şemaya sahip standart bir koleksiyon yönetimi arayüzü uygular:~~

~~**Mesaj Şeması (`StorageManagementRequest`):**~~
```json
{
  "operation": "create-collection" | "delete-collection",
  "user": "user123",
  "collection": "documents-2024"
}
```

~~**Sıra Mimarisi:**~~
~~**Vektör Depolama Yönetimi Kuyruğu** (`vector-storage-management`): Vektör/gömme depoları~~
~~**Nesne Depolama Yönetimi Kuyruğu** (`object-storage-management`): Nesne/belge depoları~~
~~**Üçlü Depolama Yönetimi Kuyruğu** (`triples-storage-management`): Grafik/RDF depoları~~
~~**Depolama Yanıt Kuyruğu** (`storage-management-response`): Tüm yanıtlar buraya gönderilir~~

**Mevcut Uygulama:**

Tüm depolama arka uçları artık `CollectionConfigHandler` kullanır:
**Yapılandırma İtme Entegrasyonu**: Depolama hizmetleri, yapılandırma itme bildirimleri için kayıt yaptırır
**Otomatik Senkronizasyon**: Koleksiyonlar, yapılandırma değişikliklerine göre oluşturulur/silinir
**Bildirimsel Model**: Koleksiyonlar, yapılandırma hizmetinde tanımlanır, arka uçlar eşleşmesi için senkronize olur
**İstek/Yanıt Yok**: Koordinasyon yükünü ve yanıt takibini ortadan kaldırır
**Koleksiyon Durumu Takibi**: `known_collections` önbelleği aracılığıyla sürdürülür
**İdeolojik İşlemler**: Aynı yapılandırmayı birden çok kez işlemek güvenlidir

Her depolama arka ucu şunları uygular:
`create_collection(user: str, collection: str, metadata: dict)` - Koleksiyon yapılarını oluşturur
`delete_collection(user: str, collection: str)` - Tüm koleksiyon verilerini kaldırır
`collection_exists(user: str, collection: str) -> bool` - Yazmadan önce doğrular

#### Cassandra Üçlü Depolama Yeniden Düzenlemesi

Bu uygulamanın bir parçası olarak, Cassandra üçlü depolama, bir koleksiyon başına tablo modelinden tek bir tablo modeline yeniden düzenlenecektir:

**Mevcut Mimari:**
Kullanıcı başına bir anahtar alanı, her koleksiyon için ayrı bir tablo
Şema: `(s, p, o)` ile `PRIMARY KEY (s, p, o)`
Tablo adları: Kullanıcı koleksiyonları, ayrı Cassandra tabloları haline gelir

**Yeni Mimari:**
Kullanıcı başına bir anahtar alanı, tüm koleksiyonlar için tek bir "üçlüler" tablosu
Şema: `(collection, s, p, o)` ile `PRIMARY KEY (collection, s, p, o)`
Koleksiyon izolasyonu, koleksiyon bölümlendirmesi yoluyla sağlanır

**Gerekli Değişiklikler:**

1. **TrustGraph Sınıfı Yeniden Düzenlemesi** (`trustgraph/direct/cassandra.py`):
   Oluşturucudan `table` parametresini kaldırın, sabit "üçlüler" tablosunu kullanın
   Tüm yöntemlere `collection` parametresini ekleyin
   Koleksiyonu ilk sütun olarak içeren şemayı güncelleyin
   **Dizin Güncellemeleri**: Tüm 8 sorgu desenini desteklemek için yeni dizinler oluşturulacaktır:
     `(s)` üzerine dizin, konu tabanlı sorgular için
     `(p)` üzerine dizin, öznelik tabanlı sorgular için
     `(o)` üzerine dizin, nesne tabanlı sorgular için
     Not: Cassandra, çok sütunlu ikincil dizinleri desteklemez, bu nedenle bunlar tek sütunlu dizinlerdir

   **Sorgu Deseni Performansı:**
     ✅ `get_all()` - `collection` üzerinde bölüm taraması
     ✅ `get_s(s)` - birincil anahtarı verimli kullanır (`collection, s`)
     ✅ `get_p(p)` - `idx_p` ile `collection` filtrelemesini kullanır
     ✅ `get_o(o)` - `idx_o` ile `collection` filtrelemesini kullanır
     ✅ `get_sp(s, p)` - birincil anahtarı verimli kullanır (`collection, s, p`)
     ⚠️ `get_po(p, o)` - `ALLOW FILTERING` gerektirir (ya `idx_p` veya `idx_o` artı filtreleme kullanır)
     ✅ `get_os(o, s)` - `idx_o` ile ek filtreleme `s` üzerinde kullanır
     ✅ `get_spo(s, p, o)` - tüm birincil anahtarı verimli kullanır

   **ALLOW FILTERING Notu:** `get_po` sorgu deseni, uygun bir birleşik dizin olmadan hem öznitelik hem de nesne kısıtlamalarına ihtiyaç duyduğu için `ALLOW FILTERING` gerektirir. Bu kabul edilebilir çünkü bu sorgu deseni, tipik üçlü depolama kullanımında konu tabanlı sorgulara göre daha az yaygındır

2. **Depolama Yazarı Güncellemeleri** (`trustgraph/storage/triples/cassandra/write.py`):
   (kullanıcı, koleksiyon) başına bir bağlantı yerine, kullanıcı başına tek bir TrustGraph bağlantısı sürdürün
   Ekleme işlemlerine koleksiyonu iletin
   Daha az bağlantıyla daha verimli kaynak kullanımı

3. **Sorgu Hizmeti Güncellemeleri** (`trustgraph/query/triples/cassandra/service.py`):
   Kullanıcı başına tek bir TrustGraph bağlantısı
   Tüm sorgu işlemlerine koleksiyonu iletin
   Koleksiyon parametresiyle aynı sorgu mantığını koruyun

**Faydaları:**
**Basitleştirilmiş Koleksiyon Silme:** Tüm 4 tablo üzerinde `collection` bölüm anahtarını kullanarak silme
**Kaynak Verimliliği:** Daha az veritabanı bağlantısı ve tablo nesnesi
**Çoklu Koleksiyon İşlemleri:** Birden çok koleksiyonu kapsayan işlemleri uygulamak daha kolaydır
**Tutarlı Mimari:** Birleşik koleksiyon meta veri yaklaşımıyla uyumludur
**Koleksiyon Doğrulama:** `triples_collection` tablosu aracılığıyla koleksiyonun varlığını kontrol etmek kolaydır

Koleksiyon işlemleri, mümkün olduğunda atomik olacak ve uygun hata yönetimi ve doğrulama sağlayacaktır.

## Güvenlik Hususları

Koleksiyon yönetimi işlemleri, yetkisiz erişimi veya koleksiyonların silinmesini önlemek için uygun yetkilendirme gerektirir. Erişim kontrolü, mevcut TrustGraph güvenlik modelleriyle uyumlu olacaktır.

## Performans Hususları

Koleksiyon listeleme işlemleri, çok sayıda koleksiyon içeren ortamlarda sayfalama gerektirebilir. Meta veri sorguları, yaygın filtreleme kalıpları için optimize edilmelidir.

## Test Stratejisi

Kapsamlı testler şunları kapsayacaktır:
Koleksiyon oluşturma iş akışı, uçtan uca
Depolama arka uç senkronizasyonu
Var olmayan koleksiyonlar için yazma doğrulaması
Var olmayan koleksiyonların sorgu işlenmesi
Koleksiyon silme işleminin tüm depolama alanlarında yayılması
Hata yönetimi ve kurtarma senaryoları
Her depolama arka ucu için birim testleri
Çapraz depolama işlemleri için entegrasyon testleri

## Uygulama Durumu

### ✅ Tamamlanmış Bileşenler

1. **Librarian Koleksiyon Yönetimi Hizmeti** (`trustgraph-flow/trustgraph/librarian/collection_manager.py`)
   Koleksiyon meta veri CRUD işlemleri (listeleme, güncelleme, silme)
   `LibraryTableStore` aracılığıyla Cassandra koleksiyon meta veri tablosu entegrasyonu
   Koleksiyon silme işleminin tüm depolama türleri arasında koordinasyonu
   Uygun hata yönetimi ile asenkron istek/yanıt işleme

2. **Koleksiyon Meta Veri Şeması** (`trustgraph-base/trustgraph/schema/services/collection.py`)
   `CollectionManagementRequest` ve `CollectionManagementResponse` şemaları
   Koleksiyon kayıtları için `CollectionMetadata` şeması
   Koleksiyon istek/yanıt kuyruğu konu tanımları

3. **Depolama Yönetimi Şeması** (`trustgraph-base/trustgraph/schema/services/storage.py`)
   `StorageManagementRequest` ve `StorageManagementResponse` şemaları
   Depolama yönetimi kuyruğu konuları tanımlandı
   Depolama seviyesindeki koleksiyon işlemleri için mesaj formatı

4. **Cassandra 4-Tablo Şeması** (`trustgraph-flow/trustgraph/direct/cassandra_kg.py`)
   Sorgu performansı için birleşik bölüm anahtarları
   SPO sorguları ve silme takibi için `triples_collection` tablosu
   Koleksiyon silme işlemi, okuyup sonra silme kalıbıyla uygulandı

### ✅ Yapılandırma Tabanlı Kalıba Geçiş - TAMAMLANDI

**Tüm depolama arka uçları, kuyruk tabanlı kalıptan yapılandırma tabanlı `CollectionConfigHandler` kalıbına geçirildi.**

Tamamlanan geçişler:
✅ `trustgraph-flow/trustgraph/storage/triples/cassandra/write.py`
✅ `trustgraph-flow/trustgraph/storage/triples/neo4j/write.py`
✅ `trustgraph-flow/trustgraph/storage/triples/memgraph/write.py`
✅ `trustgraph-flow/trustgraph/storage/triples/falkordb/write.py`
✅ `trustgraph-flow/trustgraph/storage/doc_embeddings/qdrant/write.py`
✅ `trustgraph-flow/trustgraph/storage/graph_embeddings/qdrant/write.py`
✅ `trustgraph-flow/trustgraph/storage/doc_embeddings/milvus/write.py`
✅ `trustgraph-flow/trustgraph/storage/graph_embeddings/milvus/write.py`
✅ `trustgraph-flow/trustgraph/storage/doc_embeddings/pinecone/write.py`
✅ `trustgraph-flow/trustgraph/storage/graph_embeddings/pinecone/write.py`
✅ `trustgraph-flow/trustgraph/storage/objects/cassandra/write.py`

Tüm arka uçlar artık:
`CollectionConfigHandler`'dan miras almaktadır
`self.register_config_handler(self.on_collection_config)` aracılığıyla yapılandırma itme bildirimleri için kayıtlıdır
`create_collection(user, collection, metadata)` ve `delete_collection(user, collection)`'i uygulamaktadır
Yazmadan önce `collection_exists(user, collection)` ile doğrulamaktadır
Otomatik olarak yapılandırma hizmeti değişiklikleriyle senkronize olmaktadır

Eski kuyruk tabanlı altyapı kaldırıldı:
✅ `StorageManagementRequest` ve `StorageManagementResponse` şemaları kaldırıldı
✅ Depolama yönetimi kuyruğu konu tanımları kaldırıldı
✅ Tüm arka uçlardan depolama yönetimi tüketici/üretici kaldırıldı
✅ Tüm arka uçlardan `on_storage_management` işleyicileri kaldırıldı

