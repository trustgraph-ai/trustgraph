**MAELEZI MUHIMU:**

- Hifadhi KILA muundo wa Markdown, vichwa, viungo, na alama za HTML.
- EISI tafsiri code ndani ya ` ` au katika mistari ya code.
- Toa KAMA, tu maandishi iliyotumwa bila maelezo au maelekezo.

Maandishi ya kutafsiri:

# Kuunda hati moja kwa moja

## Ufafanuzi wa API za REST na WebSocket

- `specs/build-docs.sh` - Inaunda hati za REST na WebSocket kutoka kwenye
  maelezo za OpenAPI na AsyncAPI.

## Ufafanuzi wa API ya Python

Ufafanuzi wa API ya Python unaoandaliwa kutoka kwa maelezo (docstrings) kwa kutumia skripti ya Python inayotumia, ambayo inaangalia pakiti `trustgraph.api`.

### Vigezo

Pakiti ya trustgraph lazima iweze kuagizwa. Ikiwa unatumia mazingira ya utengenezaji:

```bash
cd trustgraph-base
pip install -e .
```

### Kuunda hati

Kutoka kwenye orodha ya hati:

```bash
cd docs
python3 generate-api-docs.py > python-api.md
```

Hii inaunda faili moja ya markdown yenye hati kamili ya API, inayoeleza:
- Mwongozo wa usanidi na wa kuanza
- Maelezo za kuagiza kwa kila sinema/aina
- Maelezo kamili (docstrings) na mifano
- Orodha ya maudhui iliyopangwa kwa kategoria

### Mtindo wa hati

Maelezo yote (docstrings) yanatumia mtindo wa Google:
- Muhtasari wa mstari moja
- Maelezo kamili
- Kitengo cha "Args" na maelezo ya thamani
- Kitengo cha "Returns"
- Kitengo cha "Raises" (kama inatumika)
- Mistari ya code na umbo sahihi

Hati iliyoundwa inaonyesha API iliyo na umbo, kama watumiaji wanavyoagiza kutoka kwa `trustgraph.api`, bila kuonyesha muundo wa moduli.