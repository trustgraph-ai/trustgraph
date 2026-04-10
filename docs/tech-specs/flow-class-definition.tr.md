# Akış Şeması Tanım Özellikleri

## Genel Bakış

Bir akış şeması, TrustGraph sisteminde eksiksiz bir veri akışı kalıbı şablonunu tanımlar. Örneklenildiğinde, verilerin alınması, işlenmesi, depolanması ve sorgulanması işlemlerini tek bir sistem olarak ele alan, birbirine bağlı bir işlemci ağı oluşturur.

## Yapı

Bir akış şeması tanımı, beş ana bölümden oluşur:

### 1. Sınıf Bölümü
Her akış şeması için yalnızca bir kez örneklendirilen, paylaşılan hizmet işlemcilerini tanımlar. Bu işlemciler, bu sınıfın tüm akış örneklerinden gelen istekleri işler.

```json
"class": {
  "service-name:{class}": {
    "request": "queue-pattern:{class}",
    "response": "queue-pattern:{class}",
    "settings": {
      "setting-name": "fixed-value",
      "parameterized-setting": "{parameter-name}"
    }
  }
}
```

**Özellikler:**
Aynı sınıftaki tüm akış örnekleri arasında paylaşılır.
Genellikle maliyetli veya durumsuz hizmetlerdir (LLM'ler, gömme modelleri).
Kuyruk adlandırması için `{class}` şablon değişkenini kullanın.
Ayarlar, sabit değerler olabilir veya `{parameter-name}` sözdizimi ile parametrelendirilebilir.
Örnekler: `embeddings:{class}`, `text-completion:{class}`, `graph-rag:{class}`

### 2. Akış Bölümü
Her bir bireysel akış örneği için örneklenen, akışa özgü işlemcileri tanımlar. Her akışın kendi izole edilmiş işlemci kümesi vardır.

```json
"flow": {
  "processor-name:{id}": {
    "input": "queue-pattern:{id}",
    "output": "queue-pattern:{id}",
    "settings": {
      "setting-name": "fixed-value",
      "parameterized-setting": "{parameter-name}"
    }
  }
}
```

**Özellikler:**
Her akış için benzersiz bir örnek
Akışa özgü verileri ve durumu yönetir
Kuyruğu adlandırmak için `{id}` şablon değişkenini kullanın
Ayarlar, sabit değerler olabilir veya `{parameter-name}` sözdizimi ile parametrelendirilebilir
Örnekler: `chunker:{id}`, `pdf-decoder:{id}`, `kg-extract-relationships:{id}`

### 3. Arayüzler Bölümü
Akış için giriş noktalarını ve etkileşim sözleşmelerini tanımlar. Bunlar, harici sistemler ve dahili bileşen iletişimi için API yüzeyini oluşturur.

Arayüzler iki formda olabilir:

**Ateşle ve Unut (Fire-and-Forget) Modeli** (tek kuyruk):
```json
"interfaces": {
  "document-load": "persistent://tg/flow/document-load:{id}",
  "triples-store": "persistent://tg/flow/triples-store:{id}"
}
```

**İstek/Yanıt Modeli** (istek/yanıt alanlarına sahip nesne):
```json
"interfaces": {
  "embeddings": {
    "request": "non-persistent://tg/request/embeddings:{class}",
    "response": "non-persistent://tg/response/embeddings:{class}"
  }
}
```

**Arayüz Türleri:**
**Giriş Noktaları:** Dış sistemlerin veri enjekte ettiği yerler (`document-load`, `agent`)
**Servis Arayüzleri:** Servisler için istek/yanıt kalıpları (`embeddings`, `text-completion`)
**Veri Arayüzleri:** Ateşle-ve-unut veri akışı bağlantı noktaları (`triples-store`, `entity-contexts-load`)

### 4. Parametreler Bölümü
Akışa özgü parametre adlarını, merkezi olarak saklanan parametre tanımlarına eşler:

```json
"parameters": {
  "model": "llm-model",
  "temp": "temperature",
  "chunk": "chunk-size"
}
```

**Özellikler:**
Anahtarlar, işlemci ayarlarında kullanılan parametre adlarıdır (örneğin, `{model}`).
Değerler, şema/yapılandırmada saklanan parametre tanımlarına referans verir.
Akışlar arasında ortak parametre tanımlarının yeniden kullanılmasını sağlar.
Parametre şemalarının çoğaltılmasını azaltır.

### 5. Meta Veriler
Akış şeması hakkında ek bilgiler:

```json
"description": "Human-readable description",
"tags": ["capability-1", "capability-2"]
```

## Şablon Değişkenleri

### Sistem Değişkenleri

#### {id}
Her akış örneği için benzersiz tanımlayıcı ile değiştirilir.
Her akış için izole kaynaklar oluşturur.
Örnek: `flow-123`, `customer-A-flow`

#### {class}
Akış şablonu adıyla değiştirilir.
Aynı sınıftaki akışlar arasında paylaşılan kaynaklar oluşturur.
Örnek: `standard-rag`, `enterprise-rag`

### Parametre Değişkenleri

#### {parametre-adı}
Akış başlatma zamanında tanımlanan özel parametrelerdir.
Parametre adları, akışın `parameters` bölümündeki anahtarlarla eşleşir.
İşlemci ayarlarında davranışı özelleştirmek için kullanılır.
Örnekler: `{model}`, `{temp}`, `{chunk}`
Akışı başlattığınızda sağlanan değerlerle değiştirilir.
Merkezi olarak saklanan parametre tanımlarına göre doğrulanır.

## İşlemci Ayarları

Ayarlar, işlemcilerin başlatma zamanındaki yapılandırma değerlerini sağlar. Bunlar şunlar olabilir:

### Sabit Ayarlar
Değişmeyen doğrudan değerler:
```json
"settings": {
  "model": "gemma3:12b",
  "temperature": 0.7,
  "max_retries": 3
}
```

### Parametreleştirilmiş Ayarlar
Akış başlatılırken sağlanan parametreleri kullanan değerler:
```json
"settings": {
  "model": "{model}",
  "temperature": "{temp}",
  "endpoint": "https://{region}.api.example.com"
}
```

Ayarlardaki parametre adları, akışın `parameters` bölümündeki anahtarlara karşılık gelir.

### Ayar Örnekleri

**Parametrelerle LLM İşlemcisi:**
```json
// In parameters section:
"parameters": {
  "model": "llm-model",
  "temp": "temperature",
  "tokens": "max-tokens",
  "key": "openai-api-key"
}

// In processor definition:
"text-completion:{class}": {
  "request": "non-persistent://tg/request/text-completion:{class}",
  "response": "non-persistent://tg/response/text-completion:{class}",
  "settings": {
    "model": "{model}",
    "temperature": "{temp}",
    "max_tokens": "{tokens}",
    "api_key": "{key}"
  }
}
```

**Sabit ve Parametreize Ayarlara Sahip Parçalayıcı:**
```json
// In parameters section:
"parameters": {
  "chunk": "chunk-size"
}

// In processor definition:
"chunker:{id}": {
  "input": "persistent://tg/flow/chunk:{id}",
  "output": "persistent://tg/flow/chunk-load:{id}",
  "settings": {
    "chunk_size": "{chunk}",
    "chunk_overlap": 100,
    "encoding": "utf-8"
  }
}
```

## Kuyruk Desenleri (Pulsar)

Akış şemaları, mesajlaşma için Apache Pulsar'ı kullanır. Kuyruk adları, Pulsar formatını izler:
```
<persistence>://<tenant>/<namespace>/<topic>
```

### Bileşenler:
**kalıcılık**: `persistent` veya `non-persistent` (Pulsar kalıcılık modu)
**kiracı**: TrustGraph tarafından sağlanan akış tanım şablonları için `tg`
**isim alanı**: Mesajlaşma desenini belirtir
  `flow`: Ateşle ve unut hizmetleri
  `request`: İstek/yanıt hizmetlerinin istek kısmı
  `response`: İstek/yanıt hizmetlerinin yanıt kısmı
**konu**: Şablon değişkenleriyle belirli kuyruk/konu adı

### Kalıcı Kuyruklar
Desen: `persistent://tg/flow/<topic>:{id}`
Ateşle ve unut hizmetleri ve dayanıklı veri akışı için kullanılır
Veri, yeniden başlatmalarda Pulsar depolama alanında kalıcıdır
Örnek: `persistent://tg/flow/chunk-load:{id}`

### Kalıcı Olmayan Kuyruklar
Desen: `non-persistent://tg/request/<topic>:{class}` veya `non-persistent://tg/response/<topic>:{class}`
İstek/yanıt mesajlaşma desenleri için kullanılır
Pulsar tarafından diske kalıcı hale getirilmez, geçicidir
Daha düşük gecikme süresi, RPC tarzı iletişim için uygundur
Örnek: `non-persistent://tg/request/embeddings:{class}`

## Veri Akışı Mimarisi

Akış tanımı, aşağıdaki gibi birleşik bir veri akışı oluşturur:

1. **Belge İşleme Hattı**: Alımdan dönüşüme ve depolamaya kadar olan akış
2. **Sorgu Hizmetleri**: Aynı veri depolarını ve hizmetlerini sorgulayan entegre işlemciler
3. **Paylaşımlı Hizmetler**: Tüm akışların kullanabileceği merkezi işlemciler
4. **Depolama Yazıcıları**: İşlenmiş verileri uygun depolama alanlarına kaydeder

Tüm işlemciler (hem `{id}` hem de `{class}`), ayrı sistemler olarak değil, uyumlu bir veri akışı grafiği olarak birlikte çalışır.

## Örnek Akış Oluşturma

Verilenler:
Akış Örneği Kimliği: `customer-A-flow`
Akış Tanımı: `standard-rag`
Akış parametre eşlemeleri:
  `"model": "llm-model"`
  `"temp": "temperature"`
  `"chunk": "chunk-size"`
Kullanıcı tarafından sağlanan parametreler:
  `model`: `gpt-4`
  `temp`: `0.5`
  `chunk`: `512`

Şablon genişletmeleri:
`persistent://tg/flow/chunk-load:{id}` → `persistent://tg/flow/chunk-load:customer-A-flow`
`non-persistent://tg/request/embeddings:{class}` → `non-persistent://tg/request/embeddings:standard-rag`
`"model": "{model}"` → `"model": "gpt-4"`
`"temperature": "{temp}"` → `"temperature": "0.5"`
`"chunk_size": "{chunk}"` → `"chunk_size": "512"`

Bu, aşağıdaki öğeleri oluşturur:
`customer-A-flow` için izole edilmiş belge işleme hattı
Tüm `standard-rag` akışları için paylaşımlı gömme hizmeti
Belge alımından sorgulamaya kadar olan eksiksiz veri akışı
İşlemciler, sağlanan parametre değerleriyle yapılandırılmıştır

## Avantajlar

1. **Kaynak Verimliliği**: Pahalı hizmetler, akışlar arasında paylaşılır
2. **Akış İzolasyonu**: Her akışın kendi veri işleme hattı vardır
3. **Ölçeklenebilirlik**: Aynı şablondan birden fazla akış oluşturulabilir
4. **Modülerlik**: Paylaşılan ve akışa özgü bileşenler arasında net bir ayrım
5. **Bütünleşik Mimari**: Sorgu ve işleme, aynı veri akışının bir parçasıdır