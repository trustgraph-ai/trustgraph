---
layout: default
title: "Explicabilidad en Tiempo de Consulta"
parent: "Spanish (Beta)"
---

# Explicabilidad en Tiempo de Consulta

> **Beta Translation:** This document was translated via Machine Learning and as such may not be 100% accurate. All non-English languages are currently classified as Beta.

## Estado

Implementado

## Descripción General

Esta especificación describe cómo GraphRAG registra y comunica datos de explicabilidad durante la ejecución de consultas. El objetivo es una trazabilidad completa: desde la respuesta final, a través de los bordes seleccionados, hasta los documentos de origen.

La explicabilidad en tiempo de consulta captura lo que hizo la tubería de GraphRAG durante el razonamiento. Se conecta con la trazabilidad de la extracción de tiempo, que registra de dónde provienen los hechos del grafo de conocimiento.

## Terminología

| Término | Definición |
|---|---|
| **Explicabilidad** | El registro de cómo se derivó un resultado |
| **Sesión** | Una ejecución de consulta de GraphRAG |
| **Selección de borde** | Selección de bordes relevantes basada en LLM, con razonamiento |
| **Cadena de trazabilidad** | Ruta desde el borde → fragmento → página → documento |

## Arquitectura

### Flujo de Explicabilidad

```
Consulta de GraphRAG
    │
    ├─► Actividad de la Sesión
    │       └─► Texto de la consulta, marca de tiempo
    │
    ├─► Entidad de Recuperación
    │       └─► Todos los bordes recuperados del subgrafo
    │
    ├─► Entidad de Selección
    │       └─► Bordes seleccionados con razonamiento del LLM
    │           └─► Cada borde enlaza con la trazabilidad de extracción
    │
    └─► Entidad de Respuesta
            └─► Referencia a la respuesta sintetizada (en el bibliotecario)
```

### Tubería de GraphRAG de Dos Etapas

1. **Selección de borde:** El LLM selecciona bordes relevantes del subgrafo, proporcionando una justificación para cada uno
2. **Síntesis:** El LLM genera la respuesta a partir de los bordes seleccionados

Esta separación permite la explicabilidad: sabemos exactamente qué bordes contribuyeron.

### Almacenamiento

- Los triples de explicabilidad se almacenan en una colección configurable (por defecto: `explainability`)
- Utiliza la ontología PROV-O para las relaciones de trazabilidad
- Reificación RDF para referencias a bordes
- El contenido de la respuesta se almacena en el servicio del bibliotecario (no en línea, demasiado grande)

### Streaming en Tiempo Real

Los eventos de explicabilidad se transmiten al cliente a medida que se ejecuta la consulta:

1. Se crea la sesión → se emite un evento
2. Se recuperan los bordes → se emite un evento
3. Se seleccionan los bordes con razonamiento → se emite un evento
4. Se sintetiza la respuesta → se emite un evento

El cliente recibe `explain_id` y `explain_collection` para obtener los detalles completos.

## Estructura de URI

Todos los URI utilizan el espacio de nombres `urn:trustgraph:` con UUIDs:

| Entidad | Patrón de URI |
|---|---|
| Sesión | `urn:trustgraph:session:{uuid}` |
| Recuperación | `urn:trustgraph:prov:retrieval:{uuid}` |
| Selección | `urn:trustgraph:prov:selection:{uuid}` |
| Respuesta | `urn:trustgraph:prov:answer:{uuid}` |
| Selección de borde | `urn:trustgraph:prov:edge:{uuid}:{index}` |

## Modelo RDF (PROV-O)

### Actividad de la Sesión

```turtle
<session-uri> a prov:Activity ;
    rdfs:label "Sesión de consulta GraphRAG" ;
    prov:startedAtTime "2024-01-15T10:30:00Z" ;
    tg:query "¿Cuál fue la Guerra contra el Terrorismo?" .
```

### Entidad de Recuperación

```turtle
<retrieval-uri> a prov:Entity ;
    rdfs:label "Bordes recuperados" ;
    prov:wasGeneratedBy <session-uri> ;
    tg:edgeCount 50 .
```

### Entidad de Selección

```turtle
<selection-uri> a prov:Entity ;
    rdfs:label "Bordes seleccionados" ;
    prov:wasDerivedFrom <retrieval-uri> ;
    tg:selectedEdge <edge-sel-0> ;
    tg:selectedEdge <edge-sel-1> .

<edge-sel-0> tg:edge << <s> <p> <o> >> ;
    tg:reasoning "Este borde establece la relación clave..." .
```

### Entidad de Respuesta

```turtle
<answer-uri> a prov:Entity ;
    rdfs:label "Respuesta de GraphRAG" ;
    prov:wasDerivedFrom <selection-uri> ;
    tg:document <urn:trustgraph:answer:{uuid}> .
```

La `tg:document` hace referencia a la respuesta almacenada en el servicio del bibliotecario.

## Constantes de Espacio de Nombres

Definidas en `trustgraph-base/trustgraph/provenance/namespaces.py`:

| Constante | URI |
|---|---|
| `TG_QUERY` | `https://trustgraph.ai/ns/query` |
| `TG_EDGE_COUNT` | `https://trustgraph.ai/ns/edgeCount` |
| `TG_SELECTED_EDGE` | `https://trustgraph.ai/ns/selectedEdge` |
| `TG_EDGE` | `https://trustgraph.ai/ns/edge` |
| `TG_REASONING` | `https://trustgraph.ai/ns/reasoning` |
| `TG_CONTENT` | `https://trustgraph.ai/ns/content` |
| `TG_DOCUMENT` | `https://trustgraph.ai/ns/document` |

## Esquema GraphRagResponse

```python
@dataclass
class GraphRagResponse:
    error: Error | None = None
    response: str = ""
    end_of_stream: bool = False
    explain_id: str | None = None
    explain_collection: str | None = None
    message_type: str = ""  # "chunk" or "explain"
    end_of_session: bool = False
```

### Tipos de Mensaje

| message_type | Propósito |
|---|---|
| `chunk` | Texto de la respuesta (streaming o final) |
| `explain` | Evento de explicabilidad con referencia IRI |

### Ciclo de Vida de la Sesión

1. Múltiples mensajes `explain` (sesión, recuperación, selección, respuesta)
2. Múltiples mensajes `chunk` (respuesta en streaming)
3. Final `chunk` con `end_of_session=True`

## Formato de Selección de Bordes

El LLM devuelve un JSONL con los bordes seleccionados:

```jsonl
{"id": "edge-hash-1", "reasoning": "Este borde muestra la relación clave..."}
{"id": "edge-hash-2", "reasoning": "Proporciona evidencia de apoyo..."}
```

El `id` es un hash de `(labeled_s, labeled_p, labeled_o)` calculado por `edge_id()`.

## Preservación de URI

### El Problema

GraphRAG muestra etiquetas legibles para el LLM, pero la explicabilidad necesita los URI originales para el rastreo de la trazabilidad.

### Solución

`get_labelgraph()` devuelve:
- `labeled_edges`: Lista de `(label_s, label_p, label_o)` para el LLM
- `uri_map`: Diccionario que mapea `edge_id(labels)` → `(uri_s, uri_p, uri_o)`

Cuando se guarda la información de explicabilidad, se utilizan los URI de `uri_map`.

## Rastreando la Trazabilidad

### Desde el borde hasta la fuente

Se pueden rastrear los bordes seleccionados de vuelta a la fuente:

### Referencias

- PROV-O (W3C Provenance Ontology): https://www.w3.org/TR/prov-o/
- RDF-star: https://w3c.github.io/rdf-star/
- Trazabilidad de tiempo de extracción: `docs/tech-specs/extraction-time-provenance.md`
