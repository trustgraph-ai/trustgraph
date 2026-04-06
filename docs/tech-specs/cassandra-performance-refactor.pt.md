# Especificação Técnica: Refatoração de Desempenho da Base de Conhecimento Cassandra

**Status:** Rascunho
**Autor:** Assistente
**Data:** 2025-09-18

## Visão Geral

Esta especificação aborda problemas de desempenho na implementação da base de conhecimento Cassandra TrustGraph e propõe otimizações para o armazenamento e consulta de triplas RDF.

## Implementação Atual

### Design do Esquema

A implementação atual utiliza um design de tabela única em `trustgraph-flow/trustgraph/direct/cassandra_kg.py`:

```sql
CREATE TABLE triples (
    collection text,
    s text,
    p text,
    o text,
    PRIMARY KEY (collection, s, p, o)
);
```

**Índices Secundários:**
`triples_s` EM `s` (sujeito)
`triples_p` EM `p` (predicado)
`triples_o` EM `o` (objeto)

### Padrões de Consulta

A implementação atual suporta 8 padrões de consulta distintos:

1. **get_all(coleção, limite=50)** - Recupera todas as triplas para uma coleção
   ```sql
   SELECT s, p, o FROM triples WHERE collection = ? LIMIT 50
   ```

2. **get_s(collection, s, limit=10)** - Consulta por assunto
   ```sql
   SELECT p, o FROM triples WHERE collection = ? AND s = ? LIMIT 10
   ```

3. **get_p(collection, p, limit=10)** - Consulta por predicado
   ```sql
   SELECT s, o FROM triples WHERE collection = ? AND p = ? LIMIT 10
   ```

4. **get_o(collection, o, limit=10)** - Consulta por objeto
   ```sql
   SELECT s, p FROM triples WHERE collection = ? AND o = ? LIMIT 10
   ```

5. **get_sp(collection, s, p, limit=10)** - Consulta por sujeito + predicado
   ```sql
   SELECT o FROM triples WHERE collection = ? AND s = ? AND p = ? LIMIT 10
   ```

6. **get_po(collection, p, o, limit=10)** - Consulta por predicado + objeto ⚠️
   ```sql
   SELECT s FROM triples WHERE collection = ? AND p = ? AND o = ? LIMIT 10 ALLOW FILTERING
   ```

7. **get_os(collection, o, s, limit=10)** - Consulta por objeto + sujeito ⚠️
   ```sql
   SELECT p FROM triples WHERE collection = ? AND o = ? AND s = ? LIMIT 10 ALLOW FILTERING
   ```

8. **get_spo(collection, s, p, o, limit=10)** - Correspondência exata de tripla.
   ```sql
   SELECT s as x FROM triples WHERE collection = ? AND s = ? AND p = ? AND o = ? LIMIT 10
   ```

### Arquitetura Atual

**Arquivo: `trustgraph-flow/trustgraph/direct/cassandra_kg.py`**
Classe única `KnowledgeGraph` que gerencia todas as operações
Pool de conexões através de uma lista global `_active_clusters`
Nome de tabela fixo: `"triples"`
Modelo de keyspace por usuário
Replicação SimpleStrategy com fator 1

**Pontos de Integração:**
**Caminho de Escrita:** `trustgraph-flow/trustgraph/storage/triples/cassandra/write.py`
**Caminho de Consulta:** `trustgraph-flow/trustgraph/query/triples/cassandra/service.py`
**Armazenamento de Conhecimento:** `trustgraph-flow/trustgraph/tables/knowledge.py`

## Problemas de Desempenho Identificados

### Problemas no Nível do Schema

1. **Design de Chave Primária Ineficiente**
   Atual: `PRIMARY KEY (collection, s, p, o)`
   Resulta em agrupamento inadequado para padrões de acesso comuns
   Força o uso de índices secundários caros

2. **Uso Excessivo de Índices Secundários** ⚠️
   Três índices secundários em colunas de alta cardinalidade (s, p, o)
   Índices secundários em Cassandra são caros e não escalam bem
   As consultas 6 e 7 requerem `ALLOW FILTERING`, indicando modelagem de dados inadequada

3. **Risco de Partições Quentes**
   Uma única chave de partição `collection` pode criar partições quentes
   Grandes coleções se concentrarão em nós únicos
   Não há estratégia de distribuição para balanceamento de carga

### Problemas no Nível da Consulta

1. **Uso de ALLOW FILTERING** ⚠️
   Dois tipos de consulta (get_po, get_os) requerem `ALLOW FILTERING`
   Essas consultas escaneiam várias partições e são extremamente caras
   O desempenho degrada linearmente com o tamanho dos dados

2. **Padrões de Acesso Ineficientes**
   Não há otimização para padrões de consulta RDF comuns
   Índices compostos ausentes para combinações de consulta frequentes
   Não há consideração para padrões de travessia de grafos

3. **Falta de Otimização de Consulta**
   Não há cache de prepared statements
   Não há dicas de consulta ou estratégias de otimização
   Não há consideração para paginação além de um simples LIMIT

## Declaração do Problema

A implementação atual da base de conhecimento Cassandra tem dois gargalos críticos de desempenho:

### 1. Desempenho Ineficiente da Consulta get_po

A consulta `get_po(collection, p, o)` é extremamente ineficiente devido à necessidade de `ALLOW FILTERING`:

```sql
SELECT s FROM triples WHERE collection = ? AND p = ? AND o = ? LIMIT 10 ALLOW FILTERING
```

**Por que isso é problemático:**
`ALLOW FILTERING` força o Cassandra a escanear todas as partições dentro da coleção.
O desempenho diminui linearmente com o tamanho dos dados.
Este é um padrão de consulta RDF comum (encontrar sujeitos que têm um relacionamento específico de predicado-objeto).
Cria uma carga significativa no cluster à medida que os dados crescem.

### 2. Estratégia de Clustering Inadequada

A chave primária atual `PRIMARY KEY (collection, s, p, o)` oferece benefícios mínimos de clustering:

**Problemas com o clustering atual:**
`collection` como chave de partição não distribui os dados de forma eficaz.
A maioria das coleções contém dados diversos, tornando o clustering ineficaz.
Não há consideração para padrões de acesso comuns em consultas RDF.
Coleções grandes criam partições quentes em nós únicos.
As colunas de clustering (s, p, o) não otimizam para padrões típicos de travessia de grafos.

**Impacto:**
As consultas não se beneficiam da localidade dos dados.
Utilização inadequada do cache.
Distribuição desigual de carga entre os nós do cluster.
Gargalos de escalabilidade à medida que as coleções crescem.

## Solução Proposta: Estratégia de Desnormalização de 4 Tabelas

### Visão Geral

Substitua a única tabela `triples` por quatro tabelas projetadas especificamente, cada uma otimizada para padrões de consulta específicos. Isso elimina a necessidade de índices secundários e ALLOW FILTERING, ao mesmo tempo em que fornece desempenho ideal para todos os tipos de consulta. A quarta tabela permite a exclusão eficiente de coleções, apesar das chaves de partição compostas.

### Novo Design de Esquema

**Tabela 1: Consultas Centradas no Sujeito (triples_s)**
```sql
CREATE TABLE triples_s (
    collection text,
    s text,
    p text,
    o text,
    PRIMARY KEY ((collection, s), p, o)
);
```
**Otimiza:** get_s, get_sp, get_os
**Chave de Partição:** (coleção, s) - Melhor distribuição do que apenas a coleção
**Agrupamento:** (p, o) - Permite pesquisas eficientes de predicados/objetos para um sujeito

**Tabela 2: Consultas Predicado-Objeto (triples_p)**
```sql
CREATE TABLE triples_p (
    collection text,
    p text,
    o text,
    s text,
    PRIMARY KEY ((collection, p), o, s)
);
```
**Otimiza:** get_p, get_po (elimina ALLOW FILTERING!)
**Chave de Partição:** (coleção, p) - Acesso direto por predicado
**Agrupamento:** (o, s) - Traversal eficiente de objeto-sujeito

**Tabela 3: Consultas Orientadas a Objetos (triples_o)**
```sql
CREATE TABLE triples_o (
    collection text,
    o text,
    s text,
    p text,
    PRIMARY KEY ((collection, o), s, p)
);
```
**Otimiza:** get_o
**Chave de Partição:** (coleção, o) - Acesso direto por objeto
**Agrupamento:** (s, p) - Traversal eficiente de sujeito-predicado

**Tabela 4: Gerenciamento de Coleções e Consultas SPO (triples_collection)**
```sql
CREATE TABLE triples_collection (
    collection text,
    s text,
    p text,
    o text,
    PRIMARY KEY (collection, s, p, o)
);
```
**Otimiza:** get_spo, delete_collection
**Chave de Partição:** coleção apenas - Permite operações eficientes no nível da coleção.
**Agrupamento:** (s, p, o) - Ordenação padrão de triplas.
**Propósito:** Uso duplo para pesquisas exatas de SPO e como índice de exclusão.

### Mapeamento de Consultas

| Consulta Original | Tabela de Destino | Melhoria de Desempenho |
|----------------|-------------|------------------------|
| get_all(collection) | triples_s | PERMITE FILTRAGEM (aceitável para varredura) |
| get_s(collection, s) | triples_s | Acesso direto à partição |
| get_p(collection, p) | triples_p | Acesso direto à partição |
| get_o(collection, o) | triples_o | Acesso direto à partição |
| get_sp(collection, s, p) | triples_s | Partição + agrupamento |
| get_po(collection, p, o) | triples_p | **Não mais PERMITE FILTRAGEM!** |
| get_os(collection, o, s) | triples_o | Partição + agrupamento |
| get_spo(collection, s, p, o) | triples_collection | Pesquisa de chave exata |
| delete_collection(collection) | triples_collection | Lê o índice, exclusão em lote de todos |

### Estratégia de Exclusão de Coleção

Com chaves de partição compostas, não podemos simplesmente executar `DELETE FROM table WHERE collection = ?`. Em vez disso:

1. **Fase de Leitura:** Consulta `triples_collection` para enumerar todas as triplas:
   ```sql
   SELECT s, p, o FROM triples_collection WHERE collection = ?
   ```
   Isso é eficiente, já que `collection` é a chave de partição para esta tabela.

2. **Fase de Exclusão:** Para cada tripla (s, p, o), exclua de todas as 4 tabelas usando as chaves de partição completas:
   ```sql
   DELETE FROM triples_s WHERE collection = ? AND s = ? AND p = ? AND o = ?
   DELETE FROM triples_p WHERE collection = ? AND p = ? AND o = ? AND s = ?
   DELETE FROM triples_o WHERE collection = ? AND o = ? AND s = ? AND p = ?
   DELETE FROM triples_collection WHERE collection = ? AND s = ? AND p = ? AND o = ?
   ```
   Agrupado em lotes de 100 para maior eficiência.

**Análise de Compromissos:**
✅ Mantém o desempenho ideal das consultas com partições distribuídas.
✅ Sem partições com alta carga para grandes coleções.
❌ Lógica de exclusão mais complexa (leitura e depois exclusão).
❌ Tempo de exclusão proporcional ao tamanho da coleção.

### Benefícios

1. **Elimina ALLOW FILTERING** - Cada consulta tem um caminho de acesso ideal (exceto a varredura get_all).
2. **Sem Índices Secundários** - Cada tabela É o índice para seu padrão de consulta.
3. **Melhor Distribuição de Dados** - As chaves de partição compostas distribuem a carga de forma eficaz.
4. **Desempenho Previsível** - O tempo de consulta é proporcional ao tamanho do resultado, não ao tamanho total dos dados.
5. **Aproveita os Pontos Fortes do Cassandra** - Projetado para a arquitetura do Cassandra.
6. **Permite a Exclusão de Coleções** - triples_collection serve como índice de exclusão.

## Plano de Implementação

### Arquivos que Requerem Alterações

#### Arquivo de Implementação Primário

**`trustgraph-flow/trustgraph/direct/cassandra_kg.py`** - Reescrita completa necessária.

**Métodos Atuais a Serem Refatorados:**
```python
# Schema initialization
def init(self) -> None  # Replace single table with three tables

# Insert operations
def insert(self, collection, s, p, o) -> None  # Write to all three tables

# Query operations (API unchanged, implementation optimized)
def get_all(self, collection, limit=50)      # Use triples_by_subject
def get_s(self, collection, s, limit=10)     # Use triples_by_subject
def get_p(self, collection, p, limit=10)     # Use triples_by_po
def get_o(self, collection, o, limit=10)     # Use triples_by_object
def get_sp(self, collection, s, p, limit=10) # Use triples_by_subject
def get_po(self, collection, p, o, limit=10) # Use triples_by_po (NO ALLOW FILTERING!)
def get_os(self, collection, o, s, limit=10) # Use triples_by_subject
def get_spo(self, collection, s, p, o, limit=10) # Use triples_by_subject

# Collection management
def delete_collection(self, collection) -> None  # Delete from all three tables
```

#### Arquivos de Integração (Nenhuma Alteração de Lógica Necessária)

**`trustgraph-flow/trustgraph/storage/triples/cassandra/write.py`**
Nenhuma alteração necessária - utiliza a API KnowledgeGraph existente
Beneficia automaticamente das melhorias de desempenho

**`trustgraph-flow/trustgraph/query/triples/cassandra/service.py`**
Nenhuma alteração necessária - utiliza a API KnowledgeGraph existente
Beneficia automaticamente das melhorias de desempenho

### Arquivos de Teste que Requerem Atualizações

#### Testes Unitários
**`tests/unit/test_storage/test_triples_cassandra_storage.py`**
Atualizar as expectativas dos testes para as alterações no esquema
Adicionar testes para a consistência de várias tabelas
Verificar se não há ALLOW FILTERING nos planos de consulta

**`tests/unit/test_query/test_triples_cassandra_query.py`**
Atualizar as asserções de desempenho
Testar todos os 8 padrões de consulta contra as novas tabelas
Verificar o roteamento da consulta para as tabelas corretas

#### Testes de Integração
**`tests/integration/test_cassandra_integration.py`**
Testes de ponta a ponta com o novo esquema
Comparativos de benchmarking de desempenho
Verificação da consistência dos dados entre as tabelas

**`tests/unit/test_storage/test_cassandra_config_integration.py`**
Atualizar os testes de validação de esquema
Testar cenários de migração

### Estratégia de Implementação

#### Fase 1: Esquema e Métodos Principais
1. **Reescrever o método `init()`** - Criar quatro tabelas em vez de uma
2. **Reescrever o método `insert()`** - Gravações em lote em todas as quatro tabelas
3. **Implementar instruções preparadas** - Para desempenho ideal
4. **Adicionar lógica de roteamento de tabela** - Direcionar consultas para as tabelas mais adequadas
5. **Implementar a exclusão de coleções** - Ler de triples_collection, excluir em lote de todas as tabelas

#### Fase 2: Otimização do Método de Consulta
1. **Reescrever cada método get_*** para usar a tabela mais adequada
2. **Remover todo o uso de ALLOW FILTERING**
3. **Implementar o uso eficiente da chave de agrupamento**
4. **Adicionar registro de desempenho da consulta**

#### Fase 3: Gerenciamento de Coleções
1. **Atualizar `delete_collection()`** - Remover de todas as três tabelas
2. **Adicionar verificação de consistência** - Garantir que todas as tabelas permaneçam sincronizadas
3. **Implementar operações em lote** - Para operações multi-tabela atômicas

### Detalhes Chave da Implementação

#### Estratégia de Gravação em Lote
```python
def insert(self, collection, s, p, o):
    batch = BatchStatement()

    # Insert into all four tables
    batch.add(self.insert_subject_stmt, (collection, s, p, o))
    batch.add(self.insert_po_stmt, (collection, p, o, s))
    batch.add(self.insert_object_stmt, (collection, o, s, p))
    batch.add(self.insert_collection_stmt, (collection, s, p, o))

    self.session.execute(batch)
```

#### Lógica de Roteamento de Consultas
```python
def get_po(self, collection, p, o, limit=10):
    # Route to triples_p table - NO ALLOW FILTERING!
    return self.session.execute(
        self.get_po_stmt,
        (collection, p, o, limit)
    )

def get_spo(self, collection, s, p, o, limit=10):
    # Route to triples_collection table for exact SPO lookup
    return self.session.execute(
        self.get_spo_stmt,
        (collection, s, p, o, limit)
    )
```

#### Lógica de Exclusão de Coleções
```python
def delete_collection(self, collection):
    # Step 1: Read all triples from collection table
    rows = self.session.execute(
        f"SELECT s, p, o FROM {self.collection_table} WHERE collection = %s",
        (collection,)
    )

    # Step 2: Batch delete from all 4 tables
    batch = BatchStatement()
    count = 0

    for row in rows:
        s, p, o = row.s, row.p, row.o

        # Delete using full partition keys for each table
        batch.add(SimpleStatement(
            f"DELETE FROM {self.subject_table} WHERE collection = ? AND s = ? AND p = ? AND o = ?"
        ), (collection, s, p, o))

        batch.add(SimpleStatement(
            f"DELETE FROM {self.po_table} WHERE collection = ? AND p = ? AND o = ? AND s = ?"
        ), (collection, p, o, s))

        batch.add(SimpleStatement(
            f"DELETE FROM {self.object_table} WHERE collection = ? AND o = ? AND s = ? AND p = ?"
        ), (collection, o, s, p))

        batch.add(SimpleStatement(
            f"DELETE FROM {self.collection_table} WHERE collection = ? AND s = ? AND p = ? AND o = ?"
        ), (collection, s, p, o))

        count += 1

        # Execute every 100 triples to avoid oversized batches
        if count % 100 == 0:
            self.session.execute(batch)
            batch = BatchStatement()

    # Execute remaining deletions
    if count % 100 != 0:
        self.session.execute(batch)

    logger.info(f"Deleted {count} triples from collection {collection}")
```

#### Otimização de Instruções Preparadas
```python
def prepare_statements(self):
    # Cache prepared statements for better performance
    self.insert_subject_stmt = self.session.prepare(
        f"INSERT INTO {self.subject_table} (collection, s, p, o) VALUES (?, ?, ?, ?)"
    )
    self.insert_po_stmt = self.session.prepare(
        f"INSERT INTO {self.po_table} (collection, p, o, s) VALUES (?, ?, ?, ?)"
    )
    self.insert_object_stmt = self.session.prepare(
        f"INSERT INTO {self.object_table} (collection, o, s, p) VALUES (?, ?, ?, ?)"
    )
    self.insert_collection_stmt = self.session.prepare(
        f"INSERT INTO {self.collection_table} (collection, s, p, o) VALUES (?, ?, ?, ?)"
    )
    # ... query statements
```

## Estratégia de Migração

### Abordagem de Migração de Dados

#### Opção 1: Implantação Blue-Green (Recomendada)
1. **Implantar o novo esquema junto com o existente** - Use nomes de tabelas diferentes temporariamente
2. **Período de escrita dupla** - Escrever tanto no esquema antigo quanto no novo durante a transição
3. **Migração em segundo plano** - Copiar dados existentes para novas tabelas
4. **Alternar leituras** - Direcionar consultas para novas tabelas assim que os dados forem migrados
5. **Remover tabelas antigas** - Após o período de verificação

#### Opção 2: Migração no Local
1. **Adição de esquema** - Criar novas tabelas no keyspace existente
2. **Script de migração de dados** - Copiar em lote da tabela antiga para as novas tabelas
3. **Atualização do aplicativo** - Implantar novo código após a conclusão da migração
4. **Limpeza da tabela antiga** - Remover a tabela antiga e os índices

### Compatibilidade com Versões Anteriores

#### Estratégia de Implantação
```python
# Environment variable to control table usage during migration
USE_LEGACY_TABLES = os.getenv('CASSANDRA_USE_LEGACY', 'false').lower() == 'true'

class KnowledgeGraph:
    def __init__(self, ...):
        if USE_LEGACY_TABLES:
            self.init_legacy_schema()
        else:
            self.init_optimized_schema()
```

#### Script de Migração
```python
def migrate_data():
    # Read from old table
    old_triples = session.execute("SELECT collection, s, p, o FROM triples")

    # Batch write to new tables
    for batch in batched(old_triples, 100):
        batch_stmt = BatchStatement()
        for row in batch:
            # Add to all three new tables
            batch_stmt.add(insert_subject_stmt, row)
            batch_stmt.add(insert_po_stmt, (row.collection, row.p, row.o, row.s))
            batch_stmt.add(insert_object_stmt, (row.collection, row.o, row.s, row.p))
        session.execute(batch_stmt)
```

### Estratégia de Validação

#### Verificações de Consistência de Dados
```python
def validate_migration():
    # Count total records in old vs new tables
    old_count = session.execute("SELECT COUNT(*) FROM triples WHERE collection = ?", (collection,))
    new_count = session.execute("SELECT COUNT(*) FROM triples_by_subject WHERE collection = ?", (collection,))

    assert old_count == new_count, f"Record count mismatch: {old_count} vs {new_count}"

    # Spot check random samples
    sample_queries = generate_test_queries()
    for query in sample_queries:
        old_result = execute_legacy_query(query)
        new_result = execute_optimized_query(query)
        assert old_result == new_result, f"Query results differ for {query}"
```

## Estratégia de Testes

### Testes de Desempenho

#### Cenários de Benchmark
1. **Comparação de Desempenho de Consultas**
   Métricas de desempenho antes/depois para todos os 8 tipos de consulta
   Foco na melhoria de desempenho de `get_po` (eliminar `ALLOW FILTERING`)
   Medir a latência da consulta sob vários tamanhos de dados

2. **Testes de Carga**
   Execução de consultas concorrentes
   Taxa de transferência de escrita com operações em lote
   Utilização de memória e CPU

3. **Testes de Escalabilidade**
   Desempenho com tamanhos de coleção crescentes
   Distribuição de consultas em várias coleções
   Utilização de nós do cluster

#### Conjuntos de Dados de Teste
**Pequeno:** 10K triplas por coleção
**Médio:** 100K triplas por coleção
**Grande:** 1M+ triplas por coleção
**Múltiplas coleções:** Testar a distribuição de partições

### Testes Funcionais

#### Atualizações de Testes Unitários
```python
# Example test structure for new implementation
class TestCassandraKGPerformance:
    def test_get_po_no_allow_filtering(self):
        # Verify get_po queries don't use ALLOW FILTERING
        with patch('cassandra.cluster.Session.execute') as mock_execute:
            kg.get_po('test_collection', 'predicate', 'object')
            executed_query = mock_execute.call_args[0][0]
            assert 'ALLOW FILTERING' not in executed_query

    def test_multi_table_consistency(self):
        # Verify all tables stay in sync
        kg.insert('test', 's1', 'p1', 'o1')

        # Check all tables contain the triple
        assert_triple_exists('triples_by_subject', 'test', 's1', 'p1', 'o1')
        assert_triple_exists('triples_by_po', 'test', 'p1', 'o1', 's1')
        assert_triple_exists('triples_by_object', 'test', 'o1', 's1', 'p1')
```

#### Atualizações do Teste de Integração
```python
class TestCassandraIntegration:
    def test_query_performance_regression(self):
        # Ensure new implementation is faster than old
        old_time = benchmark_legacy_get_po()
        new_time = benchmark_optimized_get_po()
        assert new_time < old_time * 0.5  # At least 50% improvement

    def test_end_to_end_workflow(self):
        # Test complete write -> query -> delete cycle
        # Verify no performance degradation in integration
```

### Plano de Reversão

#### Estratégia de Reversão Rápida
1. **Alternância de variáveis de ambiente** - Retorne imediatamente para as tabelas legadas.
2. **Mantenha as tabelas legadas** - Não as exclua até que o desempenho seja comprovado.
3. **Alertas de monitoramento** - Disparos de reversão automatizados com base em taxas de erro/latência.

#### Validação da Reversão
```python
def rollback_to_legacy():
    # Set environment variable
    os.environ['CASSANDRA_USE_LEGACY'] = 'true'

    # Restart services to pick up change
    restart_cassandra_services()

    # Validate functionality
    run_smoke_tests()
```

## Riscos e Considerações

### Riscos de Desempenho
**Aumento da latência de escrita** - 4 operações de escrita por inserção (33% a mais do que a abordagem de 3 tabelas)
**Sobrecarga de armazenamento** - 4x o requisito de armazenamento (33% a mais do que a abordagem de 3 tabelas)
**Falhas de escrita em lote** - Necessidade de tratamento adequado de erros
**Complexidade da exclusão** - A exclusão da coleção requer um loop de leitura e exclusão

### Riscos Operacionais
**Complexidade da migração** - Migração de dados para grandes conjuntos de dados
**Desafios de consistência** - Garantir que todas as tabelas permaneçam sincronizadas
**Lacunas de monitoramento** - Necessidade de novas métricas para operações de várias tabelas

### Estratégias de Mitigação
1. **Implantação gradual** - Começar com pequenas coleções
2. **Monitoramento abrangente** - Rastrear todas as métricas de desempenho
3. **Validação automatizada** - Verificação contínua de consistência
4. **Capacidade de reversão rápida** - Seleção de tabela baseada no ambiente

## Critérios de Sucesso

### Melhorias de Desempenho
[ ] **Eliminar ALLOW FILTERING** - as consultas get_po e get_os são executadas sem filtragem
[ ] **Redução da latência da consulta** - melhoria de 50% ou mais nos tempos de resposta da consulta
[ ] **Melhor distribuição de carga** - Sem partições quentes, distribuição uniforme entre os nós do cluster
[ ] **Desempenho escalável** - Tempo de consulta proporcional ao tamanho do resultado, não ao volume total de dados

### Requisitos Funcionais
[ ] **Compatibilidade da API** - Todo o código existente continua a funcionar sem alterações
[ ] **Consistência de dados** - As três tabelas permanecem sincronizadas
[ ] **Nenhuma perda de dados** - A migração preserva todas as triplas existentes
[ ] **Compatibilidade com versões anteriores** - Capacidade de reverter para o esquema legado

### Requisitos Operacionais
[ ] **Migração segura** - Implantação blue-green com capacidade de reversão
[ ] **Cobertura de monitoramento** - Métricas abrangentes para operações de várias tabelas
[ ] **Cobertura de teste** - Todos os padrões de consulta testados com benchmarks de desempenho
[ ] **Documentação** - Procedimentos de implantação e operação atualizados

## Cronograma

### Fase 1: Implementação
[ ] Reescrever `cassandra_kg.py` com o esquema de várias tabelas
[ ] Implementar operações de escrita em lote
[ ] Adicionar otimização de declaração preparada
[ ] Atualizar testes unitários

### Fase 2: Testes de Integração
[ ] Atualizar testes de integração
[ ] Benchmarking de desempenho
[ ] Teste de carga com volumes de dados realistas
[ ] Scripts de validação para consistência de dados

### Fase 3: Planejamento da Migração
[ ] Scripts de implantação blue-green
[ ] Ferramentas de migração de dados
[ ] Atualizações do painel de monitoramento
[ ] Procedimentos de reversão

### Fase 4: Implantação em Produção
[ ] Implantação gradual em produção
[ ] Monitoramento e validação de desempenho
[ ] Limpeza de tabelas legadas
[ ] Atualizações de documentação

## Conclusão

Esta estratégia de desnormalização multi-tabela aborda diretamente os dois gargalos de desempenho críticos:

1. **Elimina o ALLOW FILTERING caro** fornecendo estruturas de tabela ideais para cada padrão de consulta
2. **Melhora a eficácia do agrupamento** por meio de chaves de partição compostas que distribuem a carga adequadamente

A abordagem aproveita os pontos fortes do Cassandra, mantendo a compatibilidade total da API, garantindo que o código existente se beneficie automaticamente das melhorias de desempenho.
