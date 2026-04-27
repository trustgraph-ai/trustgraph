---
layout: default
title: "ग्राफआरएजी प्रदर्शन अनुकूलन तकनीकी विनिर्देश"
parent: "Hindi (Beta)"
---

# ग्राफआरएजी प्रदर्शन अनुकूलन तकनीकी विनिर्देश

> **Beta Translation:** This document was translated via Machine Learning and as such may not be 100% accurate. All non-English languages are currently classified as Beta.

## अवलोकन

यह विनिर्देश ट्रस्टग्राफ में ग्राफआरएजी (ग्राफ रिट्रीवल-ऑगमेंटेड जनरेशन) एल्गोरिदम के लिए व्यापक प्रदर्शन अनुकूलन का वर्णन करता है। वर्तमान कार्यान्वयन में महत्वपूर्ण प्रदर्शन बाधाएं हैं जो स्केलेबिलिटी और प्रतिक्रिया समय को सीमित करती हैं। यह विनिर्देश चार प्राथमिक अनुकूलन क्षेत्रों को संबोधित करता है:

1. **ग्राफ ट्रैवर्सल अनुकूलन**: अक्षम पुनरावर्ती डेटाबेस प्रश्नों को समाप्त करें और बैच में ग्राफ अन्वेषण लागू करें।
2. **लेबल रिज़ॉल्यूशन अनुकूलन**: क्रमिक लेबल फ़ेचिंग को समानांतर/बैच संचालन से बदलें।
3. **कैशिंग रणनीति में सुधार**: एलआरयू निष्कासन और प्रीफ़ेचिंग के साथ बुद्धिमान कैशिंग लागू करें।
4. **क्वेरी अनुकूलन**: बेहतर प्रतिक्रिया समय के लिए परिणाम मेमोइज़ेशन और एम्बेडिंग कैशिंग जोड़ें।

## लक्ष्य

<<<<<<< HEAD
**डेटाबेस क्वेरी की मात्रा को कम करें**: बैचिंग और कैशिंग के माध्यम से कुल डेटाबेस प्रश्नों में 50-80% की कमी प्राप्त करें।
**प्रतिक्रिया समय में सुधार**: सबग्राफ निर्माण और लेबल रिज़ॉल्यूशन में 3-5 गुना तेजी और 2-3 गुना तेजी लाने का लक्ष्य रखें।
**स्केलेबिलिटी में वृद्धि**: बेहतर मेमोरी प्रबंधन के साथ बड़े नॉलेज ग्राफ का समर्थन करें।
**सटीकता बनाए रखें**: मौजूदा ग्राफआरएजी कार्यक्षमता और परिणाम गुणवत्ता को संरक्षित करें।
**समवर्तीता सक्षम करें**: एकाधिक समवर्ती अनुरोधों के लिए समानांतर प्रसंस्करण क्षमताओं में सुधार करें।
**मेमोरी पदचिह्न को कम करें**: कुशल डेटा संरचनाओं और मेमोरी प्रबंधन को लागू करें।
=======
**डेटाबेस क्वेरी की मात्रा कम करें**: बैचिंग और कैशिंग के माध्यम से कुल डेटाबेस प्रश्नों में 50-80% की कमी प्राप्त करें।
**प्रतिक्रिया समय में सुधार**: सबग्राफ निर्माण और लेबल रिज़ॉल्यूशन में 3-5 गुना तेजी और 2-3 गुना तेजी लाने का लक्ष्य रखें।
**स्केलेबिलिटी बढ़ाएं**: बेहतर मेमोरी प्रबंधन के साथ बड़े नॉलेज ग्राफ का समर्थन करें।
**सटीकता बनाए रखें**: मौजूदा ग्राफआरएजी कार्यक्षमता और परिणाम गुणवत्ता को संरक्षित करें।
**समवर्तीता सक्षम करें**: एकाधिक समवर्ती अनुरोधों के लिए समानांतर प्रसंस्करण क्षमताओं में सुधार करें।
**मेमोरी पदचिह्न कम करें**: कुशल डेटा संरचनाओं और मेमोरी प्रबंधन को लागू करें।
>>>>>>> 82edf2d (New md files from RunPod)
**अवलोकनशीलता जोड़ें**: प्रदर्शन मेट्रिक्स और निगरानी क्षमताओं को शामिल करें।
**विश्वसनीयता सुनिश्चित करें**: उचित त्रुटि हैंडलिंग और टाइमआउट तंत्र जोड़ें।

## पृष्ठभूमि

`trustgraph-flow/trustgraph/retrieval/graph_rag/graph_rag.py` में वर्तमान ग्राफआरएजी कार्यान्वयन में कई महत्वपूर्ण प्रदर्शन मुद्दे हैं जो सिस्टम स्केलेबिलिटी को गंभीर रूप से प्रभावित करते हैं:

### वर्तमान प्रदर्शन समस्याएं

**1. अक्षम ग्राफ ट्रैवर्सल (`follow_edges` फ़ंक्शन, लाइनें 79-127)**
<<<<<<< HEAD
प्रत्येक इकाई प्रति गहराई स्तर के लिए 3 अलग-अलग डेटाबेस क्वेरी करता है।
क्वेरी पैटर्न: प्रत्येक इकाई के लिए विषय-आधारित, विधेय-आधारित और ऑब्जेक्ट-आधारित क्वेरी।
कोई बैचिंग नहीं: प्रत्येक क्वेरी एक समय में केवल एक इकाई को संसाधित करती है।
=======
प्रति इकाई प्रति गहराई स्तर के लिए 3 अलग-अलग डेटाबेस क्वेरी करता है।
क्वेरी पैटर्न: प्रत्येक इकाई के लिए विषय-आधारित, विधेय-आधारित और ऑब्जेक्ट-आधारित क्वेरी।
कोई बैचिंग नहीं: प्रत्येक क्वेरी केवल एक इकाई को संसाधित करती है।
>>>>>>> 82edf2d (New md files from RunPod)
कोई चक्र का पता नहीं: समान नोड्स को कई बार फिर से देख सकता है।
मेमोइज़ेशन के बिना पुनरावर्ती कार्यान्वयन घातीय जटिलता की ओर ले जाता है।
समय जटिलता: O(entities × max_path_length × triple_limit³)

**2. क्रमिक लेबल रिज़ॉल्यूशन (`get_labelgraph` फ़ंक्शन, लाइनें 144-171)**
प्रत्येक ट्रिपल घटक (विषय, विधेय, ऑब्जेक्ट) को क्रमिक रूप से संसाधित करता है।
प्रत्येक `maybe_label` कॉल संभावित रूप से एक डेटाबेस क्वेरी को ट्रिगर करता है।
लेबल क्वेरी के समानांतर निष्पादन या बैचिंग नहीं।
परिणाम में subgraph_size × 3 व्यक्तिगत डेटाबेस कॉल होते हैं।

**3. आदिम कैशिंग रणनीति (`maybe_label` फ़ंक्शन, लाइनें 62-77)**
आकार सीमा या टीटीएल के बिना एक साधारण शब्दकोश कैश।
<<<<<<< HEAD
कोई कैश निष्कासन नीति नहीं जिसके परिणामस्वरूप असीमित मेमोरी वृद्धि होती है।
=======
कोई कैश निष्कासन नीति असीमित मेमोरी वृद्धि की ओर ले जाती है।
>>>>>>> 82edf2d (New md files from RunPod)
कैश मिस व्यक्तिगत डेटाबेस क्वेरी को ट्रिगर करते हैं।
कोई प्रीफ़ेचिंग या बुद्धिमान कैश वार्मिंग नहीं।

**4. उप-इष्टतम क्वेरी पैटर्न**
समान अनुरोधों के बीच इकाई वेक्टर समानता क्वेरी कैश नहीं की जाती हैं।
दोहराए गए क्वेरी पैटर्न के लिए कोई परिणाम मेमोइज़ेशन नहीं।
सामान्य एक्सेस पैटर्न के लिए कोई क्वेरी अनुकूलन नहीं।

**5. महत्वपूर्ण ऑब्जेक्ट लाइफटाइम मुद्दे (`rag.py:96-102`)**
**प्रत्येक अनुरोध के लिए GraphRag ऑब्जेक्ट फिर से बनाया गया**: प्रत्येक क्वेरी के लिए एक नया उदाहरण बनाया जाता है, जिससे सभी कैश लाभ खो जाते हैं।
<<<<<<< HEAD
**क्वेरी ऑब्जेक्ट बहुत कम समय तक रहता है**: एकल क्वेरी निष्पादन के भीतर बनाया और नष्ट किया जाता है (लाइनें 201-207)।
=======
**क्वेरी ऑब्जेक्ट बहुत कम समय तक जीवित रहता है**: एक ही क्वेरी निष्पादन के भीतर बनाया और नष्ट किया जाता है (लाइनें 201-207)।
>>>>>>> 82edf2d (New md files from RunPod)
**प्रत्येक अनुरोध के लिए लेबल कैश रीसेट**: कैश वार्मिंग और संचित ज्ञान के बीच खो जाता है।
**क्लाइंट पुन: निर्माण ओवरहेड**: प्रत्येक अनुरोध के लिए डेटाबेस क्लाइंट संभावित रूप से फिर से स्थापित होते हैं।
**क्रॉस-रिक्वेस्ट अनुकूलन नहीं**: क्वेरी पैटर्न या परिणाम साझाकरण से लाभ नहीं उठाया जा सकता है।

### प्रदर्शन प्रभाव विश्लेषण

एक विशिष्ट क्वेरी के लिए वर्तमान सबसे खराब स्थिति परिदृश्य:
<<<<<<< HEAD
**इकाई पुनर्प्राप्ति**: 1 वेक्टर समानता क्वेरी
**ग्राफ ट्रैवर्सल**: entities × max_path_length × 3 × triple_limit क्वेरी
**लेबल रिज़ॉल्यूशन**: subgraph_size × 3 व्यक्तिगत लेबल क्वेरी

डिफ़ॉल्ट मापदंडों के लिए (50 एंटिटीज, पथ लंबाई 2, 30 ट्रिपल सीमा, 150 सबग्राफ आकार):
**न्यूनतम क्वेरीज़**: 1 + (50 × 2 × 3 × 30) + (150 × 3) = **9,451 डेटाबेस क्वेरीज़**
**प्रतिक्रिया समय**: मध्यम आकार के ग्राफ़ के लिए 15-30 सेकंड
**मेमोरी उपयोग**: समय के साथ असीमित कैश वृद्धि
**कैश प्रभावशीलता**: 0% - प्रत्येक अनुरोध पर कैश रीसेट हो जाते हैं
**ऑब्जेक्ट निर्माण ओवरहेड**: प्रति अनुरोध बनाए गए/विनाशित GraphRag + Query ऑब्जेक्ट

यह विनिर्देश इन कमियों को बैच क्वेरी, बुद्धिमान कैशिंग और समानांतर प्रसंस्करण को लागू करके संबोधित करता है। क्वेरी पैटर्न और डेटा एक्सेस को अनुकूलित करके, TrustGraph निम्न कार्य कर सकता है:
लाखों एंटिटीज वाले एंटरप्राइज-स्केल नॉलेज ग्राफ़ का समर्थन करें
विशिष्ट क्वेरीज़ के लिए उप-सेकंड प्रतिक्रिया समय प्रदान करें
सैकड़ों समवर्ती GraphRAG अनुरोधों को संभालें
ग्राफ के आकार और जटिलता के साथ कुशलतापूर्वक स्केल करें
=======
**इकाई पुनर्प्राप्ति**: 1 वेक्टर समानता क्वेरी।
**ग्राफ ट्रैवर्सल**: entities × max_path_length × 3 × triple_limit क्वेरी।
**लेबल रिज़ॉल्यूशन**: subgraph_size × 3 व्यक्तिगत लेबल क्वेरी।

डिफ़ॉल्ट मापदंडों के लिए (50 एंटिटीज, पथ लंबाई 2, 30 ट्रिपल सीमा, 150 सबग्राफ आकार):
**न्यूनतम क्वेरीज़**: 1 + (50 × 2 × 3 × 30) + (150 × 3) = **9,451 डेटाबेस क्वेरीज़**
**प्रतिक्रिया समय**: मध्यम आकार के ग्राफ के लिए 15-30 सेकंड
**मेमोरी उपयोग**: समय के साथ असीमित कैश वृद्धि
**कैश प्रभावशीलता**: 0% - प्रत्येक अनुरोध पर कैश रीसेट हो जाते हैं
**ऑब्जेक्ट निर्माण ओवरहेड**: प्रति अनुरोध बनाए गए/विनाश किए गए ग्राफराग + क्वेरी ऑब्जेक्ट

यह विनिर्देश इन कमियों को बैच क्वेरी, बुद्धिमान कैशिंग और समानांतर प्रसंस्करण को लागू करके संबोधित करता है। क्वेरी पैटर्न और डेटा एक्सेस को अनुकूलित करके, ट्रस्टग्राफ निम्न कार्य कर सकता है:
लाखों एंटिटीज वाले एंटरप्राइज-स्केल नॉलेज ग्राफ का समर्थन करें
विशिष्ट क्वेरीज़ के लिए उप-सेकंड प्रतिक्रिया समय प्रदान करें
सैकड़ों समवर्ती ग्राफराग अनुरोधों को संभालें
ग्राफ आकार और जटिलता के साथ कुशलतापूर्वक स्केल करें
>>>>>>> 82edf2d (New md files from RunPod)

## तकनीकी डिज़ाइन

### आर्किटेक्चर

<<<<<<< HEAD
GraphRAG प्रदर्शन अनुकूलन के लिए निम्नलिखित तकनीकी घटकों की आवश्यकता होती है:

#### 1. **ऑब्जेक्ट लाइफटाइम आर्किटेक्चरल रीफैक्टर**
   **GraphRag को लंबे समय तक चलने वाला बनाएं**: GraphRag इंस्टेंस को प्रोसेसर स्तर पर ले जाएं ताकि यह अनुरोधों के बीच बना रहे
   **कैश बनाए रखें**: लेबल कैश, एम्बेडिंग कैश और क्वेरी परिणाम कैश को अनुरोधों के बीच बनाए रखें
   **क्वेरी ऑब्जेक्ट को अनुकूलित करें**: Query को एक हल्के निष्पादन संदर्भ के रूप में रीफैक्टर करें, डेटा कंटेनर के रूप में नहीं
=======
ग्राफराग प्रदर्शन अनुकूलन के लिए निम्नलिखित तकनीकी घटकों की आवश्यकता होती है:

#### 1. **ऑब्जेक्ट लाइफटाइम आर्किटेक्चरल रीफैक्टर**
   **ग्राफराग को लंबे समय तक चलने वाला बनाएं**: ग्राफराग इंस्टेंस को प्रोसेसर स्तर पर ले जाएं ताकि यह अनुरोधों के बीच बना रहे
   **कैश बनाए रखें**: लेबल कैश, एम्बेडिंग कैश और क्वेरी परिणाम कैश को अनुरोधों के बीच बनाए रखें
   **क्वेरी ऑब्जेक्ट को अनुकूलित करें**: क्वेरी को एक हल्के निष्पादन संदर्भ के रूप में रीफैक्टर करें, डेटा कंटेनर के रूप में नहीं
>>>>>>> 82edf2d (New md files from RunPod)
   **कनेक्शन दृढ़ता**: डेटाबेस क्लाइंट कनेक्शन को अनुरोधों के बीच बनाए रखें

   मॉड्यूल: `trustgraph-flow/trustgraph/retrieval/graph_rag/rag.py` (संशोधित)

#### 2. **अनुकूलित ग्राफ ट्रैवर्सल इंजन**
   पुनरावर्ती `follow_edges` को पुनरावृत्त चौड़ाई-पहली खोज से बदलें
   प्रत्येक ट्रैवर्सल स्तर पर बैच एंटिटी प्रोसेसिंग लागू करें
   देखे गए नोड ट्रैकिंग का उपयोग करके चक्र का पता लगाएं
   सीमाओं तक पहुंचने पर प्रारंभिक समाप्ति शामिल करें

   मॉड्यूल: `trustgraph-flow/trustgraph/retrieval/graph_rag/optimized_traversal.py`

#### 3. **समानांतर लेबल रिज़ॉल्यूशन सिस्टम**
<<<<<<< HEAD
   एक साथ कई एंटिटीज के लिए लेबल क्वेरीज़ को बैच करें
=======
   एक साथ कई एंटिटीज के लिए बैच लेबल क्वेरी
>>>>>>> 82edf2d (New md files from RunPod)
   समवर्ती डेटाबेस एक्सेस के लिए एसिंक्रोनस/अवेट पैटर्न लागू करें
   सामान्य लेबल पैटर्न के लिए बुद्धिमान प्रीफ़ेटिंग जोड़ें
   लेबल कैश वार्मिंग रणनीतियों शामिल करें

   मॉड्यूल: `trustgraph-flow/trustgraph/retrieval/graph_rag/label_resolver.py`

#### 4. **रूढ़िवादी लेबल कैशिंग लेयर**
<<<<<<< HEAD
   प्रदर्शन बनाम स्थिरता को संतुलित करने के लिए केवल लेबल के लिए लघु TTL के साथ LRU कैश (5 मिनट)
   कैश मेट्रिक्स और हिट अनुपात निगरानी
   **कोई एम्बेडिंग कैशिंग नहीं**: पहले से ही प्रति-क्वेरी कैश किया गया है, कोई क्रॉस-क्वेरी लाभ नहीं
   **कोई क्वेरी परिणाम कैशिंग नहीं**: ग्राफ परिवर्तन स्थिरता संबंधी चिंताओं के कारण
=======
   केवल लेबल के लिए लघु TTL के साथ LRU कैश (5 मिनट) प्रदर्शन बनाम स्थिरता को संतुलित करने के लिए
   कैश मेट्रिक्स और हिट अनुपात निगरानी
   **कोई एम्बेडिंग कैशिंग नहीं**: पहले से ही प्रति-क्वेरी कैश किया गया है, कोई क्रॉस-क्वेरी लाभ नहीं
   **कोई क्वेरी परिणाम कैशिंग नहीं**: ग्राफ उत्परिवर्तन स्थिरता संबंधी चिंताओं के कारण
>>>>>>> 82edf2d (New md files from RunPod)

   मॉड्यूल: `trustgraph-flow/trustgraph/retrieval/graph_rag/cache_manager.py`

#### 5. **क्वेरी अनुकूलन ढांचा**
   क्वेरी पैटर्न विश्लेषण और अनुकूलन सुझाव
   डेटाबेस एक्सेस के लिए बैच क्वेरी समन्वयक
   कनेक्शन पूलिंग और क्वेरी टाइमआउट प्रबंधन
   प्रदर्शन निगरानी और मेट्रिक्स संग्रह

   मॉड्यूल: `trustgraph-flow/trustgraph/retrieval/graph_rag/query_optimizer.py`

### डेटा मॉडल

#### अनुकूलित ग्राफ ट्रैवर्सल स्थिति

ट्रैवर्सल इंजन अनावश्यक कार्यों से बचने के लिए स्थिति बनाए रखता है:

```python
@dataclass
class TraversalState:
    visited_entities: Set[str]
    current_level_entities: Set[str]
    next_level_entities: Set[str]
    subgraph: Set[Tuple[str, str, str]]
    depth: int
    query_batch: List[TripleQuery]
```

<<<<<<< HEAD
यह दृष्टिकोण निम्नलिखित सुविधाएँ प्रदान करता है:
=======
यह दृष्टिकोण निम्नलिखित कार्य करने की अनुमति देता है:
>>>>>>> 82edf2d (New md files from RunPod)
विज़िट किए गए एंटिटी को ट्रैक करके कुशल चक्र का पता लगाना
प्रत्येक ट्रैवर्सल स्तर पर बैच में क्वेरी तैयार करना
मेमोरी-कुशल स्थिति प्रबंधन
जब आकार की सीमाएँ पूरी हो जाती हैं तो प्रारंभिक समाप्ति

#### बेहतर कैश संरचना

```python
@dataclass
class CacheEntry:
    value: Any
    timestamp: float
    access_count: int
    ttl: Optional[float]

class CacheManager:
    label_cache: LRUCache[str, CacheEntry]
    embedding_cache: LRUCache[str, CacheEntry]
    query_result_cache: LRUCache[str, CacheEntry]
    cache_stats: CacheStatistics
```

#### बैच क्वेरी संरचनाएं

```python
@dataclass
class BatchTripleQuery:
    entities: List[str]
    query_type: QueryType  # SUBJECT, PREDICATE, OBJECT
    limit_per_entity: int

@dataclass
class BatchLabelQuery:
    entities: List[str]
    predicate: str = LABEL
```

### एपीआई (APIs)

#### नए एपीआई (New APIs):

**ग्राफ ट्रावर्सल एपीआई (GraphTraversal API)**
```python
async def optimized_follow_edges_batch(
    entities: List[str],
    max_depth: int,
    triple_limit: int,
    max_subgraph_size: int
) -> Set[Tuple[str, str, str]]
```

**बैच लेबल रिज़ॉल्यूशन एपीआई**
```python
async def resolve_labels_batch(
    entities: List[str],
    cache_manager: CacheManager
) -> Dict[str, str]
```

**कैश प्रबंधन एपीआई**
```python
class CacheManager:
    async def get_or_fetch_label(self, entity: str) -> str
    async def get_or_fetch_embeddings(self, query: str) -> List[float]
    async def cache_query_result(self, query_hash: str, result: Any, ttl: int)
    def get_cache_statistics(self) -> CacheStatistics
```

#### संशोधित एपीआई:

**GraphRag.query()** - प्रदर्शन अनुकूलन के साथ बेहतर:
कैश नियंत्रण के लिए `cache_manager` पैरामीटर जोड़ें
`performance_metrics` रिटर्न वैल्यू शामिल करें
विश्वसनीयता के लिए `query_timeout` पैरामीटर जोड़ें

**क्वेरी क्लास** - बैच प्रोसेसिंग के लिए पुनर्गठित:
व्यक्तिगत इकाई प्रसंस्करण को बैच ऑपरेशनों से बदलें
<<<<<<< HEAD
संसाधन सफाई के लिए एसिंक्रोनस कॉन्टेक्स्ट मैनेजर जोड़ें
=======
संसाधन सफाई के लिए एसिंक्रोनस संदर्भ प्रबंधक जोड़ें
>>>>>>> 82edf2d (New md files from RunPod)
लंबे समय तक चलने वाले ऑपरेशनों के लिए प्रगति कॉलबैक शामिल करें

### कार्यान्वयन विवरण

<<<<<<< HEAD
#### चरण 0: महत्वपूर्ण आर्किटेक्चरल लाइफटाइम रिफैक्टर
=======
#### चरण 0: महत्वपूर्ण वास्तुशिल्प जीवनचक्र पुनर्गठन
>>>>>>> 82edf2d (New md files from RunPod)

**वर्तमान समस्याग्रस्त कार्यान्वयन:**
```python
# INEFFICIENT: GraphRag recreated every request
class Processor(FlowProcessor):
    async def on_request(self, msg, consumer, flow):
        # PROBLEM: New GraphRag instance per request!
        self.rag = GraphRag(
            embeddings_client = flow("embeddings-request"),
            graph_embeddings_client = flow("graph-embeddings-request"),
            triples_client = flow("triples-request"),
            prompt_client = flow("prompt-request"),
            verbose=True,
        )
        # Cache starts empty every time - no benefit from previous requests
        response = await self.rag.query(...)

# VERY SHORT-LIVED: Query object created/destroyed per request
class GraphRag:
    async def query(self, query, user="trustgraph", collection="default", ...):
        q = Query(rag=self, user=user, collection=collection, ...)  # Created
        kg = await q.get_labelgraph(query)  # Used briefly
        # q automatically destroyed when function exits
```

**अनुकूलित, दीर्घकालिक संरचना:**
```python
class Processor(FlowProcessor):
    def __init__(self, **params):
        super().__init__(**params)
        self.rag_instance = None  # Will be initialized once
        self.client_connections = {}

    async def initialize_rag(self, flow):
        """Initialize GraphRag once, reuse for all requests"""
        if self.rag_instance is None:
            self.rag_instance = LongLivedGraphRag(
                embeddings_client=flow("embeddings-request"),
                graph_embeddings_client=flow("graph-embeddings-request"),
                triples_client=flow("triples-request"),
                prompt_client=flow("prompt-request"),
                verbose=True,
            )
        return self.rag_instance

    async def on_request(self, msg, consumer, flow):
        # REUSE the same GraphRag instance - caches persist!
        rag = await self.initialize_rag(flow)

        # Query object becomes lightweight execution context
        response = await rag.query_with_context(
            query=v.query,
            execution_context=QueryContext(
                user=v.user,
                collection=v.collection,
                entity_limit=entity_limit,
                # ... other params
            )
        )

class LongLivedGraphRag:
    def __init__(self, ...):
        # CONSERVATIVE caches - balance performance vs consistency
        self.label_cache = LRUCacheWithTTL(max_size=5000, ttl=300)  # 5min TTL for freshness
        # Note: No embedding cache - already cached per-query, no cross-query benefit
        # Note: No query result cache due to consistency concerns
        self.performance_metrics = PerformanceTracker()

    async def query_with_context(self, query: str, context: QueryContext):
        # Use lightweight QueryExecutor instead of heavyweight Query object
        executor = QueryExecutor(self, context)  # Minimal object
        return await executor.execute(query)

@dataclass
class QueryContext:
    """Lightweight execution context - no heavy operations"""
    user: str
    collection: str
    entity_limit: int
    triple_limit: int
    max_subgraph_size: int
    max_path_length: int

class QueryExecutor:
    """Lightweight execution context - replaces old Query class"""
    def __init__(self, rag: LongLivedGraphRag, context: QueryContext):
        self.rag = rag
        self.context = context
        # No heavy initialization - just references

    async def execute(self, query: str):
        # All heavy lifting uses persistent rag caches
        return await self.rag.execute_optimized_query(query, self.context)
```

यह वास्तुशिल्पीय परिवर्तन निम्नलिखित सुविधाएँ प्रदान करता है:
**सामान्य संबंधों वाले ग्राफों के लिए डेटाबेस क्वेरी में 10-20% की कमी** (वर्तमान में 0% की तुलना में)
प्रत्येक अनुरोध के लिए **ऑब्जेक्ट निर्माण ओवरहेड को समाप्त करना**
**स्थायी कनेक्शन पूलिंग** और क्लाइंट पुन: उपयोग
**कैश टीटीएल विंडो के भीतर क्रॉस-अनुरोध अनुकूलन**

**महत्वपूर्ण कैश स्थिरता सीमा:**
<<<<<<< HEAD
दीर्घकालिक कैशिंग से अप्रचलन का जोखिम होता है जब अंतर्निहित ग्राफ में एंटिटीज/लेबल हटा दिए जाते हैं या संशोधित किए जाते हैं। एलआरयू कैश जिसमें टीटीएल है, प्रदर्शन लाभ और डेटा ताज़गी के बीच संतुलन प्रदान करता है, लेकिन यह वास्तविक समय में ग्राफ परिवर्तनों का पता नहीं लगा सकता है।
=======
दीर्घकालिक कैशिंग से पुरानी जानकारी का जोखिम होता है जब अंतर्निहित ग्राफ में एंटिटीज/लेबल हटा दिए जाते हैं या संशोधित किए जाते हैं। एलआरयू कैश, टीटीएल के साथ, प्रदर्शन लाभ और डेटा ताज़गी के बीच एक संतुलन प्रदान करता है, लेकिन यह वास्तविक समय में ग्राफ परिवर्तनों का पता नहीं लगा सकता है।
>>>>>>> 82edf2d (New md files from RunPod)

#### चरण 1: ग्राफ ट्रैवर्सल अनुकूलन

**वर्तमान कार्यान्वयन समस्याएं:**
```python
# INEFFICIENT: 3 queries per entity per level
async def follow_edges(self, ent, subgraph, path_length):
    # Query 1: s=ent, p=None, o=None
    res = await self.rag.triples_client.query(s=ent, p=None, o=None, limit=self.triple_limit)
    # Query 2: s=None, p=ent, o=None
    res = await self.rag.triples_client.query(s=None, p=ent, o=None, limit=self.triple_limit)
    # Query 3: s=None, p=None, o=ent
    res = await self.rag.triples_client.query(s=None, p=None, o=ent, limit=self.triple_limit)
```

**अनुकूलित कार्यान्वयन:**
```python
async def optimized_traversal(self, entities: List[str], max_depth: int) -> Set[Triple]:
    visited = set()
    current_level = set(entities)
    subgraph = set()

    for depth in range(max_depth):
        if not current_level or len(subgraph) >= self.max_subgraph_size:
            break

        # Batch all queries for current level
        batch_queries = []
        for entity in current_level:
            if entity not in visited:
                batch_queries.extend([
                    TripleQuery(s=entity, p=None, o=None),
                    TripleQuery(s=None, p=entity, o=None),
                    TripleQuery(s=None, p=None, o=entity)
                ])

        # Execute all queries concurrently
        results = await self.execute_batch_queries(batch_queries)

        # Process results and prepare next level
        next_level = set()
        for result in results:
            subgraph.update(result.triples)
            next_level.update(result.new_entities)

        visited.update(current_level)
        current_level = next_level - visited

    return subgraph
```

#### चरण 2: समानांतर लेबल समाधान

**वर्तमान अनुक्रमिक कार्यान्वयन:**
```python
# INEFFICIENT: Sequential processing
for edge in subgraph:
    s = await self.maybe_label(edge[0])  # Individual query
    p = await self.maybe_label(edge[1])  # Individual query
    o = await self.maybe_label(edge[2])  # Individual query
```

**अनुकूलित समानांतर कार्यान्वयन:**
```python
async def resolve_labels_parallel(self, subgraph: List[Triple]) -> List[Triple]:
    # Collect all unique entities needing labels
    entities_to_resolve = set()
    for s, p, o in subgraph:
        entities_to_resolve.update([s, p, o])

    # Remove already cached entities
    uncached_entities = [e for e in entities_to_resolve if e not in self.label_cache]

    # Batch query for all uncached labels
    if uncached_entities:
        label_results = await self.batch_label_query(uncached_entities)
        self.label_cache.update(label_results)

    # Apply labels to subgraph
    return [
        (self.label_cache.get(s, s), self.label_cache.get(p, p), self.label_cache.get(o, o))
        for s, p, o in subgraph
    ]
```

#### चरण 3: उन्नत कैशिंग रणनीति

**एलआरयू (LRU) कैश टीटीएल (TTL) के साथ:**
```python
class LRUCacheWithTTL:
    def __init__(self, max_size: int, default_ttl: int = 3600):
        self.cache = OrderedDict()
        self.max_size = max_size
        self.default_ttl = default_ttl
        self.access_times = {}

    async def get(self, key: str) -> Optional[Any]:
        if key in self.cache:
            # Check TTL expiration
            if time.time() - self.access_times[key] > self.default_ttl:
                del self.cache[key]
                del self.access_times[key]
                return None

            # Move to end (most recently used)
            self.cache.move_to_end(key)
            return self.cache[key]
        return None

    async def put(self, key: str, value: Any):
        if key in self.cache:
            self.cache.move_to_end(key)
        else:
            if len(self.cache) >= self.max_size:
                # Remove least recently used
                oldest_key = next(iter(self.cache))
                del self.cache[oldest_key]
                del self.access_times[oldest_key]

        self.cache[key] = value
        self.access_times[key] = time.time()
```

#### चरण 4: क्वेरी अनुकूलन और निगरानी

**प्रदर्शन मेट्रिक्स संग्रह:**
```python
@dataclass
class PerformanceMetrics:
    total_queries: int
    cache_hits: int
    cache_misses: int
    avg_response_time: float
    subgraph_construction_time: float
    label_resolution_time: float
    total_entities_processed: int
    memory_usage_mb: float
```

**क्वेरी टाइमआउट और सर्किट ब्रेकर:**
```python
async def execute_with_timeout(self, query_func, timeout: int = 30):
    try:
        return await asyncio.wait_for(query_func(), timeout=timeout)
    except asyncio.TimeoutError:
        logger.error(f"Query timeout after {timeout}s")
        raise GraphRagTimeoutError(f"Query exceeded timeout of {timeout}s")
```

## कैश कंसिस्टेंसी पर विचार

**डेटा स्टेलनेस ट्रेड-ऑफ:**
<<<<<<< HEAD
**लेबल कैश (5 मिनट TTL)**: डिलीट किए गए/रीनेम किए गए एंटिटी लेबल को प्रदर्शित करने का जोखिम।
**कोई एम्बेडिंग कैशिंग नहीं:** आवश्यक नहीं है - एम्बेडिंग पहले से ही प्रति-क्वेरी कैश किए गए हैं।
**कोई परिणाम कैशिंग नहीं:** डिलीट किए गए एंटिटीज/रिलेशनशिप से पुराने सबग्राफ परिणामों को रोकता है।
=======
**लेबल कैश (5 मिनट TTL)**: हटाए गए/पुनर्नाम किए गए एंटिटी लेबल को प्रदर्शित करने का जोखिम।
**कोई एम्बेडिंग कैशिंग नहीं:** आवश्यक नहीं है - एम्बेडिंग पहले से ही प्रति-क्वेरी कैश किए गए हैं।
**कोई परिणाम कैशिंग नहीं:** हटाए गए एंटिटीज/रिलेशनशिप से पुराने सबग्राफ परिणामों को रोकता है।
>>>>>>> 82edf2d (New md files from RunPod)

**शमन रणनीतियाँ:**
**रूढ़िवादी TTL मान:** प्रदर्शन लाभ (10-20%) को डेटा की ताजगी के साथ संतुलित करें।
**कैश अमान्यकरण हुक:** ग्राफ उत्परिवर्तन घटनाओं के साथ वैकल्पिक एकीकरण।
**निगरानी डैशबोर्ड:** कैश हिट दरों बनाम स्टेलनेस घटनाओं को ट्रैक करें।
**कॉन्फ़िगर करने योग्य कैश नीतियां:** उत्परिवर्तन आवृत्ति के आधार पर प्रति-तैनाती ट्यूनिंग की अनुमति दें।

<<<<<<< HEAD
**ग्राफ उत्परिवर्तन दर द्वारा अनुशंसित कैश कॉन्फ़िगरेशन:**
=======
**अनुशंसित कैश कॉन्फ़िगरेशन ग्राफ उत्परिवर्तन दर द्वारा:**
>>>>>>> 82edf2d (New md files from RunPod)
**उच्च उत्परिवर्तन (>100 परिवर्तन/घंटा):** TTL=60s, छोटे कैश आकार।
**मध्यम उत्परिवर्तन (10-100 परिवर्तन/घंटा):** TTL=300s (डिफ़ॉल्ट)।
**कम उत्परिवर्तन (<10 परिवर्तन/घंटा):** TTL=600s, बड़े कैश आकार।

## सुरक्षा संबंधी विचार

**क्वेरी इंजेक्शन रोकथाम:**
सभी एंटिटी पहचानकर्ताओं और क्वेरी मापदंडों को मान्य करें।
सभी डेटाबेस इंटरैक्शन के लिए पैरामीटराइज़्ड क्वेरी का उपयोग करें।
DoS हमलों को रोकने के लिए क्वेरी जटिलता सीमाएं लागू करें।

<<<<<<< HEAD
**संसाधन सुरक्षा:**
=======
**संसाधन संरक्षण:**
>>>>>>> 82edf2d (New md files from RunPod)
अधिकतम सबग्राफ आकार सीमाओं को लागू करें।
संसाधन समाप्त होने से रोकने के लिए क्वेरी टाइमआउट लागू करें।
मेमोरी उपयोग निगरानी और सीमाएं जोड़ें।

**पहुंच नियंत्रण:**
मौजूदा उपयोगकर्ता और संग्रह अलगाव बनाए रखें।
<<<<<<< HEAD
प्रदर्शन-प्रभावित करने वाले कार्यों के लिए ऑडिट लॉगिंग जोड़ें।
महंगे कार्यों के लिए दर सीमित करना लागू करें।
=======
प्रदर्शन-प्रभावित संचालन के लिए ऑडिट लॉगिंग जोड़ें।
महंगे संचालन के लिए दर सीमित करना लागू करें।
>>>>>>> 82edf2d (New md files from RunPod)

## प्रदर्शन संबंधी विचार

### अपेक्षित प्रदर्शन सुधार

**क्वेरी में कमी:**
<<<<<<< HEAD
वर्तमान: विशिष्ट अनुरोध के लिए ~9,000+ क्वेरी
अनुकूलित: ~50-100 बैच क्वेरी (98% कमी)

**प्रतिक्रिया समय में सुधार:**
ग्राफ ट्रैवर्सल: 15-20s → 3-5s (4-5x तेज़)
लेबल रिज़ॉल्यूशन: 8-12s → 2-4s (3x तेज़)
कुल क्वेरी: 25-35s → 6-10s (3-4x सुधार)

**मेमोरी दक्षता:**
बाउंडेड कैश आकार मेमोरी लीक को रोकते हैं।
=======
वर्तमान: विशिष्ट अनुरोध के लिए ~9,000+ क्वेरी।
अनुकूलित: ~50-100 बैच क्वेरी (98% कमी)।

**प्रतिक्रिया समय में सुधार:**
ग्राफ ट्रैवर्सल: 15-20s → 3-5s (4-5x तेज़)।
लेबल रिज़ॉल्यूशन: 8-12s → 2-4s (3x तेज़)।
कुल क्वेरी: 25-35s → 6-10s (3-4x सुधार)।

**मेमोरी दक्षता:**
बंधी हुई कैश आकार मेमोरी लीक को रोकते हैं।
>>>>>>> 82edf2d (New md files from RunPod)
कुशल डेटा संरचनाएं मेमोरी पदचिह्न को ~40% तक कम करती हैं।
उचित संसाधन सफाई के माध्यम से बेहतर कचरा संग्रह।

**यथार्थवादी प्रदर्शन अपेक्षाएं:**
**लेबल कैश:** सामान्य संबंधों वाले ग्राफ़ के लिए 10-20% क्वेरी में कमी।
**बैचिंग अनुकूलन:** 50-80% क्वेरी में कमी (प्राथमिक अनुकूलन)।
**ऑब्जेक्ट लाइफटाइम अनुकूलन:** प्रति-अनुरोध निर्माण ओवरहेड को समाप्त करें।
**कुल सुधार:** बैचिंग से मुख्य रूप से 3-4x प्रतिक्रिया समय में सुधार।

**स्केलेबिलिटी में सुधार:**
3-5x बड़े नॉलेज ग्राफ़ के लिए समर्थन (कैश कंसिस्टेंसी आवश्यकताओं द्वारा सीमित)।
3-5x उच्च समवर्ती अनुरोध क्षमता।
कनेक्शन पुन: उपयोग के माध्यम से बेहतर संसाधन उपयोग।

### प्रदर्शन निगरानी

**रियल-टाइम मेट्रिक्स:**
ऑपरेशन प्रकार द्वारा क्वेरी निष्पादन समय।
कैश हिट अनुपात और प्रभावशीलता।
डेटाबेस कनेक्शन पूल उपयोग।
मेमोरी उपयोग और कचरा संग्रह प्रभाव।

**प्रदर्शन बेंचमार्किंग:**
स्वचालित प्रदर्शन प्रतिगमन परीक्षण
वास्तविक डेटा वॉल्यूम के साथ लोड परीक्षण
वर्तमान कार्यान्वयन के खिलाफ तुलना बेंचमार्क

## परीक्षण रणनीति

### यूनिट परीक्षण
ट्रैवर्सल, कैशिंग और लेबल रिज़ॉल्यूशन के लिए व्यक्तिगत घटक परीक्षण
प्रदर्शन परीक्षण के लिए मॉक डेटाबेस इंटरैक्शन
कैश निष्कासन और TTL समाप्ति परीक्षण
त्रुटि हैंडलिंग और टाइमआउट परिदृश्य

### एकीकरण परीक्षण
अनुकूलन के साथ एंड-टू-एंड GraphRAG क्वेरी परीक्षण
वास्तविक डेटा के साथ डेटाबेस इंटरैक्शन परीक्षण
समवर्ती अनुरोध हैंडलिंग और संसाधन प्रबंधन
मेमोरी लीक का पता लगाना और संसाधन सफाई सत्यापन

### प्रदर्शन परीक्षण
वर्तमान कार्यान्वयन के खिलाफ बेंचमार्क परीक्षण
विभिन्न ग्राफ आकारों और जटिलताओं के साथ लोड परीक्षण
मेमोरी और कनेक्शन सीमाओं के लिए तनाव परीक्षण
प्रदर्शन सुधारों के लिए प्रतिगमन परीक्षण

### अनुकूलता परीक्षण
मौजूदा GraphRAG API संगतता सत्यापित करें
विभिन्न ग्राफ डेटाबेस बैकएंड के साथ परीक्षण करें
वर्तमान कार्यान्वयन की तुलना में परिणाम सटीकता को मान्य करें

## कार्यान्वयन योजना

### प्रत्यक्ष कार्यान्वयन दृष्टिकोण
<<<<<<< HEAD
चूंकि API में परिवर्तन की अनुमति है, इसलिए माइग्रेशन जटिलता के बिना अनुकूलन को सीधे लागू करें:
=======
चूंकि एपीआई में बदलाव की अनुमति है, इसलिए माइग्रेशन जटिलता के बिना अनुकूलन को सीधे लागू करें:
>>>>>>> 82edf2d (New md files from RunPod)

1. **`follow_edges` विधि को बदलें**: पुनरावृत्त बैच ट्रैवर्सल के साथ फिर से लिखें
2. **`get_labelgraph` को अनुकूलित करें**: समानांतर लेबल रिज़ॉल्यूशन लागू करें
3. **लंबे समय तक चलने वाला GraphRag जोड़ें**: प्रोसेसर को एक स्थायी उदाहरण बनाए रखने के लिए संशोधित करें
4. **लेबल कैशिंग लागू करें**: GraphRag क्लास में LRU कैश और TTL जोड़ें

### परिवर्तनों का दायरा
**क्वेरी क्लास**: `follow_edges` में ~50 पंक्तियों को बदलें, बैच हैंडलिंग के लिए ~30 पंक्तियाँ जोड़ें
**GraphRag क्लास**: एक कैशिंग परत जोड़ें (~40 पंक्तियाँ)
**प्रोसेसर क्लास**: एक स्थायी GraphRag उदाहरण का उपयोग करने के लिए संशोधित करें (~20 पंक्तियाँ)
**कुल**: केंद्रित परिवर्तनों की ~140 पंक्तियाँ, ज्यादातर मौजूदा कक्षाओं के भीतर

## समयरेखा

**सप्ताह 1: मुख्य कार्यान्वयन**
बैच पुनरावृत्त ट्रैवर्सल के साथ `follow_edges` को बदलें
`get_labelgraph` में समानांतर लेबल रिज़ॉल्यूशन लागू करें
प्रोसेसर में एक लंबे समय तक चलने वाला GraphRag उदाहरण जोड़ें
एक लेबल कैशिंग परत लागू करें

**सप्ताह 2: परीक्षण और एकीकरण**
<<<<<<< HEAD
नए ट्रैवर्सल और कैशिंग तर्क के लिए यूनिट परीक्षण
=======
नए ट्रैवर्सल और कैशिंग लॉजिक के लिए यूनिट परीक्षण
>>>>>>> 82edf2d (New md files from RunPod)
वर्तमान कार्यान्वयन के खिलाफ प्रदर्शन बेंचमार्किंग
वास्तविक ग्राफ डेटा के साथ एकीकरण परीक्षण
कोड समीक्षा और अनुकूलन

**सप्ताह 3: परिनियोजन**
अनुकूलित कार्यान्वयन को तैनात करें
प्रदर्शन सुधारों की निगरानी करें
वास्तविक उपयोग के आधार पर कैश TTL और बैच आकारों को ठीक करें

## खुले प्रश्न

**डेटाबेस कनेक्शन पूलिंग**: क्या हमें कस्टम कनेक्शन पूलिंग लागू करनी चाहिए या मौजूदा डेटाबेस क्लाइंट पूलिंग पर भरोसा करना चाहिए?
<<<<<<< HEAD
**कैश दृढ़ता**: क्या लेबल और एम्बेडिंग कैश सेवा पुनरारंभों में बने रहने चाहिए?
=======
**कैश दृढ़ता**: क्या लेबल और एम्बेडिंग कैश सेवा पुनरारंभों में बने रहेंगे?
>>>>>>> 82edf2d (New md files from RunPod)
**वितरित कैशिंग**: मल्टी-इंस्टेंस परिनियोजन के लिए, क्या हमें Redis/Memcached के साथ वितरित कैशिंग लागू करनी चाहिए?
**क्वेरी परिणाम प्रारूप**: क्या हमें बेहतर मेमोरी दक्षता के लिए आंतरिक ट्रिपल प्रतिनिधित्व को अनुकूलित करना चाहिए?
**निगरानी एकीकरण**: मौजूदा निगरानी प्रणालियों (Prometheus, आदि) के लिए कौन से मेट्रिक्स उजागर किए जाने चाहिए?

## संदर्भ

[GraphRAG मूल कार्यान्वयन](trustgraph-flow/trustgraph/retrieval/graph_rag/graph_rag.py)
[ट्रस्टग्राफ आर्किटेक्चर सिद्धांत](architecture-principles.md)
[संग्रह प्रबंधन विनिर्देश](collection-management.md)
