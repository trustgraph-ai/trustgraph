---
layout: default
title: "MCP 工具参数规范"
parent: "Chinese (Beta)"
---

# MCP 工具参数规范

> **Beta Translation:** This document was translated via Machine Learning and as such may not be 100% accurate. All non-English languages are currently classified as Beta.

## 概述
**功能名称**: MCP 工具参数支持
**作者**: Claude 代码助手
**日期**: 2025-08-21
**状态**: 最终

### 摘要

启用 ReACT 代理调用带有正确定义的参数的 MCP (模型上下文协议) 工具，通过在 MCP 工具配置中添加参数规范支持，类似于当前提示模板工具的工作方式。

### 问题陈述

目前，ReACT 代理框架中的 MCP 工具无法指定其预期的参数。`McpToolImpl.get_arguments()` 方法返回一个空列表，迫使 LLM 仅根据工具名称和描述来猜测正确的参数结构。这会导致：
- 由于参数猜测导致的不可靠工具调用
- 当工具因错误的参数而失败时，用户体验不佳
- 在执行之前无法验证工具参数
- 代理提示中缺少参数文档

### 目标

- [ ] 允许 MCP 工具配置指定预期的参数（名称、类型、描述）
- [ ] 更新代理管理器，通过提示向 LLM 暴露 MCP 工具参数
- [ ] 保持与现有 MCP 工具配置的向后兼容性
- [ ] 支持与提示模板工具类似的参数验证

### 不属于目标
- 从 MCP 服务器动态发现参数（未来增强功能）
- 参数类型验证，超出基本结构
- 复杂的参数模式（嵌套对象、数组）

## 背景和上下文

### 现状
MCP 工具在 ReACT 代理系统中配置为具有最小的元数据：
```json
{
  "type": "mcp-tool",
  "name": "get_bank_balance",
  "description": "获取银行账户余额",
  "mcp-tool": "get_bank_balance"
}
```

`McpToolImpl.get_arguments()` 方法返回 `[]`，因此 LLM 在提示中不会收到任何参数指导。

### 局限性

1. **缺少参数指定**: MCP 工具无法定义预期的参数
2. **LLM 参数猜测**: 代理必须根据工具名称/描述推断参数
3. **提示信息缺失**: 代理提示中不包含 MCP 工具的参数详情
4. **无验证**: 无效参数仅在 MCP 工具执行时捕获

### 相关组件
- **trustgraph-flow/agent/react/service.py**: 工具配置加载和 AgentManager 创建
- **trustgraph-flow/agent/react/tools.py**: McpToolImpl 实现
- **trustgraph-flow/agent/react/agent_manager.py**: 使用工具参数生成提示
- **tg-invoke-mcp-tool**: 用于 MCP 工具管理的 CLI 工具
- **Workbench**: 代理工具配置的外部 UI

## 要求

### 功能要求

1. **MCP 工具配置参数**: MCP 工具配置 **必须** 支持一个可选的 `arguments` 数组，包含名称、类型和描述字段
2. **参数暴露**: `McpToolImpl.get_arguments()` **必须** 返回配置的参数，而不是空列表
3. **提示集成**: 代理提示 **必须** 在指定有参数时，包含 MCP 工具参数详情
4. **向后兼容性**: 没有参数的现有 MCP 工具配置 **必须** 保持正常工作
5. **CLI 支持**: 现有的 `tg-invoke-mcp-tool` CLI 支持参数（已实现）

### 非功能要求
1. **向后兼容性**: 现有 MCP 工具配置零中断
2. **性能**: 代理提示生成没有显著性能影响
3. **一致性**: 参数处理 **必须** 与提示模板工具模式匹配

### 用户故事

1. 作为 **代理开发者**，我希望在配置中指定 MCP 工具参数，以便 LLM 可以使用正确的参数调用工具
2. 作为 **Workbench 用户**，我希望在 UI 中配置 MCP 工具参数，以便代理正确使用工具
3. 作为 **ReACT 代理中的 LLM**，我希望在提示中看到工具参数规范，以便我可以提供正确的参数

## 设计

### 高级架构
通过以下方式，扩展 MCP 工具配置以匹配提示模板模式：
1. 在 MCP 工具配置中添加可选的 `arguments` 数组，包含名称、类型和描述字段
2. 修改 `McpToolImpl` 以接受和返回配置的参数
3. 修改工具配置加载以处理 MCP 工具参数
4. 确保代理提示包含 MCP 工具参数信息

### 配置方案
```json
{
  "type": "mcp-tool",
  "name": "get_bank_balance", 
  "description": "获取银行账户余额",
  "mcp-tool": "get_bank_balance",
  "arguments": [
    {
      "name": "account_id",
      "type": "string", 
      "description": "银行账户标识符"
    },
    {
      "name": "date",
      "type": "string",
      "description": "查询余额的日期（可选，格式：YYYY-MM-DD）"
    }
  ]
}
```

### 数据流程
1. **配置加载**: 使用参数的 MCP 工具配置通过 `on_tools_config()` 加载
2. **工具创建**: 参数解析并传递给 `McpToolImpl` 通过构造函数
3. **提示生成**: `agent_manager.py` 调用 `tool.arguments` 以包含在 LLM 提示中
4. **工具调用**: LLM 提供参数，这些参数传递给 MCP 服务不变

### API 更改
- 无外部 API 更改 - 这是一个纯粹的内部配置和参数处理

### 组件详情

#### 组件 1: service.py (工具配置加载)
- **目的**: 解析 MCP 工具配置并创建工具实例
- **更改要求**:  解析 MCP 工具配置中的参数（类似于提示工具）
- **新功能**: 从 MCP 工具配置中提取 `arguments` 数组，并创建 `Argument` 对象

#### 组件 2: tools.py (McpToolImpl)
- **目的**: MCP 工具实现包装器
- **更改要求**: 接受构造函数中的参数并从 `get_arguments()` 中返回
- **新功能**: 存储并公开配置的参数，而不是返回空列表

#### 组件 3: Workbench (外部仓库)
- **目的**: 代理工具配置的 UI
- **更改要求**: 为 MCP 工具添加参数规范 UI
- **新功能**: 允许用户添加/编辑/删除 MCP 工具的参数

#### 组件 4: CLI 工具
- **目的**: 命令列工具管理
- **更改要求**: 支持在工具创建/更新命令中指定参数
- **新功能**: 在工具配置命令中接受 `arguments` 参数

## 实施计划

### 阶段 1: 核心代理框架更改
- [ ] 更新 `McpToolImpl` 构造函数以接受 `arguments` 参数
- [ ] 修改 `McpToolImpl.get_arguments()` 以返回存储的参数，而不是空列表
- [ ] 修改 `service.py` 中的 MCP 工具配置解析以处理参数
- [ ] 添加 MCP 工具参数的测试
- [ ] 更新 McpToolImpl 类文档
- [ ] 添加参数解析逻辑的注释
- [ ] 更新系统架构中的参数流程文档

### 阶段 4: 生产部署
- 核心更改具有向后兼容性 - 无需回滚，因为功能正常
- 如果出现问题，请通过回滚 MCP 工具配置加载逻辑来禁用参数解析
- Workbench 和 CLI 更改是独立的，可以单独回滚

## 安全注意事项
- **没有新的攻击面**: 参数是从现有配置源解析的，没有新的输入
- **参数验证**: 参数传递给 MCP 工具不变 - 验证在 MCP 工具级别
- **配置完整性**: 参数规范是工具配置的一部分 - 相同的安全模型适用

## 性能影响
- **极小的开销**: 参数解析仅在配置加载期间发生，而不是请求时
- **提示大小增加**: 代理提示将包含 MCP 工具参数详情，稍微增加令牌使用量
- **内存使用**: 存储参数规范在对象中的增加，可以忽略不计

## 文档

### 用户文档
- [ ] 更新 MCP 工具配置指南，提供参数示例
- [ ] 在 CLI 工具的帮助文本中添加参数规范
- [ ] 创建常见 MCP 工具参数模式的示例

### 开发者文档
- [ ] 更新 `McpToolImpl` 类文档
- [ ] 添加参数解析逻辑的注释
- [ ] 文档系统架构中的参数流程

## 未解决的问题
1. **参数验证**: 是否应该在基本结构检查之外验证参数类型/格式？
2. **动态发现**: 将来增强功能，以在运行时自动从 MCP 服务器查询工具模式？

## 考虑的替代方案
1. **动态的 MCP 模式发现**: 在运行时查询 MCP 服务器以获取工具参数模式 - 已拒绝，因为它复杂且不可靠
2. **单独的参数注册表**: 将 MCP 工具参数存储在单独的配置部分中 - 已拒绝，因为与提示模板方法保持一致
3. **类型验证**: JSON 模式验证参数 - 延迟，以便在初始实现中保持简单

## 引用
- [MCP 协议规范](https://github.com/modelcontextprotocol/spec)
- [提示模板工具实现](./trustgraph-flow/trustgraph/agent/react/service.py#L114-129)
- [当前的 MCP 工具实现](./trustgraph-flow/trustgraph/agent/react/tools.py#L58-86)
