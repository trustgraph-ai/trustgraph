# Cambios en la CLI: v1.8 a v2.1

## Resumen

La CLI (`trustgraph-cli`) tiene importantes adiciones centradas en tres temas:
**explicabilidad/origen**, **acceso a embeddings** y **consultas en el grafo**.
Se eliminaron dos herramientas heredadas, una se renombró y varias herramientas existentes
adquirieron nuevas capacidades.

---

## Nuevas Herramientas CLI

### Explicabilidad y Origen

| Comando | Descripción |
|---------|-------------|
| `tg-list-explain-traces` | Lista todas las sesiones de explicabilidad (GraphRAG y Agent) en una colección, mostrando los IDs de sesión, tipo, texto de la pregunta y marcas de tiempo. |
| `tg-show-explain-trace` | Muestra la traza completa de explicabilidad para una sesión. Para GraphRAG: Etapas de Pregunta, Exploración, Enfoque, Síntesis. Para Agent: Etapas de Sesión, Iteraciones (pensamiento/acción/observación), Respuesta Final. Detecta automáticamente el tipo de traza. Soporta la opción `--show-provenance` para rastrear los bordes de vuelta a los documentos originales. |
| `tg-show-extraction-provenance` | Dados un ID de documento, recorre la cadena de origen: Documento -> Páginas -> Bloques -> Bordes, utilizando las relaciones `prov:wasDerivedFrom`. Soporta las opciones `--show-content` y `--max-content`. |

### Embeddings

| Comando | Descripción |
|---------|-------------|
| `tg-invoke-embeddings` | Convierte texto en un embedding vectorial a través del servicio de embeddings. Acepta uno o más entradas de texto, devuelve vectores como listas de flotantes. |
| `tg-invoke-graph-embeddings` | Consulta entidades del grafo por similitud de texto utilizando embeddings vectoriales. Devuelve las entidades coincidentes con puntuaciones de similitud. |
| `tg-invoke-document-embeddings` | Consulta fragmentos de documentos por similitud de texto utilizando embeddings vectoriales. Devuelve los IDs de fragmentos coincidentes con puntuaciones de similitud. |
| `tg-invoke-row-embeddings` | Consulta filas de datos estructurados por similitud de texto en campos indexados. Devuelve las filas coincidentes con valores de índice y puntuaciones. Requiere `--schema-name` y soporta `--index-name`. |

### Consultas en el grafo

| Comando | Descripción |
|---------|-------------|
| `tg-query-graph` | Consulta basada en patrones para el almacén de triples. A diferencia de `tg-show-graph` (que muestra todo), esto permite consultas selectivas para cualquier combinación de sujeto, predicado, objeto y grafo. Detecta automáticamente los tipos de valor: IRIs (`http://...`, `urn:...`, `<...>`), triples anclados (`<<s p o>>`), y literales. |
| `tg-get-document-content` | Recupera el contenido del documento de la biblioteca por ID de documento. Puede mostrar en un archivo o en stdout, maneja tanto contenido de texto como binario. |

---

## Herramientas CLI eliminadas

| Comando | Notas |
|---------|-------|
| `tg-load-pdf` | Eliminado. La carga de documentos ahora se maneja a través de la biblioteca/pipeline de procesamiento. |
| `tg-load-text` | Eliminado. La carga de documentos ahora se maneja a través de la biblioteca/pipeline de procesamiento. |

---

## Herramientas CLI renombradas

| Nombre antiguo | Nombre nuevo | Notas |
|----------|----------|-------|
| `tg-invoke-objects-query` | `tg-invoke-rows-query` | Refleja el cambio de terminología de "objetos" a "filas" para datos estructurados. |

---

## Cambios Significativos en Herramientas Existentes

### `tg-invoke-graph-rag`

- **Soporte de explicabilidad**: Ahora soporta una tubería de explicabilidad de 4 etapas (Pregunta, Fundamentación/Exploración, Enfoque, Síntesis) con visualización de eventos de origen en línea.
- **Streaming**: Utiliza el streaming de WebSocket para la salida en tiempo real.
- **Rastreo de origen**: Puede rastrear bordes seleccionados de vuelta a los documentos originales a través de la reificación y cadenas `prov:wasDerivedFrom`.
- Crecer de ~30 líneas a ~760 líneas para acomodar la tubería de explicabilidad completa.

### `tg-invoke-document-rag`

- **Soporte de explicabilidad**: Añadido el modo `question_explainable()` que transmite las respuestas de RAG de Documento con eventos de origen en línea (etapas de Pregunta, Fundamentación, Exploración, Síntesis).

### `tg-invoke-agent`

- **Soporte de explicabilidad**: Añadido el modo `question_explainable()` que muestra los eventos de origen en línea durante la ejecución del agente (etapas de Pregunta, Análisis, Conclusión, AgentThought, AgentObservation, AgentAnswer).
- El modo verboso muestra las transmisiones de pensamentos/observaciones con prefijos de emojis.

### `tg-show-graph`

- **Modo de streaming**: Ahora utiliza `triples_query_stream()` con tamaños de lote configurables para un tiempo de primer resultado más bajo y una menor sobrecarga de memoria.
- **Soporte de grafo nombrado**: Nueva opción `--graph` de filtro. Reconoce grafos nombrados:
  - Grafo predeterminado (vacío): Hechos de conocimiento básicos
  - `urn:graph:source`: Origen de extracción
  - `urn:graph:retrieval`: Explicabilidad en tiempo de consulta
- **Mostrar columna de grafo**: Nueva bandera `--show-graph` para mostrar el grafo nombrado para cada triple.
- **Límites configurables**: Nuevas opciones `--limit` y `--batch-size`.

### `tg-graph-to-turtle`

- **Soporte de RDF-star**: Ahora maneja triples anclados (reificación de RDF-star).
- **Modo de streaming**: Utiliza streaming para un tiempo de procesamiento más rápido.
- **Manejo del formato de cable**: Actualizado para utilizar el nuevo formato de cable (`{"t": "i", "i": uri}` para IRIs, `{"t": "l", "v": value}` para literales, `{"t": "r", "r": {...}}` para triples anclados)
- **Soporte de grafo nombrado**: Nueva opción `--graph` de filtro.

### `tg-set-tool`

- **Nuevo tipo de herramienta**: `row-embeddings-query` para búsqueda semántica en índices de datos estructurados.
- **Nuevas opciones**: `--schema-name`, `--index-name`, `--limit` para configurar herramientas de consulta de embeddings de fila.

### `tg-show-tools`

- Muestra el nuevo tipo de herramienta `row-embeddings-query` con sus campos `schema-name`, `index-name` y `limit`.

### `tg-load-knowledge`

- **Informes de progreso**: Ahora cuenta y reporta los triples y contextos de entidad cargados por archivo y en total.
- **Actualización del formato de término**: Los contextos de entidad ahora utilizan el nuevo formato de término (`{"t": "i", "i": uri}`) en lugar del formato de valor antiguo (`{"v": ..., "e": ...}`).

---

## Cambios de rompimiento

- **Cambio de terminología**: El esquema `Value` se renombró a `Term` en todo el sistema (PR #622). Esto afecta al formato de cable utilizado por las herramientas CLI que interactúan con el almacén de grafos. El nuevo formato utiliza `{"t": "i", "i": uri}` para IRIs y `{"t": "l", "v": value}` para literales, reemplazando el formato antiguo `{"v": ..., "e": ...}`.
- **`tg-invoke-objects-query` renombrado** a `tg-invoke-rows-query`.
- **`tg-load-pdf` y `tg-load-text` eliminados**.