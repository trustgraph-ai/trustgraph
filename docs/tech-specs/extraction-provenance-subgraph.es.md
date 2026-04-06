# Origen de la extracción: Modelo de subgrafo

## Problema

Actualmente, la generación de la procedencia en tiempo de extracción crea una reificación completa por cada
triple extraído: un `stmt_uri`, `activity_uri` y metadatos PROV-O asociados para cada hecho de conocimiento. El procesamiento de un bloque
que produce 20 relaciones genera aproximadamente 220 triples de procedencia además de los aproximadamente 20 triples de conocimiento, lo que supone una sobrecarga de aproximadamente 10:1.

Esto es costoso (almacenamiento, indexación, transmisión) y semánticamente
inexacto. Cada bloque se procesa mediante una única llamada a un LLM que produce
todos sus triples en una sola transacción. El modelo actual, que es por triple,
oscurece esto al crear la ilusión de 20 eventos de extracción independientes.


Además, dos de los cuatro procesadores de extracción (kg-extract-ontology,
kg-extract-agent) no tienen ninguna procedencia, lo que deja lagunas en el
registro de auditoría.


## Solución


Reemplazar la reificación por triple con un **modelo de subgrafo**: un único
registro de procedencia por extracción de bloque, compartido entre todos los triples producidos a partir de ese
bloque.

### Cambio de terminología

| Antiguo | Nuevo |
|-----|-----|
| `stmt_uri` (`https://trustgraph.ai/stmt/{uuid}`) | `subgraph_uri` (`https://trustgraph.ai/subgraph/{uuid}`) |
| `statement_uri()` | `subgraph_uri()` |
| `tg:reifies` (1:1, identidad) | `tg:contains` (1:muchos, contención) |

### Estructura objetivo

Todos los triples de procedencia se almacenan en el grafo con nombre `urn:graph:source`.

```
# Subgraph contains each extracted triple (RDF-star quoted triples)
<subgraph> tg:contains <<s1 p1 o1>> .
<subgraph> tg:contains <<s2 p2 o2>> .
<subgraph> tg:contains <<s3 p3 o3>> .

# Derivation from source chunk
<subgraph> prov:wasDerivedFrom <chunk_uri> .
<subgraph> prov:wasGeneratedBy <activity> .

# Activity: one per chunk extraction
<activity> rdf:type          prov:Activity .
<activity> rdfs:label        "{component_name} extraction" .
<activity> prov:used         <chunk_uri> .
<activity> prov:wasAssociatedWith <agent> .
<activity> prov:startedAtTime "2026-03-13T10:00:00Z" .
<activity> tg:componentVersion "0.25.0" .
<activity> tg:llmModel       "gpt-4" .          # if available
<activity> tg:ontology        <ontology_uri> .   # if available

# Agent: stable per component
<agent> rdf:type   prov:Agent .
<agent> rdfs:label "{component_name}" .
```

### Comparación de volúmenes

Para un bloque que produce N triples extraídos:

| | Viejo (por triple) | Nuevo (subgrafo) |
|---|---|---|
| `tg:contains` / `tg:reifies` | N | N |
| Triples de actividad | ~9 x N | ~9 |
| Triples de agente | 2 x N | 2 |
| Metadatos de declaración/subgrafo | 2 x N | 2 |
| **Total de triples de procedencia** | **~13N** | **N + 13** |
| **Ejemplo (N=20)** | **~260** | **33** |

## Alcance

### Procesadores a Actualizar (procedencia existente, por triple)

**kg-extract-definitions**
(`trustgraph-flow/trustgraph/extract/kg/definitions/extract.py`)

Actualmente llama a `statement_uri()` + `triple_provenance_triples()` dentro
del bucle por definición.

Cambios:
Mover la creación de `subgraph_uri()` y `activity_uri()` antes del bucle
Recolectar los triples `tg:contains` dentro del bucle
Emitir el bloque compartido de actividad/agente una vez después del bucle

**kg-extract-relationships**
(`trustgraph-flow/trustgraph/extract/kg/relationships/extract.py`)

Mismo patrón que definiciones. Mismos cambios.

### Procesadores a Agregar Procedencia (actualmente ausente)

**kg-extract-ontology**
(`trustgraph-flow/trustgraph/extract/kg/ontology/extract.py`)

Actualmente emite triples sin procedencia. Agregar procedencia de subgrafo
utilizando el mismo patrón: un subgrafo por bloque, `tg:contains` para cada
triple extraído.

**kg-extract-agent**
(`trustgraph-flow/trustgraph/extract/kg/agent/extract.py`)

Actualmente emite triples sin procedencia. Agregar procedencia de subgrafo
utilizando el mismo patrón.

### Cambios en la Biblioteca Compartida de Procedencia

**`trustgraph-base/trustgraph/provenance/triples.py`**

Reemplazar `triple_provenance_triples()` con `subgraph_provenance_triples()`
Nueva función acepta una lista de triples extraídos en lugar de uno solo
Genera un `tg:contains` por triple, bloque compartido de actividad/agente
Eliminar el `triple_provenance_triples()` antiguo

**`trustgraph-base/trustgraph/provenance/uris.py`**

Reemplazar `statement_uri()` con `subgraph_uri()`

**`trustgraph-base/trustgraph/provenance/namespaces.py`**

Reemplazar `TG_REIFIES` con `TG_CONTAINS`

### No Incluido en el Alcance

**kg-extract-topics**: procesador de estilo antiguo, no se utiliza actualmente en
  flujos estándar
**kg-extract-rows**: produce filas no triples, modelo de procedencia
  diferente
**Procedencia en tiempo de consulta** (`urn:graph:retrieval`): preocupación separada,
  ya utiliza un patrón diferente (pregunta/exploración/énfasis/síntesis)
**Procedencia de documento/página/bloque** (decodificador de PDF, segmentador): ya utiliza
  `derived_entity_triples()` que es por entidad, no por triple — no hay
  problema de redundancia

## Notas de Implementación

### Reestructuración del Bucle del Procesador

Antes (por triple, en relaciones):
```python
for rel in rels:
    # ... build relationship_triple ...
    stmt_uri = statement_uri()
    prov_triples = triple_provenance_triples(
        stmt_uri=stmt_uri,
        extracted_triple=relationship_triple,
        ...
    )
    triples.extend(set_graph(prov_triples, GRAPH_SOURCE))
```

Después (subgrafo):
```python
sg_uri = subgraph_uri()

for rel in rels:
    # ... build relationship_triple ...
    extracted_triples.append(relationship_triple)

prov_triples = subgraph_provenance_triples(
    subgraph_uri=sg_uri,
    extracted_triples=extracted_triples,
    chunk_uri=chunk_uri,
    component_name=default_ident,
    component_version=COMPONENT_VERSION,
    llm_model=llm_model,
    ontology_uri=ontology_uri,
)
triples.extend(set_graph(prov_triples, GRAPH_SOURCE))
```

### Nueva Firma de Asistente

```python
def subgraph_provenance_triples(
    subgraph_uri: str,
    extracted_triples: List[Triple],
    chunk_uri: str,
    component_name: str,
    component_version: str,
    llm_model: Optional[str] = None,
    ontology_uri: Optional[str] = None,
    timestamp: Optional[str] = None,
) -> List[Triple]:
    """
    Build provenance triples for a subgraph of extracted knowledge.

    Creates:
    - tg:contains link for each extracted triple (RDF-star quoted)
    - One prov:wasDerivedFrom link to source chunk
    - One activity with agent metadata
    """
```

### Cambio importante

Este es un cambio importante en el modelo de trazabilidad. La trazabilidad no
se ha publicado, por lo que no se necesita ninguna migración. El código antiguo `tg:reifies` /
`statement_uri` se puede eliminar por completo.
