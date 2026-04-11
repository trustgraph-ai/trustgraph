---
layout: default
title: "TrustGraph 工具组系统"
parent: "Chinese (Beta)"
---

# TrustGraph 工具组系统

> **Beta Translation:** This document was translated via Machine Learning and as such may not be 100% accurate. All non-English languages are currently classified as Beta.
## 技术规范 v1.0

### 摘要

本规范定义了一个用于 TrustGraph 代理的工具分组系统，该系统允许对哪些工具可用于特定请求进行细粒度控制。该系统通过配置和请求级别的指定，引入基于组的工具过滤，从而实现更好的安全边界、资源管理以及代理功能的划分。

### 1. 概述

#### 1.1 问题陈述

目前，TrustGraph 代理可以访问所有配置的工具，而与请求上下文或安全要求无关。这带来了一些挑战：

**安全风险**: 即使是只读查询，也可能访问到敏感工具（例如，数据修改）。
**资源浪费**: 即使简单的查询也不需要，也会加载复杂的工具。
**功能混淆**: 代理可能会选择不合适的工具，而存在更简单的替代方案。
**多租户隔离**: 不同的用户组需要访问不同的工具集。

#### 1.2 解决方案概述

工具分组系统引入了：

1. **组分类**: 工具在配置时会被标记为所属的组。
2. **请求级别过滤**: AgentRequest 指定允许使用的工具组。
3. **运行时强制**: 代理只能访问与请求的组匹配的工具。
4. **灵活分组**: 工具可以属于多个组，以适应复杂的场景。

### 2. 模式变更

#### 2.1 工具配置模式增强

现有的工具配置通过添加一个 `group` 字段进行增强：

**之前：**
```json
{
  "name": "knowledge-query",
  "type": "knowledge-query", 
  "description": "Query the knowledge graph"
}
```

**翻译后：**
```json
{
  "name": "knowledge-query",
  "type": "knowledge-query",
  "description": "Query the knowledge graph",
  "group": ["read-only", "knowledge", "basic"]
}
```

**组字段规范：**
`group`: Array(String) - 此工具所属的组列表
**可选：** 没有组字段的工具属于 "默认" 组
**多重隶属：** 工具可以属于多个组
**区分大小写：** 组名必须是完全匹配的字符串

#### 2.1.2 工具状态转换增强

工具可以选择性地指定状态转换和基于状态的可用性：

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

**状态字段规范：**
`state`: String - **可选** - 成功执行工具后要转换到的状态
`available_in_states`: Array(String) - **可选** - 此工具可用的状态
**默认行为：** 没有 `available_in_states` 的工具在所有状态下都可用
**状态转换：** 仅在成功执行工具后发生

#### 2.2 AgentRequest 模式增强

`trustgraph-base/trustgraph/schema/services/agent.py` 中的 `AgentRequest` 模式已增强：

**当前 AgentRequest：**
`question`: String - 用户查询
`plan`: String - 执行计划（可以删除）
`state`: String - Agent 状态
`history`: Array(AgentStep) - 执行历史

**增强后的 AgentRequest：**
`question`: String - 用户查询
`state`: String - Agent 执行状态（现在被积极用于工具过滤）
`history`: Array(AgentStep) - 执行历史
`group`: Array(String) - **新增** - 此请求允许的工具组

**模式变更：**
**已移除：** `plan` 字段不再需要，可以删除（最初用于工具规范）
**已添加：** `group` 字段用于工具组规范
**已增强：** `state` 字段现在控制执行期间的工具可用性

**字段行为：**

**组字段：**
**可选：** 如果未指定，默认为 ["default"]
**交集：** 只有匹配至少一个指定组的工具才可用
**空数组：** 没有可用工具（agent 只能使用内部推理）
**通配符：** 特殊组 "*" 授予访问所有工具的权限

**状态字段：**
**可选：** 如果未指定，默认为 "undefined"
**基于状态的过滤：** 只有在当前状态下可用的工具才有资格
**默认状态：** "undefined" 状态允许所有工具（受组过滤限制）
**状态转换：** 成功执行后，工具可以更改状态

### 3. 自定义组示例

组织可以定义特定领域的组：

```json
{
  "financial-tools": ["stock-query", "portfolio-analysis"],
  "medical-tools": ["diagnosis-assist", "drug-interaction"],
  "legal-tools": ["contract-analysis", "case-search"]
}
```

### 4. 实现细节

#### 4.1 工具加载和过滤

**配置阶段：**
1. 所有工具从配置文件中加载，并带有其组分配信息。
2. 没有明确组分配的工具将被分配到 "默认" 组。
3. 组成员关系将被验证并存储在工具注册表中。

**请求处理阶段：**
1. AgentRequest 携带可选的组指定信息。
2. Agent 根据组的交集过滤可用的工具。
3. 只有匹配的工具才会被传递到 Agent 执行上下文。
4. Agent 在整个请求生命周期内都使用过滤后的工具集。

#### 4.2 工具过滤逻辑

**组合组和状态过滤：**

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

**状态转换逻辑：**

```
After successful tool execution:
  if tool.state is defined:
    next_request.state = tool.state
  else:
    next_request.state = current_request.state  // No change
```

#### 4.3 代理集成点

**ReAct 代理：**
工具过滤在 `agent_manager.py` 中在工具注册创建期间发生。
可用工具列表在计划生成之前，会根据组和状态进行过滤。
状态转换会在工具执行成功后更新 `AgentRequest.state` 字段。
下一次迭代使用更新后的状态进行工具过滤。

**基于置信度的代理：**
工具过滤在 `planner.py` 中在计划生成期间发生。
`ExecutionStep` 验证确保只使用组+状态符合条件的工具。
流程控制器在运行时强制执行工具可用性。
状态转换由流程控制器在步骤之间管理。

### 5. 配置示例

#### 5.1 带有组和状态的工具配置

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

#### 5.2 请求示例与状态工作流

**初始研究请求：**
```json
{
  "question": "What entities are connected to Company X?",
  "group": ["read-only", "knowledge"],
  "state": "undefined"
}
```
*可用工具：知识查询，文本补全*
*知识查询后：状态 → "分析"*

**分析阶段：**
```json
{
  "question": "Continue analysis based on previous results",
  "group": ["advanced", "compute", "write"],
  "state": "analysis"
}
```
*可用工具：复杂分析、图更新、重置工作流程*
*复杂分析之后：状态 → "结果"*

**结果阶段：**
```json
{
  "question": "What should I do with these results?",
  "group": ["admin"],
  "state": "results"
}
```
*可用的工具：仅限 reset-workflow*
*reset-workflow 之后：状态 → "undefined"*

**工作流程示例 - 完整流程：**
1. **开始 (undefined)**：使用 knowledge-query → 转换到 "analysis"
2. **分析状态：** 使用 complex-analysis → 转换到 "results"
3. **结果状态：** 使用 reset-workflow → 转换回 "undefined"
4. **返回开始：** 所有初始工具再次可用

### 6. 安全注意事项

#### 6.1 访问控制集成

**网关级别的过滤：**
网关可以根据用户权限强制执行组限制
防止通过请求修改来提升权限
审计跟踪包括请求和授予的工具组

**示例网关逻辑：**
```
user_permissions = get_user_permissions(request.user_id)
allowed_groups = user_permissions.tool_groups
requested_groups = request.group

# Validate request doesn't exceed permissions
if not is_subset(requested_groups, allowed_groups):
    reject_request("Insufficient permissions for requested tool groups")
```

#### 6.2 审计和监控

**增强的审计跟踪：**
记录每个请求所请求的工具组和初始状态
跟踪按组成员划分的状态转换和工具使用情况
监控未经授权的组访问尝试和无效的状态转换
警报不寻常的组使用模式或可疑的状态工作流程

### 7. 迁移策略

#### 7.1 向后兼容性

**第一阶段：增量更改**
向工具配置添加可选的 `group` 字段
向 AgentRequest 模式添加可选的 `group` 字段
默认行为：所有现有工具都属于 "默认" 组
现有请求如果没有组字段，则使用 "默认" 组

**保留现有行为：**
没有组配置的工具继续工作（默认组）
没有状态配置的工具在所有状态下都可用
没有组指定的请求可以访问所有工具（默认组）
没有状态指定的请求使用 "未定义" 状态（所有工具可用）
没有对现有部署进行破坏性更改

### 8. 监控和可观察性

#### 8.1 新指标

**工具组使用情况：**
`agent_tool_group_requests_total` - 按组划分的请求计数器
`agent_tool_group_availability` - 每个组可用的工具计量
`agent_filtered_tools_count` - 组+状态过滤后工具计数的直方图

**状态工作流程指标：**
`agent_state_transitions_total` - 按工具划分的状态转换计数器
`agent_workflow_duration_seconds` - 每个状态花费时间的直方图
`agent_state_availability` - 每个状态可用的工具计量

**安全指标：**
`agent_group_access_denied_total` - 未经授权的组访问计数器
`agent_invalid_state_transition_total` - 无效状态转换计数器
`agent_privilege_escalation_attempts_total` - 具有可疑请求的计数器

#### 8.2 日志增强

**请求日志记录：**
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

### 9. 测试策略

#### 9.1 单元测试

**工具过滤逻辑：**
测试组的交集计算
测试基于状态的过滤逻辑
验证默认组和状态的分配
测试通配符组的行为
验证空组的处理
测试组合的组+状态过滤场景

**配置验证：**
测试使用各种组和状态配置加载工具
验证无效的组和状态规范的模式验证
测试与现有配置的向后兼容性
验证状态转换的定义和循环

#### 9.2 集成测试

**代理行为：**
验证代理只看到组+状态过滤的工具
测试使用各种组组合的请求执行
测试代理执行期间的状态转换
验证在没有可用工具时错误处理
测试通过多个状态的工作流程进度

**安全测试：**
测试特权提升预防
验证审计跟踪的准确性
测试网关与用户权限的集成

#### 9.3 完整场景

**具有状态工作流程的多租户使用：**
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

**工作流程状态演进：**
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

### 10. 性能考虑

#### 10.1 工具加载的影响

**配置加载：**
组和状态元数据在启动时加载一次
每个工具的内存开销很小（附加字段）
不会影响工具的初始化时间

**请求处理：**
组+状态过滤的组合在每个请求中执行一次
复杂度为 O(n)，其中 n = 配置的工具数量
状态转换会增加微小的开销（字符串赋值）
对于典型的工具数量（< 100），影响可以忽略不计

#### 10.2 优化策略

**预计算的工具集：**
根据组+状态组合缓存工具集
避免重复过滤常见的组/状态模式
内存与计算之间的权衡，适用于经常使用的组合

**延迟加载：**
仅在需要时才加载工具实现
减少具有许多工具的部署的启动时间
基于组需求的动态工具注册

### 11. 未来增强功能

#### 11.1 动态组分配

**基于上下文的组：**
根据请求上下文将工具分配到组
基于时间的组可用性（仅在工作时间内）
基于负载的组限制（在低使用情况下限制昂贵的工具）

#### 11.2 组层级结构

**嵌套的组结构：**
```json
{
  "knowledge": {
    "read": ["knowledge-query", "entity-search"],
    "write": ["graph-update", "entity-create"]
  }
}
```

#### 11.3 工具推荐

**基于组的建议：**
针对请求类型，推荐最佳工具组。
从使用模式中学习，以改进推荐。
在首选工具不可用时，提供备用组。

### 12. 开放性问题

1. **组验证：** 请求中无效的组名是否应导致硬性错误或警告？

2. **组发现：** 系统是否应提供一个 API 来列出可用的组及其工具？

3. **动态组：** 组是否应在运行时配置，或者仅在启动时配置？

4. **组继承：** 工具是否应从其父类别或实现继承组？

5. **性能监控：** 需要哪些额外的指标来有效跟踪基于组的工具使用情况？

### 13. 结论

工具组系统提供：

**安全性：** 对代理功能进行细粒度的访问控制。
**性能：** 减少工具加载和选择开销。
**灵活性：** 多维工具分类。
**兼容性：** 与现有代理架构无缝集成。

该系统使 TrustGraph 部署能够更好地管理工具访问，提高安全边界，并优化资源利用率，同时与现有的配置和请求完全兼容。
