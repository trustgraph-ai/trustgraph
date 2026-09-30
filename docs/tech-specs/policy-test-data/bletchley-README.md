# GC&CS Bletchley Park — Policy Test Data

Test data for validating the policy filtering engine against
a signals intelligence compartmentalisation scenario based on
the Government Code and Cypher School at Bletchley Park, WWII.

## Files

| File | Contents |
|------|----------|
| `bletchley-graph.ttl` | Knowledge graph: sections, operations, reports, methods, personnel |
| `bletchley-policies.ttl` | SHACL-AF policy shapes stored in `urn:graph:policy` |
| `bletchley-contexts.py` | Python `UserContext` instances for each test persona |

## Scenario

GC&CS at Bletchley Park operated under extreme
compartmentalisation. Personnel in one Hut typically had no
knowledge of work in adjacent Huts. The intelligence product
(translated decrypts) was separated from the cryptanalytic
methods used to produce it.

The graph contains four tiers of data:

- **Restricted** — staff rosters, billeting, transport
- **Secret** — operational intelligence, reports, Bombe menus
  (compartmentalised by section)
- **Most Secret** — cryptanalytic methods, machine designs,
  Enigma wiring diagrams
- **Ultra** — Colossus specifications, dissemination protocols,
  Y Station network, source protection assessments

Key policy axes:

- **Hut compartmentalisation** — Hut 6 cannot see Hut 8,
  Testery cannot see ISK, etc.
- **Classification clearance** — Most Secret requires explicit
  clearance
- **Ultra barrier** — Ultra access is a hard security boundary
- **Methods/sources separation** — intelligence analysts see
  the product but never the methods

## Sections

| Section | Function | Target |
|---------|----------|--------|
| Hut 6 | Cryptanalysis | Wehrmacht/Luftwaffe Enigma |
| Hut 8 | Cryptanalysis | Kriegsmarine Enigma |
| Hut 3 | Intelligence Analysis | Army/Air Force decrypts |
| Hut 4 | Intelligence Analysis | Naval decrypts |
| Hut 11 | Machine Operations | Bombe runs for Hut 6 and 8 |
| Testery | Cryptanalysis | Lorenz (Tunny) hand-breaking |
| Newmanry | Machine Cryptanalysis | Lorenz via Colossus |
| ISK | Cryptanalysis | Abwehr Enigma |
| Directorate | Command | Full oversight |

## Test Personas

| Persona | Role | Section | Key Context |
|---------|------|---------|-------------|
| Margaret | Intelligence Analyst | Hut 3 | Secret clearance; sees product not methods |
| Alan | Section Head / Cryptanalyst | Hut 8 | Most Secret clearance; Naval Enigma |
| Dorothy | Bombe Operator | Hut 11 | Secret clearance; serves Hut 6 and 8 |
| Cdr Bradshaw | Liaison Officer | Admiralty (ext.) | Liaison assignment to Hut 4 |
| Travis | Director | Directorate | Ultra clearance; full override authority |

## Expected Policy Evaluations

| Who | Query | Expected Result | Determination | Rationale |
|-----|-------|-----------------|---------------|-----------|
| Margaret | Hut 3 intelligence summaries | Reports returned | **Allowed** | Own section, correct clearance |
| Margaret | Hut 6 Bombe menus | Not returned | **Filtered** | Methods/sources separation: analysts must not see cryptanalytic material |
| Margaret | Hut 8 naval reports | Not returned | **Filtered** | Compartmentalisation: wrong section |
| Margaret | Colossus design specs | Access blocked | **Violation** | Ultra barrier: no Ultra clearance |
| Alan | Hut 8 Bombe menus (Shark) | Menus returned | **Allowed** | Own section, Most Secret clearance |
| Alan | Banburismus method | Method returned | **Allowed** | Own section, Most Secret clearance, own invention |
| Alan | Hut 6 Kursk reports | Not returned | **Filtered** | Compartmentalisation: wrong section |
| Alan | Colossus design specs | Access blocked | **Violation** | Ultra barrier: no Ultra clearance |
| Dorothy | Bombe operating procedures | Procedures returned | **Allowed** | Own section, Most Secret material but Hut 11 |
| Dorothy | Hut 3 intelligence summaries | Not returned | **Filtered** | Compartmentalisation: Bombe operators see menus, not product |
| Dorothy | Colossus design specs | Access blocked | **Violation** | Ultra barrier: no Ultra clearance |
| Bradshaw | Hut 4 U-boat dispositions | Report returned | **Allowed** | Liaison assignment to Hut 4 |
| Bradshaw | Hut 8 cryptanalytic reports | Not returned | **Filtered** | Methods/sources separation + compartmentalisation |
| Bradshaw | Hut 3 Army intelligence | Not returned | **Filtered** | Compartmentalisation: liaison covers Hut 4 only |
| Bradshaw | Ultra dissemination protocol | Access blocked | **Violation** | Ultra barrier: no Ultra clearance |
| Travis | Colossus design specs | Specs returned | **Allowed** | Director with Ultra clearance and override authority |
| Travis | Hut 8 naval reports | Reports returned | **Allowed** | Directorate has cross-section oversight |
| Travis | Ultra source protection report | Report returned | **Allowed** | Ultra clearance + UltraDissemination override |
| Travis | Staff roster | Roster returned | **Allowed** | Restricted data, accessible to all |
