# व्याख्यात्मकता CLI तकनीकी विनिर्देश

## स्थिति

मसौदा

## अवलोकन

यह विनिर्देश ट्रस्टग्राफ में व्याख्यात्मकता डेटा को डिबग और एक्सप्लोर करने के लिए CLI टूल का वर्णन करता है। ये उपकरण उपयोगकर्ताओं को यह ट्रैक करने में सक्षम बनाते हैं कि उत्तर कैसे प्राप्त किए गए और किनारा से वापस स्रोत दस्तावेजों तक उत्पत्ति श्रृंखला को डिबग किया गया।

तीन CLI उपकरण:

1. **`tg-show-document-hierarchy`** - दस्तावेज़ → पृष्ठ → भाग → किनारा पदानुक्रम दिखाएं
2. **`tg-list-explain-traces`** - सभी GraphRAG सत्रों को प्रश्नों के साथ सूचीबद्ध करें
3. **`tg-show-explain-trace`** - एक सत्र के लिए पूर्ण व्याख्यात्मकता ट्रेस दिखाएं

## लक्ष्य

**डीबगिंग**: डेवलपर्स को दस्तावेज़ प्रसंस्करण परिणामों का निरीक्षण करने में सक्षम करें
**लेखापरीक्षा**: किसी भी निकाले गए तथ्य को उसके स्रोत दस्तावेज़ तक ट्रैक करें
**पारदर्शिता**: सटीक रूप से दिखाएं कि GraphRAG ने उत्तर कैसे प्राप्त किया
**उपयोगिता**: समझदार डिफ़ॉल्ट के साथ सरल CLI इंटरफ़ेस

## पृष्ठभूमि

ट्रस्टग्राफ में दो उत्पत्ति प्रणालियाँ हैं:

1. **निकालने के समय की उत्पत्ति** (देखें `extraction-time-provenance.md`): दस्तावेज़ → पृष्ठ → भाग → किनारा संबंधों को इनपुट के दौरान रिकॉर्ड करता है। `urn:graph:source` नामक ग्राफ में संग्रहीत, `prov:wasDerivedFrom` का उपयोग करके।

2. **क्वेरी-टाइम व्याख्यात्मकता** (देखें `query-time-explainability.md`): GraphRAG प्रश्नों के दौरान प्रश्न → अन्वेषण → फोकस → संश्लेषण श्रृंखला को रिकॉर्ड करता है। `urn:graph:retrieval` नामक ग्राफ में संग्रहीत।

वर्तमान सीमाएँ:
प्रसंस्करण के बाद दस्तावेज़ पदानुक्रम को देखने का कोई आसान तरीका नहीं है
व्याख्यात्मकता डेटा देखने के लिए ट्रिपल को मैन्युअल रूप से क्वेरी करना होगा
GraphRAG सत्र का कोई समेकित दृश्य नहीं है

## तकनीकी डिज़ाइन

### टूल 1: tg-show-document-hierarchy

**उद्देश्य**: एक दस्तावेज़ आईडी को देखते हुए, सभी व्युत्पन्न संस्थाओं को पार करें और प्रदर्शित करें।

**उपयोग**:
```bash
tg-show-document-hierarchy "urn:trustgraph:doc:abc123"
tg-show-document-hierarchy --show-content --max-content 500 "urn:trustgraph:doc:abc123"
```

**तर्क**:
| तर्क | विवरण |
|-----|-------------|
| `document_id` | दस्तावेज़ यूआरआई (स्थानिक) |
| `-u/--api-url` | गेटवे यूआरएल (डिफ़ॉल्ट: `$TRUSTGRAPH_URL`) |
| `-t/--token` | ऑथ टोकन (डिफ़ॉल्ट: `$TRUSTGRAPH_TOKEN`) |
| `-U/--user` | उपयोगकर्ता आईडी (डिफ़ॉल्ट: `trustgraph`) |
| `-C/--collection` | संग्रह (डिफ़ॉल्ट: `default`) |
| `--show-content` | ब्लॉब/दस्तावेज़ सामग्री शामिल करें |
| `--max-content` | प्रति ब्लॉब अधिकतम अक्षर (डिफ़ॉल्ट: 200) |
| `--format` | आउटपुट: `tree` (डिफ़ॉल्ट), `json` |

**कार्यान्वयन**:
1. ट्रिपल क्वेरी करें: `?child prov:wasDerivedFrom <document_id>` in `urn:graph:source`
2. प्रत्येक परिणाम के बच्चों को पुनरावर्ती रूप से क्वेरी करें
3. ट्री संरचना बनाएं: दस्तावेज़ → पृष्ठ → भाग
4. यदि `--show-content`, तो लाइब्रेरियन एपीआई से सामग्री प्राप्त करें
5. इंडेंटेड ट्री या JSON के रूप में प्रदर्शित करें

**आउटपुट उदाहरण**:
```
Document: urn:trustgraph:doc:abc123
  Title: "Sample PDF"
  Type: application/pdf

  └── Page 1: urn:trustgraph:doc:abc123/p1
      ├── Chunk 0: urn:trustgraph:doc:abc123/p1/c0
      │   Content: "The quick brown fox..." [truncated]
      └── Chunk 1: urn:trustgraph:doc:abc123/p1/c1
          Content: "Machine learning is..." [truncated]
```

### टूल 2: tg-list-explain-traces

**उद्देश्य**: एक संग्रह में सभी ग्राफ़आरएजी सत्रों (प्रश्नों) को सूचीबद्ध करना।

**उपयोग**:
```bash
tg-list-explain-traces
tg-list-explain-traces --limit 20 --format json
```

**तर्क:**
| तर्क | विवरण |
|-----|-------------|
| `-u/--api-url` | गेटवे यूआरएल |
| `-t/--token` | प्रमाणीकरण टोकन |
| `-U/--user` | उपयोगकर्ता आईडी |
| `-C/--collection` | संग्रह |
| `--limit` | अधिकतम परिणाम (डिफ़ॉल्ट: 50) |
| `--format` | आउटपुट: `table` (डिफ़ॉल्ट), `json` |

**कार्यान्वयन:**
1. क्वेरी: `?session tg:query ?text` को `urn:graph:retrieval` में |
2. क्वेरी टाइमस्टैम्प: `?session prov:startedAtTime ?time` |
3. तालिका के रूप में प्रदर्शित करें |

**आउटपुट उदाहरण:**
```
Session ID                                    | Question                        | Time
----------------------------------------------|--------------------------------|---------------------
urn:trustgraph:question:abc123                | What was the War on Terror?    | 2024-01-15 10:30:00
urn:trustgraph:question:def456                | Who founded OpenAI?            | 2024-01-15 09:15:00
```

### टूल 3: tg-show-explain-trace

**उद्देश्य**: ग्राफ़आरएजी सत्र के लिए पूर्ण व्याख्या श्रृंखला प्रदर्शित करें।

**उपयोग**:
```bash
tg-show-explain-trace "urn:trustgraph:question:abc123"
tg-show-explain-trace --max-answer 1000 --show-provenance "urn:trustgraph:question:abc123"
```

**तर्क:**
| तर्क | विवरण |
|-----|-------------|
| `question_id` | प्रश्न URI (स्थानिक) |
| `-u/--api-url` | गेटवे URL |
| `-t/--token` | प्रमाणीकरण टोकन |
| `-U/--user` | उपयोगकर्ता ID |
| `-C/--collection` | संग्रह |
| `--max-answer` | उत्तर के लिए अधिकतम अक्षर (डिफ़ॉल्ट: 500) |
| `--show-provenance` | स्रोत दस्तावेजों तक किनारों को ट्रेस करें |
| `--format` | आउटपुट: `text` (डिफ़ॉल्ट), `json` |

**कार्यान्वयन:**
1. `tg:query` विधेय से प्रश्न पाठ प्राप्त करें।
2. अन्वेषण खोजें: `?exp prov:wasGeneratedBy <question_id>`
3. फोकस खोजें: `?focus prov:wasDerivedFrom <exploration_id>`
4. चयनित किनारों को प्राप्त करें: `<focus_id> tg:selectedEdge ?edge`
5. प्रत्येक किनारे के लिए, `tg:edge` (उद्धृत ट्रिपल) और `tg:reasoning` प्राप्त करें।
6. संश्लेषण खोजें: `?synth prov:wasDerivedFrom <focus_id>`
7. लाइब्रेरियन के माध्यम से `tg:document` से उत्तर प्राप्त करें।
8. यदि `--show-provenance`, तो स्रोत दस्तावेजों तक किनारों को ट्रेस करें।

**आउटपुट उदाहरण:**
```
=== GraphRAG Session: urn:trustgraph:question:abc123 ===

Question: What was the War on Terror?
Time: 2024-01-15 10:30:00

--- Exploration ---
Retrieved 50 edges from knowledge graph

--- Focus (Edge Selection) ---
Selected 12 edges:

  1. (War on Terror, definition, "A military campaign...")
     Reasoning: Directly defines the subject of the query
     Source: chunk → page 2 → "Beyond the Vigilant State"

  2. (Guantanamo Bay, part_of, War on Terror)
     Reasoning: Shows key component of the campaign

--- Synthesis ---
Answer:
  The War on Terror was a military campaign initiated...
  [truncated at 500 chars]
```

## बनाने के लिए फ़ाइलें

| फ़ाइल | उद्देश्य |
|------|---------|
| `trustgraph-cli/trustgraph/cli/show_document_hierarchy.py` | टूल 1 |
| `trustgraph-cli/trustgraph/cli/list_explain_traces.py` | टूल 2 |
| `trustgraph-cli/trustgraph/cli/show_explain_trace.py` | टूल 3 |

## बदलने के लिए फ़ाइलें

| फ़ाइल | परिवर्तन |
|------|--------|
| `trustgraph-cli/setup.py` | console_scripts प्रविष्टियाँ जोड़ें |

## कार्यान्वयन नोट्स

1. **बाइनरी सामग्री सुरक्षा**: UTF-8 डिकोड करने का प्रयास करें; यदि विफल रहता है, तो `[Binary: {size} bytes]` प्रदर्शित करें।
2. **छंटनी**: `--max-content`/`--max-answer` का सम्मान करें जिसमें `[truncated]` संकेतक हो।
3. **उद्धृत तिगुट**: `tg:edge` विधेय से RDF-स्टार प्रारूप को पार्स करें।
4. **पैटर्न**: `query_graph.py` से मौजूदा CLI पैटर्न का पालन करें।

## सुरक्षा विचार

सभी क्वेरी उपयोगकर्ता/संग्रह सीमाओं का सम्मान करती हैं।
`--token` या `$TRUSTGRAPH_TOKEN` के माध्यम से टोकन प्रमाणीकरण समर्थित है।

## परीक्षण रणनीति

नमूना डेटा के साथ मैन्युअल सत्यापन:
```bash
# Load a test document
tg-load-pdf -f test.pdf -c test-collection

# Verify hierarchy
tg-show-document-hierarchy "urn:trustgraph:doc:test"

# Run a GraphRAG query with explainability
tg-invoke-graph-rag --explainable -q "Test question"

# List and inspect traces
tg-list-explain-traces
tg-show-explain-trace "urn:trustgraph:question:xxx"
```

## संदर्भ

क्वेरी-टाइम व्याख्यात्मकता: `docs/tech-specs/query-time-explainability.md`
निष्कर्षण-टाइम उत्पत्ति: `docs/tech-specs/extraction-time-provenance.md`
मौजूदा CLI उदाहरण: `trustgraph-cli/trustgraph/cli/invoke_graph_rag.py`
