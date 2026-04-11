# API 网关变更：v1.8 到 v2.1

## 摘要

API 网关新增了用于嵌入查询的 WebSocket 服务分发器，新增了 REST 串流端点，用于文档内容，并进行了重要的 Wire 格式变化，从 `Value` 变为 `Term`。 "对象" 服务已被重命名为 "行"。

---

## 新的 WebSocket 服务分发器

这些是可通过 WebSocket 多路复用器 `/api/v1/socket` (范围限定) 访问的新请求/响应服务：

| 服务键 | 描述 |
|---|---|
| `document-embeddings` | 通过文本相似性查询文档块。 请求/响应使用 `DocumentEmbeddingsRequest`/`DocumentEmbeddingsResponse` 模式。 |
| `row-embeddings` | 通过在索引字段上对结构化数据行进行文本相似性查询。 请求/响应使用 `RowEmbeddingsRequest`/`RowEmbeddingsResponse` 模式。 |

这些与现有的 `graph-embeddings` 分发器 (已存在于 v1.8 但可能已被更新) 关联。

### WebSocket 流程服务分发器的完整列表 (v2.1)

请求/响应服务 (通过 `/api/v1/flow/{flow}/service/{kind}` 或 WebSocket 多路复用器):

- `agent`, `text-completion`, `prompt`, `mcp-tool`
- `graph-rag`, `document-rag`
- `embeddings`, `graph-embeddings`, `document-embeddings`
- `triples`, `rows`, `nlp-query`, `structured-query`, `structured-diag`
- `row-embeddings`

---

## 新的 REST 端点

| 方法 | 路径 | 描述 |
|---|---|---|
| `GET` | `/api/v1/document-stream` | 从库中流式传输文档内容为原始字节。 查询参数：`user` (必需), `document-id` (必需), `chunk-size` (可选, 默认 1MB)。 返回文档内容，通过内部进行 base64 解码，并以块传输编码传输。 |

---

## 重命名服务： "objects" 为 "rows"

| v1.8 | v2.1 | 备注 |
|---|---|---|
| `objects_query.py` / `ObjectsQueryRequestor` | `rows_query.py` / `RowsQueryRequestor` | 模式从 `ObjectsQueryRequest`/`ObjectsQueryResponse` 变为 `RowsQueryRequest`/`RowsQueryResponse`。 |
| `objects_import.py` / `ObjectsImport` | `rows_import.py` / `RowsImport` | 结构化数据导入分发器。 |

WebSocket 服务键已从 `"objects"` 变为 `"rows"`，以及导入分发器的键也从 `"objects"` 变为 `"rows"`。

---

## Wire 格式变化： Value 为 Term

`serialize.py` (序列化层) 已重写为使用新的 `Term` 类型，而不是旧的 `Value` 类型。

### 旧格式 (v1.8 - `Value`)

```json
{"v": "http://example.org/entity", "e": true}
```

- `v`: 值 (字符串)
- `e`: 布尔标志，指示值是否为 URI

### 新格式 (v2.1 - `Term`)

IRI:
```json
{"t": "i", "i": "http://example.org/entity"}
```

字面量：
```json
{"t": "l", "v": "some text", "d": "datatype-uri", "l": "en"}
```

带引号的三元组 (RDF-star):
```json
{"t": "r", "r": {"s": {...}, "p": {...}, "o": {...}}}
```

- `t`: 类型区分值 — `"i"` (IRI), `"l"` (字面量), `"r"` (带引号的三元组), `"b"` (空节点)
- 序列化现在委托给 `trustgraph.messaging.translators.primitives` 中的 `TermTranslator` 和 `TripleTranslator`

### 其他序列化更改

| 字段 | v1.8 | v2.1 |
|---|---|---|
| 元数据 | `metadata.metadata` (子图) | `metadata.root` (简单值) |
| 图嵌入实体 | `entity.vectors` (复数) | `entity.vector` (单数) |
| 文档嵌入块 | `chunk.vectors` + `chunk.chunk` (文本) | `chunk.vector` + `chunk.chunk_id` (ID 引用) |

---

## 破坏性变更

- **Value 到 Term 的 Wire 格式**: 任何通过网关发送/接收三元组、嵌入或实体上下文的客户端都必须更新为新的 Term 格式。
- **objects 到 rows 的重命名**: WebSocket 服务键和导入键已更改。
- **元数据字段更改**: `metadata.metadata` (序列化的子图) 已被 `metadata.root` (简单值) 替换。
- **嵌入字段更改**: `vectors` (复数) 变为 `vector` (单数)；文档嵌入现在引用 `chunk_id` 而不是内联 `chunk` 文本。
- **新的 `/api/v1/document-stream` 端点**: 添加的，非破坏性。