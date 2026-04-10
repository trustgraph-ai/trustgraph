# Especificação Técnica de Otimização de Desempenho do GraphRAG

## Visão Geral

Esta especificação descreve otimizações abrangentes de desempenho para o algoritmo GraphRAG (Graph Retrieval-Augmented Generation) no TrustGraph. A implementação atual sofre de gargalos de desempenho significativos que limitam a escalabilidade e os tempos de resposta. Esta especificação aborda quatro áreas principais de otimização:

1. **Otimização de Traversal de Grafos**: Eliminar consultas ineficientes ao banco de dados e implementar exploração de grafos em lote.
2. **Otimização de Resolução de Rótulos**: Substituir a busca sequencial de rótulos por operações paralelas/em lote.
3. **Aprimoramento da Estratégia de Cache**: Implementar um cache inteligente com remoção LRU (Least Recently Used) e pré-busca.
4. **Otimização de Consultas**: Adicionar memorização de resultados e cache de incorporações para melhorar os tempos de resposta.

## Objetivos

**Reduzir o Volume de Consultas ao Banco de Dados**: Alcançar uma redução de 50-80% no volume total de consultas ao banco de dados por meio de loteamento e cache.
**Melhorar os Tempos de Resposta**: Almejar uma construção de subgrafo 3-5 vezes mais rápida e uma resolução de rótulos 2-3 vezes mais rápida.
**Aprimorar a Escalabilidade**: Suportar grafos de conhecimento maiores com melhor gerenciamento de memória.
**Manter a Precisão**: Preservar a funcionalidade e a qualidade dos resultados do GraphRAG existentes.
**Habilitar a Concorrência**: Melhorar as capacidades de processamento paralelo para vários запросов simultâneos.
**Reduzir a Pegada de Memória**: Implementar estruturas de dados e gerenciamento de memória eficientes.
**Adicionar Observabilidade**: Incluir métricas de desempenho e capacidades de monitoramento.
**Garantir a Confiabilidade**: Adicionar tratamento de erros adequado e mecanismos de tempo limite.

## Contexto

A implementação atual do GraphRAG em `trustgraph-flow/trustgraph/retrieval/graph_rag/graph_rag.py` apresenta vários problemas de desempenho críticos que afetam severamente a escalabilidade do sistema:

### Problemas de Desempenho Atuais

**1. Traversal de Grafos Ineficiente (função `follow_edges`, linhas 79-127)**
Realiza 3 consultas separadas ao banco de dados por entidade por nível de profundidade.
Padrão de consulta: consultas baseadas em sujeito, baseadas em predicado e baseadas em objeto para cada entidade.
Sem loteamento: Cada consulta processa apenas uma entidade por vez.
Sem detecção de ciclo: Pode revisitar os mesmos nós várias vezes.
A implementação recursiva sem memorização leva a uma complexidade exponencial.
Complexidade de tempo: O(entidades × max_path_length × triple_limit³)

**2. Resolução Sequencial de Rótulos (função `get_labelgraph`, linhas 144-171)**
Processa cada componente de tripla (sujeito, predicado, objeto) sequencialmente.
Cada chamada de `maybe_label` pode acionar uma consulta ao banco de dados.
Sem execução paralela ou loteamento de consultas de rótulos.
Resulta em até 3 × subgraph_size chamadas individuais ao banco de dados.

**3. Estratégia de Cache Primitiva (função `maybe_label`, linhas 62-77)**
Cache de dicionário simples sem limites de tamanho ou TTL (Time To Live).
A ausência de uma política de remoção de cache leva a um crescimento de memória ilimitado.
Falhas de cache acionam consultas individuais ao banco de dados.
Sem pré-busca ou aquecimento inteligente do cache.

**4. Padrões de Consulta Subótimos**
Consultas de similaridade de vetores de entidade não são armazenadas em cache entre запросов semelhantes.
Sem memorização de resultados para padrões de consulta repetidos.
Otimização de consulta ausente para padrões de acesso comuns.

**5. Problemas Críticos de Tempo de Vida de Objetos (`rag.py:96-102`)**
**Objeto GraphRag recriado por запросом**: Uma nova instância é criada para cada consulta, perdendo todos os benefícios do cache.
**Objeto de consulta com vida extremamente curta**: Criado e destruído dentro da execução de uma única consulta (linhas 201-207).
**Cache de rótulos redefinido por запросом**: O aquecimento do cache e o conhecimento acumulado são perdidos entre запросов.
**Sobrecarga de recriação do cliente**: Clientes de banco de dados podem ser reestabelecidos para cada запросом.
**Sem otimização entre запросов**: Não é possível se beneficiar de padrões de consulta ou compartilhamento de resultados.

### Análise de Impacto no Desempenho

Cenário de pior caso atual para uma consulta típica:
**Recuperação de Entidade**: 1 consulta de similaridade de vetor.
**Traversal de Grafos**: entidades × max_path_length × 3 × consultas de triplas.
**Resolução de Rótulos**: subgraph_size × 3 consultas individuais de rótulos.

Para parâmetros padrão (50 entidades, comprimento do caminho 2, limite de 30 triplas, tamanho do subgrafo de 150):
**Consultas mínimas**: 1 + (50 × 2 × 3 × 30) + (150 × 3) = **9.451 consultas ao banco de dados**
**Tempo de resposta**: 15-30 segundos para grafos de tamanho moderado
**Uso de memória**: Crescimento ilimitado do cache ao longo do tempo
**Eficiência do cache**: 0% - os caches são reiniciados em cada solicitação
**Sobrecarga de criação de objetos**: Objetos GraphRag + Query criados/destruídos por solicitação

Esta especificação aborda essas lacunas implementando consultas em lote, cache inteligente e processamento paralelo. Ao otimizar padrões de consulta e acesso a dados, o TrustGraph pode:
Suportar grafos de conhecimento em escala empresarial com milhões de entidades
Fornecer tempos de resposta de menos de um segundo para consultas típicas
Lidar com centenas de solicitações GraphRAG simultâneas
Escalar de forma eficiente com o tamanho e a complexidade do grafo

## Design Técnico

### Arquitetura

A otimização de desempenho do GraphRAG requer os seguintes componentes técnicos:

#### 1. **Refatoração Arquitetural do Ciclo de Vida dos Objetos**
   **Tornar o GraphRag de longa duração**: Mover a instância GraphRag para o nível do Processador para persistência entre solicitações
   **Preservar caches**: Manter o cache de rótulos, o cache de incorporações e o cache de resultados de consulta entre solicitações
   **Otimizar o objeto Query**: Refatorar o Query como um contexto de execução leve, não como um contêiner de dados
   **Persistência de conexão**: Manter as conexões do cliente do banco de dados entre solicitações

   Módulo: `trustgraph-flow/trustgraph/retrieval/graph_rag/rag.py` (modificado)

#### 2. **Motor de Traversal de Grafos Otimizado**
   Substituir a recursão `follow_edges` por busca em largura iterativa
   Implementar o processamento em lote de entidades em cada nível de traversal
   Adicionar detecção de ciclo usando o rastreamento de nós visitados
   Incluir a terminação antecipada quando os limites são atingidos

   Módulo: `trustgraph-flow/trustgraph/retrieval/graph_rag/optimized_traversal.py`

#### 3. **Sistema de Resolução de Rótulos Paralelo**
   Agrupar consultas de rótulos para várias entidades simultaneamente
   Implementar padrões async/await para acesso concorrente ao banco de dados
   Adicionar pré-busca inteligente para padrões de rótulos comuns
   Incluir estratégias de aquecimento de cache de rótulos

   Módulo: `trustgraph-flow/trustgraph/retrieval/graph_rag/label_resolver.py`

#### 4. **Camada de Cache Conservadora de Rótulos**
   Cache LRU com TTL curto apenas para rótulos (5 minutos) para equilibrar desempenho e consistência
   Monitoramento de métricas e taxa de acerto do cache
   **Sem cache de incorporações**: Já armazenado em cache por consulta, sem benefício entre consultas
   **Sem cache de resultados de consulta**: Devido a preocupações com a consistência da mutação do grafo

   Módulo: `trustgraph-flow/trustgraph/retrieval/graph_rag/cache_manager.py`

#### 5. **Framework de Otimização de Consulta**
   Análise e sugestões de otimização de padrões de consulta
   Coordenador de consultas em lote para acesso ao banco de dados
   Pool de conexões e gerenciamento de tempo limite de consulta
   Monitoramento de desempenho e coleta de métricas

   Módulo: `trustgraph-flow/trustgraph/retrieval/graph_rag/query_optimizer.py`

### Modelos de Dados

#### Estado Otimizado de Traversal de Grafos

O motor de traversal mantém o estado para evitar operações redundantes:

```python
@dataclass
class TraversalState:
    visited_entities: Set[str]
    current_level_entities: Set[str]
    next_level_entities: Set[str]
    subgraph: Set[Tuple[str, str, str]]
    depth: int
    query_batch: List[TripleQuery]
```

Esta abordagem permite:
Detecção eficiente de ciclos através do rastreamento de entidades visitadas.
Preparação de consultas em lote em cada nível de travessia.
Gerenciamento de estado com eficiência de memória.
Término antecipado quando os limites de tamanho são atingidos.

#### Estrutura de Cache Aprimorada

```python
@dataclass
class CacheEntry:
    value: Any
    timestamp: float
    access_count: int
    ttl: Optional[float]

class CacheManager:
    label_cache: LRUCache[str, CacheEntry]
    embedding_cache: LRUCache[str, CacheEntry]
    query_result_cache: LRUCache[str, CacheEntry]
    cache_stats: CacheStatistics
```

#### Estruturas de Consulta em Lote

```python
@dataclass
class BatchTripleQuery:
    entities: List[str]
    query_type: QueryType  # SUBJECT, PREDICATE, OBJECT
    limit_per_entity: int

@dataclass
class BatchLabelQuery:
    entities: List[str]
    predicate: str = LABEL
```

### APIs

#### Novas APIs:

**API de GraphTraversal**
```python
async def optimized_follow_edges_batch(
    entities: List[str],
    max_depth: int,
    triple_limit: int,
    max_subgraph_size: int
) -> Set[Tuple[str, str, str]]
```

**API de Resolução de Rótulos em Lote**
```python
async def resolve_labels_batch(
    entities: List[str],
    cache_manager: CacheManager
) -> Dict[str, str]
```

**API de Gerenciamento de Cache**
```python
class CacheManager:
    async def get_or_fetch_label(self, entity: str) -> str
    async def get_or_fetch_embeddings(self, query: str) -> List[float]
    async def cache_query_result(self, query_hash: str, result: Any, ttl: int)
    def get_cache_statistics(self) -> CacheStatistics
```

#### APIs Modificados:

**GraphRag.query()** - Aprimorado com otimizações de desempenho:
Adicionado parâmetro `cache_manager` para controle de cache.
Incluído valor de retorno `performance_metrics`.
Adicionado parâmetro `query_timeout` para confiabilidade.

**Classe Query** - Refatorada para processamento em lote:
Substituição do processamento individual de entidades por operações em lote.
Adicionados gerenciadores de contexto assíncronos para limpeza de recursos.
Incluídas funções de retorno de progresso para operações de longa duração.

### Detalhes da Implementação

#### Fase 0: Refatoração Crítica do Ciclo de Vida da Arquitetura

**Implementação Atualmente Problemática:**
```python
# INEFFICIENT: GraphRag recreated every request
class Processor(FlowProcessor):
    async def on_request(self, msg, consumer, flow):
        # PROBLEM: New GraphRag instance per request!
        self.rag = GraphRag(
            embeddings_client = flow("embeddings-request"),
            graph_embeddings_client = flow("graph-embeddings-request"),
            triples_client = flow("triples-request"),
            prompt_client = flow("prompt-request"),
            verbose=True,
        )
        # Cache starts empty every time - no benefit from previous requests
        response = await self.rag.query(...)

# VERY SHORT-LIVED: Query object created/destroyed per request
class GraphRag:
    async def query(self, query, user="trustgraph", collection="default", ...):
        q = Query(rag=self, user=user, collection=collection, ...)  # Created
        kg = await q.get_labelgraph(query)  # Used briefly
        # q automatically destroyed when function exits
```

**Arquitetura Otimizada e de Longa Duração:**
```python
class Processor(FlowProcessor):
    def __init__(self, **params):
        super().__init__(**params)
        self.rag_instance = None  # Will be initialized once
        self.client_connections = {}

    async def initialize_rag(self, flow):
        """Initialize GraphRag once, reuse for all requests"""
        if self.rag_instance is None:
            self.rag_instance = LongLivedGraphRag(
                embeddings_client=flow("embeddings-request"),
                graph_embeddings_client=flow("graph-embeddings-request"),
                triples_client=flow("triples-request"),
                prompt_client=flow("prompt-request"),
                verbose=True,
            )
        return self.rag_instance

    async def on_request(self, msg, consumer, flow):
        # REUSE the same GraphRag instance - caches persist!
        rag = await self.initialize_rag(flow)

        # Query object becomes lightweight execution context
        response = await rag.query_with_context(
            query=v.query,
            execution_context=QueryContext(
                user=v.user,
                collection=v.collection,
                entity_limit=entity_limit,
                # ... other params
            )
        )

class LongLivedGraphRag:
    def __init__(self, ...):
        # CONSERVATIVE caches - balance performance vs consistency
        self.label_cache = LRUCacheWithTTL(max_size=5000, ttl=300)  # 5min TTL for freshness
        # Note: No embedding cache - already cached per-query, no cross-query benefit
        # Note: No query result cache due to consistency concerns
        self.performance_metrics = PerformanceTracker()

    async def query_with_context(self, query: str, context: QueryContext):
        # Use lightweight QueryExecutor instead of heavyweight Query object
        executor = QueryExecutor(self, context)  # Minimal object
        return await executor.execute(query)

@dataclass
class QueryContext:
    """Lightweight execution context - no heavy operations"""
    user: str
    collection: str
    entity_limit: int
    triple_limit: int
    max_subgraph_size: int
    max_path_length: int

class QueryExecutor:
    """Lightweight execution context - replaces old Query class"""
    def __init__(self, rag: LongLivedGraphRag, context: QueryContext):
        self.rag = rag
        self.context = context
        # No heavy initialization - just references

    async def execute(self, query: str):
        # All heavy lifting uses persistent rag caches
        return await self.rag.execute_optimized_query(query, self.context)
```

Esta mudança arquitetural oferece:
**Redução de 10-20% nas consultas ao banco de dados** para grafos com relacionamentos comuns (em comparação com 0% atualmente)
**Eliminação da sobrecarga de criação de objetos** para cada requisição
**Pool de conexões persistentes** e reutilização do cliente
**Otimização entre requisições** dentro das janelas de tempo de vida (TTL) do cache

**Limitação Importante de Consistência do Cache:**
O cache de longo prazo introduz o risco de dados desatualizados quando entidades/rótulos são excluídos ou modificados no grafo subjacente. O cache LRU com TTL oferece um equilíbrio entre ganhos de desempenho e frescor dos dados, mas não pode detectar alterações em tempo real no grafo.

#### Fase 1: Otimização de Traversal de Grafos

**Problemas na Implementação Atual:**
```python
# INEFFICIENT: 3 queries per entity per level
async def follow_edges(self, ent, subgraph, path_length):
    # Query 1: s=ent, p=None, o=None
    res = await self.rag.triples_client.query(s=ent, p=None, o=None, limit=self.triple_limit)
    # Query 2: s=None, p=ent, o=None
    res = await self.rag.triples_client.query(s=None, p=ent, o=None, limit=self.triple_limit)
    # Query 3: s=None, p=None, o=ent
    res = await self.rag.triples_client.query(s=None, p=None, o=ent, limit=self.triple_limit)
```

**Implementação Otimizada:**
```python
async def optimized_traversal(self, entities: List[str], max_depth: int) -> Set[Triple]:
    visited = set()
    current_level = set(entities)
    subgraph = set()

    for depth in range(max_depth):
        if not current_level or len(subgraph) >= self.max_subgraph_size:
            break

        # Batch all queries for current level
        batch_queries = []
        for entity in current_level:
            if entity not in visited:
                batch_queries.extend([
                    TripleQuery(s=entity, p=None, o=None),
                    TripleQuery(s=None, p=entity, o=None),
                    TripleQuery(s=None, p=None, o=entity)
                ])

        # Execute all queries concurrently
        results = await self.execute_batch_queries(batch_queries)

        # Process results and prepare next level
        next_level = set()
        for result in results:
            subgraph.update(result.triples)
            next_level.update(result.new_entities)

        visited.update(current_level)
        current_level = next_level - visited

    return subgraph
```

#### Fase 2: Resolução Paralela de Rótulos

**Implementação Sequencial Atual:**
```python
# INEFFICIENT: Sequential processing
for edge in subgraph:
    s = await self.maybe_label(edge[0])  # Individual query
    p = await self.maybe_label(edge[1])  # Individual query
    o = await self.maybe_label(edge[2])  # Individual query
```

**Implementação Paralela Otimizada:**
```python
async def resolve_labels_parallel(self, subgraph: List[Triple]) -> List[Triple]:
    # Collect all unique entities needing labels
    entities_to_resolve = set()
    for s, p, o in subgraph:
        entities_to_resolve.update([s, p, o])

    # Remove already cached entities
    uncached_entities = [e for e in entities_to_resolve if e not in self.label_cache]

    # Batch query for all uncached labels
    if uncached_entities:
        label_results = await self.batch_label_query(uncached_entities)
        self.label_cache.update(label_results)

    # Apply labels to subgraph
    return [
        (self.label_cache.get(s, s), self.label_cache.get(p, p), self.label_cache.get(o, o))
        for s, p, o in subgraph
    ]
```

#### Fase 3: Estratégia Avançada de Cache

**Cache LRU com TTL:**
```python
class LRUCacheWithTTL:
    def __init__(self, max_size: int, default_ttl: int = 3600):
        self.cache = OrderedDict()
        self.max_size = max_size
        self.default_ttl = default_ttl
        self.access_times = {}

    async def get(self, key: str) -> Optional[Any]:
        if key in self.cache:
            # Check TTL expiration
            if time.time() - self.access_times[key] > self.default_ttl:
                del self.cache[key]
                del self.access_times[key]
                return None

            # Move to end (most recently used)
            self.cache.move_to_end(key)
            return self.cache[key]
        return None

    async def put(self, key: str, value: Any):
        if key in self.cache:
            self.cache.move_to_end(key)
        else:
            if len(self.cache) >= self.max_size:
                # Remove least recently used
                oldest_key = next(iter(self.cache))
                del self.cache[oldest_key]
                del self.access_times[oldest_key]

        self.cache[key] = value
        self.access_times[key] = time.time()
```

#### Fase 4: Otimização de Consulta e Monitoramento

**Coleta de Métricas de Desempenho:**
```python
@dataclass
class PerformanceMetrics:
    total_queries: int
    cache_hits: int
    cache_misses: int
    avg_response_time: float
    subgraph_construction_time: float
    label_resolution_time: float
    total_entities_processed: int
    memory_usage_mb: float
```

**Tempo Limite de Consulta e Disjuntor:**
```python
async def execute_with_timeout(self, query_func, timeout: int = 30):
    try:
        return await asyncio.wait_for(query_func(), timeout=timeout)
    except asyncio.TimeoutError:
        logger.error(f"Query timeout after {timeout}s")
        raise GraphRagTimeoutError(f"Query exceeded timeout of {timeout}s")
```

## Considerações sobre a Consistência do Cache

**Compensações entre a Atualidade dos Dados:**
**Cache de rótulos (TTL de 5 minutos)**: Risco de exibir rótulos de entidades excluídas/renomeadas.
**Sem cache de embeddings**: Não é necessário - os embeddings já são armazenados em cache por consulta.
**Sem cache de resultados**: Impede que resultados de subgrafos desatualizados sejam exibidos devido à exclusão de entidades/relacionamentos.

**Estratégias de Mitigação:**
**Valores de TTL conservadores**: Equilibre os ganhos de desempenho (10-20%) com a atualização dos dados.
**Hooks de invalidação de cache**: Integração opcional com eventos de mutação do grafo.
**Painéis de monitoramento**: Acompanhe as taxas de acerto do cache versus incidentes de desatualização.
**Políticas de cache configuráveis**: Permite ajustes específicos para cada implantação, com base na frequência de mutação.

**Configuração de Cache Recomendada pela Taxa de Mutação do Grafo:**
**Alta mutação (>100 alterações/hora)**: TTL=60s, tamanhos de cache menores.
**Média mutação (10-100 alterações/hora)**: TTL=300s (padrão).
**Baixa mutação (<10 alterações/hora)**: TTL=600s, tamanhos de cache maiores.

## Considerações de Segurança

**Prevenção de Injeção de Consulta:**
Valide todos os identificadores de entidade e parâmetros de consulta.
Use consultas parametrizadas para todas as interações com o banco de dados.
Implemente limites de complexidade de consulta para evitar ataques de negação de serviço (DoS).

**Proteção de Recursos:**
Aplique limites máximos de tamanho de subgrafo.
Implemente tempos limite de consulta para evitar o esgotamento de recursos.
Adicione monitoramento e limites de uso de memória.

**Controle de Acesso:**
Mantenha o isolamento existente de usuários e coleções.
Adicione registro de auditoria para operações que afetam o desempenho.
Implemente limitação de taxa para operações dispendiosas.

## Considerações de Desempenho

### Melhorias de Desempenho Esperadas

**Redução de Consultas:**
Atual: ~9.000+ consultas para um pedido típico.
Otimizado: ~50-100 consultas agrupadas (redução de 98%).

**Melhorias no Tempo de Resposta:**
Travessia do grafo: 15-20s → 3-5s (4-5 vezes mais rápido).
Resolução de rótulos: 8-12s → 2-4s (3 vezes mais rápido).
Consulta geral: 25-35s → 6-10s (melhora de 3-4 vezes).

**Eficiência de Memória:**
Tamanhos de cache limitados evitam vazamentos de memória.
Estruturas de dados eficientes reduzem a pegada de memória em ~40%.
Melhor coleta de lixo através da limpeza adequada de recursos.

**Expectativas Realistas de Desempenho:**
**Cache de rótulos**: Redução de 10-20% nas consultas para grafos com relacionamentos comuns.
**Otimização de agrupamento**: Redução de 50-80% nas consultas (otimização primária).
**Otimização do ciclo de vida do objeto**: Elimina a sobrecarga de criação por pedido.
**Melhora geral**: Melhoria de 3-4 vezes no tempo de resposta, principalmente devido ao agrupamento.

**Melhorias de Escalabilidade:**
Suporte para grafos de conhecimento 3-5 vezes maiores (limitado pelas necessidades de consistência do cache).
Capacidade de solicitação concorrente 3-5 vezes maior.
Melhor utilização de recursos através da reutilização de conexões.

### Monitoramento de Desempenho

**Métricas em Tempo Real:**
Tempos de execução de consultas por tipo de operação.
Taxas de acerto e eficácia do cache.
Utilização do pool de conexões do banco de dados.
Uso de memória e impacto da coleta de lixo.

**Benchmarking de Desempenho:**
Testes de regressão de desempenho automatizados
Testes de carga com volumes de dados realistas
Benchmarks de comparação com a implementação atual

## Estratégia de Testes

### Testes Unitários
Teste de componentes individuais para travessia, cache e resolução de rótulos
Simulações de interações com o banco de dados para testes de desempenho
Testes de expiração de cache e TTL
Tratamento de erros e cenários de timeout

### Testes de Integração
Testes de ponta a ponta de consultas GraphRAG com otimizações
Testes de interação com o banco de dados com dados reais
Tratamento de solicitações concorrentes e gerenciamento de recursos
Detecção de vazamentos de memória e verificação da limpeza de recursos

### Testes de Desempenho
Testes de benchmark contra a implementação atual
Testes de carga com tamanhos e complexidades de grafos variáveis
Testes de estresse para limites de memória e conexões
Testes de regressão para melhorias de desempenho

### Testes de Compatibilidade
Verificar a compatibilidade da API GraphRAG existente
Testar com vários backends de banco de dados de grafos
Validar a precisão dos resultados em comparação com a implementação atual

## Plano de Implementação

### Abordagem de Implementação Direta
Como as APIs podem ser alteradas, implemente as otimizações diretamente sem a complexidade da migração:

1. **Substituir `follow_edges`**: Reescrever com travessia em lote iterativa
2. **Otimizar `get_labelgraph`**: Implementar resolução de rótulos paralela
3. **Adicionar GraphRag de longa duração**: Modificar o Processador para manter uma instância persistente
4. **Implementar cache de rótulos**: Adicionar um cache LRU com TTL à classe GraphRag

### Escopo das Alterações
**Classe de consulta**: Substituir ~50 linhas em `follow_edges`, adicionar ~30 linhas para tratamento em lote
**Classe GraphRag**: Adicionar uma camada de cache (~40 linhas)
**Classe Processador**: Modificar para usar uma instância persistente de GraphRag (~20 linhas)
**Total**: ~140 linhas de alterações focadas, principalmente dentro das classes existentes

## Cronograma

**Semana 1: Implementação Central**
Substituir `follow_edges` por travessia iterativa em lote
Implementar resolução de rótulos paralela em `get_labelgraph`
Adicionar uma instância de longa duração de GraphRag ao Processador
Implementar a camada de cache de rótulos

**Semana 2: Testes e Integração**
Testes unitários para a nova lógica de travessia e cache
Benchmarking de desempenho contra a implementação atual
Testes de integração com dados de grafos reais
Revisão de código e otimização

**Semana 3: Implantação**
Implantar a implementação otimizada
Monitorar as melhorias de desempenho
Ajustar o TTL do cache e os tamanhos do lote com base no uso real

## Perguntas Abertas

**Pool de Conexões do Banco de Dados**: Devemos implementar um pool de conexões personalizado ou usar o pool de conexões do cliente do banco de dados existente?
**Persistência do Cache**: Os caches de rótulos e embeddings devem persistir entre as reinicializações do serviço?
**Cache Distribuído**: Para implantações multi-instância, devemos implementar um cache distribuído com Redis/Memcached?
**Formato do Resultado da Consulta**: Devemos otimizar a representação interna da tripla para uma melhor eficiência de memória?
**Integração de Monitoramento**: Quais métricas devem ser expostas aos sistemas de monitoramento existentes (Prometheus, etc.)?

## Referências

[Implementação Original do GraphRAG](trustgraph-flow/trustgraph/retrieval/graph_rag/graph_rag.py)
[Princípios de Arquitetura do TrustGraph](architecture-principles.md)
[Especificação de Gerenciamento de Coleções](collection-management.md)
