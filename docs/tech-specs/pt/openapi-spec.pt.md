---
layout: default
title: "Especificação OpenAPI - Especificação Técnica"
parent: "Portuguese (Beta)"
---

# Especificação OpenAPI - Especificação Técnica

> **Beta Translation:** This document was translated via Machine Learning and as such may not be 100% accurate. All non-English languages are currently classified as Beta.

## Objetivo

Criar uma especificação OpenAPI 3.1 abrangente e modular para o Gateway de API REST TrustGraph que:
Documenta todos os endpoints REST
Utiliza `$ref` externo para modularidade e manutenção
Mapeia diretamente para o código do tradutor de mensagens
Fornece esquemas precisos de requisição/resposta

## Fonte da Verdade

A API é definida por:
**Tradutores de Mensagens**: `trustgraph-base/trustgraph/messaging/translators/*.py`
**Gerenciador de Dispatcher**: `trustgraph-flow/trustgraph/gateway/dispatch/manager.py`
**Gerenciador de Endpoint**: `trustgraph-flow/trustgraph/gateway/endpoint/manager.py`

## Estrutura de Diretórios

```
openapi/
├── openapi.yaml                          # Main entry point
├── paths/
│   ├── config.yaml                       # Global services
│   ├── flow.yaml
│   ├── librarian.yaml
│   ├── knowledge.yaml
│   ├── collection-management.yaml
│   ├── flow-services/                    # Flow-hosted services
│   │   ├── agent.yaml
│   │   ├── document-rag.yaml
│   │   ├── graph-rag.yaml
│   │   ├── text-completion.yaml
│   │   ├── prompt.yaml
│   │   ├── embeddings.yaml
│   │   ├── mcp-tool.yaml
│   │   ├── triples.yaml
│   │   ├── objects.yaml
│   │   ├── nlp-query.yaml
│   │   ├── structured-query.yaml
│   │   ├── structured-diag.yaml
│   │   ├── graph-embeddings.yaml
│   │   ├── document-embeddings.yaml
│   │   ├── text-load.yaml
│   │   └── document-load.yaml
│   ├── import-export/
│   │   ├── core-import.yaml
│   │   ├── core-export.yaml
│   │   └── flow-import-export.yaml      # WebSocket import/export
│   ├── websocket.yaml
│   └── metrics.yaml
├── components/
│   ├── schemas/
│   │   ├── config/
│   │   ├── flow/
│   │   ├── librarian/
│   │   ├── knowledge/
│   │   ├── collection/
│   │   ├── ai-services/
│   │   ├── common/
│   │   └── errors/
│   ├── parameters/
│   ├── responses/
│   └── examples/
└── security/
    └── bearerAuth.yaml
```

## Mapeamento de Serviços

### Serviços Globais (`/api/v1/{kind}`)
`config` - Gerenciamento de configuração
`flow` - Ciclo de vida do fluxo
`librarian` - Biblioteca de documentos
`knowledge` - Núcleos de conhecimento
`collection-management` - Metadados de coleção

### Serviços Hospedados em Fluxo (`/api/v1/flow/{flow}/service/{kind}`)

**Requisição/Resposta:**
`agent`, `text-completion`, `prompt`, `mcp-tool`
`graph-rag`, `document-rag`
`embeddings`, `graph-embeddings`, `document-embeddings`
`triples`, `objects`, `nlp-query`, `structured-query`, `structured-diag`

**Enviar e Esquecer:**
`text-load`, `document-load`

### Importação/Exportação
`/api/v1/import-core` (POST)
`/api/v1/export-core` (GET)
`/api/v1/flow/{flow}/import/{kind}` (WebSocket)
`/api/v1/flow/{flow}/export/{kind}` (WebSocket)

### Outros
`/api/v1/socket` (WebSocket multiplexado)
`/api/metrics` (Prometheus)

## Abordagem

### Fase 1: Configuração
1. Criar estrutura de diretórios
2. Criar o arquivo principal `openapi.yaml` com metadados, servidores, segurança
3. Criar componentes reutilizáveis (erros, parâmetros comuns, esquemas de segurança)

### Fase 2: Esquemas Comuns
Criar esquemas compartilhados usados em todos os serviços:
`RdfValue`, `Triple` - Estruturas RDF/triplas
`ErrorObject` - Resposta de erro
`DocumentMetadata`, `ProcessingMetadata` - Estruturas de metadados
Parâmetros comuns: `FlowId`, `User`, `Collection`

### Fase 3: Serviços Globais
Para cada serviço global (configuração, fluxo, bibliotecário, conhecimento, gerenciamento de coleção):
1. Criar arquivo de caminho em `paths/`
2. Criar esquema de solicitação em `components/schemas/{service}/`
3. Criar esquema de resposta
4. Adicionar exemplos
5. Referenciar do arquivo principal `openapi.yaml`

### Fase 4: Serviços Hospedados em Fluxo
Para cada serviço hospedado em fluxo:
1. Criar arquivo de caminho em `paths/flow-services/`
2. Criar esquemas de solicitação/resposta em `components/schemas/ai-services/`
3. Adicionar documentação da flag de streaming, quando aplicável
4. Referenciar do arquivo principal `openapi.yaml`

### Fase 5: Importação/Exportação e WebSocket
1. Documentar os principais endpoints de importação/exportação
2. Documentar os padrões de protocolo WebSocket
3. Documentar os endpoints de importação/exportação WebSocket no nível do fluxo

### Fase 6: Validação
1. Validar com ferramentas de validação OpenAPI
2. Testar com Swagger UI
3. Verificar se todos os tradutores estão cobertos

## Convenção de Nomenclatura de Campos

Todos os campos JSON usam **kebab-case**:
`flow-id`, `blueprint-name`, `doc-limit`, `entity-limit`, etc.

## Criação de Arquivos de Esquema

Para cada tradutor em `trustgraph-base/trustgraph/messaging/translators/`:

1. **Ler o método do tradutor `to_pulsar()`** - Define o esquema de solicitação
2. **Ler o método do tradutor `from_pulsar()`** - Define o esquema de resposta
3. **Extrair nomes e tipos de campos**
4. **Criar o esquema OpenAPI** com:
   Nomes de campos (kebab-case)
   Tipos (string, integer, boolean, object, array)
   Campos obrigatórios
   Valores padrão
   Descrições

### Exemplo de Processo de Mapeamento

```python
# From retrieval.py DocumentRagRequestTranslator
def to_pulsar(self, data: Dict[str, Any]) -> DocumentRagQuery:
    return DocumentRagQuery(
        query=data["query"],                              # required string
        user=data.get("user", "trustgraph"),             # optional string, default "trustgraph"
        collection=data.get("collection", "default"),     # optional string, default "default"
        doc_limit=int(data.get("doc-limit", 20)),        # optional integer, default 20
        streaming=data.get("streaming", False)            # optional boolean, default false
    )
```

Tradução para:

```yaml
# components/schemas/ai-services/DocumentRagRequest.yaml
type: object
required:
  - query
properties:
  query:
    type: string
    description: Search query
  user:
    type: string
    default: trustgraph
  collection:
    type: string
    default: default
  doc-limit:
    type: integer
    default: 20
    description: Maximum number of documents to retrieve
  streaming:
    type: boolean
    default: false
    description: Enable streaming responses
```

## Respostas de Streaming

Serviços que suportam streaming retornam múltiplas respostas com a flag `end_of_stream`:
`agent`, `text-completion`, `prompt`
`document-rag`, `graph-rag`

Documente este padrão no esquema de resposta de cada serviço.

## Respostas de Erro

Todos os serviços podem retornar:
```yaml
error:
  oneOf:
    - type: string
    - $ref: '#/components/schemas/ErrorObject'
```

Onde `ErrorObject` está:
```yaml
type: object
properties:
  type:
    type: string
  message:
    type: string
```

## Referências

Tradutores: `trustgraph-base/trustgraph/messaging/translators/`
Mapeamento do despachante: `trustgraph-flow/trustgraph/gateway/dispatch/manager.py`
Roteamento de endpoint: `trustgraph-flow/trustgraph/gateway/endpoint/manager.py`
Resumo do serviço: `API_SERVICES_SUMMARY.md`
