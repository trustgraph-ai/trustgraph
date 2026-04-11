---
layout: default
title: "חילוץ ידע מתוך אונטולוגיות - שלב 2, שיפור מחדש"
parent: "Hebrew (Beta)"
---

# חילוץ ידע מתוך אונטולוגיות - שלב 2, שיפור מחדש

> **Beta Translation:** This document was translated via Machine Learning and as such may not be 100% accurate. All non-English languages are currently classified as Beta.

**סטטוס**: טיוטה
**מחבר**: מפגש ניתוח 2025-12-03
**קשור**: `ontology.md`, `ontorag.md`

## סקירה כללית

מסמך זה מזהה אי-התאמות במערכת הנוכחית לחילוץ ידע המבוססת על אונטולוגיות, ומציע שיפור מחדש כדי לשפר את הביצועים של מודלי שפה גדולים (LLM) ולהפחית אובדן מידע.

## יישום נוכחי

### איך זה עובד כרגע

1. **טעינת אונטולוגיה** (`ontology_loader.py`)
   טוען קובץ JSON של אונטולוגיה עם מפתחות כמו `"fo/Recipe"`, `"fo/Food"`, `"fo/produces"`
   מזהי מחלקות כוללים את הקידומת של מרחב השמות במפתח עצמו
   דוגמה מ-`food.ontology`:
     ```json
     "classes": {
       "fo/Recipe": {
         "uri": "http://purl.org/ontology/fo/Recipe",
         "rdfs:comment": "A Recipe is a combination..."
       }
     }
     ```

2. **בניית הנחיה** (`extract.py:299-307`, `ontology-prompt.md`)
   התבנית מקבלת מילונים `classes`, `object_properties`, `datatype_properties`
   התבנית חוזרת: `{% for class_id, class_def in classes.items() %}`
   מודל השפה (LLM) רואה: `**fo/Recipe**: A Recipe is a combination...`
   פורמט פלט לדוגמה מציג:
     ```json
     {"subject": "recipe:cornish-pasty", "predicate": "rdf:type", "object": "Recipe"}
     {"subject": "recipe:cornish-pasty", "predicate": "has_ingredient", "object": "ingredient:flour"}
     ```

3. **ניתוח תגובה** (`extract.py:382-428`)
   מצפה למערך JSON: `[{"subject": "...", "predicate": "...", "object": "..."}]`
   מאמת מול תת-אונטולוגיה
   מרחיב URI באמצעות `expand_uri()` (extract.py:473-521)

4. **הרחבת URI** (`extract.py:473-521`)
   בודק אם הערך נמצא במילון `ontology_subset.classes`
   אם נמצא, מחלץ את ה-URI מההגדרה של המחלקה
   אם לא נמצא, בונה את ה-URI: `f"https://trustgraph.ai/ontology/{ontology_id}#{value}"`

### דוגמה לזרימת נתונים

**JSON של אונטולוגיה → Loader → Prompt:**
```
"fo/Recipe" → classes["fo/Recipe"] → LLM sees "**fo/Recipe**"
```

**מודל שפה גדול → מנתח → פלט:**
```
"Recipe" → not in classes["fo/Recipe"] → constructs URI → LOSES original URI
"fo/Recipe" → found in classes → uses original URI → PRESERVES URI
```

## בעיות שזוהו

### 1. **דוגמאות לא עקביות בהנחיה**

**בעיה**: תבנית ההנחיה מציגה מזהי מחלקות עם קידומות (`fo/Recipe`) אך הפלט לדוגמה משתמש בשמות מחלקות ללא קידומות (`Recipe`).

**מיקום**: `ontology-prompt.md:5-52`

```markdown
## Ontology Classes:
- **fo/Recipe**: A Recipe is...

## Example Output:
{"subject": "recipe:cornish-pasty", "predicate": "rdf:type", "object": "Recipe"}
```

**השפעה**: מודל השפה הגדול (LLM) מקבל אותות סותרים לגבי הפורמט שיש להשתמש בו.

### 2. **אובדן מידע בהרחבת כתובות URL**

**בעיה**: כאשר מודל השפה הגדול (LLM) מחזיר שמות מחלקות ללא קידומת, בהתאם לדוגמה, `expand_uri()` לא יכול למצוא אותם במילון האונטולוגיה ויוצר כתובות URL חלופיות, ובכך מאבד את כתובות ה-URL המקוריות הנכונות.

**מיקום**: `extract.py:494-500`

```python
if value in ontology_subset.classes:  # Looks for "Recipe"
    class_def = ontology_subset.classes[value]  # But key is "fo/Recipe"
    if isinstance(class_def, dict) and 'uri' in class_def:
        return class_def['uri']  # Never reached!
return f"https://trustgraph.ai/ontology/{ontology_id}#{value}"  # Fallback
```

**השפעה:**
URI מקורי: `http://purl.org/ontology/fo/Recipe`
URI שנוצר: `https://trustgraph.ai/ontology/food#Recipe`
אובדן משמעות סמנטית, פוגע בתאימות.

### 3. **פורמט לא ברור של מופעי ישויות**

**בעיה:** אין הנחיות ברורות לגבי פורמט ה-URI של מופעי ישויות.

**דוגמאות בהנחיה:**
`"recipe:cornish-pasty"` (קידומת הדומה לשם מרחב)
`"ingredient:flour"` (קידומת שונה)

**התנהגות בפועל** (extract.py:517-520):
```python
# Treat as entity instance - construct unique URI
normalized = value.replace(" ", "-").lower()
return f"https://trustgraph.ai/{ontology_id}/{normalized}"
```

**השפעה**: מודל שפה גדול (LLM) חייב לנחש את מוסכמות הקידומת ללא הקשר אונטולוגי.

### 4. **הנחיות לגבי קידומות מרחבי שמות חסרות**

**בעיה**: קובץ ה-JSON של האונטולוגיה מכיל הגדרות מרחבי שמות (שורות 10-25 בקובץ food.ontology):
```json
"namespaces": {
  "fo": "http://purl.org/ontology/fo/",
  "rdf": "http://www.w3.org/1999/02/22-rdf-syntax-ns#",
  ...
}
```

אבל השורות האלה לעולם אינן מוצגות למודל השפה הגדול (LLM). מודל השפה הגדול אינו יודע:
מה המשמעות של "fo"
איזה קידומת להשתמש עבור ישויות
לאיזה מרחב שם מתייחס כל אלמנט

### 5. **תוויות שאינן משמשות בפרומפט**

**בעיה**: לכל מחלקה יש שדות `rdfs:label` (לדוגמה, `{"value": "Recipe", "lang": "en-gb"}`), אבל תבנית הפרומפט אינה משתמשת בהם.

**מצב נוכחי**: מציג רק `class_id` ו-`comment`
```jinja
- **{{class_id}}**{% if class_def.comment %}: {{class_def.comment}}{% endif %}
```

**זמין אך לא בשימוש:**
```python
"rdfs:label": [{"value": "Recipe", "lang": "en-gb"}]
```

**השפעה:** יכול לספק שמות קריאים לבני אדם לצד מזהים טכניים.

## פתרונות מוצעים

### אפשרות א': נרמול למזהים ללא קידומת

**גישה:** הסרת קידומות ממזהי מחלקות לפני הצגתם למודל LLM.

**שינויים:**
1. שנה את `build_extraction_variables()` כדי לשנות מפתחות:
   ```python
   classes_for_prompt = {
       k.split('/')[-1]: v  # "fo/Recipe" → "Recipe"
       for k, v in ontology_subset.classes.items()
   }
   ```

2. עדכון דוגמת ההנחיה כך שתתאים (כבר משתמשת בשמות ללא קידומת).

3. שינוי `expand_uri()` כדי לטפל בשני הפורמטים:
   ```python
   # Try exact match first
   if value in ontology_subset.classes:
       return ontology_subset.classes[value]['uri']

   # Try with prefix
   for prefix in ['fo/', 'rdf:', 'rdfs:']:
       prefixed = f"{prefix}{value}"
       if prefixed in ontology_subset.classes:
           return ontology_subset.classes[prefixed]['uri']
   ```

**יתרונות:**
נקי יותר, קריא יותר לבני אדם
תואם לדוגמאות קיימות של הנחיות
מודלי שפה גדולים (LLMs) עובדים טוב יותר עם טוקנים פשוטים יותר

**חסרונות:**
התנגשויות בשמות מחלקות אם למספר אונטולוגיות יש אותו שם מחלקה
מאבד מידע על מרחב השמות
דורש לוגיקה חלופית עבור חיפושים

### אפשרות ב': שימוש עקבי במזהים עם קידומת מלאה

**גישה:** עדכון הדוגמאות לשימוש במזהים עם קידומת התואמים למה שמוצג ברשימת המחלקות.

**שינויים:**
1. עדכון דוגמת הנחיה (ontology-prompt.md:46-52):
   ```json
   [
     {"subject": "recipe:cornish-pasty", "predicate": "rdf:type", "object": "fo/Recipe"},
     {"subject": "recipe:cornish-pasty", "predicate": "rdfs:label", "object": "Cornish Pasty"},
     {"subject": "recipe:cornish-pasty", "predicate": "fo/produces", "object": "food:cornish-pasty"},
     {"subject": "food:cornish-pasty", "predicate": "rdf:type", "object": "fo/Food"}
   ]
   ```

2. הוספת הסבר על מרחב הnamespaces להנחיה:
   ```markdown
   ## Namespace Prefixes:
   - **fo/**: Food Ontology (http://purl.org/ontology/fo/)
   - **rdf:**: RDF Schema
   - **rdfs:**: RDF Schema

   Use these prefixes exactly as shown when referencing classes and properties.
   ```

3. שמרו על `expand_uri()` כפי שהוא (עובד כראוי כאשר נמצאו התאמות).

**יתרונות:**
עקביות בין קלט לפלט.
ללא אובדן מידע.
שומר על סמנטיקת מרחבי השמות.
עובד עם מרובות אונטולוגיות.

**חסרונות:**
טוקנים מילוליים יותר עבור מודל שפה גדול (LLM).
דורש ממודל השפה הגדול (LLM) לעקוב אחר קידומות.

### אפשרות ג': היברידית - הצגת תווית ומזהה כאחד.

**גישה:** שיפור ההנחיה להצגת תוויות קריאות אנוש ומזהים טכניים.

**שינויים:**
1. עדכון תבנית ההנחיה:
   ```jinja
   {% for class_id, class_def in classes.items() %}
   - **{{class_id}}** (label: "{{class_def.labels[0].value if class_def.labels else class_id}}"){% if class_def.comment %}: {{class_def.comment}}{% endif %}
   {% endfor %}
   ```

   פלט לדוגמה:
   ```markdown
   - **fo/Recipe** (label: "Recipe"): A Recipe is a combination...
   ```

2. הוראות עדכון:
   ```markdown
   When referencing classes:
   - Use the full prefixed ID (e.g., "fo/Recipe") in JSON output
   - The label (e.g., "Recipe") is for human understanding only
   ```

**יתרונות:**
הבהרה עבור מודלי שפה גדולים (LLM)
שומר על כל המידע
מפרט במפורש מה להשתמש

**חסרונות:**
הנחיה ארוכה יותר
תבנית מורכבת יותר

## גישה מיושמת

**פורמט פשוט של ישות-קשר-תכונה** - מחליף לחלוטין את הפורמט המבוסס על שלישיות הישן.

הגישה החדשה נבחרה מכיוון:

1. **ללא אובדן מידע:** כתובות URI מקוריות נשמרות כהלכה
2. **לוגיקה פשוטה יותר:** אין צורך בטרנספורמציה, חיפושים ישירים במילון עובדים
3. **בטיחות מרחבי שמות:** מטפל במספר אונטולוגיות ללא התנגשויות
4. **נכונות סמנטית:** שומר על סמנטיקה של RDF/OWL

## יישום הושלם

### מה נבנה:

1. **תבנית הנחיה חדשה** (`prompts/ontology-extract-v2.txt`)
   ✅ חלקים ברורים: סוגי ישויות, קשרים, תכונות
   ✅ דוגמה תוך שימוש במזהים מלאים של סוגים (`fo/Recipe`, `fo/has_ingredient`)
   ✅ הוראות לשימוש במזהים מדויקים מהסכימה
   ✅ פורמט JSON חדש עם מערכים של ישויות/קשרים/תכונות

2. **נרמול ישויות** (`entity_normalizer.py`)
   ✅ `normalize_entity_name()` - ממיר שמות לפורמט בטוח ל-URI
   ✅ `normalize_type_identifier()` - מטפל בסלאשים בסוגים (`fo/Recipe` → `fo-recipe`)
   ✅ `build_entity_uri()` - יוצר כתובות URI ייחודיות באמצעות טאפל (שם, סוג)
   ✅ `EntityRegistry` - עוקב אחר ישויות לצורך הסרה כפולה

3. **מנתח JSON** (`simplified_parser.py`)
   ✅ מנתח את הפורמט החדש: `{entities: [...], relationships: [...], attributes: [...]}`
   ✅ תומך בשמות שדות בפורמט kebab-case ו-snake_case
   ✅ מחזיר מחלקות נתונים מובנות
   ✅ טיפול בשגיאות בצורה חלקה עם רישום

4. **ממיר שלישיות** (`triple_converter.py`)
   ✅ `convert_entity()` - מייצר באופן אוטומטי שלישיות של סוג + תווית
   ✅ `convert_relationship()` - מחבר כתובות URI של ישויות באמצעות מאפיינים
   ✅ `convert_attribute()` - מוסיף ערכים מילוליים
   ✅ מחפש כתובות URI מלאות מהגדרות האונטולוגיה

5. **מעבד ראשי מעודכן** (`extract.py`)
   ✅ הסר קוד חילוץ ישן מבוסס על שלישיות
   ✅ הוסף שיטה `extract_with_simplified_format()`
   ✅ משתמש כעת אך ורק בפורמט הפשוט החדש
   ✅ קורא להנחיה עם מזהה `extract-with-ontologies-v2`

## מקרי בדיקה

### בדיקה 1: שימור כתובות URI
```python
# Given ontology class
classes = {"fo/Recipe": {"uri": "http://purl.org/ontology/fo/Recipe", ...}}

# When LLM returns
llm_output = {"subject": "x", "predicate": "rdf:type", "object": "fo/Recipe"}

# Then expanded URI should be
assert expanded == "http://purl.org/ontology/fo/Recipe"
# Not: "https://trustgraph.ai/ontology/food#Recipe"
```

### מבחן 2: התנגשות בין מרובי אונטולוגיות
```python
# Given two ontologies
ont1 = {"fo/Recipe": {...}}
ont2 = {"cooking/Recipe": {...}}

# LLM should use full prefix to disambiguate
llm_output = {"object": "fo/Recipe"}  # Not just "Recipe"
```

### מבחן 3: פורמט של מופע ישות
```python
# Given prompt with food ontology
# LLM should create instances like
{"subject": "recipe:cornish-pasty"}  # Namespace-style
{"subject": "food:beef"}              # Consistent prefix
```

## שאלות פתוחות

1. **האם יש להשתמש בתוספות מרחב שם עבור מופעי ישויות?**
   נוכחי: `"recipe:cornish-pasty"` (שרירותי)
   חלופה: להשתמש בתוסף אוֹנוֹטוֹלוֹגיה `"fo:cornish-pasty"`?
   חלופה: ללא תוסף, להרחיב ב-URI `"cornish-pasty"` → URI מלא?

2. **כיצד לטפל בתחום/טווח בפרומפט?**
   מוצג כעת: `(Recipe → Food)`
   האם זה צריך להיות: `(fo/Recipe → fo/Food)`?

3. **האם עלינו לאמת אילוצי תחום/טווח?**
   הערה TODO ב-extract.py:470
   יתפוס יותר שגיאות אך מורכב יותר

4. **מה לגבי תכונות הפוכות ושקילות?**
   לאוֹנוֹטוֹלוֹגיה יש `owl:inverseOf`, `owl:equivalentClass`
   לא בשימוש כרגע בחילוץ
   האם הם צריכים להיות בשימוש?

## מדדי הצלחה

✅ אפס אובדן מידע URI (שימור של 100% מה-URIs המקוריים)
✅ פורמט הפלט של ה-LLM תואם לפורמט הקלט
✅ אין דוגמאות מעורפלות בפרומפט
✅ הבדיקות עוברות עם אוֹנוֹטוֹלוֹגיות מרובות
✅ שיפור באיכות החילוץ (נמדד על ידי אחוז משולשות חוקיות)

## גישה חלופית: פורמט חילוץ מפושט

### פילוסופיה

במקום לבקש מה-LLM להבין סמנטיקה של RDF/OWL, לבקש ממנו לעשות את מה שהוא טוב בו: **למצוא ישויות ויחסים בטקסט**.

תן לקוד לטפל בבניית URI, המרת RDF ופורמליות של רשת סמנטית.

### דוגמה: סיווג ישויות

**טקסט קלט:**
```
Cornish pasty is a traditional British pastry filled with meat and vegetables.
```

**סכימת אונטולוגיה (מוצגת למודל שפה גדול):**
```markdown
## Entity Types:
- Recipe: A recipe is a combination of ingredients and a method
- Food: A food is something that can be eaten
- Ingredient: An ingredient combines a quantity and a food
```

**מה שהמודל השפה הגדול מחזיר (JSON פשוט):**
```json
{
  "entities": [
    {
      "entity": "Cornish pasty",
      "type": "Recipe"
    }
  ]
}
```

**מה הקוד מייצר (משולשי RDF):**
```python
# 1. Normalize entity name + type to ID (type prevents collisions)
entity_id = "recipe-cornish-pasty"  # normalize("Cornish pasty", "Recipe")
entity_uri = "https://trustgraph.ai/food/recipe-cornish-pasty"

# Note: Same name, different type = different URI
# "Cornish pasty" (Recipe) → recipe-cornish-pasty
# "Cornish pasty" (Food) → food-cornish-pasty

# 2. Generate triples
triples = [
    # Type triple
    Triple(
        s=Value(value=entity_uri, is_uri=True),
        p=Value(value="http://www.w3.org/1999/02/22-rdf-syntax-ns#type", is_uri=True),
        o=Value(value="http://purl.org/ontology/fo/Recipe", is_uri=True)
    ),
    # Label triple (automatic)
    Triple(
        s=Value(value=entity_uri, is_uri=True),
        p=Value(value="http://www.w3.org/2000/01/rdf-schema#label", is_uri=True),
        o=Value(value="Cornish pasty", is_uri=False)
    )
]
```

### יתרונות

1. **מודל שפה גדול (LLM) לא צריך:**
   להבין תחביר URI
   להמציא קידומות מזהות (`recipe:`, `ingredient:`)
   לדעת על `rdf:type` או `rdfs:label`
   לבנות מזהי רשת סמנטית

2. **מודל שפה גדול (LLM) צריך רק:**
   למצוא ישויות בטקסט
   למפות אותן למחלקות אונטולוגיה
   לחלץ קשרים ומאפיינים

3. **הקוד מטפל ב:**
   נרמול ובניית URI
   יצירת משולשות RDF
   הקצאת תוויות אוטומטית
   ניהול מרחבי שמות

### למה זה עובד טוב יותר

**שאילתה פשוטה יותר** = פחות בלבול = פחות שגיאות
**מזהים עקביים** = הקוד שולט בכללי הנרמול
**תוויות שנוצרו אוטומטית** = אין משולשות rdfs:label חסרות
**מודל שפה גדול מתמקד בחילוץ** = במה שהוא באמת טוב

### דוגמה: קשרי ישויות

**טקסט קלט:**
```
Cornish pasty is a traditional British pastry filled with beef and potatoes.
```

**סכימת אונטולוגיה (מוצגת למודל שפה גדול):**
```markdown
## Entity Types:
- Recipe: A recipe is a combination of ingredients and a method
- Food: A food is something that can be eaten
- Ingredient: An ingredient combines a quantity and a food

## Relationships:
- has_ingredient: Relates a recipe to an ingredient it uses (Recipe → Ingredient)
- food: Relates an ingredient to the food that is required (Ingredient → Food)
```

**מה שהמודל השפה הגדול מחזיר (JSON פשוט):**
```json
{
  "entities": [
    {
      "entity": "Cornish pasty",
      "type": "Recipe"
    },
    {
      "entity": "beef",
      "type": "Food"
    },
    {
      "entity": "potatoes",
      "type": "Food"
    }
  ],
  "relationships": [
    {
      "subject": "Cornish pasty",
      "subject-type": "Recipe",
      "relation": "has_ingredient",
      "object": "beef",
      "object-type": "Food"
    },
    {
      "subject": "Cornish pasty",
      "subject-type": "Recipe",
      "relation": "has_ingredient",
      "object": "potatoes",
      "object-type": "Food"
    }
  ]
}
```

**מה הקוד מייצר (משולשי RDF):**
```python
# Normalize entity names to URIs
cornish_pasty_uri = "https://trustgraph.ai/food/cornish-pasty"
beef_uri = "https://trustgraph.ai/food/beef"
potatoes_uri = "https://trustgraph.ai/food/potatoes"

# Look up relation URI from ontology
has_ingredient_uri = "http://purl.org/ontology/fo/ingredients"  # from fo/has_ingredient

triples = [
    # Entity type triples (as before)
    Triple(s=cornish_pasty_uri, p=rdf_type, o="http://purl.org/ontology/fo/Recipe"),
    Triple(s=cornish_pasty_uri, p=rdfs_label, o="Cornish pasty"),

    Triple(s=beef_uri, p=rdf_type, o="http://purl.org/ontology/fo/Food"),
    Triple(s=beef_uri, p=rdfs_label, o="beef"),

    Triple(s=potatoes_uri, p=rdf_type, o="http://purl.org/ontology/fo/Food"),
    Triple(s=potatoes_uri, p=rdfs_label, o="potatoes"),

    # Relationship triples
    Triple(
        s=Value(value=cornish_pasty_uri, is_uri=True),
        p=Value(value=has_ingredient_uri, is_uri=True),
        o=Value(value=beef_uri, is_uri=True)
    ),
    Triple(
        s=Value(value=cornish_pasty_uri, is_uri=True),
        p=Value(value=has_ingredient_uri, is_uri=True),
        o=Value(value=potatoes_uri, is_uri=True)
    )
]
```

**נקודות עיקריות:**
מודל שפה גדול (LLM) מחזיר שמות של ישויות בשפה טבעית: `"Cornish pasty"`, `"beef"`, `"potatoes"`
מודל שפה גדול (LLM) כולל סוגים כדי להבהיר: `subject-type`, `object-type`
מודל שפה גדול (LLM) משתמש בשם היחס מהסכימה: `"has_ingredient"`
הקוד מייצר מזהים עקביים באמצעות (שם, סוג): `("Cornish pasty", "Recipe")` → `recipe-cornish-pasty`
הקוד מחפש את ה-URI של היחס מהאונטולוגיה: `fo/has_ingredient` → URI מלא
אותה טופל (שם, סוג) תמיד מקבל את אותו ה-URI (הסרה כפילות)

### דוגמה: הבחנה בין שמות של ישויות

**בעיה:** אותו שם יכול להתייחס לסוגי ישויות שונים.

**מקרה אמיתי:**
```
"Cornish pasty" can be:
- A Recipe (instructions for making it)
- A Food (the dish itself)
```

**כיצד זה מטופל:**

מודל שפה גדול (LLM) מחזיר את שניהם כיחידות נפרדות:
```json
{
  "entities": [
    {"entity": "Cornish pasty", "type": "Recipe"},
    {"entity": "Cornish pasty", "type": "Food"}
  ],
  "relationships": [
    {
      "subject": "Cornish pasty",
      "subject-type": "Recipe",
      "relation": "produces",
      "object": "Cornish pasty",
      "object-type": "Food"
    }
  ]
}
```

**פתרון קוד:**
```python
# Different types → different URIs
recipe_uri = normalize("Cornish pasty", "Recipe")
# → "https://trustgraph.ai/food/recipe-cornish-pasty"

food_uri = normalize("Cornish pasty", "Food")
# → "https://trustgraph.ai/food/food-cornish-pasty"

# Relationship connects them correctly
triple = Triple(
    s=recipe_uri,  # The Recipe
    p="http://purl.org/ontology/fo/produces",
    o=food_uri     # The Food
)
```

**מדוע זה עובד:**
הסוג כלול בכל ההפניות (ישויות, קשרים, תכונות)
הקוד משתמש בטופל `(name, type)` כמפתח חיפוש
אין דו-משמעות, אין התנגשויות

### דוגמה: תכונות של ישויות

**טקסט קלט:**
```
This Cornish pasty recipe serves 4-6 people and takes 45 minutes to prepare.
```

**סכימת אונטולוגיה (מוצגת למודל שפה גדול):**
```markdown
## Entity Types:
- Recipe: A recipe is a combination of ingredients and a method

## Attributes:
- serves: Indicates what the recipe is intended to serve (Recipe → text)
- preparation_time: Time needed to prepare the recipe (Recipe → text)
```

**מה שהמודל השפה הגדול מחזיר (JSON פשוט):**
```json
{
  "entities": [
    {
      "entity": "Cornish pasty recipe",
      "type": "Recipe"
    }
  ],
  "attributes": [
    {
      "entity": "Cornish pasty recipe",
      "entity-type": "Recipe",
      "attribute": "serves",
      "value": "4-6 people"
    },
    {
      "entity": "Cornish pasty recipe",
      "entity-type": "Recipe",
      "attribute": "preparation_time",
      "value": "45 minutes"
    }
  ]
}
```

**מה הקוד מייצר (משולשים RDF):**
```python
# Normalize entity name to URI
recipe_uri = "https://trustgraph.ai/food/cornish-pasty-recipe"

# Look up attribute URIs from ontology
serves_uri = "http://purl.org/ontology/fo/serves"  # from fo/serves
prep_time_uri = "http://purl.org/ontology/fo/preparation_time"  # from fo/preparation_time

triples = [
    # Entity type triple
    Triple(
        s=Value(value=recipe_uri, is_uri=True),
        p=Value(value=rdf_type, is_uri=True),
        o=Value(value="http://purl.org/ontology/fo/Recipe", is_uri=True)
    ),

    # Label triple (automatic)
    Triple(
        s=Value(value=recipe_uri, is_uri=True),
        p=Value(value=rdfs_label, is_uri=True),
        o=Value(value="Cornish pasty recipe", is_uri=False)
    ),

    # Attribute triples (objects are literals, not URIs)
    Triple(
        s=Value(value=recipe_uri, is_uri=True),
        p=Value(value=serves_uri, is_uri=True),
        o=Value(value="4-6 people", is_uri=False)  # Literal value!
    ),
    Triple(
        s=Value(value=recipe_uri, is_uri=True),
        p=Value(value=prep_time_uri, is_uri=True),
        o=Value(value="45 minutes", is_uri=False)  # Literal value!
    )
]
```

**נקודות עיקריות:**
מודל שפה גדול (LLM) מחלץ ערכים מילוליים: `"4-6 people"`, `"45 minutes"`
מודל שפה גדול (LLM) כולל סוג ישות לצורך הבחנה: `entity-type`
מודל שפה גדול (LLM) משתמש בשם תכונה מהסכימה: `"serves"`, `"preparation_time"`
הקוד מחפש את ה-URI של התכונה ממאפייני סוג הנתונים של האונטולוגיה
**האובייקט הוא מילולי** (`is_uri=False`), ולא הפניה ל-URI
הערכים נשארים כטקסט רגיל, אין צורך בנרמול

**ההבדל מיחסים:**
יחסים: גם הנושא וגם האובייקט הם ישויות (URIs)
תכונות: הנושא הוא ישות (URI), האובייקט הוא ערך מילולי (מחרוזת/מספר)

### דוגמה מלאה: ישויות + יחסים + תכונות

**טקסט קלט:**
```
Cornish pasty is a savory pastry filled with beef and potatoes.
This recipe serves 4 people.
```

**מה מודל שפה גדול מחזיר:**
```json
{
  "entities": [
    {
      "entity": "Cornish pasty",
      "type": "Recipe"
    },
    {
      "entity": "beef",
      "type": "Food"
    },
    {
      "entity": "potatoes",
      "type": "Food"
    }
  ],
  "relationships": [
    {
      "subject": "Cornish pasty",
      "subject-type": "Recipe",
      "relation": "has_ingredient",
      "object": "beef",
      "object-type": "Food"
    },
    {
      "subject": "Cornish pasty",
      "subject-type": "Recipe",
      "relation": "has_ingredient",
      "object": "potatoes",
      "object-type": "Food"
    }
  ],
  "attributes": [
    {
      "entity": "Cornish pasty",
      "entity-type": "Recipe",
      "attribute": "serves",
      "value": "4 people"
    }
  ]
}
```

**תוצאה:** נוצרו 11 משולשים של RDF:
3 משולשים מסוג ישות (rdf:type)
3 משולשים של תווית ישות (rdfs:label) - אוטומטי
2 משולשים של קשר (has_ingredient)
משולש אחד של תכונה (serves)

הכל נוצר מחילוץ פשוט משפה טבעית על ידי מודל השפה הגדול!

## הפניות

יישום נוכחי: `trustgraph-flow/trustgraph/extract/kg/ontology/extract.py`
תבנית הנחיה: `ontology-prompt.md`
מקרים בדיקה: `tests/unit/test_extract/test_ontology/`
אונטולוגיה לדוגמה: `e2e/test-data/food.ontology`
