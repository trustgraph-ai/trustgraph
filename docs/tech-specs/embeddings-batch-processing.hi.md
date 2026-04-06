# एम्बेडिंग बैच प्रोसेसिंग तकनीकी विनिर्देश

## अवलोकन

यह विनिर्देश एम्बेडिंग सेवा के लिए अनुकूलन का वर्णन करता है ताकि एक ही अनुरोध में कई ग्रंथों को बैच में संसाधित किया जा सके। वर्तमान कार्यान्वयन एक समय में एक पाठ को संसाधित करता है, जिससे एम्बेडिंग मॉडल द्वारा प्रदान किए जाने वाले महत्वपूर्ण प्रदर्शन लाभों का उपयोग नहीं हो पाता है जब बैचों में प्रसंस्करण किया जाता है।

1. **सिंगल-टेक्स्ट प्रोसेसिंग की अक्षमता**: वर्तमान कार्यान्वयन एकल ग्रंथों को एक सूची में लपेटता है, जिससे FastEmbed की बैच क्षमताओं का पूरी तरह से उपयोग नहीं हो पाता है।
2. **प्रति-टेक्स्ट अनुरोध ओवरहेड**: प्रत्येक पाठ के लिए एक अलग पल्सर संदेश राउंड-ट्रिप की आवश्यकता होती है।
3. **मॉडल अनुमान की अक्षमता**: एम्बेडिंग मॉडल में एक निश्चित प्रति-बैच ओवरहेड होता है; छोटे बैच GPU/CPU संसाधनों को बर्बाद करते हैं।
4. **कॉलरों में सीरियल प्रोसेसिंग**: प्रमुख सेवाएं आइटम्स पर लूप करती हैं और एक-एक करके एम्बेडिंग को कॉल करती हैं।

## लक्ष्य

**बैच एपीआई समर्थन**: एक ही अनुरोध में कई ग्रंथों को संसाधित करने की क्षमता सक्षम करें।
**पिछड़ा संगतता**: एकल-पाठ अनुरोधों के लिए समर्थन बनाए रखें।
**महत्वपूर्ण थ्रूपुट सुधार**: बल्क ऑपरेशनों के लिए 5-10 गुना थ्रूपुट सुधार का लक्ष्य रखें।
**प्रति-पाठ कम विलंबता**: कई ग्रंथों को एम्बेड करते समय औसत विलंबता को कम करें।
**मेमोरी दक्षता**: अत्यधिक मेमोरी खपत के बिना बैचों को संसाधित करें।
**प्रदाता-अज्ञेय**: FastEmbed, Ollama और अन्य प्रदाताओं में बैचिंग का समर्थन करें।
**कॉलर माइग्रेशन**: सभी एम्बेडिंग कॉलरों को अपडेट करें ताकि वे जहां फायदेमंद हो वहां बैच एपीआई का उपयोग करें।

## पृष्ठभूमि

### वर्तमान कार्यान्वयन - एम्बेडिंग सेवा

`trustgraph-flow/trustgraph/embeddings/fastembed/processor.py` में एम्बेडिंग कार्यान्वयन में एक महत्वपूर्ण प्रदर्शन अक्षमता है:

```python
# fastembed/processor.py line 56
async def on_embeddings(self, text, model=None):
    use_model = model or self.default_model
    self._load_model(use_model)

    vecs = self.embeddings.embed([text])  # Single text wrapped in list

    return [v.tolist() for v in vecs]
```

**समस्याएँ:**

1. **बैच का आकार 1**: FastEmbed का `embed()` तरीका बैच प्रोसेसिंग के लिए अनुकूलित है, लेकिन हम हमेशा इसे `[text]` के साथ कॉल करते हैं - जो कि आकार 1 का एक बैच है।

2. **प्रति-अनुरोध ओवरहेड**: प्रत्येक एम्बेडिंग अनुरोध में शामिल हैं:
   पल्सर संदेश का क्रमबद्धता/विघटन
   नेटवर्क राउंड-ट्रिप विलंबता
   मॉडल अनुमान स्टार्टअप ओवरहेड
   पायथन एसिंक्रोनस शेड्यूलिंग ओवरहेड

3. **स्कीमा सीमा**: `EmbeddingsRequest` स्कीमा केवल एक टेक्स्ट का समर्थन करता है:
   ```python
   @dataclass
   class EmbeddingsRequest:
       text: str = ""  # Single text only
   ```

### वर्तमान कॉलर - सीरियल प्रोसेसिंग

#### 1. एपीआई गेटवे

**फ़ाइल:** `trustgraph-flow/trustgraph/gateway/dispatch/embeddings.py`

गेटवे HTTP/WebSocket के माध्यम से सिंगल-टेक्स्ट एम्बेडिंग अनुरोध स्वीकार करता है और उन्हें एम्बेडिंग सेवा को भेजता है। वर्तमान में कोई बैच एंडपॉइंट मौजूद नहीं है।

```python
class EmbeddingsRequestor(ServiceRequestor):
    # Handles single EmbeddingsRequest -> EmbeddingsResponse
    request_schema=EmbeddingsRequest,  # Single text only
    response_schema=EmbeddingsResponse,
```

**प्रभाव:** बाहरी क्लाइंट (वेब ऐप्स, स्क्रिप्ट) को N टेक्स्ट एम्बेड करने के लिए N HTTP अनुरोध करने होंगे।

#### 2. दस्तावेज़ एम्बेडिंग सेवा

**फ़ाइल:** `trustgraph-flow/trustgraph/embeddings/document_embeddings/embeddings.py`

दस्तावेज़ के टुकड़ों को एक-एक करके संसाधित करता है:

```python
async def on_message(self, msg, consumer, flow):
    v = msg.value()

    # Single chunk per request
    resp = await flow("embeddings-request").request(
        EmbeddingsRequest(text=v.chunk)
    )
    vectors = resp.vectors
```

**प्रभाव:** प्रत्येक दस्तावेज़ खंड के लिए एक अलग एम्बेडिंग कॉल की आवश्यकता होती है। 100 खंडों वाला एक दस्तावेज़ = 100 एम्बेडिंग अनुरोध।

#### 3. ग्राफ एम्बेडिंग सेवा

**फ़ाइल:** `trustgraph-flow/trustgraph/embeddings/graph_embeddings/embeddings.py`

यह एंटिटीज पर लूप करता है और प्रत्येक को क्रमिक रूप से एम्बेड करता है:

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

**प्रभाव:** 50 एंटिटीज वाला एक संदेश = 50 सीरियल एम्बेडिंग अनुरोध। यह ज्ञान ग्राफ निर्माण के दौरान एक बड़ी बाधा है।

#### 4. रो एम्बेडिंग सेवा

**फ़ाइल:** `trustgraph-flow/trustgraph/embeddings/row_embeddings/embeddings.py`

यह अद्वितीय टेक्स्ट पर लूप करता है और प्रत्येक को क्रमिक रूप से एम्बेड करता है:

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

**प्रभाव:** 100 अद्वितीय अनुक्रमित मानों वाली तालिका को संसाधित करने से 100 सीरियल एम्बेडिंग अनुरोध उत्पन्न होते हैं।

#### 5. एम्बेडिंग्सक्लाइंट (बेस क्लाइंट)

**फ़ाइल:** `trustgraph-base/trustgraph/base/embeddings_client.py`

सभी फ्लो प्रोसेसर द्वारा उपयोग किए जाने वाले क्लाइंट केवल सिंगल-टेक्स्ट एम्बेडिंग का समर्थन करते हैं:

```python
class EmbeddingsClient(RequestResponse):
    async def embed(self, text, timeout=30):
        resp = await self.request(
            EmbeddingsRequest(text=text),  # Single text
            timeout=timeout
        )
        return resp.vectors
```

**प्रभाव:** इस क्लाइंट का उपयोग करने वाले सभी एप्लिकेशन केवल एकल-पाठ संचालन तक सीमित हैं।

#### 6. कमांड-लाइन उपकरण

**फ़ाइल:** `trustgraph-cli/trustgraph/cli/invoke_embeddings.py`

कमांड-लाइन उपकरण एक एकल पाठ तर्क स्वीकार करता है:

```python
def query(url, flow_id, text, token=None):
    result = flow.embeddings(text=text)  # Single text
    vectors = result.get("vectors", [])
```

**प्रभाव:** उपयोगकर्ता कमांड लाइन से बैच एम्बेडिंग नहीं कर सकते। टेक्स्ट फ़ाइल को संसाधित करने के लिए N बार कॉल की आवश्यकता होती है।

#### 7. पायथन SDK

पायथन SDK ट्रस्टग्राफ सेवाओं के साथ इंटरैक्ट करने के लिए दो क्लाइंट क्लास प्रदान करता है। दोनों केवल सिंगल-टेक्स्ट एम्बेडिंग का समर्थन करते हैं।

**फ़ाइल:** `trustgraph-base/trustgraph/api/flow.py`

```python
class FlowInstance:
    def embeddings(self, text):
        """Get embeddings for a single text"""
        input = {"text": text}
        return self.request("service/embeddings", input)["vectors"]
```

**फ़ाइल:** `trustgraph-base/trustgraph/api/socket_client.py`

```python
class SocketFlowInstance:
    def embeddings(self, text: str, **kwargs: Any) -> Dict[str, Any]:
        """Get embeddings for a single text via WebSocket"""
        request = {"text": text}
        return self.client._send_request_sync(
            "embeddings", self.flow_id, request, False
        )
```

**प्रभाव:** एसडीके का उपयोग करने वाले पायथन डेवलपर्स को टेक्स्ट पर लूप करना होगा और एन अलग एपीआई कॉल करने होंगे। एसडीके उपयोगकर्ताओं के लिए कोई बैच एम्बेडिंग समर्थन मौजूद नहीं है।

### प्रदर्शन प्रभाव

सामान्य दस्तावेज़ इनपुट (1000 टेक्स्ट खंड) के लिए:
**वर्तमान:** 1000 अलग-अलग अनुरोध, 1000 मॉडल अनुमान कॉल
**बैच (batch_size=32):** 32 अनुरोध, 32 मॉडल अनुमान कॉल (96.8% कमी)

ग्राफ एम्बेडिंग (50 संस्थाओं वाला संदेश) के लिए:
**वर्तमान:** 50 सीरियल अवित कॉल, ~5-10 सेकंड
**बैच:** 1-2 बैच कॉल, ~0.5-1 सेकंड (5-10 गुना सुधार)

FastEmbed और समान लाइब्रेरी हार्डवेयर सीमाओं तक बैच आकार के साथ लगभग रैखिक थ्रूपुट स्केलिंग प्राप्त करती हैं (आमतौर पर प्रति बैच 32-128 टेक्स्ट)।

## तकनीकी डिज़ाइन

### आर्किटेक्चर

एम्बेडिंग बैच प्रोसेसिंग अनुकूलन के लिए निम्नलिखित घटकों में परिवर्तन की आवश्यकता है:

#### 1. **स्कीमा संवर्धन**
   `EmbeddingsRequest` को कई टेक्स्ट का समर्थन करने के लिए विस्तारित करें
   `EmbeddingsResponse` को कई वेक्टर सेट वापस करने के लिए विस्तारित करें
   एकल-टेक्स्ट अनुरोधों के साथ पिछड़े अनुकूलता बनाए रखें

   मॉड्यूल: `trustgraph-base/trustgraph/schema/services/llm.py`

#### 2. **बेस सर्विस संवर्धन**
   `EmbeddingsService` को बैच अनुरोधों को संभालने के लिए अपडेट करें
   बैच आकार कॉन्फ़िगरेशन जोड़ें
   बैच-जागरूक अनुरोध हैंडलिंग लागू करें

   मॉड्यूल: `trustgraph-base/trustgraph/base/embeddings_service.py`

#### 3. **प्रदाता प्रोसेसर अपडेट**
   FastEmbed प्रोसेसर को अपडेट करें ताकि `embed()` को पूरा बैच पास किया जा सके
   यदि समर्थित है, तो बैचों को संभालने के लिए Ollama प्रोसेसर को अपडेट करें
   बैच समर्थन के बिना प्रदाताओं के लिए एक वैकल्पिक अनुक्रमिक प्रसंस्करण जोड़ें

   मॉड्यूल:
   `trustgraph-flow/trustgraph/embeddings/fastembed/processor.py`
   `trustgraph-flow/trustgraph/embeddings/ollama/processor.py`

#### 4. **क्लाइंट में सुधार**
   `EmbeddingsClient` में बैच एम्बेडिंग विधि जोड़ें
   सिंगल और बैच एपीआई दोनों का समर्थन करें
   बड़े इनपुट के लिए स्वचालित बैचिंग जोड़ें

   मॉड्यूल: `trustgraph-base/trustgraph/base/embeddings_client.py`

#### 5. **कॉल करने वाले अपडेट - फ्लो प्रोसेसर**
   `graph_embeddings` को बैच एंटिटी कॉन्टेक्स्ट के लिए अपडेट करें
   `row_embeddings` को बैच इंडेक्स टेक्स्ट के लिए अपडेट करें
   यदि संदेश बैचिंग संभव है, तो `document_embeddings` को अपडेट करें

   मॉड्यूल:
   `trustgraph-flow/trustgraph/embeddings/graph_embeddings/embeddings.py`
   `trustgraph-flow/trustgraph/embeddings/row_embeddings/embeddings.py`
   `trustgraph-flow/trustgraph/embeddings/document_embeddings/embeddings.py`

#### 6. **एपीआई गेटवे में सुधार**
   बैच एम्बेडिंग एंडपॉइंट जोड़ें
   अनुरोध बॉडी में टेक्स्ट की सरणी का समर्थन करें

   मॉड्यूल: `trustgraph-flow/trustgraph/gateway/dispatch/embeddings.py`

#### 7. **सीएलआई टूल में सुधार**
   कई टेक्स्ट या फ़ाइल इनपुट के लिए समर्थन जोड़ें
   बैच आकार पैरामीटर जोड़ें

   मॉड्यूल: `trustgraph-cli/trustgraph/cli/invoke_embeddings.py`

#### 8. **पायथन एसडीके में सुधार**
   `FlowInstance` में `embeddings_batch()` विधि जोड़ें
   `SocketFlowInstance` में `embeddings_batch()` विधि जोड़ें
   एसडीके उपयोगकर्ताओं के लिए सिंगल और बैच एपीआई दोनों का समर्थन करें

   मॉड्यूल:
   `trustgraph-base/trustgraph/api/flow.py`
   `trustgraph-base/trustgraph/api/socket_client.py`

### डेटा मॉडल

#### एम्बेडिंग्स रिक्वेस्ट

```python
@dataclass
class EmbeddingsRequest:
    texts: list[str] = field(default_factory=list)
```

उपयोग:
एकल पाठ: `EmbeddingsRequest(texts=["hello world"])`
बैच: `EmbeddingsRequest(texts=["text1", "text2", "text3"])`

#### एम्बेडिंग रिस्पांस

```python
@dataclass
class EmbeddingsResponse:
    error: Error | None = None
    vectors: list[list[list[float]]] = field(default_factory=list)
```

प्रतिक्रिया संरचना:
`vectors[i]` में `texts[i]` के लिए वेक्टर सेट शामिल है।
प्रत्येक वेक्टर सेट `list[list[float]]` होता है (मॉडल प्रत्येक पाठ के लिए कई वेक्टर वापस कर सकते हैं)।
उदाहरण: 3 पाठ → `vectors` में 3 प्रविष्टियाँ हैं, जिनमें से प्रत्येक में उस पाठ के एम्बेडिंग होते हैं।

### एपीआई

#### एम्बेडिंगक्लाइंट

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

#### एपीआई गेटवे एम्बेडिंग एंडपॉइंट

अपडेटेड एंडपॉइंट जो सिंगल या बैच एम्बेडिंग को सपोर्ट करता है:

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

### कार्यान्वयन विवरण

#### चरण 1: स्कीमा परिवर्तन

**एम्बेडिंग रिक्वेस्ट:**
```python
@dataclass
class EmbeddingsRequest:
    texts: list[str] = field(default_factory=list)
```

**एम्बेडिंग रिस्पांस:**
```python
@dataclass
class EmbeddingsResponse:
    error: Error | None = None
    vectors: list[list[list[float]]] = field(default_factory=list)
```

**अपडेटेड एम्बेडिंगसर्विस.ऑन_रिक्वेस्ट:**
```python
async def on_request(self, msg, consumer, flow):
    request = msg.value()
    id = msg.properties()["id"]
    model = flow("model")

    vectors = await self.on_embeddings(request.texts, model=model)
    response = EmbeddingsResponse(error=None, vectors=vectors)

    await flow("response").send(response, properties={"id": id})
```

#### चरण 2: फास्टएम्बेड प्रोसेसर अपडेट

**वर्तमान (अकुशल):**
```python
async def on_embeddings(self, text, model=None):
    use_model = model or self.default_model
    self._load_model(use_model)
    vecs = self.embeddings.embed([text])  # Batch of 1
    return [v.tolist() for v in vecs]
```

**अद्यतन:**
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

#### चरण 3: ग्राफ एम्बेडिंग सेवा अपडेट

**वर्तमान (सीरियल):**
```python
async def on_message(self, msg, consumer, flow):
    entities = []
    for entity in v.entities:
        vectors = await flow("embeddings-request").embed(text=entity.context)
        entities.append(EntityEmbeddings(...))
```

**अद्यतन (बैच):**
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

#### चरण 4: पंक्ति एम्बेडिंग सेवा अपडेट

**वर्तमान (क्रमिक):**
```python
for text, (index_name, index_value) in texts_to_embed.items():
    vectors = await flow("embeddings-request").embed(text=text)
    embeddings_list.append(RowIndexEmbedding(...))
```

**अद्यतन (बैच):**
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

#### चरण 5: कमांड-लाइन टूल में सुधार

**अद्यतन कमांड-लाइन इंटरफ़ेस:**
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

उपयोग:
```bash
# Single text (existing)
tg-invoke-embeddings "hello world"

# Multiple texts
tg-invoke-embeddings "text one" "text two" "text three"

# From file
tg-invoke-embeddings -f texts.txt --batch-size 64
```

#### चरण 6: पायथन एसडीके में सुधार

**फ्लोइंस्टेंस (एचटीटीपी क्लाइंट):**

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

**सॉकेटफ्लोइंस्टेंस (वेबसोकेट क्लाइंट):**

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

**एसडीके उपयोग के उदाहरण:**

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

## सुरक्षा संबंधी विचार

**अनुरोध आकार सीमाएँ**: संसाधनों की कमी को रोकने के लिए अधिकतम बैच आकार लागू करें।
**समय-सीमा प्रबंधन**: बैच आकार के लिए समय-सीमा को उचित रूप से समायोजित करें।
**मेमोरी सीमाएँ**: बड़े बैचों के लिए मेमोरी उपयोग की निगरानी करें।
**इनपुट सत्यापन**: प्रसंस्करण से पहले बैच में सभी पाठों को मान्य करें।

## प्रदर्शन संबंधी विचार

### अपेक्षित सुधार

**थ्रूपुट:**
एकल-पाठ: ~10-50 पाठ/सेकंड (मॉडल के आधार पर)
बैच (आकार 32): ~200-500 पाठ/सेकंड (5-10 गुना सुधार)

**प्रति पाठ विलंबता:**
एकल-पाठ: प्रति पाठ 50-200ms
बैच (आकार 32): प्रति पाठ 5-20ms (औसत)

**सेवा-विशिष्ट सुधार:**

| सेवा | वर्तमान | बैच | सुधार |
|---------|---------|---------|-------------|
| ग्राफ एम्बेडिंग (50 इकाइयाँ) | 5-10s | 0.5-1s | 5-10x |
| पंक्ति एम्बेडिंग (100 पाठ) | 10-20s | 1-2s | 5-10x |
| दस्तावेज़ इनपुट (1000 खंड) | 100-200s | 10-30s | 5-10x |

### कॉन्फ़िगरेशन पैरामीटर

```python
# Recommended defaults
DEFAULT_BATCH_SIZE = 32
MAX_BATCH_SIZE = 128
BATCH_TIMEOUT_MULTIPLIER = 2.0
```

## परीक्षण रणनीति

### यूनिट परीक्षण
सिंगल टेक्स्ट एम्बेडिंग (पिछड़ा संगतता)
खाली बैच हैंडलिंग
अधिकतम बैच आकार का प्रवर्तन
आंशिक बैच विफलताओं के लिए त्रुटि हैंडलिंग

### एकीकरण परीक्षण
पल्सर के माध्यम से एंड-टू-एंड बैच एम्बेडिंग
ग्राफ एम्बेडिंग सेवा बैच प्रसंस्करण
रो एम्बेडिंग सेवा बैच प्रसंस्करण
एपीआई गेटवे बैच एंडपॉइंट

### प्रदर्शन परीक्षण
सिंगल बनाम बैच थ्रूपुट का बेंचमार्क
विभिन्न बैच आकारों के तहत मेमोरी उपयोग
विलंबता वितरण विश्लेषण

## माइग्रेशन योजना

यह एक ब्रेकिंग चेंज रिलीज़ है। सभी चरण एक साथ लागू किए गए हैं।

### चरण 1: स्कीमा परिवर्तन
EmbeddingsRequest में `text: str` को `texts: list[str]` से बदलें
EmbeddingsResponse में `vectors` प्रकार को `list[list[list[float]]]` में बदलें

### चरण 2: प्रोसेसर अपडेट
FastEmbed और Ollama प्रोसेसर में `on_embeddings` हस्ताक्षर को अपडेट करें
सिंगल मॉडल कॉल में पूरा बैच संसाधित करें

### चरण 3: क्लाइंट अपडेट
`EmbeddingsClient.embed()` को `texts: list[str]` स्वीकार करने के लिए अपडेट करें

### चरण 4: कॉलर अपडेट
graph_embeddings को बैच एंटिटी संदर्भों के लिए अपडेट करें
row_embeddings को बैच इंडेक्स टेक्स्ट के लिए अपडेट करें
document_embeddings को नए स्कीमा का उपयोग करने के लिए अपडेट करें
CLI टूल को अपडेट करें

### चरण 5: एपीआई गेटवे
नए स्कीमा के लिए एम्बेडिंग एंडपॉइंट को अपडेट करें

### चरण 6: पायथन SDK
`FlowInstance.embeddings()` हस्ताक्षर को अपडेट करें
`SocketFlowInstance.embeddings()` हस्ताक्षर को अपडेट करें

## खुले प्रश्न

**बड़े बैचों का स्ट्रीमिंग**: क्या हमें बहुत बड़े बैचों (>100 टेक्स्ट) के लिए स्ट्रीमिंग परिणामों का समर्थन करना चाहिए?
**प्रदाता-विशिष्ट सीमाएँ**: हमें विभिन्न अधिकतम बैच आकारों वाले प्रदाताओं को कैसे संभालना चाहिए?
**आंशिक विफलता हैंडलिंग**: यदि बैच में एक टेक्स्ट विफल हो जाता है, तो क्या हमें पूरे बैच को विफल करना चाहिए या आंशिक परिणाम लौटाने चाहिए?
**डॉक्यूमेंट एम्बेडिंग बैचिंग**: क्या हमें कई चंक संदेशों में बैच करना चाहिए या प्रति-संदेश प्रसंस्करण बनाए रखना चाहिए?

## संदर्भ

[FastEmbed Documentation](https://github.com/qdrant/fastembed)
[Ollama Embeddings API](https://github.com/ollama/ollama)
[EmbeddingsService Implementation](trustgraph-base/trustgraph/base/embeddings_service.py)
[GraphRAG Performance Optimization](graphrag-performance-optimization.md)
