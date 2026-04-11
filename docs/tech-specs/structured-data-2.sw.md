---
layout: default
title: "Vipimo vya Kawaida vya Takwimu Zilizopangwa (Sehemu ya 2)"
parent: "Swahili (Beta)"
---

# Vipimo vya Kawaida vya Takwimu Zilizopangwa (Sehemu ya 2)

> **Beta Translation:** This document was translated via Machine Learning and as such may not be 100% accurate. All non-English languages are currently classified as Beta.

## Muhtasari

Maelezo haya yanaeleza masuala na pengo ambazo zimetambuliwa wakati wa utekelezaji wa awali wa ujumuishaji wa takwimu zilizopangwa wa TrustGraph, kama ilivyoelezwa katika `structured-data.md`.

## Matatizo

### 1. Utangamano Usio sawa wa Majina: "Kitu" dhidi ya "Rata"

Utaratibu wa sasa hutumia neno "kitembele" katika kila sehemu (k.m., `ExtractedObject`, utoaji wa kitu, uwekaji wa kitu). Neno hili ni la jumla sana na husababisha mchanganyiko:

"Kitembele" ni neno linalotumika kwa matumizi mengi katika programu (vitu vya Python, vitu vya JSON, n.k.)
Data inayoshughulikiwa ni ya aina ya meza - ratiba katika meza zilizo na muundo uliotofautishwa
"Rata" inaelezea vizuri zaidi mfumo wa data na inaendana na neno la hifadhi ya data

Utangamano huu huonekana katika majina ya moduli, majina ya madarasa, aina za ujumbe, na nyaraka.

### 2. Mipaka ya Ufuatiliaji wa Rata

Utaratibu wa sasa wa hifadhi ya rata una mipaka muhimu ya ufuatiliaji:

**Utangamano wa Lugha Asilia:** Ufuatiliaji unashindana na tofauti za ulimwengu halisi. Kwa mfano:
Ni vigumu kupata hifadhi ya barabara inayokuwa na `"CHESTNUT ST"` wakati unatafuta `"Chestnut Street"`
Marekebisho, tofauti za herufi, na tofauti za umbizo hufutilia ufuatiliaji wa usawizi
Watumiaji wanatarajia uelewa wa maana, lakini hifadhi hutoa mechi ya moja kwa moja

**Masuala ya Mabadiliko ya Muundo:** Mabadiliko ya muundo husababisha matatizo:
Data iliyopo inaweza kutosana na muundo uliosasishwa
Mabadiliko ya muundo wa meza yanaweza kuvunja ufuatiliaji na uadilifu wa data
Hakuna njia wazi ya kusonga muundo kwa mabadiliko ya muundo

### 3. Uwekaji wa Rata Unahitajika

Kuhusiana na tatizo la 2, mfumo unahitaji uwekaji wa vector kwa data ya rata ili kuwezesha:

Ufuatiliaji wa maana katika data iliyopangwa (kupata "Chestnut Street" wakati data ina "CHESTNUT ST")
Mechi ya ufanano kwa ufuatiliaji wa uwazi
Ufuatiliaji wa mchanganyiko unaounganisha vichujio vilivyopangwa na ufanano wa maana
Usaidizi bora wa lugha asilia ya ufuatiliaji

Huduma ya uwekaji ilikuwa imeelezwa lakini haijatekelezwa.

### 4. Uongezaji wa Data ya Rata hajakamilika

Mnyororo wa data ya takwimu zilizopangwa haujafanya kazi kikamilifu:

Mawazo ya uchunguzi yanapatikana ili kuainisha muundo wa pembejeo (CSV, JSON, n.k.)
Huduma ya uongezaji ambayo hutumia mawazo haya haijunganishwa kwenye mfumo
Hakuna njia kamili ya kupakia data iliyopangwa tayari kwenye hifadhi ya rata

## Lengo

**Unyumbufu wa Muundo:** Kuwezesha mabadiliko ya muundo bila kuvunja data iliyopo au kuhitaji uhamisho
**Utangamano wa Majina:** Kuweka "rata" kama neno la kawaida katika kila sehemu ya programu
**Ufuatiliaji wa Maana:** Kusaidia mechi ya maana/uwazi kupitia uwekaji wa rata
**Mnyororo Kamili wa Uongezaji:** Kutoa njia kamili ya kupakia data iliyopangwa

## Muundo wa Kiufundi

### Muundo Uliounganishwa wa Hifadhi ya Rata

Utaratibu wa awali uliunda meza tofauti ya Cassandra kwa kila muundo. Hii ilisababisha matatizo wakati muundo ulibadilika, kwa sababu mabadiliko ya muundo wa meza yalihitaji uhamisho.

Muundo mpya hutumia meza moja iliyounganishwa kwa data yote ya rata:

```sql
CREATE TABLE rows (
    collection text,
    schema_name text,
    index_name text,
    index_value frozen<list<text>>,
    data map<text, text>,
    source text,
    PRIMARY KEY ((collection, schema_name, index_name), index_value)
)
```

#### Ufafanuzi wa Safu

| Safu | Aina | Maelezo |
|--------|------|-------------|
| `collection` | `text` | Kitambulisho cha ukusanyaji/kuingiza data (kutoka kwa metadata) |
| `schema_name` | `text` | Jina la mpango ambao safu hii inafuata |
| `index_name` | `text` | Majina ya sehemu zilizopangiliwa, yameunganishwa kwa mkato kwa sehemu mbalimbali |
| `index_value` | `frozen<list<text>>` | Maadili ya kifunguo kama orodha |
| `data` | `map<text, text>` | Data ya safu kama jozi za ufunguo-thamani |
| `source` | `text` | URI ya hiari inayounganisha na maelezo ya asili katika mfumo wa maarifa. Mnyororo tupu au NULL inaonyesha kuwa hakuna chanzo. |

#### Usimamizi wa Faharasa

Kila safu huhifadhiwa mara nyingi - mara moja kwa kila sehemu iliyopangiliwa iliyobainishwa katika mpango. Sehemu kuu za ufunguo zinatibiwa kama faharasa bila alama maalum, ambayo hutoa uwezekano wa kubadilika katika siku zijazo.

**Mfano wa faharasa ya sehemu moja:**
Mpango unafafanua `email` kuwa iliyopangiliwa
`index_name = "email"`
`index_value = ['foo@bar.com']`

**Mfano wa faharasa mchanganyiko:**
Mpango unafafanua faharasa mchanganyiko kwenye `region` na `status`
`index_name = "region,status"` (majina ya sehemu yamepangwa na yameunganishwa kwa mkato)
`index_value = ['US', 'active']` (maadili katika utaratibu sawa na majina ya sehemu)

**Mfano wa ufunguo mkuu:**
Mpango unafafanua `customer_id` kuwa ufunguo mkuu
`index_name = "customer_id"`
`index_value = ['CUST001']`

#### Mfano wa Maswali

Maswali yote yanafuata muundo sawa bila kujali faharasa gani inayotumika:

```sql
SELECT * FROM rows
WHERE collection = 'import_2024'
  AND schema_name = 'customers'
  AND index_name = 'email'
  AND index_value = ['foo@bar.com']
```

#### Mizunguko ya Ubunifu

**Faida:**
Mabadiliko ya schema hayahitaji mabadiliko ya muundo wa jedwali
Data ya mstari ni ya siri kwa Cassandra - ongezeko/ondoano la nafasi ni wazi
Mfumo thabiti wa swali kwa njia zote za upatikanaji
Hakuna fahirisi za sekondari za Cassandra (ambazo zinaweza kuwa polepole kwa kiwango kikubwa)
Aina za asili za Cassandra katika kila sehemu (`map`, `frozen<list>`)

**Utofauti:**
Kuongezeka kwa uandishi: kila kuingizwa kwa mstari = ongezeko la N (moja kwa kila nafasi iliyofichwa)
Gharama ya kuhifadhi kutokana na data ya mstari iliyorudiwa
Habari ya aina huhifadhiwa katika usanidi wa schema, ubadilishaji katika safu ya programu

#### Mfumo wa Ulinganisho

Ubunifu huu unapokea uboreshaji fulani:

1. **Hakuna sasisho za mstari**: Mfumo huu ni wa kuongeza tu. Hii inazuia wasiwasi wa ulinganisho kuhusu kusasisha nakala nyingi za mstari mmoja.

2. **Uvumilivu wa mabadiliko ya schema**: Wakati schemas hubadilika (k.m., fahirisi zinaongezwa/kuondolewa), mistari iliyopo inaendelea kuwa na uwekaji wa fahirisi wake wa awali. Mistari ya zamani haitaweza kupatikana kupitia fahirisi mpya. Watumiaji wanaweza kufuta na kuunda tena schema ili kuhakikisha ulinganisho ikiwa ni lazima.

### Ufuatiliaji na Ufutilishaji wa Sehemu

#### Tatizo

Kwa ufunguo wa sehemu `(collection, schema_name, index_name)`, ufutaji bora unahitaji kujua ufunguo wote wa sehemu ili kufutwa. Ufutilishaji kwa `collection` au `collection + schema_name` pekee unahitaji kujua maadili yote ya `index_name` ambayo yana data.

#### Jedwali la Ufuatiliaji wa Sehemu

Jedwali la ziada la utafutaji linafuatilia sehemu zipi zilizo.

```sql
CREATE TABLE row_partitions (
    collection text,
    schema_name text,
    index_name text,
    PRIMARY KEY ((collection), schema_name, index_name)
)
```

Hii inaruhusu ugunduzi bora wa sehemu za kufutwa.

#### Tabia ya Kifaa cha Kuandika Mistari

Kifaa cha kuandika mistari kinahifadhi kumbukumbu ya jozi zilizosajiliwa za `(collection, schema_name)`. Wakati wa kuchakata mstari:

1. Angalia ikiwa `(collection, schema_name)` iko kwenye kumbukumbu
2. Ikiwa haijahifadhiwa (mstari wa kwanza kwa jozi hii):
   Tafuta usanidi wa schema ili kupata majina yote ya index
   Ingiza vipengele katika `row_partitions` kwa kila `(collection, schema_name, index_name)`
   Ongeza jozi kwenye kumbukumbu
3. Endelea na kuandika data ya mstari

Kifaa cha kuandika mistari pia kinachunguza mabadiliko ya usanidi wa schema. Wakati schema inabadilika, vipengele muhimu vya kumbukumbu vinafutwa ili mstari unaofuata usisababishwe tena usajili na majina mapya ya index.

Mbinu hii inahakikisha:
Uandikaji wa jedwali la utafutaji hutokea mara moja kwa kila jozi ya `(collection, schema_name)`, sio kwa kila mstari
Jedwali la utafutaji linaonyesha indexes ambazo zilikuwa zinafanya kazi wakati data ilipoandikwa
Mabadiliko ya schema wakati wa uingizaji yanaonekana kwa usahihi

#### Operesheni za Ufute

**Futa mkusanyiko:**
```sql
-- 1. Discover all partitions
SELECT schema_name, index_name FROM row_partitions WHERE collection = 'X';

-- 2. Delete each partition from rows table
DELETE FROM rows WHERE collection = 'X' AND schema_name = '...' AND index_name = '...';
-- (repeat for each discovered partition)

-- 3. Clean up the lookup table
DELETE FROM row_partitions WHERE collection = 'X';
```

**Futa mkusanyiko na schema:**
```sql
-- 1. Discover partitions for this schema
SELECT index_name FROM row_partitions WHERE collection = 'X' AND schema_name = 'Y';

-- 2. Delete each partition from rows table
DELETE FROM rows WHERE collection = 'X' AND schema_name = 'Y' AND index_name = '...';
-- (repeat for each discovered partition)

-- 3. Clean up the lookup table entries
DELETE FROM row_partitions WHERE collection = 'X' AND schema_name = 'Y';
```

### Uelekezaji wa Data

Uelekezaji wa data unawezesha utambuzi wa maana/ufanano kwenye maadili yaliyohifadhiwa, na kutatua tatizo la kutofautiana kwa lugha (k.m., kutafuta "CHESTNUT ST" wakati unatafuta "Chestnut Street").

#### Muhtasari wa Ubunifu

Kila jambo lililohifadhiwa limeelekezwa na kuhifadhiwa katika hifadhi ya vekta (Qdrant). Wakati wa utafutaji, swali linaelekezwa, vekta sawa zinafanywa, na metadata inayohusiana hutumiwa kutafuta mistari halisi katika Cassandra.

#### Muundo wa Mkusanyiko wa Qdrant

Mkusanyiko mmoja wa Qdrant kwa kila jozi ya `(user, collection, schema_name, dimension)`:

**Jina la mkusanyiko:** `rows_{user}_{collection}_{schema_name}_{dimension}`
Majina husafishwa (herufi ambazo sio alfabeti hubadilishwa na `_`, yamebadilishwa kuwa herufi ndogo, prefixes za namba hupata prefix ya `r_`)
**Sababu:** Inaruhusu kufutwa kwa jozi ya `(user, collection, schema_name)` kwa kufuta makusanyiko yanayolingana ya Qdrant; kiambishi cha kipimo huruhusu modeli tofauti za uelekezaji kuwepo.

#### Kile Kinachoelekezwa

Uwazi wa maandishi wa maadili ya index:

| Aina ya Index | Mfano wa `index_value` | Maandishi ya Kuelekeza |
|------------|----------------------|---------------|
| Uwanja mmoja | `['foo@bar.com']` | `"foo@bar.com"` |
| Mchanganyiko | `['US', 'active']` | `"US active"` (imeunganishwa na nafasi) |

#### Muundo wa Pointi

Kila pointi ya Qdrant ina:

```json
{
  "id": "<uuid>",
  "vector": [0.1, 0.2, ...],
  "payload": {
    "index_name": "street_name",
    "index_value": ["CHESTNUT ST"],
    "text": "CHESTNUT ST"
  }
}
```

| Uwanja wa Data | Maelezo |
|---------------|-------------|
| `index_name` | Uwanja(s) ulio(o) ambao embedding hii inawakilisha |
| `index_value` | Orodha ya awali ya maadili (kwa utafutaji wa Cassandra) |
| `text` | Nakala iliyoingizwa (kwa ajili ya utatuzi/kuonyesha) |

Kumbuka: `user`, `collection`, na `schema_name` zinaonyeshwa moja kwa moja kutoka kwa jina la mkusanyiko wa Qdrant.

#### Mtiririko wa Utafiti

1. Mtumiaji anatafuta "Chestnut Street" ndani ya mtumiaji U, mkusanyiko X, schema Y
2. Ingiza nakala ya utafutaji
3. Tambua jina(s) la mkusanyiko wa Qdrant linalolingana na kielelezo `rows_U_X_Y_`
4. Tafuta mkusanyiko(s) unaolingana wa Qdrant kwa vectori za karibu
5. Pata pointi zinazolingana zilizo na data zinazozingatia `index_name` na `index_value`
6. Tafuta Cassandra:
   ```sql
   SELECT * FROM rows
   WHERE collection = 'X'
     AND schema_name = 'Y'
     AND index_name = '<from payload>'
     AND index_value = <from payload>
   ```
7. Kurudisha mistari iliyolingana.

#### Hiari: Kuchuja kwa Jina la Index

Maswali yanaweza hiari kuchuja kwa `index_name` katika Qdrant ili kutafuta tu sehemu maalum:

**"Tafuta sehemu yoyote inayolingana na 'Chestnut'"** → tafuta vectori zote katika mkusanyiko.
**"Tafuta 'street_name' inayolingana na 'Chestnut'"** → chuja ambapo `payload.index_name = 'street_name'`.

#### Muundo

Uwekaji wa mistari unafuata **muundo wa hatua mbili** unaotumika na GraphRAG (uwekaji wa grafu, uwekaji wa hati):

**Hatua ya 1: Hesabu ya uwekaji** (`trustgraph-flow/trustgraph/embeddings/row_embeddings/`) - Hutumia `ExtractedObject`, huhesabu uwekaji kupitia huduma ya uwekaji, hutoka `RowEmbeddings`.
**Hatua ya 2: Uhifadhi wa uwekaji** (`trustgraph-flow/trustgraph/storage/row_embeddings/qdrant/`) - Hutumia `RowEmbeddings`, huandika vectori kwenye Qdrant.

Mwandishi wa mistari wa Cassandra ni mtumiaji wa ziada unaoendeshwa kwa njia fiche:

**Mwandishi wa mistari wa Cassandra** (`trustgraph-flow/trustgraph/storage/rows/cassandra`) - Hutumia `ExtractedObject`, huandika mistari kwenye Cassandra.

Huduma zote tatu hutumia kutoka kwa mtiririko mmoja, na hivyo kuzifanya kuwa huru. Hii inaruhusu:
Uongezaji wa kasi wa kujitegemea wa uandishi wa Cassandra dhidi ya utengenezaji wa uwekaji dhidi ya uhifadhi wa vectori.
Huduma za uwekaji zinaweza kuzimwa ikiwa hazihitajiki.
Hitilafu katika huduma moja hazisababishi athari kwa huduma zingine.
Muundo thabiti na mabomba ya GraphRAG.

#### Njia ya Kuandika

**Hatua ya 1 (mchakato wa uwekaji wa mistari):** Unapopokea `ExtractedObject`:

1. Tafuta schema ili kupata sehemu zilizoidishwa.
2. Kwa kila sehemu iliyoidishwa:
   Jenga uwakilishi wa maandishi wa thamani ya index.
   Hesabu uwekaji kupitia huduma ya uwekaji.
3. Toa ujumbe wa `RowEmbeddings` unao na vectori zote zilizohitajiwa.

**Hatua ya 2 (uandishi wa uwekaji wa mistari-qdrant):** Unapopokea `RowEmbeddings`:

1. Kwa kila uwekaji katika ujumbe:
   Tambua mkusanyiko wa Qdrant kutoka `(user, collection, schema_name, dimension)`.
   Unda mkusanyiko ikiwa unahitajika (utengenezaji wa polepole katika uandishi wa kwanza).
   Ongeza pointi na vector na mzigo.

#### Aina za Ujumbe

```python
@dataclass
class RowIndexEmbedding:
    index_name: str              # The indexed field name(s)
    index_value: list[str]       # The field value(s)
    text: str                    # Text that was embedded
    vectors: list[list[float]]   # Computed embedding vectors

@dataclass
class RowEmbeddings:
    metadata: Metadata
    schema_name: str
    embeddings: list[RowIndexEmbedding]
```

#### Jumuisho la Ufuteaji

Makusanyo ya Qdrant hugunduliwa kwa kutumia utangamano wa jina la makusanyo:

**Futa `(user, collection)`:**
1. Orodha makusanyo yote ya Qdrant yanayolingana na utangamano `rows_{user}_{collection}_`
2. Futa kila makusanyo yanayolingana
3. Futa sehemu za mistari ya Cassandra (kama ilivyoelezwa hapo juu)
4. Safisha maingizo ya `row_partitions`

**Futa `(user, collection, schema_name)`:**
1. Orodha makusanyo yote ya Qdrant yanayolingana na utangamano `rows_{user}_{collection}_{schema_name}_`
2. Futa kila makusanyo yanayolingana (inashughulikia vipimo vingi)
3. Futa sehemu za mistari ya Cassandra
4. Safisha `row_partitions`

#### Maeneo ya Moduli

| Hatua | Moduli | Kituo cha Kuanzia |
|-------|--------|-------------|
| Hatua 1 | `trustgraph-flow/trustgraph/embeddings/row_embeddings/` | `row-embeddings` |
| Hatua 2 | `trustgraph-flow/trustgraph/storage/row_embeddings/qdrant/` | `row-embeddings-write-qdrant` |

### API ya Uchunguzi wa Uelekezo

Uchunguzi wa uelekezo ni **API tofauti** kutoka kwa huduma ya uchunguzi wa mstari wa GraphQL:

| API | Madhumuni | Nyuma |
|-----|---------|---------|
| Uchunguzi wa Mstari (GraphQL) | Utangamano kamili kwenye sehemu zilizofichwa | Cassandra |
| Uchunguzi wa Uelekezo | Utangamano wa dhana/maneno | Qdrant |

Tofauti hii huweka masuala tofauti:
Huduma ya GraphQL inazingatia maswali kamili na yaliyo na muundo
API ya uelekezo inashughulikia ufanano wa dhana
Mchakato wa mtumiaji: utafutaji wa dhana kupitia uelekezo ili kupata wagombea, kisha uchunguzi kamili ili kupata data kamili ya mstari

#### Mfumo wa Ombi/Jibu

```python
@dataclass
class RowEmbeddingsRequest:
    vectors: list[list[float]]    # Query vectors (pre-computed embeddings)
    user: str = ""
    collection: str = ""
    schema_name: str = ""
    index_name: str = ""          # Optional: filter to specific index
    limit: int = 10               # Max results per vector

@dataclass
class RowIndexMatch:
    index_name: str = ""          # The matched index field(s)
    index_value: list[str] = []   # The matched value(s)
    text: str = ""                # Original text that was embedded
    score: float = 0.0            # Similarity score

@dataclass
class RowEmbeddingsResponse:
    error: Error | None = None
    matches: list[RowIndexMatch] = []
```

#### Mchakato wa Uchunguzi

Moduli: `trustgraph-flow/trustgraph/query/row_embeddings/qdrant`

Kuanzia: `row-embeddings-query-qdrant`

Mchakato:
1. Hupokea `RowEmbeddingsRequest` pamoja na vektor za swali
2. Hutafuta mkusanyiko unaofaa wa Qdrant kwa kutumia utangamano wa nenosiri
3. Hutafuta vektor za karibu pamoja na kipengele cha `index_name` cha hiari
4. Hurudisha `RowEmbeddingsResponse` pamoja na maelezo ya fahirisi yanayolingana

#### Uunganisho wa Milango ya API

Lango huonyesha maswali ya uelekezo wa mstari kupitia muundo wa kawaida wa ombi/jibu:

| Sehemu | Mahali |
|-----------|----------|
| Msambazaji | `trustgraph-flow/trustgraph/gateway/dispatch/row_embeddings_query.py` |
| Usajili | Ongeza `"row-embeddings"` kwenye `request_response_dispatchers` katika `manager.py` |

Jina la kiungo cha mtiririko: `row-embeddings`

Ufafanuzi wa kiungo katika mpango wa mtiririko:
```json
{
  "interfaces": {
    "row-embeddings": {
      "request": "non-persistent://tg/request/row-embeddings:{id}",
      "response": "non-persistent://tg/response/row-embeddings:{id}"
    }
  }
}
```

#### Usaidizi wa SDK ya Python

SDK hutoa njia za kuuliza kuhusu uwekaji wa data katika mistari:

```python
# Flow-scoped query (preferred)
api = Api(url)
flow = api.flow().id("default")

# Query with text (SDK computes embeddings)
matches = flow.row_embeddings_query(
    text="Chestnut Street",
    collection="my_collection",
    schema_name="addresses",
    index_name="street_name",  # Optional filter
    limit=10
)

# Query with pre-computed vectors
matches = flow.row_embeddings_query(
    vectors=[[0.1, 0.2, ...]],
    collection="my_collection",
    schema_name="addresses"
)

# Each match contains:
for match in matches:
    print(match.index_name)   # e.g., "street_name"
    print(match.index_value)  # e.g., ["CHESTNUT ST"]
    print(match.text)         # e.g., "CHESTNUT ST"
    print(match.score)        # e.g., 0.95
```

#### Utumizi wa Kamba ya Amri

Amri: `tg-invoke-row-embeddings`

```bash
# Query by text (computes embedding automatically)
tg-invoke-row-embeddings \
  --text "Chestnut Street" \
  --collection my_collection \
  --schema addresses \
  --index street_name \
  --limit 10

# Query by vector file
tg-invoke-row-embeddings \
  --vectors vectors.json \
  --collection my_collection \
  --schema addresses

# Output formats
tg-invoke-row-embeddings --text "..." --format json
tg-invoke-row-embeddings --text "..." --format table
```

#### Mfano wa Matumizi ya Kawaida

Uchunguzi wa pembejeo za mstari kwa kawaida hutumika kama sehemu ya mtiririko wa utafutaji wa "vunjifu" hadi "sahihi":

```python
# Step 1: Fuzzy search via embeddings
matches = flow.row_embeddings_query(
    text="chestnut street",
    collection="geo",
    schema_name="streets"
)

# Step 2: Exact lookup via GraphQL for full row data
for match in matches:
    query = f'''
    query {{
        streets(where: {{ {match.index_name}: {{ eq: "{match.index_value[0]}" }} }}) {{
            street_name
            city
            zip_code
        }}
    }}
    '''
    rows = flow.rows_query(query, collection="geo")
```

Mfumo huu wa hatua mbili huruhusu:
Kugundua "CHESTNUT ST" wakati mtumiaji anatafuta "Chestnut Street"
Kuchukua data kamili ya mstari pamoja na sehemu zote
Kuchanganya utambulisho wa maana na ufikiaji wa data iliyopangwa

### Uingizaji wa Data ya Mstari

Itarefushwa hadi hatua ya baadaye. Itaundwa pamoja na mabadiliko mengine ya uingizaji.

## Athari ya Utendaji

### Uchambuzi wa Hali ya Sasa

Utendaji uliopo una vipengele viwili mikuu:

| Kipengele | Mahali | Mistari | Maelezo |
|-----------|----------|-------|-------------|
| Huduma ya Utafutaji | `trustgraph-flow/trustgraph/query/objects/cassandra/service.py` | ~740 | Moja kwa moja: Uundaji wa schema ya GraphQL, uchanganuzi wa vichujio, maswali ya Cassandra, usimamizi wa ombi |
| Mwandishi | `trustgraph-flow/trustgraph/storage/objects/cassandra/write.py` | ~540 | Uundaji wa jedwali kwa kila schema, fahirisi za sekondari, kuingiza/kufuta |

**Mfumo wa Sasa wa Utafutaji:**
```sql
SELECT * FROM {keyspace}.o_{schema_name}
WHERE collection = 'X' AND email = 'foo@bar.com'
ALLOW FILTERING
```

**Muundo Mpya wa Ulizaji:**
```sql
SELECT * FROM {keyspace}.rows
WHERE collection = 'X' AND schema_name = 'customers'
  AND index_name = 'email' AND index_value = ['foo@bar.com']
```

### Mabadiliko Muhimu

1. **Uboreshaji wa maana ya maswali**: Mfumo mpya unaunga mkono tu mechi kamili kwenye `index_value`. Vifiltrishi vya GraphQL ya sasa (`gt`, `lt`, `contains`, n.k.) ama:
   Yanakuwa uchujaji wa ziada kwenye data iliyorudishwa (ikiwa bado inahitajika)
   Yanondolewa ili kutumia API ya embeddings kwa mechi zisizo sahihi

2. **Msimbo wa GraphQL umeunganishwa sana**: Mfumo wa sasa wa `service.py` unajumuisha utengenezaji wa aina za Strawberry, uchanganuzi wa vifiltrishi, na maswali maalum ya Cassandra. Kuongeza mfumo mwingine wa kuhifadhi data ingeongeza mistari ~400 ya msimbo wa GraphQL.

### Pendekezo la Urekebishaji

Urekebishaji una sehemu mbili:

#### 1. Tenganisha Msimbo wa GraphQL

Toa vipengele vya GraphQL ambavyo vinaweza kutumika tena katika moduli iliyoshirikiwa:

```
trustgraph-flow/trustgraph/query/graphql/
├── __init__.py
├── types.py        # Filter types (IntFilter, StringFilter, FloatFilter)
├── schema.py       # Dynamic schema generation from RowSchema
└── filters.py      # Filter parsing utilities
```

Hii inawezesha:
Matumizi upya katika mifumo tofauti ya kuhifadhi data.
Tofauti wazi zaidi ya majukumu.
Uchunguzi rahisi zaidi wa mantiki ya GraphQL kwa kujitegemea.

#### 2. Tengeneza Mpango Mpya wa Jedwali

Badilisha msimbo maalum wa Cassandra ili kutumia jedwali lililo na mpango mmoja:

**Mwandishi** (`trustgraph-flow/trustgraph/storage/rows/cassandra/`):
Jedwali moja la `rows` badala ya jedwali kila mpango.
Andika nakala N kwa kila mstari (moja kwa kila fahirisi).
Jisajili kwenye jedwali la `row_partitions`.
Uundaji rahisi zaidi wa jedwali (usanidi wa mara moja).

**Huduma ya Utafiti** (`trustgraph-flow/trustgraph/query/rows/cassandra/`):
Tafuta kwenye jedwali lililo na mpango mmoja la `rows`.
Tumia moduli iliyochimbwa ya GraphQL kwa uundaji wa mpango.
Usimamizi ulioboreshwa wa vichujio (mechi kamili tu kwenye kiwango cha hifadhidata).

### Mabadiliko ya Majina ya Moduli

Kama sehemu ya usafi wa majina kutoka "object" hadi "row":

| Sasa | Mpya |
|---------|-----|
| `storage/objects/cassandra/` | `storage/rows/cassandra/` |
| `query/objects/cassandra/` | `query/rows/cassandra/` |
| `embeddings/object_embeddings/` | `embeddings/row_embeddings/` |

### Moduli Mpya

| Moduli | Lengo |
|--------|---------|
| `trustgraph-flow/trustgraph/query/graphql/` | Utumizi wa pamoja wa GraphQL. |
| `trustgraph-flow/trustgraph/query/row_embeddings/qdrant/` | API ya utafiti wa uingishaji wa mstari. |
| `trustgraph-flow/trustgraph/embeddings/row_embeddings/` | Hesabu ya uingishaji wa mstari (Hatua ya 1). |
| `trustgraph-flow/trustgraph/storage/row_embeddings/qdrant/` | Uhifadhi wa uingishaji wa mstari (Hatua ya 2). |

## Marejeleo

[Maelezo ya Kiufundi ya Data Iliyopangwa](structured-data.md)
