---
layout: default
title: "Especificación Técnica: Refactorización del Rendimiento de la Base de Conocimiento Cassandra"
parent: "Spanish (Beta)"
---

# Especificación Técnica: Refactorización del Rendimiento de la Base de Conocimiento Cassandra

> **Beta Translation:** This document was translated via Machine Learning and as such may not be 100% accurate. All non-English languages are currently classified as Beta.

**Estado:** Borrador
**Autor:** Asistente
**Fecha:** 2025-09-18

## Resumen

Esta especificación aborda los problemas de rendimiento en la implementación de la base de conocimiento TrustGraph Cassandra y propone optimizaciones para el almacenamiento y la consulta de triples RDF.

## Implementación Actual

### Diseño del Esquema

La implementación actual utiliza un diseño de tabla única en `trustgraph-flow/trustgraph/direct/cassandra_kg.py`:

```sql
CREATE TABLE triples (
    collection text,
    s text,
    p text,
    o text,
    PRIMARY KEY (collection, s, p, o)
);
```

**Índices Secundarios:**
`triples_s` EN `s` (sujeto)
`triples_p` EN `p` (predicado)
`triples_o` EN `o` (objeto)

### Patrones de Consulta

La implementación actual admite 8 patrones de consulta distintos:

1. **get_all(colección, límite=50)** - Recupera todas las triples para una colección
   ```sql
   SELECT s, p, o FROM triples WHERE collection = ? LIMIT 50
   ```

2. **get_s(colección, s, límite=10)** - Consulta por tema.
   ```sql
   SELECT p, o FROM triples WHERE collection = ? AND s = ? LIMIT 10
   ```

3. **get_p(colección, p, límite=10)** - Consulta por predicado
   ```sql
   SELECT s, o FROM triples WHERE collection = ? AND p = ? LIMIT 10
   ```

4. **get_o(colección, o, límite=10)** - Consulta por objeto
   ```sql
   SELECT s, p FROM triples WHERE collection = ? AND o = ? LIMIT 10
   ```

5. **get_sp(colección, s, p, limit=10)** - Consulta por sujeto + predicado
   ```sql
   SELECT o FROM triples WHERE collection = ? AND s = ? AND p = ? LIMIT 10
   ```

6. **get_po(collection, p, o, limit=10)** - Consulta por predicado + objeto ⚠️
   ```sql
   SELECT s FROM triples WHERE collection = ? AND p = ? AND o = ? LIMIT 10 ALLOW FILTERING
   ```

7. **get_os(collection, o, s, limit=10)** - Consulta por objeto + sujeto ⚠️
   ```sql
   SELECT p FROM triples WHERE collection = ? AND o = ? AND s = ? LIMIT 10 ALLOW FILTERING
   ```

8. **get_spo(colección, s, p, o, límite=10)** - Coincidencia exacta de tripleta.
   ```sql
   SELECT s as x FROM triples WHERE collection = ? AND s = ? AND p = ? AND o = ? LIMIT 10
   ```

### Arquitectura Actual

**Archivo: `trustgraph-flow/trustgraph/direct/cassandra_kg.py`**
Clase única `KnowledgeGraph` que gestiona todas las operaciones
Agrupación de conexiones a través de una lista global `_active_clusters`
Nombre de tabla fijo: `"triples"`
Espacio de claves por modelo de usuario
Replicación SimpleStrategy con factor 1

**Puntos de Integración:**
**Ruta de Escritura:** `trustgraph-flow/trustgraph/storage/triples/cassandra/write.py`
**Ruta de Consulta:** `trustgraph-flow/trustgraph/query/triples/cassandra/service.py`
**Almacén de Conocimiento:** `trustgraph-flow/trustgraph/tables/knowledge.py`

## Problemas de Rendimiento Identificados

### Problemas a Nivel de Esquema

1. **Diseño de Clave Primaria Ineficiente**
   Actual: `PRIMARY KEY (collection, s, p, o)`
   Resulta en un agrupamiento deficiente para patrones de acceso comunes
   Obliga al uso de índices secundarios costosos

2. **Uso Excesivo de Índices Secundarios** ⚠️
   Tres índices secundarios en columnas de alta cardinalidad (s, p, o)
   Los índices secundarios en Cassandra son costosos y no escalan bien
   Las consultas 6 y 7 requieren `ALLOW FILTERING`, lo que indica un modelado de datos deficiente

3. **Riesgo de Particiones Calientes**
   Una única clave de partición `collection` puede crear particiones calientes
   Las colecciones grandes se concentrarán en nodos individuales
   No hay estrategia de distribución para el equilibrio de carga

### Problemas a Nivel de Consulta

1. **Uso de ALLOW FILTERING** ⚠️
   Dos tipos de consulta (get_po, get_os) requieren `ALLOW FILTERING`
   Estas consultas escanean múltiples particiones y son extremadamente costosas
   El rendimiento disminuye linealmente con el tamaño de los datos

2. **Patrones de Acceso Ineficientes**
   No hay optimización para patrones de consulta RDF comunes
   Faltan índices compuestos para combinaciones de consulta frecuentes
   No se tiene en cuenta los patrones de recorrido de grafos

3. **Falta de Optimización de Consultas**
   No hay almacenamiento en caché de sentencias preparadas
   No hay sugerencias de consulta ni estrategias de optimización
   No se tiene en cuenta la paginación más allá de un simple LIMIT

## Declaración del Problema

La implementación actual de la base de conocimiento de Cassandra tiene dos cuellos de botella críticos de rendimiento:

### 1. Rendimiento Ineficiente de la Consulta get_po

La consulta `get_po(collection, p, o)` es extremadamente ineficiente debido a que requiere `ALLOW FILTERING`:

```sql
SELECT s FROM triples WHERE collection = ? AND p = ? AND o = ? LIMIT 10 ALLOW FILTERING
```

**¿Por qué esto es problemático:**
`ALLOW FILTERING` obliga a Cassandra a escanear todas las particiones dentro de la colección.
El rendimiento disminuye linealmente con el tamaño de los datos.
Este es un patrón de consulta RDF común (encontrar sujetos que tengan una relación específica de predicado-objeto).
Crea una carga significativa en el clúster a medida que los datos crecen.

### 2. Estrategia de Clustering Deficiente

La clave primaria actual `PRIMARY KEY (collection, s, p, o)` proporciona beneficios de clustering mínimos:

**Problemas con el clustering actual:**
`collection` como clave de partición no distribuye los datos de manera efectiva.
La mayoría de las colecciones contienen datos diversos, lo que hace que el clustering sea ineficaz.
No se tiene en cuenta los patrones de acceso comunes en las consultas RDF.
Las colecciones grandes crean particiones "calientes" en nodos individuales.
Las columnas de clustering (s, p, o) no optimizan para los patrones típicos de recorrido de grafos.

**Impacto:**
Las consultas no se benefician de la localidad de los datos.
Utilización deficiente de la caché.
Distribución desigual de la carga en los nodos del clúster.
Cuellos de botella de escalabilidad a medida que las colecciones crecen.

## Solución Propuesta: Estrategia de Desnormalización de 4 Tablas

### Resumen

Reemplace la única tabla `triples` con cuatro tablas diseñadas específicamente, cada una optimizada para patrones de consulta específicos. Esto elimina la necesidad de índices secundarios y ALLOW FILTERING, al tiempo que proporciona un rendimiento óptimo para todos los tipos de consulta. La cuarta tabla permite una eliminación eficiente de colecciones a pesar de las claves de partición compuestas.

### Nuevo Diseño de Esquema

**Tabla 1: Consultas Centradas en el Sujeto (triples_s)**
```sql
CREATE TABLE triples_s (
    collection text,
    s text,
    p text,
    o text,
    PRIMARY KEY ((collection, s), p, o)
);
```
**Optimiza:** get_s, get_sp, get_os
**Clave de partición:** (colección, s) - Mejor distribución que solo la colección.
**Agrupamiento:** (p, o) - Permite búsquedas eficientes de predicados/objetos para un sujeto.

**Tabla 2: Consultas Predicado-Objeto (triples_p)**
```sql
CREATE TABLE triples_p (
    collection text,
    p text,
    o text,
    s text,
    PRIMARY KEY ((collection, p), o, s)
);
```
**Optimiza:** get_p, get_po (¡elimina ALLOW FILTERING!)
**Clave de partición:** (colección, p) - Acceso directo mediante predicado
**Agrupamiento:** (o, s) - Recorrido eficiente de objeto a sujeto

**Tabla 3: Consultas centradas en objetos (triples_o)**
```sql
CREATE TABLE triples_o (
    collection text,
    o text,
    s text,
    p text,
    PRIMARY KEY ((collection, o), s, p)
);
```
**Optimiza:** get_o
**Clave de partición:** (colección, o) - Acceso directo por objeto
**Clustering:** (s, p) - Recorrido eficiente de sujeto-predicado

**Tabla 4: Gestión de colecciones y consultas SPO (triples_collection)**
```sql
CREATE TABLE triples_collection (
    collection text,
    s text,
    p text,
    o text,
    PRIMARY KEY (collection, s, p, o)
);
```
**Optimiza:** get_spo, delete_collection
**Clave de partición:** solo colección - Permite operaciones eficientes a nivel de colección.
**Clustering:** (s, p, o) - Orden estándar de tripletas.
**Propósito:** Uso dual para búsquedas exactas de SPO y como índice de eliminación.

### Mapeo de consultas

| Consulta original | Tabla de destino | Mejora de rendimiento |
|----------------|-------------|------------------------|
| get_all(collection) | triples_s | PERMITE FILTRADO (aceptable para escaneo) |
| get_s(collection, s) | triples_s | Acceso directo a la partición |
| get_p(collection, p) | triples_p | Acceso directo a la partición |
| get_o(collection, o) | triples_o | Acceso directo a la partición |
| get_sp(collection, s, p) | triples_s | Partición + clustering |
| get_po(collection, p, o) | triples_p | **¡Ya no se permite ALLOW FILTERING!** |
| get_os(collection, o, s) | triples_o | Partición + clustering |
| get_spo(collection, s, p, o) | triples_collection | Búsqueda exacta de clave |
| delete_collection(collection) | triples_collection | Lee el índice, eliminación por lotes de todos |

### Estrategia de eliminación de colecciones

Con claves de partición compuestas, no podemos simplemente ejecutar `DELETE FROM table WHERE collection = ?`. En cambio:

1. **Fase de lectura:** Consulta `triples_collection` para enumerar todas las tripletas:
   ```sql
   SELECT s, p, o FROM triples_collection WHERE collection = ?
   ```
   Esto es eficiente ya que `collection` es la clave de partición para esta tabla.

2. **Fase de eliminación:** Para cada triple (s, p, o), elimine de las 4 tablas utilizando claves de partición completas:
   ```sql
   DELETE FROM triples_s WHERE collection = ? AND s = ? AND p = ? AND o = ?
   DELETE FROM triples_p WHERE collection = ? AND p = ? AND o = ? AND s = ?
   DELETE FROM triples_o WHERE collection = ? AND o = ? AND s = ? AND p = ?
   DELETE FROM triples_collection WHERE collection = ? AND s = ? AND p = ? AND o = ?
   ```
   Agrupado en lotes de 100 para mayor eficiencia.

**Análisis de compensaciones:**
✅ Mantiene un rendimiento óptimo de las consultas con particiones distribuidas.
✅ No hay particiones con alta carga para colecciones grandes.
❌ Lógica de eliminación más compleja (leer y luego eliminar).
❌ Tiempo de eliminación proporcional al tamaño de la colección.

### Beneficios

1. **Elimina ALLOW FILTERING** - Cada consulta tiene una ruta de acceso óptima (excepto el escaneo get_all).
2. **No se requieren índices secundarios** - Cada tabla ES el índice para su patrón de consulta.
3. **Mejor distribución de datos** - Las claves de partición compuestas distribuyen la carga de manera efectiva.
4. **Rendimiento predecible** - El tiempo de consulta es proporcional al tamaño del resultado, no a los datos totales.
5. **Aprovecha las fortalezas de Cassandra** - Diseñado para la arquitectura de Cassandra.
6. **Permite la eliminación de colecciones** - triples_collection sirve como índice de eliminación.

## Plan de implementación

### Archivos que requieren cambios

#### Archivo de implementación principal

**`trustgraph-flow/trustgraph/direct/cassandra_kg.py`** - Se requiere una reescritura completa.

**Métodos actuales a refactorizar:**
```python
# Schema initialization
def init(self) -> None  # Replace single table with three tables

# Insert operations
def insert(self, collection, s, p, o) -> None  # Write to all three tables

# Query operations (API unchanged, implementation optimized)
def get_all(self, collection, limit=50)      # Use triples_by_subject
def get_s(self, collection, s, limit=10)     # Use triples_by_subject
def get_p(self, collection, p, limit=10)     # Use triples_by_po
def get_o(self, collection, o, limit=10)     # Use triples_by_object
def get_sp(self, collection, s, p, limit=10) # Use triples_by_subject
def get_po(self, collection, p, o, limit=10) # Use triples_by_po (NO ALLOW FILTERING!)
def get_os(self, collection, o, s, limit=10) # Use triples_by_subject
def get_spo(self, collection, s, p, o, limit=10) # Use triples_by_subject

# Collection management
def delete_collection(self, collection) -> None  # Delete from all three tables
```

#### Archivos de Integración (No se requieren cambios en la lógica)

**`trustgraph-flow/trustgraph/storage/triples/cassandra/write.py`**
No se necesitan cambios: utiliza la API KnowledgeGraph existente.
Se beneficia automáticamente de las mejoras de rendimiento.

**`trustgraph-flow/trustgraph/query/triples/cassandra/service.py`**
No se necesitan cambios: utiliza la API KnowledgeGraph existente.
Se beneficia automáticamente de las mejoras de rendimiento.

### Archivos de Prueba que Requieren Actualizaciones

#### Pruebas Unitarias
**`tests/unit/test_storage/test_triples_cassandra_storage.py`**
Actualizar las expectativas de las pruebas para los cambios en el esquema.
Agregar pruebas para la consistencia de múltiples tablas.
Verificar que no haya "ALLOW FILTERING" en los planes de consulta.

**`tests/unit/test_query/test_triples_cassandra_query.py`**
Actualizar las aserciones de rendimiento.
Probar los 8 patrones de consulta contra las nuevas tablas.
Verificar el enrutamiento de consultas a las tablas correctas.

#### Pruebas de Integración
**`tests/integration/test_cassandra_integration.py`**
Pruebas de extremo a extremo con el nuevo esquema.
Comparaciones de referencia de rendimiento.
Verificación de la consistencia de los datos en todas las tablas.

**`tests/unit/test_storage/test_cassandra_config_integration.py`**
Actualizar las pruebas de validación de esquema.
Probar escenarios de migración.

### Estrategia de Implementación

#### Fase 1: Esquema y Métodos Centrales
1. **Reescribir el método `init()`** - Crear cuatro tablas en lugar de una.
2. **Reescribir el método `insert()`** - Escrituras por lotes a las cuatro tablas.
3. **Implementar sentencias preparadas** - Para un rendimiento óptimo.
4. **Agregar lógica de enrutamiento de tablas** - Dirigir las consultas a las tablas óptimas.
5. **Implementar la eliminación de colecciones** - Leer de triples_collection, eliminar por lotes de todas las tablas.

#### Fase 2: Optimización de Métodos de Consulta
1. **Reescribir cada método get_*** para usar la tabla óptima.
2. **Eliminar todo el uso de ALLOW FILTERING**.
3. **Implementar el uso eficiente de la clave de clustering**.
4. **Agregar registro del rendimiento de las consultas**.

#### Fase 3: Gestión de Colecciones
1. **Actualizar `delete_collection()`** - Eliminar de las tres tablas.
2. **Agregar verificación de consistencia** - Asegurar que todas las tablas se mantengan sincronizadas.
3. **Implementar operaciones por lotes** - Para operaciones multi-tabla atómicas.

### Detalles Clave de la Implementación

#### Estrategia de Escritura por Lotes
```python
def insert(self, collection, s, p, o):
    batch = BatchStatement()

    # Insert into all four tables
    batch.add(self.insert_subject_stmt, (collection, s, p, o))
    batch.add(self.insert_po_stmt, (collection, p, o, s))
    batch.add(self.insert_object_stmt, (collection, o, s, p))
    batch.add(self.insert_collection_stmt, (collection, s, p, o))

    self.session.execute(batch)
```

#### Lógica de enrutamiento de consultas
```python
def get_po(self, collection, p, o, limit=10):
    # Route to triples_p table - NO ALLOW FILTERING!
    return self.session.execute(
        self.get_po_stmt,
        (collection, p, o, limit)
    )

def get_spo(self, collection, s, p, o, limit=10):
    # Route to triples_collection table for exact SPO lookup
    return self.session.execute(
        self.get_spo_stmt,
        (collection, s, p, o, limit)
    )
```

#### Lógica de eliminación de colecciones
```python
def delete_collection(self, collection):
    # Step 1: Read all triples from collection table
    rows = self.session.execute(
        f"SELECT s, p, o FROM {self.collection_table} WHERE collection = %s",
        (collection,)
    )

    # Step 2: Batch delete from all 4 tables
    batch = BatchStatement()
    count = 0

    for row in rows:
        s, p, o = row.s, row.p, row.o

        # Delete using full partition keys for each table
        batch.add(SimpleStatement(
            f"DELETE FROM {self.subject_table} WHERE collection = ? AND s = ? AND p = ? AND o = ?"
        ), (collection, s, p, o))

        batch.add(SimpleStatement(
            f"DELETE FROM {self.po_table} WHERE collection = ? AND p = ? AND o = ? AND s = ?"
        ), (collection, p, o, s))

        batch.add(SimpleStatement(
            f"DELETE FROM {self.object_table} WHERE collection = ? AND o = ? AND s = ? AND p = ?"
        ), (collection, o, s, p))

        batch.add(SimpleStatement(
            f"DELETE FROM {self.collection_table} WHERE collection = ? AND s = ? AND p = ? AND o = ?"
        ), (collection, s, p, o))

        count += 1

        # Execute every 100 triples to avoid oversized batches
        if count % 100 == 0:
            self.session.execute(batch)
            batch = BatchStatement()

    # Execute remaining deletions
    if count % 100 != 0:
        self.session.execute(batch)

    logger.info(f"Deleted {count} triples from collection {collection}")
```

#### Optimización de sentencias preparadas
```python
def prepare_statements(self):
    # Cache prepared statements for better performance
    self.insert_subject_stmt = self.session.prepare(
        f"INSERT INTO {self.subject_table} (collection, s, p, o) VALUES (?, ?, ?, ?)"
    )
    self.insert_po_stmt = self.session.prepare(
        f"INSERT INTO {self.po_table} (collection, p, o, s) VALUES (?, ?, ?, ?)"
    )
    self.insert_object_stmt = self.session.prepare(
        f"INSERT INTO {self.object_table} (collection, o, s, p) VALUES (?, ?, ?, ?)"
    )
    self.insert_collection_stmt = self.session.prepare(
        f"INSERT INTO {self.collection_table} (collection, s, p, o) VALUES (?, ?, ?, ?)"
    )
    # ... query statements
```

## Estrategia de Migración

### Enfoque de Migración de Datos

#### Opción 1: Despliegue Blue-Green (Recomendado)
1. **Implementar el nuevo esquema junto con el existente** - Utilizar nombres de tabla diferentes temporalmente
2. **Período de escritura dual** - Escribir tanto en el esquema antiguo como en el nuevo durante la transición
3. **Migración en segundo plano** - Copiar los datos existentes a las nuevas tablas
4. **Cambiar las lecturas** - Dirigir las consultas a las nuevas tablas una vez que los datos se hayan migrado
5. **Eliminar las tablas antiguas** - Después del período de verificación

#### Opción 2: Migración In-Place
1. **Adición de esquema** - Crear nuevas tablas en el keyspace existente
2. **Script de migración de datos** - Copia por lotes de la tabla antigua a las nuevas tablas
3. **Actualización de la aplicación** - Implementar el nuevo código después de que se complete la migración
4. **Limpieza de la tabla antigua** - Eliminar la tabla antigua e índices

### Compatibilidad hacia atrás

#### Estrategia de Despliegue
```python
# Environment variable to control table usage during migration
USE_LEGACY_TABLES = os.getenv('CASSANDRA_USE_LEGACY', 'false').lower() == 'true'

class KnowledgeGraph:
    def __init__(self, ...):
        if USE_LEGACY_TABLES:
            self.init_legacy_schema()
        else:
            self.init_optimized_schema()
```

#### Script de Migración
```python
def migrate_data():
    # Read from old table
    old_triples = session.execute("SELECT collection, s, p, o FROM triples")

    # Batch write to new tables
    for batch in batched(old_triples, 100):
        batch_stmt = BatchStatement()
        for row in batch:
            # Add to all three new tables
            batch_stmt.add(insert_subject_stmt, row)
            batch_stmt.add(insert_po_stmt, (row.collection, row.p, row.o, row.s))
            batch_stmt.add(insert_object_stmt, (row.collection, row.o, row.s, row.p))
        session.execute(batch_stmt)
```

### Estrategia de Validación

#### Comprobaciones de Consistencia de Datos
```python
def validate_migration():
    # Count total records in old vs new tables
    old_count = session.execute("SELECT COUNT(*) FROM triples WHERE collection = ?", (collection,))
    new_count = session.execute("SELECT COUNT(*) FROM triples_by_subject WHERE collection = ?", (collection,))

    assert old_count == new_count, f"Record count mismatch: {old_count} vs {new_count}"

    # Spot check random samples
    sample_queries = generate_test_queries()
    for query in sample_queries:
        old_result = execute_legacy_query(query)
        new_result = execute_optimized_query(query)
        assert old_result == new_result, f"Query results differ for {query}"
```

## Estrategia de Pruebas

### Pruebas de Rendimiento

#### Escenarios de Referencia
1. **Comparación del Rendimiento de Consultas**
   Métricas de rendimiento antes y después para los 8 tipos de consultas
   Centrarse en la mejora del rendimiento de get_po (eliminar ALLOW FILTERING)
   Medir la latencia de las consultas bajo varios tamaños de datos

2. **Pruebas de Carga**
   Ejecución concurrente de consultas
   Rendimiento de escritura con operaciones por lotes
   Utilización de memoria y CPU

3. **Pruebas de Escalabilidad**
   Rendimiento con tamaños de colección crecientes
   Distribución de consultas de múltiples colecciones
   Utilización de nodos del clúster

#### Conjuntos de Datos de Prueba
**Pequeño:** 10K triples por colección
**Mediano:** 100K triples por colección
**Grande:** 1M+ triples por colección
**Múltiples colecciones:** Probar la distribución de particiones

### Pruebas Funcionales

#### Actualizaciones de Pruebas Unitarias
```python
# Example test structure for new implementation
class TestCassandraKGPerformance:
    def test_get_po_no_allow_filtering(self):
        # Verify get_po queries don't use ALLOW FILTERING
        with patch('cassandra.cluster.Session.execute') as mock_execute:
            kg.get_po('test_collection', 'predicate', 'object')
            executed_query = mock_execute.call_args[0][0]
            assert 'ALLOW FILTERING' not in executed_query

    def test_multi_table_consistency(self):
        # Verify all tables stay in sync
        kg.insert('test', 's1', 'p1', 'o1')

        # Check all tables contain the triple
        assert_triple_exists('triples_by_subject', 'test', 's1', 'p1', 'o1')
        assert_triple_exists('triples_by_po', 'test', 'p1', 'o1', 's1')
        assert_triple_exists('triples_by_object', 'test', 'o1', 's1', 'p1')
```

#### Actualizaciones de la prueba de integración
```python
class TestCassandraIntegration:
    def test_query_performance_regression(self):
        # Ensure new implementation is faster than old
        old_time = benchmark_legacy_get_po()
        new_time = benchmark_optimized_get_po()
        assert new_time < old_time * 0.5  # At least 50% improvement

    def test_end_to_end_workflow(self):
        # Test complete write -> query -> delete cycle
        # Verify no performance degradation in integration
```

### Plan de Reversión

#### Estrategia de Reversión Rápida
1. **Alternancia de variables de entorno** - Vuelva a las tablas heredadas inmediatamente.
2. **Mantenga las tablas heredadas** - No las elimine hasta que se demuestre el rendimiento.
3. **Alertas de monitoreo** - Desencadenadores de reversión automatizados basados en tasas de error/latencia.

#### Validación de la Reversión
```python
def rollback_to_legacy():
    # Set environment variable
    os.environ['CASSANDRA_USE_LEGACY'] = 'true'

    # Restart services to pick up change
    restart_cassandra_services()

    # Validate functionality
    run_smoke_tests()
```

## Riesgos y Consideraciones

### Riesgos de Rendimiento
**Aumento de la latencia de escritura** - 4 operaciones de escritura por inserción (un 33% más que el enfoque de 3 tablas)
**Sobrecarga de almacenamiento** - 4 veces más espacio de almacenamiento requerido (un 33% más que el enfoque de 3 tablas)
**Fallos en la escritura por lotes** - Se necesita un manejo adecuado de errores
**Complejidad de la eliminación** - La eliminación de la colección requiere un bucle de lectura y eliminación

### Riesgos Operacionales
**Complejidad de la migración** - Migración de datos para conjuntos de datos grandes
**Desafíos de consistencia** - Asegurar que todas las tablas permanezcan sincronizadas
**Lagunas de monitoreo** - Se necesitan nuevas métricas para las operaciones de múltiples tablas

### Estrategias de Mitigación
1. **Implementación gradual** - Comenzar con colecciones pequeñas
2. **Monitoreo integral** - Realizar un seguimiento de todas las métricas de rendimiento
3. **Validación automatizada** - Verificación continua de la consistencia
4. **Capacidad de reversión rápida** - Selección de tablas basada en el entorno

## Criterios de Éxito

### Mejoras de Rendimiento
[ ] **Eliminar ALLOW FILTERING** - Las consultas get_po y get_os se ejecutan sin filtrado
[ ] **Reducción de la latencia de la consulta** - Mejora del 50% o más en los tiempos de respuesta de las consultas
[ ] **Mejor distribución de la carga** - Sin particiones "calientes", distribución uniforme de la carga en los nodos del clúster
[ ] **Rendimiento escalable** - El tiempo de consulta es proporcional al tamaño del resultado, no a la cantidad total de datos

### Requisitos Funcionales
[ ] **Compatibilidad de la API** - Todo el código existente continúa funcionando sin cambios
[ ] **Consistencia de datos** - Las tres tablas permanecen sincronizadas
[ ] **Cero pérdida de datos** - La migración preserva todas las triples existentes
[ ] **Compatibilidad con versiones anteriores** - Capacidad de volver al esquema heredado

### Requisitos Operacionales
[ ] **Migración segura** - Implementación blue-green con capacidad de reversión
[ ] **Cobertura de monitoreo** - Métricas integrales para operaciones de múltiples tablas
[ ] **Cobertura de pruebas** - Todos los patrones de consulta se prueban con puntos de referencia de rendimiento
[ ] **Documentación** - Procedimientos de implementación y operación actualizados

## Cronograma

### Fase 1: Implementación
[ ] Reescribir `cassandra_kg.py` con el esquema de múltiples tablas
[ ] Implementar operaciones de escritura por lotes
[ ] Agregar optimización de sentencias preparadas
[ ] Actualizar pruebas unitarias

### Fase 2: Pruebas de Integración
[ ] Actualizar pruebas de integración
[ ] Pruebas de rendimiento
[ ] Pruebas de carga con volúmenes de datos realistas
[ ] Scripts de validación para la consistencia de los datos

### Fase 3: Planificación de la Migración
[ ] Scripts de implementación blue-green
[ ] Herramientas de migración de datos
[ ] Actualizaciones del panel de monitoreo
[ ] Procedimientos de reversión

### Fase 4: Despliegue en Producción
[ ] Implementación gradual en producción
[ ] Monitoreo y validación del rendimiento
[ ] Limpieza de tablas heredadas
[ ] Actualizaciones de la documentación

## Conclusión

Esta estrategia de desnormalización de múltiples tablas aborda directamente los dos cuellos de botella de rendimiento críticos:

1. **Elimina el costoso ALLOW FILTERING** al proporcionar estructuras de tabla óptimas para cada patrón de consulta
2. **Mejora la eficacia de la agrupación** a través de claves de partición compuestas que distribuyen la carga de manera adecuada

El enfoque aprovecha las fortalezas de Cassandra al tiempo que mantiene la compatibilidad total de la API, lo que garantiza que el código existente se beneficie automáticamente de las mejoras de rendimiento.
