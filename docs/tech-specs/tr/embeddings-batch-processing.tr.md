---
layout: default
title: "Gömme İşlemleri Toplu İşleme Teknik Özellikleri"
parent: "Turkish (Beta)"
---

# Gömme İşlemleri Toplu İşleme Teknik Özellikleri

> **Beta Translation:** This document was translated via Machine Learning and as such may not be 100% accurate. All non-English languages are currently classified as Beta.

## Genel Bakış

Bu teknik özellik, gömme hizmeti için, tek bir istekte birden fazla metni toplu olarak işleyebilmeyi desteklemek amacıyla yapılan optimizasyonları açıklamaktadır. Mevcut uygulama, her seferinde tek bir metni işlemektedir ve bu durum, gömme modellerinin toplu işlemler sırasında sağladığı önemli performans avantajlarından yararlanılmamasına neden olmaktadır.

1. **Tek Metin İşleme Verimsizliği**: Mevcut uygulama, tek metinleri bir liste içinde kullanarak, FastEmbed'in toplu işleme yeteneklerini tam olarak kullanamamaktadır.
2. **Metin Başına İstek Yükü**: Her metin için ayrı bir Pulsar mesajı gönderilip alınması gerekmektedir.
3. **Model Çıkarım Verimsizliği**: Gömme modellerinin sabit bir toplu işleme yükü vardır; küçük toplu işlemler GPU/CPU kaynaklarının israfına yol açar.
4. **Çağıran Tarafında Seri İşleme**: Önemli hizmetler, öğeler üzerinde döngü yaparak gömme işlemlerini tek tek gerçekleştirmektedir.

## Hedefler

**Toplu API Desteği**: Tek bir istekte birden fazla metni işleyebilmeyi destekleyin.
**Geriye Dönük Uyumluluk**: Tek metin isteklerine olan desteği koruyun.
**Önemli Verimlilik Artışı**: Toplu işlemler için 5-10 kat verimlilik artışı hedefleyin.
**Metin Başına Azaltılmış Gecikme**: Birden fazla metni gömme işlemi sırasında amortize gecikmeyi azaltın.
**Bellek Verimliliği**: Aşırı bellek tüketimi olmadan toplu işlemleri gerçekleştirin.
**Sağlayıcıdan Bağımsızlık**: FastEmbed, Ollama ve diğer sağlayıcılar arasında toplu işleme desteğini sağlayın.
**Çağıran Taraf Güncellemesi**: Toplu API'nin faydalı olduğu durumlarda tüm gömme işlemlerini kullanan hizmetleri güncelleyin.

## Arka Plan

### Mevcut Uygulama - Gömme Hizmeti

`trustgraph-flow/trustgraph/embeddings/fastembed/processor.py` içindeki gömme uygulamasında önemli bir performans verimsizliği bulunmaktadır:

```python
# fastembed/processor.py line 56
async def on_embeddings(self, text, model=None):
    use_model = model or self.default_model
    self._load_model(use_model)

    vecs = self.embeddings.embed([text])  # Single text wrapped in list

    return [v.tolist() for v in vecs]
```

**Sorunlar:**

1. **Batch Boyutu 1:** FastEmbed'in `embed()` yöntemi, toplu işleme için optimize edilmiştir, ancak bunu her zaman `[text]` - 1 boyutlu bir toplu işleme ile çağırıyoruz.

2. **İstek Başına Ek Yük:** Her gömme isteği aşağıdaki ek yükleri içerir:
   Pulsar mesajı serileştirme/deserileştirme
   Ağ gidiş-dönüş gecikmesi
   Model çıkarım başlatma ek yükü
   Python asenkron planlama ek yükü

3. **Şema Sınırlaması:** `EmbeddingsRequest` şeması yalnızca tek bir metni destekler:
   ```python
   @dataclass
   class EmbeddingsRequest:
       text: str = ""  # Single text only
   ```

### Mevcut Çağrılar - Seri İşleme

#### 1. API Ağ Geçidi

**Dosya:** `trustgraph-flow/trustgraph/gateway/dispatch/embeddings.py`

Ağ geçidi, HTTP/WebSocket üzerinden tek metin gömme isteklerini kabul eder ve bunları gömme hizmetine yönlendirir. Şu anda toplu işlem için bir uç nokta bulunmamaktadır.

```python
class EmbeddingsRequestor(ServiceRequestor):
    # Handles single EmbeddingsRequest -> EmbeddingsResponse
    request_schema=EmbeddingsRequest,  # Single text only
    response_schema=EmbeddingsResponse,
```

**Etki:** Harici müşteriler (web uygulamaları, betikler), N metni yerleştirmek için N adet HTTP isteği yapmalıdır.

#### 2. Belge Gömme Hizmeti

**Dosya:** `trustgraph-flow/trustgraph/embeddings/document_embeddings/embeddings.py`

Belgeleri tek tek parçalar halinde işler:

```python
async def on_message(self, msg, consumer, flow):
    v = msg.value()

    # Single chunk per request
    resp = await flow("embeddings-request").request(
        EmbeddingsRequest(text=v.chunk)
    )
    vectors = resp.vectors
```

**Etki:** Her belge parçası için ayrı bir gömme (embedding) çağrısı gereklidir. 100 parçadan oluşan bir belge = 100 gömme isteği.

#### 3. Grafik Gömme Hizmeti

**Dosya:** `trustgraph-flow/trustgraph/embeddings/graph_embeddings/embeddings.py`

Varlıklar üzerinde döngü yapar ve her birini sırayla gömer:

```python
async def on_message(self, msg, consumer, flow):
    for entity in v.entities:
        # Serial embedding - one entity at a time
        vectors = await flow("embeddings-request").embed(
            text=entity.context
        )
        entities.append(EntityEmbeddings(
            entity=entity.entity,
            vectors=vectors,
            chunk_id=entity.chunk_id,
        ))
```

**Etki:** 50 varlık içeren bir mesaj, 50 adet ardışık gömme (embedding) isteği anlamına gelir. Bu, bilgi grafiği oluşturma sırasında büyük bir darboğazdır.

#### 4. Satır Gömme Hizmeti

**Dosya:** `trustgraph-flow/trustgraph/embeddings/row_embeddings/embeddings.py`

Benzersiz metinler üzerinde döngü yapar ve her birini sırayla gömer:

```python
async def on_message(self, msg, consumer, flow):
    for text, (index_name, index_value) in texts_to_embed.items():
        # Serial embedding - one text at a time
        vectors = await flow("embeddings-request").embed(text=text)

        embeddings_list.append(RowIndexEmbedding(
            index_name=index_name,
            index_value=index_value,
            text=text,
            vectors=vectors
        ))
```

**Etki:** 100 benzersiz indeksli değere sahip bir tabloyu işlemek = 100 ardışık gömme isteği.

#### 5. EmbeddingsClient (Temel İstemci)

**Dosya:** `trustgraph-base/trustgraph/base/embeddings_client.py`

Tüm iş akışı işleyicileri tarafından kullanılan istemci, yalnızca tek metin gömmesini destekler:

```python
class EmbeddingsClient(RequestResponse):
    async def embed(self, text, timeout=30):
        resp = await self.request(
            EmbeddingsRequest(text=text),  # Single text
            timeout=timeout
        )
        return resp.vectors
```

**Etki:** Bu istemciyi kullanan tüm uygulamalar, yalnızca tek metin işlemleriyle sınırlıdır.

#### 6. Komut Satırı Araçları

**Dosya:** `trustgraph-cli/trustgraph/cli/invoke_embeddings.py`

CLI aracı, tek bir metin argümanı alır:

```python
def query(url, flow_id, text, token=None):
    result = flow.embeddings(text=text)  # Single text
    vectors = result.get("vectors", [])
```

**Etki:** Kullanıcılar, komut satırından toplu gömme işlemi yapamaz. Bir metin dosyasını işlemek, N sayıda çağrı gerektirir.

#### 7. Python SDK

Python SDK, TrustGraph hizmetleriyle etkileşim kurmak için iki istemci sınıfı sağlar. Her ikisi de yalnızca tek metin gömme işlemini destekler.

**Dosya:** `trustgraph-base/trustgraph/api/flow.py`

```python
class FlowInstance:
    def embeddings(self, text):
        """Get embeddings for a single text"""
        input = {"text": text}
        return self.request("service/embeddings", input)["vectors"]
```

**Dosya:** `trustgraph-base/trustgraph/api/socket_client.py`

```python
class SocketFlowInstance:
    def embeddings(self, text: str, **kwargs: Any) -> Dict[str, Any]:
        """Get embeddings for a single text via WebSocket"""
        request = {"text": text}
        return self.client._send_request_sync(
            "embeddings", self.flow_id, request, False
        )
```

**Etki:** SDK'yı kullanan Python geliştiricilerinin, metinler üzerinde döngü yapması ve N adet API çağrısı yapması gerekir. SDK kullanıcıları için toplu gömme desteği mevcut değildir.

### Performans Etkisi

Tipik belge yükleme için (1000 metin parçası):
**Mevcut:** 1000 ayrı istek, 1000 model çıkarım çağrısı
**Toplu (batch_size=32):** 32 istek, 32 model çıkarım çağrısı (%96,8 azalma)

Grafik gömme için (50 varlığa sahip mesaj):
**Mevcut:** 50 ardışık bekletme çağrısı, ~5-10 saniye
**Toplu:** 1-2 toplu çağrı, ~0,5-1 saniye (5-10 kat iyileşme)

FastEmbed ve benzeri kütüphaneler, toplu boyutun donanım sınırlarına kadar ulaştığı durumlarda, yaklaşık doğrusal bir verim ölçeklemesi sağlar (tipik olarak toplu boyutta 32-128 metin).

## Teknik Tasarım

### Mimari

Gömme toplu işleme optimizasyonu, aşağıdaki bileşenlerde değişiklikler gerektirir:

#### 1. **Şema Geliştirme**
   `EmbeddingsRequest`'ı, birden fazla metni destekleyecek şekilde genişletin
   `EmbeddingsResponse`'ı, birden fazla vektör kümesini döndürecek şekilde genişletin
   Tek metin istekleriyle uyumluluğu koruyun

   Modül: `trustgraph-base/trustgraph/schema/services/llm.py`

#### 2. **Temel Servis Geliştirme**
   `EmbeddingsService`'ı, toplu istekleri işleyebilecek şekilde güncelleyin
   Toplu boyut yapılandırması ekleyin
   Toplu işleme duyarlı istek işleme uygulayın

   Modül: `trustgraph-base/trustgraph/base/embeddings_service.py`

#### 3. **Sağlayıcı İşlemcisi Güncellemeleri**
   FastEmbed işlemcisini güncelleyin, böylece tam toplu iş yükünü `embed()`'a iletebilir
   Ollama işlemcisini güncelleyin, böylece toplu işlemleri işleyebilir (destekleniyorsa)
   Toplu işlemeyi desteklemeyen sağlayıcılar için yedek sıralı işlemeyi ekleyin

   Modüller:
   `trustgraph-flow/trustgraph/embeddings/fastembed/processor.py`
   `trustgraph-flow/trustgraph/embeddings/ollama/processor.py`

#### 4. **İstemci Geliştirme**
   `EmbeddingsClient`'a toplu gömme yöntemini ekleyin
   Hem tek hem de toplu API'leri destekleyin
   Büyük girdiler için otomatik toplu işlemeyi ekleyin

   Modül: `trustgraph-base/trustgraph/base/embeddings_client.py`

#### 5. **Çağrı Güncellemeleri - Akış İşlemcileri**
   `graph_embeddings`'ı, varlık bağlamlarını toplu hale getirecek şekilde güncelleyin
   `row_embeddings`'ı, indeks metinlerini toplu hale getirecek şekilde güncelleyin
   Mesaj toplu işlemesi mümkünse, `document_embeddings`'ı güncelleyin

   Modüller:
   `trustgraph-flow/trustgraph/embeddings/graph_embeddings/embeddings.py`
   `trustgraph-flow/trustgraph/embeddings/row_embeddings/embeddings.py`
   `trustgraph-flow/trustgraph/embeddings/document_embeddings/embeddings.py`

#### 6. **API Ağ Geçidi Geliştirme**
   Toplu gömme uç noktası ekleyin
   İstek gövdesinde metin dizisini destekleyin

   Modül: `trustgraph-flow/trustgraph/gateway/dispatch/embeddings.py`

#### 7. **CLI Aracı Geliştirme**
   Birden fazla metin veya dosya girişi desteği ekleyin
   Toplu boyut parametresi ekleyin

   Modül: `trustgraph-cli/trustgraph/cli/invoke_embeddings.py`

#### 8. **Python SDK Geliştirme**
   `embeddings_batch()` yöntemini `FlowInstance`'e ekleyin
   `embeddings_batch()` yöntemini `SocketFlowInstance`'e ekleyin
   SDK kullanıcıları için hem tek hem de toplu API'leri destekleyin

   Modüller:
   `trustgraph-base/trustgraph/api/flow.py`
   `trustgraph-base/trustgraph/api/socket_client.py`

### Veri Modelleri

#### EmbeddingsRequest

```python
@dataclass
class EmbeddingsRequest:
    texts: list[str] = field(default_factory=list)
```

Kullanım:
Tek metin: `EmbeddingsRequest(texts=["hello world"])`
Toplu işlem: `EmbeddingsRequest(texts=["text1", "text2", "text3"])`

#### EmbeddingsResponse

```python
@dataclass
class EmbeddingsResponse:
    error: Error | None = None
    vectors: list[list[list[float]]] = field(default_factory=list)
```

Yanıt yapısı:
`vectors[i]`, `texts[i]` için vektör kümesini içerir.
Her vektör kümesi `list[list[float]]`'dır (modeller, her metin için birden fazla vektör döndürebilir).
Örnek: 3 metin → `vectors`, 3 giriş içerir ve her giriş, o metnin gömülme değerlerini içerir.

### API'ler

#### EmbeddingsClient

```python
class EmbeddingsClient(RequestResponse):
    async def embed(
        self,
        texts: list[str],
        timeout: float = 300,
    ) -> list[list[list[float]]]:
        """
        Embed one or more texts in a single request.

        Args:
            texts: List of texts to embed
            timeout: Timeout for the operation

        Returns:
            List of vector sets, one per input text
        """
        resp = await self.request(
            EmbeddingsRequest(texts=texts),
            timeout=timeout
        )
        if resp.error:
            raise RuntimeError(resp.error.message)
        return resp.vectors
```

#### API Gateway Gömülü Veri (Embeddings) Uç Noktası

Tek bir veya toplu gömülü veri desteğini sağlayan güncellenmiş uç nokta:

```
POST /api/v1/embeddings
Content-Type: application/json

{
    "texts": ["text1", "text2", "text3"],
    "flow_id": "default"
}

Response:
{
    "vectors": [
        [[0.1, 0.2, ...]],
        [[0.3, 0.4, ...]],
        [[0.5, 0.6, ...]]
    ]
}
```

### Uygulama Detayları

#### Aşama 1: Şema Değişiklikleri

**EmbeddingsRequest:**
```python
@dataclass
class EmbeddingsRequest:
    texts: list[str] = field(default_factory=list)
```

**Gömme Yanıtı:**
```python
@dataclass
class EmbeddingsResponse:
    error: Error | None = None
    vectors: list[list[list[float]]] = field(default_factory=list)
```

**Güncellenmiş EmbeddingsService.on_request:**
```python
async def on_request(self, msg, consumer, flow):
    request = msg.value()
    id = msg.properties()["id"]
    model = flow("model")

    vectors = await self.on_embeddings(request.texts, model=model)
    response = EmbeddingsResponse(error=None, vectors=vectors)

    await flow("response").send(response, properties={"id": id})
```

#### 2. Aşama: FastEmbed İşlemci Güncellemesi

**Mevcut (Verimsiz):**
```python
async def on_embeddings(self, text, model=None):
    use_model = model or self.default_model
    self._load_model(use_model)
    vecs = self.embeddings.embed([text])  # Batch of 1
    return [v.tolist() for v in vecs]
```

**Güncellendi:**
```python
async def on_embeddings(self, texts: list[str], model=None):
    """Embed texts - processes all texts in single model call"""
    if not texts:
        return []

    use_model = model or self.default_model
    self._load_model(use_model)

    # FastEmbed handles the full batch efficiently
    all_vecs = list(self.embeddings.embed(texts))

    # Return list of vector sets, one per input text
    return [[v.tolist()] for v in all_vecs]
```

#### 3. Aşama: Grafik Gömme Hizmeti Güncellemesi

**Mevcut (Sıralı):**
```python
async def on_message(self, msg, consumer, flow):
    entities = []
    for entity in v.entities:
        vectors = await flow("embeddings-request").embed(text=entity.context)
        entities.append(EntityEmbeddings(...))
```

**Güncellendi (Toplu İşlem):**
```python
async def on_message(self, msg, consumer, flow):
    # Collect all contexts
    contexts = [entity.context for entity in v.entities]

    # Single batch embedding call
    all_vectors = await flow("embeddings-request").embed(texts=contexts)

    # Pair results with entities
    entities = [
        EntityEmbeddings(
            entity=entity.entity,
            vectors=vectors[0],  # First vector from the set
            chunk_id=entity.chunk_id,
        )
        for entity, vectors in zip(v.entities, all_vectors)
    ]
```

#### 4. Aşama: Satır Gömme Hizmeti Güncellemesi

**Mevcut (Sıralı):**
```python
for text, (index_name, index_value) in texts_to_embed.items():
    vectors = await flow("embeddings-request").embed(text=text)
    embeddings_list.append(RowIndexEmbedding(...))
```

**Güncellendi (Toplu İşlem):**
```python
# Collect texts and metadata
texts = list(texts_to_embed.keys())
metadata = list(texts_to_embed.values())

# Single batch embedding call
all_vectors = await flow("embeddings-request").embed(texts=texts)

# Pair results
embeddings_list = [
    RowIndexEmbedding(
        index_name=meta[0],
        index_value=meta[1],
        text=text,
        vectors=vectors[0]  # First vector from the set
    )
    for text, meta, vectors in zip(texts, metadata, all_vectors)
]
```

#### 5. Aşama: Komut Satırı Arama Aracı Geliştirme

**Güncellenmiş Komut Satırı:**
```python
def main():
    parser = argparse.ArgumentParser(...)

    parser.add_argument(
        'text',
        nargs='*',  # Zero or more texts
        help='Text(s) to convert to embedding vectors',
    )

    parser.add_argument(
        '-f', '--file',
        help='File containing texts (one per line)',
    )

    parser.add_argument(
        '--batch-size',
        type=int,
        default=32,
        help='Batch size for processing (default: 32)',
    )
```

Kullanım:
```bash
# Single text (existing)
tg-invoke-embeddings "hello world"

# Multiple texts
tg-invoke-embeddings "text one" "text two" "text three"

# From file
tg-invoke-embeddings -f texts.txt --batch-size 64
```

#### 6. Aşama: Python SDK Geliştirme

**FlowInstance (HTTP istemcisi):**

```python
class FlowInstance:
    def embeddings(self, texts: list[str]) -> list[list[list[float]]]:
        """
        Get embeddings for one or more texts.

        Args:
            texts: List of texts to embed

        Returns:
            List of vector sets, one per input text
        """
        input = {"texts": texts}
        return self.request("service/embeddings", input)["vectors"]
```

**SocketFlowInstance (WebSocket istemcisi):**

```python
class SocketFlowInstance:
    def embeddings(self, texts: list[str], **kwargs: Any) -> list[list[list[float]]]:
        """
        Get embeddings for one or more texts via WebSocket.

        Args:
            texts: List of texts to embed

        Returns:
            List of vector sets, one per input text
        """
        request = {"texts": texts}
        response = self.client._send_request_sync(
            "embeddings", self.flow_id, request, False
        )
        return response["vectors"]
```

**SDK Kullanım Örnekleri:**

```python
# Single text
vectors = flow.embeddings(["hello world"])
print(f"Dimensions: {len(vectors[0][0])}")

# Batch embedding
texts = ["text one", "text two", "text three"]
all_vectors = flow.embeddings(texts)

# Process results
for text, vecs in zip(texts, all_vectors):
    print(f"{text}: {len(vecs[0])} dimensions")
```

## Güvenlik Hususları

**İstek Boyutu Sınırları**: Kaynak tükenmesini önlemek için maksimum toplu işlem boyutunu zorlayın.
**Zaman Aşımı İşleme**: Toplu işlem boyutu için zaman aşımını uygun şekilde ayarlayın.
**Bellek Sınırları**: Büyük toplu işlemler için bellek kullanımını izleyin.
**Giriş Doğrulama**: İşleme yapmadan önce toplu işlemdeki tüm metinleri doğrulayın.

## Performans Hususları

### Beklenen İyileştirmeler

**Verim:**
Tek metin: ~10-50 metin/saniye (modele bağlı olarak)
Toplu işlem (boyut 32): ~200-500 metin/saniye (5-10 kat iyileşme)

**Metin Başına Gecikme:**
Tek metin: metin başına 50-200 ms
Toplu işlem (boyut 32): metin başına 5-20 ms (ortalama)

**Hizmete Özel İyileştirmeler:**

| Hizmet | Mevcut | Toplu | İyileşme |
|---------|---------|---------|-------------|
| Grafik Gömme (50 varlık) | 5-10 saniye | 0,5-1 saniye | 5-10 kat |
| Satır Gömme (100 metin) | 10-20 saniye | 1-2 saniye | 5-10 kat |
| Belge Alma (1000 parça) | 100-200 saniye | 10-30 saniye | 5-10 kat |

### Yapılandırma Parametreleri

```python
# Recommended defaults
DEFAULT_BATCH_SIZE = 32
MAX_BATCH_SIZE = 128
BATCH_TIMEOUT_MULTIPLIER = 2.0
```

## Test Stratejisi

### Birim Testleri
Tek metin gömülmesi (geriye dönük uyumluluk)
Boş toplu iş işleme
Maksimum toplu iş boyutu zorlaması
Kısmi toplu iş hataları için hata işleme

### Entegrasyon Testleri
Pulsar üzerinden uçtan uca toplu iş gömülmesi
Grafik gömme hizmeti toplu iş işleme
Satır gömme hizmeti toplu iş işleme
API ağ geçidi toplu iş uç noktası

### Performans Testleri
Tek ve toplu iş verimini karşılaştırma
Farklı toplu iş boyutları altındaki bellek kullanımı
Gecikme dağılımı analizi

## Geçiş Planı

Bu, önemli değişikliklere neden olan bir sürümdür. Tüm fazlar birlikte uygulanır.

### 1. Aşama: Şema Değişiklikleri
EmbeddingsRequest'teki `text: str`'ı `texts: list[str]` ile değiştirin
EmbeddingsResponse'taki `vectors` türünü `list[list[list[float]]]` olarak değiştirin

### 2. Aşama: İşlemci Güncellemeleri
FastEmbed ve Ollama işlemcilerindeki `on_embeddings` imzasını güncelleyin
Tam toplu işi tek bir model çağrısında işleyin

### 3. Aşama: İstemci Güncellemeleri
`EmbeddingsClient.embed()`'ı `texts: list[str]`'i kabul edecek şekilde güncelleyin

### 4. Aşama: Çağıran Güncellemeleri
graph_embeddings'i toplu iş varlık bağlamlarını kullanacak şekilde güncelleyin
row_embeddings'i toplu iş indeks metinlerini kullanacak şekilde güncelleyin
document_embeddings'i yeni şemayı kullanacak şekilde güncelleyin
CLI aracını güncelleyin

### 5. Aşama: API Ağ Geçidi
Yeni şema için gömme uç noktasını güncelleyin

### 6. Aşama: Python SDK
`FlowInstance.embeddings()` imzasını güncelleyin
`SocketFlowInstance.embeddings()` imzasını güncelleyin

## Açık Sorular

**Büyük Toplu İşlerin Akışı**: Çok büyük toplu işler (>100 metin) için sonuçları akış olarak desteklemeli miyiz?
**Sağlayıcıya Özel Sınırlar**: Farklı maksimum toplu iş boyutlarına sahip sağlayıcıları nasıl ele almalıyız?
**Kısmi Hata İşleme**: Bir toplu işteki bir metin başarısız olursa, tüm toplu işi mi başarısız etmeliyiz yoksa kısmi sonuçları mı döndürmeliyiz?
**Belge Gömme Toplu İşleme**: Çoklu Chunk mesajları arasında toplu işlemeyi mi yapmalıyız yoksa her mesaj için ayrı ayrı işlemeyi mi korumalıyız?

## Referanslar

[FastEmbed Belgeleri](https://github.com/qdrant/fastembed)
[Ollama Gömme API'si](https://github.com/ollama/ollama)
[EmbeddingsService Uygulaması](trustgraph-base/trustgraph/base/embeddings_service.py)
[GraphRAG Performans Optimizasyonu](graphrag-performance-optimization.md)
