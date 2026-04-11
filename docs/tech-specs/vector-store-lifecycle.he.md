# ניהול מחזור החיים של מאגר וקטורים

## סקירה כללית

מסמך זה מתאר כיצד TrustGraph מנהלת אוספי מאגרי וקטורים על פני יישומים שונים (Qdrant, Pinecone, Milvus). העיצוב מתמודד עם האתגר של תמיכה בהטבעות עם ממדים שונים מבלי לקודד ערכי ממדים באופן קשיח.

## הצהרת בעיה

מאגרי וקטורים דורשים ציון הממד של ההטבעה בעת יצירת אוספים/אינדקסים. עם זאת:
מודלים שונים של הטבעה מייצרים ממדים שונים (לדוגמה, 384, 768, 1536)
הממד אינו ידוע עד ליצירת ההטבעה הראשונה
אוסף TrustGraph יחיד עשוי לקבל הטבעות ממודלים מרובים
קידוד קשיח של ממד (לדוגמה, 384) גורם לכשלים עם גדלי הטבעה אחרים

## עקרונות עיצוב

1. **יצירה עצלה**: אוספים נוצרים לפי דרישה במהלך הכתיבה הראשונה, ולא במהלך פעולות ניהול אוספים.
2. **שמות המבוססים על ממד**: שמות האוספים כוללים את הממד כסיומת.
3. **התדרדרות חלקה**: שאילתות לאוספים שאינם קיימים מחזירות תוצאות ריקות, ולא שגיאות.
4. **תמיכה במספר ממדים**: אוסף לוגי יחיד יכול לכלול מספר אוספים פיזיים (אחד לכל ממד).

## ארכיטקטורה

### מוסכמות מתן שמות לאוספים

אוספי מאגרי וקטורים משתמשים בסיומות ממד כדי לתמוך במספר גדלי הטבעה:

**הטבעות מסמכים:**
Qdrant: `d_{user}_{collection}_{dimension}`
Pinecone: `d-{user}-{collection}-{dimension}`
Milvus: `doc_{user}_{collection}_{dimension}`

**הטבעות גרף:**
Qdrant: `t_{user}_{collection}_{dimension}`
Pinecone: `t-{user}-{collection}-{dimension}`
Milvus: `entity_{user}_{collection}_{dimension}`

דוגמאות:
`d_alice_papers_384` - אוסף המאמרים של אליס עם הטבעות ממדיות של 384.
`d_alice_papers_768` - אותו אוסף לוגי עם הטבעות ממדיות של 768.
`t_bob_knowledge_1536` - גרף הידע של בוב עם הטבעות ממדיות של 1536.

### שלבי מחזור חיים

#### 1. בקשת יצירת אוסף

**זרימת בקשה:**
```
User/System → Librarian → Storage Management Topic → Vector Stores
```

**התנהגות:**
הספרן משדר בקשות `create-collection` לכל אחסוני הנתונים.
מעבדי אחסון וקטורים מאשרים את הבקשה, אך **אינם יוצרים אוספים פיזיים**.
התגובה מוחזרת מיד עם הצלחה.
יצירת האוסף בפועל נדחית עד לכתיבה הראשונה.

**ההצדקה:**
המימד אינו ידוע בזמן היצירה.
מונע יצירת אוספים עם מימדים שגויים.
מפשט את לוגיקת ניהול האוספים.

#### 2. פעולות כתיבה (יצירה עצלה)

**זרימת הכתיבה:**
```
Data → Storage Processor → Check Collection → Create if Needed → Insert
```

**התנהגות:**
1. חילוץ ממד ההטבעה מהווקטור: `dim = len(vector)`
2. יצירת שם אוסף עם סיומת הממד
3. בדיקה האם קיים אוסף עם אותו ממד ספציפי
4. אם לא קיים:
   יצירת אוסף עם הממד הנכון
   רישום: `"Lazily creating collection {name} with dimension {dim}"`
5. הכנסת ההטבעה לאוסף הספציפי לממד

**תרחיש לדוגמה:**
```
1. User creates collection "papers"
   → No physical collections created yet

2. First document with 384-dim embedding arrives
   → Creates d_user_papers_384
   → Inserts data

3. Second document with 768-dim embedding arrives
   → Creates d_user_papers_768
   → Inserts data

Result: Two physical collections for one logical collection
```

#### 3. פעולות שאילתה

**זרימת השאילתה:**
```
Query Vector → Determine Dimension → Check Collection → Search or Return Empty
```

**התנהגות:**
1. חילוץ מימד מהווקטור של השאילתה: `dim = len(vector)`
2. יצירת שם אוסף עם סיומת המציינת את המימד
3. בדיקה האם האוסף קיים
4. אם קיים:
   ביצוע חיפוש דמיון
   החזרת תוצאות
5. אם לא קיים:
   רישום: `"Collection {name} does not exist, returning empty results"`
   החזרת רשימה ריקה (ללא העלאת שגיאה)

**מימדים מרובים באותה שאילתה:**
אם השאילתה מכילה וקטורים של מימדים שונים
כל מימד מבצע שאילתה על האוסף המתאים לו
התוצאות מאוחדות
אוספים חסרים מדלגים (לא מטופלים כשגיאות)

**ההצדקה:**
שאילתה על אוסף ריק היא מקרה שימוש חוקי
החזרת תוצאות ריקות היא נכונה מבחינה סמנטית
מונע שגיאות במהלך אתחול המערכת או לפני טעינת נתונים

#### 4. מחיקת אוסף

**תהליך מחיקה:**
```
Delete Request → List All Collections → Filter by Prefix → Delete All Matches
```

**התנהגות:**
1. בניית תבנית קידומת: `d_{user}_{collection}_` (שימו לב לקו התחתון בסוף)
2. רשימת כל האוספים במאגר הווקטורים
3. סינון אוספים התואמים לקידומת
4. מחיקת כל האוספים התואמים
5. רישום כל מחיקה: `"Deleted collection {name}"`
6. רישום סיכום: `"Deleted {count} collection(s) for {user}/{collection}"`

**דוגמה:**
```
Collections in store:
- d_alice_papers_384
- d_alice_papers_768
- d_alice_reports_384
- d_bob_papers_384

Delete "papers" for alice:
→ Deletes: d_alice_papers_384, d_alice_papers_768
→ Keeps: d_alice_reports_384, d_bob_papers_384
```

**הסבר:**
מבטיח ניקוי מלא של כל וריאציות המימדים.
התאמת תבניות מונעת מחיקה בשוגע של אוספים לא קשורים.
פעולה אטומית מנקודת מבטו של המשתמש (כל המימדים נמחקים יחד).

## מאפיינים התנהגותיים

### פעולות רגילות

**יצירת אוסף:**
✓ מחזיר הצלחה באופן מיידי.
✓ לא מוקצה אחסון פיזי.
✓ פעולה מהירה (ללא קלט/פלט של מערכת הפעלה).

**כתיבה ראשונה:**
✓ יוצר אוסף עם מימד נכון.
✓ מעט איטי יותר עקב תקורה של יצירת האוסף.
✓ כתיבות עוקבות לאותו מימד מהירות.

**שאילתות לפני כל כתיבה:**
✓ מחזיר תוצאות ריקות.
✓ אין שגיאות או חריגות.
✓ המערכת נשארת יציבה.

**כתיבות של מימדים שונים:**
✓ יוצר באופן אוטומטי אוספים נפרדים לכל מימד.
✓ כל מימד מבודד באוסף משלו.
✓ אין התנגשויות מימדים או שגיאות סכימה.

**מחיקת אוסף:**
✓ מסיר את כל וריאציות המימדים.
✓ ניקוי מלא.
✓ אין אוספים יתומים.

### מקרים קצה

**מודלים משובצים מרובים:**
```
Scenario: User switches from model A (384-dim) to model B (768-dim)
Behavior:
- Both dimensions coexist in separate collections
- Old data (384-dim) remains queryable with 384-dim vectors
- New data (768-dim) queryable with 768-dim vectors
- Cross-dimension queries return results only for matching dimension
```

**כתיבות ראשוניות מקבילות:**
```
Scenario: Multiple processes write to same collection simultaneously
Behavior:
- Each process checks for existence before creating
- Most vector stores handle concurrent creation gracefully
- If race condition occurs, second create is typically idempotent
- Final state: Collection exists and both writes succeed
```

**הגירה של ממדים:**
```
Scenario: User wants to migrate from 384-dim to 768-dim embeddings
Behavior:
- No automatic migration
- Old collection (384-dim) persists
- New collection (768-dim) created on first new write
- Both dimensions remain accessible
- Manual deletion of old dimension collections possible
```

**שאילתות לאוספים ריקים:**
```
Scenario: Query a collection that has never received data
Behavior:
- Collection doesn't exist (never created)
- Query returns empty list
- No error state
- System logs: "Collection does not exist, returning empty results"
```

## הערות יישום

### פרטים ספציפיים לגבי אחסון

**Qdrant:**
משתמש ב-`collection_exists()` לבדיקות קיום
משתמש ב-`get_collections()` לרשימה במהלך מחיקה
יצירת אוסף דורשת `VectorParams(size=dim, distance=Distance.COSINE)`

**Pinecone:**
משתמש ב-`has_index()` לבדיקות קיום
משתמש ב-`list_indexes()` לרשימה במהלך מחיקה
יצירת אינדקס דורשת המתנה למצב "מוכן"
מפרט שרת חסר מוגדר עם ענן/אזור

**Milvus:**
מחלקות ישירות (`DocVectors`, `EntityVectors`) מנהלות את מחזור החיים
מטמון פנימי `self.collections[(dim, user, collection)]` לביצועים
שמות אוספים עוברים סינון (רק תווים אלפאנומריים וקו תחתון)
תומך בסכימה עם מזהים עם הגדלה אוטומטית

### שיקולי ביצועים

**זמן השהייה לכתיבה ראשונה:**
תקורה נוספת עקב יצירת אוסף
Qdrant: ~100-500ms
Pinecone: ~10-30 שניות (הקצאת שרת חסר)
Milvus: ~500-2000ms (כולל אינדקס)

**ביצועי שאילתות:**
בדיקת קיום מוסיפה תקורה מינימלית (~1-10ms)
אין השפעה על הביצועים לאחר יצירת האוסף
כל אוסף ממד מותאם באופן עצמאי

**תקורה של אחסון:**
מטא-דאטה מינימלי לכל אוסף
התקורה העיקרית היא אחסון לכל ממד
פשרה: שטח אחסון לעומת גמישות ממדים

## שיקולים עתידיים

**איחוד ממדים אוטומטי:**
ניתן להוסיף תהליך רקע לזיהוי ומיזוג גרסאות ממדים לא בשימוש
זה ידרוש הטמעה מחדש או צמצום ממדים

**גילוי ממדים:**
ניתן לחשוף API לרשימת כל הממדים בשימוש עבור אוסף
שימושי לניהול וניטור

**העדפה ברירת מחדל לממד:**
ניתן לעקוב אחר "ממד ראשי" לכל אוסף
להשתמש עבור שאילתות כאשר הקשר הממד אינו זמין

**מכסות אחסון:**
ייתכן שיהיה צורך במגבלות ממדים לכל אוסף
למנוע התרבות של גרסאות ממדים

## הערות העברה

**ממערכת קודמת עם סיומת ממד:**
אוספים ישנים: `d_{user}_{collection}` (ללא סיומת ממד)
אוספים חדשים: `d_{user}_{collection}_{dim}` (עם סיומת ממד)
אין העברה אוטומטית - אוספים ישנים נשארים נגישים
שקול סקריפט העברה ידני אם יש צורך
ניתן להפעיל שני סכימות שמות בו זמנית

## הפניות

ניהול אוספים: `docs/tech-specs/collection-management.md`
סכימת אחסון: `trustgraph-base/trustgraph/schema/services/storage.py`
שירות ספרית: `trustgraph-flow/trustgraph/librarian/service.py`
