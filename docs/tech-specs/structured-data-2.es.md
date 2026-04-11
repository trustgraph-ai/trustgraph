# Especificación Técnica de Datos Estructurados (Parte 2)

## Resumen

Esta especificación aborda los problemas y las deficiencias identificadas durante la implementación inicial de la integración de datos estructurados de TrustGraph, como se describe en `structured-data.md`.

## Declaraciones del Problema

### 1. Inconsistencia en la Nomenclatura: "Objeto" vs "Fila"

La implementación actual utiliza la terminología de "objeto" en todo (por ejemplo, `ExtractedObject`, extracción de objetos, incrustaciones de objetos). Esta nomenclatura es demasiado genérica y causa confusión:

"Objeto" es un término ambiguo en el software (objetos de Python, objetos JSON, etc.)
Los datos que se están manejando son fundamentalmente tabulares: filas en tablas con esquemas definidos.
"Fila" describe con mayor precisión el modelo de datos y se alinea con la terminología de la base de datos.

Esta inconsistencia aparece en los nombres de los módulos, los nombres de las clases, los tipos de mensajes y la documentación.

### 2. Limitaciones de Consulta de la Tienda de Filas

La implementación actual de la tienda de filas tiene limitaciones de consulta significativas:

**Desajuste con el Lenguaje Natural**: Las consultas tienen dificultades con las variaciones de datos del mundo real. Por ejemplo:
Es difícil encontrar una base de datos de calles que contenga `"CHESTNUT ST"` cuando se pregunta por `"Chestnut Street"`.
Las abreviaturas, las diferencias de mayúsculas y minúsculas y las variaciones de formato interrumpen las consultas de coincidencia exacta.
Los usuarios esperan una comprensión semántica, pero la tienda proporciona una coincidencia literal.

**Problemas de Evolución del Esquema**: Los cambios en los esquemas causan problemas:
Los datos existentes pueden no cumplir con los esquemas actualizados.
Los cambios en la estructura de la tabla pueden romper las consultas y la integridad de los datos.
No hay una ruta de migración clara para las actualizaciones del esquema.

### 3. Se Requieren Incrustaciones de Filas

Relacionado con el problema 2, el sistema necesita incrustaciones vectoriales para los datos de las filas para permitir:

Búsqueda semántica en datos estructurados (encontrar "Chestnut Street" cuando los datos contienen "CHESTNUT ST").
Coincidencia de similitud para consultas difusas.
Búsqueda híbrida que combina filtros estructurados con similitud semántica.
Mejor soporte para consultas en lenguaje natural.

El servicio de incrustación se especificó pero no se implementó.

### 4. Ingesta de Datos de Filas Incompleta

La canalización de ingesta de datos estructurados no está completamente operativa:

Existen indicaciones de diagnóstico para clasificar los formatos de entrada (CSV, JSON, etc.).
El servicio de ingesta que utiliza estas indicaciones no está integrado en el sistema.
No hay una ruta de extremo a extremo para cargar datos preestructurados en la tienda de filas.

## Objetivos

**Flexibilidad del Esquema**: Permitir la evolución del esquema sin romper los datos existentes ni requerir migraciones.
**Nomenclatura Consistente**: Estandarizar la terminología de "fila" en todo el código base.
**Consultas Semánticas**: Compatibilidad con la coincidencia difusa/semántica a través de incrustaciones de filas.
**Canalización de Ingesta Completa**: Proporcionar una ruta de extremo a extremo para cargar datos estructurados.

## Diseño Técnico

### Esquema Unificado de Almacenamiento de Filas

La implementación anterior creó una tabla de Cassandra separada para cada esquema. Esto causó problemas cuando los esquemas evolucionaron, ya que los cambios en la estructura de la tabla requerían migraciones.

El nuevo diseño utiliza una única tabla unificada para todos los datos de filas:

```sql
CREATE TABLE rows (
    collection text,
    schema_name text,
    index_name text,
    index_value frozen<list<text>>,
    data map<text, text>,
    source text,
    PRIMARY KEY ((collection, schema_name, index_name), index_value)
)
```

#### Definiciones de columnas

| Columna | Tipo | Descripción |
|--------|------|-------------|
| `collection` | `text` | Identificador de recolección/importación de datos (procedente de metadatos) |
| `schema_name` | `text` | Nombre del esquema al que se ajusta esta fila |
| `index_name` | `text` | Nombre del(los) campo(s) indexado(s), unidos por comas para compuestos |
| `index_value` | `frozen<list<text>>` | Valor(es) del índice como una lista |
| `data` | `map<text, text>` | Datos de la fila como pares clave-valor |
| `source` | `text` | URI opcional que enlaza a información de procedencia en el grafo de conocimiento. Una cadena vacía o NULL indica que no hay fuente. |

#### Manejo de índices

Cada fila se almacena varias veces: una vez por cada campo indexado definido en el esquema. Los campos de clave primaria se tratan como un índice sin un marcador especial, lo que proporciona flexibilidad futura.

**Ejemplo de índice de un solo campo:**
El esquema define `email` como indexado
`index_name = "email"`
`index_value = ['foo@bar.com']`

**Ejemplo de índice compuesto:**
El esquema define un índice compuesto en `region` y `status`
`index_name = "region,status"` (nombres de los campos ordenados y unidos por comas)
`index_value = ['US', 'active']` (valores en el mismo orden que los nombres de los campos)

**Ejemplo de clave primaria:**
El esquema define `customer_id` como clave primaria
`index_name = "customer_id"`
`index_value = ['CUST001']`

#### Patrones de consulta

Todas las consultas siguen el mismo patrón, independientemente del índice que se utilice:

```sql
SELECT * FROM rows
WHERE collection = 'import_2024'
  AND schema_name = 'customers'
  AND index_name = 'email'
  AND index_value = ['foo@bar.com']
```

#### Compensaciones de diseño

**Ventajas:**
Los cambios de esquema no requieren cambios en la estructura de la tabla.
Los datos de las filas son opacos para Cassandra; las adiciones/eliminaciones de campos son transparentes.
Patrón de consulta consistente para todos los métodos de acceso.
No hay índices secundarios de Cassandra (que pueden ser lentos a escala).
Tipos nativos de Cassandra en todo momento (`map`, `frozen<list>`).

**Compensaciones:**
Amplificación de escritura: cada inserción de fila = N inserciones (una por cada campo indexado).
Sobrecarga de almacenamiento debido a la duplicación de datos de las filas.
La información del tipo se almacena en la configuración del esquema, la conversión se realiza en la capa de la aplicación.

#### Modelo de consistencia

El diseño acepta ciertas simplificaciones:

1. **Sin actualizaciones de filas**: El sistema es de solo escritura. Esto elimina las preocupaciones de coherencia sobre la actualización de múltiples copias de la misma fila.

2. **Tolerancia a los cambios de esquema**: Cuando los esquemas cambian (por ejemplo, se agregan o eliminan índices), las filas existentes conservan su indexación original. Las filas antiguas no se podrán descubrir a través de nuevos índices. Los usuarios pueden eliminar y recrear un esquema para garantizar la coherencia si es necesario.

### Seguimiento y eliminación de particiones

#### El problema

Con la clave de partición `(collection, schema_name, index_name)`, la eliminación eficiente requiere conocer todas las claves de partición para eliminar. Eliminar solo por `collection` o `collection + schema_name` requiere conocer todos los valores de `index_name` que tienen datos.

#### Tabla de seguimiento de particiones

Una tabla de búsqueda secundaria realiza un seguimiento de qué particiones existen:

```sql
CREATE TABLE row_partitions (
    collection text,
    schema_name text,
    index_name text,
    PRIMARY KEY ((collection), schema_name, index_name)
)
```

Esto permite una detección eficiente de particiones para operaciones de eliminación.

#### Comportamiento del Escritor de Filas

El escritor de filas mantiene una caché en memoria de pares registrados de `(collection, schema_name)`. Al procesar una fila:

1. Comprobar si `(collection, schema_name)` está en la caché.
2. Si no está en la caché (primera fila para este par):
   Buscar la configuración del esquema para obtener todos los nombres de índice.
   Insertar entradas en `row_partitions` para cada `(collection, schema_name, index_name)`.
   Agregar el par a la caché.
3. Continuar con la escritura de los datos de la fila.

El escritor de filas también supervisa los eventos de cambio de configuración del esquema. Cuando cambia un esquema, las entradas de caché relevantes se eliminan para que la siguiente fila active un nuevo registro con los nombres de índice actualizados.

Este enfoque garantiza:
Las escrituras de la tabla de búsqueda se realizan una vez por par de `(collection, schema_name)`, no por fila.
La tabla de búsqueda refleja los índices que estaban activos cuando se escribieron los datos.
Los cambios de esquema durante la importación se detectan correctamente.

#### Operaciones de Eliminación

**Eliminar colección:**
```sql
-- 1. Discover all partitions
SELECT schema_name, index_name FROM row_partitions WHERE collection = 'X';

-- 2. Delete each partition from rows table
DELETE FROM rows WHERE collection = 'X' AND schema_name = '...' AND index_name = '...';
-- (repeat for each discovered partition)

-- 3. Clean up the lookup table
DELETE FROM row_partitions WHERE collection = 'X';
```

**Eliminar colección + esquema:**
```sql
-- 1. Discover partitions for this schema
SELECT index_name FROM row_partitions WHERE collection = 'X' AND schema_name = 'Y';

-- 2. Delete each partition from rows table
DELETE FROM rows WHERE collection = 'X' AND schema_name = 'Y' AND index_name = '...';
-- (repeat for each discovered partition)

-- 3. Clean up the lookup table entries
DELETE FROM row_partitions WHERE collection = 'X' AND schema_name = 'Y';
```

### Incrustaciones de Filas

Las incrustaciones de filas permiten la coincidencia semántica/difusa en los valores indexados, resolviendo el problema de la falta de coincidencia del lenguaje natural (por ejemplo, encontrar "CHESTNUT ST" al buscar "Chestnut Street").

#### Descripción General del Diseño

Cada valor indexado se incrusta y se almacena en un almacén de vectores (Qdrant). En el momento de la consulta, la consulta se incrusta, se encuentran vectores similares y los metadatos asociados se utilizan para buscar las filas reales en Cassandra.

#### Estructura de la Colección Qdrant

Una colección Qdrant por tupla `(user, collection, schema_name, dimension)`:

**Nombre de la colección:** `rows_{user}_{collection}_{schema_name}_{dimension}`
Los nombres se limpian (los caracteres no alfanuméricos se reemplazan con `_`, se convierten a minúsculas, los prefijos numéricos reciben el prefijo `r_`)
**Justificación:** Permite la eliminación limpia de una instancia `(user, collection, schema_name)` eliminando las colecciones Qdrant correspondientes; el sufijo de dimensión permite que diferentes modelos de incrustación coexistan.

#### Qué se Incrusta

La representación de texto de los valores de índice:

| Tipo de Índice | Ejemplo `index_value` | Texto a Incrustar |
|------------|----------------------|---------------|
| Campo único | `['foo@bar.com']` | `"foo@bar.com"` |
| Compuesto | `['US', 'active']` | `"US active"` (unidos por espacios) |

#### Estructura del Punto

Cada punto Qdrant contiene:

```json
{
  "id": "<uuid>",
  "vector": [0.1, 0.2, ...],
  "payload": {
    "index_name": "street_name",
    "index_value": ["CHESTNUT ST"],
    "text": "CHESTNUT ST"
  }
}
```

| Campo de carga útil | Descripción |
|---------------|-------------|
| `index_name` | Los campos indexados que representa esta incrustación. |
| `index_value` | La lista original de valores (para la búsqueda en Cassandra). |
| `text` | El texto que se incrustó (para depuración/visualización). |

Nota: `user`, `collection` y `schema_name` se derivan implícitamente del nombre de la colección de Qdrant.

#### Flujo de consulta

1. El usuario consulta "Chestnut Street" dentro del usuario U, la colección X, el esquema Y.
2. Incrusta el texto de la consulta.
3. Determina el(los) nombre(s) de la colección de Qdrant que coinciden con el prefijo `rows_U_X_Y_`.
4. Busca en la(s) colección(es) de Qdrant que coincidan para encontrar los vectores más cercanos.
5. Obtiene los puntos coincidentes con cargas útiles que contienen `index_name` y `index_value`.
6. Consulta Cassandra:
   ```sql
   SELECT * FROM rows
   WHERE collection = 'X'
     AND schema_name = 'Y'
     AND index_name = '<from payload>'
     AND index_value = <from payload>
   ```
7. Devolver filas coincidentes

#### Opcional: Filtrado por Nombre de Índice

Las consultas pueden filtrar opcionalmente por `index_name` en Qdrant para buscar solo campos específicos:

**"Encontrar cualquier campo que coincida con 'Chestnut'"** → buscar todos los vectores en la colección
**"Encontrar street_name que coincida con 'Chestnut'"** → filtrar donde `payload.index_name = 'street_name'`

#### Arquitectura

Los incrustados de filas siguen el **patrón de dos etapas** utilizado por GraphRAG (incrustados de grafos, incrustados de documentos):

**Etapa 1: Cálculo de incrustados** (`trustgraph-flow/trustgraph/embeddings/row_embeddings/`) - Consume `ExtractedObject`, calcula incrustados a través del servicio de incrustados, produce `RowEmbeddings`
**Etapa 2: Almacenamiento de incrustados** (`trustgraph-flow/trustgraph/storage/row_embeddings/qdrant/`) - Consume `RowEmbeddings`, escribe vectores en Qdrant

El escritor de filas de Cassandra es un consumidor paralelo separado:

**Escritor de filas de Cassandra** (`trustgraph-flow/trustgraph/storage/rows/cassandra`) - Consume `ExtractedObject`, escribe filas en Cassandra

Los tres servicios consumen del mismo flujo, manteniéndolos desacoplados. Esto permite:
Escalado independiente de las escrituras de Cassandra frente a la generación de incrustados frente al almacenamiento de vectores
Los servicios de incrustados se pueden desactivar si no son necesarios
Las fallas en un servicio no afectan a los demás
Arquitectura consistente con las canalizaciones de GraphRAG

#### Ruta de Escritura

**Etapa 1 (procesador de incrustados de filas):** Al recibir un `ExtractedObject`:

1. Buscar el esquema para encontrar campos indexados
2. Para cada campo indexado:
   Construir la representación de texto del valor del índice
   Calcular el incrustado a través del servicio de incrustados
3. Producir un mensaje `RowEmbeddings` que contenga todos los vectores calculados

**Etapa 2 (escritura de incrustados de filas en Qdrant):** Al recibir un `RowEmbeddings`:

1. Para cada incrustado en el mensaje:
   Determinar la colección de Qdrant a partir de `(user, collection, schema_name, dimension)`
   Crear la colección si es necesario (creación perezosa en la primera escritura)
   Insertar el punto con el vector y la carga útil

#### Tipos de Mensajes

```python
@dataclass
class RowIndexEmbedding:
    index_name: str              # The indexed field name(s)
    index_value: list[str]       # The field value(s)
    text: str                    # Text that was embedded
    vectors: list[list[float]]   # Computed embedding vectors

@dataclass
class RowEmbeddings:
    metadata: Metadata
    schema_name: str
    embeddings: list[RowIndexEmbedding]
```

#### Integración de Eliminación

Las colecciones de Qdrant se descubren mediante la comparación de prefijos en el patrón de nombre de la colección:

**Eliminar `(user, collection)`:**
1. Listar todas las colecciones de Qdrant que coincidan con el prefijo `rows_{user}_{collection}_`
2. Eliminar cada colección que coincida
3. Eliminar particiones de filas de Cassandra (como se documenta anteriormente)
4. Limpiar las entradas de `row_partitions`

**Eliminar `(user, collection, schema_name)`:**
1. Listar todas las colecciones de Qdrant que coincidan con el prefijo `rows_{user}_{collection}_{schema_name}_`
2. Eliminar cada colección que coincida (maneja múltiples dimensiones)
3. Eliminar particiones de filas de Cassandra
4. Limpiar `row_partitions`

#### Ubicaciones de los Módulos

| Etapa | Módulo | Punto de Entrada |
|-------|--------|-------------|
| Etapa 1 | `trustgraph-flow/trustgraph/embeddings/row_embeddings/` | `row-embeddings` |
| Etapa 2 | `trustgraph-flow/trustgraph/storage/row_embeddings/qdrant/` | `row-embeddings-write-qdrant` |

### API de Consulta de Incrustaciones de Filas

La consulta de incrustaciones de filas es una **API separada** del servicio de consulta de filas GraphQL:

| API | Propósito | Backend |
|-----|---------|---------|
| Consulta de Filas (GraphQL) | Coincidencia exacta en campos indexados | Cassandra |
| Consulta de Incrustaciones de Filas | Coincidencia difusa/semántica | Qdrant |

Esta separación mantiene la claridad:
El servicio GraphQL se enfoca en consultas exactas y estructuradas
La API de incrustaciones maneja la similitud semántica
Flujo de trabajo del usuario: búsqueda difusa a través de incrustaciones para encontrar candidatos, luego una consulta exacta para obtener los datos completos de la fila

#### Esquema de Solicitud/Respuesta

```python
@dataclass
class RowEmbeddingsRequest:
    vectors: list[list[float]]    # Query vectors (pre-computed embeddings)
    user: str = ""
    collection: str = ""
    schema_name: str = ""
    index_name: str = ""          # Optional: filter to specific index
    limit: int = 10               # Max results per vector

@dataclass
class RowIndexMatch:
    index_name: str = ""          # The matched index field(s)
    index_value: list[str] = []   # The matched value(s)
    text: str = ""                # Original text that was embedded
    score: float = 0.0            # Similarity score

@dataclass
class RowEmbeddingsResponse:
    error: Error | None = None
    matches: list[RowIndexMatch] = []
```

#### Procesador de Consultas

Módulo: `trustgraph-flow/trustgraph/query/row_embeddings/qdrant`

Punto de entrada: `row-embeddings-query-qdrant`

El procesador:
1. Recibe `RowEmbeddingsRequest` con vectores de consulta
2. Encuentra la colección Qdrant apropiada mediante la coincidencia de prefijos
3. Busca los vectores más cercanos con un filtro opcional `index_name`
4. Devuelve `RowEmbeddingsResponse` con información del índice correspondiente

#### Integración con la API Gateway

La puerta de enlace expone consultas de incrustaciones de filas a través del patrón estándar de solicitud/respuesta:

| Componente | Ubicación |
|-----------|----------|
| Despachador | `trustgraph-flow/trustgraph/gateway/dispatch/row_embeddings_query.py` |
| Registro | Agrega `"row-embeddings"` a `request_response_dispatchers` en `manager.py` |

Nombre de la interfaz de flujo: `row-embeddings`

Definición de la interfaz en el plano de flujo:
```json
{
  "interfaces": {
    "row-embeddings": {
      "request": "non-persistent://tg/request/row-embeddings:{id}",
      "response": "non-persistent://tg/response/row-embeddings:{id}"
    }
  }
}
```

#### Soporte del SDK de Python

El SDK proporciona métodos para consultas de incrustaciones de filas:

```python
# Flow-scoped query (preferred)
api = Api(url)
flow = api.flow().id("default")

# Query with text (SDK computes embeddings)
matches = flow.row_embeddings_query(
    text="Chestnut Street",
    collection="my_collection",
    schema_name="addresses",
    index_name="street_name",  # Optional filter
    limit=10
)

# Query with pre-computed vectors
matches = flow.row_embeddings_query(
    vectors=[[0.1, 0.2, ...]],
    collection="my_collection",
    schema_name="addresses"
)

# Each match contains:
for match in matches:
    print(match.index_name)   # e.g., "street_name"
    print(match.index_value)  # e.g., ["CHESTNUT ST"]
    print(match.text)         # e.g., "CHESTNUT ST"
    print(match.score)        # e.g., 0.95
```

#### Utilidad de Línea de Comandos (CLI)

Comando: `tg-invoke-row-embeddings`

```bash
# Query by text (computes embedding automatically)
tg-invoke-row-embeddings \
  --text "Chestnut Street" \
  --collection my_collection \
  --schema addresses \
  --index street_name \
  --limit 10

# Query by vector file
tg-invoke-row-embeddings \
  --vectors vectors.json \
  --collection my_collection \
  --schema addresses

# Output formats
tg-invoke-row-embeddings --text "..." --format json
tg-invoke-row-embeddings --text "..." --format table
```

#### Patrón de uso típico

La consulta de incrustaciones de filas se utiliza típicamente como parte de un flujo de búsqueda difusa a exacta:

```python
# Step 1: Fuzzy search via embeddings
matches = flow.row_embeddings_query(
    text="chestnut street",
    collection="geo",
    schema_name="streets"
)

# Step 2: Exact lookup via GraphQL for full row data
for match in matches:
    query = f'''
    query {{
        streets(where: {{ {match.index_name}: {{ eq: "{match.index_value[0]}" }} }}) {{
            street_name
            city
            zip_code
        }}
    }}
    '''
    rows = flow.rows_query(query, collection="geo")
```

Este patrón de dos pasos permite:
Encontrar "CHESTNUT ST" cuando el usuario busca "Chestnut Street"
Recuperar datos de fila completos con todos los campos
Combinar la similitud semántica con el acceso a datos estructurados

### Ingesta de Datos de Fila

Se pospone a una fase posterior. Se diseñará junto con otros cambios de ingesta.

## Impacto en la Implementación

### Análisis del Estado Actual

La implementación existente tiene dos componentes principales:

| Componente | Ubicación | Líneas | Descripción |
|-----------|----------|-------|-------------|
| Servicio de Consulta | `trustgraph-flow/trustgraph/query/objects/cassandra/service.py` | ~740 | Monolítico: generación de esquema GraphQL, análisis de filtros, consultas de Cassandra, manejo de solicitudes |
| Escritor | `trustgraph-flow/trustgraph/storage/objects/cassandra/write.py` | ~540 | Creación de tablas por esquema, índices secundarios, inserción/eliminación |

**Patrón de Consulta Actual:**
```sql
SELECT * FROM {keyspace}.o_{schema_name}
WHERE collection = 'X' AND email = 'foo@bar.com'
ALLOW FILTERING
```

**Nuevo Patrón de Consulta:**
```sql
SELECT * FROM {keyspace}.rows
WHERE collection = 'X' AND schema_name = 'customers'
  AND index_name = 'email' AND index_value = ['foo@bar.com']
```

### Cambios Clave

1. **La semántica de las consultas se simplifica**: El nuevo esquema solo admite coincidencias exactas en `index_value`. Los filtros GraphQL actuales (`gt`, `lt`, `contains`, etc.) ya sea:
   Se convierten en filtrado posterior de los datos devueltos (si es necesario)
   Se eliminan en favor de usar la API de embeddings para la coincidencia difusa

2. **El código GraphQL está fuertemente acoplado**: El código `service.py` actual incluye la generación de tipos de Strawberry, el análisis de filtros y las consultas específicas de Cassandra. Agregar otro backend de almacenamiento de filas duplicaría aproximadamente 400 líneas de código GraphQL.

### Refactorización Propuesta

La refactorización tiene dos partes:

#### 1. Separar el Código GraphQL

Extraer componentes GraphQL reutilizables en un módulo compartido:

```
trustgraph-flow/trustgraph/query/graphql/
├── __init__.py
├── types.py        # Filter types (IntFilter, StringFilter, FloatFilter)
├── schema.py       # Dynamic schema generation from RowSchema
└── filters.py      # Filter parsing utilities
```

Esto permite:
Reutilización en diferentes backends de almacenamiento de datos.
Una separación más clara de responsabilidades.
Pruebas más fáciles de la lógica de GraphQL de forma independiente.

#### 2. Implementar el Nuevo Esquema de Tabla

Refactorizar el código específico de Cassandra para utilizar la tabla unificada:

**Escritor** (`trustgraph-flow/trustgraph/storage/rows/cassandra/`):
Una única tabla `rows` en lugar de tablas por esquema.
Escribir N copias por fila (una por índice).
Registrarse en la tabla `row_partitions`.
Creación de tabla más sencilla (configuración única).

**Servicio de Consulta** (`trustgraph-flow/trustgraph/query/rows/cassandra/`):
Consultar la tabla `rows` unificada.
Utilizar el módulo GraphQL extraído para la generación de esquemas.
Manejo de filtros simplificado (solo coincidencia exacta a nivel de base de datos).

### Cambios de Nombre de Módulos

Como parte de la limpieza de nombres de "objeto" a "fila":

| Actual | Nuevo |
|---------|-----|
| `storage/objects/cassandra/` | `storage/rows/cassandra/` |
| `query/objects/cassandra/` | `query/rows/cassandra/` |
| `embeddings/object_embeddings/` | `embeddings/row_embeddings/` |

### Nuevos Módulos

| Módulo | Propósito |
|--------|---------|
| `trustgraph-flow/trustgraph/query/graphql/` | Utilidades GraphQL compartidas |
| `trustgraph-flow/trustgraph/query/row_embeddings/qdrant/` | API de consulta de incrustaciones de filas |
| `trustgraph-flow/trustgraph/embeddings/row_embeddings/` | Cálculo de incrustaciones de filas (Etapa 1) |
| `trustgraph-flow/trustgraph/storage/row_embeddings/qdrant/` | Almacenamiento de incrustaciones de filas (Etapa 2) |

## Referencias

[Especificación Técnica de Datos Estructurados](structured-data.md)
