# זרימות חילוץ

מסמך זה מתאר כיצד נתונים זורמים דרך צינור החילוץ של TrustGraph, החל מהגשת המסמכים ועד לאחסון במאגרי ידע.

## סקירה כללית

```
┌──────────┐     ┌─────────────┐     ┌─────────┐     ┌────────────────────┐
│ Librarian│────▶│ PDF Decoder │────▶│ Chunker │────▶│ Knowledge          │
│          │     │ (PDF only)  │     │         │     │ Extraction         │
│          │────────────────────────▶│         │     │                    │
└──────────┘     └─────────────┘     └─────────┘     └────────────────────┘
                                          │                    │
                                          │                    ├──▶ Triples
                                          │                    ├──▶ Entity Contexts
                                          │                    └──▶ Rows
                                          │
                                          └──▶ Document Embeddings
```

## אחסון תוכן

### אחסון בלובים (S3/Minio)

תוכן מסמכים מאוחסן באחסון בלובים התואם ל-S3:
פורמט נתיב: `doc/{object_id}` כאשר object_id הוא מזהה UUID
כל סוגי המסמכים מאוחסנים כאן: מסמכים מקוריים, עמודים, חלקים

### אחסון מטא-דאטה (Cassandra)

מטא-דאטה של מסמכים המאוחסן ב-Cassandra כולל:
מזהה מסמך, כותרת, סוג (MIME type)
הפניה לאחסון הבלובים `object_id`
`parent_id` עבור מסמכים משניים (עמודים, חלקים)
`document_type`: "source", "page", "chunk", "answer"

### סף בין הטמעה להזרמה

העברת תוכן משתמשת באסטרטגיה המבוססת על גודל:
**פחות מ-2MB**: התוכן כלול בתוך ההודעה (מקודד ב-base64)
**גדול או שווה ל-2MB**: נשלח רק `document_id`; המעבד שולף דרך ממשק ה-librarian API

## שלב 1: הגשת מסמך (Librarian)

### נקודת כניסה

מסמכים נכנסים למערכת דרך הפעולה `add-document` של ה-librarian:
1. התוכן מועלה לאחסון הבלובים
2. רשומה של מטא-דאטה נוצרת ב-Cassandra
3. מחזיר מזהה מסמך

### הפעלת חילוץ

הפעולה `add-processing` מפעילה חילוץ:
מציין `document_id`, `flow` (מזהה צינור), `collection` (מחסן יעד)
הפעולה `load_document()` של ה-librarian שולפת את התוכן ומפרסמת לתור הקלט של ה-flow

### סכימה: מסמך

```
Document
├── metadata: Metadata
│   ├── id: str              # Document identifier
│   ├── user: str            # Tenant/user ID
│   ├── collection: str      # Target collection
│   └── metadata: list[Triple]  # (largely unused, historical)
├── data: bytes              # PDF content (base64, if inline)
└── document_id: str         # Librarian reference (if streaming)
```

**ניתוב:** בהתבסס על השדה `kind`:
`application/pdf` → תור `document-load` → מפענח PDF
`text/plain` → תור `text-load` → מפרק

## שלב 2: מפענח PDF

ממיר מסמכי PDF לעמודי טקסט.

### תהליך

1. שליפת תוכן (בשורת `data` או דרך `document_id` מהספרן)
2. חילוץ עמודים באמצעות PyPDF
3. עבור כל עמוד:
   שמירה כמסמך משני בספרן (`{doc_id}/p{page_num}`)
   שליחת טריפלים של מקור (עמוד שמקורו במסמך)
   העברה למפרק

### סכימה: TextDocument

```
TextDocument
├── metadata: Metadata
│   ├── id: str              # Page URI (e.g., https://trustgraph.ai/doc/xxx/p1)
│   ├── user: str
│   ├── collection: str
│   └── metadata: list[Triple]
├── text: bytes              # Page text content (if inline)
└── document_id: str         # Librarian reference (e.g., "doc123/p1")
```

## שלב 3: חלוקה לחלקים

מחלק טקסט לחלקים בגודל מוגדר.

### פרמטרים (ניתנים להגדרה בתוך זרימת העבודה)

`chunk_size`: גודל החלק המיועד בתווים (ברירת מחדל: 2000)
`chunk_overlap`: חפיפה בין חלקים (ברירת מחדל: 100)

### תהליך

1. שליפת תוכן הטקסט (בשורת הקוד או דרך הספרן)
2. חלוקה באמצעות מפריד תווים רקורסיבי
3. עבור כל חלק:
   שמירה כמסמך משני בספרן (`{parent_id}/c{index}`)
   שליחת טריפלים של מקור (החלק נגזר מדף/מסמך)
   העברה למעבדי חילוץ

### סכימה: חלק

```
Chunk
├── metadata: Metadata
│   ├── id: str              # Chunk URI
│   ├── user: str
│   ├── collection: str
│   └── metadata: list[Triple]
├── chunk: bytes             # Chunk text content
└── document_id: str         # Librarian chunk ID (e.g., "doc123/p1/c3")
```

### היררכיית מזהי מסמכים

מסמכים משניים מקודדים את שושלתם במזהה:
מקור: `doc123`
עמוד: `doc123/p5`
מקטע מעמוד: `doc123/p5/c2`
מקטע מטקסט: `doc123/c2`

## שלב 4: חילוץ ידע

קיימים דפוסי חילוץ מרובים, הנבחרים על ידי תצורת זרימת העבודה.

### דפוס א': GraphRAG בסיסי

שני מעבדים מקבילים:

**kg-extract-definitions**
קלט: מקטע
פלט: משולשים (הגדרות ישויות), הקשרים של ישויות
מחלץ: תוויות ישויות, הגדרות

**kg-extract-relationships**
קלט: מקטע
פלט: משולשים (יחסים), הקשרים של ישויות
מחלץ: יחסי נושא-נשוא-אובייקט

### דפוס ב': מונחה אונטולוגיה (kg-extract-ontology)

קלט: מקטע
פלט: משולשים, הקשרים של ישויות
משתמש באונטולוגיה מוגדרת כדי להנחות את החילוץ

### דפוס ג': מבוסס סוכן (kg-extract-agent)

קלט: מקטע
פלט: משולשים, הקשרים של ישויות
משתמש במסגרת סוכן לחילוץ

### דפוס ד': חילוץ שורות (kg-extract-rows)

קלט: מקטע
פלט: שורות (נתונים מובנים, לא משולשים)
משתמש בהגדרת סכימה כדי לחלץ רשומות מובנות

### סכימה: משולשים

```
Triples
├── metadata: Metadata
│   ├── id: str
│   ├── user: str
│   ├── collection: str
│   └── metadata: list[Triple]  # (set to [] by extractors)
└── triples: list[Triple]
    └── Triple
        ├── s: Term              # Subject
        ├── p: Term              # Predicate
        ├── o: Term              # Object
        └── g: str | None        # Named graph
```

### סכימה: EntityContexts

```
EntityContexts
├── metadata: Metadata
└── entities: list[EntityContext]
    └── EntityContext
        ├── entity: Term         # Entity identifier (IRI)
        ├── context: str         # Textual description for embedding
        └── chunk_id: str        # Source chunk ID (provenance)
```

### סכימה: שורות

```
Rows
├── metadata: Metadata
├── row_schema: RowSchema
│   ├── name: str
│   ├── description: str
│   └── fields: list[Field]
└── rows: list[dict[str, str]]   # Extracted records
```

## שלב 5: יצירת הטמעות (Embeddings)

### הטמעות גרפיות (Graph Embeddings)

ממיר הקשרים של ישויות להטמעות וקטוריות.

**תהליך:**
1. קבלת הקשרים של ישויות (EntityContexts)
2. הפעלת שירות הטמעות עם טקסט ההקשר
3. פלט הטמעות גרפיות (מיפוי ישות ← וקטור)

**סכימה: הטמעות גרפיות (GraphEmbeddings)**

```
GraphEmbeddings
├── metadata: Metadata
└── entities: list[EntityEmbeddings]
    └── EntityEmbeddings
        ├── entity: Term         # Entity identifier
        ├── vector: list[float]  # Embedding vector
        └── chunk_id: str        # Source chunk (provenance)
```

### הטמעות מסמכים

ממיר טקסט מחולק ישירות להטמעות וקטוריות.

**תהליך:**
1. קבלת מקטע
2. הפעלת שירות הטמעות עם טקסט המקטע
3. פלט הטמעות מסמכים

**סכימה: הטמעות מסמכים**

```
DocumentEmbeddings
├── metadata: Metadata
└── chunks: list[ChunkEmbeddings]
    └── ChunkEmbeddings
        ├── chunk_id: str        # Chunk identifier
        └── vector: list[float]  # Embedding vector
```

### הטמעות שורות

ממיר שדות אינדקס שורות להטמעות וקטוריות.

**תהליך:**
1. קבלת שורות
2. הטמעת שדות אינדקס מוגדרים
3. פלט לאחסון וקטורים של שורות

## שלב 6: אחסון

### מאגר משולשות

מקבל: משולשות
אחסון: Cassandra (טבלאות ממוקדות ישויות)
גרפים בעלי שמות מפרידים ידע ליבה ממידע על מקור:
  `""` (ברירת מחדל): עובדות ידע ליבה
  `urn:graph:source`: מידע על מקור החילוץ
  `urn:graph:retrieval`: הסבר בזמן שאילתה

### מאגר וקטורים (הטמעות גרפים)

מקבל: הטמעות גרפים
אחסון: Qdrant, Milvus, או Pinecone
מאוּינדקס על ידי: IRI של ישות
מטא-דאטה: chunk_id עבור מידע על מקור

### מאגר וקטורים (הטמעות מסמכים)

מקבל: הטמעות מסמכים
אחסון: Qdrant, Milvus, או Pinecone
מאוּינדקס על ידי: chunk_id

### מאגר שורות

מקבל: שורות
אחסון: Cassandra
מבנה טבלאות המונחה סכימה

### מאגר וקטורים של שורות

מקבל: הטמעות שורות
אחסון: מסד נתונים וקטורי
מאוּנדקס על ידי: שדות אינדקס שורה

## ניתוח שדות מטא-דאטה

### שדות בשימוש פעיל

| שדה | שימוש |
|-------|-------|
| `metadata.id` | מזהה מסמך/חלק, רישום, מקור
| `metadata.user` | ריבוי דיירים, ניתוב אחסון
| `metadata.collection` | בחירת אוסף יעד
| `document_id` | הפניה לספרן, קישור למקור
| `chunk_id` | מעקב אחר מקור לאורך הצינור

<<<<<<< HEAD
### שדות שעלולים להיות מיותרים

| שדה | סטטוס |
|-------|--------|
| `metadata.metadata` | מוגדר ל-`[]` על ידי כל המחלצים; מטא-דאטה ברמת המסמך מטופלים כעת על ידי הספרן בזמן ההגשה |
=======
### שדות שהוסרו

| שדה | סטטוס |
|-------|--------|
| `metadata.metadata` | הוסר ממחלקת `Metadata`. משולשות מטא-דאטה ברמת המסמך משודרים כעת ישירות על ידי הספרן למאגר משולשות בזמן ההגשה, ולא מועברים דרך צינור החילוץ. |
>>>>>>> e3bcbf73 (The metadata field (list of triples) in the pipeline Metadata class)

### תבניות שדות בייטים

כל שדות התוכן (`data`, `text`, `chunk`) הם `bytes` אך מפענחים מיד לשרשורי UTF-8 על ידי כל המעבדים. אף מעבד לא משתמש בבייטים גולמיים.

## תצורת זרימה

זרימות מוגדרות מחוץ למערכת ומועברות לספרן באמצעות שירות התצורה. כל זרימה מציינת:

תורי קלט (`text-load`, `document-load`)
שרשרת מעבדים
פרמטרים (גודל חתיכה, שיטת חילוץ, וכו')

דוגמאות לתבניות זרימה:
`pdf-graphrag`: PDF → מפענח → חולק → הגדרות + קשרים → הטמעות
`text-graphrag`: טקסט → חולק → הגדרות + קשרים → הטמעות
`pdf-ontology`: PDF → מפענח → חולק → חילוץ אונטולוגיה → הטמעות
`text-rows`: טקסט → חולק → חילוץ שורות → אחסון שורות
