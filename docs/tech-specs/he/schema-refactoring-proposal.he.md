---
layout: default
title: "הצעה לשחזור תיקיית הסכימה"
parent: "Hebrew (Beta)"
---

# הצעה לשחזור תיקיית הסכימה

> **Beta Translation:** This document was translated via Machine Learning and as such may not be 100% accurate. All non-English languages are currently classified as Beta.

## בעיות נוכחיות

1. **מבנה שטוח** - כל הסכימות במקום אחד מקשות על הבנת הקשרים
2. **שילוב דאגות** - סוגי ליבה, אובייקטים של תחום, וחוזים של API משולבים יחד
3. **שמות לא ברורים** - קבצים כמו "object.py", "types.py", "topic.py" לא מציינים בבירור את מטרתם
4. **ללא שכבות ברורות** - קשה לראות מה תלוי במה

## מבנה מוצע

```
trustgraph-base/trustgraph/schema/
├── __init__.py
├── core/              # סוגי ליבה בסיסיים המשמשים בכל מקום
│   ├── __init__.py
│   ├── primitives.py  # שגיאה, ערך, טריפל, שדה, סכימת שורה
│   ├── metadata.py    # רשומת מטא-דאטה
│   └── topic.py       # כלי לטיפול בנושאים
│
├── knowledge/         # מודלים של תחום ידע ואיסוף
│   ├── __init__.py
│   ├── graph.py       # EntityContext, EntityEmbeddings, Triples
│   ├── document.py    # מסמך, TextDocument, חתיכה
│   ├── knowledge.py   # סוגי איסוף ידע
│   ├── embeddings.py  # כל סוגי הסתמכות הקשורים (הועברו מקבצים רבים)
│   └── nlp.py         # סוגי הגדרה, נושא, קשר, עובדה
│
└── services/          # חוזים של בקשות/תגובות שירות
    ├── __init__.py
    ├── llm.py         # TextCompletion, Embeddings, בקשות/תגובות של כלי
    ├── retrieval.py   # שאילתות/תגובות של GraphRAG, DocumentRAG
    ├── query.py       # בקשות/תגובות של GraphEmbeddings, DocumentEmbeddings
    ├── agent.py       # בקשות/תגובות של סוכן
    ├── flow.py        # בקשות/תגובות של זרימה
    ├── prompt.py      # בקשות/תגובות של שירות בקשות
    ├── config.py      # שירות תצורה
    ├── library.py     # שירות ספרייה
    └── lookup.py      # שירות חיפוש
```

## שינויים מרכזיים

1. **ארגון היררכי** - הפרדה ברורה בין סוגים ליבה, מודלים של ידע, וחוזים של שירות
2. **שמות טובים יותר**:
   - `types.py` → `core/primitives.py` (מטרה ברורה יותר)
   - `object.py` → פירוק בין קבצים מתאימים בהתאם לתוכן
   - `documents.py` → `knowledge/document.py` (יחיד, עקבי)
   - `models.py` → `services/llm.py` (סוגי מודלים ברורים יותר)
   - `prompt.py` → פירוק: חלקי שירות ל- `services/prompt.py`, סוגי נתונים ל- `knowledge/nlp.py`

3. **קבוצות לוגיות**:
   - כל סוגי ההסתמכות הועברו ל- `knowledge/embeddings.py`
   - כל חוזי השירות הקשורים ל-LLM ב- `services/llm.py`
   - הפרדה ברורה של זוגות בקשות/תגובות בספריית השירותים
   - סוגי איסוף ידע מקובצים עם מודלים אחרים של תחום ידע

4. **בהירות תלות**:
   - סוגים ליבה אין תלות
   - מודלים של ידע תלויים רק בסוגים ליבה
   - חוזי שירות יכולים להיות תלויים בשני סוגים ליבה ומודלים של ידע

## יתרונות המעבר

1. **ניווט קל יותר** - מפתחים יכולים למצוא במהירות את מה שהם צריכים
2. **מודולריות טובה יותר** - גבולות ברורים בין דאגות שונות
3. **ייבוא פשוט יותר** - מסלולי ייבוא אינטואיטיביים יותר
4. **עתידי** - קל להוסיף סוגי ידע חדשים או שירותים ללא בלבול

## שינויים דוגמה לייבוא

```python
# לפני
from trustgraph.schema import Error, Triple, GraphEmbeddings, TextCompletionRequest

# אחרי
from trustgraph.schema.core import Error, Triple
from trustgraph.schema.knowledge import GraphEmbeddings
from trustgraph.schema.services import TextCompletionRequest
```

## הערות ליישום

1. שמירה על תאימות אחורה על ידי שמירה על ייבוא ב- `__init__.py`
2. העברת קבצים בהדרגה, תוך עדכון ייבוא לפי הצורך
3. שקול להוסיף קובץ `legacy.py` שיבוא הכל עבור תקופת המעבר
4. עדכון תיעוד כדי לשקף את המבנה החדש

<function_calls>
<invoke name="TodoWrite">
<parameter name="todos">[{"id": "1", "content": "להעריך את מבנה תיקיית הסכימה הנוכחי", "status": "completed", "priority": "high"}, {"id": "2", "content": "לנתח את הקבצים של הסכימה ולמטרות שלהם", "status": "completed", "priority": "high"}, {"id": "3", "content": "להציע מבנה ושמות טובים יותר", "status": "completed", "priority": "high"}]
