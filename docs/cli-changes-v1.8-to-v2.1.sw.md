**MAELEMAZO MAKUUUUU:**
- Hifadhi FORMATI YOTE ya Markdown, vichungi, viungo na alama za HTML.
- Usitafsiri code ndani ya apostrophe au makundi ya code.
- Onyesho TU MAELEZO bila maelezo au maelezo.

MAELEZO YA KUTAFSIRI:
# Mabadiliko ya CLI: v1.8 hadi v2.1

## Muhtasari

CLI (`trustgraph-cli`) ina ongezeko kubwa, iliyoangazia vipande tatu:
**ufafanuzi/asili,** **ufaa wa data,** na **utafutaji wa graphs.**
Zochorwa zote, mojawapo ilibadilishwa, na zochorwa za soko zimepata uwezo mpya.

---

## Zochorwa Mpya za CLI

### Ufafanuzi na Asili
| Amri | Maelezo |
|---------|-------------|
| `tg-list-explain-traces` | Inaorodha zote za ufafanuzi (GraphRAG na Agent) katika mkusanyiko, inaonyesha ID za mkusanyiko, aina, maandishi ya swali, na tarehe. |
| `tg-show-explain-trace` | Inaonyesha mstari kamili wa ufafanuzi kwa mkusanyiko. Kwa GraphRAG: Swali, Tafuta, Futa, na Safu za Mfumo. Kwa Agent: Mkusanyiko, Iterasi (fikra/hatua/taarifa), Jibu. Inaagizwa moja kwa moja. Inaunga mkono `--show-provenance` ili kurudisha miisho kwenye hati za asili. |
| `tg-show-extraction-provenance` | Ikiwa na ID ya hati, inaendesha mkondo wa asili: Hati -> Kurasa -> Chunks -> Miisho, kwa kutumia mahusiano ya `prov:wasDerivedFrom`. Inaunga mkono chaguzi `--show-content` na `--max-content`. |

### Data
| Amri | Maelezo |
|---------|-------------|
| `tg-invoke-embeddings` | Hufanya maandishi kuwa na upinzani wa vector kupitia huduma ya upinzani. Inasoma moja au zaidi maandishi, inaondoa vipindi kama orodha. |
| `tg-invoke-graph-embeddings` | Inaweka maandishi na graphs kupitia upinzani. Inaondoa vipindi kama orodha. |
| `tg-invoke-document-embeddings` | Inaweka maandishi kupitia upinzani. Inaondoa vipindi kama orodha. |
| `tg-invoke-row-embeddings` | Inaweka data iliyoandaliwa kupitia upinzani. Inaondoa vipindi kama orodha. |

### Tafutaji wa Graphs

| Amri | Maelezo |
|---------|-------------|
| `tg-query-graph` | Tafutaji la triple store. Mbali na `tg-show-graph` (ambayo inatumia kila kitu), inawezesha tafuta maalum kwa uwingi wa majimbo, mahusiano, na graphs. Inaagiza orodha moja kwa moja. Inaunga mkono `http://...`, `urn:...`, na `<...>`. |
| `tg-get-document-content` | Inaagiza maudhui ya hati kutoka kwenye library kupitia ID ya hati. Inaweza kuonyesha kwenye faili au stdout, na inaweza kuuza maandishi na data. |

---

## Zochorwa Zilizoondolewa za CLI

| Amri | Maelezo |
|---------|-------|
| `tg-load-pdf` | Imeondolewa. Utoaaji wa hati sasa unaendesha kupitia pipeline ya library/utumiaji. |
| `tg-load-text` | Imeondolewa. Utoaaji wa hati sasa unaendesha kupitia pipeline ya library/utumiaji. |

---

## Zochorwa Zilizo badilishwa za CLI

| Jina la Zamani | Jina la mpya | Maelezo |
|----------|----------|-------|
| `tg-invoke-objects-query` | `tg-invoke-rows-query` | Ina maelezo kuhusu jina. |

---

## Mabadiliko Makubwa katika Zochorwa za Soko

### `tg-invoke-graph-rag`

- **Ufafanuzi**: Sasa ina 4-stage pipeline ya ufafanuzi (Swali, Tafuta/Tafuta, Futa, Mfumo) na maonyesho ya matukio ya asili.
- **Streami**: Inaendesha WebSocket kwa matokeo ya muda halisi.
- **Ufafanuzi**: Inawezesha kufuatilia miisho kwenye hati za asili kupitia reification na miisho ya `prov:wasDerivedFrom`.
- Imebadilishwa na ~30 mistari hadi ~760 mistari ili kukidhi pipeline ya ufafanuzi.

### `tg-invoke-document-rag`

- **Ufafanuzi**: Inaongeza mode `question_explainable()` ambayo inatumia Graph RAG na maonyesho ya matukio ya asili.

### `tg-invoke-agent`

- **Ufafanuzi**: Inaongeza mode `question_explainable()` inayoeleza matukio ya asili wakati wa utumiaji wa agent (Swali, Tafuta, Mfumo, AgentThought, AgentObservation, AgentAnswer).
- Mode ya verbose inaonyesha miisho za fikra/taarifa na prefixes za emoji.

### `tg-show-graph`

- **Mode ya Streami**: Inaendesha `triples_query_stream()` na ukubwa wa chombo configurable kwa muda wa matokeo wa kwanza na uzoefu wa kughushi.
- **Uunganisho wa graph**: Mpya `--graph` chaguo. Inaagiza graphs:
  - Graph chungu (tupu): Hekalu
  - `urn:graph:source`: Asili
  - `urn:graph:retrieval`: Tafuta
- **Maonyesho ya graph**: Mpya `--show-graph` flag. Inaonyesha graph iliyochorwa kwa kila triple.
- **Ukubwa wa Chaguzi**: Mpya `--limit` na chaguzi `--batch-size`.

### `tg-graph-to-turtle`

- **RDF-star support**: Inaendesha miisho za apostrophe (RDF-star reification).
- **Mode ya Streami**: Inaendesha stream kwa muda wa matokezo wa kwanza.
- **Uhandishi wa format**: Inaendesha format mpya (`{"t": "i", "i": uri}` kwa IRIs, `{"t": "l", "v": value}` kwa literals, `{"t": "r", "r": {...}}` kwa miisho).
- **Uunganisho wa graph**: Mpya `--graph` chaguo.

### `tg-set-tool`

- **Aina mpya ya tool**: `row-embeddings-query` kwa utafutaji wa semantic kwenye data iliyoandaliwa.
- **Chaguzi mpya**: `--schema-name`, `--index-name`, `--limit` kwa kuunda zochorwa za upinzani.

### `tg-show-tools`

- Inaonyesha zochorwa za mpya za `row-embeddings-query` na chaguzi zake.

### `tg-load-knowledge`

- **Ripoti za Maendeleo**: Inahesabu na inaonyesha miisho na miisho za entity za ililoandaliwa kwa kila faili na kwa jumla.
- **Mbadilisho wa format**: Miisho za entity sasa inaformat mpya (`{"t": "i", "i": uri}`) badala ya format ya awali (`{"v": ..., "e": ...}`).

---

## Mabadiliko Masharti

- **Jina la jumla**: Jina la `Value` lilibadilishwa kuwa `Term` katika mfumo kote (PR #622). Hii inafanya na format mpya `{"t": "i", "i": uri}` kwa IRIs na `{"t": "l", "v": value}` kwa literals, badala ya format ya zamani `{"v": ..., "e": ...}`.
- **`tg-invoke-objects-query`** lilibadilishwa kuwa `tg-invoke-rows-query`.
- **`tg-load-pdf`** na **`tg-load-text`** liliondolewa.