# Mfumo wa Uwekaji Njia (Flow Blueprint) - Vigezo Vinavyoweza Kubadilishwa - Maelezo ya Kiufundi

## Maelezo

Maelezo haya yanaeleza utekelezaji wa vigezo vinavyoweza kubadilishwa kwa mifumo ya uwekaji njia (flow blueprints) katika TrustGraph. Vigezo huruhusu watumiaji kubadilisha vigezo vya kichakato (processor) wakati wa kuanzisha mfumo wa uwekaji njia kwa kutoa maadili ambayo hubadilisha nafasi za vigezo katika ufafanuzi wa mfumo wa uwekaji njia.

<<<<<<< HEAD
Vigezo hufanya kazi kupitia ubadilishaji wa vigezo vya kishabaha katika vigezo vya kichakato, sawa na jinsi vigezo vya `{id}` na `{class}` hufanya kazi, lakini kwa maadili ambayo hutolewa na mtumiaji.
=======
Vigezo hufanya kazi kupitia ubadilishaji wa vigezo vya kishabaha katika vigezo vya kichakato, sawa na jinsi vigezo `{id}` na `{class}` hufanya kazi, lakini kwa maadili ambayo hutolewa na mtumiaji.
>>>>>>> 82edf2d (New md files from RunPod)

Uunganishaji huu unaunga mkono matumizi manne makuu:

1. **Uchaguzi wa Mfumo**: Kuruhusu watumiaji kuchagua mifumo tofauti ya LLM (e.g., `gemma3:8b`, `gpt-4`, `claude-3`) kwa vichakato.
2. **Uwekaji Njia wa Rasilimali**: Kurekebisha vigezo vya kichakato kama vile saizi za sehemu, saizi za kundi, na mipaka ya utendaji.
3. **Urekebishaji wa Tabia**: Kubadilisha tabia ya kichakato kupitia vigezo kama vile halijoto, max-tokens, au viwango vya urejesho.
4. **Vigezo Maalum ya Mazingira**: Kusanidi sehemu za mwisho, funguo za API, au anwani za mtandao (URLs) maalum kwa eneo kwa kila uwekaji.

## Lengo

**Uwekaji Njia wa Kichakato Unaoweza Kubadilishwa**: Kuruhusu uwekaji njia wa vigezo vya kichakato wakati wa utendaji kupitia ubadilishaji wa vigezo.
**Uthibitisho wa Vigezo**: Kutoa ukaguzi wa aina na uthibitisho wa vigezo wakati wa kuanzisha mfumo wa uwekaji njia.
**Maadili ya Msingi**: Kusaidia maadili ya msingi ambayo yanafaa lakini kuruhusu ubadilishaji kwa watumiaji wa hali ya juu.
**Ubadilishaji wa Kishabaha**: Kubadilisha nafasi za vigezo katika vigezo vya kichakato kwa urahisi.
<<<<<<< HEAD
**Uunganishaji wa UI**: Kuruhusu uingizaji wa vigezo kupitia interfaces za API na UI.
=======
**Uunganisho wa UI**: Kuruhusu uingizaji wa vigezo kupitia interfaces za API na UI.
>>>>>>> 82edf2d (New md files from RunPod)
**Usalama wa Aina**: Kuhakikisha kwamba aina za vigezo zinafanana na aina zilizotarajiwa za vigezo vya kichakato.
**Ufafanuzi**: Mifumo ya vigezo inayojieleza yenyewe ndani ya ufafanuzi wa mifumo ya uwekaji njia.
**Ulinganifu na Mifumo ya Zamani**: Kuhifadhi ulinganifu na mifumo ya uwekaji njia iliyopo ambayo haitumii vigezo.

## Asili

<<<<<<< HEAD
Mifumo ya uwekaji njia katika TrustGraph sasa inaunga mkono vigezo vya kichakato ambavyo yanaweza kuwa na maadili thabiti au nafasi za vigezo. Hii huunda fursa ya urekebishaji wakati wa utendaji.
=======
Mifumo ya uwekaji njia katika TrustGraph sasa inasaidia vigezo vya kichakato ambavyo yanaweza kuwa na maadili thabiti au nafasi za vigezo. Hii huunda fursa ya urekebishaji wakati wa utendaji.
>>>>>>> 82edf2d (New md files from RunPod)

Vigezo vya kichakato vya sasa vinaunga mkono:
Maadili thabiti: `"model": "gemma3:12b"`
Nafasi za vigezo: `"model": "gemma3:{model-size}"`

Maelezo haya yanaeleza jinsi vigezo:
Yanavyoonyeshwa katika ufafanuzi wa mifumo ya uwekaji njia
Yanavyothibitishwa wakati wa kuanzisha mifumo ya uwekaji njia
Yanavyobadilishwa katika vigezo vya kichakato
Yanavyoonyeshwa kupitia API na UI

Kwa kutumia vigezo vya kichakato, TrustGraph inaweza:
Kupunguza uduzi wa mifumo ya uwekaji njia kwa kutumia vigezo kwa tofauti
Kuruhusu watumiaji kurekebisha tabia ya kichakato bila kubadilisha ufafanuzi
Kusaidia usanidi maalum wa mazingira kupitia maadili ya vigezo
Kuhifadhi usalama wa aina kupitia uthibitisho wa shabaha ya vigezo

<<<<<<< HEAD
## Ubunifu wa Kiufundi

### Muundo

Mfumo wa vigezo vinavyoweza kubadilishwa unahitaji vipengele vifuatavyo vya kiufundi:

1. **Ufafanuzi wa Shabaha ya Vigezo**
   Ufafanuzi wa vigezo unaotegemea shabaha ya JSON ndani ya metadata ya mfumo wa uwekaji njia.
=======
## Muundo wa Kiufundi

### Usanifu

Mfumo wa vigezo unaoweza kubadilishwa unahitaji vipengele vifuatavyo vya kiufundi:

1. **Ufafanuzi wa Shabaha ya Vigezo**
   Ufafanuzi wa vigezo unaotegemea kwenye JSON Schema ndani ya metadata ya mfumo wa uwekaji njia.
>>>>>>> 82edf2d (New md files from RunPod)
   Ufafanuzi wa aina ikiwa ni pamoja na aina ya maandishi, nambari, ya kweli, enum, na aina ya kitu.
   Kanuni za uthibitisho ikiwa ni pamoja na maadili ya chini/juu, mifumo, na mashamba yanayohitajika.

   Moduli: trustgraph-flow/trustgraph/flow/definition.py

<<<<<<< HEAD
2. **Injini ya Ufumbuzi wa Vigezo**
   Uthibitisho wa vigezo wakati wa utendaji dhidi ya shabaha.
   Matumizi ya maadili ya msingi kwa vigezo ambavyo havijatolewa.
   Uingizaji wa vigezo katika muktadha wa utendaji wa mfumo wa uwekaji njia.
=======
2. **Injini ya Urekebishaji wa Vigezo**
   Uthibitisho wa vigezo wakati wa utendaji dhidi ya shabaha.
   Matumizi ya maadili ya msingi kwa vigezo ambavyo havijatolewa.
   Uingizaji wa vigezo katika muktadha wa utekelezaji wa mfumo wa uwekaji njia.
>>>>>>> 82edf2d (New md files from RunPod)
   Marekebisho na ubadilishaji wa aina kama inavyohitajika.

   Moduli: trustgraph-flow/trustgraph/flow/parameter_resolver.py

<<<<<<< HEAD
3. **Uunganishaji wa Hifadhi ya Vigezo**
=======
3. **Uunganisho wa Hifadhi ya Vigezo**
>>>>>>> 82edf2d (New md files from RunPod)
   Kupata ufafanuzi wa vigezo kutoka kwa duka la shabaha/usanidi.
   Kuhifadhi ufafanuzi wa vigezo unaotumika mara kwa mara.
   Uthibitisho dhidi ya shabaha zilizohifadhiwa katikati.

   Moduli: trustgraph-flow/trustgraph/flow/parameter_store.py

4. **Viendelezi vya Kuanzisha Mfumo wa Uwekaji Njia**
   Viendelezi vya API kukubali maadili ya vigezo wakati wa kuanzisha mfumo wa uwekaji njia.
<<<<<<< HEAD
   Ufumbuzi wa ramani ya vigezo (majina ya mifumo ya uwekaji njia hadi majina ya ufafanuzi).
=======
   Urekebishaji wa ramani ya vigezo (majina ya mifumo kwa majina ya ufafanuzi).
>>>>>>> 82edf2d (New md files from RunPod)
   Usimamizi wa makosa kwa mchanganyiko usiofaa wa vigezo.

   Moduli: trustgraph-flow/trustgraph/flow/launcher.py

5. **Fomu za Vigezo za UI**
<<<<<<< HEAD
   Uundaji wa fomu ya kiotomatiki kutoka kwa metadata ya vigezo ya mfumo wa uwekaji njia.
   Kuonyesha vigezo kwa utaratibu kwa kutumia `order`.
   Laha za vigezo za maelezo kwa kutumia `description`.
   Uthibitisho wa ingizo dhidi ya ufafanuzi wa aina ya vigezo.
   Vigezo vilivyosanidiwa na vipuli.
=======
   Uzalishaji wa fomu ya kiotomatiki kutoka kwa metadata ya vigezo ya mfumo wa uwekaji njia.
   Kuonyesha vigezo kwa utaratibu kwa kutumia `order`.
   Laha za vigezo za maelezo kwa kutumia `description`.
   Uthibitisho wa uingizaji dhidi ya ufafanuzi wa aina ya vigezo.
   Vipangilio na vipuli vya vigezo.
>>>>>>> 82edf2d (New md files from RunPod)

   Moduli: trustgraph-ui/components/flow-parameters/

### Mifano ya Data

#### Ufafanuzi wa Vigezo (Imehifadhiwa katika Shabaha/Usanidi)
<<<<<<< HEAD
Ufafanuzi wa vigezo unaotegemea shabaha ya JSON ndani ya metadata ya mfumo wa uwekaji njia.
Ufafanuzi wa aina ikiwa ni pamoja na aina ya maandishi, nambari, ya kweli, enum, na aina ya kitu.
Kanuni za uthibitisho ikiwa ni pamoja na maadili ya chini/juu, mifumo, na mashamba yanayohitajika.
=======

Ufafanuzi wa vigezo umehifadhiwa ndani ya duka la shabaha/usanidi.

>>>>>>> 82edf2d (New md files from RunPod)
```json
{
  "llm-model": {
    "type": "string",
    "description": "LLM model to use",
    "default": "gpt-4",
    "enum": [
      {
        "id": "gpt-4",
        "description": "OpenAI GPT-4 (Most Capable)"
      },
      {
        "id": "gpt-3.5-turbo",
        "description": "OpenAI GPT-3.5 Turbo (Fast & Efficient)"
      },
      {
        "id": "claude-3",
        "description": "Anthropic Claude 3 (Thoughtful & Safe)"
      },
      {
        "id": "gemma3:8b",
        "description": "Google Gemma 3 8B (Open Source)"
      }
    ],
    "required": false
  },
  "model-size": {
    "type": "string",
    "description": "Model size variant",
    "default": "8b",
    "enum": ["2b", "8b", "12b", "70b"],
    "required": false
  },
  "temperature": {
    "type": "number",
    "description": "Model temperature for generation",
    "default": 0.7,
    "minimum": 0.0,
    "maximum": 2.0,
    "required": false
  },
  "chunk-size": {
    "type": "integer",
    "description": "Document chunk size",
    "default": 512,
    "minimum": 128,
    "maximum": 2048,
    "required": false
  }
}
```

#### Mpango wa Mchakato na Marejeleo ya Vigezo

Mipango ya mchakato inaelezea metadata ya vigezo pamoja na marejeleo ya aina, maelezo, na mpangilio:

```json
{
  "flow_class": "document-analysis",
  "parameters": {
    "llm-model": {
      "type": "llm-model",
      "description": "Primary LLM model for text completion",
      "order": 1
    },
    "llm-rag-model": {
      "type": "llm-model",
      "description": "LLM model for RAG operations",
      "order": 2,
      "advanced": true,
      "controlled-by": "llm-model"
    },
    "llm-temperature": {
      "type": "temperature",
      "description": "Generation temperature for creativity control",
      "order": 3,
      "advanced": true
    },
    "chunk-size": {
      "type": "chunk-size",
      "description": "Document chunk size for processing",
      "order": 4,
      "advanced": true
    },
    "chunk-overlap": {
      "type": "integer",
      "description": "Overlap between document chunks",
      "order": 5,
      "advanced": true,
      "controlled-by": "chunk-size"
    }
  },
  "class": {
    "text-completion:{class}": {
      "request": "non-persistent://tg/request/text-completion:{class}",
      "response": "non-persistent://tg/response/text-completion:{class}",
      "parameters": {
        "model": "{llm-model}",
        "temperature": "{llm-temperature}"
      }
    },
    "rag-completion:{class}": {
      "request": "non-persistent://tg/request/rag-completion:{class}",
      "response": "non-persistent://tg/response/rag-completion:{class}",
      "parameters": {
        "model": "{llm-rag-model}",
        "temperature": "{llm-temperature}"
      }
    }
  },
  "flow": {
    "chunker:{id}": {
      "input": "persistent://tg/flow/chunk:{id}",
      "output": "persistent://tg/flow/chunk-load:{id}",
      "parameters": {
        "chunk_size": "{chunk-size}",
        "chunk_overlap": "{chunk-overlap}"
      }
    }
  }
}
```

<<<<<<< HEAD
Sehemu ya `parameters` inaeleza jina la kila parameter (funguo) inayohusiana na mtiririko, na inaunganisha na vitu vya metadata ya parameter ambavyo vina:
`type`: Rejea kwa ufafanuzi wa parameter uliotolewa kwa njia ya kati (k.m., "llm-model")
`description`: Maelezo ambayo yanaweza kusomwa na binadamu kwa ajili ya kuonyeshwa kwenye kiolesura (UI)
`order`: Mpangilio wa kuonyeshwa wa parameter katika fomu (nambari ndogo huonyeshwa kwanza)
`advanced` (hiari): Bendera ya boolean inayoelezea ikiwa hii ni parameter ya hali ya juu (ya kawaida: false). Ikiwa imewekwa kuwa "true", kiolesura kinaweza kuficha parameter hii kwa chagu ku, au kuiweka katika sehemu ya "Advanced"
`controlled-by` (hiari): Jina la parameter nyingine ambayo inadhibiti thamani ya parameter hii wakati katika hali rahisi. Ikiwa imeingizwa, parameter hii inaruhusu thamani yake kutoka kwa parameter inayodhibiti, isipokuwa ikiwa imebadilishwa wazi.

Mbinu hii inaruhusu:
Ufafanuzi wa aina ya parameter unaoweza kutumika tena katika mipangilio mingi.
Usimamizi na uthibitishaji wa aina ya parameter katika eneo moja.
Maelezo na mpangilio wa parameter unaohusiana na kila mtiririko.
Uzoefu bora wa kiolesura (UI) kwa kutumia fomu za parameter zenye maelezo.
Uthibitishaji thabiti wa parameter katika mitiririko yote.
=======
Sehemu ya `parameters` inaeleza jina la parameter (funguo) inayohusiana na mtiririko, na inaunganisha na vitu vya metadata ya parameter ambavyo vina:
`type`: Rejea kwa ufafanuzi wa parameter uliotolewa kwa njia ya kati (k.m., "llm-model")
`description`: Maelezo ambayo yanaweza kusomwa na binadamu kwa ajili ya kuonyeshwa kwenye kiolesura (UI)
`order`: Mfululizo wa kuonyeshwa kwa fomu za parameter (nambari ndogo huonyeshwa kwanza)
`advanced` (hiari): Bendera ya Boolean inayoelezea ikiwa hii ni parameter ya hali ya juu (ya kawaida: false). Ikiwa imewekwa kuwa "true", kiolesura kinaweza kuficha parameter hii kwa chaguльку au kuiweka katika sehemu ya "Advanced"
`controlled-by` (hiari): Jina la parameter nyingine ambayo inadhibiti thamani ya parameter hii wakati katika hali rahisi. Ikiwa imeingizwa, parameter hii inaruhusu thamani yake kutoka kwa parameter inayodhibiti, isipokuwa ikiwa imebadilishwa wazi.

Mbinu hii inaruhusu:
Ufafanuzi wa aina ya parameter unaoweza kutumika tena katika mipangilio mingi ya mtiririko.
Usimamizi na uthibitishaji wa aina ya parameter unaozingatia.
Maelezo na mpangilio wa parameter unaozingatia mtiririko.
Uzoefu bora wa kiolesura (UI) na fomu za parameter zenye maelezo.
Uthibitishaji thabiti wa parameter katika mitiririko.
>>>>>>> 82edf2d (New md files from RunPod)
Kuongeza kwa urahisi aina mpya za parameter za kawaida.
Kiolesura kilichorahisishwa na mgawanyiko wa hali ya msingi/ya hali ya juu.
Urithi wa thamani ya parameter kwa mipangilio inayohusiana.

#### Ombi la Uzinduzi wa Mtiririko

API ya uzinduzi wa mtiririko inakubali parameter kwa kutumia majina ya parameter ya mtiririko:

```json
{
  "flow_class": "document-analysis",
  "flow_id": "customer-A-flow",
  "parameters": {
    "llm-model": "claude-3",
    "llm-temperature": 0.5,
    "chunk-size": 1024
  }
}
```

Kumbuka: Katika mfano huu, `llm-rag-model` haitoa maelezo wazi lakini itapokea thamani "claude-3" kutoka kwa `llm-model` kutokana na uhusiano wake wa `controlled-by`. Vile vile, `chunk-overlap` inaweza kupokea thamani iliyohitajiwa kulingana na `chunk-size`.

Mfumo utafanya:
1. Kuchukua metadata ya vigezo kutoka ufafanuzi wa mpango (blueprint).
2. Kuunganisha majina ya vigezo vya mpango na ufafanuzi wao wa aina (e.g., `llm-model` → `llm-model` aina).
3. Kutatua uhusiano wa "controlled-by" (e.g., `llm-rag-model` inarithi kutoka kwa `llm-model`).
<<<<<<< HEAD
4. Kuthibitisha maadili yaliyotolewa na mtumiaji na yaliyorithiwa dhidi ya ufafanuzi wa aina ya vigezo.
=======
4. Kuthibitisha maadili yaliyotolewa na mtumiaji na yaliyorithishwa dhidi ya ufafanuzi wa aina ya vigezo.
>>>>>>> 82edf2d (New md files from RunPod)
5. Kubadilisha maadili yaliyotatuliwa katika vigezo vya kichakataji (processor) wakati wa kuunda mpango.

### Maelezo ya Utendaji

#### Mchakato wa Kutatua Vigezo

Wakati mpango unaanza, mfumo hufanya hatua zifuatazo za kutatua vigezo:

1. **Kupakia Mpango (Flow Blueprint)**: Pakia ufafanuzi wa mpango na uchukue metadata ya vigezo.
<<<<<<< HEAD
2. **Kuchukua Metadata**: Chukua `type`, `description`, `order`, `advanced`, na `controlled-by` kwa kila kiparamu kilichoainishwa katika sehemu ya `parameters` ya ufafanuzi wa mpango.
3. **Kutafuta Ufafanuzi wa Aina**: Kwa kila kiparamu katika ufafanuzi wa mpango:
   Pata ufafanuzi wa aina ya kiparamu kutoka kwa duka la schema/config kwa kutumia sehemu ya `type`.
   Ufafanuzi wa aina huhifadhiwa na aina "parameter-type" katika mfumo wa config.
   Kila ufafanuzi wa aina una schema ya kiparamu, thamani ya chaguo-msingi, na sheria za uthibitishaji.
4. **Kutatua Thamani ya Chaguo-msingi**:
   Kwa kila kiparamu kilichoainishwa katika ufafanuzi wa mpango:
     Angalia ikiwa mtumiaji ametoa thamani kwa kiparamu hiki.
     Ikiwa hakuna thamani iliyotolewa na mtumiaji, tumia thamani ya `default` kutoka kwa ufafanuzi wa aina ya kiparamu.
     Unda ramani kamili ya vigezo inayojumuisha maadili yaliyotolewa na mtumiaji na maadili chaguo-msingi.
5. **Kutatua Ufuataji wa Vigezo** (uhusiano wa "controlled-by"):
   Kwa vigezo vyenye sehemu ya `controlled-by`, angalia ikiwa thamani ilitolewa wazi.
   Ikiwa hakuna thamani iliyotolewa wazi, arithia thamani kutoka kwa kiparamu kinachodhibiti.
   Ikiwa kiparamu kinachodhibiti pia hakina thamani, tumia chaguo-msingi kutoka kwa ufafanuzi wa aina.
   Hakikisha kuwa hakuna utegemezi wa mzunguko katika uhusiano wa `controlled-by`.
6. **Uthibitishaji**: Thibitisha seti kamili ya vigezo (vile vilivyotolewa na mtumiaji, chaguo-msingi, na vile vilivyorithiwa) dhidi ya ufafanuzi wa aina.
=======
2. **Kuchukua Metadata**: Chukua `type`, `description`, `order`, `advanced`, na `controlled-by` kwa kila kigezo kilichoainishwa katika sehemu ya `parameters` ya ufafanuzi wa mpango.
3. **Kutafuta Ufafanuzi wa Aina**: Kwa kila kigezo katika ufafanuzi wa mpango:
   Pata ufafanuzi wa aina ya kigezo kutoka kwa duka la schema/config kwa kutumia sehemu ya `type`.
   Ufafanuzi wa aina huhifadhiwa na aina "parameter-type" katika mfumo wa config.
   Kila ufafanuzi wa aina una schema ya kigezo, thamani ya chaguo-msingi, na sheria za uthibitishaji.
4. **Kutatua Thamani ya Chaguo-msingi**:
   Kwa kila kigezo kilichoainishwa katika ufafanuzi wa mpango:
     Angalia ikiwa mtumiaji ametoa thamani kwa kigezo hiki.
     Ikiwa hakuna thamani iliyotolewa na mtumiaji, tumia thamani ya `default` kutoka kwa ufafanuzi wa aina ya kigezo.
     Unda ramani kamili ya vigezo inayojumuisha maadili yaliyotolewa na mtumiaji na maadili chaguo-msingi.
5. **Kutatua Ufuasi wa Vigezo** (uhusiano wa "controlled-by"):
   Kwa vigezo vyenye sehemu ya `controlled-by`, angalia ikiwa thamani ilitolewa wazi.
   Ikiwa hakuna thamani iliyotolewa wazi, arithia thamani kutoka kwa kigezo kinachodhibiti.
   Ikiwa kigezo kinachodhibiti pia hakina thamani, tumia chaguo-msingi kutoka kwa ufafanuzi wa aina.
   Hakikisha kuwa hakuna utegemezi wa mzunguko katika uhusiano wa `controlled-by`.
6. **Uthibitishaji**: Thibitisha seti kamili ya vigezo (vile vilivyotolewa na mtumiaji, chaguo-msingi, na vile vilivyorithishwa) dhidi ya ufafanuzi wa aina.
>>>>>>> 82edf2d (New md files from RunPod)
7. **Uhifadhi**: Hifadhi seti kamili ya vigezo yaliyotatuliwa pamoja na mfano wa mpango kwa ajili ya uhakiki.
8. **Ubadilishaji wa Kigezo**: Badilisha nafasi za kigezo katika vigezo vya kichakataji na maadili yaliyotatuliwa.
9. **Uundaji wa Kichakataji**: Unda vichakataji na vigezo vilivyobadilishwa.

**Maelezo Muhimu ya Utendaji:**
<<<<<<< HEAD
Huduma ya mpango INAVYOHITAJI kuchanganya vigezo vilivyotolewa na mtumiaji na chaguo-msingi kutoka kwa ufafanuzi wa aina ya kiparamu.
Seti kamili ya vigezo (ikiwa ni pamoja na chaguo-msingi zilizotumiwa) INAVYOHITAJI kuhifadhiwa na mpango kwa ajili ya ufuatiliaji.
Kutatua vigezo hufanyika wakati wa kuanza kwa mpango, sio wakati wa kuunda kichakataji.
Vigezo muhimu ambavyo havina chaguo-msingi HAVIHUITAJI kusababisha kuanza kwa mpango kushindwa na ujumbe wa kosa wazi.

#### Ufuataji wa Vigezo na "controlled-by"

Sehemu ya `controlled-by` inaruhusu urithi wa thamani ya kiparamu, ambayo ni muhimu sana kwa kurahisisha mazingira ya mtumiaji huku ikiendelea kudumisha uwezekano:

**Mfano wa Matukio:**
Kiparamu cha `llm-model` kinadhibiti mfumo mkuu wa LLM.
Kiparamu cha `llm-rag-model` kina `"controlled-by": "llm-model"`.
Katika hali rahisi, kuweka `llm-model` kwa "gpt-4" huanzisha kiotomatiki `llm-rag-model` kwa "gpt-4" pia.
Katika hali ya juu, watumiaji wanaweza kubadilisha `llm-rag-model` na thamani tofauti.

**Sheria za Kutatua:**
1. Ikiwa kiparamu kina thamani iliyotolewa wazi, tumia thamani hiyo.
2. Ikiwa hakuna thamani iliyotolewa wazi na `controlled-by` imewekwa, tumia thamani ya kiparamu kinachodhibiti.
3. Ikiwa kiparamu kinachodhibiti hakina thamani, rudi kwenye chaguo-msingi kutoka kwa ufafanuzi wa aina.
4. Utendaji wa mzunguko katika uhusiano wa `controlled-by` husababisha kosa la uthibitishaji.

**Tabia ya UI:**
Katika hali ya msingi/rahisi: Vigezo vyenye `controlled-by` vinaweza kufichwa au kuonyeshwa kama visivyo na uwezo wa kubadilishwa na thamani iliyoarithi.
Katika hali ya juu: Vigezo vyote huonyeshwa na vinaweza kusanidiwa kivyake.
Wakati kiparamu kinachodhibiti kinapobadilika, vigezo vinavyotegemea hupatikana kiotomatiki isipokuwa zimebadilishwa wazi.

#### Uunganisho wa Pulsar
=======
Huduma ya mpango INAVYOKWENDA kuchanganya vigezo vilivyotolewa na mtumiaji na chaguo-msingi kutoka kwa ufafanuzi wa aina ya kigezo.
Seti kamili ya vigezo (ikiwa ni pamoja na chaguo-msingi zilizotumiwa) INAVYOKWENDA kuhifadhiwa na mpango kwa ajili ya ufuatiliaji.
Kutatua vigezo hufanyika wakati wa kuanza kwa mpango, sio wakati wa kuunda kichakataji.
Vigezo muhimu ambavyo havina chaguo-msingi HAVI kukatisha kuanza kwa mpango na kuonyesha ujumbe wa kosa wazi.

#### Ufuasi wa Vigezo na "controlled-by"

Sehemu ya `controlled-by` inaruhusu urithi wa thamani ya kigezo, ambayo ni muhimu sana kwa kurahisisha mazingira ya mtumiaji huku ikiendelea kuwezesha utendaji:

**Mfano wa Matukio:**
Kigezo cha `llm-model` kinadhibiti mfumo mkuu wa LLM.
Kigezo cha `llm-rag-model` kina `"controlled-by": "llm-model"`.
Katika hali rahisi, kuweka `llm-model` kwa "gpt-4" hufanya `llm-rag-model` pia iwe "gpt-4" kiotomatiki.
Katika hali ya juu, watumiaji wanaweza kubadilisha `llm-rag-model` na thamani tofauti.

**Sheria za Kutatua:**
1. Ikiwa kigezo kina thamani iliyotolewa wazi, tumia thamani hiyo.
2. Ikiwa hakuna thamani iliyotolewa na `controlled-by` imewekwa, tumia thamani ya kigezo kinachodhibiti.
3. Ikiwa kigezo kinachodhibiti hakina thamani, rudi kwenye chaguo-msingi kutoka kwa ufafanuzi wa aina.
4. Utendaji wa mzunguko katika uhusiano wa `controlled-by` husababisha kosa la uthibitishaji.

**Tabia ya UI:**
Katika hali ya msingi/rahisi: Vigezo vyenye `controlled-by` vinaweza kufichwa au kuonyeshwa kama visivyo na uwezo (read-only) na thamani iliyoorithishwa.
Katika hali ya juu: Vigezo vyote huonyeshwa na vinaweza kusanidiwa kivyake.
Wakati kigezo kinachodhibiti kinapobadilika, vigezo vinavyotegemea hupatikana kiotomatiki isipokuwa ikiwa vimewekwa kuwa visivyo na uwezo.

#### Ujumuishaji wa Pulsar
>>>>>>> 82edf2d (New md files from RunPod)

1. **Operesheni ya Kuanza-Mpango**
   Operesheni ya kuanza-mpango ya Pulsar inahitaji kukubali sehemu ya `parameters` inayojumuisha ramani ya maadili ya vigezo.
   Schema ya ombi la kuanza-mpango ya Pulsar inapaswa kusasishwa ili kujumuisha sehemu ya `parameters` ya hiari.
   Mfano wa ombi:
   ```json
   {
     "flow_class": "document-analysis",
     "flow_id": "customer-A-flow",
     "parameters": {
       "model": "claude-3",
       "size": "12b",
       "temp": 0.5,
       "chunk": 1024
     }
   }
   ```

<<<<<<< HEAD
2. **Operesheni ya Kupata Mtiririko**
   Mfumo wa Pulsar wa jibu la "get-flow" lazima ubadilishwe ili kujumuisha sehemu ya `parameters`
   Hii inaruhusu wateja kupata maadili ya vigezo ambayo yalitumiwa wakati mtiririko ulipoanzishwa.
   Jibu la mfano:
=======
2. **Operesheni ya Kupata Mtiririko (Get-Flow)**
   Mfumo wa Pulsar wa jibu la operesheni ya kupata mtiririko lazima ubadilishwe ili kujumuisha sehemu `parameters`
   Hii inaruhusu wateja kupata maadili ya vigezo ambayo yalitumiwa wakati mtiririko ulipoanzishwa.
   Mfano wa jibu:
>>>>>>> 82edf2d (New md files from RunPod)
   ```json
   {
     "flow_id": "customer-A-flow",
     "flow_class": "document-analysis",
     "status": "running",
     "parameters": {
       "model": "claude-3",
       "size": "12b",
       "temp": 0.5,
       "chunk": 1024
     }
   }
   ```

#### Utendaji wa Huduma ya Mchakato

Huduma ya usanidi wa mchakato (`trustgraph-flow/trustgraph/config/service/flow.py`) inahitaji maboresho yafuatayo:

1. **Kitendaji cha Ufafanuzi wa Vigezo**
   ```python
   async def resolve_parameters(self, flow_class, user_params):
       """
       Resolve parameters by merging user-provided values with defaults.

       Args:
           flow_class: The flow blueprint definition dict
           user_params: User-provided parameters dict

       Returns:
           Complete parameter dict with user values and defaults merged
       """
   ```

   Kazi hii inapaswa:
<<<<<<< HEAD
   Kuchukua metadata ya vigezo kutoka sehemu ya `parameters` ya mpango wa mtiririko
   Kwa kila vigezo, pata ufafanuzi wa aina kutoka kwa hifadhi ya usanidi
   Tumia maadili chaguu kwa vigezo vyovyote ambavyo havijatolewa na mtumiaji
   Kushughulikia uhusiano wa urithi wa `controlled-by`
   Kurudisha seti kamili ya vigezo

2. **Njia Iliyorekebishwa ya `handle_start_flow`**
   Piga `resolve_parameters` baada ya kupakua mpango wa mtiririko
   Tumia seti kamili ya vigezo vilivyomalizika kwa kubadilisha kigezo
   Hifadhi seti kamili ya vigezo (sio tu zile zilizotolewa na mtumiaji) pamoja na mtiririko
   Thibitisha kwamba vigezo vyote muhimu vina maadili

3. **Uchukuzi wa Aina ya Vigezo**
   Ufafanuzi wa aina ya vigezo huhifadhiwa katika usanidi na aina "parameter-type"
   Kila ufafanuzi wa aina una schema, thamani chaguo, na sheria za uthibitishaji
   Hifadhi aina za vigezo zinazotumika mara kwa mara ili kupunguza utafutaji wa usanidi
=======
   Kuchukua metadata ya vigezo kutoka sehemu ya `parameters` ya mpango wa mtiririko.
   Kwa kila vigezo, pata ufafanuzi wa aina yake kutoka kwa hifadhi ya usanidi.
   Tumia maadili chaguu kwa vigezo vyovyote ambavyo havijatolewa na mtumiaji.
   Kushughulikia uhusiano wa urithi wa `controlled-by`.
   Kurudisha seti kamili ya vigezo.

2. **Njia Iliyorekebishwa ya `handle_start_flow`**
   Piga `resolve_parameters` baada ya kupakua mpango wa mtiririko.
   Tumia seti kamili ya vigezo vilivyofafanuliwa kwa badiliko la kiolezo.
   Hifadhi seti kamili ya vigezo (si tu ile iliyotolewa na mtumiaji) pamoja na mtiririko.
   Thibitisha kuwa vigezo vyote muhimu vina maadili.

3. **Uchukuzi wa Aina ya Vigezo**
   Ufafanuzi wa aina ya vigezo huhifadhiwa katika usanidi na aina "parameter-type".
   Kila ufafanuzi wa aina una schema, thamani chaguo, na sheria za uthibitishaji.
   Hifadhi aina za vigezo zinazotumika mara kwa mara ili kupunguza utafutaji wa usanidi.
>>>>>>> 82edf2d (New md files from RunPod)

#### Ujumuishaji wa Mfumo wa Usanidi

3. **Uhifadhi wa Kitu cha Mtiririko**
<<<<<<< HEAD
   Wakati mtiririko unaongezwa kwenye mfumo wa usanidi na kipengele cha mtiririko katika meneja wa usanidi, kitu cha mtiririko lazima kiwe na maadili yaliyomalizika ya vigezo
   Meneja wa usanidi lazima ahifadhi vigezo vyote vilivyotolewa na mtumiaji na maadili yaliyomalizika (pamoja na maadili chaguo)
   Vitu vya mtiririko katika mfumo wa usanidi vinapaswa kujumuisha:
     `parameters`: Maadili ya vigezo yaliyomalizika ambayo hutumiwa kwa mtiririko
=======
   Wakati mtiririko unaongezwa kwenye mfumo wa usanidi na kipengele cha mtiririko katika meneja wa usanidi, kitu cha mtiririko lazima kiwe na maadili yaliyofafanuliwa ya vigezo.
   Meneja wa usanidi lazima ahifadhi vigezo vyote vilivyotolewa na mtumiaji na maadili yaliyofafanuliwa (pamoja na maadili chaguo).
   Vitu vya mtiririko katika mfumo wa usanidi vinapaswa kujumuisha:
     `parameters`: Maadili yaliyofafanuliwa ya vigezo ambayo hutumiwa kwa mtiririko.
>>>>>>> 82edf2d (New md files from RunPod)

#### Ujumuishaji wa CLI

4. **Amani za CLI za Maktaba**
   Amani za CLI ambazo huanzisha mitiririko zinahitaji usaidizi wa vigezo:
<<<<<<< HEAD
     Kukubali maadili ya vigezo kupitia bendera za mstari wa amri au faili za usanidi
     Thibitisha vigezo dhidi ya ufafanuzi wa mpango wa mtiririko kabla ya kuwasilisha
     Usaidizi wa uingizaji wa faili ya vigezo (JSON/YAML) kwa seti ngumu ya vigezo

   Amani za CLI ambazo zinaonyesha mitiririko zinahitaji kuonyesha habari ya vigezo:
     Onyesha maadili ya vigezo ambayo yalitumiwa wakati mtiririko ulipoanzishwa
     Onyesha vigezo vinavyopatikana kwa mpango wa mtiririko
     Onyesha schema na maadili chaguo ya vigezo
=======
     Kukubali maadili ya vigezo kupitia bendera za mstari wa amri au faili za usanidi.
     Thibitisha vigezo dhidi ya ufafanuzi wa mpango wa mtiririko kabla ya kuwasilisha.
     Usaidizi wa uingizaji wa faili ya vigezo (JSON/YAML) kwa seti ngumu ya vigezo.

   Amani za CLI ambazo zinaonyesha mitiririko zinahitaji kuonyesha taarifa za vigezo:
     Onyesha maadili ya vigezo ambayo yalitumiwa wakati mtiririko ulipoanzishwa.
     Onyesha vigezo vinavyopatikana kwa mpango wa mtiririko.
     Onyesha schema na maadili chaguo ya vigezo.
>>>>>>> 82edf2d (New md files from RunPod)

#### Ujumuishaji wa Darasa la Msingi la Processor

5. **Usaidizi wa ParameterSpec**
<<<<<<< HEAD
   Darasa za msingi za processor zinahitaji kusaidia kubadilisha vigezo kupitia utaratibu uliopo wa ParametersSpec
   Darasa la ParametersSpec (lililopo katika moduli sawa na ConsumerSpec na ProducerSpec) linapaswa kuimarishwa ikiwa ni lazima ili kusaidia kubadilisha kigezo
   Wasindikaji wanapaswa kuwa na uwezo wa kuita ParametersSpec ili kusanidi vigezo vyao na maadili ya vigezo ambayo yamefafanuliwa wakati wa kuzindua mtiririko
   Utaratibu wa utekelezaji wa ParametersSpec lazima:
     Kukubali usanidi wa vigezo ambao una nafasi za vigezo (k.m., `{model}`, `{temperature}`)
     Kusaidia kubadilisha vigezo wakati wa uendeshaji wa wasindikaji
     Thibitisha kwamba maadili yaliyobadilishwa yanalingana na aina na vikwazo vilivyotarajiwa
     Kutoa ushughulikiaji wa makosa kwa marejeleo yaliyopotea au yasiyo halali ya vigezo

#### Kanuni za Kubadilisha

Vigezo hutumia muundo wa `{parameter-name}` katika vigezo vya wasindikaji
Majina ya vigezo katika vigezo yanalingana na funguo katika sehemu ya `parameters` ya mtiririko
Kubadilisha hufanyika pamoja na `{id}` na `{class}`
Marejeleo yasiyo halali ya vigezo husababisha makosa wakati wa kuzindua
Uthibitisho wa aina hutokea kulingana na ufafanuzi wa vigezo uliohifadhiwa katikati
**MUHIMU**: Maadili yote ya vigezo huhifadhiwa na hutumwa kama maandishi
  Nambari hubadilishwa kuwa maandishi (k.m., `0.7` inakuwa `"0.7"`)
  Booleans hubadilishwa kuwa maandishi ya chini (k.m., `true` inakuwa `"true"`)
  Hii inahitajika na schema ya Pulsar ambayo ina `parameters = Map(String())`
=======
   Darasa za msingi za processor zinahitaji kusaidia badiliko la vigezo kupitia utaratibu uliopo wa ParametersSpec.
   Darasa la ParametersSpec (lililopo katika moduli sawa na ConsumerSpec na ProducerSpec) linapaswa kuimarishwa ikiwa ni lazima ili kusaidia badiliko la kiolezo la vigezo.
   Wasindikaji wanapaswa kuwa na uwezo wa kutumia ParametersSpec ili kusanidi vigezo vyao na maadili ya vigezo ambayo yamefafanuliwa wakati wa kuzindua mtiririko.
   Utaratibu wa utekelezaji wa ParametersSpec lazima:
     Kukubali usanidi wa vigezo ambao una nafasi za vigezo (k.m., `{model}`, `{temperature}`).
     Kusaidia badiliko la vigezo wakati wa utekelezaji wa processor.
     Thibitisha kuwa maadili yaliyobadilishwa yanalingana na aina na vikwazo vilivyotarajiwa.
     Kutoa usimamizi wa makosa kwa marejeleo yaliyopotea au yasiyo halali ya vigezo.

#### Kanuni za Badiliko

Vigezo hutumia muundo wa `{parameter-name}` katika vigezo vya processor.
Majina ya vigezo katika vigezo yanalingana na funguo katika sehemu ya `parameters` ya mtiririko.
Badiliko hufanyika pamoja na `{id}` na `{class}`.
Marejeleo yasiyo halali ya vigezo husababisha makosa wakati wa kuzindua.
Uthibitisho wa aina hutokea kulingana na ufafanuzi wa vigezo uliohifadhiwa katikati.
**MUHIMU**: Maadili yote ya vigezo huhifadhiwa na hutumwa kama maandishi.
  Nambari hubadilishwa kuwa maandishi (k.m., `0.7` inakuwa `"0.7"`).
  Maneno ya kweli hubadilishwa kuwa maandishi ya chini (k.m., `true` inakuwa `"true"`).
  Hii inahitajika na schema ya Pulsar ambayo ina `parameters = Map(String())`.
>>>>>>> 82edf2d (New md files from RunPod)

Mfano wa utatuzi:
```
Flow parameter mapping: "model": "llm-model"
Processor parameter: "model": "{model}"
User provides: "model": "gemma3:8b"
Final parameter: "model": "gemma3:8b"

Example with type conversion:
Parameter type default: 0.7 (number)
Stored in flow: "0.7" (string)
Substituted in processor: "0.7" (string)
```

## Mbinu ya Majaribio

Majaribio ya kitengo kwa uthibitishaji wa muundo wa vigezo
<<<<<<< HEAD
Majaribio ya ujumuishaji kwa ubadilishaji wa vigezo katika vigezo vya kichakato
Majaribio ya mwisho kwa kuzindua michakato na maadili tofauti ya vigezo
Majaribio ya UI kwa utengenezaji na uthibitishaji wa fomu ya vigezo
Majaribio ya utendaji kwa michakato yenye vigezo vingi
=======
Majaribio ya ujumuishaji kwa ubadilishaji wa vigezo katika vigezo vya kichakata
Majaribio ya mwisho kwa kuzindua mtiririko na maadili tofauti ya vigezo
Majaribio ya UI kwa utengenezaji na uthibitishaji wa fomu ya vigezo
Majaribio ya utendaji kwa mtiririko na vigezo vingi
>>>>>>> 82edf2d (New md files from RunPod)
Hali za kipekee: vigezo visivyopo, aina zisizo sahihi, marejeleo ya vigezo yasiyo sahihi

## Mpango wa Uhamisho

<<<<<<< HEAD
1. Mfumo unapaswa kuendelea kusaidia mipango ya michakato bila vigezo
   vilivyotangazwa.
2. Mfumo unapaswa kuendelea kusaidia michakato bila vigezo vilivyobainishwa:
   Hii inafanya kazi kwa michakato bila vigezo, na michakato yenye vigezo
   (yana maadili ya chagu).

## Maswali ya Wazi

S: Je, vigezo vinapaswa kusaidia vitu vikubwa vilivyojumuishwa au kubaki kwenye aina rahisi?
J: Maadili ya vigezo yatakuwa yamekodishwa kama maandishi, tunapaswa
   kubaki na maandishi.

S: Je, je, nafasi za vigezo zinapaswa kuruhusiwa katika majina ya folyo au tu katika
=======
1. Mfumo unapaswa kuendelea kusaidia mipango ya mtiririko ambayo haina vigezo
   vilivyotangazwa.
2. Mfumo unapaswa kuendelea kusaidia mtiririko bila vigezo vilivyobainishwa:
   Hii inafanya kazi kwa mtiririko ambayo haina vigezo, na mtiririko una vigezo
   (yana maadili chagu).

## Maswali ya Wazi

S: Je, vigezo vinapaswa kusaidia vitu vikubwa vilivyojumuishwa au kuendelea na aina rahisi?
J: Maadili ya vigezo yatakuwa yamekodishwa kama maandishi, tunapaswa
   kuzingatia maandishi.

S: Je, vigezo vya maandishi vinapaswa kuruhusiwa katika majina ya folyo au tu katika
>>>>>>> 82edf2d (New md files from RunPod)
   vigezo?
J: Tu katika vigezo ili kuondoa uingizwaji wa ajabu na hali za kipekee.

S: Jinsi ya kushughulikia migogoro kati ya majina ya vigezo na vigezo vya mfumo kama vile
   `id` na `class`?
<<<<<<< HEAD
J: Ni vibaya kutaja id na darasa wakati wa kuzindua michakato
=======
J: Ni vibaya kutaja id na darasa wakati wa kuzindua mtiririko
>>>>>>> 82edf2d (New md files from RunPod)

S: Je, tunapaswa kusaidia vigezo vilivyohitajiwa (vilivyotokana na vigezo vingine)?
J: Tu ubadilishaji wa maandishi ili kuondoa uingizwaji wa ajabu na hali za kipekee.

## Marejeleo

Vipimo vya Mpango wa JSON: https://json-schema.org/
<<<<<<< HEAD
Vipimo vya Ufafanuzi wa Mpango wa Michakato: docs/tech-specs/flow-class-definition.md
=======
Vipimo vya Ufafanuzi wa Mpango wa Mtiririko: docs/tech-specs/flow-class-definition.md
>>>>>>> 82edf2d (New md files from RunPod)
