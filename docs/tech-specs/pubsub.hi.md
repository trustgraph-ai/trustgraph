# पब/सब इंफ्रास्ट्रक्चर

## अवलोकन

यह दस्तावेज़ ट्रस्टग्राफ कोडबेस और पब/सब इंफ्रास्ट्रक्चर के बीच सभी कनेक्शनों को सूचीबद्ध करता है। वर्तमान में, सिस्टम को अपाचे पल्सर का उपयोग करने के लिए हार्डकोड किया गया है। यह विश्लेषण सभी एकीकरण बिंदुओं की पहचान करता है ताकि एक कॉन्फ़िगर करने योग्य पब/सब एब्स्ट्रैक्शन की ओर भविष्य के रीफैक्टरिंग को सूचित किया जा सके।

## वर्तमान स्थिति: पल्सर एकीकरण बिंदु

### 1. डायरेक्ट पल्सर क्लाइंट उपयोग

**स्थान:** `trustgraph-flow/trustgraph/gateway/service.py`

एपीआई गेटवे सीधे पल्सर क्लाइंट को आयात और इंस्टेंट करता है:

**पंक्ति 20:** `import pulsar`
**पंक्तियाँ 54-61:** `pulsar.Client()` का प्रत्यक्ष इंस्टेंटेशन, वैकल्पिक `pulsar.AuthenticationToken()` के साथ
**पंक्तियाँ 33-35:** पर्यावरण चर से डिफ़ॉल्ट पल्सर होस्ट कॉन्फ़िगरेशन
**पंक्तियाँ 178-192:** `--pulsar-host`, `--pulsar-api-key` और `--pulsar-listener` के लिए CLI तर्क
**पंक्तियाँ 78, 124:** `pulsar_client` को `ConfigReceiver` और `DispatcherManager` को पास करता है

यह एकमात्र स्थान है जहां पल्सर क्लाइंट को एब्स्ट्रैक्शन लेयर के बाहर सीधे इंस्टेंट किया गया है।

### 2. बेस प्रोसेसर फ्रेमवर्क

**स्थान:** `trustgraph-base/trustgraph/base/async_processor.py`

सभी प्रोसेसर के लिए बेस क्लास पल्सर कनेक्टिविटी प्रदान करता है:

**पंक्ति 9:** `import _pulsar` (अपवाद हैंडलिंग के लिए)
**पंक्ति 18:** `from . pubsub import PulsarClient`
**पंक्ति 38:** `pulsar_client_object = PulsarClient(**params)` बनाता है
**पंक्तियाँ 104-108:** गुण जो `pulsar_host` और `pulsar_client` को उजागर करते हैं
**पंक्ति 250:** स्थैतिक विधि `add_args()` CLI तर्कों के लिए `PulsarClient.add_args(parser)` को कॉल करता है
**पंक्तियाँ 223-225:** `_pulsar.Interrupted` के लिए अपवाद हैंडलिंग

सभी प्रोसेसर `AsyncProcessor` से इनहेरिट करते हैं, जिससे यह केंद्रीय एकीकरण बिंदु बन जाता है।

### 3. उपभोक्ता एब्स्ट्रैक्शन

**स्थान:** `trustgraph-base/trustgraph/base/consumer.py`

यह कतारों से संदेशों का उपभोग करता है और हैंडलर फ़ंक्शन को लागू करता है:

**पल्सर आयात:**
**पंक्ति 12:** `from pulsar.schema import JsonSchema`
**पंक्ति 13:** `import pulsar`
**पंक्ति 14:** `import _pulsar`

**पल्सर-विशिष्ट उपयोग:**
**पंक्तियाँ 100, 102:** `pulsar.InitialPosition.Earliest` / `pulsar.InitialPosition.Latest`
**पंक्ति 108:** `JsonSchema(self.schema)` रैपर
**पंक्ति 110:** `pulsar.ConsumerType.Shared`
**पंक्तियाँ 104-111:** पल्सर-विशिष्ट मापदंडों के साथ `self.client.subscribe()`
**पंक्तियाँ 143, 150, 65:** `consumer.unsubscribe()` और `consumer.close()` विधियाँ
**पंक्ति 162:** `_pulsar.Timeout` अपवाद
**पंक्तियाँ 182, 205, 232:** `consumer.acknowledge()` / `consumer.negative_acknowledge()`

**स्पेक फ़ाइल:** `trustgraph-base/trustgraph/base/consumer_spec.py`
**पंक्ति 22:** `processor.pulsar_client` को संदर्भित करता है

### 4. उत्पादक एब्स्ट्रैक्शन

**स्थान:** `trustgraph-base/trustgraph/base/producer.py`

यह कतारों में संदेश भेजता है:

**पल्सर आयात:**
**पंक्ति 2:** `from pulsar.schema import JsonSchema`

**पल्सर-विशिष्ट उपयोग:**
**पंक्ति 49:** `JsonSchema(self.schema)` रैपर
**पंक्तियाँ 47-51:** पल्सर-विशिष्ट मापदंडों (विषय, स्कीमा, चंकिंग_सक्षम) के साथ `self.client.create_producer()`
**पंक्तियाँ 31, 76:** `producer.close()` विधि
**पंक्तियाँ 64-65:** संदेश और गुणों के साथ `producer.send()`

**स्पेक फ़ाइल:** `trustgraph-base/trustgraph/base/producer_spec.py`
**पंक्ति 18:** `processor.pulsar_client` को संदर्भित करता है

### 5. प्रकाशक एब्स्ट्रैक्शन

**स्थान:** `trustgraph-base/trustgraph/base/publisher.py`

यह कतार बफरिंग के साथ एसिंक्रोनस संदेश प्रकाशन है:

**पल्सर आयात:**
**पंक्ति 2:** `from pulsar.schema import JsonSchema`
**पंक्ति 6:** `import pulsar`

**पल्सर-विशिष्ट उपयोग:**
**पंक्ति 52:** `JsonSchema(self.schema)` रैपर
**पंक्तियाँ 50-54:** पल्सर-विशिष्ट मापदंडों के साथ `self.client.create_producer()`
**पंक्तियाँ 101, 103:** संदेश और वैकल्पिक गुणों के साथ `producer.send()`
**पंक्तियाँ 106-107:** `producer.flush()` और `producer.close()` विधियाँ

### 6. सब्सक्राइबर एब्स्ट्रैक्शन

**स्थान:** `trustgraph-base/trustgraph/base/subscriber.py`

यह क्यूज़ से मल्टी-रिसीवर मैसेज डिस्ट्रीब्यूशन प्रदान करता है:

**पल्सर इम्पोर्ट्स:**
**लाइन 6:** `from pulsar.schema import JsonSchema`
**लाइन 8:** `import _pulsar`

**पल्सर-विशिष्ट उपयोग:**
**लाइन 55:** `JsonSchema(self.schema)` रैपर
**लाइन 57:** `self.client.subscribe(**subscribe_args)`
**लाइनें 101, 136, 160, 167-172:** पल्सर अपवाद: `_pulsar.Timeout`, `_pulsar.InvalidConfiguration`, `_pulsar.AlreadyClosed`
**लाइनें 159, 166, 170:** उपभोक्ता विधियाँ: `negative_acknowledge()`, `unsubscribe()`, `close()`
**लाइनें 247, 251:** मैसेज स्वीकृति: `acknowledge()`, `negative_acknowledge()`

**स्पेक फाइल:** `trustgraph-base/trustgraph/base/subscriber_spec.py`
**लाइन 19:** संदर्भ `processor.pulsar_client`

### 7. स्कीमा सिस्टम (हार्ट ऑफ डार्कनेस)

**स्थान:** `trustgraph-base/trustgraph/schema/`

सिस्टम में हर मैसेज स्कीमा पल्सर के स्कीमा फ्रेमवर्क का उपयोग करके परिभाषित किया गया है।

**कोर प्रिमिटिव्स:** `schema/core/primitives.py`
**लाइन 2:** `from pulsar.schema import Record, String, Boolean, Array, Integer`
सभी स्कीमा पल्सर के `Record` बेस क्लास से इनहेरिट होते हैं
सभी फ़ील्ड प्रकार पल्सर प्रकार हैं: `String()`, `Integer()`, `Boolean()`, `Array()`, `Map()`, `Double()`

**उदाहरण स्कीमा:**
`schema/services/llm.py` (लाइन 2): `from pulsar.schema import Record, String, Array, Double, Integer, Boolean`
`schema/services/config.py` (लाइन 2): `from pulsar.schema import Record, Bytes, String, Boolean, Array, Map, Integer`

**टॉपिक नामकरण:** `schema/core/topic.py`
**लाइनें 2-3:** टॉपिक फॉर्मेट: `{kind}://{tenant}/{namespace}/{topic}`
यह URI संरचना पल्सर-विशिष्ट है (जैसे, `persistent://tg/flow/config`)

**प्रभाव:**
पूरे कोडबेस में सभी अनुरोध/प्रतिक्रिया मैसेज परिभाषाएँ पल्सर स्कीमा का उपयोग करती हैं
इसमें निम्नलिखित के लिए सेवाएँ शामिल हैं: कॉन्फ़िग, फ्लो, एलएलएम, प्रॉम्प्ट, क्वेरी, स्टोरेज, एजेंट, कलेक्शन, डायग्नोसिस, लाइब्रेरी, लुकअप, एनएलपी_क्वेरी, ऑब्जेक्ट्स_क्वेरी, रिट्रीवल, स्ट्रक्चर्ड_क्वेरी
स्कीमा परिभाषाएँ सभी प्रोसेसर और सेवाओं में आयात की जाती हैं और व्यापक रूप से उपयोग की जाती हैं

## सारांश

### श्रेणी के अनुसार पल्सर निर्भरताएँ

1. **क्लाइंट इंस्टेंशिएशन:**
   सीधा: `gateway/service.py`
   अमूर्त: `async_processor.py` → `pubsub.py` (PulsarClient)

2. **मैसेज ट्रांसपोर्ट:**
   उपभोक्ता: `consumer.py`, `consumer_spec.py`
   उत्पादक: `producer.py`, `producer_spec.py`
   प्रकाशक: `publisher.py`
   सब्सक्राइबर: `subscriber.py`, `subscriber_spec.py`

3. **स्कीमा सिस्टम:**
   बेस प्रकार: `schema/core/primitives.py`
   सभी सेवा स्कीमा: `schema/services/*.py`
   टॉपिक नामकरण: `schema/core/topic.py`

4. **पल्सर-विशिष्ट अवधारणाएँ आवश्यक:**
   टॉपिक-आधारित मैसेजिंग
   स्कीमा सिस्टम (रिकॉर्ड, फ़ील्ड प्रकार)
   साझा सदस्यताएँ
   मैसेज स्वीकृति (सकारात्मक/नकारात्मक)
   उपभोक्ता पोजिशनिंग (सबसे पहले/नवीनतम)
   मैसेज प्रॉपर्टीज़
   प्रारंभिक पोजीशन और उपभोक्ता प्रकार
   चंकिंग सपोर्ट
   लगातार बनाम गैर-लगातार टॉपिक

### रिफैक्टरिंग चुनौतियाँ

अच्छी खबर: एब्स्ट्रैक्शन लेयर (उपभोक्ता, उत्पादक, प्रकाशक, सब्सक्राइबर) पल्सर इंटरैक्शन के अधिकांश पहलुओं को साफ-सुथरा रूप से एनकैप्सुलेट करता है।

चुनौतियाँ:
1. **स्कीमा सिस्टम की सर्वव्यापकता:** हर मैसेज परिभाषा `pulsar.schema.Record` और पल्सर फ़ील्ड प्रकारों का उपयोग करती है
2. **पल्सर-विशिष्ट एनम्स:** `InitialPosition`, `ConsumerType`
3. **पल्सर अपवाद:** `_pulsar.Timeout`, `_pulsar.Interrupted`, `_pulsar.InvalidConfiguration`, `_pulsar.AlreadyClosed`
4. **विधि हस्ताक्षर:** `acknowledge()`, `negative_acknowledge()`, `subscribe()`, `create_producer()`, आदि।
5. **टॉपिक URI फॉर्मेट:** पल्सर की `kind://tenant/namespace/topic` संरचना

### अगले कदम

पब/सब इंफ्रास्ट्रक्चर को कॉन्फ़िगर करने योग्य बनाने के लिए, हमें:

1. क्लाइंट/स्कीमा सिस्टम के लिए एक एब्स्ट्रैक्शन इंटरफ़ेस बनाएं
2. पल्सर-विशिष्ट एनम्स और अपवादों को अमूर्त करें
3. स्कीमा रैपर या वैकल्पिक स्कीमा परिभाषाएँ बनाएँ
4. पल्सर और वैकल्पिक सिस्टम (काफ्का, रैबिटएमक्यू, रेडिस स्ट्रीम्स, आदि) दोनों के लिए इंटरफ़ेस को लागू करें
5. `pubsub.py` को कॉन्फ़िगर करने योग्य बनाएं और कई बैकएंड का समर्थन करें
6. मौजूदा डिप्लॉयमेंट के लिए माइग्रेशन पाथ प्रदान करें

## दृष्टिकोण ड्राफ्ट 1: स्कीमा ट्रांसलेशन लेयर के साथ एडाप्टर पैटर्न

### मुख्य अंतर्दृष्टि
**स्कीमा सिस्टम** एकीकरण का सबसे गहरा बिंदु है - बाकी सब कुछ इससे उपजा है। हमें पहले इसे हल करना होगा, अन्यथा हमें पूरे कोडबेस को फिर से लिखना होगा।

### रणनीति: न्यूनतम व्यवधान के साथ एडाप्टर

**1. पल्सर स्कीमा को आंतरिक प्रतिनिधित्व के रूप में बनाए रखें**
सभी स्कीमा परिभाषाओं को फिर से न लिखें
स्कीमा `pulsar.schema.Record` आंतरिक रूप से बने रहेंगे
हमारे कोड और पब/सब बैकएंड के बीच की सीमा पर अनुवाद करने के लिए एडेप्टर का उपयोग करें

**2. एक पब/सब एब्स्ट्रैक्शन लेयर बनाएं:**

```
┌─────────────────────────────────────┐
│   Existing Code (unchanged)         │
│   - Uses Pulsar schemas internally  │
│   - Consumer/Producer/Publisher     │
└──────────────┬──────────────────────┘
               │
┌──────────────┴──────────────────────┐
│   PubSubFactory (configurable)      │
│   - Creates backend-specific client │
└──────────────┬──────────────────────┘
               │
        ┌──────┴──────┐
        │             │
┌───────▼─────┐  ┌────▼─────────┐
│ PulsarAdapter│  │ KafkaAdapter │  etc...
│ (passthrough)│  │ (translates) │
└──────────────┘  └──────────────┘
```

**3. अमूर्त इंटरफेस को परिभाषित करें:**
`PubSubClient` - क्लाइंट कनेक्शन
`PubSubProducer` - संदेश भेजना
`PubSubConsumer` - संदेश प्राप्त करना
`SchemaAdapter` - पल्सर स्कीमा को JSON या बैकएंड-विशिष्ट प्रारूपों में अनुवाद करना

**4. कार्यान्वयन विवरण:**

**पल्सर एडेप्टर के लिए:** लगभग सीधे, न्यूनतम अनुवाद

**अन्य बैकएंड के लिए** (Kafka, RabbitMQ, आदि):
पल्सर रिकॉर्ड ऑब्जेक्ट को JSON/बाइट में क्रमबद्ध करें
निम्नलिखित अवधारणाओं को मैप करें:
  `InitialPosition.Earliest/Latest` → Kafka का auto.offset.reset
  `acknowledge()` → Kafka का कमिट
  `negative_acknowledge()` → पुनः कतार या DLQ पैटर्न
  टॉपिक URI → बैकएंड-विशिष्ट टॉपिक नाम

### विश्लेषण

**लाभ:**
✅ मौजूदा सेवाओं में न्यूनतम कोड परिवर्तन
✅ स्कीमा अपरिवर्तित रहते हैं (कोई बड़ा पुनर्लेखन नहीं)
✅ क्रमिक माइग्रेशन पथ
✅ पल्सर उपयोगकर्ताओं को कोई अंतर दिखाई नहीं देता
✅ एडेप्टर के माध्यम से नए बैकएंड जोड़े जा सकते हैं

**नुकसान:**
⚠️ अभी भी पल्सर पर निर्भरता है (स्कीमा परिभाषाओं के लिए)
⚠️ अवधारणाओं का अनुवाद करते समय कुछ असंगति

### वैकल्पिक विचार

एक **ट्रस्टग्राफ स्कीमा सिस्टम** बनाएं जो पब/सब से स्वतंत्र हो (डेटाक्लासेस या पाइडैंटिक का उपयोग करके), और फिर पल्सर/काफ्का/आदि स्कीमा को इससे उत्पन्न करें। इसके लिए प्रत्येक स्कीमा फ़ाइल को फिर से लिखना होगा और संभावित रूप से ब्रेकिंग परिवर्तन हो सकते हैं।

### ड्राफ्ट 1 के लिए अनुशंसा

**एडाप्टर दृष्टिकोण** से शुरुआत करें क्योंकि:
1. यह व्यावहारिक है - मौजूदा कोड के साथ काम करता है
2. यह न्यूनतम जोखिम के साथ अवधारणा को सिद्ध करता है
3. यदि आवश्यक हो तो बाद में एक देशी स्कीमा सिस्टम में विकसित किया जा सकता है
4. कॉन्फ़िगरेशन-संचालित: एक पर्यावरण चर बैकएंड को स्विच करता है

## दृष्टिकोण ड्राफ्ट 2: डेटाक्लासेस के साथ बैकएंड-अज्ञेय स्कीमा सिस्टम

### मुख्य अवधारणा

पायथन **डेटाक्लासेस** का उपयोग तटस्थ स्कीमा परिभाषा प्रारूप के रूप में करें। प्रत्येक पब/सब बैकएंड डेटाक्लासेस के लिए अपना सीरियललाइज़ेशन/डीसेरियलाइज़ेशन प्रदान करता है, जिससे पल्सर स्कीमा को कोडबेस में बने रहने की आवश्यकता समाप्त हो जाती है।

### फैक्ट्री स्तर पर स्कीमा बहुरूपता

पल्सर स्कीमा का अनुवाद करने के बजाय, **प्रत्येक बैकएंड अपनी स्कीमा हैंडलिंग प्रदान करता है** जो मानक पायथन डेटाक्लासेस के साथ काम करता है।

### प्रकाशक प्रवाह

```python
# 1. Get the configured backend from factory
pubsub = get_pubsub()  # Returns PulsarBackend, MQTTBackend, etc.

# 2. Get schema class from the backend
# (Can be imported directly - backend-agnostic)
from trustgraph.schema.services.llm import TextCompletionRequest

# 3. Create a producer/publisher for a specific topic
producer = pubsub.create_producer(
    topic="text-completion-requests",
    schema=TextCompletionRequest  # Tells backend what schema to use
)

# 4. Create message instances (same API regardless of backend)
request = TextCompletionRequest(
    system="You are helpful",
    prompt="Hello world",
    streaming=False
)

# 5. Send the message
producer.send(request)  # Backend serializes appropriately
```

### उपभोक्ता प्रवाह

```python
# 1. Get the configured backend
pubsub = get_pubsub()

# 2. Create a consumer
consumer = pubsub.subscribe(
    topic="text-completion-requests",
    schema=TextCompletionRequest  # Tells backend how to deserialize
)

# 3. Receive and deserialize
msg = consumer.receive()
request = msg.value()  # Returns TextCompletionRequest dataclass instance

# 4. Use the data (type-safe access)
print(request.system)   # "You are helpful"
print(request.prompt)   # "Hello world"
print(request.streaming)  # False
```

### पर्दे के पीछे क्या होता है

**पल्सर बैकएंड के लिए:**
`create_producer()` → JSON स्कीमा या गतिशील रूप से उत्पन्न रिकॉर्ड के साथ पल्सर प्रोड्यूसर बनाता है
`send(request)` → डेटाक्लास को JSON/पल्सर प्रारूप में क्रमबद्ध करता है, पल्सर को भेजता है
`receive()` → पल्सर संदेश प्राप्त करता है, डेटाक्लास में वापस क्रमबद्ध करता है

**MQTT बैकएंड के लिए:**
`create_producer()` → MQTT ब्रोकर से कनेक्ट होता है, स्कीमा पंजीकरण की आवश्यकता नहीं है
`send(request)` → डेटाक्लास को JSON में परिवर्तित करता है, MQTT टॉपिक पर प्रकाशित करता है
`receive()` → MQTT टॉपिक की सदस्यता लेता है, JSON को डेटाक्लास में क्रमबद्ध करता है

**Kafka बैकएंड के लिए:**
`create_producer()` → Kafka प्रोड्यूसर बनाता है, यदि आवश्यक हो तो Avro स्कीमा पंजीकृत करता है
`send(request)` → डेटाक्लास को Avro प्रारूप में क्रमबद्ध करता है, Kafka को भेजता है
`receive()` → Kafka संदेश प्राप्त करता है, Avro को डेटाक्लास में वापस क्रमबद्ध करता है

### मुख्य डिज़ाइन बिंदु

1. **स्कीमा ऑब्जेक्ट निर्माण**: डेटाक्लास इंस्टेंस (`TextCompletionRequest(...)`) बैकएंड की परवाह किए बिना समान होता है
2. **बैकएंड एन्कोडिंग को संभालता है**: प्रत्येक बैकएंड जानता है कि अपने डेटाक्लास को वायर प्रारूप में कैसे क्रमबद्ध करना है
3. **निर्माण पर स्कीमा परिभाषा**: जब प्रोड्यूसर/कंज्यूमर बनाते हैं, तो आप स्कीमा प्रकार निर्दिष्ट करते हैं
4. **टाइप सुरक्षा संरक्षित**: आपको एक उचित `TextCompletionRequest` ऑब्जेक्ट वापस मिलता है, कोई डिक्ट नहीं
5. **कोई बैकएंड रिसाव नहीं**: एप्लिकेशन कोड कभी भी बैकएंड-विशिष्ट लाइब्रेरीज़ को आयात नहीं करता है

### उदाहरण परिवर्तन

**वर्तमान (पल्सर-विशिष्ट):**
```python
# schema/services/llm.py
from pulsar.schema import Record, String, Boolean, Integer

class TextCompletionRequest(Record):
    system = String()
    prompt = String()
    streaming = Boolean()
```

**नया (बैकएंड-स्वतंत्र):**
```python
# schema/services/llm.py
from dataclasses import dataclass

@dataclass
class TextCompletionRequest:
    system: str
    prompt: str
    streaming: bool = False
```

### बैकएंड एकीकरण

प्रत्येक बैकएंड डेटाक्लासों का क्रमबद्धता/अक्रमबद्धता (सीरियलाइज़ेशन/डीसीरियलाइज़ेशन) संभालता है:

**पल्सर बैकएंड:**
डेटाक्लासों से गतिशील रूप से `pulsar.schema.Record` क्लास उत्पन्न करें
या डेटाक्लासों को JSON में क्रमबद्ध करें और पल्सर के JSON स्कीमा का उपयोग करें
मौजूदा पल्सर डिप्लॉयमेंट के साथ संगतता बनाए रखता है

**MQTT/रेडिस बैकएंड:**
डेटाक्लास उदाहरणों का सीधा JSON क्रमबद्धता
`dataclasses.asdict()` / `from_dict()` का उपयोग करें
हल्का, किसी स्कीमा रजिस्ट्री की आवश्यकता नहीं है

**काफ्का बैकएंड:**
डेटाक्लास परिभाषाओं से एवरो स्कीमा उत्पन्न करें
कॉन्फ्लुएंट की स्कीमा रजिस्ट्री का उपयोग करें
स्कीमा विकास समर्थन के साथ टाइप-सुरक्षित क्रमबद्धता

### वास्तुकला

```
┌─────────────────────────────────────┐
│   Application Code                  │
│   - Uses dataclass schemas          │
│   - Backend-agnostic                │
└──────────────┬──────────────────────┘
               │
┌──────────────┴──────────────────────┐
│   PubSubFactory (configurable)      │
│   - get_pubsub() returns backend    │
└──────────────┬──────────────────────┘
               │
        ┌──────┴──────┐
        │             │
┌───────▼─────────┐  ┌────▼──────────────┐
│ PulsarBackend   │  │ MQTTBackend       │
│ - JSON schema   │  │ - JSON serialize  │
│ - or dynamic    │  │ - Simple queues   │
│   Record gen    │  │                   │
└─────────────────┘  └───────────────────┘
```

### कार्यान्वयन विवरण

**1. स्कीमा परिभाषाएँ:** साधारण डेटाक्लास, टाइप हिंट के साथ
   `str`, `int`, `bool`, `float` मूल डेटा प्रकारों के लिए
   `list[T]` सरणियों के लिए
   `dict[str, T]` मानचित्रों के लिए
   जटिल प्रकारों के लिए नेस्टेड डेटाक्लास

**2. प्रत्येक बैकएंड निम्नलिखित प्रदान करता है:**
   सीरियलइज़र: `dataclass → bytes/wire format`
   डीसीरियलइज़र: `bytes/wire format → dataclass`
   स्कीमा पंजीकरण (यदि आवश्यक हो, जैसे कि Pulsar/Kafka)

**3. उपभोक्ता/उत्पादक सार:**
   पहले से मौजूद (consumer.py, producer.py)
   बैकएंड के सीरियलइज़ेशन का उपयोग करने के लिए अपडेट करें
   सीधे Pulsar आयात को हटा दें

**4. टाइप मैपिंग:**
   Pulsar `String()` → Python `str`
   Pulsar `Integer()` → Python `int`
   Pulsar `Boolean()` → Python `bool`
   Pulsar `Array(T)` → Python `list[T]`
   Pulsar `Map(K, V)` → Python `dict[K, V]`
   Pulsar `Double()` → Python `float`
   Pulsar `Bytes()` → Python `bytes`

### माइग्रेशन पथ

1. `trustgraph/schema/` में सभी स्कीमा के डेटाक्लास संस्करण बनाएं
2. बैकएंड-प्रदान सीरियलइज़ेशन का उपयोग करने के लिए (उपभोक्ता, उत्पादक, प्रकाशक, ग्राहक) बैकएंड क्लास को अपडेट करें
3. JSON स्कीमा या गतिशील रिकॉर्ड पीढ़ी के साथ PulsarBackend को लागू करें
4. मौजूदा परिनियोजनों के साथ पिछड़े अनुकूलता सुनिश्चित करने के लिए Pulsar के साथ परीक्षण करें
5. आवश्यकतानुसार नए बैकएंड (MQTT, Kafka, Redis, आदि) जोड़ें
6. स्कीमा फ़ाइलों से Pulsar आयात को हटा दें

### लाभ

✅ **स्कीमा परिभाषाओं में कोई पब/सब निर्भरता नहीं**
✅ **मानक Python** - समझने, टाइप-चेक करने और दस्तावेज़ बनाने में आसान
✅ **आधुनिक टूलिंग** - mypy, IDE ऑटो-कंप्लीट, लिंटर के साथ काम करता है
✅ **बैकएंड-अनुकूलित** - प्रत्येक बैकएंड देशी सीरियलइज़ेशन का उपयोग करता है
✅ **कोई अनुवाद ओवरहेड नहीं** - सीधा सीरियलइज़ेशन, कोई एडेप्टर नहीं
✅ **टाइप सुरक्षा** - उचित प्रकारों के साथ वास्तविक ऑब्जेक्ट
✅ **आसान सत्यापन** - यदि आवश्यक हो तो Pydantic का उपयोग कर सकते हैं

### चुनौतियाँ और समाधान

**चुनौती:** Pulsar का `Record` में रनटाइम फ़ील्ड सत्यापन होता है
**समाधान:** यदि आवश्यक हो तो सत्यापन के लिए Pydantic डेटाक्लास का उपयोग करें, या `__post_init__` के साथ Python 3.10+ डेटाक्लास सुविधाओं का उपयोग करें

**चुनौती:** कुछ Pulsar-विशिष्ट विशेषताएं (जैसे `Bytes` प्रकार)
**समाधान:** डेटाक्लास में `bytes` प्रकार पर मैप करें, बैकएंड उचित रूप से एन्कोडिंग को संभालता है

**चुनौती:** टॉपिक नामकरण (`persistent://tenant/namespace/topic`)
**समाधान:** स्कीमा परिभाषाओं में टॉपिक नामों को सारगर्भित करें, बैकएंड उचित प्रारूप में परिवर्तित करता है

**चुनौती:** स्कीमा विकास और संस्करण
**समाधान:** प्रत्येक बैकएंड अपनी क्षमताओं के अनुसार इसका प्रबंधन करता है (Pulsar स्कीमा संस्करण, Kafka स्कीमा रजिस्ट्री, आदि)

**चुनौती:** नेस्टेड जटिल प्रकार
**समाधान:** नेस्टेड डेटाक्लास का उपयोग करें, बैकएंड पुनरावर्ती रूप से सीरियलइज़/डीसीरियलइज़ करते हैं

### डिज़ाइन निर्णय

1. **सादे डेटाक्लास या Pydantic?**
   ✅ **निर्णय: सादे Python डेटाक्लास का उपयोग करें**
   सरल, कोई अतिरिक्त निर्भरता नहीं
   सत्यापन व्यावहारिक रूप से आवश्यक नहीं है
   समझना और बनाए रखना आसान है

2. **स्कीमा विकास:**
   ✅ **निर्णय: कोई संस्करण तंत्र आवश्यक नहीं है**
   स्कीमा स्थिर और लंबे समय तक चलने वाले हैं
   अपडेट आमतौर पर नए फ़ील्ड जोड़ते हैं (पिछड़े संगत)
   बैकएंड अपनी क्षमताओं के अनुसार स्कीमा विकास को संभालते हैं

3. **पिछड़ी संगतता:**
   ✅ **निर्णय: प्रमुख संस्करण परिवर्तन, पिछड़े संगतता की आवश्यकता नहीं है**
   यह एक ब्रेकिंग परिवर्तन होगा जिसमें माइग्रेशन निर्देश होंगे
   बेहतर डिज़ाइन के लिए स्वच्छ ब्रेक
   मौजूदा परिनियोजनों के लिए एक माइग्रेशन गाइड प्रदान किया जाएगा

4. **नेस्टेड प्रकार और जटिल संरचनाएं:**
   ✅ **निर्णय: स्वाभाविक रूप से नेस्टेड डेटाक्लास का उपयोग करें**
   Python डेटाक्लास नेस्टिंग को पूरी तरह से संभालते हैं
   सरणियों के लिए `list[T]`, मानचित्रों के लिए `dict[K, V]`
   बैकएंड पुनरावर्ती रूप से सीरियलइज़/डीसीरियलइज़ करते हैं
   उदाहरण:
     ```python
     @dataclass
     class Value:
         value: str
         is_uri: bool

     @dataclass
     class Triple:
         s: Value              # Nested dataclass
         p: Value
         o: Value

     @dataclass
     class GraphQuery:
         triples: list[Triple]  # Array of nested dataclasses
         metadata: dict[str, str]
     ```

5. **डिफ़ॉल्ट मान और वैकल्पिक फ़ील्ड:**
   ✅ **निर्णय: आवश्यक, डिफ़ॉल्ट और वैकल्पिक फ़ील्ड का मिश्रण**
   आवश्यक फ़ील्ड: कोई डिफ़ॉल्ट मान नहीं
   डिफ़ॉल्ट वाले फ़ील्ड: हमेशा मौजूद, उनका उचित डिफ़ॉल्ट मान होता है
   वास्तव में वैकल्पिक फ़ील्ड: `T | None = None`, जब `None` हो तो क्रमबद्धता से छोड़े जा सकते हैं
   उदाहरण:
     ```python
     @dataclass
     class TextCompletionRequest:
         system: str              # Required, no default
         prompt: str              # Required, no default
         streaming: bool = False  # Optional with default value
         metadata: dict | None = None  # Truly optional, can be absent
     ```

   **महत्वपूर्ण क्रमबद्धता अर्थ:**

   जब `metadata = None`:
   ```json
   {
       "system": "...",
       "prompt": "...",
       "streaming": false
       // metadata field NOT PRESENT
   }
   ```

   जब `metadata = {}` (स्पष्ट रूप से खाली):
   ```json
   {
       "system": "...",
       "prompt": "...",
       "streaming": false,
       "metadata": {}  // Field PRESENT but empty
   }
   ```

   **मुख्य अंतर:**
   `None` → JSON में अनुपस्थित फ़ील्ड (सीरियलाइज़ नहीं किया गया)
   खाली मान (`{}`, `[]`, `""`) → फ़ील्ड मौजूद है लेकिन खाली मान के साथ
   यह अर्थपूर्ण रूप से महत्वपूर्ण है: "प्रदान नहीं किया गया" बनाम "स्पष्ट रूप से खाली"
   सीरियलाइज़ेशन बैकएंड को `None` फ़ील्ड को छोड़ना चाहिए, न कि इसे `null` के रूप में एन्कोड करना चाहिए

## दृष्टिकोण ड्राफ्ट 3: कार्यान्वयन विवरण

### सामान्य कतार नामकरण प्रारूप

बैकएंड-विशिष्ट कतार नामों को एक सामान्य प्रारूप से बदलें जिसे बैकएंड उचित रूप से मैप कर सकें।

**प्रारूप:** `{qos}/{tenant}/{namespace}/{queue-name}`

जहाँ:
`qos`: सेवा की गुणवत्ता स्तर
  `q0` = बेस्ट-एफर्ट (फायर एंड फॉरगेट, कोई स्वीकृति नहीं)
  `q1` = एट-लीस्ट-वन्स (स्वीकृति की आवश्यकता होती है)
  `q2` = एग्ज़ैक्टली-वन्स (दो-चरण स्वीकृति)
`tenant`: मल्टी-टेनेंसी के लिए तार्किक समूहीकरण
`namespace`: किरायेदार के भीतर उप-समूहीकरण
`queue-name`: वास्तविक कतार/विषय नाम

**उदाहरण:**
```
q1/tg/flow/text-completion-requests
q2/tg/config/config-push
q0/tg/metrics/stats
```

### बैकएंड टॉपिक मैपिंग

प्रत्येक बैकएंड सामान्य प्रारूप को अपने मूल प्रारूप में परिवर्तित करता है:

**पल्सर बैकएंड:**
```python
def map_topic(self, generic_topic: str) -> str:
    # Parse: q1/tg/flow/text-completion-requests
    qos, tenant, namespace, queue = generic_topic.split('/', 3)

    # Map QoS to persistence
    persistence = 'persistent' if qos in ['q1', 'q2'] else 'non-persistent'

    # Return Pulsar URI: persistent://tg/flow/text-completion-requests
    return f"{persistence}://{tenant}/{namespace}/{queue}"
```

**एमक्यूटीटी बैकएंड:**
```python
def map_topic(self, generic_topic: str) -> tuple[str, int]:
    # Parse: q1/tg/flow/text-completion-requests
    qos, tenant, namespace, queue = generic_topic.split('/', 3)

    # Map QoS level
    qos_level = {'q0': 0, 'q1': 1, 'q2': 2}[qos]

    # Build MQTT topic including tenant/namespace for proper namespacing
    mqtt_topic = f"{tenant}/{namespace}/{queue}"

    return mqtt_topic, qos_level
```

### अद्यतित विषय सहायक फ़ंक्शन

```python
# schema/core/topic.py
def topic(queue_name, qos='q1', tenant='tg', namespace='flow'):
    """
    Create a generic topic identifier that can be mapped by backends.

    Args:
        queue_name: The queue/topic name
        qos: Quality of service
             - 'q0' = best-effort (no ack)
             - 'q1' = at-least-once (ack required)
             - 'q2' = exactly-once (two-phase ack)
        tenant: Tenant identifier for multi-tenancy
        namespace: Namespace within tenant

    Returns:
        Generic topic string: qos/tenant/namespace/queue_name

    Examples:
        topic('my-queue')  # q1/tg/flow/my-queue
        topic('config', qos='q2', namespace='config')  # q2/tg/config/config
    """
    return f"{qos}/{tenant}/{namespace}/{queue_name}"
```

### कॉन्फ़िगरेशन और इनिशियलाइज़ेशन

**कमांड-लाइन तर्क + पर्यावरण चर:**

```python
# In base/async_processor.py - add_args() method
@staticmethod
def add_args(parser):
    # Pub/sub backend selection
    parser.add_argument(
        '--pubsub-backend',
        default=os.getenv('PUBSUB_BACKEND', 'pulsar'),
        choices=['pulsar', 'mqtt'],
        help='Pub/sub backend (default: pulsar, env: PUBSUB_BACKEND)'
    )

    # Pulsar-specific configuration
    parser.add_argument(
        '--pulsar-host',
        default=os.getenv('PULSAR_HOST', 'pulsar://localhost:6650'),
        help='Pulsar host (default: pulsar://localhost:6650, env: PULSAR_HOST)'
    )

    parser.add_argument(
        '--pulsar-api-key',
        default=os.getenv('PULSAR_API_KEY', None),
        help='Pulsar API key (env: PULSAR_API_KEY)'
    )

    parser.add_argument(
        '--pulsar-listener',
        default=os.getenv('PULSAR_LISTENER', None),
        help='Pulsar listener name (env: PULSAR_LISTENER)'
    )

    # MQTT-specific configuration
    parser.add_argument(
        '--mqtt-host',
        default=os.getenv('MQTT_HOST', 'localhost'),
        help='MQTT broker host (default: localhost, env: MQTT_HOST)'
    )

    parser.add_argument(
        '--mqtt-port',
        type=int,
        default=int(os.getenv('MQTT_PORT', '1883')),
        help='MQTT broker port (default: 1883, env: MQTT_PORT)'
    )

    parser.add_argument(
        '--mqtt-username',
        default=os.getenv('MQTT_USERNAME', None),
        help='MQTT username (env: MQTT_USERNAME)'
    )

    parser.add_argument(
        '--mqtt-password',
        default=os.getenv('MQTT_PASSWORD', None),
        help='MQTT password (env: MQTT_PASSWORD)'
    )
```

**फ़ैक्टरी फ़ंक्शन:**

```python
# In base/pubsub.py or base/pubsub_factory.py
def get_pubsub(**config) -> PubSubBackend:
    """
    Create and return a pub/sub backend based on configuration.

    Args:
        config: Configuration dict from command-line args
                Must include 'pubsub_backend' key

    Returns:
        Backend instance (PulsarBackend, MQTTBackend, etc.)
    """
    backend_type = config.get('pubsub_backend', 'pulsar')

    if backend_type == 'pulsar':
        return PulsarBackend(
            host=config.get('pulsar_host'),
            api_key=config.get('pulsar_api_key'),
            listener=config.get('pulsar_listener'),
        )
    elif backend_type == 'mqtt':
        return MQTTBackend(
            host=config.get('mqtt_host'),
            port=config.get('mqtt_port'),
            username=config.get('mqtt_username'),
            password=config.get('mqtt_password'),
        )
    else:
        raise ValueError(f"Unknown pub/sub backend: {backend_type}")
```

**एसिंक्रोनसप्रोसेसर में उपयोग:**

```python
# In async_processor.py
class AsyncProcessor:
    def __init__(self, **params):
        self.id = params.get("id")

        # Create backend from config (replaces PulsarClient)
        self.pubsub = get_pubsub(**params)

        # Rest of initialization...
```

### बैकएंड इंटरफ़ेस

```python
class PubSubBackend(Protocol):
    """Protocol defining the interface all pub/sub backends must implement."""

    def create_producer(self, topic: str, schema: type, **options) -> BackendProducer:
        """
        Create a producer for a topic.

        Args:
            topic: Generic topic format (qos/tenant/namespace/queue)
            schema: Dataclass type for messages
            options: Backend-specific options (e.g., chunking_enabled)

        Returns:
            Backend-specific producer instance
        """
        ...

    def create_consumer(
        self,
        topic: str,
        subscription: str,
        schema: type,
        initial_position: str = 'latest',
        consumer_type: str = 'shared',
        **options
    ) -> BackendConsumer:
        """
        Create a consumer for a topic.

        Args:
            topic: Generic topic format (qos/tenant/namespace/queue)
            subscription: Subscription/consumer group name
            schema: Dataclass type for messages
            initial_position: 'earliest' or 'latest' (MQTT may ignore)
            consumer_type: 'shared', 'exclusive', 'failover' (MQTT may ignore)
            options: Backend-specific options

        Returns:
            Backend-specific consumer instance
        """
        ...

    def close(self) -> None:
        """Close the backend connection."""
        ...
```

```python
class BackendProducer(Protocol):
    """Protocol for backend-specific producer."""

    def send(self, message: Any, properties: dict = {}) -> None:
        """Send a message (dataclass instance) with optional properties."""
        ...

    def flush(self) -> None:
        """Flush any buffered messages."""
        ...

    def close(self) -> None:
        """Close the producer."""
        ...
```

```python
class BackendConsumer(Protocol):
    """Protocol for backend-specific consumer."""

    def receive(self, timeout_millis: int = 2000) -> Message:
        """
        Receive a message from the topic.

        Raises:
            TimeoutError: If no message received within timeout
        """
        ...

    def acknowledge(self, message: Message) -> None:
        """Acknowledge successful processing of a message."""
        ...

    def negative_acknowledge(self, message: Message) -> None:
        """Negative acknowledge - triggers redelivery."""
        ...

    def unsubscribe(self) -> None:
        """Unsubscribe from the topic."""
        ...

    def close(self) -> None:
        """Close the consumer."""
        ...
```

```python
class Message(Protocol):
    """Protocol for a received message."""

    def value(self) -> Any:
        """Get the deserialized message (dataclass instance)."""
        ...

    def properties(self) -> dict:
        """Get message properties/metadata."""
        ...
```

### मौजूदा कक्षाओं का पुनर्गठन

मौजूदा `Consumer`, `Producer`, `Publisher`, `Subscriber` कक्षाएं काफी हद तक अपरिवर्तित रहेंगी:

**वर्तमान जिम्मेदारियां (बनाए रखें):**
एसिंक्रोनस थ्रेडिंग मॉडल और टास्कग्रुप
पुनः कनेक्शन लॉजिक और पुनः प्रयास प्रबंधन
मेट्रिक्स संग्रह
दर सीमित करना
समवर्ती प्रबंधन

**आवश्यक परिवर्तन:**
सीधे पल्सर आयात को हटा दें (`pulsar.schema`, `pulsar.InitialPosition`, आदि)
पल्सर क्लाइंट के बजाय `BackendProducer`/`BackendConsumer` स्वीकार करें
वास्तविक पब/सब संचालन को बैकएंड इंस्टेंस को सौंपें
सामान्य अवधारणाओं को बैकएंड कॉल में मैप करें

**उदाहरण पुनर्गठन:**

```python
# OLD - consumer.py
class Consumer:
    def __init__(self, client, topic, subscriber, schema, ...):
        self.client = client  # Direct Pulsar client
        # ...

    async def consumer_run(self):
        # Uses pulsar.InitialPosition, pulsar.ConsumerType
        self.consumer = self.client.subscribe(
            topic=self.topic,
            schema=JsonSchema(self.schema),
            initial_position=pulsar.InitialPosition.Earliest,
            consumer_type=pulsar.ConsumerType.Shared,
        )

# NEW - consumer.py
class Consumer:
    def __init__(self, backend_consumer, schema, ...):
        self.backend_consumer = backend_consumer  # Backend-specific consumer
        self.schema = schema
        # ...

    async def consumer_run(self):
        # Backend consumer already created with right settings
        # Just use it directly
        while self.running:
            msg = await asyncio.to_thread(
                self.backend_consumer.receive,
                timeout_millis=2000
            )
            await self.handle_message(msg)
```

### बैकएंड-विशिष्ट व्यवहार

**पल्सर बैकएंड:**
`q0` को `non-persistent://` में मैप करता है, `q1`/`q2` को `persistent://` में मैप करता है।
सभी प्रकार के उपभोक्ताओं का समर्थन करता है (साझा, विशेष, फेलओवर)।
प्रारंभिक स्थिति का समर्थन करता है (सबसे पहले/सबसे बाद में)।
मूल संदेश स्वीकृति।
स्कीमा रजिस्ट्री समर्थन।

**एमक्यूटीटी बैकएंड:**
`q0`/`q1`/`q2` को एमक्यूटीटी क्यूओएस स्तर 0/1/2 में मैप करता है।
नामस्थान के लिए टॉपिक पथ में किरायेदार/नेमस्पेस शामिल करता है।
सदस्यता नामों से स्वचालित रूप से क्लाइंट आईडी उत्पन्न करता है।
प्रारंभिक स्थिति को अनदेखा करता है (मूल एमक्यूटीटी में कोई संदेश इतिहास नहीं)।
उपभोक्ता प्रकार को अनदेखा करता है (एमक्यूटीटी क्लाइंट आईडी, उपभोक्ता समूहों का उपयोग नहीं करता है)।
सरल प्रकाशित/सदस्यता मॉडल।

### डिज़ाइन निर्णयों का सारांश

1. ✅ **सामान्य कतार नामकरण**: `qos/tenant/namespace/queue-name` प्रारूप।
2. ✅ **कतार आईडी में क्यूओएस**: कतार परिभाषा द्वारा निर्धारित, कॉन्फ़िगरेशन द्वारा नहीं।
3. ✅ **पुनः कनेक्शन**: उपभोक्ता/उत्पादक कक्षाओं द्वारा संभाला जाता है, बैकएंड द्वारा नहीं।
4. ✅ **एमक्यूटीटी टॉपिक**: उचित नामस्थान के लिए किरायेदार/नेमस्पेस शामिल करें।
5. ✅ **संदेश इतिहास**: एमक्यूटीटी `initial_position` पैरामीटर को अनदेखा करता है (भविष्य में सुधार)।
6. ✅ **क्लाइंट आईडी**: एमक्यूटीटी बैकएंड सदस्यता नाम से स्वचालित रूप से उत्पन्न करता है।

### भविष्य के सुधार

**एमक्यूटीटी संदेश इतिहास:**
वैकल्पिक दृढ़ता परत (जैसे, रिटेन्ड संदेश, बाहरी स्टोर) जोड़ा जा सकता है।
यह `initial_position='earliest'` का समर्थन करने की अनुमति देगा।
प्रारंभिक कार्यान्वयन के लिए आवश्यक नहीं है।

