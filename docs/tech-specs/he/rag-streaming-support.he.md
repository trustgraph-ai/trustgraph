---
layout: default
title: "תמיכה בסטרימינג של RAG - ספציפיציה טכנית"
parent: "Hebrew (Beta)"
---

# תמיכה בסטרימינג של RAG - ספציפיציה טכנית

> **Beta Translation:** This document was translated via Machine Learning and as such may not be 100% accurate. All non-English languages are currently classified as Beta.

## סקירה כללית

מסמך זה מתאר את הוספת תמיכה בסטרימינג לשירותי GraphRAG ו-DocumentRAG, המאפשרות תגובות בזמן אמת, שוט אחר שוט, עבור שאילתות שליפה של גרפי ידע ומסמכים. זה מרחיב את הארכיטקטורה הסטנדרטית לסטרימינג, אשר כבר מיושמת עבור שירותי LLM להשלמת טקסט, בקשות וסוכנים.

## מטרות

- **חוויית משתמש סטנדרטית בסטרימינג**: לספק חוויית סטרימינג אחידה בכל שירותי TrustGraph.
- **שינויים מינימליים בממשק API**: להוסיף תמיכה בסטרימינג באמצעות דגל `streaming` יחיד, תוך עמידה בדפוסי העבודה הקיימים.
- **תאימות לאחור**: לשמור על התנהגות לא סטנדרטית קיימת כברירת מחדל.
- **ניצול תשתית קיימת**: להשתמש בסטרימינג הקיים, אשר כבר מיושם עבור ה-PromptClient.
- **תמיכה בדגלים**: לאפשר סטרימינג באמצעות דגל websocket עבור יישומי לקוח.

## רקע

שירותי סטרימינג קיימים:
- **שירות השלמת טקסט של LLM**: שלב 1 - סטרימינג מספקי LLM
- **שירות בקשות**: שלב 2 - סטרימינג באמצעות תבניות בקשות
- **שירות סוכן**: שלבים 3-4 - סטרימינג של תגובות ReAct עם חלקים של מחשבה/תצפית/תשובה

מגבלות נוכחיות לשירותי RAG:
- GraphRAG ו-DocumentRAG תומכים רק בתגובות בלתי סטנדרטיות.
- משתמשים צריכים לחכות לתגובה שלמה של LLM לפני קבלת כל תוצאה.
- חוויית משתמש גרועה עבור תגובות ארוכות לשאילתות של גרפי ידע או מסמכים.
- חוויה לא עקבית בהשוואה לשירותי TrustGraph אחרים.

מסמך זה מטפל בבעיות אלו על ידי הוספת תמיכה בסטרימינג ל-GraphRAG ו-DocumentRAG. על ידי אפשרות תגובות שוט אחר שוט, TrustGraph יכול:
- לספק חוויית משתמש סטנדרטית בסטרימינג עבור כל סוגי השאילתות.
- להפחית את הפיגור הרגשי עבור שאילתות RAG.
- לאפשר משוב מתקדם עבור שאילתות ארוכות.
- לתמוך בהצגה בזמן אמת ביישומים של לקוח.

## עיצוב טכני

### ארכיטקטורה

היישום הסטנדרטי של RAG של מנצל את התשתית הקיימת:

1. **סטרימינג של PromptClient** (כבר מיושם)
   - הפרמטרים `kg_prompt()` ו-`document_prompt()` כבר מקבלים את הפרמטרים `streaming` ו-`chunk_callback`.
   - הפרמטרים אלו קוראים לפונקציה `prompt()` עם תמיכה בסטרימינג.
   - אין צורך לשנות את ה-PromptClient.
   - מודול: `trustgraph-base/trustgraph/base/prompt_client.py`

2. **שירות GraphRAG** (דורש העברת פרמטר סטרימינג)
   - להוסיף את הפרמטר `streaming` למתודה `query()`.
   - להעביר את הדגל הסטרימינג ואת ה-callbacks ל-`prompt_client.kg_prompt()`.
   - סכימת ה-GraphRagRequest צריכה לכלול את השדה `streaming`.
   - מודולים:
     - `trustgraph-flow/trustgraph/retrieval/graph_rag/graph_rag.py`
     - `trustgraph-flow/trustgraph/retrieval/graph_rag/rag.py` (Processor)
     - `trustgraph-base/trustgraph/schema/graph_rag.py` (סכימת בקשה)
     - `trustgraph-flow/trustgraph/gateway/dispatch/graph_rag.py` (Gateway)

3. **שירות DocumentRAG** (דורש העברת פרמטר סטרימינג)
   - להוסיף את הפרמטר `streaming` למתודה `query()`.
   - להעביר את הדגל הסטרימינג ואת ה-callbacks ל-`prompt_client.document_prompt()`.
   - סכימת ה-DocumentRagRequest צריכה לכלול את השדה `streaming`.
   - מודולים:
     - `trustgraph-flow/trustgraph/retrieval/document_rag/document_rag.py`
     - `trustgraph-flow/trustgraph/retrieval/document_rag/rag.py` (Processor)
     - `trustgraph-base/trustgraph/schema/document_rag.py` (סכימת בקשה)
     - `trustgraph-flow/trustgraph/gateway/dispatch/document_rag.py` (Gateway)

### זרימת נתונים

**לא סטנדרטי (נוכחי)**:
```
לקוח → דגל → שירות RAG → PromptClient.kg_prompt(streaming=False)
                       ↓
שירות בקשות → LLM
                       ↓
תגובה שלמה
                       ↓
לקוח ← דגל ← שירות RAG ← תגובה
```

**סטנדרטי (מוצע)**:
```
לקוח → דגל → שירות RAG → PromptClient.kg_prompt(streaming=True, chunk_callback=cb)
                       ↓
שירות בקשות → LLM (סטרימינג)
                       ↓
חלק → Callback → תגובת RAG (חלק)
                       ↓                       ↓
לקוח ← דגל ← ────────────────────────────────── זרם תגובה
```

### ממשקי API

**שינויים ב-GraphRAG**:

1. **GraphRag.query()** - הוספת פרמטרים סטרימינג
```python
async def query(
    self, query, user, collection,
    streaming=False, chunk_callback=None
):
    # ...
```
2. **שינויים ב-DocumentRAG**:
   - כפי שמתואר עבור GraphRAG.

### בדיקות

**בדיקות יחידות**:
- בדיקת GraphRag.query() עם `streaming=True/False`.
- בדיקת DocumentRAG.query() עם `streaming=True/False`.
- שימוש ב-Mock עבור PromptClient כדי לבדוק את קריאות ה-callbacks.

**בדיקות אינטגרציה**:
- בדיקת זרימת הסטרימינג המלאה של GraphRAG (בדיקות דומות לבדיקות סטרימינג של סוכן קיימות).
- בדיקת זרימת הסטרימינג המלאה של DocumentRAG.
- בדיקת העברת דגל ה-סטרימינג.
- בדיקת הפלט של ה-CLI עם סטרימינג.

**בדיקות ידניות**:
- `tg-invoke-graph-rag -q "מהו למידת מכונה?"` (סטרימינג כברירת מחדל).
- `tg-invoke-document-rag -q "סכם את המסמכים על AI"` (סטרימינג כברירת מחדל).
- `tg-invoke-graph-rag --no-streaming -q "..."` (בדיקת מצב לא סטנדרטי).
- בדיקה שהחלקים מופיעים בסטרימינג.

## תכנון בדיקות

**בדיקות יחידות**:
- בדיקת GraphRag.query() עם `streaming=True/False`.
- בדיקת DocumentRAG.query() עם `streaming=True/False`.
- שימוש ב-Mock עבור PromptClient כדי לבדוק את קריאות ה-callbacks.

**בדיקות אינטגרציה**:
- בדיקת זרימת הסטרימינג המלאה של GraphRAG (בדיקות דומות לבדיקות סטרימינג של סוכן קיימות).
- בדיקת זרימת הסטרימינג המלאה של DocumentRAG.
- בדיקת העברת דגל ה-סטרימינג.
- בדיקת הפלט של ה-CLI עם סטרימינג.

**בדיקות ידניות**:
- `tg-invoke-graph-rag -q "מהו למידת מכונה?"` (סטרימינג כברירת מחדל).
- `tg-invoke-document-rag -q "סכם את המסמכים על AI"` (סטרימינג כברירת מחדל).
- `tg-invoke-graph-rag --no-streaming -q "..."` (בדיקת מצב לא סטנדרטי).
- בדיקה שהחלקים מופיעים בסטרימינג.

## תכנון המיגרציה

אין צורך במיגרציה:
- הסטרימינג הוא "אופציונלי" באמצעות הפרמטר `streaming` (ברירת מחדל היא False).
- לקוחות קיימים ממשיכים לעבוד ללא שינוי.
- לקוחות חדשים יכולים לבחור בסטרימינג.

## לוח זמנים

הערכת זמן ליישום: 4-6 שעות
- שלב 1 (2 שעות): תמיכה בסטרימינג של GraphRAG.
- שלב 2 (2 שעות): תמיכה בסטרימינג של DocumentRAG.
- שלב 3 (1-2 שעות): עדכוני דגל ו-CLI.
- בדיקות: בונה לתוך כל שלב.

## שאלות פתוחות

- האם עלינו להוסיף תמיכה בסטרימינג לשירות ה-NLP Query גם כן?
- האם עלינו להזרים גם את השלבים הביניים (לדוגמה, "שליפת ישויות...", "שאילתה על הגרף...") או רק את הפלט של ה-LLM?
- האם עלינו לכלול מידע על החלקים בתגובות של RAG (לדוגמה, מספר החלק, מספר כולל צפוי)?

## מקורות

- יישום קיימת: `docs/tech-specs/streaming-llm-responses.md`
- סטרימינג של PromptClient: `trustgraph-base/trustgraph/base/prompt_client.py`
- סטרימינג של סוכן: `trustgraph-flow/trustgraph/agent/react/agent_manager.py`
