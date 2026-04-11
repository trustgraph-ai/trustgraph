# מפרט OpenAPI - מפרט טכני

## מטרה

ליצור מפרט OpenAPI 3.1 מקיף ומודולרי עבור שער ה-API של TrustGraph REST, אשר:
מתעד את כל נקודות הקצה של REST
משתמש בקוד חיצוני `$ref` לצורך מודולריות ותחזוקה
מתאים ישירות לקוד מתרגם ההודעות
מספק סכימות מדויקות של בקשות/תגובות

## מקור האמת

ה-API מוגדר על ידי:
**מתרגמי הודעות**: `trustgraph-base/trustgraph/messaging/translators/*.py`
**מנהל ה-Dispatcher**: `trustgraph-flow/trustgraph/gateway/dispatch/manager.py`
**מנהל נקודות הקצה**: `trustgraph-flow/trustgraph/gateway/endpoint/manager.py`

## מבנה תיקיות

```
openapi/
├── openapi.yaml                          # Main entry point
├── paths/
│   ├── config.yaml                       # Global services
│   ├── flow.yaml
│   ├── librarian.yaml
│   ├── knowledge.yaml
│   ├── collection-management.yaml
│   ├── flow-services/                    # Flow-hosted services
│   │   ├── agent.yaml
│   │   ├── document-rag.yaml
│   │   ├── graph-rag.yaml
│   │   ├── text-completion.yaml
│   │   ├── prompt.yaml
│   │   ├── embeddings.yaml
│   │   ├── mcp-tool.yaml
│   │   ├── triples.yaml
│   │   ├── objects.yaml
│   │   ├── nlp-query.yaml
│   │   ├── structured-query.yaml
│   │   ├── structured-diag.yaml
│   │   ├── graph-embeddings.yaml
│   │   ├── document-embeddings.yaml
│   │   ├── text-load.yaml
│   │   └── document-load.yaml
│   ├── import-export/
│   │   ├── core-import.yaml
│   │   ├── core-export.yaml
│   │   └── flow-import-export.yaml      # WebSocket import/export
│   ├── websocket.yaml
│   └── metrics.yaml
├── components/
│   ├── schemas/
│   │   ├── config/
│   │   ├── flow/
│   │   ├── librarian/
│   │   ├── knowledge/
│   │   ├── collection/
│   │   ├── ai-services/
│   │   ├── common/
│   │   └── errors/
│   ├── parameters/
│   ├── responses/
│   └── examples/
└── security/
    └── bearerAuth.yaml
```

## מיפוי שירותים

### שירותים גלובליים (`/api/v1/{kind}`)
`config` - ניהול תצורה
`flow` - מחזור חיים של זרימה
`librarian` - ספריית מסמכים
`knowledge` - ליבות ידע
`collection-management` - מטא-דאטה של אוסף

### שירותים המאוחסנים בתוך זרימה (Flow-Hosted Services) (`/api/v1/flow/{flow}/service/{kind}`)

**בקשה/תגובה:**
`agent`, `text-completion`, `prompt`, `mcp-tool`
`graph-rag`, `document-rag`
`embeddings`, `graph-embeddings`, `document-embeddings`
`triples`, `objects`, `nlp-query`, `structured-query`, `structured-diag`

**שליחה והתעלמות (Fire-and-Forget):**
`text-load`, `document-load`

### ייבוא/ייצוא
`/api/v1/import-core` (POST)
`/api/v1/export-core` (GET)
`/api/v1/flow/{flow}/import/{kind}` (WebSocket)
`/api/v1/flow/{flow}/export/{kind}` (WebSocket)

### אחר
`/api/v1/socket` (WebSocket מרובה)
`/api/metrics` (Prometheus)

## גישה

### שלב 1: הגדרה
1. צור מבנה תיקיות
2. צור את הקובץ הראשי `openapi.yaml` עם מטא-דאטה, שרתים, אבטחה
3. צור רכיבים שניתנים לשימוש חוזר (שגיאות, פרמטרים נפוצים, סכימות אבטחה)

### שלב 2: סכימות נפוצות
צור סכימות משותפות המשמשות בכל השירותים:
`RdfValue`, `Triple` - מבני RDF/טריפל
`ErrorObject` - תגובת שגיאה
`DocumentMetadata`, `ProcessingMetadata` - מבני מטא-דאטה
פרמטרים נפוצים: `FlowId`, `User`, `Collection`

### שלב 3: שירותים גלובליים
עבור כל שירות גלובלי (תצורה, זרימה, ספרן, ידע, ניהול אוסף):
1. צור קובץ נתיב ב-`paths/`
2. צור סכימת בקשה ב-`components/schemas/{service}/`
3. צור סכימת תגובה
4. הוסף דוגמאות
5. הפנה מהקובץ הראשי `openapi.yaml`

### שלב 4: שירותים המאוחסנים בתוך זרימה
עבור כל שירות המאוחסן בתוך זרימה:
1. צור קובץ נתיב ב-`paths/flow-services/`
2. צור סכימות בקשה/תגובה ב-`components/schemas/ai-services/`
3. הוסף תיעוד לדגל סטרימינג במידת הצורך
4. הפנה מהקובץ הראשי `openapi.yaml`

### שלב 5: ייבוא/ייצוא ו-WebSocket
1. תעד נקודות קצה מרכזיות לייבוא/ייצוא
2. תעד תבניות פרוטוקול WebSocket
3. תעד נקודות קצה של ייבוא/ייצוא ברמת הזרימה של WebSocket

### שלב 6: אימות
1. אמת באמצעות כלי אימות OpenAPI
2. בדוק באמצעות Swagger UI
3. ודא שכל המתרגמים מכוסים

## מוסכמות מתן שמות לשדות

כל השדות ב-JSON משתמשים בפורמט **kebab-case**:
`flow-id`, `blueprint-name`, `doc-limit`, `entity-limit`, וכו'.

## יצירת קבצי סכימה

עבור כל מתרגם ב-`trustgraph-base/trustgraph/messaging/translators/`:

1. **קרא את שיטת המתרגם `to_pulsar()`** - מגדיר סכימת בקשה
2. **קרא את שיטת המתרגם `from_pulsar()`** - מגדיר סכימת תגובה
3. **חלץ שמות שדות וסוגים**
4. **צור סכימה של OpenAPI** עם:
   שמות שדות (kebab-case)
   סוגים (string, integer, boolean, object, array)
   שדות חובה
   ערכי ברירת מחדל
   תיאורים

### תהליך מיפוי לדוגמה

```python
# From retrieval.py DocumentRagRequestTranslator
def to_pulsar(self, data: Dict[str, Any]) -> DocumentRagQuery:
    return DocumentRagQuery(
        query=data["query"],                              # required string
        user=data.get("user", "trustgraph"),             # optional string, default "trustgraph"
        collection=data.get("collection", "default"),     # optional string, default "default"
        doc_limit=int(data.get("doc-limit", 20)),        # optional integer, default 20
        streaming=data.get("streaming", False)            # optional boolean, default false
    )
```

מתורגם ל:

```yaml
# components/schemas/ai-services/DocumentRagRequest.yaml
type: object
required:
  - query
properties:
  query:
    type: string
    description: Search query
  user:
    type: string
    default: trustgraph
  collection:
    type: string
    default: default
  doc-limit:
    type: integer
    default: 20
    description: Maximum number of documents to retrieve
  streaming:
    type: boolean
    default: false
    description: Enable streaming responses
```

## תגובות סטרימינג

שירותים התומכים בסטרימינג מחזירים מספר תגובות עם הדגל `end_of_stream`:
`agent`, `text-completion`, `prompt`
`document-rag`, `graph-rag`

יש לתעד דפוס זה בסכימת התגובות של כל שירות.

## תגובות שגיאה

כל השירותים יכולים להחזיר:
```yaml
error:
  oneOf:
    - type: string
    - $ref: '#/components/schemas/ErrorObject'
```

היכן ש-`ErrorObject` נמצא:
```yaml
type: object
properties:
  type:
    type: string
  message:
    type: string
```

## הפניות

מתרגמים: `trustgraph-base/trustgraph/messaging/translators/`
מיפוי מפיץ: `trustgraph-flow/trustgraph/gateway/dispatch/manager.py`
ניתוב נקודת קצה: `trustgraph-flow/trustgraph/gateway/endpoint/manager.py`
תקציר שירות: `API_SERVICES_SUMMARY.md`
