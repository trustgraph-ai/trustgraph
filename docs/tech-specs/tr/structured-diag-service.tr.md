---
layout: default
title: "Yapılandırılmış Veri Tanı Hizmeti Teknik Özellikleri"
parent: "Turkish (Beta)"
---

# Yapılandırılmış Veri Tanı Hizmeti Teknik Özellikleri

> **Beta Translation:** This document was translated via Machine Learning and as such may not be 100% accurate. All non-English languages are currently classified as Beta.

## Genel Bakış

Bu özellik, TrustGraph içinde yapılandırılmış verileri teşhis etmek ve analiz etmek için yeni bir kullanılabilir hizmeti tanımlar. Bu hizmet, mevcut `tg-load-structured-data` komut satırı aracından işlevleri ayırır ve bunları istek/yanıt hizmeti olarak sunar, böylece veri türü algılama ve tanımlayıcı oluşturma yeteneklerine programlı erişim sağlar.

Bu hizmet, üç birincil işlemi destekler:

1. **Veri Türü Algılama**: Bir veri örneğinin biçimini (CSV, JSON veya XML) belirlemek için analiz gerçekleştirin.
2. **Tanımlayıcı Oluşturma**: Verilen bir veri örneği ve tür için bir TrustGraph yapılandırılmış veri tanımlayıcısı oluşturun.
3. **Birleşik Tanı**: Hem tür algılama hem de tanımlayıcı oluşturmayı sırayla gerçekleştirin.

## Hedefler

**Veri Analizini Modülerleştirme**: Veri teşhis mantığını CLI'dan yeniden kullanılabilir hizmet bileşenlerine ayırma.
**Programlı Erişimi Sağlama**: Veri analiz yeteneklerine API tabanlı erişim sağlama.
**Çoklu Veri Biçimlerini Destekleme**: CSV, JSON ve XML veri biçimlerini tutarlı bir şekilde işleme.
**Doğru Tanımlayıcılar Oluşturma**: Kaynak verileri TrustGraph şemalarına doğru bir şekilde eşleyen yapılandırılmış veri tanımlayıcıları oluşturma.
**Geriye Dönük Uyumluluğu Koruma**: Mevcut CLI işlevselliğinin çalışmaya devam etmesini sağlama.
**Hizmet Birleştirme İmkanı Sağlama**: Diğer hizmetlerin veri teşhis yeteneklerinden yararlanmasına olanak sağlama.
**Test Edilebilirliği Artırma**: İş mantığını CLI arayüzünden ayırarak daha iyi test imkanı sağlama.
**Akış Analizini Destekleme**: Tüm dosyaları yüklemeden veri örneklerinin analizini yapma imkanı sağlama.

## Arka Plan

Şu anda, `tg-load-structured-data` komutu, yapılandırılmış verileri analiz etmek ve tanımlayıcılar oluşturmak için kapsamlı işlevsellik sağlar. Ancak, bu işlevsellik CLI arayüzüne sıkı bir şekilde bağlıdır ve yeniden kullanılabilirliğini sınırlar.

Mevcut sınırlamalar şunlardır:
Veri teşhis mantığının CLI kodunda yer alması.
Tür algılama ve tanımlayıcı oluşturma için programlı erişimin olmaması.
Teşhis yeteneklerinin diğer hizmetlere entegre edilmesinin zor olması.
Veri analiz iş akışlarının birleştirme yeteneğinin sınırlı olması.

Bu özellik, yapılandırılmış veri teşhisi için özel bir hizmet oluşturarak bu boşlukları giderir. Bu yetenekleri bir hizmet olarak sunarak, TrustGraph şunları yapabilir:
Diğer hizmetlerin verileri programlı olarak analiz etmesine olanak sağlama.
Daha karmaşık veri işleme süreçlerini destekleme.
Harici sistemlerle entegrasyonu kolaylaştırma.
Endişelerin ayrılması yoluyla bakım kolaylığını artırma.

## Teknik Tasarım

### Mimari

Yapılandırılmış veri teşhis hizmeti, aşağıdaki teknik bileşenleri gerektirir:

1. **Teşhis Hizmeti İşlemcisi**
   Gelen teşhis isteklerini işler.
   Tür algılama ve tanımlayıcı oluşturmayı koordine eder.
   Teşhis sonuçlarıyla yapılandırılmış yanıtlar döndürür.

   Modül: `trustgraph-flow/trustgraph/diagnosis/structured_data/service.py`

2. **Veri Türü Algılayıcı**
   Algoritmik algılama kullanarak veri biçimini (CSV, JSON, XML) belirler.
   Veri yapısını, ayırıcıları ve sözdizimi kalıplarını analiz eder.
   Algılanan biçimi ve güvenilirlik puanlarını döndürür.

   Modül: `trustgraph-flow/trustgraph/diagnosis/structured_data/type_detector.py`

3. **Tanımlayıcı Oluşturucu**
   Tanımlayıcılar oluşturmak için bir istem hizmetini kullanır.
   Biçime özgü istemleri (diagnose-csv, diagnose-json, diagnose-xml) çağırır.
   Veri alanlarını, istem yanıtları aracılığıyla TrustGraph şema alanlarına eşler.

   Modül: `trustgraph-flow/trustgraph/diagnosis/structured_data/descriptor_generator.py`

### Veri Modelleri

#### StructuredDataDiagnosisRequest

Yapılandırılmış veri teşhis işlemleri için istek mesajı:

```python
class StructuredDataDiagnosisRequest:
    operation: str  # "detect-type", "generate-descriptor", or "diagnose"
    sample: str     # Data sample to analyze (text content)
    type: Optional[str]  # Data type (csv, json, xml) - required for generate-descriptor
    schema_name: Optional[str]  # Target schema name for descriptor generation
    options: Dict[str, Any]  # Additional options (e.g., delimiter for CSV)
```

#### YapılandırılmışVeriTeşhisYanıtı

Teşhis sonuçlarını içeren yanıt mesajı:

```python
class StructuredDataDiagnosisResponse:
    operation: str  # The operation that was performed
    detected_type: Optional[str]  # Detected data type (for detect-type/diagnose)
    confidence: Optional[float]  # Confidence score for type detection
    descriptor: Optional[Dict]  # Generated descriptor (for generate-descriptor/diagnose)
    error: Optional[str]  # Error message if operation failed
    metadata: Dict[str, Any]  # Additional metadata (e.g., field count, sample records)
```

#### Açıklayıcı Yapı

Oluşturulan açıklayıcı, mevcut yapılandırılmış veri açıklayıcı biçimini izler:

```json
{
  "format": {
    "type": "csv",
    "encoding": "utf-8",
    "options": {
      "delimiter": ",",
      "has_header": true
    }
  },
  "mappings": [
    {
      "source_field": "customer_id",
      "target_field": "id",
      "transforms": [
        {"type": "trim"}
      ]
    }
  ],
  "output": {
    "schema_name": "customer",
    "options": {
      "batch_size": 1000,
      "confidence": 0.9
    }
  }
}
```

### Hizmet Arayüzü

Hizmet, istek/yanıt kalıbı aracılığıyla aşağıdaki işlemleri sunacaktır:

1. **Tip Algılama İşlemi**
   Giriş: Veri örneği
   İşlem: Algoritmik algılama kullanarak veri yapısını analiz etme
   Çıkış: Belirlenen tip ve güvenilirlik skoru

2. **Açıklayıcı Oluşturma İşlemi**
   Giriş: Veri örneği, tip, hedef şema adı
   İşlem:
     Biçime özgü bir istem kimliği (diagnose-csv, diagnose-json veya diagnose-xml) ile istem hizmetini çağırın.
     Veri örneğini ve mevcut şemaları isteme iletin.
     İstem yanıtından oluşturulan açıklayıcıyı alın.
   Çıkış: Yapılandırılmış veri açıklayıcısı

3. **Birleşik Tanılama İşlemi**
   Giriş: Veri örneği, isteğe bağlı şema adı
   İşlem:
     Önce algoritmik algılama kullanarak biçimi belirleyin.
     Belirlenen tipe göre uygun biçime özgü istemi seçin.
     Açıklayıcı oluşturmak için istem hizmetini çağırın.
   Çıkış: Hem belirlenen tip hem de açıklayıcı

### Uygulama Detayları

Hizmet, TrustGraph hizmeti geleneklerini takip edecektir:

1. **Hizmet Kaydı**
   `structured-diag` hizmet türü olarak kaydedin
   Standart istek/yanıt konularını kullanın
   FlowProcessor temel sınıfını uygulayın
   İstem hizmeti etkileşimi için PromptClientSpec'i kaydedin

2. **Yapılandırma Yönetimi**
   Şema yapılandırmalarına yapılandırma hizmeti aracılığıyla erişin
   Performans için şemaları önbelleğe alın
   Yapılandırma güncellemelerini dinamik olarak işleyin

3. **İstem Entegrasyonu**
   Mevcut istem hizmeti altyapısını kullanın
   Biçime özgü istem kimlikleriyle istem hizmetini çağırın:
     `diagnose-csv`: CSV verisi analizi için
     `diagnose-json`: JSON verisi analizi için
     `diagnose-xml`: XML verisi analizi için
   İstemler, hizmette sabit kodlanmış olan istem yapılandırmasında yapılandırılmıştır.
   Şemaları ve veri örneklerini istem değişkenleri olarak iletin
   Açıklayıcıları çıkarmak için istem yanıtlarını ayrıştırın

4. **Hata Yönetimi**
   Giriş veri örneklerini doğrulayın
   Açıklayıcı hata mesajları sağlayın
   Hatalı verileri zarif bir şekilde işleyin
   İstem hizmeti hatalarını işleyin

5. **Veri Örneklemesi**
   Yapılandırılabilir örnek boyutlarını işleyin
   Eksik kayıtları uygun şekilde işleyin
   Örnekleme tutarlılığını koruyun

### API Entegrasyonu

Hizmet, mevcut TrustGraph API'leriyle entegre olacaktır:

Değiştirilen Bileşenler:
`tg-load-structured-data` CLI - Tanılama işlemleri için yeni hizmeti kullanmak üzere yeniden düzenlendi
Flow API - Yapılandırılmış veri tanılama isteklerini desteklemek üzere genişletildi

Yeni Hizmet Uç Noktaları:
`/api/v1/flow/{flow}/diagnose/structured-data` - Tanılama istekleri için WebSocket uç noktası
`/api/v1/diagnose/structured-data` - Senkron tanılama için REST uç noktası

### Mesaj Akışı

```
Client → Gateway → Structured Diag Service → Config Service (for schemas)
                                           ↓
                                    Type Detector (algorithmic)
                                           ↓
                                    Prompt Service (diagnose-csv/json/xml)
                                           ↓
                                 Descriptor Generator (parses prompt response)
                                           ↓
Client ← Gateway ← Structured Diag Service (response)
```

## Güvenlik Hususları

Enjeksiyon saldırılarını önlemek için girdi doğrulama
DoS saldırılarını önlemek için veri örnekleri üzerindeki boyut sınırlamaları
Oluşturulan tanımlayıcıların temizlenmesi
Mevcut TrustGraph kimlik doğrulama aracılığıyla erişim kontrolü

## Performans Hususları

Yapılandırma hizmeti çağrılarını azaltmak için şema tanımlarını önbelleğe alın
Duyarlı performansı korumak için örnek boyutlarını sınırlayın
Büyük veri örnekleri için akış işleme kullanın
Uzun süren analizler için zaman aşımı mekanizmaları uygulayın

## Test Stratejisi

1. **Birim Testleri**
   Çeşitli veri formatları için tür tespiti
   Tanımlayıcı oluşturma doğruluğu
   Hata işleme senaryoları

2. **Entegrasyon Testleri**
   Hizmet istek/yanıt akışı
   Şema alma ve önbelleğe alma
   CLI entegrasyonu

3. **Performans Testleri**
   Büyük örnek işleme
   Eşzamanlı istek işleme
   Yük altında bellek kullanımı

## Geçiş Planı

1. **1. Aşama**: Temel işlevselliğe sahip hizmeti uygulayın
2. **2. Aşama**: CLI'ı hizmeti kullanacak şekilde yeniden düzenleyin (geriye dönük uyumluluğu koruyun)
3. **3. Aşama**: REST API uç noktaları ekleyin
4. **4. Aşama**: Gömülü CLI mantığını kullanımdan kaldırın (bildirim süresiyle)

## Zaman Çizelgesi

1-2. Hafta: Temel hizmeti ve tür tespitini uygulayın
3-4. Hafta: Tanımlayıcı oluşturmayı ve entegrasyonu ekleyin
5. Hafta: Test ve dokümantasyon
6. Hafta: CLI yeniden düzenlemesi ve geçiş

## Açık Sorular

Hizmet, ek veri formatlarını (örneğin, Parquet, Avro) desteklemeli mi?
Analiz için maksimum örnek boyutu ne olmalıdır?
Teşhis sonuçları, tekrarlanan istekler için önbelleğe alınmalı mı?
Hizmet, çoklu şema senaryolarını nasıl işlemelidir?
İstek kimlikleri, hizmet için yapılandırılabilir parametreler olmalı mı?

## Referanslar

[Yapılandırılmış Veri Tanımlayıcı Özellikleri](structured-data-descriptor.md)
[Yapılandırılmış Veri Yükleme Dokümantasyonu](structured-data.md)
`tg-load-structured-data` uygulaması: `trustgraph-cli/trustgraph/cli/load_structured_data.py`
