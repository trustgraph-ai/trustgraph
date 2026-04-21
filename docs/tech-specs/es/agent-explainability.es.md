---
layout: default
title: "Explicabilidad del Agente: Registro de Origen"
parent: "Spanish (Beta)"
---

# Explicabilidad del Agente: Registro de Origen

> **Beta Translation:** This document was translated via Machine Learning and as such may not be 100% accurate. All non-English languages are currently classified as Beta.

## Resumen

Agregar el registro de origen al bucle del agente de React para que las sesiones del agente puedan ser rastreadas y depuradas utilizando la misma infraestructura de explicabilidad que GraphRAG.

**Decisiones de Diseño:**
- Escribir en `urn:graph:retrieval` (grafo de explicabilidad genérico)
- Cadena de dependencia lineal por ahora (análisis N → derivado de → análisis N-1)
- Las herramientas son cajas negras opacas (registrar solo la entrada/salida)
- El soporte de DAG se pospone a una iteración futura

## Tipos de Entidades

Tanto GraphRAG como Agent utilizan PROV-O como la ontología base con subtipos específicos de TrustGraph:

### Tipos de GraphRAG
| Entidad | Tipo PROV-O | Tipos TG | Descripción |
|--------|-------------|----------|-------------|
| Pregunta | `prov:Activity` | `tg:Question`, `tg:GraphRagQuestion` | La consulta del usuario |
| Exploración | `prov:Entity` | `tg:Exploration` | Bordes recuperados del grafo de conocimiento |
| Enfoque | `prov:Entity` | `tg:Focus` | Bordes seleccionados con razonamiento |
| Síntesis | `prov:Entity` | `tg:Synthesis` | Respuesta final |

### Tipos de Agente
| Entidad | Tipo PROV-O | Tipos TG | Descripción |
|--------|-------------|----------|-------------|
| Pregunta | `prov:Activity` | `tg:Question`, `tg:AgentQuestion` | La consulta del usuario |
| Análisis | `prov:Entity` | `tg:Analysis` | Cada ciclo de pensar/actuar/observar |
| Conclusión | `prov:Entity` | `tg:Conclusion` | Respuesta final |

### Tipos de Document RAG
| Entidad | Tipo PROV-O | Tipos TG | Descripción |
|--------|-------------|----------|-------------|
| Pregunta | `prov:Activity` | `tg:Question`, `tg:DocRagQuestion` | La consulta del usuario |
| Exploración | `prov:Entity` | `tg:Exploration` | Fragmentos recuperados del almacén de documentos |
| Síntesis | `prov:Entity` | `tg:Synthesis` | Respuesta final |

**Nota:** Document RAG utiliza un subconjunto de los tipos de GraphRAG (no hay un paso de "Enfoque" ya que no hay una fase de selección/razonamiento de bordes).

### Subtipos de Pregunta

Todas las entidades de "Pregunta" comparten `tg:Question` como un tipo base, pero tienen un subtipo específico para identificar el mecanismo de recuperación:

| Subtipo | Patrón URI | Mecanismo |
|---------|-------------|-----------|
| `tg:GraphRagQuestion` | `urn:trustgraph:question:{uuid}` | RAG de grafo de conocimiento |
| `tg:DocRagQuestion` | `urn:trustgraph:docrag:{uuid}` | RAG de documento/fragmento |
| `tg:AgentQuestion` | `urn:trustgraph:agent:{uuid}` | Agente ReAct |

Esto permite consultar todas las preguntas a través de `tg:Question` mientras se filtra por un mecanismo específico a través del subtipo.

## Modelo de Origen

```
Question (urn:trustgraph:agent:{uuid})
    │
    │  tg:query = "User's question"
    │  prov:startedAtTime = timestamp
    │  rdf:type = prov:Activity, tg:Question
    │
    ↓ prov:wasDerivedFrom
    │
Analysis1 (urn:trustgraph:agent:{uuid}/i1)
    │
    │  tg:thought = "I need to query the knowledge base..."
    │  tg:action = "knowledge-query"
    │  tg:arguments = {"question": "..."}
    │  tg:observation = "Result from tool..."
    │  rdf:type = prov:Entity, tg:Analysis
    │
    ↓ prov:wasDerivedFrom
    │
Analysis2 (urn:trustgraph:agent:{uuid}/i2)
    │  ...
    ↓ prov:wasDerivedFrom
    │
Conclusion (urn:trustgraph:agent:{uuid}/final)
    │
    │  tg:answer = "The final response..."
    │  rdf:type = prov:Entity, tg:Conclusion
```

### Modelo de Origen (Provenance) del Documento RAG

```
Question (urn:trustgraph:docrag:{uuid})
    │
    │  tg:query = "User's question"
    │  prov:startedAtTime = timestamp
    │  rdf:type = prov:Activity, tg:Question
    │
    ↓ prov:wasGeneratedBy
    │
Exploration (urn:trustgraph:docrag:{uuid}/exploration)
    │
    │  tg:chunkCount = 5
    │  tg:selectedChunk = "chunk-id-1"
    │  tg:selectedChunk = "chunk-id-2"
    │  ...
    │  rdf:type = prov:Entity, tg:Exploration
    │
    ↓ prov:wasDerivedFrom
    │
Synthesis (urn:trustgraph:docrag:{uuid}/synthesis)
    │
    │  tg:content = "The synthesized answer..."
    │  rdf:type = prov:Entity, tg:Synthesis
```

## Cambios Requeridos

### 1. Cambios en el Esquema

**Archivo:** `trustgraph-base/trustgraph/schema/services/agent.py`

Agregar los campos `session_id` y `collection` a `AgentRequest`:
```python
@dataclass
class AgentRequest:
    question: str = ""
    state: str = ""
    group: list[str] | None = None
    history: list[AgentStep] = field(default_factory=list)
    user: str = ""
    collection: str = "default"  # NEW: Collection for provenance traces
    streaming: bool = False
    session_id: str = ""         # NEW: For provenance tracking across iterations
```

**Archivo:** `trustgraph-base/trustgraph/messaging/translators/agent.py`

Actualizar el traductor para manejar `session_id` y `collection` tanto en `to_pulsar()` como en `from_pulsar()`.

### 2. Agregar un Productor de Explicabilidad al Servicio de Agente

**Archivo:** `trustgraph-flow/trustgraph/agent/react/service.py`

Registrar un productor de "explicabilidad" (mismo patrón que GraphRAG):
```python
from ... base import ProducerSpec
from ... schema import Triples

# In __init__:
self.register_specification(
    ProducerSpec(
        name = "explainability",
        schema = Triples,
    )
)
```

### 3. Generación de Triples de Proveniencia

**Archivo:** `trustgraph-base/trustgraph/provenance/agent.py`

Crear funciones auxiliares (similares a `question_triples`, `exploration_triples`, etc. de GraphRAG):
```python
def agent_session_triples(session_uri, query, timestamp):
    """Generate triples for agent Question."""
    return [
        Triple(s=session_uri, p=RDF_TYPE, o=PROV_ACTIVITY),
        Triple(s=session_uri, p=RDF_TYPE, o=TG_QUESTION),
        Triple(s=session_uri, p=TG_QUERY, o=query),
        Triple(s=session_uri, p=PROV_STARTED_AT_TIME, o=timestamp),
    ]

def agent_iteration_triples(iteration_uri, parent_uri, thought, action, arguments, observation):
    """Generate triples for one Analysis step."""
    return [
        Triple(s=iteration_uri, p=RDF_TYPE, o=PROV_ENTITY),
        Triple(s=iteration_uri, p=RDF_TYPE, o=TG_ANALYSIS),
        Triple(s=iteration_uri, p=TG_THOUGHT, o=thought),
        Triple(s=iteration_uri, p=TG_ACTION, o=action),
        Triple(s=iteration_uri, p=TG_ARGUMENTS, o=json.dumps(arguments)),
        Triple(s=iteration_uri, p=TG_OBSERVATION, o=observation),
        Triple(s=iteration_uri, p=PROV_WAS_DERIVED_FROM, o=parent_uri),
    ]

def agent_final_triples(final_uri, parent_uri, answer):
    """Generate triples for Conclusion."""
    return [
        Triple(s=final_uri, p=RDF_TYPE, o=PROV_ENTITY),
        Triple(s=final_uri, p=RDF_TYPE, o=TG_CONCLUSION),
        Triple(s=final_uri, p=TG_ANSWER, o=answer),
        Triple(s=final_uri, p=PROV_WAS_DERIVED_FROM, o=parent_uri),
    ]
```

### 4. Definiciones de tipo

**Archivo:** `trustgraph-base/trustgraph/provenance/namespaces.py`

Agregar tipos de entidad de explicabilidad y predicados de agente:
```python
# Explainability entity types (used by both GraphRAG and Agent)
TG_QUESTION = TG + "Question"
TG_EXPLORATION = TG + "Exploration"
TG_FOCUS = TG + "Focus"
TG_SYNTHESIS = TG + "Synthesis"
TG_ANALYSIS = TG + "Analysis"
TG_CONCLUSION = TG + "Conclusion"

# Agent predicates
TG_THOUGHT = TG + "thought"
TG_ACTION = TG + "action"
TG_ARGUMENTS = TG + "arguments"
TG_OBSERVATION = TG + "observation"
TG_ANSWER = TG + "answer"
```

## Archivos Modificados

| Archivo | Cambio |
|------|--------|
| `trustgraph-base/trustgraph/schema/services/agent.py` | Agregar session_id y collection a AgentRequest |
| `trustgraph-base/trustgraph/messaging/translators/agent.py` | Actualizar el traductor para nuevos campos |
| `trustgraph-base/trustgraph/provenance/namespaces.py` | Agregar tipos de entidad, predicados de agente y predicados de Document RAG |
| `trustgraph-base/trustgraph/provenance/triples.py` | Agregar tipos de TG a los constructores de triples de GraphRAG, agregar constructores de triples de Document RAG |
| `trustgraph-base/trustgraph/provenance/uris.py` | Agregar generadores de URI de Document RAG |
| `trustgraph-base/trustgraph/provenance/__init__.py` | Exportar nuevos tipos, predicados y funciones de Document RAG |
| `trustgraph-base/trustgraph/schema/services/retrieval.py` | Agregar explain_id y explain_graph a DocumentRagResponse |
| `trustgraph-base/trustgraph/messaging/translators/retrieval.py` | Actualizar DocumentRagResponseTranslator para campos de explicabilidad |
| `trustgraph-flow/trustgraph/agent/react/service.py` | Agregar lógica de productor y registro de explicabilidad |
| `trustgraph-flow/trustgraph/retrieval/document_rag/document_rag.py` | Agregar devolución de llamada de explicabilidad y emitir triples de procedencia |
| `trustgraph-flow/trustgraph/retrieval/document_rag/rag.py` | Agregar productor de explicabilidad y conectar la devolución de llamada |
| `trustgraph-cli/trustgraph/cli/show_explain_trace.py` | Manejar tipos de traza de agente |
| `trustgraph-cli/trustgraph/cli/list_explain_traces.py` | Listar sesiones de agente junto con GraphRAG |

## Archivos Creados

| Archivo | Propósito |
|------|---------|
| `trustgraph-base/trustgraph/provenance/agent.py` | Generadores de triples específicos del agente |

## Actualizaciones de la CLI

**Detección:** Tanto GraphRAG como las Preguntas del Agente tienen el tipo `tg:Question`. Se distinguen por:
1. Patrón de URI: `urn:trustgraph:agent:` vs `urn:trustgraph:question:`
2. Entidades derivadas: `tg:Analysis` (agente) vs `tg:Exploration` (GraphRAG)

**`list_explain_traces.py`:**
- Muestra la columna Tipo (Agente vs GraphRAG)

**`show_explain_trace.py`:**
- Detecta automáticamente el tipo de traza
- La representación del agente muestra: Pregunta → Paso(s) de análisis → Conclusión

## Compatibilidad con versiones anteriores

- `session_id` por defecto es `""` - las solicitudes antiguas funcionan, pero no tendrán procedencia
- `collection` por defecto es `"default"` - alternativa razonable
- La CLI maneja correctamente ambos tipos de traza

## Verificación

```bash
# Run an agent query
tg-invoke-agent -q "What is the capital of France?"

# List traces (should show agent sessions with Type column)
tg-list-explain-traces -U trustgraph -C default

# Show agent trace
tg-show-explain-trace "urn:trustgraph:agent:xxx"
```

## Trabajo Futuro (No Incluido en esta Solicitud de Incorporación)

- Dependencias de DAG (cuando el análisis N utiliza resultados de múltiples análisis anteriores)
- Enlace de procedencia específico de la herramienta (KnowledgeQuery → su traza GraphRAG)
- Emisión de procedencia en streaming (emitir a medida que se avanza, no en lote al final)
