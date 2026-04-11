# ऑन्टोलॉजी ज्ञान निष्कर्षण - चरण 2 का पुनर्गठन

**स्थिति**: मसौदा
**लेखक**: विश्लेषण सत्र 2025-12-03
**संबंधित**: `ontology.md`, `ontorag.md`

## अवलोकन

यह दस्तावेज़ वर्तमान ऑन्टोलॉजी-आधारित ज्ञान निष्कर्षण प्रणाली में मौजूद विसंगतियों की पहचान करता है और एलएलएम प्रदर्शन को बेहतर बनाने और सूचना हानि को कम करने के लिए एक पुनर्गठन का प्रस्ताव करता है।

## वर्तमान कार्यान्वयन

### यह वर्तमान में कैसे काम करता है

1. **ऑन्टोलॉजी लोडिंग** (`ontology_loader.py`)
   `"fo/Recipe"`, `"fo/Food"`, `"fo/produces"` जैसे कुंजियों के साथ ऑन्टोलॉजी JSON लोड करता है।
   क्लास आईडी में नामस्थान उपसर्ग स्वयं कुंजी में शामिल होता है।
   `food.ontology` से उदाहरण:
     ```json
     "classes": {
       "fo/Recipe": {
         "uri": "http://purl.org/ontology/fo/Recipe",
         "rdfs:comment": "A Recipe is a combination..."
       }
     }
     ```

2. **प्रॉम्प्ट निर्माण** (`extract.py:299-307`, `ontology-prompt.md`)
   टेम्पलेट को `classes`, `object_properties`, `datatype_properties` डिक्ट प्राप्त होते हैं।
   टेम्पलेट पुनरावृति करता है: `{% for class_id, class_def in classes.items() %}`
   एलएलएम देखता है: `**fo/Recipe**: A Recipe is a combination...`
   उदाहरण आउटपुट प्रारूप दर्शाता है:
     ```json
     {"subject": "recipe:cornish-pasty", "predicate": "rdf:type", "object": "Recipe"}
     {"subject": "recipe:cornish-pasty", "predicate": "has_ingredient", "object": "ingredient:flour"}
     ```

3. **प्रतिक्रिया पार्सिंग** (`extract.py:382-428`)
   JSON सरणी की अपेक्षा है: `[{"subject": "...", "predicate": "...", "object": "..."}]`
   यह एक उप-शब्दकोष के विरुद्ध मान्य है।
   `expand_uri()` के माध्यम से URI का विस्तार (extract.py:473-521)

4. **URI विस्तार** (`extract.py:473-521`)
   जांच करता है कि क्या मान `ontology_subset.classes` डिक्शनरी में है।
   यदि पाया जाता है, तो क्लास परिभाषा से URI निकालता है।
   यदि नहीं मिला, तो URI का निर्माण करता है: `f"https://trustgraph.ai/ontology/{ontology_id}#{value}"`

### डेटा प्रवाह उदाहरण

**शब्दकोष JSON → लोडर → प्रॉम्प्ट:**
```
"fo/Recipe" → classes["fo/Recipe"] → LLM sees "**fo/Recipe**"
```

**एलएलएम → पार्सर → आउटपुट:**
```
"Recipe" → not in classes["fo/Recipe"] → constructs URI → LOSES original URI
"fo/Recipe" → found in classes → uses original URI → PRESERVES URI
```

## पहचाने गए मुद्दे

### 1. **प्रॉम्प्ट में असंगत उदाहरण**

**समस्या**: प्रॉम्प्ट टेम्पलेट क्लास आईडी को उपसर्गों (`fo/Recipe`) के साथ दिखाता है, लेकिन उदाहरण आउटपुट में उपसर्ग रहित क्लास नाम (`Recipe`) का उपयोग किया गया है।

**स्थान**: `ontology-prompt.md:5-52`

```markdown
## Ontology Classes:
- **fo/Recipe**: A Recipe is...

## Example Output:
{"subject": "recipe:cornish-pasty", "predicate": "rdf:type", "object": "Recipe"}
```

**प्रभाव**: एलएलएम को किस प्रारूप का उपयोग करना है, इसके बारे में विरोधाभासी संकेत प्राप्त होते हैं।

### 2. **यूआरआई विस्तार में सूचना का नुकसान**

**समस्या**: जब एलएलएम उदाहरण के बाद बिना उपसर्ग वाले क्लास नामों को लौटाता है, तो `expand_uri()` उन्हें ऑन्टोलॉजी डिक्शनरी में नहीं ढूंढ पाता है और डिफ़ॉल्ट यूआरआई बनाता है, जिससे मूल सही यूआरआई खो जाते हैं।

**स्थान**: `extract.py:494-500`

```python
if value in ontology_subset.classes:  # Looks for "Recipe"
    class_def = ontology_subset.classes[value]  # But key is "fo/Recipe"
    if isinstance(class_def, dict) and 'uri' in class_def:
        return class_def['uri']  # Never reached!
return f"https://trustgraph.ai/ontology/{ontology_id}#{value}"  # Fallback
```

**प्रभाव:**
मूल यूआरआई: `http://purl.org/ontology/fo/Recipe`
निर्मित यूआरआई: `https://trustgraph.ai/ontology/food#Recipe`
अर्थ संबंधी जानकारी खो जाती है, इससे अंतर-क्षमता बाधित होती है।

### 3. **अस्पष्ट इकाई उदाहरण प्रारूप**

**समस्या:** इकाई उदाहरण यूआरआई प्रारूप के बारे में कोई स्पष्ट मार्गदर्शन नहीं है।

**प्रॉम्प्ट में उदाहरण:**
`"recipe:cornish-pasty"` (नेमस्पेस जैसा उपसर्ग)
`"ingredient:flour"` (एक अलग उपसर्ग)

**वास्तविक व्यवहार** (extract.py:517-520):
```python
# Treat as entity instance - construct unique URI
normalized = value.replace(" ", "-").lower()
return f"https://trustgraph.ai/{ontology_id}/{normalized}"
```

**प्रभाव**: एलएलएम को किसी भी संदर्भ के बिना उपसर्ग सम्मेलन का अनुमान लगाना होगा।

### 4. **कोई नेमस्पेस उपसर्ग मार्गदर्शन नहीं**

**समस्या**: ऑन्टोलॉजी JSON में नेमस्पेस परिभाषाएँ हैं (food.ontology में पंक्ति 10-25):
```json
"namespaces": {
  "fo": "http://purl.org/ontology/fo/",
  "rdf": "http://www.w3.org/1999/02/22-rdf-syntax-ns#",
  ...
}
```

लेकिन ये जानकारी कभी भी एलएलएम (LLM) तक नहीं पहुंचती। एलएलएम को यह नहीं पता:
"fo" का क्या मतलब है
एंटिटीज के लिए किस उपसर्ग का उपयोग करना है
कौन सा नेमस्पेस किस तत्व पर लागू होता है

### 5. **प्रॉम्प्ट में उपयोग नहीं किए गए लेबल**

**समस्या**: प्रत्येक क्लास में `rdfs:label` फ़ील्ड होते हैं (उदाहरण के लिए, `{"value": "Recipe", "lang": "en-gb"}`), लेकिन प्रॉम्प्ट टेम्पलेट इनका उपयोग नहीं करता है।

**वर्तमान**: केवल `class_id` और `comment` दिखाता है।
```jinja
- **{{class_id}}**{% if class_def.comment %}: {{class_def.comment}}{% endif %}
```

**उपलब्ध लेकिन अप्रयुक्त**:
```python
"rdfs:label": [{"value": "Recipe", "lang": "en-gb"}]
```

**प्रभाव**: यह तकनीकी आईडी के साथ पठनीय नाम प्रदान कर सकता है।

## प्रस्तावित समाधान

### विकल्प ए: उपसर्ग रहित आईडी में मानकीकरण

**दृष्टिकोण**: एलएलएम को दिखाने से पहले क्लास आईडी से उपसर्ग हटाएं।

**परिवर्तन**:
1. `build_extraction_variables()` को बदलने के लिए:
   ```python
   classes_for_prompt = {
       k.split('/')[-1]: v  # "fo/Recipe" → "Recipe"
       for k, v in ontology_subset.classes.items()
   }
   ```

2. उदाहरण प्रॉम्प्ट को अपडेट करें ताकि वह मेल खाए (यह पहले से ही बिना उपसर्ग वाले नामों का उपयोग करता है)।

3. `expand_uri()` को दोनों प्रारूपों को संभालने के लिए संशोधित करें:
   ```python
   # Try exact match first
   if value in ontology_subset.classes:
       return ontology_subset.classes[value]['uri']

   # Try with prefix
   for prefix in ['fo/', 'rdf:', 'rdfs:']:
       prefixed = f"{prefix}{value}"
       if prefixed in ontology_subset.classes:
           return ontology_subset.classes[prefixed]['uri']
   ```

**लाभ:**
अधिक स्पष्ट, अधिक मानव-पठनीय
मौजूदा प्रॉम्प्ट उदाहरणों से मेल खाता है
एलएलएम सरल टोकन के साथ बेहतर काम करते हैं

**नुकसान:**
यदि कई ऑन्टोलॉजी में समान क्लास नाम है तो क्लास नाम टकराव हो सकता है
नेमस्पेस जानकारी खो जाती है
लुकअप के लिए फॉलबैक लॉजिक की आवश्यकता होती है

### विकल्प बी: पूर्ण उपसर्ग आईडी का लगातार उपयोग करें

**दृष्टिकोण:** उदाहरणों को अपडेट करें ताकि वे क्लास सूची में दिखाए गए उपसर्ग आईडी से मेल खाएं।

**परिवर्तन:**
1. प्रॉम्प्ट उदाहरण अपडेट करें (ontology-prompt.md:46-52):
   ```json
   [
     {"subject": "recipe:cornish-pasty", "predicate": "rdf:type", "object": "fo/Recipe"},
     {"subject": "recipe:cornish-pasty", "predicate": "rdfs:label", "object": "Cornish Pasty"},
     {"subject": "recipe:cornish-pasty", "predicate": "fo/produces", "object": "food:cornish-pasty"},
     {"subject": "food:cornish-pasty", "predicate": "rdf:type", "object": "fo/Food"}
   ]
   ```

2. प्रॉम्प्ट में नेमस्पेस स्पष्टीकरण जोड़ें:
   ```markdown
   ## Namespace Prefixes:
   - **fo/**: Food Ontology (http://purl.org/ontology/fo/)
   - **rdf:**: RDF Schema
   - **rdfs:**: RDF Schema

   Use these prefixes exactly as shown when referencing classes and properties.
   ```

3. `expand_uri()` को वैसे ही रखें (जब मिलान पाया जाता है तो यह ठीक से काम करता है)।

**लाभ:**
इनपुट = आउटपुट स्थिरता
कोई जानकारी हानि नहीं
नेमस्पेस सिमेंटिक्स को संरक्षित करता है
कई ऑन्टोलॉजी के साथ काम करता है

**नुकसान:**
एलएलएम के लिए अधिक विस्तृत टोकन
एलएलएम को उपसर्गों को ट्रैक करने की आवश्यकता होती है

### विकल्प सी: हाइब्रिड - लेबल और आईडी दोनों दिखाएं

**दृष्टिकोण:** प्रॉम्प्ट को इस तरह से बेहतर बनाएं कि मानव-पठनीय लेबल और तकनीकी आईडी दोनों दिखाए जाएं।

**परिवर्तन:**
1. प्रॉम्प्ट टेम्पलेट को अपडेट करें:
   ```jinja
   {% for class_id, class_def in classes.items() %}
   - **{{class_id}}** (label: "{{class_def.labels[0].value if class_def.labels else class_id}}"){% if class_def.comment %}: {{class_def.comment}}{% endif %}
   {% endfor %}
   ```

   उदाहरण आउटपुट:
   ```markdown
   - **fo/Recipe** (label: "Recipe"): A Recipe is a combination...
   ```

2. अपडेट निर्देश:
   ```markdown
   When referencing classes:
   - Use the full prefixed ID (e.g., "fo/Recipe") in JSON output
   - The label (e.g., "Recipe") is for human understanding only
   ```

**लाभ:**
एलएलएम (LLM) के लिए सबसे स्पष्ट।
सभी जानकारी को संरक्षित करता है।
यह स्पष्ट करता है कि क्या उपयोग करना है।

**नुकसान:**
लंबा प्रॉम्प्ट।
अधिक जटिल टेम्पलेट।

## कार्यान्वित दृष्टिकोण

**सरलीकृत इकाई-संबंध-विशेषता प्रारूप** - पुराने ट्रिपल-आधारित प्रारूप को पूरी तरह से बदल देता है।

इस नए दृष्टिकोण को इसलिए चुना गया क्योंकि:

1. **कोई जानकारी हानि नहीं:** मूल यूआरआई (URI) सही ढंग से संरक्षित हैं।
2. **सरल तर्क:** किसी रूपांतरण की आवश्यकता नहीं है, सीधे डिक्ट (dict) लुकअप काम करते हैं।
3. **नेमस्पेस सुरक्षा:** टकराव के बिना कई ऑन्टोलॉजी (ontology) को संभालता है।
4. **सिमेंटिक (semantic) शुद्धता:** आरडीएफ/ओडब्ल्यूएल (RDF/OWL) सिमेंटिक्स को बनाए रखता है।

## कार्यान्वयन पूर्ण

### क्या बनाया गया:

1. **नया प्रॉम्प्ट टेम्पलेट** (`prompts/ontology-extract-v2.txt`)
   ✅ स्पष्ट अनुभाग: इकाई प्रकार, संबंध, विशेषताएँ।
   ✅ पूर्ण प्रकार पहचानकर्ताओं का उपयोग करके उदाहरण (`fo/Recipe`, `fo/has_ingredient`)।
   ✅ स्कीमा (schema) से सटीक पहचानकर्ताओं का उपयोग करने के निर्देश।
   ✅ संस्थाओं/संबंधों/विशेषताओं के सरणियों के साथ नया JSON प्रारूप।

2. **एंटिटी नॉर्मलाइजेशन** (`entity_normalizer.py`)
   ✅ `normalize_entity_name()` - नामों को URI-सुरक्षित प्रारूप में परिवर्तित करता है
   ✅ `normalize_type_identifier()` - प्रकारों में स्लैश को संभालता है (`fo/Recipe` → `fo-recipe`)
   ✅ `build_entity_uri()` - (नाम, प्रकार) टपल का उपयोग करके अद्वितीय URI बनाता है
   ✅ `EntityRegistry` - डुप्लिकेट से बचने के लिए एंटिटीज को ट्रैक करता है

3. **JSON पार्सर** (`simplified_parser.py`)
   ✅ नए प्रारूप को पार्स करता है: `{entities: [...], relationships: [...], attributes: [...]}`
   ✅ केबाब-केस और स्नेक_केस फ़ील्ड नामों का समर्थन करता है
   ✅ संरचित डेटाक्लासेस लौटाता है
   ✅ लॉगिंग के साथ त्रुटि प्रबंधन

4. **ट्रिपल कन्वर्टर** (`triple_converter.py`)
   ✅ `convert_entity()` - स्वचालित रूप से प्रकार + लेबल त्रिक उत्पन्न करता है।
   ✅ `convert_relationship()` - एंटिटी यूआरआई को गुणों के माध्यम से जोड़ता है।
   ✅ `convert_attribute()` - शाब्दिक मान जोड़ता है।
   ✅ ऑन्टोलॉजी परिभाषाओं से पूर्ण यूआरआई की खोज करता है।

5. **अपडेटेड मुख्य प्रोसेसर** (`extract.py`)
   ✅ पुराने ट्रिपल-आधारित निष्कर्षण कोड को हटा दिया गया।
   ✅ `extract_with_simplified_format()` विधि जोड़ी गई।
   ✅ अब केवल नए सरलीकृत प्रारूप का उपयोग करता है।
   ✅ `extract-with-ontologies-v2` आईडी के साथ प्रॉम्प्ट को कॉल करता है।

## परीक्षण मामले

### परीक्षण 1: यूआरआई संरक्षण
```python
# Given ontology class
classes = {"fo/Recipe": {"uri": "http://purl.org/ontology/fo/Recipe", ...}}

# When LLM returns
llm_output = {"subject": "x", "predicate": "rdf:type", "object": "fo/Recipe"}

# Then expanded URI should be
assert expanded == "http://purl.org/ontology/fo/Recipe"
# Not: "https://trustgraph.ai/ontology/food#Recipe"
```

### परीक्षण 2: बहु-ऑन्टोलॉजी टकराव
```python
# Given two ontologies
ont1 = {"fo/Recipe": {...}}
ont2 = {"cooking/Recipe": {...}}

# LLM should use full prefix to disambiguate
llm_output = {"object": "fo/Recipe"}  # Not just "Recipe"
```

### परीक्षण 3: इकाई उदाहरण प्रारूप
```python
# Given prompt with food ontology
# LLM should create instances like
{"subject": "recipe:cornish-pasty"}  # Namespace-style
{"subject": "food:beef"}              # Consistent prefix
```

## खुले प्रश्न

1. **क्या एंटिटी इंस्टेंस में नेमस्पेस उपसर्गों का उपयोग किया जाना चाहिए?**
   वर्तमान: `"recipe:cornish-pasty"` (यादृच्छिक)
   वैकल्पिक: क्या हमें ऑन्टोलॉजी उपसर्ग `"fo:cornish-pasty"` का उपयोग करना चाहिए?
   वैकल्पिक: कोई उपसर्ग नहीं, URI में विस्तार करें `"cornish-pasty"` → पूर्ण URI?

2. **प्रॉम्प्ट में डोमेन/रेंज को कैसे संभालें?**
   वर्तमान में दिखाता है: `(Recipe → Food)`
   क्या इसे `(fo/Recipe → fo/Food)` होना चाहिए?

3. **क्या हमें डोमेन/रेंज बाधाओं को मान्य करना चाहिए?**
   TODO टिप्पणी extract.py:470 पर
   यह अधिक त्रुटियों को पकड़ लेगा लेकिन अधिक जटिल होगा

4. **उलटा गुण और तुल्यता के बारे में क्या?**
   ऑन्टोलॉजी में `owl:inverseOf`, `owl:equivalentClass` है
   वर्तमान में निष्कर्षण में उपयोग नहीं किया जाता है
   क्या उन्हें उपयोग किया जाना चाहिए?

## सफलता मेट्रिक्स

✅ शून्य URI जानकारी हानि (मूल URIs का 100% संरक्षण)
✅ LLM आउटपुट प्रारूप इनपुट प्रारूप से मेल खाता है
✅ प्रॉम्प्ट में कोई अस्पष्ट उदाहरण नहीं
✅ कई ऑन्टोलॉजी के साथ परीक्षण पास होते हैं
✅ बेहतर निष्कर्षण गुणवत्ता (वैध ट्रिपल % द्वारा मापा गया)

## वैकल्पिक दृष्टिकोण: सरलीकृत निष्कर्षण प्रारूप

### दर्शन

LLM से RDF/OWL सिमेंटिक्स को समझने के बजाय, उससे वह कार्य करवाएं जिसमें वह अच्छा है: **पाठ में एंटिटीज और संबंधों को ढूंढना।**

URI निर्माण, RDF रूपांतरण और सिमेंटिक वेब औपचारिकताएं कोड द्वारा संभाली जाएं।

### उदाहरण: एंटिटी वर्गीकरण

**इनपुट टेक्स्ट:**
```
Cornish pasty is a traditional British pastry filled with meat and vegetables.
```

**ऑन्टोलॉजी स्कीमा (एलएलएम को दिखाया गया):**
```markdown
## Entity Types:
- Recipe: A recipe is a combination of ingredients and a method
- Food: A food is something that can be eaten
- Ingredient: An ingredient combines a quantity and a food
```

**एलएलएम क्या लौटाता है (सरल JSON):**
```json
{
  "entities": [
    {
      "entity": "Cornish pasty",
      "type": "Recipe"
    }
  ]
}
```

**कोड क्या उत्पन्न करता है (आरडीएफ ट्रिपल्स):**
```python
# 1. Normalize entity name + type to ID (type prevents collisions)
entity_id = "recipe-cornish-pasty"  # normalize("Cornish pasty", "Recipe")
entity_uri = "https://trustgraph.ai/food/recipe-cornish-pasty"

# Note: Same name, different type = different URI
# "Cornish pasty" (Recipe) → recipe-cornish-pasty
# "Cornish pasty" (Food) → food-cornish-pasty

# 2. Generate triples
triples = [
    # Type triple
    Triple(
        s=Value(value=entity_uri, is_uri=True),
        p=Value(value="http://www.w3.org/1999/02/22-rdf-syntax-ns#type", is_uri=True),
        o=Value(value="http://purl.org/ontology/fo/Recipe", is_uri=True)
    ),
    # Label triple (automatic)
    Triple(
        s=Value(value=entity_uri, is_uri=True),
        p=Value(value="http://www.w3.org/2000/01/rdf-schema#label", is_uri=True),
        o=Value(value="Cornish pasty", is_uri=False)
    )
]
```

### लाभ

1. **एलएलएम को इसकी आवश्यकता नहीं है:**
   यूआरआई सिंटैक्स को समझना
   पहचानकर्ता उपसर्गों का आविष्कार करना (`recipe:`, `ingredient:`)
   `rdf:type` या `rdfs:label` के बारे में जानना
   सिमेंटिक वेब पहचानकर्ताओं का निर्माण करना

2. **एलएलएम को केवल इसकी आवश्यकता है:**
   पाठ में संस्थाओं को खोजना
   उन्हें ऑन्टोलॉजी कक्षाओं में मैप करना
   संबंधों और विशेषताओं को निकालना

3. **कोड द्वारा संभाला जाता है:**
   यूआरआई सामान्यीकरण और निर्माण
   आरडीएफ ट्रिपल पीढ़ी
   स्वचालित लेबल असाइनमेंट
   नेमस्पेस प्रबंधन

### यह बेहतर क्यों है

**सरल प्रॉम्प्ट** = कम भ्रम = कम त्रुटियां
**संगत आईडी** = कोड सामान्यीकरण नियमों को नियंत्रित करता है
**स्वचालित रूप से उत्पन्न लेबल** = कोई छूटी हुई rdfs:label ट्रिपल नहीं
**एलएलएम निष्कर्षण पर केंद्रित है** = जो कि वास्तव में इसकी क्षमता है

### उदाहरण: इकाई संबंध

**इनपुट टेक्स्ट:**
```
Cornish pasty is a traditional British pastry filled with beef and potatoes.
```

**ऑन्टोलॉजी स्कीमा (एलएलएम को दिखाया गया):**
```markdown
## Entity Types:
- Recipe: A recipe is a combination of ingredients and a method
- Food: A food is something that can be eaten
- Ingredient: An ingredient combines a quantity and a food

## Relationships:
- has_ingredient: Relates a recipe to an ingredient it uses (Recipe → Ingredient)
- food: Relates an ingredient to the food that is required (Ingredient → Food)
```

**एलएलएम क्या लौटाता है (सरल JSON):**
```json
{
  "entities": [
    {
      "entity": "Cornish pasty",
      "type": "Recipe"
    },
    {
      "entity": "beef",
      "type": "Food"
    },
    {
      "entity": "potatoes",
      "type": "Food"
    }
  ],
  "relationships": [
    {
      "subject": "Cornish pasty",
      "subject-type": "Recipe",
      "relation": "has_ingredient",
      "object": "beef",
      "object-type": "Food"
    },
    {
      "subject": "Cornish pasty",
      "subject-type": "Recipe",
      "relation": "has_ingredient",
      "object": "potatoes",
      "object-type": "Food"
    }
  ]
}
```

**कोड क्या उत्पन्न करता है (आरडीएफ ट्रिपल्स):**
```python
# Normalize entity names to URIs
cornish_pasty_uri = "https://trustgraph.ai/food/cornish-pasty"
beef_uri = "https://trustgraph.ai/food/beef"
potatoes_uri = "https://trustgraph.ai/food/potatoes"

# Look up relation URI from ontology
has_ingredient_uri = "http://purl.org/ontology/fo/ingredients"  # from fo/has_ingredient

triples = [
    # Entity type triples (as before)
    Triple(s=cornish_pasty_uri, p=rdf_type, o="http://purl.org/ontology/fo/Recipe"),
    Triple(s=cornish_pasty_uri, p=rdfs_label, o="Cornish pasty"),

    Triple(s=beef_uri, p=rdf_type, o="http://purl.org/ontology/fo/Food"),
    Triple(s=beef_uri, p=rdfs_label, o="beef"),

    Triple(s=potatoes_uri, p=rdf_type, o="http://purl.org/ontology/fo/Food"),
    Triple(s=potatoes_uri, p=rdfs_label, o="potatoes"),

    # Relationship triples
    Triple(
        s=Value(value=cornish_pasty_uri, is_uri=True),
        p=Value(value=has_ingredient_uri, is_uri=True),
        o=Value(value=beef_uri, is_uri=True)
    ),
    Triple(
        s=Value(value=cornish_pasty_uri, is_uri=True),
        p=Value(value=has_ingredient_uri, is_uri=True),
        o=Value(value=potatoes_uri, is_uri=True)
    )
]
```

**मुख्य बातें:**
एलएलएम प्राकृतिक भाषा में इकाई नामों को लौटाता है: `"Cornish pasty"`, `"beef"`, `"potatoes"`
एलएलएम अस्पष्टता को दूर करने के लिए प्रकारों को शामिल करता है: `subject-type`, `object-type`
एलएलएम स्कीमा से संबंध नाम का उपयोग करता है: `"has_ingredient"`
कोड (नाम, प्रकार) का उपयोग करके सुसंगत आईडी प्राप्त करता है: `("Cornish pasty", "Recipe")` → `recipe-cornish-pasty`
कोड ऑन्टोलॉजी से संबंध यूआरआई को देखता है: `fo/has_ingredient` → पूर्ण यूआरआई
समान (नाम, प्रकार) टपल हमेशा समान यूआरआई प्राप्त करता है (डुप्लिकेट हटाने)।

### उदाहरण: इकाई नाम का अस्पष्टता निवारण

**समस्या:** एक ही नाम अलग-अलग इकाई प्रकारों को संदर्भित कर सकता है।

**वास्तविक दुनिया का मामला:**
```
"Cornish pasty" can be:
- A Recipe (instructions for making it)
- A Food (the dish itself)
```

**यह कैसे संभाला जाता है:**

एलएलएम दोनों को अलग-अलग इकाइयों के रूप में लौटाता है:
```json
{
  "entities": [
    {"entity": "Cornish pasty", "type": "Recipe"},
    {"entity": "Cornish pasty", "type": "Food"}
  ],
  "relationships": [
    {
      "subject": "Cornish pasty",
      "subject-type": "Recipe",
      "relation": "produces",
      "object": "Cornish pasty",
      "object-type": "Food"
    }
  ]
}
```

**कोड समाधान:**
```python
# Different types → different URIs
recipe_uri = normalize("Cornish pasty", "Recipe")
# → "https://trustgraph.ai/food/recipe-cornish-pasty"

food_uri = normalize("Cornish pasty", "Food")
# → "https://trustgraph.ai/food/food-cornish-pasty"

# Relationship connects them correctly
triple = Triple(
    s=recipe_uri,  # The Recipe
    p="http://purl.org/ontology/fo/produces",
    o=food_uri     # The Food
)
```

**यह क्यों काम करता है:**
प्रकार सभी संदर्भों (इकाइयों, संबंधों, विशेषताओं) में शामिल है।
कोड `(name, type)` टपल को लुकअप कुंजी के रूप में उपयोग करता है।
कोई अस्पष्टता नहीं, कोई टकराव नहीं।

### उदाहरण: इकाई विशेषताएँ

**इनपुट टेक्स्ट:**
```
This Cornish pasty recipe serves 4-6 people and takes 45 minutes to prepare.
```

**ऑन्टोलॉजी स्कीमा (एलएलएम को दिखाया गया):**
```markdown
## Entity Types:
- Recipe: A recipe is a combination of ingredients and a method

## Attributes:
- serves: Indicates what the recipe is intended to serve (Recipe → text)
- preparation_time: Time needed to prepare the recipe (Recipe → text)
```

**एलएलएम क्या लौटाता है (सरल JSON):**
```json
{
  "entities": [
    {
      "entity": "Cornish pasty recipe",
      "type": "Recipe"
    }
  ],
  "attributes": [
    {
      "entity": "Cornish pasty recipe",
      "entity-type": "Recipe",
      "attribute": "serves",
      "value": "4-6 people"
    },
    {
      "entity": "Cornish pasty recipe",
      "entity-type": "Recipe",
      "attribute": "preparation_time",
      "value": "45 minutes"
    }
  ]
}
```

**कोड क्या उत्पन्न करता है (आरडीएफ ट्रिपल्स):**
```python
# Normalize entity name to URI
recipe_uri = "https://trustgraph.ai/food/cornish-pasty-recipe"

# Look up attribute URIs from ontology
serves_uri = "http://purl.org/ontology/fo/serves"  # from fo/serves
prep_time_uri = "http://purl.org/ontology/fo/preparation_time"  # from fo/preparation_time

triples = [
    # Entity type triple
    Triple(
        s=Value(value=recipe_uri, is_uri=True),
        p=Value(value=rdf_type, is_uri=True),
        o=Value(value="http://purl.org/ontology/fo/Recipe", is_uri=True)
    ),

    # Label triple (automatic)
    Triple(
        s=Value(value=recipe_uri, is_uri=True),
        p=Value(value=rdfs_label, is_uri=True),
        o=Value(value="Cornish pasty recipe", is_uri=False)
    ),

    # Attribute triples (objects are literals, not URIs)
    Triple(
        s=Value(value=recipe_uri, is_uri=True),
        p=Value(value=serves_uri, is_uri=True),
        o=Value(value="4-6 people", is_uri=False)  # Literal value!
    ),
    Triple(
        s=Value(value=recipe_uri, is_uri=True),
        p=Value(value=prep_time_uri, is_uri=True),
        o=Value(value="45 minutes", is_uri=False)  # Literal value!
    )
]
```

**मुख्य बातें:**
एलएलएम शाब्दिक मानों को निकालता है: `"4-6 people"`, `"45 minutes"`
एलएलएम अस्पष्टता को दूर करने के लिए इकाई प्रकार को शामिल करता है: `entity-type`
एलएलएम स्कीमा से विशेषता नाम का उपयोग करता है: `"serves"`, `"preparation_time"`
कोड ऑन्टोलॉजी डेटाटाइप गुणों से विशेषता यूआरआई को देखता है
**ऑब्जेक्ट शाब्दिक है** (`is_uri=False`), कोई यूआरआई संदर्भ नहीं है
मान प्राकृतिक पाठ के रूप में रहते हैं, किसी सामान्यीकरण की आवश्यकता नहीं है

**संबंधों से अंतर:**
संबंध: विषय और वस्तु दोनों इकाइयाँ (यूआरआई) हैं
विशेषताएँ: विषय इकाई (यूआरआई) है, वस्तु शाब्दिक मान (स्ट्रिंग/संख्या) है

### संपूर्ण उदाहरण: इकाइयाँ + संबंध + विशेषताएँ

**इनपुट टेक्स्ट:**
```
Cornish pasty is a savory pastry filled with beef and potatoes.
This recipe serves 4 people.
```

**एलएलएम क्या लौटाता है:**
```json
{
  "entities": [
    {
      "entity": "Cornish pasty",
      "type": "Recipe"
    },
    {
      "entity": "beef",
      "type": "Food"
    },
    {
      "entity": "potatoes",
      "type": "Food"
    }
  ],
  "relationships": [
    {
      "subject": "Cornish pasty",
      "subject-type": "Recipe",
      "relation": "has_ingredient",
      "object": "beef",
      "object-type": "Food"
    },
    {
      "subject": "Cornish pasty",
      "subject-type": "Recipe",
      "relation": "has_ingredient",
      "object": "potatoes",
      "object-type": "Food"
    }
  ],
  "attributes": [
    {
      "entity": "Cornish pasty",
      "entity-type": "Recipe",
      "attribute": "serves",
      "value": "4 people"
    }
  ]
}
```

**परिणाम:** 11 आरडीएफ त्रिगुण उत्पन्न हुए:
3 इकाई प्रकार त्रिगुण (rdf:type)
3 इकाई लेबल त्रिगुण (rdfs:label) - स्वचालित
2 संबंध त्रिगुण (has_ingredient)
1 विशेषता त्रिगुण (serves)

ये सभी एलएलएम द्वारा सरल, प्राकृतिक भाषा निष्कर्षण से प्राप्त हुए!

## संदर्भ

वर्तमान कार्यान्वयन: `trustgraph-flow/trustgraph/extract/kg/ontology/extract.py`
प्रॉम्प्ट टेम्पलेट: `ontology-prompt.md`
परीक्षण मामले: `tests/unit/test_extract/test_ontology/`
उदाहरण ऑन्टोलॉजी: `e2e/test-data/food.ontology`
