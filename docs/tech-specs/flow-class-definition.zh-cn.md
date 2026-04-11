---
layout: default
title: "流程蓝图定义规范"
parent: "Chinese (Beta)"
---

<<<<<<< HEAD
# 流程蓝图定义规范

> **Beta Translation:** This document was translated via Machine Learning and as such may not be 100% accurate. All non-English languages are currently classified as Beta.

## 概述

流程蓝图在 TrustGraph 系统中定义了一个完整的数据流模式模板。当实例化时，它会创建一个相互连接的处理单元网络，该网络处理数据摄取、处理、存储和查询，作为一个统一的系统。

## 结构

流程蓝图定义由五个主要部分组成：

### 1. 类部分
定义共享服务处理器，这些处理器每个流程蓝图实例化一次。这些处理器处理来自此类的所有流程实例的请求。
=======
# 流工作蓝图定义规范

## 概述

一个流工作蓝图定义了 TrustGraph 系统中完整的数据流模式模板。当实例化时，它会创建一个相互连接的处理单元网络，该网络处理数据摄取、处理、存储和查询，作为一个统一的系统。

## 结构

一个流工作蓝图定义由五个主要部分组成：

### 1. 类部分
定义共享服务处理器，这些处理器每个流工作蓝图实例化一次。这些处理器处理来自此类的所有流实例的请求。
>>>>>>> 82edf2d (New md files from RunPod)

```json
"class": {
  "service-name:{class}": {
    "request": "queue-pattern:{class}",
    "response": "queue-pattern:{class}",
    "settings": {
      "setting-name": "fixed-value",
      "parameterized-setting": "{parameter-name}"
    }
  }
}
```

<<<<<<< HEAD
**特性：**
=======
**特点：**
>>>>>>> 82edf2d (New md files from RunPod)
在同一类别的所有流程实例中共享。
通常是昂贵或无状态的服务（例如：大型语言模型、嵌入模型）。
使用 `{class}` 模板变量进行队列命名。
设置可以是固定值，也可以使用 `{parameter-name}` 语法进行参数化。
示例：`embeddings:{class}`, `text-completion:{class}`, `graph-rag:{class}`

### 2. 流程部分
定义与流程相关的处理器，这些处理器为每个独立的流程实例进行实例化。 每个流程都拥有自己的一组隔离的处理器。

```json
"flow": {
  "processor-name:{id}": {
    "input": "queue-pattern:{id}",
    "output": "queue-pattern:{id}",
    "settings": {
      "setting-name": "fixed-value",
      "parameterized-setting": "{parameter-name}"
    }
  }
}
```

**特性：**
每个流程只有一个实例。
处理流程特定的数据和状态。
使用 `{id}` 模板变量进行队列命名。
设置可以是固定值，也可以使用 `{parameter-name}` 语法进行参数化。
示例：`chunker:{id}`, `pdf-decoder:{id}`, `kg-extract-relationships:{id}`

### 3. 接口部分
定义流程的入口点和交互协议。 这些构成了外部系统和内部组件通信的 API 表面。

<<<<<<< HEAD
接口可以有两种形式：

**即发即弃模式**（单个队列）：
=======
接口可以采用两种形式：

**发布-订阅模式**（单个队列）：
>>>>>>> 82edf2d (New md files from RunPod)
```json
"interfaces": {
  "document-load": "persistent://tg/flow/document-load:{id}",
  "triples-store": "persistent://tg/flow/triples-store:{id}"
}
```

**请求/响应模式** (包含请求/响应字段的对象):
```json
"interfaces": {
  "embeddings": {
    "request": "non-persistent://tg/request/embeddings:{class}",
    "response": "non-persistent://tg/response/embeddings:{class}"
  }
}
```

**接口类型：**
**入口点：** 外部系统注入数据的入口点 (`document-load`, `agent`)
**服务接口：** 服务请求/响应模式 (`embeddings`, `text-completion`)
**数据接口：** 触发/完成式数据流连接点 (`triples-store`, `entity-contexts-load`)

### 4. 参数部分
将流程特定的参数名称映射到集中存储的参数定义：

```json
"parameters": {
  "model": "llm-model",
  "temp": "temperature",
  "chunk": "chunk-size"
}
```

**特性：**
键是处理器设置中使用的参数名称（例如，`{model}`）
值引用存储在 schema/config 中的参数定义
允许在流程之间重用常见的参数定义
减少参数模式的重复

### 5. 元数据
关于流程蓝图的附加信息：

```json
"description": "Human-readable description",
"tags": ["capability-1", "capability-2"]
```

## 模板变量

### 系统变量

#### {id}
被替换为唯一的流程实例标识符
为每个流程创建隔离的资源
示例：`flow-123`, `customer-A-flow`

#### {class}
被替换为流程蓝图名称
为相同类别的流程创建共享资源
示例：`standard-rag`, `enterprise-rag`

### 参数变量

#### {parameter-name}
在流程启动时定义的自定义参数
参数名称与流程的 `parameters` 部分中的键匹配
用于在处理器设置中自定义行为
示例：`{model}`, `{temp}`, `{chunk}`
被替换为启动流程时提供的值
验证通过与集中存储的参数定义进行比较

## 处理器设置

设置在实例化时向处理器提供配置值。 它们可以是：

### 静态设置
直接值，不会改变：
```json
"settings": {
  "model": "gemma3:12b",
  "temperature": 0.7,
  "max_retries": 3
}
```

### 参数化设置
使用在流程启动时提供的参数的值：
```json
"settings": {
  "model": "{model}",
  "temperature": "{temp}",
  "endpoint": "https://{region}.api.example.com"
}
```

参数名称在设置中对应于流程的 `parameters` 部分中的键。

### 设置示例

**带有参数的 LLM 处理器：**
```json
// In parameters section:
"parameters": {
  "model": "llm-model",
  "temp": "temperature",
  "tokens": "max-tokens",
  "key": "openai-api-key"
}

// In processor definition:
"text-completion:{class}": {
  "request": "non-persistent://tg/request/text-completion:{class}",
  "response": "non-persistent://tg/response/text-completion:{class}",
  "settings": {
    "model": "{model}",
    "temperature": "{temp}",
    "max_tokens": "{tokens}",
    "api_key": "{key}"
  }
}
```

**具有固定和参数化设置的分块器：**
```json
// In parameters section:
"parameters": {
  "chunk": "chunk-size"
}

// In processor definition:
"chunker:{id}": {
  "input": "persistent://tg/flow/chunk:{id}",
  "output": "persistent://tg/flow/chunk-load:{id}",
  "settings": {
    "chunk_size": "{chunk}",
    "chunk_overlap": 100,
    "encoding": "utf-8"
  }
}
```

## 队列模式 (Pulsar)

流程蓝图使用 Apache Pulsar 进行消息传递。队列名称遵循 Pulsar 格式：
```
<persistence>://<tenant>/<namespace>/<topic>
```

### 组件：
**持久性**: `persistent` 或 `non-persistent` (Pulsar 持久性模式)
**租户**: `tg` 用于 TrustGraph 提供的流程蓝图定义
**命名空间**: 表示消息模式
  `flow`: 适用于“发送即忘”服务
  `request`: 适用于请求/响应服务的请求部分
  `response`: 适用于请求/响应服务的响应部分
**主题**: 具有模板变量的特定队列/主题名称

### 持久队列
模式: `persistent://tg/flow/<topic>:{id}`
用于“发送即忘”服务和持久数据流
数据在 Pulsar 存储中持久化，即使在重启后也保留
示例: `persistent://tg/flow/chunk-load:{id}`

### 非持久队列
模式: `non-persistent://tg/request/<topic>:{class}` 或 `non-persistent://tg/response/<topic>:{class}`
用于请求/响应消息模式
瞬态的，不由 Pulsar 持久化到磁盘
延迟较低，适用于 RPC 风格的通信
示例: `non-persistent://tg/request/embeddings:{class}`

## 数据流架构

流程蓝图创建统一的数据流，其中：

<<<<<<< HEAD
1. **文档处理管道**: 从摄取到转换再到存储的流程
2. **查询服务**: 集成的处理器，查询相同的存储和服务
3. **共享服务**: 所有流程都可以使用的集中式处理器
4. **存储写入器**: 将处理后的数据持久化到适当的存储中
=======
1. **文档处理管道**: 从摄取到转换再到存储
2. **查询服务**: 集成的处理器，查询相同的存储和服务
3. **共享服务**: 所有流程都可以使用的集中处理器
4. **存储写入器**: 将处理后的数据持久化到适当的存储
>>>>>>> 82edf2d (New md files from RunPod)

所有处理器（包括 `{id}` 和 `{class}`）协同工作，形成一个连贯的数据流图，而不是作为独立的系统。

## 流程实例化示例

假设：
流程实例 ID: `customer-A-flow`
流程蓝图: `standard-rag`
流程参数映射：
  `"model": "llm-model"`
  `"temp": "temperature"`
  `"chunk": "chunk-size"`
用户提供的参数：
  `model`: `gpt-4`
  `temp`: `0.5`
  `chunk`: `512`

模板扩展：
`persistent://tg/flow/chunk-load:{id}` → `persistent://tg/flow/chunk-load:customer-A-flow`
`non-persistent://tg/request/embeddings:{class}` → `non-persistent://tg/request/embeddings:standard-rag`
`"model": "{model}"` → `"model": "gpt-4"`
`"temperature": "{temp}"` → `"temperature": "0.5"`
`"chunk_size": "{chunk}"` → `"chunk_size": "512"`

这会创建：
用于 `customer-A-flow` 的隔离文档处理管道
用于所有 `standard-rag` 流程的共享嵌入服务
从文档摄取到查询的完整数据流
使用提供的参数值配置的处理器

## 优点

1. **资源效率**: 昂贵的服务在流程之间共享
2. **流程隔离**: 每个流程都有自己的数据处理管道
3. **可扩展性**: 可以从相同的模板实例化多个流程
4. **模块化**: 共享组件和流程特定组件之间有明确的分离
5. **统一架构**: 查询和处理是相同的数据流的一部分
