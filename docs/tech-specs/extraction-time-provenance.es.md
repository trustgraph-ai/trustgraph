# Proveniencia en Tiempo de Extracción: Capa de Origen

## Resumen

Este documento captura notas sobre la proveniencia en tiempo de extracción para futuros trabajos de especificación. La proveniencia en tiempo de extracción registra la "capa de origen": de dónde provienen los datos originalmente, cómo se extrajeron y transformaron.

Esto es diferente de la proveniencia en tiempo de consulta (ver `query-time-provenance.md`), que registra el razonamiento del agente.

## Declaración del Problema

### Implementación Actual

Actualmente, la proveniencia funciona de la siguiente manera:
Los metadatos del documento se almacenan como triples RDF en el grafo de conocimiento.
Un ID de documento vincula los metadatos al documento, de modo que el documento aparece como un nodo en el grafo.
Cuando se extraen aristas (relaciones/hechos) de los documentos, una relación `subjectOf` vincula la arista extraída con el documento de origen.

### Problemas con el Enfoque Actual

1. **Carga repetitiva de metadatos:** Los metadatos del documento se empaquetan y cargan repetidamente con cada lote de triples extraídos de ese documento. Esto es un desperdicio y redundante: los mismos metadatos viajan como carga con cada salida de extracción.

2. **Proveniencia superficial:** La relación `subjectOf` actual solo vincula los hechos directamente con el documento de nivel superior. No hay visibilidad de la cadena de transformación: qué página proporcionó el hecho, qué fragmento, qué método de extracción se utilizó.

### Estado Deseado

1. **Cargar metadatos una vez:** Los metadatos del documento deben cargarse una vez y adjuntarse al nodo del documento de nivel superior, no repetirse con cada lote de triples.

2. **DAG de proveniencia rica:** Capturar toda la cadena de transformación desde el documento de origen a través de todos los artefactos intermedios hasta los hechos extraídos. Por ejemplo, una transformación de un documento PDF:

   ```
   PDF file (source document with metadata)
     → Page 1 (decoded text)
       → Chunk 1
         → Extracted edge/fact (via subjectOf)
         → Extracted edge/fact
       → Chunk 2
         → Extracted edge/fact
     → Page 2
       → Chunk 3
         → ...
   ```

3. **Almacenamiento unificado:** El grafo de procedencia se almacena en el mismo grafo de conocimiento que el conocimiento extraído. Esto permite consultar la procedencia de la misma manera que se consulta el conocimiento: siguiendo los enlaces hacia atrás a lo largo de la cadena desde cualquier hecho hasta su ubicación de origen exacta.

4. **Identificadores estables:** Cada artefacto intermedio (página, fragmento) tiene un identificador estable como un nodo en el grafo.

5. **Enlace padre-hijo:** Los documentos derivados se vinculan a sus padres hasta el documento fuente de nivel superior, utilizando tipos de relación consistentes.

6. **Atribución precisa de hechos:** La relación `subjectOf` en los bordes extraídos apunta al padre inmediato (fragmento), no al documento de nivel superior. La procedencia completa se recupera recorriendo el DAG.

## Casos de uso

### UC1: Atribución de la fuente en las respuestas de GraphRAG

**Escenario:** Un usuario ejecuta una consulta de GraphRAG y recibe una respuesta del agente.

**Flujo:**
1. El usuario envía una consulta al agente de GraphRAG.
2. El agente recupera hechos relevantes del grafo de conocimiento para formular una respuesta.
3. De acuerdo con la especificación de procedencia en tiempo de consulta, el agente informa qué hechos contribuyeron a la respuesta.
4. Cada hecho se vincula a su fragmento de origen a través del grafo de procedencia.
5. Los fragmentos se vinculan a páginas, las páginas se vinculan a documentos fuente.

**Resultado de la experiencia de usuario:** La interfaz muestra la respuesta del LLM junto con la atribución de la fuente. El usuario puede:
Ver qué hechos respaldaron la respuesta.
Profundizar desde hechos → fragmentos → páginas → documentos.
Examinar los documentos fuente originales para verificar las afirmaciones.
Comprender exactamente dónde en un documento (en qué página, en qué sección) se originó un hecho.

**Valor:** Los usuarios pueden verificar las respuestas generadas por la IA con fuentes primarias, lo que genera confianza y permite la verificación de hechos.

### UC2: Depuración de la calidad de la extracción

Un hecho parece incorrecto. Rastrear hacia atrás a través del fragmento → página → documento para ver el texto original. ¿Fue una mala extracción, o la fuente en sí misma estaba equivocada?

### UC3: Reextracción incremental

El documento fuente se actualiza. ¿Qué fragmentos/hechos se derivaron de él? Invalidar y regenerar solo esos, en lugar de volver a procesar todo.

### UC4: Eliminación de datos / Derecho al olvido

Se debe eliminar un documento fuente (GDPR, legal, etc.). Recorrer el DAG para encontrar y eliminar todos los hechos derivados.

### UC5: Resolución de conflictos

Dos hechos se contradicen. Rastrear ambos hasta sus fuentes para comprender por qué y decidir a cuál confiar (fuente más autorizada, más reciente, etc.).

### UC6: Ponderación de la autoridad de la fuente

Algunas fuentes son más autorizadas que otras. Los hechos se pueden ponderar o filtrar según la autoridad/calidad de sus documentos de origen.

### UC7: Comparación de la canalización de extracción

Comparar los resultados de diferentes métodos/versiones de extracción. ¿Qué extractor produjo mejores hechos del mismo documento fuente?

## Puntos de integración

### Bibliotecario

El componente de bibliotecario ya proporciona almacenamiento de documentos con identificadores de documentos únicos. El sistema de procedencia se integra con esta infraestructura existente.

#### Capacidades existentes (ya implementadas)

**Vinculación de documentos padre-hijo:**
Campo `parent_id` en `DocumentMetadata`: vincula el documento hijo al documento padre.
Campo `document_type`: valores: `"source"` (original) o `"extracted"` (derivado).
API `add-child-document`: crea un documento hijo con `document_type = "extracted"` automático.
API `list-children`: recupera todos los hijos de un documento padre.
Eliminación en cascada: eliminar un padre elimina automáticamente todos los documentos hijo.

**Identificación de documentos:**
Los identificadores de documentos son especificados por el cliente (no generados automáticamente).
Documentos indexados por una clave compuesta `(user, document_id)` en Cassandra.
Identificadores de objetos (UUID) generados internamente para el almacenamiento de blobs.

**Soporte de metadatos:**
Campo `metadata: list[Triple]`: triples RDF para metadatos estructurados.
`title`, `comments`, `tags`: metadatos básicos del documento.
`time`: marca de tiempo, `kind`: tipo MIME.

**Arquitectura de almacenamiento:**
Los metadatos se almacenan en Cassandra (espacio de claves `librarian`, tabla `document`).
El contenido se almacena en MinIO/S3 blob storage (cubeta `library`).
Entrega inteligente de contenido: documentos < 2 MB incrustados, documentos más grandes transmitidos por flujo.

#### Archivos clave

`trustgraph-flow/trustgraph/librarian/librarian.py`: operaciones principales del bibliotecario.
`trustgraph-flow/trustgraph/librarian/service.py`: procesador de servicios, carga de documentos.
`trustgraph-flow/trustgraph/tables/library.py`: almacén de tablas de Cassandra.
`trustgraph-base/trustgraph/schema/services/library.py`: definiciones de esquema.

#### Aspectos a abordar

El bibliotecario tiene los componentes básicos, pero actualmente:
1. La vinculación padre-hijo es de un solo nivel: no hay ayudantes de recorrido de DAG multinivel.
2. No hay un vocabulario estándar de tipos de relación (por ejemplo, `derivedFrom`, `extractedFrom`).
3. Los metadatos de procedencia (método de extracción, confianza, posición de fragmento) no están estandarizados.
4. No hay una API de consulta para recorrer toda la cadena de procedencia desde un hecho hasta la fuente.

## Diseño de flujo de extremo a extremo

Cada procesador en la canalización sigue un patrón consistente:
Recibe el ID del documento del componente anterior.
Recupera el contenido del bibliotecario.
Produce artefactos secundarios.
Para cada hijo: guarda en el bibliotecario, emite un borde al gráfico, reenvía el ID al componente posterior.

### Flujos de procesamiento

Existen dos flujos dependiendo del tipo de documento:

#### Flujo de documento PDF

```
┌─────────────────────────────────────────────────────────────────────────┐
│ Librarian (initiate processing)                                         │
│   1. Emit root document metadata to knowledge graph (once)              │
│   2. Send root document ID to PDF extractor                             │
└─────────────────────────────────────────────────────────────────────────┘
                                    │
                                    ▼
┌─────────────────────────────────────────────────────────────────────────┐
│ PDF Extractor (per page)                                                │
│   1. Fetch PDF content from librarian using document ID                 │
│   2. Extract pages as text                                              │
│   3. For each page:                                                     │
│      a. Save page as child document in librarian (parent = root doc)   │
│      b. Emit parent-child edge to knowledge graph                       │
│      c. Send page document ID to chunker                                │
└─────────────────────────────────────────────────────────────────────────┘
                                    │
                                    ▼
┌─────────────────────────────────────────────────────────────────────────┐
│ Chunker (per chunk)                                                     │
│   1. Fetch page content from librarian using document ID                │
│   2. Split text into chunks                                             │
│   3. For each chunk:                                                    │
│      a. Save chunk as child document in librarian (parent = page)      │
│      b. Emit parent-child edge to knowledge graph                       │
│      c. Send chunk document ID + chunk content to next processor        │
└─────────────────────────────────────────────────────────────────────────┘
                                    │
                                    ▼
          ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─
          Post-chunker optimization: messages carry both
          chunk ID (for provenance) and content (to avoid
          librarian round-trip). Chunks are small (2-4KB).
          ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─
                                    │
                                    ▼
┌─────────────────────────────────────────────────────────────────────────┐
│ Knowledge Extractor (per chunk)                                         │
│   1. Receive chunk ID + content directly (no librarian fetch needed)   │
│   2. Extract facts/triples and embeddings from chunk content            │
│   3. For each triple:                                                   │
│      a. Emit triple to knowledge graph                                  │
│      b. Emit reified edge linking triple → chunk ID (edge pointing     │
│         to edge - first use of reification support)                     │
│   4. For each embedding:                                                │
│      a. Emit embedding with its entity ID                               │
│      b. Link entity ID → chunk ID in knowledge graph                   │
└─────────────────────────────────────────────────────────────────────────┘
```

#### Flujo de documentos de texto

Los documentos de texto omiten el extractor de PDF y van directamente al fragmentador:

```
┌─────────────────────────────────────────────────────────────────────────┐
│ Librarian (initiate processing)                                         │
│   1. Emit root document metadata to knowledge graph (once)              │
│   2. Send root document ID directly to chunker (skip PDF extractor)    │
└─────────────────────────────────────────────────────────────────────────┘
                                    │
                                    ▼
┌─────────────────────────────────────────────────────────────────────────┐
│ Chunker (per chunk)                                                     │
│   1. Fetch text content from librarian using document ID                │
│   2. Split text into chunks                                             │
│   3. For each chunk:                                                    │
│      a. Save chunk as child document in librarian (parent = root doc) │
│      b. Emit parent-child edge to knowledge graph                       │
│      c. Send chunk document ID + chunk content to next processor        │
└─────────────────────────────────────────────────────────────────────────┘
                                    │
                                    ▼
┌─────────────────────────────────────────────────────────────────────────┐
│ Knowledge Extractor                                                     │
│   (same as PDF flow)                                                    │
└─────────────────────────────────────────────────────────────────────────┘
```

El DAG resultante es un nivel más corto:

```
PDF:  Document → Pages → Chunks → Triples/Embeddings
Text: Document → Chunks → Triples/Embeddings
```

El diseño se adapta a ambos porque el componente de segmentación trata su entrada de forma genérica; utiliza cualquier ID de documento que reciba como elemento padre, independientemente de si se trata de un documento fuente o de una página.

### Esquema de metadatos (PROV-O)

Los metadatos de procedencia utilizan la ontología W3C PROV-O. Esto proporciona un vocabulario estándar y permite la futura firma/autenticación de los resultados de la extracción.

#### Conceptos principales de PROV-O

| Tipo PROV-O | Uso en TrustGraph |
|-------------|------------------|
| `prov:Entity` | Documento, Página, Segmento, Triple, Incrustación |
| `prov:Activity` | Instancias de operaciones de extracción |
| `prov:Agent` | Componentes de TG (extractor de PDF, segmentador, etc.) con versiones |

#### Relaciones PROV-O

| Predicado | Significado | Ejemplo |
|-----------|---------|---------|
| `prov:wasDerivedFrom` | Entidad derivada de otra entidad | Página wasDerivedFrom Documento |
| `prov:wasGeneratedBy` | Entidad generada por una actividad | Página wasGeneratedBy PDFExtractionActivity |
| `prov:used` | Actividad que utiliza una entidad como entrada | PDFExtractionActivity used Documento |
| `prov:wasAssociatedWith` | Actividad realizada por un agente | PDFExtractionActivity wasAssociatedWith tg:PDFExtractor |

#### Metadatos en cada nivel

**Documento fuente (emitido por Librarian):**
```
doc:123 a prov:Entity .
doc:123 dc:title "Research Paper" .
doc:123 dc:source <https://example.com/paper.pdf> .
doc:123 dc:date "2024-01-15" .
doc:123 dc:creator "Author Name" .
doc:123 tg:pageCount 42 .
doc:123 tg:mimeType "application/pdf" .
```

**Página (emitida por el extractor de PDF):**
```
page:123-1 a prov:Entity .
page:123-1 prov:wasDerivedFrom doc:123 .
page:123-1 prov:wasGeneratedBy activity:pdf-extract-456 .
page:123-1 tg:pageNumber 1 .

activity:pdf-extract-456 a prov:Activity .
activity:pdf-extract-456 prov:used doc:123 .
activity:pdf-extract-456 prov:wasAssociatedWith tg:PDFExtractor .
activity:pdf-extract-456 tg:componentVersion "1.2.3" .
activity:pdf-extract-456 prov:startedAtTime "2024-01-15T10:30:00Z" .
```

**Fragmento (emitido por el procesador de fragmentos):**
```
chunk:123-1-1 a prov:Entity .
chunk:123-1-1 prov:wasDerivedFrom page:123-1 .
chunk:123-1-1 prov:wasGeneratedBy activity:chunk-789 .
chunk:123-1-1 tg:chunkIndex 1 .
chunk:123-1-1 tg:charOffset 0 .
chunk:123-1-1 tg:charLength 2048 .

activity:chunk-789 a prov:Activity .
activity:chunk-789 prov:used page:123-1 .
activity:chunk-789 prov:wasAssociatedWith tg:Chunker .
activity:chunk-789 tg:componentVersion "1.0.0" .
activity:chunk-789 tg:chunkSize 2048 .
activity:chunk-789 tg:chunkOverlap 200 .
```

**Triple (emitido por el Extractor de Conocimiento):**
```
# The extracted triple (edge)
entity:JohnSmith rel:worksAt entity:AcmeCorp .

# Subgraph containing the extracted triples
subgraph:001 tg:contains <<entity:JohnSmith rel:worksAt entity:AcmeCorp>> .
subgraph:001 prov:wasDerivedFrom chunk:123-1-1 .
subgraph:001 prov:wasGeneratedBy activity:extract-999 .

activity:extract-999 a prov:Activity .
activity:extract-999 prov:used chunk:123-1-1 .
activity:extract-999 prov:wasAssociatedWith tg:KnowledgeExtractor .
activity:extract-999 tg:componentVersion "2.1.0" .
activity:extract-999 tg:llmModel "claude-3" .
activity:extract-999 tg:ontology <http://example.org/ontologies/business-v1> .
```

**Incrustación (almacenada en un almacén de vectores, no en un almacén de triples):**

Las incrustaciones se almacenan en el almacén de vectores con metadatos, no como triples RDF. Cada registro de incrustación contiene:

| Campo | Descripción | Ejemplo |
|-------|-------------|---------|
| vector | El vector de incrustación | [0.123, -0.456, ...] |
| entity | URI del nodo que representa la incrustación | `entity:JohnSmith` |
| chunk_id | Fragmento de origen (procedencia) | `chunk:123-1-1` |
| model | Modelo de incrustación utilizado | `text-embedding-ada-002` |
| component_version | Versión del incrustador de TG | `1.0.0` |

El campo `entity` vincula la incrustación al grafo de conocimiento (URI del nodo). El campo `chunk_id` proporciona la procedencia de vuelta al fragmento de origen, lo que permite el recorrido ascendente del DAG hasta el documento original.

#### Extensiones del Espacio de Nombres de TrustGraph

Predicados personalizados dentro del espacio de nombres `tg:` para metadatos específicos de la extracción:

| Predicado | Dominio | Descripción |
|-----------|--------|-------------|
| `tg:contains` | Subgrafo | Indica un triple contenido en este subgrafo de extracción |
| `tg:pageCount` | Documento | Número total de páginas en el documento de origen |
| `tg:mimeType` | Documento | Tipo MIME del documento de origen |
| `tg:pageNumber` | Página | Número de página en el documento de origen |
| `tg:chunkIndex` | Fragmento | Índice del fragmento dentro del fragmento principal |
| `tg:charOffset` | Fragmento | Desplazamiento de caracteres en el texto principal |
| `tg:charLength` | Fragmento | Longitud del fragmento en caracteres |
| `tg:chunkSize` | Actividad | Tamaño de fragmento configurado |
| `tg:chunkOverlap` | Actividad | Solapamiento configurado entre fragmentos |
| `tg:componentVersion` | Actividad | Versión del componente de TG |
| `tg:llmModel` | Actividad | LLM utilizado para la extracción |
| `tg:ontology` | Actividad | URI de la ontología utilizada para guiar la extracción |
| `tg:embeddingModel` | Actividad | Modelo utilizado para las incrustaciones |
| `tg:sourceText` | Declaración | Texto exacto del cual se extrajo un triple |
| `tg:sourceCharOffset` | Declaración | Desplazamiento de caracteres dentro del fragmento donde comienza el texto de origen |
| `tg:sourceCharLength` | Declaración | Longitud del texto de origen en caracteres |

#### Inicialización del Vocabulario (Por Colección)

El grafo de conocimiento es neutral con respecto a la ontología y se inicializa vacío. Cuando se escriben datos de procedencia PROV-O en una colección por primera vez, el vocabulario debe inicializarse con etiquetas RDF para todas las clases y predicados. Esto garantiza una visualización legible por humanos en las consultas y la interfaz de usuario.

**Clases PROV-O:**
```
prov:Entity rdfs:label "Entity" .
prov:Activity rdfs:label "Activity" .
prov:Agent rdfs:label "Agent" .
```

**Predicados PROV-O:**
```
prov:wasDerivedFrom rdfs:label "was derived from" .
prov:wasGeneratedBy rdfs:label "was generated by" .
prov:used rdfs:label "used" .
prov:wasAssociatedWith rdfs:label "was associated with" .
prov:startedAtTime rdfs:label "started at" .
```

**Predicados de TrustGraph:**
```
tg:contains rdfs:label "contains" .
tg:pageCount rdfs:label "page count" .
tg:mimeType rdfs:label "MIME type" .
tg:pageNumber rdfs:label "page number" .
tg:chunkIndex rdfs:label "chunk index" .
tg:charOffset rdfs:label "character offset" .
tg:charLength rdfs:label "character length" .
tg:chunkSize rdfs:label "chunk size" .
tg:chunkOverlap rdfs:label "chunk overlap" .
tg:componentVersion rdfs:label "component version" .
tg:llmModel rdfs:label "LLM model" .
tg:ontology rdfs:label "ontology" .
tg:embeddingModel rdfs:label "embedding model" .
tg:sourceText rdfs:label "source text" .
tg:sourceCharOffset rdfs:label "source character offset" .
tg:sourceCharLength rdfs:label "source character length" .
```

**Nota de implementación:** Este vocabulario de inicio debe ser idempotente, es decir, seguro de ejecutar varias veces sin crear duplicados. Podría activarse durante el procesamiento inicial de un documento en una colección, o como un paso separado de inicialización de la colección.

#### Origen de los Sub-Fragmentos (Aspiracional)

Para un seguimiento de origen más detallado, sería valioso registrar exactamente dónde dentro de un fragmento se extrajo una tripleta. Esto permite:

Resaltar el texto fuente exacto en la interfaz de usuario.
Verificar la precisión de la extracción en comparación con la fuente.
Depurar la calidad de la extracción a nivel de oración.

**Ejemplo con seguimiento de posición:**
```
# The extracted triple
entity:JohnSmith rel:worksAt entity:AcmeCorp .

# Subgraph with sub-chunk provenance
subgraph:001 tg:contains <<entity:JohnSmith rel:worksAt entity:AcmeCorp>> .
subgraph:001 prov:wasDerivedFrom chunk:123-1-1 .
subgraph:001 tg:sourceText "John Smith has worked at Acme Corp since 2019" .
subgraph:001 tg:sourceCharOffset 1547 .
subgraph:001 tg:sourceCharLength 46 .
```

**Ejemplo con rango de texto (alternativa):**
```
subgraph:001 tg:contains <<entity:JohnSmith rel:worksAt entity:AcmeCorp>> .
subgraph:001 prov:wasDerivedFrom chunk:123-1-1 .
subgraph:001 tg:sourceRange "1547-1593" .
subgraph:001 tg:sourceText "John Smith has worked at Acme Corp since 2019" .
```

**Consideraciones de implementación:**

La extracción basada en LLM puede no proporcionar naturalmente las posiciones de los caracteres.
Se podría solicitar al LLM que devuelva la oración/frase original junto con las triples extraídas.
Alternativamente, se puede realizar un procesamiento posterior para hacer coincidir de forma difusa las entidades extraídas con el texto fuente.
Compromiso entre la complejidad de la extracción y la granularidad de la procedencia.
Puede ser más fácil de lograr con métodos de extracción estructurados que con la extracción de LLM de formato libre.

Esto se considera una meta a largo plazo; primero se debe implementar la procedencia a nivel de fragmento, y el seguimiento de subfragmentos puede ser una mejora futura si es factible.

### Modelo de almacenamiento dual

El DAG de procedencia se construye progresivamente a medida que los documentos fluyen a través de la canalización:

| Almacén | ¿Qué se almacena | Propósito |
|-------|---------------|---------|
| Bibliotecario | Contenido del documento + enlaces padre-hijo | Recuperación de contenido, eliminación en cascada |
| Gráfico de conocimiento | Bordes padre-hijo + metadatos | Consultas de procedencia, atribución de hechos |

Ambos almacenes mantienen la misma estructura DAG. El bibliotecario almacena el contenido; el gráfico almacena las relaciones y permite las consultas de recorrido.

### Principios de diseño clave

1. **El ID del documento como unidad de flujo**: Los procesadores pasan ID, no contenido. El contenido se recupera del bibliotecario cuando es necesario.

2. **Emitir una vez en la fuente**: Los metadatos se escriben en el gráfico una vez al inicio del procesamiento, no se repiten en procesos posteriores.

3. **Patrón de procesador consistente**: Cada procesador sigue el mismo patrón de recepción/recuperación/producción/guardado/emisión/reenvío.

4. **Construcción progresiva del DAG**: Cada procesador agrega su nivel al DAG. La cadena completa de procedencia se construye de forma incremental.

5. **Optimización posterior al fragmentador**: Después de la fragmentación, los mensajes contienen tanto el ID como el contenido. Los fragmentos son pequeños (2-4 KB), por lo que incluir el contenido evita viajes de ida y vuelta innecesarios al bibliotecario, al tiempo que preserva la procedencia a través del ID.

## Tareas de implementación

### Cambios en el bibliotecario

#### Estado actual

Inicia el procesamiento de documentos enviando el ID del documento al primer procesador.
No tiene conexión con el almacén de triples; los metadatos se incluyen en los resultados de la extracción.
`add-child-document` crea enlaces padre-hijo de un solo nivel.
`list-children` devuelve solo los hijos inmediatos.

#### Cambios requeridos

**1. Nueva interfaz: Conexión al almacén de triples**

El bibliotecario debe emitir directamente los bordes de metadatos del documento al gráfico de conocimiento al iniciar el procesamiento.
Agregar un cliente/publicador del almacén de triples al servicio del bibliotecario.
Al iniciar el procesamiento: emitir los metadatos del documento raíz como bordes del gráfico (una vez).

**2. Vocabulario de tipos de documentos**

Estandarizar los valores de `document_type` para los documentos hijo:
`source` - documento original cargado.
`page` - página extraída de la fuente (PDF, etc.).
`chunk` - fragmento de texto derivado de la página o la fuente.

#### Resumen de cambios de interfaz

| Interfaz | Cambio |
|-----------|--------|
| Almacén de triples | Nueva conexión de salida: emitir bordes de metadatos del documento |
| Inicio del procesamiento | Emitir metadatos al gráfico antes de reenviar el ID del documento |

### Cambios en el extractor de PDF

#### Estado actual

Recibe el contenido del documento (o transmite documentos grandes).
Extrae texto de las páginas PDF.
Envía el contenido de la página al fragmentador.
No interactúa con el bibliotecario ni con el almacén de triples.

#### Cambios requeridos

**1. Nueva interfaz: Cliente del bibliotecario**

El extractor de PDF debe guardar cada página como un documento hijo en el bibliotecario.
Agregar un cliente del bibliotecario al servicio del extractor de PDF.
Para cada página: llamar a `add-child-document` con padre = ID del documento raíz.

**2. Nueva interfaz: Conexión al almacén de triples**

El extractor de PDF debe emitir bordes padre-hijo al gráfico de conocimiento.
Agregar un cliente/publicador del almacén de triples.
Para cada página: emitir un borde que vincule el documento de la página con el documento padre.

**3. Cambiar el formato de salida**

En lugar de reenviar el contenido de la página directamente, reenvíe el ID del documento de la página.
El componente "Chunker" recuperará el contenido del "librarian" utilizando el ID.

#### Resumen de Cambios en la Interfaz

| Interfaz | Cambio |
|-----------|--------|
| Librarian | Nueva salida: guardar documentos hijos |
| Triple store | Nueva salida: emitir aristas padre-hijo |
| Mensaje de salida | Cambio de contenido a ID de documento |

### Cambios en el Componente "Chunker"

#### Estado Actual

Recibe contenido de página/texto
Lo divide en fragmentos
Reenvía el contenido del fragmento a los procesadores posteriores
No interactúa con el "librarian" ni con el "triple store"

#### Cambios Requeridos

**1. Cambiar el manejo de la entrada**

Recibir el ID del documento en lugar del contenido, y recuperarlo del "librarian".
Agregar un cliente de "librarian" al servicio "chunker"
Recuperar el contenido de la página utilizando el ID del documento

**2. Nueva interfaz: Cliente de "Librarian" (escritura)**

Guardar cada fragmento como un documento hijo en el "librarian".
Para cada fragmento: llamar a `add-child-document` con parent = ID del documento de la página

**3. Nueva interfaz: Conexión con el "Triple store"**

Emitir aristas padre-hijo al grafo de conocimiento.
Agregar un cliente/publicador de "triple store"
Para cada fragmento: emitir una arista que vincule el documento del fragmento con el documento de la página

**4. Cambiar el formato de salida**

Reenviar tanto el ID del documento del fragmento como el contenido del fragmento (optimización posterior al componente "chunker").
Los procesadores posteriores reciben el ID para la trazabilidad y el contenido para trabajar con él

#### Resumen de Cambios en la Interfaz

| Interfaz | Cambio |
|-----------|--------|
| Mensaje de entrada | Cambio de contenido a ID de documento |
| Librarian | Nueva salida (lectura + escritura) - recuperar contenido, guardar documentos hijos |
| Triple store | Nueva salida - emitir aristas padre-hijo |
| Mensaje de salida | Cambio de contenido-único a ID + contenido |

### Cambios en el Extractor de Conocimiento

#### Estado Actual

Recibe contenido del fragmento
Extrae triples y embeddings
Los emite al "triple store" y al almacén de "embeddings"
La relación `subjectOf` apunta al documento de nivel superior (no al fragmento)

#### Cambios Requeridos

**1. Cambiar el manejo de la entrada**

Recibir el ID del fragmento junto con el contenido.
Utilizar el ID del fragmento para la vinculación de trazabilidad (el contenido ya está incluido según la optimización)

**2. Actualizar la trazabilidad de los triples**

Vincular los triples extraídos al fragmento (no al documento de nivel superior).
Utilizar la reificación para crear una arista que apunte a la arista
Relación `subjectOf`: triple → ID del documento del fragmento
Primer uso del soporte de reificación existente

**3. Actualizar la trazabilidad de los "embeddings"**

Vincular los ID de las entidades de "embedding" al fragmento.
Emitir una arista: ID de la entidad de "embedding" → ID del documento del fragmento

#### Resumen de Cambios en la Interfaz

| Interfaz | Cambio |
|-----------|--------|
| Mensaje de entrada | Se espera el ID del fragmento + contenido (no solo contenido) |
| Triple store | Utilizar la reificación para la trazabilidad de triple → fragmento |
| Trazabilidad de "embeddings" | Vincular ID de entidad → ID de fragmento |

## Referencias

Trazabilidad en tiempo de consulta: `docs/tech-specs/query-time-provenance.md`
Estándar PROV-O para el modelado de trazabilidad
Metadatos de origen existentes en el grafo de conocimiento (necesitan auditoría)
