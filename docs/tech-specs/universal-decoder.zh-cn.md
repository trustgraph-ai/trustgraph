# 通用文档解码器

## 概述

一个由 `unstructured` 驱动的通用文档解码器，它支持通过单个服务处理各种常见的文档格式。该服务具有完整的溯源功能和库管理员集成，记录源位置作为知识图谱元数据，从而实现端到端的可追溯性。

## 问题

目前，TrustGraph 仅有一个用于 PDF 文件的解码器。支持其他格式（DOCX、XLSX、HTML、Markdown、纯文本、PPTX 等）需要要么为每种格式编写新的解码器，要么采用一个通用的提取库。每种格式的结构都不同——有些是基于页面的，有些不是——并且溯源链必须记录每个提取的文本片段在原始文档中的位置。

## 解决方案

### 库：`unstructured`

使用 `unstructured.partition.auto.partition()` 函数，该函数可以自动检测格式（根据 MIME 类型或文件扩展名），并提取结构化元素（标题、正文、表格、列表项等）。每个元素都包含元数据，包括：

- `page_number`（对于基于页面的格式，如 PDF、PPTX）
- `element_id`（每个元素唯一）
- `coordinates`（PDF 文件的边界框）
- `text`（提取的文本内容）
- `category`（元素类型：标题、正文、表格等）

### 元素类型

`unstructured` 提取文档中的各种类型的元素，每个元素都有一个类别和相关的元数据：

**文本元素：**
- `Title` — 段落标题
- `NarrativeText` — 正文段落
- `ListItem` — 项目符号/编号列表项
- `Header`, `Footer` — 页面页眉/页脚
- `FigureCaption` — 图形/图像的标题
- `Formula` — 数学表达式
- `Address`, `EmailAddress` — 联系信息
- `CodeSnippet` — 代码块（来自 Markdown）

**表格：**
- `Table` — 结构化的表格数据。`unstructured` 提供了 `element.text`（纯文本）和 `element.metadata.text_as_html`（完整的 HTML `<table>` 标签，保留了行、列和标题）。对于具有显式表格结构的格式（DOCX、XLSX、HTML），提取的可靠性很高。对于 PDF 文件，表格检测依赖于 `hi_res` 策略和布局分析。

**图像：**
- `Image` — 检测到的嵌入图像（需要 `hi_res` 策略）。如果设置 `extract_image_block_to_payload=True`，则将图像数据作为 base64 编码的字符串返回到 `element.metadata.image_base64` 中。图像中的 OCR 文本位于 `element.text` 中。

### 表格处理

表格是主要的输出。当解码器遇到 `Table` 元素时，它会保留 HTML 结构，而不是将其扁平化为纯文本。这为下游的 LLM 提取器提供了更好的输入，以便从表格数据中提取结构化知识。

页面/部分文本的组装方式如下：
- 文本元素：纯文本，用换行符连接
- 表格元素：来自 `text_as_html` 的 HTML 表格标记，并用 `<table>` 标记包装，以便 LLM 区分表格和正文。

例如，一个页面包含标题、段落和表格，其内容如下：

```
Financial Overview

Revenue grew 15% year-over-year driven by enterprise adoption.

<table>
<tr><th>Quarter</th><th>Revenue</th><th>Growth</th></tr>
<tr><td>Q1</td><td>$12M</td><td>12%</td></tr>
<tr><td>Q2</td><td>$14M</td><td>17%</td></tr>
</table>
```

这在分块和提取流水线中保留了表格结构，LLM 可以直接从结构化单元格中提取关系，而无需猜测列的对齐方式。

### 图像处理

图像会被提取并存储在库管理员中，作为具有 `document_type="image"` 和 `urn:image:{uuid}` ID 的子文档。它们会生成带有类型 `tg:Image` 的溯源三元组，并通过 `prov:wasDerivedFrom` 链接到其父页面/部分。图像元数据（坐标、尺寸、`element_id`）会记录在溯源信息中。

**重要的是，图像不会作为 `TextDocument` 输出。** 它们仅被存储，不会被发送到分块器或任何文本处理流水线。这是故意的：

1. 尚未建立图像处理流水线（视觉模型集成是未来的工作）。
2. 将 base64 编码的图像数据或 OCR 片段馈送到文本提取流水线会产生无效的知识图谱三元组。

图像也被排除在组装的页面文本之外。当连接一个页面/部分的元素文本时，任何 `Image` 元素都会被静默地跳过。溯源链会记录图像的存在以及它们在文档中出现的位置，以便在将来的图像处理流水线中可以拾取它们，而无需重新导入文档。

#### 未来工作

- 将 `tg:Image` 实体路由到视觉模型，用于描述、图表解释或图表数据提取。
- 将图像描述存储为文本子文档，这些子文档会馈送到标准的 chunking/提取流水线。
- 通过溯源将提取的知识链接回源图像。

### 部分策略

对于基于页面的格式（PDF、PPTX、XLSX），元素始终首先按页面分组。对于非基于页面的格式（DOCX、HTML、Markdown 等），解码器需要一种策略来将文档拆分为多个部分。这可以通过运行时配置的 `--section-strategy` 参数进行配置。

每种策略都是一个分组函数，作用于 `unstructured` 元素的列表。输出是一个元素组的列表；其余流水线（文本组装、库管理员存储、溯源、`TextDocument` 输出）与策略无关。

#### `whole-document` (默认)

将整个文档作为一个单独的部分输出。由下游的分块器处理所有拆分。

- 最简单的方案，作为基线。
- 对于大型文件，可能会生成非常大的 `TextDocument`，但分块器会处理这种情况。
- 当希望每个部分包含最大的上下文时，使用此选项。

#### `heading`

在标题元素（`Title`）处进行拆分。每个部分是一个标题以及直到下一个相同或更高级别的标题的所有内容。嵌套的标题会创建嵌套的部分。

- 生成具有主题相关性的单元。
- 适用于结构化文档（报告、手册、规范）。
- 向提取 LLM 提供标题上下文以及内容。
- 如果未找到标题，则回退到 `whole-document`。

#### `element-type`

当元素类型发生显着变化时进行拆分，特别是，从正文文本和表格之间的转换开始一个新的部分。连续的相同宽泛类别的元素（文本、文本、文本或表格、表格、表格）保持分组。

- 保持表格作为独立的部分。
- 适用于具有混合内容的文档（包含数据表格的报告）。
- 表格会获得专门的提取关注。

#### `count`

每部分包含固定数量的元素。可以通过 `--section-element-count` 参数进行配置（默认：20）。

- 简单且可预测。
- 不尊重文档结构。
- 用作回退选项或用于实验。

#### `size`

持续累积元素，直到达到字符限制，然后开始一个新的部分。尊重元素边界，绝不会在元素内部进行拆分。可以通过 `--section-max-size` 参数进行配置（默认：4000 个字符）。

- 生成大致均匀大小的部分。
- 尊重元素边界（与下游分块器不同）。
- 在结构和大小控制之间取得良好的平衡。
- 如果单个元素超过限制，则它会成为其自己的部分。

#### 基于页面的格式交互

对于基于页面的格式，页面分组始终具有优先性。部分策略可以选择性地在非常大的页面内部应用（例如，一个包含非常大的表格的 PDF 页面），由 `--section-within-pages` 参数控制（默认：false）。当设置为 false 时，每个页面始终是一个部分，无论其大小如何。

### 格式检测

解码器需要知道文档的 MIME 类型，以便将其传递给 `unstructured` 的 `partition()` 函数。有两种方法：

- **库管理员路径**（设置了 `document_id`）：首先从库管理员中获取文档元数据，这会提供 `kind`（MIME 类型），然后获取文档内容。这需要两次库管理员调用，但元数据获取是轻量级的。
- **内联路径**（后备方案，设置了 `data`）：没有关于消息的元数据。使用 `python-magic` 从内容字节中检测格式，作为后备方案。

不需要对 `Document` 模式进行任何更改，因为库管理员已经存储了 MIME 类型。

### 架构

一个名为 `universal-decoder` 的单个服务，该服务：

1. 接收一个 `Document` 消息（内联或通过库管理员引用）。
2. 如果使用库管理员路径：获取文档元数据（获取 MIME 类型），然后获取内容。如果使用内联路径：使用 `python-magic` 从内容字节检测格式。
3. 调用 `partition()` 函数以提取元素。
4. 按以下方式对元素进行分组：对于基于页面的格式，按页面分组；对于非基于页面的格式，按配置的策略分组。
5. 对于每个页面/部分：
   - 生成一个 `urn:page:{uuid}` 或 `urn:section:{uuid}` ID。
   - 组装页面文本：正文作为纯文本，表格作为 HTML，图像被跳过。
   - 计算每个元素在页面文本中的字符偏移量。
   - 保存到库管理员中作为子文档。
   - 计算带有位置元数据的溯源三元组。
   - 将 `TextDocument` 发送到下游进行分块。
6. 对于每个图像元素：
   - 生成一个 `urn:image:{uuid}` ID。
   - 将图像数据保存到库管理员中作为子文档。
   - 计算溯源三元组（仅存储，不发送到下游）。

### 格式处理

| 格式      | MIME 类型                                  | 基于页面 | 备注                                       |
|-----------|--------------------------------------------|----------|--------------------------------------------|
| PDF       | `application/pdf`                         | 是       | 按页面分组                                   |
| DOCX      | `application/vnd.openxmlformats...`         | 否       | 使用部分策略                                 |
| PPTX      | `application/vnd.openxmlformats...`         | 是       | 按幻灯片分组                                |
| XLSX/XLS  | `application/vnd.openxmlformats...`         | 是       | 按工作表分组                                |
| HTML      | `text/html`                                | 否       | 使用部分策略                                 |
| Markdown  | `text/markdown`                            | 否       | 使用部分策略                                 |
| 纯文本    | `text/plain`                               | 否       | 使用部分策略                                 |
| CSV       | `text/csv`                                | 否       | 使用部分策略                                 |
| RST       | `text/x-rst`                               | 否       | 使用部分策略                                 |
| RTF       | `application/rtf`                          | 否       | 使用部分策略                                 |
| ODT       | `application/vnd.oasis...`                  | 否       | 使用部分策略                                 |
| TSV       | `text/tab-separated-values`                | 否       | 使用部分策略                                 |

### 溯源元数据

每个页面/部分实体会记录位置元数据，作为 `GRAPH_SOURCE` 命名图中位置元数据的溯源三元组。

#### 现有字段（已包含在 `derived_entity_triples` 中）

- `page_number` — 页面/工作表/幻灯片编号（从 1 开始，仅适用于基于页面的格式）
- `char_offset` — 此页面/部分在整个文档文本中的字符偏移量
- `char_length` — 此页面/部分的文本的字符长度

#### 新字段（扩展 `derived_entity_triples`）

- `mime_type` — 原始文档格式（例如，`application/pdf`）
- `element_types` — 使用 `unstructured` 提取的元素的类别的逗号分隔列表（例如，`Title,NarrativeText,Table`）
- `table_count` — 此页面/部分中的表格数量
- `image_count` — 此页面/部分中的图像数量

这些需要新的 TG 命名空间谓词：

```
TG_SECTION_TYPE  = "https://trustgraph.ai/ns/Section"
TG_IMAGE_TYPE    = "https://trustgraph.ai/ns/Image"
TG_ELEMENT_TYPES = "https://trustgraph.ai/ns/elementTypes"
TG_TABLE_COUNT   = "https://trustgraph.ai/ns/tableCount"
TG_IMAGE_COUNT   = "https://trustgraph.ai/ns/imageCount"
```

图像 URN 方案：`urn:image:{uuid}`

（`TG_MIME_TYPE` 已经存在。）

#### 完整的溯源链

```
知识图谱三元组
  → subgraph (提取溯源)
    → chunk (页面/部分的字符偏移量和长度)
      → page/section (页面编号、字符偏移量和长度、MIME 类型、元素类型)
        → document (库管理员中的原始文件)
```

每个链接都是 `GRAPH_SOURCE` 命名图中一组三元组。

### 服务配置

命令行参数：

```
--strategy              分区策略：auto, hi_res, fast (默认：auto)
--languages             逗号分隔的 OCR 语言代码 (默认: eng)
--section-strategy      部分分组：whole-document, heading, element-type,
                        count, size (默认: whole-document)
--section-element-count 每个部分包含的元素数量（`count` 策略），（默认: 20）
--section-max-size      每个部分的最大字符数（`size` 策略），（默认: 4000 个字符）
--section-within-pages  是否在页面内部应用部分策略 (默认: false)
```

以及标准的 `FlowProcessor` 和库管理员队列参数。

### 流集成

通用解码器在处理流程中占据与现有 PDF 解码器相同的 position：

```
Document → [通用解码器] → TextDocument → [分块器] → Chunk → ...
```

它注册：
- `input` 消费者（`Document` 模式）
- `output` 生产者（`TextDocument` 模式）
- `triples` 生产者（`Triples` 模式）
- 库管理员请求/响应（用于获取和创建子文档）

### 部署

- 新的容器：`trustgraph-flow-universal-decoder`
- 依赖项：`unstructured[all-docs]`（包含 PDF、DOCX、PPTX 等）
- 可以与现有的 PDF 解码器并行运行或替换它，具体取决于流程配置。
- 现有的 PDF 解码器仍然可用，适用于 `unstructured` 依赖项过多的环境。

### 变更内容

| 组件                    | 变更                                         |
|------------------------------|-------------------------------------------------|
| `provenance/namespaces.py`   | 添加 `TG_SECTION_TYPE`、`TG_IMAGE_TYPE`、`TG_ELEMENT_TYPES`、`TG_TABLE_COUNT`、`TG_IMAGE_COUNT` |
| `provenance/triples.py`      | 添加 `mime_type`、`element_types`、`table_count`、`image_count` 参数 |
| `provenance/__init__.py`     | 导出新的常量                                  |
| 新的：`decoding/universal/`   | 新的解码器服务模块                            |
| `setup.cfg` / `pyproject`    | 添加 `unstructured[all-docs]` 依赖项              |
| Docker                       | 新的容器镜像                                  |
| 流程定义                     | 将通用解码器设置为文档输入                       |

### 未变更的内容

- 分块器（接收 `TextDocument`，行为与之前相同）
- 下游提取器（接收 `Chunk`，未发生变化）
- 库管理员（存储子文档，未发生变化）
- 模式（`Document`、`TextDocument`、`Chunk` 未发生变化）
- 查询时溯源（未发生变化）

## 风险

- `unstructured[all-docs]` 具有大量的依赖项（包括 poppler、tesseract 和 libreoffice，用于某些格式）。容器镜像会更大。
  缓解措施：提供不包含 OCR/办公室依赖项的 `[light]` 版本。
- 某些格式可能导致文本提取效果不佳（扫描的 PDF 文件缺少 OCR，复杂的 XLSX 布局）。
  缓解措施：配置 `strategy` 参数，并且现有的 Mistral OCR 解码器仍然可用于高质量的 PDF OCR。
- `unstructured` 版本更新可能会更改元素元数据。
  缓解措施：固定版本，并为每个格式测试提取质量。