---
layout: default
title: "Cambios en el API Gateway: v1.8 a v2.1"
parent: "Spanish (Beta)"
---

# Cambios en el API Gateway: v1.8 a v2.1

> **Beta Translation:** This document was translated via Machine Learning and as such may not be 100% accurate. All non-English languages are currently classified as Beta.

## Resumen

El gateway de API ha obtenido nuevos despachadores de servicios WebSocket para consultas de incrustaciones, un nuevo punto final REST para el streaming de contenido de documentos, y ha experimentado un cambio significativo en el formato del cableado de `Value` a `Term`. El "servicio de objetos" se ha renombrado a "filas".

---

## Nuevos Despachadores de Servicios WebSocket

Estos son nuevos servicios de solicitud/respuesta disponibles a través del multiplexador WebSocket en `/api/v1/socket` (con ámbito de flujo):

| Clave de servicio | Descripción |
|-------------|-------------|
| `document-embeddings` | Consulta fragmentos de documentos por similitud de texto. La solicitud/respuesta utiliza los esquemas `DocumentEmbeddingsRequest`/`DocumentEmbeddingsResponse`. |
| `row-embeddings` | Consulta filas de datos estructurados por similitud de texto en campos indexados. La solicitud/respuesta utiliza los esquemas `RowEmbeddingsRequest`/`RowEmbeddingsResponse`. |

Estos se unen al existente `graph-embeddings` dispatcher (que ya estaba presente en v1.8 pero puede que se haya actualizado).

### Lista completa de despachadores de servicios de flujo WebSocket (v2.1)

Servicios de solicitud/respuesta (a través de `/api/v1/flow/{flow}/service/{kind}` o multiplexador WebSocket):

- `agent`, `text-completion`, `prompt`, `mcp-tool`
- `graph-rag`, `document-rag`
- `embeddings`, `graph-embeddings`, `document-embeddings`
- `triples`, `rows`, `nlp-query`, `structured-query`, `structured-diag`
- `row-embeddings`

---

## Nuevo Punto Final REST

| Método | Ruta | Descripción |
|--------|------|-------------|
| `GET` | `/api/v1/document-stream` | Transmite contenido de documentos desde la biblioteca como bytes brutos. Parámetros de consulta: `user` (obligatorio), `document-id` (obligatorio), `chunk-size` (opcional, predeterminado 1MB). Devuelve el contenido del documento con el codificado de transferencia en fragmentos, decodificado internamente en base64. |

---

## Servicio Renombrado: "objects" a "rows"

| v1.8 | v2.1 | Notas |
|------|------|-------|
| `objects_query.py` / `ObjectsQueryRequestor` | `rows_query.py` / `RowsQueryRequestor` | El esquema cambiado de `ObjectsQueryRequest`/`ObjectsQueryResponse` a `RowsQueryRequest`/`RowsQueryResponse`. |
| `objects_import.py` / `ObjectsImport` | `rows_import.py` / `RowsImport` | Despachador de importación para datos estructurados. |

La clave del servicio WebSocket cambió de `"objects"` a `"rows"`, y la clave del despachador de importación cambió de `"objects"` a `"rows"`.

---

## Cambio de Formato del Cable: Value a Term

La capa de serialización (`serialize.py`) se ha reescrito para utilizar el nuevo tipo `Term` en lugar del antiguo tipo `Value`.

### Formato antiguo (v1.8 — `Value`)

```json
{"v": "http://example.org/entity", "e": true}
```

- `v`: el valor (cadena)
- `e`: indicador booleano que indica si el valor es un URI

### Formato nuevo (v2.1 — `Term`)

IRIs:
```json
{"t": "i", "i": "http://example.org/entity"}
```

Literales:
```json
{"t": "l", "v": "some text", "d": "datatype-uri", "l": "en"}
```

Triples con comillas (RDF-star):
```json
{"t": "r", "r": {"s": {...}, "p": {...}, "o": {...}}}
```

- `t`: discriminador de tipo — `"i"` (URI), `"l"` (literal), `"r"` (triple con comillas), `"b"` (nodo en blanco)
- La serialización ahora delega a `TermTranslator` y `TripleTranslator` de `trustgraph.messaging.translators.primitives`

### Otros cambios en la serialización

| Campo | v1.8 | v2.1 |
|-------|------|------|
| Metadatos | `metadata.metadata` (subgrafo) | `metadata.root` (valor simple) |
| Entidad de incrustación | `entity.vectors` (plural) | `entity.vector` (singular) |
| Fragmento de incrustación de documento | `chunk.vectors` + `chunk.chunk` (texto) | `chunk.vector` + `chunk.chunk_id` (ID de referencia) |

---

## Cambios que Rompen

- **Cambio de formato del cable `Value` a `Term`**: Todos los clientes que envían/reciben triples, incrustaciones o contextos de entidad a través del gateway deben actualizar al nuevo formato Term.
- **Cambio de nombre de `objects` a `rows`**: Se ha modificado la clave del servicio WebSocket y la clave del despachador de importación.
- **Cambio del campo de metadatos**: `metadata.metadata` (un subgrafo serializado) reemplazado por `metadata.root` (un valor simple).
- **Cambios en los campos de incrustación**: `vectors` (plural) se convirtió en `vector` (singular); las incrustaciones de documentos ahora hacen referencia a `chunk_id` en lugar de a `chunk` de texto.
- **Nuevo punto final `/api/v1/document-stream`**: Aditivo, no rompe.
