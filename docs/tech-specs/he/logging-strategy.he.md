---
layout: default
title: "אסטרטגיית רישום (לוגינג) של TrustGraph"
parent: "Hebrew (Beta)"
---

# אסטרטגיית רישום (לוגינג) של TrustGraph

> **Beta Translation:** This document was translated via Machine Learning and as such may not be 100% accurate. All non-English languages are currently classified as Beta.

## סקירה כללית

TrustGraph משתמש במודול `logging` המובנה של Python עבור כל פעולות הרישום, עם תצורה מרכזית ושילוב אופציונלי של Loki לאיסוף יומנים. זה מספק גישה סטנדרטית וגמישה לרישום בכל רכיבי המערכת.

## תצורה ברירת מחדל

### רמת רישום
**רמה ברירת מחדל**: `INFO`
**ניתן להגדרה באמצעות**: ארגומנט שורת הפקודה `--log-level`
**אפשרויות**: `DEBUG`, `INFO`, `WARNING`, `ERROR`, `CRITICAL`

### יעדי פלט
1. **קונסולה (stdout)**: תמיד מופעלת - מבטיחה תאימות עם סביבות מבוססות קונטיינרים
2. **Loki**: איסוף יומנים מרכזי אופציונלי (מופעל כברירת מחדל, ניתן לביטול)

## מודול רישום מרכזי

כל תצורת הרישום מנוהלת על ידי המודול `trustgraph.base.logging`, המספק:
`add_logging_args(parser)` - מוסיף ארגומנטי שורת פקודה סטנדרטיים לרישום
`setup_logging(args)` - מגדיר רישום מארגומנטים מנותחים

מודול זה משמש את כל רכיבי הצד-שרת:
שירותים מבוססי AsyncProcessor
API Gateway
MCP Server

## הנחיות יישום

### 1. אתחול רשומות

כל מודול צריך ליצור את הרשומות שלו באמצעות המודול `__name__`:

```python
import logging

logger = logging.getLogger(__name__)
```

שם ה-logger משמש באופן אוטומטי כתווית ב-Loki לצורך סינון וחיפוש.

### 2. אתחול שירות

כל השירותים בצד השרת מקבלים באופן אוטומטי הגדרות רישום דרך המודול המרכזי:

```python
from trustgraph.base import add_logging_args, setup_logging
import argparse

def main():
    parser = argparse.ArgumentParser()

    # Add standard logging arguments (includes Loki configuration)
    add_logging_args(parser)

    # Add your service-specific arguments
    parser.add_argument('--port', type=int, default=8080)

    args = parser.parse_args()
    args = vars(args)

    # Setup logging early in startup
    setup_logging(args)

    # Rest of your service initialization
    logger = logging.getLogger(__name__)
    logger.info("Service starting...")
```

### 3. ארגומנטים של שורת הפקודה

כל השירותים תומכים בארגומנטים אלה של רישום:

**רמת רישום:**
```bash
--log-level {DEBUG,INFO,WARNING,ERROR,CRITICAL}
```

**תצורת לוקי:**
```bash
--loki-enabled              # Enable Loki (default)
--no-loki-enabled           # Disable Loki
--loki-url URL              # Loki push URL (default: http://loki:3100/loki/api/v1/push)
--loki-username USERNAME    # Optional authentication
--loki-password PASSWORD    # Optional authentication
```

**דוגמאות:**
```bash
# Default - INFO level, Loki enabled
./my-service

# Debug mode, console only
./my-service --log-level DEBUG --no-loki-enabled

# Custom Loki server with auth
./my-service --loki-url http://loki.prod:3100/loki/api/v1/push \
             --loki-username admin --loki-password secret
```

### 4. משתני סביבה

תצורת Loki תומכת באפשרויות ברירת מחדל עבור משתני סביבה:

```bash
export LOKI_URL=http://loki.prod:3100/loki/api/v1/push
export LOKI_USERNAME=admin
export LOKI_PASSWORD=secret
```

ארגומנטים משורת הפקודה גוברים על משתני סביבה.

### 5. שיטות עבודה מומלצות לרישום נתונים

#### שימוש ברמות רישום
**DEBUG**: מידע מפורט לצורך אבחון בעיות (ערכי משתנים, כניסה/יציאה מפונקציות)
**INFO**: הודעות מידע כלליות (השירות התחיל, תצורה נטענה, נקודות ציון בעיבוד)
**WARNING**: הודעות אזהרה למצבים שעלולים להיות מזיקים (תכונות מיושנות, שגיאות שניתן להתאושש מהן)
**ERROR**: הודעות שגיאה לבעיות חמורות (פעולות שנכשלו, חריגות)
**CRITICAL**: הודעות קריטיות לכשלים במערכת הדורשים התייחסות מיידית

#### פורמט ההודעה
```python
# Good - includes context
logger.info(f"Processing document: {doc_id}, size: {doc_size} bytes")
logger.error(f"Failed to connect to database: {error}", exc_info=True)

# Avoid - lacks context
logger.info("Processing document")
logger.error("Connection failed")
```

#### שיקולי ביצועים
```python
# Use lazy formatting for expensive operations
logger.debug("Expensive operation result: %s", expensive_function())

# Check log level for very expensive debug operations
if logger.isEnabledFor(logging.DEBUG):
    debug_data = compute_expensive_debug_info()
    logger.debug(f"Debug data: {debug_data}")
```

### 6. רישום מובנה עם לוקי

עבור נתונים מורכבים, השתמש ברישום מובנה עם תגיות נוספות עבור לוקי:

```python
logger.info("Request processed", extra={
    'tags': {
        'request_id': request_id,
        'user_id': user_id,
        'status': 'success'
    }
})
```

תגיות אלו הופכות לתויות הניתנות לחיפוש ב-Loki, בנוסף לתויות אוטומטיות:
`severity` - רמת לוג (DEBUG, INFO, WARNING, ERROR, CRITICAL)
`logger` - שם מודול (מתוך `__name__`)

### 7. רישום חריגות

תמיד כללו עקבות מחסנית עבור חריגות:

```python
try:
    process_data()
except Exception as e:
    logger.error(f"Failed to process data: {e}", exc_info=True)
    raise
```

### 8. שיקולים בנושא רישום אסינכרוני

מערכת הרישום משתמשת במטפלים (handlers) בתור לא חוסמים עבור Loki:
פלט לקונסולה הוא סינכרוני (מהיר)
פלט ל-Loki מוצג בתור עם מאגר של 500 הודעות
ניתוב רקע מטפל בהעברת נתונים ל-Loki
אין חסימה של קוד האפליקציה הראשי

```python
import asyncio
import logging

async def async_operation():
    logger = logging.getLogger(__name__)
    # Logging is thread-safe and won't block async operations
    logger.info(f"Starting async operation in task: {asyncio.current_task().get_name()}")
```

## אינטגרציה עם לוקי

### ארכיטקטורה

מערכת הרישום משתמשת בפונקציות המובנות של Python, `QueueHandler` ו-`QueueListener`, עבור אינטגרציה לא חוסמת עם לוקי:

1. **QueueHandler**: הודעות רישום מוכנסות לתור של 500 הודעות (לא חוסם).
2. **Background Thread**: QueueListener שולח הודעות רישום ללוקי באופן אסינכרוני.
3. **Graceful Degradation**: אם לוקי אינו זמין, רישום לקונסולה ממשיך.

### תגיות אוטומטיות

כל הודעת רישום שנשלחת ללוקי כוללת:
`processor`: זהות המעבד (לדוגמה, `config-svc`, `text-completion`, `embeddings`).
`severity`: רמת הרישום (DEBUG, INFO, וכו').
`logger`: שם המודול (לדוגמה, `trustgraph.gateway.service`, `trustgraph.agent.react.service`).

### תגיות מותאמות אישית

הוספת תגיות מותאמות אישית באמצעות הפרמטר `extra`:

```python
logger.info("User action", extra={
    'tags': {
        'user_id': user_id,
        'action': 'document_upload',
        'collection': collection_name
    }
})
```

### שאילתת יומנים ב-Loki

```logql
# All logs from a specific processor (recommended - matches Prometheus metrics)
{processor="config-svc"}
{processor="text-completion"}
{processor="embeddings"}

# Error logs from a specific processor
{processor="config-svc", severity="ERROR"}

# Error logs from all processors
{severity="ERROR"}

# Logs from a specific processor with text filter
{processor="text-completion"} |= "Processing"

# All logs from API gateway
{processor="api-gateway"}

# Logs from processors matching pattern
{processor=~".*-completion"}

# Logs with custom tags
{processor="api-gateway"} | json | user_id="12345"
```

### ניוון מבוקר (Graceful Degradation)

אם Loki אינו זמין או `python-logging-loki` אינו מותקן:
הודעת אזהרה מוצגת לקונסולה
רישום לקונסולה ממשיך כרגיל
היישום ממשיך לפעול
אין לוגיקה של ניסיון חוזר לחיבור ל-Loki (כשל מהיר, ניוון מבוקר)

## בדיקות (Testing)

במהלך הבדיקות, שקלו להשתמש בתצורת רישום שונה:

```python
# In test setup
import logging

# Reduce noise during tests
logging.getLogger().setLevel(logging.WARNING)

# Or disable Loki for tests
setup_logging({'log_level': 'WARNING', 'loki_enabled': False})
```

## אינטגרציה של ניטור

### פורמט סטנדרטי
כל הרישומים משתמשים בפורמט עקבי:
```
2025-01-09 10:30:45,123 - trustgraph.gateway.service - INFO - Request processed
```

מרכיבי פורמט:
חותמת זמן (פורמט ISO עם מילישניות)
שם הלוגר (נתיב מודול)
רמת לוג
הודעה

### שאילתות לוקי לניטור

שאילתות ניטור נפוצות:

```logql
# Error rate by processor
rate({severity="ERROR"}[5m]) by (processor)

# Top error-producing processors
topk(5, count_over_time({severity="ERROR"}[1h]) by (processor))

# Recent errors with processor name
{severity="ERROR"} | line_format "{{.processor}}: {{.message}}"

# All agent processors
{processor=~".*agent.*"} |= "exception"

# Specific processor error count
count_over_time({processor="config-svc", severity="ERROR"}[1h])
```

## שיקולי אבטחה

**לעולם אין לרשום מידע רגיש** (סיסמאות, מפתחות API, נתונים אישיים, טוקנים)
**לנקות קלט משתמש** לפני רישום
**להשתמש במחזירי מקום** עבור שדות רגישים: `user_id=****1234`
**אימות לוקי:** השתמשו ב-`--loki-username` ו-`--loki-password` עבור פריסות מאובטחות
**העברה מאובטחת:** השתמשו ב-HTTPS עבור כתובת ה-URL של לוקי בסביבת ייצור: `https://loki.prod:3100/loki/api/v1/push`

## תלויות

מודול הרישום המרכזי דורש:
`python-logging-loki` - עבור אינטגרציה עם לוקי (אופציונלי, ירידה הדרגתית אם חסר)

כלול כבר ב-`trustgraph-base/pyproject.toml` ו-`requirements.txt`.

## נתיב מעבר

עבור קוד קיים:

1. **שירותים שכבר משתמשים ב-AsyncProcessor:** אין צורך בשינויים, תמיכה בלוקי היא אוטומטית
2. **שירותים שאינם משתמשים ב-AsyncProcessor** (api-gateway, mcp-server): כבר עודכנו
3. **כלי שורת פקודה:** מחוץ לתחום - המשיכו להשתמש ב-print() או ברישום פשוט

### מ-print() לרישום:
```python
# Before
print(f"Processing document {doc_id}")

# After
logger = logging.getLogger(__name__)
logger.info(f"Processing document {doc_id}")
```

## סיכום הגדרות

| ארגומנט | ברירת מחדל | משתנה סביבה | תיאור |
|----------|---------|---------------------|-------------|
| `--log-level` | `INFO` | - | רמת רישום עבור קונסולה ו-Loki |
| `--loki-enabled` | `True` | - | הפעלת רישום Loki |
| `--loki-url` | `http://loki:3100/loki/api/v1/push` | `LOKI_URL` | נקודת קצה (endpoint) של Loki לשליחה |
| `--loki-username` | `None` | `LOKI_USERNAME` | שם משתמש לאימות ב-Loki |
| `--loki-password` | `None` | `LOKI_PASSWORD` | סיסמה לאימות ב-Loki |
