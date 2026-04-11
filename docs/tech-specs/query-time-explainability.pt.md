# Explicabilidade em Tempo de Consulta

## Status

Implementado

## Visão Geral

Esta especificação descreve como o GraphRAG registra e comunica dados de explicabilidade durante a execução da consulta. O objetivo é a rastreabilidade completa: desde a resposta final, passando pelas arestas selecionadas, até aos documentos de origem.

A explicabilidade em tempo de consulta captura o que o pipeline do GraphRAG fez durante o raciocínio. Isso se conecta à rastreabilidade em tempo de extração, que registra a origem dos fatos do grafo de conhecimento.

## Terminologia

| Termo | Definição |
|------|------------|
| **Explicabilidade** | O registro de como um resultado foi derivado |
| **Sessão** | Uma única execução de consulta do GraphRAG |
| **Seleção de Arestas** | Seleção de arestas relevantes impulsionada por LLM, com raciocínio |
| **Cadeia de Rastreabilidade** | Caminho de aresta → trecho → página → documento |

## Arquitetura

### Fluxo de Explicabilidade

```
GraphRAG Query
    │
    ├─► Session Activity
    │       └─► Query text, timestamp
    │
    ├─► Retrieval Entity
    │       └─► All edges retrieved from subgraph
    │
    ├─► Selection Entity
    │       └─► Selected edges with LLM reasoning
    │           └─► Each edge links to extraction provenance
    │
    └─► Answer Entity
            └─► Reference to synthesized response (in librarian)
```

### Pipeline de GraphRAG em Duas Etapas

1. **Seleção de Arestas**: O LLM seleciona as arestas relevantes do subgrafo, fornecendo a justificativa para cada uma.
2. **Síntese**: O LLM gera a resposta a partir das arestas selecionadas.

Essa separação permite a explicabilidade - sabemos exatamente quais arestas contribuíram.

### Armazenamento

Triplas de explicabilidade armazenadas em uma coleção configurável (padrão: `explainability`).
Utiliza a ontologia PROV-O para relações de procedência.
Reificação RDF-star para referências de arestas.
O conteúdo da resposta é armazenado no serviço de bibliotecário (não inline - muito grande).

### Streaming em Tempo Real

Os eventos de explicabilidade são transmitidos ao cliente enquanto a consulta é executada:

1. Sessão criada → evento emitido.
2. Arestas recuperadas → evento emitido.
3. Arestas selecionadas com justificativa → evento emitido.
4. Resposta sintetizada → evento emitido.

O cliente recebe `explain_id` e `explain_collection` para buscar detalhes completos.

## Estrutura de URI

Todos os URIs usam o namespace `urn:trustgraph:` com UUIDs:

| Entidade | Padrão de URI |
|--------|-------------|
| Sessão | `urn:trustgraph:session:{uuid}` |
| Recuperação | `urn:trustgraph:prov:retrieval:{uuid}` |
| Seleção | `urn:trustgraph:prov:selection:{uuid}` |
| Resposta | `urn:trustgraph:prov:answer:{uuid}` |
| Seleção de Aresta | `urn:trustgraph:prov:edge:{uuid}:{index}` |

## Modelo RDF (PROV-O)

### Atividade da Sessão

```turtle
<session-uri> a prov:Activity ;
    rdfs:label "GraphRAG query session" ;
    prov:startedAtTime "2024-01-15T10:30:00Z" ;
    tg:query "What was the War on Terror?" .
```

### Entidade de Recuperação

```turtle
<retrieval-uri> a prov:Entity ;
    rdfs:label "Retrieved edges" ;
    prov:wasGeneratedBy <session-uri> ;
    tg:edgeCount 50 .
```

### Entidade de Seleção

```turtle
<selection-uri> a prov:Entity ;
    rdfs:label "Selected edges" ;
    prov:wasDerivedFrom <retrieval-uri> ;
    tg:selectedEdge <edge-sel-0> ;
    tg:selectedEdge <edge-sel-1> .

<edge-sel-0> tg:edge << <s> <p> <o> >> ;
    tg:reasoning "This edge establishes the key relationship..." .
```

### Entidade de Resposta

```turtle
<answer-uri> a prov:Entity ;
    rdfs:label "GraphRAG answer" ;
    prov:wasDerivedFrom <selection-uri> ;
    tg:document <urn:trustgraph:answer:{uuid}> .
```

A `tg:document` referencia a resposta armazenada no serviço de bibliotecário.

## Constantes do Namespace

Definido em `trustgraph-base/trustgraph/provenance/namespaces.py`:

| Constante | URI |
|----------|-----|
| `TG_QUERY` | `https://trustgraph.ai/ns/query` |
| `TG_EDGE_COUNT` | `https://trustgraph.ai/ns/edgeCount` |
| `TG_SELECTED_EDGE` | `https://trustgraph.ai/ns/selectedEdge` |
| `TG_EDGE` | `https://trustgraph.ai/ns/edge` |
| `TG_REASONING` | `https://trustgraph.ai/ns/reasoning` |
| `TG_CONTENT` | `https://trustgraph.ai/ns/content` |
| `TG_DOCUMENT` | `https://trustgraph.ai/ns/document` |

## Esquema GraphRagResponse

```python
@dataclass
class GraphRagResponse:
    error: Error | None = None
    response: str = ""
    end_of_stream: bool = False
    explain_id: str | None = None
    explain_collection: str | None = None
    message_type: str = ""  # "chunk" or "explain"
    end_of_session: bool = False
```

### Tipos de Mensagem

| message_type | Propósito |
|--------------|---------|
| `chunk` | Texto de resposta (em fluxo ou final) |
| `explain` | Evento de explicabilidade com referência IRI |

### Ciclo de Vida da Sessão

1. Múltiplas mensagens `explain` (sessão, recuperação, seleção, resposta)
2. Múltiplas mensagens `chunk` (resposta em fluxo)
3. Mensagem `chunk` final com `end_of_session=True`

## Formato de Seleção de Arestas

O LLM retorna JSONL com as arestas selecionadas:

```jsonl
{"id": "edge-hash-1", "reasoning": "This edge shows the key relationship..."}
{"id": "edge-hash-2", "reasoning": "Provides supporting evidence..."}
```

O `id` é um hash de `(labeled_s, labeled_p, labeled_o)` calculado por `edge_id()`.

## Preservação de URIs

### O Problema

O GraphRAG exibe rótulos legíveis para humanos para o LLM, mas a explicabilidade precisa de URIs originais para rastreamento de origem.

### Solução

`get_labelgraph()` retorna ambos:
`labeled_edges`: Lista de `(label_s, label_p, label_o)` para o LLM
`uri_map`: Dicionário mapeando `edge_id(labels)` → `(uri_s, uri_p, uri_o)`

Ao armazenar dados de explicabilidade, os URIs de `uri_map` são usados.

## Rastreamento de Origem

### Do Borda à Fonte

As arestas selecionadas podem ser rastreadas de volta aos documentos de origem:

1. Consulta para o subgrafo contendo: `?subgraph tg:contains <<s p o>>`
2. Siga a cadeia `prov:wasDerivedFrom` até o documento raiz
3. Cada etapa na cadeia: chunk → página → documento

### Suporte de Triplas Citadas do Cassandra

O serviço de consulta do Cassandra suporta a correspondência de triplas citadas:

```python
# In get_term_value():
elif term.type == TRIPLE:
    return serialize_triple(term.triple)
```

Isso permite consultas como:
```
?subgraph tg:contains <<http://example.org/s http://example.org/p "value">>
```

## Uso da Interface de Linha de Comando (CLI)

```bash
tg-invoke-graph-rag --explainable -q "What was the War on Terror?"
```

### Formato de Saída

```
[session] urn:trustgraph:session:abc123

[retrieval] urn:trustgraph:prov:retrieval:abc123

[selection] urn:trustgraph:prov:selection:abc123
    Selected 12 edge(s)
      Edge: (Guantanamo, definition, A detention facility...)
        Reason: Directly connects Guantanamo to the War on Terror
        Source: Chunk 1 → Page 2 → Beyond the Vigilant State

[answer] urn:trustgraph:prov:answer:abc123

Based on the provided knowledge statements...
```

### Recursos

Eventos de explicabilidade em tempo real durante a consulta.
Resolução de rótulos para componentes de borda via `rdfs:label`.
Rastreamento da cadeia de origem via `prov:wasDerivedFrom`.
Cache de rótulos para evitar consultas repetidas.

## Arquivos Implementados

| Arquivo | Propósito |
|------|---------|
| `trustgraph-base/trustgraph/provenance/uris.py` | Geradores de URI |
| `trustgraph-base/trustgraph/provenance/namespaces.py` | Constantes de namespace RDF |
| `trustgraph-base/trustgraph/provenance/triples.py` | Construtores de triplas |
| `trustgraph-base/trustgraph/schema/services/retrieval.py` | Esquema GraphRagResponse |
| `trustgraph-flow/trustgraph/retrieval/graph_rag/graph_rag.py` | Núcleo GraphRAG com preservação de URI |
| `trustgraph-flow/trustgraph/retrieval/graph_rag/rag.py` | Serviço com integração de bibliotecário |
| `trustgraph-flow/trustgraph/query/triples/cassandra/service.py` | Suporte para consultas de triplas entre aspas |
| `trustgraph-cli/trustgraph/cli/invoke_graph_rag.py` | CLI com exibição de explicabilidade |

## Referências

PROV-O (Ontologia de Proveniência W3C): https://www.w3.org/TR/prov-o/
RDF-star: https://w3c.github.io/rdf-star/
Proveniência no momento da extração: `docs/tech-specs/extraction-time-provenance.md`
