# OntoRAG: Vigezo vya Kiufundi vya Utaratibu wa Kuchimbua Maarifa na Ufuatiliaji Kulingana na Ontolojia.

## Muhtasari

OntoRAG ni mfumo wa kuchimbua maarifa na kufuatilia maswali unaoendeshwa na ontolojia, ambao unaweka vikwazo vikali vya utaratibu wakati wa kuchimbua vipengele vya maarifa kutoka kwa maandishi yasiyo na muundo na wakati wa kufuatilia maswali kwenye grafu ya maarifa iliyoundwa. Kufanana na GraphRAG lakini na vikwazo vya ontolojia rasmi, OntoRAG huhakikisha kwamba vipengele vyote vilivyochimbwa vinafuata miundo iliyobainishwa ya ontolojia na hutoa uwezo wa kufuatilia maswali kwa kuzingatia maana.

Mfumo hutumia utangamano wa vector ili kuchagua kwa kasi sehemu muhimu za ontolojia kwa ajili ya uchimbaji na operesheni za kufuatilia maswali, na hivyo kuruhusu usindikaji ulioelezwa na unaofaa kwa muktadha huku ukiendelea kudumisha utaratibu wa maana.

**Jina la Huduma**: `kg-extract-ontology`

## Malengo

**Uchimbaji Unaofuata Ontolojia**: Hakikisha kwamba vipengele vyote vilivyochimbwa vinafuata kikamilifu ontolojia zilizopakuliwa.
**Uchaguzi wa Muktadha Unaobadilika**: Tumia embeddings kuchagua sehemu muhimu za ontolojia kwa kila sehemu.
**Utaratibu wa Maana**: Dumu kwa safu za darasa, nyanja/mahusiano ya mali, na vikwazo.
**Usindikaji Wenye Ufanisi**: Tumia maduka ya vector ya ndani kwa utangamano wa haraka wa vipengele vya ontolojia.
**Muundo Unaoweza Kukua**: Unga ontolojia nyingi za wakati mmoja zenye nyanja tofauti.

## Asili

Huduma za sasa za kuchimbua maarifa (`kg-extract-definitions`, `kg-extract-relationships`) zinafanya kazi bila vikwazo rasmi, na hivyo zinaweza kuzalisha vipengele ambavyo havifanani au ambavyo havikubaliki. OntoRAG inashughulikia hili kwa:

1. Kupakua ontolojia rasmi ambazo zinafafanua madarasa na mali halali.
2. Kutumia embeddings kulinganisha yaliyomo katika maandishi na vipengele muhimu vya ontolojia.
3. Kuweka kikwazo kwa uchimbaji ili kuzalisha tu vipengele vinavyofuata ontolojia.
4. Kutoa uthibitisho wa maana wa maarifa yaliyochimbwa.

Mbinu hii inachanganya unyumbufu wa uchimbaji wa neva na ukakamavu wa uwakilishi rasmi wa maarifa.

## Muundo wa Kiufundi

### Muundo

Mfumo wa OntoRAG una vipengele vifuatavyo:

```
┌─────────────────┐
│  Configuration  │
│    Service      │
└────────┬────────┘
         │ Ontologies
         ▼
┌─────────────────┐      ┌──────────────┐
│ kg-extract-     │────▶│  Embedding   │
│   ontology      │      │   Service    │
└────────┬────────┘      └──────────────┘
         │                      │
         ▼                      ▼
┌─────────────────┐      ┌──────────────┐
│   In-Memory     │◀────│   Ontology   │
│  Vector Store   │      │   Embedder   │
└────────┬────────┘      └──────────────┘
         │
         ▼
┌─────────────────┐      ┌──────────────┐
│    Sentence     │────▶│   Chunker    │
│    Splitter     │      │   Service    │
└────────┬────────┘      └──────────────┘
         │
         ▼
┌─────────────────┐      ┌──────────────┐
│    Ontology     │────▶│   Vector     │
│    Selector     │      │   Search     │
└────────┬────────┘      └──────────────┘
         │
         ▼
┌─────────────────┐      ┌──────────────┐
│    Prompt       │────▶│   Prompt     │
│   Constructor   │      │   Service    │
└────────┬────────┘      └──────────────┘
         │
         ▼
┌─────────────────┐
│  Triple Output  │
└─────────────────┘
```

### Maelezo ya Vipengele

#### 1. Mpakuzi wa Ontolojia

**Madhumuni**: Hupata na huchanganua usanidi wa ontolojia kutoka kwa huduma ya usanidi kwa kutumia sasisho zinazotokana na matukio.

**Utekelezaji**:
Mpakuzi wa Ontolojia hutumia folyo ya ConfigPush ya TrustGraph ili kupokea sasisho za usanidi wa ontolojia zinazotokana na matukio. Wakati kipengele cha usanidi cha aina ya "ontolojia" kinaongezwa au kihaririwa, mpakuzi hupokea sasisho kupitia folyo ya config-update na huchanganua muundo wa JSON unao na metadata, madarasa, sifa za kitu, na sifa za aina ya data. Ontolojia zilizochanganuliwa hizi huhifadhiwa katika kumbukumbu kama vitu vilivyopangwa ambavyo vinaweza kupatikana kwa urahisi wakati wa mchakato wa uondoaji.

**Miamala Muhimu**:
Jisajili kwa folyo ya config-update kwa usanidi wa aina ya ontolojia
Changanua muundo wa ontolojia wa JSON katika vitu vya OntologyClass na OntologyProperty
Thibitisha muundo na utangamano wa ontolojia
Hifadhi ontolojia zilizochanganuliwa katika kumbukumbu kwa upatikanaji wa haraka
Shirikisha usindikaji wa kila mtiririko na maduka ya vekta maalum ya mtiririko

**Mahali pa Utekelezaji**: `trustgraph-flow/trustgraph/extract/kg/ontology/ontology_loader.py`

#### 2. Mpakuzi wa Ontolojia

**Madhumuni**: Huunda ufumbuzi wa vekta kwa vipengele vyote vya ontolojia ili kuwezesha utangamano wa kulinganisha wa kiufundi.

**Utekelezaji**:
Mpakuzi wa Ontolojia huchakata kila kipengele katika ontolojia zilizopakuliwa (madarasa, sifa za kitu, na sifa za aina ya data) na huunda ufumbuzi wa vekta kwa kutumia huduma ya EmbeddingsClientSpec. Kwa kila kipengele, huunganisha kitambulisho cha kipengele, lebo, na maelezo (maoni) ili kuunda uwakilishi wa maandishi. Maandishi haya yabadilishwa kisha kuwa ufumbuzi wa vekta wa mchemuko mkuu ambao unaonyesha maana yake ya kiufundi. Ufumbuzi huu huhifadhiwa katika duka la vekta la FAISS la kila mtiririko pamoja na metadata kuhusu aina ya kipengele, ontolojia ya chanzo, na ufafanuzi kamili. Mpakuzi hugundua kiotomatiki mchemuko wa ufumbuzi kutoka kwa majibu ya kwanza ya ufumbuzi.

**Miamala Muhimu**:
Unda uwakilishi wa maandishi kutoka kwa kitambulisho cha kipengele, lebo, na maoni
Zunda ufumbuzi kupitia EmbeddingsClientSpec (ukitumia asyncio.gather kwa usindikaji wa kikundi)
Hifadhi ufumbuzi na metadata kamili katika duka la vekta la FAISS
Indexi kwa ontolojia, aina ya kipengele, na kitambulisho cha kipengele kwa upatikanaji wa ufanisi
Gundua kiotomatiki mchemuko wa ufumbuzi kwa upangaji wa duka la vekta
Shirikisha modeli za ufumbuzi za kila mtiririko na maduka ya vekta yanayojitegemea

**Mahali pa Utekelezaji**: `trustgraph-flow/trustgraph/extract/kg/ontology/ontology_embedder.py`

#### 3. Mchakato wa Nakala (Kigawanyishi Sentensi)

**Madhumuni**: Huondoa vipande vya nakala katika sehemu ndogo kwa utangamano wa ontolojia.

**Utekelezaji**:
Mchakato wa Nakala hutumia NLTK kwa utambaji wa sentensi na utambulisho wa POS ili kugawanya vipande vya nakala vinavyoingia katika sentensi. Inashughulikia utangamano wa toleo la NLTK kwa kujaribu kupakua `punkt_tab` na `averaged_perceptron_tagger_eng`, na kutoa nafasi kwa matoleo ya zamani ikiwa ni lazima. Kila kipande cha nakala kigawanywa katika sentensi binafsi ambazo zinaweza kulinganishwa kwa kujitegemea na vipengele vya ontolojia.

**Miamala Muhimu**:
Gawa nakala katika sentensi kwa kutumia utambaji wa sentensi wa NLTK
Shirikisha utangamano wa toleo la NLTK (punkt_tab vs punkt)
Unda vitu vya TextSegment na nakala na maelezo ya nafasi
Saidia sentensi kamili na vipande vya mtu binafsi

**Mahali pa Utekelezaji**: `trustgraph-flow/trustgraph/extract/kg/ontology/text_processor.py`

#### 4. Mchagua wa Ontolojia

**Madhumuni**: Hutambua sehemu muhimu zaidi ya vipengele vya ontolojia kwa kipande cha sasa cha nakala.

**Utekelezaji**:
Mchagua wa Ontolojia hufanya utangamano wa kiufundi kati ya sehemu za nakala na vipengele vya ontolojia kwa kutumia utafutaji wa ufanisi wa vekta wa FAISS. Kwa kila sentensi kutoka kwa kipande cha nakala, huunda ufumbuzi na hufuatilia duka la vekta kwa vipengele vya ontolojia vinavyolingana kwa ufanisi kwa kutumia ufanisi wa cosine na kizingiti kinachoweza kusanidiwa (kiasi 0.3). Baada ya kukusanya vipengele vyote muhimu, hufanya utatuzi kamili wa utegemezi: ikiwa darasa lilitajwa, madarasa yake ya wazazi hujumuishwa; ikiwa sifa ilitajwa, madarasa yake ya uwanja na safu huongezwa. Zaidi ya hayo, kwa kila darasa lililochaguliwa, hujumuisha kiotomatiki **sifa zote ambazo zinarejelea darasa hilo** katika uwanja au safu yake. Hii inahakikisha kuwa uondoaji una upatikanaji wa sifa zote muhimu za uhusiano.

**Operesheni Muhimu**:
Tengeneza embeddings kwa kila sehemu ya maandishi (sentensi)
Fanya utafutaji wa jirani wa karibu (k-nearest neighbor) katika hifadhi ya vector ya FAISS (top_k=10, threshold=0.3)
Tumia kikomo cha ufanano ili kuchuja mechi dhaifu
Tatua utegemezi (madarasa ya wazazi, nyanja, mipaka)
**Jumuisha moja kwa moja sifa zote zinazohusiana na madarasa yaliyochaguliwa** (mechi ya nyanja/mipaka)
Jenga sehemu ndogo ya ontology inayofaa na uhusiano wote unaohitajika
Ondoa vipengele ambavyo huonekana mara nyingi

**Mahali pa Utendaji**: `trustgraph-flow/trustgraph/extract/kg/ontology/ontology_selector.py`

#### 5. Uundaji wa Maagizo

**Madhumuni**: Huunda maagizo yaliyo na muundo ambayo huongoza LLM ili kuchimbua tu triples zinazolingana na ontology.

**Utendaji**:
Huduma ya uchimbaji hutumia kiolezo cha Jinja2 kilicho pakuliwa kutoka `ontology-prompt.md` ambayo inaandika sehemu ndogo ya ontology na maandishi kwa uchimbaji wa LLM. Kiolezo hicho huendelea mara kwa mara juu ya madarasa, sifa za vitu, na sifa za aina ya data kwa kutumia sintaksia ya Jinja2, na kuwasilisha kila moja pamoja na maelezo yake, nyanja, mipaka, na uhusiano wa kishati. Maagizo hayo yana sheria kali kuhusu kutumia vipengele vya ontology vilivyotolewa pekee na huomba muundo wa pato la JSON kwa upangaji thabiti.

**Operesheni Muhimu**:
Tumia kiolezo cha Jinja2 na marudio juu ya vipengele vya ontology
Andika madarasa na uhusiano wa wazazi (subclass_of) na maoni
Andika sifa na vikwazo vya nyanja/mipaka na maoni
Jumuisha sheria wazi za uchimbaji na mahitaji ya muundo wa pato
Piga simu huduma ya maagizo na kitambulisho cha kiolezo "extract-with-ontologies"

**Mahali pa Kiolezo**: `ontology-prompt.md`
**Mahali pa Utendaji**: `trustgraph-flow/trustgraph/extract/kg/ontology/extract.py` (mbinu ya build_extraction_variables)

#### 6. Huduma Kuu ya Uchimbaji

**Madhumuni**: Inadhihirisha vipengele vyote ili kufanya uchimbaji kamili wa triples kulingana na ontology.

**Utendaji**:
Huduma Kuu ya Uchimbaji (KgExtractOntology) ni safu ya upangaji ambayo inasimamia mtiririko kamili wa uchimbaji. Inatumia mtindo wa TrustGraph's FlowProcessor na usanidi wa kila mtiririko. Wakati sasisho la usanidi wa ontology linapofika, inaanzisha au inasasisha vipengele vya mtiririko (mji wa ontology, mchimbaji, mchakato wa maandishi, mchagua). Wakati kipande cha maandishi kinapofika kwa uchunguzi, inadhihirisha mstari wa kazi: kugawanya maandishi katika sehemu, kutafuta vipengele muhimu vya ontology kupitia utafutaji wa vector, kuunda maagizo ya kikomo, kupiga simu huduma ya maagizo, kuchanganua na kuthibitisha jibu, kuunda triples za ufafanuzi wa ontology, na kutoa triples za yaliyomo na mandhari ya vitu.

**Mstari wa Kazi wa Uchimbaji**:
1. Pokea kipande cha maandishi kupitia folyo ya chunks-input
2. Anzisha vipengele vya mtiririko ikiwa ni lazima (kwa kipande cha kwanza au sasisho la usanidi)
3. Gawa maandishi katika sentensi kwa kutumia NLTK
4. Tafuta hifadhi ya vector ya FAISS ili kupata dhana muhimu za ontology
5. Jenga sehemu ndogo ya ontology na ujumuishaji wa moja kwa moja wa sifa
6. Jenga mbadala wa Jinja2-templated
7. Piga simu huduma ya maagizo na kiolezo cha extract-with-ontologies
8. Changanisha jibu la JSON katika triples zilizopangwa
9. Thibitisha triples na upanue URI hadi URI kamili ya ontology
10. Jenga triples za ufafanuzi wa ontology (madarasa na sifa na lebo/maoni/nyanja/mipaka)
11. Jenga mandhari ya vitu kutoka kwa triples zote
12. Toa kwa folyo za triples na entity-contexts

**Vipengele Muhimu**:
Hifadhi za vector za kila mtiririko inayounga mkono modeli tofauti za uchimbaji
Sasisho ya ontology iliyoendeshwa na tukio kupitia folyo ya config-update
Upanuzi wa moja kwa moja wa URI kwa kutumia URI za ontology
Vipengele vya ontology vilivyoongezwa kwenye grafu ya maarifa na metadata kamili
Mandhari ya vitu inajumuisha vipengele vya yaliyomo na ontology

**Mahali pa Utendaji**: `trustgraph-flow/trustgraph/extract/kg/ontology/extract.py`

### Usanidi

Huduma hutumia mbinu ya kawaida ya usanidi ya TrustGraph na hoja za mstari wa amri:

```bash
kg-extract-ontology \
  --id kg-extract-ontology \
  --pulsar-host localhost:6650 \
  --input-queue chunks \
  --config-input-queue config-update \
  --output-queue triples \
  --entity-contexts-output-queue entity-contexts
```

**Vigezo Muhimu vya Usanidi**:
`similarity_threshold`: 0.3 (kiwango chachilia, kinaweza kusanidiwa katika programu)
`top_k`: 10 (idadi ya vipengele vya ontolojia ambavyo vitapatikana kwa kila sehemu)
`vector_store`: FAIISS IndexFlatIP kwa kila mtiririko na vipimo ambavyo vitapatikana kiotomatiki
`text_processor`: NLTK na utambuzi wa sentensi ya punkt_tab
`prompt_template`: "extract-with-ontologies" (template ya Jinja2)

**Usanidi wa Ontolojia**:
Ontolojia huzamilishwa moja kwa moja kupitia folyo ya config-update yenye aina="ontology".

### Mtiririko wa Data

1. **Awamu ya Uanzishaji** (kwa kila mtiririko):
   Pokea usanidi wa ontolojia kupitia folyo ya config-update
   Changanua JSON ya ontolojia katika vitu vya OntologyClass na OntologyProperty
   Zizalisha embeddings kwa vipengele vyote vya ontolojia kwa kutumia EmbeddingsClientSpec
   Hifadhi embeddings katika duka la vector la FAISS kwa kila mtiririko
   Gundua vipimo vya embedding kutoka kwa majibu ya kwanza

2. **Awamu ya Utoaji** (kwa kila sehemu):
   Pokea sehemu kutoka kwa folyo ya chunks-input
   Gawanya sehemu katika sentensi kwa kutumia NLTK
   Hesabu embeddings kwa kila sentensi
   Tafuta duka la vector la FAISS kwa vipengele muhimu vya ontolojia
   Unda subset ya ontolojia na ujumuishaji wa kiotomatiki wa sifa
   Unda vigezo vya template ya Jinja2 na maandishi na ontolojia
   Piga huduma ya prompt na template ya extract-with-ontologies
   Changanisha majibu ya JSON na uthibitishe triples
   Panua URIs kwa kutumia URIs za ontolojia
   Zizalisha triples za ufafanuzi wa ontolojia
   Unda muktadha wa vitu kutoka kwa triples zote
   Tuma kwa folyo za triples na entity-contexts

### Duka la Vector la Kumbukumbu

**Madhumuni**: Hutoa utafutaji wa haraka wa ufanano, unaotegemea kumbukumbu kwa utangamano wa vipengele vya ontolojia.

**Utekelezaji: FAISS**

Mfumo hutumia **FAISS (Facebook AI Similarity Search)** na IndexFlatIP kwa utafutaji wa usawa wa cosine. Vipengele muhimu:

**IndexFlatIP**: Utafutaji wa usawa wa cosine kwa kutumia bidhaa ya ndani
**Uugunduzi wa kiotomatiki**: Vipimo vinatambuliwa kutoka kwa majibu ya kwanza ya embedding
**Maduka ya kila mtiririko**: Kila mtiririko una duka la vector linalojitegemea kwa modeli tofauti za embedding
**Urekebishaji**: Vector zote zimefanywa kuwa sawa kabla ya kuingizwa
**Operesheni za kundi**: Kuongeza kikundi kwa upakiaji wa awali wa ontolojia

**Mahali pa Utekelezaji**: `trustgraph-flow/trustgraph/extract/kg/ontology/vector_store.py`

### Algoritimu ya Uchaguzi wa Subset ya Ontolojia

**Madhumuni**: Inachagua kwa moja kwa moja sehemu muhimu zaidi ya ontolojia kwa kila sehemu ya maandishi.

**Hatua za Algoritimu**:

1. **Umgawaji wa Maandishi**:
   Gawa sehemu ya pembeni katika sentensi kwa kutumia utambuzi wa sentensi ya NLP
   Toa maneno muhimu, maneno muhimu, na vitu vilivyotajwa kutoka kwa kila sentensi
   Unda muundo wa kishati wa sehemu ukiendeleza muktadha

2. **Uzalishaji wa Embedding**:
   Zizalisha embeddings ya vector kwa kila sehemu ya maandishi (sentensi na maneno)
   Tumia modeli sawa ya embedding kama ilivyotumika kwa vipengele vya ontolojia
   Hifadhi embeddings kwa sehemu zinazorudiwa ili kuboresha utendaji

3. **Utafiti wa Ufanano**:
   Kwa kila embedding ya sehemu ya maandishi, tafuta duka la vector
   Rudisha vipengele 10 bora (e.g., 10) vinavyofanana na ontolojia
   Tumia kizuia cha ufanano (e.g., 0.7) kuchuja mechi dhaifu
   Jumuisha matokeo kote katika sehemu zote, ukihesabu masafa ya mechi

4. **Suluhisho la Utendaji**:
   Kwa kila darasa lililochaguliwa, jumuisha madarasa yote ya wazazi hadi mizizi
   Kwa kila sifa iliyochaguliwa, jumuisha madarasa yake ya uwanja na upeo
   Kwa sifa za kinyume, hakikisha kuwa mwelekeo wote wamejumuishwa
   Ongeza madarasa sawa ikiwa zipo katika ontolojia

5. **Uundaji wa Subset**:
   Ondoa vipengele vilivyo na marudio huku ukiendeleza uhusiano
   Panga katika madarasa, sifa za kitu, na sifa za aina ya data
   Hakikisha kuwa vikwazo vyote na uhusiano vimehifadhiwa
   Unda mini-ontolojia inayojitegemea ambayo ni halali na kamili

**Mfano wa Uelekezaji**:
Ikiwa kuna maandishi: "Mbwa mweusi alimfuatilia paka mweupe kwenye mti."
Sehemu: ["mbwa mweusi", "paka mweupe", "mti", "alifuatilia"]
Vipengele vilivyolingana: [mbwa (darasa), paka (darasa), wanyama (mzazi), hufuatia (sifa)]
Utendaji: [wanyama (mzazi wa mbwa na paka), viumbehai (mzazi wa wanyama)]
Subset ya mwisho: Mini-ontolojia kamili na hierarkia ya wanyama na uhusiano wa kufuatilia

### Uthibitisho wa Triples

**Madhumuni**: Inahakikisha kwamba triples zote zilizotolewa zinaendana kikamilifu na vikwazo vya ontolojia.

**Algoritimu ya Uthibitisho**:

1. **Uthibiti wa Darasa**:
   Hakikisha kwamba vitu ni mifano ya madarasa yaliyoundwa katika sehemu ya ontolojia.
   Kwa sifa za vitu, hakikisha kwamba vitu pia ni mifano halali ya madarasa.
   Angalia majina ya madarasa dhidi ya kamusi ya madarasa ya ontolojia.
   Shirudia safu za madarasa - mifano ya madarasa ya chini yanafaa kwa sheria za darasa kuu.

2. **Uthibiti wa Sifa**:
   Thibitisha kwamba manukuu yanalingana na sifa katika sehemu ya ontolojia.
   Tofautisha kati ya sifa za vitu (kitu hadi kitu) na sifa za aina ya data (kitu hadi literal).
   Hakikisha kwamba majina ya sifa yanalingana kabisa (kikumbukie nafasi ikiwa ipo).

3. **Uchunguzi wa Doman/Safu**:
   Kwa kila sifa inayotumika kama manukuu, pata domania na safu yake.
   Hakikisha kwamba aina ya kitu inalingana au inameridia aina ya domania ya sifa.
   Hakikisha kwamba aina ya kitu inalingana au inameridia aina ya safu ya sifa.
   Kwa sifa za aina ya data, hakikisha kwamba kitu ni literal ya aina ya XSD inayofaa.

4. **Uthibiti wa Idadi**:
   Fuatilia idadi ya matumizi ya sifa kwa kila kitu.
   Angalia idadi ya chini - hakikisha kwamba sifa zinazohitajika zipo.
   Angalia idadi ya juu - hakikisha kwamba sifa haitumiki mara nyingi sana.
   Kwa sifa za kazi, hakikisha kwamba kuna thamani moja tu kwa kila kitu.

5. **Uthibiti wa Aina ya Data**:
   Tafsiri maadili ya literal kulingana na aina zao zilizotangazwa za XSD.
   Thibitisha kwamba nambari za integer ni nambari halali, tarehe zinaumbwa vizuri, n.k.
   Angalia muundo wa maandishi ikiwa sheria za regex zimefafuliwa.
   Hakikisha kwamba URI zimeumbwa vizuri kwa aina za xsd:anyURI.

**Mfano wa Uthibiti**:
Kifurushi: ("Buddy", "ana-miliki", "John")
Angalia kwamba "Buddy" imewekwa kama darasa ambalo linaweza kuwa na sifa ya "ana-miliki".
Angalia kwamba "ana-miliki" ipo katika ontolojia.
Thibitisha sheria ya domania: kitu lazima kiwe cha aina ya "Mbwa" au darasa la chini.
Thibitisha sheria ya safu: kitu lazima kiwe cha aina ya "Mtu" au darasa la chini.
Ikiwa halali, iongeze kwenye pato; ikiwa halali, rekodi ukiukaji na epuka.

## Mlinganisho wa Utendaji

### Mikakati ya Ubora

1. **Uficha wa Kuweka**: Hifadhi maadili yaliyowekwa kwa sehemu za maandishi ambazo hutumiwa mara kwa mara.
2. **Uchakataji wa Kundi**: Chakata sehemu nyingi kwa wakati mmoja.
3. **Ufichuaji wa Faharasa**: Tumia algorimu za jirani za karibu za takriban kwa ontolojia kubwa.
4. **Uboreshaji wa Ombi**: Punguza saizi ya ombi kwa kujumuisha tu vipengele muhimu vya ontolojia.
5. **Uficha wa Matokeo**: Hifadhi matokeo ya uondoaji kwa vipande sawa.

### Urahisi

**Upanuzi wa Afakasi**: Mifumo mingi ya utoaji inayoshiriki kumbukumbu ya ontolojia.
**Umgawanyaji wa Ontolojia**: Gawanya ontolojia kubwa kwa kulingana na eneo.
**Uchakataji wa Msururu**: Chakata vipande kadri vinavyofika bila kuunganisha.
**Usimamizi wa Kumbukumbu**: Usafishaji wa mara kwa mara wa vipimo visivyotumika.

## Usimamizi wa Madosa

### Hali za Kushindwa

1. **Ontolojia Zinazokosekana**: Tumia utoaji usio na kikomo.
2. **Ushindwa wa Huduma ya Vipimo**: Tumia vipimo vilivyohifadhiwa au epuka utoaji wa maana.
3. **Kutofa kwa Huduma ya Maagizo**: Jaribu tena kwa kuongeza muda polepole.
4. **Muundo Usio sahihi wa Triples**: Rekodi na epuka triples zilizoharibika.
5. **Utangamano wa Ontolojia**: Ripoti migogoro na tumia vipengele sahihi zaidi.

### Ufuatiliaji

Vipimo muhimu vya kufuatilia:

Muda wa kupakia ontolojia na matumizi ya kumbukumbu.
Muda wa kuunda vipimo.
Utendaji wa utafutaji wa vector.
Muda wa majibu ya huduma ya maagizo.
Usahihi wa utoaji wa triples.
Kiwango cha utangamano wa ontolojia.

## Njia ya Uhamishaji

### Kutoka kwa Vifaa vya Utoaji Vilivyopo

1. **Uendeshaji Sambamba**: Endesha pamoja na vifaa vya utoaji vilivyopo awali.
2. **Upanuzi Polepole**: Anzisha na aina mahususi za hati.
3. **Ulinganisho wa Ubora**: Linganisha ubora wa matokeo na vifaa vya utoaji vilivyopo.
4. **Uhamisho Kamili**: Badilisha vifaa vya utoaji vilivyopo baada ya ubora kuthibitishwa.

### Maendeleo ya Ontolojia

1. **Anzisha kutoka kwa Vipengele Vilivyopo**: Unda ontolojia za awali kutoka kwa maarifa iliyopo.
2. **Uboreshaji wa Mara kwa Mara**: Boresha kulingana na mifumo ya utoaji.
3. **Uhakiki wa Mtaalamu wa Lugha**: Thibitisha na wataalamu wa somo.
4. **Uboreshaji Unaoendelea**: Sasisha kulingana na maoni ya utoaji.

## Huduma ya Uulizaje inayohusiana na Ontolojia

### Maelezo

Huduma ya uulizaje inayohusiana na ontolojia hutoa njia nyingi za uulizaje ili kusaidia hifadhi tofauti za grafu. Inatumia maarifa ya ontolojia kwa majibu sahihi na ya maana ya maswali katika hifadhi za Cassandra (kupitia SPARQL) na hifadhi za grafu zinazotumia Cypher (Neo4j, Memgraph, FalkorDB).

**Vipengele vya Huduma**:
`onto-query-sparql`: Hubadilisha lugha ya asili kuwa SPARQL kwa Cassandra.
`sparql-cassandra`: Safu ya uulizaje ya SPARQL kwa Cassandra inayotumia rdflib.
`onto-query-cypher`: Hubadilisha lugha ya asili kuwa Cypher kwa hifadhi za grafu.
`cypher-executor`: Utendeshaji wa uulizaje wa Cypher kwa Neo4j/Memgraph/FalkorDB.

### Usanifu

```
                    ┌─────────────────┐
                    │   User Query    │
                    └────────┬────────┘
                             │
                             ▼
                    ┌─────────────────┐      ┌──────────────┐
                    │   Question      │────▶│   Sentence   │
                    │   Analyser      │      │   Splitter   │
                    └────────┬────────┘      └──────────────┘
                             │
                             ▼
                    ┌─────────────────┐      ┌──────────────┐
                    │   Ontology      │────▶│   Vector     │
                    │   Matcher       │      │    Store     │
                    └────────┬────────┘      └──────────────┘
                             │
                             ▼
                    ┌─────────────────┐
                    │ Backend Router  │
                    └────────┬────────┘
                             │
                 ┌───────────┴───────────┐
                 │                       │
                 ▼                       ▼
    ┌─────────────────┐          ┌─────────────────┐
    │ onto-query-     │          │ onto-query-     │
    │    sparql       │          │    cypher       │
    └────────┬────────┘          └────────┬────────┘
             │                            │
             ▼                            ▼
    ┌─────────────────┐          ┌─────────────────┐
    │   SPARQL        │          │   Cypher        │
    │  Generator      │          │  Generator      │
    └────────┬────────┘          └────────┬────────┘
             │                            │
             ▼                            ▼
    ┌─────────────────┐          ┌─────────────────┐
    │ sparql-         │          │ cypher-         │
    │ cassandra       │          │ executor        │
    └────────┬────────┘          └────────┬────────┘
             │                            │
             ▼                            ▼
    ┌─────────────────┐          ┌─────────────────┐
    │   Cassandra     │          │ Neo4j/Memgraph/ │
    │                 │          │   FalkorDB      │
    └────────┬────────┘          └────────┬────────┘
             │                            │
             └────────────┬───────────────┘
                          │
                          ▼
                 ┌─────────────────┐      ┌──────────────┐
                 │   Answer        │────▶│   Prompt     │
                 │  Generator      │      │   Service    │
                 └────────┬────────┘      └──────────────┘
                          │
                          ▼
                 ┌─────────────────┐
                 │  Final Answer   │
                 └─────────────────┘
```

### Mchakato wa Uchunguzi wa Maswali

#### 1. Mchambuzi wa Maswali

**Madhumuni**: Huainisha maswali ya mtumiaji katika vipengele vya maana kwa ajili ya utangamano wa ontolojia.

**Maelezo ya Algoritimu**:
Mchambuzi wa Maswali huchukua swali la lugha ya asili ambalo limeingia na hulifanya iwe sehemu za maana kwa kutumia mbinu sawa ya ugawaji wa sentensi kama ilivyo kwenye mchakato wa uondoaji. Hutambua vitu, uhusiano, na vikwazo muhimu ambavyo yameelezwa katika swali. Kila sehemu inachambuliwa kwa aina ya swali (ukweli, jumlisho, kulinganisha, n.k.) na muundo unaotarajiwa wa jibu. Uainishaji huu husaidia kutambua sehemu zipi za ontolojia ambazo ni muhimu zaidi kwa kujibu swali.

**Utendaji Muhimu**:
Gawa swali katika sentensi na maneno
Tambua aina na nia ya swali
Toa vitu na uhusiano uliotajwa
Gundua vikwazo na vichujio katika swali
Tambua muundo unaotarajiwa wa jibu

#### 2. Kichunguzi cha Ontolojia kwa Maswali

**Madhumuni**: Hutambua sehemu muhimu ya ontolojia inayohitajika kujibu swali.

**Maelezo ya Algoritimu**:
Kichunguzi hiki ni kama Kichunguzi cha Ontolojia katika mchakato wa uondoaji, lakini kimeboreshwa kwa ajili ya kujibu maswali. Kichunguzi hicho hutengeneza maandishi (embeddings) kwa sehemu za swali na kutafuta katika hifadhi ya maandishi vipengele muhimu vya ontolojia. Hata hivyo, linazingatia kutafuta dhana ambazo zitakuwa muhimu kwa uundaji wa swali badala ya uondoaji. Huongeza uteuzi ili kujumuisha sifa zinazohusiana ambazo zinaweza kuvinjwa wakati wa uchunguzi wa grafu, hata kama hazijaelezwa wazi katika swali. Kwa mfano, ikiwa swali ni kuhusu "wafanyakazi," linaweza kujumuisha sifa kama vile "hufanya kazi kwa," "husaidia," na "huripoti kwa" ambazo zinaweza kuwa muhimu kwa kupata habari kuhusu wafanyakazi.

**Mbinu ya Ulinganisho**:
Tengeneza maandishi ya sehemu za swali
Tafuta dhana za ontolojia zilizotajwa moja kwa moja
Jumuisha sifa zinazounganisha madarasa yaliyotajwa
Ongeza sifa za kinyume na zinazohusiana kwa ajili ya uvinjaji
Jumuisha madarasa ya wazazi/watoto kwa maswali ya kishirikina
Unda sehemu ya ontolojia iliyo na umakini wa swali

#### 3. Kijaribu cha Nyuma (Backend Router)

**Madhumuni**: Hupeleka maswali kwenye njia inayofaa ya utekelezaji wa swali kulingana na usanidi.

**Maelezo ya Algoritimu**:
Kijaribu cha Nyuma huchunguza usanidi wa mfumo ili kubaini ambayo ya mifumo ya nyuma (backends) inafanya kazi (Cassandra au Cypher-based). Hupeleka swali na sehemu ya ontolojia kwenye huduma inayofaa ya uundaji wa swali. Kijaribu hicho pia kinaweza kusaidia usambazaji wa maswali kwenye mifumo ya nyuma mingi au mitaratibu ya dharura ikiwa mfumo wa nyuma mkuu haupatikani.

**Mantiki ya Upelekeshaji**:
Angalia aina ya mfumo wa nyuma iliyosanidiwa kutoka kwa mipangilio ya mfumo
Peleka kwenye `onto-query-sparql` kwa mifumo ya nyuma ya Cassandra
Peleka kwenye `onto-query-cypher` kwa Neo4j/Memgraph/FalkorDB
Saidia usanidi wa mifumo ya nyuma mingi na usambazaji wa maswali
Shirikisha matukio ya dharura na usambazaji wa maswali

#### 4. Uundaji wa Swali la SPARQL (`onto-query-sparql`)

**Madhumuni**: Hubadilisha maswali ya lugha ya asili kuwa maswali ya SPARQL kwa utekelezaji katika Cassandra.

**Maelezo ya Algoritimu**:
Mgenuzi wa swali la SPARQL huchukua swali na sehemu ya ontolojia na huunda swali la SPARQL lililoboreshwa kwa utekelezaji katika mfumo wa nyuma wa Cassandra. Hutumia huduma ya maagizo (prompt) na kiolezo maalum cha SPARQL ambacho kinajumuisha maana ya RDF/OWL. Mgenuzi hufahamu muundo wa SPARQL kama vile njia za sifa, vifungu vya hiari, na vichujio ambavyo vinaweza kubadilishwa kwa ufanisi katika operesheni za Cassandra.

**Kiolezo cha Maagizo ya Uundaji wa SPARQL**:
```
Generate a SPARQL query for the following question using the provided ontology.

ONTOLOGY CLASSES:
{classes}

ONTOLOGY PROPERTIES:
{properties}

RULES:
- Use proper RDF/OWL semantics
- Include relevant prefixes
- Use property paths for hierarchical queries
- Add FILTER clauses for constraints
- Optimise for Cassandra backend

QUESTION: {question}

SPARQL QUERY:
```

#### 5. Uzalishaji wa Uliza wa Cypher (`onto-query-cypher`)

**Madhumuni**: Hubadilisha maswali ya lugha ya asili kuwa uliza za Cypher kwa hifadhidata za grafu.

**Maelezo ya Algoritimu**:
Mzalishaji wa uliza wa Cypher huunda uliza za Cypher ambazo zimeboreshwa kwa Neo4j, Memgraph, na FalkorDB. Huunganisha madarasa ya ontolojia na lebo za node na sifa na uhusiano, kwa kutumia sintaksia ya utambuzi wa Cypher. Mzalishaji unajumuisha maboresho maalum ya Cypher kama vile vidokezo vya mwelekeo wa uhusiano, matumizi ya fahirisi, na vidokezo vya upangaji wa uliza.

**Sampuli ya Kiolezo ya Kuomba Uliza wa Cypher**:
```
Generate a Cypher query for the following question using the provided ontology.

NODE LABELS (from classes):
{classes}

RELATIONSHIP TYPES (from properties):
{properties}

RULES:
- Use MATCH patterns for graph traversal
- Include WHERE clauses for filters
- Use aggregation functions when needed
- Optimise for graph database performance
- Consider index hints for large datasets

QUESTION: {question}

CYPHER QUERY:
```

#### 6. Injini ya Ufuatiliaji wa SPARQL-Cassandra (`sparql-cassandra`)

**Madhumuni**: Inafanya kazi ya utekelezaji wa maswali ya SPARQL dhidi ya Cassandra kwa kutumia Python rdflib.

**Maelezo ya Algoritimu**:
Injini ya SPARQL-Cassandra inatekeleza kichakataji cha SPARQL kwa kutumia maktaba ya Python's rdflib pamoja na hifadhi maalum ya Cassandra. Inatengeneza mifumo ya grafu ya SPARQL kuwa maswali ya CQL ya Cassandra, huku ikiwezesha uunganisho, vichujio, na jumlishaji. Injini hii inahifadhi uhusiano kati ya RDF na Cassandra ambao unahifadhi muundo wa maana huku ukiwezesha utendakazi bora kwa mfumo wa uhifadhi wa safu za Cassandra.

**Vipengele vya Utendakazi**:
Utendakazi wa interface ya rdflib kwa Cassandra
Usaidizi wa maswali ya SPARQL 1.1 pamoja na mifumo ya kawaida
Tafsiri bora ya mifumo ya tatu kuwa CQL
Usaidizi wa njia za mali na maswali ya kimtindo
Uhamisho wa matokeo kwa data kubwa
Uunganishaji wa kikao na kuhifadhi maswali

**Mfano wa Tafsiri**:
```sparql
SELECT ?animal WHERE {
  ?animal rdf:type :Animal .
  ?animal :hasOwner "John" .
}
```
Huuandika maswali bora ya Cassandra kwa kutumia fahirisi na funguo za partition.

#### 7. Mfumo wa Utendaji wa Maswali ya Cypher (`cypher-executor`)

**Madhumuni**: Hufanya maswali ya Cypher dhidi ya Neo4j, Memgraph, na FalkorDB.

**Maelezo ya Algoritimu**:
Mfumo wa utendaji wa Cypher hutoa kiolesura cha pamoja kwa kutekeleza maswali ya Cypher katika hifadhi tofauti za data za grafu. Inashughulikia itifaki maalum za muunganisho wa hifadhidata, vidokezo vya uboreshaji wa maswali, na utaratibu wa kawaida wa umbizo wa matokeo. Mfumo huu unajumuisha utaratibu wa kujaribu tena, udhibiti wa muunganisho, na usimamizi wa miamala unaofaa kwa kila aina ya hifadhidata.

**Usaidizi wa Hifadhidata Mbalimbali**:
**Neo4j**: Itifaki ya Bolt, kazi za miamala, vidokezo vya fahirisi
**Memgraph**: Itifaki maalum, matokeo ya utiririshaji, maswali ya uchambuzi
**FalkorDB**: Marekebisho ya itifaki ya Redis, uboreshaji wa kumbukumbu

**Vipengele vya Utendaji**:
Usimamizi wa muunganisho usio tegemea hifadhidata
Uthibitisho wa maswali na ukaguzi wa sintaksia
Utumiaji wa muda na vikwazo vya rasilimali
Urekebishaji na utiririshaji wa matokeo
Ufuatiliaji wa utendaji kwa kila aina ya hifadhidata
Uhamisho wa kiotomatiki kati ya mifano ya hifadhidata

#### 8. Mjenzi wa Majibu

**Madhumuni**: Huunda jibu la lugha ya asili kutoka kwa matokeo ya maswali.

**Maelezo ya Algoritimu**:
Mjenzi wa Majibu huchukua matokeo ya maswali yaliyopangwa na swali la awali, kisha hutumia huduma ya matangazo ili kuunda jibu kamili. Tofauti na majibu rahisi yanayotegemea vipengele, hutumia LLM (Large Language Model) ili kuchambua data ya grafu katika muktadha wa swali, na kushughulikia uhusiano tata, jumlisho, na utabiri. Mjenzi anaweza kueleza hoja zake kwa kurejelea muundo wa ontolojia na triples maalum zilizopatikana kutoka kwa grafu.

**Mchakato wa Uundaji wa Majibu**:
Huunda matokeo ya maswali katika muktadha uliopangwa
Jumuisha maelezo muhimu ya ontolojia kwa uwazi
Unda matangazo na swali na matokeo
Huunda jibu la lugha ya asili kupitia LLM
Thibitisha jibu dhidi ya nia ya swali
Ongeza marejeleo kwa vitu maalum vya grafu ikiwa inahitajika

### Uunganisho na Huduma Zilizopo

#### Uhusiano na GraphRAG

**Inakamilisha**: onto-query hutoa usahihi wa semantic huku GraphRAG hutoa matoleo mapana
**Infrastraki Iliyoshiriki**: Zote mbili hutumia grafu ya maarifa na huduma sawa za matangazo
**Uelekezaji wa Maswali**: Mfumo unaweza kuelekeza maswali kwa huduma inayofaa zaidi kulingana na aina ya swali
**Njia ya Mchanganyiko**: Inaweza kuchanganya mbinu zote mbili kwa majibu kamili

#### Uhusiano na Utoaji wa OntoRAG

**Ontolojia Zilizoshiriki**: Hutumia mipangilio sawa ya ontolojia iliyopakuliwa na kg-extract-ontology
**Hifadhi ya Vector Iliyoshiriki**: Inatumia embeddings za kumbukumbu kutoka kwa huduma ya uundaji
**Semantics Sawa**: Maswali hufanya kazi kwenye grafu zilizojengwa na vikwazo sawa vya ontolojia

### Mifano ya Maswali

#### Mfano 1: Swali la Kieleleku
**Swali**: "Wanyama gani ni wanyamapori?"
**Ulinganisho wa Ontolojia**: [wanyama, wanyamapori, subClassOf]
**Swali Lililoundwa**:
```cypher
MATCH (a:animal)-[:subClassOf*]->(m:mammal)
RETURN a.name
```

#### Mfano wa 2: Ulinganisho wa Maswali
**Swali**: "Ni nyaraka zipi ambazo ziliandikwa na John Smith?"
**Ulinganisho wa Dhana**: [hati, mtu, aliyeandika]
**Swali Lililoundwa**:
```cypher
MATCH (d:document)-[:has-author]->(p:person {name: "John Smith"})
RETURN d.title, d.date
```

#### Mfano wa 3: Uchunguzi wa Uunganishaji
**Swali**: "Paka wana miguu mingapi?"
**Ulinganisho wa Dhana**: [paka, idadi-ya-miguu (sifa ya aina ya data)]
**Uchunguzi Ulioundwa**:
```cypher
MATCH (c:cat)
RETURN c.name, c.number_of_legs
```

### Usanidi

```yaml
onto-query:
  embedding_model: "text-embedding-3-small"
  vector_store:
    shared_with_extractor: true  # Reuse kg-extract-ontology's store
  query_builder:
    model: "gpt-4"
    temperature: 0.1
    max_query_length: 1000
  graph_executor:
    timeout: 30000  # ms
    max_results: 1000
  answer_generator:
    model: "gpt-4"
    temperature: 0.3
    max_tokens: 500
```

### Uboreshaji wa Utendaji

#### Uboreshaji wa Maswali

**Uondoo wa Ontolojia**: Jumuisha tu vipengele muhimu vya ontolojia katika maagizo.
**Kuhifadhi Maswali Yanayoulizwa Mara kwa Mara**: Hifadhi maswali yanayoulizwa mara kwa mara na maswali yao.
**Kuhifadhi Matokeo**: Hifadhi matokeo kwa maswali sawa ndani ya muda maalum.
**Uchakataji wa Kundi**: Shughulikia maswali mengi yanayohusiana katika utafutaji mmoja wa chati.

#### Masuala ya Ukuaji

**Utendakazi Uliohusishwa**: Panga maswali madogo katika sehemu tofauti za chati.
**Matokeo ya Kuongezeka**: Tuma matokeo kwa data kubwa.
**Usawa wa Mizigo**: Sogeza mzigo wa maswali katika huduma tofauti.
**Makundi ya Rasilimali**: Dhibiti makundi ya muunganisho kwa hifadhia za chati.

### Usimamizi wa Madhira

#### Hali za Kushindwa

1. **Uundaji Usiofaa wa Swali**: Rudi kwenye GraphRAG au utafutaji rahisi wa neno.
2. **Utangamano Usiofaa wa Ontolojia**: Panua utafutaji hadi sehemu pana ya ontolojia.
3. **Kukata Tamaa kwa Swali**: Rahisisha swali au ongeza muda wa kutuma.
4. **Matokeo Nyembamba**: Pendekeza marekebisho ya swali au maswali yanayohusiana.
5. **Kushindwa kwa Huduma ya LLM**: Tumia maswali yaliyohifadhiwa au majibu ya msingi ya kigeuzi.

### Viashiria vya Ufuatiliaji

Usambazaji wa ugumu wa swali.
Ukubwa wa sehemu za ontolojia.
Kiwango cha mafanikio ya uundaji wa swali.
Muda wa utekelezaji wa swali la chati.
Alama za ubora wa jibu.
Viwango vya kufanikiwa kwa uhifadhi.
Masafa ya madhira kwa aina.

## Uboresho wa Baadaye

1. **Ujifunzaji wa Ontolojia**: Panua ontolojia moja kwa moja kulingana na mifumo ya uundaji.
2. **Upeo wa Umoja**: Toa alama za umoja kwa vipengele vilivyoundwa.
3. **Uundaji wa Maelezo**: Toa sababu kwa uundaji wa vipengele.
4. **Ujifunzaji Kamili**: Omba uthibitisho wa binadamu kwa uundaji usio wa uhakika.

## Masuala ya Usalama

1. **Kuzuia Uingizwaji wa Maagizo**: Safisha maandishi ya sehemu kabla ya uundaji wa agizo.
2. **Mipaka ya Rasilimali**: Punguza matumizi ya kumbukumbu kwa hifadhi ya vekta.
3. **Kikomo cha Kasi**: Punguza ombi la uundaji kwa kila mteja.
4. **Uandikaji wa Ufuatiliaji**: Fuatilia ombi na matokeo ya uundaji.

## Mkakati wa Majaribio

### Majaribio ya Kitengo

Mpakuzi wa ontolojia na muundo tofauti.
Uundaji na uhifadhi wa vekta.
Algorithmu za kutenganisha sentensi.
Hesabu za ufanano wa vekta.
Uchakataji na uthibitisho wa vipengele.

### Majaribio ya Uunganisho

Msururu kamili wa uundaji.
Uunganisho wa huduma ya usanidi.
Mwingiliano wa huduma ya agizo.
Usimamizi wa uundaji wa wakati mmoja.

### Majaribio ya Utendaji

Usimamizi wa ontolojia kubwa (madarasa 1000+).
Uchakataji wa kundi la juu.
Matumizi ya kumbukumbu chini ya mzigo.
Viwango vya kuchelewesha.

## Mpango wa Utoaji

### Muhtasari

Mfumo wa OntoRAG utatolewa katika awamu nne kuu, na kila awamu itatoa thamani ya hatua kwa hatua huku ikijenga mfumo kamili. Mpango huo unalenga kuanzisha uwezo wa msingi wa uundaji kwanza, kisha kuongeza utendakazi wa swali, kisha uboreshaji na vipengele vya hali ya juu.

### Awamu ya 1: Msingi na Uundaji wa Msingi

**Lengo**: Kuanzisha mstari wa msingi wa uundaji unaoongozwa na ontolojia na utangamano wa vekta rahisi.

#### Hatua ya 1.1: Msingi wa Usimamizi wa Ontolojia
Tengeneza mpakuzi wa usanidi wa ontolojia (`OntologyLoader`).
Pata na thibitisha miundo ya JSON ya ontolojia.
Unda hifadhi ya ontolojia ya ndani na mifumo ya ufikiaji.
Tengeneza utaratibu wa kusasisha ontolojia.

**Vigezo vya Mafanikio**:
Pakia na pata usanidi wa ontolojia.
Thibitisha muundo na utangamano wa ontolojia.
Shiriki ontolojia nyingi.

#### Hatua ya 1.2: Utumiaji wa Hifadhi ya Vektas
Tengeneza hifadhi ya vekta rahisi inayotumia NumPy kama mfano wa awali.
Ongeza utumiaji wa hifadhi ya vekta ya FAISS.
Unda utaratibu wa kiwango cha hifadhi ya vekta.
Tengeneza utafutaji wa ufanano na viwango vinavyoweza kusanidi.

**Vigezo vya Mafanikio**:
Kuhifadhi na kurejesha ujazo (embeddings) kwa ufanisi.
Kufanya utafutaji wa ufanano kwa latensi ya chini ya <100ms.
Kusaidia mifumo ya NumPy na FAISS.

#### Hatua ya 1.3: Mchakato wa Ujazo wa Ontolojia
Kuunganisha na huduma ya ujazo.
Kutekeleza kipengele cha `OntologyEmbedder`.
Kutoa ujazo kwa vipengele vyote vya ontolojia.
Kuhifadhi ujazo pamoja na metadata katika hifadhi ya vekta.

**Vigezo vya Mafanikio**:
Kutoa ujazo kwa madarasa na sifa.
Kuhifadhi ujazo pamoja na metadata sahihi.
Kujenga upya ujazo wakati wa sasisho za ontolojia.

#### Hatua ya 1.4: Vipengele vya Uchunguzi wa Nakala
Kutekeleza mgawaji wa sentensi kwa kutumia NLTK/spaCy.
Kuchukua maneno na vitambulisho.
Kuunda hierarkia ya sehemu za nakala.
Kutoa ujazo kwa sehemu za nakala.

**Vigezo vya Mafanikio**:
Kugawanya nakala katika sentensi kwa usahihi.
Kuchukua maneno yenye maana.
Kuhifadhi uhusiano wa muktadha.

#### Hatua ya 1.5: Algoritimu ya Uchaguzi wa Ontolojia
Kutekeleza utangamano kati ya nakala na ontolojia.
Kuunda utatuzi wa utegemezi kwa vipengele vya ontolojia.
Kuunda subseti ndogo na muunganisho.
Kuboresha utendaji wa utengenezaji wa subseti.

**Vigezo vya Mafanikio**:
Kuchagua vipengele muhimu vya ontolojia kwa usahihi wa >80%.
Kuunganisha utegemezi wote muhimu.
Kutoa subseti katika <500ms.

#### Hatua ya 1.6: Huduma ya Msingi ya Utoaji
Kutekeleza uundaji wa ombi la utoaji.
Kuunganisha na huduma ya ombi.
Kuchanganua na kuthibitisha majibu ya triplet.
Kuunda mwisho wa huduma ya `kg-extract-ontology`.

**Vigezo vya Mafanikio**:
Kutoa triplets inayolingana na ontolojia.
Kuthibitisha triplets zote dhidi ya ontolojia.
Kushughulikia makosa ya utoaji kwa utulivu.

### Awamu ya 2: Utendaji wa Mfumo wa Umasilifu

**Lengo**: Kuongeza uwezo wa masilifu unaoegemea kwenye ontolojia, kwa usaidizi wa mifumo mingi.

#### Hatua ya 2.1: Vipengele vya Msingi ya Umasilifu
Kutekeleza mchanganuzi wa swali.
Kuunda mlinganishi wa ontolojia kwa masilifu.
Kurekebisha utafutaji wa vekta kwa muktadha wa masilifu.
Kuunda kipengele cha kutoa masilifu.

**Vigezo vya Mafanikio**:
Kuchambua maswali katika vipengele vya semantic.
Kulinganisha maswali na vipengele muhimu vya ontolojia.
Kutoa masilifu kwa mfumo unaofaa.

#### Hatua ya 2.2: Utendaji wa Njia ya SPARQL
Kutekeleza huduma ya `onto-query-sparql`.
Kuunda jenereta ya swali la SPARQL kwa kutumia LLM.
Kuunda vipatterno vya ombi kwa utengenezaji wa SPARQL.
Kuthibitisha sintaksia iliyoundwa ya SPARQL.

**Vigezo vya Mafanikio**:
Kutoa maswali valid ya SPARQL.
Kutumia mitindo ya SPARQL inayofaa.
Kushughulikia aina ngumu za maswali.

#### Hatua ya 2.3: Injini ya SPARQL-Cassandra
Kutekeleza interface ya Hifadhi ya rdflib kwa Cassandra.
Kuunda mtafsiri wa swali la CQL.
Kuboresha utangamano wa muundo wa triplet.
Kushughulikia umbizo la matokeo ya SPARQL.

**Vigezo vya Mafanikio**:
Kutekeleza maswali ya SPARQL kwenye Cassandra.
Kusaidia mitindo ya kawaida ya SPARQL.
Kurudisha matokeo katika umbizo la kawaida.

#### Hatua ya 2.4: Utendaji wa Njia ya Cypher
Kutekeleza huduma ya `onto-query-cypher`.
Kuunda jenereta ya swali la Cypher kwa kutumia LLM.
Kuunda vipatterno vya ombi kwa utengenezaji wa Cypher.
Kuthibitisha sintaksia iliyoundwa ya Cypher.

**Vigezo vya Mafanikio**:
Kutoa maswali valid ya Cypher.
Kutumia mitindo ya grafu inayofaa.
Kusaidia Neo4j, Memgraph, FalkorDB.

#### Hatua ya 2.5: Mfumo wa Utendaji wa Cypher
Implement multi-database Cypher executor
Support Bolt protocol (Neo4j/Memgraph)
Support Redis protocol (FalkorDB)
Handle result normalization

**Success Criteria**:
Execute Cypher on all target databases
Handle database-specific differences
Maintain connection pools efficiently

#### Step 2.6: Answer Generation
Implement answer generator component
Create prompts for answer synthesis
Format query results for LLM consumption
Generate natural language answers

**Success Criteria**:
Generate accurate answers from query results
Maintain context from original question
Provide clear, concise responses

### Phase 3: Optimization and Robustness

**Goal**: Optimize performance, add caching, improve error handling, and enhance reliability.

#### Step 3.1: Performance Optimization
Implement embedding caching
Add query result caching
Optimize vector search with FAISS IVF indexes
Implement batch processing for embeddings

**Success Criteria**:
Reduce average query latency by 50%
Support 10x more concurrent requests
Maintain sub-second response times

#### Step 3.2: Advanced Error Handling
Implement comprehensive error recovery
Add fallback mechanisms between query paths
Create retry logic with exponential backoff
Improve error logging and diagnostics

**Success Criteria**:
Gracefully handle all failure scenarios
Automatic failover between backends
Detailed error reporting for debugging

#### Step 3.3: Monitoring and Observability
Add performance metrics collection
Implement query tracing
Create health check endpoints
Add resource usage monitoring

**Success Criteria**:
Track all key performance indicators
Identify bottlenecks quickly
Monitor system health in real-time

#### Step 3.4: Configuration Management
Implement dynamic configuration updates
Add configuration validation
Create configuration templates
Support environment-specific settings

**Success Criteria**:
Update configuration without restart
Validate all configuration changes
Support multiple deployment environments

### Phase 4: Advanced Features

**Goal**: Add sophisticated capabilities for production deployment and enhanced functionality.

#### Step 4.1: Multi-Ontology Support
Implement ontology selection logic
Support cross-ontology queries
Handle ontology versioning
Create ontology merge capabilities

**Success Criteria**:
Query across multiple ontologies
Handle ontology conflicts
Support ontology evolution

#### Step 4.2: Intelligent Query Routing
Implementa njia za msingi kulingana na utendaji
Ongeza uchambuzi wa utata wa swali
Unda algoriti za njia zinazobadilika
Saidia vipimo vya A/B kwa njia

**Vigezo vya Mafanikio**:
Pata njia za maswali kwa ufanisi
Jifunze kutoka kwa utendaji wa maswali
Boresha njia kwa muda

#### Hatua ya 4.3: Vipengele vya Uvunaji Vilivyoendelezwa
Ongeza alama za uaminifu kwa vitu
Leta utengenezaji wa maelezo
Unda mzunguko wa maoni kwa uboreshaji
Saidia ujifunzaji wa hatua kwa hatua

**Vigezo vya Mafanikio**:
Toa alama za uaminifu
Eleza maamuzi ya uvunaji
Boresha kwa ufanisi

#### Hatua ya 4.4: Uimarishaji wa Uzalishaji
Ongeza kikomo cha kasi
Leta uthibitishaji/idhinishaji
Unda automatisering ya usakinishaji
Ongeza nakala na urejesho

**Vigezo vya Mafanikio**:
Usalama unaofaa kwa uzalishaji
Mfumo wa usakinishaji uliyo na automatisering
Uwezo wa urejesho wa majanga

### Hatua za Utoaji

1. **Hatua ya 1** (Mwisho wa Awamu ya 1): Uvunaji wa msingi unaoendeshwa na ontolojia unafanya kazi
2. **Hatua ya 2** (Mwisho wa Awamu ya 2): Mfumo kamili wa maswali na njia za SPARQL na Cypher
3. **Hatua ya 3** (Mwisho wa Awamu ya 3): Mfumo uliopunguzwa, thabiti, na unaoendelea kufaa kwa majaribio
4. **Hatua ya 4** (Mwisho wa Awamu ya 4): Mfumo unaofaa kwa uzalishaji na vipengele vilivyoendelezwa

### Kupunguza Hatari

#### Hatari za Kiufundi
**Uwezo wa Hifadhi ya Vektor**: Anza na NumPy, uhamishie kwa FAISS hatua kwa hatua
**Ukamavu wa Uundaji wa Maswali**: Leta uthibitisho na njia mbadala
**Ulinganishi wa Backend**: Jaribu kwa uangalifu na kila aina ya hifadhidata
**Vizuizi vya Utendaji**: Fafanua mapema na mara kwa mara, boresha kwa hatua kwa hatua

#### Hatari za Uendeshaji
**Ubora wa Ontolojia**: Leta uthibitisho na ukaguzi wa utangamano
**Utegemezi wa Huduma**: Ongeza vituo vya mzunguko na njia mbadala
**Hadhara za Rasilimali**: Fuatilia na weka mipaka inayofaa
**Utangamano wa Data**: Leta ushughulikiaji sahihi wa miamala

### Viashiria vya Mafanikio

#### Viashiria vya Mafanikio ya Awamu ya 1
Ukamavu wa uvunaji: >90% utangamano wa ontolojia
Njia ya usindikaji: <1 sekunde kwa sehemu
Muda wa kupakia ontolojia: <10 sekunde
Latensi ya utafutaji wa vektor: <100ms

#### Viashiria vya Mafanikio ya Awamu ya 2
Njia ya mafanikio ya swali: >95%
Latensi ya swali: <2 sekunde kwa jumla
Ulinganishi wa backend: 100% kwa hifadhidata zilizolengwa
Ukamavu wa jibu: >85% kulingana na data iliyopo

#### Viashiria vya Mafanikio ya Awamu ya 3
Muda wa mfumo: >99.9%
Njia ya urejesho wa makosa: >95%
Njia ya hit ya kumbukumbu: >60%
Watumiaji wengi: >100

#### Viashiria vya Mafanikio ya Awamu ya 4
Maswali ya ontolojia nyingi: Yameunganishwa kikamilifu
Uboreshaji wa njia: Kupunguzwa kwa latensi ya 30%
Ukamavu wa alama: >90%
Usakinishaji wa uzalishaji: Masasisho bila kukatizwa

## Marejeleo

[Lugha ya Ontolojia ya Wavuti ya OWL 2](https://www.w3.org/TR/owl2-overview/)
[Usanifu wa GraphRAG](https://github.com/microsoft/graphrag)
[Transformers za Sentensi](https://www.sbert.net/)
[Utafiti wa Vektor wa FAISS](https://github.com/facebookresearch/faiss)
[Maktaba ya NLP ya spaCy](https://spacy.io/)
[Dokumenti ya rdflib](https://rdflib.readthedocs.io/)
[Itifaki ya Neo4j Bolt](https://neo4j.com/docs/bolt/current/)
