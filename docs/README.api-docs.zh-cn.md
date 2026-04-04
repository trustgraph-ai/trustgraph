# 自动生成文档

## REST 和 WebSocket API 文档

- `specs/build-docs.sh` - 从 OpenAPI 和 AsyncAPI 规范生成 REST 和 WebSocket 文档。

## Python API 文档

Python API 文档是从 docstrings 使用自定义 Python 脚本生成的，该脚本会反向解析 `trustgraph.api` 包。

### 预先条件

`trustgraph` 包必须可导入。 如果您在开发环境中工作，请执行以下操作：

```bash
cd trustgraph-base
pip install -e .
```

### 生成文档

从 `docs` 目录：

```bash
cd docs
python3 generate-api-docs.py > python-api.md
```

这将生成一个包含完整 API 文档的单个 Markdown 文件，其中包含：
- 安装和快速入门指南
- 每个类/类型的导入语句
- 完整的 docstrings（包含示例）
- 按类别组织的目录

### 文档风格

所有 docstrings 均遵循 Google 风格：
- 简短的一行摘要
- 详细描述
- 参数描述的 Args 部分
- Returns 部分
- Raises 部分（如果适用）
- 带有正确语法高亮的代码块（示例）

生成的文档显示了用户从 `trustgraph.api` 中导入的公共 API，而无需暴露内部模块结构。