---
layout: default
title: "तकनीकी विनिर्देश: कैसेंड्रा नॉलेज बेस प्रदर्शन पुनर्निर्माण"
parent: "Hindi (Beta)"
---

# तकनीकी विनिर्देश: कैसेंड्रा नॉलेज बेस प्रदर्शन पुनर्निर्माण

> **Beta Translation:** This document was translated via Machine Learning and as such may not be 100% accurate. All non-English languages are currently classified as Beta.

**स्थिति:** मसौदा
**लेखक:** सहायक
**तिथि:** 2025-09-18

## अवलोकन

यह विनिर्देश ट्रस्टग्राफ कैसेंड्रा नॉलेज बेस कार्यान्वयन में प्रदर्शन संबंधी मुद्दों को संबोधित करता है और आरडीएफ ट्रिपल भंडारण और क्वेरी के लिए अनुकूलन प्रस्तावित करता है।

## वर्तमान कार्यान्वयन

### स्कीमा डिज़ाइन

वर्तमान कार्यान्वयन `trustgraph-flow/trustgraph/direct/cassandra_kg.py` में एक एकल तालिका डिज़ाइन का उपयोग करता है:

```sql
CREATE TABLE triples (
    collection text,
    s text,
    p text,
    o text,
    PRIMARY KEY (collection, s, p, o)
);
```

**माध्यमिक अनुक्रमणिकाएँ:**
`triples_s` ON `s` (विषय)
`triples_p` ON `p` (क्रिया)
`triples_o` ON `o` (वस्तु)

### क्वेरी पैटर्न

वर्तमान कार्यान्वयन 8 अलग-अलग क्वेरी पैटर्न का समर्थन करता है:

1. **get_all(संग्रह, सीमा=50)** - एक संग्रह के लिए सभी त्रिगुट प्राप्त करें
   ```sql
   SELECT s, p, o FROM triples WHERE collection = ? LIMIT 50
   ```

2. **get_s(संग्रह, s, सीमा=10)** - विषय द्वारा खोज।
   ```sql
   SELECT p, o FROM triples WHERE collection = ? AND s = ? LIMIT 10
   ```

3. **get_p(संग्रह, p, सीमा=10)** - विधेय द्वारा खोज
   ```sql
   SELECT s, o FROM triples WHERE collection = ? AND p = ? LIMIT 10
   ```

4. **get_o(संग्रह, o, सीमा=10)** - ऑब्जेक्ट द्वारा क्वेरी करें।
   ```sql
   SELECT s, p FROM triples WHERE collection = ? AND o = ? LIMIT 10
   ```

5. **get_sp(संग्रह, s, p, सीमा=10)** - विषय + विधेय द्वारा खोज।
   ```sql
   SELECT o FROM triples WHERE collection = ? AND s = ? AND p = ? LIMIT 10
   ```

6. **get_po(collection, p, o, limit=10)** - पूर्व निर्धारित शर्तों और वस्तुओं के आधार पर खोज ⚠️
   ```sql
   SELECT s FROM triples WHERE collection = ? AND p = ? AND o = ? LIMIT 10 ALLOW FILTERING
   ```

7. **get_os(संग्रह, o, s, सीमा=10)** - ऑब्जेक्ट + विषय द्वारा क्वेरी ⚠️
   ```sql
   SELECT p FROM triples WHERE collection = ? AND o = ? AND s = ? LIMIT 10 ALLOW FILTERING
   ```

8. **get_spo(संग्रह, s, p, o, सीमा=10)** - सटीक त्रिगुट मिलान
   ```sql
   SELECT s as x FROM triples WHERE collection = ? AND s = ? AND p = ? AND o = ? LIMIT 10
   ```

### वर्तमान आर्किटेक्चर

**फ़ाइल: `trustgraph-flow/trustgraph/direct/cassandra_kg.py`**
सभी कार्यों को संभालने वाली एकल `KnowledgeGraph` क्लास
वैश्विक `_active_clusters` सूची के माध्यम से कनेक्शन पूलिंग
निश्चित टेबल नाम: `"triples"`
प्रति उपयोगकर्ता मॉडल के लिए कीस्पेस
फैक्टर 1 के साथ सिंपलस्ट्रैटेजी प्रतिकृति

**एकीकरण बिंदु:**
**राइट पाथ:** `trustgraph-flow/trustgraph/storage/triples/cassandra/write.py`
**क्वेरी पाथ:** `trustgraph-flow/trustgraph/query/triples/cassandra/service.py`
**नॉलेज स्टोर:** `trustgraph-flow/trustgraph/tables/knowledge.py`

## पहचाने गए प्रदर्शन संबंधी मुद्दे

### स्कीमा-स्तरीय मुद्दे

1. **अकुशल प्राइमरी की डिज़ाइन**
   वर्तमान: `PRIMARY KEY (collection, s, p, o)`
   सामान्य एक्सेस पैटर्न के लिए खराब क्लस्टरिंग का कारण बनता है
   महंगे सेकेंडरी इंडेक्स के उपयोग को मजबूर करता है

2. **सेकेंडरी इंडेक्स का अत्यधिक उपयोग** ⚠️
   उच्च कार्डिनलिटी कॉलम (s, p, o) पर तीन सेकेंडरी इंडेक्स
   कैसेंड्रा में सेकेंडरी इंडेक्स महंगे होते हैं और अच्छी तरह से स्केल नहीं होते हैं
   क्वेरी 6 और 7 को `ALLOW FILTERING` की आवश्यकता होती है, जो खराब डेटा मॉडलिंग का संकेत देती है

3. **हॉट पार्टिशन का जोखिम**
   एकल पार्टीशन कुंजी `collection` हॉट पार्टिशन बना सकती है
   बड़े संग्रह एकल नोड्स पर केंद्रित होंगे
   लोड बैलेंसिंग के लिए कोई वितरण रणनीति नहीं

### क्वेरी-स्तरीय मुद्दे

1. **ALLOW FILTERING का उपयोग** ⚠️
   दो क्वेरी प्रकार (get_po, get_os) को `ALLOW FILTERING` की आवश्यकता होती है
   ये क्वेरी कई पार्टिशन को स्कैन करती हैं और बेहद महंगी हैं
   डेटा के आकार के साथ प्रदर्शन रैखिक रूप से खराब होता है

2. **अकुशल एक्सेस पैटर्न**
   सामान्य आरडीएफ क्वेरी पैटर्न के लिए कोई अनुकूलन नहीं
   बार-बार उपयोग किए जाने वाले क्वेरी संयोजनों के लिए कोई कंपाउंड इंडेक्स नहीं
   ग्राफ ट्रैवर्सल पैटर्न पर कोई विचार नहीं

3. **क्वेरी अनुकूलन की कमी**
   कोई तैयार स्टेटमेंट कैशिंग नहीं
   कोई क्वेरी संकेत या अनुकूलन रणनीतियाँ नहीं
   साधारण LIMIT से परे पेजिंग पर कोई विचार नहीं

## समस्या विवरण

वर्तमान कैसेंड्रा नॉलेज बेस कार्यान्वयन में दो महत्वपूर्ण प्रदर्शन संबंधी बाधाएं हैं:

### 1. अकुशल get_po क्वेरी प्रदर्शन

`get_po(collection, p, o)` क्वेरी `ALLOW FILTERING` की आवश्यकता के कारण बेहद अकुशल है:

```sql
SELECT s FROM triples WHERE collection = ? AND p = ? AND o = ? LIMIT 10 ALLOW FILTERING
```

**यह समस्याग्रस्त क्यों है:**
`ALLOW FILTERING` कैसेंड्रा को संग्रह के भीतर सभी विभाजन को स्कैन करने के लिए मजबूर करता है।
डेटा के आकार के साथ प्रदर्शन रैखिक रूप से घटता है।
यह एक सामान्य आरडीएफ क्वेरी पैटर्न है (उन विषयों को खोजना जिनके पास एक विशिष्ट विधेय-वस्तु संबंध है)।
जैसे-जैसे डेटा बढ़ता है, यह क्लस्टर पर महत्वपूर्ण भार डालता है।

### 2. खराब क्लस्टरिंग रणनीति

वर्तमान प्राथमिक कुंजी `PRIMARY KEY (collection, s, p, o)` न्यूनतम क्लस्टरिंग लाभ प्रदान करती है:

**वर्तमान क्लस्टरिंग के साथ समस्याएं:**
विभाजन कुंजी के रूप में `collection` डेटा को प्रभावी ढंग से वितरित नहीं करता है।
अधिकांश संग्रहों में विविध डेटा होता है, जिससे क्लस्टरिंग अप्रभावी हो जाती है।
आरडीएफ प्रश्नों में सामान्य एक्सेस पैटर्न पर कोई विचार नहीं किया गया है।
बड़े संग्रह एकल नोड्स पर "हॉट" विभाजन बनाते हैं।
क्लस्टरिंग कॉलम (s, p, o) विशिष्ट ग्राफ ट्रैवर्सल पैटर्न के लिए अनुकूलित नहीं हैं।

**प्रभाव:**
क्वेरी डेटा स्थानीयता से लाभान्वित नहीं होती हैं।
खराब कैश उपयोग।
क्लस्टर नोड्स में असमान लोड वितरण।
जैसे-जैसे संग्रह बढ़ते हैं, स्केलेबिलिटी बाधाएं।

## प्रस्तावित समाधान: 4-टेबल डीनॉर्मलाइज़ेशन रणनीति

### अवलोकन

एकल `triples` तालिका को चार उद्देश्य-निर्मित तालिकाओं से बदलें, प्रत्येक विशिष्ट क्वेरी पैटर्न के लिए अनुकूलित है। यह द्वितीयक अनुक्रमणिकाओं और ALLOW FILTERING की आवश्यकता को समाप्त करता है, जबकि सभी प्रकार की क्वेरी के लिए इष्टतम प्रदर्शन प्रदान करता है। चौथी तालिका समग्र विभाजन कुंजियों के बावजूद कुशल संग्रह हटाने को सक्षम बनाती है।

### नया स्कीमा डिज़ाइन

**टेबल 1: विषय-केंद्रित क्वेरी (triples_s)**
```sql
CREATE TABLE triples_s (
    collection text,
    s text,
    p text,
    o text,
    PRIMARY KEY ((collection, s), p, o)
);
```
**अनुकूलन:** get_s, get_sp, get_os
**विभाजन कुंजी:** (संग्रह, s) - केवल संग्रह की तुलना में बेहतर वितरण
**समूहीकरण:** (p, o) - विषय के लिए कुशल विधेय/वस्तु लुकअप को सक्षम करता है

**तालिका 2: विधेय-वस्तु प्रश्न (triples_p)**
```sql
CREATE TABLE triples_p (
    collection text,
    p text,
    o text,
    s text,
    PRIMARY KEY ((collection, p), o, s)
);
```
**अनुकूलन:** get_p, get_po (ALLOW FILTERING को हटाता है!)
**पार्टिशन कुंजी:** (संग्रह, p) - विधेय द्वारा प्रत्यक्ष पहुंच
**क्लस्टरिंग:** (o, s) - कुशल ऑब्जेक्ट-विषय ट्रैवर्सल

**तालिका 3: ऑब्जेक्ट-केंद्रित प्रश्न (triples_o)**
```sql
CREATE TABLE triples_o (
    collection text,
    o text,
    s text,
    p text,
    PRIMARY KEY ((collection, o), s, p)
);
```
**अनुकूलन:** get_o
**विभाजन कुंजी:** (संग्रह, o) - वस्तु द्वारा प्रत्यक्ष पहुंच
**समूहीकरण:** (s, p) - कुशल विषय-क्रियापद ट्रैवर्सल

**तालिका 4: संग्रह प्रबंधन और एस.पी.ओ. प्रश्न (triples_collection)**
```sql
CREATE TABLE triples_collection (
    collection text,
    s text,
    p text,
    o text,
    PRIMARY KEY (collection, s, p, o)
);
```
**अनुकूलन:** get_spo, delete_collection
**विभाजन कुंजी:** केवल संग्रह - कुशल संग्रह-स्तरीय संचालन को सक्षम करता है
**समूहीकरण:** (s, p, o) - मानक त्रिगुट क्रम
**उद्देश्य:** सटीक SPO लुकअप के लिए दोहरे उपयोग और एक हटाने अनुक्रमणिका के रूप में

### क्वेरी मैपिंग

| मूल क्वेरी | लक्ष्य तालिका | प्रदर्शन सुधार |
|----------------|-------------|------------------------|
| get_all(संग्रह) | triples_s | ALLOW FILTERING (स्कैन के लिए स्वीकार्य) |
| get_s(संग्रह, s) | triples_s | प्रत्यक्ष विभाजन पहुंच |
| get_p(संग्रह, p) | triples_p | प्रत्यक्ष विभाजन पहुंच |
| get_o(संग्रह, o) | triples_o | प्रत्यक्ष विभाजन पहुंच |
| get_sp(संग्रह, s, p) | triples_s | विभाजन + समूहीकरण |
| get_po(संग्रह, p, o) | triples_p | **अब ALLOW FILTERING नहीं!** |
| get_os(संग्रह, o, s) | triples_o | विभाजन + समूहीकरण |
| get_spo(संग्रह, s, p, o) | triples_collection | सटीक कुंजी लुकअप |
| delete_collection(संग्रह) | triples_collection | अनुक्रमणिका पढ़ें, सभी को बैच में हटाएं |

### संग्रह हटाने की रणनीति

संयुक्त विभाजन कुंजियों के साथ, हम सीधे `DELETE FROM table WHERE collection = ?` निष्पादित नहीं कर सकते। इसके बजाय:

1. **पढ़ने का चरण:** सभी त्रिगुटों को सूचीबद्ध करने के लिए `triples_collection` क्वेरी करें:
   ```sql
   SELECT s, p, o FROM triples_collection WHERE collection = ?
   ```
   यह कुशल है क्योंकि `collection` इस तालिका के लिए विभाजन कुंजी है।

2. **हटाने का चरण:** प्रत्येक ट्रिपल (s, p, o) के लिए, सभी 4 तालिकाओं से पूर्ण विभाजन कुंजियों का उपयोग करके हटाएं:
   ```sql
   DELETE FROM triples_s WHERE collection = ? AND s = ? AND p = ? AND o = ?
   DELETE FROM triples_p WHERE collection = ? AND p = ? AND o = ? AND s = ?
   DELETE FROM triples_o WHERE collection = ? AND o = ? AND s = ? AND p = ?
   DELETE FROM triples_collection WHERE collection = ? AND s = ? AND p = ? AND o = ?
   ```
   दक्षता के लिए 100 के समूहों में समूहीकृत किया गया।

**ट्रेड-ऑफ विश्लेषण:**
✅ वितरित विभाजनों के साथ इष्टतम क्वेरी प्रदर्शन बनाए रखता है।
✅ बड़े संग्रहों के लिए कोई "हॉट" विभाजन नहीं।
❌ अधिक जटिल हटाने का तर्क (पढ़ें-फिर-हटाएं)।
❌ हटाने का समय संग्रह के आकार के समानुपाती होता है।

### लाभ

1. **ALLOW FILTERING को समाप्त करता है** - प्रत्येक क्वेरी में एक इष्टतम एक्सेस पथ होता है (सिवाय get_all स्कैन के)।
2. **कोई द्वितीयक इंडेक्स नहीं** - प्रत्येक तालिका अपने क्वेरी पैटर्न के लिए इंडेक्स है।
3. **बेहतर डेटा वितरण** - समग्र विभाजन कुंजियाँ प्रभावी रूप से लोड फैलाती हैं।
4. **अनुमानित प्रदर्शन** - क्वेरी समय परिणाम के आकार के समानुपाती होता है, कुल डेटा के नहीं।
5. **कैसेंड्रा की ताकत का लाभ उठाता है** - कैसेंड्रा के आर्किटेक्चर के लिए डिज़ाइन किया गया।
6. **संग्रह हटाने को सक्षम बनाता है** - triples_collection हटाने के इंडेक्स के रूप में कार्य करता है।

## कार्यान्वयन योजना

### उन फ़ाइलों की आवश्यकता है जिनमें परिवर्तन आवश्यक हैं

#### प्राथमिक कार्यान्वयन फ़ाइल

**`trustgraph-flow/trustgraph/direct/cassandra_kg.py`** - पूर्ण पुनर्लेखन आवश्यक है।

**वर्तमान विधियाँ जिन्हें रिफैक्टर करने की आवश्यकता है:**
```python
# Schema initialization
def init(self) -> None  # Replace single table with three tables

# Insert operations
def insert(self, collection, s, p, o) -> None  # Write to all three tables

# Query operations (API unchanged, implementation optimized)
def get_all(self, collection, limit=50)      # Use triples_by_subject
def get_s(self, collection, s, limit=10)     # Use triples_by_subject
def get_p(self, collection, p, limit=10)     # Use triples_by_po
def get_o(self, collection, o, limit=10)     # Use triples_by_object
def get_sp(self, collection, s, p, limit=10) # Use triples_by_subject
def get_po(self, collection, p, o, limit=10) # Use triples_by_po (NO ALLOW FILTERING!)
def get_os(self, collection, o, s, limit=10) # Use triples_by_subject
def get_spo(self, collection, s, p, o, limit=10) # Use triples_by_subject

# Collection management
def delete_collection(self, collection) -> None  # Delete from all three tables
```

#### एकीकरण फ़ाइलें (कोई लॉजिक परिवर्तन आवश्यक नहीं)

**`trustgraph-flow/trustgraph/storage/triples/cassandra/write.py`**
कोई बदलाव आवश्यक नहीं - मौजूदा नॉलेज ग्राफ एपीआई का उपयोग करता है
प्रदर्शन में स्वचालित सुधार से लाभ

**`trustgraph-flow/trustgraph/query/triples/cassandra/service.py`**
कोई बदलाव आवश्यक नहीं - मौजूदा नॉलेज ग्राफ एपीआई का उपयोग करता है
प्रदर्शन में स्वचालित सुधार से लाभ

### अपडेट की आवश्यकता वाली परीक्षण फ़ाइलें

#### यूनिट टेस्ट
**`tests/unit/test_storage/test_triples_cassandra_storage.py`**
स्कीमा परिवर्तनों के लिए परीक्षण अपेक्षाओं को अपडेट करें
मल्टी-टेबल स्थिरता के लिए परीक्षण जोड़ें
क्वेरी योजनाओं में कोई ALLOW FILTERING न होने की पुष्टि करें

**`tests/unit/test_query/test_triples_cassandra_query.py`**
प्रदर्शन दावों को अपडेट करें
नए तालिकाओं के खिलाफ सभी 8 क्वेरी पैटर्न का परीक्षण करें
सही तालिकाओं में क्वेरी रूटिंग की पुष्टि करें

#### एकीकरण परीक्षण
**`tests/integration/test_cassandra_integration.py`**
नए स्कीमा के साथ एंड-टू-एंड परीक्षण
प्रदर्शन बेंचमार्किंग तुलना
तालिकाओं में डेटा स्थिरता सत्यापन

**`tests/unit/test_storage/test_cassandra_config_integration.py`**
स्कीमा सत्यापन परीक्षणों को अपडेट करें
माइग्रेशन परिदृश्यों का परीक्षण करें

### कार्यान्वयन रणनीति

#### चरण 1: स्कीमा और कोर विधियाँ
1. **`init()` विधि को फिर से लिखें** - एक के बजाय चार तालिकाओं का निर्माण करें
2. **`insert()` विधि को फिर से लिखें** - सभी चार तालिकाओं में बैच राइट्स
3. **तैयार कथनों को लागू करें** - इष्टतम प्रदर्शन के लिए
4. **टेबल रूटिंग लॉजिक जोड़ें** - प्रश्नों को इष्टतम तालिकाओं पर निर्देशित करें
5. **संग्रह हटाने को लागू करें** - triples_collection से पढ़ें, सभी तालिकाओं से बैच हटाएं

#### चरण 2: क्वेरी विधि अनुकूलन
1. **प्रत्येक get_* विधि को फिर से लिखें** ताकि इष्टतम तालिका का उपयोग किया जा सके
2. **सभी ALLOW FILTERING उपयोग को हटा दें**
3. **कुशल क्लस्टरिंग कुंजी उपयोग को लागू करें**
4. **क्वेरी प्रदर्शन लॉगिंग जोड़ें**

#### चरण 3: संग्रह प्रबंधन
1. **`delete_collection()` को अपडेट करें** - सभी तीन तालिकाओं से हटाएं
2. **संगति सत्यापन जोड़ें** - सुनिश्चित करें कि सभी तालिकाओं को सिंक में रखा जाए
3. **बैच ऑपरेशंस लागू करें** - परमाणु मल्टी-टेबल ऑपरेशंस के लिए

### प्रमुख कार्यान्वयन विवरण

#### बैच राइट रणनीति
```python
def insert(self, collection, s, p, o):
    batch = BatchStatement()

    # Insert into all four tables
    batch.add(self.insert_subject_stmt, (collection, s, p, o))
    batch.add(self.insert_po_stmt, (collection, p, o, s))
    batch.add(self.insert_object_stmt, (collection, o, s, p))
    batch.add(self.insert_collection_stmt, (collection, s, p, o))

    self.session.execute(batch)
```

#### प्रश्न रूटिंग लॉजिक (Query Routing Logic)
```python
def get_po(self, collection, p, o, limit=10):
    # Route to triples_p table - NO ALLOW FILTERING!
    return self.session.execute(
        self.get_po_stmt,
        (collection, p, o, limit)
    )

def get_spo(self, collection, s, p, o, limit=10):
    # Route to triples_collection table for exact SPO lookup
    return self.session.execute(
        self.get_spo_stmt,
        (collection, s, p, o, limit)
    )
```

#### संग्रह हटाने का तर्क
```python
def delete_collection(self, collection):
    # Step 1: Read all triples from collection table
    rows = self.session.execute(
        f"SELECT s, p, o FROM {self.collection_table} WHERE collection = %s",
        (collection,)
    )

    # Step 2: Batch delete from all 4 tables
    batch = BatchStatement()
    count = 0

    for row in rows:
        s, p, o = row.s, row.p, row.o

        # Delete using full partition keys for each table
        batch.add(SimpleStatement(
            f"DELETE FROM {self.subject_table} WHERE collection = ? AND s = ? AND p = ? AND o = ?"
        ), (collection, s, p, o))

        batch.add(SimpleStatement(
            f"DELETE FROM {self.po_table} WHERE collection = ? AND p = ? AND o = ? AND s = ?"
        ), (collection, p, o, s))

        batch.add(SimpleStatement(
            f"DELETE FROM {self.object_table} WHERE collection = ? AND o = ? AND s = ? AND p = ?"
        ), (collection, o, s, p))

        batch.add(SimpleStatement(
            f"DELETE FROM {self.collection_table} WHERE collection = ? AND s = ? AND p = ? AND o = ?"
        ), (collection, s, p, o))

        count += 1

        # Execute every 100 triples to avoid oversized batches
        if count % 100 == 0:
            self.session.execute(batch)
            batch = BatchStatement()

    # Execute remaining deletions
    if count % 100 != 0:
        self.session.execute(batch)

    logger.info(f"Deleted {count} triples from collection {collection}")
```

#### तैयार स्टेटमेंट अनुकूलन (तैयार कथन अनुकूलन)
```python
def prepare_statements(self):
    # Cache prepared statements for better performance
    self.insert_subject_stmt = self.session.prepare(
        f"INSERT INTO {self.subject_table} (collection, s, p, o) VALUES (?, ?, ?, ?)"
    )
    self.insert_po_stmt = self.session.prepare(
        f"INSERT INTO {self.po_table} (collection, p, o, s) VALUES (?, ?, ?, ?)"
    )
    self.insert_object_stmt = self.session.prepare(
        f"INSERT INTO {self.object_table} (collection, o, s, p) VALUES (?, ?, ?, ?)"
    )
    self.insert_collection_stmt = self.session.prepare(
        f"INSERT INTO {self.collection_table} (collection, s, p, o) VALUES (?, ?, ?, ?)"
    )
    # ... query statements
```

## माइग्रेशन रणनीति

### डेटा माइग्रेशन दृष्टिकोण

#### विकल्प 1: ब्लू-ग्रीन परिनियोजन (अनुशंसित)
1. **नए स्कीमा को मौजूदा स्कीमा के साथ तैनात करें** - अस्थायी रूप से अलग-अलग टेबल नामों का उपयोग करें
2. **डबल-राइट अवधि** - संक्रमण के दौरान पुराने और नए दोनों स्कीमा में लिखें
3. **बैकग्राउंड माइग्रेशन** - मौजूदा डेटा को नई तालिकाओं में कॉपी करें
4. **रीड स्विच करें** - डेटा माइग्रेट होने के बाद प्रश्नों को नई तालिकाओं पर रूट करें
5. **पुराने तालिकाओं को हटाएं** - सत्यापन अवधि के बाद

#### विकल्प 2: इन-प्लेस माइग्रेशन
1. **स्कीमा जोड़ना** - मौजूदा कीस्पेस में नई तालिकाएँ बनाएँ
2. **डेटा माइग्रेशन स्क्रिप्ट** - बैच कॉपी पुराने टेबल से नई तालिकाओं में
3. **एप्लिकेशन अपडेट** - माइग्रेशन पूरा होने के बाद नया कोड तैनात करें
4. **पुरानी टेबल की सफाई** - पुरानी टेबल और इंडेक्स हटाएं

### पश्चगामी अनुकूलता

#### परिनियोजन रणनीति
```python
# Environment variable to control table usage during migration
USE_LEGACY_TABLES = os.getenv('CASSANDRA_USE_LEGACY', 'false').lower() == 'true'

class KnowledgeGraph:
    def __init__(self, ...):
        if USE_LEGACY_TABLES:
            self.init_legacy_schema()
        else:
            self.init_optimized_schema()
```

#### माइग्रेशन स्क्रिप्ट
```python
def migrate_data():
    # Read from old table
    old_triples = session.execute("SELECT collection, s, p, o FROM triples")

    # Batch write to new tables
    for batch in batched(old_triples, 100):
        batch_stmt = BatchStatement()
        for row in batch:
            # Add to all three new tables
            batch_stmt.add(insert_subject_stmt, row)
            batch_stmt.add(insert_po_stmt, (row.collection, row.p, row.o, row.s))
            batch_stmt.add(insert_object_stmt, (row.collection, row.o, row.s, row.p))
        session.execute(batch_stmt)
```

### सत्यापन रणनीति

#### डेटा संगति जांच
```python
def validate_migration():
    # Count total records in old vs new tables
    old_count = session.execute("SELECT COUNT(*) FROM triples WHERE collection = ?", (collection,))
    new_count = session.execute("SELECT COUNT(*) FROM triples_by_subject WHERE collection = ?", (collection,))

    assert old_count == new_count, f"Record count mismatch: {old_count} vs {new_count}"

    # Spot check random samples
    sample_queries = generate_test_queries()
    for query in sample_queries:
        old_result = execute_legacy_query(query)
        new_result = execute_optimized_query(query)
        assert old_result == new_result, f"Query results differ for {query}"
```

## परीक्षण रणनीति

### प्रदर्शन परीक्षण

#### बेंचमार्क परिदृश्य
1. **क्वेरी प्रदर्शन तुलना**
   सभी 8 क्वेरी प्रकारों के लिए पूर्व/पश्च प्रदर्शन मेट्रिक्स
   `get_po` प्रदर्शन सुधार पर ध्यान केंद्रित करें (ALLOW FILTERING को हटाना)
   विभिन्न डेटा आकारों के तहत क्वेरी विलंबता को मापें

2. **लोड परीक्षण**
   समवर्ती क्वेरी निष्पादन
   बैच ऑपरेशनों के साथ लेखन थ्रूपुट
   मेमोरी और सीपीयू उपयोग

3. **स्केलेबिलिटी परीक्षण**
   बढ़ते संग्रह आकारों के साथ प्रदर्शन
   मल्टी-कलेक्शन क्वेरी वितरण
   क्लस्टर नोड उपयोग

#### परीक्षण डेटा सेट
**छोटा:** प्रति संग्रह 10K त्रिगुण
**मध्यम:** प्रति संग्रह 100K त्रिगुण
**बड़ा:** 1M+ त्रिगुण
**एकाधिक संग्रह:** परीक्षण विभाजन वितरण

### कार्यात्मक परीक्षण

#### यूनिट टेस्ट अपडेट
```python
# Example test structure for new implementation
class TestCassandraKGPerformance:
    def test_get_po_no_allow_filtering(self):
        # Verify get_po queries don't use ALLOW FILTERING
        with patch('cassandra.cluster.Session.execute') as mock_execute:
            kg.get_po('test_collection', 'predicate', 'object')
            executed_query = mock_execute.call_args[0][0]
            assert 'ALLOW FILTERING' not in executed_query

    def test_multi_table_consistency(self):
        # Verify all tables stay in sync
        kg.insert('test', 's1', 'p1', 'o1')

        # Check all tables contain the triple
        assert_triple_exists('triples_by_subject', 'test', 's1', 'p1', 'o1')
        assert_triple_exists('triples_by_po', 'test', 'p1', 'o1', 's1')
        assert_triple_exists('triples_by_object', 'test', 'o1', 's1', 'p1')
```

#### एकीकरण परीक्षण अपडेट
```python
class TestCassandraIntegration:
    def test_query_performance_regression(self):
        # Ensure new implementation is faster than old
        old_time = benchmark_legacy_get_po()
        new_time = benchmark_optimized_get_po()
        assert new_time < old_time * 0.5  # At least 50% improvement

    def test_end_to_end_workflow(self):
        # Test complete write -> query -> delete cycle
        # Verify no performance degradation in integration
```

### रोलबैक योजना

#### त्वरित रोलबैक रणनीति
1. **पर्यावरण चर स्विच** - तुरंत पुराने तालिकाओं पर वापस स्विच करें
2. **पुराने तालिकाओं को बनाए रखें** - प्रदर्शन साबित होने तक उन्हें हटाएं नहीं
3. **निगरानी अलर्ट** - त्रुटि दर/विलंबता के आधार पर स्वचालित रोलबैक ट्रिगर

#### रोलबैक सत्यापन
```python
def rollback_to_legacy():
    # Set environment variable
    os.environ['CASSANDRA_USE_LEGACY'] = 'true'

    # Restart services to pick up change
    restart_cassandra_services()

    # Validate functionality
    run_smoke_tests()
```

## जोखिम और विचार

### प्रदर्शन जोखिम
**लेखन विलंबता में वृद्धि** - प्रति सम्मिलित 4x लेखन संचालन (3-तालिका दृष्टिकोण से 33% अधिक)
**भंडारण ओवरहेड** - 4x भंडारण आवश्यकता (3-तालिका दृष्टिकोण से 33% अधिक)
**बैच लेखन विफलताएं** - उचित त्रुटि प्रबंधन की आवश्यकता
**हटाने की जटिलता** - संग्रह हटाने के लिए रीड-देन-डिलीट लूप की आवश्यकता होती है

### परिचालन जोखिम
**स्थानांतरण जटिलता** - बड़े डेटासेट के लिए डेटा स्थानांतरण
**संगति चुनौतियां** - यह सुनिश्चित करना कि सभी तालिकाएं सिंक्रनाइज़ रहें
**निगरानी अंतराल** - मल्टी-टेबल ऑपरेशनों के लिए नए मेट्रिक्स की आवश्यकता

### शमन रणनीतियाँ
1. **धीरे-धीरे रोलआउट** - छोटे संग्रहों से शुरुआत करें
2. **व्यापक निगरानी** - सभी प्रदर्शन मेट्रिक्स को ट्रैक करें
3. **स्वचालित सत्यापन** - निरंतर संगति जांच
4. **त्वरित रोलबैक क्षमता** - पर्यावरण-आधारित तालिका चयन

## सफलता मानदंड

### प्रदर्शन सुधार
[ ] **ALLOW FILTERING को समाप्त करें** - get_po और get_os क्वेरी फ़िल्टरिंग के बिना चलती हैं
[ ] **क्वेरी विलंबता में कमी** - क्वेरी प्रतिक्रिया समय में 50%+ सुधार
[ ] **बेहतर लोड वितरण** - कोई हॉट विभाजन नहीं, क्लस्टर नोड्स में समान लोड
[ ] **स्केलेबल प्रदर्शन** - क्वेरी समय परिणाम आकार के समानुपाती, कुल डेटा के समानुपाती नहीं

### कार्यात्मक आवश्यकताएँ
[ ] **एपीआई संगतता** - सभी मौजूदा कोड अपरिवर्तित रूप से काम करना जारी रखता है
[ ] **डेटा संगति** - तीनों तालिकाओं को सिंक्रनाइज़ रखा जाता है
[ ] **कोई डेटा हानि नहीं** - माइग्रेशन सभी मौजूदा त्रिगुणों को संरक्षित करता है
[ ] **पिछड़ा संगतता** - विरासत स्कीमा पर वापस रोलबैक करने की क्षमता

### परिचालन आवश्यकताएँ
[ ] **सुरक्षित स्थानांतरण** - रोलबैक क्षमता के साथ ब्लू-ग्रीन परिनियोजन
[ ] **निगरानी कवरेज** - मल्टी-टेबल ऑपरेशनों के लिए व्यापक मेट्रिक्स
[ ] **परीक्षण कवरेज** - सभी क्वेरी पैटर्न प्रदर्शन बेंचमार्क के साथ परीक्षण किए गए
[ ] **प्रलेखन** - अद्यतन परिनियोजन और परिचालन प्रक्रियाएं

## समयरेखा

### चरण 1: कार्यान्वयन
[ ] मल्टी-टेबल स्कीमा के साथ `cassandra_kg.py` को फिर से लिखें
[ ] बैच लेखन संचालन लागू करें
[ ] तैयार स्टेटमेंट अनुकूलन जोड़ें
[ ] यूनिट परीक्षण अपडेट करें

### चरण 2: एकीकरण परीक्षण
[ ] एकीकरण परीक्षण अपडेट करें
[ ] प्रदर्शन बेंचमार्किंग
[ ] यथार्थवादी डेटा वॉल्यूम के साथ लोड परीक्षण
[ ] डेटा संगति के लिए सत्यापन स्क्रिप्ट

### चरण 3: माइग्रेशन योजना
[ ] ब्लू-ग्रीन परिनियोजन स्क्रिप्ट
[ ] डेटा माइग्रेशन उपकरण
[ ] निगरानी डैशबोर्ड अपडेट
[ ] रोलबैक प्रक्रियाएं

### चरण 4: उत्पादन परिनियोजन
[ ] उत्पादन में क्रमिक रोलआउट
[ ] प्रदर्शन निगरानी और सत्यापन
[ ] विरासत तालिका सफाई
[ ] प्रलेखन अपडेट

## निष्कर्ष

यह मल्टी-टेबल डीनॉर्मलाइज़ेशन रणनीति दो महत्वपूर्ण प्रदर्शन बाधाओं को सीधे संबोधित करती है:

1. **महंगे ALLOW FILTERING को समाप्त करता है** प्रत्येक क्वेरी पैटर्न के लिए इष्टतम तालिका संरचनाएं प्रदान करके
2. **बेहतर क्लस्टरिंग प्रभावशीलता** समग्र विभाजन कुंजियों के माध्यम से जो लोड को ठीक से वितरित करते हैं

यह दृष्टिकोण कैसेंड्रा की ताकत का लाभ उठाता है जबकि पूर्ण एपीआई संगतता बनाए रखता है, यह सुनिश्चित करता है कि मौजूदा कोड प्रदर्शन सुधारों से स्वचालित रूप से लाभान्वित होता है।
