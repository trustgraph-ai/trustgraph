---
layout: default
title: "Servicios de Herramientas: Herramientas de Agente Dinámicamente Conectables"
parent: "Spanish (Beta)"
---

# Servicios de Herramientas: Herramientas de Agente Dinámicamente Conectables

> **Beta Translation:** This document was translated via Machine Learning and as such may not be 100% accurate. All non-English languages are currently classified as Beta.

## Estado

Implementado

## Resumen

Esta especificación define un mecanismo para herramientas de agente dinámicamente conectables llamadas "servicios de herramientas". A diferencia de los tipos de herramientas integradas existentes (`KnowledgeQueryImpl`, `McpToolImpl`, etc.), los servicios de herramientas permiten introducir nuevas herramientas mediante:

1. Desplegar un nuevo servicio basado en Pulsar
2. Agregar un descriptor de configuración que le indique al agente cómo invocarlo

Esto permite la extensibilidad sin modificar el marco de respuesta del agente principal.

## Terminología

| Término | Definición |
|------|------------|
| **Herramienta Integrada** | Tipos de herramientas existentes con implementaciones codificadas en `tools.py` |
| **Servicio de Herramienta** | Un servicio de Pulsar que se puede invocar como una herramienta de agente, definido por un descriptor de servicio |
| **Herramienta** | Una instancia configurada que hace referencia a un servicio de herramienta, expuesta al agente/LLM |

Este es un modelo de dos niveles, análogo a las herramientas MCP:
MCP: El servidor MCP define la interfaz de la herramienta → La configuración de la herramienta la referencia
Servicios de Herramienta: El servicio de herramienta define la interfaz de Pulsar → La configuración de la herramienta la referencia

## Antecedentes: Herramientas Existentes

### Implementación de Herramienta Integrada

Las herramientas se definen actualmente en `trustgraph-flow/trustgraph/agent/react/tools.py` con implementaciones tipadas:

```python
class KnowledgeQueryImpl:
    async def invoke(self, question):
        client = self.context("graph-rag-request")
        return await client.rag(question, self.collection)
```

Cada tipo de herramienta:
Tiene un servicio Pulsar predefinido al que llama (por ejemplo, `graph-rag-request`)
Conoce el método exacto para llamar al cliente (por ejemplo, `client.rag()`)
Tiene argumentos tipados definidos en la implementación

### Registro de herramientas (service.py:105-214)

Las herramientas se cargan desde la configuración con un campo `type` que se mapea a una implementación:

```python
if impl_id == "knowledge-query":
    impl = functools.partial(KnowledgeQueryImpl, collection=data.get("collection"))
elif impl_id == "text-completion":
    impl = TextCompletionImpl
# ... etc
```

## Arquitectura

### Modelo de Dos Capas

#### Capa 1: Descriptor del Servicio de Herramienta

Un servicio de herramienta define una interfaz de servicio de Pulsar. Declara:
Las colas de Pulsar para solicitud/respuesta
Los parámetros de configuración que requiere de las herramientas que lo utilizan

```json
{
  "id": "custom-rag",
  "request-queue": "non-persistent://tg/request/custom-rag",
  "response-queue": "non-persistent://tg/response/custom-rag",
  "config-params": [
    {"name": "collection", "required": true}
  ]
}
```

Un servicio de herramienta que no necesita parámetros de configuración:

```json
{
  "id": "calculator",
  "request-queue": "non-persistent://tg/request/calc",
  "response-queue": "non-persistent://tg/response/calc",
  "config-params": []
}
```

#### Nivel 2: Descriptor de la herramienta

Una herramienta hace referencia a un servicio de herramienta y proporciona:
Valores de parámetros de configuración (que satisfacen los requisitos del servicio)
Metadatos de la herramienta para el agente (nombre, descripción)
Definiciones de argumentos para el LLM

```json
{
  "type": "tool-service",
  "name": "query-customers",
  "description": "Query the customer knowledge base",
  "service": "custom-rag",
  "collection": "customers",
  "arguments": [
    {
      "name": "question",
      "type": "string",
      "description": "The question to ask about customers"
    }
  ]
}
```

Múltiples herramientas pueden referenciar el mismo servicio con diferentes configuraciones:

```json
{
  "type": "tool-service",
  "name": "query-products",
  "description": "Query the product knowledge base",
  "service": "custom-rag",
  "collection": "products",
  "arguments": [
    {
      "name": "question",
      "type": "string",
      "description": "The question to ask about products"
    }
  ]
}
```

### Formato de solicitud

Cuando se invoca una herramienta, la solicitud al servicio de la herramienta incluye:
`user`: Desde la solicitud del agente (multitenencia)
`config`: Valores de configuración codificados en JSON provenientes de la descripción de la herramienta
`arguments`: Argumentos codificados en JSON provenientes del LLM

```json
{
  "user": "alice",
  "config": "{\"collection\": \"customers\"}",
  "arguments": "{\"question\": \"What are the top customer complaints?\"}"
}
```

El servicio de herramientas recibe esto como diccionarios analizados en el método `invoke`.

### Implementación Genérica del Servicio de Herramientas

Una clase `ToolServiceImpl` invoca servicios de herramientas basándose en la configuración:

```python
class ToolServiceImpl:
    def __init__(self, context, request_queue, response_queue, config_values, arguments, processor):
        self.request_queue = request_queue
        self.response_queue = response_queue
        self.config_values = config_values  # e.g., {"collection": "customers"}
        # ...

    async def invoke(self, **arguments):
        client = await self._get_or_create_client()
        response = await client.call(user, self.config_values, arguments)
        if isinstance(response, str):
            return response
        else:
            return json.dumps(response)
```

## Decisiones de Diseño

### Modelo de Configuración de Dos Niveles

Los servicios de herramientas siguen un modelo de dos niveles similar a las herramientas de MCP:

1. **Servicio de Herramienta**: Define la interfaz del servicio de Pulsar (tema, parámetros de configuración requeridos)
2. **Herramienta**: Hace referencia a un servicio de herramienta, proporciona valores de configuración, define argumentos de LLM

Esta separación permite:
Que un servicio de herramienta sea utilizado por múltiples herramientas con diferentes configuraciones
Una distinción clara entre la interfaz del servicio y la configuración de la herramienta
La reutilización de las definiciones de servicio

### Mapeo de Solicitudes: Transmisión con Sobre

La solicitud a un servicio de herramienta es un sobre estructurado que contiene:
`user`: Propagado desde la solicitud del agente para la multi-inquilinato
Valores de configuración: Del descriptor de la herramienta (por ejemplo, `collection`)
`arguments`: Argumentos proporcionados por el LLM, transmitidos como un diccionario

El administrador del agente analiza la respuesta del LLM en `act.arguments` como un diccionario (`agent_manager.py:117-154`). Este diccionario se incluye en el sobre de la solicitud.

### Manejo de Esquemas: No Tipado

Las solicitudes y las respuestas utilizan diccionarios no tipados. No hay validación de esquema a nivel del agente; el servicio de herramienta es responsable de validar sus entradas. Esto proporciona la máxima flexibilidad para definir nuevos servicios.

### Interfaz de Cliente: Temas Directos de Pulsar

Los servicios de herramientas utilizan temas directos de Pulsar sin requerir configuración de flujo. El descriptor del servicio de herramienta especifica los nombres completos de las colas:

```json
{
  "id": "joke-service",
  "request-queue": "non-persistent://tg/request/joke",
  "response-queue": "non-persistent://tg/response/joke",
  "config-params": [...]
}
```

Esto permite que los servicios se alojen en cualquier espacio de nombres.

### Manejo de errores: Convención de error estándar

Las respuestas del servicio de herramientas siguen la convención de esquema existente con un campo `error`:

```python
@dataclass
class Error:
    type: str = ""
    message: str = ""
```

Estructura de la respuesta:
Éxito: `error` es `None`, la respuesta contiene el resultado
Error: `error` se completa con `type` y `message`

Esto coincide con el patrón utilizado en todo el esquema de servicios existente (por ejemplo, `PromptResponse`, `QueryResponse`, `AgentResponse`).

### Correlación de solicitudes/respuestas

Las solicitudes y las respuestas se correlacionan mediante un `id` en las propiedades del mensaje de Pulsar:

La solicitud incluye `id` en las propiedades: `properties={"id": id}`
La(s) respuesta(s) incluyen el mismo `id`: `properties={"id": id}`

Esto sigue el patrón existente utilizado en todo el código base (por ejemplo, `agent_service.py`, `llm_service.py`).

### Soporte de transmisión

Los servicios de herramientas pueden devolver respuestas de transmisión:

Múltiples mensajes de respuesta con el mismo `id` en las propiedades
Cada respuesta incluye el campo `end_of_stream: bool`
La respuesta final tiene `end_of_stream: True`

Esto coincide con el patrón utilizado en `AgentResponse` y otros servicios de transmisión.

### Manejo de la respuesta: retorno de cadena

Todas las herramientas existentes siguen el mismo patrón: **recibir argumentos como un diccionario, devolver la observación como una cadena**.

| Herramienta | Manejo de la respuesta |
|------|------------------|
| `KnowledgeQueryImpl` | Devuelve `client.rag()` directamente (cadena) |
| `TextCompletionImpl` | Devuelve `client.question()` directamente (cadena) |
| `McpToolImpl` | Devuelve una cadena, o `json.dumps(output)` si no es una cadena |
| `StructuredQueryImpl` | Formatea el resultado a una cadena |
| `PromptImpl` | Devuelve `client.prompt()` directamente (cadena) |

Los servicios de herramientas siguen el mismo contrato:
El servicio devuelve una respuesta de cadena (la observación)
Si la respuesta no es una cadena, se convierte mediante `json.dumps()`
No se necesita ninguna configuración de extracción en el descriptor

Esto mantiene el descriptor simple y delega la responsabilidad de devolver una respuesta de texto adecuada al agente en el servicio.

## Guía de configuración

Para agregar un nuevo servicio de herramientas, se requieren dos elementos de configuración:

### 1. Configuración del servicio de herramientas

Se almacena bajo la clave de configuración `tool-service`. Define las colas de Pulsar y los parámetros de configuración disponibles.

| Campo | Requerido | Descripción |
|-------|----------|-------------|
| `id` | Sí | Identificador único para el servicio de herramientas |
| `request-queue` | Sí | Tema de Pulsar completo para las solicitudes (por ejemplo, `non-persistent://tg/request/joke`) |
| `response-queue` | Sí | Tema de Pulsar completo para las respuestas (por ejemplo, `non-persistent://tg/response/joke`) |
| `config-params` | No | Matriz de parámetros de configuración que el servicio acepta |

Cada parámetro de configuración puede especificar:
`name`: Nombre del parámetro (obligatorio)
`required`: Si el parámetro debe ser proporcionado por las herramientas (por defecto: falso)

Ejemplo:
```json
{
  "id": "joke-service",
  "request-queue": "non-persistent://tg/request/joke",
  "response-queue": "non-persistent://tg/response/joke",
  "config-params": [
    {"name": "style", "required": false}
  ]
}
```

### 2. Configuración de la herramienta

Almacenado bajo la clave de configuración `tool`. Define una herramienta que el agente puede utilizar.

| Campo | Requerido | Descripción |
|-------|----------|-------------|
| `type` | Sí | Debe ser `"tool-service"` |
| `name` | Sí | Nombre de la herramienta expuesto al LLM |
| `description` | Sí | Descripción de lo que hace la herramienta (mostrada al LLM) |
| `service` | Sí | ID del servicio de herramientas a invocar |
| `arguments` | No | Matriz de definiciones de argumentos para el LLM |
| *(parámetros de configuración)* | Varía | Cualquier parámetro de configuración definido por el servicio |

Cada argumento puede especificar:
`name`: Nombre del argumento (requerido)
`type`: Tipo de datos, por ejemplo, `"string"` (requerido)
`description`: Descripción mostrada al LLM (requerido)

Ejemplo:
```json
{
  "type": "tool-service",
  "name": "tell-joke",
  "description": "Tell a joke on a given topic",
  "service": "joke-service",
  "style": "pun",
  "arguments": [
    {
      "name": "topic",
      "type": "string",
      "description": "The topic for the joke (e.g., programming, animals, food)"
    }
  ]
}
```

### Carga de la configuración

Utilice `tg-put-config-item` para cargar configuraciones:

```bash
# Load tool-service config
tg-put-config-item tool-service/joke-service < joke-service.json

# Load tool config
tg-put-config-item tool/tell-joke < tell-joke.json
```

El agente-administrador debe reiniciarse para cargar nuevas configuraciones.

## Detalles de implementación

### Esquema

Tipos de solicitud y respuesta en `trustgraph-base/trustgraph/schema/services/tool_service.py`:

```python
@dataclass
class ToolServiceRequest:
    user: str = ""           # User context for multi-tenancy
    config: str = ""         # JSON-encoded config values from tool descriptor
    arguments: str = ""      # JSON-encoded arguments from LLM

@dataclass
class ToolServiceResponse:
    error: Error | None = None
    response: str = ""       # String response (the observation)
    end_of_stream: bool = False
```

### Servidor: Servicio DynamicToolService

Clase base en `trustgraph-base/trustgraph/base/dynamic_tool_service.py`:

```python
class DynamicToolService(AsyncProcessor):
    """Base class for implementing tool services."""

    def __init__(self, **params):
        topic = params.get("topic", default_topic)
        # Constructs topics: non-persistent://tg/request/{topic}, non-persistent://tg/response/{topic}
        # Sets up Consumer and Producer

    async def invoke(self, user, config, arguments):
        """Override this method to implement the tool's logic."""
        raise NotImplementedError()
```

### Cliente: ToolServiceImpl

Implementación en `trustgraph-flow/trustgraph/agent/react/tools.py`:

```python
class ToolServiceImpl:
    def __init__(self, context, request_queue, response_queue, config_values, arguments, processor):
        # Uses the provided queue paths directly
        # Creates ToolServiceClient on first use

    async def invoke(self, **arguments):
        client = await self._get_or_create_client()
        response = await client.call(user, config_values, arguments)
        return response if isinstance(response, str) else json.dumps(response)
```

### Archivos

| Archivo | Propósito |
|------|---------|
| `trustgraph-base/trustgraph/schema/services/tool_service.py` | Esquemas de solicitud/respuesta |
| `trustgraph-base/trustgraph/base/tool_service_client.py` | Cliente para invocar servicios |
| `trustgraph-base/trustgraph/base/dynamic_tool_service.py` | Clase base para la implementación de servicios |
| `trustgraph-flow/trustgraph/agent/react/tools.py` | Clase `ToolServiceImpl` |
| `trustgraph-flow/trustgraph/agent/react/service.py` | Carga de configuración |

### Ejemplo: Servicio de Chistes

Un ejemplo de servicio en `trustgraph-flow/trustgraph/tool_service/joke/`:

```python
class Processor(DynamicToolService):
    async def invoke(self, user, config, arguments):
        style = config.get("style", "pun")
        topic = arguments.get("topic", "")
        joke = pick_joke(topic, style)
        return f"Hey {user}! Here's a {style} for you:\n\n{joke}"
```

Configuración del servicio de herramientas:
```json
{
  "id": "joke-service",
  "request-queue": "non-persistent://tg/request/joke",
  "response-queue": "non-persistent://tg/response/joke",
  "config-params": [{"name": "style", "required": false}]
}
```

Configuración de la herramienta:
```json
{
  "type": "tool-service",
  "name": "tell-joke",
  "description": "Tell a joke on a given topic",
  "service": "joke-service",
  "style": "pun",
  "arguments": [
    {"name": "topic", "type": "string", "description": "The topic for the joke"}
  ]
}
```

### Compatibilidad hacia atrás

Los tipos de herramientas integradas existentes continúan funcionando sin cambios.
`tool-service` es un nuevo tipo de herramienta, además de los tipos existentes (`knowledge-query`, `mcp-tool`, etc.).

## Consideraciones futuras

### Servicios de autoanuncio

Una mejora futura podría permitir que los servicios publiquen sus propios descriptores:

Los servicios publican en un tema `tool-descriptors` conocido al inicio.
El agente se suscribe y registra dinámicamente las herramientas.
Permite una verdadera funcionalidad de conexión y uso sin cambios de configuración.

Esto está fuera del alcance de la implementación inicial.

## Referencias

Implementación actual de la herramienta: `trustgraph-flow/trustgraph/agent/react/tools.py`
Registro de herramientas: `trustgraph-flow/trustgraph/agent/react/service.py:105-214`
Esquemas del agente: `trustgraph-base/trustgraph/schema/services/agent.py`
