# JSONL İstek Çıktısı Teknik Özellikleri

## Genel Bakış

Bu özellik, TrustGraph'ta istek yanıtları için JSONL (JSON Lines) çıktı biçiminin uygulanmasını tanımlar. JSONL, LLM yanıtlarından yapılandırılmış verilerin, LLM yanıtları çıktı belirteç sınırlarına ulaştığında JSON dizisi çıktıları bozulduğunda ortaya çıkan kritik sorunları ele alarak, kesme hatalarına karşı dayanıklı bir şekilde çıkarılmasını sağlar.





Bu uygulama, aşağıdaki kullanım senaryolarını destekler:

1. **Kesintiye Dayanıklı Çıkarma**: LLM çıktısı yanıtın ortasında kesildiğinde bile geçerli kısmi sonuçları çıkarın.
   
2. **Büyük Ölçekli Çıkarma**: Token limitleri nedeniyle tam bir başarısızlık riski olmadan birçok öğenin çıkarılmasını işleyin.
   
3. **Karma Tip Çıkarma**: Tek bir istemde birden fazla varlık türünün (tanımlar, ilişkiler, varlıklar, özellikler) çıkarılmasını destekleyin.
   
4. **Akışla Uyumlu Çıktı**: Çıkarma sonuçlarının gelecekteki akış/artımlı
   işlenmesini sağlayın.

## Hedefler

**Geriye Dönük Uyumluluk**: `response-type: "text"` kullanan mevcut istemler ve
  `response-type: "json"`, herhangi bir değişiklik yapılmadan çalışmaya devam eder.
**Kesinti Dayanıklılığı**: Kısmi LLM çıktıları, tam bir başarısızlık yerine kısmi, geçerli sonuçlar üretir.
  
**Şema Doğrulama**: Bireysel nesneler için JSON şema doğrulamasını destekler.
**Ayırıcı Birleşimler**: `type` alanını kullanarak karma türlü çıktıları destekler.
  
**Minimum API Değişiklikleri**: Mevcut istem yapılandırmasını, yeni
  yanıt türü ve şema anahtarıyla genişletir.

## Arka Plan

### Mevcut Mimari

İstek hizmeti, iki tür yanıtı destekler:

1. `response-type: "text"` - Ham metin yanıtı, olduğu gibi döndürülür.
2. `response-type: "json"` - Yanıttan ayrıştırılan JSON, isteğe bağlı `response-type: "json"`'a göre doğrulanır.
   isteğe bağlı `schema`

`trustgraph-flow/trustgraph/template/prompt_manager.py`'daki mevcut uygulama:

```python
class Prompt:
    def __init__(self, template, response_type = "text", terms=None, schema=None):
        self.template = template
        self.response_type = response_type
        self.terms = terms
        self.schema = schema
```

### Mevcut Sınırlamalar

Çıkarma komutları, çıktıyı JSON dizileri (`[{...}, {...}, ...]`) olarak istediğinde:

**Kesme nedeniyle oluşan bozulma**: Eğer LLM, dizi ortasında çıktı belirteç sınırlarına ulaştığında,
  tüm yanıt geçersiz bir JSON haline gelir ve işlenemez.
**Tümünü veya hiçbirini işleme**: İşlemeye başlamadan önce tam çıktıyı almanız gerekir.
**Kısmi sonuçlar yok**: Kesilmiş bir yanıt, kullanılabilir veri olarak sıfır veri verir.
**Büyük çıkarmalar için güvenilir değil**: Çıkarılan öğe sayısı arttıkça, başarısızlık riski daha yüksektir.

Bu özellik, her çıkarılan öğenin kendi satırında bulunan tam bir JSON nesnesi olduğu JSONL formatını kullanarak, bu sınırlamaları ele alır.



## Teknik Tasarım

### Yanıt Tipi Genişletmesi

Mevcut `"text"` ve `"json"` türlerinin yanı sıra yeni bir yanıt türü `"jsonl"` ekleyin.


#### Yapılandırma Değişiklikleri


```
"response-type": "jsonl"
```

**Şema yorumlaması:**

Mevcut `"schema"` anahtarı, hem `"json"` hem de `"jsonl"` yanıtları için kullanılmaktadır.
Yorumlama, yanıt türüne bağlıdır:

`"json"`: Şema, tüm yanıtı (genellikle bir dizi veya nesne) tanımlar.
`"jsonl"`: Şema, her bir satırı/nesneyi ayrı ayrı tanımlar.

```json
{
  "response-type": "jsonl",
  "schema": {
    "type": "object",
    "properties": {
      "entity": { "type": "string" },
      "definition": { "type": "string" }
    },
    "required": ["entity", "definition"]
  }
}
```

Bu, istem yapılandırma araçlarına ve düzenleyicilere yapılan değişiklikleri önler.

### JSONL Biçim Özellikleri

#### Basit Çıkarma

Tek bir nesne türünü (tanımlar, ilişkiler,
konular, satırlar) çıkaran istemler için, çıktı her satırda bir JSON nesnesidir ve herhangi bir sarma bulunmaz:

**İstem çıktı biçimi:**
```
{"entity": "photosynthesis", "definition": "Process by which plants convert sunlight"}
{"entity": "chlorophyll", "definition": "Green pigment in plants"}
{"entity": "mitochondria", "definition": "Powerhouse of the cell"}
```

**Önceki JSON dizi formatıyla karşılaştırma:**
```json
[
  {"entity": "photosynthesis", "definition": "Process by which plants convert sunlight"},
  {"entity": "chlorophyll", "definition": "Green pigment in plants"},
  {"entity": "mitochondria", "definition": "Powerhouse of the cell"}
]
```

Eğer LLM, 2. satırdan sonra kesilirse, JSON dizisi formatı geçersiz bir JSON oluşturur,
ancak JSONL iki geçerli nesne üretir.

#### Karışık Tip Çıkarımı (Ayırıcı Birleşimler)

Birden fazla nesne türünü çıkaran (örneğin, hem tanımları hem de
ilişkileri, veya varlıklar, ilişkiler ve özellikler) istemler için, bir `"type"`
alanını ayırıcı olarak kullanın:

**İstem çıktısı formatı:**
```
{"type": "definition", "entity": "DNA", "definition": "Molecule carrying genetic instructions"}
{"type": "relationship", "subject": "DNA", "predicate": "located_in", "object": "cell nucleus", "object-entity": true}
{"type": "definition", "entity": "RNA", "definition": "Molecule that carries genetic information"}
{"type": "relationship", "subject": "RNA", "predicate": "transcribed_from", "object": "DNA", "object-entity": true}
```

**Ayırıcı birleşimler için şema, `oneOf` kullanır:**
```json
{
  "response-type": "jsonl",
  "schema": {
    "oneOf": [
      {
        "type": "object",
        "properties": {
          "type": { "const": "definition" },
          "entity": { "type": "string" },
          "definition": { "type": "string" }
        },
        "required": ["type", "entity", "definition"]
      },
      {
        "type": "object",
        "properties": {
          "type": { "const": "relationship" },
          "subject": { "type": "string" },
          "predicate": { "type": "string" },
          "object": { "type": "string" },
          "object-entity": { "type": "boolean" }
        },
        "required": ["type", "subject", "predicate", "object", "object-entity"]
      }
    ]
  }
}
```

#### Ontoloji Çıkarımı

Varlıklar, ilişkiler ve özelliklerle ontoloji tabanlı çıkarım için:

**İstenen çıktı formatı:**
```
{"type": "entity", "entity": "Cornish pasty", "entity_type": "fo/Recipe"}
{"type": "entity", "entity": "beef", "entity_type": "fo/Food"}
{"type": "relationship", "subject": "Cornish pasty", "subject_type": "fo/Recipe", "relation": "fo/has_ingredient", "object": "beef", "object_type": "fo/Food"}
{"type": "attribute", "entity": "Cornish pasty", "entity_type": "fo/Recipe", "attribute": "fo/serves", "value": "4 people"}
```

### Uygulama Detayları

#### İstek Sınıfı

Mevcut `Prompt` sınıfı herhangi bir değişiklik gerektirmiyor. `schema` alanı yeniden kullanılıyor.
JSONL formatı için, yorumlanması `response_type` ile belirlenir:

```python
class Prompt:
    def __init__(self, template, response_type="text", terms=None, schema=None):
        self.template = template
        self.response_type = response_type
        self.terms = terms
        self.schema = schema  # Interpretation depends on response_type
```

#### PromptManager.load_config

Herhangi bir değişiklik gerekli değil - mevcut yapılandırma yüklemesi zaten
`schema` anahtarını işlemektedir.

#### JSONL Ayrıştırma

JSONL yanıtları için yeni bir ayrıştırma yöntemi ekleyin:

```python
def parse_jsonl(self, text):
    """
    Parse JSONL response, returning list of valid objects.

    Invalid lines (malformed JSON, empty lines) are skipped with warnings.
    This provides truncation resilience - partial output yields partial results.
    """
    results = []

    for line_num, line in enumerate(text.strip().split('\n'), 1):
        line = line.strip()

        # Skip empty lines
        if not line:
            continue

        # Skip markdown code fence markers if present
        if line.startswith('```'):
            continue

        try:
            obj = json.loads(line)
            results.append(obj)
        except json.JSONDecodeError as e:
            # Log warning but continue - this provides truncation resilience
            logger.warning(f"JSONL parse error on line {line_num}: {e}")

    return results
```

#### PromptManager.invoke Değişiklikleri

Yeni yanıt türünü işleyebilmek için invoke yöntemini genişletin:

```python
async def invoke(self, id, input, llm):
    logger.debug("Invoking prompt template...")

    terms = self.terms | self.prompts[id].terms | input
    resp_type = self.prompts[id].response_type

    prompt = {
        "system": self.system_template.render(terms),
        "prompt": self.render(id, input)
    }

    resp = await llm(**prompt)

    if resp_type == "text":
        return resp

    if resp_type == "json":
        try:
            obj = self.parse_json(resp)
        except:
            logger.error(f"JSON parse failed: {resp}")
            raise RuntimeError("JSON parse fail")

        if self.prompts[id].schema:
            try:
                validate(instance=obj, schema=self.prompts[id].schema)
                logger.debug("Schema validation successful")
            except Exception as e:
                raise RuntimeError(f"Schema validation fail: {e}")

        return obj

    if resp_type == "jsonl":
        objects = self.parse_jsonl(resp)

        if not objects:
            logger.warning("JSONL parse returned no valid objects")
            return []

        # Validate each object against schema if provided
        if self.prompts[id].schema:
            validated = []
            for i, obj in enumerate(objects):
                try:
                    validate(instance=obj, schema=self.prompts[id].schema)
                    validated.append(obj)
                except Exception as e:
                    logger.warning(f"Object {i} failed schema validation: {e}")
            return validated

        return objects

    raise RuntimeError(f"Response type {resp_type} not known")
```

### Etkilenen İstekler

Aşağıdaki istekler JSONL formatına aktarılmalıdır:

| İstek Kimliği | Açıklama | Tür Alanı |
|-----------|-------------|------------|
| `extract-definitions` | Varlık/tanım çıkarma | Hayır (tek tür) |
| `extract-relationships` | İlişki çıkarma | Hayır (tek tür) |
| `extract-topics` | Konu/tanım çıkarma | Hayır (tek tür) |
| `extract-rows` | Yapılandırılmış satır çıkarma | Hayır (tek tür) |
| `agent-kg-extract` | Birleştirilmiş tanım + ilişki çıkarma | Evet: `"definition"`, `"relationship"` |
| `extract-with-ontologies` / `ontology-extract` | Ontoloji tabanlı çıkarma | Evet: `"entity"`, `"relationship"`, `"attribute"` |

### API Değişiklikleri

#### Müşteri Perspektifi

JSONL ayrıştırması, istem hizmeti API'sini kullananlar için şeffaftır. Ayrıştırma, istem hizmetinde sunucu tarafında gerçekleşir ve yanıt standart
bir şekilde döndürülür.
`PromptResponse.object` alanını seri hale edilmiş bir JSON dizisi olarak.

Müşteriler, istem hizmetini (`PromptClient.prompt()` veya benzeri bir yöntemle) kullandığında:

**`response-type: "json"`** (dizi şeması ile) → müşteri, Python `list` alır.
**`response-type: "jsonl"`** → müşteri, Python `list` alır.

Müşterinin bakış açısıyla, her iki yöntem de aynı veri yapılarını döndürür.
Fark, tamamen LLM çıktısının sunucu tarafında nasıl işlendiğindedir:

JSON dizisi formatı: Tek `json.loads()` çağrısı; kısaltılırsa tamamen başarısız olur.
JSONL formatı: Satır satır ayrıştırma; kısaltılırsa kısmi sonuçlar verir.

Bu, çıkarma istemlerinden bir liste bekleyen mevcut istemci kodunun, istemleri JSON'dan JSONL formatına geçirirken herhangi bir değişikliğe ihtiyaç duymamasını sağlar.


#### Sunucu Dönüş Değeri

`response-type: "jsonl"` için, `PromptManager.invoke()` metodu,
başarıyla ayrıştırılmış ve doğrulanmış tüm nesneleri içeren bir `list[dict]` döndürür. Bu
liste, daha sonra `PromptResponse.object` alanı için JSON'a dönüştürülür.

#### Hata Yönetimi

Boş sonuçlar: Uyarı günlüğü ile boş bir liste `[]` döndürür.
Kısmi ayrıştırma hatası: Başarıyla ayrıştırılmış nesnelerin bir listesini ve
  hatalar için uyarı günlüklerini döndürür.
Tam ayrıştırma hatası: Uyarı günlükleriyle boş bir liste `[]` döndürür.

Bu, `response-type: "json"`'den farklıdır, çünkü `RuntimeError` ayrıştırma hatası durumunda `RuntimeError` hatası oluşturur.
JSONL için daha hoşgörülü davranış, kesintilere karşı dayanıklılık sağlamak amacıyla kasıtlıdır.


### Yapılandırma Örneği

Tam istem yapılandırma örneği:

```json
{
  "prompt": "Extract all entities and their definitions from the following text. Output one JSON object per line.\n\nText:\n{{text}}\n\nOutput format per line:\n{\"entity\": \"<name>\", \"definition\": \"<definition>\"}",
  "response-type": "jsonl",
  "schema": {
    "type": "object",
    "properties": {
      "entity": {
        "type": "string",
        "description": "The entity name"
      },
      "definition": {
        "type": "string",
        "description": "A clear definition of the entity"
      }
    },
    "required": ["entity", "definition"]
  }
}
```

## Güvenlik Hususları

**Girdi Doğrulama**: JSON ayrıştırması, standart `json.loads()`'ı kullanır ve bu, enjeksiyon saldırılarına karşı güvenlidir.
  **Şema Doğrulama**: Şema zorlaması için ⟦CODE_0⟧ kullanılır.
**Şema Doğrulama**: Şema uyumluluğunu sağlamak için `jsonschema.validate()` kullanılır.
**Yeni Bir Saldırı Yüzeyi Yok**: JSONL ayrıştırması, satır satır işlenmesi nedeniyle JSON dizisi ayrıştırmasından çok daha güvenlidir.
  

## Performans Hususları

**Bellek**: Satır satır ayrıştırma, tam JSON dizilerini yüklemekten daha az bellek kullanır.
  **Gecikme**: Ayrıştırma performansı, JSON dizisi ayrıştırmasıyla karşılaştırılabilir.
**Doğrulama**: Şema doğrulaması, her bir nesne için yapılır, bu da ek yük getirir ancak
doğrulama başarısız olduğunda kısmi sonuçlar elde etmeyi sağlar.
  
## Test Stratejisi


### Birim Testleri

Geçerli giriş ile JSONL ayrıştırma
Boş satırlarla JSONL ayrıştırma
Markdown kod bloklarıyla JSONL ayrıştırma
Kesilmiş son satırla JSONL ayrıştırma
Geçersiz JSON satırlarının arasına serpiştirilmiş JSONL ayrıştırma
`oneOf` ayrımcı birleşimlerle şema doğrulaması
Geriye dönük uyumluluk: Mevcut `"text"` ve `"json"` istemleri değişmeden kalır

### Entegrasyon Testleri

JSONL istemleriyle uçtan uca çıkarma
Simüle edilmiş kesme ile çıkarma (yapay olarak sınırlı yanıt)
Tür ayrımcısı ile karma tür çıkarma
Üç türün tamamıyla ontoloji çıkarma

### Çıkarma Kalitesi Testleri

Çıkarma sonuçlarını karşılaştırın: JSONL ile JSON dizisi formatı
Kesme dayanıklılığını doğrulayın: JSONL, JSON'un başarısız olduğu durumlarda kısmi sonuçlar verir

## Geçiş Planı

### 1. Aşama: Uygulama

1. `parse_jsonl()` yöntemini `PromptManager` içinde uygulayın
2. `invoke()`'ı `response-type: "jsonl"`'i işleyebilecek şekilde genişletin
3. Birim testleri ekleyin

### 2. Aşama: İstek Geçişi

1. `extract-definitions` isteğini ve yapılandırmasını güncelleyin
2. `extract-relationships` isteğini ve yapılandırmasını güncelleyin
3. `extract-topics` isteğini ve yapılandırmasını güncelleyin
4. `extract-rows` isteğini ve yapılandırmasını güncelleyin
5. `agent-kg-extract` isteğini ve yapılandırmasını güncelleyin
6. `extract-with-ontologies` isteğini ve yapılandırmasını güncelleyin

### 3. Aşama: Aşağı Akış Güncellemeleri

1. Çıkarma sonuçlarını kullanan tüm kodu, liste dönüş türünü işleyebilecek şekilde güncelleyin
2. `type` alanına göre karma türdeki çıkarma sonuçlarını kategorize eden kodu güncelleyin
3. Çıkarma çıktısı formatı hakkında doğrulama yapan testleri güncelleyin

## Açık Sorular

Şu anda yok.

## Referanslar

Mevcut uygulama: `trustgraph-flow/trustgraph/template/prompt_manager.py`
JSON Lines belirtimi: https://jsonlines.org/
JSON Şeması `oneOf`: https://json-schema.org/understanding-json-schema/reference/combining.html#oneof
İlgili belirtim: Streaming LLM Responses (`docs/tech-specs/streaming-llm-responses.md`)
