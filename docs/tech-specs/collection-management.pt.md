# Especificação Técnica de Gerenciamento de Coleções

## Visão Geral

Esta especificação descreve as capacidades de gerenciamento de coleções para o TrustGraph, exigindo a criação explícita de coleções e fornecendo controle direto sobre o ciclo de vida da coleção. As coleções devem ser criadas explicitamente antes de serem usadas, garantindo a sincronização adequada entre os metadados do bibliotecário e todos os backends de armazenamento. O recurso suporta quatro casos de uso primários:

1. **Criação de Coleção**: Crie explicitamente coleções antes de armazenar dados
2. **Listagem de Coleções**: Visualize todas as coleções existentes no sistema
3. **Gerenciamento de Metadados da Coleção**: Atualize nomes, descrições e tags de coleções
4. **Exclusão de Coleções**: Remova coleções e seus dados associados em todos os tipos de armazenamento

## Objetivos

**Criação Explícita de Coleção**: Exigir que as coleções sejam criadas antes que os dados possam ser armazenados
**Sincronização de Armazenamento**: Garantir que as coleções existam em todos os backends de armazenamento (vetores, objetos, triplas)
**Visibilidade da Coleção**: Permitir que os usuários listem e inspecionem todas as coleções em seu ambiente
**Limpeza de Coleções**: Permitir a exclusão de coleções que não são mais necessárias
**Organização de Coleções**: Suportar rótulos e tags para melhor rastreamento e descoberta de coleções
**Gerenciamento de Metadados**: Associar metadados significativos às coleções para clareza operacional
**Descoberta de Coleções**: Facilitar a localização de coleções específicas por meio de filtragem e pesquisa
**Transparência Operacional**: Fornecer visibilidade clara do ciclo de vida e do uso da coleção
**Gerenciamento de Recursos**: Permitir a limpeza de coleções não utilizadas para otimizar a utilização de recursos
**Integridade de Dados**: Impedir a criação de coleções órfãs no armazenamento sem rastreamento de metadados

## Contexto

Anteriormente, as coleções no TrustGraph eram criadas implicitamente durante as operações de carregamento de dados, levando a problemas de sincronização em que as coleções poderiam existir em backends de armazenamento sem metadados correspondentes no bibliotecário. Isso criava desafios de gerenciamento e dados órfãos.

O modelo de criação explícita de coleções aborda esses problemas:
Exigindo que as coleções sejam criadas antes de serem usadas via `tg-set-collection`
Transmitindo a criação da coleção para todos os backends de armazenamento
Mantendo um estado sincronizado entre os metadados do bibliotecário e o armazenamento
Impedindo a gravação em coleções inexistentes
Fornecendo gerenciamento claro do ciclo de vida da coleção

Esta especificação define o modelo de gerenciamento explícito de coleções. Ao exigir a criação explícita de coleções, o TrustGraph garante:
Que as coleções sejam rastreadas nos metadados do bibliotecário desde a criação
Que todos os backends de armazenamento estejam cientes das coleções antes de receber dados
Que não existam coleções órfãs no armazenamento
Visibilidade e controle operacionais claros sobre o ciclo de vida da coleção
Tratamento de erros consistente quando as operações referenciam coleções inexistentes

## Design Técnico

### Arquitetura

O sistema de gerenciamento de coleções será implementado dentro da infraestrutura existente do TrustGraph:

1. **Integração do Serviço do Bibliotecário**
   As operações de gerenciamento de coleções serão adicionadas ao serviço do bibliotecário existente
   Nenhum novo serviço é necessário - aproveita os padrões de autenticação e acesso existentes
   Lida com a listagem, exclusão e gerenciamento de metadados de coleções

   Módulo: trustgraph-librarian

2. **Tabela de Metadados de Coleção do Cassandra**
   Nova tabela no keyspace existente do bibliotecário
   Armazena metadados da coleção com acesso específico ao usuário
   Chave primária: (user_id, collection_id) para multilocação adequada

   Módulo: trustgraph-librarian

3. **CLI de Gerenciamento de Coleções**
   Interface de linha de comando para operações de coleção
   Fornece comandos de listagem, exclusão, rotulagem e gerenciamento de tags
   Integra-se com o framework de CLI existente

   Módulo: trustgraph-cli

### Modelos de Dados

#### Tabela de Metadados de Coleção do Cassandra

Os metadados da coleção serão armazenados em uma tabela estruturada do Cassandra no keyspace do bibliotecário:

```sql
CREATE TABLE collections (
    user text,
    collection text,
    name text,
    description text,
    tags set<text>,
    created_at timestamp,
    updated_at timestamp,
    PRIMARY KEY (user, collection)
);
```

Estrutura da tabela:
**user** + **collection**: Chave primária composta que garante o isolamento do usuário
**name**: Nome da coleção legível por humanos
**description**: Descrição detalhada do propósito da coleção
**tags**: Conjunto de tags para categorização e filtragem
**created_at**: Timestamp de criação da coleção
**updated_at**: Timestamp da última modificação

Esta abordagem permite:
Gerenciamento de coleções multi-tenant com isolamento de usuário
Consulta eficiente por usuário e coleção
Sistema de tags flexível para organização
Rastreamento do ciclo de vida para insights operacionais

#### Ciclo de Vida da Coleção

As coleções são explicitamente criadas no gerenciador antes que as operações de dados possam prosseguir:

1. **Criação da Coleção** (Dois Caminhos):

   **Caminho A: Criação Iniciada pelo Usuário** via `tg-set-collection`:
   O usuário fornece o ID da coleção, nome, descrição e tags
   O gerenciador cria um registro de metadados na tabela `collections`
   O gerenciador transmite "create-collection" para todos os backends de armazenamento
   Todos os processadores de armazenamento criam a coleção e confirmam o sucesso
   A coleção está agora pronta para operações de dados

   **Caminho B: Criação Automática na Submissão de Documento**:
   O usuário submete um documento especificando um ID de coleção
   O gerenciador verifica se a coleção existe na tabela de metadados
   Se não existir: O gerenciador cria metadados com valores padrão (nome=collection_id, descrição/tags vazias)
   O gerenciador transmite "create-collection" para todos os backends de armazenamento
   Todos os processadores de armazenamento criam a coleção e confirmam o sucesso
   O processamento do documento prossegue com a coleção agora estabelecida

   Ambos os caminhos garantem que a coleção exista nos metadados do gerenciador E em todos os backends de armazenamento antes de permitir operações de dados.

2. **Validação de Armazenamento**: As operações de escrita validam se a coleção existe:
   Os processadores de armazenamento verificam o estado da coleção antes de aceitar escritas
   As escritas em coleções inexistentes retornam um erro
   Isso impede que as escritas contornem a lógica de criação de coleção do gerenciador

3. **Comportamento da Consulta**: As operações de consulta lidam com coleções inexistentes de forma elegante:
   As consultas em coleções inexistentes retornam resultados vazios
   Nenhum erro é lançado para operações de consulta
   Permite a exploração sem exigir que a coleção exista

4. **Atualizações de Metadados**: Os usuários podem atualizar os metadados da coleção após a criação:
   Atualize o nome, a descrição e as tags via `tg-set-collection`
   As atualizações se aplicam apenas aos metadados do gerenciador
   Os backends de armazenamento mantêm a coleção, mas as atualizações de metadados não são propagadas

5. **Exclusão Explícita**: Os usuários excluem coleções via `tg-delete-collection`:
   O gerenciador transmite "delete-collection" para todos os backends de armazenamento
   Aguarda a confirmação de todos os processadores de armazenamento
   Exclui o registro de metadados do gerenciador somente após a limpeza do armazenamento estar completa
   Garante que nenhum dado órfão permaneça no armazenamento

**Princípio Chave**: O gerenciador é o ponto de controle único para a criação de coleções. Seja iniciada por um comando do usuário ou pela submissão de um documento, o gerenciador garante o rastreamento adequado de metadados e a sincronização do backend de armazenamento antes de permitir operações de dados.

Operações necessárias:
**Criar Coleção**: Operação do usuário via `tg-set-collection` OU automática na submissão de documento
**Atualizar Metadados da Coleção**: Operação do usuário para modificar o nome, a descrição e as tags
**Excluir Coleção**: Operação do usuário para remover a coleção e seus dados em todos os armazenamentos
**Listar Coleções**: Operação do usuário para visualizar coleções com filtragem por tags

#### Gerenciamento de Coleções em Múltiplos Armazenamentos

As coleções existem em vários backends de armazenamento no TrustGraph:
**Vector Stores** (Qdrant, Milvus, Pinecone): Armazena embeddings e dados vetoriais
**Object Stores** (Cassandra): Armazena documentos e dados de arquivos
**Triple Stores** (Cassandra, Neo4j, Memgraph, FalkorDB): Armazena dados de grafo/RDF

Cada tipo de armazenamento implementa:
**Rastreamento do Estado da Coleção**: Manter o conhecimento de quais coleções existem
**Criação de Coleção**: Aceitar e processar operações de "criar-coleção"
**Validação de Coleção**: Verificar se a coleção existe antes de aceitar gravações
**Exclusão de Coleção**: Remover todos os dados para a coleção especificada

O serviço de bibliotecário coordena as operações de coleção em todos os tipos de armazenamento, garantindo:
Que as coleções sejam criadas em todos os backends antes de serem usadas
Que todos os backends confirmem a criação antes de retornar o sucesso
Ciclo de vida da coleção sincronizado em todos os tipos de armazenamento
Tratamento de erros consistente quando as coleções não existem

#### Rastreamento do Estado da Coleção por Tipo de Armazenamento

Cada backend de armazenamento rastreia o estado da coleção de forma diferente, com base em suas capacidades:

**Cassandra Triple Store:**
Usa a tabela `triples_collection` existente
Cria um triple de marcador do sistema quando a coleção é criada
Consulta: `SELECT collection FROM triples_collection WHERE collection = ? LIMIT 1`
Verificação de existência de coleção eficiente de partição única

**Qdrant/Milvus/Pinecone Vector Stores:**
As APIs nativas de coleção fornecem verificação de existência
Coleções criadas com configuração de vetor adequada
O método `collection_exists()` usa a API de armazenamento
A criação da coleção valida os requisitos de dimensão

**Neo4j/Memgraph/FalkorDB Graph Stores:**
Usa nós `:CollectionMetadata` para rastrear coleções
Propriedades do nó: `{user, collection, created_at}`
Consulta: `MATCH (c:CollectionMetadata {user: $user, collection: $collection})`
Separado de nós de dados para uma separação limpa
Permite listagem e validação eficientes de coleções

**Cassandra Object Store:**
Usa a tabela de metadados da coleção ou linhas de marcador
Padrão semelhante ao triple store
Valida a coleção antes das gravações de documentos

### APIs

APIs de Gerenciamento de Coleção (Bibliotecário):
**Criar/Atualizar Coleção**: Criar uma nova coleção ou atualizar metadados existentes via `tg-set-collection`
**Listar Coleções**: Recuperar coleções para um usuário com filtragem opcional por tag
**Excluir Coleção**: Remover a coleção e os dados associados, propagando para todos os tipos de armazenamento

APIs de Gerenciamento de Armazenamento (Todos os Processadores de Armazenamento):
**Criar Coleção**: Lidar com a operação de "criar-coleção", estabelecer a coleção no armazenamento
**Excluir Coleção**: Lidar com a operação de "excluir-coleção", remover todos os dados da coleção
**Verificação de Existência da Coleção**: Validação interna antes de aceitar operações de gravação

APIs de Operação de Dados (Comportamento Modificado):
**APIs de Gravação**: Validar se a coleção existe antes de aceitar dados, retornar um erro se não existir
**APIs de Consulta**: Retornar resultados vazios para coleções inexistentes sem erro

### Detalhes de Implementação

A implementação seguirá os padrões existentes do TrustGraph para integração de serviços e estrutura de comandos de linha de comando.

#### Exclusão em Cadeia de Coleção

Quando um usuário inicia a exclusão de uma coleção por meio do serviço de bibliotecário:

1. **Validação de Metadados**: Verificar se a coleção existe e se o usuário tem permissão para excluí-la
2. **Propagação para o Armazenamento**: O bibliotecário coordena a exclusão em todos os escritores de armazenamento:
   Escritor de armazenamento vetorial: Remover incorporações e índices de vetor para o usuário e a coleção
   Escritor de armazenamento de objetos: Remover documentos e arquivos para o usuário e a coleção
   Escritor de triple store: Remover dados de grafo e triples para o usuário e a coleção
3. **Limpeza de Metadados**: Remover o registro de metadados da coleção do Cassandra
4. **Tratamento de Erros**: Se alguma exclusão de armazenamento falhar, manter a consistência por meio de mecanismos de reversão ou repetição

#### Interface de Gerenciamento de Coleção

**⚠️ ABORDAGEM ANTIGA - SUBSTITUÍDA POR PADRÃO BASEADO EM CONFIGURAÇÃO**

A arquitetura baseada em fila descrita abaixo foi substituída por uma abordagem baseada em configuração usando `CollectionConfigHandler`. Todos os backends de armazenamento agora recebem atualizações de coleção por meio de mensagens de configuração em vez de filas de gerenciamento dedicadas.

~~Todos os escritores de armazenamento implementam uma interface de gerenciamento de coleção padronizada com um esquema comum:~~

~~**Esquema de Mensagem (`StorageManagementRequest`):**~~
```json
{
  "operation": "create-collection" | "delete-collection",
  "user": "user123",
  "collection": "documents-2024"
}
```

~~**Arquitetura de Filas:**~~
~~**Fila de Gerenciamento de Vetores** (`vector-storage-management`): Armazenamentos de vetores/embeddings~~
~~**Fila de Gerenciamento de Objetos** (`object-storage-management`): Armazenamentos de objetos/documentos~~
~~**Fila de Gerenciamento de Triplas** (`triples-storage-management`): Armazenamentos de grafos/RDF~~
~~**Fila de Resposta de Armazenamento** (`storage-management-response`): Todas as respostas são enviadas aqui~~

**Implementação Atual:**

Todos os backends de armazenamento agora usam `CollectionConfigHandler`:
**Integração de Configuração Push**: Os serviços de armazenamento se registram para notificações de configuração push
**Sincronização Automática**: Coleções criadas/excluídas com base em alterações de configuração
**Modelo Declarativo**: Coleções definidas no serviço de configuração, os backends sincronizam para corresponder
**Sem Requisição/Resposta**: Elimina a sobrecarga de coordenação e o rastreamento de respostas
**Rastreamento do Estado da Coleção**: Mantido via cache `known_collections`
**Operações Idempotentes**: É seguro processar a mesma configuração várias vezes

Cada backend de armazenamento implementa:
`create_collection(user: str, collection: str, metadata: dict)` - Criar estruturas de coleção
`delete_collection(user: str, collection: str)` - Remover todos os dados da coleção
`collection_exists(user: str, collection: str) -> bool` - Validar antes de gravar

#### Refatoração do Armazenamento de Triplas Cassandra

Como parte desta implementação, o armazenamento de triplas Cassandra será refatorado de um modelo de tabela por coleção para um modelo de tabela unificada:

**Arquitetura Atual:**
Keyspace por usuário, tabela separada por coleção
Esquema: `(s, p, o)` com `PRIMARY KEY (s, p, o)`
Nomes de tabela: coleções de usuários se tornam tabelas Cassandra separadas

**Nova Arquitetura:**
Keyspace por usuário, tabela única "triples" para todas as coleções
Esquema: `(collection, s, p, o)` com `PRIMARY KEY (collection, s, p, o)`
Isolamento de coleção por meio de particionamento de coleção

**Alterações Necessárias:**

1. **Refatoração da Classe TrustGraph** (`trustgraph/direct/cassandra.py`):
   Remover o parâmetro `table` do construtor, usar a tabela "triples" fixa
   Adicionar o parâmetro `collection` a todos os métodos
   Atualizar o esquema para incluir a coleção como a primeira coluna
   **Atualizações de Índice**: Novos índices serão criados para suportar todos os 8 padrões de consulta:
     Índice em `(s)` para consultas baseadas em sujeito
     Índice em `(p)` para consultas baseadas em predicado
     Índice em `(o)` para consultas baseadas em objeto
     Observação: O Cassandra não suporta índices secundários multi-coluna, portanto, estes são índices de coluna única

   **Desempenho do Padrão de Consulta:**
     ✅ `get_all()` - varredura de partição em `collection`
     ✅ `get_s(s)` - usa a chave primária de forma eficiente (`collection, s`)
     ✅ `get_p(p)` - usa `idx_p` com filtragem `collection`
     ✅ `get_o(o)` - usa `idx_o` com filtragem `collection`
     ✅ `get_sp(s, p)` - usa a chave primária de forma eficiente (`collection, s, p`)
     ⚠️ `get_po(p, o)` - requer `ALLOW FILTERING` (usa `idx_p` ou `idx_o` mais filtragem)
     ✅ `get_os(o, s)` - usa `idx_o` com filtragem adicional em `s`
     ✅ `get_spo(s, p, o)` - usa toda a chave primária de forma eficiente

   **Observação sobre ALLOW FILTERING**: O padrão de consulta `get_po` requer `ALLOW FILTERING`, pois precisa tanto de restrições de predicado quanto de objeto sem um índice composto adequado. Isso é aceitável, pois este padrão de consulta é menos comum do que as consultas baseadas em sujeito no uso típico de armazenamentos de triplas.

2. **Atualizações do Gravador de Armazenamento** (`trustgraph/storage/triples/cassandra/write.py`):
   Manter uma única conexão TrustGraph por usuário em vez de por (usuário, coleção)
   Passar a coleção para as operações de inserção
   Melhor utilização de recursos com menos conexões

3. **Atualizações do Serviço de Consulta** (`trustgraph/query/triples/cassandra/service.py`):
   Uma única conexão TrustGraph por usuário
   Passar a coleção para todas as operações de consulta
   Manter a mesma lógica de consulta com o parâmetro de coleção

**Benefícios:**
**Exclusão Simplificada de Coleções**: Excluir usando a chave de partição `collection` em todas as 4 tabelas
**Eficiência de Recursos**: Menos conexões de banco de dados e objetos de tabela
**Operações entre Coleções**: Mais fácil de implementar operações que abrangem várias coleções
**Arquitetura Consistente**: Alinha-se com a abordagem unificada de metadados de coleção
**Validação de Coleção**: Fácil de verificar a existência da coleção via tabela `triples_collection`

As operações de coleção serão atômicas sempre que possível e fornecerão tratamento de erros e validação apropriados.

## Considerações de Segurança

As operações de gerenciamento de coleção requerem autorização apropriada para evitar acesso ou exclusão não autorizados de coleções. O controle de acesso estará alinhado com os modelos de segurança TrustGraph existentes.

## Considerações de Desempenho

As operações de listagem de coleções podem precisar de paginação para ambientes com um grande número de coleções. As consultas de metadados devem ser otimizadas para padrões de filtragem comuns.

## Estratégia de Testes

Os testes abrangentes cobrirão:
Fluxo de trabalho de criação de coleção de ponta a ponta
Sincronização do armazenamento de back-end
Validação de gravação para coleções inexistentes
Tratamento de consultas para coleções inexistentes
Exclusão de coleção em cascata em todos os armazenamentos
Cenários de tratamento de erros e recuperação
Testes unitários para cada armazenamento de back-end
Testes de integração para operações entre armazenamentos

## Status da Implementação

### ✅ Componentes Concluídos

1. **Serviço de Gerenciamento de Coleção Librarian** (`trustgraph-flow/trustgraph/librarian/collection_manager.py`)
   Operações CRUD de metadados de coleção (listagem, atualização, exclusão)
   Integração da tabela de metadados de coleção do Cassandra via `LibraryTableStore`
   Coordenação da exclusão de coleção em cascata em todos os tipos de armazenamento
   Tratamento de solicitações/respostas assíncronas com gerenciamento de erros adequado

2. **Esquema de Metadados de Coleção** (`trustgraph-base/trustgraph/schema/services/collection.py`)
   Esquemas `CollectionManagementRequest` e `CollectionManagementResponse`
   Esquema `CollectionMetadata` para registros de coleção
   Definições de tópicos de fila de solicitações/respostas de coleção

3. **Esquema de Gerenciamento de Armazenamento** (`trustgraph-base/trustgraph/schema/services/storage.py`)
   Esquemas `StorageManagementRequest` e `StorageManagementResponse`
   Tópicos de fila de gerenciamento de armazenamento definidos
   Formato de mensagem para operações de coleção no nível do armazenamento

4. **Esquema de 4 Tabelas do Cassandra** (`trustgraph-flow/trustgraph/direct/cassandra_kg.py`)
   Chaves de partição compostas para desempenho da consulta
   Tabela `triples_collection` para consultas SPO e rastreamento de exclusão
   Exclusão de coleção implementada com o padrão de leitura e exclusão

### ✅ Migração para Padrão Baseado em Configuração - CONCLUÍDO

**Todos os armazenamentos de back-end foram migrados do padrão baseado em fila para o padrão baseado em configuração `CollectionConfigHandler`.**

Migrações concluídas:
✅ `trustgraph-flow/trustgraph/storage/triples/cassandra/write.py`
✅ `trustgraph-flow/trustgraph/storage/triples/neo4j/write.py`
✅ `trustgraph-flow/trustgraph/storage/triples/memgraph/write.py`
✅ `trustgraph-flow/trustgraph/storage/triples/falkordb/write.py`
✅ `trustgraph-flow/trustgraph/storage/doc_embeddings/qdrant/write.py`
✅ `trustgraph-flow/trustgraph/storage/graph_embeddings/qdrant/write.py`
✅ `trustgraph-flow/trustgraph/storage/doc_embeddings/milvus/write.py`
✅ `trustgraph-flow/trustgraph/storage/graph_embeddings/milvus/write.py`
✅ `trustgraph-flow/trustgraph/storage/doc_embeddings/pinecone/write.py`
✅ `trustgraph-flow/trustgraph/storage/graph_embeddings/pinecone/write.py`
✅ `trustgraph-flow/trustgraph/storage/objects/cassandra/write.py`

Todos os backends agora:
Herdam de `CollectionConfigHandler`
Registram-se para notificações de push de configuração via `self.register_config_handler(self.on_collection_config)`
Implementam `create_collection(user, collection, metadata)` e `delete_collection(user, collection)`
Usam `collection_exists(user, collection)` para validar antes de gravar
Sincronizam automaticamente com as alterações do serviço de configuração

Infraestrutura baseada em fila herdada removida:
✅ Esquemas `StorageManagementRequest` e `StorageManagementResponse` removidos
✅ Definições de tópicos de fila de gerenciamento de armazenamento removidas
✅ Consumidor/produtor de gerenciamento de armazenamento removido de todos os backends
✅ Manipuladores `on_storage_management` removidos de todos os backends

