# टूल सेवाएं: गतिशील रूप से प्लगेबल एजेंट टूल

## स्थिति

कार्यान्वित

## अवलोकन

यह विनिर्देश "टूल सेवाओं" नामक गतिशील रूप से प्लगेबल एजेंट टूल के लिए एक तंत्र को परिभाषित करता है। मौजूदा अंतर्निहित टूल प्रकारों (`KnowledgeQueryImpl`, `McpToolImpl`, आदि) के विपरीत, टूल सेवाएं नए टूल को इस प्रकार पेश करने की अनुमति देती हैं:

1. एक नई पल्सर-आधारित सेवा को तैनात करना
2. एक कॉन्फ़िगरेशन विवरण जोड़ना जो एजेंट को बताता है कि इसे कैसे कॉल करना है

यह मुख्य एजेंट-रिएक्ट फ्रेमवर्क को संशोधित किए बिना विस्तारशीलता को सक्षम बनाता है।

## शब्दावली

| शब्द | परिभाषा |
|------|------------|
| **अंतर्निहित टूल** | `tools.py` में हार्डकोडेड कार्यान्वयन वाले मौजूदा टूल प्रकार
| **टूल सेवा** | एक पल्सर सेवा जिसे एजेंट टूल के रूप में कॉल किया जा सकता है, जिसे एक सेवा विवरण द्वारा परिभाषित किया गया है
| **टूल** | एक कॉन्फ़िगर किया गया उदाहरण जो एक टूल सेवा को संदर्भित करता है, जो एजेंट/एलएलएम को उजागर किया जाता है

यह एक दो-स्तरीय मॉडल है, जो एमसीपी टूल के समान है:
एमसीपी: एमसीपी सर्वर टूल इंटरफ़ेस को परिभाषित करता है → टूल कॉन्फ़िगरेशन इसका संदर्भ देता है
टूल सेवाएं: टूल सेवा पल्सर इंटरफ़ेस को परिभाषित करती है → टूल कॉन्फ़िगरेशन इसका संदर्भ देता है

## पृष्ठभूमि: मौजूदा टूल

### अंतर्निहित टूल कार्यान्वयन

टूल वर्तमान में `trustgraph-flow/trustgraph/agent/react/tools.py` में टाइप किए गए कार्यान्वयन के साथ परिभाषित किए गए हैं:

```python
class KnowledgeQueryImpl:
    async def invoke(self, question):
        client = self.context("graph-rag-request")
        return await client.rag(question, self.collection)
```

प्रत्येक उपकरण प्रकार:
में एक हार्डकोडेड पल्सर सेवा होती है जिसे वह कॉल करता है (उदाहरण के लिए, `graph-rag-request`)
वह क्लाइंट पर कॉल करने के लिए सटीक विधि जानता है (उदाहरण के लिए, `client.rag()`)
इसमें कार्यान्वयन में परिभाषित टाइप किए गए तर्क होते हैं

### उपकरण पंजीकरण (service.py:105-214)

उपकरण कॉन्फ़िगरेशन से लोड किए जाते हैं जिसमें एक `type` फ़ील्ड होता है जो एक कार्यान्वयन से मेल खाता है:

```python
if impl_id == "knowledge-query":
    impl = functools.partial(KnowledgeQueryImpl, collection=data.get("collection"))
elif impl_id == "text-completion":
    impl = TextCompletionImpl
# ... etc
```

## आर्किटेक्चर

### दो-स्तरीय मॉडल

#### स्तर 1: टूल सर्विस डिस्क्रिप्टर

एक टूल सर्विस, पल्सर सर्विस इंटरफेस को परिभाषित करता है। यह निम्नलिखित घोषित करता है:
अनुरोध/प्रतिक्रिया के लिए पल्सर क्यू
उन कॉन्फ़िगरेशन पैरामीटर जिन्हें इसका उपयोग करने वाले टूल से इसकी आवश्यकता होती है

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

एक उपकरण सेवा जिसे किसी भी कॉन्फ़िगरेशन पैरामीटर की आवश्यकता नहीं है:

```json
{
  "id": "calculator",
  "request-queue": "non-persistent://tg/request/calc",
  "response-queue": "non-persistent://tg/response/calc",
  "config-params": []
}
```

#### स्तर 2: टूल विवरणिका

एक टूल एक टूल सेवा को संदर्भित करता है और निम्नलिखित प्रदान करता है:
कॉन्फ़िगरेशन पैरामीटर मान (सेवा की आवश्यकताओं को पूरा करते हुए)
एजेंट के लिए टूल मेटाडेटा (नाम, विवरण)
एलएलएम के लिए तर्क परिभाषाएँ

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

कई उपकरण एक ही सेवा को विभिन्न कॉन्फ़िगरेशन के साथ संदर्भित कर सकते हैं:

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

### अनुरोध प्रारूप

जब कोई टूल सक्रिय किया जाता है, तो टूल सेवा को भेजा गया अनुरोध में शामिल होता है:
`user`: एजेंट अनुरोध से (मल्टी-टेनेंसी)
`config`: टूल विवरणिका से JSON-एन्कोडेड कॉन्फ़िगरेशन मान
`arguments`: LLM से JSON-एन्कोडेड तर्क

```json
{
  "user": "alice",
  "config": "{\"collection\": \"customers\"}",
  "arguments": "{\"question\": \"What are the top customer complaints?\"}"
}
```

टूल सर्विस इन डेटा को पार्स किए गए डिक्शनरी के रूप में `invoke` मेथड में प्राप्त करती है।

### सामान्य टूल सर्विस कार्यान्वयन

एक `ToolServiceImpl` क्लास कॉन्फ़िगरेशन के आधार पर टूल सेवाओं को लागू करता है:

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

## डिज़ाइन निर्णय

### दो-स्तरीय कॉन्फ़िगरेशन मॉडल

टूल सेवाएं एमसीपी टूल के समान एक दो-स्तरीय मॉडल का पालन करती हैं:

1. **टूल सेवा**: पल्सर सेवा इंटरफ़ेस को परिभाषित करती है (विषय, आवश्यक कॉन्फ़िगरेशन पैरामीटर)
2. **टूल**: एक टूल सेवा को संदर्भित करता है, कॉन्फ़िगरेशन मान प्रदान करता है, एलएलएम तर्क को परिभाषित करता है

यह अलगाव अनुमति देता है:
एक टूल सेवा का उपयोग विभिन्न कॉन्फ़िगरेशन वाले कई टूल द्वारा किया जा सकता है
सेवा इंटरफ़ेस और टूल कॉन्फ़िगरेशन के बीच स्पष्ट अंतर
सेवा परिभाषाओं का पुन: उपयोग

### अनुरोध मैपिंग: एन्वेलप के साथ पास-थ्रू

एक टूल सेवा के लिए अनुरोध एक संरचित एन्वेलप होता है जिसमें शामिल हैं:
`user`: मल्टी-टेनेंसी के लिए एजेंट अनुरोध से प्रचारित
कॉन्फ़िगरेशन मान: टूल विवरणिका से (उदाहरण के लिए, `collection`)
`arguments`: एलएलएम-प्रदत्त तर्क, एक डिक्ट के रूप में पास किए जाते हैं

एजेंट प्रबंधक एलएलएम की प्रतिक्रिया को `act.arguments` के रूप में एक डिक्ट (`agent_manager.py:117-154`) में पार्स करता है। यह डिक्ट अनुरोध एन्वेलप में शामिल है।

### स्कीमा हैंडलिंग: अनटाइप्ड

अनुरोध और प्रतिक्रियाएं अनटाइप्ड डिक्ट का उपयोग करती हैं। एजेंट स्तर पर कोई स्कीमा सत्यापन नहीं होता है - टूल सेवा अपने इनपुट को मान्य करने के लिए जिम्मेदार है। यह नई सेवाओं को परिभाषित करने के लिए अधिकतम लचीलापन प्रदान करता है।

### क्लाइंट इंटरफ़ेस: डायरेक्ट पल्सर टॉपिक

टूल सेवाएं प्रवाह कॉन्फ़िगरेशन की आवश्यकता के बिना डायरेक्ट पल्सर टॉपिक का उपयोग करती हैं। टूल-सेवा विवरणिका पूर्ण कतार नामों को निर्दिष्ट करती है:

```json
{
  "id": "joke-service",
  "request-queue": "non-persistent://tg/request/joke",
  "response-queue": "non-persistent://tg/response/joke",
  "config-params": [...]
}
```

यह सेवाओं को किसी भी नेमस्पेस में होस्ट करने की अनुमति देता है।

### त्रुटि प्रबंधन: मानक त्रुटि सम्मेलन

टूल सेवा प्रतिक्रियाएं मौजूदा स्कीमा सम्मेलन का पालन करती हैं, जिसमें एक `error` फ़ील्ड है:

```python
@dataclass
class Error:
    type: str = ""
    message: str = ""
```

प्रतिक्रिया संरचना:
सफलता: `error` का मान `None` है, प्रतिक्रिया में परिणाम शामिल है
त्रुटि: `error` को `type` और `message` के मानों के साथ भरा जाता है

यह मौजूदा सेवा स्कीमा में उपयोग किए गए पैटर्न से मेल खाता है (उदाहरण के लिए, `PromptResponse`, `QueryResponse`, `AgentResponse`)।

### अनुरोध/प्रतिक्रिया सहसंबंध

अनुरोधों और प्रतिक्रियाओं को पल्सर संदेश गुणों में एक `id` का उपयोग करके सहसंबंधित किया जाता है:

अनुरोध में गुणों में `id` शामिल है: `properties={"id": id}`
प्रतिक्रिया(ओं) में समान `id` शामिल है: `properties={"id": id}`

यह पूरे कोडबेस में उपयोग किए गए मौजूदा पैटर्न का अनुसरण करता है (उदाहरण के लिए, `agent_service.py`, `llm_service.py`)।

### स्ट्रीमिंग समर्थन

टूल सेवाएं स्ट्रीमिंग प्रतिक्रियाएं वापस कर सकती हैं:

समान `id` वाले कई प्रतिक्रिया संदेश
प्रत्येक प्रतिक्रिया में `end_of_stream: bool` फ़ील्ड शामिल है
अंतिम प्रतिक्रिया में `end_of_stream: True` है

यह `AgentResponse` और अन्य स्ट्रीमिंग सेवाओं में उपयोग किए गए पैटर्न से मेल खाता है।

### प्रतिक्रिया हैंडलिंग: स्ट्रिंग रिटर्न

सभी मौजूदा टूल समान पैटर्न का पालन करते हैं: **तर्कों को एक डिक्ट के रूप में प्राप्त करें, अवलोकन को एक स्ट्रिंग के रूप में वापस करें।**

| टूल | प्रतिक्रिया हैंडलिंग |
|------|------------------|
| `KnowledgeQueryImpl` | `client.rag()` को सीधे वापस करता है (स्ट्रिंग) |
| `TextCompletionImpl` | `client.question()` को सीधे वापस करता है (स्ट्रिंग) |
| `McpToolImpl` | एक स्ट्रिंग वापस करता है, या यदि स्ट्रिंग नहीं है तो `json.dumps(output)` |
| `StructuredQueryImpl` | परिणाम को स्ट्रिंग में प्रारूपित करता है |
| `PromptImpl` | `client.prompt()` को सीधे वापस करता है (स्ट्रिंग) |

टूल सेवाएं समान अनुबंध का पालन करती हैं:
सेवा एक स्ट्रिंग प्रतिक्रिया (अवलोकन) वापस करती है
यदि प्रतिक्रिया एक स्ट्रिंग नहीं है, तो इसे `json.dumps()` के माध्यम से परिवर्तित किया जाता है
वर्णनकर्ता में किसी निष्कर्षण कॉन्फ़िगरेशन की आवश्यकता नहीं है

यह वर्णनकर्ता को सरल रखता है और सेवा पर एजेंट के लिए एक उपयुक्त पाठ प्रतिक्रिया वापस करने की जिम्मेदारी डालता है।

## कॉन्फ़िगरेशन गाइड

एक नई टूल सेवा जोड़ने के लिए, दो कॉन्फ़िगरेशन आइटम की आवश्यकता होती है:

### 1. टूल सेवा कॉन्फ़िगरेशन

`tool-service` कॉन्फ़िगरेशन कुंजी के अंतर्गत संग्रहीत। पल्सर कतारों और उपलब्ध कॉन्फ़िगरेशन मापदंडों को परिभाषित करता है।

| फ़ील्ड | आवश्यक | विवरण |
|-------|----------|-------------|
| `id` | हाँ | टूल सेवा के लिए अद्वितीय पहचानकर्ता |
| `request-queue` | हाँ | अनुरोधों के लिए पूर्ण पल्सर विषय (उदाहरण के लिए, `non-persistent://tg/request/joke`) |
| `response-queue` | हाँ | प्रतिक्रियाओं के लिए पूर्ण पल्सर विषय (उदाहरण के लिए, `non-persistent://tg/response/joke`) |
| `config-params` | नहीं | सेवा द्वारा स्वीकार किए जाने वाले कॉन्फ़िगरेशन मापदंडों की सरणी |

प्रत्येक कॉन्फ़िगरेशन पैरामीटर में निम्नलिखित निर्दिष्ट किया जा सकता है:
`name`: पैरामीटर नाम (आवश्यक)
`required`: क्या पैरामीटर को टूल द्वारा प्रदान किया जाना चाहिए (डिफ़ॉल्ट: झूठा)

उदाहरण:
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

### 2. टूल कॉन्फ़िगरेशन

`tool` कुंजी के अंतर्गत संग्रहीत। यह एक ऐसा टूल परिभाषित करता है जिसका उपयोग एजेंट कर सकता है।

| फ़ील्ड | आवश्यक | विवरण |
|-------|----------|-------------|
| `type` | हाँ | यह `"tool-service"` होना चाहिए |
| `name` | हाँ | एलएलएम को प्रदर्शित होने वाला टूल नाम |
| `description` | हाँ | टूल क्या करता है इसका विवरण (एलएलएम को दिखाया जाता है) |
| `service` | हाँ | टूल-सर्विस का आईडी जिसे कॉल किया जाना है |
| `arguments` | नहीं | एलएलएम के लिए तर्क परिभाषाओं का सरणी |
| *(कॉन्फ़िगरेशन पैरामीटर)* | भिन्न | सेवा द्वारा परिभाषित कोई भी कॉन्फ़िगरेशन पैरामीटर |

प्रत्येक तर्क में निम्नलिखित निर्दिष्ट किया जा सकता है:
`name`: तर्क का नाम (आवश्यक)
`type`: डेटा प्रकार, उदाहरण के लिए, `"string"` (आवश्यक)
`description`: एलएलएम को दिखाया जाने वाला विवरण (आवश्यक)

उदाहरण:
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

### कॉन्फ़िगरेशन लोड करना

कॉन्फ़िगरेशन लोड करने के लिए `tg-put-config-item` का उपयोग करें:

```bash
# Load tool-service config
tg-put-config-item tool-service/joke-service < joke-service.json

# Load tool config
tg-put-config-item tool/tell-joke < tell-joke.json
```

एजेंट-मैनेजर को नए कॉन्फ़िगरेशन को लागू करने के लिए पुनरारंभ किया जाना चाहिए।

## कार्यान्वयन विवरण

### स्कीमा

`trustgraph-base/trustgraph/schema/services/tool_service.py` में अनुरोध और प्रतिक्रिया प्रकार:

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

### सर्वर-साइड: डायनामिकटूलसर्विस

`trustgraph-base/trustgraph/base/dynamic_tool_service.py` में बेस क्लास:

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

### क्लाइंट-साइड: ToolServiceImpl

`trustgraph-flow/trustgraph/agent/react/tools.py` में कार्यान्वयन:

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

### फ़ाइलें

| फ़ाइल | उद्देश्य |
|------|---------|
| `trustgraph-base/trustgraph/schema/services/tool_service.py` | अनुरोध/प्रतिक्रिया स्कीमा |
| `trustgraph-base/trustgraph/base/tool_service_client.py` | सेवाओं को आमंत्रित करने के लिए क्लाइंट |
| `trustgraph-base/trustgraph/base/dynamic_tool_service.py` | सेवा कार्यान्वयन के लिए आधार वर्ग |
| `trustgraph-flow/trustgraph/agent/react/tools.py` | `ToolServiceImpl` वर्ग |
| `trustgraph-flow/trustgraph/agent/react/service.py` | कॉन्फ़िगरेशन लोडिंग |

### उदाहरण: जोक सर्विस

`trustgraph-flow/trustgraph/tool_service/joke/` में एक उदाहरण सेवा:

```python
class Processor(DynamicToolService):
    async def invoke(self, user, config, arguments):
        style = config.get("style", "pun")
        topic = arguments.get("topic", "")
        joke = pick_joke(topic, style)
        return f"Hey {user}! Here's a {style} for you:\n\n{joke}"
```

टूल सर्विस कॉन्फ़िगरेशन:
```json
{
  "id": "joke-service",
  "request-queue": "non-persistent://tg/request/joke",
  "response-queue": "non-persistent://tg/response/joke",
  "config-params": [{"name": "style", "required": false}]
}
```

टूल कॉन्फ़िगरेशन:
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

### पिछली अनुकूलता (पिछड़ी संगतता)

मौजूदा अंतर्निहित टूल प्रकार बिना किसी बदलाव के काम करना जारी रखते हैं।
`tool-service` एक नया टूल प्रकार है जो मौजूदा प्रकारों (`knowledge-query`, `mcp-tool`, आदि) के साथ है।

## भविष्य के विचार

### स्व-घोषणा करने वाली सेवाएं

एक भविष्य का सुधार सेवाओं को अपने स्वयं के विवरण प्रकाशित करने की अनुमति दे सकता है:

सेवाएं स्टार्टअप पर एक ज्ञात `tool-descriptors` विषय पर प्रकाशित करती हैं।
एजेंट सदस्यता लेता है और गतिशील रूप से टूल पंजीकृत करता है।
यह वास्तविक प्लग-एंड-प्ले को कॉन्फ़िगरेशन परिवर्तनों के बिना सक्षम बनाता है।

यह प्रारंभिक कार्यान्वयन के दायरे से बाहर है।

## संदर्भ

वर्तमान टूल कार्यान्वयन: `trustgraph-flow/trustgraph/agent/react/tools.py`
टूल पंजीकरण: `trustgraph-flow/trustgraph/agent/react/service.py:105-214`
एजेंट स्कीमा: `trustgraph-base/trustgraph/schema/services/agent.py`
