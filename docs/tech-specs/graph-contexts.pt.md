# Especificação Técnica dos Contextos de Grafos

## Visão Geral

Esta especificação descreve as alterações nos primitivos de grafo principais do TrustGraph para
estar em conformidade com o RDF 1.2 e suportar a semântica completa do Conjunto de Dados RDF. Esta é uma
alteração que causa incompatibilidade para a série de lançamento 2.x.

### Versionamento

**2.0**: Lançamento para usuários iniciais. Recursos principais disponíveis, mas pode não estar totalmente
  pronto para produção.
**2.1 / 2.2**: Lançamento para produção. Estabilidade e completude validadas.

A flexibilidade em relação à maturidade é intencional - os usuários iniciais podem acessar novos
recursos antes que todos os recursos sejam aprimorados para produção.

## Objetivos

Os principais objetivos deste trabalho são permitir metadados sobre fatos/declarações:

**Informações temporais**: Associar fatos a metadados de tempo
  Quando um fato foi considerado verdadeiro
  Quando um fato se tornou verdadeiro
  Quando um fato foi descoberto como falso

**Proveniência/Fontes**: Rastrear quais fontes suportam um fato
  "Este fato foi suportado pela fonte X"
<<<<<<< HEAD
  Vincular fatos aos documentos de origem
=======
  Vincular fatos aos seus documentos de origem
>>>>>>> 82edf2d (New md files from RunPod)

**Veracidade/Confiança**: Registrar afirmações sobre a verdade
  "A pessoa P afirmou que isso era verdade"
  "A pessoa Q afirma que isso é falso"
  Permitir pontuação de confiança e detecção de conflitos

**Hipótese**: A reificação (triplas RDF-star / citadas) é o mecanismo chave
para alcançar esses resultados, pois todos exigem fazer declarações sobre declarações.

## Contexto

Para expressar "o fato (Alice conhece Bob) foi descoberto em 2024-01-15" ou
"a fonte X suporta a afirmação (Y causa Z)", você precisa referenciar uma aresta
como algo sobre o qual você pode fazer declarações. Triplas padrão não suportam isso.

### Limitações Atuais

<<<<<<< HEAD
A classe `Value` atual em `trustgraph-base/trustgraph/schema/core/primitives.py`
=======
A classe `Value` em `trustgraph-base/trustgraph/schema/core/primitives.py`
>>>>>>> 82edf2d (New md files from RunPod)
pode representar:
Nós URI (`is_uri=True`)
Valores literais (`is_uri=False`)

O campo `type` existe, mas não é usado para representar tipos de dados XSD.

## Design Técnico

### Recursos RDF a serem Suportados

#### Recursos Principais (Relacionados aos Objetivos de Reificação)

Esses recursos estão diretamente relacionados aos objetivos de tempo, proveniência e veracidade:

1. **Triplas Citadas RDF 1.2 (RDF-star)**
Arestas que apontam para outras arestas
<<<<<<< HEAD
   Uma Tripla pode aparecer como o sujeito ou objeto de outra Tripla
=======
   Uma Tripla pode aparecer como o sujeito ou o objeto de outra Tripla
>>>>>>> 82edf2d (New md files from RunPod)
   Permite declarações sobre declarações (reificação)
   Mecanismo principal para anotar fatos individuais
   
2. **Conjunto de Dados RDF / Grafos Nomeados**
Suporte para vários grafos nomeados dentro de um conjunto de dados
   Cada grafo identificado por um IRI
   Passa de triplas (s, p, o) para quads (s, p, o, g)
   Inclui um grafo padrão, mais zero ou mais grafos nomeados
   O IRI do grafo pode ser um sujeito em declarações, por exemplo:
   O IRI do grafo pode ser o sujeito em declarações, por exemplo:
     ```
     <graph-source-A> <discoveredOn> "2024-01-15"
     <graph-source-A> <hasVeracity> "high"
     ```
   Nota: Os grafos nomeados são uma funcionalidade separada da reificação. Eles têm
     usos além da anotação de declarações (particionamento, controle de acesso, organização de conjuntos de dados)
     e devem ser tratados como uma capacidade distinta.

3. **Nós Anônimos** (Suporte Limitado)
   Nós anônimos sem um URI global
   Suportados para compatibilidade ao carregar dados RDF externos
   **Status limitado**: Sem garantias sobre a identidade estável após o carregamento
   Encontre-os por meio de consultas curinga (correspondência por conexões, não por ID)
   Não é uma funcionalidade de primeira classe - não dependa de um tratamento preciso de nós anônimos

#### Correções Oportunas (Mudança Incompatível 2.0)

Esses recursos não estão diretamente relacionados aos objetivos da reificação, mas são
melhorias valiosas a serem incluídas ao mesmo tempo em que são feitas alterações incompatíveis:

4. **Tipos de Dados Literais**
   Use corretamente o campo `type` para tipos de dados XSD
   Exemplos: xsd:string, xsd:integer, xsd:dateTime, etc.
   Corrige a limitação atual: não é possível representar datas ou inteiros corretamente

5. **Tags de Idioma**
   Suporte para atributos de idioma em literais de string (@en, @fr, etc.)
   Nota: Um literal tem uma tag de idioma OU um tipo de dados, não ambos
     (exceto para rdf:langString)
   Importante para casos de uso de IA/multilíngues

### Modelos de Dados

#### Termo (renomeado de Valor)

A classe `Value` será renomeada para `Term` para melhor refletir a terminologia RDF.
Esta renomeação tem dois propósitos:
1. Alinha a nomenclatura com os conceitos RDF (um "Termo" pode ser um IRI, literal ou nó anônimo.
   nó, ou tripla entre aspas - não apenas um "valor").
2. Exige revisão de código na interface de alteração significativa - qualquer código que ainda
   faça referência a `Value` estará visivelmente quebrado e precisará ser atualizado.

Um Termo pode representar:

**IRI/URI** - Um nó/recurso nomeado.
**Nó Anônimo** - Um nó anônimo com escopo local.
**Literal** - Um valor de dados com um dos seguintes:
  Um tipo de dados (tipo XSD), OU
  Uma etiqueta de idioma.
**Tripla Citada** - Uma tripla usada como um termo (RDF 1.2).

##### Abordagem Escolhida: Classe Única com Discriminador de Tipo

Os requisitos de serialização determinam a estrutura - um discriminador de tipo é necessário
<<<<<<< HEAD
no formato de transmissão, independentemente da representação em Python. Uma classe única com
=======
no formato de transmissão, independentemente da representação em Python. Uma única classe com
>>>>>>> 82edf2d (New md files from RunPod)
um campo de tipo é a opção mais adequada e está alinhada com o padrão atual `Value`.

Códigos de tipo de caractere único fornecem serialização compacta:

```python
from dataclasses import dataclass

# Term type constants
IRI = "i"      # IRI/URI node
BLANK = "b"    # Blank node
LITERAL = "l"  # Literal value
TRIPLE = "t"   # Quoted triple (RDF-star)

@dataclass
class Term:
    type: str = ""  # One of: IRI, BLANK, LITERAL, TRIPLE

    # For IRI terms (type == IRI)
    iri: str = ""

    # For blank nodes (type == BLANK)
    id: str = ""

    # For literals (type == LITERAL)
    value: str = ""
    datatype: str = ""   # XSD datatype URI (mutually exclusive with language)
    language: str = ""   # Language tag (mutually exclusive with datatype)

    # For quoted triples (type == TRIPLE)
    triple: "Triple | None" = None
```

Exemplos de uso:

```python
# IRI term
node = Term(type=IRI, iri="http://example.org/Alice")

# Literal with datatype
age = Term(type=LITERAL, value="42", datatype="xsd:integer")

# Literal with language tag
label = Term(type=LITERAL, value="Hello", language="en")

# Blank node
anon = Term(type=BLANK, id="_:b1")

# Quoted triple (statement about a statement)
inner = Triple(
    s=Term(type=IRI, iri="http://example.org/Alice"),
    p=Term(type=IRI, iri="http://example.org/knows"),
    o=Term(type=IRI, iri="http://example.org/Bob"),
)
reified = Term(type=TRIPLE, triple=inner)
```

##### Alternativas Consideradas

**Opção B: União de classes especializadas** (`Term = IRI | BlankNode | Literal | QuotedTriple`)
Rejeitada: A serialização ainda precisaria de um discriminador de tipo, adicionando complexidade.

**Opção C: Classe base com subclasses**
Rejeitada: Mesmo problema de serialização, além de peculiaridades da herança de dataclasses.

#### Tripla / Quádrupla

A classe `Triple` ganha um campo de grafo opcional para se tornar uma quádrupla:

```python
@dataclass
class Triple:
    s: Term | None = None    # Subject
    p: Term | None = None    # Predicate
    o: Term | None = None    # Object
    g: str | None = None     # Graph name (IRI), None = default graph
```

Decisões de design:
**Nome do campo**: `g` para consistência com `s`, `p`, `o`
**Opcional**: `None` significa o grafo padrão (sem nome)
**Tipo**: String simples (IRI) em vez de Termo
  Os nomes dos grafos são sempre IRIs
  Nodos vazios como nomes de grafos são descartados (muito confusos)
  Não há necessidade da totalidade do mecanismo de Termos

Nota: O nome da classe permanece `Triple` mesmo que tecnicamente seja um quad agora.
Isso evita mudanças e "tripla" ainda é a terminologia comum para a parte s/p/o.
O contexto do grafo é metadado sobre onde a tripla reside.

### Padrões de Consulta Candidatos

<<<<<<< HEAD
O mecanismo de consulta atual aceita combinações de termos S, P, O. Com triplas
entre aspas, uma tripla em si se torna um termo válido nessas posições. Abaixo estão
padrões de consulta candidatos que suportam os objetivos originais.
=======
O mecanismo de consulta atual aceita combinações de termos S, P, O. Com triplas entre aspas,
uma tripla se torna um termo válido nessas posições. Abaixo estão os padrões de consulta
candidatos que suportam os objetivos originais.
>>>>>>> 82edf2d (New md files from RunPod)

#### Semântica do Parâmetro do Grafo

Seguindo as convenções do SPARQL para compatibilidade com versões anteriores:

**`g` omitido / Nenhum**: Consulta apenas o grafo padrão
**`g` = IRI específico**: Consulta apenas aquele grafo nomeado
**`g` = curinga / `*`**: Consulta em todos os grafos (equivalente ao SPARQL
  `GRAPH ?g { ... }`)

Isso mantém as consultas simples simples e torna as consultas de grafos nomeados opcionais.

Consultas entre grafos (g=curinga) são totalmente suportadas. O esquema do Cassandra
inclui tabelas dedicadas (SPOG, POSG, OSPG) onde g é uma coluna de agrupamento
em vez de uma chave de partição, permitindo consultas eficientes em todos os grafos.

#### Consultas Temporais

**Encontre todos os fatos descobertos após uma determinada data:**
```
S: ?                                    # any quoted triple
P: <discoveredOn>
O: > "2024-01-15"^^xsd:date             # date comparison
```

**Descubra quando um fato específico foi considerado verdadeiro:**
```
S: << <Alice> <knows> <Bob> >>          # quoted triple as subject
P: <believedTrueFrom>
O: ?                                    # returns the date
```

**Encontre fatos que se tornaram falsos:**
```
S: ?                                    # any quoted triple
P: <discoveredFalseOn>
O: ?                                    # has any value (exists)
```

#### Consultas de Proveniência

**Encontre todos os fatos suportados por uma fonte específica:**
```
S: ?                                    # any quoted triple
P: <supportedBy>
O: <source:document-123>
```

**Descubra quais fontes sustentam um fato específico:**
```
S: << <DrugA> <treats> <DiseaseB> >>    # quoted triple as subject
P: <supportedBy>
O: ?                                    # returns source IRIs
```

#### Consultas de Veracidade

**Encontre as afirmações que uma pessoa marcou como verdadeiras:**
```
S: ?                                    # any quoted triple
P: <assertedTrueBy>
O: <person:Alice>
```

**Encontre asserções conflitantes (mesmo fato, diferentes níveis de veracidade):**
```
# First query: facts asserted true
S: ?
P: <assertedTrueBy>
O: ?

# Second query: facts asserted false
S: ?
P: <assertedFalseBy>
O: ?

# Application logic: find intersection of subjects
```

**Encontre fatos com uma pontuação de confiança abaixo do limite:**
```
S: ?                                    # any quoted triple
P: <trustScore>
O: < 0.5                                # numeric comparison
```

### Arquitetura

Mudanças significativas necessárias em vários componentes:

#### Este Repositório (trustgraph)

**Primitivos de esquema** (`trustgraph-base/trustgraph/schema/core/primitives.py`)
  Renomeação de Value → Term
  Nova estrutura de Term com discriminador de tipo
  Triple ganha campo `g` para contexto do grafo

**Tradutores de mensagens** (`trustgraph-base/trustgraph/messaging/translators/`)
  Atualização para novas estruturas de Term/Triple
  Serialização/desserialização para novos campos

**Componentes de gateway**
  Lidar com novas estruturas de Term e quad

**Núcleos de conhecimento**
  Mudanças no núcleo para suportar quads e reificação

**Gerenciador de conhecimento**
  Mudanças de esquema se propagam aqui

**Camadas de armazenamento**
  Cassandra: Redesenho do esquema (veja Detalhes de Implementação)
  Outros backends: Adiado para fases posteriores

**Utilitários de linha de comando**
  Atualização para novas estruturas de dados

**Documentação da API REST**
  Atualizações da especificação OpenAPI

#### Repositórios Externos

**API Python** (este repositório)
  Atualizações da biblioteca cliente para novas estruturas

**APIs TypeScript** (repositório separado)
  Atualizações da biblioteca cliente

**Workbench** (repositório separado)
  Mudanças significativas no gerenciamento de estado

### APIs

#### API REST

Documentado na especificação OpenAPI
Será necessário atualizar para novas estruturas de Term/Triple
Novos endpoints podem ser necessários para operações de contexto do grafo

#### API Python (este repositório)

Mudanças na biblioteca cliente para corresponder a novos primitivos
Mudanças significativas em Term (era Value) e Triple

#### API TypeScript (repositório separado)

Mudanças paralelas à API Python
Coordenação de lançamento separada

#### Workbench (repositório separado)

Mudanças significativas no gerenciamento de estado
Atualizações da interface do usuário para recursos de contexto do grafo

### Detalhes de Implementação

#### Implementação de Armazenamento em Fases

Existem vários backends de armazenamento de grafos (Cassandra, Neo4j, etc.). A implementação
seguirá em fases:

1. **Fase 1: Cassandra**
   Começar com o armazenamento Cassandra próprio
<<<<<<< HEAD
   O controle total sobre a camada de armazenamento permite iteração rápida
=======
   Controle total sobre a camada de armazenamento permite iteração rápida
>>>>>>> 82edf2d (New md files from RunPod)
   O esquema será redesenhado do zero para quads + reificação
   Validar o modelo de dados e os padrões de consulta em relação a casos de uso reais

#### Design de Esquema do Cassandra

O Cassandra requer múltiplas tabelas para suportar diferentes padrões de acesso a consultas
(cada tabela consulta de forma eficiente pela sua chave de partição + colunas de agrupamento).

##### Padrões de Consulta

<<<<<<< HEAD
Com quads (g, s, p, o), cada posição pode ser especificada ou curinga, dando
=======
Com tuplas (g, s, p, o), cada posição pode ser especificada ou curinga, dando
>>>>>>> 82edf2d (New md files from RunPod)
16 padrões de consulta possíveis:

| # | g | s | p | o | Descrição |
|---|---|---|---|---|-------------|
<<<<<<< HEAD
| 1 | ? | ? | ? | ? | Todos os quads |
=======
| 1 | ? | ? | ? | ? | Todas as tuplas |
>>>>>>> 82edf2d (New md files from RunPod)
| 2 | ? | ? | ? | o | Por objeto |
| 3 | ? | ? | p | ? | Por predicado |
| 4 | ? | ? | p | o | Por predicado + objeto |
| 5 | ? | s | ? | ? | Por sujeito |
| 6 | ? | s | ? | o | Por sujeito + objeto |
| 7 | ? | s | p | ? | Por sujeito + predicado |
| 8 | ? | s | p | o | Tripla completa (quais grafos?) |
| 9 | g | ? | ? | ? | Por grafo |
| 10 | g | ? | ? | o | Por grafo + objeto |
| 11 | g | ? | p | ? | Por grafo + predicado |
| 12 | g | ? | p | o | Por grafo + predicado + objeto |
| 13 | g | s | ? | ? | Por grafo + sujeito |
| 14 | g | s | ? | o | Por grafo + sujeito + objeto |
| 15 | g | s | p | ? | Por grafo + sujeito + predicado |
<<<<<<< HEAD
| 16 | g | s | p | o | Quad exato |

##### Design de Tabela

Restrição do Cassandra: Você só pode consultar de forma eficiente pela chave de partição e, em seguida,
filtrar nas colunas de agrupamento da esquerda para a direita. Para consultas com curinga "g", "g" deve ser
uma coluna de agrupamento. Para consultas com "g" especificado, "g" na chave de partição é mais
=======
| 16 | g | s | p | o | Tupla exata |

##### Design da Tabela

Restrição do Cassandra: Você só pode consultar de forma eficiente pela chave de partição e, em seguida,
filtrar nas colunas de agrupamento da esquerda para a direita. Para consultas com curinga "g", "g" deve estar
em uma coluna de agrupamento. Para consultas com "g" especificado, "g" na chave de partição é mais
>>>>>>> 82edf2d (New md files from RunPod)
eficiente.

**Duas famílias de tabelas necessárias:**

<<<<<<< HEAD
**Família A: consultas com curinga "g"** (g em colunas de agrupamento)
=======
**Família A: Consultas com curinga "g"** (g em colunas de agrupamento)
>>>>>>> 82edf2d (New md files from RunPod)

| Tabela | Partição | Agrupamento | Suporta padrões |
|-------|-----------|------------|-------------------|
| SPOG | (user, collection, s) | p, o, g | 5, 7, 8 |
| POSG | (user, collection, p) | o, s, g | 3, 4 |
| OSPG | (user, collection, o) | s, p, g | 2, 6 |

<<<<<<< HEAD
**Família B: consultas com "g" especificado** (g na chave de partição)
=======
**Família B: Consultas com "g" especificado** (g na chave de partição)
>>>>>>> 82edf2d (New md files from RunPod)

| Tabela | Partição | Agrupamento | Suporta padrões |
|-------|-----------|------------|-------------------|
| GSPO | (user, collection, g, s) | p, o | 9, 13, 15, 16 |
| GPOS | (user, collection, g, p) | o, s | 11, 12 |
| GOSP | (user, collection, g, o) | s, p | 10, 14 |

**Tabela de coleção** (para iteração e exclusão em massa)

| Tabela | Partição | Agrupamento | Propósito |
|-------|-----------|------------|---------|
<<<<<<< HEAD
| COLL | (user, collection) | g, s, p, o | Enumerar todos os quads na coleção |
=======
| COLL | (user, collection) | g, s, p, o | Enumerar todas as tuplas na coleção |
>>>>>>> 82edf2d (New md files from RunPod)

##### Caminhos de Escrita e Exclusão

**Caminho de escrita**: Inserir em todas as 7 tabelas.

**Caminho de exclusão da coleção**:
1. Iterar na tabela COLL para `(user, collection)`
<<<<<<< HEAD
2. Para cada quad, excluir de todas as 6 tabelas de consulta
3. Excluir da tabela COLL (ou exclusão por intervalo)

**Caminho de exclusão de um único quad**: Excluir diretamente de todas as 7 tabelas.

##### Custo de Armazenamento

Cada quad é armazenado 7 vezes. Este é o custo da consulta flexível combinada
com exclusão eficiente da coleção.

##### Triplas Citadas no Armazenamento

O sujeito ou o objeto podem ser uma tripla em si. Opções:
=======
2. Para cada tupla, excluir de todas as 6 tabelas de consulta
3. Excluir da tabela COLL (ou exclusão por intervalo)

**Caminho de exclusão de uma única tupla**: Excluir diretamente de todas as 7 tabelas.

##### Custo de Armazenamento

Cada tupla é armazenada 7 vezes. Este é o custo da consulta flexível
combinado com a exclusão eficiente da coleção.

##### Triplas Citadas no Armazenamento

Sujeito ou objeto podem ser uma tripla em si. Opções:
>>>>>>> 82edf2d (New md files from RunPod)

**Opção A: Serializar triplas citadas para string canônica**
```
S: "<<http://ex/Alice|http://ex/knows|http://ex/Bob>>"
P: http://ex/discoveredOn
O: "2024-01-15"
G: null
```
Armazenar a tripla citada como uma string serializada nas colunas S ou O.
Consultar por correspondência exata na forma serializada.
Prós: Simples, se encaixa em padrões de índice existentes.
Contras: Não é possível consultar "encontrar triplas onde o predicado do sujeito citado é X".

**Opção B: IDs / Hashes de Triplas**
```
Triple table:
  id: hash(s,p,o,g)
  s, p, o, g: ...

Metadata table:
  subject_triple_id: <hash>
  p: http://ex/discoveredOn
  o: "2024-01-15"
```
Atribua a cada tripla um ID (hash dos componentes)
As referências de metadados de reificação referenciam as triplas por ID
Prós: Separação limpa, pode indexar os IDs das triplas
Contras: Requer o cálculo/gerenciamento da identidade da tripla, pesquisas em duas fases

**Recomendação**: Comece com a Opção A (strings serializadas) para simplificar.
A Opção B pode ser necessária se forem necessários padrões de consulta avançados sobre triplas com aspas
componentes.

2. **Fase 2+: Outros Backends**
   Neo4j e outros armazenamentos implementados em estágios subsequentes
   As lições aprendidas com o Cassandra informam essas implementações

Esta abordagem reduz os riscos do projeto, validando em um backend totalmente controlado
antes de implementar em todos os armazenamentos.

<<<<<<< HEAD
#### Renomear Classe de Valor → Termo
=======
#### Renomeação de Valor → Termo
>>>>>>> 82edf2d (New md files from RunPod)

A classe `Value` será renomeada para `Term`. Isso afeta aproximadamente 78 arquivos em
todo o código-fonte. A renomeação funciona como um fator de força: qualquer código que ainda use
`Value` pode ser identificado imediatamente como precisando de revisão/atualização para compatibilidade com a versão 2.0


## Considerações de Segurança

Os grafos nomeados não são um recurso de segurança. Usuários e coleções permanecem
como os limites de segurança. Os grafos nomeados são puramente para organização de dados e
suporte de reificação.

## Considerações de Desempenho

Triplas com aspas adicionam profundidade de aninhamento - podem afetar o desempenho da consulta
Estratégias de indexação de grafos nomeados necessárias para consultas eficientes com escopo de grafo
O design do esquema do Cassandra precisará acomodar o armazenamento de quads de forma eficiente

### Limite do Armazenamento Vetorial

Os armazenamentos vetoriais sempre referenciam apenas IRIs:
Nunca arestas (triplas com aspas)
Nunca valores literais
Nunca nós vazios

<<<<<<< HEAD
Isso mantém o armazenamento vetorial simples - ele lida com a similaridade semântica de entidades nomeadas. A estrutura do grafo lida com relacionamentos, reificação e metadados.
=======
Isso mantém o armazenamento vetorial simples - ele lida com a similaridade semântica de entidades nomeadas.
A estrutura do grafo lida com relacionamentos, reificação e metadados.
>>>>>>> 82edf2d (New md files from RunPod)
Triplas com aspas e grafos nomeados não complicam as operações vetoriais.

## Estratégia de Teste

Use a estratégia de teste existente. Como esta é uma alteração disruptiva, concentre-se extensivamente no
conjunto de testes de ponta a ponta para validar que as novas estruturas funcionam corretamente em
todos os componentes.

<<<<<<< HEAD

=======
>>>>>>> 82edf2d (New md files from RunPod)
## Plano de Migração

A versão 2.0 é uma versão disruptiva; nenhuma compatibilidade com versões anteriores é necessária
Os dados existentes podem precisar ser migrados para um novo esquema (a ser definido com base no design final)
Considere ferramentas de migração para converter triplas existentes

## Perguntas Abertas

**Nós vazios**: Suporte limitado confirmado. Pode ser necessário decidir sobre
<<<<<<< HEAD
  estratégia de skolemização (gerar IRIs na carga, ou preservar os IDs dos nós vazios).
=======
  estratégia de skolemização (gerar IRIs na carga ou preservar os IDs dos nós vazios).
>>>>>>> 82edf2d (New md files from RunPod)
**Sintaxe de consulta**: Qual é a sintaxe concreta para especificar triplas com aspas
  em consultas? É necessário definir a API de consulta.
~~**Vocabulário de predicados**~~: Resolvido. Qualquer predicado RDF válido é permitido,
  incluindo vocabulários personalizados do usuário. Mínimas suposições sobre a validade do RDF.
  Pouquíssimos valores fixos (por exemplo, `rdfs:label` usado em alguns lugares).
<<<<<<< HEAD
  Estratégia: evite fixar qualquer coisa, a menos que seja absolutamente necessário.
~~**Impacto no armazenamento vetorial**~~: Resolvido. Os armazenamentos vetoriais sempre apontam para IRIs
  apenas - nunca arestas, literais ou nós vazios. Triplas com aspas e
  a reificação não afetam o armazenamento vetorial.
~~**Semântica do grafo nomeado**~~: Resolvido. As consultas padrão
  para o grafo padrão (corresponde ao comportamento do SPARQL, compatível com versões anteriores). Parâmetro de grafo explícito
=======
  Estratégia: evitar fixar qualquer coisa, a menos que seja absolutamente necessário.
~~**Impacto no armazenamento vetorial**~~: Resolvido. Os armazenamentos vetoriais sempre apontam para IRIs
  apenas - nunca arestas, literais ou nós vazios. Triplas com aspas e
  a reificação não afetam o armazenamento vetorial.
~~**Semântica do grafo nomeado**~~: Resolvido. As consultas usam o grafo padrão
  (corresponde ao comportamento do SPARQL, compatível com versões anteriores). Parâmetro de grafo explícito
>>>>>>> 82edf2d (New md files from RunPod)
  necessário para consultar grafos nomeados ou todos os grafos.

## Referências

[Conceitos RDF 1.2](https://www.w3.org/TR/rdf12-concepts/)
[RDF-star e SPARQL-star](https://w3c.github.io/rdf-star/)
[Conjunto de dados RDF](https://www.w3.org/TR/rdf11-concepts/#section-dataset)
