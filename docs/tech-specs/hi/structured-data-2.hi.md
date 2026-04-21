---
layout: default
title: "संरचित डेटा तकनीकी विनिर्देश (भाग 2)"
parent: "Hindi (Beta)"
---

# संरचित डेटा तकनीकी विनिर्देश (भाग 2)

> **Beta Translation:** This document was translated via Machine Learning and as such may not be 100% accurate. All non-English languages are currently classified as Beta.

## अवलोकन

यह विनिर्देश उन मुद्दों और कमियों को संबोधित करता है जिन्हें ट्रस्टग्राफ के संरचित डेटा एकीकरण के प्रारंभिक कार्यान्वयन के दौरान पहचाना गया था, जैसा कि `structured-data.md` में वर्णित है।

## समस्या विवरण

### 1. नामकरण में असंगति: "ऑब्जेक्ट" बनाम "पंक्ति"

वर्तमान कार्यान्वयन में पूरे समय "ऑब्जेक्ट" शब्दावली का उपयोग किया जाता है (उदाहरण के लिए, `ExtractedObject`, ऑब्जेक्ट निष्कर्षण, ऑब्जेक्ट एम्बेडिंग)। यह नामकरण बहुत सामान्य है और भ्रम पैदा करता है:

"ऑब्जेक्ट" सॉफ्टवेयर में एक अतिव्यापी शब्द है (पायथन ऑब्जेक्ट, JSON ऑब्जेक्ट, आदि)।
संसाधित डेटा अनिवार्य रूप से सारणीबद्ध है - परिभाषित स्कीमा वाली तालिकाओं में पंक्तियाँ।
"पंक्ति" डेटा मॉडल का अधिक सटीक वर्णन है और यह डेटाबेस शब्दावली के साथ मेल खाता है।

यह असंगति मॉड्यूल नामों, क्लास नामों, संदेश प्रकारों और दस्तावेज़ों में दिखाई देती है।

### 2. पंक्ति भंडारण क्वेरी सीमाएँ

वर्तमान पंक्ति भंडारण कार्यान्वयन में महत्वपूर्ण क्वेरी सीमाएँ हैं:

**प्राकृतिक भाषा बेमेल**: क्वेरी वास्तविक दुनिया के डेटा विविधताओं के साथ संघर्ष करती हैं। उदाहरण के लिए:
`"CHESTNUT ST"` युक्त एक सड़क डेटाबेस को `"Chestnut Street"` के बारे में पूछने पर खोजना मुश्किल है।
संक्षिप्त नाम, केस अंतर और स्वरूपण भिन्नताएं सटीक-मेल क्वेरी को तोड़ देती हैं।
उपयोगकर्ताओं को सिमेंटिक समझ की उम्मीद होती है, लेकिन स्टोर शाब्दिक मिलान प्रदान करता है।

**स्कीमा विकास मुद्दे**: स्कीमा में परिवर्तन समस्याएं पैदा करते हैं:
मौजूदा डेटा अद्यतन स्कीमा के अनुरूप नहीं हो सकता है।
तालिका संरचना में परिवर्तन क्वेरी और डेटा अखंडता को तोड़ सकते हैं।
स्कीमा अपडेट के लिए कोई स्पष्ट माइग्रेशन पथ नहीं है।

### 3. पंक्ति एम्बेडिंग की आवश्यकता

समस्या 2 से संबंधित, सिस्टम को पंक्ति डेटा के लिए वेक्टर एम्बेडिंग की आवश्यकता है ताकि:

संरचित डेटा में सिमेंटिक खोज (जब डेटा में "CHESTNUT ST" हो तो "Chestnut Street" खोजना)।
धुंधली क्वेरी के लिए समानता मिलान।
संरचित फ़िल्टर को सिमेंटिक समानता के साथ मिलाने वाली हाइब्रिड खोज।
बेहतर प्राकृतिक भाषा क्वेरी समर्थन।

एम्बेडिंग सेवा को निर्दिष्ट किया गया था लेकिन लागू नहीं किया गया था।

### 4. पंक्ति डेटा अंतर्ग्रहण अधूरा

संरचित डेटा अंतर्ग्रहण पाइपलाइन पूरी तरह से कार्यात्मक नहीं है:

इनपुट प्रारूपों (CSV, JSON, आदि) को वर्गीकृत करने के लिए नैदानिक संकेत मौजूद हैं।
इन संकेतों का उपयोग करने वाली अंतर्ग्रहण सेवा को सिस्टम में प्लंब नहीं किया गया है।
पंक्ति स्टोर में पूर्व-संरचित डेटा लोड करने के लिए कोई एंड-टू-एंड पथ नहीं है।

## लक्ष्य

**स्कीमा लचीलापन**: मौजूदा डेटा को तोड़ने या माइग्रेशन की आवश्यकता के बिना स्कीमा विकास को सक्षम करें।
**संगत नामकरण**: पूरे कोडबेस में "पंक्ति" शब्दावली का मानकीकरण करें।
**सिमेंटिक क्वेरी क्षमता**: पंक्ति एम्बेडिंग के माध्यम से धुंधली/सिमेंटिक मिलान का समर्थन करें।
**पूर्ण अंतर्ग्रहण पाइपलाइन**: संरचित डेटा लोड करने के लिए एंड-टू-एंड पथ प्रदान करें।

## तकनीकी डिजाइन

### एकीकृत पंक्ति भंडारण स्कीमा

पिछले कार्यान्वयन में प्रत्येक स्कीमा के लिए एक अलग कैसेंड्रा तालिका बनाई गई थी। इससे तब समस्याएं हुईं जब स्कीमा विकसित हुए, क्योंकि तालिका संरचना में परिवर्तन के लिए माइग्रेशन की आवश्यकता होती थी।

नए डिज़ाइन में सभी पंक्ति डेटा के लिए एक एकल, एकीकृत तालिका का उपयोग किया जाता है:

```sql
CREATE TABLE rows (
    collection text,
    schema_name text,
    index_name text,
    index_value frozen<list<text>>,
    data map<text, text>,
    source text,
    PRIMARY KEY ((collection, schema_name, index_name), index_value)
)
```

#### कॉलम परिभाषाएँ

| कॉलम | प्रकार | विवरण |
|--------|------|-------------|
| `collection` | `text` | डेटा संग्रह/आयात पहचानकर्ता (मेटाडेटा से) |
| `schema_name` | `text` | स्कीमा का नाम जिससे यह पंक्ति मेल खाती है |
| `index_name` | `text` | अनुक्रमित फ़ील्ड का नाम, संयुक्त अल्पविराम के साथ (मिश्रित के लिए) |
| `index_value` | `frozen<list<text>>` | अनुक्रमित मानों की सूची |
| `data` | `map<text, text>` | पंक्ति डेटा कुंजी-मान जोड़े के रूप में |
| `source` | `text` | वैकल्पिक यूआरआई जो नॉलेज ग्राफ में मूल जानकारी से लिंक करता है। खाली स्ट्रिंग या NULL इंगित करता है कि कोई स्रोत नहीं है। |

#### अनुक्रमण प्रबंधन

प्रत्येक पंक्ति कई बार संग्रहीत की जाती है - स्कीमा में परिभाषित प्रत्येक अनुक्रमित फ़ील्ड के लिए एक बार। प्राथमिक कुंजी फ़ील्ड को किसी विशेष मार्कर के बिना एक अनुक्रमणिका के रूप में माना जाता है, जो भविष्य में लचीलापन प्रदान करता है।

**सिंगल-फ़ील्ड अनुक्रमणिका का उदाहरण:**
स्कीमा `email` को अनुक्रमित के रूप में परिभाषित करता है
`index_name = "email"`
`index_value = ['foo@bar.com']`

**मिश्रित अनुक्रमणिका का उदाहरण:**
स्कीमा `region` और `status` पर मिश्रित अनुक्रमणिका को परिभाषित करता है
`index_name = "region,status"` (फ़ील्ड नाम क्रमबद्ध और अल्पविराम से जुड़े हुए)
`index_value = ['US', 'active']` (फ़ील्ड नामों के समान क्रम में मान)

**प्राथमिक कुंजी का उदाहरण:**
स्कीमा `customer_id` को प्राथमिक कुंजी के रूप में परिभाषित करता है
`index_name = "customer_id"`
`index_value = ['CUST001']`

#### क्वेरी पैटर्न

सभी क्वेरी एक ही पैटर्न का पालन करती हैं, चाहे कोई भी अनुक्रमणिका उपयोग की जाए:

```sql
SELECT * FROM rows
WHERE collection = 'import_2024'
  AND schema_name = 'customers'
  AND index_name = 'email'
  AND index_value = ['foo@bar.com']
```

#### डिज़ाइन में संतुलन

**लाभ:**
स्कीमा में बदलावों के लिए टेबल संरचना में बदलाव की आवश्यकता नहीं होती है।
पंक्ति डेटा कैसेंड्रा के लिए अस्पष्ट है - फ़ील्ड जोड़ने/हटाने से कोई फर्क नहीं पड़ता।
सभी एक्सेस विधियों के लिए सुसंगत क्वेरी पैटर्न।
कोई कैसेंड्रा सेकेंडरी इंडेक्स नहीं (जो बड़े पैमाने पर धीमे हो सकते हैं)।
पूरी तरह से देशी कैसेंड्रा प्रकार (`map`, `frozen<list>`)।

**गड़बड़ियाँ:**
राइट एम्प्लीफिकेशन: प्रत्येक पंक्ति डालने = N डालने (प्रत्येक इंडेक्स्ड फ़ील्ड के लिए एक)।
डुप्लिकेट पंक्ति डेटा के कारण स्टोरेज ओवरहेड।
प्रकार की जानकारी स्कीमा कॉन्फ़िगरेशन में संग्रहीत है, एप्लिकेशन लेयर पर रूपांतरण।

#### संगति मॉडल

डिज़ाइन कुछ सरलीकरणों को स्वीकार करता है:

1. **कोई पंक्ति अपडेट नहीं**: सिस्टम केवल अपेंड-ओनली है। यह एक ही पंक्ति की कई प्रतियों को अपडेट करने के बारे में संगति संबंधी चिंताओं को समाप्त करता है।

2. **स्कीमा परिवर्तन सहिष्णुता**: जब स्कीमा बदलते हैं (उदाहरण के लिए, इंडेक्स जोड़े/हटाए जाते हैं), तो मौजूदा पंक्तियाँ अपनी मूल इंडेक्सिंग को बनाए रखती हैं। पुराने पंक्तियों को नए इंडेक्स के माध्यम से खोजा नहीं जा सकता है। यदि आवश्यक हो, तो उपयोगकर्ता संगति सुनिश्चित करने के लिए एक स्कीमा को हटा और पुनः बना सकते हैं।

### विभाजन ट्रैकिंग और हटाना

#### समस्या

विभाजन कुंजी `(collection, schema_name, index_name)` के साथ, कुशल हटाने के लिए सभी विभाजन कुंजियों को हटाने की आवश्यकता होती है। केवल `collection` या `collection + schema_name` द्वारा हटाना उन सभी `index_name` मानों को जानने की आवश्यकता होती है जिनमें डेटा है।

#### विभाजन ट्रैकिंग टेबल

एक सेकेंडरी लुकअप टेबल ट्रैक करती है कि कौन से विभाजन मौजूद हैं:

```sql
CREATE TABLE row_partitions (
    collection text,
    schema_name text,
    index_name text,
    PRIMARY KEY ((collection), schema_name, index_name)
)
```

यह हटाने के कार्यों के लिए विभाजनों की कुशल खोज को सक्षम बनाता है।

#### पंक्ति लेखक व्यवहार

पंक्ति लेखक पंजीकृत `(collection, schema_name)` युग्मों का एक इन-मेमोरी कैश बनाए रखता है। पंक्ति को संसाधित करते समय:

1. जांचें कि `(collection, schema_name)` कैश में है या नहीं।
2. यदि कैश में नहीं है (इस युग्म के लिए पहली पंक्ति):
   सभी इंडेक्स नामों को प्राप्त करने के लिए स्कीमा कॉन्फ़िगरेशन देखें।
   प्रत्येक `(collection, schema_name, index_name)` के लिए `row_partitions` में प्रविष्टियाँ डालें।
   युग्म को कैश में जोड़ें।
3. पंक्ति डेटा लिखने के साथ आगे बढ़ें।

पंक्ति लेखक स्कीमा कॉन्फ़िगरेशन परिवर्तन घटनाओं की भी निगरानी करता है। जब कोई स्कीमा बदलता है, तो प्रासंगिक कैश प्रविष्टियाँ साफ़ कर दी जाती हैं ताकि अगली पंक्ति अपडेट किए गए इंडेक्स नामों के साथ पुनः पंजीकरण को ट्रिगर करे।

इस दृष्टिकोण से यह सुनिश्चित होता है:
लुकअप तालिका लेखन प्रत्येक `(collection, schema_name)` युग्म के लिए एक बार होता है, प्रत्येक पंक्ति के लिए नहीं।
लुकअप तालिका उन इंडेक्स को दर्शाती है जो डेटा लिखे जाने पर सक्रिय थे।
आयात के दौरान होने वाले स्कीमा परिवर्तनों को सही ढंग से पहचाना जाता है।

#### हटाने के कार्य

**संग्रह हटाएं:**
```sql
-- 1. Discover all partitions
SELECT schema_name, index_name FROM row_partitions WHERE collection = 'X';

-- 2. Delete each partition from rows table
DELETE FROM rows WHERE collection = 'X' AND schema_name = '...' AND index_name = '...';
-- (repeat for each discovered partition)

-- 3. Clean up the lookup table
DELETE FROM row_partitions WHERE collection = 'X';
```

**संग्रह और स्कीमा हटाएं:**
```sql
-- 1. Discover partitions for this schema
SELECT index_name FROM row_partitions WHERE collection = 'X' AND schema_name = 'Y';

-- 2. Delete each partition from rows table
DELETE FROM rows WHERE collection = 'X' AND schema_name = 'Y' AND index_name = '...';
-- (repeat for each discovered partition)

-- 3. Clean up the lookup table entries
DELETE FROM row_partitions WHERE collection = 'X' AND schema_name = 'Y';
```

### पंक्ति एम्बेडिंग

पंक्ति एम्बेडिंग, अनुक्रमित मानों पर अर्थपूर्ण/अस्पष्ट मिलान को सक्षम करते हैं, जिससे प्राकृतिक भाषा में विसंगति की समस्या हल होती है (उदाहरण के लिए, "चेस्टनट स्ट्रीट" के लिए खोज करते समय "चेस्टनट एसटी" खोजना)।

#### डिज़ाइन अवलोकन

प्रत्येक अनुक्रमित मान को एम्बेड किया जाता है और एक वेक्टर स्टोर (क्यूड्रेंट) में संग्रहीत किया जाता है। क्वेरी के समय, क्वेरी को एम्बेड किया जाता है, समान वेक्टर पाए जाते हैं, और संबंधित मेटाडेटा का उपयोग कैसेंड्रा में वास्तविक पंक्तियों को देखने के लिए किया जाता है।

#### क्यूड्रेंट संग्रह संरचना

प्रत्येक `(user, collection, schema_name, dimension)` टपल के लिए एक क्यूड्रेंट संग्रह:

**संग्रह नामकरण:** `rows_{user}_{collection}_{schema_name}_{dimension}`
नामों को साफ़ किया जाता है (गैर-अक्षरांकीय वर्णों को `_` से बदला जाता है, लोअरकेस किया जाता है, संख्यात्मक उपसर्गों को `r_` उपसर्ग मिलता है)
**तर्क:** एक `(user, collection, schema_name)` उदाहरण को मिलान वाले क्यूड्रेंट संग्रहों को हटाकर साफ-सुथरे तरीके से हटाने की अनुमति देता है; आयाम प्रत्यय विभिन्न एम्बेडिंग मॉडल को एक साथ मौजूद रहने की अनुमति देता है।

#### क्या एम्बेड किया जाता है

अनुक्रमण मानों का पाठ प्रतिनिधित्व:

| अनुक्रमण प्रकार | उदाहरण `index_value` | एम्बेड करने के लिए पाठ |
|------------|----------------------|---------------|
| एकल-क्षेत्र | `['foo@bar.com']` | `"foo@bar.com"` |
| समग्र | `['US', 'active']` | `"US active"` (स्पेस-जोड़ा हुआ) |

#### बिंदु संरचना

प्रत्येक क्यूड्रेंट बिंदु में शामिल हैं:

```json
{
  "id": "<uuid>",
  "vector": [0.1, 0.2, ...],
  "payload": {
    "index_name": "street_name",
    "index_value": ["CHESTNUT ST"],
    "text": "CHESTNUT ST"
  }
}
```

| पेलोड फ़ील्ड | विवरण |
|---------------|-------------|
| `index_name` | यह एम्बेडिंग किस अनुक्रमित फ़ील्ड(s) का प्रतिनिधित्व करता है |
| `index_value` | मूल्यों की मूल सूची (कैसेंड्रा लुकअप के लिए) |
| `text` | वह पाठ जिसे एम्बेड किया गया था (डीबगिंग/प्रदर्शन के लिए) |

ध्यान दें: `user`, `collection`, और `schema_name` Qdrant संग्रह नाम से निहित हैं।

#### क्वेरी प्रवाह

1. उपयोगकर्ता U, संग्रह X, स्कीमा Y के भीतर "चेस्टनट स्ट्रीट" के लिए क्वेरी करता है।
2. क्वेरी टेक्स्ट को एम्बेड करें।
3. उपसर्ग `rows_U_X_Y_` से मेल खाने वाले Qdrant संग्रह नाम(s) निर्धारित करें।
4. निकटतम वैक्टरों के लिए मिलान करने वाले Qdrant संग्रह(s) की खोज करें।
5. `index_name` और `index_value` युक्त पेलोड वाले मिलान करने वाले बिंदुओं को प्राप्त करें।
6. कैसेंड्रा को क्वेरी करें:
   ```sql
   SELECT * FROM rows
   WHERE collection = 'X'
     AND schema_name = 'Y'
     AND index_name = '<from payload>'
     AND index_value = <from payload>
   ```
7. मिलान किए गए पंक्तियों को वापस करना

#### वैकल्पिक: इंडेक्स नाम द्वारा फ़िल्टरिंग

क्वेरी वैकल्पिक रूप से Qdrant में `index_name` द्वारा फ़िल्टर की जा सकती हैं ताकि केवल विशिष्ट फ़ील्ड की खोज की जा सके:

**"उन सभी फ़ील्ड को खोजें जो 'Chestnut' से मेल खाते हैं"** → संग्रह में सभी वैक्टर की खोज करें
**"उन सड़कों को खोजें जिनका नाम 'Chestnut' से मेल खाता है"** → उन पंक्तियों को फ़िल्टर करें जहाँ `payload.index_name = 'street_name'`

#### आर्किटेक्चर

पंक्ति एम्बेडिंग **दो-चरणीय पैटर्न** का पालन करते हैं जिसका उपयोग GraphRAG (ग्राफ-एम्बेडिंग, दस्तावेज़-एम्बेडिंग) द्वारा किया जाता है:

**चरण 1: एम्बेडिंग गणना** (`trustgraph-flow/trustgraph/embeddings/row_embeddings/`) - `ExtractedObject` का उपयोग करता है, एम्बेडिंग सेवा के माध्यम से एम्बेडिंग की गणना करता है, `RowEmbeddings` आउटपुट करता है
**चरण 2: एम्बेडिंग भंडारण** (`trustgraph-flow/trustgraph/storage/row_embeddings/qdrant/`) - `RowEmbeddings` का उपयोग करता है, वैक्टर को Qdrant में लिखता है

कैसेंड्रा पंक्ति लेखक एक अलग समानांतर उपभोक्ता है:

**कैसेंड्रा पंक्ति लेखक** (`trustgraph-flow/trustgraph/storage/rows/cassandra`) - `ExtractedObject` का उपयोग करता है, पंक्तियों को कैसेंड्रा में लिखता है

तीनों सेवाएं एक ही प्रवाह से डेटा लेती हैं, जिससे वे अलग-अलग रहती हैं। यह अनुमति देता है:
कैसेंड्रा लेखन बनाम एम्बेडिंग पीढ़ी बनाम वेक्टर भंडारण का स्वतंत्र स्केलिंग
यदि आवश्यक न हो तो एम्बेडिंग सेवाओं को अक्षम किया जा सकता है
एक सेवा में विफलता अन्य सेवाओं को प्रभावित नहीं करती है
GraphRAG पाइपलाइनों के साथ सुसंगत आर्किटेक्चर

#### लेखन पथ

**चरण 1 (पंक्ति-एम्बेडिंग प्रोसेसर):** जब एक `ExtractedObject` प्राप्त होता है:

1. अनुक्रमित फ़ील्ड खोजने के लिए स्कीमा देखें
2. प्रत्येक अनुक्रमित फ़ील्ड के लिए:
   अनुक्रमण मान का पाठ प्रतिनिधित्व बनाएं
   एम्बेडिंग सेवा के माध्यम से एम्बेडिंग की गणना करें
3. सभी गणना किए गए वैक्टर युक्त एक `RowEmbeddings` संदेश आउटपुट करें

**चरण 2 (पंक्ति-एम्बेडिंग-लिखें-Qdrant):** जब एक `RowEmbeddings` प्राप्त होता है:

1. संदेश में प्रत्येक एम्बेडिंग के लिए:
   `(user, collection, schema_name, dimension)` से Qdrant संग्रह निर्धारित करें
   यदि आवश्यक हो तो संग्रह बनाएं (पहली बार लिखने पर आलसी निर्माण)
   वेक्टर और पेलोड के साथ पॉइंट अपサート करें

#### संदेश प्रकार

```python
@dataclass
class RowIndexEmbedding:
    index_name: str              # The indexed field name(s)
    index_value: list[str]       # The field value(s)
    text: str                    # Text that was embedded
    vectors: list[list[float]]   # Computed embedding vectors

@dataclass
class RowEmbeddings:
    metadata: Metadata
    schema_name: str
    embeddings: list[RowIndexEmbedding]
```

#### विलोपन एकीकरण

Qdrant संग्रह, संग्रह नाम पैटर्न पर उपसर्ग मिलान द्वारा खोजे जाते हैं:

**`(user, collection)` हटाएं:**
1. `rows_{user}_{collection}_` उपसर्ग से मेल खाने वाले सभी Qdrant संग्रहों की सूची बनाएं
2. प्रत्येक मेल खाने वाले संग्रह को हटाएं
3. कैसेंड्रा पंक्तियों के विभाजन को हटाएं (जैसा कि ऊपर प्रलेखित है)
4. `row_partitions` प्रविष्टियों को साफ़ करें

**`(user, collection, schema_name)` हटाएं:**
1. `rows_{user}_{collection}_{schema_name}_` उपसर्ग से मेल खाने वाले सभी Qdrant संग्रहों की सूची बनाएं
2. प्रत्येक मेल खाने वाले संग्रह को हटाएं (यह कई आयामों को संभालता है)
3. कैसेंड्रा पंक्तियों के विभाजन को हटाएं
4. `row_partitions` को साफ़ करें

#### मॉड्यूल स्थान

| चरण | मॉड्यूल | प्रवेश बिंदु |
|-------|--------|-------------|
| चरण 1 | `trustgraph-flow/trustgraph/embeddings/row_embeddings/` | `row-embeddings` |
| चरण 2 | `trustgraph-flow/trustgraph/storage/row_embeddings/qdrant/` | `row-embeddings-write-qdrant` |

### पंक्ति एम्बेडिंग क्वेरी एपीआई

पंक्ति एम्बेडिंग क्वेरी, GraphQL पंक्ति क्वेरी सेवा से एक **अलग एपीआई** है:

| एपीआई | उद्देश्य | बैकएंड |
|-----|---------|---------|
| पंक्ति क्वेरी (GraphQL) | अनुक्रमित फ़ील्ड पर सटीक मिलान | कैसेंड्रा |
| पंक्ति एम्बेडिंग क्वेरी | अस्पष्ट/अर्थ संबंधी मिलान | Qdrant |

यह अलगाव चिंताओं को साफ रखता है:
GraphQL सेवा सटीक, संरचित प्रश्नों पर केंद्रित है
एम्बेडिंग एपीआई अर्थ संबंधी समानता को संभालता है
उपयोगकर्ता कार्यप्रवाह: उम्मीदवारों को खोजने के लिए एम्बेडिंग के माध्यम से अस्पष्ट खोज, फिर पूर्ण पंक्ति डेटा प्राप्त करने के लिए सटीक क्वेरी

#### अनुरोध/प्रतिक्रिया स्कीमा

```python
@dataclass
class RowEmbeddingsRequest:
    vectors: list[list[float]]    # Query vectors (pre-computed embeddings)
    user: str = ""
    collection: str = ""
    schema_name: str = ""
    index_name: str = ""          # Optional: filter to specific index
    limit: int = 10               # Max results per vector

@dataclass
class RowIndexMatch:
    index_name: str = ""          # The matched index field(s)
    index_value: list[str] = []   # The matched value(s)
    text: str = ""                # Original text that was embedded
    score: float = 0.0            # Similarity score

@dataclass
class RowEmbeddingsResponse:
    error: Error | None = None
    matches: list[RowIndexMatch] = []
```

#### क्वेरी प्रोसेसर

मॉड्यूल: `trustgraph-flow/trustgraph/query/row_embeddings/qdrant`

प्रवेश बिंदु: `row-embeddings-query-qdrant`

प्रोसेसर:
1. `RowEmbeddingsRequest` के साथ क्वेरी वेक्टर प्राप्त करता है
2. उपसर्ग मिलान के माध्यम से उपयुक्त Qdrant संग्रह ढूंढता है
3. वैकल्पिक `index_name` फ़िल्टर के साथ निकटतम वेक्टर खोजता है
4. मिलान किए गए इंडेक्स जानकारी के साथ `RowEmbeddingsResponse` लौटाता है

#### एपीआई गेटवे एकीकरण

गेटवे मानक अनुरोध/प्रतिक्रिया पैटर्न के माध्यम से पंक्ति एम्बेडिंग प्रश्नों को उजागर करता है:

| घटक | स्थान |
|-----------|----------|
| डिस्पैचर | `trustgraph-flow/trustgraph/gateway/dispatch/row_embeddings_query.py` |
| पंजीकरण | `"row-embeddings"` को `request_response_dispatchers` में `manager.py` में जोड़ें |

फ्लो इंटरफ़ेस नाम: `row-embeddings`

फ्लो ब्लूप्रिंट में इंटरफ़ेस परिभाषा:
```json
{
  "interfaces": {
    "row-embeddings": {
      "request": "non-persistent://tg/request/row-embeddings:{id}",
      "response": "non-persistent://tg/response/row-embeddings:{id}"
    }
  }
}
```

#### पायथन एसडीके समर्थन

एसडीके पंक्ति एम्बेडिंग प्रश्नों के लिए विधियाँ प्रदान करता है:

```python
# Flow-scoped query (preferred)
api = Api(url)
flow = api.flow().id("default")

# Query with text (SDK computes embeddings)
matches = flow.row_embeddings_query(
    text="Chestnut Street",
    collection="my_collection",
    schema_name="addresses",
    index_name="street_name",  # Optional filter
    limit=10
)

# Query with pre-computed vectors
matches = flow.row_embeddings_query(
    vectors=[[0.1, 0.2, ...]],
    collection="my_collection",
    schema_name="addresses"
)

# Each match contains:
for match in matches:
    print(match.index_name)   # e.g., "street_name"
    print(match.index_value)  # e.g., ["CHESTNUT ST"]
    print(match.text)         # e.g., "CHESTNUT ST"
    print(match.score)        # e.g., 0.95
```

#### कमांड लाइन यूटिलिटी

कमांड: `tg-invoke-row-embeddings`

```bash
# Query by text (computes embedding automatically)
tg-invoke-row-embeddings \
  --text "Chestnut Street" \
  --collection my_collection \
  --schema addresses \
  --index street_name \
  --limit 10

# Query by vector file
tg-invoke-row-embeddings \
  --vectors vectors.json \
  --collection my_collection \
  --schema addresses

# Output formats
tg-invoke-row-embeddings --text "..." --format json
tg-invoke-row-embeddings --text "..." --format table
```

#### विशिष्ट उपयोग पैटर्न

पंक्ति एम्बेडिंग क्वेरी का उपयोग आमतौर पर एक अस्पष्ट-से-सटीक लुकअप प्रवाह के हिस्से के रूप में किया जाता है:

```python
# Step 1: Fuzzy search via embeddings
matches = flow.row_embeddings_query(
    text="chestnut street",
    collection="geo",
    schema_name="streets"
)

# Step 2: Exact lookup via GraphQL for full row data
for match in matches:
    query = f'''
    query {{
        streets(where: {{ {match.index_name}: {{ eq: "{match.index_value[0]}" }} }}) {{
            street_name
            city
            zip_code
        }}
    }}
    '''
    rows = flow.rows_query(query, collection="geo")
```

यह दो-चरणीय पैटर्न निम्नलिखित को सक्षम करता है:
जब उपयोगकर्ता "Chestnut Street" खोजता है तो "CHESTNUT ST" खोजना।
सभी फ़ील्ड के साथ पूरी पंक्ति डेटा प्राप्त करना।
संरचित डेटा एक्सेस के साथ सिमेंटिक समानता को जोड़ना।

### पंक्ति डेटा का अंतर्ग्रहण

बाद के चरण में स्थगित। अन्य अंतर्ग्रहण परिवर्तनों के साथ मिलकर डिज़ाइन किया जाएगा।

## कार्यान्वयन प्रभाव

### वर्तमान स्थिति विश्लेषण

मौजूदा कार्यान्वयन में दो मुख्य घटक हैं:

| घटक | स्थान | लाइनें | विवरण |
|-----------|----------|-------|-------------|
| क्वेरी सेवा | `trustgraph-flow/trustgraph/query/objects/cassandra/service.py` | ~740 | एकरूप: GraphQL स्कीमा पीढ़ी, फ़िल्टर पार्सिंग, कैसेंड्रा क्वेरी, अनुरोध हैंडलिंग |
| लेखक | `trustgraph-flow/trustgraph/storage/objects/cassandra/write.py` | ~540 | प्रति-स्कीमा तालिका निर्माण, द्वितीयक अनुक्रमणिका, सम्मिलित/हटाना |

**वर्तमान क्वेरी पैटर्न:**
```sql
SELECT * FROM {keyspace}.o_{schema_name}
WHERE collection = 'X' AND email = 'foo@bar.com'
ALLOW FILTERING
```

**नई क्वेरी पैटर्न:**
```sql
SELECT * FROM {keyspace}.rows
WHERE collection = 'X' AND schema_name = 'customers'
  AND index_name = 'email' AND index_value = ['foo@bar.com']
```

### मुख्य परिवर्तन

1. **क्वेरी सिमेंटिक्स को सरल बनाया गया**: नया स्कीमा केवल `index_value` पर सटीक मिलान का समर्थन करता है। वर्तमान GraphQL फ़िल्टर (`gt`, `lt`, `contains`, आदि) या तो:
   लौटाए गए डेटा पर पोस्ट-फ़िल्टरिंग बन जाते हैं (यदि अभी भी आवश्यक हैं)
   अस्पष्ट मिलान के लिए एम्बेडिंग एपीआई का उपयोग करने के पक्ष में हटा दिए जाते हैं

2. **GraphQL कोड दृढ़ता से युग्मित है**: वर्तमान `service.py` स्ट्रॉबेरी टाइप जनरेशन, फ़िल्टर पार्सिंग और कैसेंड्रा-विशिष्ट प्रश्नों को बंडल करता है। एक और रो स्टोर बैकएंड जोड़ने से ~400 लाइनों का GraphQL कोड दोहराया जाएगा।

### प्रस्तावित रिफैक्टर

रिफैक्टर में दो भाग हैं:

#### 1. GraphQL कोड को अलग करें

पुन: प्रयोज्य GraphQL घटकों को एक साझा मॉड्यूल में निकालें:

```
trustgraph-flow/trustgraph/query/graphql/
├── __init__.py
├── types.py        # Filter types (IntFilter, StringFilter, FloatFilter)
├── schema.py       # Dynamic schema generation from RowSchema
└── filters.py      # Filter parsing utilities
```

यह निम्नलिखित कार्य करता है:
विभिन्न रो स्टोर बैकएंड में पुन: उपयोग
चिंताओं का स्पष्ट अलगाव
GraphQL लॉजिक का स्वतंत्र रूप से परीक्षण करना आसान

#### 2. नई टेबल स्कीमा को लागू करें

कैसेंड्रा-विशिष्ट कोड को एकीकृत टेबल का उपयोग करने के लिए रिफैक्टर करें:

**राइटर** (`trustgraph-flow/trustgraph/storage/rows/cassandra/`):
प्रति-स्कीमा टेबल के बजाय एक एकल `rows` टेबल
प्रति पंक्ति N प्रतियां लिखें (प्रत्येक इंडेक्स के लिए एक)
`row_partitions` टेबल में पंजीकरण करें
सरल टेबल निर्माण (एक बार सेटअप)

**क्वेरी सर्विस** (`trustgraph-flow/trustgraph/query/rows/cassandra/`):
एकीकृत `rows` टेबल को क्वेरी करें
स्कीमा पीढ़ी के लिए निकाले गए GraphQL मॉड्यूल का उपयोग करें
सरलीकृत फ़िल्टर हैंडलिंग (केवल DB स्तर पर सटीक मिलान)

### मॉड्यूल का नाम बदलना

"ऑब्जेक्ट" से "रो" नामकरण को साफ करने के हिस्से के रूप में:

| वर्तमान | नया |
|---------|-----|
| `storage/objects/cassandra/` | `storage/rows/cassandra/` |
| `query/objects/cassandra/` | `query/rows/cassandra/` |
| `embeddings/object_embeddings/` | `embeddings/row_embeddings/` |

### नए मॉड्यूल

| मॉड्यूल | उद्देश्य |
|--------|---------|
| `trustgraph-flow/trustgraph/query/graphql/` | साझा GraphQL उपयोगिताएँ |
| `trustgraph-flow/trustgraph/query/row_embeddings/qdrant/` | रो एम्बेडिंग क्वेरी एपीआई |
| `trustgraph-flow/trustgraph/embeddings/row_embeddings/` | रो एम्बेडिंग गणना (स्टेज 1) |
| `trustgraph-flow/trustgraph/storage/row_embeddings/qdrant/` | रो एम्बेडिंग भंडारण (स्टेज 2) |

## संदर्भ

[स्ट्रक्चर्ड डेटा तकनीकी विनिर्देश](structured-data.md)
