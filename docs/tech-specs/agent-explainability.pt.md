---
layout: default
title: "Explicabilidade do Agente: Registro de Proveniência"
parent: "Portuguese (Beta)"
---

# Explicabilidade do Agente: Registro de Proveniência

> **Beta Translation:** This document was translated via Machine Learning and as such may not be 100% accurate. All non-English languages are currently classified as Beta.

## Visão Geral

Adicionar o registro de proveniência ao loop do agente React para que as sessões do agente possam ser rastreadas e depuradas usando a mesma infraestrutura de explicabilidade do GraphRAG.

**Decisões de Design:**
- Escrever em `urn:graph:retrieval` (grafo de explicabilidade genérico)
- Cadeia de dependência linear por enquanto (análise N → foiDerivadoDe → análise N-1)
- As ferramentas são caixas pretas (registrar apenas entrada/saída)
- Suporte a DAG (Directed Acyclic Graph - Grafo Acíclico Direcionado) adiado para uma iteração futura

## Tipos de Entidade

Tanto o GraphRAG quanto o Agent usam PROV-O como a ontologia base, com subtipos específicos do TrustGraph:

### Tipos do GraphRAG
| Entidade | Tipo PROV-O | Tipos TG | Descrição |
|--------|-------------|----------|-------------|
| Pergunta | `prov:Activity` | `tg:Question`, `tg:GraphRagQuestion` | A consulta do usuário |
| Exploração | `prov:Entity` | `tg:Exploration` | Arestas recuperadas do grafo de conhecimento |
| Foco | `prov:Entity` | `tg:Focus` | Arestas selecionadas com raciocínio |
| Síntese | `prov:Entity` | `tg:Synthesis` | Resposta final |

### Tipos do Agente
| Entidade | Tipo PROV-O | Tipos TG | Descrição |
|--------|-------------|----------|-------------|
| Pergunta | `prov:Activity` | `tg:Question`, `tg:AgentQuestion` | A consulta do usuário |
| Análise | `prov:Entity` | `tg:Analysis` | Cada ciclo de pensar/agir/observar |
| Conclusão | `prov:Entity` | `tg:Conclusion` | Resposta final |

### Tipos do Document RAG
| Entidade | Tipo PROV-O | Tipos TG | Descrição |
|--------|-------------|----------|-------------|
| Pergunta | `prov:Activity` | `tg:Question`, `tg:DocRagQuestion` | A consulta do usuário |
| Exploração | `prov:Entity` | `tg:Exploration` | Trechos recuperados do armazenamento de documentos |
| Síntese | `prov:Entity` | `tg:Synthesis` | Resposta final |

**Observação:** O Document RAG usa um subconjunto dos tipos do GraphRAG (sem a etapa de Foco, pois não há seleção/raciocínio de arestas).

### Subtipos de Pergunta

Todas as entidades de Pergunta compartilham `tg:Question` como um tipo base, mas têm um subtipo específico para identificar o mecanismo de recuperação:

| Subtipo | Padrão URI | Mecanismo |
|---------|-------------|-----------|
| `tg:GraphRagQuestion` | `urn:trustgraph:question:{uuid}` | RAG de grafo de conhecimento |
| `tg:DocRagQuestion` | `urn:trustgraph:docrag:{uuid}` | RAG de documento/trecho |
| `tg:AgentQuestion` | `urn:trustgraph:agent:{uuid}` | Agente ReAct |

Isso permite consultar todas as perguntas via `tg:Question`, filtrando por mecanismo específico através do subtipo.

## Modelo de Proveniência

```
Question (urn:trustgraph:agent:{uuid})
    │
    │  tg:query = "User's question"
    │  prov:startedAtTime = timestamp
    │  rdf:type = prov:Activity, tg:Question
    │
    ↓ prov:wasDerivedFrom
    │
Analysis1 (urn:trustgraph:agent:{uuid}/i1)
    │
    │  tg:thought = "I need to query the knowledge base..."
    │  tg:action = "knowledge-query"
    │  tg:arguments = {"question": "..."}
    │  tg:observation = "Result from tool..."
    │  rdf:type = prov:Entity, tg:Analysis
    │
    ↓ prov:wasDerivedFrom
    │
Analysis2 (urn:trustgraph:agent:{uuid}/i2)
    │  ...
    ↓ prov:wasDerivedFrom
    │
Conclusion (urn:trustgraph:agent:{uuid}/final)
    │
    │  tg:answer = "The final response..."
    │  rdf:type = prov:Entity, tg:Conclusion
```

### Modelo de Proveniência de Documentos RAG

```
Question (urn:trustgraph:docrag:{uuid})
    │
    │  tg:query = "User's question"
    │  prov:startedAtTime = timestamp
    │  rdf:type = prov:Activity, tg:Question
    │
    ↓ prov:wasGeneratedBy
    │
Exploration (urn:trustgraph:docrag:{uuid}/exploration)
    │
    │  tg:chunkCount = 5
    │  tg:selectedChunk = "chunk-id-1"
    │  tg:selectedChunk = "chunk-id-2"
    │  ...
    │  rdf:type = prov:Entity, tg:Exploration
    │
    ↓ prov:wasDerivedFrom
    │
Synthesis (urn:trustgraph:docrag:{uuid}/synthesis)
    │
    │  tg:content = "The synthesized answer..."
    │  rdf:type = prov:Entity, tg:Synthesis
```

## Alterações Necessárias

### 1. Alterações no Esquema

**Arquivo:** `trustgraph-base/trustgraph/schema/services/agent.py`

Adicionar os campos `session_id` e `collection` a `AgentRequest`:
```python
@dataclass
class AgentRequest:
    question: str = ""
    state: str = ""
    group: list[str] | None = None
    history: list[AgentStep] = field(default_factory=list)
    user: str = ""
    collection: str = "default"  # NEW: Collection for provenance traces
    streaming: bool = False
    session_id: str = ""         # NEW: For provenance tracking across iterations
```

**Arquivo:** `trustgraph-base/trustgraph/messaging/translators/agent.py`

Atualizar o tradutor para lidar com `session_id` e `collection` tanto em `to_pulsar()` quanto em `from_pulsar()`.

### 2. Adicionar Produtor de Explicabilidade ao Serviço de Agente

**Arquivo:** `trustgraph-flow/trustgraph/agent/react/service.py`

Registrar um "produtor de explicabilidade" (mesmo padrão do GraphRAG):
```python
from ... base import ProducerSpec
from ... schema import Triples

# In __init__:
self.register_specification(
    ProducerSpec(
        name = "explainability",
        schema = Triples,
    )
)
```

### 3. Geração de Triplas de Proveniência

**Arquivo:** `trustgraph-base/trustgraph/provenance/agent.py`

Crie funções auxiliares (semelhantes a `question_triples`, `exploration_triples`, etc. do GraphRAG):
```python
def agent_session_triples(session_uri, query, timestamp):
    """Generate triples for agent Question."""
    return [
        Triple(s=session_uri, p=RDF_TYPE, o=PROV_ACTIVITY),
        Triple(s=session_uri, p=RDF_TYPE, o=TG_QUESTION),
        Triple(s=session_uri, p=TG_QUERY, o=query),
        Triple(s=session_uri, p=PROV_STARTED_AT_TIME, o=timestamp),
    ]

def agent_iteration_triples(iteration_uri, parent_uri, thought, action, arguments, observation):
    """Generate triples for one Analysis step."""
    return [
        Triple(s=iteration_uri, p=RDF_TYPE, o=PROV_ENTITY),
        Triple(s=iteration_uri, p=RDF_TYPE, o=TG_ANALYSIS),
        Triple(s=iteration_uri, p=TG_THOUGHT, o=thought),
        Triple(s=iteration_uri, p=TG_ACTION, o=action),
        Triple(s=iteration_uri, p=TG_ARGUMENTS, o=json.dumps(arguments)),
        Triple(s=iteration_uri, p=TG_OBSERVATION, o=observation),
        Triple(s=iteration_uri, p=PROV_WAS_DERIVED_FROM, o=parent_uri),
    ]

def agent_final_triples(final_uri, parent_uri, answer):
    """Generate triples for Conclusion."""
    return [
        Triple(s=final_uri, p=RDF_TYPE, o=PROV_ENTITY),
        Triple(s=final_uri, p=RDF_TYPE, o=TG_CONCLUSION),
        Triple(s=final_uri, p=TG_ANSWER, o=answer),
        Triple(s=final_uri, p=PROV_WAS_DERIVED_FROM, o=parent_uri),
    ]
```

### 4. Definições de Tipo

**Arquivo:** `trustgraph-base/trustgraph/provenance/namespaces.py`

Adicionar tipos de entidade de explicabilidade e predicados de agente:
```python
# Explainability entity types (used by both GraphRAG and Agent)
TG_QUESTION = TG + "Question"
TG_EXPLORATION = TG + "Exploration"
TG_FOCUS = TG + "Focus"
TG_SYNTHESIS = TG + "Synthesis"
TG_ANALYSIS = TG + "Analysis"
TG_CONCLUSION = TG + "Conclusion"

# Agent predicates
TG_THOUGHT = TG + "thought"
TG_ACTION = TG + "action"
TG_ARGUMENTS = TG + "arguments"
TG_OBSERVATION = TG + "observation"
TG_ANSWER = TG + "answer"
```

## Arquivos Modificados

| Arquivo | Alteração |
|------|--------|
| `trustgraph-base/trustgraph/schema/services/agent.py` | Adiciona session_id e collection a AgentRequest |
| `trustgraph-base/trustgraph/messaging/translators/agent.py` | Atualiza o tradutor para novos campos |
| `trustgraph-base/trustgraph/provenance/namespaces.py` | Adiciona tipos de entidade, predicados de agente e predicados Document RAG |
| `trustgraph-base/trustgraph/provenance/triples.py` | Adiciona tipos TG aos construtores de triplas GraphRAG, adiciona construtores de triplas Document RAG |
| `trustgraph-base/trustgraph/provenance/uris.py` | Adiciona geradores de URI Document RAG |
| `trustgraph-base/trustgraph/provenance/__init__.py` | Exporta novos tipos, predicados e funções Document RAG |
| `trustgraph-base/trustgraph/schema/services/retrieval.py` | Adiciona explain_id e explain_graph a DocumentRagResponse |
| `trustgraph-base/trustgraph/messaging/translators/retrieval.py` | Atualiza DocumentRagResponseTranslator para campos de explicabilidade |
| `trustgraph-flow/trustgraph/agent/react/service.py` | Adiciona lógica de produção e gravação de explicabilidade |
| `trustgraph-flow/trustgraph/retrieval/document_rag/document_rag.py` | Adiciona callback de explicabilidade e emite triplas de procedência |
| `trustgraph-flow/trustgraph/retrieval/document_rag/rag.py` | Adiciona produtor de explicabilidade e conecta o callback |
| `trustgraph-cli/trustgraph/cli/show_explain_trace.py` | Lida com tipos de rastreamento de agente |
| `trustgraph-cli/trustgraph/cli/list_explain_traces.py` | Lista sessões de agente junto com GraphRAG |

## Arquivos Criados

| Arquivo | Propósito |
|------|---------|
| `trustgraph-base/trustgraph/provenance/agent.py` | Geradores de triplas específicos para agente |

## Atualizações da CLI

**Detecção:** Tanto GraphRAG quanto Agent Questions têm o tipo `tg:Question`. Distinguido por:
1. Padrão de URI: `urn:trustgraph:agent:` vs `urn:trustgraph:question:`
2. Entidades derivadas: `tg:Analysis` (agente) vs `tg:Exploration` (GraphRAG)

**`list_explain_traces.py`:**
- Mostra a coluna Tipo (Agente vs GraphRAG)

**`show_explain_trace.py`:**
- Detecta automaticamente o tipo de rastreamento
- A renderização do agente mostra: Pergunta → Etapa(s) de análise → Conclusão

## Compatibilidade com versões anteriores

- `session_id` padrão é `""` - solicitações antigas funcionam, mas não terão procedência
- `collection` padrão é `"default"` - fallback razoável
- A CLI lida graciosamente com ambos os tipos de rastreamento

## Verificação

```bash
# Run an agent query
tg-invoke-agent -q "What is the capital of France?"

# List traces (should show agent sessions with Type column)
tg-list-explain-traces -U trustgraph -C default

# Show agent trace
tg-show-explain-trace "urn:trustgraph:agent:xxx"
```

## Trabalhos Futuros (Não Neste PR)

- Dependências de DAG (quando a análise N usa resultados de várias análises anteriores)
- Vinculação de rastreabilidade específica da ferramenta (KnowledgeQuery → seu rastreamento GraphRAG)
- Emissão de rastreabilidade em fluxo (emitir continuamente, não em lote no final)
