# מפרט טכני: איחוד תצורת Cassandra

**סטטוס:** טיוטה
**כותב:** עוזר
**תאריך:** 2024-09-03

## סקירה כללית

מפרט זה עוסק בדפוסי שמות ותצורות לא עקביים עבור פרמטרי חיבור ל-Cassandra ברחבי בסיס הקוד של TrustGraph. כיום, קיימים שני סכימות שמות פרמטרים שונות (`cassandra_*` לעומת `graph_*`), מה שמוביל לבלבול ולמורכבות תחזוקה.

## הצגת הבעיה

בסיס הקוד משתמש כיום בשתי קבוצות נפרדות של פרמטרי תצורה של Cassandra:

1. **מודולים של Knowledge/Config/Library** משתמשים:
   `cassandra_host` (רשימת מארחים)
   `cassandra_user`
   `cassandra_password`

2. **מודולים של Graph/Storage** משתמשים:
   `graph_host` (מאריך יחיד, לעיתים מומר לרשימה)
   `graph_username`
   `graph_password`

3. **חשיפה לא עקבית דרך שורת הפקודה**:
   חלק מהמעבדים (לדוגמה, `kg-store`) אינם חושפים הגדרות Cassandra כארגומנטים של שורת הפקודה
   מעבדים אחרים חושפים אותם עם שמות ופורמטים שונים
   טקסט העזרה אינו משקף ערכי משתני סביבה ברירת מחדל

שתי קבוצות הפרמטרים מתחברות לאותו кластер Cassandra, אך עם קונבנציות שמות שונות, מה שגורם ל:
בלבול בתצורת משתמשים
עומס תחזוקה מוגבר
תיעוד לא עקבי
פוטנציאל לטעות בתצורה
חוסר יכולת לשנות הגדרות דרך שורת הפקודה בחלק מהמעבדים

## פתרון מוצע

### 1. סטנדרטיזציה של שמות פרמטרים

כל המודולים ישתמשו בשמות פרמטרים עקביים של `cassandra_*`:
`cassandra_host` - רשימת מארחים (מאוחסנת פנימית כרשימה)
`cassandra_username` - שם משתמש לאימות
`cassandra_password` - סיסמה לאימות

### 2. ארגומנטים של שורת הפקודה

כל המעבדים חייבים לחשוף את תצורת Cassandra דרך ארגומנטים של שורת הפקודה:
`--cassandra-host` - רשימה מופרדת בפסיקים של מארחים
`--cassandra-username` - שם משתמש לאימות
`--cassandra-password` - סיסמה לאימות

### 3. חלופה של משתני סביבה

אם לא סופקו פרמטרים של שורת הפקודה, המערכת תבדוק משתני סביבה:
`CASSANDRA_HOST` - רשימה מופרדת בפסיקים של מארחים
`CASSANDRA_USERNAME` - שם משתמש לאימות
`CASSANDRA_PASSWORD` - סיסמה לאימות

### 4. ערכי ברירת מחדל

אם לא צוינו פרמטרים של שורת פקודה ולא משתני סביבה:
`cassandra_host` ברירת המחדל היא `["cassandra"]`
`cassandra_username` ברירת המחדל היא `None` (ללא אימות)
`cassandra_password` ברירת המחדל היא `None` (ללא אימות)

### 5. דרישות טקסט עזרה

הפלט של `--help` חייב:
להציג ערכי משתני סביבה כברירות מחדל כאשר הם מוגדרים
לעולם לא להציג ערכי סיסמה (להציג `****` או `<set>` במקום)
לציין בבירור את סדר הפתרון בטקסט העזרה

דוגמה לפלט עזרה:
```
--cassandra-host HOST
    Cassandra host list, comma-separated (default: prod-cluster-1,prod-cluster-2)
    [from CASSANDRA_HOST environment variable]

--cassandra-username USERNAME
    Cassandra username (default: cassandra_user)
    [from CASSANDRA_USERNAME environment variable]
    
--cassandra-password PASSWORD  
    Cassandra password (default: <set from environment>)
```

## פרטי יישום

### סדר פתרון פרמטרים

עבור כל פרמטר של Cassandra, סדר הפתרון יהיה:
1. ערך ארגומנט שורת הפקודה
2. משתנה סביבה (`CASSANDRA_*`)
3. ערך ברירת מחדל

### טיפול בפרמטרים של מארחים

הפרמטר `cassandra_host`:
שורת הפקודה מקבלת מחרוזת מופרדת בפסיקים: `--cassandra-host "host1,host2,host3"`
משתנה סביבה מקבל מחרוזת מופרדת בפסיקים: `CASSANDRA_HOST="host1,host2,host3"`
באופן פנימי תמיד מאוחסן כרשימה: `["host1", "host2", "host3"]`
מארח בודד: `"localhost"` → מומר ל-`["localhost"]`
כבר רשימה: `["host1", "host2"]` → משמש כפי שהוא

### לוגיקת אימות

אימות ישמש כאשר גם `cassandra_username` וגם `cassandra_password` מסופקים:
```python
if cassandra_username and cassandra_password:
    # Use SSL context and PlainTextAuthProvider
else:
    # Connect without authentication
```

## קבצים שיש לשנות

### מודולים המשתמשים בפרמטרים `graph_*` (שיש לשנות):
`trustgraph-flow/trustgraph/storage/triples/cassandra/write.py`
`trustgraph-flow/trustgraph/storage/objects/cassandra/write.py`
`trustgraph-flow/trustgraph/storage/rows/cassandra/write.py`
`trustgraph-flow/trustgraph/query/triples/cassandra/service.py`

### מודולים המשתמשים בפרמטרים `cassandra_*` (שיש לעדכן עם אפשרות חלופה):
`trustgraph-flow/trustgraph/tables/config.py`
`trustgraph-flow/trustgraph/tables/knowledge.py`
`trustgraph-flow/trustgraph/tables/library.py`
`trustgraph-flow/trustgraph/storage/knowledge/store.py`
`trustgraph-flow/trustgraph/cores/knowledge.py`
`trustgraph-flow/trustgraph/librarian/librarian.py`
`trustgraph-flow/trustgraph/librarian/service.py`
`trustgraph-flow/trustgraph/config/service/service.py`
`trustgraph-flow/trustgraph/cores/service.py`

### קבצי בדיקה שיש לעדכן:
`tests/unit/test_cores/test_knowledge_manager.py`
`tests/unit/test_storage/test_triples_cassandra_storage.py`
`tests/unit/test_query/test_triples_cassandra_query.py`
`tests/integration/test_objects_cassandra_integration.py`

## אסטרטגיית יישום

### שלב 1: יצירת כלי עזר להגדרות משותפות
צור פונקציות עזר לסטנדרטיזציה של הגדרות Cassandra בכל המעבדים:

```python
import os
import argparse

def get_cassandra_defaults():
    """Get default values from environment variables or fallback."""
    return {
        'host': os.getenv('CASSANDRA_HOST', 'cassandra'),
        'username': os.getenv('CASSANDRA_USERNAME'),
        'password': os.getenv('CASSANDRA_PASSWORD')
    }

def add_cassandra_args(parser: argparse.ArgumentParser):
    """
    Add standardized Cassandra arguments to an argument parser.
    Shows environment variable values in help text.
    """
    defaults = get_cassandra_defaults()
    
    # Format help text with env var indication
    host_help = f"Cassandra host list, comma-separated (default: {defaults['host']})"
    if 'CASSANDRA_HOST' in os.environ:
        host_help += " [from CASSANDRA_HOST]"
    
    username_help = f"Cassandra username"
    if defaults['username']:
        username_help += f" (default: {defaults['username']})"
        if 'CASSANDRA_USERNAME' in os.environ:
            username_help += " [from CASSANDRA_USERNAME]"
    
    password_help = "Cassandra password"
    if defaults['password']:
        password_help += " (default: <set>)"
        if 'CASSANDRA_PASSWORD' in os.environ:
            password_help += " [from CASSANDRA_PASSWORD]"
    
    parser.add_argument(
        '--cassandra-host',
        default=defaults['host'],
        help=host_help
    )
    
    parser.add_argument(
        '--cassandra-username',
        default=defaults['username'],
        help=username_help
    )
    
    parser.add_argument(
        '--cassandra-password',
        default=defaults['password'],
        help=password_help
    )

def resolve_cassandra_config(args) -> tuple[list[str], str|None, str|None]:
    """
    Convert argparse args to Cassandra configuration.
    
    Returns:
        tuple: (hosts_list, username, password)
    """
    # Convert host string to list
    if isinstance(args.cassandra_host, str):
        hosts = [h.strip() for h in args.cassandra_host.split(',')]
    else:
        hosts = args.cassandra_host
    
    return hosts, args.cassandra_username, args.cassandra_password
```

### שלב 2: עדכון מודולים באמצעות פרמטרים `graph_*`
1. שנה שמות הפרמטרים מ-`graph_*` ל-`cassandra_*`
2. החלף שיטות `add_args()` מותאמות אישית בשיטות `add_cassandra_args()` סטנדרטיות
3. השתמש בפונקציות העזר לתצורה נפוצות
4. עדכן מחרוזות תיעוד

דוגמה לטרנספורמציה:
```python
# OLD CODE
@staticmethod
def add_args(parser):
    parser.add_argument(
        '-g', '--graph-host',
        default="localhost",
        help=f'Graph host (default: localhost)'
    )
    parser.add_argument(
        '--graph-username',
        default=None,
        help=f'Cassandra username'
    )

# NEW CODE  
@staticmethod
def add_args(parser):
    FlowProcessor.add_args(parser)
    add_cassandra_args(parser)  # Use standard helper
```

### שלב 3: עדכון מודולים באמצעות פרמטרים `cassandra_*`
1. הוספת תמיכה בארגומנטים משורת הפקודה היכן שחסרים (לדוגמה, `kg-store`)
2. החלפת הגדרות ארגומנטים קיימות ב-`add_cassandra_args()`
3. שימוש ב-`resolve_cassandra_config()` עבור פתרון עקבי
4. הבטחת טיפול עקבי ברשימת השרתים

### שלב 4: עדכון בדיקות ותיעוד
1. עדכון כל קבצי הבדיקה לשימוש בשמות פרמטרים חדשים
2. עדכון תיעוד שורת הפקודה (CLI)
3. עדכון תיעוד API
4. הוספת תיעוד עבור משתני סביבה

## תאימות לאחור

על מנת לשמור על תאימות לאחור במהלך המעבר:

1. **אזהרות הפסקה** עבור פרמטרים `graph_*`
2. **כינוי פרמטרים** - קבלת שמות ישנים וחדשים בתחילה
3. **פריסה מדורגת** על פני מספר גרסאות
4. **עדכוני תיעוד** עם מדריך מעבר

דוגמה לקוד תאימות לאחור:
```python
def __init__(self, **params):
    # Handle deprecated graph_* parameters
    if 'graph_host' in params:
        warnings.warn("graph_host is deprecated, use cassandra_host", DeprecationWarning)
        params.setdefault('cassandra_host', params.pop('graph_host'))
    
    if 'graph_username' in params:
        warnings.warn("graph_username is deprecated, use cassandra_username", DeprecationWarning)
        params.setdefault('cassandra_username', params.pop('graph_username'))
    
    # ... continue with standard resolution
```

## אסטרטגיית בדיקות

1. **בדיקות יחידה** עבור לוגיקת פתרון תצורה
2. **בדיקות אינטגרציה** עם שילובים שונים של תצורות
3. **בדיקות משתני סביבה** 
4. **בדיקות תאימות לאחור** עם פרמטרים מיושנים
5. **בדיקות Docker Compose** עם משתני סביבה

## עדכוני תיעוד

1. עדכון כל התיעוד של פקודות שורת הפקודה
2. עדכון תיעוד API
3. יצירת מדריך מעבר
4. עדכון דוגמאות Docker Compose
5. עדכון תיעוד הפניה לתצורה

## סיכונים ודרכי התמודדות

| סיכון | השפעה | דרך התמודדות |
|------|--------|------------|
| שינויים שעלולים לפגוע במשתמשים | גבוהה | יישום תקופת תאימות לאחור |
| בלבול בתצורה במהלך המעבר | בינונית | תיעוד ברור ואזהרות על הפסקה |
| כשלים בבדיקות | בינונית | עדכוני בדיקות מקיפים |
| בעיות בפריסת Docker | גבוהה | עדכון כל דוגמאות Docker Compose |

## קריטריוני הצלחה

[ ] כל המודולים משתמשים בשמות פרמטרים אחידים `cassandra_*`
[ ] כל המעבדים חושפים הגדרות Cassandra באמצעות ארגומנטים של שורת הפקודה
[ ] טקסט העזרה של שורת הפקודה מציג ערכי ברירת מחדל של משתני סביבה
[ ] ערכי סיסמה לעולם אינם מוצגים בטקסט העזרה
[ ] מנגנון החלפה למשתני סביבה פועל כהלכה
[ ] `cassandra_host` מטופל באופן עקבי כרשימה באופן פנימי
[ ] תאימות לאחור נשמרת לפחות עבור 2 גרסאות
[ ] כל הבדיקות עוברות עם מערכת התצורה החדשה
[ ] התיעוד מעודכן במלואו
[ ] דוגמאות Docker Compose עובדות עם משתני סביבה

## ציר זמן

**שבוע 1:** יישום עזר תצורה משותף ועדכון מודולי `graph_*`
**שבוע 2:** הוספת תמיכה במשתני סביבה למודולי `cassandra_*` קיימים
**שבוע 3:** עדכון בדיקות ותיעוד
**שבוע 4:** בדיקות אינטגרציה ותיקון באגים

## שיקולים עתידיים

שקול להרחיב את התבנית הזו לתצורות מסדי נתונים אחרות (לדוגמה, Elasticsearch)
יישום אימות תצורה והודעות שגיאה טובות יותר
הוספת תמיכה בתצורת חיבור בריכת חיבורים של Cassandra
שקול להוסיף תמיכה בקבצי תצורה (.env files)