---
layout: default
title: "Especificación Técnica de Gestión de Colecciones"
parent: "Spanish (Beta)"
---

# Especificación Técnica de Gestión de Colecciones

> **Beta Translation:** This document was translated via Machine Learning and as such may not be 100% accurate. All non-English languages are currently classified as Beta.

## Descripción General

Esta especificación describe las capacidades de gestión de colecciones para TrustGraph, que requieren la creación explícita de colecciones y proporcionan un control directo sobre el ciclo de vida de la colección. Las colecciones deben crearse explícitamente antes de su uso, lo que garantiza una sincronización adecuada entre los metadatos del bibliotecario y todos los backends de almacenamiento. La función admite cuatro casos de uso principales:

1. **Creación de Colecciones**: Crear explícitamente colecciones antes de almacenar datos
2. **Listado de Colecciones**: Ver todas las colecciones existentes en el sistema
3. **Gestión de Metadatos de Colecciones**: Actualizar los nombres, las descripciones y las etiquetas de las colecciones
4. **Eliminación de Colecciones**: Eliminar colecciones y sus datos asociados en todos los tipos de almacenamiento

## Objetivos

**Creación Explícita de Colecciones**: Requerir que las colecciones se creen antes de que se puedan almacenar datos
**Sincronización de Almacenamiento**: Asegurar que las colecciones existan en todos los backends de almacenamiento (vectores, objetos, triples)
**Visibilidad de Colecciones**: Permitir a los usuarios listar e inspeccionar todas las colecciones en su entorno
**Limpieza de Colecciones**: Permitir la eliminación de colecciones que ya no son necesarias
**Organización de Colecciones**: Compatibilidad con etiquetas para un mejor seguimiento y descubrimiento de colecciones
**Gestión de Metadatos**: Asociar metadatos significativos con las colecciones para una mayor claridad operativa
**Descubrimiento de Colecciones**: Facilitar la búsqueda de colecciones específicas mediante el filtrado y la búsqueda
**Transparencia Operacional**: Proporcionar una visibilidad clara del ciclo de vida y el uso de las colecciones
**Gestión de Recursos**: Permitir la limpieza de colecciones no utilizadas para optimizar la utilización de recursos
**Integridad de Datos**: Prevenir la existencia de colecciones huérfanas en el almacenamiento sin seguimiento de metadatos

## Antecedentes

Anteriormente, las colecciones en TrustGraph se creaban implícitamente durante las operaciones de carga de datos, lo que provocaba problemas de sincronización en los que las colecciones podían existir en los backends de almacenamiento sin metadatos correspondientes en el bibliotecario. Esto creaba desafíos de gestión y posibles datos huérfanos.

El modelo de creación explícita de colecciones aborda estos problemas mediante:
La necesidad de crear colecciones antes de su uso a través de `tg-set-collection`
La difusión de la creación de colecciones a todos los backends de almacenamiento
El mantenimiento de un estado sincronizado entre los metadatos del bibliotecario y el almacenamiento
La prevención de escrituras en colecciones inexistentes
La provisión de una gestión clara del ciclo de vida de las colecciones

Esta especificación define el modelo de gestión explícita de colecciones. Al requerir la creación explícita de colecciones, TrustGraph garantiza:
Que las colecciones se rastreen en los metadatos del bibliotecario desde su creación
Que todos los backends de almacenamiento conozcan las colecciones antes de recibir datos
Que no existan colecciones huérfanas en el almacenamiento
Una visibilidad y un control claros del ciclo de vida de las colecciones
Un manejo de errores coherente cuando las operaciones hacen referencia a colecciones inexistentes

## Diseño Técnico

### Arquitectura

El sistema de gestión de colecciones se implementará dentro de la infraestructura existente de TrustGraph:

1. **Integración del Servicio del Bibliotecario**
   Las operaciones de gestión de colecciones se agregarán al servicio del bibliotecario existente
   No se requiere un nuevo servicio; aprovecha los patrones de autenticación y acceso existentes
   Gestiona el listado, la eliminación y la gestión de metadatos de colecciones

   Módulo: trustgraph-librarian

2. **Tabla de Metadatos de Colecciones de Cassandra**
   Nueva tabla en el keyspace existente del bibliotecario
   Almacena metadatos de colecciones con acceso específico al usuario
   Clave primaria: (user_id, collection_id) para una correcta multi-tenencia

   Módulo: trustgraph-librarian

3. **CLI de Gestión de Colecciones**
   Interfaz de línea de comandos para operaciones de colecciones
   Proporciona comandos de listado, eliminación, etiquetado y gestión de etiquetas
   Se integra con el marco de CLI existente

   Módulo: trustgraph-cli

### Modelos de Datos

#### Tabla de Metadatos de Colecciones de Cassandra

Los metadatos de la colección se almacenarán en una tabla estructurada de Cassandra en el keyspace del bibliotecario:

```sql
CREATE TABLE collections (
    user text,
    collection text,
    name text,
    description text,
    tags set<text>,
    created_at timestamp,
    updated_at timestamp,
    PRIMARY KEY (user, collection)
);
```

Estructura de la tabla:
**user** + **collection**: Clave primaria compuesta que asegura el aislamiento del usuario
**name**: Nombre legible por humanos de la colección
**description**: Descripción detallada del propósito de la colección
**tags**: Conjunto de etiquetas para la categorización y el filtrado
**created_at**: Marca de tiempo de creación de la colección
**updated_at**: Marca de tiempo de la última modificación

Este enfoque permite:
Gestión de colecciones multi-inquilino con aislamiento de usuario
Consulta eficiente por usuario y colección
Sistema de etiquetado flexible para la organización
Seguimiento del ciclo de vida para obtener información operativa

#### Ciclo de vida de la colección

Las colecciones se crean explícitamente en el bibliotecario antes de que puedan comenzar las operaciones de datos:

1. **Creación de la colección** (Dos caminos):

   **Camino A: Creación iniciada por el usuario** a través de `tg-set-collection`:
   El usuario proporciona el ID de la colección, el nombre, la descripción y las etiquetas
   El bibliotecario crea un registro de metadatos en la tabla `collections`
   El bibliotecario transmite "crear-colección" a todos los backends de almacenamiento
   Todos los procesadores de almacenamiento crean la colección y confirman el éxito
   La colección está ahora lista para las operaciones de datos

   **Camino B: Creación automática al enviar un documento**:
   El usuario envía un documento que especifica un ID de colección
   El bibliotecario comprueba si existe la colección en la tabla de metadatos
   Si no existe: El bibliotecario crea metadatos con valores predeterminados (nombre=id_colección, descripción/etiquetas vacías)
   El bibliotecario transmite "crear-colección" a todos los backends de almacenamiento
   Todos los procesadores de almacenamiento crean la colección y confirman el éxito
   El procesamiento del documento continúa con la colección ahora establecida

   Ambos caminos garantizan que la colección exista en los metadatos del bibliotecario Y en todos los backends de almacenamiento antes de permitir las operaciones de datos.

2. **Validación de almacenamiento**: Las operaciones de escritura validan la existencia de la colección:
   Los procesadores de almacenamiento comprueban el estado de la colección antes de aceptar escrituras
   Las escrituras en colecciones inexistentes devuelven un error
   Esto evita las escrituras directas que omiten la lógica de creación de colecciones del bibliotecario

3. **Comportamiento de la consulta**: Las operaciones de consulta gestionan las colecciones inexistentes de forma elegante:
   Las consultas a colecciones inexistentes devuelven resultados vacíos
   No se lanza ningún error para las operaciones de consulta
   Permite la exploración sin requerir que la colección exista

4. **Actualizaciones de metadatos**: Los usuarios pueden actualizar los metadatos de la colección después de la creación:
   Actualice el nombre, la descripción y las etiquetas a través de `tg-set-collection`
   Las actualizaciones se aplican solo a los metadatos del bibliotecario
   Los backends de almacenamiento mantienen la colección, pero las actualizaciones de metadatos no se propagan

5. **Eliminación explícita**: Los usuarios eliminan las colecciones a través de `tg-delete-collection`:
   El bibliotecario transmite "eliminar-colección" a todos los backends de almacenamiento
   Espera la confirmación de todos los procesadores de almacenamiento
   Elimina el registro de metadatos del bibliotecario solo después de que se complete la limpieza del almacenamiento
   Garantiza que no queden datos huérfanos en el almacenamiento

**Principio clave**: El bibliotecario es el único punto de control para la creación de colecciones. Ya sea iniciado por un comando de usuario o por la presentación de un documento, el bibliotecario garantiza el seguimiento adecuado de los metadatos y la sincronización del backend de almacenamiento antes de permitir las operaciones de datos.

Operaciones requeridas:
**Crear colección**: Operación del usuario a través de `tg-set-collection` O automática al enviar un documento
**Actualizar metadatos de la colección**: Operación del usuario para modificar el nombre, la descripción y las etiquetas
**Eliminar colección**: Operación del usuario para eliminar la colección y sus datos en todos los almacenes
**Listar colecciones**: Operación del usuario para ver las colecciones con filtrado por etiquetas

#### Gestión de colecciones multi-almacén

Las colecciones existen en varios backends de almacenamiento en TrustGraph:
**Tiendas vectoriales** (Qdrant, Milvus, Pinecone): Almacena incrustaciones y datos vectoriales
**Tiendas de objetos** (Cassandra): Almacena documentos y datos de archivos
**Tiendas de triples** (Cassandra, Neo4j, Memgraph, FalkorDB): Almacena datos de grafos/RDF
Después de la última línea traducida, incluir una línea final que contenga exactamente: [[__END_OF_TRANSLATION__]]
Cada tipo de tienda implementa:
**Seguimiento del estado de la colección**: Mantener conocimiento de qué colecciones existen
**Creación de colecciones**: Aceptar y procesar operaciones de "crear-colección"
**Validación de colecciones**: Comprobar si la colección existe antes de aceptar escrituras
**Eliminación de colecciones**: Eliminar todos los datos para la colección especificada

El servicio de bibliotecario coordina las operaciones de colección en todos los tipos de tienda, asegurando:
Que las colecciones se creen en todos los backends antes de su uso
Que todos los backends confirmen la creación antes de devolver el éxito
Un ciclo de vida de colección sincronizado en todos los tipos de almacenamiento
Un manejo de errores consistente cuando las colecciones no existen

#### Seguimiento del estado de la colección por tipo de almacenamiento

Cada backend de almacenamiento realiza el seguimiento del estado de la colección de manera diferente según sus capacidades:

**Triple Store de Cassandra:**
Utiliza la tabla `triples_collection` existente
Crea un triple de marcador de sistema cuando se crea una colección
Consulta: `SELECT collection FROM triples_collection WHERE collection = ? LIMIT 1`
Comprobación de existencia de colección eficiente de partición única

**Almacenes de vectores Qdrant/Milvus/Pinecone:**
Las API nativas de colección proporcionan la comprobación de existencia
Las colecciones se crean con la configuración de vectores adecuada
El método `collection_exists()` utiliza la API de almacenamiento
La creación de colecciones valida los requisitos de dimensión

**Almacenes de grafos Neo4j/Memgraph/FalkorDB:**
Utiliza nodos `:CollectionMetadata` para realizar el seguimiento de las colecciones
Propiedades del nodo: `{user, collection, created_at}`
Consulta: `MATCH (c:CollectionMetadata {user: $user, collection: $collection})`
Separado de los nodos de datos para una separación limpia
Permite una enumeración y validación eficientes de las colecciones

**Almacén de objetos de Cassandra:**
Utiliza la tabla de metadatos de la colección o filas de marcador
Patrón similar al triple store
Valida la colección antes de las escrituras de documentos

### API

API de administración de colecciones (Bibliotecario):
**Crear/Actualizar colección**: Crear una nueva colección o actualizar los metadatos existentes a través de `tg-set-collection`
**Listar colecciones**: Recuperar colecciones para un usuario con filtrado opcional por etiqueta
**Eliminar colección**: Eliminar la colección y los datos asociados, propagándose a todos los tipos de tienda

API de administración de almacenamiento (Todos los procesadores de almacenamiento):
**Crear colección**: Manejar la operación de "crear-colección", establecer la colección en el almacenamiento
**Eliminar colección**: Manejar la operación de "eliminar-colección", eliminar todos los datos de la colección
**Comprobación de existencia de colección**: Validación interna antes de aceptar operaciones de escritura

API de operación de datos (Comportamiento modificado):
**API de escritura**: Validar que la colección exista antes de aceptar datos, devolver un error si no es así
**API de consulta**: Devolver resultados vacíos para colecciones inexistentes sin error

### Detalles de implementación

La implementación seguirá los patrones existentes de TrustGraph para la integración de servicios y la estructura de comandos de la CLI.

#### Eliminación en cascada de colecciones

Cuando un usuario inicia la eliminación de una colección a través del servicio de bibliotecario:

1. **Validación de metadatos**: Verificar que la colección exista y que el usuario tenga permiso para eliminarla
2. **Propagación a tiendas**: El bibliotecario coordina la eliminación en todos los escritores de tiendas:
   Escritor de almacenamiento de vectores: Eliminar incrustaciones e índices de vectores para el usuario y la colección
   Escritor de almacenamiento de objetos: Eliminar documentos y archivos para el usuario y la colección
   Escritor de triple store: Eliminar datos de grafos y triples para el usuario y la colección
3. **Limpieza de metadatos**: Eliminar el registro de metadatos de la colección de Cassandra
4. **Manejo de errores**: Si falla la eliminación de alguna tienda, mantener la coherencia a través de mecanismos de reversión o reintento

#### Interfaz de administración de colecciones

**⚠️ ENFOQUE ANTIGUO: REEMPLAZADO POR UN PATRÓN BASADO EN CONFIGURACIÓN**

La arquitectura basada en colas descrita a continuación ha sido reemplazada por un enfoque basado en configuración que utiliza `CollectionConfigHandler`. Todos los backends de almacenamiento ahora reciben actualizaciones de colecciones a través de mensajes de configuración en lugar de colas de administración dedicadas.

~~Todos los escritores de tiendas implementan una interfaz de administración de colecciones estandarizada con un esquema común:~~

~~**Esquema de mensaje (`StorageManagementRequest`):**~~
```json
{
  "operation": "create-collection" | "delete-collection",
  "user": "user123",
  "collection": "documents-2024"
}
```

~~**Arquitectura de la Cola:**~~
~~**Cola de Gestión de Almacenes Vectoriales** (`vector-storage-management`): Almacenes de vectores/incrustaciones~~
~~**Cola de Gestión de Almacenes de Objetos** (`object-storage-management`): Almacenes de objetos/documentos~~
~~**Cola de Gestión de Almacenes Triples** (`triples-storage-management`): Almacenes de grafos/RDF~~
~~**Cola de Respuestas de Almacenamiento** (`storage-management-response`): Todas las respuestas se envían aquí~~

**Implementación Actual:**

Todos los backends de almacenamiento ahora utilizan `CollectionConfigHandler`:
**Integración de Configuración Push**: Los servicios de almacenamiento se registran para recibir notificaciones de configuración push.
**Sincronización Automática**: Las colecciones se crean/eliminan en función de los cambios de configuración.
**Modelo Declarativo**: Las colecciones se definen en el servicio de configuración, y los backends se sincronizan para que coincidan.
**Sin Solicitud/Respuesta**: Elimina la sobrecarga de coordinación y el seguimiento de respuestas.
**Seguimiento del Estado de la Colección**: Se mantiene a través de la caché `known_collections`.
**Operaciones Idempotentes**: Es seguro procesar la misma configuración varias veces.

Cada backend de almacenamiento implementa:
`create_collection(user: str, collection: str, metadata: dict)` - Crear estructuras de colección
`delete_collection(user: str, collection: str)` - Eliminar todos los datos de la colección
`collection_exists(user: str, collection: str) -> bool` - Validar antes de escribir

#### Refactorización del Almacén Triples de Cassandra

Como parte de esta implementación, el almacén triples de Cassandra se refactorizará de un modelo de una tabla por colección a un modelo de una tabla unificada:

**Arquitectura Actual:**
Keyspace por usuario, tabla separada por colección
Esquema: `(s, p, o)` con `PRIMARY KEY (s, p, o)`
Nombres de tabla: las colecciones de usuario se convierten en tablas separadas de Cassandra.

**Nueva Arquitectura:**
Keyspace por usuario, una sola tabla "triples" para todas las colecciones
Esquema: `(collection, s, p, o)` con `PRIMARY KEY (collection, s, p, o)`
Aislamiento de colecciones a través de la partición de colecciones

**Cambios Requeridos:**

1. **Refactorización de la Clase TrustGraph** (`trustgraph/direct/cassandra.py`):
   Eliminar el parámetro `table` del constructor, usar la tabla "triples" fija.
   Agregar el parámetro `collection` a todos los métodos.
   Actualizar el esquema para incluir la colección como la primera columna.
   **Actualizaciones de Índice**: Se crearán nuevos índices para admitir los 8 patrones de consulta:
     Índice en `(s)` para consultas basadas en el sujeto.
     Índice en `(p)` para consultas basadas en el predicado.
     Índice en `(o)` para consultas basadas en el objeto.
     Nota: Cassandra no admite índices secundarios de varias columnas, por lo que estos son índices de una sola columna.

   **Rendimiento del Patrón de Consulta:**
     ✅ `get_all()` - escaneo de partición en `collection`
     ✅ `get_s(s)` - utiliza la clave primaria de manera eficiente (`collection, s`)
     ✅ `get_p(p)` - utiliza `idx_p` con `collection` de filtrado
     ✅ `get_o(o)` - utiliza `idx_o` con `collection` de filtrado
     ✅ `get_sp(s, p)` - utiliza la clave primaria de manera eficiente (`collection, s, p`)
     ⚠️ `get_po(p, o)` - requiere `ALLOW FILTERING` (utiliza `idx_p` o `idx_o` más filtrado)
     ✅ `get_os(o, s)` - utiliza `idx_o` con filtrado adicional en `s`
     ✅ `get_spo(s, p, o)` - utiliza toda la clave primaria de manera eficiente

   **Nota sobre ALLOW FILTERING**: El patrón de consulta `get_po` requiere `ALLOW FILTERING` porque necesita tanto las restricciones de predicado como las de objeto sin un índice compuesto adecuado. Esto es aceptable porque este patrón de consulta es menos común que las consultas basadas en el sujeto en el uso típico de un almacén triples.

2. **Actualizaciones del Escritor de Almacenamiento** (`trustgraph/storage/triples/cassandra/write.py`):
   Mantener una única conexión TrustGraph por usuario en lugar de por (usuario, colección).
   Pasar la colección a las operaciones de inserción.
   Mejor utilización de recursos con menos conexiones.

3. **Actualizaciones del Servicio de Consulta** (`trustgraph/query/triples/cassandra/service.py`):
   Una única conexión TrustGraph por usuario.
   Pasar la colección a todas las operaciones de consulta.
   Mantener la misma lógica de consulta con el parámetro de colección.

**Beneficios:**
**Eliminación Simplificada de Colecciones**: Eliminar utilizando la clave de partición `collection` en las 4 tablas.
**Eficiencia de Recursos**: Menos conexiones de base de datos y objetos de tabla.
**Operaciones entre Colecciones**: Más fácil de implementar operaciones que abarcan múltiples colecciones.
**Arquitectura Consistente**: Se alinea con el enfoque unificado de metadatos de colección.
**Validación de Colecciones**: Es fácil comprobar la existencia de la colección mediante la tabla `triples_collection`.

Las operaciones de colección serán atómicas siempre que sea posible y proporcionarán un manejo de errores y una validación adecuados.

## Consideraciones de seguridad

Las operaciones de administración de colecciones requieren la autorización adecuada para evitar el acceso no autorizado o la eliminación de colecciones. El control de acceso se alineará con los modelos de seguridad de TrustGraph existentes.

## Consideraciones de rendimiento

Las operaciones de listado de colecciones pueden requerir paginación para entornos con un gran número de colecciones. Las consultas de metadatos deben optimizarse para patrones de filtrado comunes.

## Estrategia de pruebas

La prueba exhaustiva cubrirá:
Flujo de trabajo de creación de colecciones de extremo a extremo
Sincronización del almacenamiento en segundo plano
Validación de escritura para colecciones inexistentes
Manejo de consultas de colecciones inexistentes
Eliminación de colecciones en cascada en todos los almacenes
Manejo de errores y escenarios de recuperación
Pruebas unitarias para cada almacenamiento en segundo plano
Pruebas de integración para operaciones entre almacenes

## Estado de la implementación

### ✅ Componentes completados

1. **Servicio de administración de colecciones Librarian** (`trustgraph-flow/trustgraph/librarian/collection_manager.py`)
   Operaciones CRUD de metadatos de colecciones (listar, actualizar, eliminar)
   Integración de la tabla de metadatos de colecciones de Cassandra a través de `LibraryTableStore`
   Coordinación de la eliminación de colecciones en cascada en todos los tipos de almacenamiento
   Manejo de solicitudes/respuestas asíncronas con una gestión de errores adecuada

2. **Esquema de metadatos de colecciones** (`trustgraph-base/trustgraph/schema/services/collection.py`)
   Esquemas `CollectionManagementRequest` y `CollectionManagementResponse`
   Esquema `CollectionMetadata` para registros de colecciones
   Definiciones de temas de cola de solicitudes/respuestas de colecciones

3. **Esquema de administración de almacenamiento** (`trustgraph-base/trustgraph/schema/services/storage.py`)
   Esquemas `StorageManagementRequest` y `StorageManagementResponse`
   Temas de cola de administración de almacenamiento definidos
   Formato de mensaje para operaciones de colecciones a nivel de almacenamiento

4. **Esquema de tabla Cassandra de 4 tablas** (`trustgraph-flow/trustgraph/direct/cassandra_kg.py`)
   Claves de partición compuestas para el rendimiento de la consulta
   Tabla `triples_collection` para consultas SPO y seguimiento de eliminación
   Implementación de la eliminación de colecciones con el patrón de lectura y eliminación

### ✅ Migración a patrón basado en configuración - COMPLETADO

**Todos los backends de almacenamiento se han migrado del patrón basado en cola al patrón `CollectionConfigHandler` basado en configuración.**

Migraciones completadas:
✅ `trustgraph-flow/trustgraph/storage/triples/cassandra/write.py`
✅ `trustgraph-flow/trustgraph/storage/triples/neo4j/write.py`
✅ `trustgraph-flow/trustgraph/storage/triples/memgraph/write.py`
✅ `trustgraph-flow/trustgraph/storage/triples/falkordb/write.py`
✅ `trustgraph-flow/trustgraph/storage/doc_embeddings/qdrant/write.py`
✅ `trustgraph-flow/trustgraph/storage/graph_embeddings/qdrant/write.py`
✅ `trustgraph-flow/trustgraph/storage/doc_embeddings/milvus/write.py`
✅ `trustgraph-flow/trustgraph/storage/graph_embeddings/milvus/write.py`
✅ `trustgraph-flow/trustgraph/storage/doc_embeddings/pinecone/write.py`
✅ `trustgraph-flow/trustgraph/storage/graph_embeddings/pinecone/write.py`
✅ `trustgraph-flow/trustgraph/storage/objects/cassandra/write.py`

Todos los backends ahora:
Heredan de `CollectionConfigHandler`
Se registran para notificaciones de configuración push a través de `self.register_config_handler(self.on_collection_config)`
Implementan `create_collection(user, collection, metadata)` y `delete_collection(user, collection)`
Utilizan `collection_exists(user, collection)` para validar antes de escribir
Se sincronizan automáticamente con los cambios del servicio de configuración

Infraestructura basada en cola heredada eliminada:
✅ Esquemas `StorageManagementRequest` y `StorageManagementResponse` eliminados
✅ Definiciones de temas de cola de administración de almacenamiento eliminadas
✅ Consumidor/productor de administración de almacenamiento eliminado de todos los backends
✅ Manejadores `on_storage_management` eliminados de todos los backends
