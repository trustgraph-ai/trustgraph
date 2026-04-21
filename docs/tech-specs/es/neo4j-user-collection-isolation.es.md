---
layout: default
title: "Soporte de aislamiento de usuarios/colecciones en Neo4j"
parent: "Spanish (Beta)"
---

# Soporte de aislamiento de usuarios/colecciones en Neo4j

> **Beta Translation:** This document was translated via Machine Learning and as such may not be 100% accurate. All non-English languages are currently classified as Beta.

## Declaración del problema

La implementación actual de almacenamiento y consulta de triples en Neo4j carece de aislamiento de usuarios/colecciones, lo que genera una vulnerabilidad de seguridad para entornos multi-inquilinos. Todos los triples se almacenan en el mismo espacio de grafo sin ningún mecanismo para evitar que los usuarios accedan a los datos de otros usuarios o mezclen colecciones.

A diferencia de otros backends de almacenamiento en TrustGraph:
- **Cassandra**: Utiliza espacios de claves y tablas separados por usuario y colección
- **Almacenes vectoriales** (Milvus, Qdrant, Pinecone): Utilizan espacios de nombres específicos de la colección
- **Neo4j**: Actualmente comparte todos los datos en un único grafo (vulnerabilidad de seguridad)

## Arquitectura actual

### Modelo de datos
- **Nodos**: Etiqueta `:Node` con propiedad `uri`, etiqueta `:Literal` con propiedad `value`
- **Relaciones**: Etiqueta `:Rel` con propiedad `uri`
- **Índices**: `Node.uri`, `Literal.value`, `Rel.uri`

### Flujo de mensajes
- Los mensajes `Triples` contienen los campos `metadata.user` y `metadata.collection`
- El servicio de almacenamiento recibe la información del usuario/colección, pero la ignora
- El servicio de consulta espera `user` y `collection` en `TriplesQueryRequest`, pero los ignora

### Problema de seguridad actual
```cypher
# Cualquier usuario puede consultar cualquier dato - sin aislamiento
MATCH (src:Node)-[rel:Rel]->(dest:Node) 
RETURN src.uri, rel.uri, dest.uri
```

## Solución propuesta: Filtrado basado en propiedades (Recomendado)

### Descripción general
Añadir las propiedades `user` y `collection` a todos los nodos y relaciones, y luego filtrar todas las operaciones por estas propiedades. Este enfoque proporciona un fuerte aislamiento manteniendo la flexibilidad de consulta y la compatibilidad con versiones anteriores.

### Cambios en el modelo de datos

#### Estructura de nodos mejorada
```cypher
// Entidades de nodo
CREATE (n:Node {
  uri: "http://example.com/entity1",
  user: "john_doe", 
  collection: "production_v1"
})

// Entidades de literal
CREATE (n:Literal {
  value: "literal value",
  user: "john_doe",
  collection: "production_v1" 
})
```

#### Estructura de relaciones mejorada
```cypher
// Relaciones con propiedades user/collection
CREATE (src)-[:Rel {
  uri: "http://example.com/predicate1",
  user: "john_doe",
  collection: "production_v1"
}]->(dest)
```

#### Índices actualizados
```cypher
// Índices compuestos para un filtrado eficiente
CREATE INDEX node_user_collection_uri FOR (n:Node) ON (n.user, n.collection, n.uri);
CREATE INDEX literal_user_collection_value FOR (n:Literal) ON (n.user, n.collection, n.value);
CREATE INDEX rel_user_collection_uri FOR ()-[r:Rel]-() ON (r.user, r.collection, r.uri);

// Mantener índices existentes para la compatibilidad con versiones anteriores (opcional)
CREATE INDEX Node_uri FOR (n:Node) ON (n.uri);
CREATE INDEX Literal_value FOR (n:Literal) ON (n.value);
CREATE INDEX Rel_uri FOR ()-[r:Rel]-() ON (r.uri);
```

### Cambios de implementación

#### Servicio de almacenamiento (`write.py`)

**Código actual:**
```python
def create_node(self, uri):
    summary = self.io.execute_query(
        "MERGE (n:Node {uri: $uri})",
        uri=uri, database_=self.db,
    ).summary
```

**Código actualizado:**
```python
def create_node(self, uri, user, collection):
    summary = self.io.execute_query(
        "MERGE (n:Node {uri: $uri, user: $user, collection: $collection})",
        uri=uri, user=user, collection=collection, database_=self.db,
    ).summary
```

#### Función query
```python
def query_triples(self, query):
    # Implementar lógica para filtrar por usuario y colección en la consulta
    # Por ejemplo, reemplazar 'user' y 'collection' en la consulta
    # Usar la función de ejecución de consultas de Neo4j para reemplazar
    # los marcadores de posición con los valores del usuario y la colección
    # y luego ejecutar la consulta.
    # Ejemplo (pseudocódigo):
    # resultado = neo4j.execute_query(query.replace("user", self.user), self.collection)
    # return resultado
    pass
```

#### Función store_triples
```python
def store_triples(self, triples):
    # Implementar lógica para almacenar triples con las propiedades user y collection
    # Por ejemplo, añadir las propiedades user y collection a los nodos al crear
    #  nuevos nodos y relaciones.
    pass
```

### Pruebas

### Pruebas unitarias
```python
def test_user_collection_isolation():
    # Almacenar triples para user1/collection1
    processor.store_triples(triples_user1_coll1)
    
    # Almacenar triples para user2/collection2
    processor.store_triples(triples_user2_coll2)
    
    # Consultar como user1 solo debería devolver datos de user1/collection1
    resultados = processor.query_triples(query_user1_coll1)
    assert all_results_belong_to_user1_coll1(resultados)
    
    # Consultar como user2 solo debería devolver datos de user2/collection2
    resultados = processor.query_triples(query_user2_coll2)
    assert all_results_belong_to_user2_coll2(resultados)
```

### Pruebas de integración
- Escenarios de múltiples usuarios con datos superpuestos
- Consultas de cross-colección (deberían fallar)
- Pruebas de migración con datos existentes
- Pruebas de rendimiento con grandes conjuntos de datos

### Pruebas de seguridad
- Intentar consultar datos de otros usuarios
- Ataques de inyección SQL en parámetros de usuario/colección
- Verificar el aislamiento completo bajo diferentes patrones de consulta

## Consideraciones de rendimiento

### Estrategia de índice
- Índices compuestos en `(user, collection, uri)` para un filtrado óptimo
- Considerar índices parciales si algunas colecciones son mucho más grandes
- Supervisar el uso y el rendimiento de los índices

### Optimización de consultas
- Utilizar EXPLAIN para verificar el uso de índices en las consultas filtradas
- Considerar el almacenamiento en caché de resultados para datos accedidos con frecuencia
- Perfilar el uso de memoria con un gran número de usuarios/colecciones

### Escalabilidad
- Cada combinación de usuario/colección crea islas de datos separadas
- Supervisar el tamaño de la base de datos y el uso de la piscina de conexiones
- Considerar estrategias de escalado horizontal si es necesario

## Seguridad y cumplimiento

### Garantías de aislamiento de datos
- **Físico**: Todos los datos del usuario almacenados con propiedades de usuario/colección explícitas
- **Lógico**: Todas las consultas filtradas por contexto de usuario/colección
- **Control de acceso**: Validación a nivel de servicio para evitar el acceso no autorizado

### Requisitos de auditoría
- Registrar todos los accesos de datos con contexto de usuario/colección
- Rastrear las actividades de migración y los movimientos de datos
- Supervisar los intentos de violar el aislamiento

### Consideraciones de cumplimiento
- GDPR: Mayor capacidad para localizar y eliminar datos específicos del usuario
- SOC2: Claros controles de aislamiento de datos y acceso
- HIPAA: Fuerte aislamiento de inquilinos para datos de atención médica

## Riesgos y mitigaciones

| Riesgo | Impacto | Probabilidad | Mitigación |
|------|--------|------------|------------|
| Consulta sin filtro de usuario/colección | Alto | Medio | Validación obligatoria, pruebas exhaustivas |
| Degradación del rendimiento | Medio | Bajo | Optimización del índice, perfilado de consultas |
| Corrupción de datos durante la migración | Alto | Bajo | Estrategia de copia de seguridad, procedimientos de reversión |
| Complejidad de consultas multi-colección | Medio | Medio | Documentar los patrones de consulta, proporcionar ejemplos |

## Criterios de éxito

1. **Seguridad**: Cero acceso de datos cruzado de usuarios en producción
2. **Rendimiento**: <10% de impacto en el rendimiento de las consultas en comparación con las consultas no filtradas
3. **Migración**: 100% de los datos existentes migrados sin pérdida de datos
4. **Usabilidad**: Todos los patrones de consulta existentes funcionan con contexto de usuario/colección
5. **Cumplimiento**: Rastro de auditoría completo del acceso de datos de usuario/colección

## Conclusión

El enfoque de filtrado basado en propiedades proporciona el mejor equilibrio de seguridad, rendimiento y mantenibilidad para añadir aislamiento de usuarios/colecciones a Neo4j. Se alinea con los patrones de multi-inquilinos existentes de TrustGraph al tiempo que aprovecha las fortalezas de Neo4j en la consulta y el indexado de grafos.

Esta solución garantiza que el backend de Neo4j de TrustGraph cumpla con los mismos estándares de seguridad que otros backends de almacenamiento, evitando las vulnerabilidades de aislamiento de datos al tiempo que mantiene la flexibilidad y el poder de las consultas de grafos.
