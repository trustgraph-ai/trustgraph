# Akışlı LLM Yanıtları Teknik Özellikleri

## Genel Bakış

Bu özellik, TrustGraph'ta LLM yanıtları için akış desteğinin uygulanmasını tanımlar. Akış, üretilen token'ların LLM tarafından üretildikleri anda gerçek zamanlı olarak iletilmesini sağlar, böylece tamamlanmış bir yanıtın oluşturulmasını beklemez.

Bu uygulama aşağıdaki kullanım senaryolarını destekler:


1. **Gerçek Zamanlı Kullanıcı Arayüzleri**: Token'ları, oluşturuldukları anda kullanıcı arayüzüne aktarın ve böylece anında görsel geri bildirim sağlayın.

2. **İlk Token'a Ulaşma Süresinin Azaltılması**: Kullanıcılar, tam oluşturma beklemeden çıktıyı hemen görmeye başlar.
   
3. **Uzun Yanıtların İşlenmesi**: Aksi takdirde zaman aşımına uğrayabilecek veya bellek sınırlarını aşabilecek çok uzun çıktıları işleyin.
   
4. **Etkileşimli Uygulamalar**: Duyarlı sohbet ve ajan arayüzlerini etkinleştirin.
   
## Hedefler


**Geriye Dönük Uyumluluk**: Mevcut, akış kullanmayan istemciler, herhangi bir değişiklik yapılmadan çalışmaya devam etmelidir.

  **Tutarlı API Tasarımı**: Akışlı ve akışsız kullanım, minimum farklılıklarla aynı şema kalıplarını kullanır.

  **Sağlayıcı Esnekliği**: Akış mevcut olduğunda akışı destekleyin, aksi takdirde zarif bir şekilde geri dönün.

  **Aşamalı Dağıtım**: Riski azaltmak için kademeli uygulama.

**Uçtan Uca Destek**: LLM sağlayıcısından Pulsar, Gateway API ve Python API aracılığıyla istemci uygulamalarına kadar akış desteği.
  
## Arka Plan

### Mevcut Mimari


Mevcut LLM metin tamamlama akışı aşağıdaki gibi çalışır:

1. İstemci, `TextCompletionRequest` ile `system` ve `prompt` alanlarını gönderir.
2. LLM hizmeti, isteği işler ve tamamlanmış bir oluşturmayı bekler.
3. Tamamlanmış `response` dizesiyle tek bir `TextCompletionResponse` döndürülür.

Mevcut şema (`trustgraph-base/trustgraph/schema/services/llm.py`):

```python
class TextCompletionRequest(Record):
    system = String()
    prompt = String()

class TextCompletionResponse(Record):
    error = Error()
    response = String()
    in_token = Integer()
    out_token = Integer()
    model = String()
```

### Mevcut Sınırlamalar

**Gecikme**: Kullanıcılar, herhangi bir çıktı görmeden önce, tamamlanmış bir üretimi beklemelidir.
**Zaman Aşımı Riski**: Uzun üretmeler, istemci zaman aşımı eşiklerini aşabilir.
**Kötü Kullanıcı Deneyimi**: Üretim sırasında geri bildirim olmaması, yavaşlık algısı yaratır.
**Kaynak Kullanımı**: Tam yanıtlar bellekte tamponlanmalıdır.

Bu özellik, art arda yanıt verme özelliğini etkinleştirerek bu sınırlamalara çözüm getirir ve aynı zamanda tam geriye dönük uyumluluğu korur.


## Teknik Tasarım

### Aşama 1: Altyapı

Aşama 1, şemaları, API'leri ve komut satırı araçlarını değiştirerek akış için temel altyapıyı oluşturur.


#### Şema Değişiklikleri

##### LLM Şeması (`trustgraph-base/trustgraph/schema/services/llm.py`)

**İstek Değişiklikleri:**

```python
class TextCompletionRequest(Record):
    system = String()
    prompt = String()
    streaming = Boolean()  # NEW: Default false for backward compatibility
```

`streaming`: `true` olduğunda, akışlı yanıt gönderimi talep eder.
Varsayılan: `false` (mevcut davranış korunmuştur).

**Yanıt Değişiklikleri:**

```python
class TextCompletionResponse(Record):
    error = Error()
    response = String()
    in_token = Integer()
    out_token = Integer()
    model = String()
    end_of_stream = Boolean()  # NEW: Indicates final message
```

`end_of_stream`: `true` olduğunda, bunun son (veya tek) yanıt olduğunu gösterir.
Akış olmayan istekler için: `end_of_stream=true` ile tek bir yanıt.
Akış istekleri için: `end_of_stream=false` ile birden fazla yanıt (son yanıt hariç).
  hariç.

##### İstek Şeması (`trustgraph-base/trustgraph/schema/services/prompt.py`)

İstek hizmeti, metin tamamlama işlemini kapsar, bu nedenle aynı kalıbı yansıtır:

**İstek Değişiklikleri:**

```python
class PromptRequest(Record):
    id = String()
    terms = Map(String())
    streaming = Boolean()  # NEW: Default false
```

**Değişiklikler:**

```python
class PromptResponse(Record):
    error = Error()
    text = String()
    object = String()
    end_of_stream = Boolean()  # NEW: Indicates final message
```

#### Ağ Geçidi API Değişiklikleri

Ağ Geçidi API'sinin, HTTP/WebSocket istemcilerine akış yeteneklerini sunması gerekir.

**REST API Güncellemeleri:**

`POST /api/v1/text-completion`: İstek gövdesinde `streaming` parametresini kabul et
Yanıt davranışı, akış bayrağına bağlıdır:
  `streaming=false`: Tek JSON yanıtı (mevcut davranış)
  `streaming=true`: Sunucu Tarafından Gönderilen Olaylar (SSE) akışı veya WebSocket mesajları

**Yanıt Formatı (Akış):**

Her akış parçası, aynı şema yapısını izler:
```json
{
  "response": "partial text...",
  "end_of_stream": false,
  "model": "model-name"
}
```

Son bölüm:
```json
{
  "response": "final text chunk",
  "end_of_stream": true,
  "in_token": 150,
  "out_token": 500,
  "model": "model-name"
}
```

#### Python API Değişiklikleri

Python istemci API'si, geriye dönük uyumluluğu korurken hem akışlı hem de akışsız modları desteklemelidir.


**LlmClient Güncellemeleri** (`trustgraph-base/trustgraph/clients/llm_client.py`):

```python
class LlmClient(BaseClient):
    def request(self, system, prompt, timeout=300, streaming=False):
        """
        Non-streaming request (backward compatible).
        Returns complete response string.
        """
        # Existing behavior when streaming=False

    async def request_stream(self, system, prompt, timeout=300):
        """
        Streaming request.
        Yields response chunks as they arrive.
        """
        # New async generator method
```

**PromptClient Güncellemeleri** (`trustgraph-base/trustgraph/base/prompt_client.py`):

`streaming` parametresi ve asenkron üreteç varyantıyla benzer yapı.

#### CLI Aracı Değişiklikleri

**tg-invoke-llm** (`trustgraph-cli/trustgraph/cli/invoke_llm.py`):

```
tg-invoke-llm [system] [prompt] [--no-streaming] [-u URL] [-f flow-id]
```

Daha iyi etkileşimli kullanıcı deneyimi için, akış varsayılan olarak etkindir.
`--no-streaming` bayrağı, akışı devre dışı bırakır.
Akış açıkken: Token'ları geldikleri gibi standart çıktıya yazdırın.
Akış kapalıyken: Tam yanıtı bekleyin, ardından çıktı verin.

**tg-invoke-prompt** (`trustgraph-cli/trustgraph/cli/invoke_prompt.py`):

```
tg-invoke-prompt [template-id] [var=value...] [--no-streaming] [-u URL] [-f flow-id]
```

`tg-invoke-llm` ile aynı kalıp.

#### LLM Hizmeti Temel Sınıfındaki Değişiklikler

**LlmService** (`trustgraph-base/trustgraph/base/llm_service.py`):

```python
class LlmService(FlowProcessor):
    async def on_request(self, msg, consumer, flow):
        request = msg.value()
        streaming = getattr(request, 'streaming', False)

        if streaming and self.supports_streaming():
            async for chunk in self.generate_content_stream(...):
                await self.send_response(chunk, end_of_stream=False)
            await self.send_response(final_chunk, end_of_stream=True)
        else:
            response = await self.generate_content(...)
            await self.send_response(response, end_of_stream=True)

    def supports_streaming(self):
        """Override in subclass to indicate streaming support."""
        return False

    async def generate_content_stream(self, system, prompt, model, temperature):
        """Override in subclass to implement streaming."""
        raise NotImplementedError()
```

--

### 2. Aşama: VertexAI Prova Çalışması

2. Aşama, altyapıyı doğrulamak ve uçtan uca testleri sağlamak için tek bir sağlayıcıda (VertexAI) akışı uygulamaktadır.


#### VertexAI Uygulaması

**Modül:** `trustgraph-vertexai/trustgraph/model/text_completion/vertexai/llm.py`

**Değişiklikler:**

1. `supports_streaming()`'ı `True` değerini döndürecek şekilde geçersiz kılın.
2. `generate_content_stream()` asenkron oluşturucusunu uygulayın.
3. Hem Gemini hem de Claude modellerini (VertexAI Anthropic API aracılığıyla) işleyin.

**Gemini Akışı:**

```python
async def generate_content_stream(self, system, prompt, model, temperature):
    model_instance = self.get_model(model, temperature)
    response = model_instance.generate_content(
        [system, prompt],
        stream=True  # Enable streaming
    )
    for chunk in response:
        yield LlmChunk(
            text=chunk.text,
            in_token=None,  # Available only in final chunk
            out_token=None,
        )
    # Final chunk includes token counts from response.usage_metadata
```

**Claude (VertexAI Anthropic) Akışı:**

```python
async def generate_content_stream(self, system, prompt, model, temperature):
    with self.anthropic_client.messages.stream(...) as stream:
        for text in stream.text_stream:
            yield LlmChunk(text=text)
    # Token counts from stream.get_final_message()
```

#### Test Etme

Akış yanıtı birleştirme için birim testleri
VertexAI (Gemini ve Claude) ile entegrasyon testleri
Uçtan uca testler: CLI -> Ağ Geçidi -> Pulsar -> VertexAI -> geri
Geriye dönük uyumluluk testleri: Akış olmayan istekler hala çalışıyor

--

### 3. Aşama: Tüm LLM Sağlayıcıları

3. Aşama, akış desteğini sistemdeki tüm LLM sağlayıcılarına genişletir.

#### Sağlayıcı Uygulama Durumu

Her sağlayıcı aşağıdaki seçeneklerden birini uygulamalıdır:
1. **Tam Akış Desteği**: `generate_content_stream()`'ı uygulayın
2. **Uyumluluk Modu**: `end_of_stream` bayrağını doğru şekilde işleyin
   (tek bir yanıt döndürün `end_of_stream=true` ile birlikte)

| Sağlayıcı | Paket | Akış Desteği |
|----------|---------|-------------------|
| OpenAI | trustgraph-flow | Tam (yerel akış API'si) |
| Claude/Anthropic | trustgraph-flow | Tam (yerel akış API'si) |
| Ollama | trustgraph-flow | Tam (yerel akış API'si) |
| Cohere | trustgraph-flow | Tam (yerel akış API'si) |
| Mistral | trustgraph-flow | Tam (yerel akış API'si) |
| Azure OpenAI | trustgraph-flow | Tam (yerel akış API'si) |
| Google AI Studio | trustgraph-flow | Tam (yerel akış API'si) |
| VertexAI | trustgraph-vertexai | Tam (2. Aşama) |
| Bedrock | trustgraph-bedrock | Tam (yerel akış API'si) |
| LM Studio | trustgraph-flow | Tam (OpenAI ile uyumlu) |
| LlamaFile | trustgraph-flow | Tam (OpenAI ile uyumlu) |
| vLLM | trustgraph-flow | Tam (OpenAI ile uyumlu) |
| TGI | trustgraph-flow | Belirlenecek |
| Azure | trustgraph-flow | Belirlenecek |

#### Uygulama Modeli

OpenAI ile uyumlu sağlayıcılar (OpenAI, LM Studio, LlamaFile, vLLM) için:

```python
async def generate_content_stream(self, system, prompt, model, temperature):
    response = await self.client.chat.completions.create(
        model=model,
        messages=[
            {"role": "system", "content": system},
            {"role": "user", "content": prompt}
        ],
        temperature=temperature,
        stream=True
    )
    async for chunk in response:
        if chunk.choices[0].delta.content:
            yield LlmChunk(text=chunk.choices[0].delta.content)
```

--

### 4. Aşama: Ajan API'si

4. Aşama, akışı Ajan API'sine genişletmektedir. Bu, Ajan API'sinin doğası gereği zaten çok mesajlı olması nedeniyle daha karmaşıktır (düşünce → eylem → gözlem
→ tekrar → son yanıt).


#### Mevcut Ajan Şeması

```python
class AgentStep(Record):
    thought = String()
    action = String()
    arguments = Map(String())
    observation = String()
    user = String()

class AgentRequest(Record):
    question = String()
    state = String()
    group = Array(String())
    history = Array(AgentStep())
    user = String()

class AgentResponse(Record):
    answer = String()
    error = Error()
    thought = String()
    observation = String()
```

#### Önerilen Ajan Şema Değişiklikleri

**Değişiklik İstekleri:**

```python
class AgentRequest(Record):
    question = String()
    state = String()
    group = Array(String())
    history = Array(AgentStep())
    user = String()
    streaming = Boolean()  # NEW: Default false
```

**Cevap Değişiklikleri:**

Ajan, akıl yürütme döngüsü sırasında çeşitli türde çıktılar üretir:
Düşünceler (akıl yürütme)
Eylemler (araç çağrıları)
Gözlemler (araç sonuçları)
Cevap (sonuç yanıtı)
Hatalar

`chunk_type`, gönderilen içeriğin türünü tanımladığı için, ayrı
`answer`, `error`, `thought` ve `observation` alanları tek bir alana dönüştürülebilir.
Tek bir `content` alanı:

```python
class AgentResponse(Record):
    chunk_type = String()       # "thought", "action", "observation", "answer", "error"
    content = String()          # The actual content (interpretation depends on chunk_type)
    end_of_message = Boolean()  # Current thought/action/observation/answer is complete
    end_of_dialog = Boolean()   # Entire agent dialog is complete
```

**Alan Anlamı:**

`chunk_type`: `content` alanında bulunan içeriğin türünü belirtir.
  `"thought"`: Aracın muhakemesi/düşüncesi.
  `"action"`: Çağrılan araç/eylem.
  `"observation"`: Araç çalıştırmasından elde edilen sonuç.
  `"answer"`: Kullanıcının sorusuna verilen nihai cevap.
  `"error"`: Hata mesajı.

`content`: `chunk_type`'e göre yorumlanan, gerçek akış içeriği.

`end_of_message`: `true` olduğunda, mevcut parça türü tamamlanmıştır.
  Örnek: Mevcut düşünce için tüm belirteçler gönderilmiştir.
  İstemcilerin bir sonraki aşamaya ne zaman geçmeleri gerektiğini bilmesini sağlar.

`end_of_dialog`: `true` olduğunda, tüm aracı etkileşimi tamamlanmıştır.
  Bu, akıştaki son mesajdır.

#### Aracı Akış Davranışı

`streaming=true` olduğunda:

1. **Düşünce akışı:**
   `chunk_type="thought"` ve `end_of_message=false` ile birden fazla parça.
   Son düşünce parçası `end_of_message=true`'a sahiptir.
2. **Eylem bildirimi:**
   `chunk_type="action"` ve `end_of_message=true` ile tek bir parça.
3. **Gözlem:**
   `chunk_type="observation"` ile parçalar, son parça `end_of_message=true`'e sahiptir.
4. Aracı muhakeme ederken 1-3 adımlarını tekrarlayın.
5. **Son cevap:**
   `content` içindeki son yanıtla `chunk_type="answer"`.
   Son parça `end_of_message=true` ve `end_of_dialog=true`'e sahiptir.

**Örnek Akış Sırası:**

```
{chunk_type: "thought", content: "I need to", end_of_message: false, end_of_dialog: false}
{chunk_type: "thought", content: " search for...", end_of_message: true, end_of_dialog: false}
{chunk_type: "action", content: "search", end_of_message: true, end_of_dialog: false}
{chunk_type: "observation", content: "Found: ...", end_of_message: true, end_of_dialog: false}
{chunk_type: "thought", content: "Based on this", end_of_message: false, end_of_dialog: false}
{chunk_type: "thought", content: " I can answer...", end_of_message: true, end_of_dialog: false}
{chunk_type: "answer", content: "The answer is...", end_of_message: true, end_of_dialog: true}
```

`streaming=false` olduğunda:
Mevcut davranış korunmuştur
Tam bir cevap içeren tek bir yanıt
`end_of_message=true`, `end_of_dialog=true`

#### Ağ Geçidi ve Python API'si

Ağ Geçidi: Ajan akışı için yeni SSE/WebSocket uç noktası
Python API'si: Yeni `agent_stream()` asenkron oluşturucu metodu

--

## Güvenlik Hususları

**Yeni bir saldırı yüzeyi yok**: Akış, aynı kimlik doğrulama/yetkilendirme mekanizmalarını kullanır
**Hız sınırlaması**: Gerekirse, her jeton veya her parça için hız sınırları uygulayın
**Bağlantı yönetimi**: İstemci bağlantısının kesilmesi durumunda akışları düzgün bir şekilde sonlandırın
**Zaman aşımı yönetimi**: Akış istekleri için uygun zaman aşımı işleme gereklidir

## Performans Hususları

**Bellek**: Akış, tepe bellek kullanımını azaltır (tam yanıt tamponlama yok)
**Gecikme**: İlk jetona ulaşma süresi önemli ölçüde azaltılmıştır
**Bağlantı ek yükü**: SSE/WebSocket bağlantılarının devamlılık ek yükü vardır
**Pulsar verim**: Tek büyük mesaj yerine çok sayıda küçük mesaj
  dengesi

## Test Stratejisi

### Birim Testleri
Yeni alanlarla şema serileştirme/deserileştirme
Geriye dönük uyumluluk (eksik alanlar için varsayılan değerler kullanılır)
Parça birleştirme mantığı

### Entegrasyon Testleri
Her LLM sağlayıcısının akış uygulaması
Ağ Geçidi API akış uç noktaları
Python istemci akış metotları

### Uçtan Uca Testler
CLI aracının akış çıktısı
Tam akış: İstemci → Ağ Geçidi → Pulsar → LLM → geri
Karışık akış/akış dışı iş yükleri

### Geriye Dönük Uyumluluk Testleri
Mevcut istemciler değişiklik yapılmadan çalışır
Akış dışı istekler aynı şekilde davranır

## Geçiş Planı

### 1. Aşama: Altyapı
Şema değişikliklerini dağıtın (geriye dönük uyumlu)
Ağ Geçidi API güncellemelerini dağıtın
Python API güncellemelerini dağıtın
CLI aracı güncellemelerini yayınlayın

### 2. Aşama: VertexAI
VertexAI akış uygulamasını dağıtın
Test iş yükleriyle doğrulayın

### 3. Aşama: Tüm Sağlayıcılar
Sağlayıcı güncellemelerini aşamalı olarak yayınlayın
Sorunlar için izleyin

### 4. Aşama: Ajan API'si
Ajan şema değişikliklerini dağıtın
Ajan akış uygulamasını dağıtın
Belgeleri güncelleyin

## Zaman Çizelgesi

| Aşama | Açıklama | Bağımlılıklar |
|-------|-------------|--------------|
| 1. Aşama | Altyapı | Yok |
| 2. Aşama | VertexAI PoC | 1. Aşama |
| 3. Aşama | Tüm Sağlayıcılar | 2. Aşama |
| 4. Aşama | Ajan API'si | 3. Aşama |

## Tasarım Kararları

Aşağıdaki sorular, belirtim sırasında çözülmüştür:

1. **Akıştaki Jeton Sayıları**: Jeton sayıları, toplamlar değil, artışlardır.
   Tüketiciler, gerekirse bunları toplayabilir. Bu, çoğu sağlayıcının kullanım
   raporlama şekliyle eşleşir ve uygulamayı basitleştirir.

2. **Akışlardaki Hata İşleme**: Bir hata oluşursa, `error` alanı
   doldurulur ve diğer alanlara ihtiyaç duyulmaz. Bir hata her zaman son
   iletişimdir; hata sonrasında başka mesajlara izin verilmez veya beklenmez.
   LLM/İstem akışları için `end_of_stream=true`. Ajan akışları için,
   `chunk_type="error"` ile `end_of_dialog=true`.

3. **Kısmi Yanıt Kurtarma**: Mesajlaşma protokolü (Pulsar) dayanıklıdır,
   bu nedenle mesaj düzeyinde yeniden deneme gerekli değildir. Bir istem, akışı
   takip edemezse veya bağlantısı kesilirse, isteği baştan yeniden denemesi gerekir.

4. **İstem Hizmeti Akışı**: Akış yalnızca metin (`text`) yanıtları için
   desteklenir, yapılandırılmış (`object`) yanıtlar için değil. İstem hizmeti,
   çıktının JSON mu yoksa metin tabanlı mı olacağını, istem şablonuna göre
   önceden bilir. Bir akış isteği, JSON çıktılı bir istem için yapılırsa,
   hizmet şunlardan birini yapmalıdır:
   Tam JSON'ı tek bir yanıtla `end_of_stream=true` ile döndürün veya
   Akış isteğini bir hata ile reddedin

## Açık Sorular

Şu anda yok.

## Referanslar

Mevcut LLM şeması: `trustgraph-base/trustgraph/schema/services/llm.py`
Mevcut istem şeması: `trustgraph-base/trustgraph/schema/services/prompt.py`
Mevcut ajan şeması: `trustgraph-base/trustgraph/schema/services/agent.py`
LLM hizmeti tabanı: `trustgraph-base/trustgraph/base/llm_service.py`
VertexAI sağlayıcısı: `trustgraph-vertexai/trustgraph/model/text_completion/vertexai/llm.py`
Ağ Geçidi API'si: `trustgraph-base/trustgraph/api/`
CLI araçları: `trustgraph-cli/trustgraph/cli/`
