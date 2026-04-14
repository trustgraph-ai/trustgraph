---
layout: default
title: "Query Time Explainability.He"
parent: "Hebrew (Beta)"
---

> **Beta Translation:** This document was translated via Machine Learning and as such may not be 100% accurate. All non-English languages are currently classified as Beta.

## הסבר על יכולת הסבר בזמן שאילתה

## סטטוס

יישום

## סקירה כללית

מפרט זה מתאר כיצד GraphRAG מתעד ומעביר נתוני הסבר במהלך ביצוע שאילתה. המטרה היא מעקב מלא: מהתשובה הסופית בחזרה דרך הקצוות שנבחרו לתיקי המסמכים המקוריים.

הסבר בזמן שאילתה לוכד מה שהצינור של GraphRAG עשה במהלך ההיגיון. הוא מתחבר להקשר של ביצוע שאילתה, אשר מתעד היכן העובדות בגרף הידע מקורות.

## מונחים

| מונח | הגדרה |
|---|---|
| **הסבר** | תיעוד של איך התוצאה הושגה |
| **סשן** | ביצוע שאילתה בודד של GraphRAG |
| **בחירת קצה** | בחירה מבוססת LLM של קצוות רלוונטיים עם היגיון |
| **שרשרת הקשר** | נתיב מ-קצה → חתיכה → עמוד → מסמך |

## ארכיטקטורה

### זרימת הסבר

```
שאילת GraphRAG
    │
    ├─► פעילות סשן
    │       └─► טקסט שאילתה, חותם זמן
    │
    ├─► ישות אחזור
    │       └─► כל הקצוות שנשלפו מהסובגרף
    │
    ├─► ישות בחירה
    │       └─► קצוות שנבחרו עם היגיון LLM
    │           └─► כל קצה מקושר להקשר של הסרת מידע
    │
    └─► ישות תשובה
            └─► הפניה לתשובה שנוצרה (בספריית הניהול)
```

### צינור GraphRAG בשני שלבים

1. **בחירת קצה:** LLM בוחר קצוות רלוונטיים מהסובגרף, ומספק הסבר לכל אחד
2. **סינתזה:** LLM מייצר תשובה מקצוות שנבחרו בלבד

ההפרדה מאפשרת הסבר - אנחנו יודעים בדיוק אילו קצוות תרמו.

### אחסון

- טריפלי הסבר מאוחסנים בספרייה שניתן להגדיר (ברירת מחדל: `explainability`)
- משתמש ב-אונטולוגיה של PROV-O ליחסי הקשר
- ייצוג RDF-star עבור הפניות לקצוות
- תוכן התשובה מאוחסן בשירות הספרייה (לא באופן ישיר - גדול מדי)

### סטרימינג בזמן אמת

אירועי הסבר זורמים ללקוח בזמן ביצוע השאילתה:

1. סשן נוצר → הודעה נשלחת
2. קצוות נשלפים → הודעה נשלחת
3. קצוות נבחרו עם הסבר → הודעה נשלחת
4. תשובה נוצרה → הודעה נשלחת

הלקוח מקבל `explain_id` ו-`explain_collection` כדי לשלוף פרטים מלאים.

## מבנה URI

כל ה-URIs משתמשים בשם מרחב שמות `urn:trustgraph:`, עם UUIDs:

| ישות | תבנית URI |
|---|---|
| סשן | `urn:trustgraph:session:{uuid}` |
| אחזור | `urn:trustgraph:prov:retrieval:{uuid}` |
| בחירה | `urn:trustgraph:prov:selection:{uuid}` |
| תשובה | `urn:trustgraph:prov:answer:{uuid}` |
| בחירת קצה | `urn:trustgraph:prov:edge:{uuid}:{index}` |

## מודל RDF (PROV-O)

### פעילות סשן

```turtle
<session-uri> a prov:Activity ;
    rdfs:label "שאילת GraphRAG" ;
    prov:startedAtTime "2024-01-15T10:30:00Z" ;
    tg:query "מה היה מלחמת הטרור?" .
```

### ישות אחזור

```turtle
<retrieval-uri> a prov:Entity ;
    rdfs:label "קצוות שאובים" ;
    prov:wasGeneratedBy <session-uri> ;
    tg:edgeCount 50 .
```

### ישות בחירה

```turtle
<selection-uri> a prov:Entity ;
    rdfs:label "קצוות שנבחרו" ;
    prov:wasDerivedFrom <retrieval-uri> ;
    tg:selectedEdge <edge-sel-0> ;
    tg:selectedEdge <edge-sel-1> .

<edge-sel-0> tg:edge << <s> <p> <o> >> ;
    tg:reasoning "קצה זה מייצג את הקשר המרכזי..." .
```

### ישות תשובה

```turtle
<answer-uri> a prov:Entity ;
    rdfs:label "תשובת GraphRAG" ;
    prov:wasDerivedFrom <selection-uri> ;
    tg:document <urn:trustgraph:answer:{uuid}> .
```

הפניה `tg:document` מתייחסת לתשובה המאוחסנת בשירות הספרייה.

## קבועי מרחב שמות

מוגדרים ב-`trustgraph-base/trustgraph/provenance/namespaces.py`:

| קבוע | URI |
|---|---|
| `TG_QUERY` | `https://trustgraph.ai/ns/query` |
| `TG_EDGE_COUNT` | `https://trustgraph.ai/ns/edgeCount` |
| `TG_SELECTED_EDGE` | `https://trustgraph.ai/ns/selectedEdge` |
| `TG_EDGE` | `https://trustgraph.ai/ns/edge` |
| `TG_REASONING` | `https://trustgraph.ai/ns/reasoning` |
| `TG_CONTENT` | `https://trustgraph.ai/ns/content` |
| `TG_DOCUMENT` | `https://trustgraph.ai/ns/document` |

## תרשים GraphRagResponse

```python
@dataclass
class GraphRagResponse:
    error: Error | None = None
    response: str = ""
    end_of_stream: bool = False
    explain_id: str | None = None
    explain_collection: str | None = None
    message_type: str = ""  # "chunk" or "explain"
    end_of_session: bool = False
```

### סוגי הודעות

| message_type | מטרת |
|---|---|
| `chunk` | טקסט תגובה (זרם או סופי) |
| `explain` | אירוע הסבר עם הפניה IRI |

### מחזור חיים של סשן

1. מספר הודעות `explain` (סשן, אחזור, בחירה, תשובה)
2. מספר הודעות `chunk` (טקסט זרם)
3. הודעת `chunk` סופית עם `end_of_session=True`

## פורמט בחירת קצה

LLM מחזיר JSONL עם הקצוות שנבחרו:

```jsonl
{"id": "edge-hash-1", "reasoning": "קצה זה מראה את הקשר המרכזי..."}
{"id": "edge-hash-2", "reasoning": "מספק ראיות תומכות..."}
```

ה-`id` הוא פאש של `(labeled_s, labeled_p, labeled_o)`
ה-`reasoning` הוא הסבר של ה-LLM.

## יישומים

- `docs/tech-specs/extraction-time-provenance.md`
