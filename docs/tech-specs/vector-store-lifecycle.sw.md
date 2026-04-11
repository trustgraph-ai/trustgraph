# Usimamizi wa Mzunguko wa Hifadhi ya Vektor

## Muhtasari

Hati hii inaeleza jinsi TrustGraph inavyosimamia mkusanyiko wa hifadhi ya vektor katika matumizi tofauti ya backend (Qdrant, Pinecone, Milvus). Muundo huu unashughulikia changamoto ya kusaidia embeddings zenye vipimo tofauti bila kuweka maadili ya vipimo yaliyopangwa awali.

## Tatizo

Hifadhi za vektor zinahitaji kipimo cha embedding kuainishwa wakati wa kuunda mkusanyiko/fahirisi. Hata hivyo:
Modeli tofauti za embedding hutoa vipimo tofauti (k.m., 384, 768, 1536)
Kipimo hakijulikani hadi embedding ya kwanza itengenezwe
Mkusaniko mmoja wa TrustGraph unaweza kupokea embeddings kutoka kwa modeli nyingi
Kuweka kipimo (k.m., 384) husababisha hitilafu na saizi zingine za embedding

## Kanuni za Muundo

1. **Uundaji wa Kila Mara:** Mikusanyiko huundwa wakati wa kuandika mara ya kwanza, sio wakati wa shughuli za usimamizi wa mkusanyiko.
2. **Jina Kulingana na Kipimo:** Majina ya mkusanyiko yanajumuisha kipimo cha embedding kama sehemu ya mwisho.
3. **Ufanisi:** Maswali dhidi ya mikusanyiko isiyopo hurudisha matokeo tupu, sio makosa.
4. **Usaidizi wa Vipimo Vingi:** Mkusaniko mmoja wa kimantiki unaweza kuwa na mikusanyiko mingi ya kimwili (moja kwa kila kipimo).

## Muundo

### Mfumo wa Majina ya Mkusaniko

Mikusanyiko ya hifadhi ya vektor hutumia sehemu za mwisho za kipimo ili kusaidia saizi nyingi za embedding:

**Embeddings za Hati:**
Qdrant: `d_{user}_{collection}_{dimension}`
Pinecone: `d-{user}-{collection}-{dimension}`
Milvus: `doc_{user}_{collection}_{dimension}`

**Embeddings za Grafu:**
Qdrant: `t_{user}_{collection}_{dimension}`
Pinecone: `t-{user}-{collection}-{dimension}`
Milvus: `entity_{user}_{collection}_{dimension}`

Mifano:
`d_alice_papers_384` - Mkusaniko wa "makala za Alice" wenye embeddings za vipimo 384
`d_alice_papers_768` - Mkusaniko huo huo wa kimantiki wenye embeddings za vipimo 768
`t_bob_knowledge_1536` - Grafu ya maarifa ya "Bob" yenye embeddings za vipimo 1536

### Awamu za Mzunguko

#### 1. Ombi la Uundaji wa Mkusaniko

**Mwendo wa Ombi:**
```
User/System → Librarian → Storage Management Topic → Vector Stores
```

**Tabia:**
Msimamizi wa maktaba hutuma ombi la `create-collection` kwa kila mfumo wa kuhifadhi data.
Vifaa vya usindikaji vya hifadhi ya vector hutambua ombi hilo lakini **havitaunda makusanyo halisi**
Jibu hurudishwa mara moja kwa mafanikio.
Uundaji halisi wa makusanyo huahirishwa hadi wakati wa kuandika wa kwanza.

**Sababu:**
Vipimo havijulikani wakati wa uundaji.
Inazuia uundaji wa makusanyo yenye vipimo vibaya.
Inarahisha mantiki ya usimamizi wa makusanyo.

#### 2. Operesheni za Kuandika (Uundaji Ulioahirishwa)

**Mchakato wa Kuandika:**
```
Data → Storage Processor → Check Collection → Create if Needed → Insert
```

**Tabia:**
1. Pata kipimo cha pembejeo kutoka kwenye vektari: `dim = len(vector)`
2. Unda jina la mkusanyiko pamoja na kiambishi cha kipimo
3. Angalia ikiwa mkusanyiko unapatikana na kipimo hicho maalum
4. Ikiwa haupo:
   Unda mkusanyiko wenye kipimo sahihi
   Rekodi: `"Lazily creating collection {name} with dimension {dim}"`
5. Ingiza pembejeo kwenye mkusanyiko maalum wa kipimo

**Mfano wa Matukio:**
```
1. User creates collection "papers"
   → No physical collections created yet

2. First document with 384-dim embedding arrives
   → Creates d_user_papers_384
   → Inserts data

3. Second document with 768-dim embedding arrives
   → Creates d_user_papers_768
   → Inserts data

Result: Two physical collections for one logical collection
```

#### 3. Operesheni za Uchunguzi

**Mwendo wa Uchunguzi:**
```
Query Vector → Determine Dimension → Check Collection → Search or Return Empty
```

**Tabia:**
1. Pata kipimo kutoka kwa vektor ya swali: `dim = len(vector)`
2. Unda jina la mkusanyiko pamoja na kiambishi cha kipimo
3. Angalia ikiwa mkusanyiko unapatikana
4. Ikiwa unapatikana:
   Fanya utafutaji wa kufanana
   Rudi na matokeo
5. Ikiwa haupatikani:
   Rekodi: `"Collection {name} does not exist, returning empty results"`
   Rudi na orodha tupu (hakuna kosa lililotokea)

**Vipimo Vingi katika Swali Moja:**
Ikiwa swali lina vektor za vipimo tofauti
Kila kipimo hufanya utafutaji katika mkusanyiko wake unaohusiana
Matokeo huunganishwa
Mikusanyiko inayokosekana huachwa (hayatibiwi kama madosa)

**Sababu:**
Kuuliza mkusanyiko ambao hauna data ni matumizi halali
Kurudi na matokeo tupu ni sahihi kwa maana
Inazuia madosa wakati wa kuanza kwa mfumo au kabla ya kuingiza data

#### 4. Ufutilishaji wa Mkusaniko

**Mchakato wa Ufutilishaji:**
```
Delete Request → List All Collections → Filter by Prefix → Delete All Matches
```

**Tabia:**
1. Unda muundo wa kielelezo: `d_{user}_{collection}_` (angalia alama ya chini)
2. Orodha zote za makusanyo katika hifadhi ya vekta
3. Chuja makusanyo yanayolingana na kielelezo
4. Futa makusanyo yote yanayolingana
5. Rekodi kila kufutwa: `"Deleted collection {name}"`
6. Rekodi ya jumla: `"Deleted {count} collection(s) for {user}/{collection}"`

**Mfano:**
```
Collections in store:
- d_alice_papers_384
- d_alice_papers_768
- d_alice_reports_384
- d_bob_papers_384

Delete "papers" for alice:
→ Deletes: d_alice_papers_384, d_alice_papers_768
→ Keeps: d_alice_reports_384, d_bob_papers_384
```

**Sababu:**
Inahakikisha usafishaji kamili wa aina zote za vipimo.
Ulinganishaji wa muundo huuzuia kufutwa kwa makusudi kwa mkusanyiko usiohusiana.
Operesheni ya atomu kutoka kwa mtazamo wa mtumiaji (vipimo vyote hufutwa pamoja).

## Tabia za Utendaji

### Operesheni za Kawaida

**Uundaji wa Mkusanyiko:**
✓ Inarudisha mafanikio mara moja.
✓ Hakuna uhifadhi wa kimwili unaoombwa.
✓ Operesheni ya haraka (hakuna pembejeo/patto la nyuma).

**Uandishi wa Kwanza:**
✓ Huunda mkusanyiko na kipimo sahihi.
✓ Huwa polepole kidogo kwa sababu ya gharama ya uundaji wa mkusanyiko.
✓ Uandishi wa baadaye kwenye kipimo sawa huwa wa haraka.

**Umasilisho Kabla ya Uandishi Wowote:**
✓ Inarudisha matokeo tupu.
✓ Hakuna makosa au ubaguzi.
✓ Mfumo unaendelea kuwa thabiti.

**Uandishi Mseto wa Vipimo:**
✓ Huunda moja kwa moja makusanyiko tofauti kwa kila kipimo.
✓ Kila kipimo kimetengwa katika mkusanyiko wake mwenyewe.
✓ Hakuna migogoro ya kipimo au makosa ya muundo.

**Ufutaji wa Mkusanyiko:**
✓ Huondoa aina zote za vipimo.
✓ Usafishaji kamili.
✓ Hakuna makusanyiko yaliyotelekezwa.

### Hali Maalum

**Miundo Mbalimbali ya Uingizaji:**
```
Scenario: User switches from model A (384-dim) to model B (768-dim)
Behavior:
- Both dimensions coexist in separate collections
- Old data (384-dim) remains queryable with 384-dim vectors
- New data (768-dim) queryable with 768-dim vectors
- Cross-dimension queries return results only for matching dimension
```

**Uandikaji wa Kwanza Unaofanyika Pamoja:**
```
Scenario: Multiple processes write to same collection simultaneously
Behavior:
- Each process checks for existence before creating
- Most vector stores handle concurrent creation gracefully
- If race condition occurs, second create is typically idempotent
- Final state: Collection exists and both writes succeed
```

**Uhamisho wa Vipimo:**
```
Scenario: User wants to migrate from 384-dim to 768-dim embeddings
Behavior:
- No automatic migration
- Old collection (384-dim) persists
- New collection (768-dim) created on first new write
- Both dimensions remain accessible
- Manual deletion of old dimension collections possible
```

**Maswali ya Mkusanyiko Tupu:**
```
Scenario: Query a collection that has never received data
Behavior:
- Collection doesn't exist (never created)
- Query returns empty list
- No error state
- System logs: "Collection does not exist, returning empty results"
```

## Maelekezo ya Utendaji

### Maelezo Maalum ya Hifadhi ya Data

**Qdrant:**
Hutumia `collection_exists()` kwa upangaji wa kuangalia uwepo
Hutumia `get_collections()` kwa orodha wakati wa kufuta
Uundaji wa mkusanyiko unahitaji `VectorParams(size=dim, distance=Distance.COSINE)`

**Pinecone:**
Hutumia `has_index()` kwa upangaji wa kuangalia uwepo
Hutumia `list_indexes()` kwa orodha wakati wa kufuta
Uundaji wa faharasa unahitaji kusubiri hali ya "tayari"
Vipimo vya seva zisizo na utunzaji vimepangwa na eneo la wingu

**Milvus:**
Darasa za moja kwa moja (`DocVectors`, `EntityVectors`) husimamia mzunguko wa maisha
Kumbukumbu ya ndani `self.collections[(dim, user, collection)]` kwa utendaji
Majina ya mkusanyiko husafishwa (herufi na nambari pekee + alama ya nukta)
Inasaidia schema na vitambulisho ambavyo huongezeka kiotomatiki

### Mambo ya Kuzingatia ya Utendaji

**Ucheleweshaji wa Uandikishaji wa Kwanza:**
Gharama ya ziada kutokana na uundaji wa mkusanyiko
Qdrant: ~100-500ms
Pinecone: ~10-30 sekunde (utayarishaji wa seva zisizo na utunzaji)
Milvus: ~500-2000ms (pamoja na uwekaji wa faharasa)

**Utendaji wa Umasilisho:**
Uangaliaji wa uwepo unaongeza gharama ndogo (~1-10ms)
Hakuna athari ya utendaji mara tu mkusanyiko ukiwepo
Kila mkusanyiko wa vipimo unafanywa kazi kwa kujitegemea

**Gharama ya Hifadhi:**
Meta-data ndogo kwa kila mkusanyiko
Gharama kuu ni kwa kila kipimo
Ulinganisho: Nafasi ya hifadhi dhidi ya uwezekano wa vipimo

## Mambo ya Kuzingatia ya Baadaye

**Uunganishaji Otomatiki wa Vipimo:**
Inaweza kuongeza mchakato wa asilia wa kutambua na kuunganisha toleo lisilo la vipimo
Itahitaji kuweka upya au kupunguza vipimo

**Unyonyaji wa Vipimo:**
Inaweza kuonyesha API ya kuorodhesha vipimo vyote vinavyotumika kwa mkusanyiko
Ni muhimu kwa utawala na ufuatiliaji

**Upendeleo wa Vipimo vya Msingi:**
Inaweza kufuatilia kipimo "cha msingi" kwa kila mkusanyiko
Tumia kwa masilisho wakati hali ya kipimo haipatikani

**Mgao wa Hifadhi:**
Inaweza kuhitaji mipaka ya kipimo kwa kila mkusanyiko
Kuzuia ongezeko la toleo la vipimo

## Maelekezo ya Uhamishaji

**Kutoka kwa Mfumo wa Zamani wa Jina la Kipimo:**
Mkusanyiko wa zamani: `d_{user}_{collection}` (hakuna jina la kipimo)
Mkusanyiko mpya: `d_{user}_{collection}_{dim}` (na jina la kipimo)
Hakuna uhamishaji otomatiki - mkusanyiko wa zamani wanaendelea kuwa na ufikiaji
Fikiria programu ya uhamishaji ya mwongozo ikiwa inahitajika
Unaweza kuendesha mifumo miwili ya majina kwa wakati mmoja

## Marejeleo

Usimamizi wa Mkusanyiko: `docs/tech-specs/collection-management.md`
Schema ya Hifadhi: `trustgraph-base/trustgraph/schema/services/storage.py`
Huduma ya Maktaba: `trustgraph-flow/trustgraph/librarian/service.py`
