# Derekezi Universal ya Hati

## Mada

Derekezi universal ya hati inayotumiwa na `unstructured` — ingiza aina yoyote ya hati inayotumika kupitia huduma moja, pamoja na taarifa kamili kuhusu chanzo na ushirikiano na mtaalamu wa maktaba, huku ikiandika nafasi za asili kama metadata ya grafu ya maarifa kwa ufuatiliaji kamili.

## Tatizo

Sasa, derekezi ya TrustGraph inalenga tu hati za PDF. Kuunga mkono aina zingine (DOCX, XLSX, HTML, Markdown, maandishi safi, PPTX, n.k.) inahitaji ama kuandika derekezi mpya kwa kila aina au kutumia maktaba ya uondoaji wa universal. Kila aina ina muundo tofauti — baadhi zinategemea kurasa, huku zingine hazitegemei — na mnyororo wa chanzo lazima urekodize ambako kila sehemu ya maandishi iliyopatikana ilitoka kwenye hati asili.

## Mbinu

### Maktaba: `unstructured`

Tumia `unstructured.partition.auto.partition()` ambayo hugundua kiotomatiki aina kutoka kwa mime type au upanuzi wa faili na huondoa vipengele vilivyopangwa (Kichwa, Nakala, Jedwali, Kipengele cha Orodha, n.k.). Kila kipengele kina metadata, pamoja na:

- `page_number` (kwa aina zinazotumia kurasa kama vile PDF, PPTX)
- `element_id` (ya kipekee kwa kila kipengele)
- `coordinates` (sanduku la mipaka kwa PDFs)
- `text` (maandishi yaliyopatikana)
- `category` (aina ya kipengele: Kichwa, Nakala, Jedwali, n.k.)

### Aina za Vipengele

`unstructured` huondoa vipengele vilivyopangwa kutoka kwenye hati. Kila kipengele kina aina na metadata inayohusiana:

**Vipengele vya maandishi:**
- `Title` — vichwa vya sehemu
- `NarrativeText` — aya za mwili
- `ListItem` — vipengele vya orodha (pointi/nambari)
- `Header`, `Footer` — vichwa/miguu ya ukurasa
- `FigureCaption` — maandishi ya maelezo kwa picha/akili
- `Formula` — maandishi ya hesabu
- `Address`, `EmailAddress` — maelezo ya mawasiliano
- `CodeSnippet` — vipengele vya nambari (kutoka kwenye maandishi)

**Jedwali:**
- `Table` — data iliyopangwa katika meza. `unstructured` hutoa `element.text` (maandishi safi) na `element.metadata.text_as_html` (HTML kamili ya `<table>` pamoja na mistari, safu, na vichwa). Kwa aina zilizo na muundo wazi wa jedwali (DOCX, XLSX, HTML), uondoaji una uaminifu mkubwa. Kwa PDFs, ugunduzi wa jedwali hutegemea mkakati wa `hi_res` pamoja na uchambuzi wa muundo.

**Picha:**
- `Image` — picha zilizowekwa ndani ambazo hugunduliwa kupitia uchambuzi wa muundo (inahitaji mkakati wa `hi_res`). Pamoja na `extract_image_block_to_payload=True`, inarudisha data ya picha kama base64 katika `element.metadata.image_base64`. Maandishi ya maandishi kutoka kwenye picha yanapatikana katika `element.text`.

### Usimamizi wa Jedwali

Jedwali hupewa umuhimu wa pekee. Pale derekezi inapokutana na kipengele cha `Table`, inahifadhi muundo wa HTML badala ya kuirekebisha kuwa maandishi safi. Hii inatoa derekezi ya LLM (Large Language Model) ya chini ya uondoaji ya taarifa bora kwa kuchimbua maarifa kutoka kwa data iliyopangwa.

Maandishi ya ukurasa/sehemu yanakusanywa kama ifuatavyo:
- Vipengele vya maandishi: maandishi safi, yakiunganishwa na mistari mipya
- Vipengele vya jedwali: alama ya HTML ya `<table>` kutoka `text_as_html`, ambayo inazingatiwa ili derekezi ya LLM iweze kutofautisha jedwali na maandishi.

Kwa mfano, ukurasa wenye kichwa, aya, na jedwali hutengenezwa kama ifuatavyo:

```
Muhtasari wa Kifedha

Mapato yaliongezeka kwa 15% mwaka jana kutokana na matumizi ya kampuni.

<table>
<tr><th>Kila Mara</th><th>Mapato</th><th>Kukua</th></tr>
<tr><td>Q1</td><td>$12M</td><td>12%</td></tr>
<tr><td>Q2</td><td>$14M</td><td>17%</td></tr>
</table>
```

Hii inahifadhi muundo wa jedwali wakati wa kuunganisha na katika mlolongo wa uondoaji, ambapo derekezi ya LLM inaweza kuchimbua uhusiano moja kwa moja kutoka kwa seli zilizopangwa badala ya kujaribu nadharia kuhusu ulinganishi wa safu kutoka kwa umbali.

### Usimamizi wa Picha

Picha zinaondolewa na kuhifadhiwa katika mtaalamu wa maktaba kama hati ndogo zenye `document_type="image"` na `urn:image:{uuid}` ID. Inapata triples za chanzo pamoja na aina `tg:Image`, ambazo zinahusiana na ukurasa/sehemu yake ya asili kupitia `prov:wasDerivedFrom`. Metadata ya picha (nafasi, vipimo, `element_id`) inarekodiwa katika chanzo.

**Muhimu, picha HAZIPI tokelezwa kama matokeo ya `TextDocument`.** Inahifadhiwa tu — haitumwi kwa derekezi ya sehemu au mlolongo wowote wa kuchakata maandishi. Hii ni kwa makusudi:

1. Bado hakuna mlolongo wa kuchakata picha (kuunganisha na modeli ya maono ni kazi ya baadaye)
2. Kupeleka data ya picha au vipande vya maandishi kutoka kwa OCR kwenye mlolongo wa uondoaji wa maandishi kutatoa triples za KG (Knowledge Graph) zisizo na maana.

Picha pia hazijumuishwi katika maandishi ya ukurasa — vipengele vyovyote vya `Image` hupita bila kutambuliwa wakati wa kuunganisha maandishi ya kipengele kwa ukurasa/sehemu. Mnyororo wa chanzo unaandika kwamba picha zipo na zilipoonekana katika hati, hivyo zinaweza kuchukuliwa na mlolongo wa baadaye wa kuchakata picha bila kuhitajika kurejesha hati.

#### Kazi za Baadaye

- Tuma vitu vya `tg:Image` kwa modeli ya maono kwa ajili ya maelezo, tafsiri ya michoro, au uondoaji wa data ya chati.
- Hifadhi maelezo ya picha kama hati ndogo za maandishi ambazo hufika katika mlolongo wa kawaida wa kuunganisha/uondoaji.
- Unganisha maarifa yaliyopatikana nyuma kwenye picha za asili kupitia chanzo.

### Mikakati ya Sehemu

Kwa aina zinazotumia kurasa (PDF, PPTX, XLSX), vipengele daima huunganishwa kwa ukurasa/slide/karatasi kwanza. Kwa aina ambazo hazitumii kurasa (DOCX, HTML, Markdown, n.k.), derekezi inahitaji mkakati wa kuainisha hati katika sehemu. Hii inaweza kubadilishwa wakati wa utendaji kupitia `--section-strategy`.

Kila mkakati ni kazi ya kuunganisha juu ya orodha ya vipengele vya `unstructured`. Matokeo ni orodha ya vikundi vya vipengele; mlolongo mwingine (kuunganisha maandishi, kuhifadhi katika mtaalamu wa maktaba, chanzo, matokeo ya `TextDocument`) ni sawa bila kujali mkakati.

#### `whole-document` (chaguo-msingi)

Tuma hati nzima kama sehemu moja. Acha derekezi ya chini ya uunganisha iweze kuainisha yote.

- Mbinu rahisi, kiwango kizuri
- Inaweza kuzalisha `TextDocument` kubwa kwa faili kubwa, lakini derekezi ya chini ya uunganisha inaweza kushughulikia hili
- Ni bora wakati unataka muktadha mwingi kwa kila sehemu

#### `heading`

Aina katika vipengele vya vichwa (`Title`). Kila sehemu ni kichwa na yote yaliyo yafuatayo hadi kichwa cha kiwango sawa au cha juu. Vichwa vilivyoingiliana huunda sehemu zilizounganishwa.

- Inazalisha vitengo vya mada ambavyo vina maana
- Inafaa kwa hati zilizopangwa (ripoti, manwal, vipimo)
- Inatoa kwa derekezi ya LLM muktadha wa vichwa pamoja na maudhui
- Inarudi kwenye `whole-document` ikiwa hakuna vichwa vilivyopatikana

#### `element-type`

Aina wakati aina ya kipengele inabadilika sana — haswa, anza sehemu mpya katika mabadiliko kati ya maandishi na jedwali. Vipengele vilivyofuata vya aina moja (maandishi, maandishi, maandishi au jedwali, jedwali) huendelea kuunganishwa.

- Inahifadhi jedwali kama sehemu zilizojitenga
- Ni nzuri kwa hati zilizo na maudhui mchanganyiko (ripoti na meza za data)
- Jedwali hupata umakini maalum wa uondoaji

#### `count`

Unganisha idadi fulani ya vipengele kwa kila sehemu. Inaweza kubadilishwa kupitia `--section-element-count` (chaguo-msingi: 20).

- Rahisi na yanayotabirika
- Hayazingati muundo wa hati
- Ni muhimu kama njia mbadala au kwa majaribio

#### `size`

Unganisha vipengele hadi kikomo cha herufi kifikie, kisha anza sehemu mpya. Inazingatia mipaka ya kipengele — haigawisi katikati ya kipengele. Inaweza kubadilishwa kupitia `--section-max-size` (chaguo-msingi: 4000 herufi).

- Inazalisha ukubwa wa sehemu unaozingatia
- Inazingatia mipaka ya kipengele (tofauti na derekezi ya chini ya uunganisha)
- Ni suluhisho bora kati ya muundo na udhibiti wa ukubwa
- Ikiwa kipengele kimoja kinazidi kikomo, kinakuwa sehemu yake mwenyewe

#### Mwingiliano na Aina Zinazotumia Kurasa

Kwa aina zinazotumia kurasa, uunganishaji wa ukurasa daima huwapa kipaumbele. Mikakati ya sehemu inaweza kutumika *ndani* ya ukurasa ikiwa ukurasa ni kubwa sana (kwa mfano, ukurasa wa PDF wenye jedwali kubwa sana), hii inadhibitiwa na `--section-within-pages` (chaguo-msingi: false). Wakati chaguo hili limezimwa, kila ukurasa ni sehemu moja bila kujali ukubwa wake.

### Ugunduzi wa Aina

Derekezi inahitaji kujua aina ya hati ili iweze kuipitisha kwa `partition()` ya `unstructured`. Kuna njia mbili:

- **Njia ya mtaalamu wa maktaba** (`document_id` imewekwa): kwanza pata metadata ya hati kutoka kwa mtaalamu wa maktaba — hii inatuonyesha `kind` (aina) ambayo ilirekodiwa wakati wa kupakia. Kisha pata maudhui ya hati. Hii inahitaji simu mbili za mtaalamu wa maktaba, lakini kupata metadata ni rahisi.
- **Njia ya ndani** (utangamano wa nyuma, `data` imewekwa): hakuna metadata inayopatikana kwenye ujumbe. Tumia `python-magic` kuchunguza aina kutoka kwa bytes za maudhui kama njia mbadala.

Hakuna mabadiliko yanayohitajika kwenye schema ya `Document` — mtaalamu wa maktaba hurejesha aina ya mime.

### Muundo

Huduma moja ya `universal-decoder` ambayo:

1. Inapokea ujumbe wa `Document` (ndani au kupitia marejeleo ya mtaalamu wa maktaba)
2. Ikiwa ni njia ya mtaalamu wa maktaba: pata metadata ya hati (pata aina), kisha pata maudhui. Ikiwa ni njia ya ndani: chunguza aina kutoka kwa bytes za maudhui.
3. Inaitisha `partition()` ili kuondoa vipengele
4. Inaainisha vipengele: kwa ukurasa kwa aina zinazotumia kurasa, kwa mkakati wa sehemu uliopangwa kwa aina ambazo hazitumii kurasa
5. Kwa kila ukurasa/sehemu:
   - Inazalisha `urn:page:{uuid}` au `urn:section:{uuid}` ID
   - Inaunganisha maandishi ya ukurasa: maandishi safi, jedwali kama HTML, picha zinarudiwa
   - Inahesabu nafasi za herufi kwa kila kipengele ndani ya maandishi ya ukurasa
   - Inahifadhi katika mtaalamu wa maktaba kama hati ndogo
   - Inazalisha triples za chanzo na metadata ya nafasi
   - Inatuma `TextDocument` chini ya uunganishaji
6. Kwa kila kipengele cha picha:
   - Inazalisha `urn:image:{uuid}` ID
   - Inahifadhi data ya picha katika mtaalamu wa maktaba kama hati ndogo
   - Inazalisha triples za chanzo (zinawekwa tu, hazitumwi chini)

### Usanidi wa Huduma

Majadiliano ya mstari wa amri:

```
--strategy              Mbinu ya kuainisha: auto, hi_res, fast (chaguo-msingi: auto)
--languages             Orodha ya msimbo wa lugha inayotumika kwa OCR (chaguo-msingi: eng)
--section-strategy      Mbinu ya kuunganisha sehemu: whole-document, heading, element-type,
                        count, size (chaguo-msingi: whole-document)
--section-element-count Vipengele kwa kila sehemu kwa mbinu ya 'count' (chaguo-msingi: 20)
--section-max-size      Kikomo cha herufi kwa kila sehemu kwa mbinu ya 'size' (chaguo-msingi: 4000)
--section-within-pages  Tumia mkakati wa sehemu ndani ya ukurasa pia (chaguo-msingi: false)
```

Pia, majadiliano ya kawaida ya `FlowProcessor` na folyo ya mtaalamu wa maktaba.

### Ushirikiano wa Flow

Derekezi ya universal huishia katika nafasi sawa ya mlolongo wa uendeshaji kama derekezi ya PDF iliyopo:

```
Hati → [derekezi-universal] → TextDocument → [derekezi-ya-kuunganisha] → Sehemu → ...
```

Inajisajili:
- Mtumiaji wa `input` (schema ya Hati)
- Mtayarishaji wa `output` (schema ya TextDocument)
- Mtayarishaji wa `triples` (schema ya Triples)
- Ombi/jibu la mtaalamu wa maktaba (kwa kupata na kuhifadhi hati ndogo)

### Uwekaji

- Chini mpya: `trustgraph-flow-universal-decoder`
- Utendakazi: `unstructured[all-docs]` (inajumuisha PDF, DOCX, PPTX, n.k.)
- Inaweza kuendeshwa pamoja au kubadilisha derekezi ya PDF iliyopo kulingana na usanidi wa mlolongo
- Derekezi ya PDF iliyopo inabaki inapatikana kwa mazingira ambapo utendakazi wa `unstructured` ni mzito sana.

### Mabadiliko

| Komponenti                    | Mabadiliko                                         |
|------------------------------|-------------------------------------------------|
| `provenance/namespaces.py`   | Ongeza `TG_SECTION_TYPE`, `TG_IMAGE_TYPE`, `TG_ELEMENT_TYPES`, `TG_TABLE_COUNT`, `TG_IMAGE_COUNT` |
| `provenance/triples.py`      | Ongeza `mime_type`, `element_types`, `table_count`, `image_count` kwa `kwargs` |
| `provenance/__init__.py`     | Exporti mara kwa mara                               |
| Mpya: `decoding/universal/`   | Moduli mpya ya derekezi                            |
| `setup.cfg` / `pyproject`    | Ongeza utendakazi wa `unstructured[all-docs]`         |
| Docker                       | Pata picha mpya ya chumba                            |
| Maelezo ya mlolongo             | Unganisha derekezi-universal kama input ya hati        |

### Mambo ambayo Hayabadiliki

- Derekezi ya kuchakata (Inapokea `TextDocument`, inafanya kama ilivyokuwa)
- Vitu vya uondoaji (Inapokea `Sehemu`, inafanya kama ilivyokuwa)
- Schema ya `Document` — inahitaji maelezo yafuatayo:
  - `file_name`: Jina la faili.
  - `file_type`: Aina ya faili.