---
layout: default
title: "Especificación Técnica de Contextos de Grafos"
parent: "Spanish (Beta)"
---

# Especificación Técnica de Contextos de Grafos

> **Beta Translation:** This document was translated via Machine Learning and as such may not be 100% accurate. All non-English languages are currently classified as Beta.

## Resumen

Esta especificación describe los cambios en los primitivos de grafos centrales de TrustGraph para
alinearse con RDF 1.2 y admitir la semántica completa del conjunto de datos RDF. Este es un
cambio importante para la serie de versiones 2.x.

### Versionamiento

- **2.0**: Lanzamiento para adoptantes tempranos. Características principales disponibles,
  puede que no esté completamente lista para producción.
- **2.1 / 2.2**: Lanzamiento de producción. Estabilidad y completitud validadas.

La flexibilidad en cuanto a la madurez es intencional: los adoptantes tempranos pueden acceder a nuevas
capacidades antes de que todas las funciones estén listas para producción.

## Objetivos

Los objetivos principales de este trabajo son habilitar metadatos sobre hechos/afirmaciones:

- **Información temporal**: Asociar hechos con metadatos de tiempo
  - Cuándo se creyó que un hecho era verdadero
  - Cuándo un hecho se volvió verdadero
  - Cuándo se descubrió que un hecho era falso

- **Origen/Fuentes**: Realizar un seguimiento de las fuentes que respaldan un hecho
  - "Este hecho fue respaldado por la fuente X"
  - Enlazar los hechos con sus documentos de origen

- **Veracidad/Confianza**: Registrar afirmaciones sobre la verdad
  - "La persona P afirmó que esto era cierto"
  - "La persona Q afirma que esto es falso"
  - Habilitar la puntuación de confianza y la detección de conflictos

**Hipótesis**: La reificación (RDF-star / triples con comillas) es el mecanismo clave
para lograr estos resultados, ya que todos requieren hacer afirmaciones sobre afirmaciones.

## Antecedentes

Para expresar "el hecho (Alice conoce a Bob) se descubrió el 2024-01-15" o
"la fuente X respalda la afirmación (Y causa Z)", necesita referenciar un borde
como algo sobre lo cual se pueden hacer afirmaciones. Los triples estándar no admiten esto.

### Limitaciones actuales

La clase `Value` actual en `trustgraph-base/trustgraph/schema/core/primitives.py`
puede representar:
- Nodos URI (`is_uri=True`)
- Valores literales (`is_uri=False`)

El campo `type` existe, pero no se utiliza para representar los tipos de datos XSD.

## Diseño técnico

### Características de RDF a admitir

#### Características principales (relacionadas con los objetivos de reificación)

Estas características están directamente relacionadas con los objetivos temporales, de origen y de veracidad:

1. **RDF 1.2 Triples con comillas (RDF-star)**
   - Bordes que apuntan a otros bordes
   - Un triple puede aparecer como sujeto u objeto de otro triple
   - Permite hacer afirmaciones sobre afirmaciones (reificación)
   - Mecanismo central para anotar hechos individuales

2. **Conjunto de datos RDF / Grafos con nombre**
   - Soporte para múltiples grafos con nombre dentro de un conjunto de datos
   - Cada grafo identificado por un IRI
   - Pasa de triples (s, p, o) a cuads (s, p, o, g)
   - Incluye un grafo predeterminado más cero o más grafos con nombre
   - El IRI del grafo puede ser un sujeto en las afirmaciones, por ejemplo:
     ```
     <graph-source-A> <discoveredOn> "2024-01-15"
     <graph-source-A> <hasVeracity> "high"
     ```
   - Nota: Los grafos con nombre son una característica separada de la reificación. Tienen
     usos más allá de la anotación de afirmaciones (particionamiento, control de acceso, organización del conjunto de datos)
     y deben tratarse como una capacidad distinta.

3. **Nodos vacíos** (Soporte limitado)
   - Nodos anónimos sin un URI global
   - Compatible al cargar datos RDF externos
   - **Estado limitado**: No hay garantías sobre la identidad estable después de la carga
   - Encontrarlos a través de consultas comodín (coincidencia por conexiones, no por ID)
   - No es una característica de primera clase: no confíe en el manejo preciso de nodos vacíos.

#### Correcciones oportunistas (cambio importante de la versión 2.0)

Estas características no están directamente relacionadas con los objetivos de la reificación, pero son
mejoras valiosas a incluir al realizar cambios importantes:

4. **Tipos de literales**
   - Utilice correctamente el campo `type` para los tipos de datos XSD
   - Ejemplos: xsd:string, xsd:integer, xsd:dateTime, etc.
   - Corrige la limitación actual: no se pueden representar fechas o enteros correctamente.

5. **Etiquetas de idioma**
   - Soporte para atributos de idioma en literales (por ejemplo, @en, @fr)
   - Nota: un literal tiene una etiqueta de idioma O un tipo de datos, no ambos
     (excepto para rdf:langString)
   - Importante para casos de uso de IA/multilingües.

### Modelos de datos

#### Término (cambiar de Value)

La clase `Value` se renombrará a `Term` para reflejar mejor la terminología de RDF.
Este cambio de nombre tiene dos propósitos:
1. Alinea la nomenclatura con los conceptos de RDF (un "Término" puede ser un IRI, literal, nodo vacío o triple con comillas,
   no solo un "valor")
2. Fuerza la revisión del código en la interfaz de cambio importante: cualquier código que aún haga referencia a `Value`
   se considera roto y debe actualizarse.

Un Término puede representar:

- **IRI/URI**: un nodo/recurso con nombre
- **Nodo vacío**: un nodo anónimo con alcance local
- **Literal**: un valor de datos con:
  - Un tipo de datos (tipo XSD), O
  - Una etiqueta de idioma
- **Triple con comillas**: un triple utilizado como término (RDF 1.2)

##### Enfoque elegido: Clase única con discriminador de tipo

Los requisitos de serialización impulsan la estructura: se necesita un discriminador de tipo en el formato de cable
independientemente de la representación de Python. Una clase única con un campo de tipo es la opción natural y se alinea con la
patrón `Value` actual.

Los códigos de tipo de un solo carácter proporcionan una serialización compacta:

```python
from dataclasses import dataclass

# Constantes de tipo de término
IRI = "i"      # Nodo IRI/URI
BLANK = "b"    # Nodo vacío
LITERAL = "l"  # Valor literal
TRIPLE = "t"   # Triple con comillas (RDF 1.2)

@dataclass
class Term:
    type: str = ""  # Uno de: IRI, BLANK, LITERAL, TRIPLE

    # Para términos IRI (type == IRI)
    iri: str = ""

    # Para nodos vacíos (type == BLANK)
    id: str = ""

    # Para literales (type == LITERAL)
    value: str = ""
    datatype: str = ""   # URI de tipo de datos XSD (mutuamente excluyente con el idioma)
    language: str = ""   # Etiqueta de idioma (mutuamente excluyente con el tipo de datos)

    # Para triples con comillas (type == TRIPLE)
    triple: "Triple | None" = None
```

Ejemplos de uso:

```python
# Término IRI
node = Term(type=IRI, iri="http://example.org/Alice")

# Literal con tipo de datos
age = Term(type=LITERAL, value="42", datatype="xsd:integer")

# Literal con etiqueta de idioma
label = Term(type=LITERAL, value="Hello", language="en")

# Nodo vacío
anon = Term(type=BLANK, id="_:b1")

# Triple con comillas (afirmación sobre una afirmación)
inner = Triple(
    s=Term(type=IRI, iri="http://example.org/Alice"),
    p=Term(type=IRI, iri="http://example.org/knows"),
    o=Term(type=IRI, iri="http://example.org/Bob"),
)
reified = Term(type=TRIPLE, triple=inner)
```

##### Alternativas consideradas

**Opción B: Unión de clases especializadas** (`Term = IRI | BlankNode | Literal | QuotedTriple`)
- Rechazada: La serialización aún necesitaría un discriminador de tipo, lo que agregaría complejidad.

**Opción C: Clase base con subclases**
- Rechazada: El mismo problema de serialización, además de peculiaridades de la herencia de dataclass.

#### Triple / Cuad

La clase `Triple` gana un campo de grafo opcional para convertirse en un cuad:

```python
@dataclass
class Triple:
    s: Term | None = None    # Sujeto
    p: Term | None = None    # Predicado
    o: Term | None = None    # Objeto
    g: str | None = None     # Nombre del grafo (IRI), None = grafo predeterminado
```

Decisiones de diseño:
- **Nombre del campo**: `g` para la coherencia con `s`, `p`, `o`
- **Opcional**: `None` significa el grafo predeterminado (sin nombre)
- **Tipo**: Cadena simple (IRI) en lugar de Term
  - Los nombres de los grafos siempre son IRIs
  - Los nodos vacíos como nombres de grafos se descartaron (demasiado confusos)
  - No es necesario el conjunto completo de mecanismos de Term

Nota: El nombre de la clase permanece `Triple` incluso si técnicamente es un cuad ahora.
Esto evita la alteración y la terminología "triple" todavía es la terminología común. El contexto del grafo es
metadatos sobre dónde vive el triple.

### Patrones de consulta candidatos

El motor de consulta actual acepta combinaciones de términos S, P, O. Con los triples con comillas,
un triple en sí mismo se convierte en un término válido en esas posiciones. A continuación, se presentan patrones de consulta
candidatos que admiten los objetivos originales.

#### Semántica de parámetros de grafo

Siguiendo las convenciones de SPARQL para la compatibilidad hacia atrás:

- **`g` omitido / None**: Consulta solo el grafo predeterminado
- **`g` = IRI específico**: Consulta solo ese grafo con nombre
- **`g` = comodín / `*`**: Consulta en todos los grafos (equivalente a `GRAPH ?g { ... }` de SPARQL)

Esto mantiene las consultas simples simples y hace que las consultas de grafos con nombre sean opcionales.

Las consultas entre grafos (g=comodín) se admiten completamente. El esquema de Cassandra incluye tablas dedicadas (SPOG, POSG, OSPG)
donde g es una columna de agrupación, en lugar de una clave de partición, lo que permite consultas eficientes en todos los grafos.

#### Consultas temporales

**Encontrar todos los hechos descubiertos después de una fecha determinada:**
```
S: ?                                    # cualquier triple con comillas
P: <discoveredOn>
O: > "2024-01-15"^^xsd:date             # comparación de fecha
```

**Encontrar cuándo se creyó que un hecho era verdadero:**
```
S: << <Alice> <knows> <Bob> >>          # triple con comillas como sujeto
P: <believedTrueFrom>
O: ?                                    # devuelve la fecha
```

**Encontrar los hechos que se descubrió que eran falsos:**
```
S: ?                                    # cualquier triple con comillas
P: <discoveredFalseOn>
O: ?                                    # tiene cualquier valor (existe)
```

#### Consultas de origen

**Encontrar todos los hechos respaldados por una fuente específica:**
```
S: ?                                    # cualquier triple con comillas
P: <supportedBy>
O: <source:document-123>
```

**Encontrar qué fuentes respaldan un hecho específico:**
```
S: << <DrugA> <treats> <DiseaseB> >>    # triple con comillas como sujeto
P: <supportedBy>
O: ?                                    # devuelve las IRIs de la fuente
```

#### Consultas de veracidad

**Encontrar las afirmaciones que una persona marcó como verdaderas:**
```
S: ?                                    # cualquier triple con comillas
P: <assertedTrueBy>
O: <person:Alice>
```

**Encontrar las afirmaciones conflictivas (el mismo hecho, diferente veracidad):**
```
# Primera consulta: hechos afirmados como verdaderos
S: ?
P: <assertedTrueBy>
O: ?

# Segunda consulta: hechos afirmados como falsos
S: ?
P: <assertedFalseBy>
O: ?

# Lógica de la aplicación: encontrar la intersección de los sujetos
```

**Encontrar los hechos con una puntuación de confianza por debajo del umbral:**
```
S: ?                                    # cualquier triple con comillas
P: <trustScore>
O: < 0.5                                # comparación numérica
```

### Arquitectura

Se requieren cambios significativos en varios componentes:

#### Este repositorio (trustgraph)

- **Primitivos del esquema** (`trustgraph-base/trustgraph/schema/core/primitives.py`)
  - `Value` → `Term` cambio de nombre
  - Nueva estructura de `Term` con discriminador de tipo
  - `Triple` gana el campo `g` para el contexto del grafo

- **Traductores de mensajes** (`trustgraph-base/trustgraph/messaging/translators/`)
  - Actualizaciones para las nuevas estructuras de `Term` y `Triple`

- **Componentes de puerta de enlace**
  - Manejar nuevas estructuras de `Term` y cuádruple

- **Núcleos de conocimiento**
  - ...

- **Pruebas**
  - ...

Esto se deja para futuras implementaciones.

- **Vector store boundary**
  - ...

Esto se deja para futuras implementaciones.

## Consideraciones de seguridad

Los grafos con nombre no son una característica de seguridad. Los usuarios y las colecciones siguen siendo los límites de seguridad.
Los grafos con nombre son puramente para la organización de datos y el soporte de la reificación.

## Consideraciones de rendimiento

- Los triples con comillas agregan profundidad de anidamiento; esto puede afectar el rendimiento de las consultas.
- Se necesitan estrategias de indexación para consultas con ámbito de grafo.
- El diseño del esquema de Cassandra deberá acomodar el almacenamiento de cuádruples de forma eficiente.

### Límite del almacén vectorial

Los almacenes vectoriales siempre hacen referencia a IRIs:
- Nunca bordes (triples con comillas)
- Nunca valores literales
- Nunca nodos vacíos

Esto mantiene el almacén vectorial simple; se encarga de la similitud semántica de las entidades con nombre. La estructura del grafo maneja las relaciones, la reificación y los metadatos. Los triples con comillas y los grafos con nombre no complican las operaciones vectoriales.

## Estrategia de pruebas

Utilice la estrategia de prueba existente. Dado que esta es una versión importante, se prestará especial atención al
conjunto de pruebas de extremo a extremo para validar que las nuevas estructuras funcionan correctamente en todos los componentes.

## Plan de migración

- La versión 2.0 es una versión importante; no se requiere compatibilidad con versiones anteriores
- Los datos existentes pueden necesitar migrarse al nuevo esquema (por determinarse según el diseño final)
- Considere herramientas de migración para convertir triples existentes

## Preguntas abiertas

- **Nodos vacíos**: Soporte limitado confirmado. Es posible que deba decidirse sobre una estrategia de skolemización (generar IRIs
  al cargar o preservar los ID de nodos vacíos).
- **Sintaxis de consulta**: ¿Cuál es la sintaxis concreta para especificar triples con comillas en las consultas? Debe definirse
  la API de consulta.
- ~~**Vocabulario de predicados**~~: Resuelto. Se permiten todos los predicados RDF válidos, incluidos los personalizados definidos por el usuario.
  Supuestos mínimos sobre la validez de RDF. Muy pocos valores bloqueados (por ejemplo, `rdfs:label` se utiliza en algunos lugares).
  Estrategia: evite bloquear cualquier cosa a menos que sea absolutamente necesario.
- ~~**Impacto del almacén vectorial**~~: Resuelto. Los almacenes vectoriales siempre apuntan a IRIs.
  solo; nunca bordes, literales o nodos vacíos. Los triples con comillas y la reificación no afectan al almacén vectorial.
- ~~**Semántica del grafo con nombre**~~: Resuelta. Las consultas predeterminadas son para el grafo predeterminado (coincide con el comportamiento de SPARQL,
  compatible con versiones anteriores). Se requiere un parámetro de grafo explícito para consultar grafos con nombre o todos los grafos.

## Referencias

- [Conceptos RDF 1.2](https://www.w3.org/TR/rdf12-concepts/)
- [RDF-star y SPARQL-star](https://w3c.github.io/rdf-star/)
- [Conjunto de datos RDF](https://www.w3.org/TR/rdf11-concepts/#section-dataset)
