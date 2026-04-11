---
layout: default
title: "Especificación Técnica de Soporte de Streaming para RAG"
parent: "Spanish (Beta)"
---

# Especificación Técnica de Soporte de Streaming para RAG

> **Beta Translation:** This document was translated via Machine Learning and as such may not be 100% accurate. All non-English languages are currently classified as Beta.

## Visión general

Esta especificación describe la adición de soporte de streaming a los servicios GraphRAG y DocumentRAG, permitiendo respuestas en tiempo real, token por token, para consultas de recuperación de conocimiento y documentos. Esto extiende la arquitectura de streaming existente, ya implementada para servicios de completado de texto, prompts y agentes de LLM.

## Objetivos

- **Experiencia de usuario consistente**: Proporcionar la misma experiencia de streaming en todos los servicios TrustGraph.
- **Cambios mínimos en la API**: Añadir soporte de streaming con una única bandera `streaming`, siguiendo patrones establecidos.
- **Compatibilidad hacia atrás**: Mantener el comportamiento no de streaming existente como predeterminado.
- **Reutilizar la infraestructura existente**: Aprovechar el streaming ya implementado en PromptClient.
- **Soporte de Gateway**: Permitir el streaming a través de un gateway websocket para aplicaciones cliente.

## Antecedentes

Servicios de streaming actualmente implementados:

- **Servicio de completado de texto de LLM**: Fase 1 - Streaming desde proveedores de LLM.
- **Servicio de prompts**: Fase 2 - Streaming a través de plantillas de prompts.
- **Servicio de agente**: Fase 3-4 - Streaming de respuestas ReAct con fragmentos incrementales de "pensamiento/observación/respuesta".

Limitaciones actuales para servicios RAG:

- GraphRAG y DocumentRAG solo soportan respuestas de bloqueo.
- Los usuarios deben esperar a que la respuesta completa del LLM antes de ver cualquier salida.
- Mala experiencia de usuario para respuestas largas de consultas de conocimiento o documentos.
- Experiencia inconsistente en comparación con otros servicios de TrustGraph.

Esta especificación aborda estas limitaciones añadiendo soporte de streaming a GraphRAG y DocumentRAG. Al permitir respuestas token por token, TrustGraph puede:

- Proporcionar una experiencia de usuario consistente de streaming para todos los tipos de consultas.
- Reducir la latencia percibida para las consultas RAG.
- Facilitar una mejor retroalimentación del progreso para las consultas de ejecución prolongada.
- Soporte para visualización en tiempo real en aplicaciones cliente.

## Diseño Técnico

### Arquitectura

La implementación de streaming de RAG aprovecha la infraestructura existente:

1.  **Streaming de PromptClient** (Ya implementado)
    -   `kg_prompt()` y `document_prompt()` ya aceptan los parámetros `streaming` y `chunk_callback`.
    -   Estos llaman `prompt()` internamente con soporte de streaming.
    -   No se necesitan cambios en PromptClient.
    -   Módulo: `trustgraph-base/trustgraph/base/prompt_client.py`

2.  **Servicio GraphRAG** (Necesita pasar el parámetro `streaming`)
    -   Añadir el parámetro `streaming` al método `query()`.
    -   Pasar la bandera de streaming y los callbacks a `prompt_client.kg_prompt()`.
    -   El esquema GraphRagRequest debe incluir el campo `streaming`.
    -   Módulos:
        -   `trustgraph-flow/trustgraph/retrieval/graph_rag/graph_rag.py`
        -   `trustgraph-flow/trustgraph/retrieval/graph_rag/rag.py` (Procesador)
        -   `trustgraph-base/trustgraph/schema/graph_rag.py` (Esquema de solicitud)
        -   `trustgraph-flow/trustgraph/gateway/dispatch/graph_rag.py` (Gateway)

3.  **Servicio DocumentRAG** (Necesita pasar el parámetro `streaming`)
    -   Añadir el parámetro `streaming` al método `query()`.
    -   Pasar la bandera de streaming y los callbacks a `prompt_client.document_prompt()`.
    -   El esquema DocumentRagRequest debe incluir el campo `streaming`.
    -   Módulos:
        -   `trustgraph-flow/trustgraph/retrieval/document_rag/document_rag.py`
        -   `trustgraph-flow/trustgraph/retrieval/document_rag/rag.py` (Procesador)
        -   `trustgraph-base/trustgraph/schema/document_rag.py` (Esquema de solicitud)
        -   `trustgraph-flow/trustgraph/gateway/dispatch/document_rag.py` (Gateway)

### Flujo de datos

**No de streaming (actual)**:
```
Client → Gateway → RAG Service → PromptClient.kg_prompt(streaming=False)
                                   ↓
                                Prompt Service → LLM
                                   ↓
                                Respuesta completa
                                   ↓
Client ← Gateway ← RAG Service ←  Respuesta
```

**Streaming (propuesto)**:
```
Client → Gateway → RAG Service → PromptClient.kg_prompt(streaming=True, chunk_callback=cb)
                                   ↓
                                Prompt Service → LLM (streaming)
                                   ↓
                                Fragmento → callback → Respuesta RAG (fragmento)
                                   ↓                       ↓
Client ← Gateway ← ────────────────────────────────── Flujo de respuesta
```

### APIs

**Cambios en GraphRAG**:

1.  **GraphRag.query()** - Añadir parámetros de streaming
```python
async def query(
    self, query, user, collection,
    verbose=False, streaming=False, chunk_callback=None  # NUEVO
):
    # ... código existente de recuperación de entidades/triples ...

    if streaming and chunk_callback:
        resp = await self.prompt_client.kg_prompt(
            query, kg,
            streaming=True,
            chunk_callback=chunk_callback
        )
    else:
        resp = await self.prompt_client.kg_prompt(query, kg)

    return resp
```

2.  **Esquema GraphRagRequest** - Añadir campo de streaming
```python
class GraphRagRequest(Record):
    query = String()
    user = String()
    collection = String()
    streaming = Boolean()  # NUEVO
```

3.  **Esquema GraphRagResponse** - Añadir campos de streaming (seguir el patrón de Agent)
```python
class GraphRagResponse(Record):
    response = String()    # LEGADO: respuesta completa
    chunk = String()       # NUEVO: fragmento de streaming
    end_of_stream = Boolean()  # NUEVO: indica el último fragmento
```

4.  **Procesador** - Pasar el streaming a través
```python
async def handle(self, msg):
    # ... código existente ...

    async def send_chunk(chunk):
        await self.respond(GraphRagResponse(
            chunk=chunk,
            end_of_stream=False,
            response=None
        ))

    if request.streaming:
        resp = await self.prompt_client.kg_prompt(
            request.query,
            request.context,
            streaming=True
        )
    else:
        resp = await self.prompt_client.kg_prompt(
            request.query,
            request.context
        )

    # Procesar respuesta
    # ...
```

### Plan de migración

No se requiere migración:

- El soporte de streaming es opcional a través del parámetro `streaming` (predeterminado a False).
- Los clientes existentes siguen funcionando sin cambios.
- Los nuevos clientes pueden optar por habilitar el streaming.

## Cronograma

Tiempo estimado de implementación: 4-6 horas.
- Fase 1 (2 horas): Soporte de streaming para GraphRAG.
- Fase 2 (2 horas): Soporte de streaming para DocumentRAG.
- Fase 3 (1-2 horas): Actualizaciones del Gateway y banderas de la CLI.
- Pruebas: Integradas en cada fase.

## Preguntas abiertas

- ¿Deberíamos añadir soporte de streaming al servicio NLP Query también?
- ¿Queremos transmitir solo los pasos intermedios (por ejemplo, "Recuperando entidades...", "Consultando el gráfico...") o también la salida del LLM?
- ¿Debería GraphRAG/DocumentRAG incluir metadatos del fragmento (por ejemplo, número de fragmento, número total esperado)?

## Referencias

- Implementación existente: `docs/tech-specs/streaming-llm-responses.md`
- Streaming de PromptClient: `trustgraph-base/trustgraph/base/prompt_client.py`
- Streaming de Agent: `trustgraph-flow/trustgraph/agent/react/agent_manager.py`
