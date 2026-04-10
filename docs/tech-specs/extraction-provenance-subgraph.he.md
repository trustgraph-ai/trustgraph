# מקור החילוץ: מודל תת-גרף

## בעיה

מעקב מקורות מידע בזמן החילוץ מייצר כיום מימוש מלא לכל טריפל
שחולץ: `stmt_uri` ייחודי, `activity_uri` ו-מטא-דאטה של PROV-O עבור כל
עובדה ידע בודדת. עיבוד של חלק אחד שמייצר 20 קשרים מייצר כ-220
טריפלי מעקב מקורות מידע בנוסף ל-כ-20 טריפלי ידע - תקורה של בערך 10:1.


זה יקר (אחסון, אינדקס, העברה) וגם לא מדויק מבחינה סמנטית. כל חלק
מעובד על ידי קריאה אחת של מודל שפה גדול (LLM) שמייצר את כל
הטריפלים שלו בעסקה אחת. המודל הנוכחי של טריפל בודד מטשטש את זה
על ידי יצירת האשליה של 20 אירועי חילוץ עצמאיים.


בנוסף, לשני מתוך ארבעה מעבדי החילוץ (kg-extract-ontology,
kg-extract-agent) אין מעקב מקורות מידע כלל, מה שמשאיר פערים
במסלול הביקורת.

## פתרון

החליפו את הפירוט של כל שלישייה במודל תת-גרף: רשומת מוצא אחת לכל חילוץ, המשותפת לכל השלישיות שנוצרו מחלק זה.


### שינוי מונחים


| ישן | חדש |
|-----|-----|
| `stmt_uri` (`https://trustgraph.ai/stmt/{uuid}`) | `subgraph_uri` (`https://trustgraph.ai/subgraph/{uuid}`) |
| `statement_uri()` | `subgraph_uri()` |
| `tg:reifies` (1:1, זהות) | `tg:contains` (1:רבים, הכלה) |

### מבנה מטרה

כל השלישיות של המוצא נכנסות לגרף המקוּם בשם `urn:graph:source`.

```
# Subgraph contains each extracted triple (RDF-star quoted triples)
<subgraph> tg:contains <<s1 p1 o1>> .
<subgraph> tg:contains <<s2 p2 o2>> .
<subgraph> tg:contains <<s3 p3 o3>> .

# Derivation from source chunk
<subgraph> prov:wasDerivedFrom <chunk_uri> .
<subgraph> prov:wasGeneratedBy <activity> .

# Activity: one per chunk extraction
<activity> rdf:type          prov:Activity .
<activity> rdfs:label        "{component_name} extraction" .
<activity> prov:used         <chunk_uri> .
<activity> prov:wasAssociatedWith <agent> .
<activity> prov:startedAtTime "2026-03-13T10:00:00Z" .
<activity> tg:componentVersion "0.25.0" .
<activity> tg:llmModel       "gpt-4" .          # if available
<activity> tg:ontology        <ontology_uri> .   # if available

# Agent: stable per component
<agent> rdf:type   prov:Agent .
<agent> rdfs:label "{component_name}" .
```

### השוואת נפחים

עבור קטע המייצר N משולשים חילוצים:

| | ישן (למשולש) | חדש (תת-גרף) |
|---|---|---|
| `tg:contains` / `tg:reifies` | N | N |
| משולשי פעילות | ~9 x N | ~9 |
| משולשי סוכנים | 2 x N | 2 |
| מטא-נתונים של הצהרה/תת-גרף | 2 x N | 2 |
| **סה"כ משולשי מקור** | **~13N** | **N + 13** |
| **דוגמה (N=20)** | **~260** | **33** |

## היקף

### מעבדים לעדכון (מקור קיים, לכל משולש)

**kg-extract-definitions**
(`trustgraph-flow/trustgraph/extract/kg/definitions/extract.py`)

כיום קורא ל-`statement_uri()` + `triple_provenance_triples()` בתוך
הלולאה לכל הגדרה.

שינויים:
העברת יצירת `subgraph_uri()` ו-`activity_uri()` לפני הלולאה
איסוף משולשי `tg:contains` בתוך הלולאה
פליטת בלוק פעילות/סוכן/הסקה משותף פעם אחת לאחר הלולאה

**kg-extract-relationships**
(`trustgraph-flow/trustgraph/extract/kg/relationships/extract.py`)

דפוס זהה כמו הגדרות. שינויים זהים.

### מעבדים להוספת מקור (חסרים כרגע)

**kg-extract-ontology**
(`trustgraph-flow/trustgraph/extract/kg/ontology/extract.py`)

כיום פולט משולשים ללא מקור. הוספת מקור תת-גרף
באמצעות הדפוס הזהה: תת-גרף אחד לכל קטע, `tg:contains` עבור כל
משולש חילוץ.

**kg-extract-agent**
(`trustgraph-flow/trustgraph/extract/kg/agent/extract.py`)

כיום פולט משולשים ללא מקור. הוספת מקור תת-גרף
באמצעות הדפוס הזהה.

### שינויים בספריית המקור המשותפת

**`trustgraph-base/trustgraph/provenance/triples.py`**

החלפת `triple_provenance_triples()` עם `subgraph_provenance_triples()`
פונקציה חדשה מקבלת רשימה של משולשים חילוצים במקום משולש בודד
מייצרת `tg:contains` אחד לכל משולש, בלוק פעילות/סוכן משותף
הסרת `triple_provenance_triples()` הישן

**`trustgraph-base/trustgraph/provenance/uris.py`**

החלפת `statement_uri()` עם `subgraph_uri()`

**`trustgraph-base/trustgraph/provenance/namespaces.py`**

החלפת `TG_REIFIES` עם `TG_CONTAINS`

### לא בתחום

**kg-extract-topics**: מעבד מסוג ישן, לא בשימוש כרגע ב
  זרימות סטנדרטיות
**kg-extract-rows**: מייצר שורות ולא משולשים, מודל מקור
  שונה
**מקור בזמן שאילתה** (`urn:graph:retrieval`): נושא נפרד,
  כבר משתמש בדפוס שונה (שאילתה/חקירה/מיקוד/סינתזה)
**מקור של מסמך/עמוד/קטע** (מקודד PDF, מפצל): כבר משתמש
  ב-`derived_entity_triples()` שהוא לכל ישות, ולא לכל משולש — אין
  בעיית יתירות

## הערות יישום

### שינוי מבנה הלולאה של המעבד

לפני (לכל משולש, ביחסים):
```python
for rel in rels:
    # ... build relationship_triple ...
    stmt_uri = statement_uri()
    prov_triples = triple_provenance_triples(
        stmt_uri=stmt_uri,
        extracted_triple=relationship_triple,
        ...
    )
    triples.extend(set_graph(prov_triples, GRAPH_SOURCE))
```

אחרי (תת-גרף):
```python
sg_uri = subgraph_uri()

for rel in rels:
    # ... build relationship_triple ...
    extracted_triples.append(relationship_triple)

prov_triples = subgraph_provenance_triples(
    subgraph_uri=sg_uri,
    extracted_triples=extracted_triples,
    chunk_uri=chunk_uri,
    component_name=default_ident,
    component_version=COMPONENT_VERSION,
    llm_model=llm_model,
    ontology_uri=ontology_uri,
)
triples.extend(set_graph(prov_triples, GRAPH_SOURCE))
```

### חתימה חדשה של עוזר

```python
def subgraph_provenance_triples(
    subgraph_uri: str,
    extracted_triples: List[Triple],
    chunk_uri: str,
    component_name: str,
    component_version: str,
    llm_model: Optional[str] = None,
    ontology_uri: Optional[str] = None,
    timestamp: Optional[str] = None,
) -> List[Triple]:
    """
    Build provenance triples for a subgraph of extracted knowledge.

    Creates:
    - tg:contains link for each extracted triple (RDF-star quoted)
    - One prov:wasDerivedFrom link to source chunk
    - One activity with agent metadata
    """
```

### שינוי משמעותי

זוהי שינוי משמעותי במודל המקור. המקור טרם פורסם, ולכן אין צורך בביצוע שדרוג. ניתן להסיר את קוד ⟦CODE_0⟧ /
`tg:reifies` הישן לחלוטין.
קוד `statement_uri` ניתן להסרה לחלוטין.
