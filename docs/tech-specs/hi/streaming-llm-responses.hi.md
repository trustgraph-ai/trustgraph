---
layout: default
title: "स्ट्रीमिंग एलएलएम प्रतिक्रियाओं के लिए तकनीकी विनिर्देश"
parent: "Hindi (Beta)"
---

# स्ट्रीमिंग एलएलएम प्रतिक्रियाओं के लिए तकनीकी विनिर्देश

> **Beta Translation:** This document was translated via Machine Learning and as such may not be 100% accurate. All non-English languages are currently classified as Beta.

## अवलोकन

यह विनिर्देश ट्रस्टग्राफ में एलएलएम प्रतिक्रियाओं के लिए स्ट्रीमिंग समर्थन के कार्यान्वयन का वर्णन करता है। स्ट्रीमिंग, उत्पन्न किए जा रहे टोकन को वास्तविक समय में वितरित करने की अनुमति देता है, बजाय कि पूरी प्रतिक्रिया उत्पन्न होने तक प्रतीक्षा करने के।
स्ट्रीमिंग, एलएलएम द्वारा उत्पन्न किए जा रहे टोकन को वास्तविक समय में वितरित करने की अनुमति देता है, बजाय कि पूरी प्रतिक्रिया उत्पन्न होने तक प्रतीक्षा करने के।
स्ट्रीमिंग, उत्पन्न किए जा रहे टोकन को वास्तविक समय में वितरित करने की अनुमति देता है, बजाय कि पूरी प्रतिक्रिया उत्पन्न होने तक प्रतीक्षा करने के।
स्ट्रीमिंग, उत्पन्न किए जा रहे टोकन को वास्तविक समय में वितरित करने की अनुमति देता है, बजाय कि पूरी प्रतिक्रिया उत्पन्न होने तक प्रतीक्षा करने के।

यह कार्यान्वयन निम्नलिखित उपयोग मामलों का समर्थन करता है:

1. **वास्तविक समय उपयोगकर्ता इंटरफेस**: उत्पन्न होने पर टोकन को UI में भेजें,
   जिससे तत्काल दृश्य प्रतिक्रिया प्रदान की जा सके।
2. **पहले टोकन के लिए कम समय**: उपयोगकर्ता तुरंत आउटपुट देखना शुरू करते हैं,
   पूर्ण पीढ़ी की प्रतीक्षा करने के बजाय।
3. **लंबी प्रतिक्रिया प्रबंधन**: बहुत लंबी आउटपुट को संभालें जो अन्यथा
   समय समाप्त हो सकते हैं या मेमोरी सीमा से अधिक हो सकते हैं।
4. **इंटरैक्टिव एप्लिकेशन**: उत्तरदायी चैट और एजेंट इंटरफेस को सक्षम करें।

## लक्ष्य

**पिछड़ा संगतता (Backward Compatibility)**: मौजूदा, गैर-स्ट्रीमिंग क्लाइंट बिना किसी बदलाव के काम करते रहते हैं।
  बिना किसी बदलाव के।
**संगत एपीआई डिज़ाइन (Consistent API Design)**: स्ट्रीमिंग और गैर-स्ट्रीमिंग दोनों समान स्कीमा पैटर्न का उपयोग करते हैं, जिसमें न्यूनतम विचलन होता है।
  होता है।
**प्रदाता लचीलापन (Provider Flexibility)**: जहां उपलब्ध हो, वहां स्ट्रीमिंग का समर्थन करें, और जहां उपलब्ध न हो, वहां सुचारू रूप से वापस आएं।
  वापस आएं।
**चरणबद्ध कार्यान्वयन (Phased Rollout)**: जोखिम को कम करने के लिए क्रमिक कार्यान्वयन।
**एंड-टू-एंड समर्थन (End-to-End Support)**: एलएलएम प्रदाता से लेकर क्लाइंट तक स्ट्रीमिंग, पल्सर, गेटवे एपीआई और पायथन एपीआई के माध्यम से एप्लिकेशन तक।
  एप्लिकेशन तक।

## पृष्ठभूमि (Background)

### वर्तमान आर्किटेक्चर (Current Architecture)

वर्तमान एलएलएम टेक्स्ट कंप्लीशन प्रवाह इस प्रकार काम करता है:

1. क्लाइंट `TextCompletionRequest` भेजता है जिसमें `system` और `prompt` फ़ील्ड होते हैं।
2. एलएलएम सेवा अनुरोध को संसाधित करती है और पूर्ण पीढ़ी की प्रतीक्षा करती है।
3. पूर्ण `response` स्ट्रिंग के साथ एक `TextCompletionResponse` वापस किया जाता है।

वर्तमान स्कीमा (`trustgraph-base/trustgraph/schema/services/llm.py`):

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

### वर्तमान सीमाएँ

**विलंबता (Latency)**: उपयोगकर्ताओं को किसी भी आउटपुट को देखने से पहले पूर्ण पीढ़ी के पूरा होने का इंतजार करना पड़ता है।
**समय-सीमा (Timeout) का जोखिम**: लंबी पीढ़ी क्लाइंट समय-सीमा सीमाओं से अधिक हो सकती है।
**खराब उपयोगकर्ता अनुभव (Poor UX)**: पीढ़ी के दौरान कोई प्रतिक्रिया नहीं होने से धीमेपन का आभास होता है।
**संसाधन उपयोग (Resource Usage)**: पूर्ण प्रतिक्रियाओं को मेमोरी में बफर किया जाना चाहिए।

यह विनिर्देश क्रमिक प्रतिक्रिया को सक्षम करके इन सीमाओं को संबोधित करता है, जबकि पूर्ण पश्च संगतता (backward compatibility) बनाए रखता है।


## तकनीकी डिज़ाइन

### चरण 1: बुनियादी ढांचा

चरण 1, स्ट्रीमिंग के लिए आधार तैयार करता है, जिसमें स्कीमा, एपीआई और सीएलआई टूल में संशोधन शामिल हैं।


#### स्कीमा परिवर्तन

##### एलएलएम स्कीमा (`trustgraph-base/trustgraph/schema/services/llm.py`)

**अनुरोध परिवर्तन:**

```python
class TextCompletionRequest(Record):
    system = String()
    prompt = String()
    streaming = Boolean()  # NEW: Default false for backward compatibility
```

`streaming`: जब `true`, तो स्ट्रीमिंग प्रतिक्रिया डिलीवरी का अनुरोध करता है।
डिफ़ॉल्ट: `false` (मौजूदा व्यवहार संरक्षित)।

**प्रतिक्रिया में परिवर्तन:**

```python
class TextCompletionResponse(Record):
    error = Error()
    response = String()
    in_token = Integer()
    out_token = Integer()
    model = String()
    end_of_stream = Boolean()  # NEW: Indicates final message
```

`end_of_stream`: जब `true`, तो यह दर्शाता है कि यह अंतिम (या एकमात्र) प्रतिक्रिया है।
गैर-स्ट्रीमिंग अनुरोधों के लिए: `end_of_stream=true` के साथ एकल प्रतिक्रिया।
स्ट्रीमिंग अनुरोधों के लिए: `end_of_stream=false` के साथ कई प्रतिक्रियाएँ,
  अंतिम प्रतिक्रिया को छोड़कर।

##### प्रॉम्प्ट स्कीमा (`trustgraph-base/trustgraph/schema/services/prompt.py`)

प्रॉम्प्ट सेवा टेक्स्ट कंप्लीशन को लपेटती है, इसलिए यह समान पैटर्न को प्रतिबिंबित करती है:

**अनुरोध परिवर्तन:**

```python
class PromptRequest(Record):
    id = String()
    terms = Map(String())
    streaming = Boolean()  # NEW: Default false
```

**प्रतिक्रिया में परिवर्तन:**

```python
class PromptResponse(Record):
    error = Error()
    text = String()
    object = String()
    end_of_stream = Boolean()  # NEW: Indicates final message
```

#### गेटवे एपीआई में बदलाव

गेटवे एपीआई को एचटीटीपी/वेबसोकेट क्लाइंट्स के लिए स्ट्रीमिंग क्षमताएं प्रदान करनी होंगी।

**रेस्ट एपीआई अपडेट:**

`POST /api/v1/text-completion`: अनुरोध बॉडी में `streaming` पैरामीटर स्वीकार करें
प्रतिक्रिया व्यवहार स्ट्रीमिंग फ़्लैग पर निर्भर करता है:
  `streaming=false`: एकल JSON प्रतिक्रिया (वर्तमान व्यवहार)
  `streaming=true`: सर्वर-सेंट इवेंट्स (एसएसई) स्ट्रीम या वेबसोकेट संदेश

**प्रतिक्रिया प्रारूप (स्ट्रीमिंग):**

प्रत्येक स्ट्रीम किए गए भाग में समान स्कीमा संरचना होती है:
```json
{
  "response": "partial text...",
  "end_of_stream": false,
  "model": "model-name"
}
```

अंतिम भाग:
```json
{
  "response": "final text chunk",
  "end_of_stream": true,
  "in_token": 150,
  "out_token": 500,
  "model": "model-name"
}
```

#### पायथन एपीआई में बदलाव

पायथन क्लाइंट एपीआई को स्ट्रीमिंग और नॉन-स्ट्रीमिंग दोनों मोड का समर्थन करना चाहिए
साथ ही पिछली अनुकूलता बनाए रखनी चाहिए।

**LlmClient अपडेट** (`trustgraph-base/trustgraph/clients/llm_client.py`):

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

**प्रॉम्प्टक्लाइंट अपडेट** (`trustgraph-base/trustgraph/base/prompt_client.py`):

`streaming` पैरामीटर और एसिंक्रोनस जेनरेटर संस्करण के साथ समान पैटर्न।

#### सीएलआई टूल में बदलाव

**tg-invoke-llm** (`trustgraph-cli/trustgraph/cli/invoke_llm.py`):

```
tg-invoke-llm [system] [prompt] [--no-streaming] [-u URL] [-f flow-id]
```

डिफ़ॉल्ट रूप से बेहतर इंटरैक्टिव यूएक्स के लिए स्ट्रीमिंग सक्षम है।
`--no-streaming` ध्वज स्ट्रीमिंग को अक्षम करता है।
जब स्ट्रीमिंग हो: आउटपुट टोकन को stdout पर तब भेजें जब वे आएं।
जब स्ट्रीमिंग न हो: पूर्ण प्रतिक्रिया की प्रतीक्षा करें, फिर आउटपुट करें।

**tg-invoke-prompt** (`trustgraph-cli/trustgraph/cli/invoke_prompt.py`):

```
tg-invoke-prompt [template-id] [var=value...] [--no-streaming] [-u URL] [-f flow-id]
```

`tg-invoke-llm` के समान पैटर्न।

#### एलएलएम सर्विस बेस क्लास में बदलाव

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

### चरण 2: वर्टेक्सएआई प्रूफ ऑफ कॉन्सेप्ट

चरण 2, सत्यापन के लिए एक ही प्रदाता (वर्टेक्सएआई) में स्ट्रीमिंग को लागू करता है और एंड-टू-एंड परीक्षण को सक्षम करता है।
बुनियादी ढांचे।

#### वर्टेक्सएआई कार्यान्वयन

**मॉड्यूल:** `trustgraph-vertexai/trustgraph/model/text_completion/vertexai/llm.py`

**परिवर्तन:**

1. `supports_streaming()` को `True` लौटाने के लिए ओवरराइड करें।
2. `generate_content_stream()` एसिंक्रोनस जेनरेटर को लागू करें।
3. जेमिनी और क्लाउड दोनों मॉडलों को संभालें (वर्टेक्सएआई एंथ्रोपिक एपीआई के माध्यम से)।

**जेमिनी स्ट्रीमिंग:**

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

**क्लाउड (वर्टेक्सएआई एंथ्रोपिक) स्ट्रीमिंग:**

```python
async def generate_content_stream(self, system, prompt, model, temperature):
    with self.anthropic_client.messages.stream(...) as stream:
        for text in stream.text_stream:
            yield LlmChunk(text=text)
    # Token counts from stream.get_final_message()
```

#### परीक्षण

स्ट्रीमिंग प्रतिक्रिया असेंबली के लिए यूनिट परीक्षण
वर्टेक्सएआई (जेमिनी और क्लाउड) के साथ एकीकरण परीक्षण
एंड-टू-एंड परीक्षण: CLI -> गेटवे -> पल्सर -> वर्टेक्सएआई -> बैक
पिछड़े संगतता परीक्षण: गैर-स्ट्रीमिंग अनुरोध अभी भी काम करते हैं

--

### चरण 3: सभी एलएलएम प्रदाता

चरण 3 सिस्टम में सभी एलएलएम प्रदाताओं के लिए स्ट्रीमिंग समर्थन का विस्तार करता है।

#### प्रदाता कार्यान्वयन स्थिति

प्रत्येक प्रदाता को या तो:
1. **पूर्ण स्ट्रीमिंग समर्थन**: `generate_content_stream()` को लागू करें
2. **संगतता मोड**: `end_of_stream` ध्वज को सही ढंग से संभालें
   (एकल प्रतिक्रिया लौटाएं जिसमें `end_of_stream=true` हो)

| प्रदाता | पैकेज | स्ट्रीमिंग समर्थन |
|----------|---------|-------------------|
| ओपनएआई | trustgraph-flow | पूर्ण (मूल स्ट्रीमिंग एपीआई) |
| क्लाउड/एंथ्रोपिक | trustgraph-flow | पूर्ण (मूल स्ट्रीमिंग एपीआई) |
| ओलामा | trustgraph-flow | पूर्ण (मूल स्ट्रीमिंग एपीआई) |
| कोहेर | trustgraph-flow | पूर्ण (मूल स्ट्रीमिंग एपीआई) |
| मिस्ट्रल | trustgraph-flow | पूर्ण (मूल स्ट्रीमिंग एपीआई) |
| एज़्योर ओपनएआई | trustgraph-flow | पूर्ण (मूल स्ट्रीमिंग एपीआई) |
| गूगल एआई स्टूडियो | trustgraph-flow | पूर्ण (मूल स्ट्रीमिंग एपीआई) |
| वर्टेक्सएआई | trustgraph-vertexai | पूर्ण (चरण 2) |
| बेडरोक | trustgraph-bedrock | पूर्ण (मूल स्ट्रीमिंग एपीआई) |
| एलएम स्टूडियो | trustgraph-flow | पूर्ण (ओपनएआई-संगत) |
| लैमाफाइल | trustgraph-flow | पूर्ण (ओपनएआई-संगत) |
| वीएलएलएम | trustgraph-flow | पूर्ण (ओपनएआई-संगत) |
| टीजीआई | trustgraph-flow | तय किया जाना है |
| एज़्योर | trustgraph-flow | तय किया जाना है |

#### कार्यान्वयन पैटर्न

ओपनएआई-संगत प्रदाताओं (ओपनएआई, एलएम स्टूडियो, लैमाफाइल, वीएलएलएम) के लिए:

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

### चरण 4: एजेंट एपीआई

चरण 4, एजेंट एपीआई तक स्ट्रीमिंग का विस्तार करता है। यह अधिक जटिल है क्योंकि
एजेंट एपीआई स्वभाव से ही मल्टी-मैसेज है (विचार → क्रिया → अवलोकन
→ दोहराव → अंतिम उत्तर)।

#### वर्तमान एजेंट स्कीमा

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

#### प्रस्तावित एजेंट स्कीमा में परिवर्तन

**परिवर्तन का अनुरोध:**

```python
class AgentRequest(Record):
    question = String()
    state = String()
    group = Array(String())
    history = Array(AgentStep())
    user = String()
    streaming = Boolean()  # NEW: Default false
```

**प्रतिक्रिया में परिवर्तन:**

एजेंट अपनी तर्क प्रक्रिया के दौरान कई प्रकार के आउटपुट उत्पन्न करता है:
विचार (तर्क)
क्रियाएं (उपकरण कॉल)
अवलोकन (उपकरण परिणाम)
उत्तर (अंतिम प्रतिक्रिया)
त्रुटियाँ

चूँकि `chunk_type` यह बताता है कि किस प्रकार की सामग्री भेजी जा रही है, इसलिए अलग-अलग
`answer`, `error`, `thought`, और `observation` फ़ील्ड को एक साथ मिलाया जा सकता है।
एक एकल `content` फ़ील्ड:

```python
class AgentResponse(Record):
    chunk_type = String()       # "thought", "action", "observation", "answer", "error"
    content = String()          # The actual content (interpretation depends on chunk_type)
    end_of_message = Boolean()  # Current thought/action/observation/answer is complete
    end_of_dialog = Boolean()   # Entire agent dialog is complete
```

**फ़ील्ड सिमेंटिक्स:**

`chunk_type`: यह इंगित करता है कि `content` फ़ील्ड में किस प्रकार की सामग्री है
  `"thought"`: एजेंट की तर्क/सोच
  `"action"`: उपयोग किए जा रहे टूल/क्रिया
  `"observation"`: टूल निष्पादन का परिणाम
  `"answer"`: उपयोगकर्ता के प्रश्न का अंतिम उत्तर
  `"error"`: त्रुटि संदेश

`content`: वास्तविक स्ट्रीम की सामग्री, जिसे `chunk_type` के आधार पर व्याख्यायित किया जाता है

`end_of_message`: जब `true`, तो वर्तमान चंक प्रकार पूरा हो गया है
  उदाहरण: वर्तमान विचार के लिए सभी टोकन भेजे जा चुके हैं
  यह क्लाइंट को यह जानने की अनुमति देता है कि अगले चरण पर कब जाना है

`end_of_dialog`: जब `true`, तो संपूर्ण एजेंट इंटरैक्शन पूरा हो गया है
  यह स्ट्रीम में अंतिम संदेश है

#### एजेंट स्ट्रीमिंग व्यवहार

जब `streaming=true`:

1. **विचार स्ट्रीमिंग:**
   `chunk_type="thought"`, `end_of_message=false` के साथ कई चंक
   अंतिम विचार चंक में `end_of_message=true` होता है
2. **एक्शन नोटिफिकेशन:**
   `chunk_type="action"`, `end_of_message=true` के साथ एक चंक
3. **अवलोकन:**
   `chunk_type="observation"` के साथ चंक(s), अंतिम में `end_of_message=true` होता है
4. **चरण 1-3 को दोहराएं** क्योंकि एजेंट तर्क करता है
5. **अंतिम उत्तर:**
   `chunk_type="answer"` जिसमें `content` में अंतिम प्रतिक्रिया है
   अंतिम चंक में `end_of_message=true`, `end_of_dialog=true` होता है

**उदाहरण स्ट्रीम अनुक्रम:**

```
{chunk_type: "thought", content: "I need to", end_of_message: false, end_of_dialog: false}
{chunk_type: "thought", content: " search for...", end_of_message: true, end_of_dialog: false}
{chunk_type: "action", content: "search", end_of_message: true, end_of_dialog: false}
{chunk_type: "observation", content: "Found: ...", end_of_message: true, end_of_dialog: false}
{chunk_type: "thought", content: "Based on this", end_of_message: false, end_of_dialog: false}
{chunk_type: "thought", content: " I can answer...", end_of_message: true, end_of_dialog: false}
{chunk_type: "answer", content: "The answer is...", end_of_message: true, end_of_dialog: true}
```

जब `streaming=false`:
वर्तमान व्यवहार संरक्षित
पूर्ण उत्तर के साथ एकल प्रतिक्रिया
`end_of_message=true`, `end_of_dialog=true`

#### गेटवे और पायथन एपीआई

गेटवे: एजेंट स्ट्रीमिंग के लिए नया एसएसई/वेबसोकेट एंडपॉइंट
पायथन एपीआई: नया `agent_stream()` एसिंक्रोनस जेनरेटर विधि

--

## सुरक्षा संबंधी विचार

**कोई नया आक्रमण सतह नहीं**: स्ट्रीमिंग समान प्रमाणीकरण/प्राधिकरण का उपयोग करती है
**दर सीमा**: यदि आवश्यक हो तो प्रति-टोकन या प्रति-खंड दर सीमा लागू करें
**कनेक्शन हैंडलिंग**: क्लाइंट डिस्कनेक्ट होने पर स्ट्रीम को ठीक से समाप्त करें
**टाइमआउट प्रबंधन**: स्ट्रीमिंग अनुरोधों के लिए उचित टाइमआउट हैंडलिंग की आवश्यकता होती है

## प्रदर्शन संबंधी विचार

**मेमोरी**: स्ट्रीमिंग से पीक मेमोरी उपयोग कम होता है (कोई पूर्ण प्रतिक्रिया बफरिंग नहीं)
**विलंबता**: पहले टोकन तक का समय काफी कम हो जाता है
**कनेक्शन ओवरहेड**: एसएसई/वेबसोकेट कनेक्शन में कीप-अलाइव ओवरहेड होता है
**पल्सर थ्रूपुट**: एक बड़े संदेश के मुकाबले कई छोटे संदेशों का व्यापार
  ट्रेडऑफ़

## परीक्षण रणनीति

### यूनिट टेस्ट
नए फ़ील्ड के साथ स्कीमा सीरियलाइज़ेशन/डीसेरियलाइज़ेशन
पिछड़ा संगतता (गायब फ़ील्ड डिफ़ॉल्ट का उपयोग करते हैं)
चंक असेंबली लॉजिक

### एकीकरण परीक्षण
प्रत्येक एलएलएम प्रदाता का स्ट्रीमिंग कार्यान्वयन
गेटवे एपीआई स्ट्रीमिंग एंडपॉइंट
पायथन क्लाइंट स्ट्रीमिंग विधियाँ

### एंड-टू-एंड टेस्ट
सीएलआई टूल स्ट्रीमिंग आउटपुट
पूर्ण प्रवाह: क्लाइंट → गेटवे → पल्सर → एलएलएम → वापस
मिश्रित स्ट्रीमिंग/गैर-स्ट्रीमिंग वर्कलोड

### पिछड़ा संगतता परीक्षण
मौजूदा क्लाइंट बिना किसी संशोधन के काम करते हैं
गैर-स्ट्रीमिंग अनुरोध समान रूप से व्यवहार करते हैं

## माइग्रेशन योजना

### चरण 1: बुनियादी ढांचा
स्कीमा परिवर्तन तैनात करें (पिछड़ा संगत)
गेटवे एपीआई अपडेट तैनात करें
पायथन एपीआई अपडेट तैनात करें
सीएलआई टूल अपडेट जारी करें

### चरण 2: वर्टेक्सएआई
वर्टेक्सएआई स्ट्रीमिंग कार्यान्वयन को तैनात करें।
परीक्षण वर्कलोड के साथ सत्यापन करें।

### चरण 3: सभी प्रदाता
प्रदाता अपडेट को धीरे-धीरे लागू करें।
समस्याओं की निगरानी करें।

### चरण 4: एजेंट एपीआई
एजेंट स्कीमा परिवर्तनों को तैनात करें।
एजेंट स्ट्रीमिंग कार्यान्वयन को तैनात करें।
दस्तावेज़ को अपडेट करें।

## समयरेखा

| चरण | विवरण | निर्भरताएँ |
|-------|-------------|--------------|
| चरण 1 | बुनियादी ढांचा | कोई नहीं |
| चरण 2 | वर्टेक्सएआई प्रूफ ऑफ कॉन्सेप्ट | चरण 1 |
| चरण 3 | सभी प्रदाता | चरण 2 |
| चरण 4 | एजेंट एपीआई | चरण 3 |

## डिज़ाइन निर्णय

निम्नलिखित प्रश्नों को विनिर्देश के दौरान हल किया गया था:

1. **स्ट्रीमिंग में टोकन गणना**: टोकन गणनाएँ अंतर हैं, न कि चल रही कुल।
   उपभोक्ता आवश्यकतानुसार उन्हें जोड़ सकते हैं। यह अधिकांश प्रदाता द्वारा उपयोग की रिपोर्टिंग के तरीके से मेल खाता है
   और कार्यान्वयन को सरल बनाता है।

2. **स्ट्रीम में त्रुटि प्रबंधन**: यदि कोई त्रुटि होती है, तो `error` फ़ील्ड भरा जाता है और अन्य फ़ील्ड की आवश्यकता नहीं होती है। त्रुटि हमेशा अंतिम संचार होती है - इसके बाद कोई अन्य संदेश अनुमत या अपेक्षित नहीं हैं।
   2. **स्ट्रीम में त्रुटि प्रबंधन**: यदि कोई त्रुटि होती है, तो ⟦CODE_0⟧ फ़ील्ड भरा जाता है और अन्य फ़ील्ड की आवश्यकता नहीं होती है। त्रुटि हमेशा अंतिम संचार होती है - इसके बाद कोई अन्य संदेश अनुमत या अपेक्षित नहीं हैं।
   2. **स्ट्रीम में त्रुटि प्रबंधन**: यदि कोई त्रुटि होती है, तो ⟦CODE_0⟧ फ़ील्ड भरा जाता है और अन्य फ़ील्ड की आवश्यकता नहीं होती है। त्रुटि हमेशा अंतिम संचार होती है - इसके बाद कोई अन्य संदेश अनुमत या अपेक्षित नहीं हैं।
   एक त्रुटि। एलएलएम/प्रॉम्प्ट स्ट्रीम के लिए, `end_of_stream=true`। एजेंट स्ट्रीम के लिए,
   `chunk_type="error"` को `end_of_dialog=true` के साथ।

3. **आंशिक प्रतिक्रिया पुनर्प्राप्ति**: संदेश प्रोटोकॉल (पल्सर) मजबूत है,
   इसलिए संदेश-स्तर पर पुनः प्रयास की आवश्यकता नहीं है। यदि कोई क्लाइंट स्ट्रीम को खो देता है
   या डिस्कनेक्ट हो जाता है, तो उसे पूरी अनुरोध को शुरुआत से फिर से प्रयास करना होगा।

4. **त्वरित सेवा स्ट्रीमिंग**: स्ट्रीमिंग केवल टेक्स्ट (`text`) के लिए समर्थित है।
   प्रतिक्रियाओं के लिए, संरचित (`object`) प्रतिक्रियाओं के लिए नहीं। त्वरित सेवा पहले से ही जानती है कि
   आउटपुट JSON होगा या टेक्स्ट-आधारित, यह प्रॉम्प्ट टेम्पलेट पर निर्भर करता है। यदि JSON-आउटपुट प्रॉम्प्ट के लिए
   एक स्ट्रीमिंग अनुरोध किया जाता है, तो
   सेवा को या तो:
   `end_of_stream=true` के साथ एक ही प्रतिक्रिया में पूरा JSON वापस करना चाहिए, या
   त्रुटि के साथ स्ट्रीमिंग अनुरोध को अस्वीकार करना चाहिए

## खुले प्रश्न

फिलहाल कोई नहीं।

## संदर्भ

वर्तमान एलएलएम स्कीमा: `trustgraph-base/trustgraph/schema/services/llm.py`
वर्तमान प्रॉम्प्ट स्कीमा: `trustgraph-base/trustgraph/schema/services/prompt.py`
वर्तमान एजेंट स्कीमा: `trustgraph-base/trustgraph/schema/services/agent.py`
एलएलएम सेवा आधार: `trustgraph-base/trustgraph/base/llm_service.py`
वर्टेक्सएआई प्रदाता: `trustgraph-vertexai/trustgraph/model/text_completion/vertexai/llm.py`
गेटवे एपीआई: `trustgraph-base/trustgraph/api/`
सीएलआई उपकरण: `trustgraph-cli/trustgraph/cli/`
