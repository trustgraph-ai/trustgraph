# Gestión del ciclo de vida del almacén de vectores

## Resumen

Este documento describe cómo TrustGraph gestiona las colecciones de almacenes de vectores en diferentes implementaciones de backend (Qdrant, Pinecone, Milvus). El diseño aborda el desafío de admitir incrustaciones con diferentes dimensiones sin codificar valores de dimensión.

## Declaración del problema

Los almacenes de vectores requieren que se especifique la dimensión de la incrustación al crear colecciones/índices. Sin embargo:
Los diferentes modelos de incrustación producen diferentes dimensiones (por ejemplo, 384, 768, 1536)
La dimensión no se conoce hasta que se genera la primera incrustación
Una sola colección de TrustGraph puede recibir incrustaciones de múltiples modelos
Codificar una dimensión (por ejemplo, 384) causa fallos con otros tamaños de incrustación

## Principios de diseño

1. **Creación perezosa**: Las colecciones se crean bajo demanda durante la primera escritura, no durante las operaciones de gestión de colecciones.
2. **Nombres basados en la dimensión**: Los nombres de las colecciones incluyen la dimensión de la incrustación como sufijo.
3. **Degradación gradual**: Las consultas contra colecciones inexistentes devuelven resultados vacíos, no errores.
4. **Soporte para múltiples dimensiones**: Una sola colección lógica puede tener múltiples colecciones físicas (una por dimensión).

## Arquitectura

### Convención de nombres de colecciones

Las colecciones del almacén de vectores utilizan sufijos de dimensión para admitir múltiples tamaños de incrustación:

**Incrustaciones de documentos:**
Qdrant: `d_{user}_{collection}_{dimension}`
Pinecone: `d-{user}-{collection}-{dimension}`
Milvus: `doc_{user}_{collection}_{dimension}`

**Incrustaciones de gráficos:**
Qdrant: `t_{user}_{collection}_{dimension}`
Pinecone: `t-{user}-{collection}-{dimension}`
Milvus: `entity_{user}_{collection}_{dimension}`

Ejemplos:
`d_alice_papers_384` - Colección de documentos de Alice con incrustaciones de 384 dimensiones
`d_alice_papers_768` - Misma colección lógica con incrustaciones de 768 dimensiones
`t_bob_knowledge_1536` - Gráfico de conocimiento de Bob con incrustaciones de 1536 dimensiones

### Fases del ciclo de vida

#### 1. Solicitud de creación de colección

**Flujo de solicitud:**
```
User/System → Librarian → Storage Management Topic → Vector Stores
```

**Comportamiento:**
El bibliotecario transmite las solicitudes `create-collection` a todos los backends de almacenamiento.
Los procesadores de almacenes vectoriales reconocen la solicitud, pero **no crean colecciones físicas**.
La respuesta se devuelve inmediatamente con éxito.
La creación real de la colección se pospone hasta la primera escritura.

**Justificación:**
La dimensión es desconocida en el momento de la creación.
Evita la creación de colecciones con dimensiones incorrectas.
Simplifica la lógica de gestión de colecciones.

#### 2. Operaciones de escritura (Creación diferida)

**Flujo de escritura:**
```
Data → Storage Processor → Check Collection → Create if Needed → Insert
```

**Comportamiento:**
1. Extraer la dimensión de incrustación del vector: `dim = len(vector)`
2. Construir el nombre de la colección con el sufijo de dimensión
3. Verificar si la colección existe con esa dimensión específica
4. Si no existe:
   Crear la colección con la dimensión correcta
   Registrar: `"Lazily creating collection {name} with dimension {dim}"`
5. Insertar la incrustación en la colección específica de la dimensión

**Escenario de ejemplo:**
```
1. User creates collection "papers"
   → No physical collections created yet

2. First document with 384-dim embedding arrives
   → Creates d_user_papers_384
   → Inserts data

3. Second document with 768-dim embedding arrives
   → Creates d_user_papers_768
   → Inserts data

Result: Two physical collections for one logical collection
```

#### 3. Operaciones de consulta

**Flujo de consulta:**
```
Query Vector → Determine Dimension → Check Collection → Search or Return Empty
```

**Comportamiento:**
1. Extraer la dimensión del vector de consulta: `dim = len(vector)`
2. Construir el nombre de la colección con el sufijo de dimensión
3. Comprobar si la colección existe
4. Si existe:
   Realizar una búsqueda de similitud
   Devolver los resultados
5. Si no existe:
   Registrar: `"Collection {name} does not exist, returning empty results"`
   Devolver una lista vacía (no se genera ningún error)

**Múltiples Dimensiones en la Misma Consulta:**
Si la consulta contiene vectores de diferentes dimensiones
Cada dimensión consulta su colección correspondiente
Los resultados se agregan
Las colecciones faltantes se omiten (no se consideran errores)

**Justificación:**
Consultar una colección vacía es un caso de uso válido
Devolver resultados vacíos es semánticamente correcto
Evita errores durante el inicio del sistema o antes de la ingesta de datos

#### 4. Eliminación de Colecciones

**Flujo de Eliminación:**
```
Delete Request → List All Collections → Filter by Prefix → Delete All Matches
```

**Comportamiento:**
1. Construir el patrón de prefijo: `d_{user}_{collection}_` (observar el guion bajo al final)
2. Listar todas las colecciones en el almacén vectorial
3. Filtrar las colecciones que coincidan con el prefijo
4. Eliminar todas las colecciones que coincidan
5. Registrar cada eliminación: `"Deleted collection {name}"`
6. Registro resumido: `"Deleted {count} collection(s) for {user}/{collection}"`

**Ejemplo:**
```
Collections in store:
- d_alice_papers_384
- d_alice_papers_768
- d_alice_reports_384
- d_bob_papers_384

Delete "papers" for alice:
→ Deletes: d_alice_papers_384, d_alice_papers_768
→ Keeps: d_alice_reports_384, d_bob_papers_384
```

**Justificación:**
Asegura una limpieza completa de todas las variantes de dimensión.
La coincidencia de patrones evita la eliminación accidental de colecciones no relacionadas.
Operación atómica desde la perspectiva del usuario (todas las dimensiones se eliminan juntas).

## Características de comportamiento

### Operaciones normales

**Creación de colecciones:**
✓ Devuelve éxito inmediatamente.
✓ No se asigna almacenamiento físico.
✓ Operación rápida (sin E/S de backend).

**Primera escritura:**
✓ Crea la colección con la dimensión correcta.
✓ Ligeramente más lenta debido a la sobrecarga de la creación de la colección.
✓ Las escrituras posteriores a la misma dimensión son rápidas.

**Consultas antes de cualquier escritura:**
✓ Devuelve resultados vacíos.
✓ No hay errores ni excepciones.
✓ El sistema permanece estable.

**Escrituras de dimensiones mixtas:**
✓ Crea automáticamente colecciones separadas por dimensión.
✓ Cada dimensión está aislada en su propia colección.
✓ No hay conflictos de dimensiones ni errores de esquema.

**Eliminación de colecciones:**
✓ Elimina todas las variantes de dimensión.
✓ Limpieza completa.
✓ No hay colecciones huérfanas.

### Casos límite

**Múltiples modelos de incrustación:**
```
Scenario: User switches from model A (384-dim) to model B (768-dim)
Behavior:
- Both dimensions coexist in separate collections
- Old data (384-dim) remains queryable with 384-dim vectors
- New data (768-dim) queryable with 768-dim vectors
- Cross-dimension queries return results only for matching dimension
```

**Primeras Escrituras Concurrentes:**
```
Scenario: Multiple processes write to same collection simultaneously
Behavior:
- Each process checks for existence before creating
- Most vector stores handle concurrent creation gracefully
- If race condition occurs, second create is typically idempotent
- Final state: Collection exists and both writes succeed
```

**Migración de Dimensiones:**
```
Scenario: User wants to migrate from 384-dim to 768-dim embeddings
Behavior:
- No automatic migration
- Old collection (384-dim) persists
- New collection (768-dim) created on first new write
- Both dimensions remain accessible
- Manual deletion of old dimension collections possible
```

**Consultas de Colecciones Vacías:**
```
Scenario: Query a collection that has never received data
Behavior:
- Collection doesn't exist (never created)
- Query returns empty list
- No error state
- System logs: "Collection does not exist, returning empty results"
```

## Notas de Implementación

### Detalles Específicos del Backend de Almacenamiento

**Qdrant:**
Utiliza `collection_exists()` para verificaciones de existencia
Utiliza `get_collections()` para listar durante la eliminación
La creación de colecciones requiere `VectorParams(size=dim, distance=Distance.COSINE)`

**Pinecone:**
Utiliza `has_index()` para verificaciones de existencia
Utiliza `list_indexes()` para listar durante la eliminación
La creación de índices requiere esperar el estado "ready"
La especificación serverless se configura con la región de la nube

**Milvus:**
Las clases directas (`DocVectors`, `EntityVectors`) gestionan el ciclo de vida
Caché interno `self.collections[(dim, user, collection)]` para mejorar el rendimiento
Los nombres de las colecciones se sanitizan (solo alfanumérico y guión bajo)
Admite esquemas con IDs de auto-incremento

### Consideraciones de Rendimiento

**Latencia de la Primera Escritura:**
Sobrecarga adicional debido a la creación de la colección
Qdrant: ~100-500ms
Pinecone: ~10-30 segundos (provisionamiento serverless)
Milvus: ~500-2000ms (incluye indexación)

**Rendimiento de la Consulta:**
La verificación de existencia agrega una sobrecarga mínima (~1-10ms)
No hay impacto en el rendimiento una vez que la colección existe
Cada colección de dimensiones se optimiza de forma independiente

**Sobrecarga de Almacenamiento:**
Metadatos mínimos por colección
La principal sobrecarga es el almacenamiento por dimensión
Compromiso: Espacio de almacenamiento vs. flexibilidad de las dimensiones

## Consideraciones Futuras

**Consolidación Automática de Dimensiones:**
Se podría agregar un proceso en segundo plano para identificar y fusionar variantes de dimensiones no utilizadas
Requeriría re-embedding o reducción de dimensiones

**Descubrimiento de Dimensiones:**
Se podría exponer una API para listar todas las dimensiones utilizadas para una colección
Útil para la administración y el monitoreo

**Preferencia de Dimensión Predeterminada:**
Se podría rastrear la dimensión "primaria" por colección
Utilizar para consultas cuando el contexto de la dimensión no está disponible

**Cuotas de Almacenamiento:**
Es posible que se necesiten límites de dimensiones por colección
Prevenir la proliferación de variantes de dimensiones

## Notas de Migración

**Desde el Sistema de Sufijo de Dimensión Anterior:**
Colecciones antiguas: `d_{user}_{collection}` (sin sufijo de dimensión)
Colecciones nuevas: `d_{user}_{collection}_{dim}` (con sufijo de dimensión)
No hay migración automática: las colecciones antiguas permanecen accesibles
Considere un script de migración manual si es necesario
Se pueden ejecutar ambos esquemas de nombres simultáneamente

## Referencias

Gestión de Colecciones: `docs/tech-specs/collection-management.md`
Esquema de Almacenamiento: `trustgraph-base/trustgraph/schema/services/storage.py`
Servicio de Bibliotecario: `trustgraph-flow/trustgraph/librarian/service.py`
