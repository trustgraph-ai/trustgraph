---
layout: default
title: "Especificación Técnica de Carga de Documentos Grandes"
parent: "Spanish (Beta)"
---

# Especificación Técnica de Carga de Documentos Grandes

> **Beta Translation:** This document was translated via Machine Learning and as such may not be 100% accurate. All non-English languages are currently classified as Beta.

## Resumen

Esta especificación aborda los problemas de escalabilidad y la experiencia del usuario al cargar
documentos grandes en TrustGraph. La arquitectura actual trata la carga de documentos
como una operación atómica única, lo que provoca una alta carga de memoria en varios puntos del
proceso y no proporciona ninguna indicación de progreso ni opciones de recuperación a los usuarios.

Esta implementación tiene como objetivo los siguientes casos de uso:

1. **Procesamiento de PDF Grandes**: Cargar y procesar archivos PDF de varios cientos de megabytes
   sin agotar la memoria.
2. **Cargas Reanudables**: Permitir que las cargas interrumpidas continúen desde donde
   se detuvieron en lugar de reiniciarse.
<<<<<<< HEAD
3. **Indicación de Progreso**: Proporcionar a los usuarios visibilidad en tiempo real del
=======
3. **Retroalimentación de Progreso**: Proporcionar a los usuarios visibilidad en tiempo real del
>>>>>>> 82edf2d (New md files from RunPod)
   progreso de la carga y el procesamiento.
4. **Procesamiento Eficiente en Memoria**: Procesar documentos de forma continua
   sin mantener archivos completos en la memoria.

## Objetivos

<<<<<<< HEAD
**Carga Incremental**: Soporte para la carga de documentos en fragmentos a través de REST y WebSocket.
**Transferencias Reanudables**: Permitir la recuperación de cargas interrumpidas.
**Visibilidad del Progreso**: Proporcionar retroalimentación de carga/procesamiento a los clientes.
**Eficiencia de Memoria**: Eliminar el almacenamiento en búfer de documentos completos en todo el proceso.
**Compatibilidad con Versiones Anteriores**: Los flujos de trabajo existentes para documentos pequeños continúan sin cambios.
**Procesamiento por Flujo Continuo**: La decodificación de PDF y el fragmentado de texto operan en flujos.
=======
**Carga Incremental**: Soporte para la carga de documentos por partes a través de REST y WebSocket.
**Transferencias Reanudables**: Permitir la recuperación de cargas interrumpidas.
**Visibilidad del Progreso**: Proporcionar retroalimentación de progreso de carga/procesamiento a los clientes.
**Eficiencia de Memoria**: Eliminar el almacenamiento en búfer de documentos completos en todo el proceso.
**Compatibilidad con Versiones Anteriores**: Los flujos de trabajo existentes para documentos pequeños continúan sin cambios.
**Procesamiento por Transmisión**: La decodificación de PDF y el fragmentado de texto operan en flujos.
>>>>>>> 82edf2d (New md files from RunPod)

## Antecedentes

### Arquitectura Actual

El flujo de envío de documentos sigue la siguiente ruta:

1. El **cliente** envía el documento a través de REST (`POST /api/v1/librarian`) o WebSocket.
2. La **API Gateway** recibe la solicitud completa con el contenido del documento codificado en base64.
3. El **LibrarianRequestor** traduce la solicitud a un mensaje Pulsar.
4. El **Librarian Service** recibe el mensaje, decodifica el documento en la memoria.
5. **BlobStore** carga el documento en Garage/S3.
6. **Cassandra** almacena los metadatos con la referencia del objeto.
<<<<<<< HEAD
7. Para el procesamiento: el documento se recupera de S3, se decodifica y se divide en fragmentos, todo en la memoria.
=======
7. Para el procesamiento: el documento se recupera de S3, se decodifica y se divide en partes, todo en la memoria.
>>>>>>> 82edf2d (New md files from RunPod)

Archivos clave:
Punto de entrada REST/WebSocket: `trustgraph-flow/trustgraph/gateway/service.py`
Núcleo de Librarian: `trustgraph-flow/trustgraph/librarian/librarian.py`
Almacenamiento de blobs: `trustgraph-flow/trustgraph/librarian/blob_store.py`
Tablas de Cassandra: `trustgraph-flow/trustgraph/tables/library.py`
Esquema de la API: `trustgraph-base/trustgraph/schema/services/library.py`

### Limitaciones Actuales

<<<<<<< HEAD
El diseño actual tiene varios problemas de memoria y experiencia de usuario que se agravan:
=======
El diseño actual tiene varios problemas de memoria y experiencia de usuario:
>>>>>>> 82edf2d (New md files from RunPod)

1. **Operación de Carga Atómica**: Se debe transmitir todo el documento en una
   solicitud única. Los documentos grandes requieren solicitudes de larga duración sin
   indicación de progreso ni mecanismo de reintento si la conexión falla.

2. **Diseño de la API**: Tanto las API REST como WebSocket esperan el documento
   completo en un solo mensaje. El esquema (`LibrarianRequest`) tiene un campo `content`
   que contiene todo el documento codificado en base64.

3. **Memoria del Librarian**: El servicio librarian decodifica todo el documento
<<<<<<< HEAD
   en la memoria antes de cargarlo en S3. Para un PDF de 500 MB, esto significa mantener
   500 MB+ en la memoria del proceso.

4. **Memoria del Decodificador de PDF**: Cuando comienza el procesamiento, el decodificador de PDF carga
   todo el PDF en la memoria para extraer el texto. Las bibliotecas como PyPDF y similares
   típicamente requieren acceso a todo el documento.
=======
   en la memoria antes de cargarlo en S3. Para un archivo PDF de 500 MB, esto significa mantener
   500 MB+ en la memoria del proceso.

4. **Memoria del Decodificador de PDF**: Cuando comienza el procesamiento, el decodificador de PDF carga
   todo el PDF en la memoria para extraer el texto. Las bibliotecas como PyPDF normalmente
   requieren acceso a todo el documento.
>>>>>>> 82edf2d (New md files from RunPod)

5. **Memoria del Fragmentador**: El fragmentador de texto recibe todo el texto extraído
   y lo mantiene en la memoria mientras produce fragmentos.

**Ejemplo de Impacto en la Memoria** (PDF de 500 MB):
Gateway: ~700 MB (sobrecarga de codificación base64)
Librarian: ~500 MB (bytes decodificados)
Decodificador de PDF: ~500 MB + búferes de extracción
Fragmentador: texto extraído (variable, potencialmente 100 MB+)

El pico total de memoria puede exceder los 2 GB para un solo documento grande.

## Diseño Técnico

### Principios de Diseño

1. **Fachada de la API**: Toda la interacción del cliente pasa por la API de librarian. Los clientes
   no tienen acceso directo ni conocimiento del almacenamiento subyacente de S3/Garage.

2. **Carga Multipart de S3**: Utilice la carga multipart estándar de S3.
   Esto está ampliamente soportado en sistemas compatibles con S3 (AWS S3, MinIO, Garage,
   Ceph, DigitalOcean Spaces, Backblaze B2, etc.), lo que garantiza la portabilidad.

3. **Completación Atómica**: Las cargas multipart de S3 son inherentemente atómicas: las partes cargadas
<<<<<<< HEAD
   son invisibles hasta que se llama a `CompleteMultipartUpload`. No se necesitan archivos temporales ni
=======
   no son visibles hasta que se llama a `CompleteMultipartUpload`. No se necesitan archivos temporales ni
>>>>>>> 82edf2d (New md files from RunPod)
   operaciones de renombrado.

4. **Estado Rastreable**: Las sesiones de carga se rastrean en Cassandra, lo que proporciona
   visibilidad de las cargas incompletas y permite la capacidad de reanudación.

<<<<<<< HEAD
### Flujo de Carga Fragmentada
=======
### Flujo de Carga por Partes
>>>>>>> 82edf2d (New md files from RunPod)

```
Client                    Librarian API                   S3/Garage
  │                            │                              │
  │── begin-upload ───────────►│                              │
  │   (metadata, size)         │── CreateMultipartUpload ────►│
  │                            │◄── s3_upload_id ─────────────│
  │◄── upload_id ──────────────│   (store session in          │
  │                            │    Cassandra)                │
  │                            │                              │
  │── upload-chunk ───────────►│                              │
  │   (upload_id, index, data) │── UploadPart ───────────────►│
  │                            │◄── etag ─────────────────────│
  │◄── ack + progress ─────────│   (store etag in session)    │
  │         ⋮                  │         ⋮                    │
  │   (repeat for all chunks)  │                              │
  │                            │                              │
  │── complete-upload ────────►│                              │
  │   (upload_id)              │── CompleteMultipartUpload ──►│
  │                            │   (parts coalesced by S3)    │
  │                            │── store doc metadata ───────►│ Cassandra
  │◄── document_id ────────────│   (delete session)           │
```

El cliente nunca interactúa directamente con S3. El "librarian" (bibliotecario) traduce entre
nuestra API de carga por partes y las operaciones multipart de S3 internamente.

### Operaciones de la API del "Librarian"

#### `begin-upload`

Inicializar una sesión de carga por partes.

Solicitud:
```json
{
  "operation": "begin-upload",
  "document-metadata": {
    "id": "doc-123",
    "kind": "application/pdf",
    "title": "Large Document",
    "user": "user-id",
    "tags": ["tag1", "tag2"]
  },
  "total-size": 524288000,
  "chunk-size": 5242880
}
```

Respuesta:
```json
{
  "upload-id": "upload-abc-123",
  "chunk-size": 5242880,
  "total-chunks": 100
}
```

El bibliotecario:
<<<<<<< HEAD
1. Genera un `upload_id` y un `object_id` únicos (UUID para almacenamiento de blobs).
=======
1. Genera un `upload_id` y un `object_id` únicos (UUID para el almacenamiento de blobs).
>>>>>>> 82edf2d (New md files from RunPod)
2. Llama a S3 `CreateMultipartUpload`, recibe `s3_upload_id`.
3. Crea un registro de sesión en Cassandra.
4. Devuelve `upload_id` al cliente.

#### `upload-chunk`

<<<<<<< HEAD
Cargar un único fragmento.
=======
Carga un único fragmento.
>>>>>>> 82edf2d (New md files from RunPod)

Solicitud:
```json
{
  "operation": "upload-chunk",
  "upload-id": "upload-abc-123",
  "chunk-index": 0,
  "content": "<base64-encoded-chunk>"
}
```

Respuesta:
```json
{
  "upload-id": "upload-abc-123",
  "chunk-index": 0,
  "chunks-received": 1,
  "total-chunks": 100,
  "bytes-received": 5242880,
  "total-bytes": 524288000
}
```

El bibliotecario:
1. Busca la sesión por `upload_id`
2. Valida la propiedad (el usuario debe coincidir con el creador de la sesión)
3. Llama a S3 `UploadPart` con los datos del fragmento, recibe `etag`
4. Actualiza el registro de la sesión con el índice del fragmento y la etiqueta (etag)
5. Devuelve el progreso al cliente

<<<<<<< HEAD
Los fragmentos fallidos se pueden reintentar; simplemente envía el mismo `chunk-index` nuevamente.
=======
Los fragmentos fallidos se pueden reintentar: simplemente envía el mismo `chunk-index` nuevamente.
>>>>>>> 82edf2d (New md files from RunPod)

#### `complete-upload`

Finaliza la carga y crea el documento.

Solicitud:
```json
{
  "operation": "complete-upload",
  "upload-id": "upload-abc-123"
}
```

Respuesta:
```json
{
  "document-id": "doc-123",
  "object-id": "550e8400-e29b-41d4-a716-446655440000"
}
```

El bibliotecario:
1. Busca la sesión, verifica que se hayan recibido todos los fragmentos.
2. Llama a S3 `CompleteMultipartUpload` con los ETags de las partes (S3 combina las partes
<<<<<<< HEAD
   internamente, sin costo de memoria para el bibliotecario).
=======
   internamente, lo que no tiene costo de memoria para el bibliotecario).
>>>>>>> 82edf2d (New md files from RunPod)
3. Crea un registro de documento en Cassandra con metadatos y referencia al objeto.
4. Elimina el registro de la sesión de carga.
5. Devuelve el ID del documento al cliente.

#### `abort-upload`

Cancelar una carga en curso.

Solicitud:
```json
{
  "operation": "abort-upload",
  "upload-id": "upload-abc-123"
}
```

El bibliotecario:
1. Llama a S3 `AbortMultipartUpload` para limpiar partes.
2. Elimina el registro de sesión de Cassandra.

#### `get-upload-status`

Consulta el estado de una carga (para la capacidad de reanudación).

Solicitud:
```json
{
  "operation": "get-upload-status",
  "upload-id": "upload-abc-123"
}
```

Respuesta:
```json
{
  "upload-id": "upload-abc-123",
  "state": "in-progress",
  "chunks-received": [0, 1, 2, 5, 6],
  "missing-chunks": [3, 4, 7, 8],
  "total-chunks": 100,
  "bytes-received": 36700160,
  "total-bytes": 524288000
}
```

#### `list-uploads`

Listar las subidas incompletas para un usuario.

Solicitud:
```json
{
  "operation": "list-uploads"
}
```

Respuesta:
```json
{
  "uploads": [
    {
      "upload-id": "upload-abc-123",
      "document-metadata": { "title": "Large Document", ... },
      "progress": { "chunks-received": 43, "total-chunks": 100 },
      "created-at": "2024-01-15T10:30:00Z"
    }
  ]
}
```

### Almacenamiento de Sesión de Carga

Realizar un seguimiento de las cargas en curso en Cassandra:

```sql
CREATE TABLE upload_session (
    upload_id text PRIMARY KEY,
    user text,
    document_id text,
    document_metadata text,      -- JSON: title, kind, tags, comments, etc.
    s3_upload_id text,           -- internal, for S3 operations
    object_id uuid,              -- target blob ID
    total_size bigint,
    chunk_size int,
    total_chunks int,
    chunks_received map<int, text>,  -- chunk_index → etag
    created_at timestamp,
    updated_at timestamp
) WITH default_time_to_live = 86400;  -- 24 hour TTL

CREATE INDEX upload_session_user ON upload_session (user);
```

**Comportamiento de TTL:**
Las sesiones expiran después de 24 horas si no se completan.
Cuando expira el TTL de Cassandra, se elimina el registro de la sesión.
Las partes de S3 huérfanas se eliminan mediante la política de ciclo de vida de S3 (configurar en el bucket).

### Manejo de errores y atomicidad

**Fallo en la carga de fragmentos:**
<<<<<<< HEAD
El cliente reintenta el fragmento fallido (mismo `upload_id` y `chunk-index`).
=======
El cliente reintenta el fragmento fallido (con el mismo `upload_id` y `chunk-index`).
>>>>>>> 82edf2d (New md files from RunPod)
`UploadPart` de S3 es idempotente para el mismo número de parte.
La sesión realiza un seguimiento de qué fragmentos tuvieron éxito.

**Desconexión del cliente durante la carga:**
La sesión permanece en Cassandra con los fragmentos recibidos registrados.
El cliente puede llamar a `get-upload-status` para ver qué falta.
Reanudar cargando solo los fragmentos faltantes, luego `complete-upload`.

**Fallo en la carga completa:**
`CompleteMultipartUpload` de S3 es atómico: o tiene éxito por completo o falla.
En caso de fallo, las partes permanecen y el cliente puede reintentar `complete-upload`.
Nunca se muestra un documento parcial.

**Vencimiento de la sesión:**
El TTL de Cassandra elimina el registro de la sesión después de 24 horas.
<<<<<<< HEAD
La política de ciclo de vida del bucket de S3 limpia las cargas multipartes incompletas.
No se requiere limpieza manual.

### Atomicidad de las cargas multipartes de S3

Las cargas multipartes de S3 proporcionan atomicidad integrada:

1. **Las partes son invisibles:** Las partes cargadas no se pueden acceder como objetos.
   Solo existen como partes de una carga multipartes incompleta.
=======
La política de ciclo de vida del bucket de S3 limpia las cargas multipart incompletas.
No se requiere limpieza manual.

### Atomicidad de las cargas multipart de S3

Las cargas multipart de S3 proporcionan atomicidad integrada:

1. **Las partes son invisibles:** Las partes cargadas no se pueden acceder como objetos.
   Solo existen como partes de una carga multipart incompleta.
>>>>>>> 82edf2d (New md files from RunPod)

2. **Finalización atómica:** `CompleteMultipartUpload` tiene éxito (el objeto
   aparece de forma atómica) o falla (no se crea ningún objeto). No hay estado parcial.

<<<<<<< HEAD
3. **No se necesita renombrar:** La clave de objeto final se especifica en
   el momento de `CreateMultipartUpload`. Las partes se combinan directamente en esa clave.
=======
3. **No se necesita renombrar:** La clave del objeto final se especifica en
   el momento de `CreateMultipartUpload`. Las partes se combinan directamente con esa clave.
>>>>>>> 82edf2d (New md files from RunPod)

4. **Combinación del lado del servidor:** S3 combina las partes internamente. El bibliotecario
   nunca lee las partes de nuevo: cero sobrecarga de memoria independientemente del tamaño del documento.

### Extensiones de BlobStore

**Archivo:** `trustgraph-flow/trustgraph/librarian/blob_store.py`

<<<<<<< HEAD
Agregar métodos de carga multipartes:
=======
Agregar métodos de carga multipart:
>>>>>>> 82edf2d (New md files from RunPod)

```python
class BlobStore:
    # Existing methods...

    def create_multipart_upload(self, object_id: UUID, kind: str) -> str:
        """Initialize multipart upload, return s3_upload_id."""
        # minio client: create_multipart_upload()

    def upload_part(
        self, object_id: UUID, s3_upload_id: str,
        part_number: int, data: bytes
    ) -> str:
        """Upload a single part, return etag."""
        # minio client: upload_part()
        # Note: S3 part numbers are 1-indexed

    def complete_multipart_upload(
        self, object_id: UUID, s3_upload_id: str,
        parts: List[Tuple[int, str]]  # [(part_number, etag), ...]
    ) -> None:
        """Finalize multipart upload."""
        # minio client: complete_multipart_upload()

    def abort_multipart_upload(
        self, object_id: UUID, s3_upload_id: str
    ) -> None:
        """Cancel multipart upload, clean up parts."""
        # minio client: abort_multipart_upload()
```

### Consideraciones sobre el tamaño de los bloques

**Mínimo de S3**: 5 MB por parte (excepto la última parte)
**Máximo de S3**: 10,000 partes por carga
**Valor predeterminado práctico**: bloques de 5 MB
  Documento de 500 MB = 100 bloques
  Documento de 5 GB = 1000 bloques
**Granularidad del progreso**: Bloques más pequeños = actualizaciones de progreso más detalladas
**Eficiencia de la red**: Bloques más grandes = menos viajes de ida y vuelta

El tamaño del bloque podría ser configurable por el cliente dentro de un rango (5 MB - 100 MB).

### Procesamiento de documentos: Recuperación en streaming

El flujo de carga se ocupa de almacenar documentos de manera eficiente. El flujo de procesamiento se ocupa de extraer y dividir documentos sin cargarlos
por completo en la memoria.


#### Principio de diseño: Identificador, no contenido

Actualmente, cuando se inicia el procesamiento, el contenido del documento fluye a través de mensajes de Pulsar. Esto carga documentos completos en la memoria. En cambio:


Los mensajes de Pulsar solo contienen el **identificador del documento**
Los procesadores recuperan el contenido del documento directamente de la biblioteca.
La recuperación se realiza como un **flujo a un archivo temporal**
El análisis específico del documento (PDF, texto, etc.) funciona con archivos, no con búferes de memoria.

Esto mantiene a la biblioteca independiente de la estructura del documento. El análisis de PDF, la extracción de texto y otras lógicas específicas del formato permanecen en los decodificadores correspondientes.


#### Flujo de procesamiento

```
Pulsar              PDF Decoder                Librarian              S3
  │                      │                          │                  │
  │── doc-id ───────────►│                          │                  │
  │  (processing msg)    │                          │                  │
  │                      │                          │                  │
  │                      │── stream-document ──────►│                  │
  │                      │   (doc-id)               │── GetObject ────►│
  │                      │                          │                  │
  │                      │◄── chunk ────────────────│◄── stream ───────│
  │                      │   (write to temp file)   │                  │
  │                      │◄── chunk ────────────────│◄── stream ───────│
  │                      │   (append to temp file)  │                  │
  │                      │         ⋮                │         ⋮        │
  │                      │◄── EOF ──────────────────│                  │
  │                      │                          │                  │
  │                      │   ┌──────────────────────────┐              │
  │                      │   │ temp file on disk        │              │
  │                      │   │ (memory stays bounded)   │              │
  │                      │   └────────────┬─────────────┘              │
  │                      │                │                            │
  │                      │   PDF library opens file                    │
  │                      │   extract page 1 text ──►  chunker          │
  │                      │   extract page 2 text ──►  chunker          │
  │                      │         ⋮                                   │
  │                      │   close file                                │
  │                      │   delete temp file                          │
```

#### API de flujo de trabajo del bibliotecario

Agregar una operación de recuperación de documentos en flujo continuo:

**`stream-document`**

Solicitud:
```json
{
  "operation": "stream-document",
  "document-id": "doc-123"
}
```

Respuesta: Fragmentos binarios transmitidos (no una respuesta única).

Para la API REST, esto devuelve una respuesta transmitida con `Transfer-Encoding: chunked`.

Para llamadas internas de servicio a servicio (del procesador al bibliotecario), esto podría ser:
Transmisión directa de S3 a través de una URL prefirmada (si la red interna lo permite).
Respuestas fragmentadas a través del protocolo del servicio.
Un punto final de transmisión dedicado.

El requisito clave: los datos fluyen en fragmentos, nunca completamente almacenados en búfer en el bibliotecario.

#### Cambios en el decodificador de PDF

**Implementación actual** (que consume mucha memoria):

```python
def decode_pdf(document_content: bytes) -> str:
    reader = PdfReader(BytesIO(document_content))  # full doc in memory
    text = ""
    for page in reader.pages:
        text += page.extract_text()  # accumulating
    return text  # full text in memory
```

**Nueva implementación** (archivo temporal, incremental):

```python
def decode_pdf_streaming(doc_id: str, librarian_client) -> Iterator[str]:
    """Yield extracted text page by page."""

    with tempfile.NamedTemporaryFile(delete=True, suffix='.pdf') as tmp:
        # Stream document to temp file
        for chunk in librarian_client.stream_document(doc_id):
            tmp.write(chunk)
        tmp.flush()

        # Open PDF from file (not memory)
        reader = PdfReader(tmp.name)

        # Yield pages incrementally
        for page in reader.pages:
            yield page.extract_text()

        # tmp file auto-deleted on context exit
```

Perfil de memoria:
Archivo temporal en disco: tamaño del PDF (el disco es barato).
En memoria: una página de texto a la vez.
Memoria máxima: limitada, independiente del tamaño del documento.

#### Cambios en el decodificador de documentos de texto.

Para documentos de texto plano, aún más simple: no se necesita archivo temporal.

```python
def decode_text_streaming(doc_id: str, librarian_client) -> Iterator[str]:
    """Yield text in chunks as it streams from storage."""

    buffer = ""
    for chunk in librarian_client.stream_document(doc_id):
        buffer += chunk.decode('utf-8')

        # Yield complete lines/paragraphs as they arrive
        while '\n\n' in buffer:
            paragraph, buffer = buffer.split('\n\n', 1)
            yield paragraph + '\n\n'

    # Yield remaining buffer
    if buffer:
        yield buffer
```

Los documentos de texto pueden transmitirse directamente sin un archivo temporal, ya que están
estructurados linealmente.

#### Integración del Fragmentador (Chunker)

El fragmentador recibe un iterador de texto (páginas o párrafos) y produce
fragmentos de forma incremental:

```python
class StreamingChunker:
    def __init__(self, chunk_size: int, overlap: int):
        self.chunk_size = chunk_size
        self.overlap = overlap

    def process(self, text_stream: Iterator[str]) -> Iterator[str]:
        """Yield chunks as text arrives."""
        buffer = ""

        for text_segment in text_stream:
            buffer += text_segment

            while len(buffer) >= self.chunk_size:
                chunk = buffer[:self.chunk_size]
                yield chunk
                # Keep overlap for context continuity
                buffer = buffer[self.chunk_size - self.overlap:]

        # Yield remaining buffer as final chunk
        if buffer.strip():
            yield buffer
```

<<<<<<< HEAD
#### Canalización de procesamiento de extremo a extremo
=======
#### Canalización de Procesamiento de Extremo a Extremo
>>>>>>> 82edf2d (New md files from RunPod)

```python
async def process_document(doc_id: str, librarian_client, embedder):
    """Process document with bounded memory."""

    # Get document metadata to determine type
    metadata = await librarian_client.get_document_metadata(doc_id)

    # Select decoder based on document type
    if metadata.kind == 'application/pdf':
        text_stream = decode_pdf_streaming(doc_id, librarian_client)
    elif metadata.kind == 'text/plain':
        text_stream = decode_text_streaming(doc_id, librarian_client)
    else:
        raise UnsupportedDocumentType(metadata.kind)

    # Chunk incrementally
    chunker = StreamingChunker(chunk_size=1000, overlap=100)

    # Process each chunk as it's produced
    for chunk in chunker.process(text_stream):
        # Generate embeddings, store in vector DB, etc.
        embedding = await embedder.embed(chunk)
        await store_chunk(doc_id, chunk, embedding)
```

<<<<<<< HEAD
En ningún momento, se mantiene en memoria el documento completo o el texto extraído completo.
=======
En ningún momento, el documento completo o el texto extraído se mantienen en la memoria.
>>>>>>> 82edf2d (New md files from RunPod)

#### Consideraciones sobre archivos temporales

**Ubicación**: Utilice el directorio temporal del sistema (`/tmp` o equivalente). Para
implementaciones en contenedores, asegúrese de que el directorio temporal tenga suficiente espacio
y que esté en un almacenamiento rápido (no montado en red, si es posible).

**Limpieza**: Utilice administradores de contexto (`with tempfile...`) para garantizar la limpieza
incluso en caso de excepciones.

**Procesamiento concurrente**: Cada trabajo de procesamiento obtiene su propio archivo temporal.
No hay conflictos entre el procesamiento paralelo de documentos.

**Espacio en disco**: Los archivos temporales son de corta duración (duración del procesamiento). Para
un archivo PDF de 500 MB, se necesitan 500 MB de espacio temporal durante el procesamiento. El límite de tamaño podría
aplicarse en el momento de la carga si el espacio en disco es limitado.

### Interfaz de procesamiento unificada: Documentos secundarios

La extracción de PDF y el procesamiento de documentos de texto deben integrarse en la misma
canalización descendente (fragmentación → incrustaciones → almacenamiento). Para lograr esto con una interfaz "recuperación por ID" consistente, los bloques de texto extraídos se almacenan de nuevo
en el sistema de gestión de documentos como documentos secundarios.

#### Flujo de procesamiento con documentos secundarios

Después de la última línea traducida, incluir una línea final que contenga exactamente: [[__END_OF_TRANSLATION__]]
```
PDF Document                                         Text Document
     │                                                     │
     ▼                                                     │
pdf-extractor                                              │
     │                                                     │
     │ (stream PDF from librarian)                         │
     │ (extract page 1 text)                               │
     │ (store as child doc → librarian)                    │
     │ (extract page 2 text)                               │
     │ (store as child doc → librarian)                    │
     │         ⋮                                           │
     ▼                                                     ▼
[child-doc-id, child-doc-id, ...]                    [doc-id]
     │                                                     │
     └─────────────────────┬───────────────────────────────┘
                           ▼
                       chunker
                           │
                           │ (receives document ID)
                           │ (streams content from librarian)
                           │ (chunks incrementally)
                           ▼
                    [chunks → embedding → storage]
```

El componente de segmentación tiene una interfaz uniforme:
Recibir un ID de documento (a través de Pulsar)
Obtener el contenido del bibliotecario
Segmentarlo

No sabe ni le importa si el ID se refiere a:
Un documento de texto subido por un usuario
Un fragmento de texto extraído de una página de PDF
Cualquier tipo de documento futuro

#### Metadatos del Documento Hijo

Extender el esquema del documento para rastrear las relaciones padre/hijo:

```sql
-- Add columns to document table
ALTER TABLE document ADD parent_id text;
ALTER TABLE document ADD document_type text;

-- Index for finding children of a parent
CREATE INDEX document_parent ON document (parent_id);
```

**Tipos de documentos:**

| `document_type` | Descripción |
|-----------------|-------------|
| `source` | Documento subido por el usuario (PDF, texto, etc.) |
| `extracted` | Derivado de un documento fuente (por ejemplo, texto de una página PDF) |

**Campos de metadatos:**

| Campo | Documento fuente | Documento hijo extraído |
|-------|-----------------|-----------------|
| `id` | proporcionado por el usuario o generado | generado (por ejemplo, `{parent-id}-page-{n}`) |
| `parent_id` | `NULL` | ID del documento padre |
| `document_type` | `source` | `extracted` |
| `kind` | `application/pdf`, etc. | `text/plain` |
| `title` | proporcionado por el usuario | generado (por ejemplo, "Página 3 del Informe.pdf") |
| `user` | usuario autenticado | igual que el padre |

<<<<<<< HEAD
#### API de Librarian para documentos hijos

**Creación de documentos hijos** (interno, utilizado por pdf-extractor):
=======
#### API de Librarian para documentos hijo

**Creación de documentos hijo** (interno, utilizado por pdf-extractor):
>>>>>>> 82edf2d (New md files from RunPod)

```json
{
  "operation": "add-child-document",
  "parent-id": "doc-123",
  "document-metadata": {
    "id": "doc-123-page-1",
    "kind": "text/plain",
    "title": "Page 1"
  },
  "content": "<base64-encoded-text>"
}
```

Para textos pequeños extraídos (el texto típico de una página es menor a 100 KB), la carga en una sola operación es aceptable. Para extracciones de texto muy grandes, se podría utilizar la carga por bloques.

**Listado de documentos secundarios** (para depuración/administración):

**Listado de documentos secundarios** (para depuración/administración):

```json
{
  "operation": "list-children",
  "parent-id": "doc-123"
}
```

Respuesta:
```json
{
  "children": [
    { "id": "doc-123-page-1", "title": "Page 1", "kind": "text/plain" },
    { "id": "doc-123-page-2", "title": "Page 2", "kind": "text/plain" },
    ...
  ]
}
```

#### Comportamiento visible para el usuario

**`list-documents` comportamiento predeterminado:**

```sql
SELECT * FROM document WHERE user = ? AND parent_id IS NULL;
```

Solo los documentos de nivel superior (fuente) aparecen en la lista de documentos del usuario.
Los documentos secundarios se filtran de forma predeterminada.

<<<<<<< HEAD
**Opción de incluir subdocumentos** (para administradores/depuración):
=======
**Opción de incluir documentos secundarios** (para administradores/depuración):
>>>>>>> 82edf2d (New md files from RunPod)

```json
{
  "operation": "list-documents",
  "include-children": true
}
```

#### Eliminación en cascada

Cuando se elimina un documento padre, todos los documentos hijos deben ser eliminados:

```python
def delete_document(doc_id: str):
    # Find all children
    children = query("SELECT id, object_id FROM document WHERE parent_id = ?", doc_id)

    # Delete child blobs from S3
    for child in children:
        blob_store.delete(child.object_id)

    # Delete child metadata from Cassandra
    execute("DELETE FROM document WHERE parent_id = ?", doc_id)

    # Delete parent blob and metadata
    parent = get_document(doc_id)
    blob_store.delete(parent.object_id)
    execute("DELETE FROM document WHERE id = ? AND user = ?", doc_id, user)
```

#### Consideraciones de almacenamiento

Los bloques de texto extraídos duplican el contenido:
El PDF original se almacena en Garage.
El texto extraído por página también se almacena en Garage.

Este compromiso permite:
**Interfaz de fragmentación uniforme**: El fragmentador siempre recupera por ID.
**Reanudación/reintento**: Se puede reiniciar en la etapa del fragmentador sin volver a extraer el PDF.
**Depuración**: El texto extraído es inspeccionable.
**Separación de responsabilidades**: El extractor de PDF y el fragmentador son servicios independientes.

Para un PDF de 500 MB con 200 páginas que promedian 5 KB de texto por página:
Almacenamiento del PDF: 500 MB.
Almacenamiento del texto extraído: ~1 MB en total.
Sobrecarga: insignificante.

#### Salida del extractor de PDF

El extractor de PDF, después de procesar un documento:

1. Transmite el PDF desde el bibliotecario a un archivo temporal.
2. Extrae el texto página por página.
3. Para cada página, almacena el texto extraído como un documento secundario a través del bibliotecario.
4. Envía los ID de los documentos secundarios a la cola del fragmentador.
<<<<<<< HEAD
Después de la última línea traducida, incluir una línea final que contenga exactamente: [[__END_OF_TRANSLATION__]]
=======

>>>>>>> 82edf2d (New md files from RunPod)
```python
async def extract_pdf(doc_id: str, librarian_client, output_queue):
    """Extract PDF pages and store as child documents."""

    with tempfile.NamedTemporaryFile(delete=True, suffix='.pdf') as tmp:
        # Stream PDF to temp file
        for chunk in librarian_client.stream_document(doc_id):
            tmp.write(chunk)
        tmp.flush()

        # Extract pages
        reader = PdfReader(tmp.name)
        for page_num, page in enumerate(reader.pages, start=1):
            text = page.extract_text()

            # Store as child document
            child_id = f"{doc_id}-page-{page_num}"
            await librarian_client.add_child_document(
                parent_id=doc_id,
                document_id=child_id,
                kind="text/plain",
                title=f"Page {page_num}",
                content=text.encode('utf-8')
            )

            # Send to chunker queue
            await output_queue.send(child_id)
```

El componente de segmentación recibe estos ID de elementos secundarios y los procesa de la misma manera que procesaría un documento de texto subido por el usuario.

### Actualizaciones del cliente

#### SDK de Python


El SDK de Python (`trustgraph-base/trustgraph/api/library.py`) debe manejar
las cargas fragmentadas de forma transparente. La interfaz pública permanece sin cambios:

```python
# Existing interface - no change for users
library.add_document(
    id="doc-123",
    title="Large Report",
    kind="application/pdf",
    content=large_pdf_bytes,  # Can be hundreds of MB
    tags=["reports"]
)
```

Internamente, el SDK detecta el tamaño del documento y cambia de estrategia:

```python
class Library:
    CHUNKED_UPLOAD_THRESHOLD = 2 * 1024 * 1024  # 2MB

    def add_document(self, id, title, kind, content, tags=None, ...):
        if len(content) < self.CHUNKED_UPLOAD_THRESHOLD:
            # Small document: single operation (existing behavior)
            return self._add_document_single(id, title, kind, content, tags)
        else:
            # Large document: chunked upload
            return self._add_document_chunked(id, title, kind, content, tags)

    def _add_document_chunked(self, id, title, kind, content, tags):
        # 1. begin-upload
        session = self._begin_upload(
            document_metadata={...},
            total_size=len(content),
            chunk_size=5 * 1024 * 1024
        )

        # 2. upload-chunk for each chunk
        for i, chunk in enumerate(self._chunk_bytes(content, session.chunk_size)):
            self._upload_chunk(session.upload_id, i, chunk)

        # 3. complete-upload
        return self._complete_upload(session.upload_id)
```

**Callbacks de progreso** (mejora opcional):

```python
def add_document(self, ..., on_progress=None):
    """
    on_progress: Optional callback(bytes_sent, total_bytes)
    """
```

Esto permite que las interfaces de usuario muestren el progreso de la carga sin cambiar la API básica.

#### Herramientas de línea de comandos

**`tg-add-library-document`** continúa funcionando sin cambios:

```bash
# Works transparently for any size - SDK handles chunking internally
tg-add-library-document --file large-report.pdf --title "Large Report"
```

Se podría agregar una visualización opcional del progreso:

```bash
tg-add-library-document --file large-report.pdf --title "Large Report" --progress
# Output:
# Uploading: 45% (225MB / 500MB)
```

**Herramientas heredadas eliminadas:**

`tg-load-pdf` - obsoleto, usar `tg-add-library-document`
`tg-load-text` - obsoleto, usar `tg-add-library-document`

**Comandos de administración/depuración** (opcional, baja prioridad):

```bash
# List incomplete uploads (admin troubleshooting)
tg-add-library-document --list-pending

# Resume specific upload (recovery scenario)
tg-add-library-document --resume upload-abc-123 --file large-report.pdf
```

Estas podrían ser banderas en el comando existente en lugar de herramientas separadas.

#### Actualizaciones de la Especificación de la API

La especificación OpenAPI (`specs/api/paths/librarian.yaml`) necesita actualizaciones para:

**Nuevas operaciones:**

`begin-upload` - Inicializar sesión de carga por partes
`upload-chunk` - Cargar parte individual
`complete-upload` - Finalizar carga
`abort-upload` - Cancelar carga
`get-upload-status` - Consultar el progreso de la carga
`list-uploads` - Listar cargas incompletas para el usuario
`stream-document` - Recuperación de documentos en streaming
`add-child-document` - Almacenar texto extraído (interno)
`list-children` - Listar documentos secundarios (administrador)

**Operaciones modificadas:**

`list-documents` - Agregar parámetro `include-children`

**Nuevos esquemas:**

`ChunkedUploadBeginRequest`
`ChunkedUploadBeginResponse`
`ChunkedUploadChunkRequest`
`ChunkedUploadChunkResponse`
`UploadSession`
`UploadProgress`

**Actualizaciones de la especificación WebSocket** (`specs/websocket/`):

Reflejar las operaciones REST para clientes WebSocket, lo que permite actualizaciones de progreso en tiempo real
durante la carga.

#### Consideraciones de la Experiencia de Usuario

Las actualizaciones de la especificación de la API permiten mejoras en la interfaz de usuario:

**Interfaz de usuario del progreso de la carga:**
Barra de progreso que muestra las partes cargadas
Tiempo estimado restante
Capacidad de pausa/reanudación

**Recuperación de errores:**
Opción de "reintentar la carga" para cargas interrumpidas
Lista de cargas pendientes al reconectar

**Manejo de archivos grandes:**
Detección del tamaño del archivo en el lado del cliente
Carga automática por partes para archivos grandes
<<<<<<< HEAD
Retroalimentación clara durante cargas largas
=======
Retroalimentación clara durante las cargas largas
>>>>>>> 82edf2d (New md files from RunPod)

Estas mejoras en la experiencia de usuario requieren trabajo en la interfaz de usuario, guiado por la especificación de la API actualizada.
