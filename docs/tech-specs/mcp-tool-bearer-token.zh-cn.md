---
layout: default
title: "MCP 工具承载令牌身份验证规范"
parent: "Chinese (Beta)"
---

# MCP 工具承载令牌身份验证规范

> **Beta Translation:** This document was translated via Machine Learning and as such may not be 100% accurate. All non-English languages are currently classified as Beta.

> **⚠️ 重要提示：仅限单租户环境**
>
> 本规范描述了一种用于 MCP 工具的**基本服务级别身份验证机制**。它**不是**一个完整的身份验证解决方案，**不适用于**以下情况：
> - 多用户环境
> - 多租户部署
> - 联合身份验证
> - 用户上下文传播
> - 基于用户的授权
>
> 此功能为**每个 MCP 工具提供一个静态令牌**，该令牌在所有用户和会话中共享。 如果您需要基于用户的身份验证或基于租户的身份验证，则此功能不适合您。

## 概述
**功能名称**: MCP 工具承载令牌身份验证支持
**作者**: Claude 代码助手
**日期**: 2025-11-11
**状态**: 正在开发中

### 执行摘要

允许 MCP 工具配置指定可选的承载令牌，用于对受保护的 MCP 服务器进行身份验证。 这允许 TrustGraph 安全地调用托管在需要身份验证的服务器上的 MCP 工具，而无需修改代理或工具调用接口。

**重要提示**: 这是一个基本身份验证机制，旨在用于单租户、服务到服务的身份验证场景。 它**不适用于**以下情况：
需要不同用户凭据的多用户环境
需要每个租户隔离的多租户部署
联合身份验证场景
基于用户的身份验证或授权
动态凭据管理或令牌刷新

此功能为每个 MCP 工具配置提供一个静态、系统范围的承载令牌，该令牌在所有用户和该工具的调用中共享。

### 问题陈述

目前，MCP 工具只能连接到公共可访问的 MCP 服务器。 许多生产 MCP 部署需要通过承载令牌进行身份验证以提高安全性。 如果没有身份验证支持：
MCP 工具无法连接到受保护的 MCP 服务器
用户必须要么公开 MCP 服务器，要么实现反向代理
没有一种标准化的方法将凭据传递给 MCP 连接
无法在 MCP 终端节点上强制执行安全最佳实践

### 目标

[ ] 允许 MCP 工具配置指定可选的 `auth-token` 参数
[ ] 更新 MCP 工具服务，使其在连接到 MCP 服务器时使用承载令牌
[ ] 更新 CLI 工具以支持设置/显示身份验证令牌
[ ] 保持与未进行身份验证的 MCP 配置的向后兼容性
[ ] 记录令牌存储的安全注意事项

### 非目标
动态令牌刷新或 OAuth 流程（仅限静态令牌）
存储令牌的加密（配置系统安全性不在范围之内）
替代身份验证方法（基本身份验证、API 密钥等）
令牌验证或到期检查
**基于用户的身份验证**: 此功能**不支持**用户特定的凭据
**多租户隔离**: 此功能**不提供**基于租户的令牌管理
**联合身份验证**: 此功能**不与**身份提供商（SSO、OAuth、SAML 等）集成
**基于上下文的身份验证**: 令牌不是基于用户上下文或会话传递的

## 背景和上下文

### 当前状态
MCP 工具配置存储在 `mcp` 配置组中，具有以下结构：
```json
{
  "remote-name": "tool_name",
  "url": "http://mcp-server:3000/api"
}
```

MCP 工具服务使用 `streamablehttp_client(url)` 连接到服务器，而无需任何身份验证头信息。

### 限制

**当前系统限制：**
1. **不支持身份验证：** 无法连接到需要身份验证的 MCP 服务器。
2. **安全风险：** MCP 服务器必须是公开可访问的，或者仅使用网络级别的安全措施。
3. **生产部署问题：** 无法遵循 API 端点的安全最佳实践。

**此解决方案的限制：**
1. **仅支持单租户：** 每个 MCP 工具只有一个静态令牌，所有用户共享该令牌。
2. **不支持按用户身份验证：** 无法以不同的用户身份进行身份验证，也无法传递用户上下文。
3. **不支持多租户：** 无法按租户或组织隔离凭据。
4. **仅支持静态令牌：** 不支持令牌刷新、轮换或过期处理。
5. **服务级别身份验证：** 仅对 TrustGraph 服务进行身份验证，而不是对单个用户进行身份验证。
6. **共享安全上下文：** 对 MCP 工具的所有调用都使用相同的凭据。

### 使用场景适用性

**✅ 适用场景：**
单租户 TrustGraph 部署。
服务到服务身份验证（TrustGraph → MCP 服务器）。
开发和测试环境。
TrustGraph 系统访问的内部 MCP 工具。
所有用户共享相同 MCP 工具访问级别的场景。
静态、长期有效的服务凭据。

**❌ 不适用场景：**
需要按用户身份验证的多用户系统。
需要租户隔离的多租户 SaaS 部署。
联合身份验证场景（SSO、OAuth、SAML）。
需要将用户上下文传播到 MCP 服务器的系统。
需要动态令牌刷新或短生命周期的令牌的环境。
不同的用户需要不同权限级别的应用程序。
用户级别审计跟踪的合规性要求。

**示例适用场景：**
单个组织的 TrustGraph 部署，其中所有员工都使用相同的内部 MCP 工具（例如，公司数据库查询）。MCP 服务器需要身份验证以防止外部访问，但所有内部用户都具有相同的访问级别。

**示例不适用场景：**
一个多租户 TrustGraph SaaS 平台，其中租户 A 和租户 B 需要访问各自隔离的 MCP 服务器，并使用不同的凭据。此功能不支持按租户管理令牌。

### 相关组件
**trustgraph-flow/trustgraph/agent/mcp_tool/service.py**: MCP 工具调用服务。
**trustgraph-cli/trustgraph/cli/set_mcp_tool.py**: 用于创建/更新 MCP 配置的 CLI 工具。
**trustgraph-cli/trustgraph/cli/show_mcp_tools.py**: 用于显示 MCP 配置的 CLI 工具。
**MCP Python SDK**: `streamablehttp_client` from `mcp.client.streamable_http`

## 要求

### 功能性要求

1. **MCP 配置身份验证令牌：** MCP 工具配置必须支持一个可选的 `auth-token` 字段。
2. **Bearer 令牌使用：** 当配置了 auth-token 时，MCP 工具服务必须发送 `Authorization: Bearer {token}` 头信息。
3. **CLI 支持：** `tg-set-mcp-tool` 必须接受一个可选的 `--auth-token` 参数。
4. **令牌显示：** `tg-show-mcp-tools` 必须指示是否配置了 auth-token（出于安全考虑，已屏蔽）。
5. **向后兼容性：** 现有不带 auth-token 的 MCP 工具配置必须继续正常工作。

### 非功能性要求
1. **向后兼容性：** 对于现有的 MCP 工具配置，不得有任何破坏性更改。
2. **性能：** 对 MCP 工具的调用不会产生任何显著的性能影响。
3. **安全性：** 令牌存储在配置中（请注意安全隐患）。

### 用户故事

1. 作为 **DevOps 工程师**，我希望配置 MCP 工具的 bearer 令牌，以便我可以保护 MCP 服务器端点。
2. 作为 **CLI 用户**，我希望在创建 MCP 工具时设置身份验证令牌，以便我可以连接到受保护的服务器。
3. 作为 **系统管理员**，我希望查看哪些 MCP 工具配置了身份验证，以便我可以审计安全设置。

## 设计

### 高级架构
扩展 MCP 工具配置和服务以支持 bearer 令牌身份验证：
1. 向 MCP 工具配置模式添加一个可选的 `auth-token` 字段。
2. 修改 MCP 工具服务以读取 auth-token 并将其传递给 HTTP 客户端。
3. 更新 CLI 工具以支持设置和显示身份验证令牌。
4. 记录安全注意事项和最佳实践。

### 配置模式

**当前模式：**
```json
{
  "remote-name": "tool_name",
  "url": "http://mcp-server:3000/api"
}
```

**新的模式**（带可选的认证令牌）：
```json
{
  "remote-name": "tool_name",
  "url": "http://mcp-server:3000/api",
  "auth-token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9..."
}
```

**字段描述**:
`remote-name` (可选): MCP 服务器使用的名称（默认为配置键）
`url` (必需): MCP 服务器端点 URL
`auth-token` (可选): 用于身份验证的 Bearer token

### 数据流

1. **配置存储**: 用户运行 `tg-set-mcp-tool --id my-tool --tool-url http://server/api --auth-token xyz123`
2. **配置加载**: MCP 工具服务通过 `on_mcp_config()` 回调接收配置更新
3. **工具调用**: 当工具被调用时：
   服务从配置中读取 `auth-token`（如果存在）
   创建 headers 字典：`{"Authorization": "Bearer {token}"}`
   将 headers 传递给 `streamablehttp_client(url, headers=headers)`
   MCP 服务器验证 token 并处理请求

### API 变更
没有外部 API 变更，仅为配置模式扩展。

### 组件详情

#### 组件 1: service.py (MCP 工具服务)
**文件**: `trustgraph-flow/trustgraph/agent/mcp_tool/service.py`

**目的**: 在远程服务器上调用 MCP 工具

**所需变更**（在 `invoke_tool()` 方法中）：
1. 检查 `auth-token` 是否在 `self.mcp_services[name]` 配置中
2. 如果 token 存在，则构建包含 Authorization header 的 headers 字典
3. 将 headers 传递给 `streamablehttp_client(url, headers=headers)`

**当前代码**（42-89 行）：
```python
async def invoke_tool(self, name, parameters):
    try:
        if name not in self.mcp_services:
            raise RuntimeError(f"MCP service {name} not known")
        if "url" not in self.mcp_services[name]:
            raise RuntimeError(f"MCP service {name} URL not defined")

        url = self.mcp_services[name]["url"]

        if "remote-name" in self.mcp_services[name]:
            remote_name = self.mcp_services[name]["remote-name"]
        else:
            remote_name = name

        logger.info(f"Invoking {remote_name} at {url}")

        # Connect to a streamable HTTP server
        async with streamablehttp_client(url) as (
                read_stream,
                write_stream,
                _,
        ):
            # ... rest of method
```

**修改后的代码**:
```python
async def invoke_tool(self, name, parameters):
    try:
        if name not in self.mcp_services:
            raise RuntimeError(f"MCP service {name} not known")
        if "url" not in self.mcp_services[name]:
            raise RuntimeError(f"MCP service {name} URL not defined")

        url = self.mcp_services[name]["url"]

        if "remote-name" in self.mcp_services[name]:
            remote_name = self.mcp_services[name]["remote-name"]
        else:
            remote_name = name

        # Build headers with optional bearer token
        headers = {}
        if "auth-token" in self.mcp_services[name]:
            token = self.mcp_services[name]["auth-token"]
            headers["Authorization"] = f"Bearer {token}"

        logger.info(f"Invoking {remote_name} at {url}")

        # Connect to a streamable HTTP server with headers
        async with streamablehttp_client(url, headers=headers) as (
                read_stream,
                write_stream,
                _,
        ):
            # ... rest of method (unchanged)
```

#### 组件 2: set_mcp_tool.py (命令行配置工具)
**文件**: `trustgraph-cli/trustgraph/cli/set_mcp_tool.py`

**目的**: 创建/更新 MCP 工具配置

**所需更改**:
1. 向 argparse 添加 `--auth-token` 可选参数
2. 在提供时，将 `auth-token` 包含在配置 JSON 中

**当前参数**:
`--id` (必需): MCP 工具标识符
`--remote-name` (可选): 远程 MCP 工具名称
`--tool-url` (必需): MCP 工具 URL 端点
`-u, --api-url` (可选): TrustGraph API URL

**新参数**:
`--auth-token` (可选): 用于身份验证的 Bearer token

**修改后的配置构建**:
```python
# Build configuration object
config = {
    "url": args.tool_url,
}

if args.remote_name:
    config["remote-name"] = args.remote_name

if args.auth_token:
    config["auth-token"] = args.auth_token

# Store configuration
api.config().put([
    ConfigValue(type="mcp", key=args.id, value=json.dumps(config))
])
```

#### 组件 3：show_mcp_tools.py (命令行显示工具)
**文件**: `trustgraph-cli/trustgraph/cli/show_mcp_tools.py`

**目的**: 显示 MCP 工具的配置

**需要修改的内容**:
1. 在输出表中添加 "Auth" 列
2. 根据是否存在 auth-token 显示 "是" 或 "否"
3. 不要显示实际的 token 值（出于安全考虑）

**当前输出**:
```
ID          Remote Name    URL
----------  -------------  ------------------------
my-tool     my-tool        http://server:3000/api
```

**新的输出：**
```
ID          Remote Name    URL                      Auth
----------  -------------  ------------------------ ------
my-tool     my-tool        http://server:3000/api   Yes
other-tool  other-tool     http://other:3000/api    No
```

#### 组件 4：文档
**文件**: `docs/cli/tg-set-mcp-tool.md`

**需要修改的内容**:
1. 文档新的 `--auth-token` 参数
2. 提供带有身份验证的示例用法
3. 文档安全注意事项

## 实施计划

### 第一阶段：创建技术规范
[x] 编写全面的技术规范，记录所有更改

### 第二阶段：更新 MCP 工具服务
[ ] 修改 `invoke_tool()` 中的 `service.py` 以从配置文件读取 auth-token
[ ] 构建 headers 字典并传递给 `streamablehttp_client`
[ ] 使用经过身份验证的 MCP 服务器进行测试

### 第三阶段：更新 CLI 工具
[ ] 向 `set_mcp_tool.py` 添加 `--auth-token` 参数
[ ] 在配置 JSON 中包含 auth-token
[ ] 向 `show_mcp_tools.py` 的输出添加 "Auth" 列
[ ] 测试 CLI 工具的更改

### 第四阶段：更新文档
[ ] 在 `tg-set-mcp-tool.md` 中记录 `--auth-token` 参数
[ ] 添加安全注意事项部分
[ ] 提供示例用法

### 第五阶段：测试
[ ] 测试 MCP 工具是否能够使用 auth-token 成功连接
[ ] 测试向后兼容性（没有 auth-token 的工具仍然可以工作）
[ ] 测试 CLI 工具是否能够正确接受和存储 auth-token
[ ] 测试 "show" 命令是否能够正确显示身份验证状态

### 代码更改摘要
| 文件 | 更改类型 | 行数 | 描述 |
|------|------------|-------|-------------|
| `service.py` | 修改 | ~52-66 | 添加 auth-token 读取和 header 构建 |
| `set_mcp_tool.py` | 修改 | ~30-60 | 添加 --auth-token 参数和配置存储 |
| `show_mcp_tools.py` | 修改 | ~40-70 | 向显示添加 Auth 列 |
| `tg-set-mcp-tool.md` | 修改 | 各种 | 文档新的参数 |

## 测试策略

### 单元测试
**Auth Token 读取**: 测试 `invoke_tool()` 是否能够正确从配置文件读取 auth-token
**Header 构建**: 测试 Authorization header 是否能够使用 Bearer 前缀正确构建
**向后兼容性**: 测试没有 auth-token 的工具是否能够正常工作
**CLI 参数解析**: 测试 `--auth-token` 参数是否能够正确解析

### 集成测试
**经过身份验证的连接**: 测试 MCP 工具服务是否能够连接到经过身份验证的服务器
**端到端**: 测试 CLI → 配置文件存储 → 服务调用，并使用 auth token
**不需要 Token**: 测试连接到未经过身份验证的服务器是否仍然可以工作

### 手动测试
**真实的 MCP 服务器**: 使用需要 bearer token 身份验证的实际 MCP 服务器进行测试
**CLI 工作流程**: 测试完整的流程：使用 auth 设置工具 → 调用工具 → 验证成功
**显示屏蔽**: 验证身份验证状态显示，但 token 值不暴露

## 迁移和发布

### 迁移策略
不需要迁移 - 这是一个纯粹的附加功能：
现有的 MCP 工具配置，如果没有 `auth-token`，可以继续正常工作
新的配置可以选择包含 `auth-token` 字段
CLI 工具接受，但不要求 `--auth-token` 参数

### 发布计划
1. **第一阶段**: 将核心服务更改部署到开发/测试环境
2. **第二阶段**: 部署 CLI 工具更新
3. **第三阶段**: 更新文档
4. **第四阶段**: 生产发布，并进行监控

### 回滚计划
核心更改是向后兼容的 - 现有的工具不受影响
如果出现问题，可以通过删除 header 构建逻辑来禁用身份验证 token 处理
CLI 更改是独立的，并且可以单独回滚

## 安全注意事项

### ⚠️ 关键限制：仅支持单租户身份验证

**此身份验证机制不适用于多用户或多租户环境。**

**共享凭据**: 所有用户和调用都共享每个 MCP 工具的相同 token
**没有用户上下文**: MCP 服务器无法区分不同的 TrustGraph 用户
**没有租户隔离**: 所有租户共享每个 MCP 工具的相同凭据
**审计跟踪限制**: MCP 服务器日志显示来自相同凭据的所有请求
**权限范围**: 无法为不同的用户强制执行不同的权限级别

**不要使用此功能，如果：**
您的 TrustGraph 部署服务于多个组织（多租户）
您需要跟踪哪些用户访问了哪些 MCP 工具
不同的用户需要不同的权限级别
您需要遵守用户级别的审计要求
您的 MCP 服务器强制执行每个用户的速率限制或配额

**多用户/多租户场景的替代方案：**
通过自定义头部实现用户上下文传播
为每个租户部署独立的 TrustGraph 实例
使用网络级别隔离（VPCs、服务网格）
实现一个代理层，该层处理每个用户的身份验证

### 令牌存储
**风险：** 身份验证令牌以明文形式存储在配置系统中

**缓解措施：**
记录令牌以明文形式存储
尽可能推荐使用短寿命令牌
推荐对配置存储进行适当的访问控制
考虑未来增强功能，用于加密令牌存储

### 令牌泄露
**风险：** 令牌可能出现在日志或 CLI 输出中

**缓解措施：**
不要记录令牌值（仅记录“身份验证已配置：是/否”）
CLI 显示命令仅显示屏蔽状态，不显示实际令牌
不要将令牌包含在错误消息中

### 网络安全
**风险：** 令牌通过未加密的连接传输

**缓解措施：**
记录推荐使用 HTTPS URL 进行 MCP 服务器访问
警告用户使用 HTTP 传输的明文风险

### 配置访问
**风险：** 未授权访问配置系统会暴露令牌

**缓解措施：**
记录保护配置系统访问的重要性
推荐对配置访问采用最小权限原则
考虑对配置更改进行审计日志记录（未来增强功能）

### 多用户环境
**风险：** 在多用户部署中，所有用户共享相同的 MCP 凭据

**风险理解：**
用户 A 和用户 B 在访问 MCP 工具时都使用相同的令牌
MCP 服务器无法区分不同的 TrustGraph 用户
没有办法强制执行每个用户的权限或速率限制
MCP 服务器上的审计日志显示来自相同凭据的所有请求
如果一个用户的会话被盗，攻击者将拥有与所有用户相同的 MCP 访问权限

**这不是一个错误 - 这是一个该设计的基本限制。**

## 性能影响
**最小开销：** 头部构建添加了可忽略的处理时间
**网络影响：** 额外的 HTTP 头部增加了每个请求约 50-200 字节
**内存使用：** 存储在配置中的令牌字符串会增加可忽略的内存

## 文档

### 用户文档
[ ] 使用 `--auth-token` 参数更新 `tg-set-mcp-tool.md`
[ ] 添加安全注意事项部分
[ ] 提供使用 bearer 令牌的示例
[ ] 记录令牌存储的影响

### 开发人员文档
[ ] 在 `service.py` 中添加身份验证令牌处理的内联注释
[ ] 记录头部构建逻辑
[ ] 更新 MCP 工具配置模式文档

## 开放问题
1. **令牌加密：** 我们是否应该在配置系统中实现加密令牌存储？
2. **令牌刷新：** 未来是否支持 OAuth 刷新流程或令牌轮换？
3. **替代身份验证方法：** 我们是否应该支持 Basic 身份验证、API 密钥或其他方法？

## 考虑过的替代方案

1. **环境变量用于令牌：** 将令牌存储在环境变量中而不是配置中
   **已拒绝：**  complicates deployment and configuration management (使部署和配置管理复杂化)

2. **单独的密钥存储：** 使用专用的密钥管理系统
   **推迟：** Out of scope for initial implementation, consider future enhancement (超出初始实现的范围，考虑未来增强)

3. **多种身份验证方法：** 支持 Basic、API 密钥、OAuth 等。
   **已拒绝：** Bearer tokens cover most use cases, keep initial implementation simple (Bearer 令牌涵盖大多数用例，保持初始实现的简单性)

4. **加密令牌存储：** 在配置系统中加密令牌
   **推迟：** Configuration system security is broader concern, defer to future work (配置系统安全是一个更广泛的问题，推迟到未来工作)

5. **按调用令牌：** 允许在调用时传递令牌
   **已拒绝：** Violates separation of concerns, agent shouldn't handle credentials (违反了关注点分离，代理不应处理凭据)

## 引用
[MCP 协议规范](https://github.com/modelcontextprotocol/spec)
[HTTP Bearer 身份验证 (RFC 6750)](https://tools.ietf.org/html/rfc6750)
[Current MCP Tool Service](../trustgraph-flow/trustgraph/agent/mcp_tool/service.py)
[MCP 工具参数规范](./mcp-tool-arguments.md)

## 附录

### 用法示例

**设置带有身份验证的 MCP 工具：**
```bash
tg-set-mcp-tool \
  --id secure-tool \
  --tool-url https://secure-server.example.com/mcp \
  --auth-token eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...
```

**展示 MCP 工具：**
```bash
tg-show-mcp-tools

ID            Remote Name   URL                                    Auth
-----------   -----------   ------------------------------------   ------
secure-tool   secure-tool   https://secure-server.example.com/mcp  Yes
public-tool   public-tool   http://localhost:3000/mcp              No
```

### 配置示例

**存储在配置系统中**:
```json
{
  "type": "mcp",
  "key": "secure-tool",
  "value": "{\"url\": \"https://secure-server.example.com/mcp\", \"auth-token\": \"eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...\"}"
}
```

### 安全最佳实践

1. **使用 HTTPS**: 始终为具有身份验证的 MCP 服务器使用 HTTPS URL。
2. **短生命周期令牌**: 尽可能使用具有过期时间的令牌。
3. **最小权限**: 授予令牌最低要求的权限。
4. **访问控制**: 限制对配置系统的访问。
5. **令牌轮换**: 定期轮换令牌。
6. **审计日志记录**: 监控配置更改以检测安全事件。
