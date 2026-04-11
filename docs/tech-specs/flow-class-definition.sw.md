---
layout: default
title: "Maelezo ya Ufafanuzi wa Mfumo wa Mtiririko"
parent: "Swahili (Beta)"
---

# Maelezo ya Ufafanuzi wa Mfumo wa Mtiririko

> **Beta Translation:** This document was translated via Machine Learning and as such may not be 100% accurate. All non-English languages are currently classified as Beta.

## Muhtasari

<<<<<<< HEAD
Mfumo wa mtiririko unafafanua kiolezo kamili cha mtiririko wa data katika mfumo wa TrustGraph. Unapoongezwa, huunda mtandao unaounganishwa wa vichakata ambavyo hushughulikia uingizaji wa data, uchakataji, uhifadhi, na kuulizia kama mfumo mmoja.
=======
Mfumo wa mtiririko unafafanua mfumo kamili wa mtiririko wa data katika mfumo wa TrustGraph. Unapoongezwa, huunda mtandao unaounganishwa wa vichakata ambavyo hushughulikia uingizaji wa data, uchakataji, uhifadhi, na kuulizia kama mfumo mmoja.
>>>>>>> 82edf2d (New md files from RunPod)

## Muundo

Ufafanuzi wa mfumo wa mtiririko una sehemu tano kuu:

### 1. Sehemu ya Darasa
<<<<<<< HEAD
Inafafanua vichakata vya huduma ambavyo huanzishwa mara moja kwa kila mfumo wa mtiririko. Vichakata hivi hushughulikia ombi kutoka kwa visasisho vyote vya mfumo wa mtiririko vya darasa hili.
=======
Inafafanua vichakata vya huduma ambavyo huanzishwa mara moja kwa kila mfumo wa mtiririko. Vichakata hivi hushughulikia ombi kutoka kwa visasisho vyote vya mfumo wa mtiririko wa darasa hili.
>>>>>>> 82edf2d (New md files from RunPod)

```json
"class": {
  "service-name:{class}": {
    "request": "queue-pattern:{class}",
    "response": "queue-pattern:{class}",
    "settings": {
      "setting-name": "fixed-value",
      "parameterized-setting": "{parameter-name}"
    }
  }
}
```

**Sifa:**
Zinashirikiwa katika visasisho vyote vya aina moja.
Hutoa huduma za kawaida au zisizo na hali (LLMs, modeli za uingizaji).
<<<<<<< HEAD
Tumia jina la kigezo cha `{class}` kwa ajili ya kujina kwa folyo.
=======
Tumia jina la kigezo `{class}` kwa ajili ya kujina kwa folyo.
>>>>>>> 82edf2d (New md files from RunPod)
Mipangilio inaweza kuwa maadili thabiti au kupangwa kwa kutumia sintaksia ya `{parameter-name}`.
Mifano: `embeddings:{class}`, `text-completion:{class}`, `graph-rag:{class}`

### 2. Sehemu ya Folyo
Inafafanua vichakataji maalum ya folyo ambavyo huanzishwa kwa kila visa maalum la folyo. Kila folyo hupata seti yake mwenyewe ya vichakataji hivi.

```json
"flow": {
  "processor-name:{id}": {
    "input": "queue-pattern:{id}",
    "output": "queue-pattern:{id}",
    "settings": {
      "setting-name": "fixed-value",
      "parameterized-setting": "{parameter-name}"
    }
  }
}
```

**Sifa:**
Mfano pekee kwa kila mtiririko.
Hushughulikia data na hali maalum ya mtiririko.
Tumia kigezo cha `{id}` kwa ajili ya kujina kwa folyo.
Mipangilio inaweza kuwa maadili thabiti au kupangishwa kwa kutumia sintaksia ya `{parameter-name}`.
Mifano: `chunker:{id}`, `pdf-decoder:{id}`, `kg-extract-relationships:{id}`.

<<<<<<< HEAD
### 3. Sehemu ya Vifaa
Inaelezea pointi za kuingilia na mikataba ya mwingiliano kwa mtiririko. Haya huunda safu ya API kwa mifumo ya nje na mawasiliano ya vipengele vya ndani.

Vifaa vinaweza kuwa na aina mbili:
=======
### Sura ya 3. Sehemu ya Vifaa vya Kuunganisha
Inaelezea pointi za kuingilia na mikataba ya kuingiliana kwa mtiririko. Hizi huunda safu ya API kwa mifumo ya nje na mawasiliano ya vipengele vya ndani.

Vifaa vya kuunganisha vinaweza kuwa na aina mbili:
>>>>>>> 82edf2d (New md files from RunPod)

**Mfumo wa "Tuma na Usahau"** (folyo moja):
```json
"interfaces": {
  "document-load": "persistent://tg/flow/document-load:{id}",
  "triples-store": "persistent://tg/flow/triples-store:{id}"
}
```

<<<<<<< HEAD
**Muundo wa Ombi/Jibu** (kitu chenye sehemu za ombi/jibu):
=======
**Muundo wa Ombi/Jibu** (objekti yenye sehemu za ombi/jibu):
>>>>>>> 82edf2d (New md files from RunPod)
```json
"interfaces": {
  "embeddings": {
    "request": "non-persistent://tg/request/embeddings:{class}",
    "response": "non-persistent://tg/response/embeddings:{class}"
  }
}
```

<<<<<<< HEAD
**Aina za Mfumo:**
**Vituo vya Kuingia**: Maeneo ambapo mifumo ya nje huingiza data (`document-load`, `agent`)
**Mifumo ya Huduma**: Mfumo wa ombi/jibu kwa huduma (`embeddings`, `text-completion`)
**Mifumo ya Data**: Vituo vya muunganisho wa mtiririko wa data (`triples-store`, `entity-contexts-load`)

### 4. Sehemu ya Vigezo
Huunganisha majina ya vigezo maalum ya mtiririko na ufafanuzi wa vigezo unaohifadhiwa katika eneo moja:
=======
**Aina za Vifaa vya Kuunganisha:**
**Vifaa vya Kuanzia:** Maeneo ambapo mifumo ya nje huingiza data (`document-load`, `agent`)
**Vifaa vya Huduma:** Mfumo wa ombi/jibu kwa huduma (`embeddings`, `text-completion`)
**Vifaa vya Data:** Vifaa vya kuunganisha mtiririko wa data (`triples-store`, `entity-contexts-load`)

### 4. Sehemu ya Vigezo
Huunganisha majina ya vigezo maalum ya mtiririko na ufafanuzi wa vigezo unaohifadhiwa katika eneo la kati:
>>>>>>> 82edf2d (New md files from RunPod)

```json
"parameters": {
  "model": "llm-model",
  "temp": "temperature",
  "chunk": "chunk-size"
}
```

**Sifa:**
<<<<<<< HEAD
Nenosiri ni majina ya vigezo yanayotumika katika mipangilio ya kichakata (k.m., `{model}`)
=======
Funguo ni majina ya vigezo yanayotumika katika mipangilio ya kichakata (k.m., `{model}`)
>>>>>>> 82edf2d (New md files from RunPod)
Maelezo yanaashiria ufafanuzi wa vigezo uliohifadhiwa katika schema/config
Inaruhusu matumizi ya mara kwa mara ya ufafanuzi wa kawaida wa vigezo katika michakato.
Hupunguza marudio ya schemas za vigezo.

### 5. Meta Data
<<<<<<< HEAD
Taarifa za ziada kuhusu mpango wa mtiririko:
=======
Habari ya ziada kuhusu mpango wa mtiririko:
>>>>>>> 82edf2d (New md files from RunPod)

```json
"description": "Human-readable description",
"tags": ["capability-1", "capability-2"]
```

## Vigezo vya Kiolele

### Vigezo vya Mfumo

#### {id}
<<<<<<< HEAD
Huibwa na kitambulisho kipekee cha kila mfumo.
Huunda rasilimali zilizotengwa kwa kila mfumo.
Mifano: `flow-123`, `customer-A-flow`

#### {class}
Huibwa na jina la mpango wa mfumo.
Huunda rasilimali zilizoshirikiwa katika mifumo ya aina moja.
Mifano: `standard-rag`, `enterprise-rag`
=======
Huibadilishwa na kitambulisho kipekee cha kila mtiririko.
Huunda rasilimali zilizojitenga kwa kila mtiririko.
Mfano: `flow-123`, `customer-A-flow`

#### {class}
Huibadilishwa na jina la mpango wa mtiririko.
Huunda rasilimali zilizoshirikiwa katika mitiririko ya aina moja.
Mfano: `standard-rag`, `enterprise-rag`
>>>>>>> 82edf2d (New md files from RunPod)

### Vigezo vya Parameta

#### {parameter-name}
<<<<<<< HEAD
Parameta maalum zilizobainishwa wakati wa kuanzisha mfumo.
Majina ya parameta yanalingana na funguo katika sehemu ya `parameters` ya mfumo.
Hutumiwa katika mipangilio ya kichakuzi ili kuboresha tabia.
Mifano: `{model}`, `{temp}`, `{chunk}`
Huibwa na maadili yaliyotolewa wakati wa kuanzisha mfumo.
Yanathibitishwa kulingana na ufafanuzi wa parameta uliohifadhiwa katika mfumo.

## Mpangilio wa Kichakuzi

Mpangilio hutoa maadili ya usanidi kwa vichakuzi wakati wa uundaji. Inaweza kuwa:

### Mpangilio Thabiti
=======
Parameta maalum zilizobainishwa wakati wa kuanzisha mtiririko.
Majina ya parametri yanalingana na funguo katika sehemu ya `parameters` ya mtiririko.
Hutumiwa katika mipangilio ya kichakataji ili kuboresha tabia.
Mifano: `{model}`, `{temp}`, `{chunk}`
Huibadilishwa na maadili yaliyotolewa wakati wa kuanzisha mtiririko.
Yanathibitishwa kulingana na ufafanuzi wa parametri uliohifadhiwa katika mfumo.

## Mipangilio ya Kichakataji

Mipangilio hutoa maadili ya usanidi kwa vichakataji wakati wa uundaji. Inaweza kuwa:

### Mipangilio Thabiti
>>>>>>> 82edf2d (New md files from RunPod)
Maadili ya moja kwa moja ambayo hayubadiliki:
```json
"settings": {
  "model": "gemma3:12b",
  "temperature": 0.7,
  "max_retries": 3
}
```

<<<<<<< HEAD
### Mipangilio Iliyobadilishwa
=======
### Parameta za Mpangilio
>>>>>>> 82edf2d (New md files from RunPod)
Maelezo ambayo hutumia vigezo vilivyotolewa wakati wa kuanzisha mtiririko:
```json
"settings": {
  "model": "{model}",
  "temperature": "{temp}",
  "endpoint": "https://{region}.api.example.com"
}
```

Majina ya vigezo katika mipangilio yanalingana na funguo katika sehemu ya `parameters` ya mtiririko.

### Mifano ya Mipangilio

**Mchakato wa LLM na Vigezo:**
```json
// In parameters section:
"parameters": {
  "model": "llm-model",
  "temp": "temperature",
  "tokens": "max-tokens",
  "key": "openai-api-key"
}

// In processor definition:
"text-completion:{class}": {
  "request": "non-persistent://tg/request/text-completion:{class}",
  "response": "non-persistent://tg/response/text-completion:{class}",
  "settings": {
    "model": "{model}",
    "temperature": "{temp}",
    "max_tokens": "{tokens}",
    "api_key": "{key}"
  }
}
```

<<<<<<< HEAD
**Kifurushi cha Mpangilio wa Kurekebisha na Unaoweza Kubadilishwa:**
=======
**Sehemu za Kujumuisha Zenye Mipangilio Thabiti na Inayoweza Kubadilishwa:**
>>>>>>> 82edf2d (New md files from RunPod)
```json
// In parameters section:
"parameters": {
  "chunk": "chunk-size"
}

// In processor definition:
"chunker:{id}": {
  "input": "persistent://tg/flow/chunk:{id}",
  "output": "persistent://tg/flow/chunk-load:{id}",
  "settings": {
    "chunk_size": "{chunk}",
    "chunk_overlap": 100,
    "encoding": "utf-8"
  }
}
```

## Mifumo ya Kinyororo (Pulsar)

<<<<<<< HEAD
Mfumo wa mtiririko hutumia Apache Pulsar kwa ujumbe. Majina ya nyororo yanafuata muundo wa Pulsar:
=======
Mfumo wa mtiririko hutumia Apache Pulsar kwa ajili ya ujumbe. Majina ya nyororo yanafuata muundo wa Pulsar:
>>>>>>> 82edf2d (New md files from RunPod)
```
<persistence>://<tenant>/<namespace>/<topic>
```

### Vipengele:
<<<<<<< HEAD
**uthibitisho**: `persistent` au `non-persistent` (Njia ya uthibitisho ya Pulsar)
**mwendeshaji**: `tg` kwa maelezo ya muundo wa mtiririko yanayotolewa na TrustGraph
**nafasi**: Inaonyesha muundo wa ujumbe
=======
**uhifadhi**: `persistent` au `non-persistent` (Njia ya uhifadhi ya Pulsar)
**mwendeshaji**: `tg` kwa maelekezo ya muundo wa mtiririko yanayotolewa na TrustGraph
**nafasi**: Inaonyesha mtindo wa ujumbe
>>>>>>> 82edf2d (New md files from RunPod)
  `flow`: Huduma za "tumia na usahau"
  `request`: Sehemu ya ombi ya huduma za ombi/jibu
  `response`: Sehemu ya jibu ya huduma za ombi/jibu
**mada**: Jina maalum la folyo/mada na vigezo vya kiolezo

### Folyozilizohifadhiwa
<<<<<<< HEAD
Muundo: `persistent://tg/flow/<topic>:{id}`
Inatumika kwa huduma za "tumia na usahau" na mtiririko wa data endelevu
Data inabaki katika hifadhi ya Pulsar wakati wa kuanzishwa upya
Mfano: `persistent://tg/flow/chunk-load:{id}`

### Folyozilizohifadhiwa
Muundo: `non-persistent://tg/request/<topic>:{class}` au `non-persistent://tg/response/<topic>:{class}`
Inatumika kwa muundo wa ujumbe wa ombi/jibu
Inapotea, haihifadhiwa kwenye diski na Pulsar
Latensi ndogo, inafaa kwa mawasiliano ya aina ya RPC
=======
Mtindo: `persistent://tg/flow/<topic>:{id}`
Inatumika kwa huduma za "tumia na usahau" na mtiririko wa data endelevu
Data inahifadhiwa katika hifadhi ya Pulsar katika kuanzishwa upya
Mfano: `persistent://tg/flow/chunk-load:{id}`

### Folyozilizohifadhiwa
Mtindo: `non-persistent://tg/request/<topic>:{class}` au `non-persistent://tg/response/<topic>:{class}`
Inatumika kwa mitindo ya ujumbe ya ombi/jibu
Inapotea, haihifadhiwi kwenye diski na Pulsar
Latensi ya chini, inayofaa kwa mawasiliano ya aina ya RPC
>>>>>>> 82edf2d (New md files from RunPod)
Mfano: `non-persistent://tg/request/embeddings:{class}`

## Usanifu wa Mtiririko wa Data

<<<<<<< HEAD
Muundo wa mtiririko huunda mtiririko wa data unaounganishwa ambapo:

1. **Mchakato wa Kusindika Nyaraka**: Mtiririko kutoka kwa kupokea hadi kubadilisha hadi kuhifadhi
=======
Muundo wa mtiririko huunda mtiririko wa data uliounganishwa ambapo:

1. **Mchakato wa Kusindika Nyaraka**: Mtiririko kutoka kwa kupokea kupitia mabadiliko hadi kuhifadhi
>>>>>>> 82edf2d (New md files from RunPod)
2. **Huduma za Uchunguzi**: Wasindikaji waliojumuishwa ambao huchunguza hifadhi na huduma sawa za data
3. **Huduma Zilizoshirikiwa**: Wasindikaji wa kati ambao mtiririko wote unaweza kutumia
4. **Waandikaji wa Hifadhi**: Kuhifadhi data iliyosindikwa kwenye hifadhi husika

<<<<<<< HEAD
Wasindikaji wote (wote `{id}` na `{class}`) hufanya kazi pamoja kama grafu moja ya mtiririko wa data, sio mifumo tofauti.
=======
Wasindikaji wote (wote `{id}` na `{class}`) hufanya kazi pamoja kama grafu ya mtiririko wa data iliyounganishwa, sio mifumo tofauti.
>>>>>>> 82edf2d (New md files from RunPod)

## Uanzishaji wa Mfano wa Mtiririko

Imepewa:
Kitambulisho cha Mfano wa Mtiririko: `customer-A-flow`
Muundo wa Mtiririko: `standard-rag`
Ramani za vigezo vya mtiririko:
  `"model": "llm-model"`
  `"temp": "temperature"`
  `"chunk": "chunk-size"`
Vigezo vilivyotolewa na mtumiaji:
  `model`: `gpt-4`
  `temp`: `0.5`
  `chunk`: `512`

Upanuzi wa kiolezo:
`persistent://tg/flow/chunk-load:{id}` → `persistent://tg/flow/chunk-load:customer-A-flow`
`non-persistent://tg/request/embeddings:{class}` → `non-persistent://tg/request/embeddings:standard-rag`
`"model": "{model}"` → `"model": "gpt-4"`
`"temperature": "{temp}"` → `"temperature": "0.5"`
`"chunk_size": "{chunk}"` → `"chunk_size": "512"`

Hii huunda:
Mchakato wa kusindika nyaraka uliotengwa kwa `customer-A-flow`
<<<<<<< HEAD
Huduma ya pamoja ya uingizaji kwa mtiririko wote wa `standard-rag`
Mtiririko kamili kutoka kwa kupokea nyaraka hadi uchunguzi
Wasindikaji walioelekezwa na maadili ya vigezo vilivyotolewa
=======
Huduma ya pamoja ya uingishaji kwa mtiririko wote wa `standard-rag`
Mtiririko kamili kutoka kwa kupokea nyaraka hadi uchunguzi
Wasindikaji uliopangwa na maadili ya vigezo vilivyotolewa
>>>>>>> 82edf2d (New md files from RunPod)

## Faida

1. **Ufanisi wa Rasilimali**: Huduma ghali hushirikiwa katika mitiririko
2. **Kutengwa kwa Mtiririko**: Kila mtiririko una mchakato wake wa kusindika data
3. **Uwezo wa Kupanuka**: Inaweza kuanzisha mitiririko mingi kutoka kwa kiolezo kimoja
4. **Uunganishaji**: Tofauti wazi kati ya vipengele vilivyoshirikiwa na vilivyohusiana na mtiririko
5. **Usanifu Uliounganishwa**: Uchunguzi na usindikaji ni sehemu ya mtiririko mmoja wa data
