# GraphQL Sorgu Teknik Özellikleri

## Genel Bakış

Bu özellik, TrustGraph'ın Apache Cassandra'daki yapılandırılmış veri depolaması için bir GraphQL sorgu arayüzünün uygulanmasını tanımlar. Yapılandırılmış-veri.md spesifikasyonunda belirtilen yapılandırılmış veri yeteneklerine dayanarak, bu belge, çıkarılan ve işlenen yapılandırılmış nesneleri içeren Cassandra tablolarına karşı GraphQL sorgularının nasıl yürütüleceğini ayrıntılı olarak açıklar.

GraphQL sorgu hizmeti, Cassandra'da depolanan yapılandırılmış verileri sorgulamak için esnek, tür güvenli bir arayüz sağlayacaktır. Şema değişikliklerine dinamik olarak uyum sağlayacak, nesneler arasındaki ilişkiler de dahil olmak üzere karmaşık sorguları destekleyecek ve TrustGraph'ın mevcut mesaj tabanlı mimarisiyle sorunsuz bir şekilde entegre olacaktır.

## Hedefler

**Dinamik Şema Desteği**: Hizmeti yeniden başlatmaya gerek kalmadan yapılandırmadaki şema değişikliklerine otomatik olarak uyum sağlayın.
**GraphQL Standartlarına Uygunluk**: Mevcut GraphQL araçları ve istemcileriyle uyumlu, standart bir GraphQL arayüzü sağlayın.
**Verimli Cassandra Sorguları**: GraphQL sorgularını, bölüm anahtarlarını ve dizinleri dikkate alarak verimli Cassandra CQL sorgularına dönüştürün.
**İlişki Çözümlemesi**: Farklı nesne türleri arasındaki ilişkiler için GraphQL alan çözümleyicilerini destekleyin.
**Tür Güvenliği**: Şema tanımlarına göre tür güvenli sorgu yürütme ve yanıt oluşturma sağlayın.
**Ölçeklenebilir Performans**: Uygun bağlantı havuzu ve sorgu optimizasyonu ile eşzamanlı sorguları verimli bir şekilde işleyin.
**İstek/Yanıt Entegrasyonu**: TrustGraph'ın Pulsar tabanlı istek/yanıt kalıbıyla uyumluluğu koruyun.
**Hata İşleme**: Şema uyumsuzlukları, sorgu hataları ve veri doğrulama sorunları için kapsamlı hata raporlama sağlayın.

## Arka Plan

Yapılandırılmış veri depolama uygulaması (trustgraph-flow/trustgraph/storage/objects/cassandra/), nesneleri TrustGraph'ın yapılandırma sisteminde depolanan şema tanımlarına göre Cassandra tablolarına yazar. Bu tablolar, koleksiyonlar içindeki verimli sorguları etkinleştiren bileşik bölüm anahtarı yapısı ve şema tanımlı birincil anahtarlar kullanır.

Bu özellik tarafından ele alınan mevcut sınırlamalar:
Cassandra'da depolanan yapılandırılmış veri için bir sorgu arayüzü yok.
Yapılandırılmış veri için GraphQL'in güçlü sorgu yeteneklerinden yararlanamama.
İlişkili nesneler arasındaki ilişki geçişi için destek eksikliği.
Yapılandırılmış veri erişimi için standart bir sorgu dili eksikliği.

GraphQL sorgu hizmeti, bunları sağlayarak bu boşlukları dolduracaktır:
Cassandra tablolarını sorgulamak için standart bir GraphQL arayüzü.
TrustGraph yapılandırmasından dinamik olarak GraphQL şemaları oluşturma.
GraphQL sorgularını Cassandra CQL'ye verimli bir şekilde dönüştürme.
Alan çözümleyicileri aracılığıyla ilişki çözümlemesini destekleme.

## Teknik Tasarım

### Mimari

GraphQL sorgu hizmeti, yerleşik kalıpları izleyen yeni bir TrustGraph akışı işlemci olarak uygulanacaktır:

**Modül Konumu**: `trustgraph-flow/trustgraph/query/objects/cassandra/`

**Ana Bileşenler**:

1. **GraphQL Sorgu Hizmeti İşlemcisi**
   Temel FlowProcessor sınıfını genişletir.
   Mevcut sorgu hizmetlerine benzer bir istek/yanıt kalıbını uygular.
   Şema güncellemeleri için yapılandırmayı izler.
   GraphQL şemasını yapılandırmayla senkronize tutar.

2. **Dinamik Şema Oluşturucu**
   TrustGraph RowSchema tanımlarını GraphQL türlerine dönüştürür.
   Uygun alan tanımlarıyla GraphQL nesne türleri oluşturur.
   Koleksiyon tabanlı çözümleyicilerle kök Sorgu türünü oluşturur.
   Yapılandırma değiştiğinde GraphQL şemasını günceller.

3. **Sorgu Yürütücüsü**
   Gelen GraphQL sorgularını Strawberry kütüphanesi kullanarak ayrıştırır.
   Sorguları mevcut şemaya göre doğrular.
   Sorguları yürütür ve yapılandırılmış yanıtlar döndürür.
   Ayrıntılı hata mesajlarıyla hataları zarif bir şekilde işler.

4. **Cassandra Sorgu Çevirmeni**
   GraphQL seçimlerini CQL sorgularına dönüştürür.
   Mevcut dizinlere ve bölüm anahtarlarına göre sorguları optimize eder.
   Filtrelemeyi, sayfalama ve sıralamayı işler.
   Bağlantı havuzunu ve oturum yaşam döngüsünü yönetir.

5. **İlişki Çözümleyici**
   Nesne ilişkileri için alan çözümleyicilerini uygular.
   N+1 sorgularından kaçınmak için verimli toplu yükleme gerçekleştirir.
   Çözümlenen ilişkileri istek bağlamı içinde önbelleğe alır.
   Hem ileri hem de geri ilişki geçişini destekler.

### Yapılandırma Şeması İzleme

Hizmet, şema güncellemelerini almak için bir yapılandırma işleyicisi kaydeder:

```python
self.register_config_handler(self.on_schema_config)
```

Şemalar değiştiğinde:
1. Yapılandırmadan yeni şema tanımlarını ayrıştırın.
2. GraphQL türlerini ve çözümleyicileri yeniden oluşturun.
3. Çalıştırılabilir şemayı güncelleyin.
4. Şemaya bağlı tüm önbellekleri temizleyin.

### GraphQL Şema Oluşturma

Yapılandırmadaki her RowSchema için aşağıdaki öğeleri oluşturun:

1. **GraphQL Nesne Türü**:
   Alan türlerini eşleyin (string → String, integer → Int, float → Float, boolean → Boolean).
   Gerekli alanları GraphQL'de nullable olmayan olarak işaretleyin.
   Şemadan alan açıklamalarını ekleyin.

2. **Kök Sorgu Alanları**:
   Koleksiyon sorgusu (örneğin, `customers`, `transactions`).
   İndekslenmiş alanlara göre filtreleme argümanları.
   Sayfalama desteği (limit, offset).
   Sıralanabilir alanlar için sıralama seçenekleri.

3. **İlişki Alanları**:
   Şemadan yabancı anahtar ilişkilerini belirleyin.
   İlgili nesneler için alan çözümleyicileri oluşturun.
   Hem tek nesne hem de liste ilişkilerini destekleyin.

### Sorgu Yürütme Akışı

1. **İstek Alma**:
   Pulsar'dan ObjectsQueryRequest'i alın.
   GraphQL sorgu dizesini ve değişkenlerini çıkarın.
   Kullanıcıyı ve koleksiyon bağlamını belirleyin.

2. **Sorgu Doğrulama**:
   Strawberry kullanarak GraphQL sorgusunu ayrıştırın.
   Mevcut şemaya göre doğrulayın.
   Alan seçimlerini ve argüman türlerini kontrol edin.

3. **CQL Oluşturma**:
   GraphQL seçimlerini analiz edin.
   Uygun WHERE koşullarına sahip CQL sorgusu oluşturun.
   Koleksiyonu bölüm anahtarına dahil edin.
   GraphQL argümanlarına göre filtreleri uygulayın.

4. **Sorgu Yürütme**:
   CQL sorgusunu Cassandra'ya karşı yürütün.
   Sonuçları GraphQL yanıt yapısına eşleyin.
   Herhangi bir ilişki alanını çözün.
   Yanıtı GraphQL spesifikasyonuna göre biçimlendirin.

5. **Yanıt Teslimi**:
   Sonuçlarla ObjectsQueryResponse oluşturun.
   Herhangi bir yürütme hatasını dahil edin.
   Yanıtı korelasyon kimliğiyle Pulsar üzerinden gönderin.

### Veri Modelleri

> **Not**: `trustgraph-base/trustgraph/schema/services/structured_query.py`'da mevcut bir StructuredQueryRequest/Response şeması bulunmaktadır. Ancak, bu şemada kritik alanlar (kullanıcı, koleksiyon) eksiktir ve alt optimal türler kullanılmaktadır. Aşağıdaki şemalar, önerilen gelişmeyi temsil etmektedir; bu şemalar ya mevcut şemaları değiştirmeli ya da yeni ObjectsQueryRequest/Response türleri olarak oluşturulmalıdır.

#### İstek Şeması (ObjectsQueryRequest)

```python
from pulsar.schema import Record, String, Map, Array

class ObjectsQueryRequest(Record):
    user = String()              # Cassandra keyspace (follows pattern from TriplesQueryRequest)
    collection = String()        # Data collection identifier (required for partition key)
    query = String()             # GraphQL query string
    variables = Map(String())    # GraphQL variables (consider enhancing to support all JSON types)
    operation_name = String()    # Operation to execute for multi-operation documents
```

**Mevcut StructuredQueryRequest'ten yapılan değişikliklerin gerekçesi:**
Diğer sorgu hizmetlerinin kalıbına uygun olarak `user` ve `collection` alanları eklendi.
Bu alanlar, Cassandra anahtar alanını ve koleksiyonu tanımlamak için gereklidir.
Değişkenler şu anda Map(String()) olarak kalmaktadır, ancak ideal olarak tüm JSON türlerini desteklemelidir.

#### Yanıt Şeması (ObjectsQueryResponse)

```python
from pulsar.schema import Record, String, Array
from ..core.primitives import Error

class GraphQLError(Record):
    message = String()
    path = Array(String())       # Path to the field that caused the error
    extensions = Map(String())   # Additional error metadata

class ObjectsQueryResponse(Record):
    error = Error()              # System-level error (connection, timeout, etc.)
    data = String()              # JSON-encoded GraphQL response data
    errors = Array(GraphQLError) # GraphQL field-level errors
    extensions = Map(String())   # Query metadata (execution time, etc.)
```

**Mevcut StructuredQueryResponse'tan yapılan değişikliklerin gerekçesi:**
Sistem hatalarını (`error`) ve GraphQL hatalarını (`errors`) ayırır.
Dizi yerine yapılandırılmış GraphQLError nesneleri kullanır.
GraphQL spesifikasyonuna uygunluk için `extensions` alanı eklenmiştir.
Uyumluluk için verileri JSON dizesi olarak tutar, ancak yerel türler tercih edilir.

### Cassandra Sorgu Optimizasyonu

Hizmet, Cassandra sorgularını aşağıdaki şekilde optimize edecektir:

1. **Bölüm Anahtarlarına Saygı Gösterme:**
   Her zaman sorgularda koleksiyonu dahil edin.
   Şema tanımlı birincil anahtarları verimli bir şekilde kullanın.
   Tam tablo taramalarından kaçının.

2. **Dizinleri Kullanma:**
   Filtreleme için ikincil dizinleri kullanın.
   Mümkün olduğunda birden fazla filtreyi birleştirin.
   Sorguların verimsiz olabileceği durumlarda uyarı verin.

3. **Toplu Yükleme:**
   İlişki sorgularını toplayın.
   Gidiş-dönüş sayısını azaltmak için toplu olarak çalıştırın.
   Sonuçları istek bağlamı içinde önbelleğe alın.

4. **Bağlantı Yönetimi:**
   Kalıcı Cassandra oturumlarını koruyun.
   Bağlantı havuzunu kullanın.
   Hatalarda yeniden bağlanmayı yönetin.

### Örnek GraphQL Sorguları

#### Basit Koleksiyon Sorgusu
```graphql
{
  customers(status: "active") {
    customer_id
    name
    email
    registration_date
  }
}
```

#### İlişkilere Sahip Sorgular
```graphql
{
  orders(order_date_gt: "2024-01-01") {
    order_id
    total_amount
    customer {
      name
      email
    }
    items {
      product_name
      quantity
      price
    }
  }
}
```

#### Sayfalı Sorgu
```graphql
{
  products(limit: 20, offset: 40) {
    product_id
    name
    price
    category
  }
}
```

### Uygulama Bağımlılıkları

**Strawberry GraphQL**: GraphQL şema tanımı ve sorgu yürütme için
**Cassandra Driver**: Veritabanı bağlantısı için (depolama modülünde zaten kullanılıyor)
**TrustGraph Base**: FlowProcessor ve şema tanımları için
**Configuration System**: Şema takibi ve güncellemeleri için

### Komut Satırı Arayüzü

Hizmet, aşağıdaki CLI komutunu sağlayacaktır: `kg-query-objects-graphql-cassandra`

Argümanlar:
`--cassandra-host`: Cassandra kümesi iletişim noktası
`--cassandra-username`: Kimlik doğrulama kullanıcı adı
`--cassandra-password`: Kimlik doğrulama parolası
`--config-type`: Şemalar için yapılandırma türü (varsayılan: "schema")
Standart FlowProcessor argümanları (Pulsar yapılandırması, vb.)

## API Entegrasyonu

### Pulsar Konuları

**Giriş Konusu**: `objects-graphql-query-request`
Şema: ObjectsQueryRequest
Ağ geçidi hizmetlerinden GraphQL sorguları alır

**Çıkış Konusu**: `objects-graphql-query-response`
Şema: ObjectsQueryResponse
Sorgu sonuçlarını ve hataları döndürür

### Ağ Geçidi Entegrasyonu

Ağ geçidi ve ters ağ geçidi, aşağıdaki işlemleri gerçekleştirmek için uç noktalarına ihtiyaç duyacaktır:
1. İstemcilerden GraphQL sorgularını kabul etme
2. Sorguları Pulsar üzerinden sorgu hizmetine yöneltme
3. Yanıtları istemcilere döndürme
4. GraphQL introspeksiyon sorgularını destekleme

### Aracılık Aracı Entegrasyonu

Yeni bir aracılık aracı sınıfı, aşağıdaki özellikleri sağlayacaktır:
Doğal dili GraphQL sorgusuna dönüştürme
Doğrudan GraphQL sorgusu yürütme
Sonuçların yorumlanması ve biçimlendirilmesi
Aracılık karar akışlarıyla entegrasyon

## Güvenlik Hususları

**Sorgu Derinliği Sınırlaması**: Performans sorunlarına neden olabilecek derinlemesine iç içe sorguları önleme
**Sorgu Karmaşıklığı Analizi**: Kaynak tükenmesini önlemek için sorgu karmaşıklığını sınırlama
**Alan Düzeyi İzinleri**: Kullanıcı rollerine göre alan düzeyinde erişim kontrolü için gelecekteki destek
**Giriş Temizleme**: Enjeksiyon saldırılarını önlemek için tüm sorgu girişlerini doğrulama ve temizleme
**Hız Sınırlaması**: Kullanıcı/koleksiyon başına sorgu hız sınırlaması uygulama

## Performans Hususları

**Sorgu Planlama**: CQL oluşturmayı optimize etmek için sorguları yürütmeden önce analiz etme
**Sonuç Önbelleği**: Sık erişilen verileri alan çözümleyici düzeyinde önbelleğe alma
**Bağlantı Havuzu**: Cassandra'ya verimli bağlantı havuzları sağlama
**Toplu İşlemler**: Mümkün olduğunda birden fazla sorguyu birleştirme, gecikmeyi azaltma
**İzleme**: Optimizasyon için sorgu performans metriklerini izleme

## Test Stratejisi

### Birim Testleri
RowSchema tanımlarından şema oluşturma
GraphQL sorgusu ayrıştırma ve doğrulama
CQL sorgusu oluşturma mantığı
Alan çözümleyici uygulamaları

### Sözleşme Testleri
Pulsar mesaj sözleşmesi uyumluluğu
GraphQL şema geçerliliği
Yanıt formatı doğrulaması
Hata yapısı doğrulaması

### Entegrasyon Testleri
Test Cassandra örneğine karşı uçtan uca sorgu yürütme
Şema güncelleme işleme
İlişki çözümü
Sayfalama ve filtreleme
Hata senaryoları

### Performans Testleri
Yük altında sorgu verimliliği
Çeşitli sorgu karmaşıklıkları için yanıt süresi
Büyük sonuç kümeleriyle bellek kullanımı
Bağlantı havuzu verimliliği

## Geçiş Planı

Bu yeni bir özellik olduğu için herhangi bir geçiş gerekli değildir. Hizmet şunları yapacaktır:
1. Mevcut şemaları yapılandırmadan okuyacaktır
2. Depolama modülü tarafından oluşturulan mevcut Cassandra tablolarına bağlanacaktır
3. Dağıtım üzerine hemen sorguları kabul etmeye başlayacaktır

## Zaman Çizelgesi

1-2. Hafta: Temel hizmet uygulaması ve şema oluşturma
3. Hafta: Sorgu yürütme ve CQL çevirisi
4. Hafta: İlişki çözümü ve optimizasyon
5. Hafta: Test etme ve performans ayarlaması
6. Hafta: Ağ geçidi entegrasyonu ve dokümantasyon

## Açık Sorular

1. **Şema Evrimi**: Hizmet, şema geçişleri sırasında sorguları nasıl işlemelidir?
   Seçenek: Şema güncellemeleri sırasında sorguları kuyruğa alın
   Seçenek: Aynı anda birden fazla şema sürümünü destekleyin

2. **Önbellekleme Stratejisi**: Sorgu sonuçları önbelleğe alınmalı mı?
   Dikkat edilmesi gerekenler: Zaman tabanlı son kullanma tarihi
   Dikkat edilmesi gerekenler: Olay tabanlı geçersiz kılma

3. **Federasyon Desteği**: Hizmet, diğer veri kaynaklarıyla birleştirme için GraphQL federasyonunu desteklemeli mi?
   Yapılandırılmış ve grafik veriler arasında birleşik sorguları etkinleştirir

4. **Abonelik Desteği**: Hizmet, gerçek zamanlı güncellemeler için GraphQL aboneliklerini desteklemeli mi?
   Ağ geçidinde WebSocket desteği gerektirir

5. **Özel Ölçekler**: Hizmet, alan adlarına özgü veri türleri için özel ölçek türlerini desteklemeli mi?
   Örnekler: DateTime, UUID, JSON alanları

## Referanslar

Yapılandırılmış Veri Teknik Özelliği: `docs/tech-specs/structured-data.md`
Strawberry GraphQL Dokümantasyonu: https://strawberry.rocks/
GraphQL Özelliği: https://spec.graphql.org/
Apache Cassandra CQL Referansı: https://cassandra.apache.org/doc/stable/cassandra/cql/
TrustGraph Akış İşlemci Dokümantasyonu: İç dokümantasyon