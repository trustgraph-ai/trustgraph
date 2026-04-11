# מפרט טכני של כלי שורת הפקודה (CLI) להסברתיות

## סטטוס

טיוטה

## סקירה כללית

מפרט זה מתאר כלי שורת פקודה (CLI) לניפוי באגים ובדיקת נתוני הסברתיות ב-TrustGraph. כלים אלה מאפשרים למשתמשים לעקוב אחר אופן קבלת התשובות ולבצע ניפוי באגים בשרשרת המקור, החל מצמתים ועד למסמכים מקוריים.

שלושה כלים של שורת פקודה:

1. **`tg-show-document-hierarchy`** - הצגת היררכיה של מסמך → עמוד → מקטע → צומת
2. **`tg-list-explain-traces`** - הצגת רשימה של כל הסשנים של GraphRAG עם שאלות
3. **`tg-show-explain-trace`** - הצגת מעקב הסברתיות מלא עבור סשן

## מטרות

**ניפוי באגים**: לאפשר למפתחים לבדוק את תוצאות עיבוד המסמכים
**ביקורת**: לעקוב אחר כל עובדה שחולצה בחזרה למסמך המקור שלה
**שקיפות**: להציג בדיוק כיצד GraphRAG הגיע לתשובה
**שימושיות**: ממשק שורת פקודה פשוט עם הגדרות ברירת מחדל הגיוניות

## רקע

ל-TrustGraph יש שתי מערכות מעקב מקור:

1. **מעקב מקור בזמן חילוץ** (ראה `extraction-time-provenance.md`): מתעד את היחסים בין מסמך → עמוד → מקטע → צומת במהלך הטעינה. מאוחסן בגרף בשם `urn:graph:source` באמצעות `prov:wasDerivedFrom`.

2. **הסברתיות בזמן שאילתה** (ראה `query-time-explainability.md`): מתעד את שרשרת השאלות → חקירה → מיקוד → סינתזה במהלך שאילתות GraphRAG. מאוחסן בגרף בשם `urn:graph:retrieval`.

מגבלות נוכחיות:
אין דרך קלה להציג את היררכיית המסמכים לאחר העיבוד
יש לבצע שאילתות ידניות על משולשים כדי לראות נתוני הסברתיות
אין תצוגה מאוחדת של סשן GraphRAG

## עיצוב טכני

### כלי 1: tg-show-document-hierarchy

**מטרה**: בהינתן מזהה מסמך, לעבור ולציין את כל הישויות הנגזרות.

**שימוש**:
```bash
tg-show-document-hierarchy "urn:trustgraph:doc:abc123"
tg-show-document-hierarchy --show-content --max-content 500 "urn:trustgraph:doc:abc123"
```

**ארגומנטים**:
| Arg | תיאור |
|-----|-------------|
| `document_id` | כתובת URI של המסמך (מיקום) |
| `-u/--api-url` | כתובת URL של ה-Gateway (ברירת מחדל: `$TRUSTGRAPH_URL`) |
| `-t/--token` | טוקן אימות (ברירת מחדל: `$TRUSTGRAPH_TOKEN`) |
| `-U/--user` | מזהה משתמש (ברירת מחדל: `trustgraph`) |
| `-C/--collection` | אוסף (ברירת מחדל: `default`) |
| `--show-content` | לכלול תוכן של קבצים/מסמכים |
| `--max-content` | מספר תווים מקסימלי לכל קובץ (ברירת מחדל: 200) |
| `--format` | פלט: `tree` (ברירת מחדל), `json` |

**יישום**:
1. שאילת משולשות: `?child prov:wasDerivedFrom <document_id>` ב-`urn:graph:source`
2. שאילת באופן רקורסיבי את הילדים של כל תוצאה
3. בניית מבנה עץ: מסמך → עמודים → חלקים
4. אם `--show-content`, שליפה של תוכן מ-API של הספרן
5. הצגה כמבנה עץ עם הזחות או JSON

**דוגמה לפלט**:
```
Document: urn:trustgraph:doc:abc123
  Title: "Sample PDF"
  Type: application/pdf

  └── Page 1: urn:trustgraph:doc:abc123/p1
      ├── Chunk 0: urn:trustgraph:doc:abc123/p1/c0
      │   Content: "The quick brown fox..." [truncated]
      └── Chunk 1: urn:trustgraph:doc:abc123/p1/c1
          Content: "Machine learning is..." [truncated]
```

### כלי 2: tg-list-explain-traces

**מטרה**: הצגת כל הסשנים (שאלות) של GraphRAG באוסף.

**שימוש**:
```bash
tg-list-explain-traces
tg-list-explain-traces --limit 20 --format json
```

**ארגומנטים**:
| Arg | תיאור |
|-----|-------------|
| `-u/--api-url` | כתובת URL של ה-Gateway |
| `-t/--token` | טוקן אימות |
| `-U/--user` | מזהה משתמש |
| `-C/--collection` | אוסף |
| `--limit` | מספר תוצאות מקסימלי (ברירת מחדל: 50) |
| `--format` | פלט: `table` (ברירת מחדל), `json` |

**יישום**:
1. שאילתה: `?session tg:query ?text` ב-`urn:graph:retrieval`
2. שאילתת חותמות זמן: `?session prov:startedAtTime ?time`
3. הצגה כטבלה

**דוגמה לפלט**:
```
Session ID                                    | Question                        | Time
----------------------------------------------|--------------------------------|---------------------
urn:trustgraph:question:abc123                | What was the War on Terror?    | 2024-01-15 10:30:00
urn:trustgraph:question:def456                | Who founded OpenAI?            | 2024-01-15 09:15:00
```

### כלי 3: tg-show-explain-trace

**מטרה**: הצגת שרשרת ההסברים המלאה עבור סשן GraphRAG.

**שימוש**:
```bash
tg-show-explain-trace "urn:trustgraph:question:abc123"
tg-show-explain-trace --max-answer 1000 --show-provenance "urn:trustgraph:question:abc123"
```

**ארגומנטים**:
| Arg | תיאור |
|-----|-------------|
| `question_id` | כתובת URI של שאלה (מיקום) |
| `-u/--api-url` | כתובת URL של שער |
| `-t/--token` | טוקן אימות |
| `-U/--user` | מזהה משתמש |
| `-C/--collection` | אוסף |
| `--max-answer` | מספר תווים מקסימלי לתשובה (ברירת מחדל: 500) |
| `--show-provenance` | לעקוב אחר קשרים למסמכים מקוריים |
| `--format` | פלט: `text` (ברירת מחדל), `json` |

**יישום**:
1. קבל את טקסט השאלה מ-`tg:query` (predicate)
2. מצא חקירה: `?exp prov:wasGeneratedBy <question_id>`
3. מצא מיקוד: `?focus prov:wasDerivedFrom <exploration_id>`
4. קבל קשרים שנבחרו: `<focus_id> tg:selectedEdge ?edge`
5. עבור כל קשר, קבל `tg:edge` (משולש מצוטט) ו-`tg:reasoning`
6. מצא סינתזה: `?synth prov:wasDerivedFrom <focus_id>`
7. קבל את התשובה מ-`tg:document` דרך הספרן |
8. אם `--show-provenance`, עקוב אחר קשרים למסמכים מקוריים

**דוגמה לפלט**:
```
=== GraphRAG Session: urn:trustgraph:question:abc123 ===

Question: What was the War on Terror?
Time: 2024-01-15 10:30:00

--- Exploration ---
Retrieved 50 edges from knowledge graph

--- Focus (Edge Selection) ---
Selected 12 edges:

  1. (War on Terror, definition, "A military campaign...")
     Reasoning: Directly defines the subject of the query
     Source: chunk → page 2 → "Beyond the Vigilant State"

  2. (Guantanamo Bay, part_of, War on Terror)
     Reasoning: Shows key component of the campaign

--- Synthesis ---
Answer:
  The War on Terror was a military campaign initiated...
  [truncated at 500 chars]
```

## קבצים ליצירה

| קובץ | מטרה |
|------|---------|
| `trustgraph-cli/trustgraph/cli/show_document_hierarchy.py` | כלי 1 |
| `trustgraph-cli/trustgraph/cli/list_explain_traces.py` | כלי 2 |
| `trustgraph-cli/trustgraph/cli/show_explain_trace.py` | כלי 3 |

## קבצים לשינוי

| קובץ | שינוי |
|------|--------|
| `trustgraph-cli/setup.py` | הוספת רשומות ל-console_scripts |

## הערות יישום

1. **בטיחות תוכן בינארי**: נסה לפענח UTF-8; אם נכשל, הצג `[Binary: {size} bytes]`
2. **חיתוך**: שמור על `--max-content`/`--max-answer` עם מציין `[truncated]`
3. **משולשות מצוטטות**: נתח פורמט RDF-star מ-predicate `tg:edge`
4. **תבניות**: עקוב אחר תבניות CLI קיימות מ-`query_graph.py`

## שיקולי אבטחה

כל השאילתות מכבדות את גבולות המשתמש/אוסף
אימות טוקן נתמך באמצעות `--token` או `$TRUSTGRAPH_TOKEN`

## אסטרטגיית בדיקה

אימות ידני עם נתוני דוגמה:
```bash
# Load a test document
tg-load-pdf -f test.pdf -c test-collection

# Verify hierarchy
tg-show-document-hierarchy "urn:trustgraph:doc:test"

# Run a GraphRAG query with explainability
tg-invoke-graph-rag --explainable -q "Test question"

# List and inspect traces
tg-list-explain-traces
tg-show-explain-trace "urn:trustgraph:question:xxx"
```

## הפניות

הסבר בזמן שאילתה: `docs/tech-specs/query-time-explainability.md`
מקור בזמן חילוץ: `docs/tech-specs/extraction-time-provenance.md`
דוגמה קיימת של שורת פקודה: `trustgraph-cli/trustgraph/cli/invoke_graph_rag.py`
