# Especificación Técnica de la Consulta GraphQL

## Descripción General

Esta especificación describe la implementación de una interfaz de consulta GraphQL para el almacenamiento de datos estructurados de TrustGraph en Apache Cassandra. Basándose en las capacidades de datos estructurados descritas en la especificación structured-data.md, este documento detalla cómo se ejecutarán las consultas GraphQL contra las tablas de Cassandra que contienen objetos estructurados extraídos e importados.

<<<<<<< HEAD
El servicio de consulta GraphQL proporcionará una interfaz flexible y segura para consultar datos estructurados almacenados en Cassandra. Se adaptará dinámicamente a los cambios de esquema, admitirá consultas complejas que incluyan relaciones entre objetos y se integrará perfectamente con la arquitectura existente basada en mensajes de TrustGraph.
=======
El servicio de consulta GraphQL proporcionará una interfaz flexible y segura para consultar datos estructurados almacenados en Cassandra. Se adaptará dinámicamente a los cambios de esquema, admitirá consultas complejas, incluidas las relaciones entre objetos, y se integrará perfectamente con la arquitectura existente basada en mensajes de TrustGraph.
>>>>>>> 82edf2d (New md files from RunPod)

## Objetivos

**Soporte de Esquema Dinámico**: Adaptación automática a los cambios de esquema en la configuración sin reiniciar el servicio.
**Cumplimiento de los Estándares GraphQL**: Proporcionar una interfaz GraphQL estándar compatible con las herramientas y clientes GraphQL existentes.
<<<<<<< HEAD
**Consultas Eficientes de Cassandra**: Traducir consultas GraphQL en consultas CQL eficientes de Cassandra, respetando las claves de partición y los índices.
**Resolución de Relaciones**: Soporte para resolutores de campos GraphQL para relaciones entre diferentes tipos de objetos.
**Seguridad de Tipos**: Garantizar la ejecución de consultas y la generación de respuestas seguras, basadas en definiciones de esquema.
**Rendimiento Escalable**: Manejar consultas concurrentes de manera eficiente con un grupo de conexiones y optimización de consultas adecuados.
**Integración de Solicitud/Respuesta**: Mantener la compatibilidad con el patrón de solicitud/respuesta basado en Pulsar de TrustGraph.
**Manejo de Errores**: Proporcionar informes de errores completos para discrepancias de esquema, errores de consulta y problemas de validación de datos.

## Antecedentes

La implementación del almacenamiento de datos estructurados (trustgraph-flow/trustgraph/storage/objects/cassandra/) escribe objetos en tablas de Cassandra según las definiciones de esquema almacenadas en el sistema de configuración de TrustGraph. Estas tablas utilizan una estructura de clave de partición compuesta con claves primarias definidas por colección y esquema, lo que permite consultas eficientes dentro de las colecciones.

Limitaciones actuales que esta especificación aborda:
No hay una interfaz de consulta para los datos estructurados almacenados en Cassandra.
Incapacidad de aprovechar las poderosas capacidades de consulta de GraphQL para datos estructurados.
=======
**Consultas Eficientes de Cassandra**: Traducir las consultas GraphQL en consultas CQL eficientes de Cassandra, respetando las claves de partición y los índices.
**Resolución de Relaciones**: Soporte para los resolvedores de campos GraphQL para las relaciones entre diferentes tipos de objetos.
**Seguridad de Tipos**: Garantizar la ejecución de consultas y la generación de respuestas seguras, basadas en las definiciones del esquema.
**Rendimiento Escalable**: Manejar las consultas concurrentes de manera eficiente con un correcto agrupamiento de conexiones y optimización de consultas.
**Integración de Solicitud/Respuesta**: Mantener la compatibilidad con el patrón de solicitud/respuesta basado en Pulsar de TrustGraph.
**Manejo de Errores**: Proporcionar informes de errores completos para las discrepancias del esquema, los errores de consulta y los problemas de validación de datos.

## Antecedentes

La implementación del almacenamiento de datos estructurados (trustgraph-flow/trustgraph/storage/objects/cassandra/) escribe objetos en tablas de Cassandra según las definiciones de esquema almacenadas en el sistema de configuración de TrustGraph. Estas tablas utilizan una estructura de clave de partición compuesta con claves primarias definidas por la colección y el esquema, lo que permite consultas eficientes dentro de las colecciones.

Limitaciones actuales que esta especificación aborda:
No hay una interfaz de consulta para los datos estructurados almacenados en Cassandra.
Incapacidad de aprovechar las potentes capacidades de consulta de GraphQL para los datos estructurados.
>>>>>>> 82edf2d (New md files from RunPod)
Falta de soporte para la navegación de relaciones entre objetos relacionados.
Falta de un lenguaje de consulta estandarizado para el acceso a datos estructurados.

El servicio de consulta GraphQL cerrará estas brechas al:
Proporcionar una interfaz GraphQL estándar para consultar tablas de Cassandra.
Generar dinámicamente esquemas GraphQL a partir de la configuración de TrustGraph.
<<<<<<< HEAD
Traducir de manera eficiente las consultas GraphQL a CQL de Cassandra.
Soporte para la resolución de relaciones a través de resolutores de campos.
=======
Traducir de forma eficiente las consultas GraphQL a CQL de Cassandra.
Soporte para la resolución de relaciones a través de resolvedores de campos.
>>>>>>> 82edf2d (New md files from RunPod)

## Diseño Técnico

### Arquitectura

El servicio de consulta GraphQL se implementará como un nuevo procesador de flujo de TrustGraph, siguiendo patrones establecidos:

**Ubicación del Módulo**: `trustgraph-flow/trustgraph/query/objects/cassandra/`

**Componentes Clave**:

1. **Procesador del Servicio de Consulta GraphQL**
   Extiende la clase base FlowProcessor.
   Implementa un patrón de solicitud/respuesta similar a los servicios de consulta existentes.
   Supervisa la configuración para las actualizaciones del esquema.
   Mantiene el esquema GraphQL sincronizado con la configuración.

2. **Generador de Esquema Dinámico**
   Convierte las definiciones de esquema de TrustGraph RowSchema en tipos GraphQL.
   Crea tipos de objetos GraphQL con definiciones de campos adecuadas.
<<<<<<< HEAD
   Genera el tipo de consulta raíz con resolutores basados en colecciones.
=======
   Genera el tipo de consulta raíz con resolvedores basados en colecciones.
>>>>>>> 82edf2d (New md files from RunPod)
   Actualiza el esquema GraphQL cuando cambia la configuración.

3. **Ejecutor de Consultas**
   Analiza las consultas GraphQL entrantes utilizando la biblioteca Strawberry.
   Valida las consultas contra el esquema actual.
   Ejecuta las consultas y devuelve respuestas estructuradas.
   Maneja los errores con elegancia con mensajes de error detallados.

4. **Traductor de Consultas de Cassandra**
   Convierte las selecciones GraphQL en consultas CQL.
   Optimiza las consultas según los índices y las claves de partición disponibles.
   Maneja el filtrado, la paginación y la clasificación.
<<<<<<< HEAD
   Administra el grupo de conexiones y el ciclo de vida de la sesión.

5. **Resolutor de Relaciones**
   Implementa resolutores de campos para relaciones de objetos.
=======
   Administra el agrupamiento de conexiones y el ciclo de vida de la sesión.

5. **Resolvedor de Relaciones**
   Implementa resolvedores de campos para las relaciones de objetos.
>>>>>>> 82edf2d (New md files from RunPod)
   Realiza una carga por lotes eficiente para evitar consultas N+1.
   Almacena en caché las relaciones resueltas dentro del contexto de la solicitud.
   Admite la navegación de relaciones tanto directa como inversa.

### Monitoreo del Esquema de Configuración

<<<<<<< HEAD
El servicio se registrará con un controlador de configuración para recibir actualizaciones de esquema:
=======
El servicio se registrará con un controlador de configuración para recibir actualizaciones del esquema:
>>>>>>> 82edf2d (New md files from RunPod)

```python
self.register_config_handler(self.on_schema_config)
```

Cuando los esquemas cambian:
1. Analizar las nuevas definiciones de esquema desde la configuración.
2. Regenerar los tipos y resolutores de GraphQL.
3. Actualizar el esquema ejecutable.
4. Limpiar cualquier caché dependiente del esquema.

### Generación de Esquema GraphQL

Para cada RowSchema en la configuración, generar:

1. **Tipo de Objeto GraphQL**:
   Mapear tipos de campo (string → String, integer → Int, float → Float, boolean → Boolean).
   Marcar los campos obligatorios como no anulables en GraphQL.
   Agregar descripciones de campo desde el esquema.

2. **Campos de Consulta de Nivel Superior**:
   Consulta de colección (por ejemplo, `customers`, `transactions`).
   Argumentos de filtrado basados en campos indexados.
   Soporte de paginación (límite, desplazamiento).
   Opciones de ordenamiento para campos ordenables.

3. **Campos de Relación**:
   Identificar relaciones de clave externa desde el esquema.
   Crear resolutores de campo para objetos relacionados.
   Soporte tanto para relaciones de objeto único como para listas.

### Flujo de Ejecución de Consulta

1. **Recepción de Solicitud**:
   Recibir ObjectsQueryRequest de Pulsar.
   Extraer la cadena de consulta GraphQL y las variables.
   Identificar el contexto de usuario y colección.

2. **Validación de Consulta**:
   Analizar la consulta GraphQL utilizando Strawberry.
   Validar contra el esquema actual.
   Comprobar las selecciones de campo y los tipos de argumentos.

3. **Generación de CQL**:
   Analizar las selecciones de GraphQL.
   Construir la consulta CQL con las cláusulas WHERE adecuadas.
   Incluir la colección en la clave de partición.
   Aplicar filtros basados en los argumentos de GraphQL.

4. **Ejecución de Consulta**:
   Ejecutar la consulta CQL contra Cassandra.
   Mapear los resultados a la estructura de respuesta de GraphQL.
   Resolver cualquier campo de relación.
   Formatear la respuesta de acuerdo con la especificación de GraphQL.

5. **Entrega de Respuesta**:
   Crear una respuesta ObjectsQueryResponse con los resultados.
   Incluir cualquier error de ejecución.
   Enviar la respuesta a través de Pulsar con el ID de correlación.

### Modelos de Datos

<<<<<<< HEAD
> **Nota**: Existe un esquema existente de StructuredQueryRequest/Response en `trustgraph-base/trustgraph/schema/services/structured_query.py`. Sin embargo, le faltan campos críticos (usuario, colección) y utiliza tipos subóptimos. Los esquemas a continuación representan la evolución recomendada, que debe reemplazar los esquemas existentes o crearse como nuevos tipos de ObjectsQueryRequest/Response.
=======
> **Nota**: Existe un esquema existente de StructuredQueryRequest/Response en `trustgraph-base/trustgraph/schema/services/structured_query.py`. Sin embargo, carece de campos críticos (usuario, colección) y utiliza tipos subóptimos. Los esquemas a continuación representan la evolución recomendada, que debe reemplazar los esquemas existentes o crearse como nuevos tipos de ObjectsQueryRequest/Response.
>>>>>>> 82edf2d (New md files from RunPod)

#### Esquema de Solicitud (ObjectsQueryRequest)

```python
from pulsar.schema import Record, String, Map, Array

class ObjectsQueryRequest(Record):
    user = String()              # Cassandra keyspace (follows pattern from TriplesQueryRequest)
    collection = String()        # Data collection identifier (required for partition key)
    query = String()             # GraphQL query string
    variables = Map(String())    # GraphQL variables (consider enhancing to support all JSON types)
    operation_name = String()    # Operation to execute for multi-operation documents
```

<<<<<<< HEAD
**Justificación de los cambios desde la solicitud de consulta estructurada existente:**
=======
**Justificación de los cambios con respecto a la solicitud de consulta estructurada existente:**
>>>>>>> 82edf2d (New md files from RunPod)
Se agregaron los campos `user` y `collection` para que coincidan con el patrón de otros servicios de consulta.
Estos campos son esenciales para identificar el espacio de claves de Cassandra y la colección.
Las variables permanecen como Map(String()) por ahora, pero idealmente deberían admitir todos los tipos JSON.

#### Esquema de respuesta (ObjectsQueryResponse)

```python
from pulsar.schema import Record, String, Array
from ..core.primitives import Error

class GraphQLError(Record):
    message = String()
    path = Array(String())       # Path to the field that caused the error
    extensions = Map(String())   # Additional error metadata

class ObjectsQueryResponse(Record):
    error = Error()              # System-level error (connection, timeout, etc.)
    data = String()              # JSON-encoded GraphQL response data
    errors = Array(GraphQLError) # GraphQL field-level errors
    extensions = Map(String())   # Query metadata (execution time, etc.)
```

**Justificación de los cambios desde StructuredQueryResponse existente:**
Distingue entre errores del sistema (`error`) y errores de GraphQL (`errors`)
Utiliza objetos GraphQLError estructurados en lugar de un array de cadenas
Agrega el campo `extensions` para el cumplimiento de la especificación de GraphQL
Mantiene los datos como una cadena JSON para la compatibilidad, aunque los tipos nativos serían preferibles

### Optimización de consultas de Cassandra

El servicio optimizará las consultas de Cassandra mediante:

1. **Respetando las claves de partición:**
   Siempre incluir la colección en las consultas
   Utilizar eficientemente las claves primarias definidas en el esquema
   Evitar escaneos completos de la tabla

2. **Aprovechando los índices:**
   Utilizar índices secundarios para filtrar
   Combinar múltiples filtros siempre que sea posible
<<<<<<< HEAD
   Emitir una advertencia cuando las consultas puedan ser ineficientes
=======
   Advertir cuando las consultas puedan ser ineficientes
>>>>>>> 82edf2d (New md files from RunPod)

3. **Carga por lotes:**
   Recopilar consultas de relaciones
   Ejecutar en lotes para reducir los viajes de ida y vuelta
   Almacenar en caché los resultados dentro del contexto de la solicitud

4. **Administración de conexiones:**
   Mantener sesiones de Cassandra persistentes
   Utilizar un grupo de conexiones
   Manejar la reconexión en caso de fallos

### Ejemplos de consultas GraphQL

#### Consulta simple de colección
```graphql
{
  customers(status: "active") {
    customer_id
    name
    email
    registration_date
  }
}
```

#### Consulta con Relaciones
```graphql
{
  orders(order_date_gt: "2024-01-01") {
    order_id
    total_amount
    customer {
      name
      email
    }
    items {
      product_name
      quantity
      price
    }
  }
}
```

#### Consulta paginada
```graphql
{
  products(limit: 20, offset: 40) {
    product_id
    name
    price
    category
  }
}
```

### Dependencias de Implementación

**Strawberry GraphQL**: Para la definición del esquema GraphQL y la ejecución de consultas.
**Cassandra Driver**: Para la conectividad con la base de datos (ya utilizado en el módulo de almacenamiento).
**TrustGraph Base**: Para FlowProcessor y definiciones de esquema.
**Sistema de Configuración**: Para la supervisión y las actualizaciones del esquema.

### Interfaz de Línea de Comandos

El servicio proporcionará un comando de la CLI: `kg-query-objects-graphql-cassandra`

Argumentos:
`--cassandra-host`: Punto de contacto del clúster de Cassandra.
`--cassandra-username`: Nombre de usuario de autenticación.
`--cassandra-password`: Contraseña de autenticación.
`--config-type`: Tipo de configuración para los esquemas (por defecto: "schema").
Argumentos estándar de FlowProcessor (configuración de Pulsar, etc.).

## Integración de la API

### Temas de Pulsar

**Tema de entrada**: `objects-graphql-query-request`
Esquema: ObjectsQueryRequest
<<<<<<< HEAD
Recibe consultas GraphQL de los servicios de puerta de enlace.
=======
Recibe consultas GraphQL de los servicios de la puerta de enlace.
>>>>>>> 82edf2d (New md files from RunPod)

**Tema de salida**: `objects-graphql-query-response`
Esquema: ObjectsQueryResponse
Devuelve los resultados de la consulta y los errores.

### Integración de la puerta de enlace

La puerta de enlace y la puerta de enlace inversa necesitarán puntos finales para:
1. Aceptar consultas GraphQL de los clientes.
2. Enviar a través de Pulsar al servicio de consulta.
<<<<<<< HEAD
3. Devolver respuestas a los clientes.
4. Compatibilidad con consultas de introspección de GraphQL.
=======
3. Devolver las respuestas a los clientes.
4. Compatibilidad con las consultas de introspección de GraphQL.
>>>>>>> 82edf2d (New md files from RunPod)

### Integración de la herramienta de agente

Una nueva clase de herramienta de agente permitirá:
Generación de consultas GraphQL a partir de lenguaje natural.
Ejecución directa de consultas GraphQL.
Interpretación y formato de resultados.
<<<<<<< HEAD
Integración con flujos de decisión de agentes.
=======
Integración con los flujos de decisión del agente.
>>>>>>> 82edf2d (New md files from RunPod)

## Consideraciones de seguridad

**Limitación de la profundidad de la consulta**: Prevenir consultas profundamente anidadas que puedan causar problemas de rendimiento.
**Análisis de la complejidad de la consulta**: Limitar la complejidad de la consulta para evitar el agotamiento de recursos.
**Permisos a nivel de campo**: Futuro soporte para el control de acceso a nivel de campo basado en los roles de usuario.
**Saneamiento de entrada**: Validar y limpiar todas las entradas de la consulta para prevenir ataques de inyección.
**Limitación de velocidad**: Implementar la limitación de velocidad de las consultas por usuario/colección.

## Consideraciones de rendimiento

**Planificación de consultas**: Analizar las consultas antes de la ejecución para optimizar la generación de CQL.
<<<<<<< HEAD
**Caché de resultados**: Considerar el almacenamiento en caché de datos accedidos con frecuencia a nivel del resolutor de campos.
**Creación de grupos de conexiones**: Mantener grupos de conexiones eficientes a Cassandra.
**Operaciones por lotes**: Combinar múltiples consultas cuando sea posible para reducir la latencia.
=======
**Caché de resultados**: Considerar el almacenamiento en caché de los datos accedidos con frecuencia a nivel del resolutor de campos.
**Creación de grupos de conexiones**: Mantener grupos de conexiones eficientes a Cassandra.
**Operaciones por lotes**: Combinar múltiples consultas siempre que sea posible para reducir la latencia.
>>>>>>> 82edf2d (New md files from RunPod)
**Supervisión**: Supervisar las métricas de rendimiento de las consultas para la optimización.

## Estrategia de pruebas

### Pruebas Unitarias
Generación de esquemas a partir de definiciones de RowSchema
Análisis y validación de consultas GraphQL
Lógica de generación de consultas CQL
Implementaciones de resolutores de campos

### Pruebas de Contrato
Cumplimiento del contrato de mensajes Pulsar
Validez del esquema GraphQL
Verificación del formato de respuesta
Validación de la estructura de errores

### Pruebas de Integración
Ejecución de consultas de extremo a extremo contra una instancia de prueba de Cassandra
Manejo de actualizaciones de esquema
Resolución de relaciones
Paginación y filtrado
Escenarios de error

### Pruebas de Rendimiento
Rendimiento de consultas bajo carga
Tiempo de respuesta para diversas complejidades de consulta
Uso de memoria con conjuntos de resultados grandes
Eficiencia del pool de conexiones

## Plan de Migración

No se requiere migración, ya que se trata de una nueva funcionalidad. El servicio:
1. Leerá los esquemas existentes desde la configuración
2. Se conectará a las tablas de Cassandra existentes creadas por el módulo de almacenamiento
3. Comenzará a aceptar consultas inmediatamente después de la implementación

## Cronograma

Semana 1-2: Implementación del servicio principal y generación de esquemas
Semana 3: Ejecución de consultas y traducción de CQL
Semana 4: Resolución de relaciones y optimización
Semana 5: Pruebas y ajuste de rendimiento
Semana 6: Integración con la puerta de enlace y documentación

## Preguntas Abiertas

1. **Evolución del Esquema**: ¿Cómo debe el servicio manejar las consultas durante las transiciones de esquema?
   Opción: Encolar consultas durante las actualizaciones de esquema
   Opción: Compatibilidad con múltiples versiones de esquema simultáneamente

2. **Estrategia de Caché**: ¿Deben almacenarse en caché los resultados de las consultas?
   Considerar: Expiración basada en el tiempo
   Considerar: Invalidación basada en eventos

3. **Soporte de Federación**: ¿Debe el servicio admitir la federación de GraphQL para combinarlo con otras fuentes de datos?
   Permitiría consultas unificadas a través de datos estructurados y de grafos

4. **Soporte de Suscripciones**: ¿Debe el servicio admitir suscripciones de GraphQL para actualizaciones en tiempo real?
   Requeriría soporte de WebSocket en la puerta de enlace

5. **Escalares Personalizados**: ¿Se deben admitir tipos de datos escalares personalizados para tipos de datos específicos del dominio?
   Ejemplos: DateTime, UUID, campos JSON

## Referencias

Especificación Técnica de Datos Estructurados: `docs/tech-specs/structured-data.md`
Documentación de Strawberry GraphQL: https://strawberry.rocks/
Especificación de GraphQL: https://spec.graphql.org/
<<<<<<< HEAD
Referencia de CQL de Apache Cassandra: https://cassandra.apache.org/doc/stable/cassandra/cql/
=======
Referencia CQL de Apache Cassandra: https://cassandra.apache.org/doc/stable/cassandra/cql/
>>>>>>> 82edf2d (New md files from RunPod)
Documentación del Procesador de Flujo de TrustGraph: Documentación interna