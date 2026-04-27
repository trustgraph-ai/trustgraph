---
layout: default
title: "Alterações no API Gateway: da versão 1.8 para a versão 2.1"
parent: "Portuguese (Beta)"
---

# Alterações no API Gateway: da versão 1.8 para a versão 2.1

> **Beta Translation:** This document was translated via Machine Learning and as such may not be 100% accurate. All non-English languages are currently classified as Beta.

## Resumo

O gateway de API ganhou novos distribuidores de serviços WebSocket para consultas de incorporações
e um novo endpoint REST para streaming de conteúdo de documentos, e passou por
uma mudança significativa no formato de comunicação, de `Value` para `Term`. O serviço "objects"
foi renomeado para "rows".

--

## Novos Distribuidores de Serviços WebSocket

Estes são novos serviços de solicitação/resposta disponíveis através do
multiplexador WebSocket em `/api/v1/socket` (com escopo de fluxo):

| Chave do Serviço | Descrição |
|-------------|-------------|
| `document-embeddings` | Consulta de trechos de documentos por similaridade de texto. Solicitação/resposta usa os esquemas `DocumentEmbeddingsRequest`/`DocumentEmbeddingsResponse`. |
| `row-embeddings` | Consulta de linhas de dados estruturados por similaridade de texto em campos indexados. Solicitação/resposta usa os esquemas `RowEmbeddingsRequest`/`RowEmbeddingsResponse`. |

Estes se juntam ao distribuidor existente `graph-embeddings` (que já
estava presente na versão 1.8, mas pode ter sido atualizado).

### Lista completa de distribuidores de serviços de fluxo WebSocket (versão 2.1)

Serviços de solicitação/resposta (via `/api/v1/flow/{flow}/service/{kind}` ou
multiplexador WebSocket):

`agent`, `text-completion`, `prompt`, `mcp-tool`
`graph-rag`, `document-rag`
`embeddings`, `graph-embeddings`, `document-embeddings`
`triples`, `rows`, `nlp-query`, `structured-query`, `structured-diag`
`row-embeddings`

--

## Novo Endpoint REST

| Método | Caminho | Descrição |
|--------|------|-------------|
| `GET` | `/api/v1/document-stream` | Transmite o conteúdo do documento da biblioteca como bytes brutos. Parâmetros de consulta: `user` (obrigatório), `document-id` (obrigatório), `chunk-size` (opcional, padrão 1MB). Retorna o conteúdo do documento em codificação de transferência em blocos, decodificado de base64 internamente. |

--

## Serviço Renomeado: "objects" para "rows"

| v1.8 | v2.1 | Notas |
|------|------|-------|
| `objects_query.py` / `ObjectsQueryRequestor` | `rows_query.py` / `RowsQueryRequestor` | Esquema alterado de `ObjectsQueryRequest`/`ObjectsQueryResponse` para `RowsQueryRequest`/`RowsQueryResponse`. |
| `objects_import.py` / `ObjectsImport` | `rows_import.py` / `RowsImport` | Distribuidor de importação para dados estruturados. |

A chave do serviço WebSocket foi alterada de `"objects"` para `"rows"`, e a
chave do distribuidor de importação foi alterada de `"objects"` para `"rows"`.

--

## Mudança no Formato de Comunicação: Valor para Termo

A camada de serialização (`serialize.py`) foi reescrita para usar o novo tipo `Term`
em vez do tipo antigo `Value`.

### Formato antigo (v1.8 — `Value`)

```json
{"v": "http://example.org/entity", "e": true}
```

`v`: o valor (string)
`e`: flag booleano que indica se o valor é um URI

### Novo formato (v2.1 — `Term`)

IRIs:
```json
{"t": "i", "i": "http://example.org/entity"}
```

Literais:
```json
{"t": "l", "v": "some text", "d": "datatype-uri", "l": "en"}
```

Triplas citadas (RDF-star):
```json
{"t": "r", "r": {"s": {...}, "p": {...}, "o": {...}}}
```

`t`: tipo de discriminador — `"i"` (IRI), `"l"` (literal), `"r"` (tripla entre aspas), `"b"` (nó vazio)
A serialização agora delega para `TermTranslator` e `TripleTranslator` a partir de `trustgraph.messaging.translators.primitives`

### Outras alterações de serialização

| Campo | v1.8 | v2.1 |
|-------|------|------|
| Metadados | `metadata.metadata` (subgrafo) | `metadata.root` (valor simples) |
| Incorporação de entidade | `entity.vectors` (plural) | `entity.vector` (singular) |
| Incorporação de fragmento de documento | `chunk.vectors` + `chunk.chunk` (texto) | `chunk.vector` + `chunk.chunk_id` (referência de ID) |

--

## Alterações Incompatíveis

**Formato de fio de `Value` para `Term`**: Todos os clientes que enviam ou recebem triplas, incorporações ou contextos de entidade através do gateway devem atualizar para o novo formato de Termo.
**Renomeação de `objects` para `rows`**: A chave do serviço WebSocket e a chave de importação foram alteradas.
**Alteração do campo de metadados**: `metadata.metadata` (um subgrafo serializado) foi substituído por `metadata.root` (um valor simples).
**Alterações nos campos de incorporação**: `vectors` (plural) se tornou `vector` (singular); as incorporações de documento agora fazem referência a `chunk_id` em vez de texto `chunk` inline.
**Novo endpoint `/api/v1/document-stream`**: Aditivo, não quebra a compatibilidade.
