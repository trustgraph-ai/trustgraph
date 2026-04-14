---
layout: default
title: "Especificação Técnica: Suporte para Multi-Tenancy"
parent: "Portuguese (Beta)"
---

# Especificação Técnica: Suporte para Multi-Tenancy

> **Beta Translation:** This document was translated via Machine Learning and as such may not be 100% accurate. All non-English languages are currently classified as Beta.

## Visão Geral

Habilite implantações multi-tenant corrigindo incompatibilidades de nomes de parâmetros que impedem a personalização da fila e adicionando parametrização do keyspace do Cassandra.

## Contexto da Arquitetura

### Resolução de Filas Baseada em Fluxo

O sistema TrustGraph usa uma **arquitetura baseada em fluxo** para a resolução dinâmica de filas, que suporta inerentemente o multi-tenancy:

As **Definições de Fluxo** são armazenadas no Cassandra e especificam os nomes das filas por meio de definições de interface.
**Os nomes das filas usam modelos** com variáveis `{id}` que são substituídas pelos IDs das instâncias de fluxo.
**Os serviços resolvem dinamicamente as filas** consultando as configurações de fluxo no momento da solicitação.
**Cada tenant pode ter fluxos únicos** com nomes de fila diferentes, proporcionando isolamento.

Exemplo de definição de interface de fluxo:
```json
{
  "interfaces": {
    "triples-store": "persistent://tg/flow/triples-store:{id}",
    "graph-embeddings-store": "persistent://tg/flow/graph-embeddings-store:{id}"
  }
}
```

Quando o tenant A inicia o fluxo `tenant-a-prod` e o tenant B inicia o fluxo `tenant-b-prod`, eles automaticamente recebem filas isoladas:
`persistent://tg/flow/triples-store:tenant-a-prod`
`persistent://tg/flow/triples-store:tenant-b-prod`

**Serviços corretamente projetados para multi-tenancy:**
✅ **Knowledge Management (cores)** - Resolve dinamicamente as filas a partir da configuração do fluxo passada nas requisições

**Serviços que precisam de correções:**
🔴 **Config Service** - Incompatibilidade no nome do parâmetro impede a personalização da fila
🔴 **Librarian Service** - Tópicos de gerenciamento de armazenamento codificados (discutido abaixo)
🔴 **Todos os Serviços** - Não é possível personalizar o keyspace do Cassandra

## Declaração do Problema

### Problema #1: Incompatibilidade no Nome do Parâmetro no AsyncProcessor
**CLI define:** `--config-queue` (nomeação pouco clara)
**Argparse converte para:** `config_queue` (no dicionário de parâmetros)
**Código procura por:** `config_push_queue`
**Resultado:** O parâmetro é ignorado, usa o valor padrão de `persistent://tg/config/config`
**Impacto:** Afeta todos os 32+ serviços que herdam do AsyncProcessor
**Bloqueia:** Impossibilita o uso de filas de configuração específicas do tenant em implantações multi-tenant
**Solução:** Renomear o parâmetro da CLI para `--config-push-queue` para maior clareza (alteração disruptiva aceitável, já que o recurso está atualmente com defeito)

### Problema #2: Incompatibilidade no Nome do Parâmetro no Config Service
**CLI define:** `--push-queue` (nomeação ambígua)
**Argparse converte para:** `push_queue` (no dicionário de parâmetros)
**Código procura por:** `config_push_queue`
**Resultado:** O parâmetro é ignorado
**Impacto:** O Config service não pode usar uma fila de push personalizada
**Solução:** Renomear o parâmetro da CLI para `--config-push-queue` para consistência e clareza (alteração disruptiva aceitável)

### Problema #3: Keyspace do Cassandra Codificado
**Atual:** Keyspace codificado como `"config"`, `"knowledge"`, `"librarian"` em vários serviços
**Resultado:** Impossibilita a personalização do keyspace para implantações multi-tenant
**Impacto:** Serviços Config, cores e librarian
**Bloqueia:** Múltiplos tenants não podem usar keyspaces separados do Cassandra

### Problema #4: Arquitetura de Gerenciamento de Coleções ✅ CONCLUÍDO
**Anterior:** Coleções armazenadas no keyspace do librarian do Cassandra em uma tabela de coleções separada
**Anterior:** O librarian usava 4 tópicos de gerenciamento de armazenamento codificados para coordenar a criação/exclusão de coleções:
  `vector_storage_management_topic`
  `object_storage_management_topic`
  `triples_storage_management_topic`
  `storage_management_response_topic`
**Problemas (Resolvidos):**
  Tópicos codificados não podiam ser personalizados para implantações multi-tenant
  Coordenação assíncrona complexa entre o librarian e 4+ serviços de armazenamento
  Tabela separada do Cassandra e infraestrutura de gerenciamento
  Filas de requisição/resposta não persistentes para operações críticas
**Solução Implementada:** Migrou as coleções para o armazenamento do serviço de configuração, usa push de configuração para distribuição
**Status:** Todos os backends de armazenamento migrados para o padrão `CollectionConfigHandler`

## Solução

Esta especificação aborda os problemas #1, #2, #3 e #4.

### Parte 1: Corrigir Incompatibilidades no Nome do Parâmetro

#### Alteração 1: Classe Base AsyncProcessor - Renomear Parâmetro da CLI
**Arquivo:** `trustgraph-base/trustgraph/base/async_processor.py`
**Linha:** 260-264

**Atual:**
```python
parser.add_argument(
    '--config-queue',
    default=default_config_queue,
    help=f'Config push queue {default_config_queue}',
)
```

**Corrigido:**
```python
parser.add_argument(
    '--config-push-queue',
    default=default_config_queue,
    help=f'Config push queue (default: {default_config_queue})',
)
```

**Justificativa:**
Nomenclatura mais clara e explícita
Coincide com o nome da variável interna `config_push_queue`
Mudança disruptiva aceitável, já que a funcionalidade está atualmente inativa
Não é necessária nenhuma alteração no código em params.get() - ele já procura pelo nome correto

#### Mudança 2: Serviço de Configuração - Renomear Parâmetro da CLI
**Arquivo:** `trustgraph-flow/trustgraph/config/service/service.py`
**Linha:** 276-279

**Atual:**
```python
parser.add_argument(
    '--push-queue',
    default=default_config_push_queue,
    help=f'Config push queue (default: {default_config_push_queue})'
)
```

**Corrigido:**
```python
parser.add_argument(
    '--config-push-queue',
    default=default_config_push_queue,
    help=f'Config push queue (default: {default_config_push_queue})'
)
```

**Justificativa:**
Nomes mais claros - "config-push-queue" é mais explícito do que apenas "push-queue".
Compatível com o nome da variável interna `config_push_queue`.
Consistente com o parâmetro `--config-push-queue` do AsyncProcessor.
Mudança disruptiva aceitável, já que o recurso está atualmente inativo.
Nenhuma alteração de código necessária em params.get() - ele já procura pelo nome correto.

### Parte 2: Adicionar Parametrização do Keyspace do Cassandra

#### Mudança 3: Adicionar Parâmetro de Keyspace ao Módulo cassandra_config
**Arquivo:** `trustgraph-base/trustgraph/base/cassandra_config.py`

**Adicionar argumento de linha de comando** (na função `add_cassandra_args()`):
```python
parser.add_argument(
    '--cassandra-keyspace',
    default=None,
    help='Cassandra keyspace (default: service-specific)'
)
```

**Adicionar suporte para variáveis de ambiente** (na função `resolve_cassandra_config()`):
```python
keyspace = params.get(
    "cassandra_keyspace",
    os.environ.get("CASSANDRA_KEYSPACE")
)
```

**Atualizar o valor de retorno** de `resolve_cassandra_config()`:
Atualmente retorna: `(hosts, username, password)`
Alterar para retornar: `(hosts, username, password, keyspace)`

**Justificativa:**
Consistente com o padrão de configuração existente do Cassandra
Disponível para todos os serviços via `add_cassandra_args()`
Suporta configuração via linha de comando e variáveis de ambiente

#### Mudança 4: Serviço de Configuração - Usar Keyspace Parametrizados
**Arquivo:** `trustgraph-flow/trustgraph/config/service/service.py`

**Linha 30** - Remover o keyspace codificado:
```python
# DELETE THIS LINE:
keyspace = "config"
```

**Linhas 69-73** - Atualização da resolução da configuração do Cassandra:

**Atual:**
```python
cassandra_host, cassandra_username, cassandra_password = \
    resolve_cassandra_config(params)
```

**Corrigido:**
```python
cassandra_host, cassandra_username, cassandra_password, keyspace = \
    resolve_cassandra_config(params, default_keyspace="config")
```

**Justificativa:**
Mantém a compatibilidade com versões anteriores, utilizando "config" como padrão.
Permite a substituição através de `--cassandra-keyspace` ou `CASSANDRA_KEYSPACE`.

#### Mudança 5: Cores/Serviço de Conhecimento - Utilizar Chaves de Espaço de Chaves Parametrizadas
**Arquivo:** `trustgraph-flow/trustgraph/cores/service.py`

**Linha 37** - Remover o espaço de chaves codificado:
```python
# DELETE THIS LINE:
keyspace = "knowledge"
```

**Atualização da resolução de configuração do Cassandra** (localização semelhante ao serviço de configuração):
```python
cassandra_host, cassandra_username, cassandra_password, keyspace = \
    resolve_cassandra_config(params, default_keyspace="knowledge")
```

#### Mudança 6: Serviço de Bibliotecário - Use Chaves de Espaço de Chaves Parametrizadas
**Arquivo:** `trustgraph-flow/trustgraph/librarian/service.py`

**Linha 51** - Remova a chave de espaço de chaves codificada:
```python
# DELETE THIS LINE:
keyspace = "librarian"
```

**Atualização da resolução de configuração do Cassandra** (localização semelhante ao serviço de configuração):
```python
cassandra_host, cassandra_username, cassandra_password, keyspace = \
    resolve_cassandra_config(params, default_keyspace="librarian")
```

### Parte 3: Migrar o Gerenciamento de Coleções para o Serviço de Configuração

#### Visão Geral
Migrar as coleções do keyspace do Cassandra librarian para o armazenamento do serviço de configuração. Isso elimina os tópicos de gerenciamento de armazenamento codificados e simplifica a arquitetura, utilizando o mecanismo de push de configuração existente para distribuição.

#### Arquitetura Atual
```
API Request → Gateway → Librarian Service
                            ↓
                    CollectionManager
                            ↓
                    Cassandra Collections Table (librarian keyspace)
                            ↓
                    Broadcast to 4 Storage Management Topics (hardcoded)
                            ↓
        Wait for 4+ Storage Service Responses
                            ↓
                    Response to Gateway
```

#### Nova Arquitetura
```
API Request → Gateway → Librarian Service
                            ↓
                    CollectionManager
                            ↓
                    Config Service API (put/delete/getvalues)
                            ↓
                    Cassandra Config Table (class='collections', key='user:collection')
                            ↓
                    Config Push (to all subscribers on config-push-queue)
                            ↓
        All Storage Services receive config update independently
```

#### Mudança 7: Gerenciador de Coleções - Usar API do Serviço de Configuração
**Arquivo:** `trustgraph-flow/trustgraph/librarian/collection_manager.py`

**Remover:**
Uso de `LibraryTableStore` (Linhas 33, 40-41)
Inicialização de produtores de gerenciamento de armazenamento (Linhas 86-140)
Método `on_storage_response` (Linhas 400-430)
Rastreamento de `pending_deletions` (Linhas 57, 90-96 e uso em todo o código)

**Adicionar:**
Cliente do serviço de configuração para chamadas de API (padrão de solicitação/resposta)

**Configuração do Cliente:**
```python
# In __init__, add config request/response producers/consumers
from trustgraph.schema.services.config import ConfigRequest, ConfigResponse

# Producer for config requests
self.config_request_producer = Producer(
    client=pulsar_client,
    topic=config_request_queue,
    schema=ConfigRequest,
)

# Consumer for config responses (with correlation ID)
self.config_response_consumer = Consumer(
    taskgroup=taskgroup,
    client=pulsar_client,
    flow=None,
    topic=config_response_queue,
    subscriber=f"{id}-config",
    schema=ConfigResponse,
    handler=self.on_config_response,
)

# Tracking for pending config requests
self.pending_config_requests = {}  # request_id -> asyncio.Event
```

**Modificar `list_collections` (Linhas 145-180):**
```python
async def list_collections(self, user, tag_filter=None, limit=None):
    """List collections from config service"""
    # Send getvalues request to config service
    request = ConfigRequest(
        id=str(uuid.uuid4()),
        operation='getvalues',
        type='collections',
    )

    # Send request and wait for response
    response = await self.send_config_request(request)

    # Parse collections from response
    collections = []
    for key, value_json in response.values.items():
        if ":" in key:
            coll_user, collection = key.split(":", 1)
            if coll_user == user:
                metadata = json.loads(value_json)
                collections.append(CollectionMetadata(**metadata))

    # Apply tag filtering in-memory (as before)
    if tag_filter:
        collections = [c for c in collections if any(tag in c.tags for tag in tag_filter)]

    # Apply limit
    if limit:
        collections = collections[:limit]

    return collections

async def send_config_request(self, request):
    """Send config request and wait for response"""
    event = asyncio.Event()
    self.pending_config_requests[request.id] = event

    await self.config_request_producer.send(request)
    await event.wait()

    return self.pending_config_requests.pop(request.id + "_response")

async def on_config_response(self, message, consumer, flow):
    """Handle config response"""
    response = message.value()
    if response.id in self.pending_config_requests:
        self.pending_config_requests[response.id + "_response"] = response
        self.pending_config_requests[response.id].set()
```

**Modificar `update_collection` (Linhas 182-312):**
```python
async def update_collection(self, user, collection, name, description, tags):
    """Update collection via config service"""
    # Create metadata
    metadata = CollectionMetadata(
        user=user,
        collection=collection,
        name=name,
        description=description,
        tags=tags,
    )

    # Send put request to config service
    request = ConfigRequest(
        id=str(uuid.uuid4()),
        operation='put',
        type='collections',
        key=f'{user}:{collection}',
        value=json.dumps(metadata.to_dict()),
    )

    response = await self.send_config_request(request)

    if response.error:
        raise RuntimeError(f"Config update failed: {response.error.message}")

    # Config service will trigger config push automatically
    # Storage services will receive update and create collections
```

**Modificar `delete_collection` (Linhas 314-398):**
```python
async def delete_collection(self, user, collection):
    """Delete collection via config service"""
    # Send delete request to config service
    request = ConfigRequest(
        id=str(uuid.uuid4()),
        operation='delete',
        type='collections',
        key=f'{user}:{collection}',
    )

    response = await self.send_config_request(request)

    if response.error:
        raise RuntimeError(f"Config delete failed: {response.error.message}")

    # Config service will trigger config push automatically
    # Storage services will receive update and delete collections
```

**Formato de Metadados de Coleção:**
Armazenado na tabela de configuração como: `class='collections', key='user:collection'`
O valor é uma CollectionMetadata serializada em JSON (sem campos de timestamp)
Campos: `user`, `collection`, `name`, `description`, `tags`
Exemplo: `class='collections', key='alice:my-docs', value='{"user":"alice","collection":"my-docs","name":"My Documents","description":"...","tags":["work"]}'`

#### Mudança 8: Serviço de Bibliotecário - Remover a Infraestrutura de Gerenciamento de Armazenamento
**Arquivo:** `trustgraph-flow/trustgraph/librarian/service.py`

**Remover:**
Produtores de gerenciamento de armazenamento (Linhas 173-190):
  `vector_storage_management_producer`
  `object_storage_management_producer`
  `triples_storage_management_producer`
Consumidor de resposta de armazenamento (Linhas 192-201)
Manipulador `on_storage_response` (Linhas 467-473)

**Modificar:**
Inicialização do CollectionManager (Linhas 215-224) - remover os parâmetros do produtor de armazenamento

**Observação:** A API externa de coleções permanece inalterada:
`list-collections`
`update-collection`
`delete-collection`

#### Mudança 9: Remover a Tabela de Coleções do LibraryTableStore
**Arquivo:** `trustgraph-flow/trustgraph/tables/library.py`

**Excluir:**
Instrução CREATE da tabela de coleções (Linhas 114-127)
Prepared statements de coleções (Linhas 205-240)
Todos os métodos de coleção (Linhas 578-717):
  `ensure_collection_exists`
  `list_collections`
  `update_collection`
  `delete_collection`
  `get_collection`
  `create_collection`

**Justificativa:**
As coleções agora são armazenadas na tabela de configuração
Mudança disruptiva aceitável - nenhuma migração de dados necessária
Simplifica significativamente o serviço de bibliotecário

#### Mudança 10: Serviços de Armazenamento - Gerenciamento de Coleção Baseado em Configuração ✅ CONCLUÍDO

**Status:** Todos os 11 backends de armazenamento foram migrados para usar `CollectionConfigHandler`.

**Serviços Afetados (11 no total):**
Embeddings de documentos: milvus, pinecone, qdrant
Embeddings de grafos: milvus, pinecone, qdrant
Armazenamento de objetos: cassandra
Armazenamento de triplas: cassandra, falkordb, memgraph, neo4j

**Arquivos:**
`trustgraph-flow/trustgraph/storage/doc_embeddings/milvus/write.py`
`trustgraph-flow/trustgraph/storage/doc_embeddings/pinecone/write.py`
`trustgraph-flow/trustgraph/storage/doc_embeddings/qdrant/write.py`
`trustgraph-flow/trustgraph/storage/graph_embeddings/milvus/write.py`
`trustgraph-flow/trustgraph/storage/graph_embeddings/pinecone/write.py`
`trustgraph-flow/trustgraph/storage/graph_embeddings/qdrant/write.py`
`trustgraph-flow/trustgraph/storage/objects/cassandra/write.py`
`trustgraph-flow/trustgraph/storage/triples/cassandra/write.py`
`trustgraph-flow/trustgraph/storage/triples/falkordb/write.py`
`trustgraph-flow/trustgraph/storage/triples/memgraph/write.py`
`trustgraph-flow/trustgraph/storage/triples/neo4j/write.py`

**Padrão de Implementação (todos os serviços):**

1. **Registrar o manipulador de configuração em `__init__`:**
```python
# Add after AsyncProcessor initialization
self.register_config_handler(self.on_collection_config)
self.known_collections = set()  # Track (user, collection) tuples
```

2. **Implementar o gerenciador de configuração:**
```python
async def on_collection_config(self, config, version):
    """Handle collection configuration updates"""
    logger.info(f"Collection config version: {version}")

    if "collections" not in config:
        return

    # Parse collections from config
    # Key format: "user:collection" in config["collections"]
    config_collections = set()
    for key in config["collections"].keys():
        if ":" in key:
            user, collection = key.split(":", 1)
            config_collections.add((user, collection))

    # Determine changes
    to_create = config_collections - self.known_collections
    to_delete = self.known_collections - config_collections

    # Create new collections (idempotent)
    for user, collection in to_create:
        try:
            await self.create_collection_internal(user, collection)
            self.known_collections.add((user, collection))
            logger.info(f"Created collection: {user}/{collection}")
        except Exception as e:
            logger.error(f"Failed to create {user}/{collection}: {e}")

    # Delete removed collections (idempotent)
    for user, collection in to_delete:
        try:
            await self.delete_collection_internal(user, collection)
            self.known_collections.discard((user, collection))
            logger.info(f"Deleted collection: {user}/{collection}")
        except Exception as e:
            logger.error(f"Failed to delete {user}/{collection}: {e}")
```

3. **Inicialize as coleções conhecidas na inicialização:**
```python
async def start(self):
    """Start the processor"""
    await super().start()
    await self.sync_known_collections()

async def sync_known_collections(self):
    """Query backend to populate known_collections set"""
    # Backend-specific implementation:
    # - Milvus/Pinecone/Qdrant: List collections/indexes matching naming pattern
    # - Cassandra: Query keyspaces or collection metadata
    # - Neo4j/Memgraph/FalkorDB: Query CollectionMetadata nodes
    pass
```

4. **Refatore os métodos de tratamento existentes:**
```python
# Rename and remove response sending:
# handle_create_collection → create_collection_internal
# handle_delete_collection → delete_collection_internal

async def create_collection_internal(self, user, collection):
    """Create collection (idempotent)"""
    # Same logic as current handle_create_collection
    # But remove response producer calls
    # Handle "already exists" gracefully
    pass

async def delete_collection_internal(self, user, collection):
    """Delete collection (idempotent)"""
    # Same logic as current handle_delete_collection
    # But remove response producer calls
    # Handle "not found" gracefully
    pass
```

5. **Remover a infraestrutura de gerenciamento de armazenamento:**
   Remover a configuração e inicialização de `self.storage_request_consumer`
   Remover a configuração de `self.storage_response_producer`
   Remover o método de dispatcher de `on_storage_management`
   Remover as métricas para o gerenciamento de armazenamento
   Remover as importações: `StorageManagementRequest`, `StorageManagementResponse`

**Considerações Específicas para o Backend:**

**Bancos de dados vetoriais (Milvus, Pinecone, Qdrant):** Rastrear a lógica `(user, collection)` em `known_collections`, mas pode criar múltiplas coleções de backend por dimensão. Continuar o padrão de criação preguiçosa. As operações de exclusão devem remover todas as variantes de dimensão.

**Cassandra Objects:** As coleções são propriedades de linha, não estruturas. Rastrear informações no nível do keyspace.

**Bancos de dados de grafos (Neo4j, Memgraph, FalkorDB):** Consultar nós `CollectionMetadata` na inicialização. Criar/excluir nós de metadados na sincronização.

**Cassandra Triples:** Usar a API `KnowledgeGraph` para operações de coleção.

**Pontos-Chave do Design:**

**Consistência eventual:** Não há mecanismo de solicitação/resposta, o envio de configuração é transmitido.
**Idempotência:** Todas as operações de criação/exclusão devem ser seguras para serem repetidas.
**Tratamento de erros:** Registrar erros, mas não bloquear as atualizações de configuração.
**Autorreparação:** As operações com falha serão repetidas na próxima atualização de configuração.
**Formato da chave da coleção:** `"user:collection"` em `config["collections"]`

#### Mudança 11: Atualizar o Esquema da Coleção - Remover Timestamps
**Arquivo:** `trustgraph-base/trustgraph/schema/services/collection.py`

**Modificar CollectionMetadata (Linhas 13-21):**
Remover os campos `created_at` e `updated_at`:
```python
class CollectionMetadata(Record):
    user = String()
    collection = String()
    name = String()
    description = String()
    tags = Array(String())
    # Remove: created_at = String()
    # Remove: updated_at = String()
```

**Modificar CollectionManagementRequest (linhas 25-47):**
Remover campos de timestamp:
```python
class CollectionManagementRequest(Record):
    operation = String()
    user = String()
    collection = String()
    timestamp = String()
    name = String()
    description = String()
    tags = Array(String())
    # Remove: created_at = String()
    # Remove: updated_at = String()
    tag_filter = Array(String())
    limit = Integer()
```

**Justificativa:**
Os carimbos de data e hora não agregam valor para coleções.
O serviço de configuração mantém seu próprio rastreamento de versão.
Simplifica o esquema e reduz o armazenamento.

#### Benefícios da Migração do Serviço de Configuração

1. ✅ **Elimina tópicos de gerenciamento de armazenamento codificados** - Resolve o bloqueio multi-inquilino.
2. ✅ **Coordenação mais simples** - Sem espera assíncrona complexa por 4 ou mais respostas de armazenamento.
3. ✅ **Consistência eventual** - Os serviços de armazenamento são atualizados independentemente por meio de push de configuração.
4. ✅ **Melhor confiabilidade** - Push de configuração persistente versus solicitação/resposta não persistente.
5. ✅ **Modelo de configuração unificado** - Coleções tratadas como configuração.
6. ✅ **Reduz a complexidade** - Remove aproximadamente 300 linhas de código de coordenação.
7. ✅ **Pronto para multi-inquilino** - A configuração já suporta o isolamento de inquilinos por meio de keyspace.
8. ✅ **Rastreamento de versão** - O mecanismo de versão do serviço de configuração fornece um histórico de auditoria.

## Notas de Implementação

### Compatibilidade com versões anteriores

**Alterações de parâmetros:**
As alterações de nome dos parâmetros da CLI são alterações disruptivas, mas aceitáveis (o recurso atualmente não está funcional).
Os serviços funcionam sem parâmetros (use os padrões).
Keyspaces padrão preservados: "config", "knowledge", "librarian".
Fila padrão: `persistent://tg/config/config`

**Gerenciamento de coleções:**
**Alteração disruptiva:** A tabela de coleções foi removida do keyspace librarian.
**Nenhuma migração de dados fornecida** - aceitável para esta fase.
A API de coleção externa não foi alterada (operações de listagem, atualização e exclusão).
O formato de metadados da coleção foi simplificado (os carimbos de data e hora foram removidos).

### Requisitos de teste

**Teste de parâmetros:**
1. Verificar se o parâmetro `--config-push-queue` funciona no serviço graph-embeddings.
2. Verificar se o parâmetro `--config-push-queue` funciona no serviço text-completion.
3. Verificar se o parâmetro `--config-push-queue` funciona no serviço de configuração.
4. Verificar se o parâmetro `--cassandra-keyspace` funciona para o serviço de configuração.
5. Verificar se o parâmetro `--cassandra-keyspace` funciona para o serviço cores.
6. Verificar se o parâmetro `--cassandra-keyspace` funciona para o serviço librarian.
7. Verificar se os serviços funcionam sem parâmetros (usa os padrões).
8. Verificar a implantação multi-inquilino com nomes de fila e keyspace personalizados.

**Teste de gerenciamento de coleções:**
9. Verificar a operação `list-collections` por meio do serviço de configuração.
10. Verificar se `update-collection` cria/atualiza na tabela de configuração.
11. Verificar se `delete-collection` remove da tabela de configuração.
12. Verificar se o push de configuração é acionado em atualizações de coleção.
13. Verificar se a filtragem de tags funciona com armazenamento baseado em configuração.
14. Verificar se as operações de coleção funcionam sem campos de carimbo de data e hora.

### Exemplo de implantação multi-inquilino
```bash
# Tenant: tg-dev
graph-embeddings \
  -p pulsar+ssl://broker:6651 \
  --pulsar-api-key <KEY> \
  --config-push-queue persistent://tg-dev/config/config

config-service \
  -p pulsar+ssl://broker:6651 \
  --pulsar-api-key <KEY> \
  --config-push-queue persistent://tg-dev/config/config \
  --cassandra-keyspace tg_dev_config
```

## Análise de Impacto

### Serviços Afetados pela Alteração 1-2 (Renomeação de Parâmetro da CLI)
Todos os serviços que herdam de AsyncProcessor ou FlowProcessor:
config-service
cores-service
librarian-service
graph-embeddings
document-embeddings
text-completion-* (todos os provedores)
extract-* (todos os extractors)
query-* (todos os serviços de consulta)
retrieval-* (todos os serviços RAG)
storage-* (todos os serviços de armazenamento)
E mais 20 serviços

### Serviços Afetados pelas Alterações 3-6 (Keyspace do Cassandra)
config-service
cores-service
librarian-service

### Serviços Afetados pelas Alterações 7-11 (Gerenciamento de Coleções)

**Alterações Imediatas:**
librarian-service (collection_manager.py, service.py)
tables/library.py (remoção da tabela de coleções)
schema/services/collection.py (remoção do timestamp)

**Alterações Concluídas (Alteração 10):** ✅
Todos os serviços de armazenamento (11 no total) - migrados para o push de configuração para atualizações de coleções via `CollectionConfigHandler`
Esquema de gerenciamento de armazenamento removido de `storage.py`

## Considerações Futuras

### Modelo de Keyspace por Usuário

Alguns serviços usam **keyspaces por usuário** dinamicamente, onde cada usuário recebe seu próprio keyspace do Cassandra:

**Serviços com keyspaces por usuário:**
1. **Triples Query Service** (`trustgraph-flow/trustgraph/query/triples/cassandra/service.py:65`)
   Usa `keyspace=query.user`
2. **Objects Query Service** (`trustgraph-flow/trustgraph/query/objects/cassandra/service.py:479`)
   Usa `keyspace=self.sanitize_name(user)`
3. **KnowledgeGraph Direct Access** (`trustgraph-flow/trustgraph/direct/cassandra_kg.py:18`)
   Parâmetro padrão `keyspace="trustgraph"`

**Status:** Estes **não são modificados** nesta especificação.

**Revisão Futura Necessária:**
Avaliar se o modelo de keyspace por usuário cria problemas de isolamento de locatários
Considerar se as implementações multi-locatário precisam de padrões de prefixo de keyspace (por exemplo, `tenant_a_user1`)
Revisar para possíveis colisões de ID de usuário entre locatários
Avaliar se um keyspace compartilhado único por locatário com isolamento de linha baseado em usuário é preferível

**Observação:** Isso não impede a implementação multi-locatário atual, mas deve ser revisado antes das implementações multi-locatário de produção.

## Fases de Implementação

### Fase 1: Correções de Parâmetros (Alterações 1-6)
Corrigir a nomenclatura do parâmetro `--config-push-queue`
Adicionar suporte ao parâmetro `--cassandra-keyspace`
**Resultado:** Configuração de fila e keyspace multi-locatário habilitada

### Fase 2: Migração do Gerenciamento de Coleções (Alterações 7-9, 11)
Migrar o armazenamento de coleções para o serviço de configuração
Remover a tabela de coleções do librarian
Atualizar o esquema de coleção (remover timestamps)
**Resultado:** Elimina tópicos de gerenciamento de armazenamento codificados, simplifica o librarian

### Fase 3: Atualizações do Serviço de Armazenamento (Alteração 10) ✅ CONCLUÍDA
Atualizados todos os serviços de armazenamento para usar o push de configuração para coleções via `CollectionConfigHandler`
Removida a infraestrutura de solicitação/resposta de gerenciamento de armazenamento
Removidas as definições de esquema legadas
**Resultado:** Gerenciamento de coleções baseado em configuração completo alcançado

## Referências
GitHub Issue: https://github.com/trustgraph-ai/trustgraph/issues/582
Arquivos Relacionados:
  `trustgraph-base/trustgraph/base/async_processor.py`
  `trustgraph-base/trustgraph/base/cassandra_config.py`
  `trustgraph-base/trustgraph/schema/core/topic.py`
  `trustgraph-base/trustgraph/schema/services/collection.py`
  `trustgraph-flow/trustgraph/config/service/service.py`
  `trustgraph-flow/trustgraph/cores/service.py`
  `trustgraph-flow/trustgraph/librarian/service.py`
  `trustgraph-flow/trustgraph/librarian/collection_manager.py`
  `trustgraph-flow/trustgraph/tables/library.py`
