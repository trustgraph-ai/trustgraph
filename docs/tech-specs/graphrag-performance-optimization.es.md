# Especificación Técnica de Optimización de Rendimiento de GraphRAG

## Resumen

Esta especificación describe optimizaciones de rendimiento integrales para el algoritmo GraphRAG (Graph Retrieval-Augmented Generation) en TrustGraph. La implementación actual sufre de cuellos de botella de rendimiento significativos que limitan la escalabilidad y los tiempos de respuesta. Esta especificación aborda cuatro áreas principales de optimización:

1. **Optimización de la Recorrido del Grafo**: Eliminar consultas ineficientes a la base de datos y implementar exploración de grafos por lotes.
2. **Optimización de la Resolución de Etiquetas**: Reemplazar la obtención secuencial de etiquetas con operaciones paralelas/por lotes.
3. **Mejora de la Estrategia de Almacenamiento en Caché**: Implementar un almacenamiento en caché inteligente con desalojo LRU (Least Recently Used) y precarga.
4. **Optimización de Consultas**: Agregar memorización de resultados y almacenamiento en caché de incrustaciones para mejorar los tiempos de respuesta.

## Objetivos

- **Reducir el Volumen de Consultas a la Base de Datos**: Lograr una reducción del 50-80% en el volumen total de consultas a la base de datos a través del procesamiento por lotes y el almacenamiento en caché.
- **Mejorar los Tiempos de Respuesta**: Reducir el tiempo de construcción de subgrafos en un factor de 3 a 5 y el tiempo de resolución de etiquetas en un factor de 2 a 3.
- **Mejorar la Escalabilidad**: Compatibilizar con grafos de conocimiento más grandes con una mejor gestión de la memoria.
- **Mantener la Precisión**: Preservar la funcionalidad existente de GraphRAG y la calidad de los resultados.
- **Habilitar la Concurrencia**: Mejorar las capacidades de procesamiento paralelo para múltiples solicitudes concurrentes.
- **Reducir la Huella de Memoria**: Implementar estructuras de datos eficientes y gestión de la memoria.
- **Agregar Observabilidad**: Incluir métricas de rendimiento y capacidades de monitoreo.
- **Garantizar la Confiabilidad**: Agregar un manejo adecuado de errores y mecanismos de tiempo de espera.

## Antecedentes

La implementación actual de GraphRAG en `trustgraph-flow/trustgraph/retrieval/graph_rag/graph_rag.py` presenta varios problemas de rendimiento críticos que afectan gravemente la escalabilidad del sistema:

### Problemas de Rendimiento Actuales

**1. Recorrido Ineficiente del Grafo (`follow_edges` function, líneas 79-127)**
- Realiza 3 consultas separadas a la base de datos por entidad y nivel de profundidad.
- Patrón de consulta: consultas basadas en sujeto, predicado y objeto para cada entidad.
- Sin procesamiento por lotes: Cada consulta procesa solo una entidad a la vez.
- Sin detección de ciclos: Puede volver a visitar los mismos nodos varias veces.
- La implementación recursiva sin memorización conduce a una complejidad exponencial.
- Complejidad temporal: O(entidades × max_path_length × triple_limit³)

**2. Resolución Secuencial de Etiquetas (`get_labelgraph` function, líneas 144-171)**
- Procesa cada componente de triple (sujeto, predicado, objeto) de forma secuencial.
- Cada llamada a `maybe_label` potencialmente desencadena una consulta a la base de datos.
- No hay ejecución paralela ni procesamiento por lotes de las consultas de etiquetas.
- Resulta en hasta 3 consultas individuales a la base de datos por tamaño del subgrafo.

**3. Estrategia de Almacenamiento en Caché Primitiva (`maybe_label` function, líneas 62-77)**
- Un diccionario de caché simple sin límites de tamaño ni TTL (Time To Live).
- No hay política de desalojo de caché, lo que lleva a un crecimiento ilimitado de la memoria.
- Las fallas de caché desencadenan consultas individuales a la base de datos.
- No hay precarga ni calentamiento inteligente de la caché.

**4. Patrones de Consulta Subóptimos**
- Las consultas de similitud de vectores de entidades no se almacenan en caché entre solicitudes similares.
- No hay memorización de resultados para patrones de consulta repetidos.
- Faltan optimizaciones de consulta para patrones de acceso comunes.

**5. Problemas Críticos del Ciclo de Vida de los Objetos (`rag.py:96-102`)**
- **El objeto GraphRag se recrea por solicitud**: Se crea una nueva instancia para cada consulta, perdiendo todos los beneficios de la caché.
- **El objeto Query tiene una vida útil extremadamente corta**: Se crea y destruye dentro de la ejecución de una sola consulta (líneas 201-207).
- **La caché de etiquetas se restablece por solicitud**: El calentamiento de la caché y el conocimiento acumulado se pierden entre las solicitudes.
- **Sobrecarga de recreación del cliente**: Los clientes de la base de datos se restablecen potencialmente para cada solicitud.
- **No hay optimización entre solicitudes**: No se puede beneficiar de patrones de consulta o uso compartido de resultados.

### Análisis del Impacto en el Rendimiento

Escenario de peor caso actual para una consulta típica:
- **Recuperación de Entidades**: 1 consulta de similitud de vectores.
- **Recorrido del Grafo**: consultas de entidades × max_path_length × 3 × triple_limit.
- **Resolución de Etiquetas**: consultas individuales de tamaño del subgrafo × 3 de etiquetas.

Para parámetros predeterminados (50 entidades, longitud de ruta 2, límite de triple 30, tamaño de subgrafo 150):
- **Número mínimo de consultas**: 1 + (50 × 2 × 3 × 30) + (150 × 3) = **9.451 consultas a la base de datos**.
- **Tiempo de respuesta**: 15-30 segundos para grafos de tamaño moderado.
- **Uso de memoria**: Crecimiento ilimitado de la caché con el tiempo.
- **Eficacia de la caché**: 0% - las cachés se restablecen en cada solicitud.
- **Sobrecarga de creación de objetos**: Se crean/destruyen objetos GraphRag + Query por solicitud.

Esta especificación aborda estas deficiencias implementando consultas por lotes, almacenamiento en caché inteligente y procesamiento paralelo. Al optimizar los patrones de consulta y el acceso a los datos, TrustGraph puede:
- Compatibilizar con grafos de conocimiento a escala empresarial con millones de entidades.
- Proporcionar tiempos de respuesta de subsegundo para consultas típicas.
- Manejar cientos de solicitudes concurrentes de GraphRAG.
- Escalar de manera eficiente con el tamaño y la complejidad del grafo.

## Diseño Técnico

### Arquitectura

La optimización del rendimiento de GraphRAG requiere los siguientes componentes técnicos:

#### 1. **Refactorización Arquitectónica del Ciclo de Vida de los Objetos**
   - **Hacer que GraphRag tenga una vida útil prolongada**: Mover la instancia de GraphRag al nivel del Procesador para la persistencia entre solicitudes.
   - **Preservar las cachés**: Mantener la caché de etiquetas, la caché de incrustaciones y la caché de resultados de consulta entre las solicitudes.
   - **Optimizar el objeto Query**: Refactorizar Query como un contexto de ejecución ligero, no como un contenedor de datos.
   - **Persistencia de la conexión**: Mantener las conexiones del cliente de la base de datos entre las solicitudes.

   Módulo: `trustgraph-flow/trustgraph/retrieval/graph_rag/rag.py` (modificado)

#### 2. **Motor de Recorrido del Grafo Optimizada**
   - Reemplazar `follow_edges` recursivo con una búsqueda en amplitud iterativa.
   - Implementar procesamiento por lotes de entidades en cada nivel de recorrido.
   - Agregar detección de ciclos utilizando el seguimiento de nodos visitados.
   - Incluir finalización temprana cuando se alcanzan los límites.

   Módulo: `trustgraph-flow/trustgraph/retrieval/graph_rag/optimized_traversal.py`

#### 3. **Sistema de Resolución de Etiquetas Paralelo**
   - Consultas de etiquetas por lotes para múltiples entidades simultáneamente.
   - Implementar patrones async/await para el acceso concurrente a la base de datos.
   - Agregar precarga inteligente para patrones de etiquetas comunes.
   - Incluir estrategias de calentamiento de etiquetas.

   Módulo: `trustgraph-flow/trustgraph/retrieval/graph_rag/label_resolver.py`

#### 4. **Capa de Almacenamiento en Caché Conservadora**
   - Caché LRU con un TTL (Tiempo de Vida) corto para las etiquetas (5 minutos) para equilibrar el rendimiento y la coherencia.
   - Métricas de caché y monitoreo de la tasa de aciertos.
   - **No se almacena en caché las incrustaciones**: Ya se almacenan en caché por consulta, no hay beneficio entre consultas.
   - **No se almacenan en caché los resultados de la consulta**: Debido a las preocupaciones sobre la consistencia de la mutación del grafo.

   Módulo: `trustgraph-flow/trustgraph/retrieval/graph_rag/cache_manager.py`

#### 5. **Marco de Optimización de Consultas**
   - Análisis y sugerencias de optimización de patrones de consulta.
   - Coordinador de consultas por lotes para el acceso a la base de datos.
   - Pooling de conexiones y gestión de tiempos de espera de consulta.
   - Monitoreo de rendimiento y recopilación de métricas.

   Módulo: `trustgraph-flow/trustgraph/retrieval/graph_rag/query_optimizer.py`

### Modelos de Datos

#### Estado de Recorrido del Grafo Optimizada

El motor de recorrido mantiene el siguiente estado:

```python
@dataclass
class GraphTraversalState:
    current_node: Node
    path: List[Node]
    visited_nodes: Set[Node]
```

#### Caching
```python
class Cache:
    def __init__(self, max_size: int):
        self.cache = {}
        self.max_size = max_size

    def get(self, key):
        if key in self.cache:
            return self.cache.pop(key)
        return None

    def put(self, key, value):
        if len(self.cache) >= self.max_size:
            # Remove least recently used
            oldest_key = next(iter(self.cache))
            del self.cache[oldest_key]
        self.cache[key] = value
```

#### PerformanceMetrics
```python
@dataclass
class PerformanceMetrics:
    total_queries: int
    cache_hits: int
    cache_misses: int
    avg_response_time: float
    subgraph_construction_time: float
    label_resolution_time: float
    total_entities_processed: int
    memory_usage_mb: float
```

### Seguridad

**Prevenir Inyección de Consultas:**
- Validar todos los identificadores de entidad y parámetros de consulta.
- Usar consultas parametrizadas para todas las interacciones con la base de datos.
- Implementar límites de complejidad de consulta para prevenir ataques de denegación de servicio.

**Protección de Recursos:**
- Hacer cumplir los límites máximos del tamaño del subgrafo.
- Implementar tiempos de espera de consulta para evitar el agotamiento de recursos.
- Agregar monitoreo del uso de la memoria y límites.

**Control de Acceso:**
- Mantener el aislamiento existente de usuarios y colecciones.
- Agregar registro de auditoría para operaciones que afectan el rendimiento.
- Implementar la limitación de velocidad para las operaciones costosas.

## Consideraciones de Rendimiento

### Mejoras de Rendimiento Esperadas

**Reducción de Consultas:**
- Actual: ~9.000+ consultas por solicitud típica.
- Optimizada: ~50-100 consultas por lotes (reducción del 98%).

**Mejoras en el Tiempo de Respuesta:**
- Recorrido del grafo: 15-20s → 3-5s (4-5 veces más rápido).
- Resolución de etiquetas: 8-12s → 2-4s (3 veces más rápido).
- Consulta general: 25-35s → 6-10s (mejora de 3-4 veces).

**Eficiencia de la Memoria:**
- Los tamaños de caché limitados evitan las fugas de memoria.
- Las estructuras de datos eficientes reducen la huella de memoria en un ~40%.
- Mejor recolección de basura a través de una limpieza adecuada de recursos.

**Mejoras de Escalabilidad:**
- Compatibilidad con grafos de conocimiento 3-5 veces más grandes (limitado por las necesidades de coherencia de la caché).
- Capacidad de solicitud concurrente 3-5 veces mayor.
- Mejor utilización de recursos a través de la reutilización de conexiones.

### Monitoreo del Rendimiento

**Métricas en Tiempo Real:**
- Tiempos de ejecución de operaciones por tipo de operación.
- Tasas de aciertos y efectividad de la caché.
- Utilización del grupo de conexiones de la base de datos.
- Uso de memoria y impacto de la recolección de basura.

**Pruebas de Rendimiento:**
- Pruebas comparativas contra la implementación actual.
- Pruebas de carga con volúmenes de datos realistas.
- Pruebas de estrés para límites de memoria y conexión.
- Pruebas de regresión para mejoras de rendimiento.

## Estrategia de Pruebas

### Pruebas Unitarias
- Pruebas de componentes individuales para recorrido, almacenamiento en caché y resolución de etiquetas.
- Interacciones simuladas con la base de datos para pruebas de rendimiento.
- Pruebas de desalojo y expiración de TTL de la caché.
- Escenarios de manejo de errores y tiempo de espera.

### Pruebas de Integración
- Pruebas de extremo a extremo de la consulta GraphRAG con optimizaciones.
- Pruebas de interacción con la base de datos con datos reales.
- Manejo de solicitudes concurrentes y gestión de recursos.
- Detección de fugas de memoria y verificación de limpieza de recursos.

### Pruebas de Rendimiento
- Pruebas comparativas contra la implementación actual.
- Pruebas de carga con diferentes tamaños y complejidades de grafos.
- Pruebas de estrés para límites de memoria y conexión.
- Pruebas de regresión para mejoras de rendimiento.

### Pruebas de Compatibilidad
- Verificar la compatibilidad de la API GraphRAG existente.
- Probar con varios backends de bases de datos de grafos.
- Validar la precisión de los resultados en comparación con la implementación actual.

## Plan de Implementación

### Enfoque de Implementación Directa
Dado que se permiten cambios en las API, implemente optimizaciones directamente sin complejidad de migración:

1. **Reemplace el método `follow_edges`**: Reescriba con un recorrido iterativo por lotes.
2. **Optimice `get_labelgraph`**: Implemente la resolución de etiquetas en paralelo.
3. **Agregue GraphRag de larga duración**: Modifique el Procesador para usar una instancia persistente.
4. **Implemente la estrategia de almacenamiento en caché**: Agregue una capa de caché LRU a la clase GraphRag.

### Alcance de los Cambios
- **Clase Query**: Reemplace ~50 líneas en `follow_edges`, agregue ~30 líneas de manejo por lotes.
- **Clase GraphRag**: Agregue una capa de almacenamiento en caché (~40 líneas).
- **Clase Procesador**: Modifique para usar una instancia GraphRag persistente (~20 líneas).
- **Total**: ~140 líneas de cambios enfocados, principalmente dentro de clases existentes.

## Cronograma

**Semana 1: Implementación Central**
- Reemplace `follow_edges` con un recorrido iterativo por lotes.
- Implemente la resolución de etiquetas en paralelo en `get_labelgraph`.
- Agregue una instancia GraphRag de larga duración al Procesador.
- Implemente la capa de almacenamiento en caché.

**Semana 2: Pruebas e Integración**
- Pruebas unitarias para la nueva lógica de recorrido y almacenamiento en caché.
- Pruebas comparativas de rendimiento con la implementación actual.
- Pruebas de integración con datos de grafo reales.
- Revisión de código y optimización.

**Semana 3: Implementación**
- Implemente la implementación optimizada.
- Monitoree las mejoras de rendimiento.
- Ajuste el TTL y los tamaños de lote de la caché en función del uso real.

## Preguntas Abiertas

- **Pooling de Conexiones de la Base de Datos**: ¿Deberíamos implementar un pooling de conexiones personalizado o confiar en el pooling de clientes de la base de datos existente?
- **Persistencia de la Caché**: ¿Deberían las cachés de etiquetas y de incrustaciones persistir entre reinicios del servicio?
- **Almacenamiento en Caché Distribuido**: Para implementaciones multi instancia, ¿deberíamos implementar un almacenamiento en caché distribuido con Redis/Memcached?
- **Formato de Resultados de Consulta**: ¿Deberíamos optimizar la representación interna del triple para una mejor eficiencia de la memoria?
- **Integración de Monitoreo**: ¿Qué métricas deben exponerse a los sistemas de monitoreo existentes (Prometheus, etc.)?

## Referencias

- [Implementación Original de GraphRAG](trustgraph-flow/trustgraph/retrieval/graph_rag/graph_rag.py)
- [Principios de Arquitectura de TrustGraph](architecture-principles.md)
- [Especificación de Gestión de Colecciones](collection-management.md)