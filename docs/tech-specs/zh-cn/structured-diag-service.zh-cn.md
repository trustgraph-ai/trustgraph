---
layout: default
title: "结构化数据诊断服务技术规范"
parent: "Chinese (Beta)"
---

# 结构化数据诊断服务技术规范

> **Beta Translation:** This document was translated via Machine Learning and as such may not be 100% accurate. All non-English languages are currently classified as Beta.

## 概述

本规范描述了一种新的可调用服务，用于诊断和分析 TrustGraph 中的结构化数据。该服务从现有的 `tg-load-structured-data` 命令行工具中提取功能，并将其暴露为请求/响应服务，从而实现对数据类型检测和描述符生成功能的编程访问。

该服务支持三种主要操作：

1. **数据类型检测**: 分析数据样本以确定其格式（CSV、JSON 或 XML）
2. **描述符生成**: 为给定的数据样本和类型生成 TrustGraph 结构化数据描述符
3. **综合诊断**: 依次执行数据类型检测和描述符生成

## 目标

**模块化数据分析**: 将数据诊断逻辑从 CLI 提取到可重用的服务组件中
**启用编程访问**: 提供基于 API 的访问数据分析能力
**支持多种数据格式**: 始终如一地处理 CSV、JSON 和 XML 数据格式
**生成准确的描述符**: 生成准确映射源数据到 TrustGraph 模式的结构化数据描述符
**保持向后兼容性**: 确保现有的 CLI 功能继续正常工作
**启用服务组合**: 允许其他服务利用数据诊断能力
**提高可测试性**: 将业务逻辑与 CLI 接口分离，以获得更好的测试效果
**支持流式分析**: 允许分析数据样本，而无需加载整个文件

## 背景

目前，`tg-load-structured-data` 命令提供了用于分析结构化数据和生成描述符的全面功能。但是，此功能与 CLI 接口紧密耦合，限制了其可重用性。

当前的限制包括：
数据诊断逻辑嵌入在 CLI 代码中
没有对数据类型检测和描述符生成的编程访问
难以将诊断能力集成到其他服务中
难以组合数据分析工作流程

本规范通过创建一个专用的结构化数据诊断服务来解决这些差距。通过将这些功能暴露为服务，TrustGraph 可以：
允许其他服务以编程方式分析数据
支持更复杂的数据处理管道
促进与外部系统的集成
通过分离关注点来提高可维护性

## 技术设计

### 架构

结构化数据诊断服务需要以下技术组件：

1. **诊断服务处理器**
   处理传入的诊断请求
   协调数据类型检测和描述符生成
   返回包含诊断结果的结构化响应

   模块：`trustgraph-flow/trustgraph/diagnosis/structured_data/service.py`

2. **数据类型检测器**
   使用算法检测来识别数据格式（CSV、JSON、XML）
   分析数据结构、分隔符和语法模式
   返回检测到的格式和置信度分数

   模块：`trustgraph-flow/trustgraph/diagnosis/structured_data/type_detector.py`

3. **描述符生成器**
   使用提示服务生成描述符
   调用特定于格式的提示（diagnose-csv、diagnose-json、diagnose-xml）
   通过提示响应将数据字段映射到 TrustGraph 模式字段

   模块：`trustgraph-flow/trustgraph/diagnosis/structured_data/descriptor_generator.py`

### 数据模型

#### StructuredDataDiagnosisRequest

结构化数据诊断操作的请求消息：

```python
class StructuredDataDiagnosisRequest:
    operation: str  # "detect-type", "generate-descriptor", or "diagnose"
    sample: str     # Data sample to analyze (text content)
    type: Optional[str]  # Data type (csv, json, xml) - required for generate-descriptor
    schema_name: Optional[str]  # Target schema name for descriptor generation
    options: Dict[str, Any]  # Additional options (e.g., delimiter for CSV)
```

#### 结构化数据诊断响应

包含诊断结果的响应消息：

```python
class StructuredDataDiagnosisResponse:
    operation: str  # The operation that was performed
    detected_type: Optional[str]  # Detected data type (for detect-type/diagnose)
    confidence: Optional[float]  # Confidence score for type detection
    descriptor: Optional[Dict]  # Generated descriptor (for generate-descriptor/diagnose)
    error: Optional[str]  # Error message if operation failed
    metadata: Dict[str, Any]  # Additional metadata (e.g., field count, sample records)
```

#### 描述符结构

生成的描述符遵循现有的结构化数据描述符格式：

```json
{
  "format": {
    "type": "csv",
    "encoding": "utf-8",
    "options": {
      "delimiter": ",",
      "has_header": true
    }
  },
  "mappings": [
    {
      "source_field": "customer_id",
      "target_field": "id",
      "transforms": [
        {"type": "trim"}
      ]
    }
  ],
  "output": {
    "schema_name": "customer",
    "options": {
      "batch_size": 1000,
      "confidence": 0.9
    }
  }
}
```

### 服务接口

该服务将通过请求/响应模式提供以下操作：

1. **类型检测操作**
   输入：数据样本
   处理：使用算法检测分析数据结构
   输出：检测到的类型及其置信度分数

2. **描述符生成操作**
   输入：数据样本、类型、目标模式名称
   处理：
     使用特定格式的提示 ID（diagnose-csv、diagnose-json 或 diagnose-xml）调用提示服务
     将数据样本和可用模式传递给提示
     从提示响应接收生成的描述符
   输出：结构化数据描述符

3. **综合诊断操作**
   输入：数据样本、可选模式名称
   处理：
     首先使用算法检测识别格式
     根据检测到的类型选择适当的特定格式的提示
     调用提示服务以生成描述符
   输出：检测到的类型和描述符

### 实现细节

该服务将遵循 TrustGraph 服务约定：

1. **服务注册**
   注册为 `structured-diag` 服务类型
   使用标准的请求/响应主题
   实现 FlowProcessor 基础类
   注册 PromptClientSpec 以进行提示服务交互

2. **配置管理**
   通过配置服务访问模式配置
   缓存模式以提高性能
   动态处理配置更新

3. **提示集成**
   使用现有的提示服务基础设施
   使用特定格式的提示 ID调用提示服务：
     `diagnose-csv`：用于 CSV 数据分析
     `diagnose-json`：用于 JSON 数据分析
     `diagnose-xml`：用于 XML 数据分析
   提示配置在提示配置中，而不是硬编码在服务中
   将模式和数据样本作为提示变量传递
   解析提示响应以提取描述符

4. **错误处理**
   验证输入数据样本
   提供描述性的错误消息
   优雅地处理格式错误的数据
   处理提示服务故障

5. **数据采样**
   处理可配置的样本大小
   适当处理不完整的记录
   保持采样的一致性

### API 集成

该服务将与现有的 TrustGraph API 集成：

修改的组件：
`tg-load-structured-data` CLI - 重新设计为使用新的服务进行诊断操作
Flow API - 扩展以支持结构化数据诊断请求

新的服务端点：
`/api/v1/flow/{flow}/diagnose/structured-data` - 用于诊断请求的 WebSocket 端点
`/api/v1/diagnose/structured-data` - 用于同步诊断的 REST 端点

### 消息流

```
Client → Gateway → Structured Diag Service → Config Service (for schemas)
                                           ↓
                                    Type Detector (algorithmic)
                                           ↓
                                    Prompt Service (diagnose-csv/json/xml)
                                           ↓
                                 Descriptor Generator (parses prompt response)
                                           ↓
Client ← Gateway ← Structured Diag Service (response)
```

## 安全注意事项

输入验证，以防止注入攻击
对数据样本的大小设置限制，以防止拒绝服务 (DoS) 攻击
清理生成的描述符
通过现有的 TrustGraph 身份验证进行访问控制

## 性能注意事项

缓存模式定义，以减少对配置服务的调用
限制样本大小，以保持响应性能
对大型数据样本使用流式处理
实施超时机制，用于长时间运行的分析

## 测试策略

1. **单元测试**
   对各种数据格式进行类型检测
   描述符生成准确性
   错误处理场景

2. **集成测试**
   服务请求/响应流程
   模式检索和缓存
   CLI 集成

3. **性能测试**
   处理大型样本
   并发请求处理
   在负载下的内存使用情况

## 迁移计划

1. **第一阶段**: 实施具有核心功能的服务
2. **第二阶段**: 重构 CLI 以使用服务（保持向后兼容性）
3. **第三阶段**: 添加 REST API 端点
4. **第四阶段**: 弃用嵌入式 CLI 逻辑（提前通知）

## 时间表

第 1-2 周：实施核心服务和类型检测
第 3-4 周：添加描述符生成和集成
第 5 周：测试和文档
第 6 周：CLI 重构和迁移

## 开放问题

该服务是否应支持其他数据格式（例如，Parquet、Avro）？
分析的最大样本大小应为多少？
诊断结果是否应针对重复请求进行缓存？
该服务应如何处理多模式场景？
提示 ID 是否应为服务的可配置参数？

## 参考文献

[结构化数据描述符规范](structured-data-descriptor.md)
[结构化数据加载文档](structured-data.md)
`tg-load-structured-data` 实现：`trustgraph-cli/trustgraph/cli/load_structured_data.py`
