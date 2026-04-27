---
layout: default
title: "本体知识抽取 - 第二阶段重构"
parent: "Chinese (Beta)"
---

# 本体知识抽取 - 第二阶段重构

> **Beta Translation:** This document was translated via Machine Learning and as such may not be 100% accurate. All non-English languages are currently classified as Beta.

**状态**: 草稿
**作者**: 分析会议 2025-12-03
**相关**: `ontology.md`, `ontorag.md`

## 概述

本文档识别了当前基于本体的知识抽取系统中存在的缺陷，并提出了重构方案，以提高 LLM 的性能并减少信息损失。

## 当前实现

### 当前工作方式

1. **本体加载** (`ontology_loader.py`)
   加载本体 JSON 文件，其中包含键，例如 `"fo/Recipe"`, `"fo/Food"`, `"fo/produces"`
   类 ID 在键本身中包含命名空间前缀
   示例来自 `food.ontology`:
     ```json
     "classes": {
       "fo/Recipe": {
         "uri": "http://purl.org/ontology/fo/Recipe",
         "rdfs:comment": "A Recipe is a combination..."
       }
     }
     ```

2. **提示构建** (`extract.py:299-307`, `ontology-prompt.md`)
   模板接收 `classes`, `object_properties`, `datatype_properties` 字典
   模板循环：`{% for class_id, class_def in classes.items() %}`
   LLM 看到：`**fo/Recipe**: A Recipe is a combination...`
   示例输出格式如下：
     ```json
     {"subject": "recipe:cornish-pasty", "predicate": "rdf:type", "object": "Recipe"}
     {"subject": "recipe:cornish-pasty", "predicate": "has_ingredient", "object": "ingredient:flour"}
     ```

3. **响应解析** (`extract.py:382-428`)
   期望接收 JSON 数组: `[{"subject": "...", "predicate": "...", "object": "..."}]`
   验证是否符合本体子集
   通过 `expand_uri()` 扩展 URI (extract.py:473-521)

4. **URI 扩展** (`extract.py:473-521`)
   检查值是否在 `ontology_subset.classes` 字典中
   如果找到，从类定义中提取 URI
   如果未找到，则构建 URI: `f"https://trustgraph.ai/ontology/{ontology_id}#{value}"`

### 数据流示例

**本体 JSON → 加载器 → 提示:**
```
"fo/Recipe" → classes["fo/Recipe"] → LLM sees "**fo/Recipe**"
```

**LLM → 解析器 → 输出:**
```
"Recipe" → not in classes["fo/Recipe"] → constructs URI → LOSES original URI
"fo/Recipe" → found in classes → uses original URI → PRESERVES URI
```

## 发现的问题

### 1. **提示语中的示例不一致**

**问题**: 提示模板显示带有前缀的类ID (`fo/Recipe`)，但示例输出使用不带前缀的类名 (`Recipe`)。

**位置**: `ontology-prompt.md:5-52`

```markdown
## Ontology Classes:
- **fo/Recipe**: A Recipe is...

## Example Output:
{"subject": "recipe:cornish-pasty", "predicate": "rdf:type", "object": "Recipe"}
```

**影响：** LLM 接收到关于应该使用哪种格式的冲突信号。

### 2. **URI 扩展中的信息丢失**

**问题：** 当 LLM 返回不带前缀的类名，例如示例中的情况时，`expand_uri()` 无法在本体字典中找到它们，而是构造了备用 URI，从而丢失了原始的正确 URI。

**位置：** `extract.py:494-500`

```python
if value in ontology_subset.classes:  # Looks for "Recipe"
    class_def = ontology_subset.classes[value]  # But key is "fo/Recipe"
    if isinstance(class_def, dict) and 'uri' in class_def:
        return class_def['uri']  # Never reached!
return f"https://trustgraph.ai/ontology/{ontology_id}#{value}"  # Fallback
```

**影响 (Impact):**
原始 URI: `http://purl.org/ontology/fo/Recipe`
构建的 URI: `https://trustgraph.ai/ontology/food#Recipe`
语义信息丢失，破坏互操作性

### 3. **实体实例格式不明确 (Ambiguous Entity Instance Format)**

**问题 (Issue):** 没有关于实体实例 URI 格式的明确指导。

**提示中的示例 (Examples in prompt):**
`"recipe:cornish-pasty"` (类似于命名空间的 前缀)
`"ingredient:flour"` (不同的前缀)

**实际行为 (Actual behavior) (extract.py:517-520):**
```python
# Treat as entity instance - construct unique URI
normalized = value.replace(" ", "-").lower()
return f"https://trustgraph.ai/{ontology_id}/{normalized}"
```

**影响：** LLM 必须在没有任何本体知识的情况下猜测前缀约定。

### 4. **没有命名空间前缀的指导**

**问题：** 本体 JSON 包含命名空间定义（food.ontology 中的第 10-25 行）：
```json
"namespaces": {
  "fo": "http://purl.org/ontology/fo/",
  "rdf": "http://www.w3.org/1999/02/22-rdf-syntax-ns#",
  ...
}
```

但是这些内容永远不会传递给大型语言模型。大型语言模型不知道：
"fo" 的含义
应使用哪个前缀来表示实体
哪个命名空间适用于哪些元素

### 5. **未在提示中使用标签**

**问题：** 每一个类都有 `rdfs:label` 字段（例如，`{"value": "Recipe", "lang": "en-gb"}`），但提示模板没有使用它们。

**当前：** 只显示 `class_id` 和 `comment`
```jinja
- **{{class_id}}**{% if class_def.comment %}: {{class_def.comment}}{% endif %}
```

**可用但未使用的：**
```python
"rdfs:label": [{"value": "Recipe", "lang": "en-gb"}]
```

**影响：** 可以为技术 ID 旁边提供人类可读的名称。

## 提出的解决方案

### 方案 A：标准化为不带前缀的 ID

**方法：** 在向 LLM 显示之前，从类 ID 中移除前缀。

**变更：**
1. 修改 `build_extraction_variables()` 以转换键：
   ```python
   classes_for_prompt = {
       k.split('/')[-1]: v  # "fo/Recipe" → "Recipe"
       for k, v in ontology_subset.classes.items()
   }
   ```

2. 将提示示例更新为匹配项（已使用未加前缀的名称）。

3. 修改 `expand_uri()` 以处理两种格式：
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

**优点：**
更清晰，更易于人类阅读
与现有的提示示例相符
LLM（大型语言模型）在处理更简单的token时效果更好

**缺点：**
如果多个本体具有相同的类名，则可能发生类名冲突
丢失命名空间信息
需要回退逻辑来执行查找

### 选项 B：始终使用完整的带前缀的 ID

**方法：** 更新示例，使其使用与类列表中显示的前缀 ID 匹配。

**更改：**
1. 更新提示示例（ontology-prompt.md:46-52）：
   ```json
   [
     {"subject": "recipe:cornish-pasty", "predicate": "rdf:type", "object": "fo/Recipe"},
     {"subject": "recipe:cornish-pasty", "predicate": "rdfs:label", "object": "Cornish Pasty"},
     {"subject": "recipe:cornish-pasty", "predicate": "fo/produces", "object": "food:cornish-pasty"},
     {"subject": "food:cornish-pasty", "predicate": "rdf:type", "object": "fo/Food"}
   ]
   ```

2. 在提示语中添加命名空间说明：
   ```markdown
   ## Namespace Prefixes:
   - **fo/**: Food Ontology (http://purl.org/ontology/fo/)
   - **rdf:**: RDF Schema
   - **rdfs:**: RDF Schema

   Use these prefixes exactly as shown when referencing classes and properties.
   ```

3. 保持 `expand_uri()` 的原样 (当找到匹配项时，它可以正常工作)。

**优点：**
输入 = 输出的一致性。
没有信息损失。
保留命名空间语义。
适用于多个本体。

**缺点：**
对于 LLM 来说，token 更加冗长。
需要 LLM 跟踪前缀。

### 选项 C：混合 - 同时显示标签和 ID

**方法：** 增强提示，同时显示人类可读的标签和技术 ID。

**更改：**
1. 更新提示模板：
   ```jinja
   {% for class_id, class_def in classes.items() %}
   - **{{class_id}}** (label: "{{class_def.labels[0].value if class_def.labels else class_id}}"){% if class_def.comment %}: {{class_def.comment}}{% endif %}
   {% endfor %}
   ```

   示例输出：
   ```markdown
   - **fo/Recipe** (label: "Recipe"): A Recipe is a combination...
   ```

2. 更新说明：
   ```markdown
   When referencing classes:
   - Use the full prefixed ID (e.g., "fo/Recipe") in JSON output
   - The label (e.g., "Recipe") is for human understanding only
   ```

**优点 (Pros)**:
对 LLM 最清晰
保留所有信息
明确说明应该使用什么

**缺点 (Cons)**:
提示更长
模板更复杂

## 实施方法 (Implemented Approach)

**简化的实体-关系-属性格式** - 完全取代了旧的三元组格式。

选择了这种新方法的原因是：

1. **无信息损失 (No Information Loss)**: 原始 URI 正确保留
2. **更简单的逻辑 (Simpler Logic)**: 无需转换，可以直接使用字典查找
3. **命名空间安全 (Namespace Safety)**: 能够处理多个本体而不会发生冲突
4. **语义正确性 (Semantic Correctness)**: 保持 RDF/OWL 语义

## 实施完成 (Implementation Complete)

### 构建内容 (What Was Built):

1. **新的提示模板 (New Prompt Template)** (`prompts/ontology-extract-v2.txt`)
   ✅ 清晰的章节：实体类型、关系、属性
   ✅ 使用完整类型标识符的示例 (`fo/Recipe`, `fo/has_ingredient`)
   ✅ 指示使用模式中确切的标识符
   ✅ 新的 JSON 格式，包含实体/关系/属性数组

2. **实体规范化 (Entity Normalization)** (`entity_normalizer.py`)
   ✅ `normalize_entity_name()` - 将名称转换为 URI 安全格式
   ✅ `normalize_type_identifier()` - 处理类型中的斜杠 (`fo/Recipe` → `fo-recipe`)
   ✅ `build_entity_uri()` - 使用 (名称, 类型) 元组创建唯一 URI
   ✅ `EntityRegistry` - 跟踪实体以进行去重

3. **JSON 解析器 (JSON Parser)** (`simplified_parser.py`)
   ✅ 解析新的格式：`{entities: [...], relationships: [...], attributes: [...]}`
   ✅ 支持 kebab-case 和 snake_case 字段名称
   ✅ 返回结构化的数据类
   ✅ 具有优雅的错误处理和日志记录

4. **三元组转换器 (Triple Converter)** (`triple_converter.py`)
   ✅ `convert_entity()` - 自动生成类型 + 标签三元组
   ✅ `convert_relationship()` - 通过属性连接实体 URI
   ✅ `convert_attribute()` - 添加字面值
   ✅ 从本体定义中查找完整的 URI

5. **更新的主要处理器 (Updated Main Processor)** (`extract.py`)
   ✅ 删除了旧的三元组提取代码
   ✅ 添加了 `extract_with_simplified_format()` 方法
   ✅ 现在仅使用新的简化格式
   ✅ 使用 `extract-with-ontologies-v2` ID 调用提示

## 测试用例 (Test Cases)

### 测试 1: URI 保留 (Test 1: URI Preservation)
```python
# Given ontology class
classes = {"fo/Recipe": {"uri": "http://purl.org/ontology/fo/Recipe", ...}}

# When LLM returns
llm_output = {"subject": "x", "predicate": "rdf:type", "object": "fo/Recipe"}

# Then expanded URI should be
assert expanded == "http://purl.org/ontology/fo/Recipe"
# Not: "https://trustgraph.ai/ontology/food#Recipe"
```

### 测试 2：多本体冲突
```python
# Given two ontologies
ont1 = {"fo/Recipe": {...}}
ont2 = {"cooking/Recipe": {...}}

# LLM should use full prefix to disambiguate
llm_output = {"object": "fo/Recipe"}  # Not just "Recipe"
```

### 测试 3：实体实例格式
```python
# Given prompt with food ontology
# LLM should create instances like
{"subject": "recipe:cornish-pasty"}  # Namespace-style
{"subject": "food:beef"}              # Consistent prefix
```

## 待解决的问题

1. **实体实例是否应该使用命名空间前缀？**
   当前：`"recipe:cornish-pasty"` (任意)
   替代方案：使用本体前缀 `"fo:cornish-pasty"`？
   替代方案：不使用前缀，在 URI 中展开 `"cornish-pasty"` → 完整 URI？

2. **如何在提示中处理域/范围？**
   当前显示：`(Recipe → Food)`
   应该是：`(fo/Recipe → fo/Food)`？

3. **是否应该验证域/范围约束？**
   TODO 注释在 extract.py:470
   可以捕获更多错误，但更复杂

4. **关于反向属性和等价性？**
   本体有 `owl:inverseOf`，`owl:equivalentClass`
   当前未在提取中使用
   应该使用吗？

## 成功指标

✅ 零 URI 信息损失（100% 保留原始 URI）
✅ LLM 输出格式与输入格式匹配
✅ 提示中没有歧义的示例
✅ 使用多个本体的测试通过
✅ 提取质量得到改进（通过有效的三元组百分比衡量）

## 替代方法：简化的提取格式

### 理念

不要让 LLM 理解 RDF/OWL 语义，而是让它做擅长的事情：**在文本中查找实体和关系**。

让代码处理 URI 构造、RDF 转换和语义网规范。

### 示例：实体分类

**输入文本：**
```
Cornish pasty is a traditional British pastry filled with meat and vegetables.
```

**本体模式（显示给LLM）：**
```markdown
## Entity Types:
- Recipe: A recipe is a combination of ingredients and a method
- Food: A food is something that can be eaten
- Ingredient: An ingredient combines a quantity and a food
```

**LLM 返回的内容（简单 JSON）：**
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

**生成的代码（RDF 三元组）：**
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

### 优点

1. **LLM 不需要：**
   理解 URI 语法
   编造标识符前缀 (`recipe:`, `ingredient:`)
   了解 `rdf:type` 或 `rdfs:label`
   构建语义网标识符

2. **LLM 只需要：**
   在文本中找到实体
   将它们映射到本体类
   提取关系和属性

3. **代码负责：**
   URI 规范化和构建
   RDF 三元组生成
   自动标签分配
   命名空间管理

### 为什么这样更好

**更简单的提示** = 减少困惑 = 更少的错误
**一致的 ID** = 代码控制规范化规则
**自动生成的标签** = 没有遗漏的 rdfs:label 三元组
**LLM 专注于提取** = 这是它擅长的事情

### 示例：实体关系

**输入文本：**
```
Cornish pasty is a traditional British pastry filled with beef and potatoes.
```

**本体模式（显示给LLM）：**
```markdown
## Entity Types:
- Recipe: A recipe is a combination of ingredients and a method
- Food: A food is something that can be eaten
- Ingredient: An ingredient combines a quantity and a food

## Relationships:
- has_ingredient: Relates a recipe to an ingredient it uses (Recipe → Ingredient)
- food: Relates an ingredient to the food that is required (Ingredient → Food)
```

**LLM 返回的内容（简单 JSON）：**
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

**生成的代码（RDF 三元组）：**
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

**关键点：**
LLM 返回自然语言实体名称：`"Cornish pasty"`, `"beef"`, `"potatoes"`
LLM 包含类型信息以消除歧义：`subject-type`, `object-type`
LLM 使用模式中的关系名称：`"has_ingredient"`
代码使用 (名称, 类型) 推导一致的 ID：`("Cornish pasty", "Recipe")` → `recipe-cornish-pasty`
代码从本体中查找关系 URI：`fo/has_ingredient` → 完整 URI
相同的 (名称, 类型) 元组始终获得相同的 URI (去重)

### 示例：实体名称消除歧义

**问题：** 相同的名称可能指不同的实体类型。

**实际案例：**
```
"Cornish pasty" can be:
- A Recipe (instructions for making it)
- A Food (the dish itself)
```

**处理方式：**

LLM 将两者都以独立的实体返回：
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

**代码解析：**
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

**原理：**
类型包含在所有引用中（实体、关系、属性）。
代码使用 `(name, type)` 元组作为查找键。
没有歧义，没有冲突。

### 示例：实体属性

**输入文本：**
```
This Cornish pasty recipe serves 4-6 people and takes 45 minutes to prepare.
```

**本体模式（显示给LLM）：**
```markdown
## Entity Types:
- Recipe: A recipe is a combination of ingredients and a method

## Attributes:
- serves: Indicates what the recipe is intended to serve (Recipe → text)
- preparation_time: Time needed to prepare the recipe (Recipe → text)
```

**LLM 返回的内容（简单 JSON）：**
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

**生成的代码（RDF 三元组）：**
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

**关键点：**
LLM 提取字面值：`"4-6 people"`, `"45 minutes"`
LLM 包含实体类型以消除歧义：`entity-type`
LLM 使用来自模式的属性名称：`"serves"`, `"preparation_time"`
代码从本体数据类型属性中查找属性 URI
**对象是字面值** (`is_uri=False`)，而不是 URI 引用
值保持为自然文本，无需进行任何标准化

**与关系的差异：**
关系：主语和宾语都是实体（URI）
属性：主语是实体（URI），宾语是字面值（字符串/数字）

### 完整示例：实体 + 关系 + 属性

**输入文本：**
```
Cornish pasty is a savory pastry filled with beef and potatoes.
This recipe serves 4 people.
```

**LLM 返回的内容：**
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

**结果：** 生成了 11 个 RDF 三元组：
3 个实体类型三元组 (rdf:type)
3 个实体标签三元组 (rdfs:label) - 自动
2 个关系三元组 (has_ingredient)
1 个属性三元组 (serves)

所有内容均由 LLM 通过简单的、自然的语言提取得出！

## 参考文献

当前实现：`trustgraph-flow/trustgraph/extract/kg/ontology/extract.py`
提示模板：`ontology-prompt.md`
测试用例：`tests/unit/test_extract/test_ontology/`
示例本体：`e2e/test-data/food.ontology`
