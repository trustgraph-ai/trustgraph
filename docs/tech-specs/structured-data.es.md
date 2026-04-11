# Especificación Técnica de Datos Estructurados

## Descripción General

Esta especificación describe la integración de TrustGraph con flujos de datos estructurados, lo que permite que el sistema trabaje con datos que se pueden representar como filas en tablas u objetos en almacenes de objetos. La integración admite cuatro casos de uso principales:

1. **Extracción de Datos No Estructurados a Estructurados**: Leer fuentes de datos no estructurados, identificar y extraer estructuras de objetos y almacenarlas en un formato tabular.
2. **Ingesta de Datos Estructurados**: Cargar datos que ya están en formatos estructurados directamente en el almacén estructurado junto con los datos extraídos.
3. **Consultas en Lenguaje Natural**: Convertir preguntas en lenguaje natural en consultas estructuradas para extraer datos coincidentes del almacén.
4. **Consultas Estructuradas Directas**: Ejecutar consultas estructuradas directamente contra el almacén de datos para una recuperación de datos precisa.

## Objetivos

**Acceso Unificado a Datos**: Proporcionar una única interfaz para acceder tanto a datos estructurados como no estructurados dentro de TrustGraph.
**Integración Fluida**: Permitir una interoperabilidad fluida entre la representación de conocimiento basada en gráficos de TrustGraph y los formatos de datos estructurados tradicionales.
**Extracción Flexible**: Admitir la extracción automática de datos estructurados de diversas fuentes no estructuradas (documentos, texto, etc.).
**Versatilidad de Consulta**: Permitir a los usuarios consultar datos utilizando tanto lenguaje natural como lenguajes de consulta estructurados.
**Consistencia de Datos**: Mantener la integridad y la consistencia de los datos en diferentes representaciones de datos.
**Optimización del Rendimiento**: Garantizar el almacenamiento y la recuperación eficientes de datos estructurados a escala.
**Flexibilidad del Esquema**: Admitir enfoques de esquema-en-escritura y esquema-en-lectura para adaptarse a diversas fuentes de datos.
**Compatibilidad con Versiones Anteriores**: Preservar la funcionalidad existente de TrustGraph al agregar capacidades de datos estructurados.

## Antecedentes

Actualmente, TrustGraph destaca en el procesamiento de datos no estructurados y en la creación de gráficos de conocimiento a partir de diversas fuentes. Sin embargo, muchos casos de uso empresariales implican datos que son inherentemente estructurados: registros de clientes, registros de transacciones, bases de datos de inventario y otros conjuntos de datos tabulares. Estos conjuntos de datos estructurados a menudo deben analizarse junto con contenido no estructurado para proporcionar información integral.

Las limitaciones actuales incluyen:
No hay soporte nativo para la ingesta de formatos de datos preestructurados (CSV, matrices JSON, exportaciones de bases de datos).
Incapacidad para preservar la estructura inherente al extraer datos tabulares de documentos.
Falta de mecanismos de consulta eficientes para patrones de datos estructurados.
Falta de un puente entre las consultas tipo SQL y las consultas de gráficos de TrustGraph.

Esta especificación aborda estas deficiencias mediante la introducción de una capa de datos estructurados que complementa las capacidades existentes de TrustGraph. Al admitir datos estructurados de forma nativa, TrustGraph puede:
Servir como una plataforma unificada para el análisis tanto de datos estructurados como no estructurados.
Permitir consultas híbridas que abarquen tanto las relaciones de gráficos como los datos tabulares.
Proporcionar interfaces familiares para los usuarios acostumbrados a trabajar con datos estructurados.
Desbloquear nuevos casos de uso en la integración de datos y la inteligencia empresarial.

## Diseño Técnico

### Arquitectura

La integración de datos estructurados requiere los siguientes componentes técnicos:

1. **Servicio de Conversión de Lenguaje Natural a Consulta Estructurada**
   Convierte preguntas en lenguaje natural en consultas estructuradas.
   Admite múltiples objetivos de lenguaje de consulta (inicialmente sintaxis tipo SQL).
   Se integra con las capacidades existentes de NLP de TrustGraph.
   
   Módulo: trustgraph-flow/trustgraph/query/nlp_query/cassandra

2. **Soporte de Esquema de Configuración** ✅ **[COMPLETO]**
   Sistema de configuración extendido para almacenar esquemas de datos estructurados.
   Soporte para definir estructuras de tablas, tipos de campos y relaciones.
   Capacidades de versionado y migración de esquemas.

3. **Módulo de Extracción de Objetos** ✅ **[COMPLETO]**
   Integración mejorada del flujo de extracción de conocimiento.
   Identifica y extrae objetos estructurados de fuentes no estructuradas.
   Mantiene el origen y las puntuaciones de confianza.
   Registra un controlador de configuración (ejemplo: trustgraph-flow/trustgraph/prompt/template/service.py) para recibir datos de configuración y decodificar información del esquema.
   Recibe objetos y los decodifica en objetos ExtractedObject para su entrega en la cola de Pulsar.
   NOTA: Existe código en `trustgraph-flow/trustgraph/extract/object/row/`. Este fue un intento anterior y deberá refactorizarse por completo, ya que no se ajusta a las API actuales. Úselo si es útil, comience desde cero si no.
   Requiere una interfaz de línea de comandos: `kg-extract-objects`

   Módulo: trustgraph-flow/trustgraph/extract/kg/objects/

4. **Módulo de Escritura de Almacén Estructurado** ✅ **[COMPLETO]**
   Recibe objetos en formato ExtractedObject de las colas de Pulsar.
   Implementación inicial dirigida a Apache Cassandra como el almacén de datos estructurados.
   Maneja la creación dinámica de tablas basada en los esquemas encontrados.
   Administra el mapeo de esquemas a tablas de Cassandra y la transformación de datos.
   Proporciona operaciones de escritura por lotes y en streaming para la optimización del rendimiento.
   No hay salidas de Pulsar: este es un servicio terminal en el flujo de datos.

   **Manejo de Esquemas**:
   Supervisa los mensajes ExtractedObject entrantes en busca de referencias de esquema.
   Cuando se encuentra un nuevo esquema por primera vez, crea automáticamente la tabla correspondiente en Cassandra.
   Mantiene una caché de esquemas conocidos para evitar intentos redundantes de creación de tablas.
   Se debe considerar si se reciben definiciones de esquema directamente o si se confía en los nombres de esquema en los mensajes ExtractedObject.

   **Mapeo de Tablas de Cassandra**:
   El espacio de claves tiene el nombre derivado del campo `user` del campo de metadatos de ExtractedObject.
   La tabla tiene el nombre derivado del campo `schema_name` de ExtractedObject.
   La colección del metadato se convierte en parte de la clave de partición para garantizar:
     Distribución de datos natural en los nodos de Cassandra.
     Consultas eficientes dentro de una colección específica.
     Aislamiento lógico entre diferentes importaciones de datos/fuentes.
   Estructura de la clave primaria: `PRIMARY KEY ((collection, <schema_primary_key_fields>), <clustering_keys>)`
     La colección siempre es el primer componente de la clave de partición.
     Los campos de la clave primaria definidos en el esquema siguen como parte de la clave de partición compuesta.
     Esto requiere que las consultas especifiquen la colección, lo que garantiza un rendimiento predecible.
   Las definiciones de campos se mapean a columnas de Cassandra con conversiones de tipo:
     `string` → `text`
     `integer` → `int` o `bigint` según la sugerencia de tamaño.
     `float` → `float` o `double` según las necesidades de precisión.
     `boolean` → `boolean`
     `timestamp` → `timestamp`
     `enum` → `text` con validación a nivel de aplicación.
   Los campos indexados crean índices secundarios de Cassandra (excluyendo los campos que ya están en la clave primaria).
   Los campos obligatorios se imponen a nivel de aplicación (Cassandra no admite NOT NULL).

   **Almacenamiento de Objetos**:
   Extrae valores del mapa ExtractedObject.values.
   Realiza la conversión de tipo y la validación antes de la inserción.
   Maneja los campos opcionales faltantes de forma elegante.
   Mantiene metadatos sobre el origen del objeto (documento de origen, puntajes de confianza).
   Admite escrituras idempotentes para manejar escenarios de retransmisión de mensajes.

   **Notas de Implementación**:
   El código existente en `trustgraph-flow/trustgraph/storage/objects/cassandra/` está obsoleto y no cumple con las API actuales.
   Debe referenciar `trustgraph-flow/trustgraph/storage/triples/cassandra` como un ejemplo de un procesador de almacenamiento que funciona.
   Es necesario evaluar el código existente para identificar cualquier componente reutilizable antes de decidir refactorizar o reescribir.

   Módulo: trustgraph-flow/trustgraph/storage/objects/cassandra

5. **Servicio de Consulta Estructurada** ✅ **[COMPLETO]**
   Acepta consultas estructuradas en formatos definidos.
   Ejecuta consultas contra el almacén estructurado.
   Devuelve objetos que coinciden con los criterios de la consulta.
   Admite paginación y filtrado de resultados.

   Módulo: trustgraph-flow/trustgraph/query/objects/cassandra

6. **Integración de Herramientas de Agente**
   Nueva clase de herramienta para marcos de agentes.
   Permite que los agentes consulten almacenes de datos estructurados.
   Proporciona interfaces de consulta de lenguaje natural y estructuradas.
   Se integra con los procesos de toma de decisiones existentes de los agentes.

7. **Servicio de Ingestión de Datos Estructurados**
   Acepta datos estructurados en múltiples formatos (JSON, CSV, XML).
   Analiza y valida los datos entrantes según los esquemas definidos.
   Convierte los datos en flujos de objetos normalizados.
   Emite objetos a colas de mensajes apropiadas para su procesamiento.
   Admite cargas masivas e ingestión en streaming.

   Módulo: trustgraph-flow/trustgraph/decoding/structured

8. **Servicio de Incrustación de Objetos**
   Genera incrustaciones vectoriales para objetos estructurados.
   Permite la búsqueda semántica en datos estructurados.
   Admite la búsqueda híbrida que combina consultas estructuradas con similitud semántica.
   Se integra con almacenes de vectores existentes.

   Módulo: trustgraph-flow/trustgraph/embeddings/object_embeddings/qdrant

### Modelos de Datos

#### Mecanismo de Almacenamiento de Esquemas

Los esquemas se almacenan en el sistema de configuración de TrustGraph utilizando la siguiente estructura:

**Tipo**: `schema` (valor fijo para todos los esquemas de datos estructurados)
**Clave**: El nombre/identificador único del esquema (por ejemplo, `customer_records`, `transaction_log`)
**Valor**: Definición de esquema JSON que contiene la estructura

Ejemplo de entrada de configuración:
```
Type: schema
Key: customer_records
Value: {
  "name": "customer_records",
  "description": "Customer information table",
  "fields": [
    {
      "name": "customer_id",
      "type": "string",
      "primary_key": true
    },
    {
      "name": "name",
      "type": "string",
      "required": true
    },
    {
      "name": "email",
      "type": "string",
      "required": true
    },
    {
      "name": "registration_date",
      "type": "timestamp"
    },
    {
      "name": "status",
      "type": "string",
      "enum": ["active", "inactive", "suspended"]
    }
  ],
  "indexes": ["email", "registration_date"]
}
```

Este enfoque permite:
Definición dinámica del esquema sin cambios en el código
Actualizaciones y versiones de esquema fáciles
Integración consistente con la gestión de configuración de TrustGraph existente
Soporte para múltiples esquemas dentro de un único despliegue

### APIs

Nuevas APIs:
  Esquemas de Pulsar para los tipos anteriores
  Interfaces de Pulsar en nuevos flujos
  Se necesita un medio para especificar los tipos de esquema en los flujos para que los flujos sepan qué
    tipos de esquema cargar
  APIs añadidas a la puerta de enlace y a la puerta de enlace de revisión

APIs modificadas:
Puntos finales de extracción de conocimiento: añadir opción de salida de objeto estructurado
Puntos finales de agentes: añadir soporte para herramientas de datos estructurados

### Detalles de implementación

Siguiendo las convenciones existentes: estos son simplemente nuevos módulos de procesamiento.
Todo está en los paquetes de trustgraph-flow, excepto los elementos del esquema
en trustgraph-base.

Se necesita algo de trabajo de interfaz de usuario en el Workbench para poder demostrar / probar
esta funcionalidad.

## Consideraciones de seguridad

No hay consideraciones adicionales.

## Consideraciones de rendimiento

Algunas preguntas sobre el uso de consultas e índices de Cassandra para que las consultas
no ralenticen el sistema.

## Estrategia de pruebas

Utilizar la estrategia de pruebas existente, se crearán pruebas unitarias, de contrato e de integración.

## Plan de migración

Ninguno.

## Cronograma

No especificado.

## Preguntas abiertas

¿Se puede hacer que esto funcione con otros tipos de almacenamiento?  Nuestro objetivo es utilizar
  interfaces que hagan que los módulos que funcionan con un almacenamiento sean aplicables a
  otros almacenamientos.

## Referencias

n/a.

