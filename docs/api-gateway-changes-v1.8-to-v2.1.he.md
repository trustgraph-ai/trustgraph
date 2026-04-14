---
layout: default
title: "שינויים ב-API Gateway: v1.8 ל-v2.1"
parent: "Hebrew (Beta)"
---

# שינויים ב-API Gateway: v1.8 ל-v2.1

> **Beta Translation:** This document was translated via Machine Learning and as such may not be 100% accurate. All non-English languages are currently classified as Beta.

## תקציר

ה-API Gateway קיבל ספקי שירות WebSocket חדשים עבור שאילתות של "embeddings", סוף שירות REST חדש להעברת תוכן מסמך, וכן שינוי משמעותי בפורמט של קוד: מ-"Value" ל-"Term". השירות "objects" שונה לשם "rows".

---

## ספקי שירות WebSocket חדשים

אלו הם שירותי בקשה/תגובה חדשים הזמינים דרך המולטיפלקסר של WebSocket בכתובת `/api/v1/socket` (הקשור למערכת זרימה):

| מפתח שירות | תיאור |
|---|---|
| `document-embeddings` | מבקש חלקים של מסמך על סמך דמיון טקסט. הבקשה/תגובה משתמשים בתבניות `DocumentEmbeddingsRequest`/`DocumentEmbeddingsResponse`. |
| `row-embeddings` | מבקש שורות של נתונים מובנים על סמך דמיון טקסט בשדות המצביעים. הבקשה/תגובה משתמשות בתבניות `RowEmbeddingsRequest`/`RowEmbeddingsResponse`. |

הם מצטרפים למספק הקיים `graph-embeddings` (שהיה קיים כבר ב-v1.8 אך ייתכן ששונה),

### רשימה מלאה של ספקי שירות זרימה של WebSocket (v2.1)

שירותי בקשה/תגובה (דרך `/api/v1/flow/{flow}/service/{kind}` או מולטיפלקסר WebSocket):

- `agent`, `text-completion`, `prompt`, `mcp-tool`
- `graph-rag`, `document-rag`
- `embeddings`, `graph-embeddings`, `document-embeddings`
- `triples`, `rows`, `nlp-query`, `structured-query`, `structured-diag`
- `row-embeddings`

---

## סוף שירות REST חדש

| שיטה | נתיב | תיאור |
|---|---|---|
| `GET` | `/api/v1/document-stream` | מעביר תוכן מסמך מהספרייה כביטים גולמיים. פרמטרי שאילתה: `user` (חובה), `document-id` (חובה), `chunk-size` (אופציונלי, ברירת מחדל 1MB). מחזיר את תוכן המסמך בתבנית העברת ביטים, לאחר פעולת Base64 פנימית. |

---

## שינוי שם שירות: "objects" ל-"rows"

| v1.8 | v2.1 | הערות |
|---|---|---|
| `objects_query.py` / `ObjectsQueryRequestor` | `rows_query.py` / `RowsQueryRequestor` | התבנית שונתה מ-`ObjectsQueryRequest`/`ObjectsQueryResponse` ל-`RowsQueryRequest`/`RowsQueryResponse`. |
| `objects_import.py` / `ObjectsImport` | `rows_import.py` / `RowsImport` | ספק ייבוא לנתונים מובנים. |

מפתח השירות של WebSocket שונה מ-"objects" ל-"rows", וממילא מפתח ספק הייבוא שונה מ-"objects" ל-"rows".

---

## שינוי פורמט קוד: Value ל-Term

שכבת הסריאליזציה (`serialize.py`) שונתה כדי להשתמש בסוג ה-"Term" החדש במקום בסוג ה-"Value" הישן.

### פורמט ישן (v1.8 — Value)

```json
{"v": "http://example.org/entity", "e": true}
```

- `v`: הערך (מחרוזת)
- `e`: דגל בוליאני המציין אם הערך הוא URI

### פורמט חדש (v2.1 — Term)

- IRI:
```json
{"t": "i", "i": "http://example.org/entity"}
```
- רשימות:
```json
{"t": "l", "v": "some text", "d": "datatype-uri", "l": "en"}
```
- טריפלים מוערים (RDF-star):
```json
{"t": "r", "r": {"s": {...}, "p": {...}, "o": {...}}}
```

- `t`: מחלקת סוג — `"i"` (IRI), `"l"` (רשימה), `"r"` (טריפל מוער), `"b"` (צומת ריק)
- הסריאליזציה כעת מקפלת ל-`TermTranslator` ו-`TripleTranslator` מ-`trustgraph.messaging.translators.primitives

### שינויי סריאליזציה אחרים

| שדה | v1.8 | v2.1 |
|---|---|---|
| Metadata | `metadata.metadata` (סופר-גרף) | `metadata.root` (ערך פשוט) |
| סוגי embeddings | `entity.vectors` (רשימה) | `entity.vector` (יחיד) |
| חלקים של embeddings | `chunk.vectors` + `chunk.chunk` (טקסט) | `chunk.vector` + `chunk.chunk_id` (מזהה התייחסות) |

---

## שינויים משמעותיים

- **פורמט קוד Value ל-Term:** כל לקוחות המשדרים/מקבלים טריפלים, embeddings או הקשרים של ישויות דרך ה-gateway צריכים לעדכן לפורמט ה-Term החדש.
- **שינוי שם של "objects" ל-"rows":** שינוי מפתח שירות של WebSocket ומפתח ייבוא.
- **שינוי שדה Metadata:** `metadata.metadata` (גרף סריאלי) הוחלף ב-`metadata.root` (ערך פשוט).
- **שינויים בשדות Embeddings:** `vectors` (רשימה) הפך ל-`vector` (יחיד); embeddings של מסמכים כעת מתייחסים ל-`chunk_id` במקום הטקסט של ה-`chunk`
- **סוף שירות חדש `/api/v1/document-stream`**: נוסף, לא משבש.
