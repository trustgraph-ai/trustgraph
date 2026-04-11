<<<<<<< HEAD
# Asili ya Data Wakati wa Utoaji: Safu ya Chanzo

## Muhtasari

Hati hii ina rekodi za maelezo kuhusu asili ya data wakati wa utoaji kwa ajili ya kazi ya maelezo ya baadaye. Asili ya data wakati wa utoaji inarejelea "safu ya chanzo" - ambako data ilitoka awali, jinsi ilivyochukuliwa na kubadilishwa.

Hii ni tofauti na asili ya data wakati wa kuulizia (angalia `query-time-provenance.md`) ambayo inarejelea utaratibu wa akili wa mhusika.

## Tatizo

### Utendaji wa Sasa

Hivi sasa, asili ya data inafanya kazi kama ifuatavyo:
Meta-data ya hati huhifadhiwa kama triple za RDF katika grafu ya maarifa.
Kitambulisho cha hati huunganisha meta-data na hati, hivyo hati inaonekana kama node katika grafu.
Wakati uhusiano (maelezo/ukweli) unachukuliwa kutoka kwa hati, uhusiano wa `subjectOf` huunganisha uhusiano uliochukuliwa na hati ya chanzo.

### Matatizo ya Mbinu ya Sasa

1. **Upakiaji wa meta-data unaorudia:** Meta-data ya hati huunganishwa na kupakiwa mara kwa mara na kila kundi la triple zilizochukuliwa kutoka kwa hati hiyo. Hii ni matumizi ya rasilimali na kurudia - meta-data sawa husafiri kama mizigo na kila pato la utoaji.

2. **Asili ya data ya juu:** Uhusiano wa `subjectOf` wa sasa huunganisha tu ukweli moja kwa moja na hati ya juu. Hakuna uonevu katika mnyororo wa mabadiliko - ukweli huo ulichukuliwa kutoka kwa ukurasa gani, sehemu gani, mbinu gani ya utoaji iliyotumika.

### Hali Inayotakikana

1. **Pakia meta-data mara moja:** Meta-data ya hati inapaswa kupakiwa mara moja na kuunganishwa na node ya juu ya hati, sio kurudiwa na kila kundi la triple.

2. **Grafu ya asili ya data iliyo na maelezo:** Rekodi mnyororo kamili wa mabadiliko kutoka kwa hati ya chanzo hadi kwa vitu vyote vya kati hadi kwa ukweli uliopatikana. Kwa mfano, mabadiliko ya hati ya PDF:
=======
# Asili ya Data Wakati wa Uvunaji: Safu ya Chanzo

## Muhtasari

Hati hii ina rekodi za maelezo kuhusu asili ya data wakati wa uvunaji kwa ajili ya kazi zijazo za kubuni. Asili ya data wakati wa uvunaji inarejelea "safu ya chanzo" - ambako data ilitoka awali, jinsi ilivyovunwa na kubadilishwa.

Hii ni tofauti na asili ya data wakati wa utafutaji (angalia `query-time-provenance.md`) ambayo inarejelea hoja za msimuizi.

## Tatizo

### Utendaji Sasa

Hivi sasa, asili ya data inafanya kazi kama ifuatavyo:
Meta-data ya hati inahifadhiwa kama triple za RDF katika grafu ya maarifa.
Kitambulisho cha hati (document ID) huunganisha meta-data na hati, hivyo hati inaonekana kama nodi katika grafu.
Wakati uhusiano (relationships/facts) unavyovunwa kutoka kwa hati, uhusiano wa `subjectOf` huunganisha uhusiano uliovunwa na hati ya asili.

### Matatizo ya Mbinu Hali

1. **Upakiaji wa meta-data unaorudia-rudia:** Meta-data ya hati huunganishwa na kupakiwa mara kwa mara na kila kundi la triple zinazovunwa kutoka kwa hati hiyo. Hii ni matumizi ya rasilimali na kurudia - meta-data sawa husafiri kama mizigo na kila matokeo ya uvunaji.

2. **Asili ya data ya kawaida:** Uhusiano wa `subjectOf` unaoonekana sasa huunganisha tu ukweli moja kwa moja na hati ya juu. Hakuna uwazi kuhusu mnyororo wa mabadiliko - ukurasa gani ukweli ulikuja, kipande gani, njia gani ya uvunaji iliyotumika.

### Hali Inayotakikana

1. **Pakia meta-data mara moja:** Meta-data ya hati inapaswa kupakiwa mara moja na kuunganishwa na nodi ya hati ya juu, sio kurudiwa na kila kundi la triple.

2. **Grafu ya asili ya data yenye maelezo:** Rekodi mnyororo kamili wa mabadiliko kutoka kwa hati ya asili kupitia kwa vitu vyote vya kati hadi kwa ukweli uliovunwa. Kwa mfano, mabadiliko ya hati ya PDF:
>>>>>>> 82edf2d (New md files from RunPod)

   ```
   PDF file (source document with metadata)
     → Page 1 (decoded text)
       → Chunk 1
         → Extracted edge/fact (via subjectOf)
         → Extracted edge/fact
       → Chunk 2
         → Extracted edge/fact
     → Page 2
       → Chunk 3
         → ...
   ```

3. **Hifadhi iliyounganishwa:** Mfumo wa uhusiano wa asili (provenance DAG) huhifadhiwa katika mfumo sawa wa maarifa kama maarifa yaliyopatikana. Hii inaruhusu uhusiano wa asili kuchunguzwa kwa njia ile ile kama maarifa - kufuata miundo kurudi nyuma kutoka kwa ukweli wowote hadi mahali pake halisi.

4. **Kitambulisho cha kudumu:** Kila kitu (artifact) cha kati (ukurasa, sehemu) kina kitambulisho cha kudumu kama node katika mfumo.

<<<<<<< HEAD
5. **Uunganisho wa mzazi-mtoto:** Hati zilizoundwa zinaunganishwa na wazazi wao hadi kwenye hati ya asili ya juu kwa kutumia aina za uhusiano sawa.

6. **Uhusiano sahihi wa ukweli:** Uhusiano wa `subjectOf` kwenye miundo iliyopatikana unaelekeza kwenye mzazi wa karibu (sehemu), sio kwenye hati ya juu. Uhusiano wa asili kamili hupatikana kwa kutembea juu ya DAG.
=======
5. **Uunganisho wa mzazi-mtoto:** Hati zilizoundwa zinaunganishwa na wazazi wao hadi hati ya asili ya juu zaidi kwa kutumia aina za uhusiano sawa.

6. **Uhusiano sahihi wa ukweli:** Uhusiano wa `subjectOf` kwenye miundo iliyopatikana unaelekeza kwa mzazi wa karibu (sehemu), sio hati ya juu. Uhusiano wa asili kamili hupatikana kwa kutembea juu ya DAG.
>>>>>>> 82edf2d (New md files from RunPod)

## Matumizi

### UC1: Uhusiano wa Chanzo katika Majibu ya GraphRAG

**Hali:** Mtumiaji hufanya swali la GraphRAG na kupokea jibu kutoka kwa programu (agent).

**Mchakato:**
1. Mtumiaji huwasilisha swali kwa programu ya GraphRAG.
2. Programu inapata ukweli unaohusiana kutoka kwa mfumo wa maarifa ili kuunda jibu.
3. Kulingana na vipimo vya uhusiano wa asili wakati wa swali, programu huripoti ukweli ambao ulichangia jibu.
4. Kila ukweli unaunganishwa na sehemu yake ya asili kupitia mfumo wa uhusiano wa asili.
5. Sehemu zinaunganishwa na kurasa, kurasa zinaunganishwa na hati za asili.

**Matokeo ya Uzoefu wa Mtumiaji (UX):** Kiolesura huonyesha jibu la LLM pamoja na uhusiano wa chanzo. Mtumiaji anaweza:
Kuona ukweli ambao uliunga mkono jibu.
Kuchunguza kutoka kwa ukweli → sehemu → kurasa → hati.
Kusoma hati za asili ili kuthibitisha madai.
Kuelewa hasa wapi katika hati (ukurasa gani, sehemu gani) ukweli ulitoka.

**Faida:** Watumiaji wanaweza kuthibitisha majibu yaliyozalishwa na AI dhidi ya vyanzo vya msingi, kuunda uaminifu na kuwezesha ukaguzi wa ukweli.

### UC2: Kurekebisha Ubora wa Upatikanaji

<<<<<<< HEAD
Ukweli unaonekana kuwa mbaya. Tembelea kurudi nyuma kupitia sehemu → ukurasa → hati ili kuona maandishi ya asili. Je, ilikuwa upatikanaji mbaya, au chanzo kilikuwa kibaya?

### UC3: Upatikanaji wa Kurekebishwa

Hati ya asili inasasishwa. Ni sehemu/ukweli gani uliotokana nayo? Ghairi na uundue tena tu zile, badala ya kuchakata kila kitu.

### UC4: Ufutilishaji wa Data / Haki ya Kusahau

Hati ya asili lazima iondolewe (GDPR, kisheria, n.k.). Tembelea DAG ili kupata na kuondoa ukweli wote uliotokana.

### UC5: Suluhisho la Mzozo

Ushawishi mbili unapingana. Tembelea zote kurudi kwenye vyanzo vyao ili kuelewa kwa nini na uamue ni ipi ya kuamini (chanzo cha mamlaka zaidi, cha hivi karibuni, n.k.).

### UC6: Uzito wa Uamuzi wa Chanzo

Vyanzo vingine ni vya mamlaka kuliko vingine. Ushawishi unaweza kupimwa au kuchujwa kulingana na uamuzi/ubora wa hati zao za asili.
=======
Ukweli unaonekana kuwa mbaya. Rudi nyuma kupitia sehemu → ukurasa → hati ili kuona maandishi ya asili. Je, ilikuwa upatikanaji mbaya, au chanzo kilikuwa kibaya?

### UC3: Upatikanaji wa Kurekebishwa

Hati ya asili inasasishwa. Ni sehemu/ukweli zipi zilizotokana nayo? Ghairi na uundue tena zile tu, badala ya kuchakata kila kitu.

### UC4: Ufutilishaji wa Data / Haki ya Kusahau

Hati ya asili lazima iondolewe (GDPR, kisheria, n.k.). Tembea kwenye DAG ili kupata na kuondoa ukweli wote uliotokana.

### UC5: Suluhisho la Mzozo

Ushawishi mbili unapingana. Rudi nyuma kwa vyanzo vyake ili kuelewa kwa nini na uamue ni ipi ya kuamini (chanzo cha mamlaka zaidi, cha hivi karibuni, n.k.).

### UC6: Uzito wa Mamlaka ya Chanzo

Vyanzo vingine ni vya mamlaka kuliko vingine. Ushawishi unaweza kupimwa au kuchujwa kulingana na mamlaka/ubora wa hati zake za asili.
>>>>>>> 82edf2d (New md files from RunPod)

### UC7: Ulinganisho wa Mfumo wa Upatikanaji

Linganisha matokeo kutoka kwa mbinu/matoleo tofauti ya upatikanaji. Mfumo wa upatikanaji upi uliunda ukweli bora kutoka kwa chanzo kimoja?

## Maeneo ya Uunganisho

### Msimamizi wa Maktaba

<<<<<<< HEAD
Kifaa cha msimamizi wa maktaba hutoa tayari uhifadhi wa hati na kitambulisho cha kipekee cha hati. Mfumo wa asili unajumuishwa na miundombinu hii iliyopo.

#### Uwezo Ulioopo (tayari umetekelezwa)

**Uunganisho wa Hati ya Mzazi-Mtoto:**
=======
Kifaa cha msimamizi wa maktaba tayari hutoa uhifadhi wa hati pamoja na kitambulisho cha kipekee cha hati. Mfumo wa asili unajumuishwa na miundombinu hii iliyopo.

#### Uwezo Ulioopo (tayari umetekelezwa)

**Uunganisho wa Hati za Mzazi na Mtoto:**
>>>>>>> 82edf2d (New md files from RunPod)
`parent_id` field katika `DocumentMetadata` - huunganisha hati ya mtoto na hati ya mzazi
`document_type` field - maadili: `"source"` (asili) au `"extracted"` (iliyotokana)
`add-child-document` API - huunda hati ya mtoto na `document_type = "extracted"` moja kwa moja
`list-children` API - hurudisha hati zote za watoto za hati ya mzazi
Ufutilishaji wa mfuatano - kuondoa hati ya mzazi huondoa moja kwa moja hati zote za watoto

**Kitambulisho cha Hati:**
Kitambulisho cha hati huamuliwa na mteja (hayajaumbwa kiotomatiki)
Hati zimepangwa kwa `(user, document_id)` iliyounganishwa katika Cassandra
Kitambulisho cha kitu (UUIDs) huundwa ndani kwa uhifadhi wa blob

**Usaidizi wa MetaData:**
`metadata: list[Triple]` field - triples za RDF kwa metaData iliyopangwa
`title`, `comments`, `tags` - metaData ya msingi ya hati
`time` - wakati, `kind` - aina ya MIME

**Muundo wa Uhifadhi:**
MetaData huhifadhiwa katika Cassandra (`librarian` keyspace, `document` meza)
Yaliyomo huhifadhiwa katika uhifadhi wa blob wa MinIO/S3 (`library` ndoo)
<<<<<<< HEAD
Uwasilishaji mahiri wa yaliyomo: hati < 2MB zimejumuishwa, hati kubwa zaidi hutiririshwa
=======
Utoaji wa yaliyomo mahiri: hati < 2MB zimejumuishwa, hati kubwa zaidi hutiririshwa
>>>>>>> 82edf2d (New md files from RunPod)

#### Faili Muhimu

`trustgraph-flow/trustgraph/librarian/librarian.py` - Operesheni muhimu za msimamizi wa maktaba
`trustgraph-flow/trustgraph/librarian/service.py` - Mchakato wa huduma, upakaji hati
`trustgraph-flow/trustgraph/tables/library.py` - Duka la meza ya Cassandra
`trustgraph-base/trustgraph/schema/services/library.py` - Ufafanuzi wa mpango

<<<<<<< HEAD
#### Mapungufu Yanayohitaji Kusuluhishwa

Msimamizi wa maktaba una vipengele muhimu lakini kwa sasa:
1. Uunganisho wa mzazi-mtoto ni safu moja tu - hakuna msaada wa utambuzi wa DAG wa ngazi nyingi
2. Hakuna hesabu ya kawaida ya aina ya uhusiano (e.g., `derivedFrom`, `extractedFrom`)
3. MetaData ya asili (mbinu ya uondoaji, uaminifu, nafasi ya kipande) hayajaainishwa
4. Hakuna API ya kuuliza ili kutambua mnyororo kamili wa asili kutoka kwa ukweli hadi chanzo

## Muundo wa Mtiririko wa Utoaji hadi Utoaji

Kila mchakato katika mstari huu unafuata mfumo unaoendana:
Kupokea kitambulisho cha hati kutoka kwa chanzo
=======
#### Mapungufu Yanayohitaji Kushughulikiwa

Msimamizi wa maktaba una vipengele muhimu lakini kwa sasa:
1. Uunganisho wa mzazi-mtoto ni safu moja tu - hakuna msaada wa uvukaji wa DAG wa ngazi nyingi
2. Hakuna hesabu ya kawaida ya aina ya uhusiano (e.g., `derivedFrom`, `extractedFrom`)
3. MetaData ya asili (njia ya uondoaji, uaminifu, nafasi ya kipande) hayajawekwa kikao
4. Hakuna API ya kuuliza ili kuvuka mnyororo kamili wa asili kutoka kwa ukweli hadi chanzo

## Muundo wa Mtiririko wa Kila Hatua

Kila mchakato katika mstari huu unafuata mfumo unaoendana:
Kupokea kitambulisho cha hati kutoka kwa mfumo wa juu
>>>>>>> 82edf2d (New md files from RunPod)
Kuchukua yaliyomo kutoka kwa msimamizi wa maktaba
Kutoa vifaa vya watoto
Kwa kila mtoto: kuhifadhi kwenye msimamizi wa maktaba, kutuma upau kwenye grafu, kusonga kitambulisho mbele

### Mitiririko ya Uendeshaji

Kuna mitiririko miwili kulingana na aina ya hati:

#### Mtiririko wa Hati ya PDF

```
┌─────────────────────────────────────────────────────────────────────────┐
│ Librarian (initiate processing)                                         │
│   1. Emit root document metadata to knowledge graph (once)              │
│   2. Send root document ID to PDF extractor                             │
└─────────────────────────────────────────────────────────────────────────┘
                                    │
                                    ▼
┌─────────────────────────────────────────────────────────────────────────┐
│ PDF Extractor (per page)                                                │
│   1. Fetch PDF content from librarian using document ID                 │
│   2. Extract pages as text                                              │
│   3. For each page:                                                     │
│      a. Save page as child document in librarian (parent = root doc)   │
│      b. Emit parent-child edge to knowledge graph                       │
│      c. Send page document ID to chunker                                │
└─────────────────────────────────────────────────────────────────────────┘
                                    │
                                    ▼
┌─────────────────────────────────────────────────────────────────────────┐
│ Chunker (per chunk)                                                     │
│   1. Fetch page content from librarian using document ID                │
│   2. Split text into chunks                                             │
│   3. For each chunk:                                                    │
│      a. Save chunk as child document in librarian (parent = page)      │
│      b. Emit parent-child edge to knowledge graph                       │
│      c. Send chunk document ID + chunk content to next processor        │
└─────────────────────────────────────────────────────────────────────────┘
                                    │
                                    ▼
          ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─
          Post-chunker optimization: messages carry both
          chunk ID (for provenance) and content (to avoid
          librarian round-trip). Chunks are small (2-4KB).
          ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─
                                    │
                                    ▼
┌─────────────────────────────────────────────────────────────────────────┐
│ Knowledge Extractor (per chunk)                                         │
│   1. Receive chunk ID + content directly (no librarian fetch needed)   │
│   2. Extract facts/triples and embeddings from chunk content            │
│   3. For each triple:                                                   │
│      a. Emit triple to knowledge graph                                  │
│      b. Emit reified edge linking triple → chunk ID (edge pointing     │
│         to edge - first use of reification support)                     │
│   4. For each embedding:                                                │
│      a. Emit embedding with its entity ID                               │
│      b. Link entity ID → chunk ID in knowledge graph                   │
└─────────────────────────────────────────────────────────────────────────┘
```

#### Mtiririko wa Nyaraka za Nakshata

<<<<<<< HEAD
Nyaraka za nakshata huenda moja kwa moja kwenye sehemu ya "chunker" na hazitumii programu ya kutenganisha faili za PDF:
=======
Nyaraka za nakshata huenda moja kwa moja kwenye sehemu ya "chunker" na hazitumii programu ya kutolea maelezo kutoka kwa faili za PDF:
>>>>>>> 82edf2d (New md files from RunPod)

```
┌─────────────────────────────────────────────────────────────────────────┐
│ Librarian (initiate processing)                                         │
│   1. Emit root document metadata to knowledge graph (once)              │
│   2. Send root document ID directly to chunker (skip PDF extractor)    │
└─────────────────────────────────────────────────────────────────────────┘
                                    │
                                    ▼
┌─────────────────────────────────────────────────────────────────────────┐
│ Chunker (per chunk)                                                     │
│   1. Fetch text content from librarian using document ID                │
│   2. Split text into chunks                                             │
│   3. For each chunk:                                                    │
│      a. Save chunk as child document in librarian (parent = root doc) │
│      b. Emit parent-child edge to knowledge graph                       │
│      c. Send chunk document ID + chunk content to next processor        │
└─────────────────────────────────────────────────────────────────────────┘
                                    │
                                    ▼
┌─────────────────────────────────────────────────────────────────────────┐
│ Knowledge Extractor                                                     │
│   (same as PDF flow)                                                    │
└─────────────────────────────────────────────────────────────────────────┘
```

<<<<<<< HEAD
DAG iliyotokea ni ya kiwango kimoja chini:
=======
Matokeo ya DAG (Grafu ya Kuelekea Mbele) ni ngazi moja chini:
>>>>>>> 82edf2d (New md files from RunPod)

```
PDF:  Document → Pages → Chunks → Triples/Embeddings
Text: Document → Chunks → Triples/Embeddings
```

<<<<<<< HEAD
Ubunifu unaoendana na matumizi ya aina zote, kwa sababu mfumo wa kugawanya (chunker) hutumia data yake ya pembejeo kwa njia ya jumla - hutumia kitambulisho chochote cha hati kinachopokelewa kama mzazi, bila kujali kama hiyo ni hati ya asili au ukurasa.
=======
Ubunifu unaoendana na matumizi ya aina zote, kwa sababu mfumo wa kugawanya (chunker) hutumia data yake ya pembeni kwa njia ya jumla - hutumia kitambulisho chochote cha hati kinachopokelewa kama mzazi, bila kujali kama hiyo ni hati ya asili au ukurasa.
>>>>>>> 82edf2d (New md files from RunPod)

### Mpango wa Meta-data (PROV-O)

Meta-data ya asili hutumia ontolojia ya W3C PROV-O. Hii hutoa msamiati wa kawaida na inawezesha usaini/uthibitishaji wa matokeo ya utoaji katika siku zijazo.

### Dhana Zikuu za PROV-O

| Aina ya PROV-O | Matumizi katika TrustGraph |
|-------------|------------------|
| `prov:Entity` | Hati, Ukurasa, Sehemu, Triple, Uingizwaji |
<<<<<<< HEAD
| `prov:Activity` | Mifano ya operesheni za utoaji |
=======
| `prov:Activity` | Mifano ya shughuli za utoaji |
>>>>>>> 82edf2d (New md files from RunPod)
| `prov:Agent` | Vipengele vya TG (mfumo wa utoaji wa PDF, mfumo wa kugawanya, n.k.) pamoja na matoleo |

### Mahusiano ya PROV-O

<<<<<<< HEAD
| Kifurushi | Maana | Mfano |
|-----------|---------|---------|
| `prov:wasDerivedFrom` | Kitu kinachotokana na kitu kingine | Ukurasa ulikuwa umetokana na Hati |
| `prov:wasGeneratedBy` | Kitu kilichoundwa na shughuli | Ukurasa ulikuwa umelindwa na Shughuli ya Utoaji wa PDF |
=======
| Kifurushi | Maana | Kifaa |
|-----------|---------|---------|
| `prov:wasDerivedFrom` | Kitu kinachotokana na kitu kingine | Ukurasa ulitokana na Hati |
| `prov:wasGeneratedBy` | Kitu kilichoanzishwa na shughuli | Ukurasa ulianzishwa na Shughuli ya Utoaji wa PDF |
>>>>>>> 82edf2d (New md files from RunPod)
| `prov:used` | Shughuli ilitumia kitu kama pembejeo | Shughuli ya Utoaji wa PDF ilitumia Hati |
| `prov:wasAssociatedWith` | Shughuli ilifanywa na wakala | Shughuli ya Utoaji wa PDF ilihusishwa na tg:PDFExtractor |

### Meta-data katika Kila Ngazi

<<<<<<< HEAD
**Hati ya Asili (inatoolewa na Librarian):**
=======
**Hati ya Asili (inatoa Librarian):**
>>>>>>> 82edf2d (New md files from RunPod)
```
doc:123 a prov:Entity .
doc:123 dc:title "Research Paper" .
doc:123 dc:source <https://example.com/paper.pdf> .
doc:123 dc:date "2024-01-15" .
doc:123 dc:creator "Author Name" .
doc:123 tg:pageCount 42 .
doc:123 tg:mimeType "application/pdf" .
```

**Ukurasa (uliochukuliwa na programu ya kuchambua faili za PDF):**
```
page:123-1 a prov:Entity .
page:123-1 prov:wasDerivedFrom doc:123 .
page:123-1 prov:wasGeneratedBy activity:pdf-extract-456 .
page:123-1 tg:pageNumber 1 .

activity:pdf-extract-456 a prov:Activity .
activity:pdf-extract-456 prov:used doc:123 .
activity:pdf-extract-456 prov:wasAssociatedWith tg:PDFExtractor .
activity:pdf-extract-456 tg:componentVersion "1.2.3" .
activity:pdf-extract-456 prov:startedAtTime "2024-01-15T10:30:00Z" .
```

<<<<<<< HEAD
**Sehemu (imetolewa na Chunker):**
=======
**Sehemu (inatoolewa na Chunker):**
>>>>>>> 82edf2d (New md files from RunPod)
```
chunk:123-1-1 a prov:Entity .
chunk:123-1-1 prov:wasDerivedFrom page:123-1 .
chunk:123-1-1 prov:wasGeneratedBy activity:chunk-789 .
chunk:123-1-1 tg:chunkIndex 1 .
chunk:123-1-1 tg:charOffset 0 .
chunk:123-1-1 tg:charLength 2048 .

activity:chunk-789 a prov:Activity .
activity:chunk-789 prov:used page:123-1 .
activity:chunk-789 prov:wasAssociatedWith tg:Chunker .
activity:chunk-789 tg:componentVersion "1.0.0" .
activity:chunk-789 tg:chunkSize 2048 .
activity:chunk-789 tg:chunkOverlap 200 .
```

**Tatu (imetolewa na Mvumbuzi wa Maarifa):**
```
# The extracted triple (edge)
entity:JohnSmith rel:worksAt entity:AcmeCorp .

# Subgraph containing the extracted triples
subgraph:001 tg:contains <<entity:JohnSmith rel:worksAt entity:AcmeCorp>> .
subgraph:001 prov:wasDerivedFrom chunk:123-1-1 .
subgraph:001 prov:wasGeneratedBy activity:extract-999 .

activity:extract-999 a prov:Activity .
activity:extract-999 prov:used chunk:123-1-1 .
activity:extract-999 prov:wasAssociatedWith tg:KnowledgeExtractor .
activity:extract-999 tg:componentVersion "2.1.0" .
activity:extract-999 tg:llmModel "claude-3" .
activity:extract-999 tg:ontology <http://example.org/ontologies/business-v1> .
```

**Uingizwaji (hifadhiwa katika hifadhi ya vekta, sio hifadhi ya triple):**

Uingizwaji huhifadhiwa katika hifadhi ya vekta pamoja na metadata, sio kama triple za RDF. Kila rekodi ya uingizwaji ina:

<<<<<<< HEAD
| Nguvu | Maelezo | Mfano |
|-------|-------------|---------|
| vekta | Vektali ya uingizwaji | [0.123, -0.456, ...] |
| kitu | URI ya node ambayo uingizwaji unawakilisha | `entity:JohnSmith` |
| kitambulisho_cha_sehemu | Sehemu ya asili (asili) | `chunk:123-1-1` |
| mfumo | Mfumo wa uingizwaji uliotumika | `text-embedding-ada-002` |
| toleo_la_komponenti | Toleo la programu ya uingizwaji | `1.0.0` |

Nguvu ya `entity` huunganisha uingizwaji na grafu ya maarifa (URI ya node). Nguvu ya `chunk_id` hutoa asili kurudi kwa sehemu ya asili, na kuwezesha ufuatiliaji hadi kwenye hati asili.

#### Miondoko ya Jina ya TrustGraph

Maneno maalum chini ya nafasi ya `tg:` kwa metadata maalum ya uondoaji:

| Neno | Doman | Maelezo |
|-----------|--------|-------------|
| `tg:contains` | Subgraph | Inaashiria triple iliyo ndani ya subgraph hii ya uondoaji |
| `tg:pageCount` | Hati | Idadi jumla ya kurasa katika hati ya asili |
| `tg:mimeType` | Hati | Aina ya MIME ya hati ya asili |
| `tg:pageNumber` | Ukurasa | Namba ya ukurasa katika hati ya asili |
| `tg:chunkIndex` | Sehemu | Index ya sehemu ndani ya sehemu ya wazazi |
| `tg:charOffset` | Sehemu | Marekebisho ya herufi katika maandishi ya wazazi |
| `tg:charLength` | Sehemu | Urefu wa sehemu katika herufi |
| `tg:chunkSize` | Shughuli | Ukubwa uliopangwa wa sehemu |
| `tg:chunkOverlap` | Shughuli | Ulinganishi kati ya sehemu |
| `tg:componentVersion` | Shughuli | Toleo la komponenti ya TG |
| `tg:llmModel` | Shughuli | LLM iliyotumika kwa uondoaji |
| `tg:ontology` | Shughuli | Ontology iliyotumika kuongoza uondoaji |
| `tg:embeddingModel` | Shughuli | Mfumo uliotumika kwa uingizwaji |
| `tg:sourceText` | Tamko | Nakala kamili kutoka ambayo triple iliondolewa |
| `tg:sourceCharOffset` | Tamko | Marekebisho ya herufi ndani ya sehemu ambapo nakala ya asili huanza |
| `tg:sourceCharLength` | Tamko | Urefu wa nakala ya asili katika herufi |

#### Uanzishaji wa Dhana (Kwa Mkusanyiko Kila Kila)

Grafu ya maarifa ni ya aina ya ontology na inaanzishwa kuwa tupu. Wakati wa kuandika data ya asili ya PROV-O kwa mkusanyiko kwa mara ya kwanza, dhana lazima ianzishwe na lebo za RDF kwa madarasa na maneno yote. Hii inahakikisha onyesho linalosoma kwa binadamu katika maswali na UI.
=======
| Shamba | Maelezo | Mfano |
|-------|-------------|---------|
| vekta | Vakta ya uingizwaji | [0.123, -0.456, ...] |
| kitu | URI ya node ambayo uingizwaji unawakilisha | `entity:JohnSmith` |
| kitambulisho_cha_sehemu | Sehemu ya asili (asili) | `chunk:123-1-1` |
| mfumo | Mfumo wa uingizwaji uliotumika | `text-embedding-ada-002` |
| toleo_la_komponenti | Toleo la mfumo wa uingizwaji wa TG | `1.0.0` |

Shamba la `entity` huunganisha uingizwaji na grafu ya maarifa (URI ya node). Shamba la `chunk_id` hutoa asili kurudi kwa sehemu ya asili, na hivyo kuruhusu ufuatiliaji hadi kwenye hati asili.

#### Miongozo ya Upanuzi wa Nafasi ya TrustGraph

Maneno maalum chini ya nafasi ya `tg:` kwa metadata maalum ya utoaji:

| Dhana | Eneo | Maelezo |
|-----------|--------|-------------|
| `tg:contains` | Subgraph | Inaashiria triple iliyo ndani ya subgraph hii. |
| `tg:pageCount` | Document | Idadi jumla ya kurasa katika hati ya asili. |
| `tg:mimeType` | Document | Aina ya MIME ya hati ya asili. |
| `tg:pageNumber` | Page | Namba ya ukurasa katika hati ya asili. |
| `tg:chunkIndex` | Chunk | Indexi ya chunk ndani ya mzazi. |
| `tg:charOffset` | Chunk | Marekebisho ya herufi katika maandishi ya mzazi. |
| `tg:charLength` | Chunk | Urefu wa chunk katika herufi. |
| `tg:chunkSize` | Activity | Ukubwa wa chunk uliopangwa. |
| `tg:chunkOverlap` | Activity | Uwianifu uliopangwa kati ya chunks. |
| `tg:componentVersion` | Activity | Toleo la kipengele cha TG. |
| `tg:llmModel` | Activity | LLM iliyotumika kwa uondoaji. |
| `tg:ontology` | Activity | URI ya ontology iliyotumika kuongoza uondoaji. |
| `tg:embeddingModel` | Activity | Mfumo uliotumika kwa embeddings. |
| `tg:sourceText` | Statement | Nakala kamili kutoka ambayo triple iliondolewa. |
| `tg:sourceCharOffset` | Statement | Marekebisho ya herufi ndani ya chunk ambapo nakala ya chanzo huanza. |
| `tg:sourceCharLength` | Statement | Urefu wa nakala ya chanzo katika herufi. |

#### Uanzishaji wa Dhana (Kwa Kundi Kila Kimoja)

Grafu ya maarifa ni ya kawaida na huanzishwa kuwa tupu. Wakati wa kuandika data ya asili ya PROV-O kwenye mkusanyiko kwa mara ya kwanza, dhana lazima ianzishwe kwa lebo za RDF kwa madarasa na dhana zote. Hii inahakikisha onyesho linalosoma na binadamu katika maswali na UI.
>>>>>>> 82edf2d (New md files from RunPod)

**Madarasa ya PROV-O:**
```
prov:Entity rdfs:label "Entity" .
prov:Activity rdfs:label "Activity" .
prov:Agent rdfs:label "Agent" .
```

**Predikati za PROV-O:**
```
prov:wasDerivedFrom rdfs:label "was derived from" .
prov:wasGeneratedBy rdfs:label "was generated by" .
prov:used rdfs:label "used" .
prov:wasAssociatedWith rdfs:label "was associated with" .
prov:startedAtTime rdfs:label "started at" .
```

<<<<<<< HEAD
**Predikatendi za TrustGraph:**
=======
**Maneno ya TrustGraph:**
>>>>>>> 82edf2d (New md files from RunPod)
```
tg:contains rdfs:label "contains" .
tg:pageCount rdfs:label "page count" .
tg:mimeType rdfs:label "MIME type" .
tg:pageNumber rdfs:label "page number" .
tg:chunkIndex rdfs:label "chunk index" .
tg:charOffset rdfs:label "character offset" .
tg:charLength rdfs:label "character length" .
tg:chunkSize rdfs:label "chunk size" .
tg:chunkOverlap rdfs:label "chunk overlap" .
tg:componentVersion rdfs:label "component version" .
tg:llmModel rdfs:label "LLM model" .
tg:ontology rdfs:label "ontology" .
tg:embeddingModel rdfs:label "embedding model" .
tg:sourceText rdfs:label "source text" .
tg:sourceCharOffset rdfs:label "source character offset" .
tg:sourceCharLength rdfs:label "source character length" .
```

<<<<<<< HEAD
**Kumbukumbu kuhusu utekelezaji:** Kamusi hii ya kuanzia inapaswa kuwa ya aina ambayo inaweza kuendeshwa mara nyingi bila kuunda nakala. Inaweza kuanzishwa wakati wa usindikaji wa hati ya kwanza katika mkusanyiko, au kama hatua tofauti ya uanzishaji wa mkusanyiko.

#### Asili ya Sehemu Ndogo (Lengo)

Kwa asili ya kina zaidi, itakuwa muhimu kurekodi hasa katika sehemu gani ya kipande ambapo triple ilitokana. Hii inaruhusu:

Kuonyesha maandishi ya asili hasa katika kiolesura (UI)
Kuthibitisha usahihi wa uondoaji dhidi ya asili
Kuchunguza ubora wa uondoaji katika kiwango cha sentensi
=======
**Kumbuka kuhusu utekelezaji:** Msamiati huu wa kuanzia inapaswa kuwa sawa - salama kuendeshwa mara nyingi bila kuunda nakala. Inaweza kuanzishwa wakati wa usindikaji wa hati ya kwanza katika mkusanyiko, au kama hatua tofauti ya uanzishaji wa mkusanyiko.

#### Asili ya Sehemu Ndogo (Lengo)

Kwa asili ya kina zaidi, itakuwa muhimu kurekodi haswa katika sehemu gani ndani ya kipande ambapo triple ilitokana. Hii inawezesha:

Kuonyesha maandishi ya asili haswa katika kiolesura (UI)
Kuangalia usahihi wa utoaji kulingana na asili
Kuchunguza ubora wa utoaji katika kiwango cha sentensi
>>>>>>> 82edf2d (New md files from RunPod)

**Mfano na ufuatiliaji wa nafasi:**
```
# The extracted triple
entity:JohnSmith rel:worksAt entity:AcmeCorp .

# Subgraph with sub-chunk provenance
subgraph:001 tg:contains <<entity:JohnSmith rel:worksAt entity:AcmeCorp>> .
subgraph:001 prov:wasDerivedFrom chunk:123-1-1 .
subgraph:001 tg:sourceText "John Smith has worked at Acme Corp since 2019" .
subgraph:001 tg:sourceCharOffset 1547 .
subgraph:001 tg:sourceCharLength 46 .
```

**Mfano na sehemu ya maandishi (badala):**
```
subgraph:001 tg:contains <<entity:JohnSmith rel:worksAt entity:AcmeCorp>> .
subgraph:001 prov:wasDerivedFrom chunk:123-1-1 .
subgraph:001 tg:sourceRange "1547-1593" .
subgraph:001 tg:sourceText "John Smith has worked at Acme Corp since 2019" .
```

**Mazingatio ya utekelezaji:**

Utaratibu wa kutolea maelezo unaotegemea modeli ya lugha (LLM) huenda usitoe nafasi za herufi kwa kawaida.
Inaweza kuwezekana kuomba LLM irudishe sentensi/maneno ya asili pamoja na vitu vilivyotolewa.
<<<<<<< HEAD
Badala yake, inaweza kufanywa urekebishaji wa ziada ili kulinganisha vitu vilivyotolewa na maandishi ya asili.
Kuna mtego kati ya utata wa utoleaji wa maelezo na kiwango cha uhakikisho.
Inaweza kuwa rahisi kufanikisha kwa kutumia mbinu zilizopangwa kuliko utoleaji wa maelezo wa aina huru unaotegemea LLM.

Hii imewekwa kama lengo la baadaye - uhakikisho wa kimsingi wa kiwango cha sehemu unapaswa kutekelezwa kwanza, na kufuatilia kwa sehemu ndogo kama uboreshaji wa baadaye ikiwa inawezekana.

### Mfumo wa Uhifadhi Mkubwa

Mfumo wa uhakikisho unajengwa hatua kwa hatua wakati hati zinapopitia katika mchakato:

| Hifadhi | Kile kinachohifadhiwa | Madhumuni |
|-------|---------------|---------|
| Msimamizi | Yaliyomo ya hati + viungo vya mzazi-mtoto | Kupata yaliyomo, kufuta kwa mfuatano |
| Grafu ya Maarifa | Miunganisho ya mzazi-mtoto + metadata | Maswali ya uhakikisho, utambuzi wa ukweli |

Hifadhi zote mbili zinahifadhi muundo sawa wa DAG. Msimamizi huhifadhi yaliyomo; grafu huhifadhi uhusiano na inaruhusu maswali ya utaftaji.

### Kanuni Muhimu za Ubunifu

1. **Kitambulisho cha hati kama kitengo cha mchakato** - Wasindikaji hupitisha vitambulisho, sio yaliyomo. Yaliyomo hupatikana kutoka kwa msimamizi wakati inahitajika.

2. **Tolea mara moja katika chanzo** - Metadata imeandikwa kwenye grafu mara moja wakati wa mchakato unaanza, sio kurudiwa baadaye.

3. **Mfumo sawa wa wasindikaji** - Kila wasindikaji hufuata muundo sawa wa kupokea/kupata/kutoa/kuokoa/kutoa/kusonga.

4. **Ujenzi wa hatua kwa hatua wa DAG** - Kila wasindikaji huongeza kiwango chake kwenye DAG. Mnyororo kamili wa uhakikisho unajengwa hatua kwa hatua.

5. **Uboreshaji baada ya kugawanyika** - Baada ya kugawanyika, ujumbe unaambatana na kitambulisho na yaliyomo. Sehemu ndogo (2-4KB), kwa hivyo kuingiza yaliyomo inazuia safari zisizo za lazima za msimamizi wakati inahifadhi uhakikisho kupitia kitambulisho.

## Majukumu ya Utekelezaji

### Marekebisho ya Msimamizi
=======
Au, inaweza kufanywa urekebishaji wa ziada ili kulinganisha vitu vilivyotolewa na maandishi ya asili.
Kuna mtego kati ya utata wa utoleaji wa maelezo na uwazi wa asili.
Inaweza kuwa rahisi kufanikisha kwa kutumia mbinu zilizopangwa kuliko utoleaji wa maelezo wa bure unaotegemea LLM.

Hii imewekwa kama lengo la baadaye - utaratibu wa msingi wa utoleaji wa maelezo wa kiwango cha sehemu unapaswa kutekelezwa kwanza, na kufuatilia kwa sehemu ndogo kama uboreshaji wa baadaye ikiwa inawezekana.

### Mfumo wa Uhifadhi Mkubwa

Mfumo wa DAG wa utoleaji wa maelezo huundwa hatua kwa hatua wakati hati zinapopitia katika mchakato:

| Hifadhi | Kitu Kinachohifadhiwa | Lengo |
|-------|---------------|---------|
| Mkumbaji | Yaliyomo ya hati + viungo vya mzazi-mtoto | Upatikanaji wa yaliyomo, kufuta kwa mfuatano |
| Grafu ya Maarifa | Aina za mzazi-mtoto + metadata | Maswali ya utoleaji wa maelezo, uhusishaji wa ukweli |

Hifadhi zote mbili zinahifadhi muundo sawa wa DAG. Mkumbaji huhifadhi yaliyomo; grafu huhifadhi uhusiano na inaruhusu maswali ya utaftaji.

### Kanuni Muhimu za Ubunifu

1. **Kitambulisho cha hati kama kitengo cha mtiririko** - Wasindikaji hutuma kitambulisho, sio yaliyomo. Yaliyomo hupatikana kutoka kwa mkumbaji wakati inahitajika.

2. **Tolea mara moja katika chanzo** - Metadata imeandikwa kwenye grafu mara moja wakati wa mchakato unaanza, sio kurudiwa baadaye.

3. **Muundo sawa wa wasindikaji** - Kila wasindikaji hufuata muundo sawa wa kupokea/kupata/kutoa/kuokoa/kutoa/kusonga.

4. **Uundaji wa hatua kwa hatua wa DAG** - Kila wasindikaji huongeza kiwango chake kwenye DAG. Mnyororo kamili wa utoleaji wa maelezo huundwa hatua kwa hatua.

5. **Uboreshaji baada ya kugawanyika** - Baada ya kugawanyika, ujumbe unaambatana na kitambulisho na yaliyomo. Sehemu ndogo (2-4KB), kwa hivyo kujumuisha yaliyomo inazuia safari zisizo za lazima za mkumbaji wakati inahifadhi utoleaji wa maelezo kupitia kitambulisho.

## Majukumu ya Utendaji

### Marekebisho ya Mkumbaji
>>>>>>> 82edf2d (New md files from RunPod)

#### Hali ya Sasa

Inaanzisha mchakato wa hati kwa kutuma kitambulisho cha hati kwa wasindikaji wa kwanza.
<<<<<<< HEAD
Hakuna muunganisho na duka la vitriple - metadata huunganishwa na matokeo ya utoleaji.
=======
Hakuna muunganisho na duka la vitri - metadata huunganishwa na matokeo ya utoleaji.
>>>>>>> 82edf2d (New md files from RunPod)
`add-child-document` huunda viungo vya mzazi-mtoto vya kiwango kimoja.
`list-children` hurudisha watoto wa karibu tu.

#### Marekebisho Yanayohitajika

<<<<<<< HEAD
**1. Kiolesura kipya: Muunganisho wa duka la vitriple**

Msimamizi anahitaji kutoa kingo za metadata ya hati moja kwa moja kwenye grafu ya maarifa wakati wa kuanzisha mchakato.
Ongeza mteja/mpublisher wa duka la vitriple kwenye huduma ya msimamizi.
Wakati wa kuanzisha mchakato: toa metadata ya hati ya mizizi kama kingo za grafu (mara moja).

**2. Hesabu ya aina ya hati**
=======
**1. Kiolesura kipya: Muunganisho wa duka la vitri**

Mkumbaji anahitaji kutoa kingo za metadata ya hati moja kwa moja kwenye grafu ya maarifa wakati wa kuanzisha mchakato.
Ongeza mteja/mpublisher wa duka la vitri kwenye huduma ya mkumbaji.
Wakati wa kuanzisha mchakato: toa metadata ya hati ya mizizi kama kingo za grafu (mara moja).

**2. Msamiati wa aina ya hati**
>>>>>>> 82edf2d (New md files from RunPod)

Sanidi maadili ya `document_type` kwa watoto wa hati:
`source` - hati iliyopakiwa asili.
`page` - ukurasa uliotolewa kutoka chanzo (PDF, n.k.).
`chunk` - sehemu ya maandishi iliyotokana na ukurasa au chanzo.

#### Muhtasari wa Marekebisho ya Kiolesura

<<<<<<< HEAD
| Kiolesura | Marekebisho |
|-----------|--------|
| Duka la vitriple | Muunganisho mpya wa kutoka nje - toa kingo za metadata ya hati |
=======
| Kiolesura | Mabadiliko |
|-----------|--------|
| Duka la vitri | Muunganisho mpya wa kutoka nje - toa kingo za metadata ya hati |
>>>>>>> 82edf2d (New md files from RunPod)
| Kuanzisha mchakato | Toa metadata kwenye grafu kabla ya kusonga kitambulisho cha hati |

### Marekebisho ya Mtoa Hati ya PDF

#### Hali ya Sasa

Hupokea yaliyomo ya hati (au mitiririko ya hati kubwa).
Hutolea maandishi kutoka kwa kurasa za PDF.
Hupeleka yaliyomo ya ukurasa kwa mtoa sehemu.
<<<<<<< HEAD
Hakuna mwingiliano na msimamizi au duka la vitriple.

#### Marekebisho Yanayohitajika

**1. Kiolesura kipya: Mteja wa msimamizi**

Mtoa hati ya PDF anahitaji kuhifadhi kila ukurasa kama hati ya mtoto katika msimamizi.
Ongeza mteja wa msimamizi kwenye huduma ya mtoa hati ya PDF.
Kwa kila ukurasa: piga `add-child-document` na mzazi = kitambulisho cha hati ya mizizi.

**2. Kiolesura kipya: Muunganisho wa duka la vitriple**

Mtoa hati ya PDF anahitaji kutoa kingo za mzazi-mtoto kwenye grafu ya maarifa.
Ongeza mteja/mpublisher wa duka la vitriple.
Kwa kila ukurasa: toa kingo inayounganisha hati ya ukurasa na hati ya mzazi.
=======
Hakuna mwingiliano na mkumbaji au duka la vitri.

#### Marekebisho Yanayohitajika

**1. Kiolesura kipya: Mteja wa mkumbaji**

Mtoa hati ya PDF anahitaji kuhifadhi kila ukurasa kama hati ya mtoto katika mkumbaji.
Ongeza mteja wa mkumbaji kwenye huduma ya mtoa hati ya PDF.
Kwa kila ukurasa: piga `add-child-document` na mzazi = kitambulisho cha hati ya mizizi.

**2. Kiolesura kipya: Muunganisho wa duka la vitri**

Mtoa hati ya PDF anahitaji kutoa aina za mzazi-mtoto kwenye grafu ya maarifa.
Ongeza mteja/mpublisher wa duka la vitri.
Kwa kila ukurasa: toa aina inayounganisha ukurasa wa hati na hati ya mzazi.
>>>>>>> 82edf2d (New md files from RunPod)

**3. Badilisha muundo wa matokeo**

Badala ya kusambaza yaliyomo ya ukurasa moja kwa moja, sambaza kitambulisho cha hati ya ukurasa.
<<<<<<< HEAD
Chunker itapata yaliyomo kutoka kwa 'librarian' kwa kutumia kitambulisho.
=======
Chunker itapakua yaliyomo kutoka kwa 'librarian' kwa kutumia kitambulisho.
>>>>>>> 82edf2d (New md files from RunPod)

#### Muhtasari wa Mabadiliko ya Kiolesura

| Kiolesura | Mabadiliko |
|-----------|--------|
| Librarian | Mabadiliko mapya ya kutoka - hifadhi hati za watoto |
<<<<<<< HEAD
| Hifadhi tatu | Mabadiliko mapya ya kutoka - toka miunganisho ya mzazi-mtoto |
=======
| Hifadhi tatu | Mabadiliko mapya ya kutoka - toa miunganisho ya mzazi-mtoto |
>>>>>>> 82edf2d (New md files from RunPod)
| Ujumbe wa pato | Mabadiliko kutoka yaliyomo hadi kitambulisho cha hati |

### Mabadiliko ya Chunker

#### Hali ya Sasa

Yanapokea yaliyomo ya ukurasa/maandishi
<<<<<<< HEAD
Yanagawanyika katika sehemu ndogo
Yanatuma yaliyomo ya sehemu ndogo kwa wasindikaji wa baadaye
=======
Yanagawanywa katika sehemu
Yanatuma yaliyomo ya sehemu kwa wasindikaji wa baadaye
>>>>>>> 82edf2d (New md files from RunPod)
Hakuna mwingiliano na 'librarian' au hifadhi tatu

#### Mabadiliko Yanayohitajika

**1. Badilisha utunzaji wa ingizo**

<<<<<<< HEAD
Pokea kitambulisho cha hati badala ya yaliyomo, pata kutoka kwa 'librarian'.
Ongeza mteja wa 'librarian' kwenye huduma ya chunker
Pata yaliyomo ya ukurasa kwa kutumia kitambulisho cha hati

**2. Kiolesura kipya: Mteja wa 'Librarian' (kuandika)**

Hifadhi kila sehemu ndogo kama hati ya mtoto katika 'librarian'.
Kwa kila sehemu ndogo: piga simu `add-child-document` na mzazi = kitambulisho cha hati ya ukurasa
=======
Pokea kitambulisho cha hati badala ya yaliyomo, upakue kutoka kwa 'librarian'.
Ongeza mteja wa 'librarian' kwenye huduma ya chunker
Pakua yaliyomo ya ukurasa kwa kutumia kitambulisho cha hati

**2. Kiolesura kipya: Mteja wa 'Librarian' (kuandika)**

Hifadhi kila sehemu kama hati ya mtoto katika 'librarian'.
Kwa kila sehemu: piga simu `add-child-document` na mzazi = kitambulisho cha hati ya ukurasa
>>>>>>> 82edf2d (New md files from RunPod)

**3. Kiolesura kipya: Muunganisho wa hifadhi tatu**

Toa miunganisho ya mzazi-mtoto kwa grafu ya maarifa.
Ongeza mteja/mpublisher wa hifadhi tatu
<<<<<<< HEAD
Kwa kila sehemu ndogo: toa muunganiko unaounganisha hati ya sehemu ndogo na hati ya ukurasa

**4. Badilisha muundo wa pato**

Sambaza kitambulisho cha hati ya sehemu ndogo na yaliyomo ya sehemu ndogo (uboreshaji wa baada ya chunker).
=======
Kwa kila sehemu: toa muunganisho unaounganisha hati ya sehemu na hati ya ukurasa

**4. Badilisha muundo wa pato**

Sambaza kitambulisho cha hati ya sehemu na yaliyomo ya sehemu (uboreshaji wa baada ya chunker).
>>>>>>> 82edf2d (New md files from RunPod)
Wasindikaji wa baadaye hupokea kitambulisho kwa ajili ya asili + yaliyomo ili kufanya kazi nayo

#### Muhtasari wa Mabadiliko ya Kiolesura

| Kiolesura | Mabadiliko |
|-----------|--------|
| Ujumbe wa ingizo | Mabadiliko kutoka yaliyomo hadi kitambulisho cha hati |
<<<<<<< HEAD
| Librarian | Mabadiliko mapya ya kutoka (kusoma + kuandika) - pata yaliyomo, hifadhi hati za watoto |
=======
| Librarian | Mabadiliko mapya ya kutoka (kusoma + kuandika) - pakua yaliyomo, hifadhi hati za watoto |
>>>>>>> 82edf2d (New md files from RunPod)
| Hifadhi tatu | Mabadiliko mapya ya kutoka - toa miunganisho ya mzazi-mtoto |
| Ujumbe wa pato | Mabadiliko kutoka yaliyomo-tu hadi kitambulisho + yaliyomo |

### Mabadiliko ya Mvumbuzi wa Maarifa

#### Hali ya Sasa

<<<<<<< HEAD
Yanapokea yaliyomo ya sehemu ndogo
Yanatoa triples na embeddings
Yanatoa kwa hifadhi ya triples na hifadhi ya embeddings
`subjectOf` uhusiano unaelekeza kwenye hati ya juu (si sehemu ndogo)
=======
Yanapokea yaliyomo ya sehemu
Yanatoa triples na embeddings
Yanatuma kwa hifadhi ya triples na hifadhi ya embeddings
`subjectOf` uhusiano unaelekeza kwenye hati ya juu (si sehemu)
>>>>>>> 82edf2d (New md files from RunPod)

#### Mabadiliko Yanayohitajika

**1. Badilisha utunzaji wa ingizo**

<<<<<<< HEAD
Pokea kitambulisho cha hati ya sehemu ndogo pamoja na yaliyomo.
Tumia kitambulisho cha sehemu ndogo kwa ulinganisho (yaliyomo tayari yamejumuishwa kwa uboreshaji)

**2. Sasisha asili ya triples**

Unganisha triples zilizotolewa na sehemu ndogo (si hati ya juu).
Tumia reification ili kuunda muunganiko unaoelekeza kwenye muunganiko
`subjectOf` uhusiano: triple → kitambulisho cha hati ya sehemu ndogo
=======
Pokea kitambulisho cha hati ya sehemu pamoja na yaliyomo.
Tumia kitambulisho cha sehemu kwa ulinganisho (yaliyomo tayari yamejumuishwa kwa uboreshaji)

**2. Sasisha asili ya triples**

Unganisha triples zilizotolewa na sehemu (si hati ya juu).
Tumia reification ili kuunda muunganisho unaoelekeza kwenye muunganisho
`subjectOf` uhusiano: triple → kitambulisho cha hati ya sehemu
>>>>>>> 82edf2d (New md files from RunPod)
Matumizi ya kwanza ya msaada uliopo wa reification

**3. Sasisha asili ya embeddings**

<<<<<<< HEAD
Unganisha kitambulisho cha entiti ya embedding na sehemu ndogo.
Toa muunganiko: kitambulisho cha entiti ya embedding → kitambulisho cha hati ya sehemu ndogo
=======
Unganisha kitambulisho cha entiti ya embedding na sehemu.
Toa muunganisho: kitambulisho cha entiti ya embedding → kitambulisho cha hati ya sehemu
>>>>>>> 82edf2d (New md files from RunPod)

#### Muhtasari wa Mabadiliko ya Kiolesura

| Kiolesura | Mabadiliko |
|-----------|--------|
<<<<<<< HEAD
| Ujumbe wa ingizo | Inatarajia kitambulisho cha sehemu ndogo + yaliyomo (si yaliyomo tu) |
| Hifadhi tatu | Tumia reification kwa asili ya triple → sehemu |
| Asili ya embedding | Unganisha kitambulisho cha entiti → kitambulisho cha sehemu |
=======
| Ujumbe wa ingizo | Inatarajia kitambulisho cha sehemu + yaliyomo (si yaliyomo tu) |
| Hifadhi ya triples | Tumia reification kwa asili ya triple → sehemu |
| Asili ya embeddings | Unganisha kitambulisho cha entiti → kitambulisho cha sehemu |
>>>>>>> 82edf2d (New md files from RunPod)

## Marejeleo

Asili ya wakati wa swali: `docs/tech-specs/query-time-provenance.md`
Kiwango cha PROV-O kwa uundaji wa asili
Meta-data ya chanzo iliyopo katika grafu ya maarifa (inahitaji ukaguzi)
