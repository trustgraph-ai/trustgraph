---
layout: default
title: "مجموعة أدوات TrustGraph"
parent: "Arabic (Beta)"
---

# مجموعة أدوات TrustGraph

> **Beta Translation:** This document was translated via Machine Learning and as such may not be 100% accurate. All non-English languages are currently classified as Beta.
## المواصفات الفنية v1.0

### ملخص تنفيذي

تحدد هذه المواصفات نظام تجميع الأدوات لوكلاء TrustGraph، مما يسمح بالتحكم الدقيق في الأدوات المتاحة لطلبات معينة. يقدم النظام تصفية الأدوات المستندة إلى المجموعات من خلال التكوين وتحديد مستوى الطلب، مما يتيح حدودًا أمنية أفضل وإدارة الموارد وتقسيمًا وظيفيًا لقدرات الوكيل.

### 1. نظرة عامة

#### 1.1 بيان المشكلة

حاليًا، يتمتع وكلاء TrustGraph بإمكانية الوصول إلى جميع الأدوات المكونة بغض النظر عن سياق الطلب أو متطلبات الأمان. وهذا يخلق عدة تحديات:

**مخاطر أمنية**: الأدوات الحساسة (مثل تعديل البيانات) متاحة حتى للاستعلامات للقراءة فقط.
**إهدار الموارد**: يتم تحميل الأدوات المعقدة حتى عندما لا تتطلب الاستعلامات البسيطة ذلك.
**ارتباك وظيفي**: قد تختار الوكلاء أدوات غير مناسبة عندما تكون هناك بدائل أبسط.
**العزل متعدد المستأجرين**: تحتاج مجموعات المستخدمين المختلفة إلى الوصول إلى مجموعات أدوات مختلفة.

#### 1.2 نظرة عامة على الحل

يقدم نظام تجميع الأدوات ما يلي:

1. **تصنيف المجموعات**: يتم وضع علامة على الأدوات باستخدام عضوية المجموعة أثناء التكوين.
2. **التصفية على مستوى الطلب**: يحدد AgentRequest مجموعات الأدوات المسموح بها.
3. **التنفيذ في وقت التشغيل**: لا تملك الوكلاء سوى الأدوات التي تتطابق مع المجموعات المطلوبة.
4. **تجميع مرن**: يمكن أن تنتمي الأدوات إلى مجموعات متعددة للسيناريوهات المعقدة.

### 2. تغييرات المخطط

#### 2.1 تحسين مخطط تكوين الأداة

يتم تحسين تكوين الأداة الحالي بإضافة حقل `group`:

**قبل:**
```json
{
  "name": "knowledge-query",
  "type": "knowledge-query", 
  "description": "Query the knowledge graph"
}
```

**بعد:**
```json
{
  "name": "knowledge-query",
  "type": "knowledge-query",
  "description": "Query the knowledge graph",
  "group": ["read-only", "knowledge", "basic"]
}
```

**تحديد حقل المجموعة:**
`group`: Array(String) - قائمة المجموعات التي تنتمي إليها هذه الأداة.
**اختياري**: الأدوات التي لا تحتوي على حقل المجموعة تنتمي إلى المجموعة الافتراضية.
**العضوية المتعددة**: يمكن للأدوات أن تنتمي إلى مجموعات متعددة.
**حساسية حالة الأحرف**: أسماء المجموعات هي مطابقات دقيقة للسلاسل النصية.

#### 2.1.2 تحسين انتقال حالة الأداة

يمكن للأدوات تحديد انتقالات الحالة وحالة التوفر بناءً على الحالة بشكل اختياري:

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

**تحديد حقل الحالة:**
`state`: String - **اختياري** - الحالة التي يتم الانتقال إليها بعد تنفيذ الأداة بنجاح
`available_in_states`: Array(String) - **اختياري** - الحالات التي تتوفر فيها هذه الأداة
**السلوك الافتراضي**: الأدوات التي لا تحتوي على `available_in_states` متاحة في جميع الحالات
**انتقال الحالة**: يحدث فقط بعد تنفيذ الأداة بنجاح

#### 2.2 تحسين مخطط AgentRequest

مخطط `AgentRequest` في `trustgraph-base/trustgraph/schema/services/agent.py` تم تحسينه:

**AgentRequest الحالي:**
`question`: String - استعلام المستخدم
`plan`: String - خطة التنفيذ (يمكن إزالتها)
`state`: String - حالة الوكيل
`history`: Array(AgentStep) - سجل التنفيذ

**AgentRequest المحسن:**
`question`: String - استعلام المستخدم
`state`: String - حالة تنفيذ الوكيل (تستخدم الآن بنشاط لتصفية الأدوات)
`history`: Array(AgentStep) - سجل التنفيذ
`group`: Array(String) - **جديد** - مجموعات الأدوات المسموح بها لهذا الطلب

**تغييرات المخطط:**
**تمت إزالة**: حقل `plan` لم يعد مطلوبًا ويمكن إزالته (كان مخصصًا في الأصل لتحديد الأدوات)
**تمت إضافة**: حقل `group` لتحديد مجموعة الأدوات
**تم التحسين**: يتحكم حقل `state` الآن في توفر الأدوات أثناء التنفيذ

**سلوكيات الحقول:**

**حقل المجموعة:**
**اختياري**: إذا لم يتم تحديده، فسيتم تعيينه افتراضيًا إلى ["default"]
**التقاطع**: تتوفر فقط الأدوات التي تتطابق مع مجموعة واحدة على الأقل من المجموعات المحددة
**مصفوفة فارغة**: لا تتوفر أي أدوات (يمكن للوكيل استخدام الاستدلال الداخلي فقط)
**رمز بدل (Wildcard)**: تمنح المجموعة الخاصة "*" إمكانية الوصول إلى جميع الأدوات

**حقل الحالة:**
**اختياري**: إذا لم يتم تحديده، فسيتم تعيينه افتراضيًا إلى "undefined"
**التصفية بناءً على الحالة**: الأدوات المتاحة فقط في الحالة الحالية هي المؤهلة
**الحالة الافتراضية**: تسمح حالة "undefined" بجميع الأدوات (مع مراعاة تصفية المجموعة)
**انتقالات الحالة**: يمكن للأدوات تغيير الحالة بعد التنفيذ الناجح

### 3. أمثلة على المجموعات المخصصة

يمكن للمؤسسات تحديد مجموعات خاصة بالمجال:

```json
{
  "financial-tools": ["stock-query", "portfolio-analysis"],
  "medical-tools": ["diagnosis-assist", "drug-interaction"],
  "legal-tools": ["contract-analysis", "case-search"]
}
```

### 4. تفاصيل التنفيذ

#### 4.1 تحميل الأدوات وتصفيتها

**مرحلة التهيئة:**
1. يتم تحميل جميع الأدوات من ملف التهيئة مع تحديد مجموعاتها.
2. يتم تعيين الأدوات التي لا تحتوي على مجموعات محددة إلى المجموعة "الافتراضية".
3. يتم التحقق من عضوية المجموعة وتخزينها في سجل الأدوات.

**مرحلة معالجة الطلبات:**
1. يصل طلب الوكيل (AgentRequest) مع تحديد المجموعة الاختياري.
2. يقوم الوكيل بتصفية الأدوات المتاحة بناءً على تقاطع المجموعات.
3. يتم تمرير الأدوات المتطابقة فقط إلى سياق تنفيذ الوكيل.
4. يعمل الوكيل مع مجموعة الأدوات المفلترة طوال دورة حياة الطلب.

#### 4.2 منطق تصفية الأدوات

**التصفية المجمعة للمجموعة والحالة:**

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

**منطق الانتقال بين الحالات:**

```
After successful tool execution:
  if tool.state is defined:
    next_request.state = tool.state
  else:
    next_request.state = current_request.state  // No change
```

#### 4.3 نقاط تكامل الوكيل

**الوكيل ReAct:**
يتم تصفية الأدوات في agent_manager.py أثناء إنشاء سجل الأدوات.
يتم تصفية قائمة الأدوات المتاحة بناءً على المجموعة والحالة قبل إنشاء الخطة.
تحديثات انتقالات الحالة تحدّث حقل AgentRequest.state بعد تنفيذ الأداة بنجاح.
تستخدم التكرار التالي الحالة المحدثة لتصفية الأدوات.

**الوكيل القائم على الثقة:**
يتم تصفية الأدوات في planner.py أثناء إنشاء الخطة.
التحقق من صحة ExecutionStep يضمن استخدام الأدوات المؤهلة فقط بناءً على المجموعة والحالة.
وحدة التحكم في التدفق تفرض توفر الأدوات في وقت التشغيل.
تتم إدارة انتقالات الحالة بواسطة وحدة التحكم في التدفق بين الخطوات.

### 5. أمثلة التكوين

#### 5.1 تكوين الأداة مع المجموعات والحالات

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

#### 5.2 أمثلة للطلبات مع سير العمل الخاص بالحالة.

**طلب البحث الأولي:**
```json
{
  "question": "What entities are connected to Company X?",
  "group": ["read-only", "knowledge"],
  "state": "undefined"
}
```
*الأدوات المتاحة: knowledge-query، text-completion*
*بعد استخدام knowledge-query: الحالة → "analysis"*

**مرحلة التحليل:**
```json
{
  "question": "Continue analysis based on previous results",
  "group": ["advanced", "compute", "write"],
  "state": "analysis"
}
```
*الأدوات المتاحة: تحليل معقد، تحديث الرسم البياني، إعادة تعيين سير العمل*
*بعد التحليل المعقد: الحالة → "النتائج"*

**مرحلة النتائج:**
```json
{
  "question": "What should I do with these results?",
  "group": ["admin"],
  "state": "results"
}
```
*الأدوات المتاحة: reset-workflow فقط*
*بعد reset-workflow: الحالة → "غير محددة"*

**مثال سير العمل - التدفق الكامل:**
1. **البداية (غير محددة):** استخدم knowledge-query للانتقال إلى الحالة "تحليل".
2. **حالة التحليل:** استخدم complex-analysis للانتقال إلى الحالة "النتائج".
3. **حالة النتائج:** استخدم reset-workflow للعودة إلى الحالة "غير محددة".
4. **العودة إلى البداية:** تتوفر جميع الأدوات الأولية مرة أخرى.

### 6. اعتبارات الأمان

#### 6.1 تكامل التحكم في الوصول

**التصفية على مستوى البوابة:**
يمكن للبوابة فرض قيود على المجموعات بناءً على أذونات المستخدم.
منع رفع الامتيازات من خلال التلاعب بالطلبات.
يتضمن سجل التدقيق المجموعات المطلوبة والمجموعات الممنوحة.

**مثال لمنطق البوابة:**
```
user_permissions = get_user_permissions(request.user_id)
allowed_groups = user_permissions.tool_groups
requested_groups = request.group

# Validate request doesn't exceed permissions
if not is_subset(requested_groups, allowed_groups):
    reject_request("Insufficient permissions for requested tool groups")
```

#### 6.2 التدقيق والمراقبة

**مسار تدقيق مُحسّن:**
تسجيل مجموعات الأدوات المطلوبة والحالة الأولية لكل طلب.
تتبع عمليات انتقال الحالة واستخدام الأدوات حسب عضوية المجموعة.
مراقبة محاولات الوصول غير المصرح بها إلى المجموعة والانتقالات غير الصالحة للحالة.
إرسال تنبيهات عند وجود أنماط استخدام غير عادية للمجموعة أو سير عمل حالة مشبوه.

### 7. استراتيجية الترحيل

#### 7.1 التوافق مع الإصدارات السابقة

**المرحلة الأولى: تغييرات إضافية**
إضافة حقل `group` اختياري إلى تكوينات الأدوات.
إضافة حقل `group` اختياري إلى مخطط AgentRequest.
السلوك الافتراضي: تنتمي جميع الأدوات الحالية إلى المجموعة "الافتراضية".
تستخدم الطلبات الحالية التي لا تحتوي على حقل المجموعة المجموعة "الافتراضية".

**الحفاظ على السلوك الحالي:**
تستمر الأدوات التي لا تحتوي على تكوين مجموعة في العمل (المجموعة الافتراضية).
الأدوات التي لا تحتوي على تكوين حالة متاحة في جميع الحالات.
يمكن للطلبات التي لا تحدد المجموعة الوصول إلى جميع الأدوات (المجموعة الافتراضية).
تستخدم الطلبات التي لا تحدد الحالة حالة "غير محددة" (جميع الأدوات متاحة).
لا توجد تغييرات تؤثر على عمليات النشر الحالية.

### 8. المراقبة وقابلية الملاحظة

#### 8.1 مقاييس جديدة

**استخدام مجموعة الأدوات:**
`agent_tool_group_requests_total` - عد الطلبات حسب المجموعة.
`agent_tool_group_availability` - مقياس للأدوات المتاحة لكل مجموعة.
`agent_filtered_tools_count` - رسم بياني لعدد الأدوات بعد تصفية المجموعة والحالة.

**مقاييس سير عمل الحالة:**
`agent_state_transitions_total` - عد عمليات انتقال الحالة لكل أداة.
`agent_workflow_duration_seconds` - رسم بياني للوقت المستغرق في كل حالة.
`agent_state_availability` - مقياس للأدوات المتاحة لكل حالة.

**مقاييس الأمان:**
`agent_group_access_denied_total` - عد الوصول غير المصرح به إلى المجموعة.
`agent_invalid_state_transition_total` - عد عمليات انتقال الحالة غير الصالحة.
`agent_privilege_escalation_attempts_total` - عد الطلبات المشبوهة.

#### 8.2 تحسينات التسجيل

**تسجيل الطلبات:**
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

### 9. استراتيجية الاختبار

#### 9.1 اختبارات الوحدة

**منطق تصفية الأدوات:**
حسابات تقاطع مجموعات الاختبار.
منطق التصفية المستند إلى الحالة.
التحقق من التعيين الافتراضي للمجموعة والحالة.
اختبار سلوك المجموعة باستخدام أحرف البدل.
التحقق من معالجة المجموعات الفارغة.
اختبار سيناريوهات التصفية المجمعة للمجموعة والحالة.

**التحقق من التكوين:**
اختبار تحميل الأدوات مع تكوينات مختلفة للمجموعة والحالة.
التحقق من صحة المخطط للمواصفات غير الصالحة للمجموعة والحالة.
اختبار التوافق مع الإصدارات السابقة مع التكوينات الحالية.
التحقق من تعريفات دورات الانتقال بين الحالات.

#### 9.2 اختبارات التكامل

**سلوك الوكيل:**
التحقق من أن الوكلاء يرون فقط الأدوات التي تم تصفيتها حسب المجموعة والحالة.
اختبار تنفيذ الطلبات مع مجموعات مختلفة.
اختبار الانتقالات بين الحالات أثناء تنفيذ الوكيل.
التحقق من معالجة الأخطاء عندما لا تتوفر أي أدوات.
اختبار تقدم سير العمل عبر حالات متعددة.

**اختبار الأمان:**
اختبار منع تصعيد الامتيازات.
التحقق من دقة سجل التدقيق.
اختبار تكامل البوابة مع أذونات المستخدم.

#### 9.3 سيناريوهات شاملة

**الاستخدام متعدد المستأجر مع سير عمل الحالة:**
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

**تطور حالة سير العمل:**
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

### 10. الاعتبارات المتعلقة بالأداء

#### 10.1 تأثير تحميل الأدوات

**تحميل التكوين:**
يتم تحميل بيانات التعريف الخاصة بالمجموعة والحالة مرة واحدة عند بدء التشغيل.
الحد الأدنى من الحمل على الذاكرة لكل أداة (حقول إضافية).
لا يوجد تأثير على وقت تهيئة الأداة.

**معالجة الطلبات:**
يتم تطبيق تصفية المجموعة + الحالة المجمعة مرة واحدة لكل طلب.
تعقيد O(n) حيث n = عدد الأدوات المكونة.
تضيف عمليات انتقال الحالة حملًا ضئيلًا (تعيين سلسلة).
تأثير ضئيل لعدد الأدوات النموذجي (< 100).

#### 10.2 استراتيجيات التحسين

**مجموعات الأدوات المحسوبة مسبقًا:**
تخزين مجموعات الأدوات حسب مجموعة + مجموعة حالة.
تجنب التصفية المتكررة لأنماط المجموعة / الحالة الشائعة.
مقايضة بين الذاكرة والحساب للتوليفات المستخدمة بشكل متكرر.

**التحميل الكسول:**
قم بتحميل تطبيقات الأدوات فقط عند الحاجة.
تقليل وقت بدء التشغيل لنشر الأدوات العديدة.
تسجيل الأدوات الديناميكي بناءً على متطلبات المجموعة.

### 11. التحسينات المستقبلية

#### 11.1 التعيين الديناميكي للمجموعة

**التجميع الواعي بالسياق:**
تعيين الأدوات إلى المجموعات بناءً على سياق الطلب.
توفر المجموعة بناءً على الوقت (ساعات العمل فقط).
قيود المجموعة بناءً على الحمل (الأدوات باهظة الثمن أثناء الاستخدام المنخفض).

#### 11.2 التسلسلات الهرمية للمجموعات

**هيكل المجموعة المتداخل:**
```json
{
  "knowledge": {
    "read": ["knowledge-query", "entity-search"],
    "write": ["graph-update", "entity-create"]
  }
}
```

#### 11.3 توصيات بالأدوات

**اقتراحات قائمة على المجموعات:**
اقتراح مجموعات الأدوات المثلى لأنواع الطلبات.
التعلم من أنماط الاستخدام لتحسين التوصيات.
توفير مجموعات احتياطية عندما تكون الأدوات المفضلة غير متاحة.

### 12. أسئلة مفتوحة

1. **التحقق من صحة المجموعة**: هل يجب أن تتسبب أسماء المجموعات غير الصالحة في الطلبات في حدوث أخطاء فادحة أم تحذيرات؟

2. **اكتشاف المجموعة**: هل يجب أن يوفر النظام واجهة برمجة تطبيقات (API) لسرد المجموعات المتاحة وأدواتها؟

3. **المجموعات الديناميكية**: هل يجب أن تكون المجموعات قابلة للتكوين في وقت التشغيل أم فقط عند بدء التشغيل؟

4. **وراثة المجموعة**: هل يجب أن ترث الأدوات مجموعات من فئاتها الأصلية أو تطبيقاتها؟

5. **مراقبة الأداء**: ما هي المقاييس الإضافية المطلوبة لتتبع استخدام الأدوات القائمة على المجموعات بشكل فعال؟

### 13. الخلاصة

يوفر نظام مجموعات الأدوات ما يلي:

**الأمان**: تحكم دقيق في الوصول إلى قدرات الوكيل.
**الأداء**: تقليل الحمل الزائد لاختيار الأدوات وتحميلها.
**المرونة**: تصنيف متعدد الأبعاد للأدوات.
**التوافق**: تكامل سلس مع بنيات الوكيل الحالية.

يمكّن هذا النظام عمليات نشر TrustGraph من إدارة الوصول إلى الأدوات بشكل أفضل، وتحسين الحدود الأمنية، وتحسين استخدام الموارد مع الحفاظ على التوافق الكامل مع التكوينات والطلبات الحالية.
