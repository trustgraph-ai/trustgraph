---
layout: default
title: "Proposta de Refatoração do Diretório de Esquemas"
parent: "Portuguese (Beta)"
---

# Proposta de Refatoração do Diretório de Esquemas

> **Beta Translation:** This document was translated via Machine Learning and as such may not be 100% accurate. All non-English languages are currently classified as Beta.

## Problemas Atuais

1. **Estrutura plana** - Todos os esquemas em um único diretório dificultam a compreensão das relações.
2. **Preocupações misturadas** - Tipos principais, objetos de domínio e contratos de API todos misturados.
3. **Nomenclatura pouco clara** - Arquivos como "object.py", "types.py", "topic.py" não indicam claramente seu propósito.
4. **Ausência de camadas claras** - Não é fácil ver o que depende do quê.

## Estrutura Proposta

```
trustgraph-base/trustgraph/schema/
├── __init__.py
├── core/              # Core primitive types used everywhere
│   ├── __init__.py
│   ├── primitives.py  # Error, Value, Triple, Field, RowSchema
│   ├── metadata.py    # Metadata record
│   └── topic.py       # Topic utilities
│
├── knowledge/         # Knowledge domain models and extraction
│   ├── __init__.py
│   ├── graph.py       # EntityContext, EntityEmbeddings, Triples
│   ├── document.py    # Document, TextDocument, Chunk
│   ├── knowledge.py   # Knowledge extraction types
│   ├── embeddings.py  # All embedding-related types (moved from multiple files)
│   └── nlp.py         # Definition, Topic, Relationship, Fact types
│
└── services/          # Service request/response contracts
    ├── __init__.py
    ├── llm.py         # TextCompletion, Embeddings, Tool requests/responses
    ├── retrieval.py   # GraphRAG, DocumentRAG queries/responses
    ├── query.py       # GraphEmbeddingsRequest/Response, DocumentEmbeddingsRequest/Response
    ├── agent.py       # Agent requests/responses
    ├── flow.py        # Flow requests/responses
    ├── prompt.py      # Prompt service requests/responses
    ├── config.py      # Configuration service
    ├── library.py     # Librarian service
    └── lookup.py      # Lookup service
```

## Principais Alterações

1. **Organização hierárquica** - Separação clara entre tipos principais, modelos de conhecimento e contratos de serviço.
2. **Melhores nomes:**
   `types.py` → `core/primitives.py` (propósito mais claro)
   `object.py` → Divisão entre arquivos apropriados com base no conteúdo real.
   `documents.py` → `knowledge/document.py` (singular, consistente)
   `models.py` → `services/llm.py` (mais claro que tipo de modelos)
   `prompt.py` → Divisão: partes de serviço para `services/prompt.py`, tipos de dados para `knowledge/nlp.py`

3. **Agrupamento lógico:**
   Todos os tipos de incorporação consolidados em `knowledge/embeddings.py`
   Todos os contratos de serviço relacionados a LLM em `services/llm.py`
   Separação clara de pares de solicitação/resposta no diretório de serviços.
   Tipos de extração de conhecimento agrupados com outros modelos de domínio de conhecimento.

4. **Clareza das dependências:**
   Tipos principais não têm dependências.
   Modelos de conhecimento dependem apenas do núcleo.
   Contratos de serviço podem depender tanto do núcleo quanto dos modelos de conhecimento.

## Benefícios da Migração

1. **Navegação mais fácil** - Os desenvolvedores podem encontrar rapidamente o que precisam.
2. **Melhor modularidade** - Limites claros entre diferentes aspectos.
3. **Importações mais simples** - Caminhos de importação mais intuitivos.
4. **Preparado para o futuro** - Fácil de adicionar novos tipos de conhecimento ou serviços sem causar desordem.

## Exemplos de Alterações de Importação

```python
# Before
from trustgraph.schema import Error, Triple, GraphEmbeddings, TextCompletionRequest

# After
from trustgraph.schema.core import Error, Triple
from trustgraph.schema.knowledge import GraphEmbeddings
from trustgraph.schema.services import TextCompletionRequest
```

## Notas de Implementação

1. Mantenha a compatibilidade com versões anteriores, mantendo as importações no diretório raiz `__init__.py`.
2. Mova os arquivos gradualmente, atualizando as importações conforme necessário.
3. Considere adicionar um `legacy.py` que importe tudo para o período de transição.
4. Atualize a documentação para refletir a nova estrutura.

<function_calls>
<invoke name="TodoWrite">
<parameter name="todos">[{"id": "1", "content": "Examinar a estrutura de diretórios do esquema atual", "status": "completed", "priority": "high"}, {"id": "2", "content": "Analisar os arquivos de esquema e seus propósitos", "status": "completed", "priority": "high"}, {"id": "3", "content": "Propor nomenclatura e estrutura aprimoradas", "status": "completed", "priority": "high"}]
