---
layout: default
title: "קבוצת כלים עבור TrustGraph"
parent: "Hebrew (Beta)"
---

# קבוצת כלים עבור TrustGraph

> **Beta Translation:** This document was translated via Machine Learning and as such may not be 100% accurate. All non-English languages are currently classified as Beta.
## מפרט טכני גרסה 1.0

### תקציר מנהלים

מפרט זה מגדיר מערכת לקבוצות כלים עבור סוכני TrustGraph, המאפשרת שליטה מדויקת על אילו כלים זמינים עבור בקשות ספציפיות. המערכת מציגה סינון כלים מבוסס קבוצות באמצעות תצורה ומפרט ברמת הבקשה, ומאפשרת גבולות אבטחה טובים יותר, ניהול משאבים וחלוקת פונקציונליות של יכולות הסוכנים.

### 1. סקירה כללית

#### 1.1 הצגת הבעיה

כיום, לסוכני TrustGraph יש גישה לכל הכלים המוגדרים, ללא קשר להקשר הבקשה או לדרישות האבטחה. זה יוצר מספר אתגרים:

**סיכון אבטחה**: כלים רגישים (לדוגמה, שינוי נתונים) זמינים גם עבור שאילתות לקריאה בלבד.
**בזבוז משאבים**: כלים מורכבים נטענים גם כאשר שאילתות פשוטות אינן דורשים אותם.
**בלבול פונקציונלי**: סוכנים עשויים לבחור כלים לא מתאימים כאשר קיימות חלופות פשוטות יותר.
**בידוד מרובה דיירים**: קבוצות משתמשים שונות צריכות גישה לקבוצות כלים שונות.

#### 1.2 סקירה כללית של הפתרון

מערכת קבוצות הכלים מציגה:

1. **סיווג קבוצות**: כלים מסומנים עם שייכות לקבוצות במהלך התצורה.
2. **סינון ברמת הבקשה**: בקשת סוכן מציינת אילו קבוצות כלים מותרות.
3. **אכיפה בזמן ריצה**: לסוכנים יש גישה רק לכלים התואמים לקבוצות המבוקשות.
4. **קיבוץ גמיש**: כלים יכולים להיות שייכים למספר קבוצות עבור תרחישים מורכבים.

### 2. שינויים בסכימה

#### 2.1 שיפור סכימת תצורת הכלים

תצורת הכלים הקיימת משופרת עם שדה `group`:

**לפני:**
```json
{
  "name": "knowledge-query",
  "type": "knowledge-query", 
  "description": "Query the knowledge graph"
}
```

**אחרי:**
```json
{
  "name": "knowledge-query",
  "type": "knowledge-query",
  "description": "Query the knowledge graph",
  "group": ["read-only", "knowledge", "basic"]
}
```

**מפרט שדה קבוצה:**
`group`: Array(String) - רשימה של קבוצות שאליהן הכלי הזה שייך
**אופציונלי**: כלים ללא שדה קבוצה שייכים לקבוצה "ברירת מחדל"
**חברות מרובות**: כלים יכולים להיות שייכים למספר קבוצות
**רגישות לאותיות**: שמות הקבוצות חייבים להיות התאמה מדויקת של מחרוזות

#### 2.1.2 שיפור מעבר מצבים של כלי

כלים יכולים לציין אופציונלית מעברי מצבים וזמינות מבוססת מצב:

```json
{
  "name": "knowledge-query",
  "type": "knowledge-query",
  "description": "Query the knowledge graph",
  "group": ["read-only", "knowledge", "basic"],
  "state": "analysis",
  "available_in_states": ["undefined", "research"]
}
```

**מפרט שדה מצב:**
`state`: מחרוזת - **אופציונלי** - המצב שאליו יש לעבור לאחר ביצוע מוצלח של הכלי
`available_in_states`: מערך(מחרוזת) - **אופציונלי** - מצבים שבהם הכלי זמין
**התנהגות ברירת מחדל**: כלים ללא `available_in_states` זמינים בכל המצבים
**מעבר מצב**: מתרחש רק לאחר ביצוע מוצלח של הכלי

#### 2.2 שיפור סכימת AgentRequest

הסכימה `AgentRequest` ב-`trustgraph-base/trustgraph/schema/services/agent.py` משופרת:

**AgentRequest נוכחי:**
`question`: מחרוזת - שאילתת משתמש
`plan`: מחרוזת - תוכנית ביצוע (ניתן להסיר)
`state`: מחרוזת - מצב סוכן
`history`: מערך(AgentStep) - היסטוריית ביצוע

**AgentRequest משופר:**
`question`: מחרוזת - שאילתת משתמש
`state`: מחרוזת - מצב ביצוע סוכן (כעת בשימוש פעיל לסינון כלים)
`history`: מערך(AgentStep) - היסטוריית ביצוע
`group`: מערך(מחרוזת) - **חדש** - קבוצות כלים מותרות עבור בקשה זו

**שינויים בסכימה:**
**הוסר**: השדה `plan` אינו נחוץ יותר וניתן להסירו (היה מיועד במקור למפרט כלים)
**נוסף**: השדה `group` למפרט קבוצות כלים
**שופר**: השדה `state` שולט כעת בזמינות הכלים במהלך הביצוע

**התנהגויות של שדות:**

**קבוצת שדות:**
**אופציונלי**: אם לא צוין, ברירת המחדל היא ["default"]
**חיתוך**: זמינים רק כלים התואמים לפחות לקבוצה אחת שצוינה
**מערך ריק**: אין כלים זמינים (הסוכן יכול להשתמש רק בנימוקים פנימיים)
**תו גלובלי**: קבוצה מיוחדת "*" מעניקה גישה לכל הכלים

**שדה מצב:**
**אופציונלי**: אם לא צוין, ברירת המחדל היא "לא מוגדר"
**סינון מבוסס מצב**: זכאים רק כלים הזמינים במצב הנוכחי
**מצב ברירת מחדל**: מצב "לא מוגדר" מאפשר לכל הכלים (בהתאם לסינון קבוצות)
**מעברי מצב**: כלים יכולים לשנות מצב לאחר ביצוע מוצלח

### 3. דוגמאות לקבוצות מותאמות אישית

ארגונים יכולים להגדיר קבוצות ספציפיות לתחום:

```json
{
  "financial-tools": ["stock-query", "portfolio-analysis"],
  "medical-tools": ["diagnosis-assist", "drug-interaction"],
  "legal-tools": ["contract-analysis", "case-search"]
}
```

### 4. פרטי יישום

#### 4.1 טעינת כלים וסינון

**שלב התצורה:**
1. כל הכלים נטענים מקובץ התצורה עם ההקצאות שלהם לקבוצות.
2. כלים שאין להם קבוצות מוגדרות מוקצים לקבוצה "ברירת מחדל".
3. חברות בקבוצות מאומתות ונשמרות במאגר הכלים.

**שלב עיבוד בקשות:**
1. בקשת סוכן מגיעה עם ציון קבוצה אופציונלי.
2. הסוכן מסנן את הכלים הזמינים בהתבסס על חיתוך קבוצות.
3. רק כלים תואמים מועברים להקשר הביצוע של הסוכן.
4. הסוכן פועל עם סט הכלים המסונן לאורך כל מחזור החיים של הבקשה.

#### 4.2 לוגיקת סינון כלים

**סינון משולב של קבוצות ומצבים:**

```
For each configured tool:
  tool_groups = tool.group || ["default"]
  tool_states = tool.available_in_states || ["*"]  // Available in all states
  
For each request:
  requested_groups = request.group || ["default"]
  current_state = request.state || "undefined"
  
Tool is available if:
  // Group filtering
  (intersection(tool_groups, requested_groups) is not empty OR "*" in requested_groups)
  AND
  // State filtering  
  (current_state in tool_states OR "*" in tool_states)
```

**לוגיקת מעבר מצבים:**

```
After successful tool execution:
  if tool.state is defined:
    next_request.state = tool.state
  else:
    next_request.state = current_request.state  // No change
```

#### 4.3 נקודות אינטגרציה של סוכן

**סוכן ReAct:**
סינון כלים מתבצע ב-agent_manager.py במהלך יצירת רישום הכלים
רשימת הכלים הזמינים מסוננת לפי קבוצה ומצב לפני יצירת תוכנית
מעברי מצבים מעדכנים את השדה AgentRequest.state לאחר ביצוע מוצלח של כלי
האיטרציה הבאה משתמשת במצב המעודכן לסינון כלים

**סוכן מבוסס ביטחון:**
סינון כלים מתבצע ב-planner.py במהלך יצירת תוכנית
אימות ExecutionStep מבטיח שרק כלים מתאימים לקבוצה ולמצב משמשים
בקר הזרימה (Flow controller) מאכף את זמינות הכלים בזמן ריצה
מעברי מצבים מנוהלים על ידי בקר הזרימה בין שלבים

### 5. דוגמאות תצורה

#### 5.1 תצורת כלים עם קבוצות ומצבים

```yaml
tool:
  knowledge-query:
    type: knowledge-query
    name: "Knowledge Graph Query"
    description: "Query the knowledge graph for entities and relationships"
    group: ["read-only", "knowledge", "basic"]
    state: "analysis"
    available_in_states: ["undefined", "research"]
    
  graph-update:
    type: graph-update
    name: "Graph Update"
    description: "Add or modify entities in the knowledge graph"
    group: ["write", "knowledge", "admin"]
    available_in_states: ["analysis", "modification"]
    
  text-completion:
    type: text-completion
    name: "Text Completion"
    description: "Generate text using language models"
    group: ["read-only", "text", "basic"]
    state: "undefined"
    # No available_in_states = available in all states
    
  complex-analysis:
    type: mcp-tool
    name: "Complex Analysis Tool"
    description: "Perform complex data analysis"
    group: ["advanced", "compute", "expensive"]
    state: "results"
    available_in_states: ["analysis"]
    mcp_tool_id: "analysis-server"
    
  reset-workflow:
    type: mcp-tool
    name: "Reset Workflow"
    description: "Reset to initial state"
    group: ["admin"]
    state: "undefined"
    available_in_states: ["analysis", "results"]
```

#### 5.2 דוגמאות לבקשות עם תהליכי עבודה מוגדרים מראש

**בקשה ראשונית למחקר:**
```json
{
  "question": "What entities are connected to Company X?",
  "group": ["read-only", "knowledge"],
  "state": "undefined"
}
```
*כלים זמינים: שאילתת ידע, השלמת טקסט*
*לאחר שאילתת ידע: מצב → "ניתוח"*

**שלב הניתוח:**
```json
{
  "question": "Continue analysis based on previous results",
  "group": ["advanced", "compute", "write"],
  "state": "analysis"
}
```
*כלים זמינים: complex-analysis, graph-update, reset-workflow*
*לאחר complex-analysis: מצב → "תוצאות"*

**שלב התוצאות:**
```json
{
  "question": "What should I do with these results?",
  "group": ["admin"],
  "state": "results"
}
```
*כלים זמינים: reset-workflow בלבד*
*לאחר הפעלת reset-workflow: מצב → "לא מוגדר"*

**דוגמה לזרימת עבודה - זרימה מלאה:**
1. **התחלה (לא מוגדר):** השתמש ב-knowledge-query → מעבר למצב "ניתוח"
2. **מצב ניתוח:** השתמש ב-complex-analysis → מעבר למצב "תוצאות"
3. **מצב תוצאות:** השתמש ב-reset-workflow → חזרה למצב "לא מוגדר"
4. **חזרה להתחלה:** כל הכלים הזמינים זמינים שוב

### 6. שיקולי אבטחה

#### 6.1 שילוב בקרת גישה

**סינון ברמת השער (Gateway):**
השער יכול לאכוף הגבלות קבוצתיות בהתבסס על הרשאות משתמש
מניעת העלאת הרשאות באמצעות מניפולציה של בקשות
רישום ביקורת כולל קבוצות כלים מבוקשות ומוענקות

**לוגיקה לדוגמה של השער:**
```
user_permissions = get_user_permissions(request.user_id)
allowed_groups = user_permissions.tool_groups
requested_groups = request.group

# Validate request doesn't exceed permissions
if not is_subset(requested_groups, allowed_groups):
    reject_request("Insufficient permissions for requested tool groups")
```

#### 6.2 ביקורת וניטור

**רשומות ביקורת משופרות:**
רישום קבוצות כלים מבוקשות ומצב התחלתי עבור כל בקשה
מעקב אחר מעברי מצבים ושימוש בכלים לפי חברות בקבוצה
ניטור ניסיונות גישה לא מורשים לקבוצות ושינויי מצב לא חוקיים
התראה על דפוסי שימוש חריגים בקבוצות או זרימות עבודה חשודות במצב

### 7. אסטרטגיית מעבר

#### 7.1 תאימות לאחור

**שלב 1: שינויים מצטברים**
הוספת שדה אופציונלי `group` לתצורות כלים
הוספת שדה אופציונלי `group` לתבנית AgentRequest
התנהגות ברירת מחדל: כל הכלים הקיימים שייכים לקבוצה "ברירת מחדל"
בקשות קיימות ללא שדה קבוצה משתמשות בקבוצה "ברירת מחדל"

**התנהגות קיימת נשמרת:**
כלים ללא תצורת קבוצה ממשיכים לעבוד (קבוצת ברירת מחדל)
כלים ללא תצורת מצב זמינים בכל המצבים
בקשות ללא ציון קבוצה ניגשות לכל הכלים (קבוצת ברירת מחדל)
בקשות ללא ציון מצב משתמשות במצב "לא מוגדר" (כל הכלים זמינים)
אין שינויים משמעותיים לפריסות קיימות

### 8. ניטור וניתוח

#### 8.1 מדדים חדשים

**שימוש בקבוצות כלים:**
`agent_tool_group_requests_total` - מונה של בקשות לפי קבוצה
`agent_tool_group_availability` - מדד של כלים זמינים לכל קבוצה
`agent_filtered_tools_count` - היסטוגרמה של מספר כלים לאחר סינון לפי קבוצה + מצב

**מדדי זרימת עבודה של מצבים:**
`agent_state_transitions_total` - מונה של מעברי מצבים לפי כלי
`agent_workflow_duration_seconds` - היסטוגרמה של זמן שהייה בכל מצב
`agent_state_availability` - מדד של כלים זמינים לכל מצב

**מדדי אבטחה:**
`agent_group_access_denied_total` - מונה של גישה לא מורשית לקבוצה
`agent_invalid_state_transition_total` - מונה של מעברי מצב לא חוקיים
`agent_privilege_escalation_attempts_total` - מונה של בקשות חשודות

#### 8.2 שיפורים ברישום

**רישום בקשות:**
```json
{
  "request_id": "req-123",
  "requested_groups": ["read-only", "knowledge"],
  "initial_state": "undefined",
  "state_transitions": [
    {"tool": "knowledge-query", "from": "undefined", "to": "analysis", "timestamp": "2024-01-01T10:00:01Z"}
  ],
  "available_tools": ["knowledge-query", "text-completion"],
  "filtered_by_group": ["graph-update", "admin-tool"],
  "filtered_by_state": [],
  "execution_time": "1.2s"
}
```

### 9. אסטרטגיית בדיקות

#### 9.1 בדיקות יחידה

**לוגיקת סינון כלים:**
חישובים של חיתוך קבוצות בדיקה
לוגיקת סינון מבוססת מצבים
אימות הקצאה ברירת מחדל של קבוצות ומצבים
בדיקת התנהגות של קבוצות עם תווים מיוחדים (wildcard)
אימות טיפול בקבוצות ריקות
בדיקת תרחישים משולבים של סינון קבוצות + מצבים

**אימות תצורה:**
בדיקת טעינת כלים עם תצורות שונות של קבוצות ומצבים
אימות של תקינות הסכימה עבור מפרטי קבוצות ומצבים לא חוקיים
בדיקת תאימות לאחור עם תצורות קיימות
אימות של הגדרות מעברים בין מצבים ומחזורים

#### 9.2 בדיקות אינטגרציה

**התנהגות של סוכן (Agent):**
אימות שהסוכן רואה רק כלים שעברו סינון לפי קבוצה + מצב
בדיקת ביצוע בקשות עם שילובים שונים של קבוצות
בדיקת מעברים בין מצבים במהלך ביצוע הסוכן
אימות של טיפול בשגיאות כאשר אין כלים זמינים
בדיקת התקדמות של זרימת עבודה דרך מצבים שונים

**בדיקות אבטחה:**
בדיקת מניעת העלאת הרשאות
אימות של דיוק רישום ביקורת (audit trail)
בדיקת שילוב של שער (gateway) עם הרשאות משתמש

#### 9.3 תרחישים מקצה לקצה

**שימוש מרובה דיירים (Multi-tenant) עם זרימות עבודה מבוססות מצבים:**
```
Scenario: Different users with different tool access and workflow states
Given: User A has "read-only" permissions, state "undefined"
  And: User B has "write" permissions, state "analysis"
When: Both request knowledge operations
Then: User A gets read-only tools available in "undefined" state
  And: User B gets write tools available in "analysis" state
  And: State transitions are tracked per user session
  And: All usage and transitions are properly audited
```

**התקדמות מצב העבודה:**
```
Scenario: Complete workflow execution
Given: Request with groups ["knowledge", "compute"] and state "undefined"
When: Agent executes knowledge-query tool (transitions to "analysis")
  And: Agent executes complex-analysis tool (transitions to "results")
  And: Agent executes reset-workflow tool (transitions to "undefined")
Then: Each step has correctly filtered available tools
  And: State transitions are logged with timestamps
  And: Final state allows initial workflow to repeat
```

### 10. שיקולי ביצועים

#### 10.1 השפעת טעינת כלים

**טעינת תצורה:**
מטא-נתונים של קבוצה ומצב נטענים פעם אחת בעת ההפעלה
תקורה מינימלית של זיכרון לכל כלי (שדות נוספים)
אין השפעה על זמן אתחול הכלי

**עיבוד בקשות:**
סינון משולב של קבוצה+מצב מתבצע פעם אחת לכל בקשה
מורכבות O(n) כאשר n = מספר הכלים המוגדרים
מעברים של מצבים מוסיפים תקורה מינימלית (הקצאת מחרוזות)
השפעה זניחה עבור מספר טיפוסי של כלים (< 100)

#### 10.2 אסטרטגיות אופטימיזציה

**סטים של כלים מחושבים מראש:**
שמירת סטים של כלים לפי שילוב של קבוצה+מצב
הימנעות מסינון חוזר עבור דפוסי קבוצה/מצב נפוצים
פשרה בין זיכרון לחישוב עבור שילובים בשימוש תכוף

**טעינה עצלה:**
טעינת יישומי כלים רק כאשר נדרש
הפחתת זמן אתחול עבור פריסות עם מספר רב של כלים
רישום דינמי של כלים בהתאם לדרישות הקבוצה

### 11. שיפורים עתידיים

#### 11.1 הקצאת קבוצות דינמית

**קיבוץ מודע להקשר:**
הקצאת כלים לקבוצות בהתבסס על הקשר הבקשה
זמינות קבוצה מבוססת זמן (שעות עסקים בלבד)
הגבלות קבוצה מבוססות עומס (כלים יקרים בזמן שימוש נמוך)

#### 11.2 היררכיות קבוצות

**מבנה קבוצות מקונן:**
```json
{
  "knowledge": {
    "read": ["knowledge-query", "entity-search"],
    "write": ["graph-update", "entity-create"]
  }
}
```

#### 11.3 המלצות כלים

**הצעות מבוססות קבוצות:**
הצעת קבוצות כלים אופטימליות עבור סוגי בקשות
למידה מדפוסי שימוש לשיפור ההמלצות
מתן קבוצות חלופיות כאשר הכלים המועדפים אינם זמינים

### 12. שאלות פתוחות

1. **אימות קבוצות**: האם שמות קבוצות לא חוקיים בבקשות צריכים לגרום לכישלונות קשים או אזהרות?

2. **גילוי קבוצות**: האם המערכת צריכה לספק API לרשימת קבוצות זמינות והכלים שלהן?

3. **קבוצות דינמיות**: האם הקבוצות צריכות להיות ניתנות להגדרה בזמן ריצה או רק בזמן ההתחלה?

4. **ירושה של קבוצות**: האם כלים צריכים לרשת קבוצות מהקטגוריות או המימושים הראשיים שלהם?

5. **ניטור ביצועים**: אילו מדדים נוספים נחוצים למעקב יעיל אחר שימוש בכלים מבוססי קבוצות?

### 13. סיכום

מערכת קבוצות הכלים מספקת:

**אבטחה**: בקרת גישה מפורטת על יכולות הסוכן
**ביצועים**: הפחתת עומס טעינה ובחירת כלים
**גמישות**: סיווג רב-ממדי של כלים
**תאימות**: שילוב חלק עם ארכיטקטורות סוכן קיימות

מערכת זו מאפשרת לפריסות TrustGraph לנהל טוב יותר את גישת הכלים, לשפר את גבולות האבטחה ולייעל את השימוש במשאבים תוך שמירה על תאימות מלאה לאחור עם תצורות ובקשות קיימות.
