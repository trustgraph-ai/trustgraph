---
layout: default
title: "Suporte para Isolamento de Usuário/Coleção no Neo4j"
parent: "Portuguese (Beta)"
---

# Suporte para Isolamento de Usuário/Coleção no Neo4j

> **Beta Translation:** This document was translated via Machine Learning and as such may not be 100% accurate. All non-English languages are currently classified as Beta.

## Declaração do Problema

A implementação atual de armazenamento e consulta de triplas do Neo4j carece de isolamento de usuário/coleção, o que cria um problema de segurança de multi-inquilinato. Todas as triplas são armazenadas no mesmo espaço de grafo sem nenhum mecanismo para impedir que os usuários acessem os dados de outros usuários ou misturem coleções.

Ao contrário de outros backends de armazenamento no TrustGraph:
**Cassandra**: Usa key spaces separados por usuário e tabelas por coleção.
**Armazenamentos vetoriais** (Milvus, Qdrant, Pinecone): Usam namespaces específicos para cada coleção.
**Neo4j**: Atualmente compartilha todos os dados em um único grafo (vulnerabilidade de segurança).

## Arquitetura Atual

### Modelo de Dados
**Nós**: Rótulo `:Node` com propriedade `uri`, rótulo `:Literal` com propriedade `value`.
**Relacionamentos**: Rótulo `:Rel` com propriedade `uri`.
**Índices**: `Node.uri`, `Literal.value`, `Rel.uri`.

### Fluxo de Mensagens
Mensagens `Triples` contêm campos `metadata.user` e `metadata.collection`.
O serviço de armazenamento recebe informações de usuário/coleção, mas as ignora.
O serviço de consulta espera `user` e `collection` em `TriplesQueryRequest`, mas os ignora.

### Problema de Segurança Atual
```cypher
# Any user can query any data - no isolation
MATCH (src:Node)-[rel:Rel]->(dest:Node) 
RETURN src.uri, rel.uri, dest.uri
```

## Solução Proposta: Filtragem Baseada em Propriedades (Recomendada)

### Visão Geral
Adicione as propriedades `user` e `collection` a todos os nós e relacionamentos, e então filtre todas as operações por essas propriedades. Essa abordagem fornece um forte isolamento, mantendo a flexibilidade da consulta e a compatibilidade com versões anteriores.

### Alterações no Modelo de Dados

#### Estrutura de Nó Aprimorada
```cypher
// Node entities
CREATE (n:Node {
  uri: "http://example.com/entity1",
  user: "john_doe", 
  collection: "production_v1"
})

// Literal entities  
CREATE (n:Literal {
  value: "literal value",
  user: "john_doe",
  collection: "production_v1" 
})
```

#### Estrutura de Relacionamento Aprimorada
```cypher
// Relationships with user/collection properties
CREATE (src)-[:Rel {
  uri: "http://example.com/predicate1",
  user: "john_doe",
  collection: "production_v1"
}]->(dest)
```

#### Índices Atualizados
```cypher
// Compound indexes for efficient filtering
CREATE INDEX node_user_collection_uri FOR (n:Node) ON (n.user, n.collection, n.uri);
CREATE INDEX literal_user_collection_value FOR (n:Literal) ON (n.user, n.collection, n.value);
CREATE INDEX rel_user_collection_uri FOR ()-[r:Rel]-() ON (r.user, r.collection, r.uri);

// Maintain existing indexes for backwards compatibility (optional)
CREATE INDEX Node_uri FOR (n:Node) ON (n.uri);
CREATE INDEX Literal_value FOR (n:Literal) ON (n.value);
CREATE INDEX Rel_uri FOR ()-[r:Rel]-() ON (r.uri);
```

### Alterações na Implementação

#### Serviço de Armazenamento (`write.py`)

**Código Atual:**
```python
def create_node(self, uri):
    summary = self.io.execute_query(
        "MERGE (n:Node {uri: $uri})",
        uri=uri, database_=self.db,
    ).summary
```

**Código Atualizado:**
```python
def create_node(self, uri, user, collection):
    summary = self.io.execute_query(
        "MERGE (n:Node {uri: $uri, user: $user, collection: $collection})",
        uri=uri, user=user, collection=collection, database_=self.db,
    ).summary
```

**Método `store_triples` aprimorado:**
```python
async def store_triples(self, message):
    user = message.metadata.user
    collection = message.metadata.collection
    
    for t in message.triples:
        self.create_node(t.s.value, user, collection)
        
        if t.o.is_uri:
            self.create_node(t.o.value, user, collection)  
            self.relate_node(t.s.value, t.p.value, t.o.value, user, collection)
        else:
            self.create_literal(t.o.value, user, collection)
            self.relate_literal(t.s.value, t.p.value, t.o.value, user, collection)
```

#### Serviço de Consulta (`service.py`)

**Código Atual:**
```python
records, summary, keys = self.io.execute_query(
    "MATCH (src:Node {uri: $src})-[rel:Rel {uri: $rel}]->(dest:Node) "
    "RETURN dest.uri as dest",
    src=query.s.value, rel=query.p.value, database_=self.db,
)
```

**Código Atualizado:**
```python
records, summary, keys = self.io.execute_query(
    "MATCH (src:Node {uri: $src, user: $user, collection: $collection})-"
    "[rel:Rel {uri: $rel, user: $user, collection: $collection}]->"
    "(dest:Node {user: $user, collection: $collection}) "
    "RETURN dest.uri as dest",
    src=query.s.value, rel=query.p.value, 
    user=query.user, collection=query.collection,
    database_=self.db,
)
```

### Estratégia de Migração

#### Fase 1: Adicionar Propriedades a Novos Dados
1. Atualizar o serviço de armazenamento para adicionar propriedades de usuário/coleção a novas triplas.
2. Manter a compatibilidade com versões anteriores, não exigindo propriedades nas consultas.
3. Os dados existentes permanecem acessíveis, mas não isolados.

#### Fase 2: Migrar Dados Existentes
```cypher
// Migrate existing nodes (requires default user/collection assignment)
MATCH (n:Node) WHERE n.user IS NULL
SET n.user = 'legacy_user', n.collection = 'default_collection';

MATCH (n:Literal) WHERE n.user IS NULL  
SET n.user = 'legacy_user', n.collection = 'default_collection';

MATCH ()-[r:Rel]->() WHERE r.user IS NULL
SET r.user = 'legacy_user', r.collection = 'default_collection';
```

#### Fase 3: Impor Isolamento
1. Atualizar o serviço de consulta para exigir filtragem por usuário/coleção.
2. Adicionar validação para rejeitar consultas sem o contexto adequado de usuário/coleção.
3. Remover caminhos de acesso a dados legados.

### Considerações de Segurança

#### Validação de Consulta
```python
async def query_triples(self, query):
    # Validate user/collection parameters
    if not query.user or not query.collection:
        raise ValueError("User and collection must be specified")
    
    # All queries must include user/collection filters
    # ... rest of implementation
```

#### Prevenção de Injeção de Parâmetros
Use exclusivamente consultas parametrizadas
Valide os valores do usuário/coleção em relação a padrões permitidos
Considere a sanitização para os requisitos de nomes de propriedades do Neo4j

#### Rastreamento de Auditoria
```python
logger.info(f"Query executed - User: {query.user}, Collection: {query.collection}, "
           f"Pattern: {query.s}/{query.p}/{query.o}")
```

## Abordagens Alternativas Consideradas

### Opção 2: Isolamento Baseado em Rótulos

**Abordagem**: Utilize rótulos dinâmicos como `User_john_Collection_prod`

**Vantagens:**
Forte isolamento através da filtragem de rótulos
Desempenho de consulta eficiente com índices de rótulos
Separação clara de dados

**Desvantagens:**
O Neo4j possui limites práticos no número de rótulos (aproximadamente 1000)
Geração e sanitização complexas de nomes de rótulos
Difícil consultar entre coleções quando necessário

**Exemplo de Implementação:**
```cypher
CREATE (n:Node:User_john_Collection_prod {uri: "http://example.com/entity"})
MATCH (n:User_john_Collection_prod) WHERE n:Node RETURN n
```

### Opção 3: Banco de Dados por Usuário

**Abordagem**: Criar bancos de dados Neo4j separados para cada usuário ou combinação de usuário/coleção.

**Vantagens:**
Isolamento completo de dados
Sem risco de contaminação cruzada
Escalonamento independente por usuário

**Desvantagens:**
Sobrecarga de recursos (cada banco de dados consome memória)
Gerenciamento complexo do ciclo de vida do banco de dados
Limites do banco de dados da Edição Community do Neo4j
Análise entre usuários difícil

### Opção 4: Estratégia de Chave Composta

**Abordagem**: Prefixar todos os URIs e valores com informações do usuário/coleção.

**Vantagens:**
Compatível com consultas existentes
Implementação simples
Não requer alterações no esquema

**Desvantagens:**
A poluição de URIs afeta a semântica dos dados
Consultas menos eficientes (correspondência de prefixo de string)
Viola padrões RDF/web semântico

**Exemplo de Implementação:**
```python
def make_composite_uri(uri, user, collection):
    return f"usr:{user}:col:{collection}:uri:{uri}"
```

## Plano de Implementação

### Fase 1: Fundação (Semana 1)
1. [ ] Atualizar o serviço de armazenamento para aceitar e armazenar propriedades de usuário/coleção
2. [ ] Adicionar índices compostos para consultas eficientes
3. [ ] Implementar uma camada de compatibilidade retroativa
4. [ ] Criar testes unitários para novas funcionalidades

### Fase 2: Atualizações de Consulta (Semana 2)
1. [ ] Atualizar todos os padrões de consulta para incluir filtros de usuário/coleção
2. [ ] Adicionar validação de consulta e verificações de segurança
3. [ ] Atualizar testes de integração
4. [ ] Testes de desempenho com consultas filtradas

### Fase 3: Migração e Implantação (Semana 3)
1. [ ] Criar scripts de migração de dados para instâncias Neo4j existentes
2. [ ] Documentação de implantação e manuais de operação
3. [ ] Monitoramento e alertas para violações de isolamento
4. [ ] Testes de ponta a ponta com vários usuários/coleções

### Fase 4: Reforço (Semana 4)
1. [ ] Remover o modo de compatibilidade legado
2. [ ] Adicionar registro de auditoria abrangente
3. [ ] Revisão de segurança e testes de penetração
4. [ ] Otimização de desempenho

## Estratégia de Testes

### Testes Unitários
```python
def test_user_collection_isolation():
    # Store triples for user1/collection1
    processor.store_triples(triples_user1_coll1)
    
    # Store triples for user2/collection2  
    processor.store_triples(triples_user2_coll2)
    
    # Query as user1 should only return user1's data
    results = processor.query_triples(query_user1_coll1)
    assert all_results_belong_to_user1_coll1(results)
    
    # Query as user2 should only return user2's data
    results = processor.query_triples(query_user2_coll2)
    assert all_results_belong_to_user2_coll2(results)
```

### Testes de Integração
Cenários multiusuário com dados sobrepostos
Consultas entre coleções (devem falhar)
Testes de migração com dados existentes
Testes de desempenho com grandes conjuntos de dados

### Testes de Segurança
Tentativa de consultar dados de outros usuários
Ataques de injeção de SQL em parâmetros de usuário/coleção
Verificar o isolamento completo sob vários padrões de consulta

## Considerações de Desempenho

### Estratégia de Indexação
Índices compostos em `(user, collection, uri)` para filtragem otimizada
Considere índices parciais se algumas coleções forem muito maiores
Monitore o uso de índices e o desempenho das consultas

### Otimização de Consultas
Use EXPLAIN para verificar o uso de índices em consultas filtradas
Considere o cache de resultados de consulta para dados acessados com frequência
Monitore o uso de memória com um grande número de usuários/coleções

### Escalabilidade
Cada combinação de usuário/coleção cria ilhas de dados separadas
Monitore o tamanho do banco de dados e o uso do pool de conexões
Considere estratégias de escalabilidade horizontal, se necessário

## Segurança e Conformidade

### Garantias de Isolamento de Dados
**Físico**: Todos os dados do usuário armazenados com propriedades explícitas de usuário/coleção
**Lógico**: Todas as consultas filtradas pelo contexto de usuário/coleção
**Controle de Acesso**: A validação no nível do serviço impede o acesso não autorizado

### Requisitos de Auditoria
Registre todo o acesso a dados com o contexto de usuário/coleção
Rastreie atividades de migração e movimentação de dados
Monitore tentativas de violação de isolamento

### Considerações de Conformidade
GDPR: Capacidade aprimorada de localizar e excluir dados específicos do usuário
SOC2: Isolamento claro de dados e controles de acesso
HIPAA: Forte isolamento de locatários para dados de saúde

## Riscos e Mitigações

| Risco | Impacto | Probabilidade | Mitigação |
|------|--------|------------|------------|
| Consulta sem o filtro de usuário/coleção | Alto | Médio | Validação obrigatória, testes abrangentes |
| Degradação de desempenho | Médio | Baixo | Otimização de índice, análise de desempenho |
| Corrupção de dados durante a migração | Alto | Baixo | Estratégia de backup, procedimentos de reversão |
| Consultas complexas entre várias coleções | Médio | Médio | Documente padrões de consulta, forneça exemplos |

## Critérios de Sucesso

1. **Segurança**: Zero acesso a dados de outros usuários em produção
2. **Desempenho**: Impacto de <10% no desempenho da consulta em comparação com consultas não filtradas
3. **Migração**: 100% dos dados existentes migrados com sucesso e sem perda
4. **Usabilidade**: Todos os padrões de consulta existentes funcionam com o contexto de usuário/coleção
5. **Conformidade**: Rastreamento completo de acesso a dados de usuário/coleção

## Conclusão

A abordagem de filtragem baseada em propriedades oferece o melhor equilíbrio entre segurança, desempenho e manutenção para adicionar o isolamento de usuário/coleção ao Neo4j. Ela se alinha aos padrões de multilocação existentes do TrustGraph, aproveitando os pontos fortes do Neo4j em consultas de grafos e indexação.

Esta solução garante que o backend do Neo4j do TrustGraph atenda aos mesmos padrões de segurança de outros backends de armazenamento, prevenindo vulnerabilidades de isolamento de dados, mantendo a flexibilidade e o poder das consultas de grafos.
