---
layout: default
title: "पायथन एपीआई रिफैक्टर तकनीकी विनिर्देश"
parent: "Hindi (Beta)"
---

# पायथन एपीआई रिफैक्टर तकनीकी विनिर्देश

> **Beta Translation:** This document was translated via Machine Learning and as such may not be 100% accurate. All non-English languages are currently classified as Beta.

## अवलोकन

यह विनिर्देश ट्रस्टग्राफ पायथन एपीआई क्लाइंट लाइब्रेरी का एक व्यापक रिफैक्टर है, जिसका उद्देश्य एपीआई गेटवे के साथ सुविधा समानता प्राप्त करना और आधुनिक रीयल-टाइम संचार पैटर्न के लिए समर्थन जोड़ना है।

यह रिफैक्टर चार प्राथमिक उपयोग मामलों को संबोधित करता है:

1. **स्ट्रीमिंग एलएलएम इंटरैक्शन**: एलएलएम प्रतिक्रियाओं (एजेंट, ग्राफ आरएजी, दस्तावेज़ आरएजी, टेक्स्ट कंप्लीशन, प्रॉम्प्ट) का रीयल-टाइम स्ट्रीमिंग सक्षम करें, जिसमें ~60 गुना कम विलंबता हो (पहले टोकन के लिए 500ms बनाम 30s)।
2. **बल्क डेटा ऑपरेशन**: बड़े पैमाने पर नॉलेज ग्राफ प्रबंधन के लिए ट्रिपल, ग्राफ एम्बेडिंग और दस्तावेज़ एम्बेडिंग के कुशल बल्क आयात/निर्यात का समर्थन करें।
3. **सुविधा समानता**: सुनिश्चित करें कि प्रत्येक एपीआई गेटवे एंडपॉइंट के लिए एक संबंधित पायथन एपीआई विधि है, जिसमें ग्राफ एम्बेडिंग क्वेरी शामिल है।
4. **लगातार कनेक्शन**: मल्टीप्लेक्स अनुरोधों और कम कनेक्शन ओवरहेड के लिए वेबसॉकेट-आधारित संचार को सक्षम करें।

## लक्ष्य

**सुविधा समानता**: प्रत्येक गेटवे एपीआई सेवा के लिए एक संबंधित पायथन एपीआई विधि है।
**स्ट्रीमिंग समर्थन**: सभी स्ट्रीमिंग-सक्षम सेवाओं (एजेंट, आरएजी, टेक्स्ट कंप्लीशन, प्रॉम्प्ट) पायथन एपीआई में स्ट्रीमिंग का समर्थन करते हैं।
**वेबसॉकेट ट्रांसपोर्ट**: लगातार कनेक्शन और मल्टीप्लेक्सिंग के लिए वैकल्पिक वेबसॉकेट ट्रांसपोर्ट लेयर जोड़ें।
**बल्क ऑपरेशन**: ट्रिपल, ग्राफ एम्बेडिंग और दस्तावेज़ एम्बेडिंग के लिए कुशल बल्क आयात/निर्यात जोड़ें।
**पूर्ण एसिंक समर्थन**: सभी इंटरफेस (REST, वेबसॉकेट, बल्क ऑपरेशन, मेट्रिक्स) के लिए पूर्ण एसिंक/अवेट कार्यान्वयन।
**पिछला संगतता**: मौजूदा कोड बिना किसी संशोधन के काम करना जारी रखता है।
**टाइप सुरक्षा**: डेटाक्लासेस और टाइप हिंट के साथ टाइप-सुरक्षित इंटरफेस बनाए रखें।
**प्रगतिशील संवर्द्धन**: स्ट्रीमिंग और एसिंक स्पष्ट इंटरफेस चयन के माध्यम से वैकल्पिक हैं।
**प्रदर्शन**: स्ट्रीमिंग ऑपरेशनों के लिए 60 गुना विलंबता में सुधार प्राप्त करें।
**आधुनिक पायथन**: अधिकतम लचीलेपन के लिए सिंक और एसिंक दोनों प्रतिमानों के लिए समर्थन।

## पृष्ठभूमि

### वर्तमान स्थिति

पायथन एपीआई (`trustgraph-base/trustgraph/api/`) एक REST-ओनली क्लाइंट लाइब्रेरी है जिसमें निम्नलिखित मॉड्यूल हैं:

`flow.py`: फ्लो प्रबंधन और फ्लो-स्कोप सेवाओं (50 विधियाँ)
`library.py`: दस्तावेज़ लाइब्रेरी ऑपरेशन (9 विधियाँ)
`knowledge.py`: केजी कोर प्रबंधन (4 विधियाँ)
`collection.py`: संग्रह मेटाडेटा (3 विधियाँ)
`config.py`: कॉन्फ़िगरेशन प्रबंधन (6 विधियाँ)
`types.py`: डेटा टाइप परिभाषाएँ (5 डेटाक्लास)

**कुल ऑपरेशन**: 50/59 (85% कवरेज)

### वर्तमान सीमाएँ

**गायब ऑपरेशन**:
ग्राफ एम्बेडिंग क्वेरी (ग्राफ संस्थाओं पर सिमेंटिक खोज)
ट्रिपल, ग्राफ एम्बेडिंग, दस्तावेज़ एम्बेडिंग, एंटिटी कॉन्टेक्स्ट, ऑब्जेक्ट के लिए बल्क आयात/निर्यात
मेट्रिक्स एंडपॉइंट

**गायब क्षमताएँ**:
एलएलएम सेवाओं के लिए स्ट्रीमिंग समर्थन
वेबसॉकेट ट्रांसपोर्ट
मल्टीप्लेक्स समवर्ती अनुरोध
लगातार कनेक्शन

**प्रदर्शन संबंधी समस्याएँ**:
एलएलएम इंटरैक्शन के लिए उच्च विलंबता (~30s समय-से-पहला-टोकन)
अक्षम बल्क डेटा ट्रांसफर (प्रति आइटम REST अनुरोध)
कई क्रमिक ऑपरेशनों के लिए कनेक्शन ओवरहेड

**उपयोगकर्ता अनुभव संबंधी समस्याएँ**:
एलएलएम पीढ़ी के दौरान कोई रीयल-टाइम प्रतिक्रिया नहीं
लंबे समय तक चलने वाले एलएलएम ऑपरेशनों को रद्द नहीं किया जा सकता है
बल्क ऑपरेशनों के लिए खराब स्केलेबिलिटी

### प्रभाव

नवंबर 2024 में गेटवे एपीआई में स्ट्रीमिंग संवर्द्धन ने एलएलएम इंटरैक्शन के लिए 60 गुना विलंबता में सुधार (पहले टोकन के लिए 500ms बनाम 30s) प्रदान किया, लेकिन पायथन एपीआई उपयोगकर्ता इस क्षमता का लाभ नहीं उठा सकते हैं। इससे पायथन और गैर-पायथन उपयोगकर्ताओं के बीच एक महत्वपूर्ण अनुभव अंतर पैदा होता है।

## तकनीकी डिजाइन

### वास्तुकला

रिफैक्टर किए गए पायथन एपीआई विभिन्न संचार पैटर्न के लिए अलग-अलग ऑब्जेक्ट के साथ एक **मॉड्यूलर इंटरफेस दृष्टिकोण** का उपयोग करता है। सभी इंटरफेस सिंक्रोनस और एसिंक्रोनस दोनों रूपों में उपलब्ध हैं:

1. **REST इंटरफेस** (मौजूदा, संवर्धित)
   **सिंक**: `api.flow()`, `api.library()`, `api.knowledge()`, `api.collection()`, `api.config()`
   **एसिंक**: `api.async_flow()`
   सिंक्रोनस/एसिंक्रोनस अनुरोध/प्रतिक्रिया
   सरल कनेक्शन मॉडल
   पिछड़े संगतता के लिए डिफ़ॉल्ट

2. **वेबसॉकेट इंटरफेस** (नया)
   **सिंक**: `api.socket()`
   **एसिंक**: `api.async_socket()`
   लगातार कनेक्शन
   मल्टीप्लेक्स अनुरोध
   स्ट्रीमिंग समर्थन
   जहां कार्यक्षमता ओवरलैप होती है, वहां REST के समान विधि हस्ताक्षर

3. **बल्क ऑपरेशन इंटरफेस** (नया)
   **सिंक**: `api.bulk()`
   **एसिंक**: `api.async_bulk()`
   दक्षता के लिए वेबसॉकेट-आधारित
   आयात/निर्यात के लिए Iterator/AsyncIterator-आधारित
   बड़े डेटासेट को संभालता है

4. **मेट्रिक्स इंटरफेस** (नया)
   **सिंक**: `api.metrics()`
   **एसिंक**: `api.async_metrics()`
   प्रोमेथियस मेट्रिक्स एक्सेस

```python
import asyncio

# Synchronous interfaces
api = Api(url="http://localhost:8088/")

# REST (existing, unchanged)
flow = api.flow().id("default")
response = flow.agent(question="...", user="...")

# WebSocket (new)
socket_flow = api.socket().flow("default")
response = socket_flow.agent(question="...", user="...")
for chunk in socket_flow.agent(question="...", user="...", streaming=True):
    print(chunk)

# Bulk operations (new)
bulk = api.bulk()
bulk.import_triples(flow="default", triples=triple_generator())

# Asynchronous interfaces
async def main():
    api = Api(url="http://localhost:8088/")

    # Async REST (new)
    flow = api.async_flow().id("default")
    response = await flow.agent(question="...", user="...")

    # Async WebSocket (new)
    socket_flow = api.async_socket().flow("default")
    async for chunk in socket_flow.agent(question="...", streaming=True):
        print(chunk)

    # Async bulk operations (new)
    bulk = api.async_bulk()
    await bulk.import_triples(flow="default", triples=async_triple_generator())

asyncio.run(main())
```

**मुख्य डिज़ाइन सिद्धांत:**
**सभी इंटरफेस के लिए समान URL:** `Api(url="http://localhost:8088/")` सभी के लिए काम करता है।
**सिंक/एसिंक्रोनस समरूपता:** प्रत्येक इंटरफेस में सिंक और एसिंक्रोनस दोनों संस्करण होते हैं, जिनमें समान मेथड सिग्नेचर होते हैं।
**समान सिग्नेचर:** जहां कार्यक्षमता ओवरलैप होती है, REST और WebSocket, सिंक और एसिंक्रोनस के बीच मेथड सिग्नेचर समान होते हैं।
**प्रगतिशील संवर्द्धन:** आवश्यकताओं के आधार पर इंटरफेस चुनें (सरल कार्यों के लिए REST, स्ट्रीमिंग के लिए WebSocket, बड़े डेटासेट के लिए बल्क, आधुनिक फ्रेमवर्क के लिए एसिंक्रोनस)।
**स्पष्ट इरादा:** `api.socket()` WebSocket को दर्शाता है, `api.async_socket()` एसिंक्रोनस WebSocket को दर्शाता है।
**पिछड़े संगत:** मौजूदा कोड अपरिवर्तित रहता है।

### घटक

#### 1. कोर एपीआई क्लास (संशोधित)

मॉड्यूल: `trustgraph-base/trustgraph/api/api.py`

**संवर्धित एपीआई क्लास:**

```python
class Api:
    def __init__(self, url: str, timeout: int = 60, token: Optional[str] = None):
        self.url = url
        self.timeout = timeout
        self.token = token  # Optional bearer token for REST, query param for WebSocket
        self._socket_client = None
        self._bulk_client = None
        self._async_flow = None
        self._async_socket_client = None
        self._async_bulk_client = None

    # Existing synchronous methods (unchanged)
    def flow(self) -> Flow:
        """Synchronous REST-based flow interface"""
        pass

    def library(self) -> Library:
        """Synchronous REST-based library interface"""
        pass

    def knowledge(self) -> Knowledge:
        """Synchronous REST-based knowledge interface"""
        pass

    def collection(self) -> Collection:
        """Synchronous REST-based collection interface"""
        pass

    def config(self) -> Config:
        """Synchronous REST-based config interface"""
        pass

    # New synchronous methods
    def socket(self) -> SocketClient:
        """Synchronous WebSocket-based interface for streaming operations"""
        if self._socket_client is None:
            self._socket_client = SocketClient(self.url, self.timeout, self.token)
        return self._socket_client

    def bulk(self) -> BulkClient:
        """Synchronous bulk operations interface for import/export"""
        if self._bulk_client is None:
            self._bulk_client = BulkClient(self.url, self.timeout, self.token)
        return self._bulk_client

    def metrics(self) -> Metrics:
        """Synchronous metrics interface"""
        return Metrics(self.url, self.timeout, self.token)

    # New asynchronous methods
    def async_flow(self) -> AsyncFlow:
        """Asynchronous REST-based flow interface"""
        if self._async_flow is None:
            self._async_flow = AsyncFlow(self.url, self.timeout, self.token)
        return self._async_flow

    def async_socket(self) -> AsyncSocketClient:
        """Asynchronous WebSocket-based interface for streaming operations"""
        if self._async_socket_client is None:
            self._async_socket_client = AsyncSocketClient(self.url, self.timeout, self.token)
        return self._async_socket_client

    def async_bulk(self) -> AsyncBulkClient:
        """Asynchronous bulk operations interface for import/export"""
        if self._async_bulk_client is None:
            self._async_bulk_client = AsyncBulkClient(self.url, self.timeout, self.token)
        return self._async_bulk_client

    def async_metrics(self) -> AsyncMetrics:
        """Asynchronous metrics interface"""
        return AsyncMetrics(self.url, self.timeout, self.token)

    # Resource management
    def close(self) -> None:
        """Close all synchronous connections"""
        if self._socket_client:
            self._socket_client.close()
        if self._bulk_client:
            self._bulk_client.close()

    async def aclose(self) -> None:
        """Close all asynchronous connections"""
        if self._async_socket_client:
            await self._async_socket_client.aclose()
        if self._async_bulk_client:
            await self._async_bulk_client.aclose()
        if self._async_flow:
            await self._async_flow.aclose()

    def __enter__(self):
        return self

    def __exit__(self, *args):
        self.close()

    async def __aenter__(self):
        return self

    async def __aexit__(self, *args):
        await self.aclose()
```

#### 2. सिंक्रोनस वेबसॉकेट क्लाइंट

मॉड्यूल: `trustgraph-base/trustgraph/api/socket_client.py` (नया)

**SocketClient क्लास:**

```python
class SocketClient:
    """Synchronous WebSocket client"""
    def __init__(self, url: str, timeout: int, token: Optional[str]):
        self.url = self._convert_to_ws_url(url)
        self.timeout = timeout
        self.token = token
        self._connection = None
        self._request_counter = 0

    def flow(self, flow_id: str) -> SocketFlowInstance:
        """Get flow instance for WebSocket operations"""
        return SocketFlowInstance(self, flow_id)

    def _connect(self) -> WebSocket:
        """Establish WebSocket connection (lazy)"""
        # Uses asyncio.run() internally to wrap async websockets library
        pass

    def _send_request(
        self,
        service: str,
        flow: Optional[str],
        request: Dict[str, Any],
        streaming: bool = False
    ) -> Union[Dict[str, Any], Iterator[Dict[str, Any]]]:
        """Send request and handle response/streaming"""
        # Synchronous wrapper around async WebSocket calls
        pass

    def close(self) -> None:
        """Close WebSocket connection"""
        pass

class SocketFlowInstance:
    """Synchronous WebSocket flow instance with same interface as REST FlowInstance"""
    def __init__(self, client: SocketClient, flow_id: str):
        self.client = client
        self.flow_id = flow_id

    # Same method signatures as FlowInstance
    def agent(
        self,
        question: str,
        user: str,
        state: Optional[Dict[str, Any]] = None,
        group: Optional[str] = None,
        history: Optional[List[Dict[str, Any]]] = None,
        streaming: bool = False,
        **kwargs
    ) -> Union[Dict[str, Any], Iterator[Dict[str, Any]]]:
        """Agent with optional streaming"""
        pass

    def text_completion(
        self,
        system: str,
        prompt: str,
        streaming: bool = False,
        **kwargs
    ) -> Union[str, Iterator[str]]:
        """Text completion with optional streaming"""
        pass

    # ... similar for graph_rag, document_rag, prompt, etc.
```

**मुख्य विशेषताएं:**
आलसी कनेक्शन (केवल पहले अनुरोध भेजे जाने पर कनेक्ट होता है)
अनुरोध मल्टीप्लेक्सिंग (एक साथ 15 तक)
डिस्कनेक्ट होने पर स्वचालित पुनः कनेक्शन
स्ट्रीमिंग प्रतिक्रिया पार्सिंग
थ्रेड-सुरक्षित संचालन
एसिंक्रोनस वेबसॉकेट लाइब्रेरी के चारों ओर सिंक्रोनस रैपर

#### 3. एसिंक्रोनस वेबसॉकेट क्लाइंट

मॉड्यूल: `trustgraph-base/trustgraph/api/async_socket_client.py` (नया)

**AsyncSocketClient क्लास:**

```python
class AsyncSocketClient:
    """Asynchronous WebSocket client"""
    def __init__(self, url: str, timeout: int, token: Optional[str]):
        self.url = self._convert_to_ws_url(url)
        self.timeout = timeout
        self.token = token
        self._connection = None
        self._request_counter = 0

    def flow(self, flow_id: str) -> AsyncSocketFlowInstance:
        """Get async flow instance for WebSocket operations"""
        return AsyncSocketFlowInstance(self, flow_id)

    async def _connect(self) -> WebSocket:
        """Establish WebSocket connection (lazy)"""
        # Native async websockets library
        pass

    async def _send_request(
        self,
        service: str,
        flow: Optional[str],
        request: Dict[str, Any],
        streaming: bool = False
    ) -> Union[Dict[str, Any], AsyncIterator[Dict[str, Any]]]:
        """Send request and handle response/streaming"""
        pass

    async def aclose(self) -> None:
        """Close WebSocket connection"""
        pass

class AsyncSocketFlowInstance:
    """Asynchronous WebSocket flow instance"""
    def __init__(self, client: AsyncSocketClient, flow_id: str):
        self.client = client
        self.flow_id = flow_id

    # Same method signatures as FlowInstance (but async)
    async def agent(
        self,
        question: str,
        user: str,
        state: Optional[Dict[str, Any]] = None,
        group: Optional[str] = None,
        history: Optional[List[Dict[str, Any]]] = None,
        streaming: bool = False,
        **kwargs
    ) -> Union[Dict[str, Any], AsyncIterator[Dict[str, Any]]]:
        """Agent with optional streaming"""
        pass

    async def text_completion(
        self,
        system: str,
        prompt: str,
        streaming: bool = False,
        **kwargs
    ) -> Union[str, AsyncIterator[str]]:
        """Text completion with optional streaming"""
        pass

    # ... similar for graph_rag, document_rag, prompt, etc.
```

**मुख्य विशेषताएं:**
मूल एसिंक्रोनस/अवेट समर्थन
एसिंक्रोनस अनुप्रयोगों के लिए कुशल (फास्टएपीआई, एआईओएचटीटीपी)
कोई थ्रेड अवरोधन नहीं
सिंक्रोनस संस्करण के समान इंटरफ़ेस
स्ट्रीमिंग के लिए AsyncIterator

#### 4. सिंक्रोनस बल्क ऑपरेशंस क्लाइंट

मॉड्यूल: `trustgraph-base/trustgraph/api/bulk_client.py` (नया)

**BulkClient क्लास:**

```python
class BulkClient:
    """Synchronous bulk operations client"""
    def __init__(self, url: str, timeout: int, token: Optional[str]):
        self.url = self._convert_to_ws_url(url)
        self.timeout = timeout
        self.token = token

    def import_triples(
        self,
        flow: str,
        triples: Iterator[Triple],
        **kwargs
    ) -> None:
        """Bulk import triples via WebSocket"""
        pass

    def export_triples(
        self,
        flow: str,
        **kwargs
    ) -> Iterator[Triple]:
        """Bulk export triples via WebSocket"""
        pass

    def import_graph_embeddings(
        self,
        flow: str,
        embeddings: Iterator[Dict[str, Any]],
        **kwargs
    ) -> None:
        """Bulk import graph embeddings via WebSocket"""
        pass

    def export_graph_embeddings(
        self,
        flow: str,
        **kwargs
    ) -> Iterator[Dict[str, Any]]:
        """Bulk export graph embeddings via WebSocket"""
        pass

    # ... similar for document embeddings, entity contexts, objects

    def close(self) -> None:
        """Close connections"""
        pass
```

**मुख्य विशेषताएं:**
निरंतर मेमोरी उपयोग के लिए इटरेटर-आधारित।
प्रत्येक ऑपरेशन के लिए समर्पित वेबसॉकेट कनेक्शन।
प्रगति ट्रैकिंग (वैकल्पिक कॉलबैक)।
आंशिक सफलता रिपोर्टिंग के साथ त्रुटि प्रबंधन।

#### 5. एसिंक्रोनस बल्क ऑपरेशंस क्लाइंट

मॉड्यूल: `trustgraph-base/trustgraph/api/async_bulk_client.py` (नया)

**AsyncBulkClient क्लास:**

```python
class AsyncBulkClient:
    """Asynchronous bulk operations client"""
    def __init__(self, url: str, timeout: int, token: Optional[str]):
        self.url = self._convert_to_ws_url(url)
        self.timeout = timeout
        self.token = token

    async def import_triples(
        self,
        flow: str,
        triples: AsyncIterator[Triple],
        **kwargs
    ) -> None:
        """Bulk import triples via WebSocket"""
        pass

    async def export_triples(
        self,
        flow: str,
        **kwargs
    ) -> AsyncIterator[Triple]:
        """Bulk export triples via WebSocket"""
        pass

    async def import_graph_embeddings(
        self,
        flow: str,
        embeddings: AsyncIterator[Dict[str, Any]],
        **kwargs
    ) -> None:
        """Bulk import graph embeddings via WebSocket"""
        pass

    async def export_graph_embeddings(
        self,
        flow: str,
        **kwargs
    ) -> AsyncIterator[Dict[str, Any]]:
        """Bulk export graph embeddings via WebSocket"""
        pass

    # ... similar for document embeddings, entity contexts, objects

    async def aclose(self) -> None:
        """Close connections"""
        pass
```

**मुख्य विशेषताएं:**
निरंतर मेमोरी उपयोग के लिए AsyncIterator-आधारित।
एसिंक्रोनस अनुप्रयोगों के लिए कुशल।
मूल एसिंक्रोनस/अवेट समर्थन।
सिंक्रोनस संस्करण के समान इंटरफ़ेस।

#### 6. REST फ्लो एपीआई (सिंक्रोनस - अपरिवर्तित)

मॉड्यूल: `trustgraph-base/trustgraph/api/flow.py`

REST फ्लो एपीआई पिछली अनुकूलता के लिए **पूरी तरह से अपरिवर्तित** रहता है। सभी मौजूदा विधियां काम करना जारी रखती हैं:

`Flow.list()`, `Flow.start()`, `Flow.stop()`, आदि।
`FlowInstance.agent()`, `FlowInstance.text_completion()`, `FlowInstance.graph_rag()`, आदि।
सभी मौजूदा हस्ताक्षर और रिटर्न प्रकार संरक्षित।

**नया:** सुविधा समानता के लिए REST फ्लोइंस्टेंस में `graph_embeddings_query()` जोड़ें:

```python
class FlowInstance:
    # All existing methods unchanged...

    # New: Graph embeddings query (REST)
    def graph_embeddings_query(
        self,
        text: str,
        user: str,
        collection: str,
        limit: int = 10,
        **kwargs
    ) -> List[Dict[str, Any]]:
        """Query graph embeddings for semantic search"""
        # Calls POST /api/v1/flow/{flow}/service/graph-embeddings
        pass
```

#### 7. एसिंक्रोनस रेस्ट फ्लो एपीआई

मॉड्यूल: `trustgraph-base/trustgraph/api/async_flow.py` (नया)

**AsyncFlow और AsyncFlowInstance क्लास:**

```python
class AsyncFlow:
    """Asynchronous REST-based flow interface"""
    def __init__(self, url: str, timeout: int, token: Optional[str]):
        self.url = url
        self.timeout = timeout
        self.token = token

    async def list(self) -> List[Dict[str, Any]]:
        """List all flows"""
        pass

    async def get(self, id: str) -> Dict[str, Any]:
        """Get flow definition"""
        pass

    async def start(self, class_name: str, id: str, description: str, parameters: Dict) -> None:
        """Start a flow"""
        pass

    async def stop(self, id: str) -> None:
        """Stop a flow"""
        pass

    def id(self, flow_id: str) -> AsyncFlowInstance:
        """Get async flow instance"""
        return AsyncFlowInstance(self.url, self.timeout, self.token, flow_id)

    async def aclose(self) -> None:
        """Close connection"""
        pass

class AsyncFlowInstance:
    """Asynchronous REST flow instance"""

    async def agent(
        self,
        question: str,
        user: str,
        state: Optional[Dict[str, Any]] = None,
        group: Optional[str] = None,
        history: Optional[List[Dict[str, Any]]] = None,
        **kwargs
    ) -> Dict[str, Any]:
        """Async agent execution"""
        pass

    async def text_completion(
        self,
        system: str,
        prompt: str,
        **kwargs
    ) -> str:
        """Async text completion"""
        pass

    async def graph_rag(
        self,
        question: str,
        user: str,
        collection: str,
        **kwargs
    ) -> str:
        """Async graph RAG"""
        pass

    # ... all other FlowInstance methods as async versions
```

**मुख्य विशेषताएं:**
देशी एसिंक्रोनस HTTP, `aiohttp` या `httpx` का उपयोग करके।
सिंक्रोनस REST API के समान मेथड सिग्नेचर।
कोई स्ट्रीमिंग नहीं (स्ट्रीमिंग के लिए `async_socket()` का उपयोग करें)।
एसिंक्रोनस अनुप्रयोगों के लिए कुशल।

#### 8. मेट्रिक्स एपीआई

मॉड्यूल: `trustgraph-base/trustgraph/api/metrics.py` (नया)

**सिंक्रोनस मेट्रिक्स:**

```python
class Metrics:
    def __init__(self, url: str, timeout: int, token: Optional[str]):
        self.url = url
        self.timeout = timeout
        self.token = token

    def get(self) -> str:
        """Get Prometheus metrics as text"""
        # Call GET /api/metrics
        pass
```

**अतुल्यकालिक मेट्रिक्स:**

```python
class AsyncMetrics:
    def __init__(self, url: str, timeout: int, token: Optional[str]):
        self.url = url
        self.timeout = timeout
        self.token = token

    async def get(self) -> str:
        """Get Prometheus metrics as text"""
        # Call GET /api/metrics
        pass
```

#### 9. उन्नत प्रकार (Enhanced Types)

मॉड्यूल: `trustgraph-base/trustgraph/api/types.py` (संशोधित)

**नए प्रकार (New Types):**

```python
from typing import Iterator, Union, Dict, Any
import dataclasses

@dataclasses.dataclass
class StreamingChunk:
    """Base class for streaming chunks"""
    content: str
    end_of_message: bool = False

@dataclasses.dataclass
class AgentThought(StreamingChunk):
    """Agent reasoning chunk"""
    chunk_type: str = "thought"

@dataclasses.dataclass
class AgentObservation(StreamingChunk):
    """Agent tool observation chunk"""
    chunk_type: str = "observation"

@dataclasses.dataclass
class AgentAnswer(StreamingChunk):
    """Agent final answer chunk"""
    chunk_type: str = "final-answer"
    end_of_dialog: bool = False

@dataclasses.dataclass
class RAGChunk(StreamingChunk):
    """RAG streaming chunk"""
    end_of_stream: bool = False
    error: Optional[Dict[str, str]] = None

# Type aliases for clarity
AgentStream = Iterator[Union[AgentThought, AgentObservation, AgentAnswer]]
RAGStream = Iterator[RAGChunk]
CompletionStream = Iterator[str]
```

#### 6. मेट्रिक्स एपीआई

मॉड्यूल: `trustgraph-base/trustgraph/api/metrics.py` (नया)

```python
class Metrics:
    def __init__(self, url: str, timeout: int, token: Optional[str]):
        self.url = url
        self.timeout = timeout
        self.token = token

    def get(self) -> str:
        """Get Prometheus metrics as text"""
        # Call GET /api/metrics
        pass
```

### कार्यान्वयन दृष्टिकोण

#### चरण 1: मुख्य एपीआई संवर्धन (सप्ताह 1)

1. `socket()`, `bulk()`, और `metrics()` विधियों को `Api` वर्ग में जोड़ें
2. वेबसॉकेट और बल्क क्लाइंट के लिए लेज़ी इनिशियलाइज़ेशन लागू करें
3. संदर्भ प्रबंधक समर्थन जोड़ें (`__enter__`, `__exit__`)
4. सफाई के लिए `close()` विधि जोड़ें
5. एपीआई वर्ग संवर्धनों के लिए यूनिट परीक्षण जोड़ें
6. पिछड़े अनुकूलता की जांच करें

**पिछड़ी अनुकूलता**: कोई ब्रेकिंग परिवर्तन नहीं। केवल नई विधियाँ।

#### चरण 2: वेबसॉकेट क्लाइंट (सप्ताह 2-3)

1. कनेक्शन प्रबंधन के साथ `SocketClient` वर्ग लागू करें
2. `SocketFlowInstance` को `FlowInstance` के समान विधि हस्ताक्षर के साथ लागू करें
3. अनुरोध मल्टीप्लेक्सिंग समर्थन जोड़ें (अधिकतम 15 समवर्ती)
4. विभिन्न चंक प्रकारों के लिए स्ट्रीमिंग प्रतिक्रिया पार्सिंग जोड़ें
5. स्वचालित पुन: कनेक्शन तर्क जोड़ें
6. यूनिट और एकीकरण परीक्षण जोड़ें
7. वेबसॉकेट उपयोग पैटर्न का दस्तावेजीकरण करें

**पिछड़ी अनुकूलता**: केवल नया इंटरफ़ेस। मौजूदा कोड पर कोई प्रभाव नहीं।

#### चरण 3: स्ट्रीमिंग समर्थन (सप्ताह 3-4)

1. स्ट्रीमिंग चंक प्रकार कक्षाएं जोड़ें (`AgentThought`, `AgentObservation`, `AgentAnswer`, `RAGChunk`)
2. `SocketClient` में स्ट्रीमिंग प्रतिक्रिया पार्सिंग लागू करें
3. `SocketFlowInstance` में सभी एलएलएम विधियों में स्ट्रीमिंग पैरामीटर जोड़ें
4. स्ट्रीमिंग के दौरान त्रुटि मामलों को संभालें
5. स्ट्रीमिंग के लिए यूनिट और एकीकरण परीक्षण जोड़ें
6. दस्तावेज़ में स्ट्रीमिंग उदाहरण जोड़ें

**पिछड़ी अनुकूलता**: केवल नया इंटरफ़ेस। मौजूदा रेस्ट एपीआई अपरिवर्तित।

#### चरण 4: बल्क ऑपरेशन (सप्ताह 4-5)

1. `BulkClient` वर्ग लागू करें
2. ट्रिपल, एम्बेडिंग, संदर्भ, ऑब्जेक्ट के लिए बल्क आयात/निर्यात विधियाँ जोड़ें
3. निरंतर मेमोरी के लिए इटरेटर-आधारित प्रसंस्करण लागू करें
4. प्रगति ट्रैकिंग जोड़ें (वैकल्पिक कॉलबैक)
5. आंशिक सफलता रिपोर्टिंग के साथ त्रुटि हैंडलिंग जोड़ें
6. यूनिट और एकीकरण परीक्षण जोड़ें
7. बल्क ऑपरेशन उदाहरण जोड़ें

**पिछड़ी अनुकूलता**: केवल नया इंटरफ़ेस। मौजूदा कोड पर कोई प्रभाव नहीं।

#### चरण 5: सुविधा समानता और पॉलिश (सप्ताह 5)

1. रेस्ट `FlowInstance` में `graph_embeddings_query()` जोड़ें
2. `Metrics` वर्ग लागू करें
3. व्यापक एकीकरण परीक्षण जोड़ें
4. प्रदर्शन बेंचमार्किंग
5. सभी दस्तावेज़ों को अपडेट करें
6. माइग्रेशन गाइड बनाएं

**पिछड़ी अनुकूलता**: केवल नई विधियाँ। मौजूदा कोड पर कोई प्रभाव नहीं।

### डेटा मॉडल

#### इंटरफ़ेस चयन

```python
# Single API instance, same URL for all interfaces
api = Api(url="http://localhost:8088/")

# Synchronous interfaces
rest_flow = api.flow().id("default")           # Sync REST
socket_flow = api.socket().flow("default")     # Sync WebSocket
bulk = api.bulk()                               # Sync bulk operations
metrics = api.metrics()                         # Sync metrics

# Asynchronous interfaces
async_rest_flow = api.async_flow().id("default")      # Async REST
async_socket_flow = api.async_socket().flow("default") # Async WebSocket
async_bulk = api.async_bulk()                          # Async bulk operations
async_metrics = api.async_metrics()                    # Async metrics
```

#### स्ट्रीमिंग प्रतिक्रिया प्रकार

**एजेंट स्ट्रीमिंग**:

```python
api = Api(url="http://localhost:8088/")

# REST interface - non-streaming (existing)
rest_flow = api.flow().id("default")
response = rest_flow.agent(question="What is ML?", user="user123")
print(response["response"])

# WebSocket interface - non-streaming (same signature)
socket_flow = api.socket().flow("default")
response = socket_flow.agent(question="What is ML?", user="user123")
print(response["response"])

# WebSocket interface - streaming (new)
for chunk in socket_flow.agent(question="What is ML?", user="user123", streaming=True):
    if isinstance(chunk, AgentThought):
        print(f"Thinking: {chunk.content}")
    elif isinstance(chunk, AgentObservation):
        print(f"Observed: {chunk.content}")
    elif isinstance(chunk, AgentAnswer):
        print(f"Answer: {chunk.content}")
        if chunk.end_of_dialog:
            break
```

**RAG स्ट्रीमिंग**:

```python
api = Api(url="http://localhost:8088/")

# REST interface - non-streaming (existing)
rest_flow = api.flow().id("default")
response = rest_flow.graph_rag(question="What is Python?", user="user123", collection="default")
print(response)

# WebSocket interface - streaming (new)
socket_flow = api.socket().flow("default")
for chunk in socket_flow.graph_rag(
    question="What is Python?",
    user="user123",
    collection="default",
    streaming=True
):
    print(chunk.content, end="", flush=True)
    if chunk.end_of_stream:
        break
```

**बल्क ऑपरेशन (सिंक्रोनस):**

```python
api = Api(url="http://localhost:8088/")

# Bulk import triples
def triple_generator():
    yield Triple(s="http://ex.com/alice", p="http://ex.com/type", o="Person")
    yield Triple(s="http://ex.com/alice", p="http://ex.com/name", o="Alice")
    yield Triple(s="http://ex.com/bob", p="http://ex.com/type", o="Person")

bulk = api.bulk()
bulk.import_triples(flow="default", triples=triple_generator())

# Bulk export triples
for triple in bulk.export_triples(flow="default"):
    print(f"{triple.s} -> {triple.p} -> {triple.o}")
```

**बल्क ऑपरेशन (असिंक्रोनस):**

```python
import asyncio

async def main():
    api = Api(url="http://localhost:8088/")

    # Async bulk import triples
    async def async_triple_generator():
        yield Triple(s="http://ex.com/alice", p="http://ex.com/type", o="Person")
        yield Triple(s="http://ex.com/alice", p="http://ex.com/name", o="Alice")
        yield Triple(s="http://ex.com/bob", p="http://ex.com/type", o="Person")

    bulk = api.async_bulk()
    await bulk.import_triples(flow="default", triples=async_triple_generator())

    # Async bulk export triples
    async for triple in bulk.export_triples(flow="default"):
        print(f"{triple.s} -> {triple.p} -> {triple.o}")

asyncio.run(main())
```

**एसिंक्रोनस रेस्ट उदाहरण:**

```python
import asyncio

async def main():
    api = Api(url="http://localhost:8088/")

    # Async REST flow operations
    flow = api.async_flow().id("default")
    response = await flow.agent(question="What is ML?", user="user123")
    print(response["response"])

asyncio.run(main())
```

**एसिंक्रोनस वेबसॉकेट स्ट्रीमिंग का उदाहरण**:

```python
import asyncio

async def main():
    api = Api(url="http://localhost:8088/")

    # Async WebSocket streaming
    socket = api.async_socket()
    flow = socket.flow("default")

    async for chunk in flow.agent(question="What is ML?", user="user123", streaming=True):
        if isinstance(chunk, AgentAnswer):
            print(chunk.content, end="", flush=True)
            if chunk.end_of_dialog:
                break

asyncio.run(main())
```

### एपीआई (APIs)

#### नए एपीआई (New APIs)

1. **कोर एपीआई क्लास (Core API Class):**
   **सिंक्रोनस (Synchronous):**
     `Api.socket()` - सिंक्रोनस वेबसॉकेट क्लाइंट प्राप्त करें (Get synchronous WebSocket client)
     `Api.bulk()` - सिंक्रोनस बल्क ऑपरेशंस क्लाइंट प्राप्त करें (Get synchronous bulk operations client)
     `Api.metrics()` - सिंक्रोनस मेट्रिक्स क्लाइंट प्राप्त करें (Get synchronous metrics client)
     `Api.close()` - सभी सिंक्रोनस कनेक्शन बंद करें (Close all synchronous connections)
     संदर्भ प्रबंधक समर्थन (Context manager support (`__enter__`, `__exit__`))
   **एसिंक्रोनस (Asynchronous):**
     `Api.async_flow()` - एसिंक्रोनस रेस्ट फ्लो क्लाइंट प्राप्त करें (Get asynchronous REST flow client)
     `Api.async_socket()` - एसिंक्रोनस वेबसॉकेट क्लाइंट प्राप्त करें (Get asynchronous WebSocket client)
     `Api.async_bulk()` - एसिंक्रोनस बल्क ऑपरेशंस क्लाइंट प्राप्त करें (Get asynchronous bulk operations client)
     `Api.async_metrics()` - एसिंक्रोनस मेट्रिक्स क्लाइंट प्राप्त करें (Get asynchronous metrics client)
     `Api.aclose()` - सभी एसिंक्रोनस कनेक्शन बंद करें (Close all asynchronous connections)
     एसिंक्रोनस संदर्भ प्रबंधक समर्थन (Async context manager support (`__aenter__`, `__aexit__`))

2. **सिंक्रोनस वेबसॉकेट क्लाइंट (Synchronous WebSocket Client):**
   `SocketClient.flow(flow_id)` - वेबसॉकेट फ्लो इंस्टेंस प्राप्त करें (Get WebSocket flow instance)
   `SocketFlowInstance.agent(..., streaming: bool = False)` - एजेंट, वैकल्पिक स्ट्रीमिंग के साथ (Agent with optional streaming)
   `SocketFlowInstance.text_completion(..., streaming: bool = False)` - टेक्स्ट कंप्लीशन, वैकल्पिक स्ट्रीमिंग के साथ (Text completion with optional streaming)
   `SocketFlowInstance.graph_rag(..., streaming: bool = False)` - ग्राफ आरएजी, वैकल्पिक स्ट्रीमिंग के साथ (Graph RAG with optional streaming)
   `SocketFlowInstance.document_rag(..., streaming: bool = False)` - डॉक्यूमेंट आरएजी, वैकल्पिक स्ट्रीमिंग के साथ (Document RAG with optional streaming)
   `SocketFlowInstance.prompt(..., streaming: bool = False)` - प्रॉम्प्ट, वैकल्पिक स्ट्रीमिंग के साथ (Prompt with optional streaming)
   `SocketFlowInstance.graph_embeddings_query()` - ग्राफ एम्बेडिंग क्वेरी (Graph embeddings query)
   सभी अन्य FlowInstance विधियाँ, समान हस्ताक्षर के साथ (All other FlowInstance methods with identical signatures)

3. **एसिंक्रोनस वेबसॉकेट क्लाइंट (Asynchronous WebSocket Client):**
   `AsyncSocketClient.flow(flow_id)` - एसिंक्रोनस वेबसॉकेट फ्लो इंस्टेंस प्राप्त करें (Get async WebSocket flow instance)
   `AsyncSocketFlowInstance.agent(..., streaming: bool = False)` - एसिंक्रोनस एजेंट, वैकल्पिक स्ट्रीमिंग के साथ (Async agent with optional streaming)
   `AsyncSocketFlowInstance.text_completion(..., streaming: bool = False)` - एसिंक्रोनस टेक्स्ट कंप्लीशन, वैकल्पिक स्ट्रीमिंग के साथ (Async text completion with optional streaming)
   `AsyncSocketFlowInstance.graph_rag(..., streaming: bool = False)` - एसिंक्रोनस ग्राफ आरएजी, वैकल्पिक स्ट्रीमिंग के साथ (Async graph RAG with optional streaming)
   `AsyncSocketFlowInstance.document_rag(..., streaming: bool = False)` - एसिंक्रोनस डॉक्यूमेंट आरएजी, वैकल्पिक स्ट्रीमिंग के साथ (Async document RAG with optional streaming)
   `AsyncSocketFlowInstance.prompt(..., streaming: bool = False)` - एसिंक्रोनस प्रॉम्प्ट, वैकल्पिक स्ट्रीमिंग के साथ (Async prompt with optional streaming)
   `AsyncSocketFlowInstance.graph_embeddings_query()` - एसिंक्रोनस ग्राफ एम्बेडिंग क्वेरी (Async graph embeddings query)
   सभी अन्य FlowInstance विधियाँ, एसिंक्रोनस संस्करण के रूप में (All other FlowInstance methods as async versions)

4. **सिंक्रोनस बल्क ऑपरेशंस क्लाइंट (Synchronous Bulk Operations Client):**
   `BulkClient.import_triples(flow, triples)` - बल्क ट्रिपल इम्पोर्ट (Bulk triple import)
   `BulkClient.export_triples(flow)` - बल्क ट्रिपल एक्सपोर्ट (Bulk triple export)
   `BulkClient.import_graph_embeddings(flow, embeddings)` - बल्क ग्राफ एम्बेडिंग इम्पोर्ट (Bulk graph embeddings import)
   `BulkClient.export_graph_embeddings(flow)` - बल्क ग्राफ एम्बेडिंग एक्सपोर्ट (Bulk graph embeddings export)
   `BulkClient.import_document_embeddings(flow, embeddings)` - बल्क डॉक्यूमेंट एम्बेडिंग इम्पोर्ट (Bulk document embeddings import)
   `BulkClient.export_document_embeddings(flow)` - बल्क डॉक्यूमेंट एम्बेडिंग एक्सपोर्ट (Bulk document embeddings export)
   `BulkClient.import_entity_contexts(flow, contexts)` - बल्क एंटिटी कॉन्टेक्स्ट इम्पोर्ट (Bulk entity contexts import)
   `BulkClient.export_entity_contexts(flow)` - बल्क एंटिटी कॉन्टेक्स्ट एक्सपोर्ट (Bulk entity contexts export)
   `BulkClient.import_objects(flow, objects)` - बल्क ऑब्जेक्ट्स इम्पोर्ट (Bulk objects import)

5. **एसिंक्रोनस बल्क ऑपरेशंस क्लाइंट (Asynchronous Bulk Operations Client):**
   `AsyncBulkClient.import_triples(flow, triples)` - एसिंक्रोनस बल्क ट्रिपल इम्पोर्ट (Async bulk triple import)
   `AsyncBulkClient.export_triples(flow)` - एसिंक्रोनस बल्क ट्रिपल एक्सपोर्ट (Async bulk triple export)
   `AsyncBulkClient.import_graph_embeddings(flow, embeddings)` - एसिंक्रोनस बल्क ग्राफ एम्बेडिंग इम्पोर्ट (Async bulk graph embeddings import)
   `AsyncBulkClient.export_graph_embeddings(flow)` - एसिंक्रोनस बल्क ग्राफ एम्बेडिंग एक्सपोर्ट (Async bulk graph embeddings export)
   `AsyncBulkClient.import_document_embeddings(flow, embeddings)` - एसिंक्रोनस बल्क डॉक्यूमेंट एम्बेडिंग इम्पोर्ट (Async bulk document embeddings import)
   `AsyncBulkClient.export_document_embeddings(flow)` - एसिंक्रोनस बल्क डॉक्यूमेंट एम्बेडिंग एक्सपोर्ट (Async bulk document embeddings export)
   `AsyncBulkClient.import_entity_contexts(flow, contexts)` - एसिंक्रोनस बल्क एंटिटी कॉन्टेक्स्ट इम्पोर्ट (Async bulk entity contexts import)
   `AsyncBulkClient.export_entity_contexts(flow)` - एसिंक्रोनस बल्क एंटिटी कॉन्टेक्स्ट एक्सपोर्ट (Async bulk entity contexts export)
   `AsyncBulkClient.import_objects(flow, objects)` - एसिंक्रोनस बल्क ऑब्जेक्ट्स इम्पोर्ट (Async bulk objects import)

6. **एसिंक्रोनस रेस्ट फ्लो क्लाइंट (Asynchronous REST Flow Client):**
   `AsyncFlow.list()` - सभी फ्लो की सूची (list all flows)
   `AsyncFlow.get(id)` - फ्लो परिभाषा प्राप्त करें (get flow definition)
   `AsyncFlow.start(...)` - फ्लो शुरू करें (start flow)
   `AsyncFlow.stop(id)` - फ्लो रोकें (stop flow)
   `AsyncFlow.id(flow_id)` - एसिंक्रोनस फ्लो इंस्टेंस प्राप्त करें (get async flow instance)
   `AsyncFlowInstance.agent(...)` - एजेंट निष्पादन (agent execution)
   `AsyncFlowInstance.text_completion(...)` - टेक्स्ट कंप्लीशन (text completion)
   `AsyncFlowInstance.graph_rag(...)` - ग्राफ आरएजी (graph RAG)
   सभी अन्य FlowInstance विधियाँ, एसिंक्रोनस संस्करण के रूप में (All other FlowInstance methods as async versions)

7. **मेट्रिक्स क्लाइंट (Metrics Clients):**
   `Metrics.get()` - सिंक्रोनस प्रोमीथियस मेट्रिक्स (Synchronous Prometheus metrics)
   `AsyncMetrics.get()` - एसिंक्रोनस प्रोमीथियस मेट्रिक्स (Asynchronous Prometheus metrics)

8. **रेस्ट फ्लो एपीआई एन्हांसमेंट (REST Flow API Enhancement):**
   `FlowInstance.graph_embeddings_query()` - ग्राफ एम्बेडिंग क्वेरी (सिंक्रोनस फीचर समानता) (Graph embeddings query (sync feature parity))
   `AsyncFlowInstance.graph_embeddings_query()` - ग्राफ एम्बेडिंग क्वेरी (एसिंक्रोनस फीचर समानता) (Graph embeddings query (async feature parity))

#### संशोधित एपीआई (Modified APIs)

1. **कंस्ट्रक्टर (Constructor)** (मामूली एन्हांसमेंट):
   ```python
   Api(url: str, timeout: int = 60, token: Optional[str] = None)
   ```
   `token` पैरामीटर जोड़ा गया (वैकल्पिक, प्रमाणीकरण के लिए)
   यदि `None` (डिफ़ॉल्ट): कोई प्रमाणीकरण उपयोग नहीं किया गया
   यदि निर्दिष्ट: REST के लिए इसे बेयरर टोकन के रूप में उपयोग किया जाता है (`Authorization: Bearer <token>`), और WebSocket के लिए क्वेरी पैरामीटर के रूप में (`?token=<token>`)
   कोई अन्य परिवर्तन नहीं - पूरी तरह से पिछली संगतता

2. **कोई महत्वपूर्ण परिवर्तन नहीं**:
   सभी मौजूदा REST API विधियाँ अपरिवर्तित हैं
   सभी मौजूदा हस्ताक्षर संरक्षित हैं
   सभी मौजूदा रिटर्न प्रकार संरक्षित हैं

### कार्यान्वयन विवरण

#### त्रुटि प्रबंधन

**WebSocket कनेक्शन त्रुटियाँ**:
```python
try:
    api = Api(url="http://localhost:8088/")
    socket = api.socket()
    socket_flow = socket.flow("default")
    response = socket_flow.agent(question="...", user="user123")
except ConnectionError as e:
    print(f"WebSocket connection failed: {e}")
    print("Hint: Ensure Gateway is running and WebSocket endpoint is accessible")
```

**सुगम प्रतिस्थापन**:
```python
api = Api(url="http://localhost:8088/")

try:
    # Try WebSocket streaming first
    socket_flow = api.socket().flow("default")
    for chunk in socket_flow.agent(question="...", user="...", streaming=True):
        print(chunk.content)
except ConnectionError:
    # Fall back to REST non-streaming
    print("WebSocket unavailable, falling back to REST")
    rest_flow = api.flow().id("default")
    response = rest_flow.agent(question="...", user="...")
    print(response["response"])
```

**आंशिक स्ट्रीमिंग त्रुटियाँ**:
```python
api = Api(url="http://localhost:8088/")
socket_flow = api.socket().flow("default")

accumulated = []
try:
    for chunk in socket_flow.graph_rag(question="...", streaming=True):
        accumulated.append(chunk.content)
        if chunk.error:
            print(f"Error occurred: {chunk.error}")
            print(f"Partial response: {''.join(accumulated)}")
            break
except Exception as e:
    print(f"Streaming error: {e}")
    print(f"Partial response: {''.join(accumulated)}")
```

#### संसाधन प्रबंधन

**संदर्भ प्रबंधक समर्थन**:
```python
# Automatic cleanup
with Api(url="http://localhost:8088/") as api:
    socket_flow = api.socket().flow("default")
    response = socket_flow.agent(question="...", user="user123")
# All connections automatically closed

# Manual cleanup
api = Api(url="http://localhost:8088/")
try:
    socket_flow = api.socket().flow("default")
    response = socket_flow.agent(question="...", user="user123")
finally:
    api.close()  # Explicitly close all connections (WebSocket, bulk, etc.)
```

#### थ्रेडिंग और समवर्ती (Threading and Concurrency)

**थ्रेड सुरक्षा (Thread Safety):**
प्रत्येक `Api` उदाहरण अपने स्वयं के कनेक्शन को बनाए रखता है।
WebSocket ट्रांसपोर्ट थ्रेड-सुरक्षित अनुरोध मल्टीप्लेक्सिंग के लिए लॉक्स का उपयोग करता है।
कई थ्रेड सुरक्षित रूप से एक `Api` उदाहरण को साझा कर सकते हैं।
स्ट्रीमिंग इटरेटर थ्रेड-सुरक्षित नहीं हैं (केवल एक थ्रेड से उपयोग करें)।

**एसिंक्रोनस समर्थन (Async Support)** (भविष्य में विचार):
```python
# Phase 2 enhancement (not in initial scope)
import asyncio

async def main():
    api = await AsyncApi(url="ws://localhost:8088/")
    flow = api.flow().id("default")

    async for chunk in flow.agent(question="...", streaming=True):
        print(chunk.content)

    await api.close()

asyncio.run(main())
```

## सुरक्षा संबंधी विचार

### प्रमाणीकरण

**टोकन पैरामीटर**:
```python
# No authentication (default)
api = Api(url="http://localhost:8088/")

# With authentication
api = Api(url="http://localhost:8088/", token="mytoken")
```

**REST ट्रांसपोर्ट:**
बेयरर टोकन `Authorization` हेडर के माध्यम से
सभी REST अनुरोधों पर स्वचालित रूप से लागू होता है
प्रारूप: `Authorization: Bearer <token>`

**वेबसोकेट ट्रांसपोर्ट:**
टोकन क्वेरी पैरामीटर के माध्यम से, जो वेबसोकेट यूआरएल में जोड़ा जाता है
कनेक्शन स्थापित करते समय स्वचालित रूप से लागू होता है
प्रारूप: `ws://localhost:8088/api/v1/socket?token=<token>`

**कार्यान्वयन:**
```python
class SocketClient:
    def _connect(self) -> WebSocket:
        # Construct WebSocket URL with optional token
        ws_url = f"{self.url}/api/v1/socket"
        if self.token:
            ws_url = f"{ws_url}?token={self.token}"
        # Connect to WebSocket
        return websocket.connect(ws_url)
```

**उदाहरण:**
```python
# REST with auth
api = Api(url="http://localhost:8088/", token="mytoken")
flow = api.flow().id("default")
# All REST calls include: Authorization: Bearer mytoken

# WebSocket with auth
socket = api.socket()
# Connects to: ws://localhost:8088/api/v1/socket?token=mytoken
```

### सुरक्षित संचार

WS (वेबसॉकेट) और WSS (वेबसॉकेट सिक्योर) दोनों योजनाओं का समर्थन करें।
WSS कनेक्शन के लिए टीएलएस प्रमाणपत्र सत्यापन।
विकास के लिए वैकल्पिक प्रमाणपत्र सत्यापन अक्षम करें (चेतावनी के साथ)।

### इनपुट सत्यापन

यूआरएल योजनाओं को मान्य करें (http, https, ws, wss)।
परिवहन पैरामीटर मानों को मान्य करें।
स्ट्रीमिंग पैरामीटर संयोजनों को मान्य करें।
बल्क आयात डेटा प्रकारों को मान्य करें।

## प्रदर्शन संबंधी विचार

### विलंबता में सुधार

**स्ट्रीमिंग एलएलएम ऑपरेशन**:
**पहले टोकन तक का समय**: ~500ms (गैर-स्ट्रीमिंग के मुकाबले ~30s)
**सुधार**: 60 गुना तेज प्रदर्शन
**लागू**: एजेंट, ग्राफ आरएजी, दस्तावेज़ आरएजी, टेक्स्ट कंप्लीशन, प्रॉम्प्ट

**स्थायी कनेक्शन**:
**कनेक्शन ओवरहेड**: बाद के अनुरोधों के लिए समाप्त
**वेबसॉकेट हैंडशेक**: एक बार की लागत (~100ms)
**लागू**: वेबसॉकेट परिवहन का उपयोग करते समय सभी ऑपरेशन

### थ्रूपुट में सुधार

**बल्क ऑपरेशन**:
**ट्रिपल्स आयात**: ~10,000 ट्रिपल्स/सेकंड (REST के साथ प्रति-आइटम ~100/सेकंड की तुलना में)
**एम्बेडिंग आयात**: ~5,000 एम्बेडिंग/सेकंड (REST के साथ प्रति-आइटम ~50/सेकंड की तुलना में)
**सुधार**: बल्क ऑपरेशन के लिए 100 गुना थ्रूपुट

**अनुरोध मल्टीप्लेक्सिंग**:
**समवर्ती अनुरोध**: एक कनेक्शन पर 15 तक समवर्ती अनुरोध
**कनेक्शन पुन: उपयोग**: समवर्ती ऑपरेशन के लिए कोई कनेक्शन ओवरहेड नहीं

### मेमोरी संबंधी विचार

**स्ट्रीमिंग प्रतिक्रियाएं**:
स्थिर मेमोरी उपयोग (जैसे ही वे आते हैं, चंक्स को संसाधित करें)
पूरी प्रतिक्रिया का कोई बफरिंग नहीं
बहुत लंबी आउटपुट (>1MB) के लिए उपयुक्त

**बल्क ऑपरेशन**:
इटरेटर-आधारित प्रसंस्करण (स्थिर मेमोरी)
संपूर्ण डेटासेट को मेमोरी में लोड नहीं किया जाता है
लाखों आइटम वाले डेटासेट के लिए उपयुक्त

### बेंचमार्क (अपेक्षित)

| ऑपरेशन | REST (मौजूदा) | वेबसॉकेट (स्ट्रीमिंग) | सुधार |
|-----------|----------------|----------------------|-------------|
| एजेंट (पहले टोकन तक का समय) | 30s | 0.5s | 60x |
| ग्राफ आरएजी (पहले टोकन तक का समय) | 25s | 0.5s | 50x |
| 10K ट्रिपल्स आयात करें | 100s | 1s | 100x |
| 1M ट्रिपल्स आयात करें | 10,000s (2.7h) | 100s (1.6m) | 100x |
| 10 समवर्ती छोटे अनुरोध | 5s (क्रमिक) | 0.5s (समानांतर) | 10x |

## परीक्षण रणनीति

### यूनिट टेस्ट

**परिवहन परत** (`test_transport.py`):
REST परिवहन अनुरोध/प्रतिक्रिया का परीक्षण करें
WebSocket परिवहन कनेक्शन का परीक्षण करें
WebSocket परिवहन पुन: कनेक्शन का परीक्षण करें
अनुरोध मल्टीप्लेक्सिंग का परीक्षण करें
स्ट्रीमिंग प्रतिक्रिया पार्सिंग का परीक्षण करें
नियतात्मक परीक्षणों के लिए मॉक WebSocket सर्वर

**API विधियाँ** (`test_flow.py`, `test_library.py`, आदि):
मॉक परिवहन के साथ नई विधियों का परीक्षण करें
स्ट्रीमिंग पैरामीटर हैंडलिंग का परीक्षण करें
बल्क ऑपरेशन इटरेटर का परीक्षण करें
त्रुटि हैंडलिंग का परीक्षण करें

**प्रकार** (`test_types.py`):
नए स्ट्रीमिंग चंक प्रकारों का परीक्षण करें
प्रकार क्रमबद्धता/वि-क्रमबद्धता का परीक्षण करें

### एकीकरण परीक्षण

**एंड-टू-एंड REST** (`test_integration_rest.py`):
वास्तविक गेटवे (REST मोड) के खिलाफ सभी कार्यों का परीक्षण करें
पिछड़े अनुकूलता को सत्यापित करें
त्रुटि स्थितियों का परीक्षण करें

**एंड-टू-एंड WebSocket** (`test_integration_websocket.py`):
वास्तविक गेटवे (WebSocket मोड) के खिलाफ सभी कार्यों का परीक्षण करें
स्ट्रीमिंग कार्यों का परीक्षण करें
बल्क कार्यों का परीक्षण करें
समवर्ती अनुरोधों का परीक्षण करें
कनेक्शन रिकवरी का परीक्षण करें

**स्ट्रीमिंग सेवाएं** (`test_streaming_integration.py`):
एजेंट स्ट्रीमिंग का परीक्षण करें (विचार, अवलोकन, उत्तर)
RAG स्ट्रीमिंग का परीक्षण करें (क्रमिक चंक)
टेक्स्ट कंप्लीशन स्ट्रीमिंग का परीक्षण करें (टोकन-दर-टोकन)
प्रॉम्प्ट स्ट्रीमिंग का परीक्षण करें
स्ट्रीमिंग के दौरान त्रुटि हैंडलिंग का परीक्षण करें

**बल्क ऑपरेशन** (`test_bulk_integration.py`):
ट्रिपल (1K, 10K, 100K आइटम) का बल्क आयात/निर्यात का परीक्षण करें
एम्बेडिंग का बल्क आयात/निर्यात का परीक्षण करें
बल्क कार्यों के दौरान मेमोरी उपयोग का परीक्षण करें
प्रगति ट्रैकिंग का परीक्षण करें

### प्रदर्शन परीक्षण

**विलंबता बेंचमार्क** (`test_performance_latency.py`):
पहले टोकन तक लगने वाले समय को मापें (स्ट्रीमिंग बनाम गैर-स्ट्रीमिंग)
कनेक्शन ओवरहेड को मापें (REST बनाम WebSocket)
अपेक्षित बेंचमार्क के विरुद्ध तुलना करें

**थ्रूपुट बेंचमार्क** (`test_performance_throughput.py`):
बल्क आयात थ्रूपुट को मापें
अनुरोध मल्टीप्लेक्सिंग दक्षता को मापें
अपेक्षित बेंचमार्क के विरुद्ध तुलना करें

### अनुकूलता परीक्षण

**पिछड़ी अनुकूलता** (`test_backward_compatibility.py`):
मौजूदा परीक्षण सूट को रिफैक्टर किए गए API के खिलाफ चलाएं
शून्य ब्रेकिंग परिवर्तनों को सत्यापित करें
सामान्य पैटर्न के लिए माइग्रेशन पथ का परीक्षण करें

## माइग्रेशन योजना

### चरण 1: पारदर्शी माइग्रेशन (डिफ़ॉल्ट)

**किसी कोड परिवर्तन की आवश्यकता नहीं है।** मौजूदा कोड काम करना जारी रखता है:

```python
# Existing code works unchanged
api = Api(url="http://localhost:8088/")
flow = api.flow().id("default")
response = flow.agent(question="What is ML?", user="user123")
```

### चरण 2: ऑप्ट-इन स्ट्रीमिंग (सरल)

**स्ट्रीमिंग को सक्षम करने के लिए `api.socket()` इंटरफ़ेस का उपयोग करें:**

```python
# Before: Non-streaming REST
api = Api(url="http://localhost:8088/")
rest_flow = api.flow().id("default")
response = rest_flow.agent(question="What is ML?", user="user123")
print(response["response"])

# After: Streaming WebSocket (same parameters!)
api = Api(url="http://localhost:8088/")  # Same URL
socket_flow = api.socket().flow("default")

for chunk in socket_flow.agent(question="What is ML?", user="user123", streaming=True):
    if isinstance(chunk, AgentAnswer):
        print(chunk.content, end="", flush=True)
```

**मुख्य बातें:**
REST और WebSocket दोनों के लिए समान URL
समान मेथड सिग्नेचर (आसान माइग्रेशन)
बस `.socket()` और `streaming=True` जोड़ें

### चरण 3: बल्क ऑपरेशन (नई क्षमता)

बड़े डेटासेट के लिए `api.bulk()` इंटरफ़ेस का उपयोग करें:

```python
# Before: Inefficient per-item operations
api = Api(url="http://localhost:8088/")
flow = api.flow().id("default")

for triple in my_large_triple_list:
    # Slow per-item operations
    # (no direct bulk insert in REST API)
    pass

# After: Efficient bulk loading
api = Api(url="http://localhost:8088/")  # Same URL
bulk = api.bulk()

# This is fast (10,000 triples/second)
bulk.import_triples(flow="default", triples=iter(my_large_triple_list))
```

### दस्तावेज़ अद्यतन

1. **README.md**: स्ट्रीमिंग और वेबसॉकेट उदाहरण जोड़ें
2. **एपीआई संदर्भ**: सभी नए तरीकों और पैरामीटरों का दस्तावेजीकरण करें
3. **माइग्रेशन गाइड**: स्ट्रीमिंग को सक्षम करने के लिए चरण-दर-चरण मार्गदर्शिका
4. **उदाहरण**: सामान्य पैटर्न के लिए उदाहरण स्क्रिप्ट जोड़ें
5. **प्रदर्शन गाइड**: अपेक्षित प्रदर्शन सुधारों का दस्तावेजीकरण करें

### अप्रचलन नीति

**कोई अप्रचलन नहीं।** सभी मौजूदा एपीआई समर्थित रहते हैं। यह एक शुद्ध संवर्द्धन है।

## समयरेखा

### सप्ताह 1: आधार
परिवहन अमूर्त परत
मौजूदा REST कोड को पुनर्गठित करें
परिवहन परत के लिए यूनिट परीक्षण
पिछड़े अनुकूलता सत्यापन

### सप्ताह 2: वेबसॉकेट परिवहन
वेबसॉकेट परिवहन कार्यान्वयन
कनेक्शन प्रबंधन और पुन: कनेक्शन
अनुरोध मल्टीप्लेक्सिंग
यूनिट और एकीकरण परीक्षण

### सप्ताह 3: स्ट्रीमिंग समर्थन
एलएलएम विधियों में स्ट्रीमिंग पैरामीटर जोड़ें
स्ट्रीमिंग प्रतिक्रिया पार्सिंग को लागू करें
स्ट्रीमिंग चंक प्रकार जोड़ें
स्ट्रीमिंग एकीकरण परीक्षण

### सप्ताह 4: बल्क ऑपरेशन
बल्क आयात/निर्यात विधियाँ जोड़ें
इटरेटर-आधारित संचालन को लागू करें
प्रदर्शन परीक्षण
बल्क ऑपरेशन एकीकरण परीक्षण

### सप्ताह 5: सुविधा समानता और दस्तावेज़
ग्राफ एम्बेडिंग क्वेरी जोड़ें
मेट्रिक्स एपीआई जोड़ें
व्यापक दस्तावेज़
माइग्रेशन गाइड
रिलीज़ उम्मीदवार

### सप्ताह 6: रिलीज़
अंतिम एकीकरण परीक्षण
प्रदर्शन बेंचमार्किंग
रिलीज़ दस्तावेज़
सामुदायिक घोषणा

**कुल अवधि**: 6 सप्ताह

## खुले प्रश्न

### एपीआई डिज़ाइन प्रश्न

1. **एसिंक्रोनस समर्थन**: ✅ **समाधान** - प्रारंभिक रिलीज़ में पूर्ण एसिंक्रोनस समर्थन शामिल है
   सभी इंटरफेस में एसिंक्रोनस वेरिएंट हैं: `async_flow()`, `async_socket()`, `async_bulk()`, `async_metrics()`
   सिंक और एसिंक्रोनस एपीआई के बीच पूर्ण समरूपता प्रदान करता है
   आधुनिक एसिंक्रोनस फ्रेमवर्क (FastAPI, aiohttp) के लिए आवश्यक है

2. **प्रगति ट्रैकिंग**: क्या बल्क ऑपरेशन प्रगति कॉलबैक का समर्थन करना चाहिए?
   ```python
   def progress_callback(processed: int, total: Optional[int]):
       print(f"Processed {processed} items")

   bulk.import_triples(flow="default", triples=triples, on_progress=progress_callback)
   ```
   **सिफारिश**: चरण 2 में जोड़ें। प्रारंभिक रिलीज़ के लिए महत्वपूर्ण नहीं है।

3. **स्ट्रीमिंग टाइमआउट**: हमें स्ट्रीमिंग कार्यों के लिए टाइमआउट को कैसे संभालना चाहिए?
   **सिफारिश**: गैर-स्ट्रीमिंग के समान टाइमआउट का उपयोग करें, लेकिन प्रत्येक प्राप्त चंक पर इसे रीसेट करें।

4. **चंक बफरिंग**: क्या हमें चंक्स को बफर करना चाहिए या तुरंत आउटपुट देना चाहिए?
   **सिफारिश**: सबसे कम विलंबता के लिए तुरंत आउटपुट दें।

5. **वेबसॉकेट के माध्यम से वैश्विक सेवाएं**: क्या `api.socket()` को वैश्विक सेवाओं (लाइब्रेरी, ज्ञान, संग्रह, कॉन्फ़िगरेशन) का समर्थन करना चाहिए या केवल फ़्लो-स्कोप सेवाओं का?
   **सिफारिश**: केवल फ़्लो-स्कोप के साथ शुरुआत करें (जहां स्ट्रीमिंग मायने रखती है)। यदि आवश्यक हो तो चरण 2 में वैश्विक सेवाओं को जोड़ें।

### कार्यान्वयन प्रश्न

1. **वेबसॉकेट लाइब्रेरी**: क्या हमें `websockets`, `websocket-client`, या `aiohttp` का उपयोग करना चाहिए?
   **सिफारिश**: `websockets` (एसिंक्रोनस, परिपक्व, अच्छी तरह से बनाए रखा गया)। `asyncio.run()` का उपयोग करके सिंक इंटरफ़ेस में लपेटें।

2. **कनेक्शन पूलिंग**: क्या हमें कई समवर्ती `Api` उदाहरणों का समर्थन करना चाहिए जो एक कनेक्शन पूल साझा करते हैं?
   **सिफारिश**: चरण 2 तक टालें। प्रत्येक `Api` उदाहरण में शुरू में अपने स्वयं के कनेक्शन होंगे।

3. **कनेक्शन पुन: उपयोग**: क्या `SocketClient` और `BulkClient` एक ही वेबसॉकेट कनेक्शन साझा करेंगे, या अलग-अलग कनेक्शन का उपयोग करेंगे?
   **सिफारिश**: अलग कनेक्शन। सरल कार्यान्वयन, चिंताओं का स्पष्ट अलगाव।

4. **लेजी बनाम ईगर कनेक्शन**: क्या वेबसॉकेट कनेक्शन `api.socket()` में स्थापित किया जाना चाहिए या पहले अनुरोध पर?
   **सिफारिश**: लेजी (पहले अनुरोध पर)। यदि उपयोगकर्ता केवल REST विधियों का उपयोग करता है तो कनेक्शन ओवरहेड से बचें।

### परीक्षण प्रश्न

1. **मॉक गेटवे**: क्या हमें परीक्षण के लिए एक हल्के मॉक गेटवे बनाना चाहिए, या वास्तविक गेटवे के खिलाफ परीक्षण करना चाहिए?
   **सिफारिश**: दोनों। यूनिट परीक्षणों के लिए मॉक का उपयोग करें, एकीकरण परीक्षणों के लिए वास्तविक गेटवे का उपयोग करें।

2. **प्रदर्शन प्रतिगमन परीक्षण**: क्या हमें CI में स्वचालित प्रदर्शन प्रतिगमन परीक्षण जोड़ना चाहिए?
   **सिफारिश**: हाँ, लेकिन CI वातावरण की परिवर्तनशीलता को ध्यान में रखते हुए उदार सीमाओं के साथ।

## संदर्भ

### संबंधित तकनीकी विनिर्देश
`docs/tech-specs/streaming-llm-responses.md` - गेटवे में स्ट्रीमिंग कार्यान्वयन
`docs/tech-specs/rag-streaming-support.md` - RAG स्ट्रीमिंग समर्थन

### कार्यान्वयन फ़ाइलें
`trustgraph-base/trustgraph/api/` - पायथन एपीआई स्रोत
`trustgraph-flow/trustgraph/gateway/` - गेटवे स्रोत
`trustgraph-flow/trustgraph/gateway/dispatch/mux.py` - वेबसॉकेट मल्टीप्लेक्सर संदर्भ कार्यान्वयन

### दस्तावेज़
`docs/apiSpecification.md` - पूर्ण एपीआई संदर्भ
`docs/api-status-summary.md` - एपीआई स्थिति सारांश
`README.websocket` - वेबसॉकेट प्रोटोकॉल दस्तावेज़
`STREAMING-IMPLEMENTATION-NOTES.txt` - स्ट्रीमिंग कार्यान्वयन नोट्स

### बाहरी लाइब्रेरी
`websockets` - पायथन वेबसॉकेट लाइब्रेरी (https://websockets.readthedocs.io/)
`requests` - पायथन एचटीटीपी लाइब्रेरी (मौजूदा)
