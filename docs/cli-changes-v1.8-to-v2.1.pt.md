# Alterações na CLI: da v1.8 para v2.1

## Resumo

A CLI (`trustgraph-cli`) possui adições significativas focadas em três temas:
**explicabilidade/proveniência**, **acesso a embeddings** e **consulta de grafos**.
Duas ferramentas legadas foram removidas, uma foi renomeada e várias ferramentas existentes
adquiriram novas funcionalidades.

--

## Novas Ferramentas da CLI

### Explicabilidade e Proveniência

| Comando | Descrição |
|---------|-------------|
| `tg-list-explain-traces` | Lista todas as sessões de explicabilidade (GraphRAG e Agent) em uma coleção, mostrando IDs de sessão, tipo, texto da pergunta e carimbos de data/hora. |
| `tg-show-explain-trace` | Exibe o rastreamento completo de explicabilidade para uma sessão. Para GraphRAG: Estágios de Pergunta, Exploração, Foco, Síntese. Para Agent: Sessão, Iterações (pensamento/ação/observação), Resposta Final. Detecta automaticamente o tipo de rastreamento. Suporta `--show-provenance` para rastrear arestas de volta para documentos de origem. |
| `tg-show-extraction-provenance` | Dado um ID de documento, percorre a cadeia de proveniência: Documento -> Páginas -> Trechos -> Arestas, usando relacionamentos `prov:wasDerivedFrom`. Suporta opções `--show-content` e `--max-content`. |

### Embeddings

| Comando | Descrição |
|---------|-------------|
| `tg-invoke-embeddings` | Converte texto em um embedding vetorial por meio do serviço de embeddings. Aceita uma ou mais entradas de texto, retorna vetores como listas de floats. |
| `tg-invoke-graph-embeddings` | Consulta entidades de grafo por similaridade de texto usando embeddings vetoriais. Retorna entidades correspondentes com pontuações de similaridade. |
| `tg-invoke-document-embeddings` | Consulta trechos de documentos por similaridade de texto usando embeddings vetoriais. Retorna IDs de trechos correspondentes com pontuações de similaridade. |
| `tg-invoke-row-embeddings` | Consulta linhas de dados estruturados por similaridade de texto em campos indexados. Retorna linhas correspondentes com valores de índice e pontuações. Requer `--schema-name` e suporta `--index-name`. |

### Consulta de Grafos

| Comando | Descrição |
|---------|-------------|
| `tg-query-graph` | Consulta de grafo baseada em padrões. Diferentemente de `tg-show-graph` (que despeja tudo), isso permite consultas seletivas por qualquer combinação de sujeito, predicado, objeto e grafo. Detecta automaticamente os tipos de valor: IRIs (`http://...`, `urn:...`, `<...>`), triplas entre aspas (`<<s p o>>`) e literais. |
| `tg-get-document-content` | Recupera o conteúdo do documento da biblioteca por ID do documento. Pode ser direcionado para um arquivo ou stdout, lida com conteúdo de texto e binário. |

--

## Ferramentas da CLI Removidas

| Comando | Notas |
|---------|-------|
| `tg-load-pdf` | Removido. O carregamento de documentos é agora tratado por meio do pipeline de biblioteca/processamento. |
| `tg-load-text` | Removido. O carregamento de documentos é agora tratado por meio do pipeline de biblioteca/processamento. |

--

## Ferramentas da CLI Renomeadas

| Nome Antigo | Novo Nome | Notas |
|----------|----------|-------|
| `tg-invoke-objects-query` | `tg-invoke-rows-query` | Reflete a alteração de terminologia de "objetos" para "linhas" para dados estruturados. |

--

## Mudanças Significativas em Ferramentas Existentes

### `tg-invoke-graph-rag`

**Suporte para explicabilidade**: Agora suporta um pipeline de explicabilidade de 4 etapas (Pergunta, Fundamentação/Exploração, Foco, Síntese) com exibição inline de eventos de rastreabilidade.
**Streaming**: Utiliza streaming WebSocket para saída em tempo real.
**Rastreabilidade**: Pode rastrear arestas selecionadas de volta para documentos de origem por meio de reificação e cadeias `prov:wasDerivedFrom`.
Cresceu de ~30 linhas para ~760 linhas para acomodar o pipeline completo de explicabilidade.

### `tg-invoke-document-rag`

**Suporte para explicabilidade**: Adicionado modo `question_explainable()` que transmite respostas do Document RAG com eventos de rastreabilidade inline (etapas de Pergunta, Fundamentação, Exploração, Síntese).

### `tg-invoke-agent`

**Suporte para explicabilidade**: Adicionado modo `question_explainable()` que exibe eventos de rastreabilidade inline durante a execução do agente (etapas de Pergunta, Análise, Conclusão, AgentThought, AgentObservation, AgentAnswer).
O modo verboso exibe fluxos de pensamento/observação com prefixos de emoji.

### `tg-show-graph`

**Modo de streaming**: Agora usa `triples_query_stream()` com tamanhos de lote configuráveis para um tempo de primeiro resultado menor e menor sobrecarga de memória.
**Suporte para grafos nomeados**: Nova opção de filtro `--graph`. Reconhece grafos nomeados:
  Grafo padrão (vazio): Fatos de conhecimento principais
  `urn:graph:source`: Rastreabilidade de extração
  `urn:graph:retrieval`: Explicabilidade no momento da consulta
**Mostrar coluna do grafo**: Nova flag `--show-graph` para exibir o grafo nomeado para cada tripla.
**Limites configuráveis**: Novas opções `--limit` e `--batch-size`.

### `tg-graph-to-turtle`

**Suporte para RDF-star**: Agora lida com triplas citadas (reificação RDF-star).
**Modo de streaming**: Utiliza streaming para um tempo de processamento inicial menor.
**Manipulação de formato de fio**: Atualizado para usar o novo formato de fio de termos (`{"t": "i", "i": uri}` para IRIs, `{"t": "l", "v": value}` para literais, `{"t": "r", "r": {...}}` para triplas citadas).
**Suporte para grafos nomeados**: Nova opção de filtro `--graph`.

### `tg-set-tool`

**Novo tipo de ferramenta**: `row-embeddings-query` para pesquisa semântica em índices de dados estruturados.
**Novas opções**: `--schema-name`, `--index-name`, `--limit` para configurar ferramentas de consulta de incorporações de linhas.

### `tg-show-tools`

Exibe o novo tipo de ferramenta `row-embeddings-query` com seus campos `schema-name`, `index-name` e `limit`.

### `tg-load-knowledge`

**Relatório de progresso**: Agora conta e relata triplas e contextos de entidade carregados por arquivo e no total.
**Atualização do formato de termo**: Os contextos de entidade agora usam o novo formato de Termo (`{"t": "i", "i": uri}`) em vez do formato de Valor antigo (`{"v": entity, "e": True}`).

--

## Mudanças Incompatíveis

**Renomeação de terminologia**: O esquema `Value` foi renomeado para `Term` em todo o sistema (PR #622). Isso afeta o formato de fio usado por ferramentas de linha de comando que interagem com o armazenamento de grafo. O novo formato usa `{"t": "i", "i": uri}` para IRIs e `{"t": "l", "v": value}` para literais, substituindo o formato antigo `{"v": ..., "e": ...}`.
**`tg-invoke-objects-query` renomeado** para `tg-invoke-rows-query`.
**`tg-load-pdf` e `tg-load-text` removidos**.
