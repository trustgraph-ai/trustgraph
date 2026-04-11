# Extracción de Conocimiento Ontológico - Fase 2, Refactorización

**Estado**: Borrador
**Autor**: Sesión de Análisis 2025-12-03
**Relacionado**: `ontology.md`, `ontorag.md`

## Resumen

Este documento identifica inconsistencias en el sistema actual de extracción de conocimiento basado en ontologías y propone una refactorización para mejorar el rendimiento de los LLM y reducir la pérdida de información.

## Implementación Actual

### Cómo Funciona Actualmente

1. **Carga de la Ontología** (`ontology_loader.py`)
   Carga el archivo JSON de la ontología con claves como `"fo/Recipe"`, `"fo/Food"`, `"fo/produces"`
   Los ID de las clases incluyen el prefijo del espacio de nombres en la clave.
   Ejemplo de `food.ontology`:
     ```json
     "classes": {
       "fo/Recipe": {
         "uri": "http://purl.org/ontology/fo/Recipe",
         "rdfs:comment": "A Recipe is a combination..."
       }
     }
     ```

2. **Construcción del prompt** (`extract.py:299-307`, `ontology-prompt.md`)
   La plantilla recibe diccionarios `classes`, `object_properties`, `datatype_properties`
   La plantilla itera: `{% for class_id, class_def in classes.items() %}`
   El LLM ve: `**fo/Recipe**: A Recipe is a combination...`
   El formato de salida de ejemplo muestra:
     ```json
     {"subject": "recipe:cornish-pasty", "predicate": "rdf:type", "object": "Recipe"}
     {"subject": "recipe:cornish-pasty", "predicate": "has_ingredient", "object": "ingredient:flour"}
     ```

3. **Análisis de la respuesta** (`extract.py:382-428`)
   Espera un array JSON: `[{"subject": "...", "predicate": "...", "object": "..."}]`
   Valida contra un subconjunto de la ontología
   Expande los URIs mediante `expand_uri()` (extract.py:473-521)

4. **Expansión de URIs** (`extract.py:473-521`)
   Comprueba si el valor está en el diccionario `ontology_subset.classes`
   Si se encuentra, extrae el URI de la definición de la clase
   Si no se encuentra, construye el URI: `f"https://trustgraph.ai/ontology/{ontology_id}#{value}"`

### Ejemplo de flujo de datos

**JSON de la ontología → Loader → Prompt:**
```
"fo/Recipe" → classes["fo/Recipe"] → LLM sees "**fo/Recipe**"
```

**LLM → Analizador → Salida:**
```
"Recipe" → not in classes["fo/Recipe"] → constructs URI → LOSES original URI
"fo/Recipe" → found in classes → uses original URI → PRESERVES URI
```

## Problemas Identificados

### 1. **Ejemplos Inconsistentes en la Instrucción**

**Problema**: La plantilla de la instrucción muestra ID de clase con prefijos (`fo/Recipe`) pero la salida de ejemplo utiliza nombres de clase sin prefijos (`Recipe`).

**Ubicación**: `ontology-prompt.md:5-52`

```markdown
## Ontology Classes:
- **fo/Recipe**: A Recipe is...

## Example Output:
{"subject": "recipe:cornish-pasty", "predicate": "rdf:type", "object": "Recipe"}
```

**Impacto**: El modelo de lenguaje (LLM) recibe señales contradictorias sobre qué formato utilizar.

### 2. **Pérdida de información en la expansión de URI**

**Problema**: Cuando el LLM devuelve nombres de clase sin prefijo, siguiendo el ejemplo, `expand_uri()` no puede encontrarlos en el diccionario de ontología y construye URI de respaldo, perdiendo los URI originales correctos.

**Ubicación**: `extract.py:494-500`

```python
if value in ontology_subset.classes:  # Looks for "Recipe"
    class_def = ontology_subset.classes[value]  # But key is "fo/Recipe"
    if isinstance(class_def, dict) and 'uri' in class_def:
        return class_def['uri']  # Never reached!
return f"https://trustgraph.ai/ontology/{ontology_id}#{value}"  # Fallback
```

**Impacto:**
URI original: `http://purl.org/ontology/fo/Recipe`
URI construido: `https://trustgraph.ai/ontology/food#Recipe`
Significado semántico perdido, interrumpe la interoperabilidad.

### 3. **Formato ambiguo de instancia de entidad**

**Problema:** No hay una guía clara sobre el formato de la URI de la instancia de entidad.

**Ejemplos en la solicitud:**
`"recipe:cornish-pasty"` (prefijo similar a un espacio de nombres)
`"ingredient:flour"` (prefijo diferente)

**Comportamiento real** (extract.py:517-520):
```python
# Treat as entity instance - construct unique URI
normalized = value.replace(" ", "-").lower()
return f"https://trustgraph.ai/{ontology_id}/{normalized}"
```

**Impacto**: El modelo de lenguaje debe adivinar la convención de prefijos sin contexto ontológico.

### 4. **Sin Guía de Prefijos de Espacio de Nombres**

**Problema**: El archivo JSON de la ontología contiene definiciones de espacios de nombres (líneas 10-25 en food.ontology):
```json
"namespaces": {
  "fo": "http://purl.org/ontology/fo/",
  "rdf": "http://www.w3.org/1999/02/22-rdf-syntax-ns#",
  ...
}
```

Pero estas líneas nunca se muestran al LLM. El LLM no sabe:
Qué significa "fo"
Qué prefijo usar para las entidades
A qué espacio de nombres se aplica a qué elementos

### 5. **Etiquetas No Utilizadas en el Prompt**

**Problema**: Cada clase tiene campos `rdfs:label` (por ejemplo, `{"value": "Recipe", "lang": "en-gb"}`), pero la plantilla del prompt no los utiliza.

**Actual**: Muestra solo `class_id` y `comment`
```jinja
- **{{class_id}}**{% if class_def.comment %}: {{class_def.comment}}{% endif %}
```

**Disponible pero no utilizado**:
```python
"rdfs:label": [{"value": "Recipe", "lang": "en-gb"}]
```

**Impacto**: Podría proporcionar nombres legibles por humanos junto con identificadores técnicos.

## Soluciones propuestas

### Opción A: Normalizar a identificadores sin prefijos

**Enfoque**: Eliminar los prefijos de los identificadores de clase antes de mostrarlos al LLM.

**Cambios**:
1. Modificar `build_extraction_variables()` para transformar las claves:
   ```python
   classes_for_prompt = {
       k.split('/')[-1]: v  # "fo/Recipe" → "Recipe"
       for k, v in ontology_subset.classes.items()
   }
   ```

2. Actualizar el ejemplo de la instrucción para que coincida (ya utiliza nombres sin prefijos).

3. Modificar `expand_uri()` para que gestione ambos formatos:
   ```python
   # Try exact match first
   if value in ontology_subset.classes:
       return ontology_subset.classes[value]['uri']

   # Try with prefix
   for prefix in ['fo/', 'rdf:', 'rdfs:']:
       prefixed = f"{prefix}{value}"
       if prefixed in ontology_subset.classes:
           return ontology_subset.classes[prefixed]['uri']
   ```

**Ventajas:**
Más limpio, más legible para los humanos.
Coincide con ejemplos de prompts existentes.
Los LLM funcionan mejor con tokens más simples.

**Desventajas:**
Colisiones de nombres de clase si múltiples ontologías tienen el mismo nombre de clase.
Pierde la información del espacio de nombres.
Requiere lógica de respaldo para las búsquedas.

### Opción B: Utilizar IDs con Prefijos Completos de Forma Consistente

**Enfoque:** Actualizar los ejemplos para utilizar IDs con prefijos que coincidan con lo que se muestra en la lista de clases.

**Cambios:**
1. Actualizar el ejemplo del prompt (ontology-prompt.md:46-52):
   ```json
   [
     {"subject": "recipe:cornish-pasty", "predicate": "rdf:type", "object": "fo/Recipe"},
     {"subject": "recipe:cornish-pasty", "predicate": "rdfs:label", "object": "Cornish Pasty"},
     {"subject": "recipe:cornish-pasty", "predicate": "fo/produces", "object": "food:cornish-pasty"},
     {"subject": "food:cornish-pasty", "predicate": "rdf:type", "object": "fo/Food"}
   ]
   ```

2. Agregar una explicación del espacio de nombres a la instrucción:
   ```markdown
   ## Namespace Prefixes:
   - **fo/**: Food Ontology (http://purl.org/ontology/fo/)
   - **rdf:**: RDF Schema
   - **rdfs:**: RDF Schema

   Use these prefixes exactly as shown when referencing classes and properties.
   ```

3. Mantener `expand_uri()` tal cual (funciona correctamente cuando se encuentran coincidencias).

**Ventajas**:
Consistencia entre entrada y salida.
Sin pérdida de información.
Preserva la semántica del espacio de nombres.
Funciona con múltiples ontologías.

**Desventajas**:
Tokens más verbosos para el LLM.
Requiere que el LLM rastree los prefijos.

### Opción C: Híbrida: Mostrar tanto la etiqueta como el ID.

**Enfoque**: Mejorar el prompt para mostrar tanto las etiquetas legibles por humanos como los ID técnicos.

**Cambios**:
1. Actualizar la plantilla del prompt:
   ```jinja
   {% for class_id, class_def in classes.items() %}
   - **{{class_id}}** (label: "{{class_def.labels[0].value if class_def.labels else class_id}}"){% if class_def.comment %}: {{class_def.comment}}{% endif %}
   {% endfor %}
   ```

   Ejemplo de salida:
   ```markdown
   - **fo/Recipe** (label: "Recipe"): A Recipe is a combination...
   ```

2. Instrucciones de actualización:
   ```markdown
   When referencing classes:
   - Use the full prefixed ID (e.g., "fo/Recipe") in JSON output
   - The label (e.g., "Recipe") is for human understanding only
   ```

**Ventajas**:
Más claro para los modelos de lenguaje (LLM).
Preserva toda la información.
Explícito sobre qué usar.

**Desventajas**:
Requiere un prompt más largo.
Plantilla más compleja.

## Enfoque Implementado

**Formato Simplificado de Entidad-Relación-Atributo** - reemplaza completamente el formato basado en triples anterior.

El nuevo enfoque se eligió porque:

1. **Sin Pérdida de Información**: Los URI originales se conservan correctamente.
2. **Lógica Más Simple**: No se necesita transformación, las búsquedas directas en diccionarios funcionan.
3. **Seguridad de Espacios de Nombres**: Maneja múltiples ontologías sin colisiones.
4. **Corrección Semántica**: Mantiene la semántica RDF/OWL.

## Implementación Completada

### Lo que se Construyó:

1. **Nueva Plantilla de Prompt** (`prompts/ontology-extract-v2.txt`)
   ✅ Secciones claras: Tipos de Entidad, Relaciones, Atributos.
   ✅ Ejemplo utilizando identificadores de tipo completos (`fo/Recipe`, `fo/has_ingredient`).
   ✅ Instrucciones para usar los identificadores exactos del esquema.
   ✅ Nuevo formato JSON con matrices de entidades/relaciones/atributos.

2. **Normalización de Entidades** (`entity_normalizer.py`)
   ✅ `normalize_entity_name()` - Convierte los nombres a un formato seguro para URI.
   ✅ `normalize_type_identifier()` - Maneja las barras diagonales en los tipos (`fo/Recipe` → `fo-recipe`).
   ✅ `build_entity_uri()` - Crea URI únicos utilizando la tupla (nombre, tipo).
   ✅ `EntityRegistry` - Realiza un seguimiento de las entidades para la eliminación de duplicados.

3. **Analizador JSON** (`simplified_parser.py`)
   ✅ Analiza el nuevo formato: `{entities: [...], relationships: [...], attributes: [...]}`
   ✅ Admite nombres de campo en formato kebab-case y snake_case.
   ✅ Devuelve clases de datos estructuradas.
   ✅ Manejo de errores con registro.

4. **Convertidor de Triples** (`triple_converter.py`)
   ✅ `convert_entity()` - Genera automáticamente triples de tipo + etiqueta.
   ✅ `convert_relationship()` - Conecta los URI de las entidades a través de propiedades.
   ✅ `convert_attribute()` - Agrega valores literales.
   ✅ Busca URI completos a partir de las definiciones de la ontología.

5. **Procesador Principal Actualizado** (`extract.py`)
   ✅ Se eliminó el código antiguo de extracción basado en triples.
   ✅ Se agregó el método `extract_with_simplified_format()`.
   ✅ Ahora utiliza exclusivamente el nuevo formato simplificado.
   ✅ Llama al indicador con el ID `extract-with-ontologies-v2`.

## Casos de Prueba

### Prueba 1: Preservación de URI
```python
# Given ontology class
classes = {"fo/Recipe": {"uri": "http://purl.org/ontology/fo/Recipe", ...}}

# When LLM returns
llm_output = {"subject": "x", "predicate": "rdf:type", "object": "fo/Recipe"}

# Then expanded URI should be
assert expanded == "http://purl.org/ontology/fo/Recipe"
# Not: "https://trustgraph.ai/ontology/food#Recipe"
```

### Prueba 2: Colisión Multi-Ontología
```python
# Given two ontologies
ont1 = {"fo/Recipe": {...}}
ont2 = {"cooking/Recipe": {...}}

# LLM should use full prefix to disambiguate
llm_output = {"object": "fo/Recipe"}  # Not just "Recipe"
```

### Prueba 3: Formato de Instancia de Entidad
```python
# Given prompt with food ontology
# LLM should create instances like
{"subject": "recipe:cornish-pasty"}  # Namespace-style
{"subject": "food:beef"}              # Consistent prefix
```

## Preguntas Abiertas

1. **¿Deben las instancias de entidades usar prefijos de espacio de nombres?**
   Actual: `"recipe:cornish-pasty"` (arbitrario)
   Alternativa: ¿Usar prefijo de ontología `"fo:cornish-pasty"`?
   Alternativa: Sin prefijo, expandir en URI `"cornish-pasty"` → URI completa?

2. **¿Cómo manejar el dominio/rango en el prompt?**
   Actualmente muestra: `(Recipe → Food)`
   ¿Debería ser: `(fo/Recipe → fo/Food)`?

3. **¿Debemos validar las restricciones de dominio/rango?**
   TODO comentario en extract.py:470
   Detectaría más errores pero sería más complejo

4. **¿Qué tal las propiedades inversas y las equivalencias?**
   La ontología tiene `owl:inverseOf`, `owl:equivalentClass`
   Actualmente no se utilizan en la extracción
   ¿Deberían usarse?

## Métricas de Éxito

✅ Pérdida de información de URI cero (100% de preservación de los URI originales)
✅ El formato de salida del LLM coincide con el formato de entrada
✅ No hay ejemplos ambiguos en el prompt
✅ Las pruebas pasan con múltiples ontologías
✅ Calidad de extracción mejorada (medida por el porcentaje de triples válidos)

## Enfoque Alternativo: Formato de Extracción Simplificado

### Filosofía

En lugar de pedirle al LLM que comprenda la semántica de RDF/OWL, pídele que haga lo que hace bien: **encontrar entidades y relaciones en el texto**.

Deje que el código se encargue de la construcción de URI, la conversión de RDF y las formalidades de la web semántica.

### Ejemplo: Clasificación de Entidades

**Texto de entrada:**
```
Cornish pasty is a traditional British pastry filled with meat and vegetables.
```

**Esquema de Ontología (mostrado al LLM):**
```markdown
## Entity Types:
- Recipe: A recipe is a combination of ingredients and a method
- Food: A food is something that can be eaten
- Ingredient: An ingredient combines a quantity and a food
```

**Lo que el LLM devuelve (JSON simple):**
```json
{
  "entities": [
    {
      "entity": "Cornish pasty",
      "type": "Recipe"
    }
  ]
}
```

**¿Qué código produce (triples RDF):**
```python
# 1. Normalize entity name + type to ID (type prevents collisions)
entity_id = "recipe-cornish-pasty"  # normalize("Cornish pasty", "Recipe")
entity_uri = "https://trustgraph.ai/food/recipe-cornish-pasty"

# Note: Same name, different type = different URI
# "Cornish pasty" (Recipe) → recipe-cornish-pasty
# "Cornish pasty" (Food) → food-cornish-pasty

# 2. Generate triples
triples = [
    # Type triple
    Triple(
        s=Value(value=entity_uri, is_uri=True),
        p=Value(value="http://www.w3.org/1999/02/22-rdf-syntax-ns#type", is_uri=True),
        o=Value(value="http://purl.org/ontology/fo/Recipe", is_uri=True)
    ),
    # Label triple (automatic)
    Triple(
        s=Value(value=entity_uri, is_uri=True),
        p=Value(value="http://www.w3.org/2000/01/rdf-schema#label", is_uri=True),
        o=Value(value="Cornish pasty", is_uri=False)
    )
]
```

### Beneficios

1. **El LLM no necesita:**
   Entender la sintaxis de URI
   Inventar prefijos de identificadores (`recipe:`, `ingredient:`)
   Conocer `rdf:type` o `rdfs:label`
   Construir identificadores de la web semántica

2. **El LLM solo necesita:**
   Encontrar entidades en el texto
   Mapearlas a clases de ontología
   Extraer relaciones y atributos

3. **El código se encarga de:**
   Normalización y construcción de URI
   Generación de triples RDF
   Asignación automática de etiquetas
   Gestión de espacios de nombres

### ¿Por qué esto funciona mejor?

**Indicación más simple** = menos confusión = menos errores
**IDs consistentes** = el código controla las reglas de normalización
**Etiquetas generadas automáticamente** = no faltan triples rdfs:label
**El LLM se centra en la extracción** = en lo que realmente es bueno

### Ejemplo: Relaciones de Entidades

**Texto de entrada:**
```
Cornish pasty is a traditional British pastry filled with beef and potatoes.
```

**Esquema de Ontología (mostrado al LLM):**
```markdown
## Entity Types:
- Recipe: A recipe is a combination of ingredients and a method
- Food: A food is something that can be eaten
- Ingredient: An ingredient combines a quantity and a food

## Relationships:
- has_ingredient: Relates a recipe to an ingredient it uses (Recipe → Ingredient)
- food: Relates an ingredient to the food that is required (Ingredient → Food)
```

**Lo que el LLM devuelve (JSON simple):**
```json
{
  "entities": [
    {
      "entity": "Cornish pasty",
      "type": "Recipe"
    },
    {
      "entity": "beef",
      "type": "Food"
    },
    {
      "entity": "potatoes",
      "type": "Food"
    }
  ],
  "relationships": [
    {
      "subject": "Cornish pasty",
      "subject-type": "Recipe",
      "relation": "has_ingredient",
      "object": "beef",
      "object-type": "Food"
    },
    {
      "subject": "Cornish pasty",
      "subject-type": "Recipe",
      "relation": "has_ingredient",
      "object": "potatoes",
      "object-type": "Food"
    }
  ]
}
```

**¿Qué código produce (triples RDF):**
```python
# Normalize entity names to URIs
cornish_pasty_uri = "https://trustgraph.ai/food/cornish-pasty"
beef_uri = "https://trustgraph.ai/food/beef"
potatoes_uri = "https://trustgraph.ai/food/potatoes"

# Look up relation URI from ontology
has_ingredient_uri = "http://purl.org/ontology/fo/ingredients"  # from fo/has_ingredient

triples = [
    # Entity type triples (as before)
    Triple(s=cornish_pasty_uri, p=rdf_type, o="http://purl.org/ontology/fo/Recipe"),
    Triple(s=cornish_pasty_uri, p=rdfs_label, o="Cornish pasty"),

    Triple(s=beef_uri, p=rdf_type, o="http://purl.org/ontology/fo/Food"),
    Triple(s=beef_uri, p=rdfs_label, o="beef"),

    Triple(s=potatoes_uri, p=rdf_type, o="http://purl.org/ontology/fo/Food"),
    Triple(s=potatoes_uri, p=rdfs_label, o="potatoes"),

    # Relationship triples
    Triple(
        s=Value(value=cornish_pasty_uri, is_uri=True),
        p=Value(value=has_ingredient_uri, is_uri=True),
        o=Value(value=beef_uri, is_uri=True)
    ),
    Triple(
        s=Value(value=cornish_pasty_uri, is_uri=True),
        p=Value(value=has_ingredient_uri, is_uri=True),
        o=Value(value=potatoes_uri, is_uri=True)
    )
]
```

**Puntos clave:**
El modelo de lenguaje (LLM) devuelve nombres de entidades en lenguaje natural: `"Cornish pasty"`, `"beef"`, `"potatoes"`
El LLM incluye tipos para disambiguar: `subject-type`, `object-type`
El LLM utiliza el nombre de la relación del esquema: `"has_ingredient"`
El código deriva IDs consistentes utilizando (nombre, tipo): `("Cornish pasty", "Recipe")` → `recipe-cornish-pasty`
El código busca el URI de la relación en la ontología: `fo/has_ingredient` → URI completo
La misma tupla (nombre, tipo) siempre obtiene el mismo URI (desduplicación)

### Ejemplo: Disambiguación del nombre de la entidad

**Problema:** El mismo nombre puede referirse a diferentes tipos de entidad.

**Caso real:**
```
"Cornish pasty" can be:
- A Recipe (instructions for making it)
- A Food (the dish itself)
```

**Cómo se gestiona:**

El modelo de lenguaje grande (LLM) devuelve ambos como entidades separadas:
```json
{
  "entities": [
    {"entity": "Cornish pasty", "type": "Recipe"},
    {"entity": "Cornish pasty", "type": "Food"}
  ],
  "relationships": [
    {
      "subject": "Cornish pasty",
      "subject-type": "Recipe",
      "relation": "produces",
      "object": "Cornish pasty",
      "object-type": "Food"
    }
  ]
}
```

**Resolución de código:**
```python
# Different types → different URIs
recipe_uri = normalize("Cornish pasty", "Recipe")
# → "https://trustgraph.ai/food/recipe-cornish-pasty"

food_uri = normalize("Cornish pasty", "Food")
# → "https://trustgraph.ai/food/food-cornish-pasty"

# Relationship connects them correctly
triple = Triple(
    s=recipe_uri,  # The Recipe
    p="http://purl.org/ontology/fo/produces",
    o=food_uri     # The Food
)
```

**¿Por qué funciona esto?:**
El tipo se incluye en TODAS las referencias (entidades, relaciones, atributos).
El código utiliza la tupla `(name, type)` como clave de búsqueda.
No hay ambigüedad, no hay colisiones.

### Ejemplo: Atributos de Entidad

**Texto de entrada:**
```
This Cornish pasty recipe serves 4-6 people and takes 45 minutes to prepare.
```

**Esquema de Ontología (mostrado al LLM):**
```markdown
## Entity Types:
- Recipe: A recipe is a combination of ingredients and a method

## Attributes:
- serves: Indicates what the recipe is intended to serve (Recipe → text)
- preparation_time: Time needed to prepare the recipe (Recipe → text)
```

**Lo que el LLM devuelve (JSON simple):**
```json
{
  "entities": [
    {
      "entity": "Cornish pasty recipe",
      "type": "Recipe"
    }
  ],
  "attributes": [
    {
      "entity": "Cornish pasty recipe",
      "entity-type": "Recipe",
      "attribute": "serves",
      "value": "4-6 people"
    },
    {
      "entity": "Cornish pasty recipe",
      "entity-type": "Recipe",
      "attribute": "preparation_time",
      "value": "45 minutes"
    }
  ]
}
```

**¿Qué código produce (triples RDF):**
```python
# Normalize entity name to URI
recipe_uri = "https://trustgraph.ai/food/cornish-pasty-recipe"

# Look up attribute URIs from ontology
serves_uri = "http://purl.org/ontology/fo/serves"  # from fo/serves
prep_time_uri = "http://purl.org/ontology/fo/preparation_time"  # from fo/preparation_time

triples = [
    # Entity type triple
    Triple(
        s=Value(value=recipe_uri, is_uri=True),
        p=Value(value=rdf_type, is_uri=True),
        o=Value(value="http://purl.org/ontology/fo/Recipe", is_uri=True)
    ),

    # Label triple (automatic)
    Triple(
        s=Value(value=recipe_uri, is_uri=True),
        p=Value(value=rdfs_label, is_uri=True),
        o=Value(value="Cornish pasty recipe", is_uri=False)
    ),

    # Attribute triples (objects are literals, not URIs)
    Triple(
        s=Value(value=recipe_uri, is_uri=True),
        p=Value(value=serves_uri, is_uri=True),
        o=Value(value="4-6 people", is_uri=False)  # Literal value!
    ),
    Triple(
        s=Value(value=recipe_uri, is_uri=True),
        p=Value(value=prep_time_uri, is_uri=True),
        o=Value(value="45 minutes", is_uri=False)  # Literal value!
    )
]
```

**Puntos Clave:**
El LLM extrae valores literales: `"4-6 people"`, `"45 minutes"`
El LLM incluye el tipo de entidad para la desambiguación: `entity-type`
El LLM utiliza el nombre del atributo del esquema: `"serves"`, `"preparation_time"`
El código busca el URI del atributo de las propiedades del tipo de datos de la ontología
**El objeto es literal** (`is_uri=False`), no una referencia de URI
Los valores permanecen como texto natural, no se necesita normalización

**Diferencia con las Relaciones:**
Relaciones: tanto el sujeto como el objeto son entidades (URIs)
Atributos: el sujeto es una entidad (URI), el objeto es un valor literal (cadena/número)

### Ejemplo Completo: Entidades + Relaciones + Atributos

**Texto de Entrada:**
```
Cornish pasty is a savory pastry filled with beef and potatoes.
This recipe serves 4 people.
```

**Lo que el LLM devuelve:**
```json
{
  "entities": [
    {
      "entity": "Cornish pasty",
      "type": "Recipe"
    },
    {
      "entity": "beef",
      "type": "Food"
    },
    {
      "entity": "potatoes",
      "type": "Food"
    }
  ],
  "relationships": [
    {
      "subject": "Cornish pasty",
      "subject-type": "Recipe",
      "relation": "has_ingredient",
      "object": "beef",
      "object-type": "Food"
    },
    {
      "subject": "Cornish pasty",
      "subject-type": "Recipe",
      "relation": "has_ingredient",
      "object": "potatoes",
      "object-type": "Food"
    }
  ],
  "attributes": [
    {
      "entity": "Cornish pasty",
      "entity-type": "Recipe",
      "attribute": "serves",
      "value": "4 people"
    }
  ]
}
```

**Resultado:** Se generaron 11 triples RDF:
3 triples de tipo de entidad (rdf:type)
3 triples de etiqueta de entidad (rdfs:label) - automático
2 triples de relación (has_ingredient)
1 triple de atributo (serves)

¡Todo proviene de extracciones simples y en lenguaje natural realizadas por el LLM!

## Referencias

Implementación actual: `trustgraph-flow/trustgraph/extract/kg/ontology/extract.py`
Plantilla de prompt: `ontology-prompt.md`
Casos de prueba: `tests/unit/test_extract/test_ontology/`
Ontología de ejemplo: `e2e/test-data/food.ontology`
