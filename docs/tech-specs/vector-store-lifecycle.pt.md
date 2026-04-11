# Gerenciamento do Ciclo de Vida do Vector Store

## Visão Geral

Este documento descreve como o TrustGraph gerencia coleções de vector store em diferentes implementações de backend (Qdrant, Pinecone, Milvus). O design aborda o desafio de suportar embeddings com diferentes dimensões sem codificar valores de dimensão.

## Declaração do Problema

Os vector stores exigem que a dimensão do embedding seja especificada ao criar coleções/índices. No entanto:
Modelos de embedding diferentes produzem dimensões diferentes (por exemplo, 384, 768, 1536)
A dimensão não é conhecida até que o primeiro embedding seja gerado
Uma única coleção do TrustGraph pode receber embeddings de vários modelos
A codificação de uma dimensão (por exemplo, 384) causa falhas com outros tamanhos de embedding

## Princípios de Design

1. **Criação Preguiçosa (Lazy Creation)**: As coleções são criadas sob demanda durante a primeira escrita, e não durante as operações de gerenciamento de coleção.
2. **Nomeação Baseada em Dimensão**: Os nomes das coleções incluem a dimensão do embedding como um sufixo.
3. **Degradação Graciosa**: As consultas contra coleções inexistentes retornam resultados vazios, e não erros.
4. **Suporte a Múltiplas Dimensões**: Uma única coleção lógica pode ter várias coleções físicas (uma por dimensão).

## Arquitetura

### Convenção de Nomenclatura de Coleções

As coleções de vector store usam sufixos de dimensão para suportar vários tamanhos de embedding:

**Embeddings de Documentos:**
Qdrant: `d_{user}_{collection}_{dimension}`
Pinecone: `d-{user}-{collection}-{dimension}`
Milvus: `doc_{user}_{collection}_{dimension}`

**Embeddings de Grafos:**
Qdrant: `t_{user}_{collection}_{dimension}`
Pinecone: `t-{user}-{collection}-{dimension}`
Milvus: `entity_{user}_{collection}_{dimension}`

Exemplos:
`d_alice_papers_384` - Coleção de artigos da Alice com embeddings de 384 dimensões
`d_alice_papers_768` - Mesma coleção lógica com embeddings de 768 dimensões
`t_bob_knowledge_1536` - Grafo de conhecimento do Bob com embeddings de 1536 dimensões

### Fases do Ciclo de Vida

#### 1. Solicitação de Criação de Coleção

**Fluxo da Solicitação:**
```
User/System → Librarian → Storage Management Topic → Vector Stores
```

**Comportamento:**
O bibliotecário transmite solicitações `create-collection` para todos os backends de armazenamento.
Os processadores de armazenamento vetorial confirmam a solicitação, mas **não criam coleções físicas**.
A resposta é retornada imediatamente com sucesso.
A criação real da coleção é adiada até a primeira escrita.

**Justificativa:**
A dimensão é desconhecida no momento da criação.
Evita a criação de coleções com dimensões incorretas.
Simplifica a lógica de gerenciamento de coleções.

#### 2. Operações de Escrita (Criação Preguiçosa)

**Fluxo de Escrita:**
```
Data → Storage Processor → Check Collection → Create if Needed → Insert
```

**Comportamento:**
1. Extrair a dimensão do embedding do vetor: `dim = len(vector)`
2. Construir o nome da coleção com o sufixo da dimensão
3. Verificar se a coleção existe com essa dimensão específica
4. Se não existir:
   Criar a coleção com a dimensão correta
   Registrar: `"Lazily creating collection {name} with dimension {dim}"`
5. Inserir o embedding na coleção específica da dimensão

**Cenário de Exemplo:**
```
1. User creates collection "papers"
   → No physical collections created yet

2. First document with 384-dim embedding arrives
   → Creates d_user_papers_384
   → Inserts data

3. Second document with 768-dim embedding arrives
   → Creates d_user_papers_768
   → Inserts data

Result: Two physical collections for one logical collection
```

#### 3. Operações de Consulta

**Fluxo de Consulta:**
```
Query Vector → Determine Dimension → Check Collection → Search or Return Empty
```

**Comportamento:**
1. Extrair a dimensão do vetor de consulta: `dim = len(vector)`
2. Construir o nome da coleção com o sufixo da dimensão
3. Verificar se a coleção existe
4. Se existir:
   Realizar uma busca de similaridade
   Retornar os resultados
5. Se não existir:
   Registrar: `"Collection {name} does not exist, returning empty results"`
   Retornar uma lista vazia (nenhum erro é gerado)

**Múltiplas Dimensões na Mesma Consulta:**
Se a consulta contiver vetores de dimensões diferentes
Cada dimensão consulta sua coleção correspondente
Os resultados são agregados
As coleções ausentes são ignoradas (não são tratadas como erros)

**Justificativa:**
Consultar uma coleção vazia é um caso de uso válido
Retornar resultados vazios é semanticamente correto
Evita erros durante a inicialização do sistema ou antes da ingestão de dados

#### 4. Exclusão de Coleção

**Fluxo de Exclusão:**
```
Delete Request → List All Collections → Filter by Prefix → Delete All Matches
```

**Comportamento:**
1. Construir o padrão de prefixo: `d_{user}_{collection}_` (observe o sublinhado no final)
2. Listar todas as coleções no armazenamento vetorial
3. Filtrar as coleções que correspondem ao prefixo
4. Excluir todas as coleções correspondentes
5. Registrar cada exclusão: `"Deleted collection {name}"`
6. Registro resumido: `"Deleted {count} collection(s) for {user}/{collection}"`

**Exemplo:**
```
Collections in store:
- d_alice_papers_384
- d_alice_papers_768
- d_alice_reports_384
- d_bob_papers_384

Delete "papers" for alice:
→ Deletes: d_alice_papers_384, d_alice_papers_768
→ Keeps: d_alice_reports_384, d_bob_papers_384
```

**Justificativa:**
Garante a limpeza completa de todas as variantes de dimensão.
A correspondência de padrões evita a exclusão acidental de coleções não relacionadas.
Operação atômica da perspectiva do usuário (todas as dimensões são excluídas juntas).

## Características Comportamentais

### Operações Normais

**Criação de Coleção:**
✓ Retorna sucesso imediatamente.
✓ Nenhum armazenamento físico é alocado.
✓ Operação rápida (sem E/S de backend).

**Primeira Escrita:**
✓ Cria a coleção com a dimensão correta.
✓ Ligeiramente mais lenta devido à sobrecarga da criação da coleção.
✓ Escritas subsequentes na mesma dimensão são rápidas.

**Consultas Antes de Qualquer Escrita:**
✓ Retorna resultados vazios.
✓ Nenhum erro ou exceção.
✓ O sistema permanece estável.

**Escritas de Dimensões Mistas:**
✓ Cria automaticamente coleções separadas por dimensão.
✓ Cada dimensão é isolada em sua própria coleção.
✓ Nenhum conflito de dimensão ou erro de esquema.

**Exclusão de Coleção:**
✓ Remove todas as variantes de dimensão.
✓ Limpeza completa.
✓ Nenhuma coleção órfã.

### Casos Limite

**Múltiplos Modelos de Incorporação:**
```
Scenario: User switches from model A (384-dim) to model B (768-dim)
Behavior:
- Both dimensions coexist in separate collections
- Old data (384-dim) remains queryable with 384-dim vectors
- New data (768-dim) queryable with 768-dim vectors
- Cross-dimension queries return results only for matching dimension
```

**Primeiras Escritas Concorrentes:**
```
Scenario: Multiple processes write to same collection simultaneously
Behavior:
- Each process checks for existence before creating
- Most vector stores handle concurrent creation gracefully
- If race condition occurs, second create is typically idempotent
- Final state: Collection exists and both writes succeed
```

**Migração de Dimensões:**
```
Scenario: User wants to migrate from 384-dim to 768-dim embeddings
Behavior:
- No automatic migration
- Old collection (384-dim) persists
- New collection (768-dim) created on first new write
- Both dimensions remain accessible
- Manual deletion of old dimension collections possible
```

**Consultas de Coleção Vazia:**
```
Scenario: Query a collection that has never received data
Behavior:
- Collection doesn't exist (never created)
- Query returns empty list
- No error state
- System logs: "Collection does not exist, returning empty results"
```

## Notas de Implementação

### Especificidades do Backend de Armazenamento

**Qdrant:**
Usa `collection_exists()` para verificações de existência
Usa `get_collections()` para listagem durante a exclusão
A criação de coleções requer `VectorParams(size=dim, distance=Distance.COSINE)`

**Pinecone:**
Usa `has_index()` para verificações de existência
Usa `list_indexes()` para listagem durante a exclusão
A criação de índices requer esperar pelo status "ready"
Especificação serverless configurada com cloud/região

**Milvus:**
Classes diretas (`DocVectors`, `EntityVectors`) gerenciam o ciclo de vida
Cache interno `self.collections[(dim, user, collection)]` para desempenho
Nomes de coleções são sanitizados (apenas alfanumérico + underscore)
Suporta esquema com IDs de incremento automático

### Considerações de Desempenho

**Latência da Primeira Gravação:**
Overhead adicional devido à criação da coleção
Qdrant: ~100-500ms
Pinecone: ~10-30 segundos (provisionamento serverless)
Milvus: ~500-2000ms (inclui indexação)

**Desempenho da Consulta:**
A verificação de existência adiciona um overhead mínimo (~1-10ms)
Nenhum impacto no desempenho depois que a coleção existe
Cada coleção de dimensões é otimizada independentemente

**Overhead de Armazenamento:**
Metadados mínimos por coleção
O principal overhead é por armazenamento de dimensão
Compromisso: Espaço de armazenamento vs. flexibilidade de dimensão

## Considerações Futuras

**Consolidação Automática de Dimensões:**
Poderia adicionar um processo em segundo plano para identificar e mesclar variantes de dimensões não utilizadas
Requereria re-embedding ou redução de dimensão

**Descoberta de Dimensões:**
Poderia expor uma API para listar todas as dimensões em uso para uma coleção
Útil para administração e monitoramento

**Preferência de Dimensão Padrão:**
Poderia rastrear a "dimensão primária" por coleção
Usar para consultas quando o contexto da dimensão não está disponível

**Quotas de Armazenamento:**
Pode ser necessário limites de dimensão por coleção
Prevenir a proliferação de variantes de dimensão

## Notas de Migração

**Do Sistema de Sufixo de Pré-Dimensão:**
Coleções antigas: `d_{user}_{collection}` (sem sufixo de dimensão)
Coleções novas: `d_{user}_{collection}_{dim}` (com sufixo de dimensão)
Nenhuma migração automática - coleções antigas permanecem acessíveis
Considere um script de migração manual, se necessário
Pode executar ambos os esquemas de nomenclatura simultaneamente

## Referências

Gerenciamento de Coleções: `docs/tech-specs/collection-management.md`
Esquema de Armazenamento: `trustgraph-base/trustgraph/schema/services/storage.py`
Serviço Librarian: `trustgraph-flow/trustgraph/librarian/service.py`
