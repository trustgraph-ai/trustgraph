---
layout: default
title: "Mbinu ya Muundo wa Ontolojia"
parent: "Swahili (Beta)"
---

# Mbinu ya Muundo wa Ontolojia

> **Beta Translation:** This document was translated via Machine Learning and as such may not be 100% accurate. All non-English languages are currently classified as Beta.

## Maelezo

Mazingira haya yanatoa maelezo kuhusu muundo na umbizo wa ontolojia ndani ya mfumo wa TrustGraph. Ontolojia hutoa modeli rasmi za maarifa ambayo inafafanua madarasa, sifa, na uhusiano, na inasaidia uwezo wa utafsiri na utabiri. Mfumo hutumia umbizo unaolingana na OWL (Web Ontology Language) ambao unafafanua dhana za OWL/RDFS, lakini umeboreshwa kwa mahitaji maalum ya TrustGraph.

**Mikataba ya Majina**: Mradi huu hutumia "kebab-case" kwa kitambulisho chote (funguo za usanidi, sehemu za API, majina ya moduli, n.k.) badala ya "snake_case".

## Lengo

- **Usimamizi wa Darasa na Sifa**: Tafsiri madarasa kama vile ya OWL na sifa, vikoa, masafa, na vikwazo vya aina.
- **Usaidizi Kamili wa Semantikia**: Uwezo wa kutumia sifa za RDFS/OWL ikiwa ni pamoja na lebo, usaidizi wa lugha nyingi, na vikwazo rasmi.
- **Usaidizi wa Ontolojia nyingi**: Kuruhusu ontolojia nyingi kuwepo na kufanya kazi pamoja.
- **Uthibitisho na Utabiri**: Hakikisha kuwa ontolojia zinafuata viwango vya aina ya OWL, na hutoa ufuatiliaji wa uthabiti na usaidizi wa utabiri.
- **Ulinganisho na Viwango**: Kusaidia uingizaji na urekebishaji katika umbizo wa kawaida (Turtle, RDF/XML, OWL/XML) wakati unahifadhi uboreshaji wa ndani.

## Misingi

TrustGraph huhifadhi ontolojia kama vitu vya usanidi katika mfumo wa thamani-funguo ambao una uwezo wa kubadilika. Ingawa umbizo huu unatokana na OWL (Web Ontology Language), umeboreshwa kwa matumio maalum ya TrustGraph na haufuate vipengele vyote vya OWL.

Ontolojia katika TrustGraph zinaruhusu:
- Ufafanuzi wa aina rasmi za vitu na sifa zake.
- Ufafanuzi wa vikoa na masafa ya sifa, pamoja na vikwazo vya aina.
- Utabiri na utafsiri wa mantiki.
- Uhusiano tata na vikwazo vya wingi.
- Usaidizi wa lugha nyingi kwa utoaji wa lugha.

## Muundo wa Ontolojia

### Uhifadhi wa Usanidi

Ontolojia huhifadhiwa kama vitu vya usanidi na muundo ufuatao:
- **Aina**: `ontology`
- **Funguo**: Kitambulisho cha kipekee cha ontolojia (k.m., `natural-world`, `domain-model`)
- **Thamani**: Ontolojia kamili katika umbizo la JSON.

### Muundo wa JSON

Muundo wa JSON wa ontolojia una sehemu nne kuu:

#### 1. MetaData

Inayo habari ya utawala na maelezo kuhusu ontolojia:

```json
{
  "metadata": {
    "name": "Ulimwengu wa asili",
    "description": "Ontolojia inayofafanua mazingira ya asili",
    "version": "1.0.0",
    "created": "2025-09-20T12:07:37.068Z",
    "modified": "2025-09-20T12:12:20.725Z",
    "creator": "mtumiaji-sasa",
    "namespace": "http://trustgraph.ai/ontologies/natural-world",
    "imports": ["http://www.w3.org/2002/07/owl#"]
  }
}
```

**Vifaa:**
- `name`: Jina linaloweza kusomwa na binadamu la ontolojia.
- `description`: Maelezo mafupi ya lengo la ontolojia.
- `version`: Nambari ya toleo.
- `created`: Alama ya muda wa ISO 8601 ya uundaji.
- `modified`: Alama ya muda wa ISO 8601 ya mabadiliko ya mwisho.
- `creator`: Kitambulisho cha mtumiaji/mfumo aliyeuunda.
- `namespace`: URI ya msingi kwa vipengele vya ontolojia.
- `imports`: Orodha ya URI za ontolojia zilizounganishwa.

#### 2. Madarasa

Inafafanua aina za vitu na uhusiano wao wa kimfumo:

```json
{
  "classes": {
    "lifeform": {
      "uri": "http://trustgraph.ai/ontologies/natural-world#lifeform",
      "type": "owl:Class",
      "rdfs:label": [{"value": "Lifeform", "lang": "en"}],
      "rdfs:comment": "Kiumbe hai"
    },
    "animal": {
      "uri": "http://trustgraph.ai/ontologies/natural-world#animal",
      "type": "owl:Class",
      "rdfs:label": [{"value": "Animal", "lang": "en"}],
      "rdfs:comment": "Kiumbe cha wanyama",
      "rdfs:subClassOf": "lifeform"
    },
    "cat": {
      "uri": "http://trustgraph.ai/ontologies/natural-world#cat",
      "type": "owl:Class",
      "rdfs:label": [{"value": "Cat", "lang": "en"}],
      "rdfs:comment": "Paka",
      "rdfs:subClassOf": "animal"
    },
    "dog": {
      "uri": "http://trustgraph.ai/ontologies/natural-world#dog",
      "type": "owl:Class",
      "rdfs:label": [{"value": "Dog", "lang": "en"}],
      "rdfs:comment": "Mbwa",
      "rdfs:subClassOf": "animal",
      "owl:disjointWith": ["cat"]
    }
  },
```

#### 3. Sifa

(Tangu hakuna sifa katika mfano, sehemu hii imetolewa)

#### 4. Ufafanuzi wa Sifa za Data

(Tangu hakunafafanushwi, sehemu hii imetolewa)

## Kanuni za Uthibitisho

### Uthibitisho wa Muundo

1. **Ulinganifu wa URI**: URI zote zinapaswa kufuata muundo `{namespace}#{identifier}`.
2. **Hieroni ya Darasa**: Hakuna urithi wa mzunguko katika `rdfs:subClassOf`.
3. **Vikoa/Masafa ya Sifa**: Lazima irejee madarasa yaliyopo au aina halali za XSD.
4. **Darasa zisizolingana**: Haiwezi kuwa ndogo za kila mmoja.
5. **Sifa za Kinyume**: Lazima iwe bidirectional ikiwa imeelezwa.

### Uthibitisho wa Semantikia

1. **Kitambulisho cha kipekee**: Kitambulisho cha darasa na sifa lazima kiwe kipekee ndani ya ontolojia.
2. **Lebo za Lugha**: Lazima ifuate muundo wa lebo wa BCP 47.
3. **Vikwazo vya Kiasi**: `minCardinality` ≤ `maxCardinality` wakati zote zimetajwa.
4. **Sifa za Kifaa**: Haiwezi kuwa na `maxCardinality` > 1.

## Usaidizi wa Umbizo wa Uingizaji/Urekebishaji

Ingawa umbizo la ndani ni JSON, mfumo unaweza kubadilisha hadi/kutoka kwa umbizo wa kawaida wa ontolojia:

- **Turtle (.ttl)** - Urekebishaji kompakt wa RDF.
- **RDF/XML (.rdf, .owl)** - Umbizo la kawaida la W3C.
- **OWL/XML (.owx)** - Umbizo la XML maalum kwa OWL.
- **JSON-LD (.jsonld)** - JSON kwa Data iliyounganishwa.

## Marejeleo

- [OWL 2 Web Ontology Language](https://www.w3.org/TR/owl2-overview/)
- [RDF Schema 1.1](https://www.w3.org/TR/rdf-schema/)
- [XML Schema Datatypes](https://www.w3.org/TR/xmlschema-2/)
- [BCP 47 Language Tags](https://tools.ietf.org/html/bcp47)
