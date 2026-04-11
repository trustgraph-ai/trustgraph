# Especificación técnica: Soporte para entornos multi-inquilino

## Resumen

Habilite implementaciones multi-inquilino corrigiendo las discrepancias en los nombres de los parámetros que impiden la personalización de la cola y agregando la parametrización del espacio de claves de Cassandra.

## Contexto de la arquitectura

### Resolución de colas basada en flujos

El sistema TrustGraph utiliza una **arquitectura basada en flujos** para la resolución dinámica de colas, lo que inherentemente admite la multi-inquilinización:

Las **definiciones de flujo** se almacenan en Cassandra y especifican los nombres de las colas a través de definiciones de interfaz.
Los **nombres de las colas utilizan plantillas** con variables `{id}` que se reemplazan con los ID de las instancias de flujo.
Los **servicios resuelven dinámicamente las colas** buscando las configuraciones de flujo en el momento de la solicitud.
**Cada inquilino puede tener flujos únicos** con diferentes nombres de cola, lo que proporciona aislamiento.

Ejemplo de definición de interfaz de flujo:
```json
{
  "interfaces": {
    "triples-store": "persistent://tg/flow/triples-store:{id}",
    "graph-embeddings-store": "persistent://tg/flow/graph-embeddings-store:{id}"
  }
}
```

Cuando el inquilino A inicia el flujo `tenant-a-prod` y el inquilino B inicia el flujo `tenant-b-prod`, automáticamente obtienen colas aisladas:
`persistent://tg/flow/triples-store:tenant-a-prod`
`persistent://tg/flow/triples-store:tenant-b-prod`

**Servicios diseñados correctamente para la multi-inquilinización:**
✅ **Knowledge Management (núcleos)** - Resuelve dinámicamente las colas a partir de la configuración del flujo que se pasa en las solicitudes.

**Servicios que necesitan correcciones:**
🔴 **Config Service** - La falta de coincidencia en el nombre del parámetro impide la personalización de la cola.
🔴 **Librarian Service** - Temas de gestión de almacenamiento codificados (se discute a continuación).
🔴 **Todos los servicios** - No se puede personalizar el keyspace de Cassandra.

## Declaración del problema

### Problema #1: Falta de coincidencia en el nombre del parámetro en AsyncProcessor
**CLI define:** `--config-queue` (nombre poco claro)
**Argparse convierte a:** `config_queue` (en el diccionario de parámetros)
**El código busca:** `config_push_queue`
**Resultado:** El parámetro se ignora, por defecto a `persistent://tg/config/config`
**Impacto:** Afecta a más de 32 servicios que heredan de AsyncProcessor.
**Bloquea:** Los despliegues multi-inquilinos no pueden usar colas de configuración específicas del inquilino.
**Solución:** Cambiar el nombre del parámetro de la CLI a `--config-push-queue` para mayor claridad (el cambio importante es aceptable, ya que la función actualmente está rota).

### Problema #2: Falta de coincidencia en el nombre del parámetro en Config Service
**CLI define:** `--push-queue` (nombre ambiguo)
**Argparse convierte a:** `push_queue` (en el diccionario de parámetros)
**El código busca:** `config_push_queue`
**Resultado:** El parámetro se ignora.
**Impacto:** El servicio de configuración no puede usar una cola de envío personalizada.
**Solución:** Cambiar el nombre del parámetro de la CLI a `--config-push-queue` para mayor coherencia y claridad (el cambio importante es aceptable).

### Problema #3: Keyspace de Cassandra codificado
**Actual:** El keyspace está codificado como `"config"`, `"knowledge"`, `"librarian"` en varios servicios.
**Resultado:** No se puede personalizar el keyspace para los despliegues multi-inquilinos.
**Impacto:** Servicios de configuración, núcleos y bibliotecario.
**Bloquea:** Múltiples inquilinos no pueden usar keyspaces de Cassandra separados.

### Problema #4: Arquitectura de gestión de colecciones ✅ COMPLETADO
**Anterior:** Las colecciones se almacenaban en el keyspace de Cassandra del bibliotecario a través de una tabla de colecciones separada.
**Anterior:** El bibliotecario utilizaba 4 temas de gestión de almacenamiento codificados para coordinar la creación/eliminación de colecciones:
  `vector_storage_management_topic`
  `object_storage_management_topic`
  `triples_storage_management_topic`
  `storage_management_response_topic`
**Problemas (Resueltos):**
  Los temas codificados no se podían personalizar para los despliegues multi-inquilinos.
  Coordinación asíncrona compleja entre el bibliotecario y 4 o más servicios de almacenamiento.
  Infraestructura de tabla y gestión de Cassandra separada.
  Colas de solicitud/respuesta no persistentes para operaciones críticas.
**Solución implementada:** Se migraron las colecciones al almacenamiento del servicio de configuración, se utiliza el envío de configuración para la distribución.
**Estado:** Todos los backends de almacenamiento se han migrado al patrón `CollectionConfigHandler`.

## Solución

Esta especificación aborda los problemas #1, #2, #3 y #4.

### Parte 1: Corregir las faltas de coincidencia en el nombre del parámetro

#### Cambio 1: Clase base AsyncProcessor - Cambiar el nombre del parámetro de la CLI
**Archivo:** `trustgraph-base/trustgraph/base/async_processor.py`
**Línea:** 260-264

**Actual:**
```python
parser.add_argument(
    '--config-queue',
    default=default_config_queue,
    help=f'Config push queue {default_config_queue}',
)
```

**Fijo:**
```python
parser.add_argument(
    '--config-push-queue',
    default=default_config_queue,
    help=f'Config push queue (default: {default_config_queue})',
)
```

**Justificación:**
Nombres más claros y explícitos.
Coincide con el nombre de la variable interna `config_push_queue`.
El cambio es aceptable ya que la función actualmente no está operativa.
No se necesita ningún cambio en el código de params.get() - ya busca el nombre correcto.

#### Cambio 2: Servicio de Configuración - Renombrar Parámetro de la Interfaz de Línea de Comandos
**Archivo:** `trustgraph-flow/trustgraph/config/service/service.py`
**Línea:** 276-279

**Actual:**
```python
parser.add_argument(
    '--push-queue',
    default=default_config_push_queue,
    help=f'Config push queue (default: {default_config_push_queue})'
)
```

**Fijo:**
```python
parser.add_argument(
    '--config-push-queue',
    default=default_config_push_queue,
    help=f'Config push queue (default: {default_config_push_queue})'
)
```

**Justificación:**
Nombres más claros: "config-push-queue" es más explícito que simplemente "push-queue".
Coincide con el nombre de la variable interna `config_push_queue`.
Consistente con el parámetro `--config-push-queue` de AsyncProcessor.
El cambio es aceptable ya que la función actualmente no está operativa.
No se necesita ningún cambio en el código en params.get() - ya busca el nombre correcto.

### Parte 2: Agregar la parametrización del espacio de claves de Cassandra

#### Cambio 3: Agregar el parámetro de espacio de claves al módulo cassandra_config
**Archivo:** `trustgraph-base/trustgraph/base/cassandra_config.py`

**Agregar argumento de la línea de comandos** (en la función `add_cassandra_args()`):
```python
parser.add_argument(
    '--cassandra-keyspace',
    default=None,
    help='Cassandra keyspace (default: service-specific)'
)
```

**Agregar soporte para variables de entorno** (en la función `resolve_cassandra_config()`):
```python
keyspace = params.get(
    "cassandra_keyspace",
    os.environ.get("CASSANDRA_KEYSPACE")
)
```

**Actualizar el valor de retorno** de `resolve_cassandra_config()`:
Actualmente devuelve: `(hosts, username, password)`
Cambiar para que devuelva: `(hosts, username, password, keyspace)`

**Justificación:**
Coherente con el patrón de configuración de Cassandra existente
Disponible para todos los servicios a través de `add_cassandra_args()`
Admite la configuración mediante la línea de comandos y variables de entorno

#### Cambio 4: Servicio de Configuración - Utilizar Espacios de Claves Parametrizados
**Archivo:** `trustgraph-flow/trustgraph/config/service/service.py`

**Línea 30** - Eliminar el espacio de claves codificado de forma rígida:
```python
# DELETE THIS LINE:
keyspace = "config"
```

**Líneas 69-73** - Actualización de la resolución de la configuración de Cassandra:

**Actual:**
```python
cassandra_host, cassandra_username, cassandra_password = \
    resolve_cassandra_config(params)
```

**Fijo:**
```python
cassandra_host, cassandra_username, cassandra_password, keyspace = \
    resolve_cassandra_config(params, default_keyspace="config")
```

**Justificación:**
Mantiene la compatibilidad con versiones anteriores, utilizando "config" como valor predeterminado.
Permite la sobrescritura a través de `--cassandra-keyspace` o `CASSANDRA_KEYSPACE`.

#### Cambio 5: Servicio de Conocimiento (Cores) - Utilizar Espacios de Claves Parametrizados
**Archivo:** `trustgraph-flow/trustgraph/cores/service.py`

**Línea 37** - Eliminar el espacio de claves codificado de forma rígida:
```python
# DELETE THIS LINE:
keyspace = "knowledge"
```

**Actualización de la resolución de la configuración de Cassandra** (ubicación similar a la del servicio de configuración):
```python
cassandra_host, cassandra_username, cassandra_password, keyspace = \
    resolve_cassandra_config(params, default_keyspace="knowledge")
```

#### Cambio 6: Servicio de Bibliotecario - Utilizar Claves de Espacio de Claves Parametrizadas
**Archivo:** `trustgraph-flow/trustgraph/librarian/service.py`

**Línea 51** - Eliminar el espacio de claves codificado de forma rígida:
```python
# DELETE THIS LINE:
keyspace = "librarian"
```

**Actualización de la resolución de la configuración de Cassandra** (ubicación similar a la del servicio de configuración):
```python
cassandra_host, cassandra_username, cassandra_password, keyspace = \
    resolve_cassandra_config(params, default_keyspace="librarian")
```

### Parte 3: Migrar la gestión de colecciones al servicio de configuración

#### Resumen
Migrar las colecciones del espacio de claves de Cassandra librarian al almacenamiento del servicio de configuración. Esto elimina los temas de gestión de almacenamiento codificados de forma rígida y simplifica la arquitectura utilizando el mecanismo de envío de configuración existente para la distribución.

#### Arquitectura actual
```
API Request → Gateway → Librarian Service
                            ↓
                    CollectionManager
                            ↓
                    Cassandra Collections Table (librarian keyspace)
                            ↓
                    Broadcast to 4 Storage Management Topics (hardcoded)
                            ↓
        Wait for 4+ Storage Service Responses
                            ↓
                    Response to Gateway
```

#### Nueva Arquitectura
```
API Request → Gateway → Librarian Service
                            ↓
                    CollectionManager
                            ↓
                    Config Service API (put/delete/getvalues)
                            ↓
                    Cassandra Config Table (class='collections', key='user:collection')
                            ↓
                    Config Push (to all subscribers on config-push-queue)
                            ↓
        All Storage Services receive config update independently
```

#### Cambio 7: Administrador de Colecciones - Utilizar la API del Servicio de Configuración
**Archivo:** `trustgraph-flow/trustgraph/librarian/collection_manager.py`

**Eliminar:**
Uso de `LibraryTableStore` (Líneas 33, 40-41)
Inicialización de productores de gestión de almacenamiento (Líneas 86-140)
Método `on_storage_response` (Líneas 400-430)
Seguimiento de `pending_deletions` (Líneas 57, 90-96 y uso en todo el código)

**Añadir:**
Cliente del servicio de configuración para llamadas a la API (patrón de solicitud/respuesta)

**Configuración del Cliente:**
```python
# In __init__, add config request/response producers/consumers
from trustgraph.schema.services.config import ConfigRequest, ConfigResponse

# Producer for config requests
self.config_request_producer = Producer(
    client=pulsar_client,
    topic=config_request_queue,
    schema=ConfigRequest,
)

# Consumer for config responses (with correlation ID)
self.config_response_consumer = Consumer(
    taskgroup=taskgroup,
    client=pulsar_client,
    flow=None,
    topic=config_response_queue,
    subscriber=f"{id}-config",
    schema=ConfigResponse,
    handler=self.on_config_response,
)

# Tracking for pending config requests
self.pending_config_requests = {}  # request_id -> asyncio.Event
```

**Modificar `list_collections` (Líneas 145-180):**
```python
async def list_collections(self, user, tag_filter=None, limit=None):
    """List collections from config service"""
    # Send getvalues request to config service
    request = ConfigRequest(
        id=str(uuid.uuid4()),
        operation='getvalues',
        type='collections',
    )

    # Send request and wait for response
    response = await self.send_config_request(request)

    # Parse collections from response
    collections = []
    for key, value_json in response.values.items():
        if ":" in key:
            coll_user, collection = key.split(":", 1)
            if coll_user == user:
                metadata = json.loads(value_json)
                collections.append(CollectionMetadata(**metadata))

    # Apply tag filtering in-memory (as before)
    if tag_filter:
        collections = [c for c in collections if any(tag in c.tags for tag in tag_filter)]

    # Apply limit
    if limit:
        collections = collections[:limit]

    return collections

async def send_config_request(self, request):
    """Send config request and wait for response"""
    event = asyncio.Event()
    self.pending_config_requests[request.id] = event

    await self.config_request_producer.send(request)
    await event.wait()

    return self.pending_config_requests.pop(request.id + "_response")

async def on_config_response(self, message, consumer, flow):
    """Handle config response"""
    response = message.value()
    if response.id in self.pending_config_requests:
        self.pending_config_requests[response.id + "_response"] = response
        self.pending_config_requests[response.id].set()
```

**Modificar `update_collection` (Líneas 182-312):**
```python
async def update_collection(self, user, collection, name, description, tags):
    """Update collection via config service"""
    # Create metadata
    metadata = CollectionMetadata(
        user=user,
        collection=collection,
        name=name,
        description=description,
        tags=tags,
    )

    # Send put request to config service
    request = ConfigRequest(
        id=str(uuid.uuid4()),
        operation='put',
        type='collections',
        key=f'{user}:{collection}',
        value=json.dumps(metadata.to_dict()),
    )

    response = await self.send_config_request(request)

    if response.error:
        raise RuntimeError(f"Config update failed: {response.error.message}")

    # Config service will trigger config push automatically
    # Storage services will receive update and create collections
```

**Modificar `delete_collection` (Líneas 314-398):**
```python
async def delete_collection(self, user, collection):
    """Delete collection via config service"""
    # Send delete request to config service
    request = ConfigRequest(
        id=str(uuid.uuid4()),
        operation='delete',
        type='collections',
        key=f'{user}:{collection}',
    )

    response = await self.send_config_request(request)

    if response.error:
        raise RuntimeError(f"Config delete failed: {response.error.message}")

    # Config service will trigger config push automatically
    # Storage services will receive update and delete collections
```

**Formato de Metadatos de Colección:**
Almacenado en la tabla de configuración como: `class='collections', key='user:collection'`
El valor es una instancia de CollectionMetadata serializada en formato JSON (sin campos de marca de tiempo)
Campos: `user`, `collection`, `name`, `description`, `tags`
Ejemplo: `class='collections', key='alice:my-docs', value='{"user":"alice","collection":"my-docs","name":"My Documents","description":"...","tags":["work"]}'`

#### Cambio 8: Servicio de Bibliotecario - Eliminar la Infraestructura de Gestión de Almacenamiento
**Archivo:** `trustgraph-flow/trustgraph/librarian/service.py`

**Eliminar:**
Productores de gestión de almacenamiento (Líneas 173-190):
  `vector_storage_management_producer`
  `object_storage_management_producer`
  `triples_storage_management_producer`
Consumidor de respuesta de almacenamiento (Líneas 192-201)
Controlador `on_storage_response` (Líneas 467-473)

**Modificar:**
Inicialización de CollectionManager (Líneas 215-224) - eliminar los parámetros del productor de almacenamiento

**Nota:** La API externa de colecciones permanece sin cambios:
`list-collections`
`update-collection`
`delete-collection`

#### Cambio 9: Eliminar la Tabla de Colecciones de LibraryTableStore
**Archivo:** `trustgraph-flow/trustgraph/tables/library.py`

**Eliminar:**
Sentencia CREATE de la tabla de colecciones (Líneas 114-127)
Sentencias preparadas de colecciones (Líneas 205-240)
Todos los métodos de colección (Líneas 578-717):
  `ensure_collection_exists`
  `list_collections`
  `update_collection`
  `delete_collection`
  `get_collection`
  `create_collection`

**Justificación:**
Las colecciones ahora se almacenan en la tabla de configuración
El cambio importante es aceptable: no se necesita migración de datos
Simplifica significativamente el servicio de bibliotecario

#### Cambio 10: Servicios de Almacenamiento - Gestión de Colecciones Basada en Configuración ✅ COMPLETADO

**Estado:** Todos los 11 backends de almacenamiento se han migrado para usar `CollectionConfigHandler`.

**Servicios Afectados (11 en total):**
Incrustaciones de documentos: milvus, pinecone, qdrant
Incrustaciones de grafos: milvus, pinecone, qdrant
Almacenamiento de objetos: cassandra
Almacenamiento de triples: cassandra, falkordb, memgraph, neo4j

**Archivos:**
`trustgraph-flow/trustgraph/storage/doc_embeddings/milvus/write.py`
`trustgraph-flow/trustgraph/storage/doc_embeddings/pinecone/write.py`
`trustgraph-flow/trustgraph/storage/doc_embeddings/qdrant/write.py`
`trustgraph-flow/trustgraph/storage/graph_embeddings/milvus/write.py`
`trustgraph-flow/trustgraph/storage/graph_embeddings/pinecone/write.py`
`trustgraph-flow/trustgraph/storage/graph_embeddings/qdrant/write.py`
`trustgraph-flow/trustgraph/storage/objects/cassandra/write.py`
`trustgraph-flow/trustgraph/storage/triples/cassandra/write.py`
`trustgraph-flow/trustgraph/storage/triples/falkordb/write.py`
`trustgraph-flow/trustgraph/storage/triples/memgraph/write.py`
`trustgraph-flow/trustgraph/storage/triples/neo4j/write.py`

**Patrón de Implementación (todos los servicios):**

1. **Registrar el controlador de configuración en `__init__`:**
```python
# Add after AsyncProcessor initialization
self.register_config_handler(self.on_collection_config)
self.known_collections = set()  # Track (user, collection) tuples
```

2. **Implementar el manejador de configuración:**
```python
async def on_collection_config(self, config, version):
    """Handle collection configuration updates"""
    logger.info(f"Collection config version: {version}")

    if "collections" not in config:
        return

    # Parse collections from config
    # Key format: "user:collection" in config["collections"]
    config_collections = set()
    for key in config["collections"].keys():
        if ":" in key:
            user, collection = key.split(":", 1)
            config_collections.add((user, collection))

    # Determine changes
    to_create = config_collections - self.known_collections
    to_delete = self.known_collections - config_collections

    # Create new collections (idempotent)
    for user, collection in to_create:
        try:
            await self.create_collection_internal(user, collection)
            self.known_collections.add((user, collection))
            logger.info(f"Created collection: {user}/{collection}")
        except Exception as e:
            logger.error(f"Failed to create {user}/{collection}: {e}")

    # Delete removed collections (idempotent)
    for user, collection in to_delete:
        try:
            await self.delete_collection_internal(user, collection)
            self.known_collections.discard((user, collection))
            logger.info(f"Deleted collection: {user}/{collection}")
        except Exception as e:
            logger.error(f"Failed to delete {user}/{collection}: {e}")
```

3. **Inicializar colecciones conocidas al inicio:**
```python
async def start(self):
    """Start the processor"""
    await super().start()
    await self.sync_known_collections()

async def sync_known_collections(self):
    """Query backend to populate known_collections set"""
    # Backend-specific implementation:
    # - Milvus/Pinecone/Qdrant: List collections/indexes matching naming pattern
    # - Cassandra: Query keyspaces or collection metadata
    # - Neo4j/Memgraph/FalkorDB: Query CollectionMetadata nodes
    pass
```

4. **Refactorizar los métodos de manejo existentes:**
```python
# Rename and remove response sending:
# handle_create_collection → create_collection_internal
# handle_delete_collection → delete_collection_internal

async def create_collection_internal(self, user, collection):
    """Create collection (idempotent)"""
    # Same logic as current handle_create_collection
    # But remove response producer calls
    # Handle "already exists" gracefully
    pass

async def delete_collection_internal(self, user, collection):
    """Delete collection (idempotent)"""
    # Same logic as current handle_delete_collection
    # But remove response producer calls
    # Handle "not found" gracefully
    pass
```

5. **Eliminar la infraestructura de administración de almacenamiento:**
   Eliminar la configuración y el inicio de `self.storage_request_consumer`
   Eliminar la configuración de `self.storage_response_producer`
   Eliminar el método de despachador de `on_storage_management`
   Eliminar las métricas para la administración de almacenamiento
   Eliminar las importaciones: `StorageManagementRequest`, `StorageManagementResponse`

**Consideraciones específicas del backend:**

**Almacenes de vectores (Milvus, Pinecone, Qdrant):** Realizar un seguimiento de `(user, collection)` lógico en `known_collections`, pero puede crear múltiples colecciones de backend por dimensión. Continuar con el patrón de creación perezosa. Las operaciones de eliminación deben eliminar todas las variantes de dimensión.

**Objetos Cassandra:** Las colecciones son propiedades de fila, no estructuras. Realizar un seguimiento de la información a nivel de keyspace.

**Almacenes de grafos (Neo4j, Memgraph, FalkorDB):** Consultar nodos `CollectionMetadata` al inicio. Crear/eliminar nodos de metadatos durante la sincronización.

**Triples de Cassandra:** Utilizar la API `KnowledgeGraph` para las operaciones de colección.

**Puntos clave de diseño:**

**Consistencia eventual:** No hay mecanismo de solicitud/respuesta, el empuje de configuración se transmite.
**Idempotencia:** Todas las operaciones de creación/eliminación deben ser seguras para reintentar.
**Manejo de errores:** Registrar los errores, pero no bloquear las actualizaciones de configuración.
**Autocuración:** Las operaciones fallidas se volverán a intentar en el siguiente empuje de configuración.
**Formato de clave de colección:** `"user:collection"` en `config["collections"]`

#### Cambio 11: Actualizar el esquema de la colección: eliminar las marcas de tiempo
**Archivo:** `trustgraph-base/trustgraph/schema/services/collection.py`

**Modificar CollectionMetadata (líneas 13-21):**
Eliminar los campos `created_at` y `updated_at`:
```python
class CollectionMetadata(Record):
    user = String()
    collection = String()
    name = String()
    description = String()
    tags = Array(String())
    # Remove: created_at = String()
    # Remove: updated_at = String()
```

**Modificar CollectionManagementRequest (líneas 25-47):**
Eliminar campos de marca de tiempo:
```python
class CollectionManagementRequest(Record):
    operation = String()
    user = String()
    collection = String()
    timestamp = String()
    name = String()
    description = String()
    tags = Array(String())
    # Remove: created_at = String()
    # Remove: updated_at = String()
    tag_filter = Array(String())
    limit = Integer()
```

**Justificación:**
Las marcas de tiempo no aportan valor a las colecciones.
El servicio de configuración mantiene su propio seguimiento de versiones.
Simplifica el esquema y reduce el almacenamiento.

#### Beneficios de la migración del servicio de configuración

1. ✅ **Elimina los temas de gestión de almacenamiento codificados de forma rígida** - Soluciona el bloqueo de multi-inquilino.
2. ✅ **Coordinación más sencilla** - No hay esperas asíncronas complejas para 4 o más respuestas de almacenamiento.
3. ✅ **Consistencia eventual** - Los servicios de almacenamiento se actualizan de forma independiente a través de la configuración.
4. ✅ **Mayor fiabilidad** - Configuración persistente frente a solicitud/respuesta no persistente.
5. ✅ **Modelo de configuración unificado** - Las colecciones se tratan como configuración.
6. ✅ **Reduce la complejidad** - Elimina aproximadamente 300 líneas de código de coordinación.
7. ✅ **Listo para multi-inquilino** - La configuración ya admite el aislamiento de inquilinos a través de espacios de claves.
8. ✅ **Seguimiento de versiones** - El mecanismo de versión del servicio de configuración proporciona un registro de auditoría.

## Notas de implementación

### Compatibilidad con versiones anteriores

**Cambios de parámetros:**
Los cambios de nombre de los parámetros de la CLI son cambios importantes, pero aceptables (la función actualmente no está operativa).
Los servicios funcionan sin parámetros (utilizan los valores predeterminados).
Los espacios de claves predeterminados se conservan: "config", "knowledge", "librarian".
Cola predeterminada: `persistent://tg/config/config`

**Gestión de colecciones:**
**Cambio importante:** La tabla de colecciones se elimina del espacio de claves de librarian.
**No se proporciona migración de datos** - aceptable para esta fase.
La API externa de colecciones no cambia (operaciones de lista, actualización y eliminación).
El formato de los metadatos de la colección se simplifica (se eliminan las marcas de tiempo).

### Requisitos de prueba

**Pruebas de parámetros:**
1. Verificar que el parámetro `--config-push-queue` funciona en el servicio graph-embeddings.
2. Verificar que el parámetro `--config-push-queue` funciona en el servicio text-completion.
3. Verificar que el parámetro `--config-push-queue` funciona en el servicio de configuración.
4. Verificar que el parámetro `--cassandra-keyspace` funciona para el servicio de configuración.
5. Verificar que el parámetro `--cassandra-keyspace` funciona para el servicio cores.
6. Verificar que el parámetro `--cassandra-keyspace` funciona para el servicio librarian.
7. Verificar que los servicios funcionan sin parámetros (utiliza los valores predeterminados).
8. Verificar la implementación multi-inquilino con nombres de cola y espacios de claves personalizados.

**Pruebas de gestión de colecciones:**
9. Verificar la operación `list-collections` a través del servicio de configuración.
10. Verificar que `update-collection` crea/actualiza en la tabla de configuración.
11. Verificar que `delete-collection` elimina de la tabla de configuración.
12. Verificar que se activa la propagación de la configuración cuando se actualizan las colecciones.
13. Verificar que el filtrado de etiquetas funciona con el almacenamiento basado en la configuración.
14. Verificar que las operaciones de la colección funcionan sin campos de marca de tiempo.

### Ejemplo de implementación multi-inquilino
```bash
# Tenant: tg-dev
graph-embeddings \
  -p pulsar+ssl://broker:6651 \
  --pulsar-api-key <KEY> \
  --config-push-queue persistent://tg-dev/config/config

config-service \
  -p pulsar+ssl://broker:6651 \
  --pulsar-api-key <KEY> \
  --config-push-queue persistent://tg-dev/config/config \
  --cassandra-keyspace tg_dev_config
```

## Análisis de Impacto

### Servicios Afectados por el Cambio 1-2 (Renombramiento de Parámetro de la CLI)
Todos los servicios que heredan de AsyncProcessor o FlowProcessor:
config-service
cores-service
librarian-service
graph-embeddings
document-embeddings
text-completion-* (todos los proveedores)
extract-* (todos los extractores)
query-* (todos los servicios de consulta)
retrieval-* (todos los servicios RAG)
storage-* (todos los servicios de almacenamiento)
Y más de 20 servicios

### Servicios Afectados por los Cambios 3-6 (Espacio de Claves de Cassandra)
config-service
cores-service
librarian-service

### Servicios Afectados por los Cambios 7-11 (Gestión de Colecciones)

**Cambios Inmediatos:**
librarian-service (collection_manager.py, service.py)
tables/library.py (eliminación de la tabla de colecciones)
schema/services/collection.py (eliminación de la marca de tiempo)

**Cambios Completados (Cambio 10):** ✅
Todos los servicios de almacenamiento (11 en total) - migrados a la configuración push para las actualizaciones de colecciones a través de `CollectionConfigHandler`
Esquema de gestión de almacenamiento eliminado de `storage.py`

## Consideraciones Futuras

### Modelo de Espacio de Claves por Usuario

Algunos servicios utilizan **espacios de claves por usuario** dinámicamente, donde cada usuario obtiene su propio espacio de claves de Cassandra:

**Servicios con espacios de claves por usuario:**
1. **Servicio de Consulta de Triples** (`trustgraph-flow/trustgraph/query/triples/cassandra/service.py:65`)
   Utiliza `keyspace=query.user`
2. **Servicio de Consulta de Objetos** (`trustgraph-flow/trustgraph/query/objects/cassandra/service.py:479`)
   Utiliza `keyspace=self.sanitize_name(user)`
3. **Acceso Directo al Gráfico de Conocimiento** (`trustgraph-flow/trustgraph/direct/cassandra_kg.py:18`)
   Parámetro predeterminado `keyspace="trustgraph"`

**Estado:** Estos **no se modifican** en esta especificación.

**Revisión Futura Requerida:**
Evaluar si el modelo de espacio de claves por usuario crea problemas de aislamiento de inquilinos
Considerar si las implementaciones multi-inquilino necesitan patrones de prefijos de espacio de claves (por ejemplo, `tenant_a_user1`)
Revisar posibles colisiones de ID de usuario entre inquilinos
Evaluar si un espacio de claves compartido único por inquilino con aislamiento de filas basado en el usuario es preferible

**Nota:** Esto no bloquea la implementación multi-inquilino actual, pero debe revisarse antes de las implementaciones multi-inquilino de producción.

## Fases de Implementación

### Fase 1: Correcciones de Parámetros (Cambios 1-6)
Corregir el nombre del parámetro `--config-push-queue`
Agregar soporte para el parámetro `--cassandra-keyspace`
**Resultado:** Configuración de cola y espacio de claves multi-inquilino habilitada

### Fase 2: Migración de la Gestión de Colecciones (Cambios 7-9, 11)
Migrar el almacenamiento de colecciones al servicio de configuración
Eliminar la tabla de colecciones de librarian
Actualizar el esquema de colecciones (eliminar marcas de tiempo)
**Resultado:** Elimina la gestión de almacenamiento codificada, simplifica librarian

### Fase 3: Actualizaciones del Servicio de Almacenamiento (Cambio 10) ✅ COMPLETADO
Se actualizaron todos los servicios de almacenamiento para usar la configuración push para las colecciones a través de `CollectionConfigHandler`
Se eliminó la infraestructura de solicitud/respuesta de gestión de almacenamiento
Se eliminaron las definiciones de esquema heredadas
**Resultado:** Se logró una gestión de colecciones basada en configuración completa

## Referencias
Problema de GitHub: https://github.com/trustgraph-ai/trustgraph/issues/582
Archivos relacionados:
  `trustgraph-base/trustgraph/base/async_processor.py`
  `trustgraph-base/trustgraph/base/cassandra_config.py`
  `trustgraph-base/trustgraph/schema/core/topic.py`
  `trustgraph-base/trustgraph/schema/services/collection.py`
  `trustgraph-flow/trustgraph/config/service/service.py`
  `trustgraph-flow/trustgraph/cores/service.py`
  `trustgraph-flow/trustgraph/librarian/service.py`
  `trustgraph-flow/trustgraph/librarian/collection_manager.py`
  `trustgraph-flow/trustgraph/tables/library.py`
