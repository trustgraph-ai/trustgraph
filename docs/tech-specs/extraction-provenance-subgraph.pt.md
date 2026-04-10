# Proveniência de Extração: Modelo de Subgrafo

## Problema

A proveniência em tempo de extração atualmente gera uma reificação completa para cada
tripla extraída: um `stmt_uri`, `activity_uri` e metadados PROV-O associados para cada
fato de conhecimento. O processamento de um bloco que gera 20 relacionamentos produz aproximadamente 220 triplas de proveniência, além de
aproximadamente 20 triplas de conhecimento — uma sobrecarga de aproximadamente 10:1.


Isso é caro (armazenamento, indexação, transmissão) e semanticamente
impreciso. Cada bloco é processado por uma única chamada de LLM que produz
todas as suas triplas em uma única transação. O modelo atual, baseado em tripla,
obscure isso, criando a ilusão de 20 eventos de extração independentes.


Além disso, dois dos quatro processadores de extração (kg-extract-ontology,
kg-extract-agent) não possuem proveniência, deixando lacunas no registro de auditoria.


## Solução

Substituir a reificação por tripla por um **modelo de subgrafo**: um registro de proveniência
por extração de bloco, compartilhado entre todas as triplas produzidas a partir desse
bloco.

### Mudança de Terminologia

| Antigo | Novo |
|-----|-----|
| `stmt_uri` (`https://trustgraph.ai/stmt/{uuid}`) | `subgraph_uri` (`https://trustgraph.ai/subgraph/{uuid}`) |
| `statement_uri()` | `subgraph_uri()` |
| `tg:reifies` (1:1, identidade) | `tg:contains` (1:muitos, contenção) |

### Estrutura Alvo

Todas as triplas de proveniência devem ser inseridas no grafo nomeado `urn:graph:source`.

```
# Subgraph contains each extracted triple (RDF-star quoted triples)
<subgraph> tg:contains <<s1 p1 o1>> .
<subgraph> tg:contains <<s2 p2 o2>> .
<subgraph> tg:contains <<s3 p3 o3>> .

# Derivation from source chunk
<subgraph> prov:wasDerivedFrom <chunk_uri> .
<subgraph> prov:wasGeneratedBy <activity> .

# Activity: one per chunk extraction
<activity> rdf:type          prov:Activity .
<activity> rdfs:label        "{component_name} extraction" .
<activity> prov:used         <chunk_uri> .
<activity> prov:wasAssociatedWith <agent> .
<activity> prov:startedAtTime "2026-03-13T10:00:00Z" .
<activity> tg:componentVersion "0.25.0" .
<activity> tg:llmModel       "gpt-4" .          # if available
<activity> tg:ontology        <ontology_uri> .   # if available

# Agent: stable per component
<agent> rdf:type   prov:Agent .
<agent> rdfs:label "{component_name}" .
```

### Comparação de Volume

Para um conjunto de dados que produz N triplas extraídas:

| | Antigo (por tripla) | Novo (subgrafo) |
|---|---|---|
| `tg:contains` / `tg:reifies` | N | N |
| Triplas de atividade | ~9 x N | ~9 |
| Triplas de agente | 2 x N | 2 |
| Metadados de declaração/subgrafo | 2 x N | 2 |
| **Total de triplas de rastreabilidade** | **~13N** | **N + 13** |
| **Exemplo (N=20)** | **~260** | **33** |

## Escopo

### Processadores a serem Atualizados (rastreabilidade existente, por tripla)

**kg-extract-definitions**
(`trustgraph-flow/trustgraph/extract/kg/definitions/extract.py`)

Atualmente, chama `statement_uri()` + `triple_provenance_triples()` dentro
do loop por definição.

Alterações:
Mover a criação de `subgraph_uri()` e `activity_uri()` antes do loop
Coletar triplas `tg:contains` dentro do loop
Emitir bloco compartilhado de atividade/agente/derivação uma vez após o loop

**kg-extract-relationships**
(`trustgraph-flow/trustgraph/extract/kg/relationships/extract.py`)

Mesmo padrão que definições. As mesmas alterações.

### Processadores a serem Adicionados para Rastreabilidade (atualmente ausente)

**kg-extract-ontology**
(`trustgraph-flow/trustgraph/extract/kg/ontology/extract.py`)

Atualmente, emite triplas sem rastreabilidade. Adicionar rastreabilidade de subgrafo
usando o mesmo padrão: um subgrafo por conjunto de dados, `tg:contains` para cada
tripla extraída.

**kg-extract-agent**
(`trustgraph-flow/trustgraph/extract/kg/agent/extract.py`)

Atualmente, emite triplas sem rastreabilidade. Adicionar rastreabilidade de subgrafo
usando o mesmo padrão.

### Alterações na Biblioteca Compartilhada de Rastreabilidade

**`trustgraph-base/trustgraph/provenance/triples.py`**

Substituir `triple_provenance_triples()` por `subgraph_provenance_triples()`
Nova função aceita uma lista de triplas extraídas em vez de uma única
Gera um `tg:contains` por tripla, bloco compartilhado de atividade/agente
Remover `triple_provenance_triples()` antigo

**`trustgraph-base/trustgraph/provenance/uris.py`**

Substituir `statement_uri()` por `subgraph_uri()`

**`trustgraph-base/trustgraph/provenance/namespaces.py`**

Substituir `TG_REIFIES` por `TG_CONTAINS`

### Não no Escopo

**kg-extract-topics**: processador de estilo antigo, não usado atualmente em
  fluxos padrão
**kg-extract-rows**: produz linhas, não triplas, modelo de rastreabilidade
  diferente
**Rastreabilidade em tempo de consulta** (`urn:graph:retrieval`): questão separada,
  já usa um padrão diferente (pergunta/exploração/foco/síntese)
**Rastreabilidade de documento/página/conjunto de dados** (decodificador PDF, divisor): já usa
  `derived_entity_triples()` que é por entidade, não por tripla — não há
  problema de redundância

## Notas de Implementação

### Reestruturação do Loop do Processador

Antes (por tripla, em relacionamentos):
```python
for rel in rels:
    # ... build relationship_triple ...
    stmt_uri = statement_uri()
    prov_triples = triple_provenance_triples(
        stmt_uri=stmt_uri,
        extracted_triple=relationship_triple,
        ...
    )
    triples.extend(set_graph(prov_triples, GRAPH_SOURCE))
```

Após (subgrafo):
```python
sg_uri = subgraph_uri()

for rel in rels:
    # ... build relationship_triple ...
    extracted_triples.append(relationship_triple)

prov_triples = subgraph_provenance_triples(
    subgraph_uri=sg_uri,
    extracted_triples=extracted_triples,
    chunk_uri=chunk_uri,
    component_name=default_ident,
    component_version=COMPONENT_VERSION,
    llm_model=llm_model,
    ontology_uri=ontology_uri,
)
triples.extend(set_graph(prov_triples, GRAPH_SOURCE))
```

### Nova Assinatura de Auxílio

```python
def subgraph_provenance_triples(
    subgraph_uri: str,
    extracted_triples: List[Triple],
    chunk_uri: str,
    component_name: str,
    component_version: str,
    llm_model: Optional[str] = None,
    ontology_uri: Optional[str] = None,
    timestamp: Optional[str] = None,
) -> List[Triple]:
    """
    Build provenance triples for a subgraph of extracted knowledge.

    Creates:
    - tg:contains link for each extracted triple (RDF-star quoted)
    - One prov:wasDerivedFrom link to source chunk
    - One activity with agent metadata
    """
```

### Mudança Significativa

Esta é uma mudança significativa no modelo de rastreabilidade. A rastreabilidade não
foi lançada, portanto, nenhuma migração é necessária. O código antigo `tg:reifies` /
`statement_uri` pode ser removido completamente.
