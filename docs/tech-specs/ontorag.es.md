# OntoRAG: Especificación Técnica de Extracción y Consulta de Conocimiento Basada en Ontologías

## Resumen

OntoRAG es un sistema de extracción y consulta de conocimiento impulsado por ontologías que impone una coherencia semántica estricta tanto durante la extracción de triples de conocimiento de texto no estructurado como durante la consulta del grafo de conocimiento resultante. Similar a GraphRAG, pero con restricciones de ontología formales, OntoRAG garantiza que todos los triples extraídos cumplan con estructuras ontológicas predefinidas y proporciona capacidades de consulta con conciencia semántica.

El sistema utiliza la coincidencia de similitud vectorial para seleccionar dinámicamente subconjuntos de ontología relevantes tanto para las operaciones de extracción como de consulta, lo que permite un procesamiento enfocado y contextualmente apropiado al tiempo que se mantiene la validez semántica.

**Nombre del Servicio**: `kg-extract-ontology`

## Objetivos

**Extracción Conforme a la Ontología**: Asegurar que todos los triples extraídos cumplan estrictamente con las ontologías cargadas.
**Selección de Contexto Dinámico**: Utilizar incrustaciones para seleccionar subconjuntos de ontología relevantes para cada fragmento.
**Coherencia Semántica**: Mantener jerarquías de clases, dominios/rangos de propiedades y restricciones.
**Procesamiento Eficiente**: Utilizar almacenes vectoriales en memoria para una coincidencia rápida de elementos de la ontología.
**Arquitectura Escalable**: Soporte para múltiples ontologías concurrentes con diferentes dominios.

## Antecedentes

Los servicios actuales de extracción de conocimiento (`kg-extract-definitions`, `kg-extract-relationships`) operan sin restricciones formales, lo que podría generar triples inconsistentes o incompatibles. OntoRAG aborda esto mediante:

1. Carga de ontologías formales que definen clases y propiedades válidas.
2. Utilización de incrustaciones para hacer coincidir el contenido de texto con elementos de ontología relevantes.
3. Restricción de la extracción para producir solo triples conformes a la ontología.
4. Provisión de validación semántica del conocimiento extraído.

Este enfoque combina la flexibilidad de la extracción neuronal con la rigurosidad de la representación formal del conocimiento.

## Diseño Técnico

### Arquitectura

El sistema OntoRAG consta de los siguientes componentes:

```
┌─────────────────┐
│  Configuration  │
│    Service      │
└────────┬────────┘
         │ Ontologies
         ▼
┌─────────────────┐      ┌──────────────┐
│ kg-extract-     │────▶│  Embedding   │
│   ontology      │      │   Service    │
└────────┬────────┘      └──────────────┘
         │                      │
         ▼                      ▼
┌─────────────────┐      ┌──────────────┐
│   In-Memory     │◀────│   Ontology   │
│  Vector Store   │      │   Embedder   │
└────────┬────────┘      └──────────────┘
         │
         ▼
┌─────────────────┐      ┌──────────────┐
│    Sentence     │────▶│   Chunker    │
│    Splitter     │      │   Service    │
└────────┬────────┘      └──────────────┘
         │
         ▼
┌─────────────────┐      ┌──────────────┐
│    Ontology     │────▶│   Vector     │
│    Selector     │      │   Search     │
└────────┬────────┘      └──────────────┘
         │
         ▼
┌─────────────────┐      ┌──────────────┐
│    Prompt       │────▶│   Prompt     │
│   Constructor   │      │   Service    │
└────────┬────────┘      └──────────────┘
         │
         ▼
┌─────────────────┐
│  Triple Output  │
└─────────────────┘
```

### Detalles del Componente

#### 1. Carga de Ontologías

**Propósito**: Recupera y analiza las configuraciones de ontologías desde el servicio de configuración utilizando actualizaciones basadas en eventos.

**Implementación**:
El cargador de ontologías utiliza la cola ConfigPush de TrustGraph para recibir actualizaciones de configuración de ontologías basadas en eventos. Cuando se agrega o modifica un elemento de configuración de tipo "ontología", el cargador recibe la actualización a través de la cola config-update y analiza la estructura JSON que contiene metadatos, clases, propiedades de objeto y propiedades de tipo de datos. Estas ontologías analizadas se almacenan en la memoria como objetos estructurados que se pueden acceder de forma eficiente durante el proceso de extracción.

**Operaciones Clave**:
Suscribirse a la cola config-update para configuraciones de tipo ontología
Analizar estructuras JSON de ontologías en objetos OntologyClass y OntologyProperty
Validar la estructura y la coherencia de la ontología
Almacenar en caché las ontologías analizadas en la memoria para un acceso rápido
Manejar el procesamiento por flujo con almacenes de vectores específicos del flujo

**Ubicación de la Implementación**: `trustgraph-flow/trustgraph/extract/kg/ontology/ontology_loader.py`

#### 2. Incrustador de Ontologías

**Propósito**: Crea incrustaciones vectoriales para todos los elementos de la ontología para habilitar la coincidencia de similitud semántica.

**Implementación**:
El incrustador de ontologías procesa cada elemento en las ontologías cargadas (clases, propiedades de objeto y propiedades de tipo de datos) y genera incrustaciones vectoriales utilizando el servicio EmbeddingsClientSpec. Para cada elemento, combina el identificador del elemento, las etiquetas y la descripción (comentario) para crear una representación de texto. Este texto se convierte luego en una incrustación vectorial de alta dimensión que captura su significado semántico. Estas incrustaciones se almacenan en un almacén de vectores FAISS en la memoria, específico de cada flujo, junto con metadatos sobre el tipo de elemento, la ontología de origen y la definición completa. El incrustador detecta automáticamente la dimensión de la incrustación a partir de la primera respuesta de la incrustación.

**Operaciones Clave**:
Crear representaciones de texto a partir de ID de elementos, etiquetas y comentarios
Generar incrustaciones a través de EmbeddingsClientSpec (utilizando asyncio.gather para el procesamiento por lotes)
Almacenar incrustaciones con metadatos completos en el almacén de vectores FAISS
Indexar por ontología, tipo de elemento y ID de elemento para una recuperación eficiente
Detectar automáticamente las dimensiones de la incrustación para la inicialización del almacén de vectores
Manejar modelos de incrustación específicos del flujo con almacenes de vectores independientes

**Ubicación de la Implementación**: `trustgraph-flow/trustgraph/extract/kg/ontology/ontology_embedder.py`

#### 3. Procesador de Texto (Divisor de Oraciones)

**Propósito**: Descompone los fragmentos de texto en segmentos granulares para una coincidencia precisa de ontologías.

**Implementación**:
El procesador de texto utiliza NLTK para la tokenización de oraciones y el etiquetado POS para dividir los fragmentos de texto entrantes en oraciones. Maneja la compatibilidad de la versión de NLTK intentando descargar `punkt_tab` y `averaged_perceptron_tagger_eng`, con retrocesos a versiones anteriores si es necesario. Cada fragmento de texto se divide en oraciones individuales que se pueden hacer coincidir de forma independiente con los elementos de la ontología.

**Operaciones Clave**:
Dividir el texto en oraciones utilizando la tokenización de oraciones de NLTK
Manejar la compatibilidad de la versión de NLTK (punkt_tab vs punkt)
Crear objetos TextSegment con texto e información de posición
Soporte tanto para oraciones completas como para fragmentos individuales

**Ubicación de la Implementación**: `trustgraph-flow/trustgraph/extract/kg/ontology/text_processor.py`

#### 4. Selector de Ontologías

**Propósito**: Identifica el subconjunto más relevante de elementos de la ontología para el fragmento de texto actual.

**Implementación**:
El selector de ontologías realiza una coincidencia semántica entre los segmentos de texto y los elementos de la ontología utilizando la búsqueda de similitud vectorial FAISS. Para cada oración del fragmento de texto, genera una incrustación y busca en el almacén de vectores los elementos de la ontología más similares utilizando la similitud coseno con un umbral configurable (por defecto 0.3). Después de recopilar todos los elementos relevantes, realiza una resolución de dependencias integral: si se selecciona una clase, se incluyen sus clases padre; si se selecciona una propiedad, se agregan sus clases de dominio y rango. Además, para cada clase seleccionada, incluye automáticamente **todas las propiedades que hacen referencia a esa clase** en su dominio o rango. Esto asegura que la extracción tenga acceso a todas las propiedades relevantes de la relación.

**Operaciones Clave**:
Generar incrustaciones para cada segmento de texto (oraciones)
Realizar una búsqueda de vecinos más cercanos en el almacén vectorial FAISS (top_k=10, threshold=0.3)
Aplicar un umbral de similitud para filtrar coincidencias débiles
Resolver dependencias (clases padre, dominios, rangos)
**Incluir automáticamente todas las propiedades relacionadas con las clases seleccionadas** (coincidencia de dominio/rango)
Construir un subconjunto de ontología coherente con todas las relaciones requeridas
Eliminar elementos duplicados que aparecen varias veces

**Ubicación de la Implementación**: `trustgraph-flow/trustgraph/extract/kg/ontology/ontology_selector.py`

#### 5. Construcción de la Consulta (Prompt)

**Propósito**: Crea consultas estructuradas que guían al LLM para extraer solo triples conformes a la ontología.

**Implementación**:
El servicio de extracción utiliza una plantilla Jinja2 cargada desde `ontology-prompt.md` que formatea el subconjunto de la ontología y el texto para la extracción del LLM. La plantilla itera dinámicamente sobre clases, propiedades de objeto y propiedades de tipo de datos utilizando la sintaxis de Jinja2, presentando cada una con sus descripciones, dominios, rangos y relaciones jerárquicas. La consulta incluye reglas estrictas sobre el uso únicamente de los elementos de la ontología proporcionados y solicita un formato de salida JSON para un análisis coherente.

**Operaciones Clave**:
Utilizar una plantilla Jinja2 con bucles sobre los elementos de la ontología
Formatear clases con relaciones padre (subclass_of) y comentarios
Formatear propiedades con restricciones de dominio/rango y comentarios
Incluir reglas de extracción explícitas y requisitos de formato de salida
Llamar al servicio de consulta con el ID de la plantilla "extract-with-ontologies"

**Ubicación de la Plantilla**: `ontology-prompt.md`
**Ubicación de la Implementación**: `trustgraph-flow/trustgraph/extract/kg/ontology/extract.py` (método build_extraction_variables)

#### 6. Servicio de Extracción Principal

**Propósito**: Coordina todos los componentes para realizar la extracción de triples basada en la ontología de extremo a extremo.

**Implementación**:
El Servicio de Extracción Principal (KgExtractOntology) es la capa de orquestación que gestiona el flujo de trabajo completo de extracción. Utiliza el patrón FlowProcessor de TrustGraph con inicialización de componentes específicos del flujo. Cuando llega una actualización de la configuración de la ontología, inicializa o actualiza los componentes específicos del flujo (cargador de ontología, incrustador, procesador de texto, selector). Cuando llega un fragmento de texto para su procesamiento, coordina la canalización: divide el texto en segmentos, encuentra elementos de ontología relevantes mediante búsqueda vectorial, construye una consulta restringida, llama al servicio de consulta, analiza y valida la respuesta, genera triples de definición de ontología y emite tanto triples de contenido como contextos de entidades.

**Canalización de Extracción**:
1. Recibir un fragmento de texto a través de la cola chunks-input
2. Inicializar los componentes del flujo si es necesario (en el primer fragmento o en la actualización de la configuración)
3. Dividir el texto en oraciones utilizando NLTK
4. Buscar en el almacén vectorial FAISS para encontrar conceptos de ontología relevantes
5. Construir un subconjunto de ontología con inclusión automática de propiedades
6. Construir variables de consulta Jinja2
7. Llamar al servicio de consulta con la plantilla extract-with-ontologies
8. Analizar la respuesta JSON en triples estructurados
9. Validar los triples y expandir los URIs a URIs completos de la ontología
10. Generar triples de definición de ontología (clases y propiedades con etiquetas/comentarios/dominios/rangos)
11. Construir contextos de entidades a partir de todos los triples
12. Emitir a las colas de triples y contextos de entidades

**Características Clave**:
Almacenes vectoriales específicos del flujo que admiten diferentes modelos de incrustación
Actualizaciones de ontología basadas en eventos a través de la cola config-update
Expansión automática de URIs utilizando URIs de ontología
Elementos de ontología añadidos al grafo de conocimiento con metadatos completos
Los contextos de entidades incluyen tanto elementos de contenido como de ontología

**Ubicación de la Implementación**: `trustgraph-flow/trustgraph/extract/kg/ontology/extract.py`

### Configuración

El servicio utiliza el enfoque de configuración estándar de TrustGraph con argumentos de línea de comandos:

```bash
kg-extract-ontology \
  --id kg-extract-ontology \
  --pulsar-host localhost:6650 \
  --input-queue chunks \
  --config-input-queue config-update \
  --output-queue triples \
  --entity-contexts-output-queue entity-contexts
```

**Parámetros de Configuración Clave**:
`similarity_threshold`: 0.3 (predeterminado, configurable en el código)
`top_k`: 10 (número de elementos de la ontología a recuperar por segmento)
`vector_store`: Índice FAISS FlatIP por flujo con detección automática de dimensiones
`text_processor`: NLTK con tokenización de oraciones punkt_tab
`prompt_template`: "extract-with-ontologies" (plantilla Jinja2)

**Configuración de la Ontología**:
Las ontologías se cargan dinámicamente a través de la cola de actualización de configuración con el tipo "ontology".

### Flujo de Datos

1. **Fase de Inicialización** (por flujo):
   Recibir la configuración de la ontología a través de la cola de actualización de configuración
   Analizar el JSON de la ontología en objetos OntologyClass y OntologyProperty
   Generar incrustaciones para todos los elementos de la ontología utilizando EmbeddingsClientSpec
   Almacenar las incrustaciones en el almacén de vectores FAISS específico de cada flujo
   Detectar automáticamente las dimensiones de la incrustación a partir de la primera respuesta

2. **Fase de Extracción** (por fragmento):
   Recibir un fragmento de la cola chunks-input
   Dividir el fragmento en oraciones utilizando NLTK
   Calcular las incrustaciones para cada oración
   Buscar en el almacén de vectores FAISS los elementos de la ontología relevantes
   Construir un subconjunto de la ontología con inclusión automática de propiedades
   Construir variables de plantilla Jinja2 con texto y ontología
   Llamar al servicio de solicitud con la plantilla extract-with-ontologías
   Analizar la respuesta JSON y validar las triples
   Expandir los URIs utilizando los URIs de la ontología
   Generar triples de definición de ontología
   Construir contextos de entidades a partir de todas las triples
   Emitir a las colas de triples y entity-contexts

### Almacén de Vectores en Memoria

**Propósito**: Proporciona una búsqueda de similitud rápida y basada en memoria para la coincidencia de elementos de la ontología.

**Implementación: FAISS**

El sistema utiliza **FAISS (Facebook AI Similarity Search)** con IndexFlatIP para la búsqueda de similitud coseno exacta. Características clave:

**IndexFlatIP**: Búsqueda de similitud coseno exacta utilizando el producto interno
**Detección automática**: La dimensión se determina a partir de la primera respuesta de incrustación
**Almacenes por flujo**: Cada flujo tiene un almacén de vectores independiente para diferentes modelos de incrustación
**Normalización**: Todos los vectores se normalizan antes de la indexación
**Operaciones por lotes**: Adición por lotes eficiente para la carga inicial de la ontología

**Ubicación de la Implementación**: `trustgraph-flow/trustgraph/extract/kg/ontology/vector_store.py`

### Algoritmo de Selección de Subconjunto de Ontología

**Propósito**: Selecciona dinámicamente la porción relevante mínima de la ontología para cada fragmento de texto.

**Pasos Detallados del Algoritmo**:

1. **Segmentación de Texto**:
   Dividir el fragmento de entrada en oraciones utilizando la detección de oraciones de NLP
   Extraer frases nominales, frases verbales y entidades nombradas de cada oración
   Crear una estructura jerárquica de segmentos que preserve el contexto

2. **Generación de Incrustaciones**:
   Generar incrustaciones vectoriales para cada segmento de texto (oraciones y frases)
   Utilizar el mismo modelo de incrustación que se utiliza para los elementos de la ontología
   Almacenar en caché las incrustaciones para los segmentos repetidos para mejorar el rendimiento

3. **Búsqueda de Similitud**:
   Para cada incrustación de segmento de texto, buscar en el almacén de vectores
   Recuperar los k elementos de la ontología más similares (por ejemplo, 10)
   Aplicar un umbral de similitud (por ejemplo, 0.7) para filtrar las coincidencias débiles
   Agregar los resultados en todos los segmentos, rastreando las frecuencias de coincidencia

4. **Resolución de Dependencias**:
   Para cada clase seleccionada, incluir recursivamente todas las clases padre hasta la raíz
   Para cada propiedad seleccionada, incluir las clases de dominio y rango
   Para las propiedades inversas, asegurarse de incluir ambas direcciones
   Agregar clases equivalentes si existen en la ontología

5. **Construcción del Subconjunto**:
   Desduplicar los elementos recopilados mientras se preservan las relaciones
   Organizar en clases, propiedades de objeto y propiedades de tipo de datos
   Asegurarse de que todas las restricciones y relaciones se preserven
   Crear una mini-ontología autocontenida que sea válida y completa

**Ejemplo de Demostración**:
Dado el texto: "The brown dog chased the white cat up the tree."
Segmentos: ["brown dog", "white cat", "tree", "chased"]
Elementos coincidentes: [dog (class), cat (class), animal (parent), chases (property)]
Dependencias: [animal (parent of dog and cat), lifeform (parent of animal)]
Subconjunto final: Mini-ontología completa con la jerarquía de animales y la relación de persecución

### Validación de Triples

**Propósito**: Asegura que todas las triples extraídas cumplan estrictamente con las restricciones de la ontología.

**Algoritmo de Validación**:

1. **Validación de Clases**:
   Verificar que los sujetos sean instancias de clases definidas en el subconjunto de la ontología.
   Para las propiedades de objeto, verificar que los objetos también sean instancias de clases válidas.
   Comprobar los nombres de las clases contra el diccionario de clases de la ontología.
   Manejar las jerarquías de clases: las instancias de subclases son válidas para las restricciones de la clase principal.

2. **Validación de Propiedades**:
   Confirmar que los predicados corresponden a las propiedades del subconjunto de la ontología.
   Distinguir entre propiedades de objeto (entidad a entidad) y propiedades de tipo de datos (entidad a literal).
   Verificar que los nombres de las propiedades coincidan exactamente (considerando el espacio de nombres si está presente).

3. **Comprobación de Dominio/Rango**:
   Para cada propiedad utilizada como predicado, recuperar su dominio y rango.
   Verificar que el tipo del sujeto coincida o herede del dominio de la propiedad.
   Verificar que el tipo del objeto coincida o herede del rango de la propiedad.
   Para las propiedades de tipo de datos, verificar que el objeto sea un literal del tipo XSD correcto.

4. **Validación de Cardinalidad**:
   Registrar los recuentos de uso de la propiedad por sujeto.
   Comprobar la cardinalidad mínima: asegurarse de que las propiedades requeridas estén presentes.
   Comprobar la cardinalidad máxima: asegurarse de que la propiedad no se utilice demasiadas veces.
   Para las propiedades funcionales, asegurarse de que haya como máximo un valor por sujeto.

5. **Validación de Tipos de Datos**:
   Analizar los valores literales según sus tipos XSD declarados.
   Validar que los enteros sean números válidos, que las fechas tengan un formato correcto, etc.
   Comprobar los patrones de cadena si se definen restricciones de expresión regular.
   Asegurarse de que las URIs estén bien formadas para los tipos xsd:anyURI.

**Ejemplo de Validación**:
Triple: ("Buddy", "tiene-dueño", "John")
Comprobar que "Buddy" esté tipado como una clase que puede tener la propiedad "tiene-dueño".
Comprobar que "tiene-dueño" exista en la ontología.
Verificar la restricción de dominio: el sujeto debe ser de tipo "Mascota" o subclase.
Verificar la restricción de rango: el objeto debe ser de tipo "Persona" o subclase.
Si es válido, agregar a la salida; si no es válido, registrar la violación y omitir.

## Consideraciones de Rendimiento

### Estrategias de Optimización

1. **Caché de Incrustaciones**: Almacenar en caché las incrustaciones para segmentos de texto utilizados con frecuencia.
2. **Procesamiento por Lotes**: Procesar múltiples segmentos en paralelo.
3. **Indexación de Almacenes Vectoriales**: Utilizar algoritmos de vecinos más cercanos aproximados para ontologías grandes.
4. **Optimización de Indicaciones**: Minimizar el tamaño de la indicación incluyendo solo los elementos esenciales de la ontología.
5. **Caché de Resultados**: Almacenar en caché los resultados de la extracción para fragmentos idénticos.

### Escalabilidad

**Escalabilidad Horizontal**: Múltiples instancias del extractor con un caché de ontología compartido.
**Partición de Ontologías**: Dividir ontologías grandes por dominio.
**Procesamiento por Transmisión**: Procesar fragmentos a medida que llegan sin agruparlos.
**Gestión de Memoria**: Limpieza periódica de incrustaciones no utilizadas.

## Manejo de Errores

### Escenarios de Fallo

1. **Ontologías Faltantes**: Recurrir a la extracción sin restricciones.
2. **Fallo del Servicio de Incrustaciones**: Utilizar incrustaciones almacenadas en caché o omitir la coincidencia semántica.
3. **Tiempo de Espera del Servicio de Indicaciones**: Reintentar con retroceso exponencial.
4. **Formato de Triple Inválido**: Registrar y omitir triples mal formados.
5. **Inconsistencias de la Ontología**: Informar de conflictos y utilizar los elementos válidos más específicos.

### Monitorización

Métricas clave a seguir:

Tiempo de carga de la ontología y uso de memoria.
Latencia de generación de incrustaciones.
Rendimiento de la búsqueda vectorial.
Tiempo de respuesta del servicio de indicaciones.
Precisión de la extracción de triples.
Tasa de conformidad de la ontología.

## Ruta de Migración

### Desde Extractores Existentes

1. **Operación Paralela**: Ejecutar junto con los extractores existentes inicialmente.
2. **Implementación Gradual**: Comenzar con tipos de documentos específicos.
3. **Comparación de Calidad**: Comparar la calidad de la salida con los extractores existentes.
4. **Migración Completa**: Reemplazar los extractores existentes una vez que se haya verificado la calidad.

### Desarrollo de Ontologías

1. **Generación Inicial desde Conocimiento Existente**: Generar ontologías iniciales a partir de conocimiento existente.
2. **Refinamiento Iterativo**: Refinar basándose en patrones de extracción.
3. **Revisión por Expertos en la Materia**: Validar con expertos en la materia.
4. **Mejora Continua**: Actualizar basándose en la retroalimentación de la extracción.

## Servicio de Consulta Sensible a la Ontología

### Descripción General

El servicio de consulta sensible a la ontología proporciona múltiples rutas de consulta para admitir diferentes almacenes de grafos de backend. Aprovecha el conocimiento de la ontología para una respuesta a preguntas precisa y semánticamente consciente en diferentes almacenes de grafos, tanto Cassandra (a través de SPARQL) como almacenes de grafos basados en Cypher (Neo4j, Memgraph, FalkorDB).

**Componentes del Servicio**:
`onto-query-sparql`: Convierte el lenguaje natural a SPARQL para Cassandra.
`sparql-cassandra`: Capa de consulta SPARQL para Cassandra que utiliza rdflib.
`onto-query-cypher`: Convierte el lenguaje natural a Cypher para bases de datos de grafos.
`cypher-executor`: Ejecución de consultas Cypher para Neo4j/Memgraph/FalkorDB.

### Arquitectura

```
                    ┌─────────────────┐
                    │   User Query    │
                    └────────┬────────┘
                             │
                             ▼
                    ┌─────────────────┐      ┌──────────────┐
                    │   Question      │────▶│   Sentence   │
                    │   Analyser      │      │   Splitter   │
                    └────────┬────────┘      └──────────────┘
                             │
                             ▼
                    ┌─────────────────┐      ┌──────────────┐
                    │   Ontology      │────▶│   Vector     │
                    │   Matcher       │      │    Store     │
                    └────────┬────────┘      └──────────────┘
                             │
                             ▼
                    ┌─────────────────┐
                    │ Backend Router  │
                    └────────┬────────┘
                             │
                 ┌───────────┴───────────┐
                 │                       │
                 ▼                       ▼
    ┌─────────────────┐          ┌─────────────────┐
    │ onto-query-     │          │ onto-query-     │
    │    sparql       │          │    cypher       │
    └────────┬────────┘          └────────┬────────┘
             │                            │
             ▼                            ▼
    ┌─────────────────┐          ┌─────────────────┐
    │   SPARQL        │          │   Cypher        │
    │  Generator      │          │  Generator      │
    └────────┬────────┘          └────────┬────────┘
             │                            │
             ▼                            ▼
    ┌─────────────────┐          ┌─────────────────┐
    │ sparql-         │          │ cypher-         │
    │ cassandra       │          │ executor        │
    └────────┬────────┘          └────────┬────────┘
             │                            │
             ▼                            ▼
    ┌─────────────────┐          ┌─────────────────┐
    │   Cassandra     │          │ Neo4j/Memgraph/ │
    │                 │          │   FalkorDB      │
    └────────┬────────┘          └────────┬────────┘
             │                            │
             └────────────┬───────────────┘
                          │
                          ▼
                 ┌─────────────────┐      ┌──────────────┐
                 │   Answer        │────▶│   Prompt     │
                 │  Generator      │      │   Service    │
                 └────────┬────────┘      └──────────────┘
                          │
                          ▼
                 ┌─────────────────┐
                 │  Final Answer   │
                 └─────────────────┘
```

### Query Processing Pipeline

#### 1. Question Analyser

**Purpose**: Decomposes user questions into semantic components for ontology matching.

**Algorithm Description**:
The Question Analyser takes the incoming natural language question and breaks it down into meaningful segments using the same sentence splitting approach as the extraction pipeline. It identifies key entities, relationships, and constraints mentioned in the question. Each segment is analysed for question type (factual, aggregation, comparison, etc.) and the expected answer format. This decomposition helps identify which parts of the ontology are most relevant for answering the question.

**Key Operations**:
Split question into sentences and phrases
Identify question type and intent
Extract mentioned entities and relationships
Detect constraints and filters in the question
Determine expected answer format

#### 2. Ontology Matcher for Queries

**Purpose**: Identifies the relevant ontology subset needed to answer the question.

**Algorithm Description**:
Similar to the extraction pipeline's Ontology Selector, but optimised for question answering. The matcher generates embeddings for question segments and searches the vector store for relevant ontology elements. However, it focuses on finding concepts that would be useful for query construction rather than extraction. It expands the selection to include related properties that might be traversed during graph exploration, even if not explicitly mentioned in the question. For example, if asked about "employees," it might include properties like "works-for," "manages," and "reports-to" that could be relevant for finding employee information.

**Matching Strategy**:
Embed question segments
Find directly mentioned ontology concepts
Include properties that connect mentioned classes
Add inverse and related properties for traversal
Include parent/child classes for hierarchical queries
Build query-focused ontology partition

#### 3. Backend Router

**Purpose**: Routes queries to the appropriate backend-specific query path based on configuration.

**Algorithm Description**:
The Backend Router examines the system configuration to determine which graph backend is active (Cassandra or Cypher-based). It routes the question and ontology partition to the appropriate query generation service. The router can also support load balancing across multiple backends or fallback mechanisms if the primary backend is unavailable.

**Routing Logic**:
Check configured backend type from system settings
Route to `onto-query-sparql` for Cassandra backends
Route to `onto-query-cypher` for Neo4j/Memgraph/FalkorDB
Support multi-backend configurations with query distribution
Handle failover and load balancing scenarios

#### 4. SPARQL Query Generation (`onto-query-sparql`)

**Purpose**: Converts natural language questions to SPARQL queries for Cassandra execution.

**Algorithm Description**:
The SPARQL query generator takes the question and ontology partition and constructs a SPARQL query optimised for execution against the Cassandra backend. It uses the prompt service with a SPARQL-specific template that includes RDF/OWL semantics. The generator understands SPARQL patterns like property paths, optional clauses, and filters that can efficiently translate to Cassandra operations.

**SPARQL Generation Prompt Template**:
```
Generate a SPARQL query for the following question using the provided ontology.

ONTOLOGY CLASSES:
{classes}

ONTOLOGY PROPERTIES:
{properties}

RULES:
- Use proper RDF/OWL semantics
- Include relevant prefixes
- Use property paths for hierarchical queries
- Add FILTER clauses for constraints
- Optimise for Cassandra backend

QUESTION: {question}

SPARQL QUERY:
```

#### 5. Generación de Consultas Cypher (`onto-query-cypher`)

**Propósito**: Convierte preguntas en lenguaje natural en consultas Cypher para bases de datos de grafos.

**Descripción del Algoritmo**:
El generador de consultas Cypher crea consultas Cypher nativas optimizadas para Neo4j, Memgraph y FalkorDB. Mapea clases de ontología a etiquetas de nodos y propiedades a relaciones, utilizando la sintaxis de coincidencia de patrones de Cypher. El generador incluye optimizaciones específicas de Cypher, como sugerencias de dirección de relación, uso de índices y sugerencias de planificación de consultas.

**Plantilla de Indicación para la Generación de Cypher**:
```
Generate a Cypher query for the following question using the provided ontology.

NODE LABELS (from classes):
{classes}

RELATIONSHIP TYPES (from properties):
{properties}

RULES:
- Use MATCH patterns for graph traversal
- Include WHERE clauses for filters
- Use aggregation functions when needed
- Optimise for graph database performance
- Consider index hints for large datasets

QUESTION: {question}

CYPHER QUERY:
```

#### 6. Motor de Consulta SPARQL-Cassandra (`sparql-cassandra`)

**Propósito**: Ejecuta consultas SPARQL contra Cassandra utilizando Python rdflib.

**Descripción del Algoritmo**:
El motor SPARQL-Cassandra implementa un procesador SPARQL utilizando la biblioteca rdflib de Python con un almacenamiento backend personalizado para Cassandra. Traduce los patrones de grafo SPARQL en consultas CQL de Cassandra apropiadas, manejando uniones, filtros y agregaciones. El motor mantiene un mapeo de RDF a Cassandra que preserva la estructura semántica al tiempo que optimiza para el modelo de almacenamiento de familias de columnas de Cassandra.

**Características de la Implementación**:
Implementación de la interfaz de almacenamiento rdflib para Cassandra
Soporte para consultas SPARQL 1.1 con patrones comunes
Traducción eficiente de patrones de triple a CQL
Soporte para rutas de propiedades y consultas jerárquicas
Transmisión de resultados para conjuntos de datos grandes
Agrupación de conexiones y almacenamiento en caché de consultas

**Ejemplo de Traducción**:
```sparql
SELECT ?animal WHERE {
  ?animal rdf:type :Animal .
  ?animal :hasOwner "John" .
}
```
Traduce a consultas optimizadas de Cassandra que aprovechan los índices y las claves de partición.

#### 7. Ejecutor de Consultas Cypher (`cypher-executor`)

**Propósito**: Ejecuta consultas Cypher contra Neo4j, Memgraph y FalkorDB.

**Descripción del Algoritmo**:
El ejecutor de Cypher proporciona una interfaz unificada para ejecutar consultas Cypher en diferentes bases de datos de grafos. Maneja protocolos de conexión específicos de la base de datos, sugerencias de optimización de consultas y normalización del formato de resultados. El ejecutor incluye lógica de reintento, agrupación de conexiones y gestión de transacciones adecuadas para cada tipo de base de datos.

**Soporte para Múltiples Bases de Datos**:
**Neo4j**: Protocolo Bolt, funciones de transacción, sugerencias de índice
**Memgraph**: Protocolo personalizado, resultados de transmisión, consultas analíticas
**FalkorDB**: Adaptación del protocolo Redis, optimizaciones en memoria

**Características de Ejecución**:
Gestión de conexiones independiente de la base de datos
Validación de consultas y verificación de sintaxis
Aplicación de límites de tiempo y recursos
Paginación y transmisión de resultados
Monitoreo de rendimiento por tipo de base de datos
Conmutación por error automática entre instancias de base de datos

#### 8. Generador de Respuestas

**Propósito**: Sintetiza una respuesta en lenguaje natural a partir de los resultados de la consulta.

**Descripción del Algoritmo**:
El Generador de Respuestas toma los resultados de la consulta estructurados y la pregunta original, y luego utiliza el servicio de prompts para generar una respuesta completa. A diferencia de las respuestas simples basadas en plantillas, utiliza un LLM para interpretar los datos del grafo en el contexto de la pregunta, manejando relaciones complejas, agregaciones y inferencias. El generador puede explicar su razonamiento haciendo referencia a la estructura de la ontología y a los triples específicos recuperados del grafo.

**Proceso de Generación de Respuestas**:
Formatea los resultados de la consulta en un contexto estructurado
Incluye definiciones de ontología relevantes para mayor claridad
Construye un prompt con la pregunta y los resultados
Genera una respuesta en lenguaje natural mediante un LLM
Valida la respuesta con respecto a la intención de la consulta
Agrega citas a entidades específicas del grafo si es necesario

### Integración con Servicios Existentes

#### Relación con GraphRAG

**Complementario**: onto-query proporciona precisión semántica mientras que GraphRAG proporciona una cobertura amplia
**Infraestructura Compartida**: Ambos utilizan el mismo grafo de conocimiento y servicios de prompts
**Enrutamiento de Consultas**: El sistema puede enrutar las consultas al servicio más apropiado según el tipo de pregunta
**Modo Híbrido**: Puede combinar ambos enfoques para obtener respuestas completas

#### Relación con OntoRAG Extraction

**Ontologías Compartidas**: Utiliza las mismas configuraciones de ontología cargadas por kg-extract-ontology
**Almacén de Vectores Compartido**: Reutiliza los embeddings en memoria del servicio de extracción
**Semántica Consistente**: Las consultas operan en grafos construidos con las mismas restricciones ontológicas

### Ejemplos de Consultas

#### Ejemplo 1: Consulta Simple de Entidad
**Pregunta**: "¿Qué animales son mamíferos?"
**Coincidencia de Ontología**: [animal, mammal, subClassOf]
**Consulta Generada**:
```cypher
MATCH (a:animal)-[:subClassOf*]->(m:mammal)
RETURN a.name
```

#### Ejemplo 2: Consulta de Relación
**Pregunta**: "¿Qué documentos fueron escritos por John Smith?"
**Correspondencia con la Ontología**: [documento, persona, tiene-autor]
**Consulta Generada**:
```cypher
MATCH (d:document)-[:has-author]->(p:person {name: "John Smith"})
RETURN d.title, d.date
```

#### Ejemplo 3: Consulta de agregación
**Pregunta**: "¿Cuántas patas tienen los gatos?"
**Coincidencia con la ontología**: [gato, número-de-patas (propiedad de tipo de dato)]
**Consulta generada**:
```cypher
MATCH (c:cat)
RETURN c.name, c.number_of_legs
```

### Configuración

```yaml
onto-query:
  embedding_model: "text-embedding-3-small"
  vector_store:
    shared_with_extractor: true  # Reuse kg-extract-ontology's store
  query_builder:
    model: "gpt-4"
    temperature: 0.1
    max_query_length: 1000
  graph_executor:
    timeout: 30000  # ms
    max_results: 1000
  answer_generator:
    model: "gpt-4"
    temperature: 0.3
    max_tokens: 500
```

### Optimizaciones de rendimiento

#### Optimización de consultas

**Poda de la ontología**: Incluir solo los elementos de la ontología necesarios en las indicaciones.
**Caché de consultas**: Almacenar en caché las preguntas frecuentes y sus consultas.
**Caché de resultados**: Almacenar los resultados para consultas idénticas dentro de un intervalo de tiempo.
**Procesamiento por lotes**: Manejar múltiples preguntas relacionadas en una sola exploración del grafo.

#### Consideraciones de escalabilidad

**Ejecución distribuida**: Paralelizar subconsultas en particiones del grafo.
**Resultados incrementales**: Transmitir los resultados para conjuntos de datos grandes.
**Equilibrio de carga**: Distribuir la carga de las consultas entre múltiples instancias de servicio.
**Grupos de recursos**: Administrar grupos de conexiones a bases de datos de grafos.

### Manejo de errores

#### Escenarios de fallo

1. **Generación de consultas inválidas**: Revertir a GraphRAG o a una búsqueda simple por palabras clave.
2. **Desajuste de la ontología**: Ampliar la búsqueda a un subconjunto más amplio de la ontología.
3. **Tiempo de espera de la consulta**: Simplificar la consulta o aumentar el tiempo de espera.
4. **Resultados vacíos**: Sugerir la reformulación de la consulta o preguntas relacionadas.
5. **Fallo del servicio LLM**: Utilizar consultas almacenadas en caché o respuestas basadas en plantillas.

### Métricas de monitoreo

Distribución de la complejidad de las preguntas.
Tamaños de las particiones de la ontología.
Tasa de éxito de la generación de consultas.
Tiempo de ejecución de las consultas al grafo.
Puntuaciones de calidad de las respuestas.
Tasas de aciertos de la caché.
Frecuencias de error por tipo.

## Mejoras futuras

1. **Aprendizaje de la ontología**: Extender automáticamente las ontologías basándose en patrones de extracción.
2. **Puntuación de confianza**: Asignar puntuaciones de confianza a las triples extraídas.
3. **Generación de explicaciones**: Proporcionar la justificación para la extracción de triples.
4. **Aprendizaje activo**: Solicitar la validación humana para las extracciones inciertas.

## Consideraciones de seguridad

1. **Prevención de la inyección de indicaciones**: Sanitizar el texto de los fragmentos antes de construir la indicación.
2. **Límites de recursos**: Limitar el uso de memoria para el almacén de vectores.
3. **Limitación de velocidad**: Limitar las solicitudes de extracción por cliente.
4. **Registro de auditoría**: Registrar todas las solicitudes y resultados de extracción.

## Estrategia de pruebas

### Pruebas unitarias

Carga de ontología con varios formatos.
Generación y almacenamiento de incrustaciones.
Algoritmos de división de oraciones.
Cálculos de similitud vectorial.
Análisis y validación de triples.

### Pruebas de integración

Canalización de extracción de extremo a extremo.
Integración del servicio de configuración.
Interacción con el servicio de indicaciones.
Manejo de extracción concurrente.

### Pruebas de rendimiento

Manejo de ontologías grandes (1000+ clases).
Procesamiento de gran volumen de fragmentos.
Uso de memoria bajo carga.
Referencias de latencia.

## Plan de entrega

### Resumen

El sistema OntoRAG se entregará en cuatro fases principales, con cada fase proporcionando valor incremental mientras se construye hacia el sistema completo. El plan se centra en establecer primero las capacidades básicas de extracción, luego agregar la funcionalidad de consulta, seguida de optimizaciones y funciones avanzadas.

### Fase 1: Fundación y extracción central

**Objetivo**: Establecer la canalización básica de extracción impulsada por la ontología con el simple emparejamiento de vectores.

#### Paso 1.1: Fundación de la gestión de la ontología
Implementar el cargador de configuración de la ontología (`OntologyLoader`).
Analizar y validar las estructuras JSON de la ontología.
Crear un almacenamiento de ontología en memoria y patrones de acceso.
Implementar un mecanismo de actualización de la ontología.

**Criterios de éxito**:
Cargar y analizar correctamente las configuraciones de la ontología.
Validar la estructura y la coherencia de la ontología.
Manejar múltiples ontologías concurrentes.

#### Paso 1.2: Implementación del almacén de vectores
Implementar un almacén de vectores simple basado en NumPy como prototipo inicial.
Agregar la implementación del almacén de vectores FAISS.
Crear una abstracción de interfaz para el almacén de vectores.
Implementar la búsqueda de similitud con umbrales configurables.

**Criterios de Éxito**:
Almacenar y recuperar incrustaciones de manera eficiente
Realizar búsquedas de similitud con una latencia menor a 100 ms
Soporte para backends NumPy y FAISS

#### Paso 1.3: Canal de Incrustación de Ontologías
Integración con el servicio de incrustación
Implementar componente `OntologyEmbedder`
Generar incrustaciones para todos los elementos de la ontología
Almacenar las incrustaciones con metadatos en el almacén de vectores

**Criterios de Éxito**:
Generar incrustaciones para clases y propiedades
Almacenar las incrustaciones con los metadatos correctos
Reconstruir las incrustaciones al actualizar la ontología

#### Paso 1.4: Componentes de Procesamiento de Texto
Implementar un divisor de oraciones utilizando NLTK/spaCy
Extraer frases y entidades nombradas
Crear una jerarquía de segmentos de texto
Generar incrustaciones para los segmentos de texto

**Criterios de Éxito**:
Dividir el texto en oraciones de forma precisa
Extraer frases significativas
Mantener las relaciones de contexto

#### Paso 1.5: Algoritmo de Selección de Ontología
Implementar la coincidencia de similitud entre el texto y la ontología
Construir la resolución de dependencias para los elementos de la ontología
Crear subconjuntos coherentes mínimos de la ontología
Optimizar el rendimiento de la generación de subconjuntos

**Criterios de Éxito**:
Seleccionar elementos de la ontología relevantes con una precisión >80%
Incluir todas las dependencias necesarias
Generar subconjuntos en <500 ms

#### Paso 1.6: Servicio de Extracción Básico
Implementar la construcción de indicaciones para la extracción
Integración con el servicio de indicaciones
Analizar y validar las respuestas de triple
Crear un punto final de servicio `kg-extract-ontology`

**Criterios de Éxito**:
Extraer triples conformes a la ontología
Validar todos los triples contra la ontología
Manejar los errores de extracción de forma elegante

### Fase 2: Implementación del Sistema de Consulta

**Objetivo**: Agregar capacidades de consulta con conocimiento de la ontología con soporte para múltiples backends.

#### Paso 2.1: Componentes Fundamentales de la Consulta
Implementar el analizador de preguntas
Crear un comparador de ontologías para las consultas
Adaptar la búsqueda vectorial al contexto de la consulta
Construir el componente de enrutamiento de backends

**Criterios de Éxito**:
Analizar las preguntas en componentes semánticos
Hacer coincidir las preguntas con los elementos de ontología relevantes
Enrutar las consultas al backend apropiado

#### Paso 2.2: Implementación de la Ruta SPARQL
Implementar el servicio `onto-query-sparql`
Crear un generador de consultas SPARQL utilizando LLM
Desarrollar plantillas de indicaciones para la generación de SPARQL
Validar la sintaxis SPARQL generada

**Criterios de Éxito**:
Generar consultas SPARQL válidas
Utilizar patrones SPARQL apropiados
Manejar tipos de consultas complejos

#### Paso 2.3: Motor SPARQL-Cassandra
Implementar la interfaz de almacenamiento rdflib para Cassandra
Crear un traductor de consultas CQL
Optimizar la coincidencia de patrones de triple
Manejar el formato de resultados de SPARQL

**Criterios de Éxito**:
Ejecutar consultas SPARQL en Cassandra
Soporte para patrones SPARQL comunes
Devolver resultados en formato estándar

#### Paso 2.4: Implementación de la Ruta Cypher
Implementar el servicio `onto-query-cypher`
Crear un generador de consultas Cypher utilizando LLM
Desarrollar plantillas de indicaciones para la generación de Cypher
Validar la sintaxis Cypher generada

**Criterios de Éxito**:
Generar consultas Cypher válidas
Utilizar patrones de grafos apropiados
Soporte para Neo4j, Memgraph, FalkorDB

#### Paso 2.5: Ejecutor de Cypher
Implement multi-database Cypher executor
Support Bolt protocol (Neo4j/Memgraph)
Support Redis protocol (FalkorDB)
Handle result normalization

**Success Criteria**:
Execute Cypher on all target databases
Handle database-specific differences
Maintain connection pools efficiently

#### Step 2.6: Answer Generation
Implement answer generator component
Create prompts for answer synthesis
Format query results for LLM consumption
Generate natural language answers

**Success Criteria**:
Generate accurate answers from query results
Maintain context from original question
Provide clear, concise responses

### Phase 3: Optimization and Robustness

**Goal**: Optimize performance, add caching, improve error handling, and enhance reliability.

#### Step 3.1: Performance Optimization
Implement embedding caching
Add query result caching
Optimize vector search with FAISS IVF indexes
Implement batch processing for embeddings

**Success Criteria**:
Reduce average query latency by 50%
Support 10x more concurrent requests
Maintain sub-second response times

#### Step 3.2: Advanced Error Handling
Implement comprehensive error recovery
Add fallback mechanisms between query paths
Create retry logic with exponential backoff
Improve error logging and diagnostics

**Success Criteria**:
Gracefully handle all failure scenarios
Automatic failover between backends
Detailed error reporting for debugging

#### Step 3.3: Monitoring and Observability
Add performance metrics collection
Implement query tracing
Create health check endpoints
Add resource usage monitoring

**Success Criteria**:
Track all key performance indicators
Identify bottlenecks quickly
Monitor system health in real-time

#### Step 3.4: Configuration Management
Implement dynamic configuration updates
Add configuration validation
Create configuration templates
Support environment-specific settings

**Success Criteria**:
Update configuration without restart
Validate all configuration changes
Support multiple deployment environments

### Phase 4: Advanced Features

**Goal**: Add sophisticated capabilities for production deployment and enhanced functionality.

#### Step 4.1: Multi-Ontology Support
Implement ontology selection logic
Support cross-ontology queries
Handle ontology versioning
Create ontology merge capabilities

**Success Criteria**:
Query across multiple ontologies
Handle ontology conflicts
Support ontology evolution

#### Step 4.2: Intelligent Query Routing
Implementar enrutamiento basado en el rendimiento
Agregar análisis de complejidad de la consulta
Crear algoritmos de enrutamiento adaptativos
Compatibilizar pruebas A/B para rutas

**Criterios de éxito**:
Enrutar las consultas de forma óptima
Aprender del rendimiento de las consultas
Mejorar el enrutamiento con el tiempo

#### Paso 4.3: Características Avanzadas de Extracción
Agregar puntuación de confianza para las triples
Implementar generación de explicaciones
Crear bucles de retroalimentación para la mejora
Compatibilizar aprendizaje incremental

**Criterios de éxito**:
Proporcionar puntuaciones de confianza
Explicar las decisiones de extracción
Mejorar continuamente la precisión

#### Paso 4.4: Endurecimiento para Producción
Agregar limitación de velocidad
Implementar autenticación/autorización
Crear automatización de implementación
Agregar copia de seguridad y recuperación

**Criterios de éxito**:
Seguridad lista para producción
Canal de implementación automatizado
Capacidad de recuperación ante desastres

### Hitos de Entrega

1. **Hito 1** (Fin de la Fase 1): Extracción básica basada en la ontología en funcionamiento
2. **Hito 2** (Fin de la Fase 2): Sistema de consulta completo con rutas SPARQL y Cypher
3. **Hito 3** (Fin de la Fase 3): Sistema optimizado y robusto listo para la etapa de pruebas
4. **Hito 4** (Fin de la Fase 4): Sistema listo para producción con características avanzadas

### Mitigación de Riesgos

#### Riesgos Técnicos
**Escalabilidad del Almacén de Vectores**: Comenzar con NumPy, migrar gradualmente a FAISS
**Precisión de la Generación de Consultas**: Implementar mecanismos de validación y respaldo
**Compatibilidad con el Backend**: Probar exhaustivamente con cada tipo de base de datos
**Cuellos de Botella de Rendimiento**: Perfil temprano y con frecuencia, optimizar de forma iterativa

#### Riesgos Operacionales
**Calidad de la Ontología**: Implementar validación y verificación de la consistencia
**Dependencias del Servicio**: Agregar interruptores de circuito y mecanismos de respaldo
**Restricciones de Recursos**: Monitorear y establecer límites apropiados
**Consistencia de Datos**: Implementar un manejo adecuado de transacciones

### Métricas de Éxito

#### Métricas de Éxito de la Fase 1
Precisión de la extracción: >90% de conformidad con la ontología
Velocidad de procesamiento: <1 segundo por fragmento
Tiempo de carga de la ontología: <10 segundos
Latencia de búsqueda de vectores: <100 ms

#### Métricas de Éxito de la Fase 2
Tasa de éxito de las consultas: >95%
Latencia de la consulta: <2 segundos de extremo a extremo
Compatibilidad con el backend: 100% para las bases de datos objetivo
Precisión de la respuesta: >85% según los datos disponibles

#### Métricas de Éxito de la Fase 3
Tiempo de actividad del sistema: >99.9%
Tasa de recuperación de errores: >95%
Tasa de aciertos en caché: >60%
Usuarios concurrentes: >100

#### Métricas de Éxito de la Fase 4
Consultas multi-ontología: Totalmente compatibles
Optimización del enrutamiento: Reducción de la latencia del 30%
Precisión de la puntuación de confianza: >90%
Implementación en producción: Actualizaciones sin tiempo de inactividad

## Referencias

[OWL 2 Web Ontology Language](https://www.w3.org/TR/owl2-overview/)
[GraphRAG Architecture](https://github.com/microsoft/graphrag)
[Sentence Transformers](https://www.sbert.net/)
[FAISS Vector Search](https://github.com/facebookresearch/faiss)
[spaCy NLP Library](https://spacy.io/)
[rdflib Documentation](https://rdflib.readthedocs.io/)
[Neo4j Bolt Protocol](https://neo4j.com/docs/bolt/current/)
