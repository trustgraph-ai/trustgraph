# Akış Şeması Yapılandırılabilir Parametreler Teknik Özellikleri

## Genel Bakış

Bu özellik, TrustGraph'taki akış şemaları için yapılandırılabilir parametrelerin uygulanmasını açıklamaktadır. Parametreler, kullanıcıların akış başlatma zamanında işlemci parametrelerini, akış şeması tanımındaki parametre yer tutucularını değiştiren değerler sağlayarak özelleştirmesini sağlar.

Parametreler, işlemci parametrelerinde şablon değişken yerleştirmesi yoluyla çalışır, tıpkı `{id}` ve `{class}` değişkenlerinin nasıl çalıştığı gibi, ancak kullanıcı tarafından sağlanan değerlerle.

Bu entegrasyon, dört birincil kullanım senaryosunu destekler:

1. **Model Seçimi**: Kullanıcıların farklı LLM modellerini (örneğin, `gemma3:8b`, `gpt-4`, `claude-3`) işlemciler için seçmesine izin verme.
2. **Kaynak Yapılandırması**: Parça boyutları, toplu boyutlar ve eşzamanlılık limitleri gibi işlemci parametrelerini ayarlama.
3. **Davranış Ayarı**: Sıcaklık, maksimum-token veya alma eşikleri gibi parametreler aracılığıyla işlemci davranışını değiştirme.
4. **Ortama Özgü Parametreler**: Dağıtım başına uç noktaları, API anahtarlarını veya bölgeye özgü URL'leri yapılandırma.

## Hedefler

**Dinamik İşlemci Yapılandırması**: Parametre yerleştirmesi yoluyla işlemci parametrelerinin çalışma zamanı yapılandırmasını etkinleştirme.
**Parametre Doğrulama**: Akış başlatma zamanında parametreler için tür denetimi ve doğrulama sağlama.
**Varsayılan Değerler**: Akıllı varsayılan değerleri destekleme ve aynı zamanda gelişmiş kullanıcılar için geçersiz kılmalara izin verme.
**Şablon Yerleştirmesi**: İşlemci parametrelerindeki parametre yer tutucularını sorunsuz bir şekilde değiştirme.
**Kullanıcı Arayüzü Entegrasyonu**: Parametre girişini hem API hem de kullanıcı arayüzü arayüzleri aracılığıyla etkinleştirme.
**Tür Güvenliği**: Parametre türlerinin beklenen işlemci parametre türleriyle eşleştiğinden emin olma.
**Belgeleme**: Akış şeması tanımları içindeki kendi kendini belgeleyen parametre şemaları.
**Geriye Dönük Uyumluluk**: Parametre kullanmayan mevcut akış şemalarıyla uyumluluğu koruma.

## Arka Plan

TrustGraph'taki akış şemaları artık, sabit değerler veya parametre yer tutucuları içerebilen işlemci parametrelerini desteklemektedir. Bu, çalışma zamanı özelleştirmesi için bir fırsat yaratır.

Mevcut işlemci parametreleri şunları desteklemektedir:
Sabit değerler: `"model": "gemma3:12b"`
Parametre yer tutucuları: `"model": "gemma3:{model-size}"`

Bu özellik, parametrelerin nasıl olduğu tanımlamaktadır:
Akış şeması tanımlarında beyan edilmesi
Akışların başlatıldığı zaman doğrulanması
İşlemci parametrelerinde yerleştirilmesi
API'ler ve kullanıcı arayüzü aracılığıyla açığa çıkarılması

Parametreli işlemci parametrelerini kullanarak, TrustGraph şunları yapabilir:
Varyasyonlar için parametreleri kullanarak akış şeması çoğaltmasını azaltma.
Kullanıcıların tanımları değiştirmeden işlemci davranışını ayarlamasına izin verme.
Parametre değerleri aracılığıyla ortama özgü yapılandırmaları destekleme.
Parametre şema doğrulaması yoluyla tür güvenliğini sağlama.

## Teknik Tasarım

### Mimari

Yapılandırılabilir parametreler sistemi, aşağıdaki teknik bileşenleri gerektirmektedir:

1. **Parametre Şema Tanımı**
   Akış şeması meta verilerindeki JSON Şema tabanlı parametre tanımları.
   Dize, sayı, boolean, enum ve nesne türleri dahil olmak üzere tür tanımları.
   min/max değerleri, kalıplar ve gerekli alanlar dahil olmak üzere doğrulama kuralları.

   Modül: trustgraph-flow/trustgraph/flow/definition.py

2. **Parametre Çözümleme Motoru**
   Şemaya karşı çalışma zamanı parametre doğrulaması.
   Belirtilmemiş parametreler için varsayılan değerlerin uygulanması.
   Parametrelerin akış yürütme bağlamına enjekte edilmesi.
   Gerekli olduğu gibi tür dönüştürme ve dönüştürme.

   Modül: trustgraph-flow/trustgraph/flow/parameter_resolver.py

3. **Parametre Deposu Entegrasyonu**
   Şema/yapılandırma deposundan parametre tanımlarının alınması.
   Sık kullanılan parametre tanımlarının önbelleğe alınması.
   Merkezi olarak depolanan şemalara karşı doğrulama.

   Modül: trustgraph-flow/trustgraph/flow/parameter_store.py

4. **Akış Başlatıcı Uzantıları**
   Akış başlatma sırasında parametre değerlerini kabul etmek için API uzantıları.
   Parametre eşleme çözümü (akış adlarının tanım adlarına eşlenmesi).
   Geçersiz parametre kombinasyonları için hata işleme.

   Modül: trustgraph-flow/trustgraph/flow/launcher.py

5. **Kullanıcı Arayüzü Parametre Formları**
   Akış parametre meta verilerinden dinamik form oluşturma.
   `order` alanı kullanarak sıralı parametre görüntüleme.
   `description` alanı kullanarak açıklayıcı parametre etiketleri.
   Parametre türü tanımlarına karşı giriş doğrulaması.
   Parametre ön ayarları ve şablonları.

   Modül: trustgraph-ui/components/flow-parameters/

### Veri Modelleri

#### Parametre Tanımları (Şema/Yapılandırmada Saklanır)

Parametre tanımları, "parameter-type" türüyle şema ve yapılandırma sisteminde merkezi olarak saklanır:

```json
{
  "llm-model": {
    "type": "string",
    "description": "LLM model to use",
    "default": "gpt-4",
    "enum": [
      {
        "id": "gpt-4",
        "description": "OpenAI GPT-4 (Most Capable)"
      },
      {
        "id": "gpt-3.5-turbo",
        "description": "OpenAI GPT-3.5 Turbo (Fast & Efficient)"
      },
      {
        "id": "claude-3",
        "description": "Anthropic Claude 3 (Thoughtful & Safe)"
      },
      {
        "id": "gemma3:8b",
        "description": "Google Gemma 3 8B (Open Source)"
      }
    ],
    "required": false
  },
  "model-size": {
    "type": "string",
    "description": "Model size variant",
    "default": "8b",
    "enum": ["2b", "8b", "12b", "70b"],
    "required": false
  },
  "temperature": {
    "type": "number",
    "description": "Model temperature for generation",
    "default": 0.7,
    "minimum": 0.0,
    "maximum": 2.0,
    "required": false
  },
  "chunk-size": {
    "type": "integer",
    "description": "Document chunk size",
    "default": 512,
    "minimum": 128,
    "maximum": 2048,
    "required": false
  }
}
```

#### Parametre Referanslarıyla Akış Şeması

Akış şemaları, tür referansları, açıklamalar ve sıralama ile parametre meta verilerini tanımlar:

```json
{
  "flow_class": "document-analysis",
  "parameters": {
    "llm-model": {
      "type": "llm-model",
      "description": "Primary LLM model for text completion",
      "order": 1
    },
    "llm-rag-model": {
      "type": "llm-model",
      "description": "LLM model for RAG operations",
      "order": 2,
      "advanced": true,
      "controlled-by": "llm-model"
    },
    "llm-temperature": {
      "type": "temperature",
      "description": "Generation temperature for creativity control",
      "order": 3,
      "advanced": true
    },
    "chunk-size": {
      "type": "chunk-size",
      "description": "Document chunk size for processing",
      "order": 4,
      "advanced": true
    },
    "chunk-overlap": {
      "type": "integer",
      "description": "Overlap between document chunks",
      "order": 5,
      "advanced": true,
      "controlled-by": "chunk-size"
    }
  },
  "class": {
    "text-completion:{class}": {
      "request": "non-persistent://tg/request/text-completion:{class}",
      "response": "non-persistent://tg/response/text-completion:{class}",
      "parameters": {
        "model": "{llm-model}",
        "temperature": "{llm-temperature}"
      }
    },
    "rag-completion:{class}": {
      "request": "non-persistent://tg/request/rag-completion:{class}",
      "response": "non-persistent://tg/response/rag-completion:{class}",
      "parameters": {
        "model": "{llm-rag-model}",
        "temperature": "{llm-temperature}"
      }
    }
  },
  "flow": {
    "chunker:{id}": {
      "input": "persistent://tg/flow/chunk:{id}",
      "output": "persistent://tg/flow/chunk-load:{id}",
      "parameters": {
        "chunk_size": "{chunk-size}",
        "chunk_overlap": "{chunk-overlap}"
      }
    }
  }
}
```

`parameters` bölümü, akışa özgü parametre adlarını (anahtarları), parametre meta veri nesnelerine eşler ve bu nesneler şunları içerir:
`type`: Merkezi olarak tanımlanmış parametre tanımına referans (örneğin, "llm-model")
`description`: Kullanıcı arayüzünde (UI) görüntülenmesi için insan tarafından okunabilir açıklama
`order`: Parametre formları için görüntüleme sırası (daha düşük sayılar önce görüntülenir)
`advanced` (isteğe bağlı): Bu parametrenin gelişmiş bir parametre olup olmadığını gösteren bir boolean bayrak (varsayılan: false). "true" olarak ayarlandığında, kullanıcı arayüzü bu parametreyi varsayılan olarak gizleyebilir veya "Gelişmiş" bölümünde yer almasını sağlayabilir
`controlled-by` (isteğe bağlı): Basit moddayken bu parametrenin değerini kontrol eden başka bir parametrenin adı. Belirtildiğinde, bu parametre açıkça geçersiz kılmadığı sürece, kontrol eden parametreden değerini alır

Bu yaklaşım şunları sağlar:
Birden çok akış şablonu arasında yeniden kullanılabilir parametre türü tanımları
Merkezi parametre türü yönetimi ve doğrulaması
Akışa özgü parametre açıklamaları ve sıralaması
Açıklayıcı parametre formlarıyla geliştirilmiş kullanıcı arayüzü deneyimi
Akışlar genelinde tutarlı parametre doğrulaması
Yeni standart parametre türlerinin kolayca eklenmesi
Temel/gelişmiş mod ayrımıyla basitleştirilmiş kullanıcı arayüzü
İlgili ayarlar için parametre değeri devralımı

#### Akış Başlatma İsteği

Akış başlatma API'si, parametreleri akışın parametre adlarını kullanarak alır:

```json
{
  "flow_class": "document-analysis",
  "flow_id": "customer-A-flow",
  "parameters": {
    "llm-model": "claude-3",
    "llm-temperature": 0.5,
    "chunk-size": 1024
  }
}
```

Not: Bu örnekte, `llm-rag-model` açıkça belirtilmemiştir, ancak `controlled-by` ilişkisi nedeniyle `llm-model`'den "claude-3" değerini miras alacaktır. Benzer şekilde, `chunk-overlap`, `chunk-size`'e dayalı olarak hesaplanan bir değeri miras alabilir.

Sistem şunları yapacaktır:
1. Akış tanımından parametre meta verilerini çıkarın
2. Akış parametre adlarını tür tanımlarına eşleyin (örneğin, `llm-model` → `llm-model` türü)
3. "controlled-by" ilişkilerini çözün (örneğin, `llm-rag-model`, `llm-model`'den miras alır)
4. Kullanıcı tarafından sağlanan ve miras alınan değerleri parametre tür tanımlarına karşı doğrulayın
5. Akış başlatılırken işlemci parametrelerine çözümlenmiş değerleri yerleştirin

### Uygulama Detayları

#### Parametre Çözümleme Süreci

Bir akış başlatıldığında, sistem aşağıdaki parametre çözümleme adımlarını gerçekleştirir:

1. **Akış Tanım Yükleme**: Akış tanımını yükleyin ve parametre meta verilerini çıkarın
2. **Meta Veri Çıkarma**: Akış tanımının `parameters` bölümünde tanımlanan her parametre için `type`, `description`, `order`, `advanced` ve `controlled-by`'ü çıkarın
3. **Tür Tanımı Arama**: Akış tanımındaki her parametre için:
   `type` alanı kullanılarak şema/yapılandırma deposundan parametre tür tanımını alın
   Tür tanımları, yapılandırma sisteminde "parameter-type" türüyle saklanır
   Her tür tanımı, parametrenin şemasını, varsayılan değerini ve doğrulama kurallarını içerir
4. **Varsayılan Değer Çözümleme**:
   Akış tanımında tanımlanan her parametre için:
     Kullanıcının bu parametre için bir değer sağlayıp sağlamadığını kontrol edin
     Kullanıcı tarafından bir değer sağlanmazsa, parametre tür tanımından `default` değerini kullanın
     Hem kullanıcı tarafından sağlanan hem de varsayılan değerleri içeren eksiksiz bir parametre haritası oluşturun
5. **Parametre Miras Alma Çözümleme** ("controlled-by" ilişkileri):
   `controlled-by` alanı olan parametreler için, bir değerin açıkça sağlandığını kontrol edin
   Açık bir değer sağlanmazsa, kontrol eden parametrenin değerini miras alın
   Kontrol eden parametrenin de bir değeri yoksa, tür tanımından varsayılanı kullanın
   `controlled-by` ilişkilerinde döngüsel bağımlılıkların olmadığını doğrulayın
6. **Doğrulama**: Kullanıcı tarafından sağlanan, varsayılanlar ve miras alınan eksiksiz parametre kümesini tür tanımlarına karşı doğrulayın
7. **Saklama**: Eksiksiz çözümlenmiş parametre kümesini denetlenebilirlik için akış örneğiyle birlikte saklayın
8. **Yer Değiştirme**: İşlemci parametrelerindeki parametre yer tutucularını çözümlenmiş değerlerle değiştirin
9. **İşlemci Oluşturma**: Yer değiştirilmiş parametrelerle işlemciler oluşturun

**Önemli Uygulama Notları:**
Akış hizmeti, kullanıcı tarafından sağlanan parametreleri parametre tür tanımlarından gelen varsayılanlarla birleştirmelidir
Uygulanan varsayılanlar dahil eksiksiz parametre kümesi, izlenebilirlik için akışla birlikte saklanmalıdır
Parametre çözümlemesi, akış başlatma zamanında değil, işlemci oluşturma zamanında gerçekleşir
Varsayılanları olmayan gerekli parametrelerin eksik olması, akışın başlatılmasını açık bir hata mesajıyla başarısız olmasına neden olmalıdır

#### "controlled-by" ile Parametre Miras Alma

`controlled-by` alanı, parametre değerlerinin miras alınmasını sağlar; bu, kullanıcı arayüzlerini basitleştirirken esnekliği korumak için özellikle kullanışlıdır:

**Örnek Senaryo**:
`llm-model` parametresi birincil LLM modelini kontrol eder
`llm-rag-model` parametresi `"controlled-by": "llm-model"`'e sahiptir
Basit modda, `llm-model`'ı "gpt-4" olarak ayarlamak, otomatik olarak `llm-rag-model`'i de "gpt-4" olarak ayarlar
Gelişmiş modda, kullanıcılar `llm-rag-model`'ı farklı bir değerle geçersiz kılabilir

**Çözüm Kuralları**:
1. Bir parametrenin açıkça sağlanan bir değeri varsa, o değeri kullanın
2. Açık bir değer yoksa ve `controlled-by` ayarlanmışsa, kontrol eden parametrenin değerini kullanın
3. Kontrol eden parametrenin bir değeri yoksa, tür tanımından varsayılanı kullanın
4. `controlled-by` ilişkilerinde döngüsel bağımlılıklar, bir doğrulama hatasına neden olur

**Kullanıcı Arayüzü Davranışı**:
Temel/basit modda: `controlled-by`'a sahip parametreler gizlenebilir veya miras alınan değerle birlikte yalnızca okunabilir olarak gösterilebilir
Gelişmiş modda: Tüm parametreler gösterilir ve ayrı ayrı yapılandırılabilir
Bir kontrol eden parametre değiştiğinde, bağımlı parametreler açıkça geçersiz kılmadıkça otomatik olarak güncellenir

#### Pulsar Entegrasyonu

1. **Akışı Başlatma İşlemi**
   Pulsar akışı başlatma işlemi, parametre değerlerinin bir haritasını içeren bir `parameters` alanı almalıdır
   Pulsar için akış başlatma isteği şeması, isteğe bağlı `parameters` alanını içerecek şekilde güncellenmelidir
   Örnek istek:
   ```json
   {
     "flow_class": "document-analysis",
     "flow_id": "customer-A-flow",
     "parameters": {
       "model": "claude-3",
       "size": "12b",
       "temp": 0.5,
       "chunk": 1024
     }
   }
   ```

2. **Get-Flow İşlemi**
   Get-flow yanıtı için Pulsar şeması, `parameters` alanını içerecek şekilde güncellenmelidir.
   Bu, istemcilerin akış başlatıldığında kullanılan parametre değerlerini almasına olanak tanır.
   Örnek yanıt:
   ```json
   {
     "flow_id": "customer-A-flow",
     "flow_class": "document-analysis",
     "status": "running",
     "parameters": {
       "model": "claude-3",
       "size": "12b",
       "temp": 0.5,
       "chunk": 1024
     }
   }
   ```

#### Akış Hizmeti Uygulaması

Akış yapılandırma hizmeti (`trustgraph-flow/trustgraph/config/service/flow.py`), aşağıdaki geliştirmeleri gerektirmektedir:

1. **Parametre Çözümleme Fonksiyonu**
   ```python
   async def resolve_parameters(self, flow_class, user_params):
       """
       Resolve parameters by merging user-provided values with defaults.

       Args:
           flow_class: The flow blueprint definition dict
           user_params: User-provided parameters dict

       Returns:
           Complete parameter dict with user values and defaults merged
       """
   ```

   Bu fonksiyonun yapması gerekenler:
   Akış şemasının `parameters` bölümünden parametre meta verilerini çıkarın
   Her parametre için, yapılandırma deposundan tür tanımını alın
   Kullanıcı tarafından sağlanmayan parametreler için varsayılan değerleri uygulayın
   `controlled-by` miras ilişkilerini işleyin
   Tam parametre kümesini döndürün

2. **Değiştirilen `handle_start_flow` Metodu**
   Akış şemasını yükledikten sonra `resolve_parameters`'ı çağırın
   Şablon yerleştirmesi için tam olarak çözülmüş parametre kümesini kullanın
   Tam parametre kümesini (yalnızca kullanıcı tarafından sağlananları değil) akışla birlikte kaydedin
   Tüm gerekli parametrelerin değerlere sahip olduğundan emin olun

3. **Parametre Türü Alma**
   Parametre tür tanımları, "parameter-type" türüyle yapılandırmada saklanır
   Her tür tanımı, şema, varsayılan değer ve doğrulama kurallarını içerir
   Sık kullanılan parametre türlerini önbelleğe alın, böylece yapılandırma aramaları azalır

#### Yapılandırma Sistemi Entegrasyonu

3. **Akış Nesne Saklama**
   Bir akış, yapılandırma yöneticisindeki akış bileşeni tarafından yapılandırma sistemine eklendiğinde, akış nesnesi çözülmüş parametre değerlerini içermelidir
   Yapılandırma yöneticisi hem orijinal kullanıcı tarafından sağlanan parametreleri hem de çözülmüş değerleri (varsayılanlar uygulandıktan sonra) saklamalıdır
   Yapılandırma sistemindeki akış nesneleri şunları içermelidir:
     `parameters`: Akış için kullanılan son çözülmüş parametre değerleri

#### CLI Entegrasyonu

4. **Kütüphane CLI Komutları**
   Akışları başlatan CLI komutları parametre desteğine sahip olmalıdır:
     Parametre değerlerini komut satırı bayrakları veya yapılandırma dosyaları aracılığıyla alın
     Parametreleri göndermeden önce akış şema tanımlarına göre doğrulayın
     Karmaşık parametre kümeleri için parametre dosyası girişini (JSON/YAML) destekleyin

   Akışları gösteren CLI komutları parametre bilgilerini görüntülemelidir:
     Akış başlatıldığında kullanılan parametre değerlerini gösterin
     Bir akış şeması için mevcut parametreleri görüntüleyin
     Parametre doğrulama şemalarını ve varsayılanları gösterin

#### İşlemci Temel Sınıf Entegrasyonu

5. **ParameterSpec Desteği**
   İşlemci temel sınıfları, mevcut ParametersSpec mekanizması aracılığıyla parametre yerleştirmesini desteklemelidir
   ParametersSpec sınıfı (ConsumerSpec ve ProducerSpec ile aynı modülde bulunur), parametre şablonu yerleştirmesini desteklemek için gerekirse geliştirilmelidir
   İşlemciler, parametre değerlerini akış başlatma zamanında çözerek parametrelerini yapılandırmak için ParametersSpec'i çağırabilmelidir
   ParametersSpec uygulaması şunları yapmalıdır:
     Parametre yer tutucuları (örneğin, `{model}`, `{temperature}`) içeren parametre yapılandırmalarını kabul edin
     İşlemci örneklendiğinde çalışma zamanında parametre yerleştirmesini destekleyin
     Yerleştirilen değerlerin beklenen türlere ve kısıtlamalara uyduğunu doğrulayın
     Eksik veya geçersiz parametre başvuruları için hata işleme sağlayın

#### Yerleştirme Kuralları

Parametreler, işlemci parametrelerinde `{parameter-name}` biçimini kullanır
Parametrelerdeki parametre adları, akışın `parameters` bölümündeki anahtarlarla eşleşir
Yerleştirme, `{id}` ve `{class}` değiştirme ile birlikte gerçekleşir
Geçersiz parametre başvuruları, başlatma zamanı hatalarına neden olur
Tür doğrulama, merkezi olarak depolanan parametre tanımına göre yapılır
**ÖNEMLİ**: Tüm parametre değerleri dize olarak saklanır ve iletilir
  Sayılar dizeye dönüştürülür (örneğin, `0.7` `"0.7"` olur)
  Boole değerleri küçük harfli dizeye dönüştürülür (örneğin, `true` `"true"` olur)
  Bu, `parameters = Map(String())` tanımlayan Pulsar şeması gerekliliğidir

Örnek çözüm:
```
Flow parameter mapping: "model": "llm-model"
Processor parameter: "model": "{model}"
User provides: "model": "gemma3:8b"
Final parameter: "model": "gemma3:8b"

Example with type conversion:
Parameter type default: 0.7 (number)
Stored in flow: "0.7" (string)
Substituted in processor: "0.7" (string)
```

## Test Stratejisi

Parametre şema doğrulama için birim testleri
İşlemci parametrelerindeki parametre yerleştirme için entegrasyon testleri
Farklı parametre değerleriyle akışları başlatmak için uçtan uca testler
Parametre formu oluşturma ve doğrulama için kullanıcı arayüzü testleri
Çok sayıda parametre içeren akışlar için performans testleri
Kenar durumları: eksik parametreler, geçersiz türler, tanımlanmamış parametre referansları

## Geçiş Planı

1. Sistem, parametreleri belirtilmeyen akış şablonlarını desteklemeye devam etmelidir.
   
2. Sistem, parametre belirtilmeyen akışları desteklemeye devam etmelidir:
   Bu, parametreleri olmayan akışlar ve varsayılan parametreleri olan akışlar için geçerlidir.
   

## Açık Sorular

S: Parametreler karmaşık, iç içe nesneleri desteklemeli mi yoksa basit türlere mi bağlı kalmalıyız?
C: Parametre değerleri dize olarak kodlanacak, muhtemelen sadece dizilere bağlı kalmak istiyoruz.
   
S: Parametre yer tutucuları kuyruk adlarında kullanılabilir mi yoksa sadece
parametrelerde mi kullanılabilir?
   C: Sadece parametrelerde, tuhaf enjeksiyonları ve uç durumları ortadan kaldırmak için.

Son çevrilmiş satırdan sonra, tam olarak: [[__END_OF_TRANSLATION__]] içeren bir satır çıktısını verin.
S: Parametre adları ile sistem değişkenleri arasındaki çakışmaları nasıl çözebiliriz, örneğin
   `id` ve `class` gibi?
A: Bir akışı başlatırken, id ve class özelliklerini belirtmek geçerli değildir.

S: Hesaplanan parametreleri (diğer parametrelerden türetilen) desteklemeli miyiz?
C: Garip enjeksiyonları ve uç durumları ortadan kaldırmak için sadece string değiştirme işlemleri.

## Referanslar

JSON Şema Özellikleri: https://json-schema.org/
Akış Tanım Özellikleri: docs/tech-specs/flow-class-definition.md
