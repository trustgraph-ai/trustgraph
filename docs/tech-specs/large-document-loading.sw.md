---
layout: default
title: "Vipimo vya Utekelezaji wa Teknolojia ya Kupakia Hati Kubwa"
parent: "Swahili (Beta)"
---

<<<<<<< HEAD
# Vipimo vya Utekelezaji wa Teknolojia ya Kupakia Hati Kubwa

> **Beta Translation:** This document was translated via Machine Learning and as such may not be 100% accurate. All non-English languages are currently classified as Beta.

## Muhtasari

Maelekezo haya yanaeleza masuala ya uwezo wa kufanya kazi na uzoefu wa mtumiaji wakati wa kupakia
hati kubwa katika TrustGraph. Muundo wa sasa hutumia kupakia hati kama operesheni moja, na kusababisha
shinikizo la kumbukumbu katika hatua nyingi za mchakato na kutoa maelezo au chaguo za kurejesha kwa watumiaji.


Utaratibu huu unalenga matumizi yafuatayo:

1. **Uchakataji wa Hati za PDF Kubwa**: Kupakia na kuchakata faili za PDF zenye mamia ya megabytes
   bila kutumia kumbukumbu yote.
2. **Kupakia Ambayo Inaweza Kuendelea**: Kuruhusu kupakia ambacho kimetokea kukatika kuendelea kutoka
   ambapo kilisimama badala ya kuanza tena.
3. **Maelezo ya Maendeleo**: Kutoa kwa watumiaji maelezo ya muda halisi kuhusu maendeleo ya
   kupakia na uchakataji.
4. **Uchakataji Wenye Ufanisi wa Kumbukumbu**: Kuchakata hati kwa njia ya mtiririko
=======
# Vipimo vya Utekelezaji wa Uteuzi wa Hati Kubwa

## Muhtasari

Maelekezo haya yanaeleza masuala ya uwezo wa kutosha na uzoefu wa mtumiaji wakati wa kupakia
hati kubwa katika TrustGraph. Muundo wa sasa hutibu kupakia hati kama operesheni moja na kamili,
na kusababisha shinikizo la kumbukumbu katika sehemu nyingi za
mchakato na kutoa hakikisho au chaguo za urejesho kwa watumiaji.

Utendaji huu unalenga matumizi yafuatayo:

1. **Uchakataji wa PDF Kubwa**: Pakia na uchakata faili za PDF zenye mamia ya megabytes
   bila kutumia kumbukumbu.
2. **Uipakaji Unaoweza Kuendelea**: Ruhusu uipakaji ambao umevunjika kuendelea kutoka
   ambapo ulikuwa umeacha badala ya kuanza tena.
3. **Hakikisho la Maendeleo**: Toa watumiaji maoni ya wakati halisi kuhusu
   maendeleo ya uipakaji na uchakataji.
4. **Uchakataji Wenye Ufanisi wa Kumbukumbu**: Chakata hati kwa njia ya mtiririko
>>>>>>> 82edf2d (New md files from RunPod)
   bila kuhifadhi faili zilizokamilika katika kumbukumbu.

## Lengo

<<<<<<< HEAD
**Kupakia kwa Awamu**: Kusaidia kupakia hati kwa sehemu kupitia REST na WebSocket
**Uhamisho Unaoweza Kuendelea**: Kuruhusu kurejesha kutoka kupakia ambacho kimetokea kukatika
**Uonekana wa Maendeleo**: Kutoa maelezo ya maendeleo ya kupakia/uchakataji kwa wateja
**Ufanisi wa Kumbukumbu**: Kuondoa uhifadhi wa hati zilizokamilika katika mchakato wote
**Ulinganifu na Mifumo ya Zamani**: Mchakato wa sasa wa hati ndogo unaendelea bila mabadiliko
**Uchakataji wa Mtiririko**: Ufichuzi na uainishaji wa maandishi hufanywa kwa kutumia mitiririko
=======
**Uipakaji wa Hatua-Hatua**: Unga uipakaji wa hati kwa sehemu kupitia REST na WebSocket
**Uhamisho Unaoweza Kuendelea**: Ruhusu urejesho kutoka uipakaji ambao umevunjika
**Uonekana wa Maendeleo**: Toa watumiaji maoni ya maendeleo ya uipakaji/uchakataji
**Ufanisi wa Kumbukumbu**: Ondoa kuhifadhi hati zilizokamilika katika mchakato
**Ulinganifu na Mifumo ya Zamani**: Mchakato wa sasa wa hati ndogo unaendelea bila mabadiliko
**Uchakataji wa Mtiririko**: Uvunjaji wa PDF na maandishi hufanya kazi kwenye mitiririko
>>>>>>> 82edf2d (New md files from RunPod)

## Asili

### Muundo wa Sasa

<<<<<<< HEAD
Hati zinatumiwa kupitia njia ifuatayo:

1. **Mteja** hutuma hati kupitia REST (`POST /api/v1/librarian`) au WebSocket
2. **Lango la API** linapokea ombi kamili lenye maudhui ya hati yaliyokuzwa kwa msingi 64
3. **LibrarianRequestor** huongeza ombi kwenye ujumbe wa Pulsar
4. **Huduma ya Librarian** inapokea ujumbe, huondoa maudhui ya hati katika kumbukumbu
5. **BlobStore** huhamisha hati kwenye Garage/S3
6. **Cassandra** huhifadhi metadata pamoja na rejea ya kitu
7. Kwa uchakataji: hati inavyolewa kutoka S3, huondoa maudhui, huainishwa—yote katika kumbukumbu
=======
Mchakato wa kuwasilisha hati hufuatilia njia ifuatayo:

1. **Mteja** huwasilisha hati kupitia REST (`POST /api/v1/librarian`) au WebSocket
2. **Lango la API** hupokea ombi kamili na maudhui ya hati iliyosimbwa kwa base64
3. **LibrarianRequestor** huongeza ombi kwenye ujumbe wa Pulsar
4. **Huduma ya Librarian** hupokea ujumbe, huondoa usimbaji wa hati katika kumbukumbu
5. **BlobStore** huipakia hati kwenye Garage/S3
6. **Cassandra** huhifadhi metadata na rejea la kitu
7. Kwa uchakataji: hati hupelekwa kutoka S3, huondoa usimbaji, huainishwa—yote katika kumbukumbu
>>>>>>> 82edf2d (New md files from RunPod)

Faili muhimu:
Ingizo la REST/WebSocket: `trustgraph-flow/trustgraph/gateway/service.py`
Msingi wa Librarian: `trustgraph-flow/trustgraph/librarian/librarian.py`
Uhifadhi wa blob: `trustgraph-flow/trustgraph/librarian/blob_store.py`
Jedwali la Cassandra: `trustgraph-flow/trustgraph/tables/library.py`
Mpango wa API: `trustgraph-base/trustgraph/schema/services/library.py`

### Mapungufu ya Sasa

<<<<<<< HEAD
Muundo wa sasa una masuala kadhaa ambayo huathiri kumbukumbu na uzoefu wa mtumiaji:

1. **Operesheni ya Kupakia ya Atomiki**: Hati nzima lazima ihamishwe katika
   ombi moja. Hati kubwa zinahitaji ombi linalodumu kwa muda mrefu bila
   maelezo ya maendeleo na hakuna njia ya kujaribu tena ikiwa muunganisho utakatika.

2. **Muundo wa API**: API za REST na WebSocket zinatarajia hati
   nzima katika ujumbe mmoja. Mpango (`LibrarianRequest`) una `content`
   ambayo ina maudhui ya hati nzima yaliyokuzwa kwa msingi 64.

3. **Kumbukumbu ya Librarian**: Huduma ya librarian huondoa maudhui ya hati
   katika kumbukumbu kabla ya kuihamisha kwenye S3. Kwa PDF ya 500MB, hii inamaanisha
   kuhifadhi 500MB+ katika kumbukumbu ya mchakato.

4. **Kumbukumbu ya Kufichua PDF**: Wakati wa uchakataji, programu ya kufichua PDF
   huhamisha hati nzima katika kumbukumbu ili kuchimbua maandishi. Maktaba kama vile PyPDF
   zinaweza kuhitaji upataji wa hati nzima.

5. **Kumbukumbu ya Kifaa cha Kuchakata**: Kifaa cha kuchakata maandishi hupokea maandishi
   yaliyochimbuliwa na kuhifadhi katika kumbukumbu huku huchakata na kuunda sehemu.

**Mfano wa Athari ya Kumbukumbu** (PDF ya 500MB):
Lango: ~700MB (maudhui yaliyokuzwa)
Librarian: ~500MB (bytes zilizofichuliwa)
Kifaa cha Kufichua PDF: ~500MB + buffers za uchimbaji
Kifaa cha Kuchakata: maandishi yaliyochimbuliwa (hubadilika, inaweza kuwa 100MB+)
=======
Muundo wa sasa una masuala kadhaa yanayoathiri kumbukumbu na uzoefu wa mtumiaji:

1. **Operesheni ya Uipakaji Kamili**: Hati nzima lazima iwasilishwe katika
   ombi moja. Hati kubwa zinahitaji ombi linalodumu kwa muda mrefu bila
   hakikisho ya maendeleo na hakuna njia ya kujaribu tena ikiwa muunganisho utavunjika.

2. **Muundo wa API**: API za REST na WebSocket zinatarajia hati
   nzima katika ujumbe mmoja. Mpango (`LibrarianRequest`) una `content`
   sehemu inayohifadhi maudhui ya hati iliyosimbwa kwa base64.

3. **Kumbukumbu ya Librarian**: Huduma ya librarian huondoa usimbaji wa hati
   nzima katika kumbukumbu kabla ya kuipeleka kwenye S3. Kwa PDF ya 500MB,
   hii inamaanisha kuhifadhi 500MB+ katika kumbukumbu ya programu.

4. **Kumbukumbu ya Dekoda ya PDF**: Wakati uchakataji unaanza, dekoda ya PDF
   hupakia hati nzima katika kumbukumbu ili kuchimbua maandishi. Maktabu kama
   PyPDF na zile kama hizo kawaida zinahitaji upataji wa hati nzima.

5. **Kumbukumbu ya Chunker**: Chunker hupokea maandishi yaliyochimbuliwa
   na kuhifadhi katika kumbukumbu huku inazalisha sehemu.

**Mfano wa Athari ya Kumbukumbu** (PDF ya 500MB):
Lango: ~700MB (ghairi ya usimbaji)
Librarian: ~500MB (bytes zilizopunguzwa)
Dekoda ya PDF: ~500MB + buffers za uchimbaji
Chunker: maandishi yaliyopatikana (hubadilika, inaweza kuwa 100MB+)
>>>>>>> 82edf2d (New md files from RunPod)

Kumbukumbu ya juu inaweza kuzidi 2GB kwa hati kubwa moja.

## Muundo wa Kiufundi

### Kanuni za Muundo

<<<<<<< HEAD
1. **Uhusiano wa API**: Mwingiliano wote wa mteja hupitia API ya librarian. Wateja
   hawana upataji wa moja kwa moja au kujua kuhusu uhifadhi wa S3/Garage.

2. **Kupakia kwa Sehemu ya S3**: Tumia kupakia kwa sehemu ya S3.
   Hii inasaidiwa kwa mfumo wowote unaolingana na S3 (AWS S3, MinIO, Garage,
   Ceph, DigitalOcean Spaces, Backblaze B2, n.k.) kuhakikisha uwezekano wa kuhamishwa.

3. **Kukamilika kwa Atomiki**: Kupakia kwa sehemu ya S3 kunaweza kukamilika kwa atomiki - sehemu
   zilizopakiwa hazionekani hadi `CompleteMultipartUpload` itakapopigwa.
   Hakuna faili za muda au operesheni za kubadilisha.

4. **Hali Inayoweza Kufuatiliwa**: Vipindi vya kupakia hufuatiliwa katika Cassandra, kutoa
   uonevu kuhusu kupakia ambacho hakikamilika na kuruhusu uwezo wa kuanza tena.

### Mchakato wa Kupakia kwa Sehemu
=======
1. **Kifurushi cha API**: Mwingiliano wote wa mteja hupitia API ya librarian. Wateja
   hawana upataji wa moja kwa moja au kujua kuhusu uhifadhi wa S3/Garage.

2. **Uipakaji wa Sehemu wa S3**: Tumia uipakaji wa sehemu wa S3.
   Hii inasaidiwa sana katika mifumo inayolingana na S3 (AWS S3, MinIO, Garage,
   Ceph, DigitalOcean Spaces, Backblaze B2, n.k.) kuhakikisha uwezekano wa kuhamishwa.

3. **Uhakikisho Kamili**: Uipakaji wa sehemu wa S3 ni wa uhakikisho kamili - sehemu
   zilizopakiwa hazionekani hadi `CompleteMultipartUpload` itakapopigwa.
   Hakuna faili za muda au operesheni za kubadilisha.

4. **Hali Inayoweza Kufuatiliwa**: Vipindi vya uipakaji hufuatiliwa katika Cassandra,
   kutoa uonevu kuhusu uipakaji usio kamili na kuwezesha uwezo wa kuanza tena.

### Mchakato wa Uipakaji wa Sehemu
>>>>>>> 82edf2d (New md files from RunPod)

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

Mteja hawezi kuwasiliana na S3 moja kwa moja. Msimamizi (librarian) hutafsiri kati ya
API yetu ya kupakia vipande na operesheni za S3 za sehemu nyingi (multipart) kwa ndani.

### Operesheni za API ya Msimamizi (Librarian)

#### `begin-upload`

Anzisha kipindi cha kupakia vipande.

Ombi:
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

Jibu:
```json
{
  "upload-id": "upload-abc-123",
  "chunk-size": 5242880,
  "total-chunks": 100
}
```

Msimamizi wa maktaba:
1. Huunda nambari ya kipekee `upload_id` na `object_id` (UUID kwa uhifadhi wa data).
2. Huita `CreateMultipartUpload` ya S3, na kupokea `s3_upload_id`.
3. Huunda rekodi ya kikao katika Cassandra.
4. Hurudisha `upload_id` kwa mteja.

#### `upload-chunk`

<<<<<<< HEAD
Pakia kipande kimoja.
=======
Pakia sehemu moja.
>>>>>>> 82edf2d (New md files from RunPod)

Ombi:
```json
{
  "operation": "upload-chunk",
  "upload-id": "upload-abc-123",
  "chunk-index": 0,
  "content": "<base64-encoded-chunk>"
}
```

Jibu:
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

Msimamizi wa maktaba:
<<<<<<< HEAD
1. Tafuta kikao kwa kutumia `upload_id`
2. Thibitisha umiliki (mtumiaji lazima awe yule aliyeunda kikao)
3. Piga simu kwa S3 `UploadPart` pamoja na data ya sehemu, na upokee `etag`
4. Sasisha rekodi ya kikao na fahirisi ya sehemu na etag
5. Rejesha maelezo ya maendeleo kwa mteja

Sehemu ambazo hazijafaulu zinaweza kujaribiwa tena - tuma tu `chunk-index` tena.
=======
1. Tafuta kipindi kwa `upload_id`
2. Thibitisha umiliki (mtumiaji lazima awe yule aliyeunda kipindi)
3. Piga S3 `UploadPart` na data ya sehemu, pokea `etag`
4. Sasisha rekodi ya kipindi na fahirisi ya sehemu na etag
5. Rejesha maendeleo kwa mteja

Sehemu ambazo hazijafaulu zinaweza kujaribiwa tena - tuma tu `chunk-index` ile ile tena.
>>>>>>> 82edf2d (New md files from RunPod)

#### `complete-upload`

Hakisha upakiaji na uunde hati.

Ombi:
```json
{
  "operation": "complete-upload",
  "upload-id": "upload-abc-123"
}
```

Jibu:
```json
{
  "document-id": "doc-123",
  "object-id": "550e8400-e29b-41d4-a716-446655440000"
}
```

Msimamizi wa maktaba:
<<<<<<< HEAD
1. Tafuta kikao, thibitisha kwamba vipande vyote vimepokelewa
2. Anapiga S3 `CompleteMultipartUpload` na etags za sehemu (S3 huunganisha sehemu
   ndani - hakuna gharama ya kumbukumbu kwa msimamizi)
3. Huunda rekodi ya hati katika Cassandra na metadata na rejeleo la kitu
4. Huondoa rekodi ya kikao cha kupakia
5. Hurudisha kitambulisho cha hati kwa mteja
=======
1. Angalia kikao, thibitisha kwamba vipande vyote vimepokelewa.
2. Anapiga S3 `CompleteMultipartUpload` na etags za sehemu (S3 huunganisha sehemu
   ndani - hakuna gharama ya kumbukumbu kwa msimamizi).
3. Huunda rekodi ya hati katika Cassandra na metadata na rejea la kitu.
4. Huondoa rekodi ya kikao cha kupakia.
5. Anarudisha kitambulisho cha hati kwa mteja.
>>>>>>> 82edf2d (New md files from RunPod)

#### `abort-upload`

Kuacha kupakia ambacho kinaendelea.

Ombi:
```json
{
  "operation": "abort-upload",
  "upload-id": "upload-abc-123"
}
```

Msimamizi wa maktaba:
1. Anapiga simu kwa S3 `AbortMultipartUpload` ili kusafisha sehemu.
2. Anafuta rekodi ya kikao kutoka Cassandra.

#### `get-upload-status`

Angalia hali ya kupakia (kwa uwezo wa kuendelea).

Ombi:
```json
{
  "operation": "get-upload-status",
  "upload-id": "upload-abc-123"
}
```

Jibu:
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

Orodha ya vipakuliwa ambavyo havijakamilika kwa mtumiaji.

Ombi:
```json
{
  "operation": "list-uploads"
}
```

Jibu:
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

### Hifadhi ya Kipindi cha Uipakaji

Fuatilia uipakaji unaoendelea katika Cassandra:

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

<<<<<<< HEAD
**Tabia ya TTL:**
Vikao hupotea baada ya saa 24 ikiwa havijakamilika.
Wakati TTL ya Cassandra inapita, rekodi ya kikao inafutwa.
Sehemu zisizo na uhusiano za S3 huondolewa na sera ya maisha ya S3 (sanidi kwenye ndoo).

### Usimamizi wa Hitilafu na Uadilifu

**Hitilafu ya kupakia sehemu:**
Mteja hurudia kupakia sehemu iliyoshindwa (na `upload_id` na `chunk-index` sawa).
=======
**Tabia ya Muda (TTL):**
Vikao hupotea baada ya saa 24 ikiwa havijakamilika.
Wakati muda (TTL) wa Cassandra unapita, rekodi ya kikao inafutwa.
Sehemu zisizo na uhusiano za S3 huondolewa na sera ya maisha ya S3 (sanidi kwenye ndoo).

### Usimamizi wa Hitilafu na Umoja

**Hitilafu ya kupakia sehemu:**
Mteja hujaribu tena sehemu iliyoshindwa (na `upload_id` na `chunk-index` sawa).
>>>>>>> 82edf2d (New md files from RunPod)
`UploadPart` ya S3 ni sawa kwa nambari sawa ya sehemu.
Kikao kinafuatilia sehemu zipi zilizofanikiwa.

**Mteja hukatika wakati wa kupakia:**
Kikao kinaendelea katika Cassandra na sehemu zilizopokelewa zimeandikwa.
Mteja anaweza kupiga `get-upload-status` ili kuona nini kinakosekana.
Anza tena kwa kupakia sehemu ambazo hazijapakiwa, kisha `complete-upload`.

**Hitilafu ya kupakia kikamilifu:**
<<<<<<< HEAD
`CompleteMultipartUpload` ya S3 ni ya uadilifu - inaweza kufanikiwa kikamilifu au kushindwa.
Katika hali ya kushindwa, sehemu zinaendelea na mteja anaweza kujaribu tena `complete-upload`.
Hati yoyote ya nusu haionekani.

**Kumalizika kwa kikao:**
TTL ya Cassandra inafuta rekodi ya kikao baada ya saa 24.
Sera ya maisha ya ndoo ya S3 husafisha kupakia kwa sehemu nyingi ambazo hazijakamilika.
Hakuna usafishaji wa mwongozo unaohitajika.

### Uadilifu wa Sehemu Nyingi za S3

Kupakia kwa sehemu nyingi za S3 hutoa uadilifu uliopo:

1. **Sehemu hazionekani:** Sehemu zilizopakuliwa haziwezi kupatikana kama vitu.
   Zipo tu kama sehemu za kupakia kwa sehemu nyingi ambazo hazijakamilika.

2. **Kukamilisha kwa uadilifu:** `CompleteMultipartUpload` inaweza kufanikiwa (kitu
   kinaonekana kwa uadilifu) au kushindwa (hakuna kitu kilichoanzishwa). Hakuna hali ya nusu.

3. **Hakuna jina tena linalohitajika:** Ufunguo wa mwisho wa kitu unaonyeshwa wakati
   `CreateMultipartUpload`. Sehemu huunganishwa moja kwa moja kwenye ufunguo huo.

4. **Uunganishaji wa upande wa seva:** S3 inaunganisha sehemu ndani. Msimamizi
=======
`CompleteMultipartUpload` ya S3 ni ya umoja - inaweza kufanikiwa kikamilifu au kushindwa.
Katika hali ya kushindwa, sehemu zinaendelea na mteja anaweza kujaribu tena `complete-upload`.
Hati yoyote isiyo kamili haionekani.

**Muda wa kikao:**
Muda (TTL) wa Cassandra hufuta rekodi ya kikao baada ya saa 24.
Sera ya maisha ya ndoo ya S3 husafisha kupakia kwa sehemu nyingi ambazo hazijakamilika.
Hakuna usafishaji wa mwongozo unaohitajika.

### Umoja wa Kupakia Sehemu ya S3

Kupakia sehemu nyingi za S3 hutoa umoja uliopo:

1. **Sehemu hazionekani:** Sehemu zilizopakuliwa haziwezi kupatikana kama vitu.
   Zipo tu kama sehemu za kupakia sehemu nyingi ambazo hazijakamilika.

2. **Uhakikisho wa umoja:** `CompleteMultipartUpload` inaweza kufanikiwa (kitu
   kinaonekana kikamilifu) au kushindwa (kitu hakitengenezwi). Hakuna hali ya nusu.

3. **Hakuna haja ya kubadilisha jina:** Ufunguo wa mwisho wa kitu unaonyeshwa wakati
   `CreateMultipartUpload`. Sehemu huunganishwa moja kwa moja kwenye ufunguo huo.

4. **Uunganishaji wa upande wa seva:** S3 huunganisha sehemu ndani. Msimamizi
>>>>>>> 82edf2d (New md files from RunPod)
   haisomi sehemu - hakuna gharama ya kumbukumbu bila kujali ukubwa wa hati.

### Upanuzi wa BlobStore

**Faili:** `trustgraph-flow/trustgraph/librarian/blob_store.py`

Ongeza mbinu za kupakia sehemu nyingi:

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

<<<<<<< HEAD
### Mambo Yanayohusiana na Ukubwa wa Sehemu

**Kiwango cha chini cha S3**: 5MB kwa kila sehemu (isipokuwa sehemu ya mwisho)
**Kiwango cha juu cha S3**: Sehemu 10,000 kwa kila upakiaji
**Kiwango cha kawaida kinachopendekezwa**: Sehemu za 5MB
  Hati ya 500MB = sehemu 100
  Hati ya 5GB = sehemu 1,000
**Ufuatiliaji wa maendeleo**: Sehemu ndogo = taarifa za maendeleo bora
**Ufanisi wa mtandao**: Sehemu kubwa = safari ndogo

Ukubwa wa sehemu unaweza kupangwa na mtumiaji ndani ya mipaka (5MB - 100MB).

### Ufuatiliaji wa Hati: Upakiaji wa Kiasi

Mchakato wa upakiaji unalenga kuweka hati kwenye hifadhi kwa ufanisi. Mchakato
wa ufuatiliaji unalenga kuchuja na kugawanya hati bila kuzipakia
zote kwenye kumbukumbu.

#### Kanuni ya Ubunifu: Kitambulisho, Sio Yaliyomo

Kwa sasa, wakati mchakato unaanza, yaliyomo kwenye hati huhamishwa kupitia
ujumbe wa Pulsar. Hii inapakia hati zote kwenye kumbukumbu. Badala yake:

Ujumbe wa Pulsar unaonyesha tu **kitambulisho cha hati**
Vifaa vya ufuatiliaji hupata yaliyomo kwenye hati moja kwa moja kutoka kwa mfumo
Kupata hufanyika kama **mtiririko kwenye faili ya muda**
Ufuatiliaji maalum wa hati (PDF, maandishi, n.k.) hufanya kazi na faili, sio
mipaka ya kumbukumbu

Hii inahakikisha kwamba mfumo wa hati hautegemei muundo wa hati. Ufuatiliaji
wa PDF, ufuatiliaji wa maandishi, na mantiki nyingine maalum ya muundo
inabaki katika vichujio husika.
=======
### Mambo Yanayohusiana na Ukubwa wa Kifurushi

**Kiwango cha chini cha S3**: 5MB kwa kila sehemu (isipokuwa sehemu ya mwisho)
**Kiwango cha juu cha S3**: Sehemu 10,000 kwa kila upakiaji
**Kiwango cha kawaida kinachopendekezwa**: Kifurushi cha 5MB
  Hati ya 500MB = Kifurushi 100
  Hati ya 5GB = Kifurushi 1,000
**Ufuatiliaji wa maendeleo**: Kifurushi kidogo = Taarifa za maendeleo bora
**Ufanisi wa mtandao**: Kifurushi kikubwa = Safari ndogo

Ukubwa wa kifurushi unaweza kusanidiwa na mtumiaji ndani ya mipaka (5MB - 100MB).

### Ufuatiliaji wa Hati: Upakiaji wa Kwenye Mtiririko

Mchakato wa upakiaji unahusu kuweka hati kwenye hifadhi kwa ufanisi. Mchakato wa ufuatiliaji unahusu kuchuja na kugawanya hati bila kuiziba yote kwenye kumbukumbu.



#### Kanuni ya Ubunifu: Kitambulisho, Sio Yaliyomo

Kwa sasa, wakati mchakato unaanza, yaliyomo kwenye hati huhamishwa kupitia ujumbe wa Pulsar. Hii huweka hati zilizokamilika kwenye kumbukumbu. Badala yake:


Ujumbe wa Pulsar unaonyesha tu **kitambulisho cha hati**
Vifaa hupata yaliyomo kwenye hati moja kwa moja kutoka kwa mfumo wa kumbukumbu
Kupata hufanyika kama **mtiririko kwenye faili ya muda**
Ufuatiliaji maalum wa hati (PDF, maandishi, n.k.) hutumia faili, sio mipaka ya kumbukumbu

Hii huweka mfumo wa kumbukumbu usio na kujua muundo wa hati. Ufuatiliaji wa PDF, ufuatiliaji wa maandishi, na mantiki nyingine maalum ya muundo huendelea katika vichujio husika.


#### Mchakato wa Ufuatiliaji
>>>>>>> 82edf2d (New md files from RunPod)

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

<<<<<<< HEAD
#### API ya Mfumo wa Maktaba

Ongeza operesheni ya upataji wa hati kwa njia ya mtiririko:
=======
#### API ya Mto wa Huduma za Maktaba

Ongeza operesheni ya kupata hati kwa mtiririko:
>>>>>>> 82edf2d (New md files from RunPod)

**`stream-document`**

Ombi:
```json
{
  "operation": "stream-document",
  "document-id": "doc-123"
}
```

Jibu: Vipande vya binary vilivyotumwa (si jibu moja).

Kwa API ya REST, hii hurudisha jibu linaloendelea kwa kutumia `Transfer-Encoding: chunked`.

<<<<<<< HEAD
Kwa simu za ndani kati ya huduma (kwa mfumo wa uprosesa hadi mfumo wa kumbukumbu), hii inaweza kuwa:
Uhamisho wa moja kwa moja wa S3 kupitia URL iliyosainiwa (ikiwa mtandao wa ndani unaruhusu).
Majibu yaliyogawanywa kupitia itifaki ya huduma.
Kituo maalum cha utumaji wa data.
=======
Kwa simu za ndani kati ya huduma (kwa mfumo wa usindikaji hadi kwa mfumo wa kumbukumbu), hii inaweza kuwa:
Uhamisho wa moja kwa moja wa S3 kupitia URL iliyosainiwa (ikiwa mtandao wa ndani unaruhusu).
Majibu yaliyogawanywa kupitia itifaki ya huduma.
Kifaa maalum cha utumaji wa data.
>>>>>>> 82edf2d (New md files from RunPod)

Mahitaji muhimu: data inatiririka kwa vipande, haijahifadhiwa kikamilifu katika mfumo wa kumbukumbu.

#### Mabadiliko ya Kipanguli cha PDF

**Utendaji wa sasa** (unaotumia kumbukumbu nyingi):

```python
def decode_pdf(document_content: bytes) -> str:
    reader = PdfReader(BytesIO(document_content))  # full doc in memory
    text = ""
    for page in reader.pages:
        text += page.extract_text()  # accumulating
    return text  # full text in memory
```

**Utekelezaji mpya** (faili ya muda, hatua kwa hatua):

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

Profaili ya kumbukumbu:
Faili ya muda kwenye diski: ukubwa wa faili ya PDF (diski ni rahisi).
Katika kumbukumbu: ukurasa mmoja wa maandishi kwa wakati.
Kumbukumbu ya juu: imepunguzwa, haitegemei saizi ya hati.

#### Mabadiliko ya Kipanguli cha Hati za Nakshata

Kwa hati za nakshata, rahisi zaidi - hakuna faili ya muda inayohitajika:

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

Hati za maandishi zinaweza kutiririka moja kwa moja bila faili ya muda kwa sababu zina
muundo wa mstari.

<<<<<<< HEAD
#### Jumuisho la Kifaa cha Kugawa (Chunker)

Kifaa cha kugawa hupokea mfuatiliaji wa maandishi (kurasa au aya) na hutoa
=======
#### Jumuisho la Kichungia (Chunker)

Kichungia hupokea mfuatiliaji wa maandishi (kurasa au aya) na hutoa
>>>>>>> 82edf2d (New md files from RunPod)
vipande kwa hatua kwa hatua:

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

#### Mchakato Kamili wa Uendeshaji

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

<<<<<<< HEAD
Katika hakuna hatua, hati kamili au maandishi yaliyotolewa kamili hayahifadhiwi kwenye kumbukumbu.
=======
Katika hakuna hatua, hati kamili au maandishi yaliyochukuliwa kamili hayahifadhiwi kwenye kumbukumbu.
>>>>>>> 82edf2d (New md files from RunPod)

#### Mambo Yanayohusiana na Faili za Muda

**Mahali:** Tumia saraka ya muda ya mfumo (`/tmp` au sawa). Kwa
matumizi yaliyojumuishwa, hakikisha saraka ya muda ina nafasi ya kutosha
na iko kwenye uhifadhi wa haraka (si iliyounganishwa kwenye mtandao, ikiwezekana).

**Usafishaji:** Tumia menejeria wa muktadha (`with tempfile...`) ili kuhakikisha usafishaji
hata wakati wa hitilafu.

**Uchakataji sambamba:** Kazi kila moja ya uchakataji hupata faili yake ya muda.
Hakuna migogoro kati ya uchakataji wa hati sambamba.

**Nafasi ya diski:** Faili za muda zina muda mfupi (muda wa uchakataji). Kwa
<<<<<<< HEAD
hati ya PDF ya 500MB, inahitaji nafasi ya muda ya 500MB wakati wa uchakataji. Kikomo cha ukubwa
kinaweza kutekelezwa wakati wa kupakia ikiwa nafasi ya diski ni mdogo.

### Kiolesura Kimoja cha Uchakataji: Hati za Mtoto

Uchimbaji wa hati za PDF na uchakataji wa hati za maandishi lazima ziingie katika
mstari mmoja wa baadaye (kugawanya → embeddings → uhifadhi). Ili kufanikisha hili kwa
"kupata kwa ID" kiolesura, vipande vya maandishi vilivyochimbwa huhifadhiwa tena
kwenye mfumo kama hati za mtoto.

#### Mchakato wa Uchakataji na Hati za Mtoto
=======
hati ya PDF ya 500MB, inahitaji nafasi ya muda ya 500MB wakati wa uchakataji. Kizuia cha ukubwa
kunaweza kutekelezwa wakati wa kupakia ikiwa nafasi ya diski ni mdogo.

### Kiolesura Kimoja cha Uchakataji: Hati za Watoto

Uchimbaji wa hati za PDF na uchakataji wa maandishi unahitaji kuingia kwenye
mstari mmoja wa baadaye (kugawanya → maandishi → uhifadhi). Ili kufanikisha hili kwa
"kupata kwa ID" kiolesura, vipande vya maandishi vilivyochimbwa huhifadhiwa tena
kwenye mfumo kama hati za watoto.

#### Mchakato wa Uchakataji na Hati za Watoto
>>>>>>> 82edf2d (New md files from RunPod)

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

Kifaa cha kuainisha (chunker) kina muundo mmoja wa kiungo:
Pokea kitambulisho cha hati (kupitia Pulsar)
Pumua yaliyomo kutoka kwa mfumo wa kumbukumbu (librarian)
Igawanye katika sehemu ndogo

Haijulishi au hajali kama kitambulisho kinarejelea:
Hati ya maandishi iliyopakiwa na mtumiaji
Sehemu ya maandishi iliyochimbwa kutoka kwa ukurasa wa PDF
Aina yoyote ya hati ya siku zijazo

<<<<<<< HEAD
#### Meta-data ya Hati Ndogo
=======
#### Meta Data ya Hati Ndogo
>>>>>>> 82edf2d (New md files from RunPod)

Panua muundo wa hati ili kufuatilia uhusiano wa mzazi/mtoto:

```sql
-- Add columns to document table
ALTER TABLE document ADD parent_id text;
ALTER TABLE document ADD document_type text;

-- Index for finding children of a parent
CREATE INDEX document_parent ON document (parent_id);
```

**Aina za nyaraka:**

| `document_type` | Maelezo |
|-----------------|-------------|
| `source` | Nyaraka zilizopakiwa na mtumiaji (PDF, maandishi, n.k.) |
<<<<<<< HEAD
| `extracted` | Zilizotokana na nyaraka asili (k.m., maandishi ya ukurasa wa PDF) |

**Nafasi za metadata:**

| Nafasi | Nyaraka Asili | Nyaraka Zilizotokana |
|-------|-----------------|-----------------|
| `id` | Zilizotolewa na mtumiaji au zilizoundwa | Zilizoundwa (k.m., `{parent-id}-page-{n}`) |
| `parent_id` | `NULL` | Kitambulisho cha nyaraka asili |
| `document_type` | `source` | `extracted` |
| `kind` | `application/pdf`, n.k. | `text/plain` |
| `title` | Zilizotolewa na mtumiaji | Zilizoundwa (k.m., "Ukurasa wa 3 wa Ripoti.pdf") |
| `user` | Mtumiaji aliyeidhinishwa | Sawa na nyaraka asili |

#### API ya Maktaba kwa Nyaraka Zilizotokana

**Kuunda nyaraka zilizotokana** (ya ndani, hutumiwa na pdf-extractor):
=======
| `extracted` | Imetokana na nyaraka ya asili (k.m., maandishi ya ukurasa wa PDF) |

**Nafasi za metadata:**

| Nafasi | Nyaraka ya Asili | Mtoto Uliochukuliwa |
|-------|-----------------|-----------------|
| `id` | Iliyotolewa na mtumiaji au iliyoundwa | Iliyoundwa (k.m., `{parent-id}-page-{n}`) |
| `parent_id` | `NULL` | Kitambulisho cha nyaraka mama |
| `document_type` | `source` | `extracted` |
| `kind` | `application/pdf`, n.k. | `text/plain` |
| `title` | Iliyotolewa na mtumiaji | Iliyoundwa (k.m., "Ukurasa wa 3 wa Ripoti.pdf") |
| `user` | Mtumiaji aliyeidhinishwa | Sawa na nyaraka mama |

#### API ya Maktaba kwa Nyaraka za Watoto

**Kutengeneza nyaraka za watoto** (ya ndani, inayotumika na pdf-extractor):
>>>>>>> 82edf2d (New md files from RunPod)

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

<<<<<<< HEAD
Kwa maandishi madogo ambayo yamechukuliwa (maandishi ya kawaida ya ukurasa ni chini ya 100KB), kupakia kwa operesheni moja ni sawa. Kwa matamshi makubwa sana ya maandishi, kupakia kwa sehemu kunaweza kutumika.
=======
Kwa maandishi madogo ambayo yamechukuliwa (maandishi ya kawaida ya ukurasa ni chini ya 100KB), kupakia kwa hatua moja ni la kukubalika. Kwa matamshi makubwa sana ya maandishi, kupakia kwa sehemu kunaweza kutumika.
>>>>>>> 82edf2d (New md files from RunPod)

**Orodha ya hati za watoto** (kwa ajili ya utatuzi/utawala):


<<<<<<< HEAD

=======
Hati ya Matokeo
>>>>>>> 82edf2d (New md files from RunPod)
```json
{
  "operation": "list-children",
  "parent-id": "doc-123"
}
```

Jibu:
```json
{
  "children": [
    { "id": "doc-123-page-1", "title": "Page 1", "kind": "text/plain" },
    { "id": "doc-123-page-2", "title": "Page 2", "kind": "text/plain" },
    ...
  ]
}
```

#### Tabia inayoonwa na mtumiaji

**Tabia ya kawaida ya `list-documents`:**

```sql
SELECT * FROM document WHERE user = ? AND parent_id IS NULL;
```

Tuandishi kuu (vyanzo) pekee ndivyo yanavyoonekana kwenye orodha ya vyanzo vya mtumiaji.
Vyanzo vidogo huondolewa kwa chaguo-msingi.

**Bendera ya hiari ya kujumuisha-vyanzo-vidogo** (kwa wasimamizi/uchunguzi):

```json
{
  "operation": "list-documents",
  "include-children": true
}
```

<<<<<<< HEAD
#### Ufutilishaji wa Kuondoa Data kwa Kadirio

Wakati hati mama inapoondolewa, watoto wote lazima waondolewe:
=======
#### Ufutilishaji Pamoja na Uharibifu wa Data

Wakati hati mama inafutwa, watoto wote lazima waondolewe:
>>>>>>> 82edf2d (New md files from RunPod)

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

<<<<<<< HEAD
#### Mawazo Kuhusu Uhifadhi

Matini yaliyotolewa yana nakala sawa:
Nakala asili ya PDF inahifadhiwa katika "Garage"
Nakala iliyotolewa kwa kila ukurasa pia inahifadhiwa katika "Garage"

Hii inaruhusu:
**Kiolesura sawa cha "chunker"**: "Chunker" daima hupata data kwa kutumia kitambulisho
**Uendelezaji/jaribio tena**: Inaweza kuanza tena katika hatua ya "chunker" bila kuhariri tena PDF
**Urekebishaji**: Nakala iliyotolewa inaweza kuchunguzwa
**Tofauti ya majukumu**: Huduma ya kuchimbua PDF na "chunker" ni huduma tofauti
=======
#### Mawasilisho ya Uhifadhi

Matini yaliyotolewa yana nakala za maudhui:
Nakala ya asili ya PDF inahifadhiwa katika "Garage"
Nakala ya matini iliyotolewa kwa kila ukurasa pia inahifadhiwa katika "Garage"

Hii inaruhusu:
**Kiolesura cha kawaida cha "chunker"**: "Chunker" daima hupata kwa kitambulisho
**Uanzishaji upya/jaribio**: Inaweza kuanzisha tena katika hatua ya "chunker" bila kuharibu tena PDF
**Urekebishaji**: Matini iliyotolewa inaweza kuchunguzwa
**Tofauti ya majukumu**: Huduma ya kutolea matini kutoka PDF na "chunker" ni huduma tofauti
>>>>>>> 82edf2d (New md files from RunPod)

Kwa PDF ya 500MB yenye kurasa 200, kwa wastani ya matini ya 5KB kwa kila ukurasa:
Uhifadhi wa PDF: 500MB
Uhifadhi wa matini iliyotolewa: ~1MB jumla
Gharama ya ziada: ndogo sana

<<<<<<< HEAD
#### Matokeo ya Kuchimbua PDF

Kichunguzi cha kuchimbua PDF, baada ya kuchakata hati:

1. Hupata PDF kutoka kwa "librarian" hadi kwenye faili ya muda
2. Huchimbua matini ukurasa kwa ukurasa
=======
#### Matokeo ya Kutoa Matini kutoka PDF

Kifaa cha kutoa matini kutoka PDF, baada ya kuchakata hati:

1. Hupokea PDF kutoka kwa "librarian" hadi faili ya muda
2. Hutoa matini ukurasa kwa ukurasa
>>>>>>> 82edf2d (New md files from RunPod)
3. Kwa kila ukurasa, huhifadhi matini iliyotolewa kama hati ndogo kupitia "librarian"
4. Hutuma kitambulisho cha hati ndogo kwa folyo ya "chunker"

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

<<<<<<< HEAD
Kifaa cha kuainisha vitapokea kitambulisho hivi vya watoto na vitawatumia kwa njia ile ile
ambayo kingetumia hati ya maandishi iliyopakiwa na mtumiaji.

### Sasizi za Mteja
=======
Kifaa cha "chunker" hupokea kitambulisho hivi vya watoto na huviweka sawa na
jinsi lingeweza kuchakata hati ya maandishi iliyopakiwa na mtumiaji.

### Masasisho ya Mteja
>>>>>>> 82edf2d (New md files from RunPod)

#### SDK ya Python

SDK ya Python (`trustgraph-base/trustgraph/api/library.py`) inapaswa kushughulikia
<<<<<<< HEAD
vipakio vilivyogawanywa kwa njia ya moja kwa moja. Muundo wa umma haubadiliki:
=======
vipakio vilivyogawanywa kwa njia ambayo haionyeshi. Muundo wa umma haubadiliki:
>>>>>>> 82edf2d (New md files from RunPod)

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

Kwa ndani, SDK hugundua ukubwa wa hati na hubadilisha mkakati:

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

**Arifa za maendeleo** (ongezeko la hiari):

```python
def add_document(self, ..., on_progress=None):
    """
    on_progress: Optional callback(bytes_sent, total_bytes)
    """
```

Hii inaruhusu programu za kiutengenezaji kuonyesha maendeleo ya kupakia bila kubadilisha API ya msingi.

#### Zana za CLI (Command Line Interface)

**`tg-add-library-document`** inaendelea kufanya kazi bila kubadilika:

```bash
# Works transparently for any size - SDK handles chunking internally
tg-add-library-document --file large-report.pdf --title "Large Report"
```

Onyesho la maendeleo la hiari linaweza kuongezwa:

```bash
tg-add-library-document --file large-report.pdf --title "Large Report" --progress
# Output:
# Uploading: 45% (225MB / 500MB)
```

**Vifaa vya zamani vimetoolewa:**

<<<<<<< HEAD
`tg-load-pdf` - imepitwa na wakati, tumia `tg-add-library-document`
`tg-load-text` - imepitwa na wakati, tumia `tg-add-library-document`
=======
`tg-load-pdf` - yamefutwa, tumia `tg-add-library-document`
`tg-load-text` - yamefutwa, tumia `tg-add-library-document`
>>>>>>> 82edf2d (New md files from RunPod)

**Amri za utawala/uchunguzi** (hiari, kipaumbele cha chini):

```bash
# List incomplete uploads (admin troubleshooting)
tg-add-library-document --list-pending

# Resume specific upload (recovery scenario)
tg-add-library-document --resume upload-abc-123 --file large-report.pdf
```

Haya yanaweza kuwa maboresho kwenye amri iliyopo badala ya zana tofauti.

#### Masuala ya Mabadiliko ya Vipimo vya API

Vipimo vya OpenAPI (`specs/api/paths/librarian.yaml`) vinahitaji mabadiliko kwa:

**Utendaji mpya:**

<<<<<<< HEAD
`begin-upload` - Anzisha kipindi cha kupakia kwa sehemu
=======
`begin-upload` - Anzisha kipindi cha kupakia sehemu
>>>>>>> 82edf2d (New md files from RunPod)
`upload-chunk` - Pakia sehemu moja
`complete-upload` - Kamilisha kupakia
`abort-upload` - Ghairi kupakia
`get-upload-status` - Angalia maendeleo ya kupakia
`list-uploads` - Orodha ya kupakia ambayo hayaja kamili kwa mtumiaji
`stream-document` - Kuchukua hati kwa njia ya utiririshaji
`add-child-document` - Hifadhi maandishi yaliyotolewa (ya ndani)
`list-children` - Orodha ya hati za chini (ya msimamizi)

**Utendaji uliorekebishwa:**

`list-documents` - Ongeza parameter `include-children`

<<<<<<< HEAD
**Muundo mpya:**
=======
**Vipimo vipya:**
>>>>>>> 82edf2d (New md files from RunPod)

`ChunkedUploadBeginRequest`
`ChunkedUploadBeginResponse`
`ChunkedUploadChunkRequest`
`ChunkedUploadChunkResponse`
`UploadSession`
`UploadProgress`

**Mabadiliko ya vipimo vya WebSocket** (`specs/websocket/`):

Nakala utendaji wa REST kwa wateja wa WebSocket, na kuwezesha
<<<<<<< HEAD
maendeleo ya muda halisi wakati wa kupakia.
=======
maendeleo ya wakati halisi wakati wa kupakia.
>>>>>>> 82edf2d (New md files from RunPod)

#### Mambo ya Kuzingatia ya Uzoefu wa Mtumiaji

Mabadiliko ya vipimo vya API yanawezesha maboresho ya upande wa mbele:

**Kiolesura cha maendeleo ya kupakia:**
Pampu ya maendeleo ya kuonyesha sehemu zilizopakwa
Muda uliokadiri wa kupakia
Uwezo wa kusitisha/kuendeleza

**Kupona kwa makosa:**
<<<<<<< HEAD
Chaguo la "Endeleza kupakia" kwa kupakia ambacho kimekatika
Orodha ya kupakia ambayo hayaja kamili wakati wa kuunganisha tena

**Ushughulikiaji wa faili kubwa:**
Uchunguzi wa ukubwa wa faili kwenye upande wa mteja
Kupakia kwa sehemu kiotomatiki kwa faili kubwa
=======
Chaguo la "endelea kupakia" kwa kupakia ambacho kimekatika
Orodha ya kupakia ambayo hayaja kamili wakati wa kuunganisha tena

**Usimamizi wa faili kubwa:**
Uchunguzi wa ukubwa wa faili kwenye upande wa mteja
Kupakia kiotomatiki kwa sehemu kwa faili kubwa
>>>>>>> 82edf2d (New md files from RunPod)
Maelezo wazi wakati wa kupakia kwa muda mrefu

Maboresho haya ya uzoefu wa mtumiaji yanahitaji kazi ya upande wa mbele inayong'wa na vipimo vya API vilivyoboreshwa.
