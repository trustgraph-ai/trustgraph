# Especificación Técnica de la Estructura de Ontologías

## Resumen

Esta especificación describe la estructura y el formato de las ontologías dentro del sistema TrustGraph. Las ontologías proporcionan modelos de conocimiento formales que definen clases, propiedades y relaciones, lo que permite capacidades de razonamiento e inferencia. El sistema utiliza un formato de configuración inspirado en OWL que representa ampliamente los conceptos de OWL/RDFS, al tiempo que está optimizado para los requisitos de TrustGraph.

**Convención de Nombres**: Este proyecto utiliza kebab-case para todos los identificadores (claves de configuración, puntos finales de la API, nombres de módulos, etc.) en lugar de snake_case.

## Objetivos

- **Gestión de Clases y Propiedades**: Definir clases similares a OWL con propiedades, dominios, rangos y restricciones de tipo.
- **Soporte Semántico Avanzado**: Permitir propiedades completas de RDFS/OWL, incluyendo etiquetas, soporte multilingüe y restricciones formales.
- **Soporte para Múltiples Ontologías**: Permitir que múltiples ontologías coexistan e interactúen.
- **Validación y Razonamiento**: Asegurar que las ontologías cumplan con estándares similares a OWL, con verificación de consistencia y soporte de inferencia.
- **Compatibilidad con Estándares**: Soporte de importación/exportación en formatos estándar (Turtle, RDF/XML, OWL/XML) al tiempo que se mantiene la optimización interna.

## Antecedentes

TrustGraph almacena ontologías como elementos de configuración en un sistema flexible de clave-valor. Si bien el formato está inspirado en OWL (Web Ontology Language), está optimizado para los casos de uso específicos de TrustGraph y no se adhiere estrictamente a todas las especificaciones de OWL.

Las ontologías en TrustGraph permiten:
- Definición de tipos de objetos formales y sus propiedades.
- Especificación de dominios, rangos y restricciones de tipo de propiedades.
- Razonamiento e inferencia lógicos.
- Relaciones complejas y restricciones de cardinalidad.
- Soporte multilingüe para la internacionalización.

## Estructura de la Ontología

### Almacenamiento de la Configuración

Las ontologías se almacenan como elementos de configuración con el siguiente patrón:
- **Tipo**: `ontology`
- **Clave**: Identificador de ontología único (por ejemplo, `natural-world`, `domain-model`).
- **Valor**: Ontología completa en formato JSON.

### Estructura JSON

El formato JSON de la ontología consta de cuatro secciones principales:

#### 1. Metadatos

Contiene información administrativa y descriptiva sobre la ontología:

```json
{
  "metadata": {
    "name": "The natural world",
    "description": "Ontology covering the natural order",
    "version": "1.0.0",
    "created": "2025-09-20T12:07:37.068Z",
    "modified": "2025-09-20T12:12:20.725Z",
    "creator": "current-user",
    "namespace": "http://trustgraph.ai/ontologies/natural-world",
    "imports": ["http://www.w3.org/2002/07/owl#"]
  }
}
```

**Campos:**
- `name`: Nombre legible por humanos de la ontología.
- `description`: Descripción breve del propósito de la ontología.
- `version`: Número de versión semántico.
- `created`: Marca de tiempo ISO 8601 de creación.
- `modified`: Marca de tiempo ISO 8601 de última modificación.
- `creator`: Identificador del usuario/sistema que creó.
- `namespace`: URI base para elementos de la ontología.
- `imports`: Matriz de URIs de ontologías importadas.

#### 2. Clases

Define los tipos de objetos y sus relaciones jerárquicas:

```json
{
  "classes": {
    "animal": {
      "uri": "http://trustgraph.ai/ontologies/natural-world#animal",
      "type": "owl:Class",
      "rdfs:label": [{"value": "Animal", "lang": "en"}],
      "rdfs:comment": "An animal",
      "rdfs:subClassOf": "lifeform",
      "owl:equivalentClass": ["creature"],
      "owl:disjointWith": ["plant"],
      "dcterms:identifier": "ANI-001"
    }
  }
}
```

**Propiedades soportadas:**
- `uri`: URI completa de la clase.
- `type`: Siempre `"owl:Class"`.
- `rdfs:label`: Matriz de etiquetas con etiquetas de idioma.
- `rdfs:comment`: Descripción de la clase.
- `rdfs:subClassOf`: Identificador de la clase padre (herencia simple).
- `owl:equivalentClass`: Lista de clases equivalentes.
- `owl:disjointWith`: Lista de clases disjuntas.
- `dcterms:identifier`: Identificador de la clase.

#### 3. Propiedades de Objetos

Define las relaciones entre las clases:

```json
{
  "objectProperties": {
    "hasPart": {
      "uri": "http://trustgraph.ai/ontologies/natural-world#hasPart",
      "type": "owl:ObjectProperty",
      "rdfs:label": [{"value": "hasPart", "lang": "en"}],
      "rdfs:comment": "Represents a part-whole relationship",
      "domain": "lifeform",
      "range": "lifeform"
    }
  }
}
```

**Propiedades soportadas:**
- `uri`: URI completa de la propiedad de objeto.
- `type`: Siempre `"owl:ObjectProperty"`.
- `rdfs:label`: Matriz de etiquetas con etiquetas de idioma.
- `rdfs:comment`: Descripción de la propiedad de objeto.
- `domain`: Clase de dominio de la propiedad de objeto.
- `range`: Clase de rango de la propiedad de objeto.

#### 4. Propiedades de Datos

Define las características de las clases:

```json
{
  "datatypeProperties": {
    "number-of-legs": {
      "uri": "http://trustgraph.ai/ontologies/natural-world#number-of-legs",
      "type": "owl:DatatypeProperty",
      "rdfs:label": [{"value": "number-of-legs", "lang": "en"}],
      "rdfs:comment": "Count of number of legs of the animal",
      "rdfs:range": "xsd:nonNegativeInteger",
      "rdfs:domain": "animal"
    }
  }
}
```

**Propiedades soportadas:**
- `uri`: URI completa de la propiedad de datos.
- `type`: Siempre `"owl:DatatypeProperty"`.
- `rdfs:label`: Matriz de etiquetas con etiquetas de idioma.
- `rdfs:comment`: Descripción de la propiedad de datos.
- `rdfs:range`: Tipo de datos de la propiedad de datos.
- `rdfs:domain`: Clase de dominio de la propiedad de datos.

### Estructura JSON

El formato JSON de la ontología consta de cuatro secciones principales:

#### 1. Metadatos

Contiene información administrativa y descriptiva sobre la ontología:

```json
{
  "metadata": {
    "name": "The natural world",
    "description": "Ontology covering the natural order",
    "version": "1.0.0",
    "created": "2025-09-20T12:07:37.068Z",
    "modified": "2025-09-20T12:12:20.725Z",
    "creator": "current-user",
    "namespace": "http://trustgraph.ai/ontologies/natural-world",
    "imports": ["http://www.w3.org/2002/07/owl#"]
  }
}
```

**Campos:**
- `name`: Nombre legible por humanos de la ontología.
- `description`: Descripción breve del propósito de la ontología.
- `version`: Número de versión semántico.
- `created`: Marca de tiempo ISO 8601 de creación.
- `modified`: Marca de tiempo ISO 8601 de última modificación.
- `creator`: Identificador del usuario/sistema que creó.
- `namespace`: URI base para elementos de la ontología.
- `imports`: Matriz de URIs de ontologías importadas.

#### 2. Clases

Define los tipos de objetos y sus relaciones jerárquicas:

```json
{
  "classes": {
    "lifeform": {
      "uri": "http://trustgraph.ai/ontologies/natural-world#lifeform",
      "type": "owl:Class",
      "rdfs:label": [{"value": "Lifeform", "lang": "en"}],
      "rdfs:comment": "A living thing"
    },
    "animal": {
      "uri": "http://trustgraph.ai/ontologies/natural-world#animal",
      "type": "owl:Class",
      "rdfs:label": [{"value": "Animal", "lang": "en"}],
      "rdfs:comment": "An animal",
      "rdfs:subClassOf": "lifeform"
    },
    "cat": {
      "uri": "http://trustgraph.ai/ontologies/natural-world#cat",
      "type": "owl:Class",
      "rdfs:label": [{"value": "Cat", "lang": "en"}],
      "rdfs:comment": "A cat",
      "rdfs:subClassOf": "animal"
    },
    "dog": {
      "uri": "http://trustgraph.ai/ontologies/natural-world#dog",
      "type": "owl:Class",
      "rdfs:label": [{"value": "Dog", "lang": "en"}],
      "rdfs:comment": "A dog",
      "rdfs:subClassOf": "animal",
      "owl:disjointWith": ["cat"]
    }
  },
  "objectProperties": {},
  "datatypeProperties": {
    "number-of-legs": {
      "uri": "http://trustgraph.ai/ontologies/natural-world#number-of-legs",
      "type": "owl:DatatypeProperty",
      "rdfs:label": [{"value": "number-of-legs", "lang": "en"}],
      "rdfs:comment": "Count of number of legs of the animal",
      "rdfs:range": "xsd:nonNegativeInteger",
      "rdfs:domain": "animal"
    }
  }
}
```

## Reglas de Validación

### Validación Estructural

1. **Consistencia de URI**: Todos los URIs deben seguir el patrón `{namespace}#{identifier}`.
2. **Jerarquía de Clases**: No debe haber herencia circular en `rdfs:subClassOf`.
3. **Dominios/Rangos de Propiedades**: Deben referenciar clases existentes o tipos XSD válidos.
4. **Clases Disjuntas**: No pueden ser subclases entre sí.
5. **Propiedades Inversas**: Deben ser bidireccionales si se especifican.

### Validación Semántica

1. **Identificadores Únicos**: Los identificadores de clase y propiedad deben ser únicos dentro de una ontología.
2. **Etiquetas de Idioma**: Deben seguir el formato de etiqueta de idioma BCP 47.
3. **Restricciones de Cardinalidad**: `minCardinality` ≤ `maxCardinality` cuando ambos están especificados.
4. **Propiedades Funcionales**: No pueden tener `maxCardinality` > 1.

## Soporte de Formato de Importación/Exportación

Si bien el formato interno es JSON, el sistema admite la conversión a/desde formatos de ontología estándar:

- **Turtle (.ttl)**: Serialización RDF compacta.
- **RDF/XML (.rdf, .owl)**: Formato estándar de W3C.
- **OWL/XML (.owx)**: Formato XML específico de OWL.
- **JSON-LD (.jsonld)**: JSON para Linked Data.

## Referencias

- [OWL 2 Web Ontology Language](https://www.w3.org/TR/owl2-overview/)
- [RDF Schema 1.1](https://www.w3.org/TR/rdf-schema/)
- [XML Schema Datatypes](https://www.w3.org/TR/xmlschema-2/)
- [BCP 47 Language Tags](https://tools.ietf.org/html/bcp47)