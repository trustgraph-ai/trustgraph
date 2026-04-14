---
layout: default
title: "הסברתיות של סוכן: רישום מקורות"
parent: "Hebrew (Beta)"
---

# הסברתיות של סוכן: רישום מקורות

> **Beta Translation:** This document was translated via Machine Learning and as such may not be 100% accurate. All non-English languages are currently classified as Beta.

## סקירה כללית

הוספת רישום מקורות ללולאת הסוכן של React כך שניתן יהיה לעקוב אחר סשנים של סוכנים ולבצע ניפוי באגים באמצעות אותה תשתית הסברתיות כמו GraphRAG.

**החלטות עיצוב:**
כתיבה ל-`urn:graph:retrieval` (גרף הסברתיות גנרי)
שרשרת תלות ליניארית כרגע (ניתוח N → נגזר מ → ניתוח N-1)
כלים הם תיבות שחורות (רישום קלט/פלט בלבד)
תמיכה ב-DAG (גרף מכוון) נדחית למהלך עתידי

## סוגי ישויות

גם GraphRAG וגם Agent משתמשים ב-PROV-O כאונטולוגיה בסיסית עם תת-סוגים ספציפיים ל-TrustGraph:

### סוגי GraphRAG
| ישות | סוג PROV-O | סוגי TG | תיאור |
|--------|-------------|----------|-------------|
| שאלה | `prov:Activity` | `tg:Question`, `tg:GraphRagQuestion` | השאלה של המשתמש |
| חקירה | `prov:Entity` | `tg:Exploration` | צמתים שאוחזרו מגרף ידע |
| מיקוד | `prov:Entity` | `tg:Focus` | צמתים שנבחרו עם נימוק |
| סינתזה | `prov:Entity` | `tg:Synthesis` | תשובה סופית |

### סוגי סוכן
| ישות | סוג PROV-O | סוגי TG | תיאור |
|--------|-------------|----------|-------------|
| שאלה | `prov:Activity` | `tg:Question`, `tg:AgentQuestion` | השאלה של המשתמש |
| ניתוח | `prov:Entity` | `tg:Analysis` | כל מחזור חשיבה/פעולה/תצפית |
| מסקנה | `prov:Entity` | `tg:Conclusion` | תשובה סופית |

### סוגי RAG של מסמכים
| ישות | סוג PROV-O | סוגי TG | תיאור |
|--------|-------------|----------|-------------|
| שאלה | `prov:Activity` | `tg:Question`, `tg:DocRagQuestion` | השאלה של המשתמש |
| חקירה | `prov:Entity` | `tg:Exploration` | חלקים שאוחזרו מחנות מסמכים |
| סינתזה | `prov:Entity` | `tg:Synthesis` | תשובה סופית |

**הערה:** RAG של מסמכים משתמש בתת-קבוצה של סוגים של GraphRAG (אין שלב מיקוד מכיוון שאין שלב בחירת/נימוק צמתים).

### תת-סוגים של שאלה

כל ישויות השאלה חולקות את `tg:Question` כסוג בסיסי אך יש להן תת-סוג ספציפי כדי לזהות את מנגנון השליפה:

| תת-סוג | תבנית URI | מנגנון |
|---------|-------------|-----------|
| `tg:GraphRagQuestion` | `urn:trustgraph:question:{uuid}` | RAG של גרף ידע |
| `tg:DocRagQuestion` | `urn:trustgraph:docrag:{uuid}` | RAG של מסמכים/חלקים |
| `tg:AgentQuestion` | `urn:trustgraph:agent:{uuid}` | סוכן ReAct |

זה מאפשר שאילתא של כל השאלות באמצעות `tg:Question` תוך סינון לפי מנגנון ספציפי באמצעות תת-הסוג.

## מודל מקורות

```
Question (urn:trustgraph:agent:{uuid})
    │
    │  tg:query = "User's question"
    │  prov:startedAtTime = timestamp
    │  rdf:type = prov:Activity, tg:Question
    │
    ↓ prov:wasDerivedFrom
    │
Analysis1 (urn:trustgraph:agent:{uuid}/i1)
    │
    │  tg:thought = "I need to query the knowledge base..."
    │  tg:action = "knowledge-query"
    │  tg:arguments = {"question": "..."}
    │  tg:observation = "Result from tool..."
    │  rdf:type = prov:Entity, tg:Analysis
    │
    ↓ prov:wasDerivedFrom
    │
Analysis2 (urn:trustgraph:agent:{uuid}/i2)
    │  ...
    ↓ prov:wasDerivedFrom
    │
Conclusion (urn:trustgraph:agent:{uuid}/final)
    │
    │  tg:answer = "The final response..."
    │  rdf:type = prov:Entity, tg:Conclusion
```

### מודל מקור (Provenance) של מסמכים בשיטת RAG

```
Question (urn:trustgraph:docrag:{uuid})
    │
    │  tg:query = "User's question"
    │  prov:startedAtTime = timestamp
    │  rdf:type = prov:Activity, tg:Question
    │
    ↓ prov:wasGeneratedBy
    │
Exploration (urn:trustgraph:docrag:{uuid}/exploration)
    │
    │  tg:chunkCount = 5
    │  tg:selectedChunk = "chunk-id-1"
    │  tg:selectedChunk = "chunk-id-2"
    │  ...
    │  rdf:type = prov:Entity, tg:Exploration
    │
    ↓ prov:wasDerivedFrom
    │
Synthesis (urn:trustgraph:docrag:{uuid}/synthesis)
    │
    │  tg:content = "The synthesized answer..."
    │  rdf:type = prov:Entity, tg:Synthesis
```

## שינויים נדרשים

### 1. שינויים בסכימה

**קובץ:** `trustgraph-base/trustgraph/schema/services/agent.py`

הוסף את השדות `session_id` ו-`collection` ל-`AgentRequest`:
```python
@dataclass
class AgentRequest:
    question: str = ""
    state: str = ""
    group: list[str] | None = None
    history: list[AgentStep] = field(default_factory=list)
    user: str = ""
    collection: str = "default"  # NEW: Collection for provenance traces
    streaming: bool = False
    session_id: str = ""         # NEW: For provenance tracking across iterations
```

**קובץ:** `trustgraph-base/trustgraph/messaging/translators/agent.py`

עדכון המתרגם כדי לטפל ב-`session_id` וב-`collection` הן ב-`to_pulsar()` והן ב-`from_pulsar()`.

### 2. הוספת יצרן הסברות לשירות הסוכנים

**קובץ:** `trustgraph-flow/trustgraph/agent/react/service.py`

רישום יצרן "הסברות" (באותו דפוס כמו GraphRAG):
```python
from ... base import ProducerSpec
from ... schema import Triples

# In __init__:
self.register_specification(
    ProducerSpec(
        name = "explainability",
        schema = Triples,
    )
)
```

### 3. יצירת משולש מוצא

**קובץ:** `trustgraph-base/trustgraph/provenance/agent.py`

צור פונקציות עזר (בדומה ל-`question_triples`, `exploration_triples` וכו' של GraphRAG):
```python
def agent_session_triples(session_uri, query, timestamp):
    """Generate triples for agent Question."""
    return [
        Triple(s=session_uri, p=RDF_TYPE, o=PROV_ACTIVITY),
        Triple(s=session_uri, p=RDF_TYPE, o=TG_QUESTION),
        Triple(s=session_uri, p=TG_QUERY, o=query),
        Triple(s=session_uri, p=PROV_STARTED_AT_TIME, o=timestamp),
    ]

def agent_iteration_triples(iteration_uri, parent_uri, thought, action, arguments, observation):
    """Generate triples for one Analysis step."""
    return [
        Triple(s=iteration_uri, p=RDF_TYPE, o=PROV_ENTITY),
        Triple(s=iteration_uri, p=RDF_TYPE, o=TG_ANALYSIS),
        Triple(s=iteration_uri, p=TG_THOUGHT, o=thought),
        Triple(s=iteration_uri, p=TG_ACTION, o=action),
        Triple(s=iteration_uri, p=TG_ARGUMENTS, o=json.dumps(arguments)),
        Triple(s=iteration_uri, p=TG_OBSERVATION, o=observation),
        Triple(s=iteration_uri, p=PROV_WAS_DERIVED_FROM, o=parent_uri),
    ]

def agent_final_triples(final_uri, parent_uri, answer):
    """Generate triples for Conclusion."""
    return [
        Triple(s=final_uri, p=RDF_TYPE, o=PROV_ENTITY),
        Triple(s=final_uri, p=RDF_TYPE, o=TG_CONCLUSION),
        Triple(s=final_uri, p=TG_ANSWER, o=answer),
        Triple(s=final_uri, p=PROV_WAS_DERIVED_FROM, o=parent_uri),
    ]
```

### 4. הגדרות סוג

**קובץ:** `trustgraph-base/trustgraph/provenance/namespaces.py`

הוסף סוגי ישויות הסבר ופרדיקטים של סוכנים:
```python
# Explainability entity types (used by both GraphRAG and Agent)
TG_QUESTION = TG + "Question"
TG_EXPLORATION = TG + "Exploration"
TG_FOCUS = TG + "Focus"
TG_SYNTHESIS = TG + "Synthesis"
TG_ANALYSIS = TG + "Analysis"
TG_CONCLUSION = TG + "Conclusion"

# Agent predicates
TG_THOUGHT = TG + "thought"
TG_ACTION = TG + "action"
TG_ARGUMENTS = TG + "arguments"
TG_OBSERVATION = TG + "observation"
TG_ANSWER = TG + "answer"
```

## קבצים ששונו

| קובץ | שינוי |
|------|--------|
| `trustgraph-base/trustgraph/schema/services/agent.py` | הוספת session_id ו-collection ל-AgentRequest |
| `trustgraph-base/trustgraph/messaging/translators/agent.py` | עדכון מתרגם עבור שדות חדשים |
| `trustgraph-base/trustgraph/provenance/namespaces.py` | הוספת סוגי ישויות, טענות של סוכן וטענות של Document RAG |
| `trustgraph-base/trustgraph/provenance/triples.py` | הוספת סוגי TG לבונים של משולשים של GraphRAG, הוספת בונים של משולשים של Document RAG |
| `trustgraph-base/trustgraph/provenance/uris.py` | הוספת יוצרי URI של Document RAG |
| `trustgraph-base/trustgraph/provenance/__init__.py` | ייצוא סוגים, טענות ופונקציות חדשות של Document RAG |
| `trustgraph-base/trustgraph/schema/services/retrieval.py` | הוספת explain_id ו-explain_graph ל-DocumentRagResponse |
| `trustgraph-base/trustgraph/messaging/translators/retrieval.py` | עדכון DocumentRagResponseTranslator עבור שדות הסברתיות |
| `trustgraph-flow/trustgraph/agent/react/service.py` | הוספת מפיק הסברתיות + לוגיקת הקלטה |
| `trustgraph-flow/trustgraph/retrieval/document_rag/document_rag.py` | הוספת קריאה חוזרת של הסברתיות ופליטת משולשים של מקור |
| `trustgraph-flow/trustgraph/retrieval/document_rag/rag.py` | הוספת מפיק הסברתיות וחיבור הקריאה החוזרת |
| `trustgraph-cli/trustgraph/cli/show_explain_trace.py` | טיפול בסוגי מעקב של סוכן |
| `trustgraph-cli/trustgraph/cli/list_explain_traces.py` | הצגת סשנים של סוכן לצד GraphRAG |

## קבצים שנוצרו

| קובץ | מטרה |
|------|---------|
| `trustgraph-base/trustgraph/provenance/agent.py` | יוצרי משולשים ספציפיים לסוכן |

## עדכוני CLI

**זיהוי:** גם לשאלות GraphRAG וגם לשאלות סוכן יש סוג `tg:Question`. מובחנים על ידי:
1. תבנית URI: `urn:trustgraph:agent:` לעומת `urn:trustgraph:question:`
2. ישויות נגזרות: `tg:Analysis` (סוכן) לעומת `tg:Exploration` (GraphRAG)

**`list_explain_traces.py`:**
מציג את עמודת הסוג (סוכן לעומת GraphRAG)

**`show_explain_trace.py`:**
מזהה אוטומטית את סוג המעקב
הצגת סוכן מציגה: שאלה → שלב(ים) של ניתוח → מסקנה

## תאימות לאחור

`session_id` כברירת מחדל הוא `""` - בקשות ישנות עובדות, פשוט לא יהיו להן נתונים של מקור
`collection` כברירת מחדל הוא `"default"` - חזרה סבירה
ה-CLI מטפל בצורה חלקה בשני סוגי המעקב

## אימות

```bash
# Run an agent query
tg-invoke-agent -q "What is the capital of France?"

# List traces (should show agent sessions with Type column)
tg-list-explain-traces -U trustgraph -C default

# Show agent trace
tg-show-explain-trace "urn:trustgraph:agent:xxx"
```

## עבודה עתידית (לא בבקשה הזו)

תלותיות DAG (כאשר ניתוח N משתמש בתוצאות ממספר ניתוחים קודמים)
קישור מקורות מידע ספציפי לכלי (KnowledgeQuery → המעקב GraphRAG שלו)
פליטת מקורות מידע בסטרימינג (לשלוח תוך כדי פעולה, ולא במקשה בסוף)
