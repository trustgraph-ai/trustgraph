# Especificación Técnica del Procesamiento por Lotes de Embeddings

## Resumen

Esta especificación describe optimizaciones para el servicio de embeddings para soportar el procesamiento por lotes de múltiples textos en una sola solicitud. La implementación actual procesa un texto a la vez, perdiendo las significativas ventajas de rendimiento que los modelos de embeddings proporcionan al procesar lotes.

1. **Ineficiencia en el Procesamiento de un Solo Texto**: La implementación actual envuelve textos individuales en una lista, lo que no aprovecha las capacidades de procesamiento por lotes de FastEmbed.
2. **Sobrecarga de una Solicitud por Texto**: Cada texto requiere un viaje de ida y vuelta separado de Pulsar.
3. **Ineficiencia en la Inferencia del Modelo**: Los modelos de embeddings tienen una sobrecarga fija por lote; los lotes pequeños desperdician recursos de GPU/CPU.
4. **Procesamiento Serial en los Llamadores**: Los servicios clave iteran sobre los elementos y llaman a los embeddings uno a la vez.

## Objetivos

**Soporte para la API de Lotes**: Permitir el procesamiento de múltiples textos en una sola solicitud.
**Compatibilidad con Versiones Anteriores**: Mantener el soporte para solicitudes de un solo texto.
**Mejora Significativa del Rendimiento**: Apuntar a una mejora de rendimiento de 5 a 10 veces para operaciones por lotes.
**Latencia Reducida por Texto**: Disminuir la latencia amortizada al incrustar múltiples textos.
**Eficiencia de Memoria**: Procesar lotes sin un consumo excesivo de memoria.
**Independencia del Proveedor**: Soporte para el procesamiento por lotes en FastEmbed, Ollama y otros proveedores.
**Migración de Llamadores**: Actualizar todos los llamadores de embeddings para que utilicen la API de lotes cuando sea beneficioso.

## Antecedentes

### Implementación Actual - Servicio de Embeddings

La implementación de embeddings en `trustgraph-flow/trustgraph/embeddings/fastembed/processor.py` presenta una ineficiencia de rendimiento significativa:

```python
# fastembed/processor.py line 56
async def on_embeddings(self, text, model=None):
    use_model = model or self.default_model
    self._load_model(use_model)

    vecs = self.embeddings.embed([text])  # Single text wrapped in list

    return [v.tolist() for v in vecs]
```

**Problemas:**

1. **Tamaño de lote 1**: El método `embed()` de FastEmbed está optimizado para el procesamiento por lotes, pero siempre lo llamamos con `[text]`, un lote de tamaño 1.

2. **Sobrecarga por solicitud**: Cada solicitud de incrustación incurre en:
   Serialización/deserialización de mensajes de Pulsar
   Latencia de ida y vuelta de la red
   Sobrecarga de inicio de inferencia del modelo
   Sobrecarga de programación asíncrona de Python

3. **Limitación del esquema**: El esquema `EmbeddingsRequest` solo admite un texto:
   ```python
   @dataclass
   class EmbeddingsRequest:
       text: str = ""  # Single text only
   ```

### Llamadores actuales - Procesamiento serial

#### 1. API Gateway

**Archivo:** `trustgraph-flow/trustgraph/gateway/dispatch/embeddings.py`

La puerta de enlace acepta solicitudes de incrustación de texto único a través de HTTP/WebSocket y las reenvía al servicio de incrustaciones. Actualmente no existe un punto final por lotes.

```python
class EmbeddingsRequestor(ServiceRequestor):
    # Handles single EmbeddingsRequest -> EmbeddingsResponse
    request_schema=EmbeddingsRequest,  # Single text only
    response_schema=EmbeddingsResponse,
```

**Impacto:** Los clientes externos (aplicaciones web, scripts) deben realizar N solicitudes HTTP para incrustar N textos.

#### 2. Servicio de Incorporación de Documentos

**Archivo:** `trustgraph-flow/trustgraph/embeddings/document_embeddings/embeddings.py`

Procesa fragmentos de documentos uno a la vez:

```python
async def on_message(self, msg, consumer, flow):
    v = msg.value()

    # Single chunk per request
    resp = await flow("embeddings-request").request(
        EmbeddingsRequest(text=v.chunk)
    )
    vectors = resp.vectors
```

**Impacto:** Cada fragmento de documento requiere una llamada de incrustación separada. Un documento con 100 fragmentos = 100 solicitudes de incrustación.

#### 3. Servicio de Incrustaciones de Grafos

**Archivo:** `trustgraph-flow/trustgraph/embeddings/graph_embeddings/embeddings.py`

Recorre las entidades e incrusta cada una de forma secuencial:

```python
async def on_message(self, msg, consumer, flow):
    for entity in v.entities:
        # Serial embedding - one entity at a time
        vectors = await flow("embeddings-request").embed(
            text=entity.context
        )
        entities.append(EntityEmbeddings(
            entity=entity.entity,
            vectors=vectors,
            chunk_id=entity.chunk_id,
        ))
```

**Impacto:** Un mensaje con 50 entidades = 50 solicitudes de incrustación serial. Esto es un cuello de botella importante durante la construcción del grafo de conocimiento.

#### 4. Servicio de Incrustaciones de Filas

**Archivo:** `trustgraph-flow/trustgraph/embeddings/row_embeddings/embeddings.py`

Itera sobre textos únicos e incrusta cada uno de forma serial:

```python
async def on_message(self, msg, consumer, flow):
    for text, (index_name, index_value) in texts_to_embed.items():
        # Serial embedding - one text at a time
        vectors = await flow("embeddings-request").embed(text=text)

        embeddings_list.append(RowIndexEmbedding(
            index_name=index_name,
            index_value=index_value,
            text=text,
            vectors=vectors
        ))
```

**Impacto:** Procesar una tabla con 100 valores indexados únicos = 100 solicitudes de incrustación seriales.

#### 5. EmbeddingsClient (Cliente Base)

**Archivo:** `trustgraph-base/trustgraph/base/embeddings_client.py`

El cliente utilizado por todos los procesadores de flujo solo admite la incrustación de texto único:

```python
class EmbeddingsClient(RequestResponse):
    async def embed(self, text, timeout=30):
        resp = await self.request(
            EmbeddingsRequest(text=text),  # Single text
            timeout=timeout
        )
        return resp.vectors
```

**Impacto:** Todos los clientes que utilizan esta herramienta están limitados a operaciones de texto único.

#### 6. Herramientas de Línea de Comandos

**Archivo:** `trustgraph-cli/trustgraph/cli/invoke_embeddings.py`

La herramienta de la línea de comandos acepta un único argumento de texto:

```python
def query(url, flow_id, text, token=None):
    result = flow.embeddings(text=text)  # Single text
    vectors = result.get("vectors", [])
```

**Impacto:** Los usuarios no pueden realizar incrustaciones por lotes desde la línea de comandos. El procesamiento de un archivo de textos requiere N invocaciones.

#### 7. SDK de Python

El SDK de Python proporciona dos clases de cliente para interactuar con los servicios de TrustGraph. Ambas solo admiten la incrustación de un solo texto.

**Archivo:** `trustgraph-base/trustgraph/api/flow.py`

```python
class FlowInstance:
    def embeddings(self, text):
        """Get embeddings for a single text"""
        input = {"text": text}
        return self.request("service/embeddings", input)["vectors"]
```

**Archivo:** `trustgraph-base/trustgraph/api/socket_client.py`

```python
class SocketFlowInstance:
    def embeddings(self, text: str, **kwargs: Any) -> Dict[str, Any]:
        """Get embeddings for a single text via WebSocket"""
        request = {"text": text}
        return self.client._send_request_sync(
            "embeddings", self.flow_id, request, False
        )
```

**Impacto:** Los desarrolladores de Python que utilizan el SDK deben iterar sobre los textos y realizar N llamadas de API separadas. No existe soporte para la inserción por lotes para los usuarios del SDK.

### Impacto en el rendimiento

Para la ingestión típica de documentos (1000 fragmentos de texto):
**Actual:** 1000 solicitudes separadas, 1000 llamadas de inferencia de modelos.
**Por lotes (batch_size=32):** 32 solicitudes, 32 llamadas de inferencia de modelos (reducción del 96.8%).

Para la inserción de gráficos (mensaje con 50 entidades):
**Actual:** 50 llamadas `await` secuenciales, ~5-10 segundos.
**Por lotes:** 1-2 llamadas por lotes, ~0.5-1 segundo (mejora de 5-10 veces).

FastEmbed y bibliotecas similares logran una escalabilidad de rendimiento cercana a la lineal con el tamaño del lote hasta los límites del hardware (típicamente 32-128 textos por lote).

## Diseño técnico

### Arquitectura

La optimización del procesamiento por lotes de inserciones requiere cambios en los siguientes componentes:

#### 1. **Mejora del esquema**
   Extender `EmbeddingsRequest` para admitir múltiples textos.
   Extender `EmbeddingsResponse` para devolver múltiples conjuntos de vectores.
   Mantener la compatibilidad con versiones anteriores con solicitudes de un solo texto.

   Módulo: `trustgraph-base/trustgraph/schema/services/llm.py`

#### 2. **Mejora del servicio base**
   Actualizar `EmbeddingsService` para manejar solicitudes por lotes.
   Agregar configuración del tamaño del lote.
   Implementar el manejo de solicitudes con conocimiento del lote.

   Módulo: `trustgraph-base/trustgraph/base/embeddings_service.py`

#### 3. **Actualizaciones del procesador del proveedor**
   Actualizar el procesador FastEmbed para pasar el lote completo a `embed()`.
   Actualizar el procesador de Ollama para manejar lotes (si es compatible).
   Agregar procesamiento secuencial de respaldo para los proveedores que no admiten lotes.

   Módulos:
   `trustgraph-flow/trustgraph/embeddings/fastembed/processor.py`
   `trustgraph-flow/trustgraph/embeddings/ollama/processor.py`

#### 4. **Mejora del cliente**
   Agregar un método de inserción por lotes a `EmbeddingsClient`.
   Admitir tanto API individuales como por lotes.
   Agregar inserción automática por lotes para grandes entradas.

   Módulo: `trustgraph-base/trustgraph/base/embeddings_client.py`

#### 5. **Actualizaciones del llamador: Procesadores de flujo**
   Actualizar `graph_embeddings` para agrupar los contextos de las entidades.
   Actualizar `row_embeddings` para agrupar los textos del índice.
   Actualizar `document_embeddings` si el agrupamiento de mensajes es factible.

   Módulos:
   `trustgraph-flow/trustgraph/embeddings/graph_embeddings/embeddings.py`
   `trustgraph-flow/trustgraph/embeddings/row_embeddings/embeddings.py`
   `trustgraph-flow/trustgraph/embeddings/document_embeddings/embeddings.py`

#### 6. **Mejora de la puerta de enlace de API**
   Agregar un punto final de inserción por lotes.
   Admitir una matriz de textos en el cuerpo de la solicitud.

   Módulo: `trustgraph-flow/trustgraph/gateway/dispatch/embeddings.py`

#### 7. **Mejora de la herramienta de la línea de comandos**
   Agregar soporte para múltiples textos o entrada de archivos.
   Agregar un parámetro de tamaño de lote.

   Módulo: `trustgraph-cli/trustgraph/cli/invoke_embeddings.py`

#### 8. **Mejora del SDK de Python**
   Agregar el método `embeddings_batch()` a `FlowInstance`.
   Agregar el método `embeddings_batch()` a `SocketFlowInstance`.
   Admitir tanto API individuales como por lotes para los usuarios del SDK.

   Módulos:
   `trustgraph-base/trustgraph/api/flow.py`
   `trustgraph-base/trustgraph/api/socket_client.py`

### Modelos de datos

#### EmbeddingsRequest

```python
@dataclass
class EmbeddingsRequest:
    texts: list[str] = field(default_factory=list)
```

Uso:
Texto único: `EmbeddingsRequest(texts=["hello world"])`
Lote: `EmbeddingsRequest(texts=["text1", "text2", "text3"])`

#### EmbeddingsResponse

```python
@dataclass
class EmbeddingsResponse:
    error: Error | None = None
    vectors: list[list[list[float]]] = field(default_factory=list)
```

Estructura de la respuesta:
`vectors[i]` contiene el conjunto de vectores para `texts[i]`
Cada conjunto de vectores es `list[list[float]]` (los modelos pueden devolver múltiples vectores por texto)
Ejemplo: 3 textos → `vectors` tiene 3 entradas, cada una conteniendo los incrustados de ese texto

### APIs

#### EmbeddingsClient

```python
class EmbeddingsClient(RequestResponse):
    async def embed(
        self,
        texts: list[str],
        timeout: float = 300,
    ) -> list[list[list[float]]]:
        """
        Embed one or more texts in a single request.

        Args:
            texts: List of texts to embed
            timeout: Timeout for the operation

        Returns:
            List of vector sets, one per input text
        """
        resp = await self.request(
            EmbeddingsRequest(texts=texts),
            timeout=timeout
        )
        if resp.error:
            raise RuntimeError(resp.error.message)
        return resp.vectors
```

#### Punto final de incrustaciones de la API Gateway

Punto final actualizado que admite incrustaciones individuales o por lotes:

```
POST /api/v1/embeddings
Content-Type: application/json

{
    "texts": ["text1", "text2", "text3"],
    "flow_id": "default"
}

Response:
{
    "vectors": [
        [[0.1, 0.2, ...]],
        [[0.3, 0.4, ...]],
        [[0.5, 0.6, ...]]
    ]
}
```

### Detalles de implementación

#### Fase 1: Cambios en el esquema

**EmbeddingsRequest:**
```python
@dataclass
class EmbeddingsRequest:
    texts: list[str] = field(default_factory=list)
```

**Respuesta de Inserción:**
```python
@dataclass
class EmbeddingsResponse:
    error: Error | None = None
    vectors: list[list[list[float]]] = field(default_factory=list)
```

**Actualizaciones en EmbeddingsService.on_request:**
```python
async def on_request(self, msg, consumer, flow):
    request = msg.value()
    id = msg.properties()["id"]
    model = flow("model")

    vectors = await self.on_embeddings(request.texts, model=model)
    response = EmbeddingsResponse(error=None, vectors=vectors)

    await flow("response").send(response, properties={"id": id})
```

#### Fase 2: Actualización del Procesador FastEmbed

**Actual (Ineficiente):**
```python
async def on_embeddings(self, text, model=None):
    use_model = model or self.default_model
    self._load_model(use_model)
    vecs = self.embeddings.embed([text])  # Batch of 1
    return [v.tolist() for v in vecs]
```

**Actualizado:**
```python
async def on_embeddings(self, texts: list[str], model=None):
    """Embed texts - processes all texts in single model call"""
    if not texts:
        return []

    use_model = model or self.default_model
    self._load_model(use_model)

    # FastEmbed handles the full batch efficiently
    all_vecs = list(self.embeddings.embed(texts))

    # Return list of vector sets, one per input text
    return [[v.tolist()] for v in all_vecs]
```

#### Fase 3: Actualización del Servicio de Inserción de Gráficos

**Actual (Serial):**
```python
async def on_message(self, msg, consumer, flow):
    entities = []
    for entity in v.entities:
        vectors = await flow("embeddings-request").embed(text=entity.context)
        entities.append(EntityEmbeddings(...))
```

**Actualizado (Lote):**
```python
async def on_message(self, msg, consumer, flow):
    # Collect all contexts
    contexts = [entity.context for entity in v.entities]

    # Single batch embedding call
    all_vectors = await flow("embeddings-request").embed(texts=contexts)

    # Pair results with entities
    entities = [
        EntityEmbeddings(
            entity=entity.entity,
            vectors=vectors[0],  # First vector from the set
            chunk_id=entity.chunk_id,
        )
        for entity, vectors in zip(v.entities, all_vectors)
    ]
```

#### Fase 4: Actualización del Servicio de Incrustación de Filas

**Actual (Serial):**
```python
for text, (index_name, index_value) in texts_to_embed.items():
    vectors = await flow("embeddings-request").embed(text=text)
    embeddings_list.append(RowIndexEmbedding(...))
```

**Actualizado (Lote):**
```python
# Collect texts and metadata
texts = list(texts_to_embed.keys())
metadata = list(texts_to_embed.values())

# Single batch embedding call
all_vectors = await flow("embeddings-request").embed(texts=texts)

# Pair results
embeddings_list = [
    RowIndexEmbedding(
        index_name=meta[0],
        index_value=meta[1],
        text=text,
        vectors=vectors[0]  # First vector from the set
    )
    for text, meta, vectors in zip(texts, metadata, all_vectors)
]
```

#### Fase 5: Mejora de la Herramienta de Línea de Comandos (CLI)

**CLI Actualizada:**
```python
def main():
    parser = argparse.ArgumentParser(...)

    parser.add_argument(
        'text',
        nargs='*',  # Zero or more texts
        help='Text(s) to convert to embedding vectors',
    )

    parser.add_argument(
        '-f', '--file',
        help='File containing texts (one per line)',
    )

    parser.add_argument(
        '--batch-size',
        type=int,
        default=32,
        help='Batch size for processing (default: 32)',
    )
```

Uso:
```bash
# Single text (existing)
tg-invoke-embeddings "hello world"

# Multiple texts
tg-invoke-embeddings "text one" "text two" "text three"

# From file
tg-invoke-embeddings -f texts.txt --batch-size 64
```

#### Fase 6: Mejora del SDK de Python

**FlowInstance (cliente HTTP):**

```python
class FlowInstance:
    def embeddings(self, texts: list[str]) -> list[list[list[float]]]:
        """
        Get embeddings for one or more texts.

        Args:
            texts: List of texts to embed

        Returns:
            List of vector sets, one per input text
        """
        input = {"texts": texts}
        return self.request("service/embeddings", input)["vectors"]
```

**SocketFlowInstance (cliente WebSocket):**

```python
class SocketFlowInstance:
    def embeddings(self, texts: list[str], **kwargs: Any) -> list[list[list[float]]]:
        """
        Get embeddings for one or more texts via WebSocket.

        Args:
            texts: List of texts to embed

        Returns:
            List of vector sets, one per input text
        """
        request = {"texts": texts}
        response = self.client._send_request_sync(
            "embeddings", self.flow_id, request, False
        )
        return response["vectors"]
```

**Ejemplos de uso del SDK:**

```python
# Single text
vectors = flow.embeddings(["hello world"])
print(f"Dimensions: {len(vectors[0][0])}")

# Batch embedding
texts = ["text one", "text two", "text three"]
all_vectors = flow.embeddings(texts)

# Process results
for text, vecs in zip(texts, all_vectors):
    print(f"{text}: {len(vecs[0])} dimensions")
```

## Consideraciones de seguridad

**Límites de tamaño de la solicitud**: Aplicar un tamaño máximo de lote para evitar el agotamiento de recursos.
**Manejo de tiempos de espera**: Ajustar los tiempos de espera de manera adecuada para el tamaño del lote.
**Límites de memoria**: Monitorear el uso de memoria para lotes grandes.
**Validación de entrada**: Validar todos los textos en el lote antes de procesarlos.

## Consideraciones de rendimiento

### Mejoras esperadas

**Rendimiento:**
Texto único: ~10-50 textos/segundo (dependiendo del modelo)
Lote (tamaño 32): ~200-500 textos/segundo (mejora de 5 a 10 veces)

**Latencia por texto:**
Texto único: 50-200 ms por texto
Lote (tamaño 32): 5-20 ms por texto (promedio)

**Mejoras específicas del servicio:**

| Servicio | Actual | En lote | Mejora |
|---------|---------|---------|-------------|
| Incrustaciones de grafos (50 entidades) | 5-10 s | 0.5-1 s | 5-10 veces |
| Incrustaciones de filas (100 textos) | 10-20 s | 1-2 s | 5-10 veces |
| Ingestión de documentos (1000 fragmentos) | 100-200 s | 10-30 s | 5-10 veces |

### Parámetros de configuración

```python
# Recommended defaults
DEFAULT_BATCH_SIZE = 32
MAX_BATCH_SIZE = 128
BATCH_TIMEOUT_MULTIPLIER = 2.0
```

## Estrategia de Pruebas

### Pruebas Unitarias
Inserción de texto única (compatibilidad con versiones anteriores)
Manejo de lotes vacíos
Aplicación del tamaño máximo del lote
Manejo de errores para fallas parciales del lote

### Pruebas de Integración
Inserción de lote de extremo a extremo a través de Pulsar
Procesamiento por lotes del servicio de inserción de gráficos
Procesamiento por lotes del servicio de inserción de filas
Punto final de lote de la puerta de enlace de la API

### Pruebas de Rendimiento
Comparación de rendimiento de inserción única frente a inserción por lotes
Uso de memoria con varios tamaños de lote
Análisis de la distribución de la latencia

## Plan de Migración

Esta es una versión que introduce cambios importantes. Todas las fases se implementan juntas.

### Fase 1: Cambios en el Esquema
Reemplazar `text: str` con `texts: list[str]` en EmbeddingsRequest
Cambiar el tipo de `vectors` a `list[list[list[float]]]` en EmbeddingsResponse

### Fase 2: Actualizaciones del Procesador
Actualizar la firma de `on_embeddings` en los procesadores FastEmbed y Ollama
Procesar el lote completo en una única llamada al modelo

### Fase 3: Actualizaciones del Cliente
Actualizar `EmbeddingsClient.embed()` para que acepte `texts: list[str]`

### Fase 4: Actualizaciones del Llamador
Actualizar graph_embeddings para procesar contextos de entidades por lotes
Actualizar row_embeddings para procesar textos de índice por lotes
Actualizar document_embeddings para usar el nuevo esquema
Actualizar la herramienta de línea de comandos

### Fase 5: Puerta de Enlace de la API
Actualizar el punto final de inserción para el nuevo esquema

### Fase 6: SDK de Python
Actualizar la firma de `FlowInstance.embeddings()`
Actualizar la firma de `SocketFlowInstance.embeddings()`

## Preguntas Abiertas

**Inserción de Lotes Grandes en Streaming**: ¿Debemos admitir la transmisión de resultados para lotes muy grandes (>100 textos)?
**Límites Específicos del Proveedor**: ¿Cómo debemos manejar los proveedores con tamaños máximos de lote diferentes?
**Manejo de Fallas Parciales**: Si un texto en un lote falla, ¿deberíamos fallar todo el lote o devolver resultados parciales?
**Inserción por Lotes de Documentos**: ¿Debemos realizar la inserción por lotes en varios mensajes de Chunk o mantener el procesamiento por mensaje?

## Referencias

[Documentación de FastEmbed](https://github.com/qdrant/fastembed)
[API de Inserción de Ollama](https://github.com/ollama/ollama)
[Implementación del Servicio de Inserción](trustgraph-base/trustgraph/base/embeddings_service.py)
[Optimización del Rendimiento de GraphRAG](graphrag-performance-optimization.md)
