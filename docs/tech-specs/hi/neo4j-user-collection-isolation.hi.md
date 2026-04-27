---
layout: default
title: "नियो4जे उपयोगकर्ता/संग्रह अलगाव समर्थन"
parent: "Hindi (Beta)"
---

# नियो4जे उपयोगकर्ता/संग्रह अलगाव समर्थन

> **Beta Translation:** This document was translated via Machine Learning and as such may not be 100% accurate. All non-English languages are currently classified as Beta.

## समस्या विवरण

नियो4जे का त्रिगुट भंडारण और क्वेरी कार्यान्वयन वर्तमान में उपयोगकर्ता/संग्रह अलगाव की कमी रखता है, जो एक बहु-किरायेदारी सुरक्षा समस्या पैदा करता है। सभी त्रिगुट एक ही ग्राफ स्पेस में संग्रहीत होते हैं, बिना किसी ऐसी तंत्र के जो उपयोगकर्ताओं को अन्य उपयोगकर्ताओं के डेटा तक पहुंचने या संग्रहों को मिलाने से रोकता हो।

ट्रस्टग्राफ में अन्य स्टोरेज बैकएंड के विपरीत:
**कैसेंड्रा**: प्रत्येक उपयोगकर्ता के लिए अलग-अलग कीस्पेस और प्रत्येक संग्रह के लिए टेबल का उपयोग करता है।
**वेक्टर स्टोर** (मिलवस, क्यूड्रांट, पाइनकोन): संग्रह-विशिष्ट नेमस्पेस का उपयोग करते हैं।
**नियो4जे**: वर्तमान में सभी डेटा को एक ही ग्राफ में साझा करता है (सुरक्षा भेद्यता)।

## वर्तमान आर्किटेक्चर

### डेटा मॉडल
**नोड्स**: `:Node` लेबल के साथ `uri` प्रॉपर्टी, `:Literal` लेबल के साथ `value` प्रॉपर्टी।
**रिलेशनशिप्स**: `:Rel` लेबल के साथ `uri` प्रॉपर्टी।
**इंडेक्स**: `Node.uri`, `Literal.value`, `Rel.uri`।

### संदेश प्रवाह
`Triples` संदेशों में `metadata.user` और `metadata.collection` फ़ील्ड होते हैं।
स्टोरेज सेवा उपयोगकर्ता/संग्रह जानकारी प्राप्त करती है लेकिन इसे अनदेखा करती है।
क्वेरी सेवा `TriplesQueryRequest` में `user` और `collection` की अपेक्षा करती है लेकिन उन्हें अनदेखा करती है।

### वर्तमान सुरक्षा समस्या
```cypher
# Any user can query any data - no isolation
MATCH (src:Node)-[rel:Rel]->(dest:Node) 
RETURN src.uri, rel.uri, dest.uri
```

## प्रस्तावित समाधान: प्रॉपर्टी-आधारित फ़िल्टरिंग (अनुशंसित)

### अवलोकन
सभी नोड्स और संबंधों में `user` और `collection` प्रॉपर्टीज़ जोड़ें, और फिर सभी ऑपरेशन्स को इन प्रॉपर्टीज़ के आधार पर फ़िल्टर करें। यह दृष्टिकोण मजबूत अलगाव प्रदान करता है, जबकि क्वेरी लचीलापन और पिछड़े अनुकूलता को बनाए रखता है।

### डेटा मॉडल परिवर्तन

#### उन्नत नोड संरचना
```cypher
// Node entities
CREATE (n:Node {
  uri: "http://example.com/entity1",
  user: "john_doe", 
  collection: "production_v1"
})

// Literal entities  
CREATE (n:Literal {
  value: "literal value",
  user: "john_doe",
  collection: "production_v1" 
})
```

#### उन्नत संबंध संरचना
```cypher
// Relationships with user/collection properties
CREATE (src)-[:Rel {
  uri: "http://example.com/predicate1",
  user: "john_doe",
  collection: "production_v1"
}]->(dest)
```

#### अद्यतित अनुक्रमणिकाएँ
```cypher
// Compound indexes for efficient filtering
CREATE INDEX node_user_collection_uri FOR (n:Node) ON (n.user, n.collection, n.uri);
CREATE INDEX literal_user_collection_value FOR (n:Literal) ON (n.user, n.collection, n.value);
CREATE INDEX rel_user_collection_uri FOR ()-[r:Rel]-() ON (r.user, r.collection, r.uri);

// Maintain existing indexes for backwards compatibility (optional)
CREATE INDEX Node_uri FOR (n:Node) ON (n.uri);
CREATE INDEX Literal_value FOR (n:Literal) ON (n.value);
CREATE INDEX Rel_uri FOR ()-[r:Rel]-() ON (r.uri);
```

### कार्यान्वयन में परिवर्तन

#### स्टोरेज सर्विस (`write.py`)

**वर्तमान कोड:**
```python
def create_node(self, uri):
    summary = self.io.execute_query(
        "MERGE (n:Node {uri: $uri})",
        uri=uri, database_=self.db,
    ).summary
```

**अद्यतित कोड:**
```python
def create_node(self, uri, user, collection):
    summary = self.io.execute_query(
        "MERGE (n:Node {uri: $uri, user: $user, collection: $collection})",
        uri=uri, user=user, collection=collection, database_=self.db,
    ).summary
```

**बेहतर `store_triples` विधि:**
```python
async def store_triples(self, message):
    user = message.metadata.user
    collection = message.metadata.collection
    
    for t in message.triples:
        self.create_node(t.s.value, user, collection)
        
        if t.o.is_uri:
            self.create_node(t.o.value, user, collection)  
            self.relate_node(t.s.value, t.p.value, t.o.value, user, collection)
        else:
            self.create_literal(t.o.value, user, collection)
            self.relate_literal(t.s.value, t.p.value, t.o.value, user, collection)
```

#### क्वेरी सर्विस (`service.py`)

**वर्तमान कोड:**
```python
records, summary, keys = self.io.execute_query(
    "MATCH (src:Node {uri: $src})-[rel:Rel {uri: $rel}]->(dest:Node) "
    "RETURN dest.uri as dest",
    src=query.s.value, rel=query.p.value, database_=self.db,
)
```

**अद्यतित कोड:**
```python
records, summary, keys = self.io.execute_query(
    "MATCH (src:Node {uri: $src, user: $user, collection: $collection})-"
    "[rel:Rel {uri: $rel, user: $user, collection: $collection}]->"
    "(dest:Node {user: $user, collection: $collection}) "
    "RETURN dest.uri as dest",
    src=query.s.value, rel=query.p.value, 
    user=query.user, collection=query.collection,
    database_=self.db,
)
```

### माइग्रेशन रणनीति

#### चरण 1: नए डेटा में गुण जोड़ें
1. स्टोरेज सर्विस को अपडेट करें ताकि नए त्रिगुणों में उपयोगकर्ता/संग्रह गुण जोड़े जा सकें।
2. पिछली अनुकूलता बनाए रखें, क्योंकि प्रश्नों में गुणों की आवश्यकता नहीं होगी।
3. मौजूदा डेटा सुलभ रहेगा, लेकिन अलग नहीं होगा।

#### चरण 2: मौजूदा डेटा का माइग्रेशन
```cypher
// Migrate existing nodes (requires default user/collection assignment)
MATCH (n:Node) WHERE n.user IS NULL
SET n.user = 'legacy_user', n.collection = 'default_collection';

MATCH (n:Literal) WHERE n.user IS NULL  
SET n.user = 'legacy_user', n.collection = 'default_collection';

MATCH ()-[r:Rel]->() WHERE r.user IS NULL
SET r.user = 'legacy_user', r.collection = 'default_collection';
```

#### चरण 3: अलगाव को लागू करना
1. क्वेरी सेवा को अपडेट करें ताकि उपयोगकर्ता/संग्रह फ़िल्टरिंग की आवश्यकता हो
2. उचित उपयोगकर्ता/संग्रह संदर्भ के बिना क्वेरी को अस्वीकार करने के लिए सत्यापन जोड़ें
3. पुराने डेटा एक्सेस पथ को हटा दें

### सुरक्षा संबंधी विचार

#### क्वेरी सत्यापन
```python
async def query_triples(self, query):
    # Validate user/collection parameters
    if not query.user or not query.collection:
        raise ValueError("User and collection must be specified")
    
    # All queries must include user/collection filters
    # ... rest of implementation
```

#### पैरामीटर इंजेक्शन को रोकना
केवल पैरामीटराइज़्ड क्वेरी का उपयोग करें।
उपयोगकर्ता/संग्रह मूल्यों को स्वीकृत पैटर्न के विरुद्ध मान्य करें।
Neo4j प्रॉपर्टी नाम आवश्यकताओं के लिए सैनिटाइजेशन पर विचार करें।

#### ऑडिट ट्रेल
```python
logger.info(f"Query executed - User: {query.user}, Collection: {query.collection}, "
           f"Pattern: {query.s}/{query.p}/{query.o}")
```

## वैकल्पिक दृष्टिकोणों पर विचार

### विकल्प 2: लेबल-आधारित अलगाव

**दृष्टिकोण**: गतिशील लेबल का उपयोग करें जैसे `User_john_Collection_prod`

**लाभ:**
लेबल फ़िल्टरिंग के माध्यम से मजबूत अलगाव
लेबल इंडेक्स के साथ कुशल क्वेरी प्रदर्शन
स्पष्ट डेटा पृथक्करण

**नुकसान:**
Neo4j में लेबल की संख्या पर व्यावहारिक सीमाएं हैं (~1000)
जटिल लेबल नाम पीढ़ी और सैनिटाइजेशन
जब आवश्यक हो तो संग्रहों में क्वेरी करना मुश्किल होता है

**कार्यान्वयन उदाहरण:**
```cypher
CREATE (n:Node:User_john_Collection_prod {uri: "http://example.com/entity"})
MATCH (n:User_john_Collection_prod) WHERE n:Node RETURN n
```

### विकल्प 3: प्रति-उपयोगकर्ता डेटाबेस

**दृष्टिकोण**: प्रत्येक उपयोगकर्ता या उपयोगकर्ता/संग्रह संयोजन के लिए अलग-अलग Neo4j डेटाबेस बनाएं।

**लाभ:**
पूर्ण डेटा अलगाव
क्रॉस-संदूषण का कोई जोखिम नहीं
प्रति-उपयोगकर्ता स्वतंत्र स्केलिंग

**नुकसान:**
संसाधन ओवरहेड (प्रत्येक डेटाबेस मेमोरी का उपयोग करता है)
जटिल डेटाबेस जीवनचक्र प्रबंधन
Neo4j कम्युनिटी एडिशन डेटाबेस सीमाएं
उपयोगकर्ताओं के बीच विश्लेषण करना मुश्किल

### विकल्प 4: समग्र कुंजी रणनीति

**दृष्टिकोण**: सभी URIs और मानों को उपयोगकर्ता/संग्रह जानकारी के साथ उपसर्ग करें।

**लाभ:**
मौजूदा प्रश्नों के साथ संगत
सरल कार्यान्वयन
कोई स्कीमा परिवर्तन आवश्यक नहीं

**नुकसान:**
URI प्रदूषण डेटा अर्थशास्त्र को प्रभावित करता है
कम कुशल प्रश्न (स्ट्रिंग उपसर्ग मिलान)
RDF/सिमेंटिक वेब मानकों का उल्लंघन

**कार्यान्वयन उदाहरण:**
```python
def make_composite_uri(uri, user, collection):
    return f"usr:{user}:col:{collection}:uri:{uri}"
```

## कार्यान्वयन योजना

### चरण 1: आधार (सप्ताह 1)
1. [ ] स्टोरेज सेवा को उपयोगकर्ता/संग्रह गुणों को स्वीकार करने और संग्रहीत करने के लिए अपडेट करें।
2. [ ] कुशल क्वेरी के लिए कंपाउंड इंडेक्स जोड़ें।
3. [ ] पिछड़े अनुकूलता परत लागू करें।
4. [ ] नई कार्यक्षमता के लिए यूनिट परीक्षण बनाएं।

### चरण 2: क्वेरी अपडेट (सप्ताह 2)
1. [ ] सभी क्वेरी पैटर्न को उपयोगकर्ता/संग्रह फ़िल्टर शामिल करने के लिए अपडेट करें।
2. [ ] क्वेरी सत्यापन और सुरक्षा जांच जोड़ें।
3. [ ] एकीकरण परीक्षण अपडेट करें।
4. [ ] फ़िल्टर किए गए प्रश्नों के साथ प्रदर्शन परीक्षण।

### चरण 3: माइग्रेशन और परिनियोजन (सप्ताह 3)
1. [ ] मौजूदा Neo4j उदाहरणों के लिए डेटा माइग्रेशन स्क्रिप्ट बनाएं।
2. [ ] परिनियोजन दस्तावेज़ और रनबुक।
3. [ ] अलगाव उल्लंघनों के लिए निगरानी और अलर्ट।
4. [ ] कई उपयोगकर्ताओं/संग्रहों के साथ एंड-टू-एंड परीक्षण।

### चरण 4: मजबूती (सप्ताह 4)
1. [ ] विरासत अनुकूलता मोड हटाएं।
2. [ ] व्यापक ऑडिट लॉगिंग जोड़ें।
3. [ ] सुरक्षा समीक्षा और प्रवेश परीक्षण।
4. [ ] प्रदर्शन अनुकूलन।

## परीक्षण रणनीति

### यूनिट परीक्षण
```python
def test_user_collection_isolation():
    # Store triples for user1/collection1
    processor.store_triples(triples_user1_coll1)
    
    # Store triples for user2/collection2  
    processor.store_triples(triples_user2_coll2)
    
    # Query as user1 should only return user1's data
    results = processor.query_triples(query_user1_coll1)
    assert all_results_belong_to_user1_coll1(results)
    
    # Query as user2 should only return user2's data
    results = processor.query_triples(query_user2_coll2)
    assert all_results_belong_to_user2_coll2(results)
```

### एकीकरण परीक्षण (एकीकरण परीक्षण)
मल्टी-यूजर परिदृश्य जिसमें ओवरलैपिंग डेटा शामिल है
क्रॉस-कलेक्शन क्वेरी (विफल होनी चाहिए)
मौजूदा डेटा के साथ माइग्रेशन परीक्षण
बड़े डेटासेट के साथ प्रदर्शन बेंचमार्क

### सुरक्षा परीक्षण (सुरक्षा परीक्षण)
अन्य उपयोगकर्ताओं के डेटा को क्वेरी करने का प्रयास
उपयोगकर्ता/कलेक्शन पैरामीटर पर SQL इंजेक्शन-शैली के हमले
विभिन्न क्वेरी पैटर्न के तहत पूर्ण अलगाव को सत्यापित करें

## प्रदर्शन संबंधी विचार (प्रदर्शन संबंधी विचार)

### इंडेक्स रणनीति (इंडेक्स रणनीति)
इष्टतम फ़िल्टरिंग के लिए `(user, collection, uri)` पर कंपाउंड इंडेक्स
यदि कुछ संग्रह बहुत बड़े हैं तो आंशिक इंडेक्स पर विचार करें
इंडेक्स उपयोग और क्वेरी प्रदर्शन की निगरानी करें

### क्वेरी अनुकूलन (क्वेरी अनुकूलन)
फ़िल्टर किए गए क्वेरी में इंडेक्स उपयोग को सत्यापित करने के लिए EXPLAIN का उपयोग करें
बार-बार एक्सेस किए जाने वाले डेटा के लिए क्वेरी परिणाम कैशिंग पर विचार करें
बड़ी संख्या में उपयोगकर्ताओं/संग्रहों के साथ मेमोरी उपयोग को प्रोफाइल करें

### मापनीयता (मापनीयता)
प्रत्येक उपयोगकर्ता/संग्रह संयोजन अलग-अलग डेटा द्वीप बनाता है
डेटाबेस आकार और कनेक्शन पूल उपयोग की निगरानी करें
यदि आवश्यक हो तो क्षैतिज स्केलिंग रणनीतियों पर विचार करें

## सुरक्षा और अनुपालन (सुरक्षा और अनुपालन)

### डेटा अलगाव गारंटी (डेटा अलगाव गारंटी)
**भौतिक**: सभी उपयोगकर्ता डेटा स्पष्ट उपयोगकर्ता/संग्रह गुणों के साथ संग्रहीत होते हैं
**तार्किक**: सभी क्वेरी उपयोगकर्ता/संग्रह संदर्भ द्वारा फ़िल्टर की जाती हैं
**पहुंच नियंत्रण**: सेवा-स्तरीय सत्यापन अनधिकृत पहुंच को रोकता है

### ऑडिट आवश्यकताएँ (ऑडिट आवश्यकताएँ)
उपयोगकर्ता/संग्रह संदर्भ के साथ सभी डेटा एक्सेस को लॉग करें
माइग्रेशन गतिविधियों और डेटा मूवमेंट को ट्रैक करें
अलगाव उल्लंघन के प्रयासों की निगरानी करें

### अनुपालन संबंधी विचार (अनुपालन संबंधी विचार)
जीडीपीआर: उपयोगकर्ता-विशिष्ट डेटा को खोजने और हटाने की बेहतर क्षमता
एसओसी2: स्पष्ट डेटा अलगाव और पहुंच नियंत्रण
एचआईपीएए: स्वास्थ्य सेवा डेटा के लिए मजबूत किरायेदार अलगाव

## जोखिम और निवारण (जोखिम और निवारण)

| जोखिम | प्रभाव | संभावना | निवारण |
|------|--------|------------|------------|
| क्वेरी में उपयोगकर्ता/संग्रह फ़िल्टर गुम है | उच्च | मध्यम | अनिवार्य सत्यापन, व्यापक परीक्षण
| प्रदर्शन में गिरावट | मध्यम | कम | इंडेक्स अनुकूलन, क्वेरी प्रोफाइलिंग
| माइग्रेशन डेटा भ्रष्टाचार | उच्च | कम | बैकअप रणनीति, रोलबैक प्रक्रियाएं
| जटिल मल्टी-कलेक्शन क्वेरी | मध्यम | मध्यम | क्वेरी पैटर्न को दस्तावेज़ करें, उदाहरण प्रदान करें

## सफलता मानदंड (सफलता मानदंड)

1. **सुरक्षा**: उत्पादन में क्रॉस-यूजर डेटा एक्सेस शून्य
2. **प्रदर्शन**: अनफ़िल्टर किए गए क्वेरी की तुलना में <10% क्वेरी प्रदर्शन प्रभाव
3. **माइग्रेशन**: 100% मौजूदा डेटा बिना किसी नुकसान के सफलतापूर्वक माइग्रेट किया गया
4. **उपयोगिता**: सभी मौजूदा क्वेरी पैटर्न उपयोगकर्ता/संग्रह संदर्भ के साथ काम करते हैं
5. **अनुपालन**: उपयोगकर्ता/संग्रह डेटा एक्सेस का पूर्ण ऑडिट ट्रेल

## निष्कर्ष (निष्कर्ष)

संपत्ति-आधारित फ़िल्टरिंग दृष्टिकोण उपयोगकर्ता/संग्रह अलगाव को Neo4j में जोड़ने के लिए सुरक्षा, प्रदर्शन और रखरखाव के बीच सबसे अच्छा संतुलन प्रदान करता है। यह Neo4j की ग्राफ क्वेरी और इंडेक्सिंग में ताकत का लाभ उठाते हुए TrustGraph के मौजूदा मल्टी-टेनेंसी पैटर्न के साथ संरेखित है।

यह समाधान सुनिश्चित करता है कि TrustGraph का Neo4j बैकएंड अन्य स्टोरेज बैकएंड के समान सुरक्षा मानकों को पूरा करता है, जिससे डेटा अलगाव कमजोरियों को रोका जा सकता है, जबकि ग्राफ क्वेरी की लचीलापन और शक्ति को बनाए रखा जा सकता है।
