# RAG स्ट्रीमिंग सपोर्ट तकनीकी विनिर्देश

## अवलोकन

यह विनिर्देश ग्राफआरएजी और डॉक्यूमेंटआरएजी सेवाओं में स्ट्रीमिंग सपोर्ट जोड़ने का वर्णन करता है, जो नॉलेज ग्राफ और डॉक्यूमेंट रिट्रीवल क्वेरी के लिए वास्तविक समय में टोकन-दर-टोकन प्रतिक्रियाएं सक्षम करता है। यह एलएलएम टेक्स्ट-कंप्लीशन, प्रॉम्प्ट और एजेंट सेवाओं के लिए पहले से लागू किए गए मौजूदा स्ट्रीमिंग आर्किटेक्चर का विस्तार करता है।

## लक्ष्य

**संगत स्ट्रीमिंग यूएक्स**: सभी ट्रस्टग्राफ सेवाओं में समान स्ट्रीमिंग अनुभव प्रदान करें।
**न्यूनतम एपीआई परिवर्तन**: एक ही `streaming` फ़्लैग के साथ स्ट्रीमिंग सपोर्ट जोड़ें, स्थापित पैटर्न का पालन करें।
**पिछड़ा संगतता**: मौजूदा गैर-स्ट्रीमिंग व्यवहार को डिफ़ॉल्ट के रूप में बनाए रखें।
**मौजूदा बुनियादी ढांचे का पुन: उपयोग**: पहले से लागू प्रॉम्प्टक्लाइंट स्ट्रीमिंग का लाभ उठाएं।
**गेटवे सपोर्ट**: क्लाइंट एप्लिकेशन के लिए वेबसॉकेट गेटवे के माध्यम से स्ट्रीमिंग सक्षम करें।

## पृष्ठभूमि

वर्तमान में लागू की गई स्ट्रीमिंग सेवाएं:
**एलएलएम टेक्स्ट-कंप्लीशन सेवा**: चरण 1 - एलएलएम प्रदाताओं से स्ट्रीमिंग।
**प्रॉम्प्ट सेवा**: चरण 2 - प्रॉम्प्ट टेम्प्लेट के माध्यम से स्ट्रीमिंग।
**एजेंट सेवा**: चरण 3-4 - इंक्रीमेंटल थॉट/ऑब्जर्वेशन/एन्सर चंक्स के साथ रीएक्ट प्रतिक्रियाओं को स्ट्रीमिंग करना।

आरएजी सेवाओं के लिए वर्तमान सीमाएं:
ग्राफआरएजी और डॉक्यूमेंटआरएजी केवल ब्लॉकिंग प्रतिक्रियाओं का समर्थन करते हैं।
उपयोगकर्ताओं को किसी भी आउटपुट को देखने से पहले एलएलएम प्रतिक्रिया पूरी होने तक इंतजार करना होगा।
नॉलेज ग्राफ या डॉक्यूमेंट क्वेरी से लंबी प्रतिक्रियाओं के लिए खराब यूएक्स।
अन्य ट्रस्टग्राफ सेवाओं की तुलना में असंगत अनुभव।

यह विनिर्देश ग्राफआरएजी और डॉक्यूमेंटआरएजी में स्ट्रीमिंग सपोर्ट जोड़कर इन कमियों को दूर करता है। टोकन-दर-टोकन प्रतिक्रियाओं को सक्षम करके, ट्रस्टग्राफ:
सभी क्वेरी प्रकारों में संगत स्ट्रीमिंग यूएक्स प्रदान कर सकता है।
आरएजी क्वेरी के लिए कथित विलंबता को कम कर सकता है।
लंबी अवधि की क्वेरी के लिए बेहतर प्रगति प्रतिक्रिया प्रदान कर सकता है।
क्लाइंट एप्लिकेशन में वास्तविक समय प्रदर्शन का समर्थन कर सकता है।

## तकनीकी डिजाइन

### आर्किटेक्चर

आरएजी स्ट्रीमिंग कार्यान्वयन मौजूदा बुनियादी ढांचे का लाभ उठाता है:

1. **प्रॉम्प्टक्लाइंट स्ट्रीमिंग** (पहले से लागू)
   `kg_prompt()` और `document_prompt()` पहले से ही `streaming` और `chunk_callback` पैरामीटर स्वीकार करते हैं।
   ये आंतरिक रूप से स्ट्रीमिंग सपोर्ट के साथ `prompt()` को कॉल करते हैं।
   प्रॉम्प्टक्लाइंट में कोई बदलाव आवश्यक नहीं है।

   मॉड्यूल: `trustgraph-base/trustgraph/base/prompt_client.py`

2. **ग्राफआरएजी सेवा** (स्ट्रीमिंग पैरामीटर पास-थ्रू की आवश्यकता है)
   `query()` विधि में `streaming` पैरामीटर जोड़ें।
   `prompt_client.kg_prompt()` और कॉलबैक को `prompt_client.kg_prompt()` में पास करें।
   ग्राफआरैग रिक्वेस्ट स्कीमा में `streaming` फ़ील्ड की आवश्यकता है।

   मॉड्यूल:
   `trustgraph-flow/trustgraph/retrieval/graph_rag/graph_rag.py`
   `trustgraph-flow/trustgraph/retrieval/graph_rag/rag.py` (प्रोसेसर)
   `trustgraph-base/trustgraph/schema/graph_rag.py` (रिक्वेस्ट स्कीमा)
   `trustgraph-flow/trustgraph/gateway/dispatch/graph_rag.py` (गेटवे)

3. **डॉक्यूमेंटआरएजी सेवा** (स्ट्रीमिंग पैरामीटर पास-थ्रू की आवश्यकता है)
   `query()` विधि में `streaming` पैरामीटर जोड़ें।
   `prompt_client.document_prompt()` और कॉलबैक को `prompt_client.document_prompt()` में पास करें।
   डॉक्यूमेंटआरैग रिक्वेस्ट स्कीमा में `streaming` फ़ील्ड की आवश्यकता है।

   मॉड्यूल:
   `trustgraph-flow/trustgraph/retrieval/document_rag/document_rag.py`
   `trustgraph-flow/trustgraph/retrieval/document_rag/rag.py` (प्रोसेसर)
   `trustgraph-base/trustgraph/schema/document_rag.py` (रिक्वेस्ट स्कीमा)
   `trustgraph-flow/trustgraph/gateway/dispatch/document_rag.py` (गेटवे)

### डेटा फ्लो

**गैर-स्ट्रीमिंग (वर्तमान)**:
```
Client → Gateway → RAG Service → PromptClient.kg_prompt(streaming=False)
                                   ↓
                                Prompt Service → LLM
                                   ↓
                                Complete response
                                   ↓
Client ← Gateway ← RAG Service ←  Response
```

**स्ट्रीमिंग (प्रस्तावित):**
```
Client → Gateway → RAG Service → PromptClient.kg_prompt(streaming=True, chunk_callback=cb)
                                   ↓
                                Prompt Service → LLM (streaming)
                                   ↓
                                Chunk → callback → RAG Response (chunk)
                                   ↓                       ↓
Client ← Gateway ← ────────────────────────────────── Response stream
```

### एपीआई (APIs)

**ग्राफआरएजी (GraphRAG) में बदलाव**:

1. **GraphRag.query()** - स्ट्रीमिंग पैरामीटर जोड़े गए।
```python
async def query(
    self, query, user, collection,
    verbose=False, streaming=False, chunk_callback=None  # NEW
):
    # ... existing entity/triple retrieval ...

    if streaming and chunk_callback:
        resp = await self.prompt_client.kg_prompt(
            query, kg,
            streaming=True,
            chunk_callback=chunk_callback
        )
    else:
        resp = await self.prompt_client.kg_prompt(query, kg)

    return resp
```

2. **ग्राफराग रिक्वेस्ट स्कीमा** - स्ट्रीमिंग फ़ील्ड जोड़ें।
```python
class GraphRagRequest(Record):
    query = String()
    user = String()
    collection = String()
    streaming = Boolean()  # NEW
```

3. **ग्राफराग रिस्पांस स्कीमा** - स्ट्रीमिंग फ़ील्ड जोड़ें (एजेंट पैटर्न का पालन करें)।
```python
class GraphRagResponse(Record):
    response = String()    # Legacy: complete response
    chunk = String()       # NEW: streaming chunk
    end_of_stream = Boolean()  # NEW: indicates last chunk
```

4. **प्रोसेसर** - डेटा को लगातार प्रवाहित करें।
```python
async def handle(self, msg):
    # ... existing code ...

    async def send_chunk(chunk):
        await self.respond(GraphRagResponse(
            chunk=chunk,
            end_of_stream=False,
            response=None
        ))

    if request.streaming:
        full_response = await self.rag.query(
            query=request.query,
            user=request.user,
            collection=request.collection,
            streaming=True,
            chunk_callback=send_chunk
        )
        # Send final message
        await self.respond(GraphRagResponse(
            chunk=None,
            end_of_stream=True,
            response=full_response
        ))
    else:
        # Existing non-streaming path
        response = await self.rag.query(...)
        await self.respond(GraphRagResponse(response=response))
```

**डॉक्यूमेंटआरएजी में परिवर्तन**:

ग्राफआरएजी के समान पैटर्न:
1. `streaming` और `chunk_callback` पैरामीटर को `DocumentRag.query()` में जोड़ें।
2. `streaming` फ़ील्ड को `DocumentRagRequest` में जोड़ें।
3. `chunk` और `end_of_stream` फ़ील्ड को `DocumentRagResponse` में जोड़ें।
4. प्रोसेसर को कॉलबैक के साथ स्ट्रीमिंग को संभालने के लिए अपडेट करें।

**गेटवे में परिवर्तन**:

गेटवे/डिस्पैच में `graph_rag.py` और `document_rag.py` दोनों को वेबसॉकेट पर स्ट्रीमिंग चंक्स को अग्रेषित करने के लिए अपडेट की आवश्यकता है:

```python
async def handle(self, message, session, websocket):
    # ... existing code ...

    if request.streaming:
        async def recipient(resp):
            if resp.chunk:
                await websocket.send(json.dumps({
                    "id": message["id"],
                    "response": {"chunk": resp.chunk},
                    "complete": resp.end_of_stream
                }))
            return resp.end_of_stream

        await self.rag_client.request(request, recipient=recipient)
    else:
        # Existing non-streaming path
        resp = await self.rag_client.request(request)
        await websocket.send(...)
```

### कार्यान्वयन विवरण

**कार्यान्वयन क्रम**:
1. स्कीमा फ़ील्ड जोड़ें (RAG सेवाओं दोनों के लिए अनुरोध + प्रतिक्रिया)
2. GraphRag.query() और DocumentRag.query() विधियों को अपडेट करें
3. प्रोसेसर को स्ट्रीमिंग को संभालने के लिए अपडेट करें
4. गेटवे डिस्पैच हैंडलर को अपडेट करें
5. `--no-streaming` ध्वज `tg-invoke-graph-rag` और `tg-invoke-document-rag` में जोड़ें (डिफ़ॉल्ट रूप से स्ट्रीमिंग सक्षम, एजेंट CLI पैटर्न का अनुसरण करते हुए)

**कॉलबैक पैटर्न**:
एजेंट स्ट्रीमिंग में स्थापित समान एसिंक्रोनस कॉल बैक पैटर्न का पालन करें:
प्रोसेसर `async def send_chunk(chunk)` कॉल बैक को परिभाषित करता है
कॉल बैक को RAG सेवा को पास करता है
RAG सेवा कॉल बैक को PromptClient को पास करती है
PromptClient प्रत्येक LLM टुकड़े के लिए कॉल बैक को लागू करता है
प्रोसेसर प्रत्येक टुकड़े के लिए स्ट्रीमिंग प्रतिक्रिया संदेश भेजता है

**त्रुटि प्रबंधन**:
स्ट्रीमिंग के दौरान होने वाली त्रुटियों को `end_of_stream=True` के साथ त्रुटि प्रतिक्रिया भेजनी चाहिए
एजेंट स्ट्रीमिंग से मौजूदा त्रुटि प्रसार पैटर्न का पालन करें

## सुरक्षा संबंधी विचार

मौजूदा RAG सेवाओं से परे कोई नया सुरक्षा संबंधी विचार नहीं:
स्ट्रीमिंग प्रतिक्रियाएं समान उपयोगकर्ता/संग्रह अलगाव का उपयोग करती हैं
प्रमाणीकरण या प्राधिकरण में कोई बदलाव नहीं
टुकड़े की सीमाएं संवेदनशील डेटा को उजागर नहीं करती हैं

## प्रदर्शन संबंधी विचार

**लाभ**:
कथित विलंबता में कमी (पहले टोकन तेजी से आते हैं)
लंबे उत्तरों के लिए बेहतर UX
कम मेमोरी उपयोग (पूरे उत्तर को बफर करने की आवश्यकता नहीं है)

**संभावित चिंताएं**:
स्ट्रीमिंग प्रतिक्रियाओं के लिए अधिक Pulsar संदेश
टुकड़ा करने/कॉल बैक ओवरहेड के लिए थोड़ा अधिक CPU
स्ट्रीमिंग वैकल्पिक है, डिफ़ॉल्ट गैर-स्ट्रीमिंग रहता है, जिससे इसे कम किया जा सकता है

**परीक्षण संबंधी विचार**:
बड़ी नॉलेज ग्राफ (कई त्रिगुण) के साथ परीक्षण करें
कई पुनर्प्राप्त दस्तावेज़ों के साथ परीक्षण करें
स्ट्रीमिंग बनाम गैर-स्ट्रीमिंग के ओवरहेड को मापें

## परीक्षण रणनीति

**इकाई परीक्षण**:
streaming=True/False के साथ GraphRag.query() का परीक्षण करें
streaming=True/False के साथ DocumentRag.query() का परीक्षण करें
कॉल बैक कार्यान्वयन को सत्यापित करने के लिए PromptClient को मॉक करें

**एकीकरण परीक्षण**:
पूर्ण GraphRAG स्ट्रीमिंग प्रवाह का परीक्षण करें (मौजूदा एजेंट स्ट्रीमिंग परीक्षणों के समान)
पूर्ण DocumentRAG स्ट्रीमिंग प्रवाह का परीक्षण करें
गेटवे स्ट्रीमिंग अग्रेषण का परीक्षण करें
CLI स्ट्रीमिंग आउटपुट का परीक्षण करें

**मैन्युअल परीक्षण**:
`tg-invoke-graph-rag -q "What is machine learning?"` (डिफ़ॉल्ट रूप से स्ट्रीमिंग)
`tg-invoke-document-rag -q "Summarize the documents about AI"` (डिफ़ॉल्ट रूप से स्ट्रीमिंग)
`tg-invoke-graph-rag --no-streaming -q "..."` (गैर-स्ट्रीमिंग मोड का परीक्षण करें)
सत्यापित करें कि स्ट्रीमिंग मोड में वृद्धिशील आउटपुट दिखाई दे रहा है

## माइग्रेशन योजना

माइग्रेशन की आवश्यकता नहीं:
`streaming` पैरामीटर (डिफ़ॉल्ट रूप से False) के माध्यम से स्ट्रीमिंग वैकल्पिक है
मौजूदा क्लाइंट अपरिवर्तित रहते हैं
नए क्लाइंट स्ट्रीमिंग को अपना सकते हैं

## समयरेखा

अनुमानित कार्यान्वयन: 4-6 घंटे
चरण 1 (2 घंटे): GraphRAG स्ट्रीमिंग समर्थन
चरण 2 (2 घंटे): DocumentRAG स्ट्रीमिंग समर्थन
चरण 3 (1-2 घंटे): गेटवे अपडेट और CLI ध्वज
परीक्षण: प्रत्येक चरण में शामिल

## खुले प्रश्न

क्या हमें NLP क्वेरी सेवा में भी स्ट्रीमिंग समर्थन जोड़ना चाहिए?
क्या हम केवल LLM आउटपुट या मध्यवर्ती चरणों (जैसे, "इकाइयों को पुनर्प्राप्त करना...", "ग्राफ को क्वेरी करना...") को स्ट्रीम करना चाहते हैं?
क्या GraphRAG/DocumentRAG प्रतिक्रियाओं में टुकड़े मेटाडेटा (जैसे, टुकड़े संख्या, कुल अपेक्षित) शामिल होना चाहिए?

## संदर्भ

मौजूदा कार्यान्वयन: `docs/tech-specs/streaming-llm-responses.md`
एजेंट स्ट्रीमिंग: `trustgraph-flow/trustgraph/agent/react/agent_manager.py`
PromptClient स्ट्रीमिंग: `trustgraph-base/trustgraph/base/prompt_client.py`
