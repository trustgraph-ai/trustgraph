---
layout: default
title: "更高级的 CLI 技术规格"
parent: "Chinese (Beta)"
---

# 更高级的 CLI 技术规格

> **Beta Translation:** This document was translated via Machine Learning and as such may not be 100% accurate. All non-English languages are currently classified as Beta.

## 概述

该规范描述了 TrustGraph 的增强型命令行配置功能，允许用户通过精细的 CLI 命令来管理单个配置项。 该集成支持四个主要用例：

1.  **列出配置项**: 显示特定类型的配置键
2.  **获取配置项**: 获取特定配置值
3.  **设置配置项**: 设置或更新单个配置项
4.  **删除配置项**: 删除特定配置项

## 目标

-   **精细控制**: 能够管理单个配置项，而不是批量操作
-   **基于类型的列出**: 允许用户按类型探索配置项
-   **单个项操作**: 提供获取/设置/删除单个配置项的命令
-   **API 集成**: 利用现有的 Config API 进行所有操作
-   **一致的 CLI 模式**: 遵循 TrustGraph 的标准 CLI 约定和模式
-   **错误处理**: 提供无效操作的清晰错误消息
-   **JSON 输出**: 支持结构化输出，用于程序化使用
-   **文档**: 包含全面的帮助和用法示例

## 背景

目前，TrustGraph 通过 Config API 和一个名为 `tg-show-config` 的单一 CLI 命令来管理配置。 该命令显示整个配置。 虽然这对于查看配置有效，但缺乏精细的管理功能。

目前存在以下限制：
-   无法从 CLI 列出按类型配置项
-   没有 CLI 命令用于检索特定配置值
-   没有 CLI 命令用于设置单个配置项
-   没有 CLI 命令用于删除特定配置项

该规范通过添加四个新的 CLI 命令来解决这些问题，从而提供精细的配置管理。 通过将单个 Config API 操作暴露到 CLI 命令中，TrustGraph 可以：
-   启用脚本化的配置管理
-   允许用户按类型探索配置结构
-   支持有针对性的配置更新
-   提供精细的配置控制

## 技术设计

### 架构

增强的 CLI 配置需要以下技术组件：

1.  **tg-list-config-items**
    -   列出指定类型的配置键
    -   调用 Config.list(type) API 方法
    -   输出配置键列表

    模块：`trustgraph.cli.list_config_items`

2.  **tg-get-config-item**
    -   检索特定配置项
    -   调用 Config.get(keys) API 方法
    -   以 JSON 格式输出配置值

    模块：`trustgraph.cli.get_config_item`

3.  **tg-put-config-item**
    -   设置或更新配置项
    -   调用 Config.put(values) API 方法
    -   接受类型、键和值参数

    模块：`trustgraph.cli.put_config_item`

4.  **tg-delete-config-item**
    -   删除配置项
    -   调用 Config.delete(keys) API 方法
    -   接受类型和键参数

    模块：`trustgraph.cli.delete_config_item`

### 数据模型

#### ConfigKey 和 ConfigValue

这些命令使用来自 `trustgraph.api.types` 的现有数据结构：

```python
@dataclasses.dataclass
class ConfigKey:
    type : str
    key : str

@dataclasses.dataclass
class ConfigValue:
    type : str
    key : str
    value : str
```

这种方法允许：
-   在 CLI 和 API 中保持数据的一致性
-   类型安全的配置操作
-   结构化输入/输出格式
-   与现有的 Config API 集成

### CLI 命令规范

#### tg-list-config-items
```bash
tg-list-config-items --type <config-type> [--format text|json] [--api-url <url>]
```
-   **目的**: 列出给定类型的所有配置键
-   **API 调用**: `Config.list(type)`
-   **输出**:
    -   `text` (默认): 键按换行分隔
    -   `json`: 键的 JSON 数组

#### tg-get-config-item
```bash
tg-get-config-item --type <type> --key <key> [--format text|json] [--api-url <url>]
```
-   **目的**: 获取特定配置项
-   **API 调用**: `Config.get([ConfigKey(type, key)])`
-   **输出**:
    -   `text` (默认): 原始字符串值
    -   `json`: JSON 编码的字符串值

#### tg-put-config-item
```bash
tg-put-config-item --type <type> --key <key> --value <value> [--api-url <url>]
tg-put-config-item --type <type> --key <key> --stdin [--api-url <url>]
```
-   **目的**: 设置或更新配置项
-   **API 调用**: `Config.put([ConfigValue(type, key, value)])`
-   **输入选项**:
    -   `--value <字符串>`: 直接在命令行中提供的字符串值
    -   `--stdin`: 从标准输入读取整个输入作为配置值
    -   标准输入读取为原始文本 (保留换行符、空格等)
    -   支持通过文件、命令或交互式输入

#### tg-delete-config-item
```bash
tg-delete-config-item --type <type> --key <key> [--api-url <url>]
```
-   **目的**: 删除配置项
-   **API 调用**: `Config.delete([ConfigKey(type, key)])`
-   **输出**: 成功确认

### 实现细节

所有命令都遵循 TrustGraph 的标准 CLI 模式：
-   使用 `argparse` 进行命令行参数解析
-   导入和使用 `trustgraph.api.Api` 进行后端通信
-   遵循现有 CLI 命令的相同错误处理模式
-   支持标准 `--api-url` 参数，用于配置 API 端点
-   提供描述性的帮助文本和用法示例

#### 输出格式处理

**文本格式 (默认)**:
-   `tg-list-config-items`: 键按新行分隔，纯文本
-   `tg-get-config-item`: 原始字符串值，无引号或编码

**JSON 格式**:
-   `tg-list-config-items`: 字符串数组 `["key1", "key2", "key3"]`
-   `tg-get-config-item`: JSON 编码的字符串值 `"实际字符串值"`

#### 输入处理

**tg-put-config-item** 支持两种互斥的输入方法：
-   `--value <字符串>`: 命令行中的直接字符串值
-   `--stdin`: 从标准输入读取整个输入作为配置值
-   标准输入读取为原始文本 (保留换行符、空格等)
-   支持通过文件、命令或交互式输入

## 安全性

-   如果配置项包含敏感信息，如何安全地处理这些信息？
-   如何验证用户输入，以防止恶意攻击？
-   如何控制对配置项的访问权限？

## 开放问题

-   是否应该支持命令以批量操作 (多个键) 之外的单个项？
-   成功确认消息应该使用哪种格式？
-   用户应该如何发现和使用配置类型？
