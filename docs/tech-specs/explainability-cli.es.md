---
layout: default
title: "Especificación Técnica de la CLI para Explicabilidad"
parent: "Spanish (Beta)"
---

# Especificación Técnica de la CLI para Explicabilidad

> **Beta Translation:** This document was translated via Machine Learning and as such may not be 100% accurate. All non-English languages are currently classified as Beta.

## Estado

Borrador

## Visión General

Esta especificación describe las herramientas de CLI para depurar y explorar datos de explicabilidad en TrustGraph. Estas herramientas permiten a los usuarios rastrear cómo se derivaron las respuestas y depurar la cadena de origen desde los bordes hasta los documentos fuente.

Tres herramientas de CLI:

1.  **`tg-show-document-hierarchy`** - Muestra la jerarquía documento → página → fragmento → borde
2.  **`tg-list-explain-traces`** - Lista todas las sesiones GraphRAG con preguntas
3.  **`tg-show-explain-trace`** - Muestra la trazabilidad completa de explicabilidad para una sesión

## Objetivos

-   **Depuración**: Permitir a los desarrolladores inspeccionar los resultados del procesamiento de documentos.
-   **Auditabilidad**: Rastrear cualquier hecho extraído hasta su documento fuente.
-   **Transparencia**: Mostrar exactamente cómo GraphRAG derivó una respuesta.
-   **Usabilidad**: Interfaz CLI sencilla con valores predeterminados apropiados.

## Antecedentes

TrustGraph tiene dos sistemas de origen:

1.  **Origen en tiempo de extracción** (ver `extraction-time-provenance.md`): Registra las relaciones documento → página → fragmento → borde durante la ingestión. Almacenado en el gráfico llamado `urn:graph:source` utilizando `prov:wasDerivedFrom`.

2.  **Explicabilidad en tiempo de consulta** (ver `query-time-explainability.md`): Registra la cadena de pregunta → exploración → enfoque → síntesis durante las consultas GraphRAG. Almacenado en el gráfico llamado `urn:graph:retrieval`.

Limitaciones actuales:

-   No hay una manera fácil de visualizar la jerarquía del documento después del procesamiento.
-   Se deben consultar manualmente los triples para ver los datos de explicabilidad.
-   No hay una vista consolidada de una sesión GraphRAG.

## Diseño Técnico

### Herramienta 1: `tg-show-document-hierarchy`

**Propósito**: Dado un ID de documento, recorrer y mostrar todas las entidades derivadas.

**Uso**:
```bash
tg-show-document-hierarchy "urn:trustgraph:doc:abc123"
tg-show-document-hierarchy --show-content --max-content 500 "urn:trustgraph:doc:abc123"
```

**Argumentos**:
| Arg | Descripción |
|---|---|
| `document_id` | URI del documento (posicional) |
| `-u/--api-url` | URL del gateway (por defecto: `$TRUSTGRAPH_URL`) |
| `-t/--token` | Token de autenticación (por defecto: `$TRUSTGRAPH_TOKEN`) |
| `-U/--user` | ID de usuario (por defecto: `trustgraph`) |
| `-C/--collection` | Colección (por defecto: `default`) |
| `--show-content` | Incluir el contenido del blob/documento |
| `--max-content` | Máx. caracteres por blob (por defecto: 200) |
| `--format` | Salida: `tree` (por defecto), `json` |

**Implementación**:
1.  Consultar triples: `?child prov:wasDerivedFrom <document_id>` en `urn:graph:source`
2.  Consultar recursivamente los hijos de cada resultado
3.  Construir la estructura del árbol: Documento → Páginas → Fragmentos
4.  Si `--show-content`, recuperar el contenido de la API del bibliotecario
5.  Mostrar como árbol anidado o JSON

**Ejemplo de Salida**:
```
Document: urn:trustgraph:doc:abc123
  Título: "Sample PDF"
  Tipo: application/pdf

  └── Página 1: urn:trustgraph:doc:abc123/p1
      ├── Fragmento 0: urn:trustgraph:doc:abc123/p1/c0
          Contenido: "The quick brown fox..." [truncado]
      └── Fragmento 1: urn:trustgraph:doc:abc123/p1/c1
          Contenido: "Machine learning is..." [truncado]
```

### Herramienta 2: `tg-list-explain-traces`

**Propósito**: Listar todas las sesiones GraphRAG (preguntas) en una colección.

**Uso**:
```bash
tg-list-explain-traces
tg-list-explain-traces --limit 20 --format json
```

**Argumentos**:
| Arg | Descripción |
|---|---|
| `-u/--api-url` | URL del gateway |
| `-t/--token` | Token de autenticación |
| `-U/--user` | ID de usuario |
| `-C/--collection` | Colección |
| `--limit` | Máx. resultados (por defecto: 50) |
| `--format` | Salida: `table` (por defecto), `json` |

**Implementación**:
1.  Consultar: `?session tg:query ?text` en `urn:graph:retrieval`
2.  Consultar los tiempos: `?session prov:startedAtTime ?time`
3.  Mostrar como tabla

**Ejemplo de Salida**:
```
Session ID                                    | Pregunta                        | Tiempo
----------------------------------------------|--------------------------------|---------------------
urn:trustgraph:question:abc123                | ¿Cuál fue la Guerra Fría?    | 2024-01-15 10:30:00
urn:trustgraph:question:def456                | ¿Quién fundó la NASA?            | 2024-01-15 09:15:00
```

### Herramienta 3: `tg-show-explain-trace`

**Propósito**: Mostrar la trazabilidad completa de explicabilidad para una sesión GraphRAG.

**Uso**:
```bash
tg-show-explain-trace "urn:trustgraph:question:abc123"
tg-show-explain-trace --max-answer 1000 --show-provenance "urn:trustgraph:question:abc123"
```

**Argumentos**:
| Arg | Descripción |
|---|---|
| `question_id` | URI de la pregunta (posicional) |
| `-u/--api-url` | URL del gateway |
| `-t/--token` | Token de autenticación |
| `-U/--user` | ID de usuario |
| `-C/--collection` | Colección |
| `--max-answer` | Máx. caracteres para la respuesta (por defecto: 500) |
| `--show-provenance` | Rastrear los bordes hasta los documentos fuente |
| `--format` | Salida: `text` (por defecto), `json` |

**Implementación**:
1.  Obtener el texto de la pregunta del predicado `tg:query`
2.  Encontrar la exploración: `?exp prov:wasGeneratedBy <question_id>`
3.  Encontrar el enfoque: `?focus prov:wasDerivedFrom <exploration_id>`
4.  Obtener los bordes seleccionados: `<focus_id> tg:selectedEdge ?edge`
5.  Para cada borde, obtener `tg:edge` (triple acotado) y `tg:reasoning`
6.  Encontrar la síntesis: `?synth prov:wasDerivedFrom <focus_id>`
7.  Obtener la respuesta del documento a través de la API del bibliotecario
8.  Si `--show-provenance`, rastrear los bordes hasta los documentos fuente

**Ejemplo de Salida**:
```
=== Sesión GraphRAG: urn:trustgraph:question:abc123 ===

Pregunta: ¿Cuál fue la Guerra Fría?
Tiempo: 2024-01-15 10:30:00

--- Exploración ---
Se recuperaron 50 bordes de la gráfica de conocimiento

--- Enfoque (Selección de Bordes) ---
Se seleccionaron 12 bordes:

  1.  "The Cold War"
  2.  "Yuri Andropov"
  3.  "Khrushchev"
  4.  "NATO"
  5.  "Warsaw Pact"
  6.  "Berlin Wall"
  7.  "Cuban Missile Crisis"
  8.  "Detente"
  9.  "Détente"
  10. "Joseph Stalin"
  11. "Nikita Khrushchev"
  12. "US-Soviet Relations"

--- Trazabilidad ---
```

## Referencias

-   CLI de explicabilidad: `docs/tech-specs/query-time-explainability.md`
-   Origen en tiempo de extracción: `docs/tech-specs/extraction-time-provenance.md`
-   Ejemplo de CLI: `trustgraph-cli/trustgraph/cli/invoke_graph_rag.py`
