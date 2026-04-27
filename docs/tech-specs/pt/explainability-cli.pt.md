---
layout: default
title: "Especificação Técnica da Interface de Linha de Comando (CLI) para Explicabilidade"
parent: "Portuguese (Beta)"
---

# Especificação Técnica da Interface de Linha de Comando (CLI) para Explicabilidade

> **Beta Translation:** This document was translated via Machine Learning and as such may not be 100% accurate. All non-English languages are currently classified as Beta.

## Status

Rascunho

## Visão Geral

Esta especificação descreve ferramentas de linha de comando para depurar e explorar dados de explicabilidade no TrustGraph. Essas ferramentas permitem que os usuários rastreiem como as respostas foram derivadas e depurem a cadeia de origem desde as arestas até os documentos de origem.

Três ferramentas de linha de comando:

1. **`tg-show-document-hierarchy`** - Mostrar a hierarquia de documento → página → trecho → aresta
2. **`tg-list-explain-traces`** - Listar todas as sessões GraphRAG com perguntas
3. **`tg-show-explain-trace`** - Mostrar o rastreamento completo de explicabilidade para uma sessão

## Objetivos

**Depuração**: Permitir que os desenvolvedores inspecionem os resultados do processamento de documentos
**Auditabilidade**: Rastrear qualquer fato extraído de volta ao seu documento de origem
**Transparência**: Mostrar exatamente como o GraphRAG derivou uma resposta
**Usabilidade**: Interface de linha de comando simples com configurações padrão sensatas

## Contexto

O TrustGraph possui dois sistemas de rastreabilidade:

1. **Rastreabilidade em tempo de extração** (veja `extraction-time-provenance.md`): Registra os relacionamentos de documento → página → trecho → aresta durante a ingestão. Armazenado em um grafo chamado `urn:graph:source` usando `prov:wasDerivedFrom`.

2. **Explicabilidade em tempo de consulta** (veja `query-time-explainability.md`): Registra a cadeia de pergunta → exploração → foco → síntese durante as consultas GraphRAG. Armazenado em um grafo chamado `urn:graph:retrieval`.

Limitações atuais:
Não há uma maneira fácil de visualizar a hierarquia de documentos após o processamento
É necessário consultar manualmente as triplas para ver os dados de explicabilidade
Não há uma visão consolidada de uma sessão GraphRAG

## Design Técnico

### Ferramenta 1: tg-show-document-hierarchy

**Propósito**: Dado um ID de documento, percorrer e exibir todas as entidades derivadas.

**Uso**:
```bash
tg-show-document-hierarchy "urn:trustgraph:doc:abc123"
tg-show-document-hierarchy --show-content --max-content 500 "urn:trustgraph:doc:abc123"
```

**Argumentos**:
| Arg | Descrição |
|-----|-------------|
| `document_id` | URI do documento (posicional) |
| `-u/--api-url` | URL do gateway (padrão: `$TRUSTGRAPH_URL`) |
| `-t/--token` | Token de autenticação (padrão: `$TRUSTGRAPH_TOKEN`) |
| `-U/--user` | ID do usuário (padrão: `trustgraph`) |
| `-C/--collection` | Coleção (padrão: `default`) |
| `--show-content` | Incluir conteúdo do blob/documento |
| `--max-content` | Máximo de caracteres por blob (padrão: 200) |
| `--format` | Saída: `tree` (padrão), `json` |

**Implementação**:
1. Consultar triplas: `?child prov:wasDerivedFrom <document_id>` em `urn:graph:source`
2. Consultar recursivamente os filhos de cada resultado
3. Construir estrutura de árvore: Documento → Páginas → Blocos
4. Se `--show-content`, buscar conteúdo da API do bibliotecário
5. Exibir como árvore indentada ou JSON

**Exemplo de Saída**:
```
Document: urn:trustgraph:doc:abc123
  Title: "Sample PDF"
  Type: application/pdf

  └── Page 1: urn:trustgraph:doc:abc123/p1
      ├── Chunk 0: urn:trustgraph:doc:abc123/p1/c0
      │   Content: "The quick brown fox..." [truncated]
      └── Chunk 1: urn:trustgraph:doc:abc123/p1/c1
          Content: "Machine learning is..." [truncated]
```

### Ferramenta 2: tg-list-explain-traces

**Propósito**: Listar todas as sessões (perguntas) do GraphRAG em uma coleção.

**Uso**:
```bash
tg-list-explain-traces
tg-list-explain-traces --limit 20 --format json
```

**Argumentos**:
| Arg | Descrição |
|-----|-------------|
| `-u/--api-url` | URL do gateway |
| `-t/--token` | Token de autenticação |
| `-U/--user` | ID do usuário |
| `-C/--collection` | Coleção |
| `--limit` | Resultados máximos (padrão: 50) |
| `--format` | Saída: `table` (padrão), `json` |

**Implementação**:
1. Consulta: `?session tg:query ?text` em `urn:graph:retrieval`
2. Consulta de carimbos de data/hora: `?session prov:startedAtTime ?time`
3. Exibir como tabela

**Exemplo de Saída**:
```
Session ID                                    | Question                        | Time
----------------------------------------------|--------------------------------|---------------------
urn:trustgraph:question:abc123                | What was the War on Terror?    | 2024-01-15 10:30:00
urn:trustgraph:question:def456                | Who founded OpenAI?            | 2024-01-15 09:15:00
```

### Ferramenta 3: tg-show-explain-trace

**Propósito**: Mostrar a cascata completa de explicabilidade para uma sessão GraphRAG.

**Uso**:
```bash
tg-show-explain-trace "urn:trustgraph:question:abc123"
tg-show-explain-trace --max-answer 1000 --show-provenance "urn:trustgraph:question:abc123"
```

**Argumentos**:
| Arg | Descrição |
|-----|-------------|
| `question_id` | URI da pergunta (posicional) |
| `-u/--api-url` | URL do gateway |
| `-t/--token` | Token de autenticação |
| `-U/--user` | ID do usuário |
| `-C/--collection` | Coleção |
| `--max-answer` | Número máximo de caracteres para a resposta (padrão: 500) |
| `--show-provenance` | Rastrear arestas para documentos de origem |
| `--format` | Saída: `text` (padrão), `json` |

**Implementação**:
1. Obter o texto da pergunta do predicado `tg:query`
2. Encontrar a exploração: `?exp prov:wasGeneratedBy <question_id>`
3. Encontrar o foco: `?focus prov:wasDerivedFrom <exploration_id>`
4. Obter as arestas selecionadas: `<focus_id> tg:selectedEdge ?edge`
5. Para cada aresta, obter `tg:edge` (tripla entre aspas) e `tg:reasoning`
6. Encontrar a síntese: `?synth prov:wasDerivedFrom <focus_id>`
7. Obter a resposta de `tg:document` através do bibliotecário
8. Se `--show-provenance`, rastrear as arestas para os documentos de origem

**Exemplo de Saída**:
```
=== GraphRAG Session: urn:trustgraph:question:abc123 ===

Question: What was the War on Terror?
Time: 2024-01-15 10:30:00

--- Exploration ---
Retrieved 50 edges from knowledge graph

--- Focus (Edge Selection) ---
Selected 12 edges:

  1. (War on Terror, definition, "A military campaign...")
     Reasoning: Directly defines the subject of the query
     Source: chunk → page 2 → "Beyond the Vigilant State"

  2. (Guantanamo Bay, part_of, War on Terror)
     Reasoning: Shows key component of the campaign

--- Synthesis ---
Answer:
  The War on Terror was a military campaign initiated...
  [truncated at 500 chars]
```

## Arquivos a Criar

| Arquivo | Propósito |
|------|---------|
| `trustgraph-cli/trustgraph/cli/show_document_hierarchy.py` | Ferramenta 1 |
| `trustgraph-cli/trustgraph/cli/list_explain_traces.py` | Ferramenta 2 |
| `trustgraph-cli/trustgraph/cli/show_explain_trace.py` | Ferramenta 3 |

## Arquivos a Modificar

| Arquivo | Alteração |
|------|--------|
| `trustgraph-cli/setup.py` | Adicionar entradas de console_scripts |

## Notas de Implementação

1. **Segurança do conteúdo binário**: Tente decodificar UTF-8; se falhar, mostre `[Binary: {size} bytes]`
2. **Truncamento**: Respeite `--max-content`/`--max-answer` com indicador `[truncated]`
3. **Triplas entre aspas**: Analise o formato RDF-star a partir do predicado `tg:edge`
4. **Padrões**: Siga os padrões de CLI existentes a partir de `query_graph.py`

## Considerações de Segurança

Todas as consultas respeitam os limites de usuário/coleção
Autenticação por token suportada via `--token` ou `$TRUSTGRAPH_TOKEN`

## Estratégia de Teste

Verificação manual com dados de amostra:
```bash
# Load a test document
tg-load-pdf -f test.pdf -c test-collection

# Verify hierarchy
tg-show-document-hierarchy "urn:trustgraph:doc:test"

# Run a GraphRAG query with explainability
tg-invoke-graph-rag --explainable -q "Test question"

# List and inspect traces
tg-list-explain-traces
tg-show-explain-trace "urn:trustgraph:question:xxx"
```

## Referências

Explicabilidade em tempo de consulta: `docs/tech-specs/query-time-explainability.md`
Proveniência em tempo de extração: `docs/tech-specs/extraction-time-provenance.md`
Exemplo de CLI existente: `trustgraph-cli/trustgraph/cli/invoke_graph_rag.py`
