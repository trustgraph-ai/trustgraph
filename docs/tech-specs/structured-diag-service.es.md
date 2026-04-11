# Especificación Técnica del Servicio de Diagnóstico de Datos Estructurados

## Descripción General

Esta especificación describe un nuevo servicio invocable para diagnosticar y analizar datos estructurados dentro de TrustGraph. El servicio extrae la funcionalidad de la herramienta de línea de comandos `tg-load-structured-data` existente y la expone como un servicio de solicitud/respuesta, lo que permite el acceso programático a las capacidades de detección de tipos de datos y generación de descriptores.

El servicio admite tres operaciones principales:

1. **Detección de Tipo de Datos**: Analiza una muestra de datos para determinar su formato (CSV, JSON o XML).
2. **Generación de Descriptores**: Genera un descriptor de datos estructurados de TrustGraph para una muestra de datos y tipo dados.
3. **Diagnóstico Combinado**: Realiza la detección de tipo y la generación de descriptores en secuencia.

## Objetivos

**Modularización del Análisis de Datos**: Extrae la lógica de diagnóstico de datos de la CLI en componentes de servicio reutilizables.
**Habilitar el Acceso Programático**: Proporciona acceso basado en API a las capacidades de análisis de datos.
**Admitir Múltiples Formatos de Datos**: Maneja los formatos de datos CSV, JSON y XML de manera consistente.
**Generar Descriptores Precisos**: Produce descriptores de datos estructurados que mapean con precisión los datos de origen a los esquemas de TrustGraph.
**Mantener la Compatibilidad Inversa**: Garantiza que la funcionalidad existente de la CLI continúe funcionando.
**Habilitar la Composición de Servicios**: Permite que otros servicios aprovechen las capacidades de diagnóstico de datos.
**Mejorar la Capacidad de Pruebas**: Separa la lógica de negocio de la interfaz de la CLI para una mejor prueba.
**Admitir el Análisis por Flujo**: Permite el análisis de muestras de datos sin cargar archivos completos.

## Antecedentes

Actualmente, el comando `tg-load-structured-data` proporciona una funcionalidad completa para analizar datos estructurados y generar descriptores. Sin embargo, esta funcionalidad está estrechamente acoplada a la interfaz de la CLI, lo que limita su reutilización.

Las limitaciones actuales incluyen:
Lógica de diagnóstico de datos incrustada en el código de la CLI.
Sin acceso programático a la detección de tipos y la generación de descriptores.
Difícil de integrar las capacidades de diagnóstico en otros servicios.
Capacidad limitada para componer flujos de trabajo de análisis de datos.

Esta especificación aborda estas deficiencias mediante la creación de un servicio dedicado para el diagnóstico de datos estructurados. Al exponer estas capacidades como un servicio, TrustGraph puede:
Permitir que otros servicios analicen datos de forma programática.
Admitir canalizaciones de procesamiento de datos más complejas.
Facilitar la integración con sistemas externos.
Mejorar la mantenibilidad mediante la separación de responsabilidades.

## Diseño Técnico

### Arquitectura

El servicio de diagnóstico de datos estructurados requiere los siguientes componentes técnicos:

1. **Procesador del Servicio de Diagnóstico**
   Maneja las solicitudes de diagnóstico entrantes.
   Orquesta la detección de tipos y la generación de descriptores.
   Devuelve respuestas estructuradas con los resultados del diagnóstico.

   Módulo: `trustgraph-flow/trustgraph/diagnosis/structured_data/service.py`

2. **Detector de Tipo de Datos**
   Utiliza la detección algorítmica para identificar el formato de datos (CSV, JSON, XML).
   Analiza la estructura de datos, los delimitadores y los patrones de sintaxis.
   Devuelve el formato detectado y las puntuaciones de confianza.

   Módulo: `trustgraph-flow/trustgraph/diagnosis/structured_data/type_detector.py`

3. **Generador de Descriptores**
   Utiliza el servicio de prompts para generar descriptores.
   Invoca prompts específicos del formato (diagnose-csv, diagnose-json, diagnose-xml).
   Mapea los campos de datos a los campos del esquema de TrustGraph a través de las respuestas del prompt.

   Módulo: `trustgraph-flow/trustgraph/diagnosis/structured_data/descriptor_generator.py`

### Modelos de Datos

#### StructuredDataDiagnosisRequest

Mensaje de solicitud para operaciones de diagnóstico de datos estructurados:

```python
class StructuredDataDiagnosisRequest:
    operation: str  # "detect-type", "generate-descriptor", or "diagnose"
    sample: str     # Data sample to analyze (text content)
    type: Optional[str]  # Data type (csv, json, xml) - required for generate-descriptor
    schema_name: Optional[str]  # Target schema name for descriptor generation
    options: Dict[str, Any]  # Additional options (e.g., delimiter for CSV)
```

#### RespuestaDiagnósticoDatosEstructurados

Mensaje de respuesta que contiene los resultados del diagnóstico:

```python
class StructuredDataDiagnosisResponse:
    operation: str  # The operation that was performed
    detected_type: Optional[str]  # Detected data type (for detect-type/diagnose)
    confidence: Optional[float]  # Confidence score for type detection
    descriptor: Optional[Dict]  # Generated descriptor (for generate-descriptor/diagnose)
    error: Optional[str]  # Error message if operation failed
    metadata: Dict[str, Any]  # Additional metadata (e.g., field count, sample records)
```

#### Estructura del descriptor

El descriptor generado sigue el formato de descriptor de datos estructurados existente:

```json
{
  "format": {
    "type": "csv",
    "encoding": "utf-8",
    "options": {
      "delimiter": ",",
      "has_header": true
    }
  },
  "mappings": [
    {
      "source_field": "customer_id",
      "target_field": "id",
      "transforms": [
        {"type": "trim"}
      ]
    }
  ],
  "output": {
    "schema_name": "customer",
    "options": {
      "batch_size": 1000,
      "confidence": 0.9
    }
  }
}
```

### Interfaz de Servicio

El servicio expondrá las siguientes operaciones a través del patrón de solicitud/respuesta:

1. **Operación de Detección de Tipo**
   Entrada: Muestra de datos
   Procesamiento: Analizar la estructura de datos utilizando la detección algorítmica
   Salida: Tipo detectado con una puntuación de confianza

2. **Operación de Generación de Descriptores**
   Entrada: Muestra de datos, tipo, nombre del esquema de destino
   Procesamiento:
     Llamar al servicio de solicitud con el ID de solicitud específico del formato (diagnóstico-csv, diagnóstico-json o diagnóstico-xml)
     Pasar la muestra de datos y los esquemas disponibles a la solicitud
     Recibir el descriptor generado de la respuesta de la solicitud
   Salida: Descriptor de datos estructurados

3. **Operación de Diagnóstico Combinado**
   Entrada: Muestra de datos, nombre de esquema opcional
   Procesamiento:
     Utilizar la detección algorítmica para identificar el formato primero
     Seleccionar la solicitud específica del formato basada en el tipo detectado
     Llamar al servicio de solicitud para generar el descriptor
   Salida: Tanto el tipo detectado como el descriptor

### Detalles de Implementación

El servicio seguirá las convenciones del servicio TrustGraph:

1. **Registro de Servicio**
   Registrarse como tipo de servicio `structured-diag`
   Utilizar temas estándar de solicitud/respuesta
   Implementar la clase base FlowProcessor
   Registrar PromptClientSpec para la interacción con el servicio de solicitud

2. **Gestión de la Configuración**
   Acceder a las configuraciones del esquema a través del servicio de configuración
   Almacenar en caché los esquemas para mejorar el rendimiento
   Manejar las actualizaciones de configuración de forma dinámica

3. **Integración de Solicitudes**
   Utilizar la infraestructura existente del servicio de solicitud
   Llamar al servicio de solicitud con los ID de solicitud específicos del formato:
     `diagnose-csv`: Para el análisis de datos CSV
     `diagnose-json`: Para el análisis de datos JSON
     `diagnose-xml`: Para el análisis de datos XML
   Las solicitudes están configuradas en la configuración de la solicitud, no codificadas de forma rígida en el servicio
   Pasar los esquemas y las muestras de datos como variables de la solicitud
   Analizar las respuestas de la solicitud para extraer los descriptores

4. **Manejo de Errores**
   Validar las muestras de datos de entrada
   Proporcionar mensajes de error descriptivos
   Manejar los datos incorrectos de forma elegante
   Manejar las fallas del servicio de solicitud

5. **Muestreo de Datos**
   Procesar tamaños de muestra configurables
   Manejar los registros incompletos de forma adecuada
   Mantener la coherencia del muestreo

### Integración de la API

El servicio se integrará con las API existentes de TrustGraph:

Componentes Modificados:
`tg-load-structured-data` CLI: Refactorizado para utilizar el nuevo servicio para las operaciones de diagnóstico
Flow API: Extendido para admitir solicitudes de diagnóstico de datos estructurados

Nuevos Puntos Finales del Servicio:
`/api/v1/flow/{flow}/diagnose/structured-data`: Punto final de WebSocket para solicitudes de diagnóstico
`/api/v1/diagnose/structured-data`: Punto final REST para el diagnóstico sincrónico

### Flujo de Mensajes

```
Client → Gateway → Structured Diag Service → Config Service (for schemas)
                                           ↓
                                    Type Detector (algorithmic)
                                           ↓
                                    Prompt Service (diagnose-csv/json/xml)
                                           ↓
                                 Descriptor Generator (parses prompt response)
                                           ↓
Client ← Gateway ← Structured Diag Service (response)
```

## Consideraciones de seguridad

Validación de entrada para prevenir ataques de inyección
Límites de tamaño en muestras de datos para prevenir DoS
Sanitización de descriptores generados
Control de acceso a través de la autenticación TrustGraph existente

## Consideraciones de rendimiento

Almacenar en caché las definiciones de esquema para reducir las llamadas al servicio de configuración
Limitar los tamaños de muestra para mantener un rendimiento receptivo
Utilizar procesamiento en streaming para grandes muestras de datos
Implementar mecanismos de tiempo de espera para análisis de larga duración

## Estrategia de pruebas

1. **Pruebas unitarias**
   Detección de tipo para varios formatos de datos
   Precisión de la generación de descriptores
   Escenarios de manejo de errores

2. **Pruebas de integración**
   Flujo de solicitud/respuesta del servicio
   Recuperación y almacenamiento en caché del esquema
   Integración de la CLI

3. **Pruebas de rendimiento**
   Procesamiento de grandes muestras
   Manejo de solicitudes concurrentes
   Uso de memoria bajo carga

## Plan de migración

1. **Fase 1**: Implementar el servicio con la funcionalidad principal
2. **Fase 2**: Refactorizar la CLI para que utilice el servicio (mantener la compatibilidad con versiones anteriores)
3. **Fase 3**: Agregar puntos finales de la API REST
4. **Fase 4**: Descartar la lógica integrada de la CLI (con un período de aviso)

## Cronograma

Semana 1-2: Implementar el servicio principal y la detección de tipo
Semana 3-4: Agregar la generación de descriptores y la integración
Semana 5: Pruebas y documentación
Semana 6: Refactorización de la CLI y migración

## Preguntas abiertas

¿Debería el servicio admitir formatos de datos adicionales (por ejemplo, Parquet, Avro)?
¿Cuál debería ser el tamaño máximo de la muestra para el análisis?
¿Deben almacenarse en caché los resultados del diagnóstico para solicitudes repetidas?
¿Cómo debe manejar el servicio los escenarios de esquemas múltiples?
¿Deben los ID de las indicaciones ser parámetros configurables para el servicio?

## Referencias

[Especificación del descriptor de datos estructurados](structured-data-descriptor.md)
[Documentación de carga de datos estructurados](structured-data.md)
`tg-load-structured-data` implementación: `trustgraph-cli/trustgraph/cli/load_structured_data.py`