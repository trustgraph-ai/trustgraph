---
layout: default
title: "Especificação Técnica de Dados Estruturados (Parte 2)"
parent: "Portuguese (Beta)"
---

# Especificação Técnica de Dados Estruturados (Parte 2)

> **Beta Translation:** This document was translated via Machine Learning and as such may not be 100% accurate. All non-English languages are currently classified as Beta.

## Visão Geral

Esta especificação aborda problemas e lacunas identificadas durante a implementação inicial da integração de dados estruturados do TrustGraph, conforme descrito em `structured-data.md`.

## Declarações do Problema

### 1. Inconsistência na Nomenclatura: "Objeto" vs "Linha"

A implementação atual usa a terminologia "objeto" em todo o código (por exemplo, `ExtractedObject`, extração de objetos, incorporações de objetos). Essa nomenclatura é muito genérica e causa confusão:

"Objeto" é um termo sobrecarregado em software (objetos Python, objetos JSON, etc.)
Os dados que estão sendo processados são fundamentalmente tabulares - linhas em tabelas com esquemas definidos
"Linha" descreve com mais precisão o modelo de dados e está alinhado com a terminologia de banco de dados

Essa inconsistência aparece em nomes de módulos, nomes de classes, tipos de mensagens e documentação.

### 2. Limitações de Consulta do Armazenamento de Linhas

A implementação atual do armazenamento de linhas tem limitações significativas de consulta:

**Incompatibilidade com a Linguagem Natural**: As consultas têm dificuldades com variações de dados do mundo real. Por exemplo:
É difícil encontrar uma base de dados de ruas contendo `"CHESTNUT ST"` quando se pergunta sobre `"Chestnut Street"`
Abreviaturas, diferenças de maiúsculas e minúsculas e variações de formatação interrompem as consultas de correspondência exata
Os usuários esperam compreensão semântica, mas o armazenamento fornece correspondência literal

**Problemas de Evolução do Esquema**: Alterar os esquemas causa problemas:
Os dados existentes podem não estar em conformidade com os esquemas atualizados
Alterações na estrutura da tabela podem quebrar consultas e a integridade dos dados
Não há um caminho de migração claro para atualizações de esquema

### 3. Incorporações de Linhas Necessárias

Relacionado ao problema 2, o sistema precisa de incorporações vetoriais para dados de linha para permitir:

Pesquisa semântica em dados estruturados (encontrando "Chestnut Street" quando os dados contêm "CHESTNUT ST")
Correspondência de similaridade para consultas aproximadas
Pesquisa híbrida combinando filtros estruturados com similaridade semântica
Melhor suporte para consultas em linguagem natural

O serviço de incorporação foi especificado, mas não implementado.

### 4. Ingestão de Dados de Linha Incompleta

O pipeline de ingestão de dados estruturados não está totalmente operacional:

Existem prompts de diagnóstico para classificar formatos de entrada (CSV, JSON, etc.)
O serviço de ingestão que usa esses prompts não está integrado ao sistema
Não há um caminho de ponta a ponta para carregar dados pré-estruturados no armazenamento de linhas

## Objetivos

**Flexibilidade de Esquema**: Permitir a evolução do esquema sem quebrar dados existentes ou exigir migrações
**Nomenclatura Consistente**: Padronizar na terminologia "linha" em todo o código
**Consultabilidade Semântica**: Suportar correspondência aproximada/semântica por meio de incorporações de linhas
**Pipeline de Ingestão Completo**: Fornecer um caminho de ponta a ponta para carregar dados estruturados

## Design Técnico

### Esquema de Armazenamento de Linhas Unificado

A implementação anterior criou uma tabela Cassandra separada para cada esquema. Isso causou problemas quando os esquemas evoluíram, pois as alterações na estrutura da tabela exigiram migrações.

O novo design usa uma única tabela unificada para todos os dados de linha:

```sql
CREATE TABLE rows (
    collection text,
    schema_name text,
    index_name text,
    index_value frozen<list<text>>,
    data map<text, text>,
    source text,
    PRIMARY KEY ((collection, schema_name, index_name), index_value)
)
```

#### Definições das Colunas

| Coluna | Tipo | Descrição |
|--------|------|-------------|
| `collection` | `text` | Identificador de coleta/importação de dados (a partir de metadados) |
| `schema_name` | `text` | Nome do esquema ao qual esta linha está em conformidade |
| `index_name` | `text` | Nome(s) do(s) campo(s) indexado(s), unidos por vírgula para compostos |
| `index_value` | `frozen<list<text>>` | Valor(es) do índice como uma lista |
| `data` | `map<text, text>` | Dados da linha como pares chave-valor |
| `source` | `text` | URI opcional que faz referência a informações de procedência no grafo de conhecimento. Uma string vazia ou NULL indica que não há fonte. |

#### Tratamento de Índices

Cada linha é armazenada várias vezes - uma vez por campo indexado definido no esquema. Os campos de chave primária são tratados como um índice sem um marcador especial, proporcionando flexibilidade futura.

**Exemplo de índice de campo único:**
O esquema define `email` como indexado
`index_name = "email"`
`index_value = ['foo@bar.com']`

**Exemplo de índice composto:**
O esquema define um índice composto em `region` e `status`
`index_name = "region,status"` (nomes dos campos ordenados e unidos por vírgula)
`index_value = ['US', 'active']` (valores na mesma ordem dos nomes dos campos)

**Exemplo de chave primária:**
O esquema define `customer_id` como chave primária
`index_name = "customer_id"`
`index_value = ['CUST001']`

#### Padrões de Consulta

Todas as consultas seguem o mesmo padrão, independentemente de qual índice é usado:

```sql
SELECT * FROM rows
WHERE collection = 'import_2024'
  AND schema_name = 'customers'
  AND index_name = 'email'
  AND index_value = ['foo@bar.com']
```

#### Compensações no Design

**Vantagens:**
Alterações no esquema não exigem alterações na estrutura da tabela
Os dados das linhas são opacos para o Cassandra - adições/remoções de campos são transparentes
Padrão de consulta consistente para todos os métodos de acesso
Sem índices secundários do Cassandra (que podem ser lentos em grande escala)
Tipos nativos do Cassandra em todo o sistema (`map`, `frozen<list>`)

**Compensações:**
Amplificação de escrita: cada inserção de linha = N inserções (uma por campo indexado)
Sobrecarga de armazenamento devido à duplicação de dados das linhas
Informações de tipo armazenadas na configuração do esquema, conversão na camada de aplicação

#### Modelo de Consistência

O design aceita certas simplificações:

1. **Sem atualizações de linha**: O sistema é somente de anexação. Isso elimina as preocupações com a consistência ao atualizar várias cópias da mesma linha.

2. **Tolerância a alterações de esquema**: Quando os esquemas são alterados (por exemplo, índices adicionados/removidos), as linhas existentes mantêm seu índice original. Linhas antigas não serão encontradas por meio de novos índices. Os usuários podem excluir e recriar um esquema para garantir a consistência, se necessário.

### Rastreamento e Exclusão de Partições

#### O Problema

Com a chave de partição `(collection, schema_name, index_name)`, a exclusão eficiente requer o conhecimento de todas as chaves de partição a serem excluídas. Excluir apenas por `collection` ou `collection + schema_name` requer o conhecimento de todos os valores de `index_name` que contêm dados.

#### Tabela de Rastreamento de Partições

Uma tabela de consulta secundária rastreia quais partições existem:

```sql
CREATE TABLE row_partitions (
    collection text,
    schema_name text,
    index_name text,
    PRIMARY KEY ((collection), schema_name, index_name)
)
```

Isso permite a descoberta eficiente de partições para operações de exclusão.

#### Comportamento do Escritor de Linhas

O escritor de linhas mantém um cache na memória de pares `(collection, schema_name)` registrados. Ao processar uma linha:

1. Verifique se `(collection, schema_name)` está no cache.
2. Se não estiver no cache (primeira linha para este par):
   Consulte a configuração do esquema para obter todos os nomes de índice.
   Insira entradas em `row_partitions` para cada `(collection, schema_name, index_name)`.
   Adicione o par ao cache.
3. Continue com a escrita dos dados da linha.

O escritor de linhas também monitora eventos de alteração da configuração do esquema. Quando um esquema é alterado, as entradas relevantes do cache são limpas para que a próxima linha acione o re-registro com os nomes de índice atualizados.

Essa abordagem garante:
As escritas na tabela de pesquisa ocorrem apenas uma vez por par `(collection, schema_name)`, e não por linha.
A tabela de pesquisa reflete os índices que estavam ativos quando os dados foram escritos.
As alterações no esquema durante a importação são detectadas corretamente.

#### Operações de Exclusão

**Excluir coleção:**
```sql
-- 1. Discover all partitions
SELECT schema_name, index_name FROM row_partitions WHERE collection = 'X';

-- 2. Delete each partition from rows table
DELETE FROM rows WHERE collection = 'X' AND schema_name = '...' AND index_name = '...';
-- (repeat for each discovered partition)

-- 3. Clean up the lookup table
DELETE FROM row_partitions WHERE collection = 'X';
```

**Excluir coleção + esquema:**
```sql
-- 1. Discover partitions for this schema
SELECT index_name FROM row_partitions WHERE collection = 'X' AND schema_name = 'Y';

-- 2. Delete each partition from rows table
DELETE FROM rows WHERE collection = 'X' AND schema_name = 'Y' AND index_name = '...';
-- (repeat for each discovered partition)

-- 3. Clean up the lookup table entries
DELETE FROM row_partitions WHERE collection = 'X' AND schema_name = 'Y';
```

### Incorporações de Linhas

As incorporações de linhas permitem a correspondência semântica/aproximada em valores indexados, resolvendo o problema de incompatibilidade de linguagem natural (por exemplo, encontrar "CHESTNUT ST" ao pesquisar por "Chestnut Street").

#### Visão Geral do Design

Cada valor indexado é incorporado e armazenado em um armazenamento vetorial (Qdrant). No momento da consulta, a consulta é incorporada, vetores semelhantes são encontrados e os metadados associados são usados para pesquisar as linhas reais no Cassandra.

#### Estrutura da Coleção Qdrant

Uma coleção Qdrant por tupla `(user, collection, schema_name, dimension)`:

**Nome da coleção:** `rows_{user}_{collection}_{schema_name}_{dimension}`
Os nomes são higienizados (caracteres não alfanuméricos substituídos por `_`, em letras minúsculas, os prefixos numéricos recebem o prefixo `r_`)
**Justificativa:** Permite a exclusão limpa de uma instância `(user, collection, schema_name)`, descartando as coleções Qdrant correspondentes; o sufixo de dimensão permite que diferentes modelos de incorporação coexistam.

#### O Que é Incorporado

A representação de texto dos valores do índice:

| Tipo de Índice | Exemplo `index_value` | Texto a Incorporar |
|------------|----------------------|---------------|
| Campo único | `['foo@bar.com']` | `"foo@bar.com"` |
| Composto | `['US', 'active']` | `"US active"` (juntados por espaço) |

#### Estrutura do Ponto

Cada ponto Qdrant contém:

```json
{
  "id": "<uuid>",
  "vector": [0.1, 0.2, ...],
  "payload": {
    "index_name": "street_name",
    "index_value": ["CHESTNUT ST"],
    "text": "CHESTNUT ST"
  }
}
```

| Campo de Payload | Descrição |
|---------------|-------------|
| `index_name` | Os campos indexados que esta incorporação representa |
| `index_value` | A lista original de valores (para pesquisa no Cassandra) |
| `text` | O texto que foi incorporado (para depuração/exibição) |

Nota: `user`, `collection` e `schema_name` são implícitos do nome da coleção Qdrant.

#### Fluxo de Consulta

1. O usuário consulta por "Chestnut Street" dentro do usuário U, coleção X, esquema Y
2. Incorpore o texto da consulta
3. Determine o(s) nome(s) da coleção Qdrant que correspondem ao prefixo `rows_U_X_Y_`
4. Pesquise na(s) coleção(ões) Qdrant correspondente(s) pelos vetores mais próximos
5. Obtenha os pontos correspondentes com payloads contendo `index_name` e `index_value`
6. Consulte o Cassandra:
   ```sql
   SELECT * FROM rows
   WHERE collection = 'X'
     AND schema_name = 'Y'
     AND index_name = '<from payload>'
     AND index_value = <from payload>
   ```
7. Retornar linhas correspondentes

#### Opcional: Filtragem por Nome do Índice

As consultas podem opcionalmente filtrar por `index_name` no Qdrant para pesquisar apenas campos específicos:

**"Encontrar qualquer campo que corresponda a 'Chestnut'"** → pesquisa todos os vetores na coleção
**"Encontrar street_name que corresponda a 'Chestnut'"** → filtrar onde `payload.index_name = 'street_name'`

#### Arquitetura

Os embeddings das linhas seguem o **padrão de duas etapas** usado pelo GraphRAG (embeddings do grafo, embeddings do documento):

**Etapa 1: Computação de embeddings** (`trustgraph-flow/trustgraph/embeddings/row_embeddings/`) - Consome `ExtractedObject`, calcula embeddings através do serviço de embeddings, gera `RowEmbeddings`
**Etapa 2: Armazenamento de embeddings** (`trustgraph-flow/trustgraph/storage/row_embeddings/qdrant/`) - Consome `RowEmbeddings`, escreve vetores no Qdrant

O escritor de linhas do Cassandra é um consumidor paralelo separado:

**Escritor de linhas do Cassandra** (`trustgraph-flow/trustgraph/storage/rows/cassandra`) - Consome `ExtractedObject`, escreve linhas no Cassandra

Todos os três serviços consomem do mesmo fluxo, mantendo-os desacoplados. Isso permite:
Escalonamento independente das escritas do Cassandra em relação à geração de embeddings em relação ao armazenamento de vetores
Os serviços de embeddings podem ser desativados se não forem necessários
Falhas em um serviço não afetam os outros
Arquitetura consistente com os pipelines do GraphRAG

#### Caminho de Escrita

**Etapa 1 (processador de embeddings das linhas):** Ao receber um `ExtractedObject`:

1. Consultar o esquema para encontrar campos indexados
2. Para cada campo indexado:
   Construir a representação de texto do valor do índice
   Calcular o embedding através do serviço de embeddings
3. Gerar uma mensagem `RowEmbeddings` contendo todos os vetores calculados

**Etapa 2 (escritor de embeddings-Qdrant):** Ao receber um `RowEmbeddings`:

1. Para cada embedding na mensagem:
   Determinar a coleção do Qdrant a partir de `(user, collection, schema_name, dimension)`
   Criar a coleção, se necessário (criação preguiçosa na primeira escrita)
   Inserir/atualizar o ponto com o vetor e o payload

#### Tipos de Mensagens

```python
@dataclass
class RowIndexEmbedding:
    index_name: str              # The indexed field name(s)
    index_value: list[str]       # The field value(s)
    text: str                    # Text that was embedded
    vectors: list[list[float]]   # Computed embedding vectors

@dataclass
class RowEmbeddings:
    metadata: Metadata
    schema_name: str
    embeddings: list[RowIndexEmbedding]
```

#### Integração de Exclusão

As coleções Qdrant são descobertas por correspondência de prefixo no padrão de nome da coleção:

**Excluir `(user, collection)`:**
1. Listar todas as coleções Qdrant que correspondem ao prefixo `rows_{user}_{collection}_`
2. Excluir cada coleção correspondente
3. Excluir partições de linhas do Cassandra (como documentado acima)
4. Limpar as entradas `row_partitions`

**Excluir `(user, collection, schema_name)`:**
1. Listar todas as coleções Qdrant que correspondem ao prefixo `rows_{user}_{collection}_{schema_name}_`
2. Excluir cada coleção correspondente (lida com múltiplas dimensões)
3. Excluir partições de linhas do Cassandra
4. Limpar `row_partitions`

#### Localizações dos Módulos

| Estágio | Módulo | Ponto de Entrada |
|-------|--------|-------------|
| Estágio 1 | `trustgraph-flow/trustgraph/embeddings/row_embeddings/` | `row-embeddings` |
| Estágio 2 | `trustgraph-flow/trustgraph/storage/row_embeddings/qdrant/` | `row-embeddings-write-qdrant` |

### API de Consulta de Incorporações de Linhas

A consulta de incorporações de linhas é uma **API separada** do serviço de consulta de linhas GraphQL:

| API | Propósito | Backend |
|-----|---------|---------|
| Consulta de Linhas (GraphQL) | Correspondência exata em campos indexados | Cassandra |
| Consulta de Incorporações de Linhas | Correspondência aproximada/semântica | Qdrant |

Essa separação mantém as responsabilidades bem definidas:
O serviço GraphQL se concentra em consultas estruturadas e exatas
A API de incorporações lida com a similaridade semântica
Fluxo de trabalho do usuário: pesquisa aproximada por meio de incorporações para encontrar candidatos e, em seguida, consulta exata para obter os dados completos da linha

#### Esquema de Solicitação/Resposta

```python
@dataclass
class RowEmbeddingsRequest:
    vectors: list[list[float]]    # Query vectors (pre-computed embeddings)
    user: str = ""
    collection: str = ""
    schema_name: str = ""
    index_name: str = ""          # Optional: filter to specific index
    limit: int = 10               # Max results per vector

@dataclass
class RowIndexMatch:
    index_name: str = ""          # The matched index field(s)
    index_value: list[str] = []   # The matched value(s)
    text: str = ""                # Original text that was embedded
    score: float = 0.0            # Similarity score

@dataclass
class RowEmbeddingsResponse:
    error: Error | None = None
    matches: list[RowIndexMatch] = []
```

#### Processador de Consultas

Módulo: `trustgraph-flow/trustgraph/query/row_embeddings/qdrant`

Ponto de entrada: `row-embeddings-query-qdrant`

O processador:
1. Recebe `RowEmbeddingsRequest` com vetores de consulta
2. Encontra a coleção Qdrant apropriada por correspondência de prefixo
3. Procura os vetores mais próximos com filtro opcional `index_name`
4. Retorna `RowEmbeddingsResponse` com informações do índice correspondente

#### Integração com o Gateway de API

O gateway expõe consultas de incorporações de linhas através do padrão padrão de solicitação/resposta:

| Componente | Localização |
|-----------|----------|
| Dispatcher | `trustgraph-flow/trustgraph/gateway/dispatch/row_embeddings_query.py` |
| Registro | Adicione `"row-embeddings"` a `request_response_dispatchers` em `manager.py` |

Nome da interface do fluxo: `row-embeddings`

Definição da interface no blueprint do fluxo:
```json
{
  "interfaces": {
    "row-embeddings": {
      "request": "non-persistent://tg/request/row-embeddings:{id}",
      "response": "non-persistent://tg/response/row-embeddings:{id}"
    }
  }
}
```

#### Suporte ao SDK Python

O SDK fornece métodos para consultas de incorporações de linhas:

```python
# Flow-scoped query (preferred)
api = Api(url)
flow = api.flow().id("default")

# Query with text (SDK computes embeddings)
matches = flow.row_embeddings_query(
    text="Chestnut Street",
    collection="my_collection",
    schema_name="addresses",
    index_name="street_name",  # Optional filter
    limit=10
)

# Query with pre-computed vectors
matches = flow.row_embeddings_query(
    vectors=[[0.1, 0.2, ...]],
    collection="my_collection",
    schema_name="addresses"
)

# Each match contains:
for match in matches:
    print(match.index_name)   # e.g., "street_name"
    print(match.index_value)  # e.g., ["CHESTNUT ST"]
    print(match.text)         # e.g., "CHESTNUT ST"
    print(match.score)        # e.g., 0.95
```

#### Utilitário de Linha de Comando (CLI)

Comando: `tg-invoke-row-embeddings`

```bash
# Query by text (computes embedding automatically)
tg-invoke-row-embeddings \
  --text "Chestnut Street" \
  --collection my_collection \
  --schema addresses \
  --index street_name \
  --limit 10

# Query by vector file
tg-invoke-row-embeddings \
  --vectors vectors.json \
  --collection my_collection \
  --schema addresses

# Output formats
tg-invoke-row-embeddings --text "..." --format json
tg-invoke-row-embeddings --text "..." --format table
```

#### Padrão de Uso Típico

A consulta de incorporações de linhas é normalmente usada como parte de um fluxo de pesquisa aproximada para correspondência exata:

```python
# Step 1: Fuzzy search via embeddings
matches = flow.row_embeddings_query(
    text="chestnut street",
    collection="geo",
    schema_name="streets"
)

# Step 2: Exact lookup via GraphQL for full row data
for match in matches:
    query = f'''
    query {{
        streets(where: {{ {match.index_name}: {{ eq: "{match.index_value[0]}" }} }}) {{
            street_name
            city
            zip_code
        }}
    }}
    '''
    rows = flow.rows_query(query, collection="geo")
```

Este padrão de duas etapas permite:
Encontrar "CHESTNUT ST" quando o usuário pesquisa por "Chestnut Street"
Recuperar dados completos da linha com todos os campos
Combinar similaridade semântica com acesso a dados estruturados

### Ingestão de Dados da Linha

Será adiada para uma fase posterior. Será projetada juntamente com outras alterações de ingestão.

## Impacto na Implementação

### Análise do Estado Atual

A implementação existente possui dois componentes principais:

| Componente | Localização | Linhas | Descrição |
|-----------|----------|-------|-------------|
| Serviço de Consulta | `trustgraph-flow/trustgraph/query/objects/cassandra/service.py` | ~740 | Monolítico: geração de esquema GraphQL, análise de filtros, consultas Cassandra, tratamento de solicitações |
| Escritor | `trustgraph-flow/trustgraph/storage/objects/cassandra/write.py` | ~540 | Criação de tabelas por esquema, índices secundários, inserção/exclusão |

**Padrão de Consulta Atual:**
```sql
SELECT * FROM {keyspace}.o_{schema_name}
WHERE collection = 'X' AND email = 'foo@bar.com'
ALLOW FILTERING
```

**Novo Padrão de Consulta:**
```sql
SELECT * FROM {keyspace}.rows
WHERE collection = 'X' AND schema_name = 'customers'
  AND index_name = 'email' AND index_value = ['foo@bar.com']
```

### Mudanças Principais

1. **A semântica das consultas é simplificada**: O novo esquema suporta apenas correspondências exatas em `index_value`. Os filtros GraphQL atuais (`gt`, `lt`, `contains`, etc.) ou:
   Tornam-se pós-filtragem nos dados retornados (se ainda forem necessários)
   São removidos em favor do uso da API de embeddings para correspondências aproximadas

2. **O código GraphQL está fortemente acoplado**: O código `service.py` atual combina a geração de tipos Strawberry, a análise de filtros e as consultas específicas do Cassandra. Adicionar outro backend de armazenamento de linhas duplicaria cerca de 400 linhas de código GraphQL.

### Refatoração Proposta

A refatoração tem duas partes:

#### 1. Separar o Código GraphQL

Extrair componentes GraphQL reutilizáveis para um módulo compartilhado:

```
trustgraph-flow/trustgraph/query/graphql/
├── __init__.py
├── types.py        # Filter types (IntFilter, StringFilter, FloatFilter)
├── schema.py       # Dynamic schema generation from RowSchema
└── filters.py      # Filter parsing utilities
```

Isso permite:
Reutilização em diferentes backends de armazenamento de dados.
Separação mais clara de responsabilidades.
Teste mais fácil da lógica GraphQL de forma independente.

#### 2. Implementar Novo Esquema de Tabela

Refatorar o código específico do Cassandra para usar a tabela unificada:

**Escritor** (`trustgraph-flow/trustgraph/storage/rows/cassandra/`):
Uma única tabela `rows` em vez de tabelas por esquema.
Escrever N cópias por linha (uma por índice).
Registrar na tabela `row_partitions`.
Criação de tabela mais simples (configuração única).

**Serviço de Consulta** (`trustgraph-flow/trustgraph/query/rows/cassandra/`):
Consultar a tabela `rows` unificada.
Usar o módulo GraphQL extraído para geração de esquema.
Tratamento de filtros simplificado (apenas correspondência exata no nível do banco de dados).

### Renomeação de Módulos

Como parte da limpeza de nomes de "objeto" para "linha":

| Atual | Novo |
|---------|-----|
| `storage/objects/cassandra/` | `storage/rows/cassandra/` |
| `query/objects/cassandra/` | `query/rows/cassandra/` |
| `embeddings/object_embeddings/` | `embeddings/row_embeddings/` |

### Novos Módulos

| Módulo | Propósito |
|--------|---------|
| `trustgraph-flow/trustgraph/query/graphql/` | Utilitários GraphQL compartilhados |
| `trustgraph-flow/trustgraph/query/row_embeddings/qdrant/` | API de consulta de incorporações de linhas |
| `trustgraph-flow/trustgraph/embeddings/row_embeddings/` | Cálculo de incorporações de linhas (Etapa 1) |
| `trustgraph-flow/trustgraph/storage/row_embeddings/qdrant/` | Armazenamento de incorporações de linhas (Etapa 2) |

## Referências

[Especificação Técnica de Dados Estruturados](structured-data.md)
