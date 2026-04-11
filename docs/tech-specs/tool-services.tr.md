# Araç Hizmetleri: Dinamik Olarak Eklenebilen Ajan Araçları

## Durum

Uygulandı

## Genel Bakış

Bu özellik, "araç hizmetleri" olarak adlandırılan, dinamik olarak eklenebilen ajan araçları için bir mekanizma tanımlar. Mevcut, yerleşik araç türlerinin (`KnowledgeQueryImpl`, `McpToolImpl`, vb.) aksine, araç hizmetleri, aşağıdaki yöntemlerle yeni araçların eklenmesine olanak tanır:

1. Yeni bir Pulsar tabanlı hizmetin dağıtılması
2. Ajanın hizmeti nasıl çağıracağını belirten bir yapılandırma açıklamasının eklenmesi

Bu, çekirdek ajan-yanıt çerçevesini değiştirmeden genişletilebilirlik sağlar.

## Terminoloji

| Terim | Tanım |
|------|------------|
| **Yerleşik Araç** | `tools.py` içinde sabit kodlanmış uygulamalara sahip mevcut araç türleri |
| **Araç Hizmeti** | Bir hizmet açıklamasıyla tanımlanan ve bir ajan aracı olarak çağrılabilecek bir Pulsar hizmeti |
| **Araç** | Bir hizmet aracını referans alan ve ajana/LLM'ye sunulan yapılandırılmış bir örnek |

Bu, MCP araçlarına benzer iki katmanlı bir modeldir:
MCP: MCP sunucusu araç arayüzünü tanımlar → Araç yapılandırması buna başvurur
Araç Hizmetleri: Araç hizmeti Pulsar arayüzünü tanımlar → Araç yapılandırması buna başvurur

## Arka Plan: Mevcut Araçlar

### Yerleşik Araç Uygulaması

Araçlar şu anda `trustgraph-flow/trustgraph/agent/react/tools.py` içinde, türlenmiş uygulamalarla tanımlanmıştır:

```python
class KnowledgeQueryImpl:
    async def invoke(self, question):
        client = self.context("graph-rag-request")
        return await client.rag(question, self.collection)
```

Her araç türü:
Çağırdığı sabit kodlu bir Pulsar servisine sahiptir (örneğin, `graph-rag-request`)
İstemci üzerinde çağrılacak kesin yöntemi bilir (örneğin, `client.rag()`)
Uygulamada tanımlanmış türlü argümanlara sahiptir

### Araç Kaydı (service.py:105-214)

Araçlar, bir uygulamaya eşleyen `type` alanıyla yapılandırmadan yüklenir:

```python
if impl_id == "knowledge-query":
    impl = functools.partial(KnowledgeQueryImpl, collection=data.get("collection"))
elif impl_id == "text-completion":
    impl = TextCompletionImpl
# ... etc
```

## Mimari

### İki Katmanlı Model

#### 1. Katman: Araç Hizmeti Tanımlayıcısı

Bir araç hizmeti, bir Pulsar hizmeti arayüzünü tanımlar. Aşağıdakileri belirtir:
İstek/yanıt için kullanılan Pulsar kuyrukları
Onu kullanan araçlardan gerektirdiği yapılandırma parametreleri

```json
{
  "id": "custom-rag",
  "request-queue": "non-persistent://tg/request/custom-rag",
  "response-queue": "non-persistent://tg/response/custom-rag",
  "config-params": [
    {"name": "collection", "required": true}
  ]
}
```

Herhangi bir yapılandırma parametresine ihtiyaç duymayan bir araç hizmeti:

```json
{
  "id": "calculator",
  "request-queue": "non-persistent://tg/request/calc",
  "response-queue": "non-persistent://tg/response/calc",
  "config-params": []
}
```

#### 2. Seviye: Araç Açıklaması

Bir araç, bir araç hizmetine başvurur ve şunları sağlar:
Yapılandırma parametre değerleri (hizmetin gereksinimlerini karşılar)
Aracının ajana yönelik meta verileri (ad, açıklama)
LLM için argüman tanımları

```json
{
  "type": "tool-service",
  "name": "query-customers",
  "description": "Query the customer knowledge base",
  "service": "custom-rag",
  "collection": "customers",
  "arguments": [
    {
      "name": "question",
      "type": "string",
      "description": "The question to ask about customers"
    }
  ]
}
```

Birden fazla aracın, farklı yapılandırmalarla aynı hizmete başvurabileceğini unutmayın:

```json
{
  "type": "tool-service",
  "name": "query-products",
  "description": "Query the product knowledge base",
  "service": "custom-rag",
  "collection": "products",
  "arguments": [
    {
      "name": "question",
      "type": "string",
      "description": "The question to ask about products"
    }
  ]
}
```

### İstek Formatı

Bir araç çağrıldığında, araca yapılan istek, aşağıdaki bilgileri içerir:
`user`: Aracının isteğinden (çoklu kiracılık)
`config`: Araç açıklamasından alınan, JSON formatında kodlanmış yapılandırma değerleri
`arguments`: LLM'den alınan, JSON formatında kodlanmış argümanlar

```json
{
  "user": "alice",
  "config": "{\"collection\": \"customers\"}",
  "arguments": "{\"question\": \"What are the top customer complaints?\"}"
}
```

Araç hizmeti, bunları `invoke` yönteminde ayrıştırılmış sözlükler olarak alır.

### Genel Araç Hizmeti Uygulaması

Bir `ToolServiceImpl` sınıfı, yapılandırmaya göre araç hizmetlerini çağırır:

```python
class ToolServiceImpl:
    def __init__(self, context, request_queue, response_queue, config_values, arguments, processor):
        self.request_queue = request_queue
        self.response_queue = response_queue
        self.config_values = config_values  # e.g., {"collection": "customers"}
        # ...

    async def invoke(self, **arguments):
        client = await self._get_or_create_client()
        response = await client.call(user, self.config_values, arguments)
        if isinstance(response, str):
            return response
        else:
            return json.dumps(response)
```

## Tasarım Kararları

### İki Katmanlı Konfigürasyon Modeli

Araç hizmetleri, MCP araçlarına benzer bir iki katmanlı model izler:

1. **Araç Hizmeti**: Pulsar hizmet arayüzünü (konu, gerekli yapılandırma parametreleri) tanımlar.
2. **Araç**: Bir araç hizmetine başvurur, yapılandırma değerlerini sağlar, LLM argümanlarını tanımlar.

Bu ayrım şunları sağlar:
Farklı yapılandırmalara sahip birden fazla aracın aynı araç hizmetini kullanabilmesi
Hizmet arayüzü ve araç yapılandırması arasındaki net ayrım
Hizmet tanımlarının yeniden kullanılabilirliği

### İstek Eşleme: Zarf ile Doğrudan İletim

Bir araç hizmetine yapılan istek, şunları içeren yapılandırılmış bir zarf içerir:
`user`: Çoklu kiracılık için aracıdan gelen istekten aktarılır.
Yapılandırma değerleri: Araç açıklamasından (örneğin, `collection`).
`arguments`: LLM tarafından sağlanan argümanlar, bir sözlük olarak iletilir.

Aracı yöneticisi, LLM'nin yanıtını `act.arguments` olarak bir sözlükte (`agent_manager.py:117-154`) ayrıştırır. Bu sözlük, istek zarfında bulunur.

### Şema İşleme: Türsüz

İstekler ve yanıtlar, tür tanımlaması olmayan sözlükler kullanır. Aracılar seviyesinde herhangi bir şema doğrulaması yapılmaz; araç hizmeti, girişlerini doğrulamaktan sorumludur. Bu, yeni hizmetler tanımlamak için maksimum esneklik sağlar.

### İstemci Arayüzü: Doğrudan Pulsar Konuları

Araç hizmetleri, akış yapılandırması gerektirmeden doğrudan Pulsar konularını kullanır. Araç hizmeti tanımında, tam kuyruk adları belirtilir:

```json
{
  "id": "joke-service",
  "request-queue": "non-persistent://tg/request/joke",
  "response-queue": "non-persistent://tg/response/joke",
  "config-params": [...]
}
```

Bu, hizmetlerin herhangi bir ad alanında barındırılmasını sağlar.

### Hata Yönetimi: Standart Hata Kuralı

Ara hizmet yanıtları, `error` alanı ile mevcut şema kuralını takip eder:

```python
@dataclass
class Error:
    type: str = ""
    message: str = ""
```

Yanıt yapısı:
Başarı: `error`, `None` ise, yanıt sonuç içerir.
Hata: `error`, `type` ve `message` ile doldurulur.

Bu, mevcut hizmet şemalarında kullanılan kalıpla eşleşir (örneğin, `PromptResponse`, `QueryResponse`, `AgentResponse`).

### İstek/Yanıt İlişkilendirmesi

İstekler ve yanıtlar, Pulsar mesaj özelliklerindeki bir `id` kullanılarak ilişkilendirilir:

İstek, özelliklerde `id` içerir: `properties={"id": id}`
Yanıt(lar), aynı `id`'ı içerir: `properties={"id": id}`

Bu, kod tabanında kullanılan mevcut kalıpla uyumludur (örneğin, `agent_service.py`, `llm_service.py`).

### Akış Desteği

Araç hizmetleri, akış yanıtları döndürebilir:

Aynı `id`'a sahip çoklu yanıt mesajı
Her yanıt, `end_of_stream: bool` alanını içerir
Son yanıt, `end_of_stream: True`'a sahiptir

Bu, `AgentResponse` ve diğer akış hizmetlerinde kullanılan kalıpla eşleşir.

### Yanıt İşleme: String Dönüşü

Tüm mevcut araçlar aynı kalıbı izler: **argümanları bir sözlük olarak alın, gözlemi bir dize olarak döndürün**.

| Araç | Yanıt İşleme |
|------|------------------|
| `KnowledgeQueryImpl` | `client.rag()`'i doğrudan döndürür (dize) |
| `TextCompletionImpl` | `client.question()`'i doğrudan döndürür (dize) |
| `McpToolImpl` | Bir dize döndürür veya dize değilse `json.dumps(output)` döndürür |
| `StructuredQueryImpl` | Sonucu bir dizeye dönüştürür |
| `PromptImpl` | `client.prompt()`'i doğrudan döndürür (dize) |

Araç hizmetleri aynı sözleşmeyi izler:
Hizmet, bir dize yanıtı (gözlem) döndürür
Yanıt bir dize değilse, `json.dumps()` aracılığıyla dönüştürülür
Tanımlayıcıda herhangi bir çıkarma yapılandırması gerekmez

Bu, tanımlayıcıyı basit tutar ve aracın uygun bir metin yanıtı döndürme sorumluluğunu hizmete bırakır.

## Yapılandırma Kılavuzu

Yeni bir araç hizmeti eklemek için, iki yapılandırma öğesi gereklidir:

### 1. Araç Hizmeti Yapılandırması

`tool-service` yapılandırma anahtarı altında saklanır. Pulsar kuyruklarını ve mevcut yapılandırma parametrelerini tanımlar.

| Alan | Gerekli | Açıklama |
|-------|----------|-------------|
| `id` | Evet | Araç hizmeti için benzersiz tanımlayıcı |
| `request-queue` | Evet | İstekler için tam Pulsar konusu (örneğin, `non-persistent://tg/request/joke`) |
| `response-queue` | Evet | Yanıtlar için tam Pulsar konusu (örneğin, `non-persistent://tg/response/joke`) |
| `config-params` | Hayır | Hizmetin kabul ettiği yapılandırma parametrelerinin dizisi |

Her yapılandırma parametresi şunları belirtebilir:
`name`: Parametre adı (gerekli)
`required`: Parametrenin araçlar tarafından sağlanması gerekip gerekmediği (varsayılan: false)

Örnek:
```json
{
  "id": "joke-service",
  "request-queue": "non-persistent://tg/request/joke",
  "response-queue": "non-persistent://tg/response/joke",
  "config-params": [
    {"name": "style", "required": false}
  ]
}
```

### 2. Araç Yapılandırması

`tool` anahtarının altında saklanır. Aracının kullanabileceği bir aracı tanımlar.

| Alan | Gerekli | Açıklama |
|-------|----------|-------------|
| `type` | Evet | `"tool-service"` olmalıdır |
| `name` | Evet | LLM'ye sunulan araç adı |
| `description` | Evet | Aracın ne yaptığına dair açıklama (LLM'ye gösterilir) |
| `service` | Evet | Çağrılacak araç hizmetinin kimliği |
| `arguments` | Hayır | LLM için argüman tanımları dizisi |
| *(yapılandırma parametreleri)* | Değişken | Hizmet tarafından tanımlanan herhangi bir yapılandırma parametresi |

Her argüman aşağıdaki gibi bir şeye sahip olabilir:
`name`: Argüman adı (gerekli)
`type`: Veri türü, örneğin `"string"` (gerekli)
`description`: LLM'ye gösterilen açıklama (gerekli)

Örnek:
```json
{
  "type": "tool-service",
  "name": "tell-joke",
  "description": "Tell a joke on a given topic",
  "service": "joke-service",
  "style": "pun",
  "arguments": [
    {
      "name": "topic",
      "type": "string",
      "description": "The topic for the joke (e.g., programming, animals, food)"
    }
  ]
}
```

### Yapılandırmayı Yükleme

Yapılandırmaları yüklemek için `tg-put-config-item`'ı kullanın:

```bash
# Load tool-service config
tg-put-config-item tool-service/joke-service < joke-service.json

# Load tool config
tg-put-config-item tool/tell-joke < tell-joke.json
```

Aracının ve yöneticinin, yeni yapılandırmaları alabilmesi için yeniden başlatılması gerekir.

## Uygulama Detayları

### Şema

`trustgraph-base/trustgraph/schema/services/tool_service.py` içindeki istek ve yanıt türleri:

```python
@dataclass
class ToolServiceRequest:
    user: str = ""           # User context for multi-tenancy
    config: str = ""         # JSON-encoded config values from tool descriptor
    arguments: str = ""      # JSON-encoded arguments from LLM

@dataclass
class ToolServiceResponse:
    error: Error | None = None
    response: str = ""       # String response (the observation)
    end_of_stream: bool = False
```

### Sunucu Tarafı: DynamicToolService

`trustgraph-base/trustgraph/base/dynamic_tool_service.py` içindeki temel sınıf:

```python
class DynamicToolService(AsyncProcessor):
    """Base class for implementing tool services."""

    def __init__(self, **params):
        topic = params.get("topic", default_topic)
        # Constructs topics: non-persistent://tg/request/{topic}, non-persistent://tg/response/{topic}
        # Sets up Consumer and Producer

    async def invoke(self, user, config, arguments):
        """Override this method to implement the tool's logic."""
        raise NotImplementedError()
```

### İstemci Tarafı: ToolServiceImpl

`trustgraph-flow/trustgraph/agent/react/tools.py` içindeki uygulama:

```python
class ToolServiceImpl:
    def __init__(self, context, request_queue, response_queue, config_values, arguments, processor):
        # Uses the provided queue paths directly
        # Creates ToolServiceClient on first use

    async def invoke(self, **arguments):
        client = await self._get_or_create_client()
        response = await client.call(user, config_values, arguments)
        return response if isinstance(response, str) else json.dumps(response)
```

### Dosyalar

| Dosya | Amaç |
|------|---------|
| `trustgraph-base/trustgraph/schema/services/tool_service.py` | İstek/yanıt şemaları |
| `trustgraph-base/trustgraph/base/tool_service_client.py` | Hizmetleri çağırmak için istemci |
| `trustgraph-base/trustgraph/base/dynamic_tool_service.py` | Hizmet uygulamasının temel sınıfı |
| `trustgraph-flow/trustgraph/agent/react/tools.py` | `ToolServiceImpl` sınıfı |
| `trustgraph-flow/trustgraph/agent/react/service.py` | Yapılandırma yükleme |

### Örnek: Şaka Hizmeti

`trustgraph-flow/trustgraph/tool_service/joke/`'da bir örnek hizmet:

```python
class Processor(DynamicToolService):
    async def invoke(self, user, config, arguments):
        style = config.get("style", "pun")
        topic = arguments.get("topic", "")
        joke = pick_joke(topic, style)
        return f"Hey {user}! Here's a {style} for you:\n\n{joke}"
```

Araç hizmeti yapılandırması:
```json
{
  "id": "joke-service",
  "request-queue": "non-persistent://tg/request/joke",
  "response-queue": "non-persistent://tg/response/joke",
  "config-params": [{"name": "style", "required": false}]
}
```

Araç yapılandırması:
```json
{
  "type": "tool-service",
  "name": "tell-joke",
  "description": "Tell a joke on a given topic",
  "service": "joke-service",
  "style": "pun",
  "arguments": [
    {"name": "topic", "type": "string", "description": "The topic for the joke"}
  ]
}
```

### Geriye Dönük Uyumluluk

Mevcut, yerleşik araç türleri, herhangi bir değişiklik olmadan çalışmaya devam etmektedir.
`tool-service`, mevcut türlerin (`knowledge-query`, `mcp-tool`, vb.) yanı sıra yeni bir araç türüdür.

## Gelecek Planları

### Kendini Tanımlayan Hizmetler

Gelecekteki bir geliştirmede, hizmetlerin kendi tanımlarını yayınlamasına izin verilebilir:

Hizmetler, başlatıldığında, bilinen bir `tool-descriptors` konusuna yayın yapar.
Aracılar abone olur ve araçları dinamik olarak kaydeder.
Yapılandırma değişiklikleri olmadan gerçek bir tak ve çalıştır imkanı sağlar.

Bu, ilk uygulamada kapsam dışındadır.

## Referanslar

Mevcut araç uygulaması: `trustgraph-flow/trustgraph/agent/react/tools.py`
Araç kaydı: `trustgraph-flow/trustgraph/agent/react/service.py:105-214`
Aracı şemaları: `trustgraph-base/trustgraph/schema/services/agent.py`
