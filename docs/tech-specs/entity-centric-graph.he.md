# אחסון גרף ידע ממוקד ישויות ב-Cassandra

## סקירה כללית

מסמך זה מתאר מודל אחסון עבור גרפי ידע מסוג RDF ב-Apache Cassandra. המודל משתמש בגישה **ממוקדת ישויות**, כאשר כל ישות יודעת כל רביעיות (quads) בהן היא משתתפת והתפקיד שלה. זה מחליף גישה מסורתית של מספר טבלאות המייצגות את כל הפרמוטציות של Subject, Predicate, Object ו-Dataset (SPOD) עם שתי טבלאות בלבד.

## רקע ומניעים

### הגישה המסורתית

חנות רביעיות RDF סטנדרטית ב-Cassandra דורשת מספר טבלאות לא מנורמלות כדי לכסות דפוסי שאילתות - בדרך כלל 6 טבלאות או יותר המייצגות את הפרמוטציות השונות של Subject, Predicate, Object ו-Dataset (SPOD). כל רביעייה נכתבת לכל טבלה, מה שגורם להגדלת כתיבה משמעותית, תקורה תפעולית ומורכבות סכימה.

בנוסף, פתרון תוויות (שליפת שמות קריאים לבני אדם עבור ישויות) דורש שאילתות נפרדות, דבר שיכול להיות יקר במיוחד במקרי שימוש של AI ו-GraphRAG, שבהם תוויות חיוניות להקשר של מודלי שפה גדולים (LLM).

### התובנה הממוקדת בישות

כל רביעייה `(D, S, P, O)` כוללת עד 4 ישויות. על ידי כתיבת שורה עבור כל השתתפות של ישות ברביעייה, אנו מבטיחים ש-**כל שאילתה עם לפחות רכיב אחד ידוע תפגע במפתח מחיצה**. זה מכסה את כל 16 דפוסי השאילתות עם טבלת נתונים אחת.

יתרונות עיקריים:

**2 טבלאות** במקום 7+
**4 כתיבות לרביעייה** במקום 6+
**פתרון תוויות בחינם** - התוויות של ישות נמצאות יחד עם הקשרים שלה, מה שמחמם באופן טבעי את מטמון האפליקציה.
**כל 16 דפוסי השאילתות** נגישים באמצעות קריאות מחיצה יחידה.
**פעולות פשוטות יותר** - טבלת נתונים אחת לכוונן, לדחוס ולתקן.

## סכימה

### טבלה 1: quads_by_entity

טבלת הנתונים העיקרית. לכל ישות יש מחיצה המכילה את כל הרביעיות בהן היא משתתפת. נקראה כך כדי לשקף את דפוס השאילתה (חיפוש לפי ישות).
פלט חוזה (יש לעקוב אחר הפורמט המדויק).
```sql
CREATE TABLE quads_by_entity (
    collection text,       -- Collection/tenant scope (always specified)
    entity     text,       -- The entity this row is about
    role       text,       -- 'S', 'P', 'O', 'G' — how this entity participates
    p          text,       -- Predicate of the quad
    otype      text,       -- 'U' (URI), 'L' (literal), 'T' (triple/reification)
    s          text,       -- Subject of the quad
    o          text,       -- Object of the quad
    d          text,       -- Dataset/graph of the quad
    dtype      text,       -- XSD datatype (when otype = 'L'), e.g. 'xsd:string'
    lang       text,       -- Language tag (when otype = 'L'), e.g. 'en', 'fr'
    PRIMARY KEY ((collection, entity), role, p, otype, s, o, d, dtype, lang)
);
```

**מפתח מחיצה**: `(collection, entity)` — מוגבל לאוסף, מחיצה אחת לכל ישות.

**ההצדקה עבור סדר עמודי הצבירה**:

1. **role** — רוב השאילתות מתחילות ב"היכן נמצאת ישות זו כנושא/אובייקט"
2. **p** — מסנן נפוץ נוסף, "תן לי את כל `knows` הקשרים"
3. **otype** — מאפשר סינון לפי קשרים בעלי ערך URI לעומת קשרים בעלי ערך מילולי
4. **s, o, d** — עמודות שנותרו לשם ייחודיות
5. **dtype, lang** — מבדילים בין מילולים בעלי אותו ערך אך מטא-נתונים שונים (לדוגמה, `"thing"` לעומת `"thing"@en` לעומת `"thing"^^xsd:string`)

### טבלה 2: quads_by_collection

תומך בשאילתות ובמחיקות ברמת האוסף. מספק תצוגה של כל ה-quads השייכים לאוסף. נקרא כך כדי לשקף את דפוס השאילתה (חיפוש לפי אוסף).

```sql
CREATE TABLE quads_by_collection (
    collection text,
    d          text,       -- Dataset/graph of the quad
    s          text,       -- Subject of the quad
    p          text,       -- Predicate of the quad
    o          text,       -- Object of the quad
    otype      text,       -- 'U' (URI), 'L' (literal), 'T' (triple/reification)
    dtype      text,       -- XSD datatype (when otype = 'L')
    lang       text,       -- Language tag (when otype = 'L')
    PRIMARY KEY (collection, d, s, p, o, otype, dtype, lang)
);
```

מאוגדים לפי קבוצת נתונים תחילה, מה שמאפשר מחיקה ברמת אוסף או ברמת קבוצת נתונים. העמודות `otype`, `dtype` ו-`lang` כלולות במפתח האריגה כדי להבחין בין ערכים המילוליים עם אותו ערך אך עם מטא-נתונים מסוג שונים - ב-RDF, `"thing"`, `"thing"@en` ו-`"thing"^^xsd:string` הם ערכים שונים מבחינה סמנטית.

## נתיב כתיבה

עבור כל רביעייה נכנסת `(D, S, P, O)` בתוך אוסף `C`, כתבו **4 שורות** ל-`quads_by_entity` ו-**שורה אחת** ל-`quads_by_collection`.

### דוגמה

בהינתן הרביעייה באוסף `tenant1`:

```
Dataset:  https://example.org/graph1
Subject:  https://example.org/Alice
Predicate: https://example.org/knows
Object:   https://example.org/Bob
```

כתוב 4 שורות ל-`quads_by_entity`:

| collection | entity | role | p | otype | s | o | d |
|---|---|---|---|---|---|---|---|
| tenant1 | https://example.org/graph1 | G | https://example.org/knows | U | https://example.org/Alice | https://example.org/Bob | https://example.org/graph1 |
| tenant1 | https://example.org/Alice | S | https://example.org/knows | U | https://example.org/Alice | https://example.org/Bob | https://example.org/graph1 |
| tenant1 | https://example.org/knows | P | https://example.org/knows | U | https://example.org/Alice | https://example.org/Bob | https://example.org/graph1 |
| tenant1 | https://example.org/Bob | O | https://example.org/knows | U | https://example.org/Alice | https://example.org/Bob | https://example.org/graph1 |

כתוב שורה אחת ל-`quads_by_collection`:

| collection | d | s | p | o | otype | dtype | lang |
|---|---|---|---|---|---|---|---|
| tenant1 | https://example.org/graph1 | https://example.org/Alice | https://example.org/knows | https://example.org/Bob | U | | |

### דוגמה מילולית

עבור משולש תווית:

```
Dataset:  https://example.org/graph1
Subject:  https://example.org/Alice
Predicate: http://www.w3.org/2000/01/rdf-schema#label
Object:   "Alice Smith" (lang: en)
```

הקוד `otype` הוא `'L'`, `dtype` הוא `'xsd:string'`, ו-`lang` הוא `'en'`. הערך המילולי `"Alice Smith"` מאוחסן ב-`o`. נדרשות רק 3 שורות ב-`quads_by_entity` - שורה אינה נכתבת עבור הערך המילולי כישות, מכיוון שערכים מילוליים אינם ישויות שאפשר לשאול אותן באופן עצמאי.

## תבניות שאילתה

### כל 16 תבניות DSPO

בטבלה למטה, "קידומת מושלמת" פירושה שהשאילתה משתמשת בקידומת רציפה של עמודי הקיבוץ. "סריקת מחיצה + סינון" פירושה ש-Cassandra קוראת חלק ממחיצה ומסננת בזיכרון - יעיל, אבל לא התאמה מדויקת לקידומת.

| # | ידוע | ישות | קידומת קיבוץ | יעילות |
|---|---|---|---|---|
| 1 | D,S,P,O | entity=S, role='S', p=P | התאמה מלאה | קידומת מושלמת |
| 2 | D,S,P,? | entity=S, role='S', p=P | סינון על D | סריקת מחיצה + סינון |
| 3 | D,S,?,O | entity=S, role='S' | סינון על D, O | סריקת מחיצה + סינון |
| 4 | D,?,P,O | entity=O, role='O', p=P | סינון על D | סריקת מחיצה + סינון |
| 5 | ?,S,P,O | entity=S, role='S', p=P | סינון על O | סריקת מחיצה + סינון |
| 6 | D,S,?,? | entity=S, role='S' | סינון על D | סריקת מחיצה + סינון |
| 7 | D,?,P,? | entity=P, role='P' | סינון על D | סריקת מחיצה + סינון |
| 8 | D,?,?,O | entity=O, role='O' | סינון על D | סריקת מחיצה + סינון |
| 9 | ?,S,P,? | entity=S, role='S', p=P | — | **קידומת מושלמת** |
| 10 | ?,S,?,O | entity=S, role='S' | סינון על O | סריקת מחיצה + סינון |
| 11 | ?,?,P,O | entity=O, role='O', p=P | — | **קידומת מושלמת** |
| 12 | D,?,?,? | entity=D, role='G' | — | **קידומת מושלמת** |
| 13 | ?,S,?,? | entity=S, role='S' | — | **קידומת מושלמת** |
| 14 | ?,?,P,? | entity=P, role='P' | — | **קידומת מושלמת** |
| 15 | ?,?,?,O | entity=O, role='O' | — | **קידומת מושלמת** |
| 16 | ?,?,?,? | — | סריקה מלאה | חקירה בלבד |

**תוצאה עיקרית**: 7 מתוך 15 התבניות הלא טריוויאליות הן התאמות מושלמות לקידומת קיבוץ. שמונה הנותרות הן קריאות מחיצה בודדות עם סינון בתוך המחיצה. כל שאילתה עם לפחות רכיב ידוע פוגעת במפתח המחיצה.

התבנית 16 (?,?,?,?) אינה מתרחשת בפועל מכיוון שאוסף תמיד מצוין, מה שמצמצם אותה לתבנית 12.

### דוגמאות נפוצות לשאילתות

**כל דבר על ישות:**

```sql
SELECT * FROM quads_by_entity
WHERE collection = 'tenant1' AND entity = 'https://example.org/Alice';
```

**כל הקשרים יוצאים עבור ישות:**

```sql
SELECT * FROM quads_by_entity
WHERE collection = 'tenant1' AND entity = 'https://example.org/Alice'
AND role = 'S';
```

**תכונה ספציפית עבור ישות:**

```sql
SELECT * FROM quads_by_entity
WHERE collection = 'tenant1' AND entity = 'https://example.org/Alice'
AND role = 'S' AND p = 'https://example.org/knows';
```

**תווית עבור ישות (שפה ספציפית):**

```sql
SELECT * FROM quads_by_entity
WHERE collection = 'tenant1' AND entity = 'https://example.org/Alice'
AND role = 'S' AND p = 'http://www.w3.org/2000/01/rdf-schema#label'
AND otype = 'L';
```

לאחר מכן, במידת הצורך, סננו באמצעות `lang = 'en'` בצד האפליקציה.

**רק קשרים בעלי ערך URI (קישורים בין ישויות לישויות):**

```sql
SELECT * FROM quads_by_entity
WHERE collection = 'tenant1' AND entity = 'https://example.org/Alice'
AND role = 'S' AND p = 'https://example.org/knows' AND otype = 'U';
```

**חיפוש הפוך — מה מצביע על ישות זו:**

```sql
SELECT * FROM quads_by_entity
WHERE collection = 'tenant1' AND entity = 'https://example.org/Bob'
AND role = 'O';
```

## פתרון תוויות וחימום מטמון

אחד היתרונות המשמעותיים ביותר של מודל המרכז את הישות הוא ש**פתרון תוויות הופך לתופעת לוואי חופשית**.

במודל הרב-טבלאי המסורתי, שליפת תוויות דורשת שאילתות נפרדות: יש לשלוף משולשות, לזהות את כתובות ה-URI של הישויות בתוצאות, ולאחר מכן לשלוף `rdfs:label` עבור כל אחת. דפוס N+1 זה יקר.

במודל המרכז את הישות, שאילתה של ישות מחזירה את כל ה-quads שלה - כולל התוויות, הסוגים ותכונות אחרות. כאשר האפליקציה שומרת תוצאות שאילתה במטמון, התוויות מחוממות מראש לפני שמישהו מבקש אותן.

שני מצבי שימוש מאשרים שזה עובד היטב בפועל:

**שאילתות המיועדות למשתמשים**: קבוצות תוצאות קטנות באופן טבעי, תוויות חיוניות. קריאות לישות מחממות את המטמון מראש.
**שאילתות AI/מערכיות**: קבוצות תוצאות גדולות עם מגבלות קשות. תוויות או שאינן נחוצות או נדרשות רק עבור תת-קבוצה מבוקרת של ישויות שכבר נמצאות במטמון.

החשש התיאורטי של פתרון תוויות עבור קבוצות תוצאות גדולות (לדוגמה, 30,000 ישויות) מופחת על ידי התצפית המעשית שאף צרכן אנושי או AI לא מעבד שימושית כמות כזו של תוויות. מגבלות שאילתה ברמת האפליקציה מבטיחות שלחץ המטמון נשאר ניתן לניהול.

## מחיצות רחבות ומימוש

מימוש (הצהרות מסוג RDF-star על הצהרות) יוצר ישויות מרכזיות - לדוגמה, מסמך מקור התומך באלפי עובדות שחולצו. זה יכול ליצור מחיצות רחבות.

גורמים מקלים:

**מגבלות שאילתה ברמת האפליקציה**: כל שאילתות GraphRAG ושאילתות המיועדות למשתמשים מאכפות מגבלות קשות, כך שמחיצות רחבות לעולם אינן נסרקות במלואן בנתיב הקריאה החמה
**Cassandra מטפלת בקריאות חלקיות בצורה יעילה**: סריקת עמודת קיבוץ עם עצירה מוקדמת היא מהירה גם על מחיצות גדולות
**מחיקת אוסף** (הפעולה היחידה שעשויה לעבור על מחיצות מלאות) היא תהליך רקע מקובל

## מחיקת אוסף

מופעלת על ידי קריאת API, רצה ברקע (עקביות בסופו של דבר).

1. קרא `quads_by_collection` עבור האוסף המיועד כדי לקבל את כל ה-quads
2. חלץ ישויות ייחודיות מה-quads (ערכי s, p, o, d)
3. עבור כל ישות ייחודית, מחק את המחיצה מ-`quads_by_entity`
4. מחק את השורות מ-`quads_by_collection`

הטבלה `quads_by_collection` מספקת את האינדקס הדרוש כדי לאתר את כל מחיצות הישויות מבלי לסרוק את הטבלה כולה. מחיקות ברמת המחיצה יעילות מכיוון ש-`(collection, entity)` הוא מפתח המחיצה.

## נתיב מעבר ממודל רב-טבלאי

מודל המרכז את הישות יכול לדור בכפיפות למודל הרב-טבלאי הקיים במהלך המעבר:

1. פרוס את הטבלאות `quads_by_entity` ו-`quads_by_collection` לצד הטבלאות הקיימות
2. כתוב כפול quads חדשים גם לטבלאות הישנות וגם לטבלאות החדשות
3. מלא נתונים קיימים לתוך הטבלאות החדשות
4. העבר נתיבי קריאה דפוס שאילתה בכל פעם
5. הפסק את פעולת הטבלאות הישנות לאחר שכל הקריאות עברו

## סיכום

| היבט | מסורתי (6 טבלאות) | מרכז ישות (2 טבלאות) |
|---|---|---|
| טבלאות | 7+ | 2 |
| כתיבות לכל quad | 6+ | 5 (4 נתונים + 1 מניפסט) |
| פתרון תוויות | מעברי נסיעה נפרדים | חימום מטמון חופשי |
| דפוסי שאילתה | 16 על פני 6 טבלאות | 16 על טבלה אחת |
| מורכבות סכימה | גבוהה | נמוכה |
| תקורה תפעולית | 6 טבלאות לכיול/תיקון | טבלת נתונים אחת |
| תמיכה במימוש | מורכבות נוספת | התאמה טבעית |
| סינון סוגי אובייקטים | לא זמין | ילידי (דרך קיבוץ otype) |
פלט חוזה (יש לעקוב בדיוק אחר הפורמט).
