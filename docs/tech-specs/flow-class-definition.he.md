<<<<<<< HEAD
# הגדרת מפרט תוכנית זרימה
=======
# מפרט הגדרת תוכנית זרימה
>>>>>>> 82edf2d (New md files from RunPod)

## סקירה כללית

תוכנית זרימה מגדירה תבנית מלאה של דפוסי זרימת נתונים במערכת TrustGraph. כאשר היא מופעלת, היא יוצרת רשת מקושרת של מעבדים המטפלים בקליטת נתונים, עיבוד, אחסון ושליפה כחלק ממערכת מאוחדת.

## מבנה

הגדרת תוכנית זרימה מורכבת מחמש קטעים עיקריים:

### 1. קטע מחלקה
<<<<<<< HEAD
מגדיר מעבדי שירות משותפים המופעלים פעם אחת לכל תוכנית זרימה. מעבדים אלה מטפלים בבקשות מכל מופעי הזרימה של מחלקה זו.
=======
מגדיר מעבדים משותפים המופעלים פעם אחת לכל תוכנית זרימה. מעבדים אלה מטפלים בבקשות מכל מופעי הזרימה של מחלקה זו.
>>>>>>> 82edf2d (New md files from RunPod)

```json
"class": {
  "service-name:{class}": {
    "request": "queue-pattern:{class}",
    "response": "queue-pattern:{class}",
    "settings": {
      "setting-name": "fixed-value",
      "parameterized-setting": "{parameter-name}"
    }
  }
}
```

**מאפיינים:**
משותפים לכל מופעי זרימה מאותו סוג.
בדרך כלל שירותים יקרים או חסרי מצב (מודלים של שפה גדולים, מודלים להטמעה).
השתמשו במשתנה תבנית `{class}` עבור שמות תורים.
הגדרות יכולות להיות ערכים קבועים או פרמטריות באמצעות תחביר `{parameter-name}`.
דוגמאות: `embeddings:{class}`, `text-completion:{class}`, `graph-rag:{class}`

### 2. סעיף זרימה
<<<<<<< HEAD
מגדיר מעבדים ספציפיים לזרימה, אשר מופעלים עבור כל מופע זרימה בודד. לכל זרימה יש סט נפרד משלה של מעבדים אלה.
=======
מגדיר מעבדים ספציפיים לזרימה אשר מופעלים עבור כל מופע זרימה בודד. לכל זרימה יש סט נפרד משלה של מעבדים אלה.
>>>>>>> 82edf2d (New md files from RunPod)

```json
"flow": {
  "processor-name:{id}": {
    "input": "queue-pattern:{id}",
    "output": "queue-pattern:{id}",
    "settings": {
      "setting-name": "fixed-value",
      "parameterized-setting": "{parameter-name}"
    }
  }
}
```

**מאפיינים:**
מופע ייחודי לכל זרימה
טיפול בנתונים ובמצב ספציפיים לזרימה
שימוש במשתנה תבנית `{id}` עבור שמות תורים
הגדרות יכולות להיות ערכים קבועים או פרמטריות באמצעות תחביר `{parameter-name}`
דוגמאות: `chunker:{id}`, `pdf-decoder:{id}`, `kg-extract-relationships:{id}`

### 3. סעיף ממשקים
מגדיר את נקודות הכניסה ואת חוזי האינטראקציה עבור הזרימה. אלה מהווים את ממשק ה-API עבור מערכות חיצוניות ותקשורת בין רכיבים פנימיים.

ממשקים יכולים לקבל שתי צורות:

<<<<<<< HEAD
**תבנית "שלח ושכח"** (תור יחיד):
=======
**תבנית "שלח והשכח"** (תור יחיד):
>>>>>>> 82edf2d (New md files from RunPod)
```json
"interfaces": {
  "document-load": "persistent://tg/flow/document-load:{id}",
  "triples-store": "persistent://tg/flow/triples-store:{id}"
}
```

**תבנית בקשה/תגובה** (אובייקט עם שדות בקשה/תגובה):
```json
"interfaces": {
  "embeddings": {
    "request": "non-persistent://tg/request/embeddings:{class}",
    "response": "non-persistent://tg/response/embeddings:{class}"
  }
}
```

**סוגי ממשקים:**
<<<<<<< HEAD
**נקודות כניסה:** נקודות שבהן מערכות חיצוניות מזריקות נתונים (`document-load`, `agent`)
**ממשקי שירות:** תבניות בקשה/תגובה עבור שירותים (`embeddings`, `text-completion`)
**ממשקי נתונים:** נקודות חיבור לזרימת נתונים מסוג "שלח וסגור" (`triples-store`, `entity-contexts-load`)
=======
**נקודות כניסה:** נקודות בהן מערכות חיצוניות מזריקות נתונים (`document-load`, `agent`)
**ממשקי שירות:** תבניות בקשה/תגובה עבור שירותים (`embeddings`, `text-completion`)
**ממשקי נתונים:** נקודות חיבור לזרימת נתונים מסוג "שלח ושים" (`triples-store`, `entity-contexts-load`)
>>>>>>> 82edf2d (New md files from RunPod)

### 4. סעיף פרמטרים
ממפה שמות פרמטרים ספציפיים לזרימה להגדרות פרמטרים המאוחסנות באופן מרכזי:

```json
"parameters": {
  "model": "llm-model",
  "temp": "temperature",
  "chunk": "chunk-size"
}
```

**מאפיינים:**
המפתחות הם שמות הפרמטרים המשמשים בהגדרות המעבד (לדוגמה, `{model}`)
הערכים מפנים להגדרות הפרמטרים המאוחסנות ב-schema/config
מאפשר שימוש חוזר בהגדרות פרמטרים נפוצות בין זרימות
מפחית כפילויות של סכימות פרמטרים

### 5. מטא-נתונים
מידע נוסף על תוכנית הזרימה:

```json
"description": "Human-readable description",
"tags": ["capability-1", "capability-2"]
```

## משתנים בתבנית

### משתנים של המערכת

#### {id}
מוחלף במזהה הייחודי של מופע ה-flow
יוצר משאבים מבודדים עבור כל flow
דוגמה: `flow-123`, `customer-A-flow`

#### {class}
מוחלף בשם התבנית של ה-flow
יוצר משאבים משותפים בין flows של אותה תבנית
דוגמה: `standard-rag`, `enterprise-rag`

### משתנים של פרמטרים

#### {parameter-name}
פרמטרים מותאמים אישית המוגדרים בזמן הפעלת ה-flow
שמות הפרמטרים תואמים למפתחות במקטע `parameters` של ה-flow
משמש בהגדרות של מעבדים כדי להתאים אישית את ההתנהגות
דוגמאות: `{model}`, `{temp}`, `{chunk}`
מוחלף בערכים המסופקים בעת הפעלת ה-flow
<<<<<<< HEAD
מאומתים מול הגדרות פרמטרים המאוחסנות באופן מרכזי
=======
מאומתים מול הגדרות פרמטרים המאוחסנות במרכז
>>>>>>> 82edf2d (New md files from RunPod)

## הגדרות מעבד

הגדרות מספקות ערכי תצורה למעבדים בזמן יצירתם. ניתן להגדיר אותן כ:

### הגדרות קבועות
ערכים ישירים שאינם משתנים:
```json
"settings": {
  "model": "gemma3:12b",
  "temperature": 0.7,
  "max_retries": 3
}
```

### הגדרות מותאמות אישית
ערכים המשתמשים בפרמטרים המסופקים בעת הפעלת ה-flow:
```json
"settings": {
  "model": "{model}",
  "temperature": "{temp}",
  "endpoint": "https://{region}.api.example.com"
}
```

שמות הפרמטרים בהגדרות תואמים למפתחות במקטע `parameters` של ה-flow.

### דוגמאות להגדרות

**מעבד LLM עם פרמטרים:**
```json
// In parameters section:
"parameters": {
  "model": "llm-model",
  "temp": "temperature",
  "tokens": "max-tokens",
  "key": "openai-api-key"
}

// In processor definition:
"text-completion:{class}": {
  "request": "non-persistent://tg/request/text-completion:{class}",
  "response": "non-persistent://tg/response/text-completion:{class}",
  "settings": {
    "model": "{model}",
    "temperature": "{temp}",
    "max_tokens": "{tokens}",
    "api_key": "{key}"
  }
}
```

**חלוקה למקטעים עם הגדרות קבועות וניתנות לשינוי:**
```json
// In parameters section:
"parameters": {
  "chunk": "chunk-size"
}

// In processor definition:
"chunker:{id}": {
  "input": "persistent://tg/flow/chunk:{id}",
  "output": "persistent://tg/flow/chunk-load:{id}",
  "settings": {
    "chunk_size": "{chunk}",
    "chunk_overlap": 100,
    "encoding": "utf-8"
  }
}
```

## תבניות תורים (פולסר)

תבניות זרימה משתמשות ב-Apache Pulsar עבור העברת הודעות. שמות התורים עוקבים אחר הפורמט של פולסר:
```
<persistence>://<tenant>/<namespace>/<topic>
```

### רכיבים:
**persistence**: `persistent` או `non-persistent` (מצב אחסון של Pulsar)
**tenant**: `tg` עבור הגדרות תבניות זרימה המסופקות על ידי TrustGraph
**namespace**: מציין את דפוס העברת ההודעות
  `flow`: שירותים מסוג "שלח וגע" (fire-and-forget)
<<<<<<< HEAD
  `request`: החלק של הבקשה בשירותי בקשה/תגובה (request/response)
  `response`: החלק של התגובה בשירותי בקשה/תגובה (request/response)
=======
  `request`: החלק של הבקשה בשירותי "בקשה/תגובה" (request/response)
  `response`: החלק של התגובה בשירותי "בקשה/תגובה" (request/response)
>>>>>>> 82edf2d (New md files from RunPod)
**topic**: שם התור/נושא הספציפי עם משתני תבנית

### תורים קבועים (Persistent Queues)
דפוס: `persistent://tg/flow/<topic>:{id}`
משמש עבור שירותים מסוג "שלח וגע" וזרימת נתונים עמידה
<<<<<<< HEAD
הנתונים נשמרים באחסון של Pulsar בין הפעלות מחדש
=======
הנתונים נשמרים באחסון של Pulsar גם לאחר אתחולים מחדש
>>>>>>> 82edf2d (New md files from RunPod)
דוגמה: `persistent://tg/flow/chunk-load:{id}`

### תורים לא קבועים (Non-Persistent Queues)
דפוס: `non-persistent://tg/request/<topic>:{class}` או `non-persistent://tg/response/<topic>:{class}`
<<<<<<< HEAD
משמש עבור דפוסי העברת הודעות מסוג בקשה/תגובה
=======
משמש עבור דפוסי העברת הודעות מסוג "בקשה/תגובה"
>>>>>>> 82edf2d (New md files from RunPod)
זמני, אינו נשמר בדיסק על ידי Pulsar
השהיה נמוכה יותר, מתאים לתקשורת בסגנון RPC
דוגמה: `non-persistent://tg/request/embeddings:{class}`

## ארכיטקטורת זרימת נתונים

תבנית זרימת הנתונים יוצרת זרימה מאוחדת שבה:

1. **צינור עיבוד מסמכים**: זרימה מאיסוף דרך טרנספורמציה לאחסון
2. **שירותי שאילתות**: מעבדים משולבים השואלים את אותם מאגרי נתונים ושירותים
3. **שירותים משותפים**: מעבדים מרכזיים שכל הזרימות יכולות להשתמש בהם
4. **כותבי אחסון**: שומרים נתונים מעובדים לאחסונים המתאימים

כל המעבדים (גם `{id}` וגם `{class}`) עובדים יחד כגרף זרימת נתונים מגובש, ולא כמערכות נפרדות.

## דוגמה להפעלה של זרימה

בהינתן:
מזהה מופע של זרימה: `customer-A-flow`
תבנית זרימה: `standard-rag`
מיפוי פרמטרים של זרימה:
  `"model": "llm-model"`
  `"temp": "temperature"`
  `"chunk": "chunk-size"`
פרמטרים שסופקו על ידי המשתמש:
  `model`: `gpt-4`
  `temp`: `0.5`
  `chunk`: `512`

הרחבות תבניות:
`persistent://tg/flow/chunk-load:{id}` → `persistent://tg/flow/chunk-load:customer-A-flow`
`non-persistent://tg/request/embeddings:{class}` → `non-persistent://tg/request/embeddings:standard-rag`
`"model": "{model}"` → `"model": "gpt-4"`
`"temperature": "{temp}"` → `"temperature": "0.5"`
`"chunk_size": "{chunk}"` → `"chunk_size": "512"`

זה יוצר:
<<<<<<< HEAD
צינור עיבוד מסמכים נפרד עבור `customer-A-flow`
=======
צינור עיבוד מסמכים מבודד עבור `customer-A-flow`
>>>>>>> 82edf2d (New md files from RunPod)
שירות הטמעה משותף עבור כל זרימות `standard-rag`
זרימת נתונים שלמה מאיסוף מסמכים דרך שאילתות
מעבדים מוגדרים עם ערכי הפרמטרים שסופקו

## יתרונות

1. **יעילות משאבים**: שירותים יקרים משותפים בין זרימות
2. **בידוד זרימות**: לכל זרימה יש את צינור עיבוד הנתונים שלה
3. **מדרגיות**: ניתן להפעיל מספר זרימות מאותה תבנית
4. **מודולריות**: הפרדה ברורה בין רכיבים משותפים ורכיבים ספציפיים לזרימה
5. **ארכיטקטורה מאוחדת**: שאילתות ועיבוד הם חלק מאותה זרימת נתונים