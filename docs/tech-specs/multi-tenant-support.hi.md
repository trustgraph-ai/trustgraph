# तकनीकी विनिर्देश: मल्टी-टेनेंट समर्थन

## अवलोकन

पैरामीटर नाम विसंगतियों को ठीक करके मल्टी-टेनेंट परिनियोजन सक्षम करें जो कतार अनुकूलन को रोकते हैं, और कैसेंड्रा कीस्पेस पैरामीटराइज़ेशन जोड़ें।

## आर्किटेक्चर संदर्भ

### फ्लो-आधारित कतार समाधान

ट्रस्टग्राफ सिस्टम गतिशील कतार समाधान के लिए एक **फ्लो-आधारित आर्किटेक्चर** का उपयोग करता है, जो स्वाभाविक रूप से मल्टी-टेनेंसी का समर्थन करता है:

**फ्लो परिभाषाएँ** कैसेंड्रा में संग्रहीत हैं और इंटरफ़ेस परिभाषाओं के माध्यम से कतार नामों को निर्दिष्ट करती हैं।
**कतार नाम टेम्प्लेट का उपयोग करते हैं** जिसमें `{id}` चर होते हैं जिन्हें फ्लो इंस्टेंस आईडी के साथ प्रतिस्थापित किया जाता है।
**सेवाएँ गतिशील रूप से कतारों को हल करती हैं** अनुरोध समय पर फ्लो कॉन्फ़िगरेशन की खोज करके।
**प्रत्येक किरायेदार के पास अलग-अलग कतार नामों के साथ अद्वितीय फ्लो हो सकते हैं**, जो अलगाव प्रदान करते हैं।

फ्लो इंटरफ़ेस परिभाषा का उदाहरण:
```json
{
  "interfaces": {
    "triples-store": "persistent://tg/flow/triples-store:{id}",
    "graph-embeddings-store": "persistent://tg/flow/graph-embeddings-store:{id}"
  }
}
```

जब किरायेदार ए प्रवाह `tenant-a-prod` शुरू करता है और किरायेदार बी प्रवाह `tenant-b-prod` शुरू करता है, तो उन्हें स्वचालित रूप से अलग-अलग कतारें मिलती हैं:
`persistent://tg/flow/triples-store:tenant-a-prod`
`persistent://tg/flow/triples-store:tenant-b-prod`

**मल्टी-टेनेंसी के लिए सही ढंग से डिज़ाइन की गई सेवाएं:**
✅ **नॉलेज मैनेजमेंट (कोर)** - अनुरोधों में पारित प्रवाह कॉन्फ़िगरेशन से कतारों को गतिशील रूप से हल करता है

**जिन सेवाओं को ठीक करने की आवश्यकता है:**
🔴 **कॉन्फ़िग सर्विस** - पैरामीटर नाम बेमेल होने से कतार अनुकूलन में बाधा आती है
🔴 **लाइब्रेरियन सर्विस** - हार्डकोडेड स्टोरेज मैनेजमेंट टॉपिक (नीचे चर्चा की गई है)
🔴 **सभी सेवाएं** - कैसेंड्रा कीस्पेस को अनुकूलित नहीं किया जा सकता है

## समस्या विवरण

### मुद्दा #1: एसिंक्रोनसप्रोसेसर में पैरामीटर नाम बेमेल
**CLI द्वारा परिभाषित:** `--config-queue` (अस्पष्ट नामकरण)
**Argparse द्वारा रूपांतरण:** `config_queue` (पैरामीटर डिक्ट में)
**कोड द्वारा खोजा गया:** `config_push_queue`
**परिणाम:** पैरामीटर को अनदेखा किया जाता है, डिफ़ॉल्ट रूप से `persistent://tg/config/config`
**प्रभाव:** 32 से अधिक सेवाओं पर प्रभाव पड़ता है जो AsyncProcessor से विरासत में मिली हैं
**बाधा:** मल्टी-टेनेंट डिप्लॉयमेंट किरायेदार-विशिष्ट कॉन्फ़िग कतारों का उपयोग नहीं कर सकते हैं
**समाधान:** स्पष्टता के लिए CLI पैरामीटर का नाम बदलकर `--config-push-queue` करें (ब्रेकिंग चेंज स्वीकार्य है क्योंकि सुविधा वर्तमान में टूटी हुई है)

### मुद्दा #2: कॉन्फ़िग सर्विस में पैरामीटर नाम बेमेल
**CLI द्वारा परिभाषित:** `--push-queue` (अस्पष्ट नामकरण)
**Argparse द्वारा रूपांतरण:** `push_queue` (पैरामीटर डिक्ट में)
**कोड द्वारा खोजा गया:** `config_push_queue`
**परिणाम:** पैरामीटर को अनदेखा किया जाता है
**प्रभाव:** कॉन्फ़िग सर्विस कस्टम पुश कतार का उपयोग नहीं कर सकती है
**समाधान:** स्थिरता और स्पष्टता के लिए CLI पैरामीटर का नाम बदलकर `--config-push-queue` करें (ब्रेकिंग चेंज स्वीकार्य है)

### मुद्दा #3: हार्डकोडेड कैसेंड्रा कीस्पेस
**वर्तमान:** विभिन्न सेवाओं में कीस्पेस को हार्डकोडेड के रूप में `"config"`, `"knowledge"`, `"librarian"` के रूप में परिभाषित किया गया है
**परिणाम:** मल्टी-टेनेंट डिप्लॉयमेंट के लिए कीस्पेस को अनुकूलित नहीं किया जा सकता है
**प्रभाव:** कॉन्फ़िग, कोर और लाइब्रेरियन सेवाएं
**बाधा:** कई किरायेदार अलग-अलग कैसेंड्रा कीस्पेस का उपयोग नहीं कर सकते हैं

### मुद्दा #4: कलेक्शन मैनेजमेंट आर्किटेक्चर ✅ पूर्ण
**पिछला:** कलेक्शन को लाइब्रेरियन कीस्पेस में एक अलग कलेक्शन टेबल के माध्यम से संग्रहीत किया जाता था
**पिछला:** लाइब्रेरियन ने कलेक्शन बनाने/हटाने के लिए 4 हार्डकोडेड स्टोरेज मैनेजमेंट टॉपिक का उपयोग किया:
  `vector_storage_management_topic`
  `object_storage_management_topic`
  `triples_storage_management_topic`
  `storage_management_response_topic`
**समस्याएं (हल की गई):**
  हार्डकोडेड टॉपिक को मल्टी-टेनेंट डिप्लॉयमेंट के लिए अनुकूलित नहीं किया जा सकता था
  लाइब्रेरियन और 4+ स्टोरेज सेवाओं के बीच जटिल एसिंक्रोनस समन्वय
  अलग कैसेंड्रा टेबल और प्रबंधन अवसंरचना
  महत्वपूर्ण कार्यों के लिए गैर-स्थायी अनुरोध/प्रतिक्रिया कतारें
**कार्यान्वित समाधान:** कलेक्शन को कॉन्फ़िग सर्विस स्टोरेज में माइग्रेट किया गया, वितरण के लिए कॉन्फ़िग पुश का उपयोग किया गया
**स्थिति:** सभी स्टोरेज बैकएंड को `CollectionConfigHandler` पैटर्न में माइग्रेट किया गया है

## समाधान

यह विनिर्देश मुद्दों #1, #2, #3 और #4 को संबोधित करता है।

### भाग 1: पैरामीटर नाम बेमेल को ठीक करें

#### परिवर्तन 1: AsyncProcessor बेस क्लास - CLI पैरामीटर का नाम बदलें
**फ़ाइल:** `trustgraph-base/trustgraph/base/async_processor.py`
**पंक्ति:** 260-264

**वर्तमान:**
```python
parser.add_argument(
    '--config-queue',
    default=default_config_queue,
    help=f'Config push queue {default_config_queue}',
)
```

**निश्चित:**
```python
parser.add_argument(
    '--config-push-queue',
    default=default_config_queue,
    help=f'Config push queue (default: {default_config_queue})',
)
```

**तर्क:**
अधिक स्पष्ट और विस्तृत नामकरण
आंतरिक चर नाम से मेल खाता है `config_push_queue`
परिवर्तन स्वीकार्य है क्योंकि सुविधा वर्तमान में गैर-कार्यात्मक है
params.get() में कोई कोड परिवर्तन आवश्यक नहीं है - यह पहले से ही सही नाम की तलाश करता है

#### परिवर्तन 2: कॉन्फ़िगरेशन सेवा - CLI पैरामीटर का नाम बदलें
**फ़ाइल:** `trustgraph-flow/trustgraph/config/service/service.py`
**पंक्ति:** 276-279

**वर्तमान:**
```python
parser.add_argument(
    '--push-queue',
    default=default_config_push_queue,
    help=f'Config push queue (default: {default_config_push_queue})'
)
```

**निश्चित:**
```python
parser.add_argument(
    '--config-push-queue',
    default=default_config_push_queue,
    help=f'Config push queue (default: {default_config_push_queue})'
)
```

**तर्क:**
अधिक स्पष्ट नामकरण - "config-push-queue" केवल "push-queue" से अधिक स्पष्ट है।
आंतरिक चर नाम `config_push_queue` से मेल खाता है।
AsyncProcessor के `--config-push-queue` पैरामीटर के साथ संगत।
परिवर्तन स्वीकार्य है क्योंकि सुविधा वर्तमान में गैर-कार्यात्मक है।
params.get() में कोई कोड परिवर्तन आवश्यक नहीं है - यह पहले से ही सही नाम की तलाश करता है।

### भाग 2: कैसेंड्रा कीस्पेस पैरामीटराइज़ेशन जोड़ें

#### परिवर्तन 3: cassandra_config मॉड्यूल में कीस्पेस पैरामीटर जोड़ें
**फ़ाइल:** `trustgraph-base/trustgraph/base/cassandra_config.py`

**CLI तर्क जोड़ें** (`add_cassandra_args()` फ़ंक्शन में):
```python
parser.add_argument(
    '--cassandra-keyspace',
    default=None,
    help='Cassandra keyspace (default: service-specific)'
)
```

**पर्यावरण चर समर्थन जोड़ें** (फ़ंक्शन `resolve_cassandra_config()` में):
```python
keyspace = params.get(
    "cassandra_keyspace",
    os.environ.get("CASSANDRA_KEYSPACE")
)
```

**`resolve_cassandra_config()` का रिटर्न वैल्यू अपडेट करें:**
वर्तमान में रिटर्न करता है: `(hosts, username, password)`
बदलने पर रिटर्न करेगा: `(hosts, username, password, keyspace)`

**तर्क:**
मौजूदा कैसेंड्रा कॉन्फ़िगरेशन पैटर्न के अनुरूप
`add_cassandra_args()` के माध्यम से सभी सेवाओं के लिए उपलब्ध
CLI और पर्यावरण चर कॉन्फ़िगरेशन दोनों का समर्थन करता है

#### परिवर्तन 4: कॉन्फ़िगरेशन सर्विस - पैरामीटराइज़्ड कीस्पेस का उपयोग करें
**फ़ाइल:** `trustgraph-flow/trustgraph/config/service/service.py`

**पंक्ति 30** - हार्डकोडेड कीस्पेस हटाएं:
```python
# DELETE THIS LINE:
keyspace = "config"
```

**पंक्तियाँ 69-73** - कैसेंड्रा कॉन्फ़िगरेशन रिज़ॉल्यूशन को अपडेट करें:

**वर्तमान:**
```python
cassandra_host, cassandra_username, cassandra_password = \
    resolve_cassandra_config(params)
```

**निश्चित:**
```python
cassandra_host, cassandra_username, cassandra_password, keyspace = \
    resolve_cassandra_config(params, default_keyspace="config")
```

**तर्क:**
"config" को डिफ़ॉल्ट के रूप में रखते हुए पिछली अनुकूलता बनाए रखता है।
`--cassandra-keyspace` या `CASSANDRA_KEYSPACE` के माध्यम से ओवरराइड करने की अनुमति देता है।

#### परिवर्तन 5: कोर/नॉलेज सर्विस - पैरामीटराइज़्ड कीस्पेस का उपयोग करें।
**फ़ाइल:** `trustgraph-flow/trustgraph/cores/service.py`

**पंक्ति 37** - हार्डकोडेड कीस्पेस को हटाएँ:
```python
# DELETE THIS LINE:
keyspace = "knowledge"
```

**कैसेंड्रा कॉन्फ़िगरेशन रिज़ॉल्यूशन को अपडेट करें** (कॉन्फ़िगरेशन सेवा के समान स्थान पर):
```python
cassandra_host, cassandra_username, cassandra_password, keyspace = \
    resolve_cassandra_config(params, default_keyspace="knowledge")
```

#### परिवर्तन 6: लाइब्रेरियन सेवा - पैरामीटराइज़्ड कीस्पेस का उपयोग करें
**फ़ाइल:** `trustgraph-flow/trustgraph/librarian/service.py`

**पंक्ति 51** - हार्डकोडेड कीस्पेस हटाएं:
```python
# DELETE THIS LINE:
keyspace = "librarian"
```

**कैसेंड्रा कॉन्फ़िगरेशन रिज़ॉल्यूशन को अपडेट करें** (कॉन्फ़िगरेशन सेवा के समान स्थान पर):
```python
cassandra_host, cassandra_username, cassandra_password, keyspace = \
    resolve_cassandra_config(params, default_keyspace="librarian")
```

### भाग 3: संग्रह प्रबंधन को कॉन्फ़िगरेशन सेवा में स्थानांतरित करें

#### अवलोकन
संग्रहों को कैसेंड्रा लाइब्रेरियन कीस्पेस से कॉन्फ़िगरेशन सेवा भंडारण में स्थानांतरित करें। यह हार्ड-कोडेड भंडारण प्रबंधन विषयों को समाप्त करता है और मौजूदा कॉन्फ़िगरेशन पुश तंत्र का उपयोग करके वितरण के लिए वास्तुकला को सरल बनाता है।

#### वर्तमान वास्तुकला
```
API Request → Gateway → Librarian Service
                            ↓
                    CollectionManager
                            ↓
                    Cassandra Collections Table (librarian keyspace)
                            ↓
                    Broadcast to 4 Storage Management Topics (hardcoded)
                            ↓
        Wait for 4+ Storage Service Responses
                            ↓
                    Response to Gateway
```

#### नई वास्तुकला
```
API Request → Gateway → Librarian Service
                            ↓
                    CollectionManager
                            ↓
                    Config Service API (put/delete/getvalues)
                            ↓
                    Cassandra Config Table (class='collections', key='user:collection')
                            ↓
                    Config Push (to all subscribers on config-push-queue)
                            ↓
        All Storage Services receive config update independently
```

#### परिवर्तन 7: संग्रह प्रबंधक - कॉन्फ़िगरेशन सेवा एपीआई का उपयोग करें
**फ़ाइल:** `trustgraph-flow/trustgraph/librarian/collection_manager.py`

**हटाएं:**
`LibraryTableStore` का उपयोग (पंक्तियाँ 33, 40-41)
स्टोरेज प्रबंधन उत्पादकों का आरंभीकरण (पंक्तियाँ 86-140)
`on_storage_response` विधि (पंक्तियाँ 400-430)
`pending_deletions` ट्रैकिंग (पंक्तियाँ 57, 90-96, और पूरे में उपयोग)

**जोड़ें:**
एपीआई कॉल के लिए कॉन्फ़िगरेशन सेवा क्लाइंट (अनुरोध/प्रतिक्रिया पैटर्न)

**कॉन्फ़िगरेशन क्लाइंट सेटअप:**
```python
# In __init__, add config request/response producers/consumers
from trustgraph.schema.services.config import ConfigRequest, ConfigResponse

# Producer for config requests
self.config_request_producer = Producer(
    client=pulsar_client,
    topic=config_request_queue,
    schema=ConfigRequest,
)

# Consumer for config responses (with correlation ID)
self.config_response_consumer = Consumer(
    taskgroup=taskgroup,
    client=pulsar_client,
    flow=None,
    topic=config_response_queue,
    subscriber=f"{id}-config",
    schema=ConfigResponse,
    handler=self.on_config_response,
)

# Tracking for pending config requests
self.pending_config_requests = {}  # request_id -> asyncio.Event
```

**`list_collections` को संशोधित करें (पंक्तियाँ 145-180):**
```python
async def list_collections(self, user, tag_filter=None, limit=None):
    """List collections from config service"""
    # Send getvalues request to config service
    request = ConfigRequest(
        id=str(uuid.uuid4()),
        operation='getvalues',
        type='collections',
    )

    # Send request and wait for response
    response = await self.send_config_request(request)

    # Parse collections from response
    collections = []
    for key, value_json in response.values.items():
        if ":" in key:
            coll_user, collection = key.split(":", 1)
            if coll_user == user:
                metadata = json.loads(value_json)
                collections.append(CollectionMetadata(**metadata))

    # Apply tag filtering in-memory (as before)
    if tag_filter:
        collections = [c for c in collections if any(tag in c.tags for tag in tag_filter)]

    # Apply limit
    if limit:
        collections = collections[:limit]

    return collections

async def send_config_request(self, request):
    """Send config request and wait for response"""
    event = asyncio.Event()
    self.pending_config_requests[request.id] = event

    await self.config_request_producer.send(request)
    await event.wait()

    return self.pending_config_requests.pop(request.id + "_response")

async def on_config_response(self, message, consumer, flow):
    """Handle config response"""
    response = message.value()
    if response.id in self.pending_config_requests:
        self.pending_config_requests[response.id + "_response"] = response
        self.pending_config_requests[response.id].set()
```

**`update_collection` को संशोधित करें (पंक्तियाँ 182-312):**
```python
async def update_collection(self, user, collection, name, description, tags):
    """Update collection via config service"""
    # Create metadata
    metadata = CollectionMetadata(
        user=user,
        collection=collection,
        name=name,
        description=description,
        tags=tags,
    )

    # Send put request to config service
    request = ConfigRequest(
        id=str(uuid.uuid4()),
        operation='put',
        type='collections',
        key=f'{user}:{collection}',
        value=json.dumps(metadata.to_dict()),
    )

    response = await self.send_config_request(request)

    if response.error:
        raise RuntimeError(f"Config update failed: {response.error.message}")

    # Config service will trigger config push automatically
    # Storage services will receive update and create collections
```

**`delete_collection` में संशोधन करें (पंक्तियाँ 314-398):**
```python
async def delete_collection(self, user, collection):
    """Delete collection via config service"""
    # Send delete request to config service
    request = ConfigRequest(
        id=str(uuid.uuid4()),
        operation='delete',
        type='collections',
        key=f'{user}:{collection}',
    )

    response = await self.send_config_request(request)

    if response.error:
        raise RuntimeError(f"Config delete failed: {response.error.message}")

    # Config service will trigger config push automatically
    # Storage services will receive update and delete collections
```

**संग्रह मेटाडेटा प्रारूप:**
कॉन्फ़िगरेशन तालिका में इस प्रकार संग्रहीत: `class='collections', key='user:collection'`
मान JSON-सीरियलाइज़्ड CollectionMetadata है (समय-मुद्रांकन फ़ील्ड के बिना)
फ़ील्ड: `user`, `collection`, `name`, `description`, `tags`
उदाहरण: `class='collections', key='alice:my-docs', value='{"user":"alice","collection":"my-docs","name":"My Documents","description":"...","tags":["work"]}'`

#### परिवर्तन 8: लाइब्रेरियन सेवा - स्टोरेज मैनेजमेंट इंफ्रास्ट्रक्चर को हटाएं
**फ़ाइल:** `trustgraph-flow/trustgraph/librarian/service.py`

**हटाएं:**
स्टोरेज मैनेजमेंट प्रोड्यूसर (पंक्ति 173-190):
  `vector_storage_management_producer`
  `object_storage_management_producer`
  `triples_storage_management_producer`
स्टोरेज रिस्पांस कंज्यूमर (पंक्ति 192-201)
`on_storage_response` हैंडलर (पंक्ति 467-473)

**संशोधित करें:**
CollectionManager इनिशियलाइज़ेशन (पंक्ति 215-224) - स्टोरेज प्रोड्यूसर पैरामीटर हटाएं

**ध्यान दें:** बाहरी संग्रह एपीआई अपरिवर्तित रहता है:
`list-collections`
`update-collection`
`delete-collection`

#### परिवर्तन 9: LibraryTableStore से Collections टेबल को हटाएं
**फ़ाइल:** `trustgraph-flow/trustgraph/tables/library.py`

**हटाएं:**
Collections टेबल CREATE स्टेटमेंट (पंक्ति 114-127)
Collections तैयार स्टेटमेंट (पंक्ति 205-240)
सभी संग्रह विधियाँ (पंक्ति 578-717):
  `ensure_collection_exists`
  `list_collections`
  `update_collection`
  `delete_collection`
  `get_collection`
  `create_collection`

**तर्क:**
संग्रह अब कॉन्फ़िगरेशन तालिका में संग्रहीत हैं।
परिवर्तन स्वीकार्य है - डेटा माइग्रेशन की आवश्यकता नहीं है।
लाइब्रेरियन सेवा को काफी सरल बनाता है।

#### परिवर्तन 10: स्टोरेज सेवाएं - कॉन्फ़िगरेशन-आधारित संग्रह प्रबंधन ✅ पूर्ण

**स्थिति:** सभी 11 स्टोरेज बैकएंड को `CollectionConfigHandler` का उपयोग करने के लिए माइग्रेट किया गया है।

**प्रभावित सेवाएं (कुल 11):**
दस्तावेज़ एम्बेडिंग: मिलवस, पाइनकोन, क्यूड्रांट
ग्राफ एम्बेडिंग: मिलवस, पाइनकोन, क्यूड्रांट
ऑब्जेक्ट स्टोरेज: कैसेंड्रा
ट्रिपल स्टोरेज: कैसेंड्रा, फाल्कोडीबी, मेमग्राफ, नियो4जे

**फाइलें:**
`trustgraph-flow/trustgraph/storage/doc_embeddings/milvus/write.py`
`trustgraph-flow/trustgraph/storage/doc_embeddings/pinecone/write.py`
`trustgraph-flow/trustgraph/storage/doc_embeddings/qdrant/write.py`
`trustgraph-flow/trustgraph/storage/graph_embeddings/milvus/write.py`
`trustgraph-flow/trustgraph/storage/graph_embeddings/pinecone/write.py`
`trustgraph-flow/trustgraph/storage/graph_embeddings/qdrant/write.py`
`trustgraph-flow/trustgraph/storage/objects/cassandra/write.py`
`trustgraph-flow/trustgraph/storage/triples/cassandra/write.py`
`trustgraph-flow/trustgraph/storage/triples/falkordb/write.py`
`trustgraph-flow/trustgraph/storage/triples/memgraph/write.py`
`trustgraph-flow/trustgraph/storage/triples/neo4j/write.py`

**कार्यान्वयन पैटर्न (सभी सेवाएं):**

1. **`__init__` में कॉन्फ़िगरेशन हैंडलर पंजीकृत करें:**
```python
# Add after AsyncProcessor initialization
self.register_config_handler(self.on_collection_config)
self.known_collections = set()  # Track (user, collection) tuples
```

2. **कॉन्फ़िगरेशन हैंडलर को लागू करें:**
```python
async def on_collection_config(self, config, version):
    """Handle collection configuration updates"""
    logger.info(f"Collection config version: {version}")

    if "collections" not in config:
        return

    # Parse collections from config
    # Key format: "user:collection" in config["collections"]
    config_collections = set()
    for key in config["collections"].keys():
        if ":" in key:
            user, collection = key.split(":", 1)
            config_collections.add((user, collection))

    # Determine changes
    to_create = config_collections - self.known_collections
    to_delete = self.known_collections - config_collections

    # Create new collections (idempotent)
    for user, collection in to_create:
        try:
            await self.create_collection_internal(user, collection)
            self.known_collections.add((user, collection))
            logger.info(f"Created collection: {user}/{collection}")
        except Exception as e:
            logger.error(f"Failed to create {user}/{collection}: {e}")

    # Delete removed collections (idempotent)
    for user, collection in to_delete:
        try:
            await self.delete_collection_internal(user, collection)
            self.known_collections.discard((user, collection))
            logger.info(f"Deleted collection: {user}/{collection}")
        except Exception as e:
            logger.error(f"Failed to delete {user}/{collection}: {e}")
```

3. **प्रारंभ में ज्ञात संग्रहों को आरंभीकृत करें:**
```python
async def start(self):
    """Start the processor"""
    await super().start()
    await self.sync_known_collections()

async def sync_known_collections(self):
    """Query backend to populate known_collections set"""
    # Backend-specific implementation:
    # - Milvus/Pinecone/Qdrant: List collections/indexes matching naming pattern
    # - Cassandra: Query keyspaces or collection metadata
    # - Neo4j/Memgraph/FalkorDB: Query CollectionMetadata nodes
    pass
```

4. **मौजूदा हैंडलर विधियों को पुनर्गठित करें:**
```python
# Rename and remove response sending:
# handle_create_collection → create_collection_internal
# handle_delete_collection → delete_collection_internal

async def create_collection_internal(self, user, collection):
    """Create collection (idempotent)"""
    # Same logic as current handle_create_collection
    # But remove response producer calls
    # Handle "already exists" gracefully
    pass

async def delete_collection_internal(self, user, collection):
    """Delete collection (idempotent)"""
    # Same logic as current handle_delete_collection
    # But remove response producer calls
    # Handle "not found" gracefully
    pass
```

5. **भंडारण प्रबंधन अवसंरचना को हटाएं:**
   `self.storage_request_consumer` सेटअप और प्रारंभ को हटाएं
   `self.storage_response_producer` सेटअप को हटाएं
   `on_storage_management` डिस्पैचर विधि को हटाएं
   भंडारण प्रबंधन के लिए मेट्रिक्स को हटाएं
   इम्पोर्ट को हटाएं: `StorageManagementRequest`, `StorageManagementResponse`

**बैकएंड-विशिष्ट विचार:**

**वेक्टर स्टोर (मिलवस, पाइनकोन, क्यूड्रांट):** `known_collections` में लॉजिकल `(user, collection)` को ट्रैक करें, लेकिन प्रत्येक आयाम के लिए कई बैकएंड संग्रह बनाए जा सकते हैं। आलसी निर्माण पैटर्न जारी रखें। हटाने के कार्यों को सभी आयाम वेरिएंट को हटाना चाहिए।

**कैसेंड्रा ऑब्जेक्ट्स:** संग्रह पंक्ति गुण हैं, संरचनाएं नहीं। कीस्पेस-स्तरीय जानकारी को ट्रैक करें।

**ग्राफ स्टोर (नियो4जे, मेमग्राफ, फाल्कोर्डबी):** स्टार्टअप पर `CollectionMetadata` नोड्स को क्वेरी करें। सिंक पर मेटाडेटा नोड्स बनाएं/हटाएं।

**कैसेंड्रा ट्रिपल्स:** संग्रह संचालन के लिए `KnowledgeGraph` एपीआई का उपयोग करें।

**मुख्य डिज़ाइन बिंदु:**

**अंतिम स्थिरता:** कोई अनुरोध/प्रतिक्रिया तंत्र नहीं, कॉन्फ़िगरेशन पुश प्रसारित किया जाता है
**अपरिवर्तनीयता:** सभी निर्माण/हटाने के संचालन को पुनः प्रयास करना सुरक्षित होना चाहिए
**त्रुटि प्रबंधन:** त्रुटियों को लॉग करें लेकिन कॉन्फ़िगरेशन अपडेट को अवरुद्ध न करें
**स्व-सुधार:** विफल संचालन अगले कॉन्फ़िगरेशन पुश पर पुनः प्रयास करेंगे
**संग्रह कुंजी प्रारूप:** `config["collections"]` में `"user:collection"`

#### परिवर्तन 11: संग्रह स्कीमा अपडेट करें - टाइमस्टैम्प हटाएं
**फ़ाइल:** `trustgraph-base/trustgraph/schema/services/collection.py`

**संग्रहMetadata (पंक्ति 13-21) को संशोधित करें:**
`created_at` और `updated_at` फ़ील्ड को हटाएं:
```python
class CollectionMetadata(Record):
    user = String()
    collection = String()
    name = String()
    description = String()
    tags = Array(String())
    # Remove: created_at = String()
    # Remove: updated_at = String()
```

**कलेक्शनमैनेजमेंट रिक्वेस्ट में बदलाव (पंक्ति 25-47):**
टाइमस्टैम्प फ़ील्ड हटाएं:
```python
class CollectionManagementRequest(Record):
    operation = String()
    user = String()
    collection = String()
    timestamp = String()
    name = String()
    description = String()
    tags = Array(String())
    # Remove: created_at = String()
    # Remove: updated_at = String()
    tag_filter = Array(String())
    limit = Integer()
```

**तर्क:**
टाइमस्टैम्प संग्रह के लिए कोई मूल्य नहीं जोड़ते हैं।
कॉन्फ़िगरेशन सेवा अपनी संस्करण ट्रैकिंग बनाए रखती है।
स्कीमा को सरल बनाता है और भंडारण को कम करता है।

#### कॉन्फ़िगरेशन सेवा माइग्रेशन के लाभ

1. ✅ **हार्डकोडेड स्टोरेज प्रबंधन विषयों को समाप्त करता है** - मल्टी-टेनेंट अवरोध को हल करता है।
2. ✅ **सरल समन्वय** - 4+ स्टोरेज प्रतिक्रियाओं के लिए कोई जटिल एसिंक्रोनस प्रतीक्षा नहीं।
3. ✅ **अंतिम स्थिरता** - स्टोरेज सेवाएं कॉन्फ़िगरेशन पुश के माध्यम से स्वतंत्र रूप से अपडेट करती हैं।
4. ✅ **बेहतर विश्वसनीयता** - गैर-स्थायी अनुरोध/प्रतिक्रिया के विपरीत, लगातार कॉन्फ़िगरेशन पुश।
5. ✅ **एकीकृत कॉन्फ़िगरेशन मॉडल** - संग्रह को कॉन्फ़िगरेशन के रूप में माना जाता है।
6. ✅ **जटिलता को कम करता है** - ~300 लाइनों के समन्वय कोड को हटाता है।
7. ✅ **मल्टी-टेनेंट के लिए तैयार** - कॉन्फ़िगरेशन पहले से ही कीस्पेस के माध्यम से किरायेदार अलगाव का समर्थन करता है।
8. ✅ **संस्करण ट्रैकिंग** - कॉन्फ़िगरेशन सेवा संस्करण तंत्र ऑडिट ट्रेल प्रदान करता है।

## कार्यान्वयन नोट्स

### पिछड़ा संगतता

**पैरामीटर परिवर्तन:**
CLI पैरामीटर का नाम बदलना एक ब्रेकिंग परिवर्तन है लेकिन स्वीकार्य है (फ़ीचर वर्तमान में गैर-कार्यात्मक है)।
सेवाएं पैरामीटर के बिना काम करती हैं (डिफ़ॉल्ट का उपयोग करें)।
डिफ़ॉल्ट कीस्पेस संरक्षित हैं: "config", "knowledge", "librarian"
डिफ़ॉल्ट कतार: `persistent://tg/config/config`

**संग्रह प्रबंधन:**
**ब्रेकिंग परिवर्तन:** लाइब्रेरियन कीस्पेस से संग्रह तालिका हटा दी गई है।
**कोई डेटा माइग्रेशन प्रदान नहीं किया गया है** - इस चरण के लिए स्वीकार्य है।
बाहरी संग्रह API अपरिवर्तित है (सूची/अपडेट/हटाने के संचालन)।
संग्रह मेटाडेटा प्रारूप को सरल बनाया गया है (टाइमस्टैम्प हटा दिए गए हैं)।

### परीक्षण आवश्यकताएँ

**पैरामीटर परीक्षण:**
1. सत्यापित करें कि `--config-push-queue` पैरामीटर ग्राफ-एम्बेडिंग सेवा पर काम करता है।
2. सत्यापित करें कि `--config-push-queue` पैरामीटर टेक्स्ट-कंप्लीशन सेवा पर काम करता है।
3. सत्यापित करें कि `--config-push-queue` पैरामीटर कॉन्फ़िगरेशन सेवा पर काम करता है।
4. सत्यापित करें कि `--cassandra-keyspace` पैरामीटर कॉन्फ़िगरेशन सेवा के लिए काम करता है।
5. सत्यापित करें कि `--cassandra-keyspace` पैरामीटर कोर सेवा के लिए काम करता है।
6. सत्यापित करें कि `--cassandra-keyspace` पैरामीटर लाइब्रेरियन सेवा के लिए काम करता है।
7. सत्यापित करें कि सेवाएं पैरामीटर के बिना काम करती हैं (डिफ़ॉल्ट का उपयोग करती हैं)।
8. कस्टम कतार नामों और कीस्पेस के साथ मल्टी-टेनेंट परिनियोजन सत्यापित करें।

**संग्रह प्रबंधन परीक्षण:**
9. कॉन्फ़िगरेशन सेवा के माध्यम से `list-collections` ऑपरेशन सत्यापित करें।
10. सत्यापित करें कि `update-collection` कॉन्फ़िगरेशन तालिका में बनाता/अपडेट करता है।
11. सत्यापित करें कि `delete-collection` कॉन्फ़िगरेशन तालिका से हटाता है।
12. सत्यापित करें कि संग्रह अपडेट पर कॉन्फ़िगरेशन पुश ट्रिगर होता है।
13. सत्यापित करें कि कॉन्फ़िगरेशन-आधारित स्टोरेज के साथ टैग फ़िल्टरिंग काम करता है।
14. सत्यापित करें कि संग्रह ऑपरेशन टाइमस्टैम्प फ़ील्ड के बिना काम करते हैं।

### मल्टी-टेनेंट परिनियोजन उदाहरण
```bash
# Tenant: tg-dev
graph-embeddings \
  -p pulsar+ssl://broker:6651 \
  --pulsar-api-key <KEY> \
  --config-push-queue persistent://tg-dev/config/config

config-service \
  -p pulsar+ssl://broker:6651 \
  --pulsar-api-key <KEY> \
  --config-push-queue persistent://tg-dev/config/config \
  --cassandra-keyspace tg_dev_config
```

## प्रभाव विश्लेषण

### परिवर्तन 1-2 से प्रभावित सेवाएं (CLI पैरामीटर का नाम बदलना)
सभी सेवाएं जो AsyncProcessor या FlowProcessor से विरासत में मिली हैं:
config-service
cores-service
librarian-service
graph-embeddings
document-embeddings
text-completion-* (सभी प्रदाता)
extract-* (सभी एक्सट्रैक्टर)
query-* (सभी क्वेरी सेवाएं)
retrieval-* (सभी RAG सेवाएं)
storage-* (सभी स्टोरेज सेवाएं)
और 20+ से अधिक सेवाएं

### परिवर्तन 3-6 से प्रभावित सेवाएं (कैसेंड्रा कीस्पेस)
config-service
cores-service
librarian-service

### परिवर्तन 7-11 से प्रभावित सेवाएं (संग्रह प्रबंधन)

**तत्काल परिवर्तन:**
librarian-service (collection_manager.py, service.py)
tables/library.py (संग्रह तालिका को हटाना)
schema/services/collection.py (टाइमस्टैम्प को हटाना)

**पूरे हुए परिवर्तन (परिवर्तन 10):** ✅
सभी स्टोरेज सेवाएं (कुल 11) - संग्रह अपडेट के लिए कॉन्फ़िगरेशन पुश के माध्यम से `CollectionConfigHandler` में माइग्रेट किया गया
`storage.py` से स्टोरेज प्रबंधन स्कीमा को हटाया गया

## भविष्य के विचार

### प्रति-उपयोगकर्ता कीस्पेस मॉडल

कुछ सेवाएं **प्रति-उपयोगकर्ता कीस्पेस** गतिशील रूप से उपयोग करती हैं, जहां प्रत्येक उपयोगकर्ता का अपना कैसेंड्रा कीस्पेस होता है:

**प्रति-उपयोगकर्ता कीस्पेस वाली सेवाएं:**
1. **ट्रिपल्स क्वेरी सर्विस** (`trustgraph-flow/trustgraph/query/triples/cassandra/service.py:65`)
   `keyspace=query.user` का उपयोग करता है
2. **ऑब्जेक्ट्स क्वेरी सर्विस** (`trustgraph-flow/trustgraph/query/objects/cassandra/service.py:479`)
   `keyspace=self.sanitize_name(user)` का उपयोग करता है
3. **नॉलेज ग्राफ डायरेक्ट एक्सेस** (`trustgraph-flow/trustgraph/direct/cassandra_kg.py:18`)
   डिफ़ॉल्ट पैरामीटर `keyspace="trustgraph"`

**स्थिति:** ये इस विनिर्देश में **बदले नहीं गए** हैं।

**भविष्य की समीक्षा आवश्यक:**
मूल्यांकन करें कि क्या प्रति-उपयोगकर्ता कीस्पेस मॉडल किरायेदार अलगाव के मुद्दे बनाता है
इस पर विचार करें कि क्या मल्टी-टेनेन्ट डिप्लॉयमेंट को कीस्पेस उपसर्ग पैटर्न (जैसे, `tenant_a_user1`) की आवश्यकता है
किरायेदारों में संभावित उपयोगकर्ता आईडी टकराव के लिए समीक्षा करें
मूल्यांकन करें कि क्या प्रति किरायेदार एकल साझा कीस्पेस उपयोगकर्ता-आधारित पंक्ति अलगाव के साथ अधिक उपयुक्त है

**नोट:** यह वर्तमान मल्टी-टेनेन्ट कार्यान्वयन को अवरुद्ध नहीं करता है, लेकिन उत्पादन मल्टी-टेनेन्ट डिप्लॉयमेंट से पहले इसकी समीक्षा की जानी चाहिए।

## कार्यान्वयन चरण

### चरण 1: पैरामीटर सुधार (परिवर्तन 1-6)
`--config-push-queue` पैरामीटर नामकरण को ठीक करें
`--cassandra-keyspace` पैरामीटर समर्थन जोड़ें
**परिणाम:** मल्टी-टेनेन्ट कतार और कीस्पेस कॉन्फ़िगरेशन सक्षम

### चरण 2: संग्रह प्रबंधन माइग्रेशन (परिवर्तन 7-9, 11)
संग्रह स्टोरेज को कॉन्फ़िगरेशन सेवा में माइग्रेट करें
लाइब्रेरियन से संग्रह तालिका को हटा दें
संग्रह स्कीमा को अपडेट करें (टाइमस्टैम्प हटाएं)
**परिणाम:** हार्डकोडेड स्टोरेज प्रबंधन विषयों को समाप्त करता है, लाइब्रेरियन को सरल बनाता है

### चरण 3: स्टोरेज सर्विस अपडेट (परिवर्तन 10) ✅ पूर्ण
सभी स्टोरेज सेवाओं को `CollectionConfigHandler` के माध्यम से संग्रह के लिए कॉन्फ़िगरेशन पुश का उपयोग करने के लिए अपडेट किया गया
स्टोरेज प्रबंधन अनुरोध/प्रतिक्रिया बुनियादी ढांचे को हटा दिया गया
विरासत स्कीमा परिभाषाओं को हटा दिया गया
**परिणाम:** कॉन्फ़िगरेशन-आधारित संग्रह प्रबंधन प्राप्त हुआ

## संदर्भ
GitHub मुद्दा: https://github.com/trustgraph-ai/trustgraph/issues/582
संबंधित फाइलें:
  `trustgraph-base/trustgraph/base/async_processor.py`
  `trustgraph-base/trustgraph/base/cassandra_config.py`
  `trustgraph-base/trustgraph/schema/core/topic.py`
  `trustgraph-base/trustgraph/schema/services/collection.py`
  `trustgraph-flow/trustgraph/config/service/service.py`
  `trustgraph-flow/trustgraph/cores/service.py`
  `trustgraph-flow/trustgraph/librarian/service.py`
  `trustgraph-flow/trustgraph/librarian/collection_manager.py`
  `trustgraph-flow/trustgraph/tables/library.py`
