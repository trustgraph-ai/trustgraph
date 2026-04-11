# Especificação Técnica da Estrutura da Ontologia

## Visão Geral

Esta especificação descreve a estrutura e o formato das ontologias dentro do sistema TrustGraph. As ontologias fornecem modelos de conhecimento formais que definem classes, propriedades e relacionamentos, suportando capacidades de raciocínio e inferência. O sistema usa um formato de configuração inspirado em OWL que representa amplamente os conceitos OWL/RDFS, ao mesmo tempo que é otimizado para os requisitos do TrustGraph.

**Convenção de Nomenclatura**: Este projeto usa kebab-case para todos os identificadores (chaves de configuração, pontos finais de API, nomes de módulos, etc.) em vez de snake_case.

## Objetivos

**Gerenciamento de Classes e Propriedades**: Definir classes semelhantes a OWL com propriedades, domínios, intervalos e restrições de tipo.
**Suporte Semântico Rico**: Habilitar propriedades abrangentes RDFS/OWL, incluindo rótulos, suporte multilíngue e restrições formais.
**Suporte a Múltiplas Ontologias**: Permitir que várias ontologias coexistam e interoperem.
**Validação e Raciocínio**: Garantir que as ontologias estejam em conformidade com padrões semelhantes a OWL, com verificação de consistência e suporte de inferência.
**Compatibilidade com Padrões**: Suportar importação/exportação em formatos padrão (Turtle, RDF/XML, OWL/XML) mantendo a otimização interna.

## Contexto

O TrustGraph armazena ontologias como itens de configuração em um sistema flexível de chave-valor. Embora o formato seja inspirado em OWL (Web Ontology Language), ele é otimizado para casos de uso específicos do TrustGraph e não adere estritamente a todas as especificações do OWL.

As ontologias no TrustGraph permitem:
Definição de tipos de objetos formais e suas propriedades.
Especificação de domínios, intervalos e restrições de tipo de propriedade.
Raciocínio e inferência lógica.
Relacionamentos complexos e restrições de cardinalidade.
Suporte multilíngue para internacionalização.

## Estrutura da Ontologia

### Armazenamento de Configuração

As ontologias são armazenadas como itens de configuração com o seguinte padrão:
**Tipo**: `ontology`
**Chave**: Identificador de ontologia exclusivo (por exemplo, `natural-world`, `domain-model`)
**Valor**: Ontologia completa em formato JSON.

### Estrutura JSON

O formato JSON da ontologia consiste em quatro seções principais:

#### 1. Metadados

Contém informações administrativas e descritivas sobre a ontologia:

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
`name`: Nome legível para humanos da ontologia
`description`: Breve descrição do propósito da ontologia
`version`: Número de versão semântico
`created`: Carimbo de data/hora ISO 8601 de criação
`modified`: Carimbo de data/hora ISO 8601 da última modificação
`creator`: Identificador do usuário/sistema que criou
`namespace`: URI base para elementos da ontologia
`imports`: Array de URIs de ontologias importadas

#### 2. Classes

Define os tipos de objeto e seus relacionamentos hierárquicos:

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

**Propriedades Suportadas:**
`uri`: URI completo da classe
`type`: Sempre `"owl:Class"`
`rdfs:label`: Array de rótulos com informações de idioma
`rdfs:comment`: Descrição da classe
`rdfs:subClassOf`: Identificador da classe pai (herança simples)
`owl:equivalentClass`: Array de identificadores de classes equivalentes
`owl:disjointWith`: Array de identificadores de classes disjuntas
`dcterms:identifier`: Identificador de referência externa opcional

#### 3. Propriedades de Objeto

Propriedades que conectam instâncias a outras instâncias:

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

**Propriedades Suportadas:**
`uri`: URI completo da propriedade
`type`: Sempre `"owl:ObjectProperty"`
`rdfs:label`: Array de rótulos com informações de idioma
`rdfs:comment`: Descrição da propriedade
`rdfs:domain`: Identificador da classe que possui esta propriedade
`rdfs:range`: Identificador da classe para valores de propriedade
`owl:inverseOf`: Identificador da propriedade inversa
`owl:functionalProperty`: Booleano indicando no máximo um valor
`owl:inverseFunctionalProperty`: Booleano para propriedades de identificação única

#### 4. Propriedades de Tipo de Dado

Propriedades que conectam instâncias a valores literais:

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

**Propriedades Suportadas:**
`uri`: URI completo da propriedade
`type`: Sempre `"owl:DatatypeProperty"`
`rdfs:label`: Array de rótulos com marcação de idioma
`rdfs:comment`: Descrição da propriedade
`rdfs:domain`: Identificador da classe que possui esta propriedade
`rdfs:range`: Tipo de dados XSD para os valores da propriedade
`owl:functionalProperty`: Booleano indicando no máximo um valor
`owl:minCardinality`: Número mínimo de valores (opcional)
`owl:maxCardinality`: Número máximo de valores (opcional)
`owl:cardinality`: Número exato de valores (opcional)

### Tipos de Dados XSD Suportados

Os seguintes tipos de dados XML Schema são suportados para intervalos de propriedades:

`xsd:string` - Valores de texto
`xsd:integer` - Números inteiros
`xsd:nonNegativeInteger` - Inteiros não negativos
`xsd:float` - Números de ponto flutuante
`xsd:double` - Números de precisão dupla
`xsd:boolean` - Valores verdadeiro/falso
`xsd:dateTime` - Valores de data e hora
`xsd:date` - Valores de data
`xsd:anyURI` - Referências de URI

### Suporte a Idiomas

Rótulos e comentários suportam vários idiomas usando o formato de etiqueta de idioma W3C:

```json
{
  "rdfs:label": [
    {"value": "Animal", "lang": "en"},
    {"value": "Tier", "lang": "de"},
    {"value": "Animal", "lang": "es"}
  ]
}
```

## Exemplo de Ontologia

Aqui está um exemplo completo de uma ontologia simples:

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

## Regras de Validação

### Validação Estrutural

1. **Consistência de URIs**: Todos os URIs devem seguir o padrão `{namespace}#{identifier}`
2. **Hierarquia de Classes**: Não pode haver herança circular em `rdfs:subClassOf`
3. **Domínios/Intervalos de Propriedades**: Deve referenciar classes existentes ou tipos XSD válidos
4. **Classes Disjuntas**: Não podem ser subclasses umas das outras
5. **Propriedades Inversas**: Devem ser bidirecionais se especificadas

### Validação Semântica

1. **Identificadores Únicos**: Os identificadores de classe e propriedade devem ser únicos dentro de uma ontologia
2. **Etiquetas de Idioma**: Devem seguir o formato de etiqueta de idioma BCP 47
3. **Restrições de Cardinalidade**: `minCardinality` ≤ `maxCardinality` quando ambos são especificados
4. **Propriedades Funcionais**: Não podem ter `maxCardinality` > 1

## Suporte a Formatos de Importação/Exportação

Embora o formato interno seja JSON, o sistema suporta a conversão para/de formatos de ontologia padrão:

**Turtle (.ttl)** - Serialização RDF compacta
**RDF/XML (.rdf, .owl)** - Formato padrão W3C
**OWL/XML (.owx)** - Formato XML específico para OWL
**JSON-LD (.jsonld)** - JSON para Dados Vinculados

## Referências

[OWL 2 Web Ontology Language](https://www.w3.org/TR/owl2-overview/)
[RDF Schema 1.1](https://www.w3.org/TR/rdf-schema/)
[XML Schema Datatypes](https://www.w3.org/TR/xmlschema-2/)
[BCP 47 Language Tags](https://tools.ietf.org/html/bcp47)