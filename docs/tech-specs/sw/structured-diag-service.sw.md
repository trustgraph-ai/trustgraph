---
layout: default
title: "Vigezo vya Kisaikolojia kwa Huduma ya Utambuzi wa Data Imebuniwa"
parent: "Swahili (Beta)"
---

# Vigezo vya Kisaikolojia kwa Huduma ya Utambuzi wa Data Imebuniwa

> **Beta Translation:** This document was translated via Machine Learning and as such may not be 100% accurate. All non-English languages are currently classified as Beta.

## Muhtasari

Vigezo hivi vinaelezea huduma mpya inayoweza kutumika kwa utambuzi na uchambuzi wa data iliyobuniwa ndani ya TrustGraph. Huduma hii hutoa utendakazi kutoka kwa zana ya `tg-load-structured-data` iliyopo ya mstari wa amri na kuifanya kuwa huduma ya ombi/jibu, na hivyo kuwezesha ufikiaji wa programu kwa uwezo wa utambuzi wa aina ya data na uundaji wa maelezo.

Huduma hii inasaidia operesheni tatu kuu:

1. **Utambuzi wa Aina ya Data**: Changanua sampuli ya data ili kubaini muundo wake (CSV, JSON, au XML)
2. **Uundaji wa Maelezo**: Unda maelezo ya TrustGraph ya data iliyobuniwa kwa sampuli fulani ya data na aina
3. **Utambuzi Mchanganyiko**: Fanya utambuzi wa aina na uundaji wa maelezo kwa pamoja

## Lengo

**Kugawa Uchunguzi wa Data**: Toa mantiki ya utambuzi wa data kutoka kwa CLI hadi vipengele vya huduma vinavyoweza kutumika tena
**Kuwezesha Ufikiaji wa Programu**: Toa ufikiaji wa API kwa uwezo wa uchambuzi wa data
**Kusaidia Muundo Mbalimbali wa Data**: Shirikisha muundo wa data wa CSV, JSON, na XML kwa uthabiti
**Kuzalisha Maelezo Sahihi**: Toa maelezo ya data iliyobuniwa ambayo yanaelea data ya chanzo kwa schemas za TrustGraph
**Kuhifadhi Utangamano wa Zamani**: Hakikisha utendakazi wa sasa wa CLI unaendelea kufanya kazi
**Kuwezesha Uundaji wa Huduma**: Ruhusu huduma zingine kutumia uwezo wa utambuzi wa data
**Kuboresha Uwezekano wa Kujaribu**: Tenganisha mantiki ya biashara kutoka kwa kiolesura cha CLI kwa ajili ya majaribio bora
**Kusaidia Uchanganuzi wa Msururu**: Wezesha uchanganuzi wa sampuli za data bila kulaini faili nzima

## Asili

Kwa sasa, amri ya `tg-load-structured-data` hutoa utendakazi kamili kwa uchambuzi wa data iliyobuniwa na uundaji wa maelezo. Hata hivyo, utendakazi huu umeunganishwa sana na kiolesura cha CLI, na hivyo kupunguza uwezekano wake wa kutumika tena.

Mapungufu ya sasa ni pamoja na:
Mantiki ya utambuzi wa data iliyo ndani ya nambari ya CLI
Hakuna ufikiaji wa programu kwa utambuzi wa aina na uundaji wa maelezo
Ni vigumu kuunganisha uwezo wa utambuzi katika huduma zingine
Uwezo mdogo wa kuunda mchakato wa uchambuzi wa data

Vigezo hivi vinashughulikia pengo hizi kwa kuunda huduma maalum ya utambuzi wa data iliyobuniwa. Kwa kuonyesha uwezo huu kama huduma, TrustGraph inaweza:
Kuwezesha huduma zingine kuchambua data kwa programu
Kusaidia mnyororo wa uchakataji wa data unaozidi
Kurahisisha ushirikiano na mifumo ya nje
Kuboresha uendelevu kupitia kutenganisha masuala

## Muundo wa Kiufundi

### Usanifu

Huduma ya utambuzi wa data iliyobuniwa inahitaji vipengele vifuatavyo vya kiufundi:

1. **Mchakato wa Huduma ya Utambuzi**
   Hushughulikia ombi la utambuzi linalokuja
   Huendesha utambuzi wa aina na uundaji wa maelezo
   Hurudisha majibu yaliyobuniwa na matokeo ya utambuzi

   Moduli: `trustgraph-flow/trustgraph/diagnosis/structured_data/service.py`

2. **Kigunduzi cha Aina ya Data**
   Hutumia utambuzi wa algorithm ili kutambua muundo wa data (CSV, JSON, XML)
   Inachanganua muundo wa data, vichakavu, na mifumo ya sintaksia
   Hurudisha muundo uliogunduliwa na alama za uaminifu

   Moduli: `trustgraph-flow/trustgraph/diagnosis/structured_data/type_detector.py`

3. **Mundua wa Maelezo**
   Hutumia huduma ya ombi ili kuzalisha maelezo
   Huita ombi maalum ya muundo (diagnose-csv, diagnose-json, diagnose-xml)
   Inoelekeza nafasi za data kwa nafasi za schema za TrustGraph kupitia majibu ya ombi

   Moduli: `trustgraph-flow/trustgraph/diagnosis/structured_data/descriptor_generator.py`

### Mifano ya Data

#### StructuredDataDiagnosisRequest

Ujumbe wa ombi kwa operesheni za utambuzi wa data iliyobuniwa:

```python
class StructuredDataDiagnosisRequest:
    operation: str  # "detect-type", "generate-descriptor", or "diagnose"
    sample: str     # Data sample to analyze (text content)
    type: Optional[str]  # Data type (csv, json, xml) - required for generate-descriptor
    schema_name: Optional[str]  # Target schema name for descriptor generation
    options: Dict[str, Any]  # Additional options (e.g., delimiter for CSV)
```

#### Jibu la Uchambuzi wa Data Iliyopangwa

Ujumbe wa jibu unaoonyesha matokeo ya uchambuzi:

```python
class StructuredDataDiagnosisResponse:
    operation: str  # The operation that was performed
    detected_type: Optional[str]  # Detected data type (for detect-type/diagnose)
    confidence: Optional[float]  # Confidence score for type detection
    descriptor: Optional[Dict]  # Generated descriptor (for generate-descriptor/diagnose)
    error: Optional[str]  # Error message if operation failed
    metadata: Dict[str, Any]  # Additional metadata (e.g., field count, sample records)
```

#### Muundo wa Kisajili

Kisajili kinachozalishwa kinafuata muundo wa sasa wa kisajili cha data iliyopangwa:

```json
{
  "format": {
    "type": "csv",
    "encoding": "utf-8",
    "options": {
      "delimiter": ",",
      "has_header": true
    }
  },
  "mappings": [
    {
      "source_field": "customer_id",
      "target_field": "id",
      "transforms": [
        {"type": "trim"}
      ]
    }
  ],
  "output": {
    "schema_name": "customer",
    "options": {
      "batch_size": 1000,
      "confidence": 0.9
    }
  }
}
```

### Kiolesho cha Muunganisho

Huduma itatoa huduma zifuatazo kupitia mfumo wa ombi/jibu:

1. **Operesheni ya Udagilizaji wa Aina**
   Ingizo: Sampuli ya data
   Uchakataji: Angalia muundo wa data kwa kutumia ugani wa uchunguzi
   Patoto: Aina iliyogunduliwa pamoja na alama ya uaminifu

2. **Operesheni ya Uundaji wa Kisajili**
   Ingizo: Sampuli ya data, aina, jina la mpango (schema) unaolengwa
   Uchakataji:
     Piga huduma ya ombi kwa kitambulisho cha ombi maalum kwa aina (diagnose-csv, diagnose-json, au diagnose-xml)
     Pasa sampuli ya data na mipango inayopatikana kwa ombi
     Pokea kisajili kilichoundwa kutoka kwa jibu la ombi
   Patoto: Kisajili cha data iliyopangwa

3. **Operesheni ya Uchambuzi Mchanganyiko**
   Ingizo: Sampuli ya data, jina la mpango (schema) la hiari
   Uchakataji:
     Tumia ugani wa uchunguzi ili kubaini aina kwanza
     Chagua ombi maalum kwa aina kulingana na aina iliyogunduliwa
     Piga huduma ya ombi ili kuunda kisajili
   Patoto: Aina iliyogunduliwa na kisajili

### Maelezo ya Utendaji

Huduma itafuata miongozo ya huduma ya TrustGraph:

1. **Usajili wa Huduma**
   Sajili kama aina ya `structured-diag`
   Tumia mada za kipekee za ombi/jibu
   Lenga darasa la msingi la FlowProcessor
   Sajili PromptClientSpec kwa mwingiliano wa huduma ya ombi

2. **Usimamizi wa Usanidi**
   Pata usanidi wa mpango kupitia huduma ya usanidi
   Hifadhi mipango kwa utendaji
   Shirikisha mabadiliko ya usanidi kwa utaratibu

3. **Uunganisho wa Ombi**
   Tumia miundombinu iliyopo ya huduma ya ombi
   Piga huduma ya ombi kwa kitambulisho cha ombi maalum kwa aina:
     `diagnose-csv`: Kwa uchambuzi wa data ya CSV
     `diagnose-json`: Kwa uchambuzi wa data ya JSON
     `diagnose-xml`: Kwa uchambuzi wa data ya XML
   Ombi zimepangwa katika usanidi wa ombi, sio zilizopangwa katika huduma
   Pasa mipango na sampuli za data kama vigezo vya ombi
   Changanua majibu ya ombi ili kuchimbua visajili

4. **Usimamizi wa Hitilafu**
   Thibitisha sampuli za ingizo
   Toa ujumbe wa kosa unaoeleweka
   Shirikisha data iliyo na kasoro kwa utaratibu
   Shirikisha hitilafu za huduma ya ombi

5. **Uchukuzi wa Sampuli**
   Chakata saizi za sampuli zinazoweza kusanidiwa
   Shirikisha rekodi zisizo kamili kwa utaratibu
   Dumishe utaratibu wa uchukuzi

### Uunganisho wa API

Huduma itounganisha na API za TrustGraph zilizopo:

Vipengele Vilivyobadilishwa:
`tg-load-structured-data` CLI - Imepangwa upya ili kutumia huduma mpya kwa operesheni za uchambuzi
Flow API - Imepanuliwa ili kusaidia ombi za uchambuzi wa data iliyopangwa

Ncha Mpya za Huduma:
`/api/v1/flow/{flow}/diagnose/structured-data` - Ncha ya WebSocket kwa ombi za uchambuzi
`/api/v1/diagnose/structured-data` - Ncha ya REST kwa uchambuzi wa synchronous

### Mtiririko wa Ujumbe

```
Client → Gateway → Structured Diag Service → Config Service (for schemas)
                                           ↓
                                    Type Detector (algorithmic)
                                           ↓
                                    Prompt Service (diagnose-csv/json/xml)
                                           ↓
                                 Descriptor Generator (parses prompt response)
                                           ↓
Client ← Gateway ← Structured Diag Service (response)
```

## Masuala ya Usalama

Uthibitishaji wa pembejeo ili kuzuia mashambulizi ya kuingiza data
Mipaka ya ukubwa ya sampuli za data ili kuzuia mashambulizi ya aina ya "Denial of Service" (DoS)
Usafishaji wa maelezo yaliyoundwa
Udhibiti wa ufikiaji kupitia uthibitishaji wa TrustGraph uliopo

## Masuala ya Utendaji

Hifadhi maelezo ya muundo ili kupunguza idadi ya ombi kwa huduma ya usanidi
Punguza ukubwa wa sampuli ili kudumisha utendaji wa haraka
Tumia usindikaji wa mtiririko kwa sampuli kubwa za data
Lenga mitambo ya muda kwa uchambuzi unaochukua muda mrefu

## Mkakati wa Majaribio

1. **Majaribio ya Kitengo**
   Utambuzi wa aina kwa muundo tofauti wa data
   Usahihi wa uundaji wa maelezo
   Hali za kushughulikia makosa

2. **Majaribio ya Uunganisho**
   Mtiririko wa ombi/jibu wa huduma
   Kupata na kuhifadhi muundo
   Uunganisho wa CLI

3. **Majaribio ya Utendaji**
   Usindikaji wa sampuli kubwa
   Kushughulikia ombi kwa wakati mmoja
   Matumizi ya kumbukumbu chini ya mzigo

## Mpango wa Uhamisho

1. **Awamu ya 1**: Tekeleza huduma na utendaji wa msingi
2. **Awamu ya 2**: Badilisha CLI ili itumie huduma (dumishe utangamano wa zamani)
3. **Awamu ya 3**: Ongeza vidokezo vya API ya REST
4. **Awamu ya 4**: Ondoa mantiki iliyojumuishwa ya CLI (na kipindi cha taarifa)

## Ratiba

Wiki ya 1-2: Tekeleza huduma ya msingi na utambuzi wa aina
Wiki ya 3-4: Ongeza uundaji wa maelezo na uunganisho
Wiki ya 5: Majaribio na maandishi
Wiki ya 6: Ubadilishaji wa CLI na uhamishaji

## Maswali ya Wazi

Je, huduma inapaswa kusaidia muundo wa ziada wa data (e.g., Parquet, Avro)?
Je, ukubwa wa juu wa sampuli kwa uchambuzi unapaswa kuwa gani?
Je, matokeo ya uchunguzi yanapaswa kuhifadhiwa kwa ombi zinazorudia?
Huduma inapaswa kushughulikia hali ya muundo mwingi vipi?
Je, kitambulisho cha ombi (prompt IDs) vinaweza kupangwa kama vigezo vya huduma?

## Marejeleo

[Maelezo ya Muundo wa Data](structured-data-descriptor.md)
[Maandishi ya Kupakua Data Imeundwa](structured-data.md)
`tg-load-structured-data` utekelezaji: `trustgraph-cli/trustgraph/cli/load_structured_data.py`
