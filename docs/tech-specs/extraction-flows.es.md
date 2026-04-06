# Flujos de extracción

Este documento describe cómo los datos fluyen a través de la canalización de extracción de TrustGraph, desde la presentación del documento hasta el almacenamiento en almacenes de conocimiento.

## Resumen

```
┌──────────┐     ┌─────────────┐     ┌─────────┐     ┌────────────────────┐
│ Librarian│────▶│ PDF Decoder │────▶│ Chunker │────▶│ Knowledge          │
│          │     │ (PDF only)  │     │         │     │ Extraction         │
│          │────────────────────────▶│         │     │                    │
└──────────┘     └─────────────┘     └─────────┘     └────────────────────┘
                                          │                    │
                                          │                    ├──▶ Triples
                                          │                    ├──▶ Entity Contexts
                                          │                    └──▶ Rows
                                          │
                                          └──▶ Document Embeddings
```

## Almacenamiento de contenido

### Almacenamiento de objetos (S3/Minio)

El contenido de los documentos se almacena en un almacenamiento de objetos compatible con S3:
Formato de la ruta: `doc/{object_id}` donde object_id es un UUID
Todos los tipos de documentos se almacenan aquí: documentos fuente, páginas, fragmentos

### Almacenamiento de metadatos (Cassandra)

Los metadatos de los documentos almacenados en Cassandra incluyen:
ID del documento, título, tipo (MIME)
Referencia al almacenamiento de objetos `object_id`
Referencia `parent_id` para documentos secundarios (páginas, fragmentos)
`document_type`: "fuente", "página", "fragmento", "respuesta"

### Umbral de contenido en línea frente a transmisión

La transmisión de contenido utiliza una estrategia basada en el tamaño:
**< 2MB**: El contenido se incluye directamente en el mensaje (codificado en base64)
**≥ 2MB**: Solo se envía `document_id`; el procesador recupera el contenido a través de la API del bibliotecario

## Etapa 1: Envío de documentos (Bibliotecario)

### Punto de entrada

Los documentos ingresan al sistema a través de la operación `add-document` del bibliotecario:
1. El contenido se carga en el almacenamiento de objetos
2. Se crea un registro de metadatos en Cassandra
3. Devuelve el ID del documento

### Activación de la extracción

La operación `add-processing` activa la extracción:
Especifica `document_id`, `flow` (ID de la canalización), `collection` (almacén de destino)
La operación `load_document()` del bibliotecario recupera el contenido y lo publica en la cola de entrada del flujo

### Esquema: Documento

```
Document
├── metadata: Metadata
│   ├── id: str              # Document identifier
│   ├── user: str            # Tenant/user ID
│   ├── collection: str      # Target collection
│   └── metadata: list[Triple]  # (largely unused, historical)
├── data: bytes              # PDF content (base64, if inline)
└── document_id: str         # Librarian reference (if streaming)
```

**Enrutamiento**: Basado en el campo `kind`:
`application/pdf` → cola `document-load` → Decodificador de PDF
`text/plain` → cola `text-load` → Fragmentador

## Etapa 2: Decodificador de PDF

Convierte documentos PDF en páginas de texto.

### Proceso

1. Obtener contenido (inline `data` o a través de `document_id` desde el bibliotecario)
2. Extraer páginas utilizando PyPDF
3. Para cada página:
   Guardar como documento hijo en el bibliotecario (`{doc_id}/p{page_num}`)
   Emitir triples de procedencia (página derivada del documento)
   Enviar al fragmentador

### Esquema: TextDocument

```
TextDocument
├── metadata: Metadata
│   ├── id: str              # Page URI (e.g., https://trustgraph.ai/doc/xxx/p1)
│   ├── user: str
│   ├── collection: str
│   └── metadata: list[Triple]
├── text: bytes              # Page text content (if inline)
└── document_id: str         # Librarian reference (e.g., "doc123/p1")
```

## Etapa 3: Fragmentador

Divide el texto en fragmentos de un tamaño configurado.

### Parámetros (configurables)

`chunk_size`: Tamaño de fragmento objetivo en caracteres (predeterminado: 2000)
`chunk_overlap`: Solapamiento entre fragmentos (predeterminado: 100)

### Proceso

1. Obtener el contenido del texto (en línea o a través del bibliotecario)
2. Dividir utilizando un divisor de caracteres recursivo
3. Para cada fragmento:
   Guardar como documento hijo en el bibliotecario (`{parent_id}/c{index}`)
   Emitir triples de procedencia (fragmento derivado de página/documento)
   Enviar a los procesadores de extracción

### Esquema: Fragmento

```
Chunk
├── metadata: Metadata
│   ├── id: str              # Chunk URI
│   ├── user: str
│   ├── collection: str
│   └── metadata: list[Triple]
├── chunk: bytes             # Chunk text content
└── document_id: str         # Librarian chunk ID (e.g., "doc123/p1/c3")
```

### Jerarquía de Identificadores de Documentos

Los documentos secundarios codifican su linaje en el identificador:
Fuente: `doc123`
Página: `doc123/p5`
Fragmento de página: `doc123/p5/c2`
Fragmento de texto: `doc123/c2`

## Etapa 4: Extracción de Conocimiento

Múltiples patrones de extracción disponibles, seleccionados por la configuración del flujo.

### Patrón A: Basic GraphRAG

Dos procesadores paralelos:

**kg-extract-definitions**
Entrada: Fragmento
Salida: Triples (definiciones de entidades), EntityContexts
Extrae: etiquetas de entidades, definiciones

**kg-extract-relationships**
Entrada: Fragmento
Salida: Triples (relaciones), EntityContexts
Extrae: relaciones sujeto-predicado-objeto

### Patrón B: Basado en Ontología (kg-extract-ontology)

Entrada: Fragmento
Salida: Triples, EntityContexts
Utiliza una ontología configurada para guiar la extracción

### Patrón C: Basado en Agente (kg-extract-agent)

Entrada: Fragmento
Salida: Triples, EntityContexts
Utiliza un marco de agente para la extracción

### Patrón D: Extracción de Filas (kg-extract-rows)

Entrada: Fragmento
Salida: Filas (datos estructurados, no triples)
Utiliza una definición de esquema para extraer registros estructurados

### Esquema: Triples

```
Triples
├── metadata: Metadata
│   ├── id: str
│   ├── user: str
│   ├── collection: str
│   └── metadata: list[Triple]  # (set to [] by extractors)
└── triples: list[Triple]
    └── Triple
        ├── s: Term              # Subject
        ├── p: Term              # Predicate
        ├── o: Term              # Object
        └── g: str | None        # Named graph
```

### Esquema: EntityContexts

```
EntityContexts
├── metadata: Metadata
└── entities: list[EntityContext]
    └── EntityContext
        ├── entity: Term         # Entity identifier (IRI)
        ├── context: str         # Textual description for embedding
        └── chunk_id: str        # Source chunk ID (provenance)
```

### Esquema: Filas

```
Rows
├── metadata: Metadata
├── row_schema: RowSchema
│   ├── name: str
│   ├── description: str
│   └── fields: list[Field]
└── rows: list[dict[str, str]]   # Extracted records
```

## Etapa 5: Generación de Incrustaciones (Embeddings)

### Incrustaciones de Grafos (Graph Embeddings)

Convierte los contextos de las entidades en incrustaciones vectoriales.

**Proceso:**
1. Recibir EntityContexts (Contextos de Entidades)
2. Llamar al servicio de incrustaciones con el texto del contexto
3. Salida: GraphEmbeddings (mapeo de entidad a vector)

**Esquema: GraphEmbeddings**

```
GraphEmbeddings
├── metadata: Metadata
└── entities: list[EntityEmbeddings]
    └── EntityEmbeddings
        ├── entity: Term         # Entity identifier
        ├── vector: list[float]  # Embedding vector
        └── chunk_id: str        # Source chunk (provenance)
```

### Incrustaciones de documentos

Convierte texto de fragmentos directamente en incrustaciones vectoriales.

**Proceso:**
1. Recibir fragmento
2. Llamar al servicio de incrustaciones con el texto del fragmento
3. Salida: Incrustaciones de documentos

**Esquema: Incrustaciones de documentos**

```
DocumentEmbeddings
├── metadata: Metadata
└── chunks: list[ChunkEmbeddings]
    └── ChunkEmbeddings
        ├── chunk_id: str        # Chunk identifier
        └── vector: list[float]  # Embedding vector
```

### Incrustaciones de filas

Convierte los campos de índice de fila en incrustaciones vectoriales.

**Proceso:**
1. Recibir filas
2. Incrustar campos de índice configurados
3. Salida a la tienda de vectores de filas

## Etapa 6: Almacenamiento

### Triple Store

Recibe: Triples
Almacenamiento: Cassandra (tablas centradas en entidades)
Los grafos con nombre separan el conocimiento central de la procedencia:
  `""` (predeterminado): Hechos de conocimiento central
  `urn:graph:source`: Procedencia de extracción
  `urn:graph:retrieval`: Explicabilidad en tiempo de consulta

### Tienda de vectores (Incrustaciones de grafos)

Recibe: GraphEmbeddings
Almacenamiento: Qdrant, Milvus o Pinecone
Indexado por: IRI de entidad
Metadatos: chunk_id para la procedencia

### Tienda de vectores (Incrustaciones de documentos)

Recibe: DocumentEmbeddings
Almacenamiento: Qdrant, Milvus o Pinecone
Indexado por: chunk_id

### Tienda de filas

Recibe: Filas
Almacenamiento: Cassandra
Estructura de tabla basada en esquema

### Tienda de vectores de filas

Recibe: Incrustaciones de filas
Almacenamiento: Base de datos de vectores
Indexado por: Campos de índice de fila

## Análisis de campos de metadatos

### Campos utilizados activamente

| Campo | Uso |
|-------|-------|
| `metadata.id` | Identificador de documento/fragmento, registro, procedencia |
| `metadata.user` | Multitenencia, enrutamiento de almacenamiento |
| `metadata.collection` | Selección de colección de destino |
| `document_id` | Referencia de bibliotecario, enlace de procedencia |
| `chunk_id` | Seguimiento de la procedencia a través de la canalización |

<<<<<<< HEAD
### Campos potencialmente redundantes

| Campo | Estado |
|-------|--------|
| `metadata.metadata` | Establecido en `[]` por todos los extractores; los metadatos a nivel de documento ahora se gestionan por el bibliotecario en el momento de la presentación |
=======
### Campos eliminados

| Campo | Estado |
|-------|--------|
| `metadata.metadata` | Eliminado de la clase `Metadata`. Los triples de metadatos a nivel de documento ahora se emiten directamente por el bibliotecario a la triple store en el momento de la presentación, y no se transmiten a través de la canalización de extracción. |
>>>>>>> e3bcbf73 (The metadata field (list of triples) in the pipeline Metadata class)

### Patrón de campos de bytes

Todos los campos de contenido (`data`, `text`, `chunk`) son `bytes`, pero se decodifican inmediatamente a cadenas UTF-8 por todos los procesadores. Ningún procesador utiliza bytes sin procesar.

## Configuración del flujo

Los flujos se definen externamente y se proporcionan al bibliotecario a través del servicio de configuración. Cada flujo especifica:

Colas de entrada (`text-load`, `document-load`)
Cadena de procesadores
Parámetros (tamaño del fragmento, método de extracción, etc.)

Patrones de flujo de ejemplo:
`pdf-graphrag`: PDF → Decodificador → Fragmentador → Definiciones + Relaciones → Incrustaciones
`text-graphrag`: Texto → Fragmentador → Definiciones + Relaciones → Incrustaciones
`pdf-ontology`: PDF → Decodificador → Fragmentador → Extracción de ontología → Incrustaciones
`text-rows`: Texto → Fragmentador → Extracción de filas → Tienda de filas
