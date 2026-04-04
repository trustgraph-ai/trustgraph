# Cambios en el Esquema de Datos Estructurados en Pulsar

## Visión general

Basado en la especificación `STRUCTURED_DATA.md`, este documento propone las adiciones y modificaciones necesarias en el esquema de Pulsar para soportar las capacidades de datos estructurados en TrustGraph.

## Cambios de Esquema Requeridos

### 1. Mejoras en el Esquema Central

#### Definición de Campo Mejorada
La clase `Field` existente en `core/primitives.py` necesita propiedades adicionales:

```python
class Field(Record):
    name = String()
    type = String()  # int, string, long, bool, float, double, timestamp
    size = Integer()
    primary = Boolean()
    description = String()
    # CAMPOS NUEVOS:
    required = Boolean()  # Indica si el campo es obligatorio
    enum_values = Array(String())  # Para campos de tipo enum
    indexed = Boolean()  # Indica si el campo debe ser indexado
```

### 2. Nuevos Esquemas de Conocimiento

#### 2.1 Envío de Datos Estructurados
Nuevo archivo: `knowledge/structured.py`

```python
from pulsar.schema import Record, String, Bytes, Map
from ..core.metadata import Metadata

class StructuredDataSubmission(Record):
    metadata = Metadata()
    format = String()  # "json", "csv", "xml"
    schema_name = String()  # Referencia al esquema en la configuración
    data = Bytes()  # Datos brutos para ingerir
    options = Map(String())  # Opciones específicas del formato
```

#### 2.2 Nuevo Servicio de Consulta Estructurada
Nuevo archivo: `services/nlp_query.py`

```python
from pulsar.schema import Record, String, Array, Map, Integer, Double
from ..core.primitives import Error

class NLPToStructuredQueryRequest(Record):
    natural_language_query = String()
    max_results = Integer()
    context_hints = Map(String())  # Contexto opcional para la generación de consulta

class NLPToStructuredQueryResponse(Record):
    error = Error()
    graphql_query = String()  # Consulta GraphQL generada
    variables = Map(String())  # Variables de GraphQL si existen
    detected_schemas = Array(String())  # Esquemas a los que apunta la consulta
    confidence = Double()
```

#### 2.2 Servicio de Consulta Estructurada
Nuevo archivo: `services/structured_query.py`

```python
from pulsar.schema import Record, String, Map, Array
from ..core.primitives import Error

class StructuredQueryRequest(Record):
    query = String()  # Consulta GraphQL
    variables = Map(String())  # Variables de GraphQL
    operation_name = String()  # Nombre opcional de operación para documentos con múltiples operaciones

class StructuredQueryResponse(Record):
    error = Error()
    data = String()  # Datos de respuesta GraphQL codificados en JSON
    errors = Array(String())  # Errores GraphQL si existen
```

#### 2.2 Salida de Extracción de Objetos
Nuevo archivo: `knowledge/object.py`

```python
from pulsar.schema import Record, String, Map, Double
from ..core.metadata import Metadata

class ExtractedObject(Record):
    metadata = Metadata()
    schema_name = String()  # Esquema al que pertenece este objeto
    values = Map(String())  # Nombre del campo -> valor
    confidence = Double()
    source_span = String()  # Rango de texto donde se encontró el objeto
```

### 4. Esquemas de Conocimiento Mejorados

#### 4.1 Mejora en la Incorporación de Objetos
Actualiza `knowledge/embeddings.py` para soportar una mejor incorporación de objetos estructurados:

```python
class StructuredObjectEmbedding(Record):
    metadata = Metadata()
    vectors = Array(Array(Double()))
    schema_name = String()
    object_id = String()  # Valor clave primaria
    field_embeddings = Map(Array(Double()))  # Incorporaciones por campo
```

## Puntos de Integración

### Integración de Flujo

Los esquemas se utilizarán en nuevos módulos de flujo:
- `trustgraph-flow/trustgraph/decoding/structured` - Utiliza StructuredDataSubmission
- `trustgraph-flow/trustgraph/query/nlp_query/cassandra` - Utiliza esquemas de consulta NLP
- `trustgraph-flow/trustgraph/query/objects/cassandra` - Utiliza esquemas de consulta estructurada
- `trustgraph-flow/trustgraph/extract/object/row/` - Consumo de Chunk, produce ExtractedObject
- `trustgraph-flow/trustgraph/storage/objects/cassandra` - Utiliza Esquema de Filas
- `trustgraph-flow/trustgraph/embeddings/object_embeddings/qdrant` - Utiliza esquemas de incorporación de objetos

## Notas de Implementación

1. **Versionado del Esquema**: Considerar añadir un campo `version` al Esquema de Fila para soporte de migración futuro.
2. **Sistema de Tipos**: El `Field.type` debería soportar todos los tipos nativos de Cassandra.
3. **Operaciones en Lotes**: La mayoría de los servicios deben soportar tanto operaciones individuales como en lote.
4. **Manejo de Errores**: Reporte de errores consistente en todos los nuevos servicios.
5. **Compatibilidad hacia atrás**: Los esquemas existentes permanecen sin cambios, excepto por las pequeñas mejoras en los Campos.

## Próximos Pasos

1. Implementar los archivos de esquema en la nueva estructura.
2. Actualizar los servicios existentes para reconocer los nuevos tipos de esquema.
3. Implementar los módulos de flujo que utilicen estos esquemas.
4. Añadir puntos finales gateway/rev-gateway para los nuevos servicios.
5. Crear pruebas unitarias para la validación del esquema.