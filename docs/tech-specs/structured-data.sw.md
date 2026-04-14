---
layout: default
title: "Vipimo vya Teknisia vya Data Iliyoainishwa"
parent: "Swahili (Beta)"
---

# Vipimo vya Teknisia vya Data Iliyoainishwa

> **Beta Translation:** This document was translated via Machine Learning and as such may not be 100% accurate. All non-English languages are currently classified as Beta.

## Muhtasari

Maelekezo haya yanaelezea jinsi TrustGraph inavyounganishwa na mtiririko wa data iliyoainishwa, na kuwezesha mfumo kufanya kazi na data ambayo inaweza kuwakilishwa kama mistari katika meza au vitu katika maduka ya vitu. Uunganisho huu unaunga mkono matumizi manne makuu:

1. **Utoaji kutoka kwa Data Isiyoainishwa hadi Imeinishwa**: Soma vyanzo vya data visivyoainishwa, tambua na uondoe muundo wa vitu, na uihifadhi katika umbizo wa meza.
2. **Uingizaji wa Data Imeinishwa**: Pakia data ambayo tayari iko katika umbizo iliyoainishwa moja kwa moja katika duka la data iliyoainishwa pamoja na data iliyoondolewa.
3. **Uulizaje kwa Lugha Asilia**: Badilisha maswali ya lugha asilia katika maswali iliyoainishwa ili kuchuja data inayolingana kutoka kwa duka.
4. **Uulizaje wa Moja kwa Moja wa Imeinishwa**: Fanya maswali iliyoainishwa moja kwa moja dhidi ya duka la data ili kupata data kwa usahihi.

## Lengo

**Ufikiaji Umoja wa Data**: Toa kiungo kimoja cha kufikia data zote, iliyoainishwa na isiyoainishwa, ndani ya TrustGraph.
**Uunganisho Kamili**: Uwezesha utendaji wa pamoja kati ya uwakilishi wa maarifa wa TrustGraph unaotegemea chati na umbizo wa jadi wa data iliyoainishwa.
**Utoaji Wenye Ugumu**: Unga uondoleaji wa moja kwa moja wa data iliyoainishwa kutoka kwa vyanzo mbalimbali visivyoainishwa (nyaraka, maandishi, n.k.).
**Uwezekano wa Uulizaje**: Ruhusu watumiaji kuuliza data kwa kutumia lugha ya asilia na lugha za uulizaje iliyoainishwa.
**Ulinganifu wa Data**: Dumishe uadilifu na ulinganifu wa data katika uwakilishi tofauti wa data.
**Uboreshaji wa Utendaji**: Hakikisha uhifadhi na upekuzi wa ufanisi wa data iliyoainishwa kwa kiwango kikubwa.
**Uwezekano wa Mfumo**: Unga mifumo ya "andika-mfumo" na "soma-mfumo" ili kukidhi vyanzo tofauti vya data.
**Ulinganifu na Mifumo ya Zamani**: Dumishe utendaji wa sasa wa TrustGraph huku uongezwa uwezekano wa data iliyoainishwa.

## Asili

Hivi sasa, TrustGraph inafaa katika kuchakata data isiyoainishwa na kuunda chati za maarifa kutoka kwa vyanzo tofauti. Hata hivyo, matumizi mengi ya kampuni yanahusisha data ambayo ina muundo - rekodi za wateja, magogo ya miamala, hifadhi za bidhaa, na mengineyo ya seti za data za meza. Data hii iliyoainishwa mara nyingi inahitaji kuchanganuliwa pamoja na maudhui isiyoainishwa ili kutoa ufahamu kamili.

Mapungufu ya sasa ni pamoja na:
Hakuna msaada wa asili kwa kuingiza umbizo la awali la data (CSV, safu za JSON, mauzo ya hifadhi ya data).
Uwezekano wa kutohifadhi muundo halisi wakati wa kuondoa data ya meza kutoka kwa nyaraka.
Ukosefu wa mitambo ya uulizaje ya ufanisi kwa muundo wa data iliyoainishwa.
Upungufu wa daraja kati ya maswali kama ya SQL na maswali ya chati ya TrustGraph.

Maelekezo haya yanaashiria pengo hizi kwa kuleta safu ya data iliyoainishwa ambayo inakamilisha uwezekano wa sasa wa TrustGraph. Kwa kusaidia data iliyoainishwa kwa asili, TrustGraph inaweza:
Kutoa jukwaa la umoja kwa uchanganuzi wa data iliyoainishwa na isiyoainishwa.
Kuwezesha maswali ya mchanganyiko ambayo yanaenea katika uhusiano wa chati na data ya meza.
Kutoa kiungo cha kawaida kwa watumiaji ambao wamezoea kufanya kazi na data iliyoainishwa.
Kufungua matumizi mapya katika ujumuishaji wa data na ujasusi wa biashara.

## Muundo wa Kiufundi

### Usanifu

Uunganisho wa data iliyoainishwa unahitaji vipengele vifuatavyo vya kiufundi:

1. **Huduma ya NLP-kwa-Uulizaje-Imeinishwa**
   Inabadilisha maswali ya lugha asilia katika maswali iliyoainishwa.
   Inasaidia malengo mengi ya lugha ya uulizaje (hasa, usanifu kama wa SQL).
   Inaunganishwa na uwezekano wa sasa wa NLP ya TrustGraph.
   
   Moduli: trustgraph-flow/trustgraph/query/nlp_query/cassandra

2. **Usaidizi wa Mfumo wa Mpangilio** ✅ **[IMEKAMILIKA]**
   Mfumo ulioongezwa wa mpangilio ili kuhifadhi umbizo wa data iliyoainishwa.
   Usaidizi wa kufafanua muundo wa meza, aina za sehemu, na uhusiano.
   Utoleaji wa toleo na uwezekano wa uhamishaji wa mfumo.

3. **Moduli ya Utoaji wa Vitu** ✅ **[IMEKAMILIKA]**
   Uunganisho uliorekebishwa wa mtiririko wa uondoleaji wa maarifa.
   Inatambua na kuondoa vitu vilivyoainishwa kutoka kwa vyanzo visivyoainishwa.
   Inahifadhi asili na alama za uaminifu.
   Inasajili kiungo cha usanidi (mfano: trustgraph-flow/trustgraph/prompt/template/service.py) ili kupokea data ya usanidi na kuondoa maelezo ya mfumo.
   Inapokea vitu na kuyaondoa kuwa vitu vya ExtractedObject ili kuwasilisha kwenye folyo ya Pulsar.
   NOTE: Kuna msimbo uliopo kwenye `trustgraph-flow/trustgraph/extract/object/row/`. Hii ilikuwa jaribio la awali na itahitaji marekebisho makubwa kwani haikubaliana na API za sasa. Tumia ikiwa ni muhimu, anza kutoka mwanzo ikiwa sio.
   Inahitaji kiungo cha mstari wa amri: `kg-extract-objects`

   Moduli: trustgraph-flow/trustgraph/extract/kg/objects/

4. **Moduli ya Kuandika ya Duka la Imeinishwa** ✅ **[IMEKAMILIKA]**
   Inapokea vitu katika umbizo wa ExtractedObject kutoka kwa folyo za Pulsar.
   Utumiaji wa awali unalenga Apache Cassandra kama duka la data iliyoainishwa.
   Inashughulikia uundaji wa meza ya moja kwa moja kulingana na umbizo uliokutana.
   Inadhibiti ramani ya mfumo-kwa-meza ya Cassandra na ubadilishaji wa data.
   Inatoa operesheni za kuandika za kundi na za mtiririko kwa uboreshaji wa utendaji.
   Hakuna matokeo ya Pulsar - hii ni huduma ya mwisho katika mtiririko wa data.

   **Ushughulikiaji wa Mfumo**:
   Inafuatilia meseji zinazoingia za ExtractedObject kwa marejeleo ya mfumo.
   
   
   Inapaswa kuzingatia kama itapokea maelezo ya muundo moja kwa moja au itategemea majina ya muundo katika ujumbe wa ExtractedObject.

   **Ramapishi ya Jedwali la Cassandra**:
   Jina la keyspace linatokana na sehemu `user` kutoka Metadata ya ExtractedObject
   Jina la jedwali linatokana na sehemu `schema_name` kutoka ExtractedObject
   Mkusanyiko kutoka Metadata unakuwa sehemu ya ufunguo wa partition ili kuhakikisha:
     Usambazaji wa data kwa njia ya asili katika nodi za Cassandra
     Maswali (queries) bora ndani ya mkusanyiko maalum
     Utengano wa mantiki kati ya uingizaji wa data tofauti/vyanzo
   Muundo wa ufunguo mkuu: `PRIMARY KEY ((collection, <schema_primary_key_fields>), <clustering_keys>)`
     Mkusanyiko huwa sehemu ya kwanza ya ufunguo wa partition
     Sehemu za ufunguo mkuu zilizobainishwa katika schema zinafuata kama sehemu ya ufunguo wa partition iliyounganishwa
     Hii inahitaji maswali (queries) yataonyesha mkusanyiko, kuhakikisha utendaji unaoweza kutabirika
   Ufafanuzi wa sehemu unahusishwa na safu za Cassandra na mabadiliko ya aina:
     `string` → `text`
     `integer` → `int` au `bigint` kulingana na ukubwa
     `float` → `float` au `double` kulingana na mahitaji ya usahihi
     `boolean` → `boolean`
     `timestamp` → `timestamp`
     `enum` → `text` na uthibitishaji wa kiwango cha programu
   Sehemu zilizo na fahirisi huunda fahirisi za sekondari za Cassandra (isipokuwa sehemu zilizopo katika ufunguo mkuu)
   Sehemu zinazohitajika zinafanywa katika kiwango cha programu (Cassandra haitumii NOT NULL)

   **Hifadhi ya Data (Object Storage)**:
   Inatoa maadili kutoka ramani ya ExtractedObject.values
   Inafanya mabadiliko ya aina na uthibitishaji kabla ya kuingizwa
   Inashughulikia sehemu za hiari ambazo hazipo kwa utulivu
   Inahifadhi metadata kuhusu asili ya data (hati ya chanzo, alama za uaminifu)
   Inasaidia uandikaji ambao unaweza kufanywa tena ili kushughulikia hali za kucheza tena ujumbe

   **Maelezo ya Utendaji**:
   Msimbo uliopo katika `trustgraph-flow/trustgraph/storage/objects/cassandra/` ni wa zamani na haukidhi vipimo vya sasa vya API
   Inapaswa kurejelea `trustgraph-flow/trustgraph/storage/triples/cassandra` kama mfano wa mchakato wa hifadhi unaofanya kazi
   Inahitaji tathmini ya msimbo uliopo ili kuona ikiwa kuna sehemu ambazo zinaweza kutumika tena kabla ya kuamua kufanya marekebisho au kuandika upya

   Moduli: trustgraph-flow/trustgraph/storage/objects/cassandra

5. **Huduma ya Maswali (Structured Query Service)** ✅ **[IMEKAMILIKA]**
   Inakubali maswali ya muundo katika muundo uliotolewa
   Inatekeleza maswali dhidi ya hifadhi ya muundo
   Inarudisha data inayolingana na vigezo vya swali
   Inasaidia upangishaji na uchujaji wa matokeo

   Moduli: trustgraph-flow/trustgraph/query/objects/cassandra

6. **Uunganisho wa Zana za Wakala (Agent Tool Integration)**
   Darasa jipya la zana kwa mifumo ya wakala
   Inaruhusu wakala kuuliza hifadhi za data zilizopangwa
   Inatoa interfaces ya lugha ya asili na maswali ya muundo
   Inajumuishwa na michakato iliyopo ya wakala ya kufanya maamuzi

7. **Huduma ya Uingizaji wa Data Iliyopangwa (Structured Data Ingestion Service)**
   Inakubali data iliyopangwa katika muundo mbalimbali (JSON, CSV, XML)
   Inachanganua na kuthibitisha data inayokuja dhidi ya schemas zilizobainishwa
   Inabadilisha data kuwa mitirisho ya data iliyopangwa
   Inatoa data kwa folyo za ujumbe zinazofaa kwa usindikaji
   Inasaidia upakiaji wa wingi na uingizaji wa mtiririko

   Moduli: trustgraph-flow/trustgraph/decoding/structured

8. **Huduma ya Uwekaji wa Data (Object Embedding Service)**
   Inazalisha uwekaji wa vector kwa data iliyopangwa
   Inaruhusu utafutaji wa semantic katika data iliyopangwa
   Inasaidia utafutaji wa mchanganyiko unaounganisha maswali ya muundo na ufanano wa semantic
   Inajumuishwa na hifadhi za vector zilizopo

   Moduli: trustgraph-flow/trustgraph/embeddings/object_embeddings/qdrant

### Mifano ya Data

#### Utaratibu wa Uhifadhi wa Schema

Schemas zinawekwa katika mfumo wa usanidi wa TrustGraph kwa kutumia muundo ufuatao:

**Aina**: `schema` (thamani iliyobainishwa kwa schemas zote za data iliyopangwa)
**Ufunguo**: Jina/kitambulisho cha kipekee cha schema (k.m., `customer_records`, `transaction_log`)
**Thamani**: Ufafanuzi wa schema ya JSON unao na muundo

Ingizo la usanidi wa mfano:
```
Type: schema
Key: customer_records
Value: {
  "name": "customer_records",
  "description": "Customer information table",
  "fields": [
    {
      "name": "customer_id",
      "type": "string",
      "primary_key": true
    },
    {
      "name": "name",
      "type": "string",
      "required": true
    },
    {
      "name": "email",
      "type": "string",
      "required": true
    },
    {
      "name": "registration_date",
      "type": "timestamp"
    },
    {
      "name": "status",
      "type": "string",
      "enum": ["active", "inactive", "suspended"]
    }
  ],
  "indexes": ["email", "registration_date"]
}
```

Mbinu hii inaruhusu:
Ufafanuzi wa muundo (schema) unaobadilika bila mabadiliko ya programu
Marekebisho na matoleo ya muundo (schema) rahisi
Uunganishaji thabiti na usimamizi wa usanidi wa TrustGraph uliopo
Usaidizi wa muundo (schemas) nyingi ndani ya matumizi moja

### API

API mpya:
  Muundo (schemas) za Pulsar kwa aina zilizo hapo juu
  Vifaa vya Pulsar katika mtiririko mpya
  Inahitajika njia ya kutaja aina za muundo (schema) katika mitiririko ili mitiririko iweze kujua
    aina gani za muundo (schema) kupakua
  API zimeongezwa kwenye lango na lango la marekebisho

API zilizobadilishwa:
Vifaa vya utoaji wa maarifa - Ongeza chaguo la pato la kitu kilicho na muundo
Vifaa vya wakala - Ongeza usaidizi wa zana za data iliyo na muundo

### Maelezo ya Utendaji

Kufuata mbinu zilizopo - haya ni moduli mpya tu za usindikaji.
Kila kitu kiko katika vifurushi vya trustgraph-flow isipokuwa vipengele vya muundo (schema)
katika trustgraph-base.

Inahitajika kazi ya UI katika Workbench ili kuweza kuonyesha / majaribio ya
uwezo huu.

## Masuala ya Usalama

Hakuna masuala ya ziada.

## Masuala ya Utendaji

Maswali kadhaa kuhusu matumizi ya maswali na fahirisi za Cassandra ili maswali
yasichanganye.

## Mkakati wa Majaribio

Tumia mkakati wa majaribio uliopo, tutaunda majaribio ya kitengo, mkataba na ujumuishaji.

## Mpango wa Uhamisho

Hakuna.

## Muda

Haikubainishwa.

## Maswali Yaliyofunguliwa

Je, hii inaweza kufanywa ili kufanya kazi na aina zingine za hifadhi? Tunalenga kutumia
  vifaa ambavyo hufanya moduli zinazofanya kazi na hifadhi moja kuwa zinapatikana kwa
  hifadhi zingine.

## Marejeleo

n/a.
