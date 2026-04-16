---
layout: default
title: "Decodificador Universal de Documentos"
parent: "Portuguese (Beta)"
---

# Decodificador Universal de Documentos

> **Beta Translation:** This document was translated via Machine Learning and as such may not be 100% accurate. All non-English languages are currently classified as Beta.

## Título

Decodificador universal de documentos alimentado por `unstructured` — ingira qualquer formato de documento comum
através de um único serviço com total rastreabilidade e integração com o sistema de gerenciamento de informações,
registrando as posições de origem como metadados de gráfico de conhecimento para
rastreabilidade de ponta a ponta.

## Problema

Atualmente, o TrustGraph possui um decodificador específico para PDF. Suportar formatos adicionais
(DOCX, XLSX, HTML, Markdown, texto simples, PPTX, etc.) requer
ou a escrita de um novo decodificador para cada formato ou a adoção de uma biblioteca de extração universal.
Cada formato tem uma estrutura diferente — alguns são baseados em páginas, outros não — e a cadeia de rastreabilidade
deve registrar de onde em cada documento original cada trecho de texto extraído se originou.


## Abordagem

### Biblioteca: `unstructured`

Utilize `unstructured.partition.auto.partition()`, que detecta automaticamente o formato
a partir do tipo MIME ou da extensão do arquivo e extrai elementos estruturados
(Título, TextoNarrativo, Tabela, ItemDeLista, etc.). Cada elemento carrega
metadados, incluindo:

`page_number` (para formatos baseados em páginas, como PDF, PPTX)
`element_id` (único para cada elemento)
`coordinates` (caixa delimitadora para PDFs)
`text` (o conteúdo de texto extraído)
`category` (tipo de elemento: Título, TextoNarrativo, Tabela, etc.)

### Tipos de Elementos

`unstructured` extrai elementos tipados de documentos. Cada elemento tem
uma categoria e metadados associados:

**Elementos de texto:**
`Title` — títulos de seções
`NarrativeText` — parágrafos do corpo do texto
`ListItem` — itens de listas (com marcadores/numerados)
`Header`, `Footer` — cabeçalhos/rodapés de página
`FigureCaption` — legendas para figuras/imagens
`Formula` — expressões matemáticas
`Address`, `EmailAddress` — informações de contato
`CodeSnippet` — blocos de código (do Markdown)

**Tabelas:**
`Table` — dados tabulares estruturados. `unstructured` fornece ambos
  `element.text` (texto simples) e `element.metadata.text_as_html`
  (HTML completo `<table>` com linhas, colunas e cabeçalhos preservados).
  Para formatos com estrutura de tabela explícita (DOCX, XLSX, HTML), a
  extração é altamente confiável. Para PDFs, a detecção de tabelas depende da
  estratégia `hi_res` com análise de layout.

**Imagens:**
`Image` — imagens incorporadas detectadas por meio de análise de layout (requer
  `hi_res` estratégia). Com `extract_image_block_to_payload=True`,
  retorna os dados da imagem como base64 em `element.metadata.image_base64`.
  O texto OCR da imagem está disponível em `element.text`.

### Tratamento de Tabelas

Tabelas são um tipo de saída de primeira classe. Quando o decodificador encontra um elemento `Table`,
ele preserva a estrutura HTML em vez de converter para
texto simples. Isso fornece ao extrator LLM downstream uma entrada muito melhor
para extrair conhecimento estruturado de dados tabulares.

O texto da página/seção é montado da seguinte forma:
Elementos de texto: texto simples, unidos por quebras de linha
Elementos de tabela: marcação de tabela HTML de `text_as_html`, envolvida em um
  marcador `<table>` para que o LLM possa distinguir tabelas de texto narrativo

Por exemplo, uma página com um título, um parágrafo e uma tabela produz:

```
Financial Overview

Revenue grew 15% year-over-year driven by enterprise adoption.

<table>
<tr><th>Quarter</th><th>Revenue</th><th>Growth</th></tr>
<tr><td>Q1</td><td>$12M</td><td>12%</td></tr>
<tr><td>Q2</td><td>$14M</td><td>17%</td></tr>
</table>
```

Isso preserva a estrutura da tabela por meio da divisão em partes e no processo de extração
pipeline, onde o LLM pode extrair relacionamentos diretamente de
células estruturadas, em vez de adivinhar o alinhamento das colunas a partir de
espaços em branco.

### Tratamento de Imagens

As imagens são extraídas e armazenadas no sistema como documentos filhos
com `document_type="image"` e um ID `urn:image:{uuid}`. Elas recebem
triplas de procedência com o tipo `tg:Image`, vinculadas à página/seção pai
por meio de `prov:wasDerivedFrom`. Os metadados da imagem (coordenadas,
dimensões, element_id) são registrados na procedência.

**É crucial que as imagens NÃO sejam emitidas como saídas do tipo TextDocument.** Elas são
armazenadas apenas — não enviadas para o chunker ou qualquer processo de texto
pipeline. Isso é intencional:

1. Ainda não existe um pipeline de processamento de imagens (a integração do modelo de visão
   é um trabalho futuro).
2. Alimentar dados de imagem em base64 ou fragmentos de OCR no processo de extração de texto
   produziria triplas de grafo de conhecimento (KG) inúteis.

As imagens também são excluídas do texto da página montado — quaisquer elementos `Image`
são ignorados silenciosamente ao concatenar os textos dos elementos para uma
página/seção. A cadeia de procedência registra que as imagens existem e onde
elas apareceram no documento, para que possam ser recuperadas por um futuro
pipeline de processamento de imagens sem reingestão do documento.

#### Trabalho futuro

Direcionar entidades `tg:Image` para um modelo de visão para descrição,
  interpretação de diagramas ou extração de dados de gráficos.
Armazenar descrições de imagens como documentos de texto filhos que são alimentados no
  processo de divisão/extração padrão.
Vincular o conhecimento extraído de volta às imagens de origem por meio da procedência.

### Estratégias de Seção

Para formatos baseados em páginas (PDF, PPTX, XLSX), os elementos são sempre agrupados
por página/slide/planilha primeiro. Para formatos não baseados em páginas (DOCX, HTML, Markdown,
etc.), o decodificador precisa de uma estratégia para dividir o documento em
seções. Isso é configurável em tempo de execução por meio de `--section-strategy`.

Cada estratégia é uma função de agrupamento sobre a lista de `unstructured`
elementos. A saída é uma lista de grupos de elementos; o restante do
pipeline (montagem de texto, armazenamento do bibliotecário, rastreabilidade, emissão de TextDocument
) é idêntico, independentemente da estratégia.

#### `whole-document` (padrão)

Emita todo o documento como uma única seção. Deixe que o
divisor de blocos (chunker) lide com toda a divisão.

Abordagem mais simples, bom ponto de partida
Pode produzir um TextDocument muito grande para arquivos grandes, mas o divisor de blocos
  lida com isso
Melhor quando você deseja o máximo de contexto por seção

#### `heading`

Divida nos elementos de cabeçalho (`Title`). Cada seção é um cabeçalho mais
todo o conteúdo até o próximo cabeçalho de nível igual ou superior. Cabeçalhos
aninhados criam seções aninhadas.

Produz unidades coerentes em termos de tópico
Funciona bem para documentos estruturados (relatórios, manuais, especificações)
Fornece ao LLM de extração o contexto do cabeçalho junto com o conteúdo
Recua para `whole-document` se nenhum cabeçalho for encontrado

#### `element-type`

Divida quando o tipo de elemento muda significativamente — especificamente,
comece uma nova seção nas transições entre texto narrativo e tabelas.
Elementos consecutivos da mesma categoria ampla (texto, texto, texto ou
tabela, tabela) permanecem agrupados.

Mantém as tabelas como seções independentes
Bom para documentos com conteúdo misto (relatórios com tabelas de dados)
As tabelas recebem atenção especial na extração

#### `count`

Agrupe um número fixo de elementos por seção. Configurável via
`--section-element-count` (padrão: 20).

Simples e previsível
Não respeita a estrutura do documento
Útil como uma opção de fallback ou para experimentação

#### `size`

Acumula elementos até que um limite de caracteres seja atingido, então inicia uma
nova seção. Respeita os limites dos elementos — nunca divide no meio de um elemento.
Configurável via `--section-max-size` (padrão: 4000 caracteres).

Produz tamanhos de seção aproximadamente uniformes
Respeita os limites dos elementos (ao contrário do "chunker" subsequente)
Bom compromisso entre estrutura e controle de tamanho
Se um único elemento exceder o limite, ele se torna sua própria seção

#### Interação com formatos baseados em página

Para formatos baseados em página, o agrupamento de páginas sempre tem prioridade.
As estratégias de seção podem ser aplicadas opcionalmente *dentro* de uma página se ela for muito
grande (por exemplo, uma página PDF com uma tabela enorme), controlado por
`--section-within-pages` (padrão: falso). Quando falso, cada página é
sempre uma seção, independentemente do tamanho.

### Detecção de Formato

O decodificador precisa saber o tipo MIME do documento para passar para
`unstructured`'s `partition()`. Dois caminhos:

**Caminho do "Librarian"** (`document_id` definido): busca os metadados do documento
  do "librarian" primeiro — isso nos dá o `kind` (tipo MIME)
  que foi registrado no momento do upload. Em seguida, busca o conteúdo do documento.
  Duas chamadas ao "librarian", mas a busca de metadados é leve.
**Caminho "inline"** (compatibilidade com versões anteriores, `data` definido): sem metadados
  disponíveis na mensagem. Use `python-magic` para detectar o formato
  a partir dos bytes do conteúdo como uma alternativa.

Não são necessárias alterações no esquema `Document` — o bibliotecário já armazena o tipo MIME.


### Arquitetura

Um único serviço `universal-decoder` que:

1. Recebe uma mensagem `Document` (inline ou via referência ao bibliotecário).
2. Se o caminho for o do bibliotecário: busca os metadados do documento (obtém o tipo MIME), então
   busca o conteúdo. Se o caminho for inline: detecta o formato a partir dos bytes do conteúdo.
3. Chama `partition()` para extrair os elementos.
4. Agrupa elementos: por página para formatos baseados em página, por estratégia de seção configurada para formatos não baseados em página.
   seção.
5. Para cada página/seção:
   Gera um ID `urn:page:{uuid}` ou `urn:section:{uuid}`
   Monta o texto da página: narrativa como texto simples, tabelas como HTML,
     imagens ignoradas
   Calcula os deslocamentos de caracteres para cada elemento dentro do texto da página.
   Salva no "librarian" como documento filho.
   Emite triplas de procedência com metadados posicionais.
   Envia `TextDocument` para o processo de divisão em partes (chunking).
6. Para cada elemento de imagem:
   Gera um ID `urn:image:{uuid}`.
   Salva os dados da imagem no "librarian" como documento filho.
   Emite triplas de procedência (armazenadas apenas, não enviadas para o processo de divisão em partes).

### Manipulação de Formato

| Formato   | Tipo MIME                          | Baseado em Página | Notas                          |
|----------|------------------------------------|------------|--------------------------------|
| PDF      | application/pdf                    | Sim        | Agrupamento por página              |
| DOCX     | application/vnd.openxmlformats...  | Não         | Usa estratégia de seção          |
| PPTX     | application/vnd.openxmlformats...  | Sim        | Agrupamento por slide             |
| XLSX/XLS | application/vnd.openxmlformats...  | Sim        | Agrupamento por planilha             |
| HTML     | text/html                          | Não         | Usa estratégia de seção          |
| Markdown | text/markdown                      | Não         | Usa estratégia de seção          |
| Texto Simples | text/plain                         | Não         | Usa estratégia de seção          |
| CSV      | text/csv                           | Não         | Usa estratégia de seção          |
| RST      | text/x-rst                         | Não         | Usa estratégia de seção          |
| RTF      | application/rtf                    | Não         | Usa estratégia de seção          |
| ODT      | application/vnd.oasis...           | Não         | Usa estratégia de seção          |
| TSV      | text/tab-separated-values          | Não         | Usa estratégia de seção          |

### Metadados de Proveniência

Cada entidade de página/seção registra metadados de posição como triplas de proveniência
em `GRAPH_SOURCE`, permitindo rastreabilidade completa desde as triplas do grafo
até as posições no documento de origem.

#### Campos existentes (já em `derived_entity_triples`)

`page_number` — número da página/planilha/slide (indexado a partir de 1, apenas para documentos baseados em página)
`char_offset` — deslocamento de caractere desta página/seção dentro do
  texto completo do documento
`char_length` — comprimento do caractere do texto desta página/seção

#### Novos campos (extender `derived_entity_triples`)

`mime_type` — formato original do documento (por exemplo, `application/pdf`)
`element_types` — lista separada por vírgula de categorias de `unstructured`
  encontradas nesta página/seção (por exemplo, "Título,TextoNarrativo,Tabela")
`table_count` — número de tabelas nesta página/seção
`image_count` — número de imagens nesta página/seção

Estes requerem novos predicados do namespace TG:

```
TG_SECTION_TYPE  = "https://trustgraph.ai/ns/Section"
TG_IMAGE_TYPE    = "https://trustgraph.ai/ns/Image"
TG_ELEMENT_TYPES = "https://trustgraph.ai/ns/elementTypes"
TG_TABLE_COUNT   = "https://trustgraph.ai/ns/tableCount"
TG_IMAGE_COUNT   = "https://trustgraph.ai/ns/imageCount"
```

Esquema URN de imagem: `urn:image:{uuid}`

(`TG_MIME_TYPE` já existe.)

#### Novo tipo de entidade

Para formatos não paginados (DOCX, HTML, Markdown, etc.) onde o decodificador
emite todo o documento como uma única unidade em vez de dividi-lo por
página, a entidade recebe um novo tipo:

```
TG_SECTION_TYPE = "https://trustgraph.ai/ns/Section"
```

Isso distingue seções de páginas ao consultar a procedência:

| Entidade | Tipo | Quando usado |
|----------|-----------------------------|----------------------------------------|
| Documento | `tg:Document` | Arquivo original carregado |
| Página | `tg:Page` | Formatos baseados em páginas (PDF, PPTX, XLSX) |
| Seção | `tg:Section` | Formatos não baseados em páginas (DOCX, HTML, MD, etc.) |
| Imagem | `tg:Image` | Imagens incorporadas (armazenadas, não processadas) |
| Trecho | `tg:Chunk` | Saída do processador de trechos |
| Subgrafo | `tg:Subgraph` | Saída da extração de grafo de conhecimento |

O tipo é definido pelo decodificador com base em se está agrupando por página
ou emitindo uma seção de documento inteiro. `derived_entity_triples` recebe
um parâmetro booleano opcional `section` — quando verdadeiro, a entidade é
classificada como `tg:Section` em vez de `tg:Page`.

#### Cadeia completa de procedência

```
KG triple
  → subgraph (extraction provenance)
    → chunk (char_offset, char_length within page)
      → page/section (page_number, char_offset, char_length within doc, mime_type, element_types)
        → document (original file in librarian)
```

Cada link é um conjunto de triplas no grafo nomeado `GRAPH_SOURCE`.

### Configuração do Serviço

Argumentos de linha de comando:

```
--strategy              Partitioning strategy: auto, hi_res, fast (default: auto)
--languages             Comma-separated OCR language codes (default: eng)
--section-strategy      Section grouping: whole-document, heading, element-type,
                        count, size (default: whole-document)
--section-element-count Elements per section for 'count' strategy (default: 20)
--section-max-size      Max chars per section for 'size' strategy (default: 4000)
--section-within-pages  Apply section strategy within pages too (default: false)
```

Além dos argumentos padrão `FlowProcessor` e da fila de bibliotecários.

### Integração de Fluxo

O decodificador universal ocupa a mesma posição no fluxo de processamento
que o decodificador PDF atual:

```
Document → [universal-decoder] → TextDocument → [chunker] → Chunk → ...
```

Ele registra:
`input` consumidor (schema de documento)
`output` produtor (schema TextDocument)
`triples` produtor (schema de triplas)
Requisição/resposta do bibliotecário (para busca e armazenamento de documentos filhos)

### Implantação

Novo contêiner: `trustgraph-flow-universal-decoder`
Dependência: `unstructured[all-docs]` (inclui PDF, DOCX, PPTX, etc.)
Pode ser executado em conjunto ou substituir o decodificador PDF existente, dependendo
  da configuração do fluxo
O decodificador PDF existente permanece disponível para ambientes onde
  as dependências `unstructured` são muito pesadas

### O que Muda

| Componento | Alteração |
|------------------------------|-------------------------------------------------|
| `provenance/namespaces.py` | Adicionar `TG_SECTION_TYPE`, `TG_IMAGE_TYPE`, `TG_ELEMENT_TYPES`, `TG_TABLE_COUNT`, `TG_IMAGE_COUNT` |
| `provenance/triples.py` | Adicionar argumentos `mime_type`, `element_types`, `table_count`, `image_count` (kwargs) |
| `provenance/__init__.py` | Exportar novas constantes |
| Novo: `decoding/universal/` | Novo módulo de serviço de decodificação |
| `setup.cfg` / `pyproject` | Adicionar dependência `unstructured[all-docs]` |
| Docker | Nova imagem de contêiner |
| Definições de fluxo | Conectar universal-decoder como entrada de documento |

### O que não muda

Chunker (recebe TextDocument, funciona como antes)
Extratores subsequentes (recebem Chunk, inalterados)
Librarian (armazena documentos filhos, inalterado)
Schema (Document, TextDocument, Chunk inalterados)
Proveniência em tempo de consulta (inalterado)

## Riscos

`unstructured[all-docs]` tem muitas dependências (poppler, tesseract,
  libreoffice para alguns formatos). A imagem do contêiner será maior.
  Mitigação: oferecer uma variante de `[light]` sem dependências de OCR/office.
Alguns formatos podem produzir extração de texto de baixa qualidade (PDFs digitalizados sem
  OCR, layouts complexos de XLSX). Mitigação: parâmetro `strategy` configurável
  e o decodificador OCR Mistral existente permanece disponível
  para OCR de PDF de alta qualidade.
As atualizações de versão de `unstructured` podem alterar os metadados dos elementos.
  Mitigação: fixar a versão, testar a qualidade da extração por formato.
