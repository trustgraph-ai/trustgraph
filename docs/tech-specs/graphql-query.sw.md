# Vipimo vya Kiufundi vya Umasilisho wa GraphQL

## Muhtasari

Maelekezo haya yanaelezea utekelezaji wa kiolesura cha uwasilisho wa GraphQL kwa kuhifadhi data iliyopangwa ya TrustGraph katika Apache Cassandra. Kujenga juu ya uwezo wa data iliyopangwa uliyoainishwa katika maelekezo ya structured-data.md, hati hii inaeleza jinsi maswali ya GraphQL yanavyotekelezwa dhidi ya meza za Cassandra zinazokuza vitu vilivyochukuliwa na vilivyomingwa.

Huduma ya uwasilisho wa GraphQL itatoa kiolesura kinachobadilika na kinacholingana na aina kwa kuuliza data iliyopangwa iliyohifadhiwa katika Cassandra. Itabadilika moja kwa moja kwa mabadiliko ya mpango, inasaidia maswali tata ikiwa ni pamoja na uhusiano kati ya vitu, na itounganisha kikamilifu na usanifu uliopo wa TrustGraph unaotegemea ujumbe.

## Lengo

**Usaidizi wa Mpango Unaobadilika**: Kujifunga kiotomatiki kwa mabadiliko ya mpango bila kuacha huduma
**Uzingatiaji wa Viwango vya GraphQL**: Kutoa kiolesura cha kawaida cha GraphQL kinacholingana na zana na wateja wa GraphQL iliyopo
**Maswali ya Ufanisi ya Cassandra**: Kubadilisha maswali ya GraphQL kuwa maswali ya ufanisi ya Cassandra CQL kwa kuheshimu funguo za sehemu na fahirisi
**Suluhisho la Uhusiano**: Kusaidia suluhu za GraphQL kwa uhusiano kati ya aina tofauti za vitu
**Usalama wa Aina**: Kuhakikisha utekelezaji wa aina-salama wa maswali na utengenezaji wa majibu kulingana na maelezo ya mpango
**Utendaji Unaoweza Kukidhi Mahitaji**: Kushughulikia maswali mengi kwa ufanisi kwa kutumia udhibiti wa muunganisho na uboreshaji wa maswali
**Ujumuishaji wa Ombi/Jibu**: Kuhifadhi utangamano na mtindo wa ombi/jibu wa TrustGraph unaotegemea Pulsar
**Usimamizi wa Makosa**: Kutoa ripoti kamili ya makosa kwa kutofautiana kwa mpango, makosa ya maswali, na masuala ya uthibitisho wa data

## Asili

Utekelezaji wa uhifadhi wa data iliyopangwa (trustgraph-flow/trustgraph/storage/objects/cassandra/) huandika vitu kwenye meza za Cassandra kulingana na maelezo ya mpango yaliyohifadhiwa katika mfumo wa usanidi wa TrustGraph. Meza hizi hutumia muundo wa funguo ya sehemu iliyounganishwa na funguo za msingi zilizobainishwa na mpango, na kuwezesha maswali ya ufanisi ndani ya makusanyo.

Marekebisho ya sasa ambayo maelekezo haya yanaashiria:
Hakuna kiolesura cha kuuliza kwa data iliyopangwa iliyohifadhiwa katika Cassandra
Uwasilishaji usio wa uwezo wa uwezo wa maswali ya GraphQL kwa data iliyopangwa
Usaidizi usio na uhusiano kati ya vitu vinavyohusiana
Ukosefu wa lugha ya kawaida ya kuuliza kwa upataji wa data iliyopangwa

Huduma ya uwasilisho wa GraphQL itafunga pengo hizi kwa:
Kutoa kiolesura cha kawaida cha GraphQL kwa kuuliza meza za Cassandra
Kujenga schemas za GraphQL kwa moja kwa moja kutoka usanidi wa TrustGraph
Kubadilisha maswali ya GraphQL kwa ufanisi kwa CQL ya Cassandra
Kusaidia suluhisho la uhusiano kupitia suluhu za uwanja

## Ubunifu wa Kiufundi

### Usanifu

Huduma ya uwasilisho wa GraphQL itatekelezwa kama mchakato mpya wa TrustGraph kufuatia mbinu zilizopo:

**Eneo la Moduli**: `trustgraph-flow/trustgraph/query/objects/cassandra/`

**Vipengele Muhimu**:

1. **Mchakato wa Huduma ya Uwasilisho wa GraphQL**
   Huendelea na darasa la msingi la FlowProcessor
   Inatekeleza mtindo wa ombi/jibu sawa na huduma zingine za kuuliza
   Inafuatilia usanidi kwa sasisho za mpango
   Inahifadhi mpango wa GraphQL inayosawazishwa na usanidi

2. **Mjenzi wa Mpango wa Njia Moja Moja**
   Inabadilisha maelezo ya TrustGraph RowSchema kuwa aina za GraphQL
   Inaunda aina za vitu vya GraphQL na maelezo ya uwanja sahihi
   Inazalisha aina ya mizizi ya Ombi na suluhu za msingi za makusanyo
   Inasasisha mpango wa GraphQL wakati usanidi unabadilika

3. **Mtekelezaji wa Maswali**
   Inachambua maswali ya GraphQL yanayoingia kwa kutumia maktaba ya Strawberry
   Inathibitisha maswali dhidi ya mpango wa sasa
   Inatekeleza maswali na inarudisha majibu yaliyopangwa
   Inashughulikia makosa kwa utulivu na ujumbe wa makosa wa kina

4. **Mhubiri wa Maswali ya Cassandra**
   Inabadilisha uteuzi wa GraphQL kuwa maswali ya CQL
   Inaboresha maswali kulingana na fahirisi na funguo za sehemu zinazopatikana
   Inashughulikia kuchujwa, upangishaji, na utaratibu
   Inadhibiti udhibiti wa muunganisho na maisha ya kikao

5. **Suluhu ya Uhusiano**
   Inatekeleza suluhu za uwanja kwa uhusiano wa vitu
   Inafanya upakiaji wa kundi ili kuepuka maswali ya N+1
   Inahifadhi suluhu za uhusiano ndani ya muktadha wa ombi
   Inasaidia utambuzi wa uhusiano wa mbele na nyuma

### Ufuatiliaji wa Mpango wa Usanidi

Huduma itasajili mshukiwa wa usanidi ili kupokea sasisho za mpango:

```python
self.register_config_handler(self.on_schema_config)
```

Wakati schemas hubadilika:
1. Changanua maelezo mapya ya schema kutoka kwa usanidi
2. Tengeneza upya aina za GraphQL na suluhu
3. Sasisha schema inayotumika
4. Ondoa kumbukumbu zozote zinazotegemea schema

### Uzalishaji wa Schema ya GraphQL

Kwa kila RowSchema katika usanidi, tengeneza:

1. **Aina ya Kitu cha GraphQL**:
   Linganisha aina za sehemu (string → String, integer → Int, float → Float, boolean → Boolean)
   Weka sehemu ambazo zinahitajika kama zisizo na thamani null katika GraphQL
   Ongeza maelezo ya sehemu kutoka kwa schema

2. **Sehemu za Uchunguzi Mkuu**:
   Uchunguzi wa mkusanyiko (e.g., `customers`, `transactions`)
   Vigezo vya kuchujwa kulingana na sehemu zilizo na fahirisi
   Usaidizi wa ukurasa (limit, offset)
   Chaguo za kupanga kwa sehemu ambazo zinaweza kupangwa

3. **Sehemu za Uhusiano**:
   Tambua uhusiano wa ufunguo wa kigeni kutoka kwa schema
   Unda suluhu za sehemu kwa vitu vinavyohusiana
   Usaidizi wa uhusiano wa kitu kimoja na orodha

### Mtiririko wa Utendaji wa Uchunguzi

1. **Mapokezi ya Ombi**:
   Pokea `ObjectsQueryRequest` kutoka Pulsar.
   Toa mfuatano wa GraphQL na vigezo.
   Tambua muktadha wa mtumiaji na mkusanyiko.

2. **Uthibitisho wa Ombi**:
   Changanua mfuatano wa GraphQL kwa kutumia Strawberry.
   Thibitisha dhidi ya mpango (schema) unaoendelea.
   Angalia uteuzi wa sehemu na aina za hoja (argument).

3. **Uundaji wa Ombi la CQL**:
   Jadili uteuzi wa GraphQL.
   Unda ombi la CQL na vipengele sahihi vya `WHERE`.
   Jumuisha mkusanyiko katika ufunguo wa sehemu (partition key).
   Tumia vichujio kulingana na hoja za GraphQL.

4. **Utendaji wa Ombi**:
   Tekeleza ombi la CQL dhidi ya Cassandra.
   Linganisha matokeo na muundo wa jibu la GraphQL.
   Tatua sehemu zozote za uhusiano.
   Tengeneza jibu kulingana na vipimo vya GraphQL.

5. **Utoaji wa Jibu**:
   Unda `ObjectsQueryResponse` na matokeo.
   Jumuisha makosa yoyote ya utekelezaji.
   Tuma jibu kupitia Pulsar na kitambulisho cha uhusiano (correlation ID).

### Mifano ya Data

> **Kumbuka**: Mpango (schema) uliopo wa `StructuredQueryRequest/Response` unafanya kazi katika `trustgraph-base/trustgraph/schema/services/structured_query.py`. Hata hivyo, hauna vipengele muhimu (mtumiaji, mkusanyiko) na hutumia aina ambazo sio bora. Mifano iliyo hapa chini inaonyesha maendeleo yanayopendekezwa, ambayo inaweza kuchukua nafasi ya mifano iliyopo au kuundwa kama aina mpya za `ObjectsQueryRequest/Response`.

#### Mpango wa Ombi (ObjectsQueryRequest)

```python
from pulsar.schema import Record, String, Map, Array

class ObjectsQueryRequest(Record):
    user = String()              # Cassandra keyspace (follows pattern from TriplesQueryRequest)
    collection = String()        # Data collection identifier (required for partition key)
    query = String()             # GraphQL query string
    variables = Map(String())    # GraphQL variables (consider enhancing to support all JSON types)
    operation_name = String()    # Operation to execute for multi-operation documents
```

**Mazingatio ya mabadiliko kutoka kwa Ombi la Ulinganisho Lililopo:**
Imeongezwa sehemu `user` na `collection` ili kuendana na mtindo wa huduma zingine za utafutaji.
Sehemu hizi ni muhimu kwa kutambua eneo la kuhifadhi data (keyspace) na mkusanyiko (collection) katika Cassandra.
Vigezo vinaendelea kuwa Map(String()) kwa sasa, lakini inapaswa kusaidia aina zote za JSON.

#### Muundo wa Majibu (ObjectsQueryResponse)

```python
from pulsar.schema import Record, String, Array
from ..core.primitives import Error

class GraphQLError(Record):
    message = String()
    path = Array(String())       # Path to the field that caused the error
    extensions = Map(String())   # Additional error metadata

class ObjectsQueryResponse(Record):
    error = Error()              # System-level error (connection, timeout, etc.)
    data = String()              # JSON-encoded GraphQL response data
    errors = Array(GraphQLError) # GraphQL field-level errors
    extensions = Map(String())   # Query metadata (execution time, etc.)
```

**Mazingatio ya mabadiliko kutoka kwa Jibu la Uliopo la StructuredQueryResponse:**
Hutofautisha kati ya makosa ya mfumo (`error`) na makosa ya GraphQL (`errors`)
Hutumia vitu vilivyopangwa vya GraphQLError badala ya safu ya maandishi
Huongeza sehemu `extensions` ili kufuata vipimo vya GraphQL
Huhifadhi data kama mnyororo wa JSON ili kuendana, ingawa aina asilia zingekuwa bora

### Uboreshaji wa Umasilisho wa Cassandra

Huduma itaboresha masilisho ya Cassandra kwa:

1. **Kufuata Vipengele vya Partition:**
   Daima jumuisha mkusanyiko katika masilisho
   Tumia funguo kuu zilizotolewa na mpango kwa ufanisi
   Epuka uchanganuzi kamili wa jedwali

2. **Kutumia Faharasa:**
   Tumia faharasa za sekondari kwa kuchujwa
   Unganisha vichujio vingi wakati inafaa
   Toa onyo wakati masilisho yanaweza kuwa yasiyo na ufanisi

3. **Upakiaji wa Kundi:**
   Kusanya masilisho ya uhusiano
   Tekeleza kwa makundi ili kupunguza safari za kurudi na kuja
   Hifadhi matokeo ndani ya muktadha wa ombi

4. **Usimamizi wa Muunganisho:**
   Dumishe vipindi vya Cassandra vinavyoendelea
   Tumia mabwalo ya muunganisho
   Shughulikia muunganisho upya katika hali ya kushindwa

### Mifano ya Masilisho ya GraphQL

#### Masilisho ya Mkusaniko Rahisi
```graphql
{
  customers(status: "active") {
    customer_id
    name
    email
    registration_date
  }
}
```

#### Swali na Mahusiano
```graphql
{
  orders(order_date_gt: "2024-01-01") {
    order_id
    total_amount
    customer {
      name
      email
    }
    items {
      product_name
      quantity
      price
    }
  }
}
```

#### Swali lililogawanywa katika kurasa.
```graphql
{
  products(limit: 20, offset: 40) {
    product_id
    name
    price
    category
  }
}
```

### Utendaji (Implementation)

**Strawberry GraphQL**: Kwa uainishaji wa schema ya GraphQL na utekelezaji wa swali.
**Cassandra Driver**: Kwa muunganisho wa hifadhidata (tayari inatumika katika moduli ya uhifadhi).
**TrustGraph Base**: Kwa FlowProcessor na uainishaji wa schema.
**Mfumo wa Usanidi**: Kwa ufuatiliaji na sasisho za schema.

### Kiolesura cha Amri (Command-Line Interface)

Huduma itatoa amri ya CLI: `kg-query-objects-graphql-cassandra`

Majadilisho:
`--cassandra-host`: Alama ya kuwasiliana na kundi la Cassandra.
`--cassandra-username`: Jina la mtumiaji la uthibitishaji.
`--cassandra-password`: Nenosiri la uthibitishaji.
`--config-type`: Aina ya usanidi kwa schema (ya kawaida: "schema").
Majadilisho ya kawaida ya FlowProcessor (usanidi wa Pulsar, n.k.).

## Uunganisho wa API

### Mada za Pulsar

**Mada ya Ingizo**: `objects-graphql-query-request`
Schema: ObjectsQueryRequest
Inapokea maswali ya GraphQL kutoka kwa huduma za lango.

**Mada ya Toa**: `objects-graphql-query-response`
Schema: ObjectsQueryResponse
Inarudisha matokeo ya swali na makosa.

### Uunganisho wa Lango

Lango na lango la kinyume (reverse-gateway) itahitaji sehemu za:
1. Kukubali maswali ya GraphQL kutoka kwa wateja.
2. Kusambaza kwa huduma ya swali kupitia Pulsar.
3. Kurudisha majibu kwa wateja.
4. Kusaidia maswali ya utafiti wa GraphQL.

### Uunganisho wa Zana ya Wakala

Darasa mpya la zana ya wakala itaruhusu:
Uundaji wa swali la GraphQL kutoka kwa lugha ya asili.
Utendaji wa moja kwa moja wa swali la GraphQL.
Tafsiri na umbizo wa matokeo.
Uunganisho na mtiririko wa maamuzi wa wakala.

## Masuala ya Usalama

**Kipengele cha Kuzuia Kina cha Swali**: Kuzuia maswali yenye kina kikubwa ambacho kinaweza kusababisha matatizo ya utendaji.
**Uchambuzi wa Ufumbuzi wa Swali**: Kupunguza ufumbuzi wa swali ili kuzuia matumizi yasiyofaa ya rasilimali.
**Ruhusa za Kawaida**: Usaidizi wa baadaye kwa udhibiti wa ufikiaji wa kawaida kulingana na majukumu ya mtumiaji.
**Usanifu wa Ingizo**: Kuhakikisha na kusafisha pembejeo zote za swali ili kuzuia mashambulizi ya kuingiza.
**Kipengele cha Kupunguza Kasi**: Kuweka kikomo cha kasi ya swali kwa kila mtumiaji/mkusanyiko.

## Masuala ya Utendaji

**Upangaji wa Swali**: Kuchambua maswali kabla ya utekelezaji ili kuongeza ufanisi wa uundaji wa CQL.
**Kuhifadhi Matokeo**: Kuzingatia kuhifadhi data inayopatikana mara kwa mara katika kiwango cha kielekezi cha matokeo.
**Usimamizi wa Muunganisho**: Kudumisha mizingi bora ya muunganisho kwa Cassandra.
**Operesheni za Kikundi**: Kuchanganya maswali mengi wakati inafaa ili kupunguza latensi.
**Ufuatiliaji**: Kufuatilia vipimo vya utendaji wa swali kwa ajili ya uboreshaji.

## Mkakati wa Majaribio

### Majaribio ya Vitengo
Uzalishaji wa schema kutoka kwenye maelezo ya RowSchema
Uchunguzi na uthibitisho wa swali la GraphQL
Mantiki ya uzalishaji wa swali la CQL
Utendaji wa suluhu za sehemu

### Majaribio ya Mkataba
Uzingatiaji wa mkataba wa ujumbe wa Pulsar
Uthibitisho wa uhalali wa schema ya GraphQL
Uthibitisho wa muundo wa jibu
Uthibitisho wa muundo wa hitilafu

### Majaribio ya Uunganishaji
Utendaji wa swali kamili dhidi ya mfano wa Cassandra wa majaribio
Usimamizi wa sasisho za schema
Suluhisho la uhusiano
Urekebishaji na utafutaji
Hali za hitilafu

### Majaribio ya Utendaji
Ufanisi wa swali chini ya mzigo
Muda wa jibu kwa utata wa swali mbalimbali
Matumizi ya kumbukumbu na matokeo makubwa
Ufanisi wa kikundi cha muunganisho

## Mpango wa Uhamishaji

Uhamishaji hauhitajiki kwani hii ni uwezo mpya. Huduma itafanya:
1. Kusoma schema zilizopo kutoka kwenye usanidi
2. Kuunganisha na meza zilizopo za Cassandra zilizoundwa na moduli ya uhifadhi
3. Kuanza kukubali maswali mara tu inaposanikishwa

## Muda

Wiki 1-2: Utendaji wa msingi wa huduma na uzalishaji wa schema
Wiki 3: Utendaji wa swali na tafsiri ya CQL
Wiki 4: Suluhisho la uhusiano na uboreshaji
Wiki 5: Majaribio na uboreshaji wa utendaji
Wiki 6: Uunganisho wa lango na maandishi

## Maswali ya Wazi

1. **Maendeleo ya Schema**: Huduma inapaswa kushughulikia maswali vipi wakati wa mabadiliko ya schema?
   Chaguo: Kuweka maswali kwenye folyo wakati wa sasisho za schema
   Chaguo: Kusaidia matoleo mengi ya schema kwa wakati mmoja

2. **Mkakati wa Uhifadhi**: Je, matokeo ya swali yanapaswa kuhifadhiwa?
   Zingatia: Muda wa kumalizika
   Zingatia: Ubatilishaji kulingana na tukio

3. **Usaidizi wa Shirikisho**: Je, huduma inapaswa kusaidia shirikisho la GraphQL ili kuunganisha na vyanzo vingine vya data?
   Itaruhusu maswali ya umoja katika data iliyopangwa na ya grafu

4. **Usaidizi wa Ujiandikishaji**: Je, huduma inapaswa kusaidia uandikishaji wa GraphQL kwa sasisho za wakati halisi?
   Itahitaji usaidizi wa WebSocket katika lango

5. **Scalar Maalum**: Je, aina za scalar maalum zinapaswa kuungwa mkono kwa aina za data maalum za kikoa?
   Mifano: DateTime, UUID, nafasi za JSON

## Marejeleo

Maelezo ya Kimataifa ya Data Iliyopangwa: `docs/tech-specs/structured-data.md`
Nyaraka za Strawberry GraphQL: https://strawberry.rocks/
Maelezo ya GraphQL: https://spec.graphql.org/
Marejeleo ya Apache Cassandra CQL: https://cassandra.apache.org/doc/stable/cassandra/cql/
Nyaraka za Msimamizi wa Mtiririko wa TrustGraph: Nyaraka za ndani