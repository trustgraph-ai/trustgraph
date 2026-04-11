---
layout: default
title: "Api Gateway Changes V1.8 To V2.1.Hi"
parent: "Hindi (Beta)"
---

> **Beta Translation:** This document was translated via Machine Learning and as such may not be 100% accurate. All non-English languages are currently classified as Beta.

## API गेटवे में बदलाव: v1.8 से v2.1

## सारांश

API गेटवे में एम्बेडिंग प्रश्नों के लिए नए WebSocket सेवा डिस्पैचर, दस्तावेज़ सामग्री के लिए एक नया REST स्ट्रीमिंग एंडपॉइंट, और `Value` से `Term` में एक महत्वपूर्ण वायर प्रारूप परिवर्तन शामिल है। "ऑब्जेक्ट्स" सेवा को "रो" के रूप में पुनः नाम दिया गया।

---

## नए WebSocket सेवा डिस्पैचर

ये `/api/v1/socket` पर उपलब्ध नए अनुरोध/प्रतिक्रिया सेवाएँ हैं (फ्लो-स्कोप):

| सेवा कुंजी | विवरण |
|---|---|
| `document-embeddings` | टेक्स्ट समानता के आधार पर दस्तावेज़ टुकड़ों के लिए क्वेरी करता है। अनुरोध/प्रतिक्रिया `DocumentEmbeddingsRequest`/`DocumentEmbeddingsResponse` स्कीमा का उपयोग करते हैं। |
| `row-embeddings` | इंडेक्स किए गए फ़ील्ड में टेक्स्ट समानता के आधार पर संरचित डेटा पंक्तियों के लिए क्वेरी करता है। अनुरोध/प्रतिक्रिया `RowEmbeddingsRequest`/`RowEmbeddingsResponse` स्कीमा का उपयोग करते हैं। |

ये मौजूदा `graph-embeddings` डिस्पैचर (जो पहले से ही v1.8 में मौजूद है, लेकिन अपडेट किया जा सकता है) के साथ जुड़ते हैं।

### WebSocket फ़्लो सेवा डिस्पैचर की पूरी सूची (v2.1)

अनुरोध/प्रतिक्रिया सेवाएँ (`/api/v1/flow/{flow}/service/{kind}` या WebSocket मक्स) के माध्यम से:

- `agent`, `text-completion`, `prompt`, `mcp-tool`
- `graph-rag`, `document-rag`
- `embeddings`, `graph-embeddings`, `document-embeddings`
- `triples`, `rows`, `nlp-query`, `structured-query`, `structured-diag`
- `row-embeddings`

---

## नया REST एंडपॉइंट

| विधि | पथ | विवरण |
|---|---|---|
| `GET` | `/api/v1/document-stream` | लाइब्रेरी से मूल बाइट के रूप में दस्तावेज़ सामग्री स्ट्रीम करता है। क्वेरी पैरामीटर: `user` (आवश्यक), `document-id` (आवश्यक), `chunk-size` (वैकल्पिक, डिफ़ॉल्ट 1MB)। आंतरिक रूप से base64 से डिकोड करके दस्तावेज़ सामग्री को chunked transfer encoding में लौटाता है। |

---

## पुनः नामकरण की गई सेवा: "objects" से "rows"

| v1.8 | v2.1 | नोट्स |
|---|---|---|
| `objects_query.py` / `ObjectsQueryRequestor` | `rows_query.py` / `RowsQueryRequestor` | `ObjectsQueryRequest`/`ObjectsQueryResponse` से `RowsQueryRequest`/`RowsQueryResponse` स्कीमा में बदलाव। |
| `objects_import.py` / `ObjectsImport` | `rows_import.py` / `RowsImport` | संरचित डेटा के लिए आयात डिस्पैचर। |

WebSocket सेवा कुंजी `"objects"` से `"rows"` में बदल गई है, और आयात डिस्पैचर कुंजी `"objects"` से `"rows"` में बदल गई है।

---

## वायर प्रारूप में बदलाव: Value से Term

`serialize.py` में serialization लेयर को नए `Term` प्रकार का उपयोग करने के लिए फिर से लिखा गया है, बजाय पुराने `Value` प्रकार का।

### पुराना प्रारूप (v1.8 — `Value`)

```json
{"v": "http://example.org/entity", "e": true}
```

- `v`: मान (स्ट्रिंग)
- `e`: एक बूलियन ध्वज जो दर्शाता है कि मान एक URI है या नहीं

### नया प्रारूप (v2.1 — `Term`)

IRI:
```json
{"t": "i", "i": "http://example.org/entity"}
```

प्रत्यक्ष:
```json
{"t": "l", "v": "some text", "d": "datatype-uri", "l": "en"}
```

कोटेड ट्रिपल (RDF-star):
```json
{"t": "r", "r": {"s": {...}, "p": {...}, "o": {...}}}
```

- `t`: प्रकार डिस्‍क्रिमिनेटर — `"i"` (IRI), `"l"` (प्रत्यक्ष), `"r"` (कोटेड ट्रिपल), `"b"` (ब्लैंक नोड)
- serialization अब `trustgraph.messaging.translators.primitives` से `TermTranslator` और `TripleTranslator` को सौंपता है।

### अन्य serialization में बदलाव

| फ़ील्ड | v1.8 | v2.1 |
|---|---|---|
| मेटाडेटा | `metadata.metadata` (उप-ग्राफ) | `metadata.root` (सरल मान) |
| ग्राफ एम्बेडिंग इकाई | `entity.vectors` (बहु) | `entity.vector` (एकल) |
| दस्तावेज़ एम्बेडिंग टुकड़ा | `chunk.vectors` + `chunk.chunk` (टेक्स्ट) | `chunk.vector` + `chunk.chunk_id` (आईडी संदर्भ) |

---

## महत्वपूर्ण बदलाव

- **`Value` से `Term` वायर प्रारूप**: गेटवे के माध्यम से ट्रिपल, एम्बेडिंग या इकाई संदर्भ भेजने/प्राप्त करने वाले सभी क्लाइंट को नए Term प्रारूप के साथ अपडेट करना होगा।
- **`objects` से `rows` का नामकरण**: WebSocket सेवा कुंजी और आयात कुंजी में बदलाव।
- **मेटाडेटा फ़ील्ड में बदलाव**: `metadata.metadata` (एक serialized उप-ग्राफ) को `metadata.root` (एक सरल मान) से बदला गया।
- **एम्बेडिंग फ़ील्ड में बदलाव**: `vectors` (बहु) को `vector` (एकल) से बदला गया; दस्तावेज़ एम्बेडिंग अब `chunk_id` को संदर्भित करती हैं, बजाय inline `chunk` टेक्स्ट के।
- **नया `/api/v1/document-stream` एंडपॉइंट**: यह एक अतिरिक्त परिवर्तन है, जो पहले से ही मौजूद है।
