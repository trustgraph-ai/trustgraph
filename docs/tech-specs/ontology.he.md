---
layout: default
title: "מבנה אונטולוגי - מפרט טכני"
parent: "Hebrew (Beta)"
---

# מבנה אונטולוגי - מפרט טכני

> **Beta Translation:** This document was translated via Machine Learning and as such may not be 100% accurate. All non-English languages are currently classified as Beta.

## סקירה כללית

מפרט זה מתאר את המבנה והפורמט של אונטולוגיות במערכת TrustGraph. אונטולוגיות מספקות מודלים פורמליים של ידע המגדירים מחלקות, תכונות ויחסים, ומאפשרים יכולות של הסקה והסקת מסקנות. המערכת משתמשת בפורמט תצורה השואב השראה מ-OWL, ומייצג באופן כללי מושגי OWL/RDFS תוך התאמה לדרישות של TrustGraph.

**נוהל שמות:** הפרויקט משתמש בפורמט "קאב-קייז" (kebab-case) לכל המזהים (מפתחות תצורה, נקודות קצה של API, שמות מודולים, וכו') במקום "סנקה_קייז" (snake_case).

## מטרות

- **ניהול מחלקות ותכונות:** הגדרת מחלקות "דו-צורתיות" עם תכונות, תחומים, טווחי ערכים ומגבלות סוג
- **תמיכה סמנטית עשירה:** אפשרות לתכונות RDFS/OWL מקיפות, כולל תוויות, תמיכה רב-לשונית ומגבלות פורמליות
- **תמיכה באונטולוגיות מרובות:** אפשרות לאונטולוגיות מרובות להתקיים ולפעול יחד
- **אימות והסקה:** הבטחת עמידה של האונטולוגיות בתקנים דמויי-OWL תוך בדיקות עקביות ותמיכה בהסקה
- **תאימות לתקנים:** תמיכה בייבוא/ייצוא בפורמטים סטנדרטיים (Turtle, RDF/XML, OWL/XML) תוך שמירה על אופטימיזציה פנימית

## רקע

TrustGraph מאחסן אונטולוגיות כפריטים תצורה במערכת מבוססת מפתח-ערך גמישה. למרות שהפורמט מושפע מ-OWL (שפת אונטולוגיה ווב), הוא מותאם במיוחד לשימושים הספציפיים של TrustGraph ואינו עומד במלואן בכל המפרטים של OWL.

אונטולוגיות ב-TrustGraph מאפשרות:
- הגדרה של סוגי אובייקט פורמליים והתכונות שלהם
- הגדרה של תחומים, טווחי ערכים ומגבלות סוג
- הסקה וסקת מסקנות
- יחסים מורכבים ומגבלות כמותיות
- תמיכה רב-לשונית לבינלאומיות

## מבנה אונטולוגי

### אחסון תצורה

אונטולוגיות מאוחסנות כפריטי תצורה עם התבנית הבאה:
- **סוג:** `ontology`
- **מפתח:** מזהה אונטולוגי ייחודי (למשל, `natural-world`, `domain-model`)
- **ערך:** האונטולוגיה השלמה בפורמט JSON

### מבנה JSON

פורמט ה-JSON של האונטולוגיה מורכב מארבעה חלקים עיקריים:

#### 1. מטא-נתונים

מכיל מידע ניהולי ותיאורי על האונטולוגיה:

```json
{
  "metadata": {
    "name": "העולם הטבעי",
    "description": "אונטולוגיה המכסה את הסדר הטבעי",
    "version": "1.0.0",
    "created": "2025-09-20T12:07:37.068Z",
    "modified": "2025-09-20T12:12:20.725Z",
    "creator": "משתמש נוכחי",
    "namespace": "http://trustgraph.ai/ontologies/natural-world",
    "imports": ["http://www.w3.org/2002/07/owl#"]
  }
}
```

**שדות:**
- `name`: שם אנושי של האונטולוגיה
- `description`: תיאור קצר של מטרת האונטולוגיה
- `version`: מספר גרסה סמנטי
- `created`: תאריך ושעה של יצירה בפורמט ISO 8601
- `modified`: תאריך ושעה של העדכון האחרון בפורמט ISO 8601
- `creator`: מזהה המשתמש/מערכת שיוצרת
- `namespace`: URI בסיסי עבור אלמנטי האונטולוגיה
- `imports`: מערך של URI של אונטולוגיות ייבוא

#### 2. מחלקות

מגדיר סוגי אובייקט ויחסים היררכיים:

```json
{
  "classes": {
    "animal": {
      "uri": "http://trustgraph.ai/ontologies/natural-world#animal",
      "type": "owl:Class",
      "rdfs:label": [{"value": "Animal", "lang": "en"}],
      "rdfs:comment": "בעל חיים",
      "rdfs:subClassOf": "lifeform"
    },
    "cat": {
      "uri": "http://trustgraph.ai/ontologies/natural-world#cat",
      "type": "owl:Class",
      "rdfs:label": [{"value": "Cat", "lang": "en"}],
      "rdfs:comment": "חתול",
      "rdfs:subClassOf": "animal"
    },
    "dog": {
      "uri": "http://trustgraph.ai/ontologies/natural-world#dog",
      "type": "owl:Class",
      "rdfs:label": [{"value": "Dog", "lang": "en"}],
      "rdfs:comment": "כלב",
      "rdfs:subClassOf": "animal",
      "owl:disjointWith": ["cat"]
    }
  }
}
```

#### 3. תכונות

מגדיר יחסים בין מחלקות:

```json
{
  "objectProperties": {},
  "datatypeProperties": {
    "number-of-legs": {
      "uri": "http://trustgraph.ai/ontologies/natural-world#number-of-legs",
      "type": "owl:DatatypeProperty",
      "rdfs:label": [{"value": "number-of-legs", "lang": "en"}],
      "rdfs:comment": "ספירת הרגלי הבעל חיים",
      "rdfs:range": "xsd:nonNegativeInteger",
      "rdfs:domain": "animal"
    }
  }
}
```

#### 4. קובץ JSON לדוגמה (סגנון)

```json
{
  "metadata": {
    "name": "אונטולוגיית בעלי חיים",
    "version": "1.0",
    "description": "אונטולוגיה המגדירה סוגי בעלי חיים",
    "created": "2024-01-01T00:00:00Z",
    "modified": "2024-01-01T00:00:00Z",
    "creator": "המשתמש"
  },
  "classes": {
    "בעל חיים": {
      "uri": "http://example.com/animals#Animal",
      "type": "owl:Class",
      "rdfs:label": {
        "value": "בעל חיים",
        "lang": "en"
      }
    },
    "חתול": {
      "uri": "http://example.com/animals#Cat",
      "type": "owl:Class",
      "rdfs:label": {
        "value": "חתול",
        "lang": "en"
      },
      "rdfs:subClassOf": "בעל חיים"
    },
    "כלב": {
      "uri": "http://example.com/animals#Dog",
      "type": "owl:Class",
      "rdfs:label": {
        "value": "כלב",
        "lang": "en"
      },
      "rdfs:subClassOf": "בעל חיים",
      "owl:disjointWith": [
        "חתול"
      ]
    }
  },
  "properties": {
    "hasBody": {
      "type": "owl:ObjectProperty",
      "domain": "בעל חיים",
      "range": "http://example.com/things#Body"
    }
  }
}
```

## כללי אימות

### אימות מבני

1. **עקביות URI:** כל ה-URI צריכים להיות בפורמט `{namespace}#{identifier}`
2. **היררכיית מחלקות:** אין ירושה מעגלית ב-`rdfs:subClassOf`
3. **תחומים/טווח תכונות:** צריכים להתייחס למחלקות קיימות או לסוגי XSD תקינים
4. **מחלקות חופפות:** לא יכולות להיות תחת מחלקות אחרות
5. **תכונות דו-כיוניות:** אם מצוינות, חייבות להיות דו-כיוניות

### אימות סמנטי

1. **מזהים ייחודיים:** מזהי מחלקות ותכונות צריכים להיות ייחודיים באונטולוגיה
2. **תוויות שפה:** צריכות להיות בפורמט BCP 47
3. **מגבלות כמותיות:** `minCardinality` ≤ `maxCardinality` כאשר שניהם מצוינים
4. **תכונות פונקציונליות:** לא צריכות להכיל `maxCardinality` > 1

## תמיכה בפורמט ייבוא/ייצוא

למרות שהפורמט הפנימי הוא JSON, המערכת תומכת בהמרה בין פורמטים סטנדרטיים של אונטולוגיות:

- **Turtle (.ttl)** - פורמט RDF קומפקטי
- **RDF/XML (.rdf, .owl)** - פורמט W3C סטנדרטי
- **OWL/XML (.owx)** - פורמט OWL ספציפי ל-XML
- **JSON-LD (.jsonld)** - JSON עבור נתונים מקושרים
