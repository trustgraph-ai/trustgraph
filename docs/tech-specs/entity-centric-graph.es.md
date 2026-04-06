# Almacenamiento de Grafos de Conocimiento Centrados en Entidades en Cassandra

## Resumen

Este documento describe un modelo de almacenamiento para grafos de conocimiento de estilo RDF en Apache Cassandra. El modelo utiliza un enfoque **centrado en entidades** donde cada entidad conoce cada cuadrupla en la que participa y el rol que juega. Esto reemplaza un enfoque tradicional de permutaciones SPO con múltiples tablas con solo dos tablas.

## Antecedentes y Motivación

### El Enfoque Tradicional

Un almacén de cuádruplas RDF estándar en Cassandra requiere múltiples tablas desnormalizadas para cubrir los patrones de consulta, normalmente de 6 o más tablas que representan diferentes permutaciones de Sujeto, Predicado, Objeto y Conjunto de Datos (SPOD). Cada cuadrupla se escribe en cada tabla, lo que resulta en una amplificación de escritura significativa, una sobrecarga operativa y una complejidad del esquema.

Además, la resolución de etiquetas (obtención de nombres legibles para humanos para las entidades) requiere consultas de ida y vuelta separadas, lo que es particularmente costoso en casos de uso de IA y GraphRAG donde las etiquetas son esenciales para el contexto de los LLM.

### La Perspectiva Centrada en Entidades

Cada cuadrupla `(D, S, P, O)` involucra hasta 4 entidades. Al escribir una fila para la participación de cada entidad en la cuadrupla, garantizamos que **cualquier consulta con al menos un elemento conocido golpeará una clave de partición**. Esto cubre los 16 patrones de consulta con una sola tabla de datos.

Beneficios clave:

**2 tablas** en lugar de 7+
**4 escrituras por cuadrupla** en lugar de 6+
**Resolución de etiquetas de forma gratuita**: las etiquetas de una entidad están ubicadas junto con sus relaciones, lo que calienta naturalmente la caché de la aplicación.
**Los 16 patrones de consulta** se sirven mediante lecturas de partición única.
**Operaciones más simples**: una sola tabla de datos para ajustar, compactar y reparar.

## Esquema

### Tabla 1: quads_by_entity

La tabla de datos principal. Cada entidad tiene una partición que contiene todas las cuádruplas en las que participa. Nombrada para reflejar el patrón de consulta (búsqueda por entidad).
Después de la última línea traducida, incluir una línea final que contenga exactamente: [[__END_OF_TRANSLATION__]]
```sql
CREATE TABLE quads_by_entity (
    collection text,       -- Collection/tenant scope (always specified)
    entity     text,       -- The entity this row is about
    role       text,       -- 'S', 'P', 'O', 'G' — how this entity participates
    p          text,       -- Predicate of the quad
    otype      text,       -- 'U' (URI), 'L' (literal), 'T' (triple/reification)
    s          text,       -- Subject of the quad
    o          text,       -- Object of the quad
    d          text,       -- Dataset/graph of the quad
    dtype      text,       -- XSD datatype (when otype = 'L'), e.g. 'xsd:string'
    lang       text,       -- Language tag (when otype = 'L'), e.g. 'en', 'fr'
    PRIMARY KEY ((collection, entity), role, p, otype, s, o, d, dtype, lang)
);
```

**Clave de partición**: `(collection, entity)` — con alcance a la colección, una partición por entidad.

**Justificación del orden de las columnas de clustering**:

1. **role** — la mayoría de las consultas comienzan con "dónde está esta entidad como sujeto/objeto".
2. **p** — el siguiente filtro más común, "muéstrame todas las relaciones `knows`".
3. **otype** — permite filtrar por relaciones con valores URI frente a relaciones con valores literales.
4. **s, o, d** — columnas restantes para la unicidad.
5. **dtype, lang** — distingue literales con el mismo valor pero con diferentes metadatos de tipo (por ejemplo, `"thing"` vs `"thing"@en` vs `"thing"^^xsd:string`).

### Tabla 2: quads_by_collection

Soporta consultas y eliminaciones a nivel de colección. Proporciona un manifiesto de todos los cuads pertenecientes a una colección. Nombrado para reflejar el patrón de consulta (búsqueda por colección).

```sql
CREATE TABLE quads_by_collection (
    collection text,
    d          text,       -- Dataset/graph of the quad
    s          text,       -- Subject of the quad
    p          text,       -- Predicate of the quad
    o          text,       -- Object of the quad
    otype      text,       -- 'U' (URI), 'L' (literal), 'T' (triple/reification)
    dtype      text,       -- XSD datatype (when otype = 'L')
    lang       text,       -- Language tag (when otype = 'L')
    PRIMARY KEY (collection, d, s, p, o, otype, dtype, lang)
);
```

Agrupados primero por conjunto de datos, lo que permite la eliminación a nivel de colección o de conjunto de datos. Las columnas `otype`, `dtype` y `lang` se incluyen en la clave de agrupación para distinguir literales con el mismo valor pero con diferentes metadatos de tipo; en RDF, `"thing"`, `"thing"@en` y `"thing"^^xsd:string` son valores semánticamente distintos.

## Ruta de escritura

Para cada cuadruple entrante `(D, S, P, O)` dentro de una colección `C`, escriba **4 filas** en `quads_by_entity` y **1 fila** en `quads_by_collection`.

### Ejemplo

Dado el cuadruple en la colección `tenant1`:

```
Dataset:  https://example.org/graph1
Subject:  https://example.org/Alice
Predicate: https://example.org/knows
Object:   https://example.org/Bob
```

Escriba 4 filas en `quads_by_entity`:

| collection | entity | role | p | otype | s | o | d |
|---|---|---|---|---|---|---|---|
| tenant1 | https://example.org/graph1 | G | https://example.org/knows | U | https://example.org/Alice | https://example.org/Bob | https://example.org/graph1 |
| tenant1 | https://example.org/Alice | S | https://example.org/knows | U | https://example.org/Alice | https://example.org/Bob | https://example.org/graph1 |
| tenant1 | https://example.org/knows | P | https://example.org/knows | U | https://example.org/Alice | https://example.org/Bob | https://example.org/graph1 |
| tenant1 | https://example.org/Bob | O | https://example.org/knows | U | https://example.org/Alice | https://example.org/Bob | https://example.org/graph1 |

Escriba 1 fila en `quads_by_collection`:

| collection | d | s | p | o | otype | dtype | lang |
|---|---|---|---|---|---|---|---|
| tenant1 | https://example.org/graph1 | https://example.org/Alice | https://example.org/knows | https://example.org/Bob | U | | |

### Ejemplo Literal

Para una tripleta de etiqueta:

```
Dataset:  https://example.org/graph1
Subject:  https://example.org/Alice
Predicate: http://www.w3.org/2000/01/rdf-schema#label
Object:   "Alice Smith" (lang: en)
```

El `otype` es `'L'`, `dtype` es `'xsd:string'`, y `lang` es `'en'`. El valor literal `"Alice Smith"` se almacena en `o`. Solo se necesitan 3 filas en `quads_by_entity`; no se escribe ninguna fila para el literal como entidad, ya que los literales no son entidades consultables de forma independiente.

## Patrones de consulta

### Los 16 patrones DSPO

En la tabla a continuación, "Prefijo perfecto" significa que la consulta utiliza un prefijo contiguo de las columnas de clustering. "Escaneo de partición + filtro" significa que Cassandra lee una porción de una partición y filtra en memoria; es eficiente, pero no es una coincidencia de prefijo pura.

| # | Conocido | Búsqueda de entidad | Prefijo de clustering | Eficiencia |
|---|---|---|---|---|
| 1 | D,S,P,O | entidad=S, rol='S', p=P | Coincidencia completa | Prefijo perfecto |
| 2 | D,S,P,? | entidad=S, rol='S', p=P | Filtro en D | Escaneo de partición + filtro |
| 3 | D,S,?,O | entidad=S, rol='S' | Filtro en D, O | Escaneo de partición + filtro |
| 4 | D,?,P,O | entidad=O, rol='O', p=P | Filtro en D | Escaneo de partición + filtro |
| 5 | ?,S,P,O | entidad=S, rol='S', p=P | Filtro en O | Escaneo de partición + filtro |
| 6 | D,S,?,? | entidad=S, rol='S' | Filtro en D | Escaneo de partición + filtro |
| 7 | D,?,P,? | entidad=P, rol='P' | Filtro en D | Escaneo de partición + filtro |
| 8 | D,?,?,O | entidad=O, rol='O' | Filtro en D | Escaneo de partición + filtro |
| 9 | ?,S,P,? | entidad=S, rol='S', p=P | — | **Prefijo perfecto** |
| 10 | ?,S,?,O | entidad=S, rol='S' | Filtro en O | Escaneo de partición + filtro |
| 11 | ?,?,P,O | entidad=O, rol='O', p=P | — | **Prefijo perfecto** |
| 12 | D,?,?,? | entidad=D, rol='G' | — | **Prefijo perfecto** |
| 13 | ?,S,?,? | entidad=S, rol='S' | — | **Prefijo perfecto** |
| 14 | ?,?,P,? | entidad=P, rol='P' | — | **Prefijo perfecto** |
| 15 | ?,?,?,O | entidad=O, rol='O' | — | **Prefijo perfecto** |
| 16 | ?,?,?,? | — | Escaneo completo | Exploración solo |

**Resultado clave**: 7 de los 15 patrones no triviales son coincidencias perfectas de prefijo de clustering. Los 8 restantes son lecturas de partición única con filtrado dentro de la partición. Cada consulta con al menos un elemento conocido coincide con una clave de partición.

El patrón 16 (?,?,?,?) no ocurre en la práctica, ya que la colección siempre se especifica, lo que lo reduce al patrón 12.

### Ejemplos comunes de consultas

**Todo sobre una entidad:**

```sql
SELECT * FROM quads_by_entity
WHERE collection = 'tenant1' AND entity = 'https://example.org/Alice';
```

**Todas las relaciones de salida para una entidad:**

```sql
SELECT * FROM quads_by_entity
WHERE collection = 'tenant1' AND entity = 'https://example.org/Alice'
AND role = 'S';
```

**Predicado específico para una entidad:**

```sql
SELECT * FROM quads_by_entity
WHERE collection = 'tenant1' AND entity = 'https://example.org/Alice'
AND role = 'S' AND p = 'https://example.org/knows';
```

**Etiqueta para una entidad (idioma específico):**

```sql
SELECT * FROM quads_by_entity
WHERE collection = 'tenant1' AND entity = 'https://example.org/Alice'
AND role = 'S' AND p = 'http://www.w3.org/2000/01/rdf-schema#label'
AND otype = 'L';
```

Luego, filtre según la aplicación `lang = 'en'`, si es necesario.

**Solo relaciones con valores URI (enlaces de entidad a entidad):**

```sql
SELECT * FROM quads_by_entity
WHERE collection = 'tenant1' AND entity = 'https://example.org/Alice'
AND role = 'S' AND p = 'https://example.org/knows' AND otype = 'U';
```

**Búsqueda inversa: ¿a qué entidades hace referencia esta?**

```sql
SELECT * FROM quads_by_entity
WHERE collection = 'tenant1' AND entity = 'https://example.org/Bob'
AND role = 'O';
```

## Resolución de etiquetas y calentamiento de la caché

Una de las ventajas más significativas del modelo centrado en entidades es que **la resolución de etiquetas se convierte en un efecto secundario gratuito**.

En el modelo tradicional de múltiples tablas, recuperar etiquetas requiere consultas separadas: recuperar triples, identificar los URI de las entidades en los resultados y luego recuperar `rdfs:label` para cada uno. Este patrón N+1 es costoso.

En el modelo centrado en entidades, consultar una entidad devuelve **todos** sus cuads, incluidas sus etiquetas, tipos y otras propiedades. Cuando la aplicación almacena en caché los resultados de las consultas, las etiquetas se precalientan antes de que alguien las solicite.

Dos regímenes de uso confirman que esto funciona bien en la práctica:

**Consultas orientadas al usuario**: conjuntos de resultados naturalmente pequeños, las etiquetas son esenciales. Las lecturas de entidades precalientan la caché.
**Consultas de IA/masivas**: conjuntos de resultados grandes con límites estrictos. Las etiquetas son innecesarias o se necesitan solo para un subconjunto curado de entidades que ya están en la caché.

La preocupación teórica de resolver etiquetas para conjuntos de resultados enormes (por ejemplo, 30 000 entidades) se mitiga por la observación práctica de que ningún consumidor humano o de IA procesa útilmente tantas etiquetas. Los límites de consulta a nivel de aplicación garantizan que la presión de la caché siga siendo manejable.

## Particiones anchas y reificación

La reificación (declaraciones RDF-star sobre declaraciones) crea entidades de centro, por ejemplo, un documento de origen que admite miles de hechos extraídos. Esto puede producir particiones anchas.

Factores atenuantes:

**Límites de consulta a nivel de aplicación**: todas las consultas de GraphRAG y orientadas al usuario imponen límites estrictos, por lo que las particiones anchas nunca se escanean completamente en la ruta de lectura activa.
**Cassandra maneja las lecturas parciales de manera eficiente**: un escaneo de columna de agrupación con una parada temprana es rápido incluso en particiones grandes.
**Eliminación de colecciones** (la única operación que podría recorrer particiones completas) es un proceso de segundo plano aceptable.

## Eliminación de colecciones

Se activa mediante una llamada a la API, se ejecuta en segundo plano (consistencia eventual).

1. Leer `quads_by_collection` para la colección de destino para obtener todos los cuads.
2. Extraer entidades únicas de los cuads (valores s, p, o, d).
3. Para cada entidad única, eliminar la partición de `quads_by_entity`.
4. Eliminar las filas de `quads_by_collection`.

La tabla `quads_by_collection` proporciona el índice necesario para localizar todas las particiones de entidades sin un escaneo completo de la tabla. Las eliminaciones a nivel de partición son eficientes porque `(collection, entity)` es la clave de partición.

## Ruta de migración desde el modelo de múltiples tablas

El modelo centrado en entidades puede coexistir con el modelo de múltiples tablas existente durante la migración:

1. Implementar las tablas `quads_by_entity` y `quads_by_collection` junto con las tablas existentes.
2. Escribir duplicados nuevos cuads tanto en las tablas antiguas como en las nuevas.
3. Rellenar los datos existentes en las nuevas tablas.
4. Migrar las rutas de consulta un patrón a la vez.
5. Desactivar las tablas antiguas una vez que todas las lecturas se hayan migrado.

## Resumen

| Aspecto | Tradicional (6 tablas) | Centrado en entidades (2 tablas) |
|---|---|---|
| Tablas | 7+ | 2 |
| Escrituras por quad | 6+ | 5 (4 datos + 1 manifiesto) |
| Resolución de etiquetas | Viajes separados | Gratuito a través del calentamiento de la caché |
| Patrones de consulta | 16 en 6 tablas | 16 en 1 tabla |
| Complejidad del esquema | Alto | Bajo |
| Sobrecarga operativa | 6 tablas para ajustar/reparar | 1 tabla de datos |
| Soporte de reificación | Complejidad adicional | Ajuste natural |
| Filtrado de tipo de objeto | No disponible | Nativo (a través de la agrupación de otype) |
Después de la última línea traducida, incluir una línea final que contenga exactamente: [[__END_OF_TRANSLATION__]]
