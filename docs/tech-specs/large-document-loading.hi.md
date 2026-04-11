---
layout: default
title: "बड़े दस्तावेज़ लोडिंग के लिए तकनीकी विनिर्देश"
parent: "Hindi (Beta)"
---

# बड़े दस्तावेज़ लोडिंग के लिए तकनीकी विनिर्देश

> **Beta Translation:** This document was translated via Machine Learning and as such may not be 100% accurate. All non-English languages are currently classified as Beta.

## अवलोकन

यह विनिर्देश स्केलेबिलिटी और उपयोगकर्ता अनुभव से संबंधित मुद्दों को संबोधित करता है जो तब उत्पन्न होते हैं जब TrustGraph में बड़े दस्तावेज़ लोड किए जाते हैं। वर्तमान आर्किटेक्चर दस्तावेज़ अपलोड को एक एकल, अविभाज्य ऑपरेशन के रूप में मानता है, जिससे पाइपलाइन के कई बिंदुओं पर मेमोरी का दबाव पड़ता है और उपयोगकर्ताओं को कोई प्रतिक्रिया या रिकवरी विकल्प नहीं मिलते हैं।

यह कार्यान्वयन निम्नलिखित उपयोग मामलों को लक्षित करता है:




1. **बड़े पीडीएफ प्रसंस्करण**: सैकड़ों मेगाबाइट के पीडीएफ फ़ाइलों को अपलोड करें और संसाधित करें
   बिना मेमोरी समाप्त किए।
2. **फिर से शुरू करने योग्य अपलोड**: बाधित अपलोड को वहीं से जारी करने की अनुमति दें जहां से
   वे रुके थे, न कि पुनः आरंभ करने के बजाय।
3. **प्रगति प्रतिक्रिया**: उपयोगकर्ताओं को अपलोड और प्रसंस्करण की वास्तविक समय की जानकारी प्रदान करें।
   4. **मेमोरी-कुशल प्रसंस्करण**: दस्तावेज़ों को स्ट्रीमिंग तरीके से संसाधित करें
बिना पूरी फ़ाइलों को मेमोरी में रखे।
   

## लक्ष्य

**क्रमिक अपलोड**: REST और WebSocket के माध्यम से खंडित दस्तावेज़ अपलोड का समर्थन।
**फिर से शुरू करने योग्य स्थानांतरण**: बाधित अपलोड से उबरने की क्षमता।
**प्रगति दृश्यता**: क्लाइंट को अपलोड/प्रोसेसिंग प्रगति प्रतिक्रिया प्रदान करें।
**मेमोरी दक्षता**: पाइपलाइन में पूरे दस्तावेज़ को बफर करने से बचें।
**पिछड़ा संगतता**: मौजूदा छोटे दस्तावेज़ वर्कफ़्लो बिना किसी बदलाव के जारी रहते हैं।
**स्ट्रीमिंग प्रोसेसिंग**: PDF डिकोडिंग और टेक्स्ट चंकिंग स्ट्रीम पर काम करते हैं।

## पृष्ठभूमि

### वर्तमान आर्किटेक्चर

दस्तावेज़ सबमिशन निम्नलिखित पथ से गुजरता है:

1. **क्लाइंट** REST (`POST /api/v1/librarian`) या WebSocket के माध्यम से दस्तावेज़ सबमिट करता है।
2. **API गेटवे** बेस64-एन्कोडेड दस्तावेज़ सामग्री के साथ पूर्ण अनुरोध प्राप्त करता है।
3. **LibrarianRequestor** अनुरोध को Pulsar संदेश में बदलता है।
4. **Librarian सर्विस** संदेश प्राप्त करता है, दस्तावेज़ को मेमोरी में डिकोड करता है।
5. **BlobStore** दस्तावेज़ को Garage/S3 पर अपलोड करता है।
6. **Cassandra** ऑब्जेक्ट संदर्भ के साथ मेटाडेटा संग्रहीत करता है।
7. प्रोसेसिंग के लिए: दस्तावेज़ को S3 से पुनर्प्राप्त किया जाता है, डिकोड किया जाता है, खंडित किया जाता है - सभी मेमोरी में।

मुख्य फाइलें:
REST/WebSocket एंट्री: `trustgraph-flow/trustgraph/gateway/service.py`
Librarian कोर: `trustgraph-flow/trustgraph/librarian/librarian.py`
Blob स्टोरेज: `trustgraph-flow/trustgraph/librarian/blob_store.py`
Cassandra टेबल: `trustgraph-flow/trustgraph/tables/library.py`
API स्कीमा: `trustgraph-base/trustgraph/schema/services/library.py`

### वर्तमान सीमाएँ

वर्तमान डिज़ाइन में कई जटिल मेमोरी और उपयोगकर्ता अनुभव संबंधी समस्याएं हैं:

1. **परमाणु अपलोड ऑपरेशन**: संपूर्ण दस्तावेज़ को एक
   एकल अनुरोध में प्रेषित किया जाना चाहिए। बड़े दस्तावेज़ों के लिए लंबे समय तक चलने वाले अनुरोधों की आवश्यकता होती है, जिसमें कोई प्रगति संकेत नहीं होता है और यदि कनेक्शन विफल हो जाता है तो कोई पुनः प्रयास तंत्र नहीं होता है।
   

2. **एपीआई डिज़ाइन**: REST और WebSocket दोनों एपीआई संपूर्ण दस्तावेज़ की अपेक्षा करते हैं
   एक ही संदेश में। स्कीमा (`LibrarianRequest`) में एक `content`
   फ़ील्ड है जिसमें संपूर्ण बेस64-एन्कोडेड दस्तावेज़ होता है।

3. **लाइब्रेरियन मेमोरी**: लाइब्रेरियन सेवा पूरे दस्तावेज़ को
   मेमोरी में डिकोड करती है, फिर इसे S3 पर अपलोड करने से पहले। 500MB के PDF के लिए, इसका मतलब है कि 500MB+ को प्रोसेस मेमोरी में रखना।
   500MB+ को प्रोसेस मेमोरी में रखना।

4. **PDF डिकोडर मेमोरी**: जब प्रोसेसिंग शुरू होती है, तो PDF डिकोडर टेक्स्ट निकालने के लिए पूरे PDF को मेमोरी में लोड करता है। PyPDF और समान लाइब्रेरीज़ को आमतौर पर पूरे दस्तावेज़ तक पहुंच की आवश्यकता होती है।
   PyPDF और समान लाइब्रेरीज़ को आमतौर पर पूरे दस्तावेज़ तक पहुंच की आवश्यकता होती है।
   

5. **चंकर मेमोरी**: टेक्स्ट चंकर, निकाले गए पूरे टेक्स्ट को प्राप्त करता है
   और इसे मेमोरी में रखता है, जबकि चंक्स बनाता है।

**मेमोरी प्रभाव का उदाहरण** (500MB पीडीएफ):
गेटवे: ~700MB (बेस64 एन्कोडिंग ओवरहेड)
लाइब्रेरियन: ~500MB (डिकोडेड बाइट्स)
पीडीएफ डिकोडर: ~500MB + एक्सट्रैक्शन बफ़र्स
चंकर: निकाला गया टेक्स्ट (चर, संभावित रूप से 100MB+)

एक बड़े दस्तावेज़ के लिए कुल अधिकतम मेमोरी 2GB से अधिक हो सकती है।

## तकनीकी डिज़ाइन

### डिज़ाइन सिद्धांत

1. **एपीआई फ़ेसड**: सभी क्लाइंट इंटरैक्शन लाइब्रेरियन एपीआई के माध्यम से होते हैं। क्लाइंट
   के पास अंतर्निहित S3/गैराज स्टोरेज तक प्रत्यक्ष पहुंच या ज्ञान नहीं है।

2. **एस3 मल्टीपार्ट अपलोड**: आंतरिक रूप से मानक एस3 मल्टीपार्ट अपलोड का उपयोग करें।
   यह एस3-संगत प्रणालियों (AWS S3, MinIO, Garage,
   Ceph, DigitalOcean Spaces, Backblaze B2, आदि) में व्यापक रूप से समर्थित है, जो पोर्टेबिलिटी सुनिश्चित करता है।

3. **परमाणु पूर्णता**: एस3 मल्टीपार्ट अपलोड स्वाभाविक रूप से परमाणु होते हैं - अपलोड किए गए
   भाग तब तक अदृश्य रहते हैं जब तक कि `CompleteMultipartUpload` को कॉल नहीं किया जाता। कोई अस्थायी
   फ़ाइलें या नाम बदलने की क्रियाएं आवश्यक नहीं हैं।

4. **ट्रैक करने योग्य स्थिति**: अपलोड सत्रों को कैसेंड्रा में ट्रैक किया जाता है, जो
   अपूर्ण अपलोडों में दृश्यता प्रदान करता है और पुनः आरंभ करने की क्षमता को सक्षम करता है।

### चंक्ड अपलोड प्रवाह

```
Client                    Librarian API                   S3/Garage
  │                            │                              │
  │── begin-upload ───────────►│                              │
  │   (metadata, size)         │── CreateMultipartUpload ────►│
  │                            │◄── s3_upload_id ─────────────│
  │◄── upload_id ──────────────│   (store session in          │
  │                            │    Cassandra)                │
  │                            │                              │
  │── upload-chunk ───────────►│                              │
  │   (upload_id, index, data) │── UploadPart ───────────────►│
  │                            │◄── etag ─────────────────────│
  │◄── ack + progress ─────────│   (store etag in session)    │
  │         ⋮                  │         ⋮                    │
  │   (repeat for all chunks)  │                              │
  │                            │                              │
  │── complete-upload ────────►│                              │
  │   (upload_id)              │── CompleteMultipartUpload ──►│
  │                            │   (parts coalesced by S3)    │
  │                            │── store doc metadata ───────►│ Cassandra
  │◄── document_id ────────────│   (delete session)           │
```

क्लाइंट कभी भी सीधे S3 के साथ इंटरैक्ट नहीं करता है। लाइब्रेरियन हमारे चंक्ड अपलोड API और S3 मल्टीपार्ट ऑपरेशंस के बीच आंतरिक रूप से अनुवाद करता है।

### लाइब्रेरियन API ऑपरेशन
### लाइब्रेरियन एपीआई ऑपरेशन

#### `begin-upload`

एक खंडित अपलोड सत्र शुरू करें।

अनुरोध:
```json
{
  "operation": "begin-upload",
  "document-metadata": {
    "id": "doc-123",
    "kind": "application/pdf",
    "title": "Large Document",
    "user": "user-id",
    "tags": ["tag1", "tag2"]
  },
  "total-size": 524288000,
  "chunk-size": 5242880
}
```

प्रतिक्रिया:
```json
{
  "upload-id": "upload-abc-123",
  "chunk-size": 5242880,
  "total-chunks": 100
}
```

लाइब्रेरियन:
1. एक अद्वितीय `upload_id` और `object_id` उत्पन्न करता है (ब्लॉब स्टोरेज के लिए UUID)।
2. S3 `CreateMultipartUpload` को कॉल करता है, `s3_upload_id` प्राप्त करता है।
3. कैसेंड्रा में सत्र रिकॉर्ड बनाता है।
4. `upload_id` को क्लाइंट को वापस करता है।

#### `upload-chunk`

एक सिंगल चंक अपलोड करें।

अनुरोध:
```json
{
  "operation": "upload-chunk",
  "upload-id": "upload-abc-123",
  "chunk-index": 0,
  "content": "<base64-encoded-chunk>"
}
```

प्रतिक्रिया:
```json
{
  "upload-id": "upload-abc-123",
  "chunk-index": 0,
  "chunks-received": 1,
  "total-chunks": 100,
  "bytes-received": 5242880,
  "total-bytes": 524288000
}
```

लाइब्रेरियन:
1. `upload_id` द्वारा सत्र खोजें।
2. स्वामित्व की पुष्टि करें (उपयोगकर्ता को सत्र निर्माता से मेल खाना चाहिए)।
3. चंक डेटा के साथ S3 `UploadPart` को कॉल करें, `etag` प्राप्त करें।
4. चंक इंडेक्स और ईटैग के साथ सत्र रिकॉर्ड को अपडेट करें।
5. क्लाइंट को प्रगति वापस करें।

विफल चंक्स को फिर से प्रयास किया जा सकता है - बस उसी `chunk-index` को फिर से भेजें।

#### `complete-upload`

अपलोड को अंतिम रूप दें और दस्तावेज़ बनाएं।

अनुरोध:
```json
{
  "operation": "complete-upload",
  "upload-id": "upload-abc-123"
}
```

प्रतिक्रिया:
```json
{
  "document-id": "doc-123",
  "object-id": "550e8400-e29b-41d4-a716-446655440000"
}
```

लाइब्रेरियन:
1. सत्र की जांच करता है, यह सुनिश्चित करता है कि सभी भाग प्राप्त हो गए हैं।
2. पार्ट एटाग्स के साथ S3 `CompleteMultipartUpload` को कॉल करता है (S3 आंतरिक रूप से भागों को संयोजित करता है - लाइब्रेरियन के लिए शून्य मेमोरी लागत)।
   3. मेटाडेटा और ऑब्जेक्ट संदर्भ के साथ कैसेंड्रा में दस्तावेज़ रिकॉर्ड बनाता है।
4. अपलोड सत्र रिकॉर्ड को हटाता है।
5. क्लाइंट को दस्तावेज़ आईडी वापस करता है।
6.

#### `abort-upload`

एक चल रहे अपलोड को रद्द करें।

अनुरोध:
```json
{
  "operation": "abort-upload",
  "upload-id": "upload-abc-123"
}
```

लाइब्रेरियन:
1. एस3 `AbortMultipartUpload` को भागों को साफ़ करने के लिए कॉल करता है।
2. कैसेंड्रा से सत्र रिकॉर्ड को हटाता है।

#### `get-upload-status`

अपलोड की स्थिति की जांच करें (रिज़्यूम क्षमता के लिए)।

अनुरोध:
```json
{
  "operation": "get-upload-status",
  "upload-id": "upload-abc-123"
}
```

प्रतिक्रिया:
```json
{
  "upload-id": "upload-abc-123",
  "state": "in-progress",
  "chunks-received": [0, 1, 2, 5, 6],
  "missing-chunks": [3, 4, 7, 8],
  "total-chunks": 100,
  "bytes-received": 36700160,
  "total-bytes": 524288000
}
```

#### `list-uploads`

किसी उपयोगकर्ता के लिए अपूर्ण अपलोड की सूची प्राप्त करें।

अनुरोध:
```json
{
  "operation": "list-uploads"
}
```

प्रतिक्रिया:
```json
{
  "uploads": [
    {
      "upload-id": "upload-abc-123",
      "document-metadata": { "title": "Large Document", ... },
      "progress": { "chunks-received": 43, "total-chunks": 100 },
      "created-at": "2024-01-15T10:30:00Z"
    }
  ]
}
```

### अपलोड सेशन स्टोरेज

कैसेंड्रा में चल रहे अपलोड को ट्रैक करें:

```sql
CREATE TABLE upload_session (
    upload_id text PRIMARY KEY,
    user text,
    document_id text,
    document_metadata text,      -- JSON: title, kind, tags, comments, etc.
    s3_upload_id text,           -- internal, for S3 operations
    object_id uuid,              -- target blob ID
    total_size bigint,
    chunk_size int,
    total_chunks int,
    chunks_received map<int, text>,  -- chunk_index → etag
    created_at timestamp,
    updated_at timestamp
) WITH default_time_to_live = 86400;  -- 24 hour TTL

CREATE INDEX upload_session_user ON upload_session (user);
```

**टीटीएल व्यवहार:**
सत्र 24 घंटे के बाद समाप्त हो जाते हैं यदि वे पूरे नहीं होते हैं।
जब कैसेंड्रा टीटीएल समाप्त होता है, तो सत्र रिकॉर्ड हटा दिया जाता है।
अनाथ एस3 भाग को एस3 लाइफसाइकिल नीति द्वारा साफ़ किया जाता है (बकेट पर कॉन्फ़िगर करें)।

### विफलता प्रबंधन और परमाणुता

**चंक अपलोड विफलता:**
क्लाइंट विफल चंक को फिर से प्रयास करता है (समान `upload_id` और `chunk-index`)।
एस3 `UploadPart` समान भाग संख्या के लिए अपरिवर्तनीय है।
सत्र ट्रैक करता है कि कौन से चंक सफल हुए।

**क्लाइंट अपलोड के दौरान डिस्कनेक्ट हो जाता है:**
प्राप्त चंक के साथ सत्र कैसेंड्रा में बना रहता है।
क्लाइंट यह देखने के लिए `get-upload-status` को कॉल कर सकता है कि क्या गायब है।
केवल गायब चंक अपलोड करके फिर से शुरू करें, फिर `complete-upload`।

**पूर्ण-अपलोड विफलता:**
एस3 `CompleteMultipartUpload` परमाणु है - या तो यह पूरी तरह से सफल होता है या विफल रहता है।
विफलता पर, भाग बने रहते हैं और क्लाइंट `complete-upload` को फिर से प्रयास कर सकता है।
कोई आंशिक दस्तावेज़ कभी भी दिखाई नहीं देता है।

**सेशन समाप्ति:**
कैसेंड्रा TTL 24 घंटे बाद सेशन रिकॉर्ड को हटा देता है।
S3 बकेट लाइफसाइकिल पॉलिसी अधूरी मल्टीपार्ट अपलोड को साफ़ करती है।
कोई मैनुअल सफाई की आवश्यकता नहीं है।

### S3 मल्टीपार्ट एटॉमिकिटी

S3 मल्टीपार्ट अपलोड अंतर्निहित एटॉमिकिटी प्रदान करते हैं:

1. **भाग अदृश्य होते हैं**: अपलोड किए गए भागों को ऑब्जेक्ट के रूप में एक्सेस नहीं किया जा सकता है।
   वे केवल एक अधूरी मल्टीपार्ट अपलोड के हिस्से के रूप में मौजूद होते हैं।

2. **पूर्णता (Atomic completion)**: `CompleteMultipartUpload` या तो सफल होता है (वस्तु परमाणु रूप से दिखाई देती है) या विफल होता है (कोई वस्तु नहीं बनाई जाती है)। कोई आंशिक स्थिति नहीं।
   
3. **नाम बदलने की आवश्यकता नहीं**: अंतिम वस्तु कुंजी ⟦CODE_0⟧ समय पर निर्दिष्ट की जाती है। भाग सीधे उस कुंजी पर संयोजित होते हैं।

   `CreateMultipartUpload` समय। भाग सीधे उस कुंजी में संयोजित किए जाते हैं।

4. **सर्वर-साइड कोएलेसेंस (Server-side coalesce)**: S3 आंतरिक रूप से भागों को जोड़ता है। लाइब्रेरियन
   कभी भी भागों को वापस नहीं पढ़ता है - दस्तावेज़ के आकार की परवाह किए बिना शून्य मेमोरी ओवरहेड।

### ब्लबस्टोर एक्सटेंशन (BlobStore Extensions)

**फ़ाइल:** `trustgraph-flow/trustgraph/librarian/blob_store.py`

मल्टीपार्ट अपलोड विधियों को जोड़ें:

```python
class BlobStore:
    # Existing methods...

    def create_multipart_upload(self, object_id: UUID, kind: str) -> str:
        """Initialize multipart upload, return s3_upload_id."""
        # minio client: create_multipart_upload()

    def upload_part(
        self, object_id: UUID, s3_upload_id: str,
        part_number: int, data: bytes
    ) -> str:
        """Upload a single part, return etag."""
        # minio client: upload_part()
        # Note: S3 part numbers are 1-indexed

    def complete_multipart_upload(
        self, object_id: UUID, s3_upload_id: str,
        parts: List[Tuple[int, str]]  # [(part_number, etag), ...]
    ) -> None:
        """Finalize multipart upload."""
        # minio client: complete_multipart_upload()

    def abort_multipart_upload(
        self, object_id: UUID, s3_upload_id: str
    ) -> None:
        """Cancel multipart upload, clean up parts."""
        # minio client: abort_multipart_upload()
```

### चंक आकार (Chunk Size) पर विचार

**S3 न्यूनतम**: प्रति भाग 5MB (अंतिम भाग को छोड़कर)
**S3 अधिकतम**: प्रति अपलोड 10,000 भाग
**व्यावहारिक डिफ़ॉल्ट**: 5MB के चंक
  500MB का दस्तावेज़ = 100 चंक
  5GB का दस्तावेज़ = 1,000 चंक
**प्रगति की सूक्ष्मता**: छोटे चंक = अधिक सटीक प्रगति अपडेट
**नेटवर्क दक्षता**: बड़े चंक = कम राउंड ट्रिप

चंक का आकार (5MB - 100MB) की सीमा के भीतर क्लाइंट द्वारा कॉन्फ़िगर किया जा सकता है।

### दस्तावेज़ प्रसंस्करण: स्ट्रीमिंग पुनर्प्राप्ति

अपलोड प्रवाह भंडारण में दस्तावेजों को कुशलतापूर्वक लाने के लिए है। प्रसंस्करण प्रवाह दस्तावेजों को पूरी तरह से मेमोरी में लोड किए बिना, उन्हें निकालने और चंक में विभाजित करने के लिए है।

#### डिज़ाइन सिद्धांत: पहचानकर्ता, सामग्री नहीं

वर्तमान में, जब प्रसंस्करण शुरू होता है, तो दस्तावेज़ सामग्री पल्सर संदेशों के माध्यम से प्रवाहित होती है। इससे पूरे दस्तावेज़ मेमोरी में लोड हो जाते हैं। इसके बजाय:

पल्सर संदेश केवल **दस्तावेज़ पहचानकर्ता** ले जाते हैं
प्रोसेसर सीधे लाइब्रेरियन से दस्तावेज़ सामग्री प्राप्त करते हैं
पुनर्प्राप्ति एक **अस्थायी फ़ाइल में स्ट्रीम** के रूप में होती है
दस्तावेज़-विशिष्ट पार्सिंग (PDF, टेक्स्ट, आदि) फ़ाइलों के साथ काम करते हैं, मेमोरी बफ़र्स के साथ नहीं

यह लाइब्रेरियन को दस्तावेज़-संरचना-अज्ञेयवादी रखता है। PDF पार्सिंग, टेक्स्ट
निष्कर्षण और अन्य प्रारूप-विशिष्ट तर्क संबंधित डिकोडर में रहते हैं।

#### प्रसंस्करण प्रवाह


#### प्रसंस्करण प्रवाह

```
Pulsar              PDF Decoder                Librarian              S3
  │                      │                          │                  │
  │── doc-id ───────────►│                          │                  │
  │  (processing msg)    │                          │                  │
  │                      │                          │                  │
  │                      │── stream-document ──────►│                  │
  │                      │   (doc-id)               │── GetObject ────►│
  │                      │                          │                  │
  │                      │◄── chunk ────────────────│◄── stream ───────│
  │                      │   (write to temp file)   │                  │
  │                      │◄── chunk ────────────────│◄── stream ───────│
  │                      │   (append to temp file)  │                  │
  │                      │         ⋮                │         ⋮        │
  │                      │◄── EOF ──────────────────│                  │
  │                      │                          │                  │
  │                      │   ┌──────────────────────────┐              │
  │                      │   │ temp file on disk        │              │
  │                      │   │ (memory stays bounded)   │              │
  │                      │   └────────────┬─────────────┘              │
  │                      │                │                            │
  │                      │   PDF library opens file                    │
  │                      │   extract page 1 text ──►  chunker          │
  │                      │   extract page 2 text ──►  chunker          │
  │                      │         ⋮                                   │
  │                      │   close file                                │
  │                      │   delete temp file                          │
```

#### लाइब्रेरियन स्ट्रीम एपीआई

एक स्ट्रीमिंग दस्तावेज़ पुनर्प्राप्ति ऑपरेशन जोड़ें:

**`stream-document`**

अनुरोध:
```json
{
  "operation": "stream-document",
  "document-id": "doc-123"
}
```

प्रतिक्रिया: स्ट्रीम किए गए बाइनरी खंड (एकल प्रतिक्रिया नहीं)।

REST API के लिए, यह `Transfer-Encoding: chunked` के साथ एक स्ट्रीमिंग प्रतिक्रिया लौटाता है।

आंतरिक सेवा-से-सेवा कॉल के लिए (प्रोसेसर से लाइब्रेरियन तक), यह हो सकता है:
सीधे प्रीसाइंड URL के माध्यम से S3 स्ट्रीमिंग (यदि आंतरिक नेटवर्क अनुमति देता है)
सेवा प्रोटोकॉल पर खंडित प्रतिक्रियाएं
एक समर्पित स्ट्रीमिंग एंडपॉइंट

मुख्य आवश्यकता: डेटा खंडों में प्रवाहित होता है, और कभी भी पूरी तरह से लाइब्रेरियन में बफर नहीं होता है।

#### PDF डिकोडर परिवर्तन

**वर्तमान कार्यान्वयन** (मेमोरी-गहन):

```python
def decode_pdf(document_content: bytes) -> str:
    reader = PdfReader(BytesIO(document_content))  # full doc in memory
    text = ""
    for page in reader.pages:
        text += page.extract_text()  # accumulating
    return text  # full text in memory
```

**नया कार्यान्वयन** (अस्थायी फ़ाइल, क्रमिक):

```python
def decode_pdf_streaming(doc_id: str, librarian_client) -> Iterator[str]:
    """Yield extracted text page by page."""

    with tempfile.NamedTemporaryFile(delete=True, suffix='.pdf') as tmp:
        # Stream document to temp file
        for chunk in librarian_client.stream_document(doc_id):
            tmp.write(chunk)
        tmp.flush()

        # Open PDF from file (not memory)
        reader = PdfReader(tmp.name)

        # Yield pages incrementally
        for page in reader.pages:
            yield page.extract_text()

        # tmp file auto-deleted on context exit
```

मेमोरी प्रोफाइल:
अस्थायी फ़ाइल डिस्क पर: पीडीएफ का आकार (डिस्क सस्ती है)
मेमोरी में: एक बार में एक पृष्ठ का टेक्स्ट
अधिकतम मेमोरी: सीमित, दस्तावेज़ के आकार से स्वतंत्र

#### टेक्स्ट डॉक्यूमेंट डिकोडर में बदलाव

सादे टेक्स्ट दस्तावेज़ों के लिए, और भी सरल - किसी अस्थायी फ़ाइल की आवश्यकता नहीं:

```python
def decode_text_streaming(doc_id: str, librarian_client) -> Iterator[str]:
    """Yield text in chunks as it streams from storage."""

    buffer = ""
    for chunk in librarian_client.stream_document(doc_id):
        buffer += chunk.decode('utf-8')

        # Yield complete lines/paragraphs as they arrive
        while '\n\n' in buffer:
            paragraph, buffer = buffer.split('\n\n', 1)
            yield paragraph + '\n\n'

    # Yield remaining buffer
    if buffer:
        yield buffer
```

टेक्स्ट दस्तावेज़ सीधे अस्थायी फ़ाइल के बिना स्ट्रीम किए जा सकते हैं क्योंकि वे
रैखिक रूप से संरचित होते हैं।

#### स्ट्रीमिंग चंकर एकीकरण

चंकर टेक्स्ट (पृष्ठों या पैराग्राफों) का एक इटरेटर प्राप्त करता है और क्रमिक रूप से
चंक्स उत्पन्न करता है:

```python
class StreamingChunker:
    def __init__(self, chunk_size: int, overlap: int):
        self.chunk_size = chunk_size
        self.overlap = overlap

    def process(self, text_stream: Iterator[str]) -> Iterator[str]:
        """Yield chunks as text arrives."""
        buffer = ""

        for text_segment in text_stream:
            buffer += text_segment

            while len(buffer) >= self.chunk_size:
                chunk = buffer[:self.chunk_size]
                yield chunk
                # Keep overlap for context continuity
                buffer = buffer[self.chunk_size - self.overlap:]

        # Yield remaining buffer as final chunk
        if buffer.strip():
            yield buffer
```

#### एंड-टू-एंड प्रोसेसिंग पाइपलाइन

```python
async def process_document(doc_id: str, librarian_client, embedder):
    """Process document with bounded memory."""

    # Get document metadata to determine type
    metadata = await librarian_client.get_document_metadata(doc_id)

    # Select decoder based on document type
    if metadata.kind == 'application/pdf':
        text_stream = decode_pdf_streaming(doc_id, librarian_client)
    elif metadata.kind == 'text/plain':
        text_stream = decode_text_streaming(doc_id, librarian_client)
    else:
        raise UnsupportedDocumentType(metadata.kind)

    # Chunk incrementally
    chunker = StreamingChunker(chunk_size=1000, overlap=100)

    # Process each chunk as it's produced
    for chunk in chunker.process(text_stream):
        # Generate embeddings, store in vector DB, etc.
        embedding = await embedder.embed(chunk)
        await store_chunk(doc_id, chunk, embedding)
```

किसी भी समय, संपूर्ण दस्तावेज़ या संपूर्ण निकाले गए पाठ को मेमोरी में संग्रहीत नहीं किया जाता है।

#### अस्थायी फ़ाइल संबंधी विचार

**स्थान:** सिस्टम के अस्थायी फ़ोल्डर का उपयोग करें (`/tmp` या समकक्ष)। कंटेनरयुक्त परिनियोजन के लिए, सुनिश्चित करें कि अस्थायी फ़ोल्डर में पर्याप्त जगह है
और यह तेज़ स्टोरेज पर है (यदि संभव हो तो नेटवर्क-माउंटेड नहीं)।


**सफाई:** सफाई सुनिश्चित करने के लिए संदर्भ प्रबंधकों (`with tempfile...`) का उपयोग करें
यहां तक कि अपवादों पर भी।

**समवर्ती प्रसंस्करण:** प्रत्येक प्रसंस्करण कार्य का अपना अस्थायी फ़ाइल होता है।
समानांतर दस्तावेज़ प्रसंस्करण के बीच कोई टकराव नहीं होता है।

**डिस्क स्पेस**: अस्थायी फ़ाइलें अल्पकालिक होती हैं (प्रोसेसिंग की अवधि)।
500MB के PDF के लिए, प्रोसेसिंग के दौरान 500MB अस्थायी स्थान की आवश्यकता होती है। यदि डिस्क स्पेस सीमित है, तो आकार सीमा अपलोड के समय लागू की जा सकती है।


### एकीकृत प्रोसेसिंग इंटरफ़ेस: चाइल्ड दस्तावेज़

PDF निष्कर्षण और टेक्स्ट दस्तावेज़ प्रोसेसिंग को एक ही
डाउनस्ट्रीम पाइपलाइन (चंकर → एम्बेडिंग → स्टोरेज) में फीड करने की आवश्यकता है। इसे एक सुसंगत "आईडी द्वारा प्राप्त करें" इंटरफ़ेस के साथ प्राप्त करने के लिए, निकाले गए टेक्स्ट ब्लॉकों को "चाइल्ड दस्तावेज़" के रूप में लाइब्रेरियन में वापस संग्रहीत किया जाता है।



#### चाइल्ड दस्तावेज़ों के साथ प्रोसेसिंग प्रवाह

```
PDF Document                                         Text Document
     │                                                     │
     ▼                                                     │
pdf-extractor                                              │
     │                                                     │
     │ (stream PDF from librarian)                         │
     │ (extract page 1 text)                               │
     │ (store as child doc → librarian)                    │
     │ (extract page 2 text)                               │
     │ (store as child doc → librarian)                    │
     │         ⋮                                           │
     ▼                                                     ▼
[child-doc-id, child-doc-id, ...]                    [doc-id]
     │                                                     │
     └─────────────────────┬───────────────────────────────┘
                           ▼
                       chunker
                           │
                           │ (receives document ID)
                           │ (streams content from librarian)
                           │ (chunks incrementally)
                           ▼
                    [chunks → embedding → storage]
```

चंकर (chunker) में एक समान इंटरफ़ेस है:
एक दस्तावेज़ आईडी प्राप्त करें (पल्सर के माध्यम से)
लाइब्रेरियन से सामग्री स्ट्रीम करें
इसे छोटे भागों में विभाजित करें

यह नहीं जानता या परवाह नहीं करता कि आईडी किस चीज़ को संदर्भित करती है:
एक उपयोगकर्ता द्वारा अपलोड किया गया टेक्स्ट दस्तावेज़
एक पीडीएफ पृष्ठ से निकाला गया टेक्स्ट ब्लॉक
कोई भी भविष्य का दस्तावेज़ प्रकार

#### चाइल्ड दस्तावेज़ मेटाडेटा

दस्तावेज़ स्कीमा को पैरेंट/चाइल्ड संबंधों को ट्रैक करने के लिए विस्तारित करें:

```sql
-- Add columns to document table
ALTER TABLE document ADD parent_id text;
ALTER TABLE document ADD document_type text;

-- Index for finding children of a parent
CREATE INDEX document_parent ON document (parent_id);
```

**दस्तावेज़ के प्रकार:**

| `document_type` | विवरण |
|-----------------|-------------|
| `source` | उपयोगकर्ता द्वारा अपलोड किया गया दस्तावेज़ (पीडीएफ, टेक्स्ट, आदि) |
| `extracted` | स्रोत दस्तावेज़ से प्राप्त (उदाहरण के लिए, पीडीएफ पृष्ठ पाठ) |

**मेटाडेटा फ़ील्ड:**

| फ़ील्ड | स्रोत दस्तावेज़ | निकाली गई चाइल्ड |
|-------|-----------------|-----------------|
| `id` | उपयोगकर्ता द्वारा प्रदान किया गया या उत्पन्न | उत्पन्न (उदाहरण के लिए, `{parent-id}-page-{n}`) |
| `parent_id` | `NULL` | मूल दस्तावेज़ आईडी |
| `document_type` | `source` | `extracted` |
| `kind` | `application/pdf`, आदि | `text/plain` |
| `title` | उपयोगकर्ता द्वारा प्रदान किया गया | उत्पन्न (उदाहरण के लिए, "रिपोर्ट.pdf का पृष्ठ 3") |
| `user` | प्रमाणित उपयोगकर्ता | मूल के समान |

#### चाइल्ड दस्तावेज़ों के लिए लाइब्रेरियन एपीआई

**चाइल्ड दस्तावेज़ बनाना** (आंतरिक, pdf-extractor द्वारा उपयोग किया जाता है):

```json
{
  "operation": "add-child-document",
  "parent-id": "doc-123",
  "document-metadata": {
    "id": "doc-123-page-1",
    "kind": "text/plain",
    "title": "Page 1"
  },
  "content": "<base64-encoded-text>"
}
```

छोटे, निकाले गए टेक्स्ट के लिए (सामान्य पृष्ठ टेक्स्ट < 100KB है), सिंगल-ऑपरेशन अपलोड स्वीकार्य है। बहुत बड़े टेक्स्ट एक्सट्रैक्शन के लिए, चंक्ड अपलोड का उपयोग किया जा सकता है।

**चाइल्ड दस्तावेज़ों की सूची** (डीबगिंग/एडमिन के लिए):

**चाइल्ड दस्तावेज़ों की सूची** (डीबगिंग/प्रशासन के लिए):

```json
{
  "operation": "list-children",
  "parent-id": "doc-123"
}
```

प्रतिक्रिया:
```json
{
  "children": [
    { "id": "doc-123-page-1", "title": "Page 1", "kind": "text/plain" },
    { "id": "doc-123-page-2", "title": "Page 2", "kind": "text/plain" },
    ...
  ]
}
```

#### उपयोगकर्ता-सामना करने वाला व्यवहार

**`list-documents` डिफ़ॉल्ट व्यवहार:**

```sql
SELECT * FROM document WHERE user = ? AND parent_id IS NULL;
```

केवल शीर्ष-स्तरीय (मूल) दस्तावेज़ ही उपयोगकर्ता की दस्तावेज़ सूची में दिखाई देते हैं।
चाइल्ड दस्तावेज़ डिफ़ॉल्ट रूप से फ़िल्टर कर दिए जाते हैं।

**वैकल्पिक 'शामिल-चाइल्ड' फ़्लैग** (व्यवस्थापक/डीबगिंग के लिए):

```json
{
  "operation": "list-documents",
  "include-children": true
}
```

#### कैस्केड डिलीट

जब कोई पैरेंट दस्तावेज़ हटाया जाता है, तो सभी चाइल्ड दस्तावेज़ों को भी हटाया जाना चाहिए:

```python
def delete_document(doc_id: str):
    # Find all children
    children = query("SELECT id, object_id FROM document WHERE parent_id = ?", doc_id)

    # Delete child blobs from S3
    for child in children:
        blob_store.delete(child.object_id)

    # Delete child metadata from Cassandra
    execute("DELETE FROM document WHERE parent_id = ?", doc_id)

    # Delete parent blob and metadata
    parent = get_document(doc_id)
    blob_store.delete(parent.object_id)
    execute("DELETE FROM document WHERE id = ? AND user = ?", doc_id, user)
```

#### भंडारण संबंधी विचार

निकाले गए टेक्स्ट ब्लॉक डुप्लिकेट सामग्री बनाते हैं:
मूल पीडीएफ "गैराज" में संग्रहीत है।
प्रत्येक पृष्ठ के लिए निकाला गया टेक्स्ट भी "गैराज" में संग्रहीत है।

यह समझौता निम्नलिखित को सक्षम बनाता है:
**समान चंकर इंटरफ़ेस**: चंकर हमेशा आईडी द्वारा डेटा प्राप्त करता है।
**फिर से शुरू/पुनः प्रयास**: पीडीएफ को फिर से निकालने के बिना, चंकर चरण पर पुनः आरंभ किया जा सकता है।
**डीबगिंग**: निकाले गए टेक्स्ट का निरीक्षण किया जा सकता है।
**चिंताओं का पृथक्करण**: पीडीएफ एक्सट्रैक्टर और चंकर स्वतंत्र सेवाएं हैं।

500 एमबी के पीडीएफ में 200 पृष्ठ हैं, जिनमें से प्रत्येक पृष्ठ पर औसतन 5 केबी टेक्स्ट है:
पीडीएफ भंडारण: 500 एमबी
निकाले गए टेक्स्ट भंडारण: लगभग 1 एमबी
अतिरिक्त भार: नगण्य

#### पीडीएफ एक्सट्रैक्टर आउटपुट

पीडीएफ-एक्सट्रैक्टर, किसी दस्तावेज़ को संसाधित करने के बाद:

1. पीडीएफ को लाइब्रेरियन से अस्थायी फ़ाइल में स्ट्रीम करता है।
2. पृष्ठ दर पृष्ठ टेक्स्ट निकालता है।
3. प्रत्येक पृष्ठ के लिए, निकाले गए टेक्स्ट को लाइब्रेरियन के माध्यम से एक चाइल्ड दस्तावेज़ के रूप में संग्रहीत करता है।
4. चाइल्ड दस्तावेज़ आईडी को चंकर कतार में भेजता है।

```python
async def extract_pdf(doc_id: str, librarian_client, output_queue):
    """Extract PDF pages and store as child documents."""

    with tempfile.NamedTemporaryFile(delete=True, suffix='.pdf') as tmp:
        # Stream PDF to temp file
        for chunk in librarian_client.stream_document(doc_id):
            tmp.write(chunk)
        tmp.flush()

        # Extract pages
        reader = PdfReader(tmp.name)
        for page_num, page in enumerate(reader.pages, start=1):
            text = page.extract_text()

            # Store as child document
            child_id = f"{doc_id}-page-{page_num}"
            await librarian_client.add_child_document(
                parent_id=doc_id,
                document_id=child_id,
                kind="text/plain",
                title=f"Page {page_num}",
                content=text.encode('utf-8')
            )

            # Send to chunker queue
            await output_queue.send(child_id)
```

चंकर इन चाइल्ड आईडी को प्राप्त करता है और उन्हें उसी तरह संसाधित करता है जैसे कि वह किसी उपयोगकर्ता द्वारा अपलोड किए गए टेक्स्ट दस्तावेज़ को संसाधित करता है।
चंकर इन चाइल्ड आईडी को प्राप्त करता है और उन्हें उसी तरह संसाधित करता है जैसे कि वह किसी उपयोगकर्ता द्वारा अपलोड किए गए टेक्स्ट दस्तावेज़ को संसाधित करता है।

### क्लाइंट अपडेट

#### पायथन एसडीके

पायथन एसडीके (`trustgraph-base/trustgraph/api/library.py`) को खंडित अपलोड को पारदर्शी रूप से संभालना चाहिए। सार्वजनिक इंटरफ़ेस अपरिवर्तित रहता है:
खंडित अपलोड को पारदर्शी रूप से संभालना चाहिए। सार्वजनिक इंटरफ़ेस अपरिवर्तित रहता है:

```python
# Existing interface - no change for users
library.add_document(
    id="doc-123",
    title="Large Report",
    kind="application/pdf",
    content=large_pdf_bytes,  # Can be hundreds of MB
    tags=["reports"]
)
```

आंतरिक रूप से, SDK दस्तावेज़ के आकार का पता लगाता है और रणनीति बदलता है:

```python
class Library:
    CHUNKED_UPLOAD_THRESHOLD = 2 * 1024 * 1024  # 2MB

    def add_document(self, id, title, kind, content, tags=None, ...):
        if len(content) < self.CHUNKED_UPLOAD_THRESHOLD:
            # Small document: single operation (existing behavior)
            return self._add_document_single(id, title, kind, content, tags)
        else:
            # Large document: chunked upload
            return self._add_document_chunked(id, title, kind, content, tags)

    def _add_document_chunked(self, id, title, kind, content, tags):
        # 1. begin-upload
        session = self._begin_upload(
            document_metadata={...},
            total_size=len(content),
            chunk_size=5 * 1024 * 1024
        )

        # 2. upload-chunk for each chunk
        for i, chunk in enumerate(self._chunk_bytes(content, session.chunk_size)):
            self._upload_chunk(session.upload_id, i, chunk)

        # 3. complete-upload
        return self._complete_upload(session.upload_id)
```

**प्रगति कॉलबैक** (वैकल्पिक संवर्द्धन):

```python
def add_document(self, ..., on_progress=None):
    """
    on_progress: Optional callback(bytes_sent, total_bytes)
    """
```

यह यूआई को बुनियादी एपीआई को बदले बिना अपलोड की प्रगति प्रदर्शित करने की अनुमति देता है।

#### कमांड लाइन उपकरण

**`tg-add-library-document`** बिना किसी बदलाव के काम करता रहता है:

```bash
# Works transparently for any size - SDK handles chunking internally
tg-add-library-document --file large-report.pdf --title "Large Report"
```

वैकल्पिक प्रगति प्रदर्शन जोड़ा जा सकता है:

```bash
tg-add-library-document --file large-report.pdf --title "Large Report" --progress
# Output:
# Uploading: 45% (225MB / 500MB)
```

**पुराने उपकरण हटा दिए गए:**

`tg-load-pdf` - अप्रचलित, `tg-add-library-document` का उपयोग करें।
`tg-load-text` - अप्रचलित, `tg-add-library-document` का उपयोग करें।

**व्यवस्थापक/डीबग कमांड** (वैकल्पिक, कम प्राथमिकता):

```bash
# List incomplete uploads (admin troubleshooting)
tg-add-library-document --list-pending

# Resume specific upload (recovery scenario)
tg-add-library-document --resume upload-abc-123 --file large-report.pdf
```

ये मौजूदा कमांड पर मौजूद फ़्लैग हो सकते हैं, अलग-अलग टूल नहीं।

#### एपीआई विनिर्देश अपडेट

OpenAPI विनिर्देश (`specs/api/paths/librarian.yaml`) को निम्नलिखित के लिए अपडेट करने की आवश्यकता है:

**नए ऑपरेशन:**

`begin-upload` - चंक्ड अपलोड सत्र को आरंभ करें
`upload-chunk` - व्यक्तिगत चंक अपलोड करें
`complete-upload` - अपलोड को अंतिम रूप दें
`abort-upload` - अपलोड को रद्द करें
`get-upload-status` - अपलोड की प्रगति की जांच करें
`list-uploads` - उपयोगकर्ता के लिए अपूर्ण अपलोड की सूची बनाएं
`stream-document` - दस्तावेज़ पुनर्प्राप्ति (स्ट्रीमिंग)
`add-child-document` - निकाले गए पाठ को संग्रहीत करें (आंतरिक)
`list-children` - चाइल्ड दस्तावेज़ों की सूची बनाएं (व्यवस्थापक)

**संशोधित ऑपरेशन:**

`list-documents` - `include-children` पैरामीटर जोड़ें

**नए स्कीमा:**

`ChunkedUploadBeginRequest`
`ChunkedUploadBeginResponse`
`ChunkedUploadChunkRequest`
`ChunkedUploadChunkResponse`
`UploadSession`
`UploadProgress`

**WebSocket विनिर्देश अपडेट** (`specs/websocket/`):

WebSocket क्लाइंट के लिए REST ऑपरेशन को प्रतिबिंबित करें, जिससे अपलोड के दौरान वास्तविक समय
प्रगति अपडेट सक्षम हो सके।

#### यूएक्स विचार

एपीआई विनिर्देश अपडेट फ्रंटएंड में सुधारों को सक्षम करते हैं:

**अपलोड प्रगति यूआई:**
अपलोड किए गए चंक्स को दिखाने वाला प्रगति बार
अनुमानित शेष समय
पॉज़/रीज़्यूम क्षमता

**त्रुटि सुधार:**
बाधित अपलोड के लिए "अपलोड फिर से शुरू करें" विकल्प
पुनः कनेक्ट करने पर लंबित अपलोड की सूची

**बड़ी फ़ाइल हैंडलिंग:**
क्लाइंट-साइड फ़ाइल आकार का पता लगाना
बड़ी फ़ाइलों के लिए स्वचालित चंक्ड अपलोड
लंबे अपलोड के दौरान स्पष्ट प्रतिक्रिया

ये यूएक्स सुधार अपडेट किए गए एपीआई विनिर्देश द्वारा निर्देशित फ्रंटएंड कार्य की आवश्यकता है।
