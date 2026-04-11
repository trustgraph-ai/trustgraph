---
layout: default
title: "Propuesta de Refactorización del Directorio de Esquemas"
parent: "Spanish (Beta)"
---

# Propuesta de Refactorización del Directorio de Esquemas

> **Beta Translation:** This document was translated via Machine Learning and as such may not be 100% accurate. All non-English languages are currently classified as Beta.

## Problemas Actuales

1. **Estructura plana** - Tener todos los esquemas en un solo directorio dificulta la comprensión de las relaciones.
2. **Preocupaciones mixtas** - Tipos centrales, objetos de dominio y contratos de API mezclados.
3. **Nombres poco claros** - Archivos como "object.py", "types.py", "topic.py" no indican claramente su propósito.
4. **Sin capa clara** - No es fácil ver qué depende de qué.

## Estructura Propuesta

```
trustgraph-base/trustgraph/schema/
├── __init__.py
├── core/              # Tipos primitivos centrales utilizados en todas partes
│   ├── __init__.py
│   ├── primitives.py  # Error, Value, Triple, Field, RowSchema
│   ├── metadata.py    # Registro de metadatos
│   └── topic.py       # Utilitarios de tema
│
├── knowledge/         # Modelos del dominio de conocimiento y extracción
│   ├── __init__.py
│   ├── graph.py       # EntityContext, EntityEmbeddings, Triples
│   ├── document.py    # Document, TextDocument, Chunk
│   ├── knowledge.py   # Tipos de extracción de conocimiento
│   ├── embeddings.py  # Todos los tipos relacionados con la incorporación (movidos de múltiples archivos)
│   └── nlp.py         # Tipos de Definición, Tema, Relación, Hecho
│
└── services/          # Contratos de solicitud/respuesta de servicios
    ├── __init__.py
    ├── llm.py         # TextCompletion, Embeddings, Solicitudes/respuestas de Herramientas
    ├── retrieval.py   # Consultas/respuestas de GraphRAG, DocumentRAG
    ├── query.py       # Consultas/respuestas de GraphEmbeddingsRequest, DocumentEmbeddingsRequest
    ├── agent.py       # Solicitudes/respuestas del agente
    ├── flow.py        # Solicitudes/respuestas de flujo
    ├── prompt.py      # Solicitudes/respuestas del servicio de prompt
    ├── config.py      # Servicio de configuración
    ├── library.py     # Servicio de bibliotecario
    └── lookup.py      # Servicio de búsqueda
```

## Cambios Clave

1. **Organización jerárquica** - Separación clara entre tipos centrales, modelos de conocimiento y contratos de servicio.
2. **Nombres mejorados**:
   - `types.py` → `core/primitives.py` (propósito más claro)
   - `object.py` → Dividir entre archivos apropiados según el contenido real
   - `documents.py` → `knowledge/document.py` (singular, consistente)
   - `models.py` → `services/llm.py` (qué tipo de modelos)
   - `prompt.py` → Dividir: partes del servicio a `services/prompt.py`, tipos de datos a `knowledge/nlp.py`

3. **Agrupamiento lógico**:
   - Todos los tipos de incorporación consolidados en `knowledge/embeddings.py`
   - Todos los contratos de servicio relacionados con LLM en `services/llm.py`
   - Separación clara de pares de solicitud/respuesta en el directorio de servicios
   - Grupos de tipos de extracción de conocimiento con otros modelos de dominio de conocimiento

4. **Claridad de dependencias**:
   - Los tipos centrales no tienen dependencias
   - Los modelos de conocimiento dependen solo de los centrales
   - Los contratos de servicio pueden depender de los centrales y de los modelos de conocimiento

## Beneficios de la Migración

1. **Navegación más fácil** - Los desarrolladores pueden encontrar rápidamente lo que necesitan.
2. **Mejor modularidad** - Límites claros entre diferentes preocupaciones.
3. **Importaciones más simples** - Rutas de importación más intuitivas.
4. **Futurizable** - Fácil de agregar nuevos tipos de conocimiento o servicios sin desorden.

## Cambios de Importación de Ejemplo

```python
# Antes
from trustgraph.schema import Error, Triple, GraphEmbeddings, TextCompletionRequest

# Después
from trustgraph.schema.core import Error, Triple
from trustgraph.schema.knowledge import GraphEmbeddings
from trustgraph.schema.services import TextCompletionRequest
```

## Notas de Implementación

1. Mantener la compatibilidad hacia atrás manteniendo las importaciones en el `__init__.py` raíz.
2. Mover los archivos gradualmente, actualizando las importaciones según sea necesario.
3. Considerar agregar un `legacy.py` que importe todo para el período de transición.
4. Actualizar la documentación para reflejar la nueva estructura.

<function_calls>
<invoke name="TodoWrite">
<parameter name="todos">[{"id": "1", "content": "Examinar la estructura actual del directorio de esquemas", "status": "completed", "priority": "high"}, {"id": "2", "content": "Analizar los archivos de esquema y sus propósitos", "status": "completed", "priority": "high"}, {"id": "3", "content": "Proponer una estructura y nombres mejorados", "status": "completed", "priority": "high"}]
