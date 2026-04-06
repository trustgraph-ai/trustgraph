# Fluxos de Extração

Este documento descreve como os dados fluem através do pipeline de extração do TrustGraph, desde o envio do documento até ao armazenamento nos repositórios de conhecimento.

## Visão Geral

```
┌──────────┐     ┌─────────────┐     ┌─────────┐     ┌────────────────────┐
│ Librarian│────▶│ PDF Decoder │────▶│ Chunker │────▶│ Knowledge          │
│          │     │ (PDF only)  │     │         │     │ Extraction         │
│          │────────────────────────▶│         │     │                    │
└──────────┘     └─────────────┘     └─────────┘     └────────────────────┘
                                          │                    │
                                          │                    ├──▶ Triples
                                          │                    ├──▶ Entity Contexts
                                          │                    └──▶ Rows
                                          │
                                          └──▶ Document Embeddings
```

## Armazenamento de Conteúdo

### Armazenamento de Blobs (S3/Minio)

O conteúdo do documento é armazenado em armazenamento de blobs compatível com S3:
Formato do caminho: `doc/{object_id}`, onde object_id é um UUID
Todos os tipos de documentos armazenados aqui: documentos de origem, páginas, trechos

### Armazenamento de Metadados (Cassandra)

Os metadados do documento armazenados no Cassandra incluem:
ID do documento, título, tipo (MIME)
Referência ao armazenamento de blobs `object_id`
Referência `parent_id` para documentos filhos (páginas, trechos)
`document_type`: "source", "page", "chunk", "answer"

### Limiar de Incorporação vs. Streaming

A transmissão de conteúdo usa uma estratégia baseada no tamanho:
**< 2MB**: O conteúdo é incluído inline na mensagem (codificado em base64)
**≥ 2MB**: Apenas `document_id` é enviado; o processador busca via API do bibliotecário

## Etapa 1: Envio de Documento (Bibliotecário)

### Ponto de Entrada

Os documentos entram no sistema através da operação `add-document` do bibliotecário:
1. O conteúdo é carregado no armazenamento de blobs
2. Um registro de metadados é criado no Cassandra
3. Retorna o ID do documento

### Disparando a Extração

A operação `add-processing` dispara a extração:
Especifica `document_id`, `flow` (ID do pipeline), `collection` (loja de destino)
A operação `load_document()` do bibliotecário busca o conteúdo e o publica na fila de entrada do fluxo

### Esquema: Documento

```
Document
├── metadata: Metadata
│   ├── id: str              # Document identifier
│   ├── user: str            # Tenant/user ID
│   ├── collection: str      # Target collection
│   └── metadata: list[Triple]  # (largely unused, historical)
├── data: bytes              # PDF content (base64, if inline)
└── document_id: str         # Librarian reference (if streaming)
```

**Roteamento**: Baseado no campo `kind`:
`application/pdf` → fila `document-load` → Decodificador PDF
`text/plain` → fila `text-load` → Fragmentador

## Etapa 2: Decodificador PDF

Converte documentos PDF em páginas de texto.

### Processo

1. Buscar conteúdo (inline `data` ou via `document_id` do bibliotecário)
2. Extrair páginas usando PyPDF
3. Para cada página:
   Salvar como documento filho no bibliotecário (`{doc_id}/p{page_num}`)
   Emitir triplas de procedência (página derivada do documento)
   Enviar para o fragmentador

### Esquema: TextDocument

```
TextDocument
├── metadata: Metadata
│   ├── id: str              # Page URI (e.g., https://trustgraph.ai/doc/xxx/p1)
│   ├── user: str
│   ├── collection: str
│   └── metadata: list[Triple]
├── text: bytes              # Page text content (if inline)
└── document_id: str         # Librarian reference (e.g., "doc123/p1")
```

## Etapa 3: Divisor em Blocos

Divide o texto em blocos de tamanho configurado.

### Parâmetros (configuráveis no fluxo)

`chunk_size`: Tamanho do bloco alvo em caracteres (padrão: 2000)
`chunk_overlap`: Sobreposição entre blocos (padrão: 100)

### Processo

1. Buscar o conteúdo do texto (inline ou via bibliotecário)
2. Dividir usando o divisor de caracteres recursivo
3. Para cada bloco:
   Salvar como documento filho no bibliotecário (`{parent_id}/c{index}`)
   Emitir triplas de procedência (bloco derivado da página/documento)
   Encaminhar para os processadores de extração

### Esquema: Bloco

```
Chunk
├── metadata: Metadata
│   ├── id: str              # Chunk URI
│   ├── user: str
│   ├── collection: str
│   └── metadata: list[Triple]
├── chunk: bytes             # Chunk text content
└── document_id: str         # Librarian chunk ID (e.g., "doc123/p1/c3")
```

### Hierarquia de Identificação de Documentos

Documentos filhos codificam sua linhagem no ID:
Fonte: `doc123`
Página: `doc123/p5`
Trecho da página: `doc123/p5/c2`
Trecho de texto: `doc123/c2`

## Etapa 4: Extração de Conhecimento

Múltiplos padrões de extração disponíveis, selecionados pela configuração do fluxo.

### Padrão A: Basic GraphRAG

Dois processadores paralelos:

**kg-extract-definitions**
Entrada: Trecho
Saída: Triplas (definições de entidades), Contextos de Entidade
Extrai: rótulos de entidades, definições

**kg-extract-relationships**
Entrada: Trecho
Saída: Triplas (relacionamentos), Contextos de Entidade
Extrai: relações sujeito-predicado-objeto

### Padrão B: Orientado a Ontologia (kg-extract-ontology)

Entrada: Trecho
Saída: Triplas, Contextos de Entidade
Utiliza uma ontologia configurada para guiar a extração

### Padrão C: Baseado em Agente (kg-extract-agent)

Entrada: Trecho
Saída: Triplas, Contextos de Entidade
Utiliza um framework de agente para a extração

### Padrão D: Extração de Linhas (kg-extract-rows)

Entrada: Trecho
Saída: Linhas (dados estruturados, não triplas)
Utiliza uma definição de esquema para extrair registros estruturados

### Esquema: Triplas

```
Triples
├── metadata: Metadata
│   ├── id: str
│   ├── user: str
│   ├── collection: str
│   └── metadata: list[Triple]  # (set to [] by extractors)
└── triples: list[Triple]
    └── Triple
        ├── s: Term              # Subject
        ├── p: Term              # Predicate
        ├── o: Term              # Object
        └── g: str | None        # Named graph
```

### Esquema: EntityContexts

```
EntityContexts
├── metadata: Metadata
└── entities: list[EntityContext]
    └── EntityContext
        ├── entity: Term         # Entity identifier (IRI)
        ├── context: str         # Textual description for embedding
        └── chunk_id: str        # Source chunk ID (provenance)
```

### Esquema: Linhas

```
Rows
├── metadata: Metadata
├── row_schema: RowSchema
│   ├── name: str
│   ├── description: str
│   └── fields: list[Field]
└── rows: list[dict[str, str]]   # Extracted records
```

## Etapa 5: Geração de Embeddings

### Embeddings de Grafos

Converte contextos de entidades em embeddings vetoriais.

**Processo:**
1. Receber EntityContexts
2. Chamar o serviço de embeddings com o texto do contexto
3. Output GraphEmbeddings (mapeamento de entidade para vetor)

**Esquema: GraphEmbeddings**

```
GraphEmbeddings
├── metadata: Metadata
└── entities: list[EntityEmbeddings]
    └── EntityEmbeddings
        ├── entity: Term         # Entity identifier
        ├── vector: list[float]  # Embedding vector
        └── chunk_id: str        # Source chunk (provenance)
```

### Incorporações de Documentos

Converte texto em partes diretamente em incorporações vetoriais.

**Processo:**
1. Receber Parte (Chunk)
2. Chamar o serviço de incorporação com o texto da parte
3. Saída: Incorporações de Documento (DocumentEmbeddings)

**Esquema: Incorporações de Documento (DocumentEmbeddings)**

```
DocumentEmbeddings
├── metadata: Metadata
└── chunks: list[ChunkEmbeddings]
    └── ChunkEmbeddings
        ├── chunk_id: str        # Chunk identifier
        └── vector: list[float]  # Embedding vector
```

### Incorporações de Linhas

Converte campos de índice de linha em incorporações vetoriais.

**Processo:**
1. Receber Linhas
2. Incorporar campos de índice configurados
3. Saída para o armazenamento vetorial de linhas

## Fase 6: Armazenamento

### Armazenamento Triplo

Recebe: Triplas
Armazenamento: Cassandra (tabelas centradas em entidades)
Grafos nomeados separam o conhecimento central da procedência:
  `""` (padrão): Fatos de conhecimento central
  `urn:graph:source`: Procedência de extração
  `urn:graph:retrieval`: Explicabilidade em tempo de consulta

### Armazenamento Vetorial (Incorporações de Grafos)

Recebe: Incorporações de Grafos
Armazenamento: Qdrant, Milvus ou Pinecone
Indexado por: IRI da entidade
Metadados: chunk_id para procedência

### Armazenamento Vetorial (Incorporações de Documentos)

Recebe: Incorporações de Documentos
Armazenamento: Qdrant, Milvus ou Pinecone
Indexado por: chunk_id

### Armazenamento de Linhas

Recebe: Linhas
Armazenamento: Cassandra
Estrutura de tabela orientada por esquema

### Armazenamento Vetorial de Linhas

Recebe: Incorporações de linhas
Armazenamento: Banco de dados vetorial
Indexado por: campos de índice de linha

## Análise de Campos de Metadados

### Campos Ativamente Utilizados

| Campo | Uso |
|-------|-------|
| `metadata.id` | Identificador de documento/fragmento, registro, procedência |
| `metadata.user` | Multilocação, roteamento de armazenamento |
| `metadata.collection` | Seleção de coleção de destino |
| `document_id` | Referência do bibliotecário, vinculação de procedência |
| `chunk_id` | Rastreamento de procedência através do pipeline |

<<<<<<< HEAD
### Campos Potencialmente Redundantes

| Campo | Status |
|-------|--------|
| `metadata.metadata` | Definido como `[]` por todos os extratores; metadados de nível de documento agora gerenciados pelo bibliotecário no momento do envio |
=======
### Campos Removidos

| Campo | Status |
|-------|--------|
| `metadata.metadata` | Removido da classe `Metadata`. Triplas de metadados de nível de documento agora são emitidas diretamente pelo bibliotecário para o armazenamento de triplas no momento do envio, e não são transmitidas através do pipeline de extração. |
>>>>>>> e3bcbf73 (The metadata field (list of triples) in the pipeline Metadata class)

### Padrão de Campos de Bytes

Todos os campos de conteúdo (`data`, `text`, `chunk`) são `bytes`, mas são imediatamente decodificados para strings UTF-8 por todos os processadores. Nenhum processador usa bytes brutos.

## Configuração do Fluxo

Os fluxos são definidos externamente e fornecidos ao bibliotecário através do serviço de configuração. Cada fluxo especifica:

Filas de entrada (`text-load`, `document-load`)
Cadeia de processadores
Parâmetros (tamanho do fragmento, método de extração, etc.)

Padrões de fluxo de exemplo:
`pdf-graphrag`: PDF → Decodificador → Fragmentador → Definições + Relacionamentos → Incorporações
`text-graphrag`: Texto → Fragmentador → Definições + Relacionamentos → Incorporações
`pdf-ontology`: PDF → Decodificador → Fragmentador → Extração de Ontologia → Incorporações
`text-rows`: Texto → Fragmentador → Extração de Linhas → Armazenamento de Linhas
