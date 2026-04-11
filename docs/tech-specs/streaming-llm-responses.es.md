# Especificación Técnica de Respuestas de LLM en Streaming

## Resumen

Esta especificación describe la implementación del soporte de streaming para respuestas de LLM
en TrustGraph. El streaming permite la entrega en tiempo real de tokens generados
a medida que son producidos por el LLM, en lugar de esperar a que se complete
la generación de la respuesta.

Esta implementación admite los siguientes casos de uso:

1. **Interfaces de Usuario en Tiempo Real**: Transmite tokens a la interfaz de usuario a medida que se generan,
   proporcionando retroalimentación visual inmediata.
2. **Reducción del Tiempo Hasta el Primer Token**: Los usuarios ven la salida inmediatamente
   en lugar de esperar a que se complete la generación.
3. **Manejo de Respuestas Largas**: Maneja salidas muy largas que de otro modo
   podrían provocar un tiempo de espera o exceder los límites de memoria.
4. **Aplicaciones Interactivas**: Permite interfaces de chat y agentes receptivas.

## Objetivos

**Compatibilidad con Versiones Anteriores**: Los clientes existentes que no utilizan streaming continúan funcionando
  sin modificaciones.
**Diseño de API Consistente**: El streaming y el no streaming utilizan los mismos patrones de esquema
  con una divergencia mínima.
**Flexibilidad del Proveedor**: Soporte de streaming cuando esté disponible, con una
  alternativa gradual cuando no esté disponible.
**Implementación por Fases**: Implementación incremental para reducir el riesgo.
**Soporte de Extremo a Extremo**: Streaming desde el proveedor de LLM hasta las aplicaciones cliente
  a través de Pulsar, la API de Gateway y la API de Python.

## Antecedentes

### Arquitectura Actual

El flujo actual de finalización de texto de LLM funciona de la siguiente manera:

1. El cliente envía `TextCompletionRequest` con los campos `system` y `prompt`.
2. El servicio de LLM procesa la solicitud y espera a que se complete la generación.
3. Se devuelve un único `TextCompletionResponse` con la cadena `response` completa.

Esquema actual (`trustgraph-base/trustgraph/schema/services/llm.py`):

```python
class TextCompletionRequest(Record):
    system = String()
    prompt = String()

class TextCompletionResponse(Record):
    error = Error()
    response = String()
    in_token = Integer()
    out_token = Integer()
    model = String()
```

### Limitaciones actuales

**Latencia**: Los usuarios deben esperar a que se complete la generación antes de ver cualquier resultado.
**Riesgo de tiempo de espera**: Las generaciones largas pueden exceder los umbrales de tiempo de espera del cliente.
**Mala experiencia de usuario**: La falta de retroalimentación durante la generación crea la percepción de lentitud.
**Uso de recursos**: Las respuestas completas deben almacenarse en búfer en la memoria.

Esta especificación aborda estas limitaciones al permitir la entrega incremental de respuestas, manteniendo la compatibilidad total con versiones anteriores.


## Diseño técnico

### Fase 1: Infraestructura

La Fase 1 establece la base para la transmisión mediante la modificación de esquemas, API y herramientas de línea de comandos.


#### Cambios en el esquema

##### Esquema de LLM (`trustgraph-base/trustgraph/schema/services/llm.py`)

**Cambios en la solicitud:**

```python
class TextCompletionRequest(Record):
    system = String()
    prompt = String()
    streaming = Boolean()  # NEW: Default false for backward compatibility
```

`streaming`: Cuando `true`, solicita la entrega de la respuesta en modo de transmisión.
Predeterminado: `false` (el comportamiento existente se mantiene).

**Cambios en la respuesta:**

```python
class TextCompletionResponse(Record):
    error = Error()
    response = String()
    in_token = Integer()
    out_token = Integer()
    model = String()
    end_of_stream = Boolean()  # NEW: Indicates final message
```

`end_of_stream`: Cuando `true`, indica que esta es la respuesta final (o única).
Para solicitudes no de transmisión: Respuesta única con `end_of_stream=true`.
Para solicitudes de transmisión: Múltiples respuestas, todas con `end_of_stream=false`
  excepto la última.

##### Esquema de la solicitud (`trustgraph-base/trustgraph/schema/services/prompt.py`)

El servicio de solicitud envuelve la finalización de texto, por lo que refleja el mismo patrón:

**Cambios en la solicitud:**

```python
class PromptRequest(Record):
    id = String()
    terms = Map(String())
    streaming = Boolean()  # NEW: Default false
```

**Cambios en la respuesta:**

```python
class PromptResponse(Record):
    error = Error()
    text = String()
    object = String()
    end_of_stream = Boolean()  # NEW: Indicates final message
```

#### Cambios en la API de Gateway

La API de Gateway debe exponer capacidades de transmisión a clientes HTTP/WebSocket.

**Actualizaciones de la API REST:**

`POST /api/v1/text-completion`: Aceptar el parámetro `streaming` en el cuerpo de la solicitud.
El comportamiento de la respuesta depende de la bandera de transmisión:
  `streaming=false`: Respuesta JSON única (comportamiento actual).
  `streaming=true`: Flujo de eventos enviados por el servidor (SSE) o mensajes WebSocket.

**Formato de respuesta (transmisión):**

Cada fragmento transmitido sigue la misma estructura de esquema:
```json
{
  "response": "partial text...",
  "end_of_stream": false,
  "model": "model-name"
}
```

Fragmento final:
```json
{
  "response": "final text chunk",
  "end_of_stream": true,
  "in_token": 150,
  "out_token": 500,
  "model": "model-name"
}
```

#### Cambios en la API de Python

La API del cliente de Python debe soportar tanto modos de transmisión como no de transmisión
manteniendo la compatibilidad con versiones anteriores.

**Actualizaciones de LlmClient** (`trustgraph-base/trustgraph/clients/llm_client.py`):

```python
class LlmClient(BaseClient):
    def request(self, system, prompt, timeout=300, streaming=False):
        """
        Non-streaming request (backward compatible).
        Returns complete response string.
        """
        # Existing behavior when streaming=False

    async def request_stream(self, system, prompt, timeout=300):
        """
        Streaming request.
        Yields response chunks as they arrive.
        """
        # New async generator method
```

**Actualizaciones de PromptClient** (`trustgraph-base/trustgraph/base/prompt_client.py`):

Patrón similar con el parámetro `streaming` y la variante de generador asíncrono.

#### Cambios en la herramienta de línea de comandos

**tg-invoke-llm** (`trustgraph-cli/trustgraph/cli/invoke_llm.py`):

```
tg-invoke-llm [system] [prompt] [--no-streaming] [-u URL] [-f flow-id]
```

La transmisión está habilitada de forma predeterminada para una mejor experiencia de usuario interactiva.
La opción `--no-streaming` desactiva la transmisión.
Cuando la transmisión está habilitada: envía los tokens a la salida estándar a medida que llegan.
Cuando la transmisión no está habilitada: espera la respuesta completa y luego la muestra.

**tg-invoke-prompt** (`trustgraph-cli/trustgraph/cli/invoke_prompt.py`):

```
tg-invoke-prompt [template-id] [var=value...] [--no-streaming] [-u URL] [-f flow-id]
```

El mismo patrón que `tg-invoke-llm`.

#### Cambios en la Clase Base del Servicio LLM

**LlmService** (`trustgraph-base/trustgraph/base/llm_service.py`):

```python
class LlmService(FlowProcessor):
    async def on_request(self, msg, consumer, flow):
        request = msg.value()
        streaming = getattr(request, 'streaming', False)

        if streaming and self.supports_streaming():
            async for chunk in self.generate_content_stream(...):
                await self.send_response(chunk, end_of_stream=False)
            await self.send_response(final_chunk, end_of_stream=True)
        else:
            response = await self.generate_content(...)
            await self.send_response(response, end_of_stream=True)

    def supports_streaming(self):
        """Override in subclass to indicate streaming support."""
        return False

    async def generate_content_stream(self, system, prompt, model, temperature):
        """Override in subclass to implement streaming."""
        raise NotImplementedError()
```

--

### Fase 2: Prueba de concepto de VertexAI

La Fase 2 implementa el streaming en un único proveedor (VertexAI) para validar la
infraestructura y habilitar pruebas de extremo a extremo.

#### Implementación de VertexAI

**Módulo:** `trustgraph-vertexai/trustgraph/model/text_completion/vertexai/llm.py`

**Cambios:**

1. Sobreescribir `supports_streaming()` para devolver `True`
2. Implementar generador asíncrono `generate_content_stream()`
3. Manejar tanto los modelos Gemini como Claude (a través de la API de VertexAI Anthropic)

**Streaming de Gemini:**

```python
async def generate_content_stream(self, system, prompt, model, temperature):
    model_instance = self.get_model(model, temperature)
    response = model_instance.generate_content(
        [system, prompt],
        stream=True  # Enable streaming
    )
    for chunk in response:
        yield LlmChunk(
            text=chunk.text,
            in_token=None,  # Available only in final chunk
            out_token=None,
        )
    # Final chunk includes token counts from response.usage_metadata
```

**Claude (a través de VertexAI Anthropic) en modo de transmisión:**

```python
async def generate_content_stream(self, system, prompt, model, temperature):
    with self.anthropic_client.messages.stream(...) as stream:
        for text in stream.text_stream:
            yield LlmChunk(text=text)
    # Token counts from stream.get_final_message()
```

#### Pruebas

Pruebas unitarias para el ensamblaje de respuestas en streaming.
Pruebas de integración con VertexAI (Gemini y Claude).
Pruebas de extremo a extremo: CLI -> Gateway -> Pulsar -> VertexAI -> back.
Pruebas de compatibilidad con versiones anteriores: Las solicitudes no en streaming aún funcionan.

--

### Fase 3: Todos los proveedores de LLM

La fase 3 extiende el soporte de streaming a todos los proveedores de LLM en el sistema.

#### Estado de implementación del proveedor

Cada proveedor debe:
1. **Soporte completo de streaming**: Implementar `generate_content_stream()`
2. **Modo de compatibilidad**: Manejar la bandera `end_of_stream` correctamente
   (devolver una única respuesta con `end_of_stream=true`)

| Proveedor | Paquete | Soporte de streaming |
|----------|---------|-------------------|
| OpenAI | trustgraph-flow | Completo (API de streaming nativo) |
| Claude/Anthropic | trustgraph-flow | Completo (API de streaming nativo) |
| Ollama | trustgraph-flow | Completo (API de streaming nativo) |
| Cohere | trustgraph-flow | Completo (API de streaming nativo) |
| Mistral | trustgraph-flow | Completo (API de streaming nativo) |
| Azure OpenAI | trustgraph-flow | Completo (API de streaming nativo) |
| Google AI Studio | trustgraph-flow | Completo (API de streaming nativo) |
| VertexAI | trustgraph-vertexai | Completo (Fase 2) |
| Bedrock | trustgraph-bedrock | Completo (API de streaming nativo) |
| LM Studio | trustgraph-flow | Completo (compatible con OpenAI) |
| LlamaFile | trustgraph-flow | Completo (compatible con OpenAI) |
| vLLM | trustgraph-flow | Completo (compatible con OpenAI) |
| TGI | trustgraph-flow | Por determinar |
| Azure | trustgraph-flow | Por determinar |

#### Patrón de implementación

Para proveedores compatibles con OpenAI (OpenAI, LM Studio, LlamaFile, vLLM):

```python
async def generate_content_stream(self, system, prompt, model, temperature):
    response = await self.client.chat.completions.create(
        model=model,
        messages=[
            {"role": "system", "content": system},
            {"role": "user", "content": prompt}
        ],
        temperature=temperature,
        stream=True
    )
    async for chunk in response:
        if chunk.choices[0].delta.content:
            yield LlmChunk(text=chunk.choices[0].delta.content)
```

--

### Fase 4: API del Agente

La Fase 4 extiende la transmisión a la API del Agente. Esto es más complejo porque
la API del Agente ya es inherentemente multi-mensaje (pensamiento → acción → observación
→ repetir → respuesta final).

#### Esquema actual del Agente

```python
class AgentStep(Record):
    thought = String()
    action = String()
    arguments = Map(String())
    observation = String()
    user = String()

class AgentRequest(Record):
    question = String()
    state = String()
    group = Array(String())
    history = Array(AgentStep())
    user = String()

class AgentResponse(Record):
    answer = String()
    error = Error()
    thought = String()
    observation = String()
```

#### Cambios Propuestos al Esquema del Agente

**Solicitar Cambios:**

```python
class AgentRequest(Record):
    question = String()
    state = String()
    group = Array(String())
    history = Array(AgentStep())
    user = String()
    streaming = Boolean()  # NEW: Default false
```

**Cambios en la respuesta:**

El agente produce múltiples tipos de salida durante su ciclo de razonamiento:
Pensamientos (razonamiento)
Acciones (llamadas a herramientas)
Observaciones (resultados de las herramientas)
Respuesta (respuesta final)
Errores

Dado que `chunk_type` identifica qué tipo de contenido se está enviando, los campos separados
`answer`, `error`, `thought` y `observation` se pueden combinar en
un único campo `content`:

```python
class AgentResponse(Record):
    chunk_type = String()       # "thought", "action", "observation", "answer", "error"
    content = String()          # The actual content (interpretation depends on chunk_type)
    end_of_message = Boolean()  # Current thought/action/observation/answer is complete
    end_of_dialog = Boolean()   # Entire agent dialog is complete
```

**Semántica de los campos:**

`chunk_type`: Indica qué tipo de contenido se encuentra en el campo `content`
  `"thought"`: Razonamiento/pensamiento del agente
  `"action"`: Herramienta/acción que se está invocando
  `"observation"`: Resultado de la ejecución de la herramienta
  `"answer"`: Respuesta final a la pregunta del usuario
  `"error"`: Mensaje de error

`content`: El contenido transmitido real, interpretado según `chunk_type`

`end_of_message`: Cuando `true`, el tipo de fragmento actual está completo
  Ejemplo: Todos los tokens para el pensamiento actual han sido enviados
  Permite a los clientes saber cuándo pasar a la siguiente etapa

`end_of_dialog`: Cuando `true`, la interacción completa del agente ha finalizado
  Este es el mensaje final en la transmisión

#### Comportamiento de la transmisión del agente

Cuando `streaming=true`:

1. **Transmisión de pensamientos:**
   Múltiples fragmentos con `chunk_type="thought"`, `end_of_message=false`
   El fragmento final del pensamiento tiene `end_of_message=true`
2. **Notificación de acción:**
   Un solo fragmento con `chunk_type="action"`, `end_of_message=true`
3. **Observación:**
   Fragmento(s) con `chunk_type="observation"`, el final tiene `end_of_message=true`
4. **Repetir** los pasos 1-3 mientras el agente razona
5. **Respuesta final:**
   `chunk_type="answer"` con la respuesta final en `content`
   El último fragmento tiene `end_of_message=true`, `end_of_dialog=true`

**Secuencia de ejemplo de la transmisión:**

```
{chunk_type: "thought", content: "I need to", end_of_message: false, end_of_dialog: false}
{chunk_type: "thought", content: " search for...", end_of_message: true, end_of_dialog: false}
{chunk_type: "action", content: "search", end_of_message: true, end_of_dialog: false}
{chunk_type: "observation", content: "Found: ...", end_of_message: true, end_of_dialog: false}
{chunk_type: "thought", content: "Based on this", end_of_message: false, end_of_dialog: false}
{chunk_type: "thought", content: " I can answer...", end_of_message: true, end_of_dialog: false}
{chunk_type: "answer", content: "The answer is...", end_of_message: true, end_of_dialog: true}
```

Cuando `streaming=false`:
Comportamiento actual preservado
Respuesta única con respuesta completa
`end_of_message=true`, `end_of_dialog=true`

#### Gateway y API de Python

Gateway: Nuevo punto final SSE/WebSocket para la transmisión de agentes
API de Python: Nuevo método de generador asíncrono `agent_stream()`

--

## Consideraciones de seguridad

**Sin nueva superficie de ataque**: La transmisión utiliza la misma autenticación/autorización
**Limitación de velocidad**: Aplicar límites de velocidad por token o por fragmento si es necesario
**Manejo de conexiones**: Terminar correctamente las transmisiones en caso de desconexión del cliente
**Gestión de tiempos de espera**: Las solicitudes de transmisión requieren un manejo adecuado de los tiempos de espera

## Consideraciones de rendimiento

**Memoria**: La transmisión reduce el uso máximo de memoria (sin almacenamiento en búfer de la respuesta completa)
**Latencia**: El tiempo hasta el primer token se reduce significativamente
**Sobrecarga de conexión**: Las conexiones SSE/WebSocket tienen una sobrecarga de mantenimiento activo
**Rendimiento de Pulsar**: Múltiples mensajes pequeños frente a un mensaje grande único
  tradeoff

## Estrategia de pruebas

### Pruebas unitarias
Serialización/deserialización de esquema con nuevos campos
Compatibilidad con versiones anteriores (los campos faltantes utilizan los valores predeterminados)
Lógica de ensamblaje de fragmentos

### Pruebas de integración
Implementación de transmisión de cada proveedor de LLM
Puntos finales de transmisión de la API de Gateway
Métodos de transmisión del cliente de Python

### Pruebas de extremo a extremo
Salida de transmisión de la herramienta de línea de comandos
Flujo completo: Cliente → Gateway → Pulsar → LLM → de vuelta
Cargas de trabajo mixtas de transmisión/no transmisión

### Pruebas de compatibilidad con versiones anteriores
Los clientes existentes funcionan sin modificaciones
Las solicitudes no de transmisión se comportan de la misma manera

## Plan de migración

### Fase 1: Infraestructura
Implementar cambios de esquema (compatible con versiones anteriores)
Implementar actualizaciones de la API de Gateway
Implementar actualizaciones de la API de Python
Lanzar actualizaciones de la herramienta de línea de comandos

### Fase 2: VertexAI
Implementar la implementación de transmisión de VertexAI
Validar con cargas de trabajo de prueba

### Fase 3: Todos los proveedores
Implementar las actualizaciones de los proveedores de forma incremental
Monitorear problemas

### Fase 4: API de agente
Implementar cambios de esquema de agente
Implementar la implementación de transmisión de agente
Actualizar la documentación

## Cronograma

| Fase | Descripción | Dependencias |
|-------|-------------|--------------|
| Fase 1 | Infraestructura | Ninguna |
| Fase 2 | PoC de VertexAI | Fase 1 |
| Fase 3 | Todos los proveedores | Fase 2 |
| Fase 4 | API de agente | Fase 3 |

## Decisiones de diseño

Las siguientes preguntas se resolvieron durante la especificación:

1. **Conteo de tokens en la transmisión**: Los conteos de tokens son deltas, no totales acumulados.
   Los consumidores pueden sumarlos si es necesario. Esto coincide con la forma en que la mayoría de los proveedores informan
   el uso y simplifica la implementación.

2. **Manejo de errores en la transmisión**: Si ocurre un error, el campo `error` se
   completa y no se necesitan otros campos. Un error siempre es la comunicación final
   no se permiten ni se esperan mensajes posteriores después de
   un error. Para las transmisiones de LLM/Prompt, `end_of_stream=true`. Para las transmisiones de agente,
   `chunk_type="error"` con `end_of_dialog=true`.

3. **Recuperación de respuesta parcial**: El protocolo de mensajería (Pulsar) es resistente,
   por lo que no se necesita reintento a nivel de mensaje. Si un cliente pierde el seguimiento de la transmisión
   o se desconecta, debe reintentar la solicitud completa desde cero.

4. **Transmisión del servicio de prompt**: La transmisión solo es compatible con texto (`text`)
   respuestas, no respuestas estructuradas (`object`). El servicio de prompt lo sabe desde
   el principio si la salida será JSON o texto según la plantilla del prompt. Si se realiza una
   solicitud de transmisión para un prompt de salida JSON, el
   servicio debe:
   Devolver el JSON completo en una sola respuesta con `end_of_stream=true`, o
   Rechazar la solicitud de transmisión con un error

## Preguntas abiertas

Ninguna en este momento.

## Referencias

Esquema de LLM actual: `trustgraph-base/trustgraph/schema/services/llm.py`
Esquema de prompt actual: `trustgraph-base/trustgraph/schema/services/prompt.py`
Esquema de agente actual: `trustgraph-base/trustgraph/schema/services/agent.py`
Base del servicio de LLM: `trustgraph-base/trustgraph/base/llm_service.py`
Proveedor de VertexAI: `trustgraph-vertexai/trustgraph/model/text_completion/vertexai/llm.py`
API de Gateway: `trustgraph-base/trustgraph/api/`
Herramientas de CLI: `trustgraph-cli/trustgraph/cli/`
