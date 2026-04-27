---
layout: default
title: "技术规范：Cassandra 配置整合"
parent: "Chinese (Beta)"
---

# 技术规范：Cassandra 配置整合

> **Beta Translation:** This document was translated via Machine Learning and as such may not be 100% accurate. All non-English languages are currently classified as Beta.

**状态：** 草稿
**作者：** 助理
**日期：** 2024-09-03

## 概述

本规范旨在解决 TrustGraph 代码库中 Cassandra 连接参数命名和配置模式的不一致问题。目前，存在两种不同的参数命名方案（`cassandra_*` 与 `graph_*`），这导致了混乱和维护复杂性。

## 问题陈述

当前代码库使用两组不同的 Cassandra 配置参数：

1. **知识/配置/库模块** 使用：
   `cassandra_host` (主机列表)
   `cassandra_user`
   `cassandra_password`

2. **图/存储模块** 使用：
   `graph_host` (单个主机，有时转换为列表)
   `graph_username`
   `graph_password`

3. **命令行暴露不一致：**
   一些处理器（例如，`kg-store`）不将 Cassandra 设置作为命令行参数暴露
   其他处理器以不同的名称和格式暴露这些设置
   帮助文本未反映环境变量的默认值

这两组参数都连接到同一个 Cassandra 集群，但使用不同的命名约定，导致：
用户配置混乱
维护负担增加
文档不一致
可能出现配置错误
在某些处理器中，无法通过命令行覆盖设置

## 解决方案

### 1. 标准化参数名称

所有模块都将使用一致的 `cassandra_*` 参数名称：
`cassandra_host` - 主机列表（内部存储为列表）
`cassandra_username` - 身份验证用户名
`cassandra_password` - 身份验证密码

### 2. 命令行参数

所有处理器都必须通过命令行参数暴露 Cassandra 配置：
`--cassandra-host` - 逗号分隔的主机列表
`--cassandra-username` - 身份验证用户名
`--cassandra-password` - 身份验证密码

### 3. 环境变量回退

如果未显式提供命令行参数，系统将检查环境变量：
`CASSANDRA_HOST` - 逗号分隔的主机列表
`CASSANDRA_USERNAME` - 身份验证用户名
`CASSANDRA_PASSWORD` - 身份验证密码

### 4. 默认值

如果未指定命令行参数或环境变量：
`cassandra_host` 默认为 `["cassandra"]`
`cassandra_username` 默认为 `None` (无身份验证)
`cassandra_password` 默认为 `None` (无身份验证)

### 5. 帮助文本要求

`--help` 输出必须：
显示已设置的环境变量值作为默认值
绝不显示密码值（显示 `****` 或 `<set>` 代替）
在帮助文本中清楚地指示解析顺序

示例帮助输出：
```
--cassandra-host HOST
    Cassandra host list, comma-separated (default: prod-cluster-1,prod-cluster-2)
    [from CASSANDRA_HOST environment variable]

--cassandra-username USERNAME
    Cassandra username (default: cassandra_user)
    [from CASSANDRA_USERNAME environment variable]
    
--cassandra-password PASSWORD  
    Cassandra password (default: <set from environment>)
```

## 实现细节

### 参数解析顺序

对于每个 Cassandra 参数，解析顺序如下：
1. 命令行参数值
2. 环境变量 (`CASSANDRA_*`)
3. 默认值

### 主机参数处理

`cassandra_host` 参数：
命令行接受逗号分隔的字符串：`--cassandra-host "host1,host2,host3"`
环境变量接受逗号分隔的字符串：`CASSANDRA_HOST="host1,host2,host3"`
内部始终存储为列表：`["host1", "host2", "host3"]`
单个主机：`"localhost"` → 转换为 `["localhost"]`
已经是列表：`["host1", "host2"]` → 保持原样

### 认证逻辑

当同时提供 `cassandra_username` 和 `cassandra_password` 时，将使用认证：
```python
if cassandra_username and cassandra_password:
    # Use SSL context and PlainTextAuthProvider
else:
    # Connect without authentication
```

## 需要修改的文件

### 使用 `graph_*` 参数的模块（需要修改）：
`trustgraph-flow/trustgraph/storage/triples/cassandra/write.py`
`trustgraph-flow/trustgraph/storage/objects/cassandra/write.py`
`trustgraph-flow/trustgraph/storage/rows/cassandra/write.py`
`trustgraph-flow/trustgraph/query/triples/cassandra/service.py`

### 使用 `cassandra_*` 参数的模块（需要更新，并使用环境变量回退）：
`trustgraph-flow/trustgraph/tables/config.py`
`trustgraph-flow/trustgraph/tables/knowledge.py`
`trustgraph-flow/trustgraph/tables/library.py`
`trustgraph-flow/trustgraph/storage/knowledge/store.py`
`trustgraph-flow/trustgraph/cores/knowledge.py`
`trustgraph-flow/trustgraph/librarian/librarian.py`
`trustgraph-flow/trustgraph/librarian/service.py`
`trustgraph-flow/trustgraph/config/service/service.py`
`trustgraph-flow/trustgraph/cores/service.py`

### 需要更新的测试文件：
`tests/unit/test_cores/test_knowledge_manager.py`
`tests/unit/test_storage/test_triples_cassandra_storage.py`
`tests/unit/test_query/test_triples_cassandra_query.py`
`tests/integration/test_objects_cassandra_integration.py`

## 实施策略

### 第一阶段：创建通用的配置辅助工具
创建实用函数，以标准化所有处理器中的 Cassandra 配置：

```python
import os
import argparse

def get_cassandra_defaults():
    """Get default values from environment variables or fallback."""
    return {
        'host': os.getenv('CASSANDRA_HOST', 'cassandra'),
        'username': os.getenv('CASSANDRA_USERNAME'),
        'password': os.getenv('CASSANDRA_PASSWORD')
    }

def add_cassandra_args(parser: argparse.ArgumentParser):
    """
    Add standardized Cassandra arguments to an argument parser.
    Shows environment variable values in help text.
    """
    defaults = get_cassandra_defaults()
    
    # Format help text with env var indication
    host_help = f"Cassandra host list, comma-separated (default: {defaults['host']})"
    if 'CASSANDRA_HOST' in os.environ:
        host_help += " [from CASSANDRA_HOST]"
    
    username_help = f"Cassandra username"
    if defaults['username']:
        username_help += f" (default: {defaults['username']})"
        if 'CASSANDRA_USERNAME' in os.environ:
            username_help += " [from CASSANDRA_USERNAME]"
    
    password_help = "Cassandra password"
    if defaults['password']:
        password_help += " (default: <set>)"
        if 'CASSANDRA_PASSWORD' in os.environ:
            password_help += " [from CASSANDRA_PASSWORD]"
    
    parser.add_argument(
        '--cassandra-host',
        default=defaults['host'],
        help=host_help
    )
    
    parser.add_argument(
        '--cassandra-username',
        default=defaults['username'],
        help=username_help
    )
    
    parser.add_argument(
        '--cassandra-password',
        default=defaults['password'],
        help=password_help
    )

def resolve_cassandra_config(args) -> tuple[list[str], str|None, str|None]:
    """
    Convert argparse args to Cassandra configuration.
    
    Returns:
        tuple: (hosts_list, username, password)
    """
    # Convert host string to list
    if isinstance(args.cassandra_host, str):
        hosts = [h.strip() for h in args.cassandra_host.split(',')]
    else:
        hosts = args.cassandra_host
    
    return hosts, args.cassandra_username, args.cassandra_password
```

### 第二阶段：使用 `graph_*` 参数更新模块
1. 将参数名称从 `graph_*` 更改为 `cassandra_*`
2. 将自定义 `add_args()` 方法替换为标准化的 `add_cassandra_args()`
3. 使用通用的配置辅助函数
4. 更新文档字符串

示例转换：
```python
# OLD CODE
@staticmethod
def add_args(parser):
    parser.add_argument(
        '-g', '--graph-host',
        default="localhost",
        help=f'Graph host (default: localhost)'
    )
    parser.add_argument(
        '--graph-username',
        default=None,
        help=f'Cassandra username'
    )

# NEW CODE  
@staticmethod
def add_args(parser):
    FlowProcessor.add_args(parser)
    add_cassandra_args(parser)  # Use standard helper
```

### 第三阶段：使用 `cassandra_*` 参数更新模块
1. 在缺失的地方添加命令行参数支持（例如：`kg-store`）
2. 将现有的参数定义替换为 `add_cassandra_args()`
3. 使用 `resolve_cassandra_config()` 以实现一致的解析
4. 确保一致的主机列表处理

### 第四阶段：更新测试和文档
1. 更新所有测试文件以使用新的参数名称
2. 更新命令行界面 (CLI) 文档
3. 更新 API 文档
4. 添加环境变量文档

## 向后兼容性

为了在过渡期间保持向后兼容性：

1. **弃用警告**，用于 `graph_*` 参数
2. **参数别名** - 初始阶段接受旧名称和新名称
3. **分阶段发布**，在多个版本中进行
4. **文档更新**，包含迁移指南

示例向后兼容代码：
```python
def __init__(self, **params):
    # Handle deprecated graph_* parameters
    if 'graph_host' in params:
        warnings.warn("graph_host is deprecated, use cassandra_host", DeprecationWarning)
        params.setdefault('cassandra_host', params.pop('graph_host'))
    
    if 'graph_username' in params:
        warnings.warn("graph_username is deprecated, use cassandra_username", DeprecationWarning)
        params.setdefault('cassandra_username', params.pop('graph_username'))
    
    # ... continue with standard resolution
```

## 测试策略

1. **单元测试**，用于配置解析逻辑
2. **集成测试**，使用各种配置组合
3. **环境变量测试**
4. **向后兼容性测试**，针对已弃用的参数
5. **Docker Compose 测试**，使用环境变量

## 文档更新

1. 更新所有 CLI 命令文档
2. 更新 API 文档
3. 创建迁移指南
4. 更新 Docker Compose 示例
5. 更新配置参考文档

## 风险与缓解

| 风险 | 影响 | 缓解措施 |
|------|--------|------------|
| 对用户的破坏性更改 | 高 | 实施向后兼容性过渡期 |
| 转换期间的配置混淆 | 中 | 清晰的文档和弃用警告 |
| 测试失败 | 中 | 全面的测试更新 |
| Docker 部署问题 | 高 | 更新所有 Docker Compose 示例 |

## 成功标准

[ ] 所有模块使用一致的 `cassandra_*` 参数名称
[ ] 所有处理器通过命令行参数暴露 Cassandra 设置
[ ] 命令行帮助文本显示环境变量的默认值
[ ] 密码值绝不在帮助文本中显示
[ ] 环境变量回退工作正常
[ ] `cassandra_host` 内部始终被处理为列表
[ ] 至少在 2 个版本中保持向后兼容性
[ ] 所有测试在新配置系统中通过
[ ] 文档已完全更新
[ ] Docker Compose 示例使用环境变量

## 时间线

**第一周：** 实施通用的配置助手，并更新 `graph_*` 模块
**第二周：** 为现有的 `cassandra_*` 模块添加环境变量支持
**第三周：** 更新测试和文档
**第四周：** 集成测试和错误修复

## 未来考虑

考虑将此模式扩展到其他数据库配置（例如，Elasticsearch）
实施配置验证和更好的错误消息
添加对 Cassandra 连接池配置的支持
考虑添加对配置文件支持（.env 文件）
