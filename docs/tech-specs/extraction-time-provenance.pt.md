---
layout: default
title: "Proveniência no Momento da Extração: Camada de Origem"
parent: "Portuguese (Beta)"
---

# Proveniência no Momento da Extração: Camada de Origem

> **Beta Translation:** This document was translated via Machine Learning and as such may not be 100% accurate. All non-English languages are currently classified as Beta.

## Visão Geral

Este documento registra notas sobre a proveniência no momento da extração para trabalhos de especificação futuros. A proveniência no momento da extração registra a "camada de origem" - de onde os dados vieram originalmente, como foram extraídos e transformados.

Isso é diferente da proveniência no momento da consulta (veja `query-time-provenance.md`), que registra o raciocínio do agente.

## Declaração do Problema

### Implementação Atual

Atualmente, a proveniência funciona da seguinte forma:
Metadados do documento são armazenados como triplas RDF no grafo de conhecimento.
Um ID de documento associa metadados ao documento, de modo que o documento aparece como um nó no grafo.
Quando arestas (relacionamentos/fatos) são extraídas de documentos, um relacionamento `subjectOf` vincula a aresta extraída ao documento de origem.

### Problemas com a Abordagem Atual

<<<<<<< HEAD
1. **Carregamento repetitivo de metadados:** Os metadados do documento são agrupados e carregados repetidamente com cada lote de triplas extraídas daquele documento. Isso é um desperdício e redundante - os mesmos metadados viajam como carga com cada saída de extração.
=======
1. **Carregamento repetitivo de metadados:** Os metadados do documento são agrupados e carregados repetidamente com cada lote de triplas extraídas daquele documento. Isso é um desperdício e redundante - os mesmos metadados viajam como carga útil com cada saída de extração.
>>>>>>> 82edf2d (New md files from RunPod)

2. **Proveniência superficial:** O relacionamento `subjectOf` atual vincula apenas os fatos diretamente ao documento de nível superior. Não há visibilidade da cadeia de transformação - qual página o fato veio, qual trecho, qual método de extração foi usado.

### Estado Desejado

1. **Carregar metadados uma vez:** Os metadados do documento devem ser carregados uma vez e anexados ao nó do documento de nível superior, não repetidos com cada lote de triplas.

2. **DAG de proveniência rica:** Capture toda a cadeia de transformação desde o documento de origem, passando por todos os artefatos intermediários, até os fatos extraídos. Por exemplo, uma transformação de documento PDF:

   ```
   PDF file (source document with metadata)
     → Page 1 (decoded text)
       → Chunk 1
         → Extracted edge/fact (via subjectOf)
         → Extracted edge/fact
       → Chunk 2
         → Extracted edge/fact
     → Page 2
       → Chunk 3
         → ...
   ```

<<<<<<< HEAD
3. **Armazenamento unificado:** O grafo de proveniência é armazenado no mesmo grafo de conhecimento que o conhecimento extraído. Isso permite que a proveniência seja consultada da mesma forma que o conhecimento - seguindo as arestas de volta à cadeia de qualquer fato para sua localização de origem exata.
=======
3. **Armazenamento unificado:** O grafo de proveniência é armazenado no mesmo grafo de conhecimento que o conhecimento extraído. Isso permite que a proveniência seja consultada da mesma forma que o conhecimento - seguindo as arestas de volta à cadeia de qualquer fato até sua localização de origem exata.
>>>>>>> 82edf2d (New md files from RunPod)

4. **IDs estáveis:** Cada artefato intermediário (página, trecho) possui um ID estável como um nó no grafo.

5. **Vinculação pai-filho:** Documentos derivados são vinculados aos seus pais até o documento de origem de nível superior, usando tipos de relacionamento consistentes.

<<<<<<< HEAD
6. **Atribuição precisa de fatos:** O relacionamento `subjectOf` nas arestas extraídas aponta para o pai imediato (trecho), não para o documento de nível superior. A proveniência completa é recuperada percorrendo o DAG.
=======
6. **Atribuição precisa de fatos:** O relacionamento `subjectOf` nas arestas extraídas aponta para o pai imediato (trecho), e não para o documento de nível superior. A proveniência completa é recuperada percorrendo o DAG.
>>>>>>> 82edf2d (New md files from RunPod)

## Casos de Uso

### UC1: Atribuição de Fonte em Respostas GraphRAG

**Cenário:** Um usuário executa uma consulta GraphRAG e recebe uma resposta do agente.

**Fluxo:**
1. O usuário envia uma consulta para o agente GraphRAG.
2. O agente recupera fatos relevantes do grafo de conhecimento para formular uma resposta.
3. De acordo com a especificação de proveniência em tempo de consulta, o agente informa quais fatos contribuíram para a resposta.
4. Cada fato vincula-se ao seu trecho de origem através do grafo de proveniência.
5. Trechos vinculam-se a páginas, páginas vinculam-se a documentos de origem.

**Resultado da Experiência do Usuário:** A interface exibe a resposta do LLM juntamente com a atribuição da fonte. O usuário pode:
<<<<<<< HEAD
Ver quais fatos apoiaram a resposta.
=======
Ver quais fatos suportaram a resposta.
>>>>>>> 82edf2d (New md files from RunPod)
Acessar informações detalhadas de fatos → trechos → páginas → documentos.
Examinar os documentos de origem para verificar as alegações.
Entender exatamente onde em um documento (qual página, qual seção) um fato se originou.

**Valor:** Os usuários podem verificar as respostas geradas por IA em relação às fontes primárias, construindo confiança e permitindo a verificação de fatos.

### UC2: Depuração da Qualidade da Extração

Um fato parece incorreto. Rastreie de volta através do trecho → página → documento para ver o texto original. Foi uma extração ruim ou a fonte em si estava incorreta?

<<<<<<< HEAD
### UC3: Reextração Incremental
=======
### UC3: Re-extração Incremental
>>>>>>> 82edf2d (New md files from RunPod)

O documento de origem é atualizado. Quais trechos/fatos foram derivados dele? Invalide e regenere apenas esses, em vez de reprocessar tudo.

### UC4: Exclusão de Dados / Direito ao Esquecimento

Um documento de origem deve ser removido (GDPR, legal, etc.). Percorra o DAG para encontrar e remover todos os fatos derivados.

### UC5: Resolução de Conflitos

<<<<<<< HEAD
Dois fatos se contradizem. Rastreie ambos de volta às suas fontes para entender por que e decidir qual confiar (fonte mais autoritária, mais recente, etc.).
=======
Dois fatos se contradizem. Rastreie ambos de volta às suas fontes para entender o porquê e decidir qual confiar (fonte mais autoritária, mais recente, etc.).
>>>>>>> 82edf2d (New md files from RunPod)

### UC6: Ponderação da Autoridade da Fonte

Algumas fontes são mais autoritárias do que outras. Os fatos podem ser ponderados ou filtrados com base na autoridade/qualidade de seus documentos de origem.

### UC7: Comparação de Pipelines de Extração

Compare os resultados de diferentes métodos/versões de extração. Qual extrator produziu melhores fatos da mesma fonte?

## Pontos de Integração

### Bibliotecário

<<<<<<< HEAD
O componente bibliotecário já fornece armazenamento de documentos com IDs de documento exclusivos. O sistema de rastreabilidade se integra com essa infraestrutura existente.
=======
O componente bibliotecário já fornece armazenamento de documentos com IDs de documentos exclusivos. O sistema de rastreabilidade se integra a essa infraestrutura existente.
>>>>>>> 82edf2d (New md files from RunPod)

#### Capacidades Existentes (já implementadas)

**Vinculação de Documentos Pai-Filho:**
Campo `parent_id` em `DocumentMetadata` - vincula o documento filho ao documento pai
Campo `document_type` - valores: `"source"` (original) ou `"extracted"` (derivado)
API `add-child-document` - cria um documento filho com `document_type = "extracted"` automático
API `list-children` - recupera todos os filhos de um documento pai
Exclusão em cascata - a remoção de um pai exclui automaticamente todos os documentos filhos

**Identificação de Documentos:**
<<<<<<< HEAD
Os IDs de documento são especificados pelo cliente (não gerados automaticamente)
Documentos indexados por `(user, document_id)` composto no Cassandra
IDs de objeto (UUIDs) gerados internamente para armazenamento de blobs
=======
Os IDs dos documentos são especificados pelo cliente (não gerados automaticamente)
Documentos indexados por `(user, document_id)` composto no Cassandra
IDs de objetos (UUIDs) gerados internamente para armazenamento de blobs
>>>>>>> 82edf2d (New md files from RunPod)

**Suporte a Metadados:**
Campo `metadata: list[Triple]` - triplas RDF para metadados estruturados
`title`, `comments`, `tags` - metadados básicos do documento
`time` - carimbo de data/hora, `kind` - tipo MIME

**Arquitetura de Armazenamento:**
Metadados armazenados no Cassandra (espaço de chaves `librarian`, tabela `document`)
Conteúdo armazenado no armazenamento de blobs MinIO/S3 (bucket `library`)
Entrega inteligente de conteúdo: documentos < 2MB incorporados, documentos maiores transmitidos

#### Arquivos Chave

`trustgraph-flow/trustgraph/librarian/librarian.py` - Operações principais do bibliotecário
<<<<<<< HEAD
`trustgraph-flow/trustgraph/librarian/service.py` - Processador de serviço, carregamento de documento
=======
`trustgraph-flow/trustgraph/librarian/service.py` - Processador de serviço, carregamento de documentos
>>>>>>> 82edf2d (New md files from RunPod)
`trustgraph-flow/trustgraph/tables/library.py` - Armazenamento de tabela Cassandra
`trustgraph-base/trustgraph/schema/services/library.py` - Definições de esquema

#### Lacunas a Serem Abordadas

O bibliotecário tem os blocos de construção, mas atualmente:
1. A vinculação pai-filho é de um único nível - não há auxiliares de travessia de DAG de vários níveis
2. Não há vocabulário padrão de tipo de relacionamento (por exemplo, `derivedFrom`, `extractedFrom`)
3. Metadados de rastreabilidade (método de extração, confiança, posição do fragmento) não estão padronizados
<<<<<<< HEAD
4. Não há API de consulta para percorrer toda a cadeia de rastreabilidade de um fato até a fonte
=======
4. Não há API de consulta para percorrer toda a cadeia de rastreabilidade de um fato até a origem
>>>>>>> 82edf2d (New md files from RunPod)

## Design de Fluxo de Extremo a Extremo

Cada processador no pipeline segue um padrão consistente:
Recebe o ID do documento do upstream
Recupera o conteúdo do bibliotecário
Produz artefatos filhos
Para cada filho: salva no bibliotecário, emite uma aresta para o grafo, encaminha o ID para o downstream

### Fluxos de Processamento

Existem dois fluxos dependendo do tipo de documento:

#### Fluxo de Documento PDF

```
┌─────────────────────────────────────────────────────────────────────────┐
│ Librarian (initiate processing)                                         │
│   1. Emit root document metadata to knowledge graph (once)              │
│   2. Send root document ID to PDF extractor                             │
└─────────────────────────────────────────────────────────────────────────┘
                                    │
                                    ▼
┌─────────────────────────────────────────────────────────────────────────┐
│ PDF Extractor (per page)                                                │
│   1. Fetch PDF content from librarian using document ID                 │
│   2. Extract pages as text                                              │
│   3. For each page:                                                     │
│      a. Save page as child document in librarian (parent = root doc)   │
│      b. Emit parent-child edge to knowledge graph                       │
│      c. Send page document ID to chunker                                │
└─────────────────────────────────────────────────────────────────────────┘
                                    │
                                    ▼
┌─────────────────────────────────────────────────────────────────────────┐
│ Chunker (per chunk)                                                     │
│   1. Fetch page content from librarian using document ID                │
│   2. Split text into chunks                                             │
│   3. For each chunk:                                                    │
│      a. Save chunk as child document in librarian (parent = page)      │
│      b. Emit parent-child edge to knowledge graph                       │
│      c. Send chunk document ID + chunk content to next processor        │
└─────────────────────────────────────────────────────────────────────────┘
                                    │
                                    ▼
          ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─
          Post-chunker optimization: messages carry both
          chunk ID (for provenance) and content (to avoid
          librarian round-trip). Chunks are small (2-4KB).
          ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─
                                    │
                                    ▼
┌─────────────────────────────────────────────────────────────────────────┐
│ Knowledge Extractor (per chunk)                                         │
│   1. Receive chunk ID + content directly (no librarian fetch needed)   │
│   2. Extract facts/triples and embeddings from chunk content            │
│   3. For each triple:                                                   │
│      a. Emit triple to knowledge graph                                  │
│      b. Emit reified edge linking triple → chunk ID (edge pointing     │
│         to edge - first use of reification support)                     │
│   4. For each embedding:                                                │
│      a. Emit embedding with its entity ID                               │
│      b. Link entity ID → chunk ID in knowledge graph                   │
└─────────────────────────────────────────────────────────────────────────┘
```

#### Fluxo de Documentos de Texto

Documentos de texto ignoram o extrator de PDF e vão diretamente para o processador de fragmentos:

```
┌─────────────────────────────────────────────────────────────────────────┐
│ Librarian (initiate processing)                                         │
│   1. Emit root document metadata to knowledge graph (once)              │
│   2. Send root document ID directly to chunker (skip PDF extractor)    │
└─────────────────────────────────────────────────────────────────────────┘
                                    │
                                    ▼
┌─────────────────────────────────────────────────────────────────────────┐
│ Chunker (per chunk)                                                     │
│   1. Fetch text content from librarian using document ID                │
│   2. Split text into chunks                                             │
│   3. For each chunk:                                                    │
│      a. Save chunk as child document in librarian (parent = root doc) │
│      b. Emit parent-child edge to knowledge graph                       │
│      c. Send chunk document ID + chunk content to next processor        │
└─────────────────────────────────────────────────────────────────────────┘
                                    │
                                    ▼
┌─────────────────────────────────────────────────────────────────────────┐
│ Knowledge Extractor                                                     │
│   (same as PDF flow)                                                    │
└─────────────────────────────────────────────────────────────────────────┘
```

<<<<<<< HEAD
O grafo acíclico dirigido (DAG) resultante é um nível mais curto:
=======
O grafo acíclico direcionado (DAG) resultante é um nível mais curto:
>>>>>>> 82edf2d (New md files from RunPod)

```
PDF:  Document → Pages → Chunks → Triples/Embeddings
Text: Document → Chunks → Triples/Embeddings
```

O design acomoda ambos porque o processador divide o conteúdo de forma genérica - ele usa qualquer ID de documento que recebe como pai, independentemente de ser um documento de origem ou uma página.

### Esquema de Metadados (PROV-O)

Os metadados de procedência utilizam a ontologia W3C PROV-O. Isso fornece um vocabulário padrão e permite a futura assinatura/autenticação dos resultados da extração.

#### Conceitos Principais do PROV-O

| Tipo PROV-O | Uso no TrustGraph |
|-------------|------------------|
| `prov:Entity` | Documento, Página, Trecho, Tripla, Incorporação |
| `prov:Activity` | Instâncias de operações de extração |
| `prov:Agent` | Componentes do TG (extrator de PDF, processador, etc.) com versões |

#### Relacionamentos do PROV-O

| Predicado | Significado | Exemplo |
|-----------|---------|---------|
<<<<<<< HEAD
| `prov:wasDerivedFrom` | Entidade derivada de outra entidade | Página foiDerivadaDe Documento |
| `prov:wasGeneratedBy` | Entidade gerada por uma atividade | Página foiGeradaPor AtividadeDeExtraçãoDePDF |
| `prov:used` | Atividade que usou uma entidade como entrada | AtividadeDeExtraçãoDePDF usou Documento |
| `prov:wasAssociatedWith` | Atividade realizada por um agente | AtividadeDeExtraçãoDePDF foiAssociadaA tg:ExtratorDePDF |
=======
| `prov:wasDerivedFrom` | Entidade derivada de outra entidade | Página derivadaDocumento |
| `prov:wasGeneratedBy` | Entidade gerada por uma atividade | Página geradaPor AtividadeDeExtraçãoDePDF |
| `prov:used` | Atividade que usou uma entidade como entrada | AtividadeDeExtraçãoDePDF usou Documento |
| `prov:wasAssociatedWith` | Atividade realizada por um agente | AtividadeDeExtraçãoDePDF associadaA tg:ExtratorDePDF |
>>>>>>> 82edf2d (New md files from RunPod)

#### Metadados em Cada Nível

**Documento de Origem (emitido pelo Librarian):**
```
doc:123 a prov:Entity .
doc:123 dc:title "Research Paper" .
doc:123 dc:source <https://example.com/paper.pdf> .
doc:123 dc:date "2024-01-15" .
doc:123 dc:creator "Author Name" .
doc:123 tg:pageCount 42 .
doc:123 tg:mimeType "application/pdf" .
```

**Página (emitida pelo Extrator de PDF):**
```
page:123-1 a prov:Entity .
page:123-1 prov:wasDerivedFrom doc:123 .
page:123-1 prov:wasGeneratedBy activity:pdf-extract-456 .
page:123-1 tg:pageNumber 1 .

activity:pdf-extract-456 a prov:Activity .
activity:pdf-extract-456 prov:used doc:123 .
activity:pdf-extract-456 prov:wasAssociatedWith tg:PDFExtractor .
activity:pdf-extract-456 tg:componentVersion "1.2.3" .
activity:pdf-extract-456 prov:startedAtTime "2024-01-15T10:30:00Z" .
```

**Bloco (emitido pelo Chunker):**
```
chunk:123-1-1 a prov:Entity .
chunk:123-1-1 prov:wasDerivedFrom page:123-1 .
chunk:123-1-1 prov:wasGeneratedBy activity:chunk-789 .
chunk:123-1-1 tg:chunkIndex 1 .
chunk:123-1-1 tg:charOffset 0 .
chunk:123-1-1 tg:charLength 2048 .

activity:chunk-789 a prov:Activity .
activity:chunk-789 prov:used page:123-1 .
activity:chunk-789 prov:wasAssociatedWith tg:Chunker .
activity:chunk-789 tg:componentVersion "1.0.0" .
activity:chunk-789 tg:chunkSize 2048 .
activity:chunk-789 tg:chunkOverlap 200 .
```

**Tripla (emitida pelo Extrator de Conhecimento):**
```
# The extracted triple (edge)
entity:JohnSmith rel:worksAt entity:AcmeCorp .

# Subgraph containing the extracted triples
subgraph:001 tg:contains <<entity:JohnSmith rel:worksAt entity:AcmeCorp>> .
subgraph:001 prov:wasDerivedFrom chunk:123-1-1 .
subgraph:001 prov:wasGeneratedBy activity:extract-999 .

activity:extract-999 a prov:Activity .
activity:extract-999 prov:used chunk:123-1-1 .
activity:extract-999 prov:wasAssociatedWith tg:KnowledgeExtractor .
activity:extract-999 tg:componentVersion "2.1.0" .
activity:extract-999 tg:llmModel "claude-3" .
activity:extract-999 tg:ontology <http://example.org/ontologies/business-v1> .
```

**Incorporação (armazenada em um armazenamento vetorial, não em um armazenamento triplo):**

As incorporações são armazenadas no armazenamento vetorial com metadados, e não como triplos RDF. Cada registro de incorporação contém:

| Campo | Descrição | Exemplo |
|-------|-------------|---------|
| vetor | O vetor de incorporação | [0.123, -0.456, ...] |
| entidade | URI do nó que a incorporação representa | `entity:JohnSmith` |
| chunk_id | Fragmento de origem (proveniência) | `chunk:123-1-1` |
| modelo | Modelo de incorporação usado | `text-embedding-ada-002` |
| component_version | Versão do incorporador TG | `1.0.0` |

<<<<<<< HEAD
O campo `entity` vincula a incorporação ao grafo de conhecimento (URI do nó). O campo `chunk_id` fornece a proveniência de volta ao fragmento de origem, permitindo a navegação ascendente no DAG até o documento original.
=======
O campo `entity` vincula a incorporação ao grafo de conhecimento (URI do nó). O campo `chunk_id` fornece a proveniência de volta ao fragmento de origem, permitindo a travessia ascendente do DAG até o documento original.
>>>>>>> 82edf2d (New md files from RunPod)

#### Extensões do Namespace TrustGraph

Predicados personalizados sob o namespace `tg:` para metadados específicos de extração:

| Predicado | Domínio | Descrição |
|-----------|--------|-------------|
| `tg:contains` | Subgrafo | Aponta para um triplo contido neste subgrafo de extração |
| `tg:pageCount` | Documento | Número total de páginas no documento de origem |
| `tg:mimeType` | Documento | Tipo MIME do documento de origem |
| `tg:pageNumber` | Página | Número da página no documento de origem |
| `tg:chunkIndex` | Fragmento | Índice do fragmento dentro do fragmento pai |
| `tg:charOffset` | Fragmento | Deslocamento de caractere no texto pai |
| `tg:charLength` | Fragmento | Comprimento do fragmento em caracteres |
| `tg:chunkSize` | Atividade | Tamanho do fragmento configurado |
| `tg:chunkOverlap` | Atividade | Sobreposição configurada entre fragmentos |
| `tg:componentVersion` | Atividade | Versão do componente TG |
| `tg:llmModel` | Atividade | LLM usado para extração |
| `tg:ontology` | Atividade | URI da ontologia usada para guiar a extração |
| `tg:embeddingModel` | Atividade | Modelo usado para incorporações |
| `tg:sourceText` | Declaração | Texto exato do qual um triplo foi extraído |
| `tg:sourceCharOffset` | Declaração | Deslocamento de caractere dentro do fragmento onde o texto de origem começa |
| `tg:sourceCharLength` | Declaração | Comprimento do texto de origem em caracteres |

#### Inicialização do Vocabulário (Por Coleção)

O grafo de conhecimento é neutro em relação à ontologia e é inicializado como vazio. Ao gravar dados de proveniência PROV-O em uma coleção pela primeira vez, o vocabulário deve ser inicializado com rótulos RDF para todas as classes e predicados. Isso garante a exibição legível por humanos em consultas e na interface do usuário.

**Classes PROV-O:**
```
prov:Entity rdfs:label "Entity" .
prov:Activity rdfs:label "Activity" .
prov:Agent rdfs:label "Agent" .
```

**Predicados PROV-O:**
```
prov:wasDerivedFrom rdfs:label "was derived from" .
prov:wasGeneratedBy rdfs:label "was generated by" .
prov:used rdfs:label "used" .
prov:wasAssociatedWith rdfs:label "was associated with" .
prov:startedAtTime rdfs:label "started at" .
```

<<<<<<< HEAD
**Predicados TrustGraph:**
=======
**Predicados do TrustGraph:**
>>>>>>> 82edf2d (New md files from RunPod)
```
tg:contains rdfs:label "contains" .
tg:pageCount rdfs:label "page count" .
tg:mimeType rdfs:label "MIME type" .
tg:pageNumber rdfs:label "page number" .
tg:chunkIndex rdfs:label "chunk index" .
tg:charOffset rdfs:label "character offset" .
tg:charLength rdfs:label "character length" .
tg:chunkSize rdfs:label "chunk size" .
tg:chunkOverlap rdfs:label "chunk overlap" .
tg:componentVersion rdfs:label "component version" .
tg:llmModel rdfs:label "LLM model" .
tg:ontology rdfs:label "ontology" .
tg:embeddingModel rdfs:label "embedding model" .
tg:sourceText rdfs:label "source text" .
tg:sourceCharOffset rdfs:label "source character offset" .
tg:sourceCharLength rdfs:label "source character length" .
```

<<<<<<< HEAD
**Observação sobre a implementação:** Este processo de inicialização do vocabulário deve ser idempotente - seguro para executar várias vezes sem criar duplicatas. Pode ser acionado no processamento do primeiro documento em uma coleção, ou como uma etapa separada de inicialização da coleção.
=======
**Observação sobre a implementação:** Este vocabulário de inicialização deve ser idempotente - seguro para executar várias vezes sem criar duplicatas. Pode ser acionado no processamento do primeiro documento em uma coleção, ou como uma etapa separada de inicialização da coleção.
>>>>>>> 82edf2d (New md files from RunPod)

#### Proveniência de Sub-Fragmentos (Alvo)

Para uma rastreabilidade mais detalhada, seria valioso registrar exatamente onde, dentro de um fragmento, uma tripla foi extraída. Isso permite:

Destacar o texto de origem exato na interface do usuário
<<<<<<< HEAD
Verificar a precisão da extração em relação à fonte
=======
Verificar a precisão da extração em relação à origem
>>>>>>> 82edf2d (New md files from RunPod)
Depurar a qualidade da extração no nível da frase

**Exemplo com rastreamento de posição:**
```
# The extracted triple
entity:JohnSmith rel:worksAt entity:AcmeCorp .

# Subgraph with sub-chunk provenance
subgraph:001 tg:contains <<entity:JohnSmith rel:worksAt entity:AcmeCorp>> .
subgraph:001 prov:wasDerivedFrom chunk:123-1-1 .
subgraph:001 tg:sourceText "John Smith has worked at Acme Corp since 2019" .
subgraph:001 tg:sourceCharOffset 1547 .
subgraph:001 tg:sourceCharLength 46 .
```

**Exemplo com intervalo de texto (alternativa):**
```
subgraph:001 tg:contains <<entity:JohnSmith rel:worksAt entity:AcmeCorp>> .
subgraph:001 prov:wasDerivedFrom chunk:123-1-1 .
subgraph:001 tg:sourceRange "1547-1593" .
subgraph:001 tg:sourceText "John Smith has worked at Acme Corp since 2019" .
```

**Considerações de implementação:**

A extração baseada em LLM pode não fornecer naturalmente as posições dos caracteres.
Poderia solicitar ao LLM que retornasse a frase/frase de origem junto com as triplas extraídas.
<<<<<<< HEAD
Alternativamente, pós-processe para fazer uma correspondência aproximada das entidades extraídas com o texto de origem.
=======
Alternativamente, pós-processar para fazer uma correspondência aproximada das entidades extraídas com o texto de origem.
>>>>>>> 82edf2d (New md files from RunPod)
Compromisso entre a complexidade da extração e a granularidade da procedência.
Pode ser mais fácil de alcançar com métodos de extração estruturados do que com a extração de LLM de formato livre.

Isso está marcado como uma meta a longo prazo - a procedência no nível do bloco deve ser implementada primeiro, com o rastreamento de subblocos como um aprimoramento futuro, se viável.

### Modelo de Armazenamento Duplo

O grafo de procedência é construído progressivamente à medida que os documentos fluem pelo pipeline:

| Armazenamento | O que é armazenado | Propósito |
|-------|---------------|---------|
<<<<<<< HEAD
| Bibliotecário | Conteúdo do documento + links pai-filho | Recuperação de conteúdo, exclusão em cascata |
| Grafo de Conhecimento | Arestas pai-filho + metadados | Consultas de procedência, atribuição de fatos |

Ambos os armazenamentos mantêm a mesma estrutura de grafo. O bibliotecário armazena o conteúdo; o grafo armazena os relacionamentos e permite consultas de travessia.

### Princípios de Design Chave

1. **ID do documento como a unidade de fluxo** - Os processadores passam IDs, não o conteúdo. O conteúdo é buscado do bibliotecário quando necessário.
=======
| Librarian | Conteúdo do documento + links pai-filho | Recuperação de conteúdo, exclusão em cascata |
| Knowledge Graph | Arestas pai-filho + metadados | Consultas de procedência, atribuição de fatos |

Ambos os armazenamentos mantêm a mesma estrutura de grafo. O librarian armazena o conteúdo; o grafo armazena os relacionamentos e permite consultas de travessia.

### Princípios de Design Chave

1. **ID do documento como a unidade de fluxo** - Os processadores passam IDs, não o conteúdo. O conteúdo é buscado do librarian quando necessário.
>>>>>>> 82edf2d (New md files from RunPod)

2. **Emitir uma vez na origem** - Os metadados são gravados no grafo uma vez quando o processamento começa, e não repetidos downstream.

3. **Padrão de processador consistente** - Cada processador segue o mesmo padrão de receber/buscar/produzir/salvar/emitir/transmitir.

4. **Construção progressiva do grafo** - Cada processador adiciona seu nível ao grafo. A cadeia completa de procedência é construída incrementalmente.

<<<<<<< HEAD
5. **Otimização pós-fragmentação** - Após a fragmentação, as mensagens carregam tanto o ID quanto o conteúdo. Os fragmentos são pequenos (2-4 KB), portanto, incluir o conteúdo evita viagens de ida e volta desnecessárias ao bibliotecário, preservando a procedência por meio do ID.

## Tarefas de Implementação

### Alterações no Bibliotecário
=======
5. **Otimização pós-fragmentação** - Após a fragmentação, as mensagens carregam tanto o ID quanto o conteúdo. Os fragmentos são pequenos (2-4 KB), portanto, incluir o conteúdo evita viagens de ida e volta desnecessárias ao librarian, preservando a procedência por meio do ID.

## Tarefas de Implementação

### Alterações no Librarian
>>>>>>> 82edf2d (New md files from RunPod)

#### Estado Atual

Inicia o processamento do documento enviando o ID do documento para o primeiro processador.
<<<<<<< HEAD
Não possui conexão com o armazenamento de triplas - os metadados são agrupados com as saídas de extração.
=======
Não possui conexão com o triple store - os metadados são agrupados com as saídas de extração.
>>>>>>> 82edf2d (New md files from RunPod)
`add-child-document` cria links pai-filho de um nível.
`list-children` retorna apenas os filhos imediatos.

#### Alterações Necessárias

<<<<<<< HEAD
**1. Nova interface: Conexão com o armazenamento de triplas**

O bibliotecário precisa emitir as bordas de metadados do documento diretamente para o grafo de conhecimento ao iniciar o processamento.
Adicione um cliente/publicador de armazenamento de triplas ao serviço do bibliotecário.
Na inicialização do processamento: emita os metadados do documento raiz como bordas do grafo (uma vez).

**2. Vocabulário de tipo de documento**

Padronize os valores de `document_type` para documentos filhos:
=======
**1. Nova interface: Conexão com o triple store**

O librarian precisa emitir as bordas de metadados do documento diretamente para o knowledge graph ao iniciar o processamento.
Adicionar cliente/publicador do triple store ao serviço do librarian.
Na inicialização do processamento: emitir os metadados do documento raiz como bordas do grafo (uma vez).

**2. Vocabulário de tipo de documento**

Padronizar os valores de `document_type` para documentos filhos:
>>>>>>> 82edf2d (New md files from RunPod)
`source` - documento original carregado.
`page` - página extraída da fonte (PDF, etc.).
`chunk` - fragmento de texto derivado da página ou da fonte.

#### Resumo das Alterações na Interface

| Interface | Alteração |
|-----------|--------|
<<<<<<< HEAD
| Armazenamento de triplas | Nova conexão de saída - emita bordas de metadados do documento |
| Início do processamento | Emita metadados para o grafo antes de encaminhar o ID do documento |
=======
| Triple store | Nova conexão de saída - emitir bordas de metadados do documento |
| Início do processamento | Emitir metadados para o grafo antes de encaminhar o ID do documento |
>>>>>>> 82edf2d (New md files from RunPod)

### Alterações no Extrator de PDF

#### Estado Atual

Recebe o conteúdo do documento (ou transmite documentos grandes).
Extrai texto das páginas PDF.
Transmite o conteúdo da página para o fragmentador.
<<<<<<< HEAD
Não interage com o bibliotecário ou o armazenamento de triplas.

#### Alterações Necessárias

**1. Nova interface: Cliente do bibliotecário**

O extrator de PDF precisa salvar cada página como um documento filho no bibliotecário.
Adicione um cliente do bibliotecário ao serviço do extrator de PDF.
Para cada página: chame `add-child-document` com pai = ID do documento raiz.

**2. Nova interface: Conexão com o armazenamento de triplas**

O extrator de PDF precisa emitir bordas pai-filho para o grafo de conhecimento.
Adicione um cliente/publicador de armazenamento de triplas.
Para cada página: emita uma borda que vincule o documento da página ao documento pai.
=======
Não interage com o librarian ou o triple store.

#### Alterações Necessárias

**1. Nova interface: Cliente do librarian**

O extrator de PDF precisa salvar cada página como um documento filho no librarian.
Adicionar cliente do librarian ao serviço do extrator de PDF.
Para cada página: chamar `add-child-document` com pai = ID do documento raiz.

**2. Nova interface: Conexão com o triple store**

O extrator de PDF precisa emitir bordas pai-filho para o knowledge graph.
Adicionar cliente/publicador do triple store.
Para cada página: emitir uma borda que vincule o documento da página ao documento pai.
>>>>>>> 82edf2d (New md files from RunPod)

**3. Alterar o formato de saída**

Em vez de encaminhar o conteúdo da página diretamente, encaminhe o ID do documento da página.
O Chunker buscará o conteúdo do "librarian" usando o ID.

#### Resumo das Alterações na Interface

| Interface | Mudança |
|-----------|--------|
| Librarian | Nova saída - salvar documentos filhos |
| Triple store | Nova saída - emitir arestas pai-filho |
| Mensagem de saída | Mudança de conteúdo para ID do documento |

### Mudanças no Chunker

#### Estado Atual

Recebe conteúdo da página/texto
Divide em partes (chunks)
Encaminha o conteúdo da parte para processadores subsequentes
Sem interação com o "librarian" ou o "triple store"

#### Mudanças Necessárias

**1. Alterar o tratamento da entrada**

Receber o ID do documento em vez do conteúdo, buscar do "librarian".
Adicionar cliente do "librarian" ao serviço do Chunker
Buscar o conteúdo da página usando o ID do documento

**2. Nova interface: Cliente do "Librarian" (escrita)**

Salvar cada parte como um documento filho no "librarian".
Para cada parte: chamar `add-child-document` com parent = ID do documento da página

**3. Nova interface: Conexão com o "Triple store"**

Emitir arestas pai-filho para o grafo de conhecimento.
Adicionar cliente/publicador do "triple store"
Para cada parte: emitir aresta ligando o documento da parte ao documento da página

**4. Alterar o formato de saída**

Encaminhar tanto o ID do documento da parte quanto o conteúdo da parte (otimização pós-chunker).
Os processadores subsequentes recebem o ID para rastreabilidade + o conteúdo para trabalhar

#### Resumo das Alterações na Interface

| Interface | Mudança |
|-----------|--------|
| Mensagem de entrada | Mudança de conteúdo para ID do documento |
| Librarian | Nova saída (leitura + escrita) - buscar conteúdo, salvar documentos filhos |
| Triple store | Nova saída - emitir arestas pai-filho |
| Mensagem de saída | Mudança de conteúdo-apenas para ID + conteúdo |

### Mudanças no Extrator de Conhecimento

#### Estado Atual

Recebe conteúdo da parte
Extrai triplas e embeddings
Emite para o "triple store" e o "embedding store"
A relação `subjectOf` aponta para o documento de nível superior (não para a parte)

#### Mudanças Necessárias

**1. Alterar o tratamento da entrada**

Receber o ID do documento da parte junto com o conteúdo.
Usar o ID da parte para rastreabilidade (o conteúdo já está incluído por otimização)

**2. Atualizar a rastreabilidade das triplas**

Ligar as triplas extraídas à parte (não ao documento de nível superior).
Usar a reificação para criar uma aresta apontando para a aresta
Relação `subjectOf`: tripla → ID do documento da parte
Primeiro uso do suporte de reificação existente

**3. Atualizar a rastreabilidade dos embeddings**

Ligar os IDs das entidades de embedding à parte.
Emitir aresta: ID da entidade de embedding → ID do documento da parte

#### Resumo das Alterações na Interface

| Interface | Mudança |
|-----------|--------|
| Mensagem de entrada | Esperar ID da parte + conteúdo (não apenas conteúdo) |
| Triple store | Usar reificação para rastreabilidade de tripla → parte |
| Rastreabilidade de embedding | Ligar ID da entidade → ID da parte |

## Referências

Rastreabilidade em tempo de consulta: `docs/tech-specs/query-time-provenance.md`
Padrão PROV-O para modelagem de rastreabilidade
Metadados de origem existentes no grafo de conhecimento (precisa de auditoria)
