# Armazenamento de Grafos de Conhecimento Centrados em Entidades no Cassandra

## Visão Geral

Este documento descreve um modelo de armazenamento para grafos de conhecimento no estilo RDF no Apache Cassandra. O modelo usa uma abordagem **centrada em entidades**, onde cada entidade conhece cada quádrupla em que participa e o papel que desempenha. Isso substitui uma abordagem tradicional de permutação SPO em várias tabelas por apenas duas tabelas.

## Contexto e Motivação

### A Abordagem Tradicional

Um armazenamento RDF padrão no Cassandra requer várias tabelas desnormalizadas para cobrir padrões de consulta — normalmente 6 ou mais tabelas representando diferentes permutações de Sujeito, Predicado, Objeto e Conjunto de Dados (SPOD). Cada quádrupla é escrita em todas as tabelas, resultando em uma amplificação de escrita significativa, sobrecarga operacional e complexidade do esquema.

Além disso, a resolução de rótulos (busca de nomes legíveis para humanos para entidades) requer consultas separadas de ida e volta, o que é particularmente caro em casos de uso de IA e GraphRAG, onde os rótulos são essenciais para o contexto do LLM.

### A Perspectiva Centrada na Entidade

Cada quádrupla `(D, S, P, O)` envolve até 4 entidades. Ao escrever uma linha para a participação de cada entidade na quádrupla, garantimos que **qualquer consulta com pelo menos um elemento conhecido atingirá uma chave de partição**. Isso cobre todos os 16 padrões de consulta com uma única tabela de dados.

Benefícios principais:

**2 tabelas** em vez de 7+
**4 gravações por quádrupla** em vez de 6+
**Resolução de rótulos gratuita** — os rótulos de uma entidade estão localizados com seus relacionamentos, aquecendo naturalmente o cache da aplicação
**Todos os 16 padrões de consulta** atendidos por leituras de partição única
**Operações mais simples** — uma única tabela de dados para ajustar, compactar e reparar

## Esquema

### Tabela 1: quads_by_entity

A tabela de dados primária. Cada entidade tem uma partição contendo todas as quádruplas em que participa. Nomeada para refletir o padrão de consulta (busca por entidade).
Saída do contrato (deve seguir exatamente o formato abaixo).
```sql
CREATE TABLE quads_by_entity (
    collection text,       -- Collection/tenant scope (always specified)
    entity     text,       -- The entity this row is about
    role       text,       -- 'S', 'P', 'O', 'G' — how this entity participates
    p          text,       -- Predicate of the quad
    otype      text,       -- 'U' (URI), 'L' (literal), 'T' (triple/reification)
    s          text,       -- Subject of the quad
    o          text,       -- Object of the quad
    d          text,       -- Dataset/graph of the quad
    dtype      text,       -- XSD datatype (when otype = 'L'), e.g. 'xsd:string'
    lang       text,       -- Language tag (when otype = 'L'), e.g. 'en', 'fr'
    PRIMARY KEY ((collection, entity), role, p, otype, s, o, d, dtype, lang)
);
```

**Chave de partição**: `(collection, entity)` — restrita à coleção, uma partição por entidade.

**Justificativa para a ordem das colunas de agrupamento**:

1. **role** — a maioria das consultas começa com "onde esta entidade é um sujeito/objeto"
2. **p** — próximo filtro mais comum, "me dê todas as relações `knows`"
3. **otype** — permite filtrar por relações com valor URI versus relações com valor literal
4. **s, o, d** — colunas restantes para garantir a unicidade
5. **dtype, lang** — distingue literais com o mesmo valor, mas com metadados de tipo diferentes (por exemplo, `"thing"` vs `"thing"@en` vs `"thing"^^xsd:string`)

### Tabela 2: quads_by_collection

Suporta consultas e exclusões no nível da coleção. Fornece um manifesto de todos os quads pertencentes a uma coleção. Nomeado para refletir o padrão de consulta (pesquisa por coleção).

```sql
CREATE TABLE quads_by_collection (
    collection text,
    d          text,       -- Dataset/graph of the quad
    s          text,       -- Subject of the quad
    p          text,       -- Predicate of the quad
    o          text,       -- Object of the quad
    otype      text,       -- 'U' (URI), 'L' (literal), 'T' (triple/reification)
    dtype      text,       -- XSD datatype (when otype = 'L')
    lang       text,       -- Language tag (when otype = 'L')
    PRIMARY KEY (collection, d, s, p, o, otype, dtype, lang)
);
```

Agrupados primeiro por conjunto de dados, permitindo a exclusão em nível de coleção ou de conjunto de dados. As colunas `otype`, `dtype` e `lang` estão incluídas na chave de agrupamento para distinguir literais com o mesmo valor, mas com metadados de tipo diferentes — em RDF, `"thing"`, `"thing"@en` e `"thing"^^xsd:string` são valores semanticamente distintos.

## Caminho de Escrita

Para cada quádruplo de entrada `(D, S, P, O)` dentro de uma coleção `C`, escreva **4 linhas** em `quads_by_entity` e **1 linha** em `quads_by_collection`.

### Exemplo

Dado o quádruplo na coleção `tenant1`:

```
Dataset:  https://example.org/graph1
Subject:  https://example.org/Alice
Predicate: https://example.org/knows
Object:   https://example.org/Bob
```

Escreva 4 linhas para `quads_by_entity`:

| collection | entity | role | p | otype | s | o | d |
|---|---|---|---|---|---|---|---|
| tenant1 | https://example.org/graph1 | G | https://example.org/knows | U | https://example.org/Alice | https://example.org/Bob | https://example.org/graph1 |
| tenant1 | https://example.org/Alice | S | https://example.org/knows | U | https://example.org/Alice | https://example.org/Bob | https://example.org/graph1 |
| tenant1 | https://example.org/knows | P | https://example.org/knows | U | https://example.org/Alice | https://example.org/Bob | https://example.org/graph1 |
| tenant1 | https://example.org/Bob | O | https://example.org/knows | U | https://example.org/Alice | https://example.org/Bob | https://example.org/graph1 |

Escreva 1 linha para `quads_by_collection`:

| collection | d | s | p | o | otype | dtype | lang |
|---|---|---|---|---|---|---|---|
| tenant1 | https://example.org/graph1 | https://example.org/Alice | https://example.org/knows | https://example.org/Bob | U | | |

### Exemplo Literal

Para uma tripla de rótulo:

```
Dataset:  https://example.org/graph1
Subject:  https://example.org/Alice
Predicate: http://www.w3.org/2000/01/rdf-schema#label
Object:   "Alice Smith" (lang: en)
```

O `otype` é `'L'`, `dtype` é `'xsd:string'`, e `lang` é `'en'`. O valor literal `"Alice Smith"` é armazenado em `o`. Apenas 3 linhas são necessárias em `quads_by_entity` — nenhuma linha é escrita para o literal como entidade, pois os literais não são entidades consultáveis independentes.

## Padrões de Consulta

### Todos os 16 Padrões DSPO

Na tabela abaixo, "Prefixo perfeito" significa que a consulta usa um prefixo contíguo das colunas de agrupamento. "Leitura de partição + filtro" significa que o Cassandra lê uma fatia de uma partição e filtra na memória — ainda eficiente, mas não uma correspondência de prefixo pura.

| # | Conhecido | Consulta de entidade | Prefixo de agrupamento | Eficiência |
|---|---|---|---|---|
| 1 | D,S,P,O | entidade=S, role='S', p=P | Correspondência completa | Prefixo perfeito |
| 2 | D,S,P,? | entidade=S, role='S', p=P | Filtro em D | Leitura de partição + filtro |
| 3 | D,S,?,O | entidade=S, role='S' | Filtro em D, O | Leitura de partição + filtro |
| 4 | D,?,P,O | entidade=O, role='O', p=P | Filtro em D | Leitura de partição + filtro |
| 5 | ?,S,P,O | entidade=S, role='S', p=P | Filtro em O | Leitura de partição + filtro |
| 6 | D,S,?,? | entidade=S, role='S' | Filtro em D | Leitura de partição + filtro |
| 7 | D,?,P,? | entidade=P, role='P' | Filtro em D | Leitura de partição + filtro |
| 8 | D,?,?,O | entidade=O, role='O' | Filtro em D | Leitura de partição + filtro |
| 9 | ?,S,P,? | entidade=S, role='S', p=P | — | **Prefixo perfeito** |
| 10 | ?,S,?,O | entidade=S, role='S' | Filtro em O | Leitura de partição + filtro |
| 11 | ?,?,P,O | entidade=O, role='O', p=P | — | **Prefixo perfeito** |
| 12 | D,?,?,? | entidade=D, role='G' | — | **Prefixo perfeito** |
| 13 | ?,S,?,? | entidade=S, role='S' | — | **Prefixo perfeito** |
| 14 | ?,?,P,? | entidade=P, role='P' | — | **Prefixo perfeito** |
| 15 | ?,?,?,O | entidade=O, role='O' | — | **Prefixo perfeito** |
| 16 | ?,?,?,? | — | Leitura completa | Apenas exploração |

**Resultado chave**: 7 dos 15 padrões não triviais são correspondências perfeitas de prefixo de agrupamento. Os 8 restantes são leituras de partição única com filtragem dentro da partição. Cada consulta com pelo menos um elemento conhecido atinge uma chave de partição.

O padrão 16 (?,?,?,?) não ocorre na prática, pois a coleção é sempre especificada, reduzindo-o ao padrão 12.

### Exemplos Comuns de Consulta

**Tudo sobre uma entidade:**

```sql
SELECT * FROM quads_by_entity
WHERE collection = 'tenant1' AND entity = 'https://example.org/Alice';
```

**Todos os relacionamentos de saída para uma entidade:**

```sql
SELECT * FROM quads_by_entity
WHERE collection = 'tenant1' AND entity = 'https://example.org/Alice'
AND role = 'S';
```

**Predicado específico para uma entidade:**

```sql
SELECT * FROM quads_by_entity
WHERE collection = 'tenant1' AND entity = 'https://example.org/Alice'
AND role = 'S' AND p = 'https://example.org/knows';
```

**Rótulo para uma entidade (idioma específico):**

```sql
SELECT * FROM quads_by_entity
WHERE collection = 'tenant1' AND entity = 'https://example.org/Alice'
AND role = 'S' AND p = 'http://www.w3.org/2000/01/rdf-schema#label'
AND otype = 'L';
```

Em seguida, filtre por aplicação no lado do cliente, se necessário, usando `lang = 'en'`.

**Apenas relacionamentos com valores URI (links de entidade para entidade):**

```sql
SELECT * FROM quads_by_entity
WHERE collection = 'tenant1' AND entity = 'https://example.org/Alice'
AND role = 'S' AND p = 'https://example.org/knows' AND otype = 'U';
```

**Pesquisa reversa — o que aponta para esta entidade:**

```sql
SELECT * FROM quads_by_entity
WHERE collection = 'tenant1' AND entity = 'https://example.org/Bob'
AND role = 'O';
```

## Resolução de Rótulos e Aquecimento do Cache

Uma das vantagens mais significativas do modelo centrado em entidades é que **a resolução de rótulos se torna um efeito colateral gratuito**.

No modelo tradicional de várias tabelas, buscar rótulos requer consultas separadas: recuperar triplas, identificar URIs de entidades nos resultados e, em seguida, buscar `rdfs:label` para cada uma. Esse padrão N+1 é caro.

No modelo centrado em entidades, consultar uma entidade retorna **todos** os seus quadros — incluindo seus rótulos, tipos e outras propriedades. Quando o aplicativo armazena em cache os resultados das consultas, os rótulos são pré-aquecidos antes que qualquer coisa os solicite.

Dois regimes de uso confirmam que isso funciona bem na prática:

**Consultas voltadas para o usuário**: conjuntos de resultados naturalmente pequenos, rótulos essenciais. As leituras de entidades pré-aquecem o cache.
**Consultas de IA/em lote**: conjuntos de resultados grandes com limites rígidos. Os rótulos são desnecessários ou necessários apenas para um subconjunto selecionado de entidades que já estão no cache.

A preocupação teórica de resolver rótulos para conjuntos de resultados enormes (por exemplo, 30.000 entidades) é atenuada pela observação prática de que nenhum usuário humano ou de IA processa tantos rótulos de forma útil. Os limites de consulta no nível da aplicação garantem que a pressão do cache permaneça gerenciável.

## Partições Largas e Reificação

A reificação (declarações RDF-star sobre declarações) cria entidades de hub — por exemplo, um documento de origem que suporta milhares de fatos extraídos. Isso pode produzir partições largas.

Fatores atenuantes:

**Limites de consulta no nível da aplicação**: todas as consultas do GraphRAG e voltadas para o usuário impõem limites rígidos, portanto, as partições largas nunca são totalmente examinadas no caminho de leitura quente.
**O Cassandra lida com leituras parciais de forma eficiente**: uma varredura de coluna de agrupamento com uma parada antecipada é rápida, mesmo em partições grandes.
**Exclusão de coleções** (a única operação que pode percorrer partições completas) é um processo de segundo plano aceitável.

## Exclusão de Coleções

Acionada por chamada de API, é executada em segundo plano (consistência eventual).

1. Leia `quads_by_collection` para a coleção de destino para obter todos os quadros.
2. Extraia entidades exclusivas das quadros (valores s, p, o, d).
3. Para cada entidade exclusiva, exclua a partição de `quads_by_entity`.
4. Exclua as linhas de `quads_by_collection`.

A tabela `quads_by_collection` fornece o índice necessário para localizar todas as partições de entidade sem uma varredura completa da tabela. As exclusões em nível de partição são eficientes porque `(collection, entity)` é a chave da partição.

## Caminho de Migração do Modelo de Múltiplas Tabelas

O modelo centrado em entidades pode coexistir com o modelo de múltiplas tabelas existente durante a migração:

1. Implante as tabelas `quads_by_entity` e `quads_by_collection` junto com as tabelas existentes.
2. Escreva em duplicata novas quadros para ambas as tabelas antigas e novas.
3. Preencha os dados existentes nas novas tabelas.
4. Migre os caminhos de leitura um padrão de consulta por vez.
5. Desative as tabelas antigas assim que todos os caminhos de leitura forem migrados.

## Resumo

| Aspecto | Tradicional (6 tabelas) | Centrado em entidade (2 tabelas) |
|---|---|---|
| Tabelas | 7+ | 2 |
| Escritas por quadro | 6+ | 5 (4 dados + 1 manifesto) |
| Resolução de rótulos | Consultas separadas | Gratuito via aquecimento do cache |
| Padrões de consulta | 16 em 6 tabelas | 16 em 1 tabela |
| Complexidade do esquema | Alta | Baixa |
| Sobrecarga operacional | 6 tabelas para ajustar/reparar | 1 tabela de dados |
| Suporte de reificação | Complexidade adicional | Adequação natural |
| Filtragem de tipo de objeto | Não disponível | Nativo (via agrupamento de otype) |
Saída do contrato (deve seguir exatamente o formato abaixo).
