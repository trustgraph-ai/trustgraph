# JSONL प्रॉम्प्ट आउटपुट तकनीकी विनिर्देश

## अवलोकन

<<<<<<< HEAD
यह विनिर्देश ट्रस्टग्राफ में प्रॉम्प्ट प्रतिक्रियाओं के लिए JSONL (JSON लाइन्स) आउटपुट प्रारूप के कार्यान्वयन का वर्णन करता है। JSONL, LLM प्रतिक्रियाओं से संरचित डेटा को निकालने में सक्षम बनाता है, जो कि LLM प्रतिक्रियाओं के आउटपुट टोकन सीमाओं तक पहुंचने पर JSON सरणी आउटपुट के दूषित होने जैसी महत्वपूर्ण समस्याओं को हल करता है।




=======
यह विनिर्देश ट्रस्टग्राफ में प्रॉम्प्ट प्रतिक्रियाओं के लिए JSONL (JSON लाइन्स) आउटपुट प्रारूप के कार्यान्वयन का वर्णन करता है। JSONL, LLM प्रतिक्रियाओं से संरचित डेटा को निकालने में सक्षम बनाता है, जो कि LLM प्रतिक्रियाओं के आउटपुट टोकन सीमाओं तक पहुंचने पर JSON सरणी आउटपुट के दूषित होने जैसी महत्वपूर्ण समस्याओं का समाधान करता है।
>>>>>>> 82edf2d (New md files from RunPod)


<<<<<<< HEAD
1. **ट्रंकेशन-रेज़िलिएंट एक्सट्रैक्शन (Truncation-Resilient Extraction)**: वैध आंशिक परिणाम निकालें, भले ही
   एलएलएम (LLM) आउटपुट प्रतिक्रिया के बीच में ही काट दिया गया हो।
2. **बड़े पैमाने पर एक्सट्रैक्शन (Large-Scale Extraction)**: टोकन सीमाओं के कारण पूर्ण विफलता के जोखिम के बिना, कई वस्तुओं के निष्कर्षण को संभालें।
   3. **मिश्रित-प्रकार एक्सट्रैक्शन (Mixed-Type Extraction)**: एक ही प्रॉम्प्ट में कई इकाई प्रकारों (परिभाषाओं, संबंधों, संस्थाओं, विशेषताओं) के निष्कर्षण का समर्थन करें।
4. **स्ट्रीमिंग-संगत आउटपुट (Streaming-Compatible Output)**: निष्कर्षण परिणामों की भविष्य की स्ट्रीमिंग/क्रमिक
   प्रसंस्करण को सक्षम करें।

   
=======



यह कार्यान्वयन निम्नलिखित उपयोग परिदृश्यों का समर्थन करता है:

1. **ट्रंकेशन-प्रतिरोधी निष्कर्षण**: भले ही एलएलएम आउटपुट प्रतिक्रिया के बीच में काट दिया गया हो, फिर भी मान्य आंशिक परिणाम निकालें।
   एलएलएम आउटपुट प्रतिक्रिया के बीच में काट दिया गया हो, फिर भी मान्य आंशिक परिणाम निकालें।
2. **बड़ी-पैमाने पर निष्कर्षण**: टोकन सीमाओं के कारण पूर्ण विफलता के जोखिम के बिना, कई वस्तुओं के निष्कर्षण को संभालें।
   टोकन सीमाओं के कारण पूर्ण विफलता के जोखिम के बिना, कई वस्तुओं के निष्कर्षण को संभालें।
3. **मिश्रित-प्रकार निष्कर्षण**: एक ही प्रॉम्प्ट में कई इकाई प्रकारों (परिभाषाएँ, संबंध, इकाइयाँ, विशेषताएँ) के निष्कर्षण का समर्थन करें।
   एक ही प्रॉम्प्ट में कई इकाई प्रकारों (परिभाषाएँ, संबंध, इकाइयाँ, विशेषताएँ) के निष्कर्षण का समर्थन करें।
4. **स्ट्रीमिंग-संगत आउटपुट**: निष्कर्षण परिणामों की भविष्य की स्ट्रीमिंग/क्रमिक प्रसंस्करण को सक्षम करें।
   निष्कर्षण परिणामों की भविष्य की स्ट्रीमिंग/क्रमिक प्रसंस्करण को सक्षम करें।
>>>>>>> 82edf2d (New md files from RunPod)

## लक्ष्य

**पिछड़ा संगतता (Backward Compatibility)**: मौजूदा प्रॉम्प्ट जो `response-type: "text"` और का उपयोग करते हैं,
<<<<<<< HEAD
  `response-type: "json"` बिना किसी बदलाव के काम करना जारी रखते हैं।
**अतिसंयमी लचीलापन (Truncation Resilience)**: आंशिक एलएलएम आउटपुट आंशिक, मान्य परिणाम देते हैं,
  पूर्ण विफलता के बजाय।
**स्कीमा सत्यापन (Schema Validation)**: व्यक्तिगत ऑब्जेक्ट के लिए JSON स्कीमा सत्यापन का समर्थन।
=======
  `response-type: "json"`, बिना किसी बदलाव के काम करना जारी रखते हैं।
**अतिसंयमी लचीलापन (Truncation Resilience)**: आंशिक एलएलएम आउटपुट आंशिक, मान्य परिणाम देते हैं,
  पूर्ण विफलता के बजाय।
**स्कीमा सत्यापन (Schema Validation)**: व्यक्तिगत वस्तुओं के लिए JSON स्कीमा सत्यापन का समर्थन।
>>>>>>> 82edf2d (New md files from RunPod)
**विभेदक संघ (Discriminated Unions)**: `type` फ़ील्ड का उपयोग करके मिश्रित-प्रकार के आउटपुट का समर्थन।
  विभेदक।
**न्यूनतम एपीआई परिवर्तन (Minimal API Changes)**: नए प्रतिक्रिया प्रकार और स्कीमा कुंजी के साथ मौजूदा प्रॉम्प्ट कॉन्फ़िगरेशन का विस्तार।
  

## पृष्ठभूमि

### वर्तमान आर्किटेक्चर

प्रॉम्प्ट सेवा दो प्रकार के प्रतिक्रियाओं का समर्थन करती है:

1. `response-type: "text"` - बिना किसी बदलाव के वापस की गई कच्ची टेक्स्ट प्रतिक्रिया
<<<<<<< HEAD
2. `response-type: "json"` - प्रतिक्रिया से पार्स किया गया JSON, जिसकी जाँच `response-type: "json"` के विरुद्ध की जाती है
   वैकल्पिक `schema`

`trustgraph-flow/trustgraph/template/prompt_manager.py` में वर्तमान कार्यान्वयन:
=======
2. `response-type: "json"` - प्रतिक्रिया से पार्स किया गया JSON, जिसकी तुलना
   वैकल्पिक `schema` से की जाती है

वर्तमान कार्यान्वयन `trustgraph-flow/trustgraph/template/prompt_manager.py` में:
>>>>>>> 82edf2d (New md files from RunPod)

```python
class Prompt:
    def __init__(self, template, response_type = "text", terms=None, schema=None):
        self.template = template
        self.response_type = response_type
        self.terms = terms
        self.schema = schema
```

<<<<<<< HEAD
### वर्तमान सीमाएँ

जब निष्कर्षण प्रॉम्प्ट आउटपुट को JSON सरणियों (`[{...}, {...}, ...]`) के रूप में मांगते हैं:

**अतिसंक्षेपण भ्रष्टाचार**: यदि LLM आउटपुट टोकन सीमाओं को सरणी के बीच में पार करता है, तो
  संपूर्ण प्रतिक्रिया अमान्य JSON बन जाती है और इसे पार्स नहीं किया जा सकता है।
**सब कुछ या कुछ नहीं पार्सिंग**: पार्स करने से पहले पूर्ण आउटपुट प्राप्त करना आवश्यक है।
**कोई आंशिक परिणाम नहीं**: एक छोटा आउटपुट शून्य उपयोगी डेटा उत्पन्न करता है।
**बड़े निष्कर्षणों के लिए अविश्वसनीय**: अधिक निकाले गए आइटम = उच्च विफलता जोखिम।

यह विनिर्देश इन सीमाओं को JSONL प्रारूप को पेश करके संबोधित करता है, जहाँ प्रत्येक निकाले गए आइटम को अपनी
=======
### वर्तमान सीमाएं

जब निष्कर्षण प्रॉम्प्ट आउटपुट को JSON सरणियों (`[{...}, {...}, ...]`) के रूप में मांगते हैं:

**अतिसंयोजन भ्रष्टाचार**: यदि LLM आउटपुट टोकन सीमाओं को सरणी के बीच में पार करता है, तो
  संपूर्ण प्रतिक्रिया अमान्य JSON बन जाती है और इसे पार्स नहीं किया जा सकता है।
**सब कुछ या कुछ नहीं पार्सिंग**: पार्स करने से पहले पूर्ण आउटपुट प्राप्त करना आवश्यक है।
**कोई आंशिक परिणाम नहीं**: एकtruncated प्रतिक्रिया शून्य उपयोगी डेटा उत्पन्न करती है।
**बड़े निष्कर्षणों के लिए अविश्वसनीय**: अधिक निकाले गए आइटम = उच्च विफलता जोखिम।

यह विनिर्देश इन सीमाओं को JSONL प्रारूप को पेश करके संबोधित करता है, जहां प्रत्येक निकाले गए आइटम को अपनी
>>>>>>> 82edf2d (New md files from RunPod)
पंक्ति पर एक पूर्ण JSON ऑब्जेक्ट के रूप में दर्शाया जाता है।


## तकनीकी डिज़ाइन

### प्रतिक्रिया प्रकार विस्तार

मौजूदा `"text"` और `"json"` प्रकारों के साथ एक नया प्रतिक्रिया प्रकार `"jsonl"` जोड़ें।

#### कॉन्फ़िगरेशन परिवर्तन

**नया प्रतिक्रिया प्रकार मान:**

```
"response-type": "jsonl"
```

**स्कीमा व्याख्या:**

मौजूदा `"schema"` कुंजी का उपयोग `"json"` और `"jsonl"` दोनों प्रतिक्रिया प्रकारों के लिए किया जाता है।
व्याख्या प्रतिक्रिया के प्रकार पर निर्भर करती है:

`"json"`: स्कीमा संपूर्ण प्रतिक्रिया का वर्णन करता है (आमतौर पर एक सरणी या ऑब्जेक्ट)।
`"jsonl"`: स्कीमा प्रत्येक व्यक्तिगत पंक्ति/ऑब्जेक्ट का वर्णन करता है।

```json
{
  "response-type": "jsonl",
  "schema": {
    "type": "object",
    "properties": {
      "entity": { "type": "string" },
      "definition": { "type": "string" }
    },
    "required": ["entity", "definition"]
  }
}
```

यह प्रॉम्प्ट कॉन्फ़िगरेशन टूलिंग और संपादकों में बदलावों से बचाता है।

### JSONL प्रारूप विनिर्देश

#### सरल निष्कर्षण

उन प्रॉम्प्ट के लिए जो केवल एक प्रकार की वस्तु (परिभाषाएँ, संबंध,
<<<<<<< HEAD
विषय, पंक्तियाँ) निकालते हैं, आउटपुट में बिना किसी अतिरिक्त आवरण के प्रति पंक्ति एक JSON ऑब्जेक्ट होता है:
=======
विषय, पंक्तियाँ) निकालते हैं, आउटपुट में बिना किसी अतिरिक्त आवरण के, प्रति पंक्ति एक JSON ऑब्जेक्ट होता है:
>>>>>>> 82edf2d (New md files from RunPod)

**प्रॉम्प्ट आउटपुट प्रारूप:**
```
{"entity": "photosynthesis", "definition": "Process by which plants convert sunlight"}
{"entity": "chlorophyll", "definition": "Green pigment in plants"}
{"entity": "mitochondria", "definition": "Powerhouse of the cell"}
```

**पिछले JSON सरणी प्रारूप के साथ अंतर:**
```json
[
  {"entity": "photosynthesis", "definition": "Process by which plants convert sunlight"},
  {"entity": "chlorophyll", "definition": "Green pigment in plants"},
  {"entity": "mitochondria", "definition": "Powerhouse of the cell"}
]
```

यदि एलएलएम (LLM) दूसरी पंक्ति के बाद कट जाता है, तो JSON सरणी प्रारूप अमान्य JSON उत्पन्न करता है,
जबकि JSONL दो मान्य ऑब्जेक्ट उत्पन्न करता है।

#### मिश्रित-प्रकार निष्कर्षण (भेदभावपूर्ण संघ)

<<<<<<< HEAD
उन प्रॉम्प्ट के लिए जो ऑब्जेक्ट के कई प्रकारों को निकालते हैं (उदाहरण के लिए, परिभाषाएँ और
संबंध, या इकाइयाँ, संबंध और विशेषताएँ), एक `"type"`
फ़ील्ड को विभेदक के रूप में उपयोग करें:
=======
उन प्रॉम्प्ट के लिए जो कई प्रकार की वस्तुओं को निकालते हैं (उदाहरण के लिए, परिभाषाएँ और
संबंध, या इकाइयाँ, संबंध और विशेषताएँ), एक `"type"`
फ़ील्ड का उपयोग विभेदक के रूप में करें:
>>>>>>> 82edf2d (New md files from RunPod)

**प्रॉम्प्ट आउटपुट प्रारूप:**
```
{"type": "definition", "entity": "DNA", "definition": "Molecule carrying genetic instructions"}
{"type": "relationship", "subject": "DNA", "predicate": "located_in", "object": "cell nucleus", "object-entity": true}
{"type": "definition", "entity": "RNA", "definition": "Molecule that carries genetic information"}
{"type": "relationship", "subject": "RNA", "predicate": "transcribed_from", "object": "DNA", "object-entity": true}
```

**विभेदक संघों के लिए स्कीमा `oneOf` का उपयोग करता है:**
```json
{
  "response-type": "jsonl",
  "schema": {
    "oneOf": [
      {
        "type": "object",
        "properties": {
          "type": { "const": "definition" },
          "entity": { "type": "string" },
          "definition": { "type": "string" }
        },
        "required": ["type", "entity", "definition"]
      },
      {
        "type": "object",
        "properties": {
          "type": { "const": "relationship" },
          "subject": { "type": "string" },
          "predicate": { "type": "string" },
          "object": { "type": "string" },
          "object-entity": { "type": "boolean" }
        },
        "required": ["type", "subject", "predicate", "object", "object-entity"]
      }
    ]
  }
}
```

#### शब्दावली निष्कर्षण

संस्थाओं, संबंधों और विशेषताओं के साथ शब्दावली-आधारित निष्कर्षण के लिए:

**प्रॉम्प्ट आउटपुट प्रारूप:**
```
{"type": "entity", "entity": "Cornish pasty", "entity_type": "fo/Recipe"}
{"type": "entity", "entity": "beef", "entity_type": "fo/Food"}
{"type": "relationship", "subject": "Cornish pasty", "subject_type": "fo/Recipe", "relation": "fo/has_ingredient", "object": "beef", "object_type": "fo/Food"}
{"type": "attribute", "entity": "Cornish pasty", "entity_type": "fo/Recipe", "attribute": "fo/serves", "value": "4 people"}
```

### कार्यान्वयन विवरण

#### प्रॉम्प्ट क्लास

मौजूदा `Prompt` क्लास में कोई बदलाव आवश्यक नहीं है। `schema` फ़ील्ड का पुन: उपयोग किया गया है।
JSONL के लिए, जिसका अर्थ `response_type` द्वारा निर्धारित किया जाता है:

```python
class Prompt:
    def __init__(self, template, response_type="text", terms=None, schema=None):
        self.template = template
        self.response_type = response_type
        self.terms = terms
        self.schema = schema  # Interpretation depends on response_type
```

<<<<<<< HEAD
#### प्रॉम्प्टमैनेजर.लोड_कॉन्फ़िगरेशन
=======
#### PromptManager.load_config
>>>>>>> 82edf2d (New md files from RunPod)

कोई बदलाव आवश्यक नहीं है - मौजूदा कॉन्फ़िगरेशन लोड करने की प्रक्रिया पहले से ही
`schema` कुंजी को संभालती है।

#### JSONL पार्सिंग

JSONL प्रतिक्रियाओं के लिए एक नई पार्सिंग विधि जोड़ें:

```python
def parse_jsonl(self, text):
    """
    Parse JSONL response, returning list of valid objects.

    Invalid lines (malformed JSON, empty lines) are skipped with warnings.
    This provides truncation resilience - partial output yields partial results.
    """
    results = []

    for line_num, line in enumerate(text.strip().split('\n'), 1):
        line = line.strip()

        # Skip empty lines
        if not line:
            continue

        # Skip markdown code fence markers if present
        if line.startswith('```'):
            continue

        try:
            obj = json.loads(line)
            results.append(obj)
        except json.JSONDecodeError as e:
            # Log warning but continue - this provides truncation resilience
            logger.warning(f"JSONL parse error on line {line_num}: {e}")

    return results
```

#### प्रॉम्प्टमैनेजर.इनवॉइक में बदलाव

इनवॉइक विधि को नए प्रतिक्रिया प्रकार को संभालने के लिए विस्तारित करें:

```python
async def invoke(self, id, input, llm):
    logger.debug("Invoking prompt template...")

    terms = self.terms | self.prompts[id].terms | input
    resp_type = self.prompts[id].response_type

    prompt = {
        "system": self.system_template.render(terms),
        "prompt": self.render(id, input)
    }

    resp = await llm(**prompt)

    if resp_type == "text":
        return resp

    if resp_type == "json":
        try:
            obj = self.parse_json(resp)
        except:
            logger.error(f"JSON parse failed: {resp}")
            raise RuntimeError("JSON parse fail")

        if self.prompts[id].schema:
            try:
                validate(instance=obj, schema=self.prompts[id].schema)
                logger.debug("Schema validation successful")
            except Exception as e:
                raise RuntimeError(f"Schema validation fail: {e}")

        return obj

    if resp_type == "jsonl":
        objects = self.parse_jsonl(resp)

        if not objects:
            logger.warning("JSONL parse returned no valid objects")
            return []

        # Validate each object against schema if provided
        if self.prompts[id].schema:
            validated = []
            for i, obj in enumerate(objects):
                try:
                    validate(instance=obj, schema=self.prompts[id].schema)
                    validated.append(obj)
                except Exception as e:
                    logger.warning(f"Object {i} failed schema validation: {e}")
            return validated

        return objects

    raise RuntimeError(f"Response type {resp_type} not known")
```

### प्रभावित संकेत (प्रॉम्प्ट)

निम्नलिखित संकेतों को JSONL प्रारूप में स्थानांतरित किया जाना चाहिए:

| संकेत आईडी | विवरण | प्रकार फ़ील्ड |
|-----------|-------------|------------|
| `extract-definitions` | इकाई/परिभाषा निष्कर्षण | नहीं (एकल प्रकार) |
| `extract-relationships` | संबंध निष्कर्षण | नहीं (एकल प्रकार) |
| `extract-topics` | विषय/परिभाषा निष्कर्षण | नहीं (एकल प्रकार) |
| `extract-rows` | संरचित पंक्ति निष्कर्षण | नहीं (एकल प्रकार) |
| `agent-kg-extract` | संयुक्त परिभाषा + संबंध निष्कर्षण | हाँ: `"definition"`, `"relationship"` |
| `extract-with-ontologies` / `ontology-extract` | ज्ञान-आधारित निष्कर्षण | हाँ: `"entity"`, `"relationship"`, `"attribute"` |

### एपीआई में बदलाव

#### क्लाइंट का दृष्टिकोण

JSONL पार्सिंग, प्रॉम्प्ट सर्विस एपीआई उपयोगकर्ताओं के लिए पारदर्शी है। पार्सिंग प्रॉम्प्ट सर्विस में सर्वर-साइड पर होता है, और प्रतिक्रिया मानक ⟦CODE_0⟧ फ़ील्ड के रूप में एक क्रमबद्ध JSON सरणी के माध्यम से वापस की जाती है।

`PromptResponse.object`

जब ग्राहक प्रॉम्प्ट सेवा को कॉल करते हैं (`PromptClient.prompt()` या इसी तरह के माध्यम से):

**`response-type: "json"`** जिसमें एरे स्कीमा है → ग्राहक को पायथन `list` प्राप्त होता है।
**`response-type: "jsonl"`** → ग्राहक को पायथन `list` प्राप्त होता है।

<<<<<<< HEAD
ग्राहक के दृष्टिकोण से, दोनों समान डेटा संरचनाएं लौटाते हैं।
अंतर पूरी तरह से इस बात में है कि सर्वर-साइड पर एलएलएम आउटपुट को कैसे पार्स किया जाता है:

JSON सरणी प्रारूप: एक `json.loads()` कॉल; यदि छोटा किया गया तो पूरी तरह से विफल हो जाता है।
JSONL प्रारूप: लाइन-दर-लाइन पार्सिंग; यदि छोटा किया गया तो आंशिक परिणाम देता है।
=======
ग्राहक के दृष्टिकोण से, दोनों समान डेटा संरचनाएँ लौटाते हैं।
अंतर पूरी तरह से इस बात में है कि सर्वर-साइड पर एलएलएम आउटपुट को कैसे पार्स किया जाता है:

JSON सरणी प्रारूप: एक `json.loads()` कॉल; यदि छोटा किया गया तो पूरी तरह विफल हो जाता है।
JSONL प्रारूप: पंक्ति-दर-पंक्ति पार्सिंग; यदि छोटा किया गया तो आंशिक परिणाम देता है।
>>>>>>> 82edf2d (New md files from RunPod)

इसका मतलब है कि मौजूदा क्लाइंट कोड जो एक्सट्रैक्शन प्रॉम्प्ट से एक सूची की अपेक्षा करता है,
को JSON से JSONL प्रारूप में प्रॉम्प्ट माइग्रेट करते समय किसी भी बदलाव की आवश्यकता नहीं होती है।

#### सर्वर रिटर्न वैल्यू

`response-type: "jsonl"` के लिए, `PromptManager.invoke()` विधि एक
<<<<<<< HEAD
`list[dict]` लौटाती है जिसमें सभी सफलतापूर्वक पार्स और मान्य किए गए ऑब्जेक्ट शामिल होते हैं। इस
=======
`list[dict]` लौटाती है जिसमें सभी सफलतापूर्वक पार्स किए गए और मान्य ऑब्जेक्ट शामिल हैं। इस
>>>>>>> 82edf2d (New md files from RunPod)
सूची को तब `PromptResponse.object` फ़ील्ड के लिए JSON में क्रमबद्ध किया जाता है।

#### त्रुटि प्रबंधन

<<<<<<< HEAD
खाली परिणाम: खाली सूची `[]` लौटाता है चेतावनी लॉग के साथ।
आंशिक पार्स विफलता: सफलतापूर्वक पार्स किए गए ऑब्जेक्ट की सूची लौटाता है,
  विफलताओं के लिए चेतावनी लॉग के साथ।
पूर्ण पार्स विफलता: खाली सूची `[]` लौटाता है, चेतावनी लॉग के साथ।

यह `response-type: "json"` से अलग है, जो पार्स विफलता पर `RuntimeError` उत्पन्न करता है।
=======
खाली परिणाम: खाली सूची `[]` लौटाता है, साथ में चेतावनी लॉग।
आंशिक पार्स विफलता: सफलतापूर्वक पार्स किए गए ऑब्जेक्ट की सूची लौटाता है,
  विफलताओं के लिए चेतावनी लॉग के साथ।
पूर्ण पार्स विफलता: खाली सूची `[]` लौटाता है, साथ में चेतावनी लॉग।

यह `response-type: "json"` से भिन्न है, जो पार्स विफलता पर `RuntimeError` उत्पन्न करता है।
>>>>>>> 82edf2d (New md files from RunPod)
JSONL के लिए उदार व्यवहार जानबूझकर प्रदान किया गया है ताकि ट्रंकेशन के प्रति लचीलापन मिल सके।


### कॉन्फ़िगरेशन उदाहरण

पूर्ण प्रॉम्प्ट कॉन्फ़िगरेशन उदाहरण:

```json
{
  "prompt": "Extract all entities and their definitions from the following text. Output one JSON object per line.\n\nText:\n{{text}}\n\nOutput format per line:\n{\"entity\": \"<name>\", \"definition\": \"<definition>\"}",
  "response-type": "jsonl",
  "schema": {
    "type": "object",
    "properties": {
      "entity": {
        "type": "string",
        "description": "The entity name"
      },
      "definition": {
        "type": "string",
        "description": "A clear definition of the entity"
      }
    },
    "required": ["entity", "definition"]
  }
}
```

## सुरक्षा संबंधी विचार

**इनपुट सत्यापन**: JSON पार्सिंग मानक `json.loads()` का उपयोग करता है, जो इंजेक्शन हमलों के खिलाफ सुरक्षित है।
  **स्कीमा सत्यापन**: स्कीमा प्रवर्तन के लिए ⟦CODE_0⟧ का उपयोग करता है।
**स्कीमा सत्यापन**: स्कीमा के अनुपालन को सुनिश्चित करने के लिए `jsonschema.validate()` का उपयोग करता है।
**कोई नया आक्रमण क्षेत्र नहीं**: JSONL पार्सिंग, लाइन-दर-लाइन प्रसंस्करण के कारण, JSON सरणी पार्सिंग की तुलना में बहुत अधिक सुरक्षित है।
  

## प्रदर्शन संबंधी विचार

<<<<<<< HEAD
**मेमोरी**: पंक्ति-दर-पंक्ति पार्सिंग, पूरे JSON सरणियों को लोड करने की तुलना में कम चरम मेमोरी का उपयोग करती है।
=======
**मेमोरी**: लाइन-दर-लाइन पार्सिंग, पूरे JSON सरणियों को लोड करने की तुलना में कम चरम मेमोरी का उपयोग करती है।
>>>>>>> 82edf2d (New md files from RunPod)
  **विलंबता**: पार्सिंग प्रदर्शन, JSON सरणी पार्सिंग के समान है।
**सत्यापन**: स्कीमा सत्यापन प्रत्येक ऑब्जेक्ट के लिए किया जाता है, जिससे ओवरहेड बढ़ता है, लेकिन सत्यापन विफलता पर आंशिक परिणाम प्राप्त करने की अनुमति मिलती है।

  ## परीक्षण रणनीति

## परीक्षण रणनीति

### यूनिट परीक्षण (Unit Tests)

मान्य इनपुट के साथ JSONL पार्सिंग
खाली पंक्तियों के साथ JSONL पार्सिंग
मार्कडाउन कोड फ़ेंस के साथ JSONL पार्सिंग
<<<<<<< HEAD
कटे हुए अंतिम पंक्ति के साथ JSONL पार्सिंग
=======
truncated अंतिम पंक्ति के साथ JSONL पार्सिंग
>>>>>>> 82edf2d (New md files from RunPod)
अमान्य JSON पंक्तियों के साथ JSONL पार्सिंग
`oneOf` विभेदक संघों के साथ स्कीमा सत्यापन
पिछली अनुकूलता: मौजूदा `"text"` और `"json"` प्रॉम्प्ट अपरिवर्तित

### एकीकरण परीक्षण (Integration Tests)

JSONL प्रॉम्प्ट के साथ एंड-टू-एंड निष्कर्षण
<<<<<<< HEAD
अनुकरणित कटाई के साथ निष्कर्षण (कृत्रिम रूप से सीमित प्रतिक्रिया)
=======
अनुकरणित ट्रंकेशन के साथ निष्कर्षण (कृत्रिम रूप से सीमित प्रतिक्रिया)
>>>>>>> 82edf2d (New md files from RunPod)
टाइप डिस्क्रिमिनेटर के साथ मिश्रित-प्रकार निष्कर्षण
सभी तीन प्रकारों के साथ ऑन्टोलॉजी निष्कर्षण

### निष्कर्षण गुणवत्ता परीक्षण (Extraction Quality Tests)

निष्कर्षण परिणामों की तुलना करें: JSONL बनाम JSON सरणी प्रारूप
ट्रंकेशन के प्रति लचीलापन की जाँच करें: JSONL आंशिक परिणाम देता है जहाँ JSON विफल रहता है

## माइग्रेशन योजना

### चरण 1: कार्यान्वयन

1. `parse_jsonl()` विधि को `PromptManager` में लागू करें
2. `invoke()` को `response-type: "jsonl"` को संभालने के लिए विस्तारित करें
3. यूनिट परीक्षण जोड़ें

### चरण 2: प्रॉम्प्ट माइग्रेशन

1. `extract-definitions` प्रॉम्प्ट और कॉन्फ़िगरेशन को अपडेट करें
2. `extract-relationships` प्रॉम्प्ट और कॉन्फ़िगरेशन को अपडेट करें
3. `extract-topics` प्रॉम्प्ट और कॉन्फ़िगरेशन को अपडेट करें
4. `extract-rows` प्रॉम्प्ट और कॉन्फ़िगरेशन को अपडेट करें
5. `agent-kg-extract` प्रॉम्प्ट और कॉन्फ़िगरेशन को अपडेट करें
6. `extract-with-ontologies` प्रॉम्प्ट और कॉन्फ़िगरेशन को अपडेट करें

### चरण 3: डाउनस्ट्रीम अपडेट

1. निष्कर्षण परिणामों का उपयोग करने वाले किसी भी कोड को सूची रिटर्न प्रकार को संभालने के लिए अपडेट करें
2. `type` फ़ील्ड द्वारा मिश्रित-प्रकार के निष्कर्षणों को वर्गीकृत करने वाले कोड को अपडेट करें
<<<<<<< HEAD
3. निष्कर्षण आउटपुट प्रारूप पर दावा करने वाले परीक्षणों को अपडेट करें
=======
3. निष्कर्षण आउटपुट प्रारूप पर जोर देने वाले परीक्षणों को अपडेट करें
>>>>>>> 82edf2d (New md files from RunPod)

## खुले प्रश्न

फिलहाल कोई नहीं।

## संदर्भ

वर्तमान कार्यान्वयन: `trustgraph-flow/trustgraph/template/prompt_manager.py`
JSON लाइन्स विनिर्देश: https://jsonlines.org/
JSON स्कीमा `oneOf`: https://json-schema.org/understanding-json-schema/reference/combining.html#oneof
संबंधित विनिर्देश: स्ट्रीमिंग LLM प्रतिक्रियाएँ (`docs/tech-specs/streaming-llm-responses.md`)
