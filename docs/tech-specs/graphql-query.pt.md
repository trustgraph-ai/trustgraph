# Especificação Técnica da Consulta GraphQL

## Visão Geral

Esta especificação descreve a implementação de uma interface de consulta GraphQL para o armazenamento de dados estruturados do TrustGraph no Apache Cassandra. Baseando-se nas capacidades de dados estruturados descritas na especificação structured-data.md, este documento detalha como as consultas GraphQL serão executadas contra tabelas do Cassandra contendo objetos estruturados extraídos e ingeridos.

O serviço de consulta GraphQL fornecerá uma interface flexível e segura para consultar dados estruturados armazenados no Cassandra. Ele se adaptará dinamicamente às alterações de esquema, suportará consultas complexas, incluindo relacionamentos entre objetos, e se integrará perfeitamente à arquitetura existente baseada em mensagens do TrustGraph.

## Objetivos

**Suporte Dinâmico de Esquema**: Adaptar-se automaticamente às alterações de esquema na configuração sem reinicializações do serviço.
**Conformidade com os Padrões GraphQL**: Fornecer uma interface GraphQL padrão compatível com as ferramentas e clientes GraphQL existentes.
**Consultas Eficientes do Cassandra**: Traduzir consultas GraphQL em consultas CQL eficientes do Cassandra, respeitando as chaves de partição e os índices.
**Resolução de Relacionamentos**: Suportar resolvedores de campos GraphQL para relacionamentos entre diferentes tipos de objetos.
**Segurança de Tipo**: Garantir a execução de consultas e a geração de respostas com segurança de tipo, com base nas definições do esquema.
**Desempenho Escalável**: Lidar com consultas concorrentes de forma eficiente, com um pool de conexões adequado e otimização de consultas.
**Integração de Solicitação/Resposta**: Manter a compatibilidade com o padrão de solicitação/resposta baseado no Pulsar do TrustGraph.
**Tratamento de Erros**: Fornecer relatórios de erros abrangentes para incompatibilidades de esquema, erros de consulta e problemas de validação de dados.

## Contexto

A implementação do armazenamento de dados estruturados (trustgraph-flow/trustgraph/storage/objects/cassandra/) grava objetos em tabelas do Cassandra com base em definições de esquema armazenadas no sistema de configuração do TrustGraph. Essas tabelas usam uma estrutura de chave de partição composta com chaves primárias definidas por coleção e esquema, permitindo consultas eficientes dentro das coleções.

Limitações atuais que esta especificação aborda:
Não há interface de consulta para os dados estruturados armazenados no Cassandra.
Impossibilidade de aproveitar os poderosos recursos de consulta do GraphQL para dados estruturados.
Falta de suporte para a travessia de relacionamentos entre objetos relacionados.
Falta de uma linguagem de consulta padronizada para acesso a dados estruturados.

O serviço de consulta GraphQL preencherá essas lacunas fornecendo:
Uma interface GraphQL padrão para consultar tabelas do Cassandra.
Geração dinâmica de esquemas GraphQL a partir da configuração do TrustGraph.
Tradução eficiente de consultas GraphQL para CQL do Cassandra.
Suporte para resolução de relacionamentos por meio de resolvedores de campos.

## Design Técnico

### Arquitetura

O serviço de consulta GraphQL será implementado como um novo processador de fluxo do TrustGraph, seguindo padrões estabelecidos:

**Localização do Módulo**: `trustgraph-flow/trustgraph/query/objects/cassandra/`

**Componentes Principais**:

1. **Processador do Serviço de Consulta GraphQL**
   Estende a classe base FlowProcessor.
   Implementa um padrão de solicitação/resposta semelhante aos serviços de consulta existentes.
   Monitora a configuração para atualizações de esquema.
   Mantém o esquema GraphQL sincronizado com a configuração.

2. **Gerador de Esquema Dinâmico**
   Converte definições de RowSchema do TrustGraph em tipos GraphQL.
   Cria tipos de objetos GraphQL com definições de campo adequadas.
   Gera o tipo de consulta raiz com resolvedores baseados em coleções.
   Atualiza o esquema GraphQL quando a configuração é alterada.

3. **Executor de Consulta**
   Analisa consultas GraphQL recebidas usando a biblioteca Strawberry.
   Valida as consultas em relação ao esquema atual.
   Executa as consultas e retorna respostas estruturadas.
   Lida com erros de forma elegante com mensagens de erro detalhadas.

4. **Tradutor de Consulta do Cassandra**
   Converte seleções GraphQL em consultas CQL.
   Otimiza as consultas com base nos índices e chaves de partição disponíveis.
   Lida com filtragem, paginação e classificação.
   Gerencia o pool de conexões e o ciclo de vida da sessão.

5. **Resolvedor de Relacionamentos**
   Implementa resolvedores de campos para relacionamentos entre objetos.
   Realiza carregamento em lote eficiente para evitar consultas N+1.
   Armazena em cache os relacionamentos resolvidos dentro do contexto da solicitação.
   Suporta a travessia de relacionamentos tanto para frente quanto para trás.

### Monitoramento do Esquema de Configuração

O serviço registrará um manipulador de configuração para receber atualizações de esquema:

```python
self.register_config_handler(self.on_schema_config)
```

Quando os esquemas mudam:
1. Analisar as novas definições de esquema a partir da configuração
2. Regenerar os tipos e resolvedores GraphQL
3. Atualizar o esquema executável
4. Limpar quaisquer caches dependentes do esquema

### Geração de Esquema GraphQL

Para cada RowSchema na configuração, gerar:

1. **Tipo de Objeto GraphQL**:
   Mapear tipos de campo (string → String, integer → Int, float → Float, boolean → Boolean)
   Marcar campos obrigatórios como não nulos no GraphQL
   Adicionar descrições de campo do esquema

2. **Campos de Consulta Raiz**:
   Consulta de coleção (por exemplo, `customers`, `transactions`)
   Argumentos de filtragem com base em campos indexados
   Suporte de paginação (limite, deslocamento)
   Opções de ordenação para campos classificáveis

3. **Campos de Relacionamento**:
   Identificar relacionamentos de chave estrangeira do esquema
   Criar resolvedores de campo para objetos relacionados
   Suportar relacionamentos de objeto único e de lista

### Fluxo de Execução da Consulta

1. **Recepção da Requisição**:
   Receber ObjectsQueryRequest do Pulsar
   Extrair a string de consulta GraphQL e as variáveis
   Identificar o contexto de usuário e coleção

2. **Validação da Consulta**:
   Analisar a consulta GraphQL usando Strawberry
   Validar em relação ao esquema atual
   Verificar as seleções de campo e os tipos de argumento

3. **Geração de CQL**:
   Analisar as seleções GraphQL
   Construir a consulta CQL com as cláusulas WHERE apropriadas
   Incluir a coleção na chave de partição
   Aplicar filtros com base nos argumentos GraphQL

4. **Execução da Consulta**:
   Executar a consulta CQL contra o Cassandra
   Mapear os resultados para a estrutura de resposta GraphQL
   Resolver quaisquer campos de relacionamento
   Formatar a resposta de acordo com a especificação GraphQL

5. **Entrega da Resposta**:
   Criar uma ObjectsQueryResponse com os resultados
   Incluir quaisquer erros de execução
   Enviar a resposta via Pulsar com o ID de correlação

### Modelos de Dados

> **Nota**: Um esquema StructuredQueryRequest/Response existente existe em `trustgraph-base/trustgraph/schema/services/structured_query.py`. No entanto, ele carece de campos críticos (usuário, coleção) e usa tipos subótimos. Os esquemas abaixo representam a evolução recomendada, que deve substituir os esquemas existentes ou ser criada como novos tipos ObjectsQueryRequest/Response.

#### Esquema de Requisição (ObjectsQueryRequest)

```python
from pulsar.schema import Record, String, Map, Array

class ObjectsQueryRequest(Record):
    user = String()              # Cassandra keyspace (follows pattern from TriplesQueryRequest)
    collection = String()        # Data collection identifier (required for partition key)
    query = String()             # GraphQL query string
    variables = Map(String())    # GraphQL variables (consider enhancing to support all JSON types)
    operation_name = String()    # Operation to execute for multi-operation documents
```

**Justificativa para as alterações em relação ao StructuredQueryRequest existente:**
Adicionados os campos `user` e `collection` para corresponder ao padrão de outros serviços de consulta.
Esses campos são essenciais para identificar o keyspace e a coleção do Cassandra.
As variáveis permanecem como Map(String()) por enquanto, mas idealmente deveriam suportar todos os tipos JSON.

#### Esquema de Resposta (ObjectsQueryResponse)

```python
from pulsar.schema import Record, String, Array
from ..core.primitives import Error

class GraphQLError(Record):
    message = String()
    path = Array(String())       # Path to the field that caused the error
    extensions = Map(String())   # Additional error metadata

class ObjectsQueryResponse(Record):
    error = Error()              # System-level error (connection, timeout, etc.)
    data = String()              # JSON-encoded GraphQL response data
    errors = Array(GraphQLError) # GraphQL field-level errors
    extensions = Map(String())   # Query metadata (execution time, etc.)
```

**Justificativa para as alterações em relação à StructuredQueryResponse existente:**
Distingue entre erros do sistema (`error`) e erros do GraphQL (`errors`)
Utiliza objetos GraphQLError estruturados em vez de um array de strings
Adiciona o campo `extensions` para conformidade com a especificação do GraphQL
Mantém os dados como uma string JSON para compatibilidade, embora os tipos nativos seriam preferíveis

### Otimização de Consultas Cassandra

O serviço otimizará as consultas do Cassandra, através de:

1. **Respeitando as Chaves de Partição:**
   Inclua sempre a coleção nas consultas
   Utilize as chaves primárias definidas no esquema de forma eficiente
   Evite varreduras completas da tabela

2. **Aproveitando os Índices:**
   Utilize índices secundários para filtragem
   Combine vários filtros sempre que possível
   Avise quando as consultas podem ser ineficientes

3. **Carregamento em Lote:**
   Colete consultas de relacionamento
   Execute em lotes para reduzir o número de viagens de ida e volta
   Armazene em cache os resultados dentro do contexto da requisição

4. **Gerenciamento de Conexões:**
   Mantenha sessões persistentes do Cassandra
   Utilize um pool de conexões
   Lide com a reconexão em caso de falhas

### Exemplos de Consultas GraphQL

#### Consulta Simples de Coleção
```graphql
{
  customers(status: "active") {
    customer_id
    name
    email
    registration_date
  }
}
```

#### Consulta com Relacionamentos
```graphql
{
  orders(order_date_gt: "2024-01-01") {
    order_id
    total_amount
    customer {
      name
      email
    }
    items {
      product_name
      quantity
      price
    }
  }
}
```

#### Consulta Paginação
```graphql
{
  products(limit: 20, offset: 40) {
    product_id
    name
    price
    category
  }
}
```

### Dependências de Implementação

**Strawberry GraphQL**: Para definição de esquema GraphQL e execução de consultas.
**Cassandra Driver**: Para conectividade com o banco de dados (já utilizado no módulo de armazenamento).
**TrustGraph Base**: Para FlowProcessor e definições de esquema.
**Configuration System**: Para monitoramento e atualizações de esquema.

### Interface de Linha de Comando

O serviço fornecerá um comando de CLI: `kg-query-objects-graphql-cassandra`

Argumentos:
`--cassandra-host`: Ponto de contato do cluster Cassandra.
`--cassandra-username`: Nome de usuário de autenticação.
`--cassandra-password`: Senha de autenticação.
`--config-type`: Tipo de configuração para esquemas (padrão: "schema").
Argumentos padrão do FlowProcessor (configuração do Pulsar, etc.).

## Integração de API

### Tópicos Pulsar

**Tópico de Entrada**: `objects-graphql-query-request`
Esquema: ObjectsQueryRequest
Recebe consultas GraphQL de serviços de gateway.

**Tópico de Saída**: `objects-graphql-query-response`
Esquema: ObjectsQueryResponse
Retorna resultados de consulta e erros.

### Integração de Gateway

O gateway e o gateway reverso precisarão de endpoints para:
1. Aceitar consultas GraphQL de clientes.
2. Encaminhar para o serviço de consulta via Pulsar.
3. Retornar respostas aos clientes.
4. Suportar consultas de introspecção GraphQL.

### Integração da Ferramenta de Agente

Uma nova classe de ferramenta de agente permitirá:
Geração de consultas GraphQL a partir de linguagem natural.
Execução direta de consultas GraphQL.
Interpretação e formatação de resultados.
Integração com fluxos de decisão do agente.

## Considerações de Segurança

**Limitação de Profundidade da Consulta**: Prevenir consultas profundamente aninhadas que possam causar problemas de desempenho.
**Análise de Complexidade da Consulta**: Limitar a complexidade da consulta para evitar o esgotamento de recursos.
**Permissões de Nível de Campo**: Suporte futuro para controle de acesso baseado em funções de usuário.
**Sanitização de Entrada**: Validar e sanitizar todas as entradas de consulta para prevenir ataques de injeção.
**Limitação de Taxa**: Implementar a limitação de taxa de consulta por usuário/coleção.

## Considerações de Desempenho

**Planejamento de Consulta**: Analisar consultas antes da execução para otimizar a geração de CQL.
**Cache de Resultados**: Considerar o cache de dados acessados com frequência no nível do resolvedor de campo.
**Pool de Conexões**: Manter pools de conexão eficientes para o Cassandra.
**Operações em Lote**: Combinar várias consultas sempre que possível para reduzir a latência.
**Monitoramento**: Rastrear métricas de desempenho da consulta para otimização.

## Estratégia de Teste

### Testes Unitários
Geração de esquema a partir de definições de RowSchema.
Análise e validação de consultas GraphQL.
Lógica de geração de consultas CQL.
Implementações de resolvedores de campo.

### Testes de Contrato
Conformidade do contrato de mensagem Pulsar.
Validade do esquema GraphQL.
Verificação do formato da resposta.
Validação da estrutura de erro.

### Testes de Integração
Execução de consulta de ponta a ponta contra uma instância de teste do Cassandra.
Tratamento de atualização de esquema.
Resolução de relacionamento.
Paginação e filtragem.
Cenários de erro.

### Testes de Desempenho
Taxa de transferência de consultas sob carga.
Tempo de resposta para várias complexidades de consulta.
Uso de memória com grandes conjuntos de resultados.
Eficiência do pool de conexões.

## Plano de Migração

Não é necessária migração, pois esta é uma nova funcionalidade. O serviço irá:
1. Ler esquemas existentes da configuração.
2. Conectar-se às tabelas Cassandra existentes criadas pelo módulo de armazenamento.
3. Começar a aceitar consultas imediatamente após a implantação.

## Perguntas Abertas

1. **Evolução do Esquema**: Como o serviço deve lidar com consultas durante as transições de esquema?
Opção: Enfileirar consultas durante as atualizações de esquema.
Opção: Suportar várias versões de esquema simultaneamente.

2. **Estratégia de Cache**: Os resultados da consulta devem ser armazenados em cache?
Considerar: Expiração baseada em tempo.
Considerar: Invalidação baseada em eventos.

3. **Suporte à Federação**: O serviço deve suportar a federação GraphQL para combinar com outras fontes de dados?
   Permitiria consultas unificadas em dados estruturados e de grafo.
   
4. **Suporte a Assinaturas**: O serviço deve suportar assinaturas GraphQL para atualizações em tempo real?
Requereria suporte WebSocket no gateway.
   
   5. **Escalares Personalizados**: O serviço deve suportar tipos escalares personalizados para tipos de dados específicos do domínio?
Exemplos: DateTime, UUID, campos JSON.

   ## Referências

Especificação de Dados Estruturados: ⟦CODE_0⟧
   Documentação do Strawberry GraphQL: ⟦URL_0⟧
Especificação GraphQL: ⟦URL_0⟧
Referência CQL do Apache Cassandra: ⟦URL_0⟧
   Documentação do Flow Processor TrustGraph: Documentação interna.

## Referências

Especificação Técnica de Dados Estruturados: `docs/tech-specs/structured-data.md`
Documentação do Strawberry GraphQL: https://strawberry.rocks/
Especificação do GraphQL: https://spec.graphql.org/
Referência CQL do Apache Cassandra: https://cassandra.apache.org/doc/stable/cassandra/cql/
Documentação do Processador de Fluxo TrustGraph: Documentação interna