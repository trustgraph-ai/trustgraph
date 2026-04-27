---
layout: default
title: "本体结构技术规范"
parent: "Chinese (Beta)"
---

# 本体结构技术规范

> **Beta Translation:** This document was translated via Machine Learning and as such may not be 100% accurate. All non-English languages are currently classified as Beta.

## 概述

本规范描述了 TrustGraph 系统中本体的结构和格式。 本体提供正式的知识模型，定义类、属性、以及它们之间的关系，从而支持推理和推断功能。 该系统采用基于 OWL 的配置格式，广泛地表示 OWL/RDFS 概念，同时针对 TrustGraph 的特定需求进行了优化。

**命名约定**: 该项目使用 kebab-case 格式（例如，`natural-world`、`domain-model`、`configuration keys`、`API endpoints`、`module names` 等）来表示所有标识符，而不是 snake_case。

## 目标

- **类和属性管理**: 定义类似 OWL 的类，并包含属性、域、范围以及类型约束
- **强大的语义支持**: 启用全面的 RDFS/OWL 属性，包括标签、多语言支持以及正式约束
- **多本体支持**: 允许多个本体共存并相互协作
- **验证和推理**: 确保本体符合 OWL 类似的标准，包括一致性检查和推理支持
- **标准兼容性**: 支持以标准格式（Turtle、RDF/XML、OWL/XML）进行导入/导出，同时保持内部优化

## 背景

TrustGraph 将本体存储为配置项，采用灵活的键值系统。 尽管该格式受到 OWL (Web Ontology Language) 的启发，但它针对 TrustGraph 的特定用例进行了优化，并且并非完全符合所有 OWL 规范。

在 TrustGraph 中，本体能够实现以下功能：

- 定义对象类型及其属性
- 规范属性的域、范围和类型约束
- 进行逻辑推理
- 定义复杂的关系和数量约束
- 支持多种语言，用于国际化

## 本体结构

### 配置存储

本体以配置项的形式存储，具有以下模式：

- **类型**: `ontology`
- **键**: 唯一本体标识符（例如，`natural-world`、`domain-model`）
- **值**: 完整的本体，采用 JSON 格式

### JSON 结构

本体的 JSON 格式主要包含四个部分：

#### 1. 元数据

包含本体的行政和描述性信息：

```json
{
  "metadata": {
    "name": "The natural world",
    "description": "Ontology covering the natural order",
    "version": "1.0.0",
    "created": "2025-09-20T12:07:37.068Z",
    "modified": "2025-09-20T12:12:20.725Z",
    "creator": "current-user",
    "namespace": "http://trustgraph.ai/ontologies/natural-world",
    "imports": ["http://www.w3.org/2002/07/owl#"]
  }
}
```

**字段**:
- `name`: 本体的人类可读名称
- `description`: 本体目的的简要描述
- `version`: 语义版本号
- `created`: 创建时间 (ISO 8601 格式)
- `modified`: 最后修改时间 (ISO 8601 格式)
- `creator`: 创建用户的/系统的标识符
- `namespace`: 本体元素的基 URI
- `imports`: 导入本体 URI 数组

#### 2. 类

定义对象类型及其层次关系：

```json
{
  "classes": {
    "animal": {
      "uri": "http://trustgraph.ai/ontologies/natural-world#animal",
      "type": "owl:Class",
      "rdfs:label": [{"value": "Animal", "lang": "en"}],
      "rdfs:comment": "An animal",
      "rdfs:subClassOf": "lifeform",
      "owl:equivalentClass": ["creature"],
      "owl:disjointWith": ["plant"],
      "dcterms:identifier": "ANI-001"
    }
  }
}
```

**支持的属性**:
- `uri`: 类的完整 URI
- `type`: 始终为 `"owl:Class"`
- `rdfs:label`: 语言标记的标签数组
- `rdfs:comment`: 类的描述
- `rdfs:subClassOf`: 上级类的标识符 (单继承)
- `owl:equivalentClass`: 等效类的标识符数组
- `owl:disjointWith`: 互斥类的标识符数组
- `dcterms:identifier`: 外部参考标识符 (可选)

#### 3. 对象属性

用于链接实例的对象属性：

```json
{
  "objectProperties": {
    "has-parent": {
      "uri": "http://trustgraph.ai/ontologies/natural-world#has-parent",
      "type": "owl:ObjectProperty",
      "rdfs:label": [{"value": "has parent", "lang": "en"}],
      "rdfs:comment": "Links an animal to its parent",
      "rdfs:domain": "animal",
      "rdfs:range": "animal",
      "owl:inverseOf": "parent-of",
      "owl:functionalProperty": false
    }
  }
}
```

**支持的属性**:
- `uri`: 属性的完整 URI
- `type`: 始终为 `"owl:ObjectProperty"`
- `rdfs:label`: 语言标记的标签数组
- `rdfs:comment`: 属性的描述
- `rdfs:domain`: 域的标识符
- `rdfs:range`: 范围的标识符
- `owl:inverseOf`: 互反属性的标识符
- `owl:functionalProperty`: 功能属性的标识符 (可选)

#### 4. 数据类型属性

```json
{
  "datatypeProperties": {
    "number-of-legs": {
      "uri": "http://trustgraph.ai/ontologies/natural-world#number-of-legs",
      "type": "owl:DatatypeProperty",
      "rdfs:label": [{"value": "number-of-legs", "lang": "en"}],
      "rdfs:comment": "Count of number of legs of the animal",
      "rdfs:range": "xsd:nonNegativeInteger",
      "rdfs:domain": "animal"
    }
  }
}
```

#### 5. 示例本体

```json
{
  "metadata": {
    "name": "The natural world",
    "description": "Ontology covering the natural order",
    "version": "1.0.0",
    "created": "2025-09-20T12:07:37.068Z",
    "modified": "2025-09-20T12:12:20.725Z",
    "creator": "current-user",
    "namespace": "http://trustgraph.ai/ontologies/natural-world",
    "imports": ["http://www.w3.org/2002/07/owl#"]
  },
  "classes": {
    "animal": {
      "uri": "http://trustgraph.ai/ontologies/natural-world#animal",
      "type": "owl:Class",
      "rdfs:label": [{"value": "Animal", "lang": "en"}],
      "rdfs:comment": "An animal"
    },
    "cat": {
      "uri": "http://trustgraph.ai/ontologies/natural-world#cat",
      "type": "owl:Class",
      "rdfs:label": [{"value": "Cat", "lang": "en"}],
      "rdfs:comment": "A cat",
      "rdfs:subClassOf": "animal"
    },
    "dog": {
      "uri": "http://trustgraph.ai/ontologies/natural-world#dog",
      "type": "owl:Class",
      "rdfs:label": [{"value": "Dog", "lang": "en"}],
      "rdfs:comment": "A dog",
      "rdfs:subClassOf": "animal",
      "owl:disjointWith": ["cat"]
    }
  },
  "objectProperties": {},
  "datatypeProperties": {
    "number-of-legs": {
      "uri": "http://trustgraph.ai/ontologies/natural-world#number-of-legs",
      "type": "owl:DatatypeProperty",
      "rdfs:label": [{"value": "number-of-legs", "lang": "en"}],
      "rdfs:comment": "Count of number of legs of the animal",
      "rdfs:range": "xsd:nonNegativeInteger",
      "rdfs:domain": "animal"
    }
  }
}
```

## 验证规则

### 结构验证

1. **URI 约束**: 所有 URI 必须遵循模式 `{namespace}#{identifier}`
2. **类层次**: 避免在 `rdfs:subClassOf` 中出现循环继承
3. **属性域/范围**: 必须引用现有类或有效的 XSD 类型
4. **互斥类**: 互斥类不能是互斥类的子类
5. **互反属性**: 如果指定，必须是双向的

### 语义验证

1. **唯一标识符**: 类的标识符和属性标识符必须是唯一的
2. **语言标签**: 必须符合 BCP 47 语言标签格式
3. **数量约束**: `minCardinality` ≤ `maxCardinality`，当两者都指定时
4. **功能属性**: 不能有 `maxCardinality` > 1

## 导入/导出格式支持

虽然内部格式为 JSON，但该系统支持与标准本体格式的转换：

- **Turtle (.ttl)** - 紧凑的 RDF 序列化
- **RDF/XML (.rdf, .owl)** - W3C 标准格式
- **OWL/XML (.owx)** - OWL 特定 XML 格式
- **JSON-LD (.jsonld)** - 用于链接数据的 JSON

## 参考文献

- [OWL 2 Web Ontology Language](https://www.w3.org/TR/owl2-overview/)
- [RDF Schema 1.1](https://www.w3.org/TR/rdf-schema/)
- [XML Schema Datatypes](https://www.w3.org/TR/xmlschema-2/)
- [BCP 47 Language Tags](https://tools.ietf.org/html/bcp47)
