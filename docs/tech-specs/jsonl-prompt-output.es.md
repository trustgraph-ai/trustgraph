# Especificación técnica de la salida de JSONL para prompts

## Resumen

Esta especificación describe la implementación del formato de salida JSONL (JSON Lines)
para respuestas de prompts en TrustGraph. JSONL permite la extracción resistente a
la truncación de datos estructurados de las respuestas de los LLM, abordando problemas
críticos con las salidas de matrices JSON que se corrompen cuando las respuestas de
los LLM alcanzan los límites de tokens de salida.

Esta implementación admite los siguientes casos de uso:

1. **Extracción resistente a la truncación**: Extraer resultados parciales válidos
   incluso cuando la salida del LLM se trunca a la mitad de la respuesta.
2. **Extracción a gran escala**: Manejar la extracción de muchos elementos sin riesgo
   de fallo completo debido a los límites de tokens.
3. **Extracción de tipos mixtos**: Admitir la extracción de múltiples tipos de
   entidades (definiciones, relaciones, entidades, atributos) en un solo prompt.
4. **Salida compatible con el streaming**: Permitir el procesamiento futuro de
   resultados de extracción de forma incremental.

## Objetivos

**Compatibilidad con versiones anteriores**: Las indicaciones existentes que utilizan `response-type: "text"` y
  `response-type: "json"` siguen funcionando sin modificaciones.
**Resiliencia a la truncación**: Las salidas parciales del LLM producen resultados válidos parciales
  en lugar de un fallo completo.
**Validación de esquema**: Soporte para la validación de esquemas JSON para objetos individuales.
**Uniones discriminadas**: Soporte para salidas de tipos mixtos utilizando un campo `type`
  discriminador.
**Cambios mínimos en la API**: Extiende la configuración de indicaciones existente con un nuevo
  tipo de respuesta y clave de esquema.

## Contexto

### Arquitectura actual

El servicio de indicaciones admite dos tipos de respuesta:

1. `response-type: "text"`: Respuesta de texto sin formato devuelta tal cual.
2. `response-type: "json"`: JSON analizado de la respuesta, validado contra
   un esquema `schema` opcional.

Implementación actual en `trustgraph-flow/trustgraph/template/prompt_manager.py`:

```python
class Prompt:
    def __init__(self, template, response_type = "text", terms=None, schema=None):
        self.template = template
        self.response_type = response_type
        self.terms = terms
        self.schema = schema
```

### Limitaciones actuales

Cuando las indicaciones de extracción solicitan una salida en formato de matrices JSON (`[{...}, {...}, ...]`):

**Corrupción por truncamiento**: Si el LLM alcanza los límites de tokens de salida a la mitad de la matriz,
  toda la respuesta se vuelve JSON inválido y no se puede analizar.
**Análisis todo o nada**: Debe recibir la salida completa antes de analizarla.
**Sin resultados parciales**: Una respuesta truncada produce cero datos utilizables.
**No es fiable para extracciones grandes**: Cuantos más elementos se extraen, mayor es el riesgo de fallo.

Esta especificación aborda estas limitaciones introduciendo el formato JSONL para
las indicaciones de extracción, donde cada elemento extraído es un objeto JSON completo en su
propia línea.

## Diseño técnico

### Extensión del tipo de respuesta

Agregue un nuevo tipo de respuesta `"jsonl"` junto con los tipos existentes `"text"` y `"json"`.

#### Cambios de configuración

**Nuevo valor del tipo de respuesta:**

```
"response-type": "jsonl"
```

**Interpretación del esquema:**

La clave existente `"schema"` se utiliza tanto para el tipo de respuesta `"json"` como para el tipo de respuesta `"jsonl"`.
La interpretación depende del tipo de respuesta:

`"json"`: El esquema describe toda la respuesta (típicamente un array u objeto).
`"jsonl"`: El esquema describe cada línea/objeto individual.

```json
{
  "response-type": "jsonl",
  "schema": {
    "type": "object",
    "properties": {
      "entity": { "type": "string" },
      "definition": { "type": "string" }
    },
    "required": ["entity", "definition"]
  }
}
```

Esto evita cambios en las herramientas de configuración y los editores.

### Especificación del formato JSONL

#### Extracción simple

Para los prompts que extraen un solo tipo de objeto (definiciones, relaciones,
temas, filas), la salida es un objeto JSON por línea sin envoltorio:

**Formato de salida del prompt:**
```
{"entity": "photosynthesis", "definition": "Process by which plants convert sunlight"}
{"entity": "chlorophyll", "definition": "Green pigment in plants"}
{"entity": "mitochondria", "definition": "Powerhouse of the cell"}
```

**Contraste con el formato anterior de matriz JSON:**
```json
[
  {"entity": "photosynthesis", "definition": "Process by which plants convert sunlight"},
  {"entity": "chlorophyll", "definition": "Green pigment in plants"},
  {"entity": "mitochondria", "definition": "Powerhouse of the cell"}
]
```

Si el modelo de lenguaje (LLM) trunca después de la línea 2, el formato de matriz JSON produce JSON inválido,
mientras que JSONL produce dos objetos válidos.

#### Extracción de Tipos Mixtos (Uniones Discriminadas)

Para las indicaciones que extraen múltiples tipos de objetos (por ejemplo, tanto definiciones como
relaciones, o entidades, relaciones y atributos), utilice un campo `"type"`
como discriminador:

**Formato de salida de la indicación:**
```
{"type": "definition", "entity": "DNA", "definition": "Molecule carrying genetic instructions"}
{"type": "relationship", "subject": "DNA", "predicate": "located_in", "object": "cell nucleus", "object-entity": true}
{"type": "definition", "entity": "RNA", "definition": "Molecule that carries genetic information"}
{"type": "relationship", "subject": "RNA", "predicate": "transcribed_from", "object": "DNA", "object-entity": true}
```

**Esquema para uniones discriminadas utiliza `oneOf`:**
```json
{
  "response-type": "jsonl",
  "schema": {
    "oneOf": [
      {
        "type": "object",
        "properties": {
          "type": { "const": "definition" },
          "entity": { "type": "string" },
          "definition": { "type": "string" }
        },
        "required": ["type", "entity", "definition"]
      },
      {
        "type": "object",
        "properties": {
          "type": { "const": "relationship" },
          "subject": { "type": "string" },
          "predicate": { "type": "string" },
          "object": { "type": "string" },
          "object-entity": { "type": "boolean" }
        },
        "required": ["type", "subject", "predicate", "object", "object-entity"]
      }
    ]
  }
}
```

#### Extracción de Ontología

Para la extracción basada en ontologías con entidades, relaciones y atributos:

**Formato de salida del prompt:**
```
{"type": "entity", "entity": "Cornish pasty", "entity_type": "fo/Recipe"}
{"type": "entity", "entity": "beef", "entity_type": "fo/Food"}
{"type": "relationship", "subject": "Cornish pasty", "subject_type": "fo/Recipe", "relation": "fo/has_ingredient", "object": "beef", "object_type": "fo/Food"}
{"type": "attribute", "entity": "Cornish pasty", "entity_type": "fo/Recipe", "attribute": "fo/serves", "value": "4 people"}
```

### Detalles de implementación

#### Clase Prompt

La clase `Prompt` existente no requiere cambios. El campo `schema` se reutiliza
para JSONL, y su interpretación está determinada por `response_type`:

```python
class Prompt:
    def __init__(self, template, response_type="text", terms=None, schema=None):
        self.template = template
        self.response_type = response_type
        self.terms = terms
        self.schema = schema  # Interpretation depends on response_type
```

#### PromptManager.load_config

No se requieren cambios: la carga de configuración existente ya gestiona la
clave `schema`.

#### Análisis de JSONL

Agregar un nuevo método de análisis para respuestas JSONL:

```python
def parse_jsonl(self, text):
    """
    Parse JSONL response, returning list of valid objects.

    Invalid lines (malformed JSON, empty lines) are skipped with warnings.
    This provides truncation resilience - partial output yields partial results.
    """
    results = []

    for line_num, line in enumerate(text.strip().split('\n'), 1):
        line = line.strip()

        # Skip empty lines
        if not line:
            continue

        # Skip markdown code fence markers if present
        if line.startswith('```'):
            continue

        try:
            obj = json.loads(line)
            results.append(obj)
        except json.JSONDecodeError as e:
            # Log warning but continue - this provides truncation resilience
            logger.warning(f"JSONL parse error on line {line_num}: {e}")

    return results
```

#### Cambios en PromptManager.invoke

Extender el método invoke para manejar el nuevo tipo de respuesta:

```python
async def invoke(self, id, input, llm):
    logger.debug("Invoking prompt template...")

    terms = self.terms | self.prompts[id].terms | input
    resp_type = self.prompts[id].response_type

    prompt = {
        "system": self.system_template.render(terms),
        "prompt": self.render(id, input)
    }

    resp = await llm(**prompt)

    if resp_type == "text":
        return resp

    if resp_type == "json":
        try:
            obj = self.parse_json(resp)
        except:
            logger.error(f"JSON parse failed: {resp}")
            raise RuntimeError("JSON parse fail")

        if self.prompts[id].schema:
            try:
                validate(instance=obj, schema=self.prompts[id].schema)
                logger.debug("Schema validation successful")
            except Exception as e:
                raise RuntimeError(f"Schema validation fail: {e}")

        return obj

    if resp_type == "jsonl":
        objects = self.parse_jsonl(resp)

        if not objects:
            logger.warning("JSONL parse returned no valid objects")
            return []

        # Validate each object against schema if provided
        if self.prompts[id].schema:
            validated = []
            for i, obj in enumerate(objects):
                try:
                    validate(instance=obj, schema=self.prompts[id].schema)
                    validated.append(obj)
                except Exception as e:
                    logger.warning(f"Object {i} failed schema validation: {e}")
            return validated

        return objects

    raise RuntimeError(f"Response type {resp_type} not known")
```

### Prompts Afectados

Los siguientes prompts deben migrarse al formato JSONL:

| ID del Prompt | Descripción | Campo de Tipo |
|-----------|-------------|------------|
| `extract-definitions` | Extracción de entidades/definiciones | No (un solo tipo) |
| `extract-relationships` | Extracción de relaciones | No (un solo tipo) |
| `extract-topics` | Extracción de temas/definiciones | No (un solo tipo) |
| `extract-rows` | Extracción de filas estructuradas | No (un solo tipo) |
| `agent-kg-extract` | Extracción combinada de definiciones + relaciones | Sí: `"definition"`, `"relationship"` |
| `extract-with-ontologies` / `ontology-extract` | Extracción basada en ontología | Sí: `"entity"`, `"relationship"`, `"attribute"` |

### Cambios en la API

#### Perspectiva del Cliente

El análisis JSONL es transparente para los clientes de la API del servicio de prompts. El análisis se
realiza en el servidor en el servicio de prompts, y la respuesta se devuelve a través del
campo estándar `PromptResponse.object` como una matriz JSON serializada.

Cuando los clientes llaman al servicio de prompts (a través de `PromptClient.prompt()` o similar):

**`response-type: "json"`** con esquema de matriz → el cliente recibe Python `list`
**`response-type: "jsonl"`** → el cliente recibe Python `list`

Desde la perspectiva del cliente, ambos devuelven estructuras de datos idénticas. La
diferencia es completamente en cómo se analiza la salida del LLM en el servidor:

Formato de matriz JSON: Una sola llamada a `json.loads()`; falla completamente si se trunca
Formato JSONL: Análisis línea por línea; produce resultados parciales si se trunca

Esto significa que el código de cliente existente que espera una lista de los prompts de extracción
no requiere cambios al migrar los prompts de JSON a JSONL.

#### Valor de Retorno del Servidor

Para `response-type: "jsonl"`, el método `PromptManager.invoke()` devuelve un
`list[dict]` que contiene todos los objetos analizados y validados correctamente. Esta
lista se serializa luego a JSON para el campo `PromptResponse.object`.

#### Manejo de Errores

Resultados vacíos: Devuelve una lista vacía `[]` con un registro de advertencia
Fallo parcial de análisis: Devuelve una lista de objetos analizados correctamente con
  registros de advertencia para los fallos
Fallo completo de análisis: Devuelve una lista vacía `[]` con registros de advertencia

Esto difiere de `response-type: "json"` que lanza `RuntimeError` en
caso de fallo de análisis. El comportamiento permisivo para JSONL es intencional para proporcionar
resistencia a la truncación.

### Ejemplo de Configuración

Ejemplo completo de configuración de prompt:

```json
{
  "prompt": "Extract all entities and their definitions from the following text. Output one JSON object per line.\n\nText:\n{{text}}\n\nOutput format per line:\n{\"entity\": \"<name>\", \"definition\": \"<definition>\"}",
  "response-type": "jsonl",
  "schema": {
    "type": "object",
    "properties": {
      "entity": {
        "type": "string",
        "description": "The entity name"
      },
      "definition": {
        "type": "string",
        "description": "A clear definition of the entity"
      }
    },
    "required": ["entity", "definition"]
  }
}
```

## Consideraciones de seguridad

**Validación de entrada**: El análisis JSON utiliza `json.loads()` estándar, que es seguro
  contra ataques de inyección.
**Validación de esquema**: Utiliza `jsonschema.validate()` para la aplicación de esquemas.
**Sin nueva superficie de ataque**: El análisis de JSONL es estrictamente más seguro que el análisis de matrices JSON
  debido al procesamiento línea por línea.

## Consideraciones de rendimiento

**Memoria**: El análisis línea por línea utiliza menos memoria máxima que la carga de matrices JSON completas.
  
**Latencia**: El rendimiento del análisis es comparable al análisis de matrices JSON.
**Validación**: La validación de esquema se ejecuta por objeto, lo que añade sobrecarga, pero
  permite resultados parciales en caso de fallo de la validación.

## Estrategia de pruebas

### Pruebas Unitarias

Análisis de JSONL con entrada válida
Análisis de JSONL con líneas vacías
Análisis de JSONL con bloques de código Markdown
Análisis de JSONL con línea final truncada
Análisis de JSONL con líneas JSON inválidas intercaladas
Validación de esquema con uniones discriminadas `oneOf`
Compatibilidad hacia atrás: las indicaciones existentes `"text"` y `"json"` no se modifican

### Pruebas de Integración

Extracción de extremo a extremo con indicaciones JSONL
Extracción con truncamiento simulado (respuesta artificialmente limitada)
Extracción de tipos mixtos con discriminador de tipo
Extracción de ontología con los tres tipos

### Pruebas de Calidad de Extracción

Comparar los resultados de la extracción: formato JSONL frente a formato de matriz JSON.
Verificar la resistencia a la truncación: JSONL produce resultados parciales donde JSON falla.

## Plan de Migración

### Fase 1: Implementación

1. Implementar el método `parse_jsonl()` en `PromptManager`.
2. Extender `invoke()` para manejar `response-type: "jsonl"`.
3. Agregar pruebas unitarias.

### Fase 2: Migración de Prompts

1. Actualizar el prompt y la configuración de `extract-definitions`.
2. Actualizar el prompt y la configuración de `extract-relationships`.
3. Actualizar el prompt y la configuración de `extract-topics`.
4. Actualizar el prompt y la configuración de `extract-rows`.
5. Actualizar el prompt y la configuración de `agent-kg-extract`.
6. Actualizar el prompt y la configuración de `extract-with-ontologies`.

### Fase 3: Actualizaciones Posteriores

1. Actualizar cualquier código que consuma los resultados de la extracción para manejar el tipo de retorno de lista.
2. Actualizar el código que categoriza las extracciones de tipos mixtos según el campo `type`.
3. Actualizar las pruebas que afirman sobre el formato de salida de la extracción.

## Preguntas Abiertas

Ninguna por el momento.

## Referencias

Implementación actual: `trustgraph-flow/trustgraph/template/prompt_manager.py`.
Especificación de JSON Lines: https://jsonlines.org/.
Esquema JSON `oneOf`: https://json-schema.org/understanding-json-schema/reference/combining.html#oneof.
Especificación relacionada: Streaming LLM Responses (`docs/tech-specs/streaming-llm-responses.md`).
