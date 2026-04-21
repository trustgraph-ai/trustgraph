---
layout: default
title: "Especificação Técnica de Suporte a Streaming RAG"
parent: "Portuguese (Beta)"
---

# Especificação Técnica de Suporte a Streaming RAG

> **Beta Translation:** This document was translated via Machine Learning and as such may not be 100% accurate. All non-English languages are currently classified as Beta.

## Visão Geral

Esta especificação descreve a adição de suporte a streaming aos serviços GraphRAG e DocumentRAG, permitindo respostas em tempo real, token por token, para consultas de grafos de conhecimento e recuperação de documentos. Isso estende a arquitetura de streaming existente já implementada para serviços de preenchimento de texto, prompt e agente LLM.

## Objetivos

**Experiência de streaming consistente**: Fornecer a mesma experiência de streaming em todos os serviços TrustGraph.
**Alterações mínimas na API**: Adicionar suporte a streaming com um único sinalizador `streaming`, seguindo padrões estabelecidos.
**Compatibilidade com versões anteriores**: Manter o comportamento padrão existente sem streaming.
**Reutilizar infraestrutura existente**: Aproveitar o streaming do PromptClient já implementado.
**Suporte a gateway**: Permitir o streaming através do gateway WebSocket para aplicativos cliente.

## Contexto

Serviços de streaming atualmente implementados:
**Serviço de preenchimento de texto LLM**: Fase 1 - streaming de provedores LLM.
**Serviço de prompt**: Fase 2 - streaming através de modelos de prompt.
**Serviço de agente**: Fase 3-4 - streaming de respostas ReAct com fragmentos incrementais de pensamento/observação/resposta.

Limitações atuais para serviços RAG:
GraphRAG e DocumentRAG suportam apenas respostas bloqueadas.
Os usuários devem esperar pela resposta completa do LLM antes de ver qualquer saída.
Má experiência do usuário para respostas longas de grafos de conhecimento ou consultas de documentos.
Experiência inconsistente em comparação com outros serviços TrustGraph.

Esta especificação aborda essas lacunas adicionando suporte a streaming ao GraphRAG e ao DocumentRAG. Ao permitir respostas token por token, o TrustGraph pode:
Fornecer uma experiência de streaming consistente em todos os tipos de consulta.
Reduzir a latência percebida para consultas RAG.
Permitir um melhor feedback de progresso para consultas de longa duração.
Suportar a exibição em tempo real em aplicativos cliente.

## Design Técnico

### Arquitetura

A implementação de streaming RAG aproveita a infraestrutura existente:

1. **Streaming do PromptClient** (Já implementado)
   `kg_prompt()` e `document_prompt()` já aceitam parâmetros `streaming` e `chunk_callback`.
   Isso chama `prompt()` internamente com suporte a streaming.
   Não são necessárias alterações no PromptClient.

   Módulo: `trustgraph-base/trustgraph/base/prompt_client.py`

2. **Serviço GraphRAG** (Precisa de passagem de parâmetro de streaming)
   Adicionar parâmetro `streaming` ao método `query()`.
   Passar o sinalizador de streaming e os callbacks para `prompt_client.kg_prompt()`.
   O esquema GraphRagRequest precisa do campo `streaming`.

   Módulos:
   `trustgraph-flow/trustgraph/retrieval/graph_rag/graph_rag.py`
   `trustgraph-flow/trustgraph/retrieval/graph_rag/rag.py` (Processador)
   `trustgraph-base/trustgraph/schema/graph_rag.py` (Esquema de solicitação)
   `trustgraph-flow/trustgraph/gateway/dispatch/graph_rag.py` (Gateway)

3. **Serviço DocumentRAG** (Precisa de passagem de parâmetro de streaming)
   Adicionar parâmetro `streaming` ao método `query()`.
   Passar o sinalizador de streaming e os callbacks para `prompt_client.document_prompt()`.
   O esquema DocumentRagRequest precisa do campo `streaming`.

   Módulos:
   `trustgraph-flow/trustgraph/retrieval/document_rag/document_rag.py`
   `trustgraph-flow/trustgraph/retrieval/document_rag/rag.py` (Processador)
   `trustgraph-base/trustgraph/schema/document_rag.py` (Esquema de solicitação)
   `trustgraph-flow/trustgraph/gateway/dispatch/document_rag.py` (Gateway)

### Fluxo de Dados

**Não streaming (atual)**:
```
Client → Gateway → RAG Service → PromptClient.kg_prompt(streaming=False)
                                   ↓
                                Prompt Service → LLM
                                   ↓
                                Complete response
                                   ↓
Client ← Gateway ← RAG Service ←  Response
```

**Streaming (proposto):**
```
Client → Gateway → RAG Service → PromptClient.kg_prompt(streaming=True, chunk_callback=cb)
                                   ↓
                                Prompt Service → LLM (streaming)
                                   ↓
                                Chunk → callback → RAG Response (chunk)
                                   ↓                       ↓
Client ← Gateway ← ────────────────────────────────── Response stream
```

### APIs

**Alterações no GraphRAG**:

1. **GraphRag.query()** - Adicionar parâmetros de streaming
```python
async def query(
    self, query, user, collection,
    verbose=False, streaming=False, chunk_callback=None  # NEW
):
    # ... existing entity/triple retrieval ...

    if streaming and chunk_callback:
        resp = await self.prompt_client.kg_prompt(
            query, kg,
            streaming=True,
            chunk_callback=chunk_callback
        )
    else:
        resp = await self.prompt_client.kg_prompt(query, kg)

    return resp
```

2. **Esquema GraphRagRequest** - Adicionar campo de streaming.
```python
class GraphRagRequest(Record):
    query = String()
    user = String()
    collection = String()
    streaming = Boolean()  # NEW
```

3. **Esquema GraphRagResponse** - Adicionar campos de streaming (seguir o padrão do Agente).
```python
class GraphRagResponse(Record):
    response = String()    # Legacy: complete response
    chunk = String()       # NEW: streaming chunk
    end_of_stream = Boolean()  # NEW: indicates last chunk
```

4. **Processador** - Permitir a passagem de dados em fluxo contínuo.
```python
async def handle(self, msg):
    # ... existing code ...

    async def send_chunk(chunk):
        await self.respond(GraphRagResponse(
            chunk=chunk,
            end_of_stream=False,
            response=None
        ))

    if request.streaming:
        full_response = await self.rag.query(
            query=request.query,
            user=request.user,
            collection=request.collection,
            streaming=True,
            chunk_callback=send_chunk
        )
        # Send final message
        await self.respond(GraphRagResponse(
            chunk=None,
            end_of_stream=True,
            response=full_response
        ))
    else:
        # Existing non-streaming path
        response = await self.rag.query(...)
        await self.respond(GraphRagResponse(response=response))
```

**Alterações no DocumentRAG:**

Padrão idêntico ao GraphRAG:
1. Adicionar parâmetros `streaming` e `chunk_callback` a `DocumentRag.query()`
2. Adicionar campo `streaming` a `DocumentRagRequest`
3. Adicionar campos `chunk` e `end_of_stream` a `DocumentRagResponse`
4. Atualizar o Processador para lidar com streaming com callbacks

**Alterações no Gateway:**

Tanto `graph_rag.py` quanto `document_rag.py` no gateway/dispatch precisam de atualizações para encaminhar trechos de streaming para o websocket:

```python
async def handle(self, message, session, websocket):
    # ... existing code ...

    if request.streaming:
        async def recipient(resp):
            if resp.chunk:
                await websocket.send(json.dumps({
                    "id": message["id"],
                    "response": {"chunk": resp.chunk},
                    "complete": resp.end_of_stream
                }))
            return resp.end_of_stream

        await self.rag_client.request(request, recipient=recipient)
    else:
        # Existing non-streaming path
        resp = await self.rag_client.request(request)
        await websocket.send(...)
```

### Detalhes de Implementação

**Ordem de implementação**:
1. Adicionar campos de esquema (Request + Response para ambos os serviços RAG)
2. Atualizar os métodos GraphRag.query() e DocumentRag.query()
3. Atualizar Processadores para lidar com streaming
4. Atualizar manipuladores de despacho do Gateway
5. Adicionar `--no-streaming` flags a `tg-invoke-graph-rag` e `tg-invoke-document-rag` (streaming habilitado por padrão, seguindo o padrão da CLI do agente)

**Padrão de callback**:
Seguir o mesmo padrão de callback assíncrono estabelecido no streaming do Agente:
O Processador define o `async def send_chunk(chunk)` callback
Passa o callback para o serviço RAG
O serviço RAG passa o callback para o PromptClient
O PromptClient invoca o callback para cada chunk do LLM
O Processador envia uma mensagem de resposta de streaming para cada chunk

**Tratamento de erros**:
Erros durante o streaming devem enviar uma resposta de erro com `end_of_stream=True`
Seguir os padrões existentes de propagação de erros do streaming do Agente

## Considerações de Segurança

Não há novas considerações de segurança além dos serviços RAG existentes:
As respostas de streaming usam o mesmo isolamento de usuário/coleção
Não há alterações na autenticação ou autorização
Os limites de chunk não expõem dados sensíveis

## Considerações de Desempenho

**Benefícios**:
Latência percebida reduzida (os primeiros tokens chegam mais rápido)
Melhor experiência do usuário para respostas longas
Menor uso de memória (não é necessário armazenar em buffer a resposta completa)

**Preocupações potenciais**:
Mais mensagens Pulsar para respostas de streaming
Ligeiramente maior uso de CPU para a sobrecarga de chunking/callback
Mitigado por: o streaming é opcional, o padrão permanece não-streaming

**Considerações de teste**:
Testar com grafos de conhecimento grandes (muitos triplos)
Testar com muitos documentos recuperados
Medir a sobrecarga do streaming versus não-streaming

## Estratégia de Teste

**Testes unitários**:
Testar GraphRag.query() com streaming=True/False
Testar DocumentRag.query() com streaming=True/False
Simular o PromptClient para verificar as invocações de callback

**Testes de integração**:
Testar o fluxo completo de streaming do GraphRAG (semelhante aos testes existentes de streaming do agente)
Testar o fluxo completo de streaming do DocumentRAG
Testar o encaminhamento de streaming do Gateway
Testar a saída de streaming da CLI

**Testes manuais**:
`tg-invoke-graph-rag -q "What is machine learning?"` (streaming por padrão)
`tg-invoke-document-rag -q "Summarize the documents about AI"` (streaming por padrão)
`tg-invoke-graph-rag --no-streaming -q "..."` (testar o modo não-streaming)
Verificar se a saída incremental aparece no modo de streaming

## Plano de Migração

Nenhuma migração necessária:
O streaming é opcional por meio do parâmetro `streaming` (o padrão é Falso)
Os clientes existentes continuam a funcionar sem alterações
Novos clientes podem optar por usar o streaming

## Cronograma

Tempo estimado de implementação: 4-6 horas
Fase 1 (2 horas): suporte de streaming do GraphRAG
Fase 2 (2 horas): suporte de streaming do DocumentRAG
Fase 3 (1-2 horas): atualizações do Gateway e flags da CLI
Testes: integrados em cada fase

## Perguntas Abertas

Devemos adicionar suporte de streaming ao serviço de consulta NLP também?
Queremos transmitir etapas intermediárias (por exemplo, "Recuperando entidades...", "Consultando o grafo...") ou apenas a saída do LLM?
As respostas do GraphRAG/DocumentRAG devem incluir metadados do chunk (por exemplo, número do chunk, total esperado)?

## Referências

Implementação existente: `docs/tech-specs/streaming-llm-responses.md`
Streaming do Agente: `trustgraph-flow/trustgraph/agent/react/agent_manager.py`
Streaming do PromptClient: `trustgraph-base/trustgraph/base/prompt_client.py`
