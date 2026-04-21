---
layout: default
title: "Infraestructura Pub/Sub"
parent: "Spanish (Beta)"
---

# Infraestructura Pub/Sub

> **Beta Translation:** This document was translated via Machine Learning and as such may not be 100% accurate. All non-English languages are currently classified as Beta.

## Resumen

Este documento cataloga todas las conexiones entre el código base de TrustGraph y la infraestructura pub/sub. Actualmente, el sistema está codificado para usar Apache Pulsar. Este análisis identifica todos los puntos de integración para informar futuras refactorizaciones hacia una abstracción pub/sub configurable.

## Estado actual: Puntos de integración de Pulsar

### 1. Uso directo del cliente de Pulsar

**Ubicación:** `trustgraph-flow/trustgraph/gateway/service.py`

La puerta de enlace de la API importa y crea una instancia directamente del cliente de Pulsar:

**Línea 20:** `import pulsar`
**Líneas 54-61:** Creación directa de `pulsar.Client()` con `pulsar.AuthenticationToken()` opcional
**Líneas 33-35:** Configuración predeterminada del host de Pulsar desde variables de entorno
**Líneas 178-192:** Argumentos de la línea de comandos para `--pulsar-host`, `--pulsar-api-key` y `--pulsar-listener`
**Líneas 78, 124:** Pasa `pulsar_client` a `ConfigReceiver` y `DispatcherManager`

Esta es la única ubicación que crea directamente un cliente de Pulsar fuera de la capa de abstracción.

### 2. Marco base del procesador

**Ubicación:** `trustgraph-base/trustgraph/base/async_processor.py`

La clase base para todos los procesadores proporciona conectividad de Pulsar:

**Línea 9:** `import _pulsar` (para el manejo de excepciones)
**Línea 18:** `from . pubsub import PulsarClient`
**Línea 38:** Crea `pulsar_client_object = PulsarClient(**params)`
**Líneas 104-108:** Propiedades que exponen `pulsar_host` y `pulsar_client`
**Línea 250:** El método estático `add_args()` llama a `PulsarClient.add_args(parser)` para los argumentos de la línea de comandos
**Líneas 223-225:** Manejo de excepciones para `_pulsar.Interrupted`

Todos los procesadores heredan de `AsyncProcessor`, lo que convierte a este en el punto de integración central.

### 3. Abstracción del consumidor

**Ubicación:** `trustgraph-base/trustgraph/base/consumer.py`

Consume mensajes de colas e invoca funciones de controlador:

**Importaciones de Pulsar:**
**Línea 12:** `from pulsar.schema import JsonSchema`
**Línea 13:** `import pulsar`
**Línea 14:** `import _pulsar`

**Uso específico de Pulsar:**
**Líneas 100, 102:** `pulsar.InitialPosition.Earliest` / `pulsar.InitialPosition.Latest`
**Línea 108:** Envoltorio `JsonSchema(self.schema)`
**Línea 110:** `pulsar.ConsumerType.Shared`
**Líneas 104-111:** `self.client.subscribe()` con parámetros específicos de Pulsar
**Líneas 143, 150, 65:** Métodos `consumer.unsubscribe()` y `consumer.close()`
**Línea 162:** Excepción `_pulsar.Timeout`
**Líneas 182, 205, 232:** `consumer.acknowledge()` / `consumer.negative_acknowledge()`

**Archivo de especificación:** `trustgraph-base/trustgraph/base/consumer_spec.py`
**Línea 22:** Hace referencia a `processor.pulsar_client`

### 4. Abstracción del productor

**Ubicación:** `trustgraph-base/trustgraph/base/producer.py`

Envía mensajes a colas:

**Importaciones de Pulsar:**
**Línea 2:** `from pulsar.schema import JsonSchema`

**Uso específico de Pulsar:**
**Línea 49:** Envoltorio `JsonSchema(self.schema)`
**Líneas 47-51:** `self.client.create_producer()` con parámetros específicos de Pulsar (tema, esquema, habilitación de fragmentación)
**Líneas 31, 76:** Método `producer.close()`
**Líneas 64-65:** `producer.send()` con mensaje y propiedades

**Archivo de especificación:** `trustgraph-base/trustgraph/base/producer_spec.py`
**Línea 18:** Hace referencia a `processor.pulsar_client`

### 5. Abstracción del publicador

**Ubicación:** `trustgraph-base/trustgraph/base/publisher.py`

Publicación de mensajes asíncrona con almacenamiento en búfer de cola:

**Importaciones de Pulsar:**
**Línea 2:** `from pulsar.schema import JsonSchema`
**Línea 6:** `import pulsar`

**Uso específico de Pulsar:**
**Línea 52:** Envoltorio `JsonSchema(self.schema)`
**Líneas 50-54:** `self.client.create_producer()` con parámetros específicos de Pulsar
**Líneas 101, 103:** `producer.send()` con mensaje y propiedades opcionales
**Líneas 106-107:** Métodos `producer.flush()` y `producer.close()`

### 6. Abstracción del suscriptor

**Ubicación:** `trustgraph-base/trustgraph/base/subscriber.py`

Proporciona la distribución de mensajes a múltiples destinatarios desde colas:

**Importaciones de Pulsar:**
**Línea 6:** `from pulsar.schema import JsonSchema`
**Línea 8:** `import _pulsar`

**Uso específico de Pulsar:**
**Línea 55:** `JsonSchema(self.schema)` wrapper
**Línea 57:** `self.client.subscribe(**subscribe_args)`
**Líneas 101, 136, 160, 167-172:** Excepciones de Pulsar: `_pulsar.Timeout`, `_pulsar.InvalidConfiguration`, `_pulsar.AlreadyClosed`
**Líneas 159, 166, 170:** Métodos de consumidor: `negative_acknowledge()`, `unsubscribe()`, `close()`
**Líneas 247, 251:** Reconocimiento de mensajes: `acknowledge()`, `negative_acknowledge()`

**Archivo de especificaciones:** `trustgraph-base/trustgraph/base/subscriber_spec.py`
**Línea 19:** Referencias a `processor.pulsar_client`

### 7. Sistema de esquemas (Heart of Darkness)

**Ubicación:** `trustgraph-base/trustgraph/schema/`

Cada esquema de mensaje en el sistema se define utilizando el marco de esquemas de Pulsar.

**Primitivos principales:** `schema/core/primitives.py`
**Línea 2:** `from pulsar.schema import Record, String, Boolean, Array, Integer`
Todos los esquemas heredan de la clase base de Pulsar `Record`
Todos los tipos de campo son tipos de Pulsar: `String()`, `Integer()`, `Boolean()`, `Array()`, `Map()`, `Double()`

**Esquemas de ejemplo:**
`schema/services/llm.py` (Línea 2): `from pulsar.schema import Record, String, Array, Double, Integer, Boolean`
`schema/services/config.py` (Línea 2): `from pulsar.schema import Record, Bytes, String, Boolean, Array, Map, Integer`

**Nomenclatura de temas:** `schema/core/topic.py`
**Líneas 2-3:** Formato del tema: `{kind}://{tenant}/{namespace}/{topic}`
Esta estructura de URI es específica de Pulsar (por ejemplo, `persistent://tg/flow/config`)

**Impacto:**
Todas las definiciones de mensajes de solicitud/respuesta en todo el código base utilizan esquemas de Pulsar
Esto incluye servicios para: config, flow, llm, prompt, query, storage, agent, collection, diagnosis, library, lookup, nlp_query, objects_query, retrieval, structured_query
Las definiciones de esquemas se importan y utilizan ampliamente en todos los procesadores y servicios

## Resumen

### Dependencias de Pulsar por Categoría

1. **Instanciación del cliente:**
   Directo: `gateway/service.py`
   Abstracto: `async_processor.py` → `pubsub.py` (PulsarClient)

2. **Transporte de mensajes:**
   Consumidor: `consumer.py`, `consumer_spec.py`
   Productor: `producer.py`, `producer_spec.py`
   Publicador: `publisher.py`
   Suscriptor: `subscriber.py`, `subscriber_spec.py`

3. **Sistema de esquemas:**
   Tipos base: `schema/core/primitives.py`
   Todos los esquemas de servicio: `schema/services/*.py`
   Nomenclatura de temas: `schema/core/topic.py`

4. **Conceptos específicos de Pulsar requeridos:**
   Mensajería basada en temas
   Sistema de esquemas (Registro, tipos de campo)
   Suscripciones compartidas
   Reconocimiento de mensajes (positivo/negativo)
   Posicionamiento del consumidor (más temprano/más reciente)
   Propiedades del mensaje
   Posiciones iniciales y tipos de consumidor
   Soporte de fragmentación
   Temas persistentes frente a no persistentes

### Desafíos de refactorización

La buena noticia: la capa de abstracción (Consumidor, Productor, Publicador, Suscriptor) proporciona una encapsulación limpia de la mayoría de las interacciones de Pulsar.

Los desafíos:
1. **Ubicuidad del sistema de esquemas:** Cada definición de mensaje utiliza `pulsar.schema.Record` y los tipos de campo de Pulsar
2. **Enums específicos de Pulsar:** `InitialPosition`, `ConsumerType`
3. **Excepciones de Pulsar:** `_pulsar.Timeout`, `_pulsar.Interrupted`, `_pulsar.InvalidConfiguration`, `_pulsar.AlreadyClosed`
4. **Fichas de método:** `acknowledge()`, `negative_acknowledge()`, `subscribe()`, `create_producer()`, etc.
5. **Formato de URI de tema:** Estructura de Pulsar `kind://tenant/namespace/topic`

### Próximos pasos

Para hacer que la infraestructura de pub/sub sea configurable, necesitamos:

1. Crear una interfaz de abstracción para el sistema de cliente/esquemas
2. Abstractar enums y excepciones específicas de Pulsar
3. Crear envoltorios de esquema o definiciones de esquema alternativas
4. Implementar la interfaz tanto para Pulsar como para sistemas alternativos (Kafka, RabbitMQ, Redis Streams, etc.)
5. Actualizar `pubsub.py` para que sea configurable y admita varios backends
6. Proporcionar una ruta de migración para implementaciones existentes

## Borrador de enfoque 1: Patrón de adaptador con capa de traducción de esquemas

### Idea clave
El **sistema de esquemas** es el punto de integración más profundo; todo lo demás se deriva de él. Necesitamos resolver esto primero, o tendremos que reescribir todo el código base.

### Estrategia: Interrupción mínima con adaptadores

**1. Mantener los esquemas de Pulsar como la representación interna**
No reescribir todas las definiciones de esquemas.
Los esquemas permanecen `pulsar.schema.Record` internamente.
Utilizar adaptadores para traducir en la frontera entre nuestro código y el backend de publicación/suscripción.

**2. Crear una capa de abstracción de publicación/suscripción:**

```
┌─────────────────────────────────────┐
│   Existing Code (unchanged)         │
│   - Uses Pulsar schemas internally  │
│   - Consumer/Producer/Publisher     │
└──────────────┬──────────────────────┘
               │
┌──────────────┴──────────────────────┐
│   PubSubFactory (configurable)      │
│   - Creates backend-specific client │
└──────────────┬──────────────────────┘
               │
        ┌──────┴──────┐
        │             │
┌───────▼─────┐  ┌────▼─────────┐
│ PulsarAdapter│  │ KafkaAdapter │  etc...
│ (passthrough)│  │ (translates) │
└──────────────┘  └──────────────┘
```

**3. Defina interfaces abstractas:**
`PubSubClient` - conexión del cliente
`PubSubProducer` - envío de mensajes
`PubSubConsumer` - recepción de mensajes
`SchemaAdapter` - traducción de esquemas de Pulsar a/desde JSON o formatos específicos del backend

**4. Detalles de implementación:**

Para el **adaptador de Pulsar**: Casi una transmisión directa, traducción mínima.

Para **otros backends** (Kafka, RabbitMQ, etc.):
Serializar objetos de registro de Pulsar a JSON/bytes.
Mapear conceptos como:
  `InitialPosition.Earliest/Latest` → auto.offset.reset de Kafka
  `acknowledge()` → confirmación de Kafka
  `negative_acknowledge()` → patrón de re-cola o cola de mensajes no entregados (DLQ).
  URIs de temas → nombres de temas específicos del backend.

### Análisis

**Ventajas:**
✅ Cambios mínimos en el código de los servicios existentes.
✅ Los esquemas permanecen sin cambios (sin reescritura masiva).
✅ Ruta de migración gradual.
✅ Los usuarios de Pulsar no notan ninguna diferencia.
✅ Se agregan nuevos backends a través de adaptadores.

**Desventajas:**
⚠️ Aún mantiene la dependencia de Pulsar (para las definiciones de esquemas).
⚠️ Algunos problemas de compatibilidad al traducir conceptos.

### Consideración alternativa

Crear un sistema de esquemas **TrustGraph** que sea independiente de pub/sub (usando dataclasses o Pydantic), y luego generar esquemas de Pulsar/Kafka/etc a partir de él. Esto requiere reescribir cada archivo de esquema y podría provocar cambios importantes.

### Recomendación para la versión preliminar 1

Comience con el **enfoque de adaptador** porque:
1. Es práctico: funciona con el código existente.
2. Demuestra el concepto con un riesgo mínimo.
3. Puede evolucionar hacia un sistema de esquemas nativo más adelante, si es necesario.
4. Impulsado por la configuración: una variable de entorno cambia entre backends.

## Enfoque de la versión preliminar 2: Sistema de esquemas independiente del backend con dataclasses

### Concepto central

Utilice **dataclasses** de Python como el formato de definición de esquema neutral. Cada backend de pub/sub proporciona su propia serialización/deserialización para dataclasses, eliminando la necesidad de que los esquemas de Pulsar permanezcan en el código base.

### Polimorfismo de esquema a nivel de fábrica

En lugar de traducir esquemas de Pulsar, **cada backend proporciona su propia gestión de esquemas** que funciona con dataclasses de Python estándar.

### Flujo del publicador

```python
# 1. Get the configured backend from factory
pubsub = get_pubsub()  # Returns PulsarBackend, MQTTBackend, etc.

# 2. Get schema class from the backend
# (Can be imported directly - backend-agnostic)
from trustgraph.schema.services.llm import TextCompletionRequest

# 3. Create a producer/publisher for a specific topic
producer = pubsub.create_producer(
    topic="text-completion-requests",
    schema=TextCompletionRequest  # Tells backend what schema to use
)

# 4. Create message instances (same API regardless of backend)
request = TextCompletionRequest(
    system="You are helpful",
    prompt="Hello world",
    streaming=False
)

# 5. Send the message
producer.send(request)  # Backend serializes appropriately
```

### Flujo del consumidor

```python
# 1. Get the configured backend
pubsub = get_pubsub()

# 2. Create a consumer
consumer = pubsub.subscribe(
    topic="text-completion-requests",
    schema=TextCompletionRequest  # Tells backend how to deserialize
)

# 3. Receive and deserialize
msg = consumer.receive()
request = msg.value()  # Returns TextCompletionRequest dataclass instance

# 4. Use the data (type-safe access)
print(request.system)   # "You are helpful"
print(request.prompt)   # "Hello world"
print(request.streaming)  # False
```

### ¿Qué sucede detrás de escena?

**Para el backend de Pulsar:**
`create_producer()` → crea un productor de Pulsar con un esquema JSON o un registro generado dinámicamente.
`send(request)` → serializa la clase de datos a formato JSON/Pulsar y lo envía a Pulsar.
`receive()` → recibe un mensaje de Pulsar, lo deserializa de nuevo a la clase de datos.

**Para el backend de MQTT:**
`create_producer()` → se conecta a un broker de MQTT, no es necesario registrar ningún esquema.
`send(request)` → convierte la clase de datos a JSON y lo publica en un tema de MQTT.
`receive()` → se suscribe a un tema de MQTT y deserializa el JSON a la clase de datos.

**Para el backend de Kafka:**
`create_producer()` → crea un productor de Kafka y registra el esquema Avro si es necesario.
`send(request)` → serializa la clase de datos a formato Avro y lo envía a Kafka.
`receive()` → recibe un mensaje de Kafka y lo deserializa de Avro de nuevo a la clase de datos.

### Puntos Clave del Diseño

1. **Creación del objeto de esquema**: La instancia de la clase de datos (`TextCompletionRequest(...)`) es idéntica independientemente del backend.
2. **El backend se encarga de la codificación**: Cada backend sabe cómo serializar su clase de datos al formato de cable.
3. **Definición del esquema en la creación**: Al crear el productor/consumidor, se especifica el tipo de esquema.
4. **Se mantiene la seguridad de tipos**: Se obtiene un objeto `TextCompletionRequest` adecuado, no un diccionario.
5. **Sin filtración del backend**: El código de la aplicación nunca importa bibliotecas específicas del backend.

### Ejemplo de Transformación

**Actual (específico de Pulsar):**
```python
# schema/services/llm.py
from pulsar.schema import Record, String, Boolean, Integer

class TextCompletionRequest(Record):
    system = String()
    prompt = String()
    streaming = Boolean()
```

**Nuevo (Independiente del backend):**
```python
# schema/services/llm.py
from dataclasses import dataclass

@dataclass
class TextCompletionRequest:
    system: str
    prompt: str
    streaming: bool = False
```

### Integración con el Backend

Cada backend se encarga de la serialización/deserialización de dataclasses:

**Backend de Pulsar:**
Genera clases `pulsar.schema.Record` dinámicamente a partir de dataclasses
O serializa dataclasses a JSON y utiliza el esquema JSON de Pulsar
Mantiene la compatibilidad con implementaciones de Pulsar existentes

**Backend de MQTT/Redis:**
Serialización directa de instancias de dataclass a JSON
Utiliza `dataclasses.asdict()` / `from_dict()`
Ligero, no se necesita un registro de esquemas

**Backend de Kafka:**
Genera esquemas Avro a partir de definiciones de dataclass
Utiliza el registro de esquemas de Confluent
Serialización con seguridad de tipos y soporte para la evolución del esquema

### Arquitectura

```
┌─────────────────────────────────────┐
│   Application Code                  │
│   - Uses dataclass schemas          │
│   - Backend-agnostic                │
└──────────────┬──────────────────────┘
               │
┌──────────────┴──────────────────────┐
│   PubSubFactory (configurable)      │
│   - get_pubsub() returns backend    │
└──────────────┬──────────────────────┘
               │
        ┌──────┴──────┐
        │             │
┌───────▼─────────┐  ┌────▼──────────────┐
│ PulsarBackend   │  │ MQTTBackend       │
│ - JSON schema   │  │ - JSON serialize  │
│ - or dynamic    │  │ - Simple queues   │
│   Record gen    │  │                   │
└─────────────────┘  └───────────────────┘
```

### Detalles de implementación

**1. Definiciones de esquema:** Clases de datos simples con sugerencias de tipo
   `str`, `int`, `bool`, `float` para tipos primitivos
   `list[T]` para arreglos
   `dict[str, T]` para mapas
   Clases de datos anidadas para tipos complejos

**2. Cada backend proporciona:**
   Serializador: `dataclass → bytes/wire format`
   Deserializador: `bytes/wire format → dataclass`
   Registro de esquema (si es necesario, como Pulsar/Kafka)

**3. Abstracción de consumidor/productor:**
   Ya existe (consumer.py, producer.py)
   Actualizar para usar la serialización del backend
   Eliminar importaciones directas de Pulsar

**4. Mapeos de tipo:**
   Pulsar `String()` → Python `str`
   Pulsar `Integer()` → Python `int`
   Pulsar `Boolean()` → Python `bool`
   Pulsar `Array(T)` → Python `list[T]`
   Pulsar `Map(K, V)` → Python `dict[K, V]`
   Pulsar `Double()` → Python `float`
   Pulsar `Bytes()` → Python `bytes`

### Ruta de migración

1. **Crear versiones de clases de datos** de todos los esquemas en `trustgraph/schema/`
2. **Actualizar clases de backend** (Consumidor, Productor, Publicador, Suscriptor) para usar la serialización proporcionada por el backend
3. **Implementar PulsarBackend** con esquema JSON o generación dinámica de registros
4. **Probar con Pulsar** para garantizar la compatibilidad hacia atrás con las implementaciones existentes
5. **Agregar nuevos backends** (MQTT, Kafka, Redis, etc.) según sea necesario
6. **Eliminar importaciones de Pulsar** de los archivos de esquema

### Beneficios

✅ **Sin dependencia de pub/sub** en las definiciones de esquema
✅ **Python estándar** - fácil de entender, tipificar, documentar
✅ **Herramientas modernas** - funciona con mypy, autocompletado de IDE, analizadores
✅ **Optimizada para el backend** - cada backend utiliza la serialización nativa
✅ **Sin sobrecarga de traducción** - serialización directa, sin adaptadores
✅ **Seguridad de tipos** - objetos reales con tipos adecuados
✅ **Validación fácil** - se puede usar Pydantic si es necesario

### Desafíos y soluciones

**Desafío:** El `Record` de Pulsar tiene validación de campo en tiempo de ejecución
**Solución:** Usar clases de datos de Pydantic para la validación si es necesario, o características de clase de datos de Python 3.10+ con `__post_init__`

**Desafío:** Algunas características específicas de Pulsar (como el tipo `Bytes`)
**Solución:** Mapear al tipo `bytes` en la clase de datos, el backend se encarga de la codificación apropiadamente

**Desafío:** Nombres de temas (`persistent://tenant/namespace/topic`)
**Solución:** Abstracto los nombres de los temas en las definiciones de esquema, el backend convierte al formato adecuado

**Desafío:** Evolución y versionado del esquema
**Solución:** Cada backend maneja esto de acuerdo con sus capacidades (versiones de esquema de Pulsar, registro de esquema de Kafka, etc.)

**Desafío:** Tipos complejos anidados
**Solución:** Usar clases de datos anidadas, los backends serializan/deserializan recursivamente

### Decisiones de diseño

1. **¿Clases de datos simples o Pydantic?**
   ✅ **Decisión: Usar clases de datos de Python simples**
   Más simple, sin dependencias adicionales
   La validación no es necesaria en la práctica
   Más fácil de entender y mantener

2. **Evolución del esquema:**
   ✅ **Decisión: No se necesita un mecanismo de versionado**
   Los esquemas son estables y duraderos
   Las actualizaciones normalmente agregan nuevos campos (compatible con versiones anteriores)
   Los backends manejan la evolución del esquema según sus capacidades

3. **Compatibilidad hacia atrás:**
   ✅ **Decisión: Cambio de versión importante, no se requiere compatibilidad hacia atrás**
   Será un cambio importante con instrucciones de migración
   La ruptura limpia permite un mejor diseño
   Se proporcionará una guía de migración para las implementaciones existentes

4. **Tipos anidados y estructuras complejas:**
   ✅ **Decisión: Usar clases de datos anidadas de forma natural**
   Las clases de datos de Python manejan el anidamiento perfectamente
   `list[T]` para arreglos, `dict[K, V]` para mapas
   Los backends serializan/deserializan recursivamente
   Ejemplo:
     ```python
     @dataclass
     class Value:
         value: str
         is_uri: bool

     @dataclass
     class Triple:
         s: Value              # Nested dataclass
         p: Value
         o: Value

     @dataclass
     class GraphQuery:
         triples: list[Triple]  # Array of nested dataclasses
         metadata: dict[str, str]
     ```

5. **Valores predeterminados y campos opcionales:**
   ✅ **Decisión: Combinación de campos obligatorios, valores predeterminados y campos opcionales**
   Campos obligatorios: Sin valor predeterminado
   Campos con valores predeterminados: Siempre presentes, tienen un valor predeterminado razonable
   Campos verdaderamente opcionales: `T | None = None`, omitidos de la serialización cuando `None`
   Ejemplo:
     ```python
     @dataclass
     class TextCompletionRequest:
         system: str              # Required, no default
         prompt: str              # Required, no default
         streaming: bool = False  # Optional with default value
         metadata: dict | None = None  # Truly optional, can be absent
     ```

   **Semántica de serialización importante:**

   Cuando `metadata = None`:
   ```json
   {
       "system": "...",
       "prompt": "...",
       "streaming": false
       // metadata field NOT PRESENT
   }
   ```

   Cuando `metadata = {}` (explícitamente vacío):
   ```json
   {
       "system": "...",
       "prompt": "...",
       "streaming": false,
       "metadata": {}  // Field PRESENT but empty
   }
   ```

   **Diferencia clave:**
   `None` → campo ausente en JSON (no se serializa)
   Valor vacío (`{}`, `[]`, `""`) → campo presente con valor vacío
   Esto es importante semánticamente: "no proporcionado" vs "explícitamente vacío"
   Los sistemas de serialización deben omitir los campos `None`, no codificarlos como `null`

## Esquema de Implementación Borrador 3: Detalles de Implementación

### Formato Genérico para Nombres de Colas

Reemplace los nombres de colas específicos del sistema de respaldo con un formato genérico que los sistemas de respaldo puedan mapear adecuadamente.

**Formato:** `{qos}/{tenant}/{namespace}/{queue-name}`

Donde:
`qos`: Nivel de Calidad de Servicio
  `q0` = mejor esfuerzo (enviar y olvidar, sin confirmación)
  `q1` = al menos una vez (requiere confirmación)
  `q2` = exactamente una vez (confirmación de dos fases)
`tenant`: Agrupación lógica para multi-inquilino
`namespace`: Sub-agrupación dentro del inquilino
`queue-name`: Nombre real de la cola/tema

**Ejemplos:**
```
q1/tg/flow/text-completion-requests
q2/tg/config/config-push
q0/tg/metrics/stats
```

### Mapeo de temas del backend

Cada backend mapea el formato genérico a su formato nativo:

**Backend de Pulsar:**
```python
def map_topic(self, generic_topic: str) -> str:
    # Parse: q1/tg/flow/text-completion-requests
    qos, tenant, namespace, queue = generic_topic.split('/', 3)

    # Map QoS to persistence
    persistence = 'persistent' if qos in ['q1', 'q2'] else 'non-persistent'

    # Return Pulsar URI: persistent://tg/flow/text-completion-requests
    return f"{persistence}://{tenant}/{namespace}/{queue}"
```

**Backend de MQTT:**
```python
def map_topic(self, generic_topic: str) -> tuple[str, int]:
    # Parse: q1/tg/flow/text-completion-requests
    qos, tenant, namespace, queue = generic_topic.split('/', 3)

    # Map QoS level
    qos_level = {'q0': 0, 'q1': 1, 'q2': 2}[qos]

    # Build MQTT topic including tenant/namespace for proper namespacing
    mqtt_topic = f"{tenant}/{namespace}/{queue}"

    return mqtt_topic, qos_level
```

### Función de ayuda de tema actualizada

```python
# schema/core/topic.py
def topic(queue_name, qos='q1', tenant='tg', namespace='flow'):
    """
    Create a generic topic identifier that can be mapped by backends.

    Args:
        queue_name: The queue/topic name
        qos: Quality of service
             - 'q0' = best-effort (no ack)
             - 'q1' = at-least-once (ack required)
             - 'q2' = exactly-once (two-phase ack)
        tenant: Tenant identifier for multi-tenancy
        namespace: Namespace within tenant

    Returns:
        Generic topic string: qos/tenant/namespace/queue_name

    Examples:
        topic('my-queue')  # q1/tg/flow/my-queue
        topic('config', qos='q2', namespace='config')  # q2/tg/config/config
    """
    return f"{qos}/{tenant}/{namespace}/{queue_name}"
```

### Configuración e Inicialización

**Argumentos de Línea de Comandos + Variables de Entorno:**

```python
# In base/async_processor.py - add_args() method
@staticmethod
def add_args(parser):
    # Pub/sub backend selection
    parser.add_argument(
        '--pubsub-backend',
        default=os.getenv('PUBSUB_BACKEND', 'pulsar'),
        choices=['pulsar', 'mqtt'],
        help='Pub/sub backend (default: pulsar, env: PUBSUB_BACKEND)'
    )

    # Pulsar-specific configuration
    parser.add_argument(
        '--pulsar-host',
        default=os.getenv('PULSAR_HOST', 'pulsar://localhost:6650'),
        help='Pulsar host (default: pulsar://localhost:6650, env: PULSAR_HOST)'
    )

    parser.add_argument(
        '--pulsar-api-key',
        default=os.getenv('PULSAR_API_KEY', None),
        help='Pulsar API key (env: PULSAR_API_KEY)'
    )

    parser.add_argument(
        '--pulsar-listener',
        default=os.getenv('PULSAR_LISTENER', None),
        help='Pulsar listener name (env: PULSAR_LISTENER)'
    )

    # MQTT-specific configuration
    parser.add_argument(
        '--mqtt-host',
        default=os.getenv('MQTT_HOST', 'localhost'),
        help='MQTT broker host (default: localhost, env: MQTT_HOST)'
    )

    parser.add_argument(
        '--mqtt-port',
        type=int,
        default=int(os.getenv('MQTT_PORT', '1883')),
        help='MQTT broker port (default: 1883, env: MQTT_PORT)'
    )

    parser.add_argument(
        '--mqtt-username',
        default=os.getenv('MQTT_USERNAME', None),
        help='MQTT username (env: MQTT_USERNAME)'
    )

    parser.add_argument(
        '--mqtt-password',
        default=os.getenv('MQTT_PASSWORD', None),
        help='MQTT password (env: MQTT_PASSWORD)'
    )
```

**Función de Fábrica:**

```python
# In base/pubsub.py or base/pubsub_factory.py
def get_pubsub(**config) -> PubSubBackend:
    """
    Create and return a pub/sub backend based on configuration.

    Args:
        config: Configuration dict from command-line args
                Must include 'pubsub_backend' key

    Returns:
        Backend instance (PulsarBackend, MQTTBackend, etc.)
    """
    backend_type = config.get('pubsub_backend', 'pulsar')

    if backend_type == 'pulsar':
        return PulsarBackend(
            host=config.get('pulsar_host'),
            api_key=config.get('pulsar_api_key'),
            listener=config.get('pulsar_listener'),
        )
    elif backend_type == 'mqtt':
        return MQTTBackend(
            host=config.get('mqtt_host'),
            port=config.get('mqtt_port'),
            username=config.get('mqtt_username'),
            password=config.get('mqtt_password'),
        )
    else:
        raise ValueError(f"Unknown pub/sub backend: {backend_type}")
```

**Uso en AsyncProcessor:**

```python
# In async_processor.py
class AsyncProcessor:
    def __init__(self, **params):
        self.id = params.get("id")

        # Create backend from config (replaces PulsarClient)
        self.pubsub = get_pubsub(**params)

        # Rest of initialization...
```

### Interfaz de Backend

```python
class PubSubBackend(Protocol):
    """Protocol defining the interface all pub/sub backends must implement."""

    def create_producer(self, topic: str, schema: type, **options) -> BackendProducer:
        """
        Create a producer for a topic.

        Args:
            topic: Generic topic format (qos/tenant/namespace/queue)
            schema: Dataclass type for messages
            options: Backend-specific options (e.g., chunking_enabled)

        Returns:
            Backend-specific producer instance
        """
        ...

    def create_consumer(
        self,
        topic: str,
        subscription: str,
        schema: type,
        initial_position: str = 'latest',
        consumer_type: str = 'shared',
        **options
    ) -> BackendConsumer:
        """
        Create a consumer for a topic.

        Args:
            topic: Generic topic format (qos/tenant/namespace/queue)
            subscription: Subscription/consumer group name
            schema: Dataclass type for messages
            initial_position: 'earliest' or 'latest' (MQTT may ignore)
            consumer_type: 'shared', 'exclusive', 'failover' (MQTT may ignore)
            options: Backend-specific options

        Returns:
            Backend-specific consumer instance
        """
        ...

    def close(self) -> None:
        """Close the backend connection."""
        ...
```

```python
class BackendProducer(Protocol):
    """Protocol for backend-specific producer."""

    def send(self, message: Any, properties: dict = {}) -> None:
        """Send a message (dataclass instance) with optional properties."""
        ...

    def flush(self) -> None:
        """Flush any buffered messages."""
        ...

    def close(self) -> None:
        """Close the producer."""
        ...
```

```python
class BackendConsumer(Protocol):
    """Protocol for backend-specific consumer."""

    def receive(self, timeout_millis: int = 2000) -> Message:
        """
        Receive a message from the topic.

        Raises:
            TimeoutError: If no message received within timeout
        """
        ...

    def acknowledge(self, message: Message) -> None:
        """Acknowledge successful processing of a message."""
        ...

    def negative_acknowledge(self, message: Message) -> None:
        """Negative acknowledge - triggers redelivery."""
        ...

    def unsubscribe(self) -> None:
        """Unsubscribe from the topic."""
        ...

    def close(self) -> None:
        """Close the consumer."""
        ...
```

```python
class Message(Protocol):
    """Protocol for a received message."""

    def value(self) -> Any:
        """Get the deserialized message (dataclass instance)."""
        ...

    def properties(self) -> dict:
        """Get message properties/metadata."""
        ...
```

### Refactorización de Clases Existentes

Las clases existentes `Consumer`, `Producer`, `Publisher`, `Subscriber` permanecen en gran medida intactas:

**Responsabilidades actuales (mantener):**
Modelo de subprocesos asíncronos y grupos de tareas
Lógica de reconexión y manejo de reintentos
Recopilación de métricas
Limitación de velocidad
Gestión de la concurrencia

**Cambios necesarios:**
Eliminar importaciones directas de Pulsar (`pulsar.schema`, `pulsar.InitialPosition`, etc.)
Aceptar `BackendProducer`/`BackendConsumer` en lugar del cliente de Pulsar
Delegar las operaciones de publicación/suscripción reales a instancias de backend
Mapear conceptos genéricos a llamadas de backend

**Ejemplo de refactorización:**

```python
# OLD - consumer.py
class Consumer:
    def __init__(self, client, topic, subscriber, schema, ...):
        self.client = client  # Direct Pulsar client
        # ...

    async def consumer_run(self):
        # Uses pulsar.InitialPosition, pulsar.ConsumerType
        self.consumer = self.client.subscribe(
            topic=self.topic,
            schema=JsonSchema(self.schema),
            initial_position=pulsar.InitialPosition.Earliest,
            consumer_type=pulsar.ConsumerType.Shared,
        )

# NEW - consumer.py
class Consumer:
    def __init__(self, backend_consumer, schema, ...):
        self.backend_consumer = backend_consumer  # Backend-specific consumer
        self.schema = schema
        # ...

    async def consumer_run(self):
        # Backend consumer already created with right settings
        # Just use it directly
        while self.running:
            msg = await asyncio.to_thread(
                self.backend_consumer.receive,
                timeout_millis=2000
            )
            await self.handle_message(msg)
```

### Comportamientos Específicos del Backend

**Backend de Pulsar:**
Mapea `q0` → `non-persistent://`, `q1`/`q2` → `persistent://`
Soporta todos los tipos de consumidores (compartido, exclusivo, de respaldo)
Soporta la posición inicial (earliest/latest)
Reconocimiento nativo de mensajes
Soporte para el registro de esquemas

**Backend de MQTT:**
Mapea `q0`/`q1`/`q2` → Niveles de QoS de MQTT 0/1/2
Incluye el inquilino/espacio de nombres en la ruta del tema para el espaciado de nombres
Genera automáticamente ID de cliente a partir de los nombres de suscripción
Ignora la posición inicial (no hay historial de mensajes en MQTT básico)
Ignora el tipo de consumidor (MQTT utiliza ID de cliente, no grupos de consumidores)
Modelo de publicación/suscripción simple

### Resumen de Decisiones de Diseño

1. ✅ **Nombres de cola genéricos**: Formato `qos/tenant/namespace/queue-name`
2. ✅ **QoS en el ID de la cola**: Determinado por la definición de la cola, no por la configuración
3. ✅ **Reconexión**: Manejada por las clases Consumer/Producer, no por los backends
4. ✅ **Temas de MQTT**: Incluir inquilino/espacio de nombres para un espaciado de nombres adecuado
5. ✅ **Historial de mensajes**: MQTT ignora el parámetro `initial_position` (mejora futura)
6. ✅ **ID de cliente**: El backend de MQTT genera automáticamente a partir del nombre de la suscripción

### Mejoras Futuras

**Historial de mensajes de MQTT:**
Se podría agregar una capa de persistencia opcional (por ejemplo, mensajes retenidos, almacenamiento externo)
Permitiría soportar `initial_position='earliest'`
No es necesario para la implementación inicial
