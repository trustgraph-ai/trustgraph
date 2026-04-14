---
layout: default
title: "إنشاء الوثائق تلقائيًا"
parent: "Arabic (Beta)"
---

**تعليمات مهمة:**

- الحفاظ على جميع تنسيقات Markdown، والعناوين، والروابط، وعلامات HTML.
- لا تقم بترجمة الكود الموجود داخل علامات backticks أو كتل الكود.
- قم بإخراج النص المترجم فقط، بدون مقدمات أو تفسيرات.

النص المراد ترجمته:

# إنشاء الوثائق تلقائيًا

> **Beta Translation:** This document was translated via Machine Learning and as such may not be 100% accurate. All non-English languages are currently classified as Beta.

## وثائق واجهة برمجة تطبيقات REST و WebSocket

- `specs/build-docs.sh` - يقوم بإنشاء وثائق REST و WebSocket من مواصفات OpenAPI و AsyncAPI.

## وثائق واجهة برمجة تطبيقات Python

يتم إنشاء وثائق واجهة برمجة تطبيقات Python من سلاسل التوثيق باستخدام نص برمجي Python مخصص يقوم بتحليل حزمة `trustgraph.api`.

### المتطلبات الأساسية

يجب أن تكون حزمة trustgraph قابلة للاستيراد. إذا كنت تعمل في بيئة تطوير:

```bash
cd trustgraph-base
pip install -e .
```

### إنشاء الوثائق

من دليل الوثائق:

```bash
cd docs
python3 generate-api-docs.py > python-api.md
```

يولد هذا ملف Markdown واحد يحتوي على وثائق واجهة برمجة تطبيقات كاملة، ويظهر:
- دليل التثبيت والإرشادات السريعة
- عبارات الاستيراد لكل فئة/نوع
- سلاسل التوثيق الكاملة مع أمثلة
- جدول محتويات مُنظمة حسب الفئة

### أسلوب الوثائق

تتبع جميع سلاسل التوثيق تنسيق Google:
- ملخص موجز في سطر واحد
- وصف تفصيلي
- قسم Args مع أوصاف المعلمات
- قسم Returns
- قسم Raises (عندما يكون ذلك مناسبًا)
- كتل كود مع تمييز نحوي مناسب

تعرض الوثائق التي تم إنشاؤها واجهة برمجة التطبيقات العامة تمامًا كما يستوردها المستخدمون من `trustgraph.api`، دون الكشف عن هيكل الوحدة الداخلية.
