---
layout: default
title: "Tahadhari za Kiufundi za Mazingira ya Picha (Graph Contexts)"
parent: "Swahili (Beta)"
---

# Tahadhari za Kiufundi za Mazingira ya Picha (Graph Contexts)

> **Beta Translation:** This document was translated via Machine Learning and as such may not be 100% accurate. All non-English languages are currently classified as Beta.

## Muhtasari

Maelezo haya yanataja mabadiliko kwenye vitu vya msingi (primitives) vya TrustGraph ili
kuendana na RDF 1.2 na kusaidia maana kamili ya RDF Dataset. Hii ni
mabadiliko ambayo yanaweza kusababisha utosoni (breaking change) kwa toleo la 2.x.

### Matoleo

- **2.0**: Toleo la kwanza kwa watumiaji. Vitu muhimu vipo, lakini vinaweza
  kusiletelewa kikamilifu kwa matumizi ya uzalishaji.
- **2.1 / 2.2**: Toleo la uzalishaji. Uthabiti na ukamilifu umehakikishwa.

Uhusika wa uthabiti ni wa kujua - watumiaji wa kwanza wanaweza kupata
uwezo mpya kabla ya sifa zote kuwa zimekamilishwa.

## Lengo

Lengo kuu la kazi hii ni kuruhusu metadata kuhusu ukweli/taarifa:

- **Habari za muda (Temporal information)**: Kuunganisha ukweli na metadata ya wakati
  - Wakati ambapo ukweli ulikuwa unaaminika kuwa ni kweli
  - Wakati ambapo ukweli ulipoanza kuwa kweli
  - Wakati ambapo ukweli ulipoonekana kuwa bandia

- **Chanzo/Asili (Provenance/Sources)**: Kufuatilia vyanzo ambavyo vinaunga mkono ukweli
  - "Ukweli huu ulikuwa unaungwa mkono na chanzo X"
  - Kuunganisha ukweli na hati zao za asili

- **Ukweli/Amani (Veracity/Trust)**: Kurekodi maelezo kuhusu ukweli
  - "Mtu P amesema kwamba hii ni kweli"
  - "Mtu Q anadai kwamba hii ni bandia"
  - Kuruhusu upimaji wa uaminifu na ugunduzi wa migogoro

**Nadharia**: Ufufunzaji (reification) (RDF-star / triples zilizotiwa nukuu) ni
mfumo muhimu wa kufanikisha matokeo haya, kwani yote yanahitaji kufanya
maelezo kuhusu maelezo.

## Msingi

Ili kueleza "ukweli kwamba (Alice anajua Bob) uligunduliwa tarehe 2024-01-15" au
"chanzo X kinaunga mkono dai kwamba (Y husababisha Z)", unahitaji
kurejelea ukingo kama kitu ambacho unaweza kufanya maelezo. Triples
za kawaida hazisaidii hii.

### Vikwazo vya Sasa

Darasa la `Value` linalopo `trustgraph-base/trustgraph/schema/core/primitives.py`
linaweza kuwakilisha:
- Nodi za URI (`is_uri=True`)
- Maadili ya kawaida (`is_uri=False`)

Nguvu ya `type` ipo lakini haitumiki kuwakilisha aina za XSD.

## Muundo wa Kiufundi

### Sifa za RDF za Kusaidiwa

#### Sifa za Msingi (Zilizohusiana na Lengo la Ufufunzaji)

Sifa hizi zinahusiana moja kwa moja na malengo ya muda, chanzo, na ukweli:

1. **Triples Zilizotiwa Nukuu za RDF 1.2 (RDF-star)**
   - Ukingo ambao unaelekea kwenye ukingo mwingine
   - Triple inaweza kuonekana kama mada au kitu cha Triple nyingine
   - Inaruhusu maelezo kuhusu maelezo (ufufunzaji)
   - Mfumo muhimu wa kuongeza maelezo kwa ukweli binafsi

2. **RDF Dataset / Picha Zilizojulikana (Named Graphs)**
   - Usaidizi wa picha nyingi zilizojulikana ndani ya dataset
   - Kila picha huainishwa na IRI
   - Mabadiliko kutoka kwa triples (s, p, o) hadi quads (s, p, o, g)
   - Inajumuisha picha ya chaguo-msingi pamoja na picha za majina
   - IRI ya picha inaweza kuwa mada katika maelezo, kwa mfano:
     ```
     <graph-source-A> <discoveredOn> "2024-01-15"
     <graph-source-A> <hasVeracity> "high"
     ```
   - Kumbuka: Picha zilizojulikana ni kipengele tofauti kutoka kwa ufufunzaji.
     Zina matumizi mengine yakiwa nje ya kuongeza maelezo (kugawanya, udhibiti
     wa ufikiaji, shirika la dataset) na zinapaswa kuchukuliwa kama
     uwezo tofauti.

3. **Nodi Tupu (Limited Support)**
   - Nodi bila URI ya kimataifa
   - Inasaidiwa kwa utangamano wakati wa kupakua data ya RDF ya nje
   - **Hali mdogo**: Hakuna ahadi kuhusu utambulisho wa imara baada ya kupakia
   - Zipate kupitia maswali ya wildcard (pangilia kwa muunganisho, sio kwa ID)
   - Sio kipengele cha kwanza - usitegemee usimamizi sahihi wa nodi tupu

#### Marekebisho ya Nafasi (2.0 Breaking Change)

Sifa hizi hazihusiani moja kwa moja na malengo ya ufufunzaji lakini ni
mafanikio muhimu ya kuingiza wakati wa kufanya mabadiliko ambayo yanaweza
kusababisha utosoni:

4. **Aina za Literal**
   - Tumia vizuri nguvu ya `type` kwa aina za XSD
   - Mifano: xsd:string, xsd:integer, xsd:dateTime, n.k.
   - Huondoa kikwazo cha sasa: haiwezi kuwakilisha tarehe au nambari
     kwa usahihi

5. **Lebo za Lugha**
   - Usaidizi wa sifa za lugha kwenye maadili ya kawaida (@en, @fr, n.k.)
   - Kumbuka: Literal inaweza kuwa na lebo ya lugha AU aina, sio zote
     (isipokuwa rdf:langString)
   - Muhimu kwa matumizi ya AI/mbalimbali za lugha

### Miundo ya Data

#### Nguvu (kutoka Value)

Darasa la `Value` litabadilishwa na `Term` ili kuakisi vizuri dhana za RDF.
Mabadiliko haya yafanywa kwa sababu mbili:
1. Inaakisi majina na dhana za RDF (nguvu inaweza kuwa IRI, literal,
   nodi tupu, au triple iliyotiwa nukuu - sio tu "maadili")
2. Inalazimisha ukaguzi wa msimbo kwenye interface ya mabadiliko ambayo
   yanaweza kusababisha utosoni - msimbo wowote unaoendelea kurejelea `Value`
   unaonyeshwa kuwa umevunjika na unahitaji kusasishwa.

Nguvu inaweza kuwakilisha:

- **IRI/URI** - Nodi/rasilimali iliyojulikana
- **Nodi Tupu** - Nodi isiyo na jina yenye upeo wa ndani
- **Literal** - Maadili ya data ambayo ina:
  - Aina ya data (aina ya XSD), AU
  - Lebo ya lugha
- **Triple Iliyotiwa Nukuu** - Triple inayotumika kama nguvu (RDF 1.2)

##### Mbinu Iliyo Chaguliwa: Darasa Moja na Kichunguzi Aina

Mahitaji ya utayarishaji yanaendesha muundo - kichunguzi aina inahitajika
katika muundo wa waya bila kujali uwakilishi wa Python. Darasa moja na
aina ni inayofaa na inaakibiana na mtindo wa `Value` wa sasa.

Msimbo wa aina ya herufi moja hutoa utayarishaji kompakt:

```python
from dataclasses import dataclass

# Mara ya aina ya Nguvu
IRI = "i"      # Nodi ya IRI/URI
BLANK = "b"    # Nodi tupu
LITERAL = "l"  # Maadili
TRIPLE = "t"   # Triple iliyotiwa nukuu (RDF 1.2)

@dataclass
class Term:
    type: str = ""  # Moja ya: IRI, BLANK, LITERAL, TRIPLE

    # Kwa masharti ya IRI (aina == IRI)
    iri: str = ""

    # Kwa nodi tupu (aina == BLANK)
    id: str = ""

    # Kwa maadili (aina == LITERAL)
    value: str = ""
    datatype: str = ""   # URI ya aina ya XSD (inatenganishwa)
    language: str = ""   # Lebo ya lugha (inatenganishwa)

    # Kwa triples zilizotiwa nukuu (aina == TRIPLE)
    triple: "Triple | None" = None
```

Mifano ya matumizi:

```python
# Nguvu ya IRI
node = Term(type=IRI, iri="http://example.org/Alice")

# Maadili na aina
age = Term(type=LITERAL, value="42", datatype="xsd:integer")

# Maadili na lebo ya lugha
label = Term(type=LITERAL, value="Hello", language="en")

# Nodi tupu
anon = Term(type=BLANK, id="_:b1")

# Triple iliyotiwa nukuu (taarifa kuhusu taarifa)
inner = Triple(
    s=Term(type=IRI, iri="http://example.org/Alice"),
    p=Term(type=IRI, iri="http://example.org/knows"),
    o=Term(type=IRI, iri="http://example.org/Bob"),
)
reified = Term(type=TRIPLE, triple=inner)
```

##### Mbinu Zingine Zilizozingatiwa

**Njia B: Muungano wa madarasa maalum** (`Term = IRI | BlankNode | Literal | QuotedTriple`)
- Ilikataliwa: Utayarishaji bado unahitaji kichunguzi aina, na kuongeza
  ugumu.

**Njia C: Darasa la msingi na madarasa ya ndoto**
- Ilikataliwa: Tatizo lile lile la utayarishaji, pamoja na utata wa
  urithi wa dataclass

#### Triple / Quad

Darasa la `Triple` hupata nguvu ya hiari kuwa quad:

```python
@dataclass
class Triple:
    s: Term | None = None    # Mada
    p: Term | None = None    # Kieleuzo
    o: Term | None = None    # Kitu
    g: str | None = None     # Jina la picha (IRI), None = picha ya
                                 # chaguo-msingi
```

Maamuzi ya muundo:
- **Jina la nguvu**: `g` kwa utangamano na `s`, `p`, `o`
- **Hiari**: `None` inamaanisha picha ya chaguo-msingi (isiyo na jina)
- **Aina**: Kamba (IRI) badala ya Nguvu
  - Majina ya picha daima ni IRIs
  - Nodi tupu kama majina ya picha zilikataliwa (zinaweza kusababisha
    uchanganyifu)
  - Hakuna haja ya utaratibu kamili wa Nguvu

Kumbuka: Jina la darasa linaendelea kuwa `Triple` licha ya kuwa quad sasa.
Hii inazuia mabadiliko na "triple" bado ni terminolojia ya kawaida.
Mazingira ya picha ni metadata kuhusu mahali ambapo triple inakaa.

### Mfano wa Maswali Yanayowezekana

Msimu wa maswali unaokubaliwa hivi sasa unachanganya masharti ya S, P, O.
Katika quoted triples, triple yenyewe inakuwa nguvu halali katika
maeneo hayo. Hapa chini kuna mifano ya maswali yanayodumisha malengo
yaliyoelezwa.

#### Semantika ya Paramu ya Picha

Kufuata makubaliano ya SPARQL kwa utangamano wa kurudi nyuma:

- **`g` imepunguzwa / None**: Huuliza picha ya chaguo-msingi pekee
- **`g` = IRI maalum**: Huuliza picha hiyo maalum pekee
- **`g` = wildcard / `*`**: Huuliza katika picha zote (inalingana na
  SPARQL `GRAPH ?g { ... }`)

Hii inaendelea na maswali rahisi rahisi na inafanya maswali ya picha
kuwa ya hiari.

Maswali ya picha (g=wildcard) yanasaidiwa kikamilifu. Cassandra schema
inajumuisha jedwali maalum (SPOG, POSG, OSPG) ambapo g ni nguzo ya
kugandana badala ya nguzo ya sehemu, na inaruhusu maswali ya ufanisi
katika picha zote.

#### Maswali ya Muda

**Kutafuta ukweli wote ambao uligunduliwa baada ya tarehe fulani:**
```
S: ?                                    # triple yoyote iliyotiwa nukuu
P: <discoveredOn>
O: > "2024-01-15"^^xsd:date
G: null
```
**Kumbuka:** `^^xsd:date` inahitajika ili kuonyesha kuwa `2024-01-15` ni
tarehe, si kamba.

**Kumbuka:** Huwezi kuuliza "tafuta triples ambapo kieleuzo cha mada ya
triple iliyotiwa nukuu ni X"

#### Maswala ya Chanzo/Asili

```python
# Tafuta ukweli ambao umeungwa mkono na chanzo X
# Tafuta taarifa ambapo chanzo ni X
# Tafuta masharti ambapo chanzo ni X
```

#### Maswala ya Ukweli/Amani

```python
# Tafuta maelezo ambayo yamesemwa kuwa ni kweli
# Tafuta masharti ambapo ukweli ni kweli
# Tafuta maelezo ambayo yamesemwa kuwa ni kweli
```

Vitu vyote vyote vya RDF vinaruhusiwa, ikiwa ni pamoja na maneno ya
mtumiaji. Mkakati: epuka kuweka kitu chochote kilichofungwa isipokuwa
linapohitajika.

## Masuala ya Usalama

Picha hazina kipengele cha usalama. Watumiaji na makusudi ndio mipaka
ya usalama. Picha ni tu kwa shirika la data na usaidizi wa ufufunzaji.

## Masuala ya Utendaji

- Triples zilizotiwa nukuu zinaongeza kina cha kuziba - zinaweza kuathiri
  utendaji wa maswali
- Mikakati ya ufuataji wa picha inahitajika kwa maswali ya picha
- Muundo wa schema ya Cassandra utahitaji kuweka nafasi kwa uhifadhi
  wa quad kwa ufanisi

### Kikomo cha Hifadhi ya Vector

Hifadhi za vector daima zinaunga mkono IRIs pekee:
- Kamwe ukingo (triples zilizotiwa nukuu)
- Kamwe maadili
- Kamwe nodi tupu

Hii inahifadhi hifadhi ya vector kuwa rahisi - inashughulikia utangamano
wa kimaana wa vitu vilivyoainishwa. Muundo wa grafu hushughulikia
mahusiano, ufufunzaji, na metadata. Triples zilizotiwa nukuu na picha
hazichanganyishi shughuli za vector.

## Mkakati wa Majaribio

Tumia mkakati wa sasa wa majaribio. Kwa kuwa hii ni mabadiliko ambayo
yanaweza kusababisha utosoni, zingatia sana seti ya majaribio ya mwisho
ku hakikisha kwamba miundo mipya inafanya kazi vizuri katika vipengele
vyote.

## Mpango wa Uhamishaji

- 2.0 ni toleo ambalo linaweza kusababisha utosoni; hakuna utangamano
  wa kurudi nyuma unaohitajika
- Data iliyopo inaweza kuhitaji uhamishaji kwenye schema mpya (itaamuliwa
  kulingana na muundo wa mwisho)
- Tafadhali fikiria zana za uhamishaji kwa ajili ya kubadilisha triples
  zilizo zilizopo.

## Masuala yaliyowazi

- **Nodi tupu**: Usaidizi mdogo umeanzishwa. Inaweza kuhitaji uamuzi wa
  mkakati wa skolemization (kuunda IRIs wakati wa kupakua, au kudumisha
  vitambulisho vya nodi tupu).
- **Mbinu ya maswali**: Mbinu halisi ya kutaja triples zilizotiwa nukuu
  katika maswali ni nini? Tafadhali define API ya swali.
- ~~**Sanaa ya kieleuzo**~~: Limeelekezwa. Maneno yoyote ya RDF yanaruhusiwa,
  pamoja na maneno ya mtumiaji. Vipengele vichache tu vya kufungwa (k.m.,
  rdfs:label inatumiwa katika baadhi ya maeneo).
  Mkakati: epuka kufunga kitu chochote isipokuwa kinapohitajika.
- ~~**Athari ya hifadhi ya vector**~~: Limeelekezwa. Hifadhi za vector
  daima zinarejelea IRIs pekee - kamwe ukingo, maadili, au nodi tupu.
  Triples zilizotiwa nukuu na ufufunzaji hazisababishi hifadhi ya vector.
- ~~**Semantika ya picha**~~: Limeelekezwa. Maswali huanguka chaguo-msingi
  kwenye picha ya chaguo-msingi (inalingana na tabia ya SPARQL, inafaa
  kurudi nyuma). Paramu halisi ya picha inahitajika kuuliza picha
  zilizoainishwa au picha zote.

## Marejeo

- [Mawazo ya RDF 1.2](https://www.w3.org/TR/rdf12-concepts/)
- [RDF-star na SPARQL-star](https://w3c.github.io/rdf-star/)
- [RDF Dataset](https://www.w3.org/TR/rdf11-concepts/#section-dataset)
