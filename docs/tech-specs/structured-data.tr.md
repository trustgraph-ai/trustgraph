# Yapılandırılmış Veri Teknik Özellikleri

## Genel Bakış

Bu özellik, TrustGraph'ın yapılandırılmış veri akışlarıyla entegrasyonunu tanımlar ve sistemin, satırlar halinde tablolarda veya nesne depolarında temsil edilebilen verilerle çalışmasını sağlar. Bu entegrasyon, dört birincil kullanım senaryosunu destekler:

1. **Yapısızdan Yapılandırılmışa Çıkarma**: Yapısız veri kaynaklarını okuyun, nesne yapılarını belirleyin ve çıkarın ve bunları tablo formatında saklayın.
2. **Yapılandırılmış Veri Alma**: Zaten yapılandırılmış formatlarda olan verileri, çıkarılan verilerle birlikte yapılandırılmış depoya doğrudan yükleyin.
3. **Doğal Dil Sorgulama**: Doğal dil sorularını, depodan eşleşen verileri çıkarmak için yapılandırılmış sorgulara dönüştürün.
4. **Doğrudan Yapılandırılmış Sorgulama**: Hassas veri alımı için yapılandırılmış sorguları doğrudan veri deposuna çalıştırın.

## Hedefler

**Birleşik Veri Erişimi**: TrustGraph içinde hem yapılandırılmış hem de yapılandırılmamış verilere erişmek için tek bir arayüz sağlayın.
**Sorunsuz Entegrasyon**: TrustGraph'ın grafik tabanlı bilgi gösterimi ile geleneksel yapılandırılmış veri formatları arasındaki sorunsuz uyumluluğu sağlayın.
**Esnek Çıkarma**: Çeşitli yapılandırılmamış kaynaklardan (belgeler, metin vb.) yapılandırılmış verilerin otomatik olarak çıkarılmasını destekleyin.
**Sorgu Çeşitliliği**: Kullanıcıların verilere hem doğal dil hem de yapılandırılmış sorgu dilleriyle sorgu yapmasına izin verin.
**Veri Tutarlılığı**: Farklı veri gösterimleri arasında veri bütünlüğünü ve tutarlılığını koruyun.
**Performans Optimizasyonu**: Ölçekte yapılandırılmış verilerin verimli bir şekilde depolanmasını ve alınmasını sağlayın.
**Şema Esnekliği**: Çeşitli veri kaynaklarına uyum sağlamak için hem şema-yazma hem de şema-okuma yaklaşımlarını destekleyin.
**Geriye Dönük Uyumluluk**: Yapılandırılmış veri yetenekleri eklerken mevcut TrustGraph işlevselliğini koruyun.

## Arka Plan

TrustGraph şu anda yapılandırılmamış verileri işleme ve çeşitli kaynaklardan bilgi grafikleri oluşturma konusunda mükemmeldir. Ancak, birçok kurumsal kullanım senaryosu, müşteri kayıtları, işlem günlükleri, envanter veritabanları ve diğer tablo veri kümeleri gibi doğası gereği yapılandırılmış verileri içerir. Bu yapılandırılmış veri kümeleri genellikle kapsamlı bilgiler sağlamak için yapılandırılmamış içerikle birlikte analiz edilmelidir.

Mevcut sınırlamalar şunlardır:
Önceden yapılandırılmış veri formatlarını (CSV, JSON dizileri, veritabanı dışa aktarmaları) alma konusunda yerel destek yoktur.
Belgelerden tablo verilerini çıkarırken, yerleşik yapıyı koruyamama.
Yapılandırılmış veri kalıpları için verimli sorgulama mekanizmalarının olmaması.
SQL benzeri sorgular ile TrustGraph'ın grafik sorguları arasındaki köprünün olmaması.

Bu özellik, TrustGraph'ın mevcut yeteneklerini tamamlayan bir yapılandırılmış veri katmanı tanıtarak bu boşlukları giderir. Yapılandırılmış verilere yerel olarak destek sağlayarak, TrustGraph şunları yapabilir:
Hem yapılandırılmış hem de yapılandırılmamış veri analizleri için birleşik bir platform görevi görmek.
Hem grafik ilişkilerini hem de tablo verilerini kapsayan hibrit sorguları etkinleştirmek.
Yapılandırılmış verilerle çalışmaya alışkın kullanıcılar için tanıdık arayüzler sağlamak.
Veri entegrasyonu ve iş zekası alanlarında yeni kullanım senaryolarını açmak.

## Teknik Tasarım

### Mimari

Yapılandırılmış veri entegrasyonu, aşağıdaki teknik bileşenleri gerektirir:

1. **NLP'den Yapılandırılmış Sorgu Hizmetine**
   Doğal dil sorularını yapılandırılmış sorgulara dönüştürür.
   Birden çok sorgu dili hedefi (başlangıçta SQL benzeri sözdizimi) destekler.
   Mevcut TrustGraph NLP yetenekleriyle entegre olur.
   
   Modül: trustgraph-flow/trustgraph/query/nlp_query/cassandra

2. **Yapılandırma Şema Desteği** ✅ **[TAMAMLANDI]**
   Yapılandırılmış veri şemalarını depolamak için genişletilmiş yapılandırma sistemi.
   Tablo yapılarını, alan türlerini ve ilişkileri tanımlama desteği.
   Şema sürümleme ve geçiş yetenekleri.

3. **Nesne Çıkarma Modülü** ✅ **[TAMAMLANDI]**
   Gelişmiş bilgi çıkarıcı akışı entegrasyonu.
   Yapısız kaynaklardan yapılandırılmış nesneleri tanımlar ve çıkarır.
   Kaynak ve güven puanlarını korur.
   Yapılandırma verilerini almak ve şema bilgilerini çözmek için bir yapılandırma işleyici (örneğin: trustgraph-flow/trustgraph/prompt/template/service.py) kaydeder.
   Nesneleri alır ve bunları Pulsar kuyruğuna teslim etmek üzere ExtractedObject nesnelerine dönüştürür.
   NOT: `trustgraph-flow/trustgraph/extract/object/row/` adresinde mevcut kod bulunmaktadır. Bu, önceki bir girişimdir ve mevcut API'lere uymadığından büyük ölçüde yeniden düzenlenmesi gerekecektir. Kullanışlıysa kullanın, değilse sıfırdan başlayın.
   Bir komut satırı arayüzü gerektirir: `kg-extract-objects`

   Modül: trustgraph-flow/trustgraph/extract/kg/objects/

4. **Yapılandırılmış Depo Yazma Modülü** ✅ **[TAMAMLANDI]**
   ExtractedObject formatında nesneleri Pulsar kuyruklarından alır.
   İlk uygulama, yapılandırılmış veri deposu olarak Apache Cassandra'yı hedef alır.
   Karşılaşılan şemalara göre dinamik olarak tablo oluşturmayı yönetir.
   Şema-Cassandra tablo eşlemesini ve veri dönüşümünü yönetir.
   Performans optimizasyonu için toplu ve akışlı yazma işlemleri sağlar.
   Pulsar çıktıları yok - bu, veri akışında bir terminal hizmetidir.

   **Şema İşleme**:
   Yeni bir şema ilk kez karşılaşıldığında, otomatik olarak ilgili Cassandra tablosunu oluşturur.
   Tekrarlayan tablo oluşturma girişimlerinden kaçınmak için bilinen şemaların bir önbelleğini korur.
   Şema tanımlarını doğrudan alıp almamak veya ExtractedObject mesajlarındaki şema adlarına güvenip güvenmemek konusunda dikkat edilmesi gereken bir durum.
   

   **Cassandra Tablo Eşlemesi**:
   Anahtar alanı, ExtractedObject'in Meta Verilerinden gelen `user` alanından alınır.
   Tablo, ExtractedObject'in `schema_name` alanından alınır.
   Meta Verilerden gelen Koleksiyon, Cassandra düğümleri arasında doğal veri dağılımını sağlamak için bölüm anahtarının bir parçası haline gelir:
     Cassandra düğümleri arasında verilerin doğal bir şekilde dağıtılmasını sağlar.
     Belirli bir koleksiyon içindeki sorguların verimli bir şekilde çalışmasını sağlar.
     Farklı veri aktarımları/kaynakları arasında mantıksal bir izolasyon sağlar.
   Birincil anahtar yapısı: `PRIMARY KEY ((collection, <schema_primary_key_fields>), <clustering_keys>)`
     Koleksiyon, her zaman bölüm anahtarının ilk bileşenidir.
     Şema tanımlı birincil anahtar alanları, birleşik bölüm anahtarının bir parçası olarak gelir.
     Bu, sorguların koleksiyonu belirtmesini gerektirir ve öngörülebilir bir performans sağlar.
   Alan tanımları, Cassandra sütunlarına tür dönüşümleriyle eşlenir:
     `string` → `text`
     `integer` → `int` veya `bigint` (boyut ipucuna bağlı olarak)
     `float` → `float` veya `double` (doğruluk gereksinimlerine bağlı olarak)
     `boolean` → `boolean`
     `timestamp` → `timestamp`
     `enum` → `text` (uygulama seviyesinde doğrulama ile)
   İndeksli alanlar, Cassandra ikincil indekslerini oluşturur (birincil anahtarda zaten bulunan alanlar hariç).
   Gerekli alanlar, uygulama seviyesinde zorunlu kılınır (Cassandra NOT NULL'ı desteklemez).

   **Nesne Depolama**:
   ExtractedObject.values haritasından değerleri çıkarır.
   Eklemeden önce tür dönüşümü ve doğrulama yapar.
   Eksik isteğe bağlı alanları zarif bir şekilde işler.
   Nesne kökeni hakkında meta verileri korur (kaynak belge, güvenilirlik puanları).
   Mesaj tekrar senaryolarını işlemek için idempotent yazma işlemlerini destekler.

   **Uygulama Notları**:
   `trustgraph-flow/trustgraph/storage/objects/cassandra/` adresindeki mevcut kod güncel değildir ve mevcut API'lere uygun değildir.
   Çalışan bir depolama işlemcisinin örneği olarak `trustgraph-flow/trustgraph/storage/triples/cassandra`'a başvurulmalıdır.
   Yeniden düzenleme veya yeniden yazma kararı vermeden önce, yeniden kullanılabilir bileşenler için mevcut kodun değerlendirilmesi gerekir.

   Modül: trustgraph-flow/trustgraph/storage/objects/cassandra

5. **Yapılandırılmış Sorgu Hizmeti** ✅ **[TAMAMLANDI]**
   Tanımlanmış formatlarda yapılandırılmış sorguları kabul eder.
   Yapılandırılmış depoya karşı sorguları yürütür.
   Sorgu kriterlerine uyan nesneleri döndürür.
   Sayfalama ve sonuç filtrelemeyi destekler.

   Modül: trustgraph-flow/trustgraph/query/objects/cassandra

6. **Ajan Aracı Entegrasyonu**
   Ajan çerçeveleri için yeni bir araç sınıfı.
   Ajanların yapılandırılmış veri depolarını sorgulamasına olanak tanır.
   Doğal dil ve yapılandırılmış sorgu arayüzleri sağlar.
   Mevcut ajan karar verme süreçleriyle entegre olur.

7. **Yapılandırılmış Veri Alma Hizmeti**
   Yapılandırılmış verileri çeşitli formatlarda (JSON, CSV, XML) kabul eder.
   Gelen verileri tanımlanmış şemalara göre ayrıştırır ve doğrular.
   Verileri normalleştirilmiş nesne akışlarına dönüştürür.
   Nesneleri işleme için uygun mesaj kuyruklarına gönderir.
   Toplu yüklemeleri ve akışlı almayı destekler.

   Modül: trustgraph-flow/trustgraph/decoding/structured

8. **Nesne Gömme Hizmeti**
   Yapılandırılmış nesneler için vektör gömmeleri oluşturur.
   Yapılandırılmış veriler arasında semantik aramayı sağlar.
   Yapılandırılmış sorguları semantik benzerlikle birleştiren hibrit aramayı destekler.
   Mevcut vektör depolarıyla entegre olur.

   Modül: trustgraph-flow/trustgraph/embeddings/object_embeddings/qdrant

### Veri Modelleri

#### Şema Depolama Mekanizması

Şemalar, aşağıdaki yapı kullanılarak TrustGraph'ın yapılandırma sisteminde saklanır:

**Türü**: `schema` (tüm yapılandırılmış veri şemaları için sabit değer)
**Anahtar**: Şemanın benzersiz adı/tanımlayıcısı (örneğin, `customer_records`, `transaction_log`)
**Değer**: Yapıyı içeren JSON şema tanımı

Örnek yapılandırma girişi:
```
Type: schema
Key: customer_records
Value: {
  "name": "customer_records",
  "description": "Customer information table",
  "fields": [
    {
      "name": "customer_id",
      "type": "string",
      "primary_key": true
    },
    {
      "name": "name",
      "type": "string",
      "required": true
    },
    {
      "name": "email",
      "type": "string",
      "required": true
    },
    {
      "name": "registration_date",
      "type": "timestamp"
    },
    {
      "name": "status",
      "type": "string",
      "enum": ["active", "inactive", "suspended"]
    }
  ],
  "indexes": ["email", "registration_date"]
}
```

Bu yaklaşım şunları sağlar:
Kod değişiklikleri olmadan dinamik şema tanımı
Kolay şema güncellemeleri ve sürüm yönetimi
Mevcut TrustGraph yapılandırma yönetimi ile tutarlı entegrasyon
Tek bir dağıtım içinde birden fazla şema desteği

### API'ler

Yeni API'ler:
  Yukarıdaki türler için Pulsar şemaları
  Yeni akışlarda Pulsar arayüzleri
  Akışların hangi şema türlerini yükleyeceğini bilmesi için, şema türlerini akışlarda belirtmenin bir yolu gereklidir
    Ağ geçidi ve ters ağ geçidine eklenen API'ler
  

Değiştirilen API'ler:
Bilgi çıkarma uç noktaları - Yapılandırılmış nesne çıktısı seçeneği ekleyin
Ajan uç noktaları - Yapılandırılmış veri aracı desteği ekleyin

### Uygulama Detayları

Mevcut kurallara uygun olarak, bunlar sadece yeni işleme modülleridir.
Her şey trustgraph-flow paketlerinde yer almaktadır, şema öğeleri ise trustgraph-base'de bulunmaktadır.


Bu özelliği tanıtmak/denemek için Workbench'te bazı kullanıcı arayüzü (UI) çalışmaları yapılması gerekmektedir.


## Güvenlik Hususları

Ek hususlar bulunmamaktadır.

## Performans Hususları

Sorguların yavaşlamasını önlemek için Cassandra sorgularının ve indekslerinin kullanımına ilişkin bazı sorular bulunmaktadır.


## Test Stratejisi

Mevcut test stratejisi kullanılacak, birim, sözleşme ve entegrasyon testleri oluşturulacaktır.

## Geçiş Planı

Yok.

## Zaman Çizelgesi

Belirtilmemiştir.

## Açık Sorular

Bu, diğer depolama türleriyle de çalışacak şekilde yapılabilir mi? Tek bir depolamayla çalışan modüllerin, diğer depolamalara da uygulanabilmesi için arayüzler kullanmayı hedefliyoruz.
  
  
## Referanslar


n/a.

