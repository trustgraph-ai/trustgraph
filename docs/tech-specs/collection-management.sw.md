# Maelekezo ya Ufundi ya Usimamizi wa Mkusanyiko

## Muhtasari

Maelekezo haya yanaelezea uwezo wa usimamizi wa mkusanyiko kwa TrustGraph, ambayo yanahitaji uundaji wa mkusanyiko unaoonekana na yanatoa udhibiti wa moja kwa moja wa mzunguko wa maisha wa mkusanyiko. Mkusanyiko lazima uundwe kwa uwazi kabla ya kutumika, kuhakikisha usawazishaji sahihi kati ya metadata ya msimamizi na kila mfumo wa kuhifadhi. Kipengele hiki kinaunga mkazo kwa matumizi manne makuu:

1. **Uundaji wa Mkusanyiko**: Unda mkusanyiko kwa uwazi kabla ya kuhifadhi data
2. **Orodha ya Mkusanyiko**: Angalia mkusanyiko wote uliopo katika mfumo
3. **Usimamizi wa Metadata ya Mkusanyiko**: Sasisha majina, maelezo, na lebo za mkusanyiko
4. **Ufutaji wa Mkusanyiko**: Ondoa mkusanyiko na data inayohusiana katika aina zote za uhifadhi

## Lengo

**Uundaji wa Mkusanyiko unaoonekana**: Hakikisha mkusanyiko uundwe kabla ya data kuweza kuhifadhiwa
**Usawazishaji wa Uhifadhi**: Hakikisha mkusanyiko umezaliwa katika mifumo yote ya uhifadhi (vektali, vitu, triplet)
**Uonevu wa Mkusanyiko**: Wasaidie watumiaji kuorodhesha na kuchunguza mkusanyiko wote katika mazingira yao
**Usafishaji wa Mkusanyiko**: Waruhusu kuondoa mkusanyiko ambao hauhitajiki tena
**Mpangilio wa Mkusanyiko**: Unga lebo na lebo za mada kwa ajili ya ufuatiliaji na ugunduzi bora wa mkusanyiko
**Usimamizi wa Metadata**: Unganisha metadata inayoeleweka na mkusanyiko kwa uwazi wa utendaji
**Ugunduzi wa Mkusanyiko**: Ifanye iwe rahisi zaidi kupata mkusanyiko maalum kupitia utaratibu na utafutaji
**Uwazi wa Utendaji**: Toa uonevu wazi wa mzunguko wa maisha na matumizi ya mkusanyiko
**Usimamizi wa Rasilimali**: Wasaidie kusafisha mkusanyiko usiohitajika ili kuongeza matumizi ya rasilimali
**Uadilifu wa Data**: Zuia mkusanyiko usio na uhusiano katika uhifadhi bila kufuatilia metadata

## Asili

Hapo awali, mkusanyiko katika TrustGraph uliundwa kwa njia isiyoonekana wakati wa operesheni za kupakia data, na kusababisha matatizo ya usawazishaji ambapo mkusanyiko ulikuwa na uwezekano wa kuwepo katika mifumo ya uhifadhi bila metadata inayolingana katika msimamizi. Hii ilisababisha changamoto za usimamizi na uwezekano wa data isiyo na uhusiano.

Mfumo wa uundaji wa mkusanyiko unaoonekana unafanya kazi na masuala haya kwa:
Kuhitaji mkusanyiko uundwe kabla ya kutumika kupitia `tg-set-collection`
Kutangaza uundaji wa mkusanyiko kwa mifumo yote ya uhifadhi
Kuhifadhi hali iliyosawazishwa kati ya metadata ya msimamizi na uhifadhi
Kuzuia uandishi kwenye mkusanyiko usio na uwepo
Kutoa usimamizi wazi wa mzunguko wa maisha wa mkusanyiko

Maelekezo haya yanafafanua mfumo wa usimamizi wa mkusanyiko unaoonekana. Kwa kuhitaji uundaji wa mkusanyiko unaoonekana, TrustGraph huhakikisha:
Mkusanyiko unafuatiliwa katika metadata ya msimamizi kuanzia uundaji
Mifumo yote ya uhifadhi inajua mkusanyiko kabla ya kupokea data
Hakuna mkusanyiko usio na uhusiano katika uhifadhi
Uwazi wa utendaji na udhibiti wa mzunguko wa maisha wa mkusanyiko
Usimamizi thabiti wa makosa wakati operesheni zinarejelea mkusanyiko usio na uwepo

## Ubunifu wa Kiufundi

### Usanifu

Mfumo wa usimamizi wa mkusanyiko utatekelezwa ndani ya miundombinu iliyopo ya TrustGraph:

1. **Jumuisha Huduma ya Msimamizi**
   Operesheni za usimamizi wa mkusanyiko zitaongezwa kwenye huduma iliyopo ya msimamizi
   Huduma mpya haihitajiki - inatumia mitindo iliyopo ya uthibitishaji na ufikiaji
   Inashughulikia orodha ya mkusanyiko, kufutwa, na usimamizi wa metadata

   Moduli: trustgraph-librarian

2. **Jedwali la Metadata ya Mkusanyiko la Cassandra**
   Jedwali jipya katika nafasi ya funguo ya msimamizi iliyopo
   Inahifadhi metadata ya mkusanyiko na ufikiaji wa mtumiaji
   Ufunguo mkuu: (user_id, collection_id) kwa usawazishaji sahihi wa wateja wengi

   Moduli: trustgraph-librarian

3. **Kifaa cha Amri cha Usimamizi wa Mkusanyiko**
   Kiwao cha amri kwa operesheni za mkusanyiko
   Inatoa orodha, kufuta, lebo, na amri za usimamizi wa lebo
   Inajumuisha na mfumo uliopo wa kifaa cha amri

   Moduli: trustgraph-cli

### Mifano ya Data

#### Jedwali la Metadata ya Mkusanyiko la Cassandra

Metadata ya mkusanyiko itahifadhiwa katika jedwali lililopangwa la Cassandra katika nafasi ya funguo ya msimamizi:

```sql
CREATE TABLE collections (
    user text,
    collection text,
    name text,
    description text,
    tags set<text>,
    created_at timestamp,
    updated_at timestamp,
    PRIMARY KEY (user, collection)
);
```

Muundo wa jedwali:
**user** + **collection**: Ufunguo mkuu unaojumuisha unaohakikisha kutenganishwa kwa watumiaji
**name**: Jina la mkusanyiko linaloweza kusomwa na binadamu
**description**: Maelezo ya kina ya madhumuni ya mkusanyiko
**tags**: Kundi la lebo kwa ajili ya uainishaji na kuchujwa
**created_at**: Alama ya muda ya uundaji wa mkusanyiko
**updated_at**: Alama ya muda ya mabadiliko ya mwisho

Mbinu hii inaruhusu:
Usimamizi wa mkusanyiko wa wateja wengi pamoja na kutenganishwa kwa watumiaji
Ufuatiliaji wa haraka kwa mtumiaji na mkusanyiko
Mfumo wa lebo unaobadilika kwa ajili ya upangaji
Ufuatiliaji wa mzunguko wa maisha kwa ajili ya ufahamu wa utendaji

#### Mzunguko wa Maisha wa Mkusanyiko

Mkusanyiko huundwa wazi katika mfumo wa usimamizi kabla ya shughuli za data zinaweza kuendelea:

1. **Uundaji wa Mkusanyiko** (Njia Mbili):

   **Njia A: Uundaji unaoanzishwa na Mtumiaji** kupitia `tg-set-collection`:
   Mtumiaji hutoa kitambulisho cha mkusanyiko, jina, maelezo, na lebo
   Mfumo wa usimamizi huunda rekodi ya metadata katika meza ya `collections`
   Mfumo wa usimamizi hutuma "unda-mkusanyiko" kwa kila mfumo wa kuhifadhi
   Mifumo yote ya kuhifadhi huunda mkusanyiko na kuthibitisha mafanikio
   Mkusanyiko sasa uko tayari kwa shughuli za data

   **Njia B: Uundaji Otomatiki wakati wa Uwasilishaji wa Hati**:
   Mtumiaji huwasilisha hati inayobainisha kitambulisho cha mkusanyiko
   Mfumo wa usimamizi huhakikisha ikiwa mkusanyiko umejumuishwa katika meza ya metadata
   Ikiwa haujumuishwa: Mfumo wa usimamizi huunda metadata na mipangilio chache (jina=kitambulisho_cha_mkusanyiko, maelezo/lebo tupu)
   Mfumo wa usimamizi hutuma "unda-mkusanyiko" kwa kila mfumo wa kuhifadhi
   Mifumo yote ya kuhifadhi huunda mkusanyiko na kuthibitisha mafanikio
   Ufuatiliaji wa hati unaendelea na mkusanyiko sasa umeanzishwa

   Njia zote mbili zinahakikisha kuwa mkusanyiko umejumuishwa katika metadata ya mfumo wa usimamizi NA katika mifumo yote ya kuhifadhi kabla ya shughuli za data.

2. **Uthibitisho wa Uhifadhi**: Shughuli za kuandika zinathibitisha kuwa mkusanyiko umejumuishwa:
   Mifumo ya kuhifadhi huhakikisha hali ya mkusanyiko kabla ya kukubali kuandika
   Kuandika kwa mkusanyiko usiojumuishwa kunarudisha kosa
   Hii inazuia kuandika moja kwa moja ambayo yanaweza kuepuka mantiki ya uundaji wa mkusanyiko ya mfumo wa usimamizi

3. **Tabia ya Ufuatiliaji**: Shughuli za kufuatilia hushughulikia mkusanyiko usiojumuishwa kwa utulivu:
   Ufuatiliaji kwa mkusanyiko usiojumuishwa hurudisha matokeo tupu
   Hakuna kosa linalorushwa kwa shughuli za kufuatilia
   Inaruhusu uchunguzi bila kuhitaji mkusanyiko kuwepo

4. **Sasisho za Metadata**: Watumiaji wanaweza kusasisha metadata ya mkusanyiko baada ya uundaji:
   Sasisha jina, maelezo, na lebo kupitia `tg-set-collection`
   Sasisho hutumika kwa metadata ya mfumo wa usimamizi pekee
   Mifumo ya kuhifadhi yanaendelea kuweka mkusanyiko lakini sasisho za metadata hazisambazwi

5. **Ufutaji Wazi**: Watumiaji huondoa mkusanyiko kupitia `tg-delete-collection`:
   Mfumo wa usimamizi hutuma "ondoa-mkusanyiko" kwa kila mfumo wa kuhifadhi
   Inasubiri uthibitisho kutoka kwa mifumo yote ya kuhifadhi
   Huondoa rekodi ya metadata ya mfumo wa usimamizi tu baada ya kusafishwa kwa uhifadhi kukamilika
   Inahakikisha hakuna data iliyoachwa katika uhifadhi

**Kanuni Muhimu**: Mfumo wa usimamizi ndio sehemu pekee ya udhibiti kwa uundaji wa mkusanyiko. Iwe iliyoanzishwa na amri ya mtumiaji au uwasilishaji wa hati, mfumo wa usimamizi huhakikisha ufuatiliaji sahihi wa metadata na usawazishaji wa mfumo wa kuhifadhi kabla ya kuruhusu shughuli za data.

Shughuli zinazohitajika:
**Unda Mkusanyiko**: Shughuli ya mtumiaji kupitia `tg-set-collection` AU otomatiki wakati wa uwasilishaji wa hati
**Sasisha Metadata ya Mkusanyiko**: Shughuli ya mtumiaji ili kurekebisha jina, maelezo, na lebo
**Ondoa Mkusanyiko**: Shughuli ya mtumiaji ili kuondoa mkusanyiko na data yake katika maduka yote
**Orodha ya Mkusanyiko**: Shughuli ya mtumiaji ili kuona mkusanyiko pamoja na kuchujwa kwa lebo

#### Usimamizi wa Mkusanyiko wa Maduka Mengi

Mkusanyiko huwepo katika mifumo tofauti ya kuhifadhi katika TrustGraph:
**Maduka ya Vifaa** (Qdrant, Milvus, Pinecone): Kuhifadhi vifaa na data ya vifaa
**Maduka ya Vitu** (Cassandra): Kuhifadhi hati na data ya faili
**Maduka ya Vitatu** (Cassandra, Neo4j, Memgraph, FalkorDB): Kuhifadhi data ya grafu/RDF

Kila aina ya duka inatekeleza:
**Ufuatiliaji wa Hali ya Mkusanyiko**: Kuhifadhi habari kuhusu makusanyiko ambayo yamepo.
**Uundaji wa Mkusanyiko**: Kukubali na kuchakata "unda-mkusanyiko" shughuli.
**Uthibitisho wa Mkusanyiko**: Angalia ikiwa mkusanyiko unapatikana kabla ya kukubali uandikaji.
**Ufutaji wa Mkusanyiko**: Ondoa data yote kwa mkusanyiko uliotajwa.

Huduma ya mhakimishi inaangazia shughuli za mkusanyiko katika aina zote za kuhifadhi, kuhakikisha:
Makusanyiko yanaundwa katika mifumo yote ya nyuma kabla ya matumizi.
Mifumo yote ya nyuma inaonyesha uundaji kabla ya kurejesha mafanikio.
Mzunguko wa mkusanyiko umeunganishwa katika aina tofauti za uhifadhi.
Usimamizi thabiti wa makosa wakati makusanyiko hayapo.

#### Ufuatiliaji wa Hali ya Mkusanyiko kwa Aina ya Uhifadhi

Kila mfumo wa nyuma wa uhifadhi unafuatilia hali ya mkusanyiko tofauti kulingana na uwezo wake:

**Duka la Maneno la Cassandra:**
Hutumia meza iliyopo `triples_collection`.
Huunda alama ya mfumo wakati mkusanyiko unaundwa.
Uulizo: `SELECT collection FROM triples_collection WHERE collection = ? LIMIT 1`.
Uchunguzi wa sehemu moja kwa uwepo wa mkusanyiko.

**Vifaa vya Vector vya Qdrant/Milvus/Pinecone:**
API za asili za mkusanyiko hutoa uchunguzi wa uwepo.
Makusanyiko yanaundwa na usanidi sahihi wa vector.
Njia `collection_exists()` hutumia API ya uhifadhi.
Uundaji wa mkusanyiko unafanya uthibitisho wa mahitaji ya kipimo.

**Vifaa vya Grafu vya Neo4j/Memgraph/FalkorDB:**
Hutumia nodi `:CollectionMetadata` kufuatilia makusanyiko.
Vipengele vya nodi: `{user, collection, created_at}`.
Uulizo: `MATCH (c:CollectionMetadata {user: $user, collection: $collection})`.
Tofauti na nodi za data kwa kutenganisha vizuri.
Inaruhusu orodha na uthibitisho wa mkusanyiko kuwa rahisi.

**Duka la Vitu la Cassandra:**
Hutumia meza ya metadata ya mkusanyiko au mistari ya alama.
Mfano sawa na duka la maneno.
Inathibitisha mkusanyiko kabla ya uandikaji wa hati.

### API

API za Usimamizi wa Mkusanyiko (Mhakimishi):
**Unda/Boresha Mkusanyiko**: Unda mkusanyiko mpya au boresha metadata iliyopo kupitia `tg-set-collection`.
**Orodha ya Makusanyiko**: Pata makusanyiko kwa mtumiaji na uchujaji wa tag wa hiari.
**Futa Mkusanyiko**: Ondoa mkusanyiko na data inayohusiana, na kuenea kwa aina zote za kuhifadhi.

API za Usimamizi wa Uhifadhi (Wote Wasindikaji wa Uhifadhi):
**Unda Mkusanyiko**: Shughuli ya "unda-mkusanyiko", weka mkusanyiko katika uhifadhi.
**Futa Mkusanyiko**: Shughuli ya "futa-mkusanyiko", ondoa data yote ya mkusanyiko.
**Angalia Ikiwa Mkusanyiko Upo**: Uthibitisho wa ndani kabla ya kukubali shughuli za uandikaji.

API za Uendeshaji wa Data (Tabia Imebadilishwa):
**API za Uandikaji**: Thibitisha kuwa mkusanyiko unapatikana kabla ya kukubali data, na uweke makosa ikiwa haipo.
**API za Uulizo**: Rejesha matokeo tupu kwa makusanyiko ambayo hayapo bila makosa.

### Maelezo ya Utendaji

Utendaji utafuata mifumo iliyopo ya TrustGraph kwa ujumuishaji wa huduma na muundo wa amri ya CLI.

#### Ufufuo wa Ufufuo wa Mkusanyiko

Wakati mtumiaji anaanzisha ufutaji wa mkusanyiko kupitia huduma ya mhakimishi:

1. **Uthibitisho wa Metadata**: Thibitisha kuwa mkusanyiko unapatikana na mtumiaji ana ruhusa ya kufuta.
2. **Ufufuo wa Duka**: Mhakimishi inaangazia ufutaji katika waandishi wote wa duka:
   Mwandishi wa duka la vector: Ondoa embeddings na fahirisi za vector kwa mtumiaji na mkusanyiko.
   Mwandishi wa duka la kitu: Ondoa hati na faili kwa mtumiaji na mkusanyiko.
   Mwandishi wa duka la maneno: Ondoa data ya grafu na maneno kwa mtumiaji na mkusanyiko.
3. **Usafishaji wa Metadata**: Ondoa rekodi ya metadata ya mkusanyiko kutoka Cassandra.
4. **Usimamizi wa Makosa**: Ikiwa ufutaji wowote wa duka hufeli, dhibiti uthabiti kupitia utaratibu wa kurejesha au kujaribu tena.

#### Kiolesura cha Usimamizi wa Mkusanyiko

**⚠️ MFUMO WA KALE - IMEBADILISHWA NA MFUMO WA MSINGI WA MSINGI**

Arkitektura iliyoelezwa ya msingi ya folyo imebadilishwa na mbinu iliyosimama na usanidi inayotumia `CollectionConfigHandler`. Mifumo yote ya nyuma ya uhifadhi sasa hupokea sasisho za mkusanyiko kupitia ujumbe wa kushinikiza usanidi badala ya folyo maalum za usimamizi.

~~Wote waandishi wa duka inatekeleza kiolesura cha kawaida cha usimamizi wa mkusanyiko na schema ya kawaida:~~

~~**Schema ya Ujumbe (`StorageManagementRequest`):**~~
```json
{
  "operation": "create-collection" | "delete-collection",
  "user": "user123",
  "collection": "documents-2024"
}
```

~~**Usawa wa Mifumo:**~~
~~**Kikao cha Usimamizi wa Hifadhi ya Data (Vector Store)** (`vector-storage-management`): Hifadhi za vector/embedding~~
~~**Kikao cha Usimamizi wa Hifadhi ya Data (Object Store)** (`object-storage-management`): Hifadhi za data/nyaraka~~
~~**Kikao cha Usimamizi wa Hifadhi ya Data (Triple Store)** (`triples-storage-management`): Hifadhi za grafu/RDF~~
~~**Kikao cha Majibu ya Hifadhi ya Data** (`storage-management-response`): Majibu yote hutumwa hapa~~

**Utendaji Sasa:**

Mifumo yote ya hifadhi ya data sasa hutumia `CollectionConfigHandler`:
**Uunganishaji wa Uhamisho wa Config**: Huduma za hifadhi ya data huzungushwa kwa arifa za uhamisho wa config
**Usawajili Otomatiki**: Mkusanyiko huundwa/kufutwa kulingana na mabadiliko ya config
**Mfumo wa Kielelezo:** Mkusanyiko umeinuliwa katika huduma ya config, hifadhi ya data husawazishwa ili kuendana
**Hakuna Ombi/Jibu:** Huondoa gharama ya uratibu na ufuatiliaji wa majibu
**Ufuatiliaji wa Hali ya Mkusanyiko:** Inahifadhiwa kupitia kumbukumbu `known_collections`
**Operesheni za Idempotent:** Ni salama kuchakata config sawa mara nyingi

Kila mfumo wa hifadhi ya data unatekeleza:
`create_collection(user: str, collection: str, metadata: dict)` - Unda miundo ya mkusanyiko
`delete_collection(user: str, collection: str)` - Ondoa data yote ya mkusanyiko
`collection_exists(user: str, collection: str) -> bool` - Thibitisha kabla ya kuandika

#### Urekebishaji wa Hifadhi ya Data ya Triple ya Cassandra

Kama sehemu ya utekelezaji huu, hifadhi ya data ya triple ya Cassandra itarekebishwa kutoka kwa mfumo wa jedwali-kwa-mkusanyiko hadi mfumo wa jedwali lililo na muundo mmoja:

**Muundo Sasa:**
Keyspace kwa kila mtumiaji, jedwali tofauti kwa kila mkusanyiko
Schema: `(s, p, o)` na `PRIMARY KEY (s, p, o)`
Majina ya jedwali: mkusanyiko wa mtumiaji unakuwa jedwali tofauti za Cassandra

**Muundo Mpya:**
Keyspace kwa kila mtumiaji, jedwali moja la "triples" kwa mkusanyiko wote
Schema: `(collection, s, p, o)` na `PRIMARY KEY (collection, s, p, o)`
Utengano wa mkusanyiko kupitia ugawaji wa mkusanyiko

**Mabadiliko Yanayohitajika:**

1. **Urekebishaji wa Darasa la TrustGraph** (`trustgraph/direct/cassandra.py`):
   Ondoa parameter `table` kutoka kwa konstrukata, tumia jedwali "triples" lililo na muundo mmoja
   Ongeza parameter `collection` kwa mbinu zote
   Sasisha schema ili kujumuisha mkusanyiko kama safu ya kwanza
   **Sasisho za Indexi:** Indexi mpya zitaundwa ili kusaidia mifumo yote 8 ya swali:
     Indexi kwenye `(s)` kwa maswali yanayohusiana na mada
     Indexi kwenye `(p)` kwa maswali yanayohusiana na sifa
     Indexi kwenye `(o)` kwa maswali yanayohusiana na kitu
     Kumbuka: Cassandra haitumii indexi za sekondari za safu nyingi, kwa hivyo hizi ni indexi za safu moja

   **Utendaji wa Mfumo wa Swali:**
     ✅ `get_all()` - skani ya ugawaji kwenye `collection`
     ✅ `get_s(s)` - hutumia ufunguo mkuu kwa ufanisi (`collection, s`)
     ✅ `get_p(p)` - hutumia `idx_p` na `collection` ya kuchujwa
     ✅ `get_o(o)` - hutumia `idx_o` na `collection` ya kuchujwa
     ✅ `get_sp(s, p)` - hutumia ufunguo mkuu kwa ufanisi (`collection, s, p`)
     ⚠️ `get_po(p, o)` - inahitaji `ALLOW FILTERING` (inatumia ama `idx_p` au `idx_o` pamoja na kuchujwa)
     ✅ `get_os(o, s)` - hutumia `idx_o` na kuchujwa cha ziada kwenye `s`
     ✅ `get_spo(s, p, o)` - hutumia ufunguo mkuu kwa ufanisi

   **Kumbuka kuhusu ALLOW FILTERING:** Mfumo wa swali `get_po` unahitaji `ALLOW FILTERING` kwa sababu unahitaji sifa na kikomo cha kitu bila indexi ya pamoja inayofaa. Hii inakubalika kwa sababu mfumo huu wa swali ni mdogo kuliko maswali yanayohusiana na mada katika matumizi ya kawaida ya hifadhi ya data ya triple

2. **Sasisho za Mwandishi wa Hifadhi ya Data** (`trustgraph/storage/triples/cassandra/write.py`):
   Dumishe muunganisho mmoja wa TrustGraph kwa kila mtumiaji badala ya kwa kila (mtumiaji, mkusanyiko)
   Pasa mkusanyiko kwenye operesheni za kuingiza
   Matumizi bora ya rasilimali kwa muunganisho mdogo

3. **Sasisho za Huduma ya Swali** (`trustgraph/query/triples/cassandra/service.py`):
   Muunganisho mmoja wa TrustGraph kwa kila mtumiaji
   Pasa mkusanyiko kwa operesheni zote za swali
   Dumishe mantiki sawa ya swali na parameter ya mkusanyiko

**Faida:**
**Uondoo Ulioboreshwa wa Mkusanyiko:** Ondoa kwa kutumia ufunguo wa ugawaji `collection` katika meza zote 4
**Ufanisi wa Rasilimali:** Muunganisho mdogo wa hifadhi ya data na vitu vya jedwali
**Operesheni za Mkusanyiko Mbalimbali:** Ni rahisi kutekeleza operesheni zinazohusisha mkusanyiko mwingi
**Muundo Uliofanana:** Inalingana na mbinu iliyounganishwa ya metadata ya mkusanyiko
**Uthibitisho wa Mkusanyiko:** Ni rahisi kuangalia uwepo wa mkusanyiko kupitia jedwali `triples_collection`

Operesheni za ukusanyaji zitakuwa za atomiki ambapo inawezekana na hutoa utunzaji wa makosa unaofaa na uthibitisho.

## Masuala ya Usalama

Operesheni za usimamizi wa ukusanyaji zinahitaji idhini inayofaa ili kuzuia ufikiaji usioidhinishwa au kufutwa kwa ukusanyaji. Udhibiti wa ufikiaji utalingana na modeli za usalama za TrustGraph zilizopo.

## Masuala ya Utendaji

Operesheni za kuorodhesha ukusanyaji zinaweza kuhitaji upangishaji katika mazingira yenye idadi kubwa ya ukusanyaji. Maswali ya metadata yanapaswa kuboreshwa kwa mifumo ya kawaida ya kuchujwa.

## Mkakati wa Majaribio

Majaribio kamili yataangazia:
Mchakato wa kuunda ukusanyaji kutoka mwanzo hadi mwisho
Usawazishaji wa mfumo wa kuhifadhi data
Uthibitisho wa kuandika kwa ukusanyaji usiopo
Usimamizi wa maswali ya ukusanyaji usiopo
Ufutilishaji wa ukusanyaji unaoenea katika maduka yote
Usimamizi wa makosa na hali ya uponyaji
Majaribio ya kitengo kwa kila mfumo wa kuhifadhi data
Majaribio ya ujumuishaji kwa operesheni za duka nyingi

## Hali ya Utendaji

### ✅ Vipengele Vilivyokamilika

1. **Huduma ya Usimamizi wa Ukusanyaji ya Librarian** (`trustgraph-flow/trustgraph/librarian/collection_manager.py`)
   Operesheni za CRUD za metadata ya ukusanyaji (orodha, sasisha, futa)
   Ujumuishaji wa jedwali la metadata ya ukusanyaji ya Cassandra kupitia `LibraryTableStore`
   Uratibu wa kufutiliwa kwa ukusanyaji unaoenea katika aina zote za uhifadhi
   Usimamizi wa ombi/jibu lisilo na wakati pamoja na usimamizi wa makosa unaofaa

2. **Mfumo wa Metadata wa Ukusanyaji** (`trustgraph-base/trustgraph/schema/services/collection.py`)
   Mfumo wa `CollectionManagementRequest` na `CollectionManagementResponse`
   Mfumo wa `CollectionMetadata` kwa rekodi za ukusanyaji
   Ufafanuzi wa mada ya folyo ya ombi/jibu la ukusanyaji

3. **Mfumo wa Usimamizi wa Uhifadhi** (`trustgraph-base/trustgraph/schema/services/storage.py`)
   Mfumo wa `StorageManagementRequest` na `StorageManagementResponse`
   Mada za folyo za usimamizi wa uhifadhi zimefafanuliwa
   Muundo wa ujumbe kwa operesheni za ukusanyaji za kiwango cha uhifadhi

4. **Mfumo wa Jedwali la Cassandra 4** (`trustgraph-flow/trustgraph/direct/cassandra_kg.py`)
   Funguo za sehemu mchanganyiko kwa utendaji wa swali
   Jedwali la `triples_collection` kwa maswali ya SPO na kufuatilia kufutiliwa
   Ufutilishaji wa ukusanyaji umetekelezwa na mfumo wa kusoma kisha kufuta

### ✅ Uhamishaji kwa Mfumo Kulingana na Config - UMEKABALIKA

**Maduka yote ya uhifadhi yamehamishwa kutoka kwa mfumo unaotegemea folyo hadi kwa mfumo unaotegemea config wa `CollectionConfigHandler`.**

Uhamishaji uliokamilika:
✅ `trustgraph-flow/trustgraph/storage/triples/cassandra/write.py`
✅ `trustgraph-flow/trustgraph/storage/triples/neo4j/write.py`
✅ `trustgraph-flow/trustgraph/storage/triples/memgraph/write.py`
✅ `trustgraph-flow/trustgraph/storage/triples/falkordb/write.py`
✅ `trustgraph-flow/trustgraph/storage/doc_embeddings/qdrant/write.py`
✅ `trustgraph-flow/trustgraph/storage/graph_embeddings/qdrant/write.py`
✅ `trustgraph-flow/trustgraph/storage/doc_embeddings/milvus/write.py`
✅ `trustgraph-flow/trustgraph/storage/graph_embeddings/milvus/write.py`
✅ `trustgraph-flow/trustgraph/storage/doc_embeddings/pinecone/write.py`
✅ `trustgraph-flow/trustgraph/storage/graph_embeddings/pinecone/write.py`
✅ `trustgraph-flow/trustgraph/storage/objects/cassandra/write.py`

Maduka yote sasa:
Yanachukua kutoka `CollectionConfigHandler`
Yamesajiliwa kwa arifa za config inayoboreshwa kupitia `self.register_config_handler(self.on_collection_config)`
Yatekeleza `create_collection(user, collection, metadata)` na `delete_collection(user, collection)`
Yatumie `collection_exists(user, collection)` ili kuthibitisha kabla ya kuandika
Yanasawazishwa kiotomatiki na mabadiliko ya huduma ya config

Infrastrakturu ya zamani inayotegemea folyo imeondolewa:
✅ Mfumo wa `StorageManagementRequest` na `StorageManagementResponse` umeondolewa
✅ Ufafanuzi wa mada za usimamizi wa uhifadhi umeondolewa
✅ Mtumiaji/mtayarishaji wa folyo kutoka kwa maduka yote umeondolewa
✅ Wasimamizi wa `on_storage_management` kutoka kwa maduka yote umeondolewa

