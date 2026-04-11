---
layout: default
title: "Decodificador Universal de Documentos"
parent: "Spanish (Beta)"
---

# Decodificador Universal de Documentos

> **Beta Translation:** This document was translated via Machine Learning and as such may not be 100% accurate. All non-English languages are currently classified as Beta.

## Título

Decodificador universal de documentos impulsado por `unstructured`: ingrese cualquier formato de documento común
a través de un servicio único con un registro completo de la procedencia y la integración de la biblioteca,
registrando las posiciones de origen como metadatos del gráfico de conocimiento para
la trazabilidad de extremo a extremo.

## Problema

Actualmente, TrustGraph tiene un decodificador específico para PDF. Para admitir formatos adicionales
(DOCX, XLSX, HTML, Markdown, texto plano, PPTX, etc.), es necesario
escribir un nuevo decodificador por formato o adoptar una biblioteca de extracción universal.
Cada formato tiene una estructura diferente; algunos son basados en páginas, otros no,
y la cadena de procedencia debe registrar de dónde se originó cada parte del texto extraído
en el documento original.

## Enfoque

### Biblioteca: `unstructured`

Utilice `unstructured.partition.auto.partition()`, que detecta automáticamente el formato
a partir del tipo MIME o la extensión del archivo y extrae elementos estructurados
(Título, TextoNarrativo, Tabla, ElementoLista, etc.). Cada elemento lleva
metadatos que incluyen:

`page_number` (para formatos basados en páginas como PDF, PPTX)
`element_id` (único para cada elemento)
`coordinates` (cuadro delimitador para PDF)
`text` (el contenido de texto extraído)
`category` (tipo de elemento: Título, TextoNarrativo, Tabla, etc.)

### Tipos de Elemento

`unstructured` extrae elementos tipados de los documentos. Cada elemento tiene
una categoría y metadatos asociados:

**Elementos de texto:**
`Title` — encabezados de sección
`NarrativeText` — párrafos del cuerpo
`ListItem` — elementos de lista con viñetas/numerados
`Header`, `Footer` — encabezados/pies de página
`FigureCaption` — leyendas para figuras/imágenes
`Formula` — expresiones matemáticas
`Address`, `EmailAddress` — información de contacto
`CodeSnippet` — bloques de código (de Markdown)

**Tablas:**
`Table` — datos tabulares estructurados. `unstructured` proporciona tanto
  `element.text` (texto plano) como `element.metadata.text_as_html`
  (HTML completo `<table>` con filas, columnas y encabezados conservados).
  Para formatos con una estructura de tabla explícita (DOCX, XLSX, HTML),
  la extracción es muy fiable. Para PDF, la detección de tablas depende de
  la estrategia de `hi_res` con el análisis de diseño.

**Imágenes:**
`Image` — imágenes integradas detectadas mediante el análisis de diseño (requiere
  la estrategia de `hi_res`). Con `extract_image_block_to_payload=True`,
  devuelve los datos de la imagen como base64 en `element.metadata.image_base64`.
  El texto OCR de la imagen está disponible en `element.text`.

### Manejo de Tablas

Las tablas son una salida de primera clase. Cuando el decodificador encuentra un elemento `Table`,
conserva la estructura HTML en lugar de aplanarla a texto plano. Esto proporciona
a la biblioteca de extracción LLM descendente una mejor entrada para extraer conocimiento
estructurado de los datos tabulares.

El texto de la página/sección se ensambla de la siguiente manera:
Elementos de texto: texto plano, unido con saltos de línea
Elementos de tabla: marcado de tabla HTML de `text_as_html`, envuelto en un
  marcador `<table>` para que el LLM pueda distinguir las tablas del texto narrativo.

Por ejemplo, una página con un encabezado, un párrafo y una tabla produce:

```
Financial Overview

Revenue grew 15% year-over-year driven by enterprise adoption.

<table>
<tr><th>Quarter</th><th>Revenue</th><th>Growth</th></tr>
<tr><td>Q1</td><td>$12M</td><td>12%</td></tr>
<tr><td>Q2</td><td>$14M</td><td>17%</td></tr>
</table>
```

Esto preserva la estructura de la tabla mediante la segmentación y en la
canalización de extracción, donde el LLM puede extraer relaciones directamente de
celdas estructuradas en lugar de adivinar la alineación de columnas a partir de
espacios en blanco.

### Manejo de imágenes

Las imágenes se extraen y se almacenan en la biblioteca como documentos
secundarios con un `document_type="image"` y un ID `urn:image:{uuid}`. Obtienen
tripletas de procedencia con el tipo `tg:Image`, vinculadas a su página/sección
principal a través de `prov:wasDerivedFrom`. Los metadatos de la imagen (coordenadas,
dimensiones, element_id) se registran en la procedencia.

**Es crucial que las imágenes NO se emitan como salidas de TextDocument.** Se
almacenan únicamente; no se envían a la canalización de segmentación ni a ningún
proceso de texto. Esto es intencional:

1. Todavía no existe una canalización de procesamiento de imágenes (la integración
   del modelo de visión es un trabajo futuro).
2. Alimentar datos de imagen en base64 o fragmentos de OCR en la
   canalización de extracción de texto produciría tripletas de KG basura.

Las imágenes también se excluyen del texto de la página ensamblada; cualquier `Image`
elemento se omite silenciosamente al concatenar los textos de los elementos para una
página/sección. La cadena de procedencia registra que las imágenes existen y dónde
aparecieron en el documento, por lo que pueden ser recuperadas por una futura
canalización de procesamiento de imágenes sin volver a importar el documento.

#### Trabajo futuro

Enviar `tg:Image` entidades a un modelo de visión para descripción,
  interpretación de diagramas o extracción de datos de gráficos.
Almacenar las descripciones de las imágenes como documentos de texto secundarios que se integran en
  la canalización estándar de fragmentación/extracción.
Vincular el conocimiento extraído de nuevo a las imágenes de origen a través de la procedencia.

### Estrategias de sección

Para formatos basados en páginas (PDF, PPTX, XLSX), los elementos siempre se agrupan
por página/diapositiva/hoja primero. Para formatos no basados en páginas (DOCX, HTML, Markdown,
etc.), el decodificador necesita una estrategia para dividir el documento en
secciones. Esto se puede configurar en tiempo de ejecución a través de `--section-strategy`.

Cada estrategia es una función de agrupación sobre la lista de `unstructured`
elementos. La salida es una lista de grupos de elementos; el resto de la
canalización (ensamblaje de texto, almacenamiento en la biblioteca, procedencia,
emisión de TextDocument) es idéntico independientemente de la estrategia.

#### `whole-document` (predeterminado)

Emite todo el documento como una sola sección. Permite que el
fragmentador (chunker) posterior gestione todas las divisiones.

Enfoque más simple, buena línea de base
Puede producir un TextDocument muy grande para archivos grandes, pero el
  fragmentador se encarga de eso.
Mejor cuando se desea el máximo contexto por sección.

#### `heading`

Divide en elementos de encabezado (`Title`). Cada sección es un encabezado más
todo el contenido hasta el siguiente encabezado de igual o mayor nivel. Los
encabezados anidados crean secciones anidadas.

Produce unidades temáticamente coherentes.
Funciona bien para documentos estructurados (informes, manuales, especificaciones).
Proporciona al LLM de extracción el contexto del encabezado junto con el contenido.
Retrocede a `whole-document` si no se encuentran encabezados.

#### `element-type`

Divide cuando el tipo de elemento cambia significativamente; específicamente,
comienza una nueva sección en las transiciones entre texto narrativo y tablas.
Los elementos consecutivos de la misma categoría general (texto, texto, texto o
tabla, tabla) permanecen agrupados.

Mantiene las tablas como secciones independientes.
Bueno para documentos con contenido mixto (informes con tablas de datos).
Las tablas reciben una atención de extracción dedicada.

#### `count`

Agrupa un número fijo de elementos por sección. Configurable a través de
`--section-element-count` (predeterminado: 20).

Simple y predecible.
No respeta la estructura del documento.
Útil como alternativa o para la experimentación.

#### `size`

Acumula elementos hasta que se alcanza un límite de caracteres, luego comienza una
nueva sección. Respeta los límites de los elementos; nunca los divide a la mitad.
Configurable a través de `--section-max-size` (por defecto: 4000 caracteres).

Produce tamaños de sección aproximadamente uniformes.
Respeta los límites de los elementos (a diferencia del fragmentador posterior).
Buen compromiso entre estructura y control de tamaño.
Si un solo elemento excede el límite, se convierte en su propia sección.

#### Interacción con formatos basados en páginas

Para formatos basados en páginas, el agrupamiento de páginas siempre tiene prioridad.
Las estrategias de sección opcionalmente se pueden aplicar *dentro* de una página si es muy
grande (por ejemplo, una página PDF con una tabla enorme), controlado por
`--section-within-pages` (por defecto: falso). Cuando es falso, cada página es
siempre una sección, independientemente del tamaño.

### Detección de formato

El decodificador necesita conocer el tipo MIME del documento para pasarlo a
`unstructured`'s `partition()`. Dos caminos:

**Ruta del bibliotecario** (`document_id` configurado): primero, recupera los metadatos del documento
  del bibliotecario; esto nos da el `kind` (tipo MIME)
  que se registró en el momento de la carga. Luego, recupera el contenido del documento.
  Dos llamadas al bibliotecario, pero la recuperación de metadatos es ligera.
**Ruta integrada** (compatibilidad con versiones anteriores, `data` configurado): no hay metadatos
  disponibles en el mensaje. Usa `python-magic` para detectar el formato
  a partir de los bytes del contenido como una opción alternativa.

No se necesitan cambios en el esquema `Document`; el bibliotecario ya almacena el tipo MIME.


### Arquitectura

Un único servicio `universal-decoder` que:

1. Recibe un mensaje `Document` (en línea o a través de una referencia a la biblioteca).
2. Si la ruta es a través de la biblioteca: recupera los metadatos del documento (obtiene el tipo MIME), luego
   recupera el contenido. Si la ruta es en línea: detecta el formato a partir de los bytes del contenido.
3. Llama a `partition()` para extraer los elementos.
4. Agrupa elementos: por página para formatos basados en páginas, por estrategia de sección configurada para formatos no basados en páginas.
   sección.
5. Para cada página/sección:
   Genera un ID `urn:page:{uuid}` o `urn:section:{uuid}`
   Ensambla el texto de la página: el texto narrativo como texto plano, las tablas como HTML,
     imágenes omitidas
   Calcula los desplazamientos de caracteres para cada elemento dentro del texto de la página.
   Guarda en el sistema de gestión de documentos como documento hijo.
   Emite triples de procedencia con metadatos de posición.
   Envía `TextDocument` a la siguiente etapa para la segmentación.
6. Para cada elemento de imagen:
   Genera un ID `urn:image:{uuid}`.
   Guarda los datos de la imagen en el sistema de gestión de documentos como documento hijo.
   Emite triples de procedencia (almacenados solo, no enviados a la siguiente etapa).

### Manejo de formatos

| Formato   | Tipo MIME                          | Basado en páginas | Notas                          |
|----------|------------------------------------|------------|--------------------------------|
| PDF      | application/pdf                    | Sí        | Agrupación por página              |
| DOCX     | application/vnd.openxmlformats...  | No         | Utiliza estrategia de secciones          |
| PPTX     | application/vnd.openxmlformats...  | Sí        | Agrupación por diapositiva             |
| XLSX/XLS | application/vnd.openxmlformats...  | Sí        | Agrupación por hoja             |
| HTML     | text/html                          | No         | Utiliza estrategia de secciones          |
| Markdown | text/markdown                      | No         | Utiliza estrategia de secciones          |
| Texto plano | text/plain                         | No         | Utiliza estrategia de secciones          |
| CSV      | text/csv                           | No         | Utiliza estrategia de secciones          |
| RST      | text/x-rst                         | No         | Utiliza estrategia de secciones          |
| RTF      | application/rtf                    | No         | Utiliza estrategia de secciones          |
| ODT      | application/vnd.oasis...           | No         | Utiliza estrategia de secciones          |
| TSV      | text/tab-separated-values          | No         | Utiliza estrategia de secciones          |

### Metadatos de procedencia

Cada entidad de página/sección registra metadatos de posición como metadatos de procedencia
en `GRAPH_SOURCE`, lo que permite una trazabilidad completa desde las triples del grafo de conocimiento
hasta las posiciones del documento de origen.

#### Campos existentes (ya están en `derived_entity_triples`)

`page_number` — número de página/hoja/diapositiva (indexado desde 1, solo para páginas)
`char_offset` — desplazamiento de caracteres de esta página/sección dentro del
  texto completo del documento.
`char_length` — longitud de caracteres del texto de esta página/sección.

#### Nuevos campos (extender `derived_entity_triples`)

`mime_type` — formato original del documento (por ejemplo, `application/pdf`)
`element_types` — lista separada por comas de categorías de elementos `unstructured`
  encontradas en esta página/sección (por ejemplo, "Título,TextoNarrativo,Tabla")
`table_count` — número de tablas en esta página/sección.
`image_count` — número de imágenes en esta página/sección.

Estos requieren nuevos predicados del espacio de nombres TG:

```
TG_SECTION_TYPE  = "https://trustgraph.ai/ns/Section"
TG_IMAGE_TYPE    = "https://trustgraph.ai/ns/Image"
TG_ELEMENT_TYPES = "https://trustgraph.ai/ns/elementTypes"
TG_TABLE_COUNT   = "https://trustgraph.ai/ns/tableCount"
TG_IMAGE_COUNT   = "https://trustgraph.ai/ns/imageCount"
```

Esquema URN de imagen: `urn:image:{uuid}`

(`TG_MIME_TYPE` ya existe.)

#### Nuevo tipo de entidad

Para formatos que no son de página (DOCX, HTML, Markdown, etc.) donde el decodificador
emite todo el documento como una sola unidad en lugar de dividirlo por
página, la entidad obtiene un nuevo tipo:

```
TG_SECTION_TYPE = "https://trustgraph.ai/ns/Section"
```

Esto distingue las secciones de las páginas al consultar el origen:

| Entidad | Tipo | Cuándo se utiliza |
|----------|-----------------------------|----------------------------------------|
| Documento | `tg:Document` | Archivo original subido |
| Página | `tg:Page` | Formatos basados en páginas (PDF, PPTX, XLSX) |
| Sección | `tg:Section` | Formatos que no son de página (DOCX, HTML, MD, etc.) |
| Imagen | `tg:Image` | Imágenes incrustadas (almacenadas, no procesadas) |
| Fragmento | `tg:Chunk` | Resultado del fragmentador |
| Subgrafo | `tg:Subgraph` | Resultado de la extracción del grafo de conocimiento |

El tipo se establece por el decodificador según si se está agrupando por página
o emitiendo una sección de todo el documento. `derived_entity_triples` obtiene
un parámetro booleano opcional `section`; cuando es verdadero, la entidad se
clasifica como `tg:Section` en lugar de `tg:Page`.

#### Cadena completa de origen

```
KG triple
  → subgraph (extraction provenance)
    → chunk (char_offset, char_length within page)
      → page/section (page_number, char_offset, char_length within doc, mime_type, element_types)
        → document (original file in librarian)
```

Cada enlace es un conjunto de triples en el grafo denominado `GRAPH_SOURCE`.

### Configuración del servicio

Argumentos de línea de comandos:

```
--strategy              Partitioning strategy: auto, hi_res, fast (default: auto)
--languages             Comma-separated OCR language codes (default: eng)
--section-strategy      Section grouping: whole-document, heading, element-type,
                        count, size (default: whole-document)
--section-element-count Elements per section for 'count' strategy (default: 20)
--section-max-size      Max chars per section for 'size' strategy (default: 4000)
--section-within-pages  Apply section strategy within pages too (default: false)
```

Además de los argumentos estándar de `FlowProcessor` y la cola del bibliotecario.

### Integración del flujo

El decodificador universal ocupa la misma posición en el flujo de procesamiento
que el decodificador PDF actual:

```
Document → [universal-decoder] → TextDocument → [chunker] → Chunk → ...
```

Se registra:
`input` consumidor (esquema de documento)
`output` productor (esquema de TextDocument)
`triples` productor (esquema de Triples)
Solicitud/respuesta del bibliotecario (para la recuperación y el almacenamiento de documentos secundarios)

### Despliegue

Nuevo contenedor: `trustgraph-flow-universal-decoder`
Dependencia: `unstructured[all-docs]` (incluye PDF, DOCX, PPTX, etc.)
Puede ejecutarse junto con o reemplazar el decodificador PDF existente, dependiendo de
  la configuración del flujo.
El decodificador PDF existente permanece disponible para entornos donde
  las dependencias de `unstructured` son demasiado pesadas.

### ¿Qué Cambia?

| Component                    | Change                                         |
|------------------------------|-------------------------------------------------|
| `provenance/namespaces.py`   | Add `TG_SECTION_TYPE`, `TG_IMAGE_TYPE`, `TG_ELEMENT_TYPES`, `TG_TABLE_COUNT`, `TG_IMAGE_COUNT` |
| `provenance/triples.py`      | Add `mime_type`, `element_types`, `table_count`, `image_count` kwargs |
| `provenance/__init__.py`     | Export new constants                            |
| New: `decoding/universal/`   | New decoder service module                      |
| `setup.cfg` / `pyproject`    | Add `unstructured[all-docs]` dependency         |
| Docker                       | New container image                             |
| Flow definitions             | Wire universal-decoder as document input        |

### What Doesn't Change

Chunker (receives TextDocument, works as before)
Downstream extractors (receive Chunk, unchanged)
Librarian (stores child documents, unchanged)
Schema (Document, TextDocument, Chunk unchanged)
Query-time provenance (unchanged)

## Risks

`unstructured[all-docs]` has heavy dependencies (poppler, tesseract,
  libreoffice for some formats). Container image will be larger.
  Mitigation: offer a `[light]` variant without OCR/office deps.
Some formats may produce poor text extraction (scanned PDFs without
  OCR, complex XLSX layouts). Mitigation: configurable `strategy`
  parameter, and the existing Mistral OCR decoder remains available
  for high-quality PDF OCR.
`unstructured` version updates may change element metadata.
  Mitigation: pin version, test extraction quality per format.
