# ट्रस्टग्राफ लॉगिंग रणनीति

## अवलोकन

ट्रस्टग्राफ सभी लॉगिंग कार्यों के लिए पायथन के अंतर्निहित `logging` मॉड्यूल का उपयोग करता है, जिसमें केंद्रीकृत कॉन्फ़िगरेशन और लॉग एकत्रीकरण के लिए वैकल्पिक लोकी एकीकरण शामिल है। यह सिस्टम के सभी घटकों में लॉगिंग के लिए एक मानकीकृत, लचीला दृष्टिकोण प्रदान करता है।

## डिफ़ॉल्ट कॉन्फ़िगरेशन

### लॉगिंग स्तर
**डिफ़ॉल्ट स्तर**: `INFO`
**कॉन्फ़िगरेशन**: `--log-level` कमांड-लाइन तर्क के माध्यम से
**विकल्प**: `DEBUG`, `INFO`, `WARNING`, `ERROR`, `CRITICAL`

### आउटपुट गंतव्य
1. **कंसोल (stdout)**: हमेशा सक्षम - कंटेनरीकृत वातावरणों के साथ संगतता सुनिश्चित करता है
2. **लोकी**: वैकल्पिक केंद्रीकृत लॉग एकत्रीकरण (डिफ़ॉल्ट रूप से सक्षम, इसे अक्षम किया जा सकता है)

## केंद्रीकृत लॉगिंग मॉड्यूल

सभी लॉगिंग कॉन्फ़िगरेशन को `trustgraph.base.logging` मॉड्यूल द्वारा प्रबंधित किया जाता है, जो निम्नलिखित प्रदान करता है:
`add_logging_args(parser)` - मानक लॉगिंग CLI तर्क जोड़ता है
`setup_logging(args)` - पार्स किए गए तर्कों से लॉगिंग को कॉन्फ़िगर करता है

इस मॉड्यूल का उपयोग सभी सर्वर-साइड घटकों द्वारा किया जाता है:
AsyncProcessor-आधारित सेवाएं
एपीआई गेटवे
एमसीपी सर्वर

## कार्यान्वयन दिशानिर्देश

### 1. लॉगर इनिशियलाइज़ेशन

प्रत्येक मॉड्यूल को मॉड्यूल के `__name__` का उपयोग करके अपना लॉगर बनाना चाहिए:

```python
import logging

logger = logging.getLogger(__name__)
```

लॉगर का नाम स्वचालित रूप से लोकी में फ़िल्टरिंग और खोज के लिए एक लेबल के रूप में उपयोग किया जाता है।

### 2. सेवा आरंभिकरण

सभी सर्वर-साइड सेवाओं को केंद्रीकृत मॉड्यूल के माध्यम से स्वचालित रूप से लॉगिंग कॉन्फ़िगरेशन प्राप्त होता है:

```python
from trustgraph.base import add_logging_args, setup_logging
import argparse

def main():
    parser = argparse.ArgumentParser()

    # Add standard logging arguments (includes Loki configuration)
    add_logging_args(parser)

    # Add your service-specific arguments
    parser.add_argument('--port', type=int, default=8080)

    args = parser.parse_args()
    args = vars(args)

    # Setup logging early in startup
    setup_logging(args)

    # Rest of your service initialization
    logger = logging.getLogger(__name__)
    logger.info("Service starting...")
```

### 3. कमांड-लाइन तर्क

सभी सेवाएं इन लॉगिंग तर्कों का समर्थन करती हैं:

**लॉग स्तर:**
```bash
--log-level {DEBUG,INFO,WARNING,ERROR,CRITICAL}
```

**लोकी कॉन्फ़िगरेशन:**
```bash
--loki-enabled              # Enable Loki (default)
--no-loki-enabled           # Disable Loki
--loki-url URL              # Loki push URL (default: http://loki:3100/loki/api/v1/push)
--loki-username USERNAME    # Optional authentication
--loki-password PASSWORD    # Optional authentication
```

**उदाहरण:**
```bash
# Default - INFO level, Loki enabled
./my-service

# Debug mode, console only
./my-service --log-level DEBUG --no-loki-enabled

# Custom Loki server with auth
./my-service --loki-url http://loki.prod:3100/loki/api/v1/push \
             --loki-username admin --loki-password secret
```

### 4. पर्यावरण चर

लोकी कॉन्फ़िगरेशन पर्यावरण चर के उपयोग का समर्थन करता है:

```bash
export LOKI_URL=http://loki.prod:3100/loki/api/v1/push
export LOKI_USERNAME=admin
export LOKI_PASSWORD=secret
```

कमांड-लाइन तर्क पर्यावरण चर से अधिक महत्वपूर्ण होते हैं।

### 5. लॉगिंग के सर्वोत्तम अभ्यास

#### लॉग स्तरों का उपयोग
**DEBUG**: समस्याओं के निदान के लिए विस्तृत जानकारी (चर मान, फ़ंक्शन प्रविष्टि/निकास)
**INFO**: सामान्य सूचनात्मक संदेश (सेवा शुरू, कॉन्फ़िगरेशन लोड, प्रसंस्करण मील के पत्थर)
**WARNING**: संभावित रूप से हानिकारक स्थितियों के लिए चेतावनी संदेश (अप्रचलित सुविधाएँ, ठीक होने योग्य त्रुटियाँ)
**ERROR**: गंभीर समस्याओं के लिए त्रुटि संदेश (विफल संचालन, अपवाद)
**CRITICAL**: तत्काल ध्यान देने की आवश्यकता वाले सिस्टम विफलताओं के लिए महत्वपूर्ण संदेश

#### संदेश प्रारूप
```python
# Good - includes context
logger.info(f"Processing document: {doc_id}, size: {doc_size} bytes")
logger.error(f"Failed to connect to database: {error}", exc_info=True)

# Avoid - lacks context
logger.info("Processing document")
logger.error("Connection failed")
```

#### प्रदर्शन संबंधी विचार
```python
# Use lazy formatting for expensive operations
logger.debug("Expensive operation result: %s", expensive_function())

# Check log level for very expensive debug operations
if logger.isEnabledFor(logging.DEBUG):
    debug_data = compute_expensive_debug_info()
    logger.debug(f"Debug data: {debug_data}")
```

### 6. लोकी के साथ संरचित लॉगिंग

जटिल डेटा के लिए, लोकी के लिए अतिरिक्त टैग के साथ संरचित लॉगिंग का उपयोग करें:

```python
logger.info("Request processed", extra={
    'tags': {
        'request_id': request_id,
        'user_id': user_id,
        'status': 'success'
    }
})
```

ये टैग, स्वचालित लेबल के अतिरिक्त, लोकी में खोज योग्य लेबल बन जाते हैं:
`severity` - लॉग स्तर (डीबग, जानकारी, चेतावनी, त्रुटि, गंभीर)
`logger` - मॉड्यूल का नाम (`__name__` से)

### 7. अपवाद लॉगिंग

हमेशा अपवादों के लिए स्टैक ट्रेस शामिल करें:

```python
try:
    process_data()
except Exception as e:
    logger.error(f"Failed to process data: {e}", exc_info=True)
    raise
```

### 8. एसिंक्रोनस लॉगिंग संबंधी विचार

लॉगिंग सिस्टम लोकी के लिए गैर-ब्लॉकिंग कतार वाले हैंडलर का उपयोग करता है:
कंसोल आउटपुट सिंक्रोनस (तेज़) है
लोकी आउटपुट 500-संदेश बफर के साथ कतारबद्ध है
बैकग्राउंड थ्रेड लोकी ट्रांसमिशन को संभालता है
मुख्य एप्लिकेशन कोड का कोई अवरोधन नहीं

```python
import asyncio
import logging

async def async_operation():
    logger = logging.getLogger(__name__)
    # Logging is thread-safe and won't block async operations
    logger.info(f"Starting async operation in task: {asyncio.current_task().get_name()}")
```

## लोकी एकीकरण

### वास्तुकला

लॉगिंग सिस्टम, गैर-अवरुद्ध लोकी एकीकरण के लिए पायथन के अंतर्निहित `QueueHandler` और `QueueListener` का उपयोग करता है:

1. **क्यू हैंडलर**: लॉग को 500 संदेशों की कतार में रखा जाता है (गैर-अवरुद्ध)।
2. **बैकग्राउंड थ्रेड**: क्यू लिसनर एसिंक्रोनस रूप से लोकी को लॉग भेजता है।
3. **सुगम गिरावट**: यदि लोकी अनुपलब्ध है, तो कंसोल लॉगिंग जारी रहती है।

### स्वचालित लेबल

लोकी को भेजे गए प्रत्येक लॉग में शामिल हैं:
`processor`: प्रोसेसर पहचान (उदाहरण के लिए, `config-svc`, `text-completion`, `embeddings`)
`severity`: लॉग स्तर (डीबग, जानकारी, आदि)
`logger`: मॉड्यूल नाम (उदाहरण के लिए, `trustgraph.gateway.service`, `trustgraph.agent.react.service`)

### कस्टम लेबल

`extra` पैरामीटर के माध्यम से कस्टम लेबल जोड़ें:

```python
logger.info("User action", extra={
    'tags': {
        'user_id': user_id,
        'action': 'document_upload',
        'collection': collection_name
    }
})
```

### लोकी में लॉग की खोज

```logql
# All logs from a specific processor (recommended - matches Prometheus metrics)
{processor="config-svc"}
{processor="text-completion"}
{processor="embeddings"}

# Error logs from a specific processor
{processor="config-svc", severity="ERROR"}

# Error logs from all processors
{severity="ERROR"}

# Logs from a specific processor with text filter
{processor="text-completion"} |= "Processing"

# All logs from API gateway
{processor="api-gateway"}

# Logs from processors matching pattern
{processor=~".*-completion"}

# Logs with custom tags
{processor="api-gateway"} | json | user_id="12345"
```

### सुचारू रूप से कार्यक्षमता में कमी

यदि लोकी अनुपलब्ध है या `python-logging-loki` स्थापित नहीं है:
कंसोल पर चेतावनी संदेश प्रदर्शित किया जाता है
कंसोल लॉगिंग सामान्य रूप से जारी रहता है
एप्लिकेशन चलता रहता है
लोकी कनेक्शन के लिए कोई पुनः प्रयास तर्क नहीं (तुरंत विफल, सुचारू रूप से कार्यक्षमता में कमी)

## परीक्षण

परीक्षण के दौरान, एक अलग लॉगिंग कॉन्फ़िगरेशन का उपयोग करने पर विचार करें:

```python
# In test setup
import logging

# Reduce noise during tests
logging.getLogger().setLevel(logging.WARNING)

# Or disable Loki for tests
setup_logging({'log_level': 'WARNING', 'loki_enabled': False})
```

## निगरानी एकीकरण

### मानक प्रारूप
सभी लॉग एक सुसंगत प्रारूप का उपयोग करते हैं:
```
2025-01-09 10:30:45,123 - trustgraph.gateway.service - INFO - Request processed
```

प्रारूप घटक:
टाइमस्टैम्प (मिलीसेकंड के साथ आईएसओ प्रारूप)
लॉगर नाम (मॉड्यूल पथ)
लॉग स्तर
संदेश

### निगरानी के लिए लोकी प्रश्न

सामान्य निगरानी प्रश्न:

```logql
# Error rate by processor
rate({severity="ERROR"}[5m]) by (processor)

# Top error-producing processors
topk(5, count_over_time({severity="ERROR"}[1h]) by (processor))

# Recent errors with processor name
{severity="ERROR"} | line_format "{{.processor}}: {{.message}}"

# All agent processors
{processor=~".*agent.*"} |= "exception"

# Specific processor error count
count_over_time({processor="config-svc", severity="ERROR"}[1h])
```

## सुरक्षा संबंधी विचार

**कभी भी संवेदनशील जानकारी लॉग न करें** (पासवर्ड, एपीआई कुंजियाँ, व्यक्तिगत डेटा, टोकन)
लॉगिंग से पहले **उपयोगकर्ता इनपुट को साफ़ करें**
संवेदनशील फ़ील्ड के लिए **प्लेसहोल्डर का उपयोग करें**: `user_id=****1234`
**लोकी प्रमाणीकरण**: सुरक्षित परिनियोजन के लिए `--loki-username` और `--loki-password` का उपयोग करें
**सुरक्षित परिवहन**: उत्पादन में लोकी यूआरएल के लिए HTTPS का उपयोग करें: `https://loki.prod:3100/loki/api/v1/push`

## निर्भरताएँ

केंद्रीकृत लॉगिंग मॉड्यूल को निम्नलिखित की आवश्यकता है:
`python-logging-loki` - लोकी एकीकरण के लिए (वैकल्पिक, यदि अनुपलब्ध हो तो सुचारू गिरावट)

पहले से ही `trustgraph-base/pyproject.toml` और `requirements.txt` में शामिल है।

## माइग्रेशन पथ

मौजूदा कोड के लिए:

1. **AsyncProcessor का उपयोग कर रहे सेवाएँ**: कोई बदलाव आवश्यक नहीं, लोकी समर्थन स्वचालित है
2. **AsyncProcessor का उपयोग नहीं कर रही सेवाएँ** (api-gateway, mcp-server): पहले से ही अपडेट किया गया है
3. **CLI उपकरण**: दायरे से बाहर - print() या साधारण लॉगिंग का उपयोग जारी रखें

### print() से लॉगिंग तक:
```python
# Before
print(f"Processing document {doc_id}")

# After
logger = logging.getLogger(__name__)
logger.info(f"Processing document {doc_id}")
```

## कॉन्फ़िगरेशन सारांश

| तर्क | डिफ़ॉल्ट | पर्यावरण चर | विवरण |
|----------|---------|---------------------|-------------|
| `--log-level` | `INFO` | - | कंसोल और लोकी लॉग स्तर |
| `--loki-enabled` | `True` | - | लोकी लॉगिंग सक्षम करें |
| `--loki-url` | `http://loki:3100/loki/api/v1/push` | `LOKI_URL` | लोकी पुश एंडपॉइंट |
| `--loki-username` | `None` | `LOKI_USERNAME` | लोकी ऑथ उपयोगकर्ता नाम |
| `--loki-password` | `None` | `LOKI_PASSWORD` | लोकी ऑथ पासवर्ड |
