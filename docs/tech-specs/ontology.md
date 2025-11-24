# Ontology Structure Technical Specification

## Overview

This specification describes the structure and format of ontologies within the TrustGraph system. Ontologies provide formal knowledge models that define classes, properties, and relationships, supporting reasoning and inference capabilities. The system uses an OWL-inspired configuration format that broadly represents OWL/RDFS concepts while being optimized for TrustGraph's requirements.

**Naming Convention**: This project uses kebab-case for all identifiers (configuration keys, API endpoints, module names, etc.) rather than snake_case.

## Goals

- **Class and Property Management**: Define OWL-like classes with properties, domains, ranges, and type constraints
- **Rich Semantic Support**: Enable comprehensive RDFS/OWL properties including labels, multi-language support, and formal constraints
- **Multi-Ontology Support**: Allow multiple ontologies to coexist and interoperate
- **Validation and Reasoning**: Ensure ontologies conform to OWL-like standards with consistency checking and inference support
- **Standard Compatibility**: Support import/export in standard formats (Turtle, RDF/XML, OWL/XML) while maintaining internal optimization

## Background

TrustGraph stores ontologies as configuration items in a flexible key-value system. While the format is inspired by OWL (Web Ontology Language), it is optimized for TrustGraph's specific use cases and does not strictly adhere to all OWL specifications.

Ontologies in TrustGraph enable:
- Definition of formal object types and their properties
- Specification of property domains, ranges, and type constraints
- Logical reasoning and inference
- Complex relationships and cardinality constraints
- Multi-language support for internationalization

## Ontology Structure

### Configuration Storage

Ontologies are stored as configuration items with the following pattern:
- **Type**: `ontology`
- **Key**: Unique ontology identifier (e.g., `natural-world`, `domain-model`)
- **Value**: Complete ontology in JSON format

### JSON Structure

The ontology JSON format consists of four main sections:

#### 1. Metadata

Contains administrative and descriptive information about the ontology:

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

**Fields:**
- `name`: Human-readable name of the ontology
- `description`: Brief description of the ontology's purpose
- `version`: Semantic version number
- `created`: ISO 8601 timestamp of creation
- `modified`: ISO 8601 timestamp of last modification
- `creator`: Identifier of the creating user/system
- `namespace`: Base URI for ontology elements
- `imports`: Array of imported ontology URIs

#### 2. Classes

Defines the object types and their hierarchical relationships:

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

**Supported Properties:**
- `uri`: Full URI of the class
- `type`: Always `"owl:Class"`
- `rdfs:label`: Array of language-tagged labels
- `rdfs:comment`: Description of the class
- `rdfs:subClassOf`: Parent class identifier (single inheritance)
- `owl:equivalentClass`: Array of equivalent class identifiers
- `owl:disjointWith`: Array of disjoint class identifiers
- `dcterms:identifier`: Optional external reference identifier

#### 3. Object Properties

Properties that link instances to other instances:

```json
{
  "objectProperties": {
    "has-parent": {
      "uri": "http://trustgraph.ai/ontologies/natural-world#has-parent",
      "type": "owl:ObjectProperty",
      "rdfs:label": [{"value": "has parent", "lang": "en"}],
      "rdfs:comment": "Links an animal to its parent",
      "rdfs:domain": "animal",
      "rdfs:range": "animal",
      "owl:inverseOf": "parent-of",
      "owl:functionalProperty": false
    }
  }
}
```

**Supported Properties:**
- `uri`: Full URI of the property
- `type`: Always `"owl:ObjectProperty"`
- `rdfs:label`: Array of language-tagged labels
- `rdfs:comment`: Description of the property
- `rdfs:domain`: Class identifier that has this property
- `rdfs:range`: Class identifier for property values
- `owl:inverseOf`: Identifier of inverse property
- `owl:functionalProperty`: Boolean indicating at most one value
- `owl:inverseFunctionalProperty`: Boolean for unique identifying properties

#### 4. Datatype Properties

Properties that link instances to literal values:

```json
{
  "datatypeProperties": {
    "number-of-legs": {
      "uri": "http://trustgraph.ai/ontologies/natural-world#number-of-legs",
      "type": "owl:DatatypeProperty",
      "rdfs:label": [{"value": "number of legs", "lang": "en"}],
      "rdfs:comment": "Count of number of legs of the animal",
      "rdfs:domain": "animal",
      "rdfs:range": "xsd:nonNegativeInteger",
      "owl:functionalProperty": true,
      "owl:minCardinality": 0,
      "owl:maxCardinality": 1
    }
  }
}
```

**Supported Properties:**
- `uri`: Full URI of the property
- `type`: Always `"owl:DatatypeProperty"`
- `rdfs:label`: Array of language-tagged labels
- `rdfs:comment`: Description of the property
- `rdfs:domain`: Class identifier that has this property
- `rdfs:range`: XSD datatype for property values
- `owl:functionalProperty`: Boolean indicating at most one value
- `owl:minCardinality`: Minimum number of values (optional)
- `owl:maxCardinality`: Maximum number of values (optional)
- `owl:cardinality`: Exact number of values (optional)

### Supported XSD Datatypes

The following XML Schema datatypes are supported for datatype property ranges:

- `xsd:string` - Text values
- `xsd:integer` - Integer numbers
- `xsd:nonNegativeInteger` - Non-negative integers
- `xsd:float` - Floating point numbers
- `xsd:double` - Double precision numbers
- `xsd:boolean` - True/false values
- `xsd:dateTime` - Date and time values
- `xsd:date` - Date values
- `xsd:anyURI` - URI references

### Language Support

Labels and comments support multiple languages using the W3C language tag format:

```json
{
  "rdfs:label": [
    {"value": "Animal", "lang": "en"},
    {"value": "Tier", "lang": "de"},
    {"value": "Animal", "lang": "es"}
  ]
}
```

## Example Ontology

Here's a complete example of a simple ontology:

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
  },
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

## Validation Rules

### Structural Validation

1. **URI Consistency**: All URIs should follow the pattern `{namespace}#{identifier}`
2. **Class Hierarchy**: No circular inheritance in `rdfs:subClassOf`
3. **Property Domains/Ranges**: Must reference existing classes or valid XSD types
4. **Disjoint Classes**: Cannot be subclasses of each other
5. **Inverse Properties**: Must be bidirectional if specified

### Semantic Validation

1. **Unique Identifiers**: Class and property identifiers must be unique within an ontology
2. **Language Tags**: Must follow BCP 47 language tag format
3. **Cardinality Constraints**: `minCardinality` ≤ `maxCardinality` when both specified
4. **Functional Properties**: Cannot have `maxCardinality` > 1

## Import/Export Format Support

While the internal format is JSON, the system supports conversion to/from standard ontology formats:

- **Turtle (.ttl)** - Compact RDF serialization
- **RDF/XML (.rdf, .owl)** - W3C standard format
- **OWL/XML (.owx)** - OWL-specific XML format
- **JSON-LD (.jsonld)** - JSON for Linked Data

## References

- [OWL 2 Web Ontology Language](https://www.w3.org/TR/owl2-overview/)
- [RDF Schema 1.1](https://www.w3.org/TR/rdf-schema/)
- [XML Schema Datatypes](https://www.w3.org/TR/xmlschema-2/)
- [BCP 47 Language Tags](https://tools.ietf.org/html/bcp47)