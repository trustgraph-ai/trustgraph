---
layout: default
title: "Alterações no Esquema Pulsar para Dados Estruturados"
parent: "Portuguese (Beta)"
---

# Alterações no Esquema Pulsar para Dados Estruturados

> **Beta Translation:** This document was translated via Machine Learning and as such may not be 100% accurate. All non-English languages are currently classified as Beta.

## Visão Geral

Com base na especificação STRUCTURED_DATA.md, este documento propõe as adições e modificações necessárias no esquema Pulsar para suportar as capacidades de dados estruturados no TrustGraph.

## Alterações Necessárias no Esquema

### 1. Melhorias no Esquema Principal

#### Definição de Campo Aprimorada
A classe `Field` existente em `core/primitives.py` precisa de propriedades adicionais:

```python
class Field(Record):
    name = String()
    type = String()  # int, string, long, bool, float, double, timestamp
    size = Integer()
    primary = Boolean()
    description = String()
    # NEW FIELDS:
    required = Boolean()  # Whether field is required
    enum_values = Array(String())  # For enum type fields
    indexed = Boolean()  # Whether field should be indexed
```

### 2. Novos Esquemas de Conhecimento

#### 2.1 Submissão de Dados Estruturados
Novo arquivo: `knowledge/structured.py`

```python
from pulsar.schema import Record, String, Bytes, Map
from ..core.metadata import Metadata

class StructuredDataSubmission(Record):
    metadata = Metadata()
    format = String()  # "json", "csv", "xml"
    schema_name = String()  # Reference to schema in config
    data = Bytes()  # Raw data to ingest
    options = Map(String())  # Format-specific options
```

### 3. Novos Esquemas de Serviço

#### 3.1 Serviço de Consulta Estruturada a partir de Processamento de Linguagem Natural
Novo arquivo: `services/nlp_query.py`

```python
from pulsar.schema import Record, String, Array, Map, Integer, Double
from ..core.primitives import Error

class NLPToStructuredQueryRequest(Record):
    natural_language_query = String()
    max_results = Integer()
    context_hints = Map(String())  # Optional context for query generation

class NLPToStructuredQueryResponse(Record):
    error = Error()
    graphql_query = String()  # Generated GraphQL query
    variables = Map(String())  # GraphQL variables if any
    detected_schemas = Array(String())  # Which schemas the query targets
    confidence = Double()
```

#### 3.2 Serviço de Consulta Estruturada
Novo arquivo: `services/structured_query.py`

```python
from pulsar.schema import Record, String, Map, Array
from ..core.primitives import Error

class StructuredQueryRequest(Record):
    query = String()  # GraphQL query
    variables = Map(String())  # GraphQL variables
    operation_name = String()  # Optional operation name for multi-operation documents

class StructuredQueryResponse(Record):
    error = Error()
    data = String()  # JSON-encoded GraphQL response data
    errors = Array(String())  # GraphQL errors if any
```

#### 2.2 Saída da Extração de Objetos
Novo arquivo: `knowledge/object.py`

```python
from pulsar.schema import Record, String, Map, Double
from ..core.metadata import Metadata

class ExtractedObject(Record):
    metadata = Metadata()
    schema_name = String()  # Which schema this object belongs to
    values = Map(String())  # Field name -> value
    confidence = Double()
    source_span = String()  # Text span where object was found
```

### 4. Esquemas de Conhecimento Aprimorados

#### 4.1 Aprimoramento de Incorporações de Objetos
Atualizar `knowledge/embeddings.py` para oferecer melhor suporte a incorporações de objetos estruturadas:

```python
class StructuredObjectEmbedding(Record):
    metadata = Metadata()
    vectors = Array(Array(Double()))
    schema_name = String()
    object_id = String()  # Primary key value
    field_embeddings = Map(Array(Double()))  # Per-field embeddings
```

## Pontos de Integração

### Integração de Fluxo

Os esquemas serão usados por novos módulos de fluxo:
`trustgraph-flow/trustgraph/decoding/structured` - Usa StructuredDataSubmission
`trustgraph-flow/trustgraph/query/nlp_query/cassandra` - Usa esquemas de consulta NLP
`trustgraph-flow/trustgraph/query/objects/cassandra` - Usa esquemas de consulta estruturados
`trustgraph-flow/trustgraph/extract/object/row/` - Consome Chunk, produz ExtractedObject
`trustgraph-flow/trustgraph/storage/objects/cassandra` - Usa o esquema Rows
`trustgraph-flow/trustgraph/embeddings/object_embeddings/qdrant` - Usa esquemas de incorporação de objetos

## Notas de Implementação

1. **Versionamento de Esquemas**: Considere adicionar um campo `version` em RowSchema para suporte futuro de migração.
2. **Sistema de Tipos**: O `Field.type` deve suportar todos os tipos nativos do Cassandra.
3. **Operações em Lote**: A maioria dos serviços deve suportar operações individuais e em lote.
4. **Tratamento de Erros**: Relatório de erros consistente em todos os novos serviços.
5. **Compatibilidade com Versões Anteriores**: Os esquemas existentes permanecem inalterados, exceto por pequenos aprimoramentos de campos.

## Próximos Passos

1. Implementar os arquivos de esquema na nova estrutura.
2. Atualizar os serviços existentes para reconhecer os novos tipos de esquema.
3. Implementar módulos de fluxo que usem esses esquemas.
4. Adicionar endpoints de gateway/rev-gateway para novos serviços.
5. Criar testes unitários para validação de esquema.
