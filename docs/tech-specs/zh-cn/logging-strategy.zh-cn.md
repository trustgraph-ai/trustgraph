---
layout: default
title: "默认 - INFO 级别，启用 Loki"
parent: "Chinese (Beta)"
---

## TrustGraph 日志策略

## 概述

TrustGraph 使用 Python 内置的 `logging` 模块进行所有日志操作，并具有集中配置以及可选的 Loki 集成，用于日志聚合。 这提供了一种标准且灵活的方式，可在系统的所有组件中进行日志记录。

## 默认配置

### 日志级别
- **默认级别**: `INFO`
- **可通过**: `--log-level` 命令行参数配置
- **选项**: `DEBUG`, `INFO`, `WARNING`, `ERROR`, `CRITICAL`

### 输出目标
1. **控制台 (stdout)**: 始终启用 - 确保与容器化环境兼容
2. **Loki**: 可选的集中式日志聚合 (默认启用，可禁用)

## 集中式日志模块

所有日志配置都由 `trustgraph.base.logging` 模块管理，该模块提供：
- `add_logging_args(parser)` - 添加标准的日志 CLI 参数
- `setup_logging(args)` - 从解析的参数配置日志

该模块用于所有服务器端组件：
- 基于 AsyncProcessor 的服务
- API 网关
- MCP 服务器

## 实现指南

### 1. 日志记录器初始化

每个模块应使用模块的 `__name__` 创建自己的日志记录器：

```python
import logging

logger = logging.getLogger(__name__)
```

日志记录器的名称会自动用作在 Loki 中用于过滤和搜索的标签。

### 2. 服务初始化

所有服务器端服务都通过集中化模块自动获取日志配置：

```python
from trustgraph.base import add_logging_args, setup_logging
import argparse

def main():
    parser = argparse.ArgumentParser()

    # 添加标准的日志参数 (包括 Loki 配置)
    add_logging_args(parser)

    # 添加您自己的服务特定的参数
    parser.add_argument('--port', type=int, default=8080)

    args = parser.parse_args()
    args = vars(args)

    # 提前设置日志
    setup_logging(args)

    # 剩余的服务初始化
    logger = logging.getLogger(__name__)
    logger.info("服务开始...")
```

### 3. 命令行参数

所有服务都支持以下日志参数：

**日志级别:**
```bash
--log-level {DEBUG,INFO,WARNING,ERROR,CRITICAL}
```

**Loki 配置:**
```bash
--loki-enabled              # 启用 Loki (默认)
--no-loki-enabled           # 禁用 Loki
--loki-url URL              # Loki 推送 URL (默认: http://loki:3100/loki/api/v1/push)
--loki-username USERNAME    # 可选身份验证
--loki-password PASSWORD    # 可选身份验证
```

**示例:**
```bash
# 默认 - INFO 级别，启用 Loki

> **Beta Translation:** This document was translated via Machine Learning and as such may not be 100% accurate. All non-English languages are currently classified as Beta.
./my-service

# 调试模式，仅控制台
./my-service --log-level DEBUG --no-loki-enabled

# 自定义 Loki 服务器，带身份验证
./my-service --loki-url http://loki.prod:3100/loki/api/v1/push \
             --loki-username admin --loki-password secret
```

### 4. 环境变量

Loki 配置支持环境变量的后备：

```bash
export LOKI_URL=http://loki.prod:3100/loki/api/v1/push
export LOKI_USERNAME=admin
export LOKI_PASSWORD=secret
```

命令行参数优先于环境变量。

### 5. 日志记录最佳实践

#### 日志级别使用
- **DEBUG**: 用于诊断问题的详细信息 (变量值、函数入口/退出)
- **INFO**: 通用信息消息 (服务启动、配置加载、处理里程碑)
- **WARNING**: 警告消息，用于潜在的危险情况 (弃用功能、可恢复错误)
- **ERROR**: 错误消息，用于严重问题 (失败的操作、异常)
- **CRITICAL**: 关键消息，用于系统故障，需要立即关注

#### 消息格式
```python
# 良好 - 包含上下文
logger.info(f"处理文档: {doc_id}, 大小: {doc_size} 字节")
logger.error(f"无法连接到数据库: {error}", exc_info=True)

# 不好 - 缺少上下文
logger.info("处理文档")
logger.error("连接失败")
```

#### 性能考虑
```python
# 使用延迟格式化进行昂贵的操作
logger.debug("昂贵操作结果: %s", expensive_function())

# 检查日志级别以进行非常昂贵的调试操作
if logger.isEnabledFor(logging.DEBUG):
    debug_data = compute_expensive_debug_info()
    logger.debug(f"调试数据: {debug_data}")
```

### 6. 使用 Loki 的结构化日志记录

对于复杂的结构化数据，可以使用结构化日志记录，并添加额外的标签以供 Loki 使用：

```python
logger.info("请求已处理", extra={
    'tags': {
        'request_id': request_id,
        'user_id': user_id,
        'status': 'success'
    }
})
```

这些标签将作为 Loki 中的可搜索标签：
- `severity` - 日志级别 (DEBUG, INFO, 等)
- `logger` - 模块名称 (来自 `__name__`)

### 7. 异常日志记录

始终包含异常堆栈跟踪：

```python
try:
    process_data()
except Exception as e:
    logger.error(f"无法处理数据: {e}", exc_info=True)
    raise
```

### 8. 异步日志记录的注意事项

日志系统使用非阻塞的队列处理程序进行 Loki 集成：
- 控制台输出是同步的 (快速)
- Loki 输出是异步排队 (500 条消息缓冲区)
- 后台线程处理 Loki 传输
- 没有阻塞主应用程序代码

```python
import asyncio
import logging

async def async_operation():
    logger = logging.getLogger(__name__)
    # 日志记录是线程安全的，不会阻塞异步操作
    logger.info(f"在任务中开始异步操作: {asyncio.current_task().get_name()}")
```

## Loki 集成

### 架构

日志系统使用 Python 内置的 `logging` 模块进行 Loki 集成：
- `python-logging-loki` - 用于 Loki 集成 (可选，如果缺少则回退)

已经在 `trustgraph-base/pyproject.toml` 和 `requirements.txt` 中包含。

### 从 print() 到 logging：
```python
# 之前
print(f"处理文档 {doc_id}")

# 之后
logger = logging.getLogger(__name__)
logger.info(f"处理文档 {doc_id}")
```

## 安全注意事项

- **永远不要记录敏感信息** (密码、API 密钥、个人数据、令牌)
- **清理用户输入** 之前进行日志记录
- **使用占位符** 来记录敏感字段： `user_id=****1234`
- **使用 Loki 身份验证**： 对于生产环境，使用 `--loki-username` 和 `--loki-password`
- **安全传输**： 在生产中使用 HTTPS： `https://loki.prod:3100/loki/api/v1/push`

## 依赖

集中式日志模块需要：
- `python-logging-loki` - 用于 Loki 集成 (可选，如果缺失则回退)
