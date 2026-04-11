# Uhifadhi wa Mfumo wa Maarifa unaozingatia Vitu kwenye Cassandra

## Muhtasari

Hati hii inaelezea mfumo wa uhifadhi wa mifumo ya maarifa ya mtindo wa RDF kwenye Apache Cassandra. Mfumo hutumia mbinu inayozingatia **vitu**, ambapo kila kitu kinajua kila nne (quad) ambacho kinashiriki na jukumu ambalo linacheza. Hii inabadilisha mbinu ya awali ya meza nyingi zinazobadilisha mpangilio wa SPO kuwa meza mbili tu.

## Asili na Lengo

### Mbinu ya Jadi

Hifadhi ya kawaida ya nne (quad) ya RDF kwenye Cassandra inahitaji meza nyingi zisizofaa ili kufidia mitindo ya maswali — kwa kawaida meza 6 au zaidi zinazowakilisha mabadiliko tofauti ya Mada (Subject), Kielelezo (Predicate), Kitu (Object), na Kundi (Dataset) (SPOD). Kila nne (quad) imeandikwa kwenye kila meza, na kusababisha ongezeko kubwa la uandishi, gharama za uendeshaji, na utata wa muundo.

Zaidi ya hayo, utatuzi wa lebo (kupata majina yanayoweza kusomwa kwa urahisi kwa vitu) inahitaji maswali ya ziada, ambayo ni ya gharama kubwa hasa katika matumizi ya AI na GraphRAG ambapo lebo ni muhimu kwa muktadha wa LLM.

### Mwangaza wa Mbinu inayozingatia Vitu

Kila kikundi cha `(D, S, P, O)` kinahusisha hadi vitu 4. Kwa kuandika safu kwa kila shiriki la kitu katika kikundi, tunahakikisha kwamba **maswali yoyote yenye angalau kipengele kimoja kinachojulikana yatatumia ufunguo wa sehemu**. Hii inafunika mifumo yote 16 ya maswali na jedwali moja la data.

Faida kuu:

**Jedwali 2** badala ya 7+
**Hali 4 kwa kila kikundi** badala ya 6+
**Utatuzi wa lebo bila malipo** — lebo za kitu ziko karibu na uhusiano wake, na hivyo kuongeza kasi ya kumbukumbu ya programu.
**Mifumo yote 16 ya maswali** hutumika kwa usomaji wa sehemu moja.
**Utendaji rahisi** — jedwali moja la data ili kurekebisha, kupunguza, na kurekebisha.

## Mpango

### Jedwali 1: quads_by_entity

Jedwali kuu la data. Kila kitu kina sehemu inayoyakilisha vikundi vyote ambavyo kitu hicho kinashiriki. Jina lake linaonyesha mfumo wa swali (utafutaji kwa kutumia kitu).

```sql
CREATE TABLE quads_by_entity (
    collection text,       -- Collection/tenant scope (always specified)
    entity     text,       -- The entity this row is about
    role       text,       -- 'S', 'P', 'O', 'G' — how this entity participates
    p          text,       -- Predicate of the quad
    otype      text,       -- 'U' (URI), 'L' (literal), 'T' (triple/reification)
    s          text,       -- Subject of the quad
    o          text,       -- Object of the quad
    d          text,       -- Dataset/graph of the quad
    dtype      text,       -- XSD datatype (when otype = 'L'), e.g. 'xsd:string'
    lang       text,       -- Language tag (when otype = 'L'), e.g. 'en', 'fr'
    PRIMARY KEY ((collection, entity), role, p, otype, s, o, d, dtype, lang)
);
```

**Ufunguo wa partition:** `(collection, entity)` — unafichwa kwa mkusanyiko, na partition moja kwa kila entiti.

**Mazingira ya utaratibu wa safu za kuunganisha (clustering):**

1. **role** — maswali mengi huanza kwa "entiti hii ni mada/jambo"
2. **p** — chujio cha kawaida cha pili, "nipa uhusiano wote wa `knows`"
3. **otype** — inaruhusu kuchujwa kwa uhusiano wenye thamani ya URI dhidi ya uhusiano wenye thamani ya moja kwa moja
4. **s, o, d** — safu zilizobaki kwa uhakikisho
5. **dtype, lang** — hutofautisha maandishi yenye thamani sawa lakini metadata tofauti ya aina (k.m., `"thing"` vs `"thing"@en` vs `"thing"^^xsd:string`)

### Jedwali 2: quads_by_collection

Inasaidia maswali na uondoaji wa kiwango cha mkusanyiko. Inatoa orodha ya quads zote zinazohusiana na mkusanyiko. Imejina ili kuonyesha muundo wa swali (utafutaji kwa mkusanyiko).

```sql
CREATE TABLE quads_by_collection (
    collection text,
    d          text,       -- Dataset/graph of the quad
    s          text,       -- Subject of the quad
    p          text,       -- Predicate of the quad
    o          text,       -- Object of the quad
    otype      text,       -- 'U' (URI), 'L' (literal), 'T' (triple/reification)
    dtype      text,       -- XSD datatype (when otype = 'L')
    lang       text,       -- Language tag (when otype = 'L')
    PRIMARY KEY (collection, d, s, p, o, otype, dtype, lang)
);
```

Imefunganishwa kwanza kwa muundo wa data, na hivyo kuruhusu kufutwa kwa vitu au muundo wa data. Safu za `otype`, `dtype`, na `lang` zimejumuishwa katika ufunganishi ili kutofautisha vipengele ambavyo vina thamani sawa lakini data tofauti — katika RDF, `"thing"`, `"thing"@en`, na `"thing"^^xsd:string` ni thamani tofauti kwa maana.

## Njia ya Kuandika

Kwa kila kipengele kinachokuja `(D, S, P, O)` ndani ya mkusanyiko `C`, andika **safu 4** kwenye `quads_by_entity` na **safu 1** kwenye `quads_by_collection`.

### Mfano

Ikiwa kuna kipengele katika mkusanyiko `tenant1`:

```
Dataset:  https://example.org/graph1
Subject:  https://example.org/Alice
Predicate: https://example.org/knows
Object:   https://example.org/Bob
```

Andika mistari 4 hadi `quads_by_entity`:

| mkusanyiko | kitu | jukumu | p | aina ya kitu | s | o | d |
|---|---|---|---|---|---|---|---|
| tenant1 | https://example.org/graph1 | G | https://example.org/knows | U | https://example.org/Alice | https://example.org/Bob | https://example.org/graph1 |
| tenant1 | https://example.org/Alice | S | https://example.org/knows | U | https://example.org/Alice | https://example.org/Bob | https://example.org/graph1 |
| tenant1 | https://example.org/knows | P | https://example.org/knows | U | https://example.org/Alice | https://example.org/Bob | https://example.org/graph1 |
| tenant1 | https://example.org/Bob | O | https://example.org/knows | U | https://example.org/Alice | https://example.org/Bob | https://example.org/graph1 |

Andika mstari 1 hadi `quads_by_collection`:

| mkusanyiko | d | s | p | o | aina ya kitu | aina ya data | lugha |
|---|---|---|---|---|---|---|---|
| tenant1 | https://example.org/graph1 | https://example.org/Alice | https://example.org/knows | https://example.org/Bob | U | | |

### Mfano Halisi

Kwa jozi ya lebo:

```
Dataset:  https://example.org/graph1
Subject:  https://example.org/Alice
Predicate: http://www.w3.org/2000/01/rdf-schema#label
Object:   "Alice Smith" (lang: en)
```

Msimbo `otype` ni `'L'`, `dtype` ni `'xsd:string'`, na `lang` ni `'en'`. Thamani halisi `"Alice Smith"` huhifadhiwa katika `o`. Safu 3 tu zinahitajika katika `quads_by_entity` — hakuna safu inayorekodiwa kwa thamani kama kitu, kwa sababu vitu haviwezi kuchunguzwa kando.

## Mifumo ya Uchunguzi

### Mifumo 16 Yote ya DSPO

Katika meza iliyo hapa chini, "Kielelezo kamili" ina maana kwamba swali hutumia kielelezo cha kuendelea cha safu za kuunganisha. "Ufuatiliaji wa sehemu + chujio" ina maana kwamba Cassandra husoma sehemu ya moja ya sehemu na kuchuja katika kumbukumbu — bado ni ufanisi, lakini sio mechi ya kielelezo safi.

| # | Inajulikana | Tafuta kitu | Kielelezo cha kuunganisha | Ufanisi |
|---|---|---|---|---|
| 1 | D,S,P,O | kitu=S, jukumu='S', p=P | Mechi kamili | Kielelezo kamili |
| 2 | D,S,P,? | kitu=S, jukumu='S', p=P | Chujio kwenye D | Ufuatiliaji wa sehemu + chujio |
| 3 | D,S,?,O | kitu=S, jukumu='S' | Chujio kwenye D, O | Ufuatiliaji wa sehemu + chujio |
| 4 | D,?,P,O | kitu=O, jukumu='O', p=P | Chujio kwenye D | Ufuatiliaji wa sehemu + chujio |
| 5 | ?,S,P,O | kitu=S, jukumu='S', p=P | Chujio kwenye O | Ufuatiliaji wa sehemu + chujio |
| 6 | D,S,?,? | kitu=S, jukumu='S' | Chujio kwenye D | Ufuatiliaji wa sehemu + chujio |
| 7 | D,?,P,? | kitu=P, jukumu='P' | Chujio kwenye D | Ufuatiliaji wa sehemu + chujio |
| 8 | D,?,?,O | kitu=O, jukumu='O' | Chujio kwenye D | Ufuatiliaji wa sehemu + chujio |
| 9 | ?,S,P,? | kitu=S, jukumu='S', p=P | — | **Kielelezo kamili** |
| 10 | ?,S,?,O | kitu=S, jukumu='S' | Chujio kwenye O | Ufuatiliaji wa sehemu + chujio |
| 11 | ?,?,P,O | kitu=O, jukumu='O', p=P | — | **Kielelezo kamili** |
| 12 | D,?,?,? | kitu=D, jukumu='G' | — | **Kielelezo kamili** |
| 13 | ?,S,?,? | kitu=S, jukumu='S' | — | **Kielelezo kamili** |
| 14 | ?,?,P,? | kitu=P, jukumu='P' | — | **Kielelezo kamili** |
| 15 | ?,?,?,O | kitu=O, jukumu='O' | — | **Kielelezo kamili** |
| 16 | ?,?,?,? | — | Ufuatiliaji kamili | Uchunguzi tu |

**Matokeo muhimu**: 7 kati ya mifumo 15 isiyo ya kawaida ni mechi kamili za kielelezo cha kuunganisha. Mifumo 8 iliyobaki ni usomaji wa sehemu moja na chujio ndani ya sehemu. Kila swali lenye kipengele kinachojulikana hupiga ufunguo wa sehemu.

Mfumo 16 (?,?,?,?) haujulikani katika mazoezi kwa sababu mkusanyiko daima umeelezwa, na hivyo kuifanya iwe mfumo wa 12.

### Mifano ya kawaida ya swali

**Kila kitu kuhusu kitu:**

```sql
SELECT * FROM quads_by_entity
WHERE collection = 'tenant1' AND entity = 'https://example.org/Alice';
```

**Uhusiano wote unaotoka kwa kitu:**

```sql
SELECT * FROM quads_by_entity
WHERE collection = 'tenant1' AND entity = 'https://example.org/Alice'
AND role = 'S';
```

**Tabia maalum ya kitu:**

```sql
SELECT * FROM quads_by_entity
WHERE collection = 'tenant1' AND entity = 'https://example.org/Alice'
AND role = 'S' AND p = 'https://example.org/knows';
```

**KILabeli kwa kitu (lugha mahususi):**

```sql
SELECT * FROM quads_by_entity
WHERE collection = 'tenant1' AND entity = 'https://example.org/Alice'
AND role = 'S' AND p = 'http://www.w3.org/2000/01/rdf-schema#label'
AND otype = 'L';
```

Kisha, chambua matokeo kwa kutumia `lang = 'en'` upande wa programu, ikiwa ni lazima.

**Tu uhusiano ambao una thamani ya URI (viungo vya aina ya kitu-kwa-kitu):**

```sql
SELECT * FROM quads_by_entity
WHERE collection = 'tenant1' AND entity = 'https://example.org/Alice'
AND role = 'S' AND p = 'https://example.org/knows' AND otype = 'U';
```

**Utafutaji wa kurudi nyuma — ni nini kinachoelekeza kwenye kitu hiki:**

```sql
SELECT * FROM quads_by_entity
WHERE collection = 'tenant1' AND entity = 'https://example.org/Bob'
AND role = 'O';
```

## Utatuzi wa Lebo na Ukaushaji wa Kumbukumbu (Cache Warming)

Moja ya faida muhimu zaidi ya mfumo unaozingatia vitu (entity-centric) ni kwamba **utatuzi wa lebo unakuwa matokeo ya ziada**.

Katika mfumo wa zamani unaojumuisha meza nyingi, kupata lebo inahitaji maswali tofauti: pata triplet, tambua URI za vitu katika matokeo, kisha pata `rdfs:label` kwa kila moja. Mfumo huu wa N+1 ni ghali.

Katika mfumo unaozingatia vitu, kuhoji kitu hurejesha **quads zote** - ikiwa ni pamoja na lebo zake, aina, na sifa zingine. Wakati programu inahifadhi matokeo ya maswali, lebo zimeandaliwa kabla ya chochote kuomba.

Sera mbili za matumizi zinaonyesha kwamba hii inafanya kazi vizuri katika mazoezi:

**Maswali yanayoeleweka na binadamu**: kawaida matokeo madogo, lebo ni muhimu. Maswali ya vitu huandalia kumbukumbu (cache).
**Maswali ya AI/wingi**: matokeo makubwa na mipaka ngumu. Lebo ama hazihitajiki au zinahitajika tu kwa sehemu ndogo ya vitu ambavyo tayari viko kwenye kumbukumbu.

Wasiwasi wa kisia wa kutatua lebo kwa matokeo makubwa (k.m. vitu 30,000) hupunguzwa na utambuzi wa vitendo kwamba hakuna mtumiaji wa binadamu au AI anayeweza kuchakata lebo nyingi. Mipaka ya programu ya maswali inahakikisha kwamba shinikizo la kumbukumbu linabaki linaloweza kudhibitiwa.

## Sehemu Zinazopaswa Kusambazwa na Ufafanuzi

Ufafanuzi (taarifa za aina ya RDF-star kuhusu taarifa) huunda vitu vya kitovu - k.m. hati ya chanzo ambayo inasaidia ukweli mwingi uliotolewa. Hii inaweza kuzalisha sehemu zinazopaswa kusambazwa.

Mambo yanayoweza kupunguza:

**Mipaka ya maswali ya programu**: maswali yote ya GraphRAG na yale yanayoeleweka na binadamu yana mipaka ngumu, kwa hivyo sehemu zinazopaswa kusambazwa hazisomwi kamwe kwa upeo wa njia ya usomaji.
**Cassandra inashughulikia usomaji wa sehemu kwa ufanisi**: uchanganuzi wa safu ya ufunguo wa uainishaji na kusimamishwa mapema ni wa haraka hata kwenye sehemu kubwa.
**Ufutaji wa mkusanyiko** (operesheni pekee ambayo inaweza kuvuka sehemu kamili) ni mchakato unaokubalika wa asili.

## Ufufuo wa Mkusaniko

Huendeshwa na wito wa API, inafanya kazi kwa asili (inatimiza kwa wakati).

1. Soma `quads_by_collection` kwa mkusanyiko unaolengwa ili kupata quads zote.
2. Toa vitu vya kipekee kutoka kwa quads (mahesabu ya s, p, o, d).
3. Kwa kila kitu cha kipekee, futa sehemu kutoka kwa `quads_by_entity`.
4. Futa mistari kutoka kwa `quads_by_collection`.

Jedwali la `quads_by_collection` hutoa fahirisi inayohitajika ili kupata sehemu zote za kitu bila uchanganuzi kamili wa jedwali. Ufufuo wa kiwango cha sehemu ni wa ufanisi kwa sababu `(collection, entity)` ndio ufunguo wa sehemu.

## Njia ya Uhamishaji kutoka kwa Mfumo wa Meza Nyingi

Mfumo unaozingatia vitu unaweza kuwepo na mfumo wa zamani unaojumuisha meza nyingi wakati wa uhamishaji:

1. Weka meza za `quads_by_entity` na `quads_by_collection` pamoja na meza zilizopo.
2. Andika quads mpya kwa meza zote mbili za zamani na mpya.
3. Jaza data iliyopo kwenye meza mpya.
4. Hamisha njia za maswali moja kwa moja.
5. Ondoa meza za zamani baada ya maswali yote kuhamishwa.

## Muhtasari

| Nguvu | Zamani (meza 6) | Kitu (meza 2) |
|---|---|---|
| Meza | 7+ | 2 |
| Andishi kwa kila quad | 6+ | 5 (4 data + 1 manifest) |
| Utafiti wa lebo | Safari tofauti | Bila shida kupitia ukaushaji wa kumbukumbu |
| Mfumo wa maswali | 16 katika meza 6 | 16 katika meza 1 |
| Ufumbuzi wa mpango | Wa juu | Wa chini |
| Uendeshaji | Meza 6 za kurekebisha/kufufua | Jedwali 1 la data |
| Usaidizi wa ufafanuzi | Ufumbuzi wa ziada | Inafaa asili |
| Uchunguzi wa aina ya kitu | Haipatikani | Asili (kupitia uainishaji wa otype) |

