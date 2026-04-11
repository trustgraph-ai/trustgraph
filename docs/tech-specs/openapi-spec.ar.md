# مواصفات OpenAPI - المواصفات الفنية

## الهدف

إنشاء مواصفات OpenAPI 3.1 شاملة وقابلة للتطوير لواجهة TrustGraph REST API التي:
توثق جميع نقاط النهاية REST.
تستخدم `$ref` خارجية من أجل modularity وقابلية الصيانة.
تتوافق مباشرة مع كود مترجم الرسائل.
توفر مخططات دقيقة للطلبات والاستجابات.

## المصدر الموثوق

يتم تعريف واجهة برمجة التطبيقات بواسطة:
**مترجمو الرسائل**: `trustgraph-base/trustgraph/messaging/translators/*.py`
**مدير الموزع**: `trustgraph-flow/trustgraph/gateway/dispatch/manager.py`
**مدير نقطة النهاية**: `trustgraph-flow/trustgraph/gateway/endpoint/manager.py`

## هيكل الدليل

```
openapi/
├── openapi.yaml                          # Main entry point
├── paths/
│   ├── config.yaml                       # Global services
│   ├── flow.yaml
│   ├── librarian.yaml
│   ├── knowledge.yaml
│   ├── collection-management.yaml
│   ├── flow-services/                    # Flow-hosted services
│   │   ├── agent.yaml
│   │   ├── document-rag.yaml
│   │   ├── graph-rag.yaml
│   │   ├── text-completion.yaml
│   │   ├── prompt.yaml
│   │   ├── embeddings.yaml
│   │   ├── mcp-tool.yaml
│   │   ├── triples.yaml
│   │   ├── objects.yaml
│   │   ├── nlp-query.yaml
│   │   ├── structured-query.yaml
│   │   ├── structured-diag.yaml
│   │   ├── graph-embeddings.yaml
│   │   ├── document-embeddings.yaml
│   │   ├── text-load.yaml
│   │   └── document-load.yaml
│   ├── import-export/
│   │   ├── core-import.yaml
│   │   ├── core-export.yaml
│   │   └── flow-import-export.yaml      # WebSocket import/export
│   ├── websocket.yaml
│   └── metrics.yaml
├── components/
│   ├── schemas/
│   │   ├── config/
│   │   ├── flow/
│   │   ├── librarian/
│   │   ├── knowledge/
│   │   ├── collection/
│   │   ├── ai-services/
│   │   ├── common/
│   │   └── errors/
│   ├── parameters/
│   ├── responses/
│   └── examples/
└── security/
    └── bearerAuth.yaml
```

## ربط الخدمات

### الخدمات العامة (`/api/v1/{kind}`)
`config` - إدارة التكوين
`flow` - دورة حياة التدفق
`librarian` - مكتبة المستندات
`knowledge` - نوى المعرفة
`collection-management` - بيانات وصفية للمجموعة

### الخدمات المستضافة على التدفق (`/api/v1/flow/{flow}/service/{kind}`)

**الطلب/الاستجابة:**
`agent`, `text-completion`, `prompt`, `mcp-tool`
`graph-rag`, `document-rag`
`embeddings`, `graph-embeddings`, `document-embeddings`
`triples`, `objects`, `nlp-query`, `structured-query`, `structured-diag`

**إرسال واستقبال:**
`text-load`, `document-load`

### الاستيراد/التصدير
`/api/v1/import-core` (POST)
`/api/v1/export-core` (GET)
`/api/v1/flow/{flow}/import/{kind}` (WebSocket)
`/api/v1/flow/{flow}/export/{kind}` (WebSocket)

### أخرى
`/api/v1/socket` (WebSocket متعدد)
`/api/metrics` (Prometheus)

## النهج

### المرحلة الأولى: الإعداد
1. إنشاء هيكل الدليل
2. إنشاء ملف رئيسي `openapi.yaml` مع البيانات الوصفية والخوادم والأمان
3. إنشاء مكونات قابلة لإعادة الاستخدام (أخطاء، معلمات شائعة، مخططات أمان)

### المرحلة الثانية: المخططات الشائعة
إنشاء مخططات مشتركة تستخدم عبر الخدمات:
`RdfValue`, `Triple` - هياكل RDF/ثلاثية
`ErrorObject` - استجابة الخطأ
`DocumentMetadata`, `ProcessingMetadata` - هياكل البيانات الوصفية
المعلمات الشائعة: `FlowId`, `User`, `Collection`

### المرحلة الثالثة: الخدمات العامة
لكل خدمة عامة (تكوين، تدفق، أمين مكتبة، معرفة، إدارة المجموعة):
1. إنشاء ملف مسار في `paths/`
2. إنشاء مخطط الطلب في `components/schemas/{service}/`
3. إنشاء مخطط الاستجابة
4. إضافة أمثلة
5. الإشارة من الملف الرئيسي `openapi.yaml`

### المرحلة الرابعة: الخدمات المستضافة على التدفق
لكل خدمة مستضافة على التدفق:
1. إنشاء ملف مسار في `paths/flow-services/`
2. إنشاء مخططات الطلب/الاستجابة في `components/schemas/ai-services/`
3. إضافة وثائق علامة التدفق حيثما ينطبق
4. الإشارة من الملف الرئيسي `openapi.yaml`

### المرحلة الخامسة: الاستيراد/التصدير و WebSocket
1. توثيق نقاط النهاية الأساسية للاستيراد/التصدير
2. توثيق أنماط بروتوكول WebSocket
3. توثيق نقاط نهاية استيراد/تصدير WebSocket على مستوى التدفق

### المرحلة السادسة: التحقق من الصحة
1. التحقق من الصحة باستخدام أدوات التحقق من صحة OpenAPI
2. الاختبار باستخدام واجهة Swagger UI
3. التحقق من تغطية جميع المترجمين

## اصطلاح تسمية الحقول

جميع الحقول في JSON تستخدم **kebab-case**:
`flow-id`, `blueprint-name`, `doc-limit`, `entity-limit`، إلخ.

## إنشاء ملفات المخططات

لكل مترجم في `trustgraph-base/trustgraph/messaging/translators/`:

1. **قراءة طريقة مترجم `to_pulsar()`** - يحدد مخطط الطلب
2. **قراءة طريقة مترجم `from_pulsar()`** - يحدد مخطط الاستجابة
3. **استخراج أسماء وأنواع الحقول**
4. **إنشاء مخطط OpenAPI** مع:
   أسماء الحقول (kebab-case)
   الأنواع (سلسلة، عدد صحيح، منطقي، كائن، مصفوفة)
   الحقول المطلوبة
   القيم الافتراضية
   الأوصاف

### مثال لعملية التعيين

```python
# From retrieval.py DocumentRagRequestTranslator
def to_pulsar(self, data: Dict[str, Any]) -> DocumentRagQuery:
    return DocumentRagQuery(
        query=data["query"],                              # required string
        user=data.get("user", "trustgraph"),             # optional string, default "trustgraph"
        collection=data.get("collection", "default"),     # optional string, default "default"
        doc_limit=int(data.get("doc-limit", 20)),        # optional integer, default 20
        streaming=data.get("streaming", False)            # optional boolean, default false
    )
```

الترجمة:

```yaml
# components/schemas/ai-services/DocumentRagRequest.yaml
type: object
required:
  - query
properties:
  query:
    type: string
    description: Search query
  user:
    type: string
    default: trustgraph
  collection:
    type: string
    default: default
  doc-limit:
    type: integer
    default: 20
    description: Maximum number of documents to retrieve
  streaming:
    type: boolean
    default: false
    description: Enable streaming responses
```

## الاستجابات المتدفقة

الخدمات التي تدعم التدفق تُرجع استجابات متعددة مع العلامة `end_of_stream`:
`agent`، `text-completion`، `prompt`
`document-rag`، `graph-rag`

قم بتوثيق هذا النمط في مخطط استجابة كل خدمة.

## استجابات الأخطاء

يمكن لجميع الخدمات إرجاع:
```yaml
error:
  oneOf:
    - type: string
    - $ref: '#/components/schemas/ErrorObject'
```

حيث أن `ErrorObject` هو:
```yaml
type: object
properties:
  type:
    type: string
  message:
    type: string
```

## المراجع

المترجمون: `trustgraph-base/trustgraph/messaging/translators/`
تعيين الموزع: `trustgraph-flow/trustgraph/gateway/dispatch/manager.py`
توجيه نقطة النهاية: `trustgraph-flow/trustgraph/gateway/endpoint/manager.py`
ملخص الخدمة: `API_SERVICES_SUMMARY.md`
