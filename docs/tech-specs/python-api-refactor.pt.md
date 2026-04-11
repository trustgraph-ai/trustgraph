# Python API Refactor Technical Specification

## Overview

Esta especificação descreve uma refatoração abrangente da biblioteca de cliente da API Python TrustGraph para alcançar a paridade de recursos com o API Gateway e adicionar suporte para padrões de comunicação em tempo real modernos.

A refatoração aborda quatro casos de uso primários:

1. **Interações de LLM em Streaming**: Habilitar o streaming em tempo real de respostas de LLM (agente, RAG de grafo, RAG de documento, conclusão de texto, prompts) com uma latência ~60 vezes menor (500ms vs 30s para o primeiro token).
2. **Operações em Lote**: Suportar a importação/exportação eficiente em lote de triplas, incorporações de grafos e incorporações de documentos para gerenciamento de grafos de conhecimento em grande escala.
3. **Paridade de Recursos**: Garantir que cada endpoint do API Gateway tenha um método de API Python correspondente, incluindo a consulta de incorporações de grafos.
4. **Conexões Persistentes**: Habilitar a comunicação baseada em WebSocket para solicitações multiplexadas e redução da sobrecarga de conexão.

## Objetivos

**Paridade de Recursos**: Cada serviço do Gateway API tem um método de API Python correspondente.
**Suporte para Streaming**: Todos os serviços capazes de streaming (agente, RAG, conclusão de texto, prompt) suportam streaming na API Python.
**Transporte WebSocket**: Adicionar uma camada de transporte WebSocket opcional para conexões persistentes e multiplexação.
**Operações em Lote**: Adicionar importação/exportação eficiente em lote para triplas, incorporações de grafos e incorporações de documentos.
**Suporte Completo Async**: Implementação completa de async/await para todas as interfaces (REST, WebSocket, operações em lote, métricas).
**Compatibilidade com Versões Anteriores**: O código existente continua a funcionar sem modificação.
**Segurança de Tipos**: Manter interfaces com segurança de tipos com dataclasses e dicas de tipo.
**Aprimoramento Progressivo**: Streaming e async são opcionais por meio da seleção explícita da interface.
**Desempenho**: Alcançar uma melhoria de latência de 60 vezes para operações de streaming.
**Python Moderno**: Suporte para paradigmas sync e async para máxima flexibilidade.

## Contexto

### Estado Atual

A API Python (`trustgraph-base/trustgraph/api/`) é uma biblioteca de cliente REST somente com os seguintes módulos:

`flow.py`: Gerenciamento de fluxo e serviços com escopo de fluxo (50 métodos).
`library.py`: Operações da biblioteca de documentos (9 métodos).
`knowledge.py`: Gerenciamento central do KG (4 métodos).
`collection.py`: Metadados da coleção (3 métodos).
`config.py`: Gerenciamento de configuração (6 métodos).
`types.py`: Definições de tipo de dados (5 dataclasses).

**Operações Totais**: 50/59 (85% de cobertura).

### Limitações Atuais

**Operações Ausentes**:
Consulta de incorporações de grafos (busca semântica sobre entidades de grafos).
Importação/exportação em lote para triplas, incorporações de grafos, incorporações de documentos, contextos de entidades, objetos.
Endpoint de métricas.

**Capacidades Ausentes**:
Suporte para streaming para serviços de LLM.
Transporte WebSocket.
Solicitações concorrentes multiplexadas.
Conexões persistentes.

**Problemas de Desempenho**:
Alta latência para interações de LLM (~30s para o primeiro token).
Transferência de dados em lote ineficiente (requisição REST por item).
Sobrecarga de conexão para várias operações sequenciais.

**Problemas de Experiência do Usuário**:
Sem feedback em tempo real durante a geração de LLM.
Não é possível cancelar operações de LLM em execução prolongada.
Má escalabilidade para operações em lote.

### Impacto

O aprimoramento de streaming do API Gateway em novembro de 2024 proporcionou uma melhoria de latência de 60 vezes (500ms vs 30s para o primeiro token) para interações de LLM, mas os usuários da API Python não podem aproveitar essa capacidade. Isso cria uma lacuna significativa de experiência entre usuários de Python e não usuários de Python.

## Design Técnico

### Arquitetura

A API Python refatorada usa uma **abordagem de interface modular** com objetos separados para diferentes padrões de comunicação. Todas as interfaces estão disponíveis tanto em variantes **síncronas quanto assíncronas**:

1. **Interface REST** (existente, aprimorada).
   **Sync**: `api.flow()`, `api.library()`, `api.knowledge()`, `api.collection()`, `api.config()`.
   **Async**: `api.async_flow()`.
   Requisição/resposta síncrona/assíncrona.
   Modelo de conexão simples.
   Padrão para compatibilidade com versões anteriores.

2. **Interface WebSocket** (nova).
   **Sync**: `api.socket()`.
   **Async**: `api.async_socket()`.
   Conexão persistente.
   Solicitações multiplexadas.
   Suporte para streaming.
   Mesmas assinaturas de método do REST onde a funcionalidade se sobrepõe.

3. **Interface de Operações em Lote** (nova).
   **Sync**: `api.bulk()`.
   **Async**: `api.async_bulk()`.
   Baseado em WebSocket para eficiência.
   Importação/exportação baseada em iterador/AsyncIterator.
   Lida com grandes conjuntos de dados.

4. **Interface de Métricas** (nova).
   **Sync**: `api.metrics()`.
   **Async**: `api.async_metrics()`.
   Acesso a métricas Prometheus.

```python
import asyncio

# Synchronous interfaces
api = Api(url="http://localhost:8088/")

# REST (existing, unchanged)
flow = api.flow().id("default")
response = flow.agent(question="...", user="...")

# WebSocket (new)
socket_flow = api.socket().flow("default")
response = socket_flow.agent(question="...", user="...")
for chunk in socket_flow.agent(question="...", user="...", streaming=True):
    print(chunk)

# Bulk operations (new)
bulk = api.bulk()
bulk.import_triples(flow="default", triples=triple_generator())

# Asynchronous interfaces
async def main():
    api = Api(url="http://localhost:8088/")

    # Async REST (new)
    flow = api.async_flow().id("default")
    response = await flow.agent(question="...", user="...")

    # Async WebSocket (new)
    socket_flow = api.async_socket().flow("default")
    async for chunk in socket_flow.agent(question="...", streaming=True):
        print(chunk)

    # Async bulk operations (new)
    bulk = api.async_bulk()
    await bulk.import_triples(flow="default", triples=async_triple_generator())

asyncio.run(main())
```

**Princípios de Design Chave:**
**Mesmo URL para todas as interfaces:** `Api(url="http://localhost:8088/")` funciona para todas.
**Simetria Síncrona/Assíncrona:** Cada interface possui variantes síncronas e assíncronas com assinaturas de método idênticas.
**Assinaturas Idênticas:** Onde a funcionalidade se sobrepõe, as assinaturas dos métodos são idênticas entre REST e WebSocket, síncronas e assíncronas.
**Melhoria Progressiva:** Escolha a interface com base nas necessidades (REST para tarefas simples, WebSocket para streaming, Bulk para grandes conjuntos de dados, assíncrono para frameworks modernos).
**Intenção Explícita:** `api.socket()` sinaliza WebSocket, `api.async_socket()` sinaliza WebSocket assíncrono.
**Compatível com versões anteriores:** Código existente permanece inalterado.

### Componentes

#### 1. Classe de API Principal (Modificada)

Módulo: `trustgraph-base/trustgraph/api/api.py`

**Classe de API Aprimorada:**

```python
class Api:
    def __init__(self, url: str, timeout: int = 60, token: Optional[str] = None):
        self.url = url
        self.timeout = timeout
        self.token = token  # Optional bearer token for REST, query param for WebSocket
        self._socket_client = None
        self._bulk_client = None
        self._async_flow = None
        self._async_socket_client = None
        self._async_bulk_client = None

    # Existing synchronous methods (unchanged)
    def flow(self) -> Flow:
        """Synchronous REST-based flow interface"""
        pass

    def library(self) -> Library:
        """Synchronous REST-based library interface"""
        pass

    def knowledge(self) -> Knowledge:
        """Synchronous REST-based knowledge interface"""
        pass

    def collection(self) -> Collection:
        """Synchronous REST-based collection interface"""
        pass

    def config(self) -> Config:
        """Synchronous REST-based config interface"""
        pass

    # New synchronous methods
    def socket(self) -> SocketClient:
        """Synchronous WebSocket-based interface for streaming operations"""
        if self._socket_client is None:
            self._socket_client = SocketClient(self.url, self.timeout, self.token)
        return self._socket_client

    def bulk(self) -> BulkClient:
        """Synchronous bulk operations interface for import/export"""
        if self._bulk_client is None:
            self._bulk_client = BulkClient(self.url, self.timeout, self.token)
        return self._bulk_client

    def metrics(self) -> Metrics:
        """Synchronous metrics interface"""
        return Metrics(self.url, self.timeout, self.token)

    # New asynchronous methods
    def async_flow(self) -> AsyncFlow:
        """Asynchronous REST-based flow interface"""
        if self._async_flow is None:
            self._async_flow = AsyncFlow(self.url, self.timeout, self.token)
        return self._async_flow

    def async_socket(self) -> AsyncSocketClient:
        """Asynchronous WebSocket-based interface for streaming operations"""
        if self._async_socket_client is None:
            self._async_socket_client = AsyncSocketClient(self.url, self.timeout, self.token)
        return self._async_socket_client

    def async_bulk(self) -> AsyncBulkClient:
        """Asynchronous bulk operations interface for import/export"""
        if self._async_bulk_client is None:
            self._async_bulk_client = AsyncBulkClient(self.url, self.timeout, self.token)
        return self._async_bulk_client

    def async_metrics(self) -> AsyncMetrics:
        """Asynchronous metrics interface"""
        return AsyncMetrics(self.url, self.timeout, self.token)

    # Resource management
    def close(self) -> None:
        """Close all synchronous connections"""
        if self._socket_client:
            self._socket_client.close()
        if self._bulk_client:
            self._bulk_client.close()

    async def aclose(self) -> None:
        """Close all asynchronous connections"""
        if self._async_socket_client:
            await self._async_socket_client.aclose()
        if self._async_bulk_client:
            await self._async_bulk_client.aclose()
        if self._async_flow:
            await self._async_flow.aclose()

    def __enter__(self):
        return self

    def __exit__(self, *args):
        self.close()

    async def __aenter__(self):
        return self

    async def __aexit__(self, *args):
        await self.aclose()
```

#### 2. Cliente WebSocket Síncrono

Módulo: `trustgraph-base/trustgraph/api/socket_client.py` (novo)

**Classe SocketClient**:

```python
class SocketClient:
    """Synchronous WebSocket client"""
    def __init__(self, url: str, timeout: int, token: Optional[str]):
        self.url = self._convert_to_ws_url(url)
        self.timeout = timeout
        self.token = token
        self._connection = None
        self._request_counter = 0

    def flow(self, flow_id: str) -> SocketFlowInstance:
        """Get flow instance for WebSocket operations"""
        return SocketFlowInstance(self, flow_id)

    def _connect(self) -> WebSocket:
        """Establish WebSocket connection (lazy)"""
        # Uses asyncio.run() internally to wrap async websockets library
        pass

    def _send_request(
        self,
        service: str,
        flow: Optional[str],
        request: Dict[str, Any],
        streaming: bool = False
    ) -> Union[Dict[str, Any], Iterator[Dict[str, Any]]]:
        """Send request and handle response/streaming"""
        # Synchronous wrapper around async WebSocket calls
        pass

    def close(self) -> None:
        """Close WebSocket connection"""
        pass

class SocketFlowInstance:
    """Synchronous WebSocket flow instance with same interface as REST FlowInstance"""
    def __init__(self, client: SocketClient, flow_id: str):
        self.client = client
        self.flow_id = flow_id

    # Same method signatures as FlowInstance
    def agent(
        self,
        question: str,
        user: str,
        state: Optional[Dict[str, Any]] = None,
        group: Optional[str] = None,
        history: Optional[List[Dict[str, Any]]] = None,
        streaming: bool = False,
        **kwargs
    ) -> Union[Dict[str, Any], Iterator[Dict[str, Any]]]:
        """Agent with optional streaming"""
        pass

    def text_completion(
        self,
        system: str,
        prompt: str,
        streaming: bool = False,
        **kwargs
    ) -> Union[str, Iterator[str]]:
        """Text completion with optional streaming"""
        pass

    # ... similar for graph_rag, document_rag, prompt, etc.
```

**Principais Características:**
Conexão preguiçosa (conecta apenas quando o primeiro pedido é enviado)
Multiplexação de requisições (até 15 simultâneas)
Reconexão automática em caso de desconexão
Análise de resposta em streaming
Operação thread-safe
Wrapper síncrono em torno da biblioteca assíncrona de WebSockets

#### 3. Cliente WebSocket Assíncrono

Módulo: `trustgraph-base/trustgraph/api/async_socket_client.py` (novo)

**Classe AsyncSocketClient:**

```python
class AsyncSocketClient:
    """Asynchronous WebSocket client"""
    def __init__(self, url: str, timeout: int, token: Optional[str]):
        self.url = self._convert_to_ws_url(url)
        self.timeout = timeout
        self.token = token
        self._connection = None
        self._request_counter = 0

    def flow(self, flow_id: str) -> AsyncSocketFlowInstance:
        """Get async flow instance for WebSocket operations"""
        return AsyncSocketFlowInstance(self, flow_id)

    async def _connect(self) -> WebSocket:
        """Establish WebSocket connection (lazy)"""
        # Native async websockets library
        pass

    async def _send_request(
        self,
        service: str,
        flow: Optional[str],
        request: Dict[str, Any],
        streaming: bool = False
    ) -> Union[Dict[str, Any], AsyncIterator[Dict[str, Any]]]:
        """Send request and handle response/streaming"""
        pass

    async def aclose(self) -> None:
        """Close WebSocket connection"""
        pass

class AsyncSocketFlowInstance:
    """Asynchronous WebSocket flow instance"""
    def __init__(self, client: AsyncSocketClient, flow_id: str):
        self.client = client
        self.flow_id = flow_id

    # Same method signatures as FlowInstance (but async)
    async def agent(
        self,
        question: str,
        user: str,
        state: Optional[Dict[str, Any]] = None,
        group: Optional[str] = None,
        history: Optional[List[Dict[str, Any]]] = None,
        streaming: bool = False,
        **kwargs
    ) -> Union[Dict[str, Any], AsyncIterator[Dict[str, Any]]]:
        """Agent with optional streaming"""
        pass

    async def text_completion(
        self,
        system: str,
        prompt: str,
        streaming: bool = False,
        **kwargs
    ) -> Union[str, AsyncIterator[str]]:
        """Text completion with optional streaming"""
        pass

    # ... similar for graph_rag, document_rag, prompt, etc.
```

**Principais Características:**
Suporte nativo para async/await
Eficiente para aplicações assíncronas (FastAPI, aiohttp)
Sem bloqueio de threads
Mesma interface da versão síncrona
AsyncIterator para streaming

#### 4. Cliente de Operações em Lote Síncronas

Módulo: `trustgraph-base/trustgraph/api/bulk_client.py` (novo)

**Classe BulkClient:**

```python
class BulkClient:
    """Synchronous bulk operations client"""
    def __init__(self, url: str, timeout: int, token: Optional[str]):
        self.url = self._convert_to_ws_url(url)
        self.timeout = timeout
        self.token = token

    def import_triples(
        self,
        flow: str,
        triples: Iterator[Triple],
        **kwargs
    ) -> None:
        """Bulk import triples via WebSocket"""
        pass

    def export_triples(
        self,
        flow: str,
        **kwargs
    ) -> Iterator[Triple]:
        """Bulk export triples via WebSocket"""
        pass

    def import_graph_embeddings(
        self,
        flow: str,
        embeddings: Iterator[Dict[str, Any]],
        **kwargs
    ) -> None:
        """Bulk import graph embeddings via WebSocket"""
        pass

    def export_graph_embeddings(
        self,
        flow: str,
        **kwargs
    ) -> Iterator[Dict[str, Any]]:
        """Bulk export graph embeddings via WebSocket"""
        pass

    # ... similar for document embeddings, entity contexts, objects

    def close(self) -> None:
        """Close connections"""
        pass
```

**Principais Características:**
Baseado em iteradores para uso constante de memória.
Conexões WebSocket dedicadas por operação.
Rastreamento de progresso (callback opcional).
Tratamento de erros com relatórios de sucesso parcial.

#### 5. Cliente de Operações em Massa Assíncronas

Módulo: `trustgraph-base/trustgraph/api/async_bulk_client.py` (novo)

**Classe AsyncBulkClient:**

```python
class AsyncBulkClient:
    """Asynchronous bulk operations client"""
    def __init__(self, url: str, timeout: int, token: Optional[str]):
        self.url = self._convert_to_ws_url(url)
        self.timeout = timeout
        self.token = token

    async def import_triples(
        self,
        flow: str,
        triples: AsyncIterator[Triple],
        **kwargs
    ) -> None:
        """Bulk import triples via WebSocket"""
        pass

    async def export_triples(
        self,
        flow: str,
        **kwargs
    ) -> AsyncIterator[Triple]:
        """Bulk export triples via WebSocket"""
        pass

    async def import_graph_embeddings(
        self,
        flow: str,
        embeddings: AsyncIterator[Dict[str, Any]],
        **kwargs
    ) -> None:
        """Bulk import graph embeddings via WebSocket"""
        pass

    async def export_graph_embeddings(
        self,
        flow: str,
        **kwargs
    ) -> AsyncIterator[Dict[str, Any]]:
        """Bulk export graph embeddings via WebSocket"""
        pass

    # ... similar for document embeddings, entity contexts, objects

    async def aclose(self) -> None:
        """Close connections"""
        pass
```

**Principais Características:**
Baseado em AsyncIterator para uso constante de memória
Eficiente para aplicações assíncronas
Suporte nativo para async/await
Mesma interface da versão síncrona

#### 6. API REST Flow (Síncrona - Inalterada)

Módulo: `trustgraph-base/trustgraph/api/flow.py`

A API REST Flow permanece **completamente inalterada** para compatibilidade com versões anteriores. Todos os métodos existentes continuam a funcionar:

`Flow.list()`, `Flow.start()`, `Flow.stop()`, etc.
`FlowInstance.agent()`, `FlowInstance.text_completion()`, `FlowInstance.graph_rag()`, etc.
Todas as assinaturas e tipos de retorno existentes preservados

**Novo:** Adicione `graph_embeddings_query()` a REST FlowInstance para paridade de recursos:

```python
class FlowInstance:
    # All existing methods unchanged...

    # New: Graph embeddings query (REST)
    def graph_embeddings_query(
        self,
        text: str,
        user: str,
        collection: str,
        limit: int = 10,
        **kwargs
    ) -> List[Dict[str, Any]]:
        """Query graph embeddings for semantic search"""
        # Calls POST /api/v1/flow/{flow}/service/graph-embeddings
        pass
```

#### 7. API de Fluxo REST Assíncrono

Módulo: `trustgraph-base/trustgraph/api/async_flow.py` (novo)

**Classes AsyncFlow e AsyncFlowInstance:**

```python
class AsyncFlow:
    """Asynchronous REST-based flow interface"""
    def __init__(self, url: str, timeout: int, token: Optional[str]):
        self.url = url
        self.timeout = timeout
        self.token = token

    async def list(self) -> List[Dict[str, Any]]:
        """List all flows"""
        pass

    async def get(self, id: str) -> Dict[str, Any]:
        """Get flow definition"""
        pass

    async def start(self, class_name: str, id: str, description: str, parameters: Dict) -> None:
        """Start a flow"""
        pass

    async def stop(self, id: str) -> None:
        """Stop a flow"""
        pass

    def id(self, flow_id: str) -> AsyncFlowInstance:
        """Get async flow instance"""
        return AsyncFlowInstance(self.url, self.timeout, self.token, flow_id)

    async def aclose(self) -> None:
        """Close connection"""
        pass

class AsyncFlowInstance:
    """Asynchronous REST flow instance"""

    async def agent(
        self,
        question: str,
        user: str,
        state: Optional[Dict[str, Any]] = None,
        group: Optional[str] = None,
        history: Optional[List[Dict[str, Any]]] = None,
        **kwargs
    ) -> Dict[str, Any]:
        """Async agent execution"""
        pass

    async def text_completion(
        self,
        system: str,
        prompt: str,
        **kwargs
    ) -> str:
        """Async text completion"""
        pass

    async def graph_rag(
        self,
        question: str,
        user: str,
        collection: str,
        **kwargs
    ) -> str:
        """Async graph RAG"""
        pass

    # ... all other FlowInstance methods as async versions
```

**Principais Características:**
HTTP assíncrono nativo usando `aiohttp` ou `httpx`
Mesmas assinaturas de método da API REST síncrona
Sem streaming (use `async_socket()` para streaming)
Eficiente para aplicações assíncronas

#### 8. API de Métricas

Módulo: `trustgraph-base/trustgraph/api/metrics.py` (novo)

**Métricas Síncronas:**

```python
class Metrics:
    def __init__(self, url: str, timeout: int, token: Optional[str]):
        self.url = url
        self.timeout = timeout
        self.token = token

    def get(self) -> str:
        """Get Prometheus metrics as text"""
        # Call GET /api/metrics
        pass
```

**Métricas Assíncronas**:

```python
class AsyncMetrics:
    def __init__(self, url: str, timeout: int, token: Optional[str]):
        self.url = url
        self.timeout = timeout
        self.token = token

    async def get(self) -> str:
        """Get Prometheus metrics as text"""
        # Call GET /api/metrics
        pass
```

#### 9. Tipos Aprimorados

Módulo: `trustgraph-base/trustgraph/api/types.py` (modificado)

**Novos Tipos**:

```python
from typing import Iterator, Union, Dict, Any
import dataclasses

@dataclasses.dataclass
class StreamingChunk:
    """Base class for streaming chunks"""
    content: str
    end_of_message: bool = False

@dataclasses.dataclass
class AgentThought(StreamingChunk):
    """Agent reasoning chunk"""
    chunk_type: str = "thought"

@dataclasses.dataclass
class AgentObservation(StreamingChunk):
    """Agent tool observation chunk"""
    chunk_type: str = "observation"

@dataclasses.dataclass
class AgentAnswer(StreamingChunk):
    """Agent final answer chunk"""
    chunk_type: str = "final-answer"
    end_of_dialog: bool = False

@dataclasses.dataclass
class RAGChunk(StreamingChunk):
    """RAG streaming chunk"""
    end_of_stream: bool = False
    error: Optional[Dict[str, str]] = None

# Type aliases for clarity
AgentStream = Iterator[Union[AgentThought, AgentObservation, AgentAnswer]]
RAGStream = Iterator[RAGChunk]
CompletionStream = Iterator[str]
```

#### 6. API de Métricas

Módulo: `trustgraph-base/trustgraph/api/metrics.py` (novo)

```python
class Metrics:
    def __init__(self, url: str, timeout: int, token: Optional[str]):
        self.url = url
        self.timeout = timeout
        self.token = token

    def get(self) -> str:
        """Get Prometheus metrics as text"""
        # Call GET /api/metrics
        pass
```

### Abordagem de Implementação

#### Fase 1: Aprimoramento da API Central (Semana 1)

1. Adicionar métodos `socket()`, `bulk()` e `metrics()` à classe `Api`
2. Implementar inicialização preguiçosa para clientes WebSocket e em lote
3. Adicionar suporte a gerenciador de contexto (`__enter__`, `__exit__`)
4. Adicionar método `close()` para limpeza
5. Adicionar testes unitários para aprimoramentos da classe da API
6. Verificar compatibilidade com versões anteriores

**Compatibilidade com versões anteriores**: Nenhuma alteração disruptiva. Apenas novos métodos.

#### Fase 2: Cliente WebSocket (Semana 2-3)

1. Implementar classe `SocketClient` com gerenciamento de conexão
2. Implementar `SocketFlowInstance` com as mesmas assinaturas de método de `FlowInstance`
3. Adicionar suporte para multiplexação de solicitações (até 15 simultâneas)
4. Adicionar análise de resposta em streaming para diferentes tipos de fragmentos
5. Adicionar lógica de reconexão automática
6. Adicionar testes unitários e de integração
7. Documentar padrões de uso do WebSocket

**Compatibilidade com versões anteriores**: Nova interface apenas. Sem impacto no código existente.

#### Fase 3: Suporte a Streaming (Semana 3-4)

1. Adicionar classes de tipo de fragmento de streaming (`AgentThought`, `AgentObservation`, `AgentAnswer`, `RAGChunk`)
2. Implementar análise de resposta em streaming em `SocketClient`
3. Adicionar parâmetro de streaming a todos os métodos LLM em `SocketFlowInstance`
4. Lidar com casos de erro durante o streaming
5. Adicionar testes unitários e de integração para streaming
6. Adicionar exemplos de streaming à documentação

**Compatibilidade com versões anteriores**: Nova interface apenas. API REST existente inalterada.

#### Fase 4: Operações em Lote (Semana 4-5)

1. Implementar classe `BulkClient`
2. Adicionar métodos de importação/exportação em lote para triplas, incorporações, contextos, objetos
3. Implementar processamento baseado em iterador para uso de memória constante
4. Adicionar rastreamento de progresso (callback opcional)
5. Adicionar tratamento de erros com relatório de sucesso parcial
6. Adicionar testes unitários e de integração
7. Adicionar exemplos de operações em lote

**Compatibilidade com versões anteriores**: Nova interface apenas. Sem impacto no código existente.

#### Fase 5: Paridade de Recursos e Refinamento (Semana 5)

1. Adicionar `graph_embeddings_query()` ao REST `FlowInstance`
2. Implementar classe `Metrics`
3. Adicionar testes de integração abrangentes
4. Teste de desempenho
5. Atualizar toda a documentação
6. Criar guia de migração

**Compatibilidade com versões anteriores**: Novos métodos apenas. Sem impacto no código existente.

### Modelos de Dados

#### Seleção de Interface

```python
# Single API instance, same URL for all interfaces
api = Api(url="http://localhost:8088/")

# Synchronous interfaces
rest_flow = api.flow().id("default")           # Sync REST
socket_flow = api.socket().flow("default")     # Sync WebSocket
bulk = api.bulk()                               # Sync bulk operations
metrics = api.metrics()                         # Sync metrics

# Asynchronous interfaces
async_rest_flow = api.async_flow().id("default")      # Async REST
async_socket_flow = api.async_socket().flow("default") # Async WebSocket
async_bulk = api.async_bulk()                          # Async bulk operations
async_metrics = api.async_metrics()                    # Async metrics
```

#### Tipos de Resposta de Streaming

**Streaming do Agente**:

```python
api = Api(url="http://localhost:8088/")

# REST interface - non-streaming (existing)
rest_flow = api.flow().id("default")
response = rest_flow.agent(question="What is ML?", user="user123")
print(response["response"])

# WebSocket interface - non-streaming (same signature)
socket_flow = api.socket().flow("default")
response = socket_flow.agent(question="What is ML?", user="user123")
print(response["response"])

# WebSocket interface - streaming (new)
for chunk in socket_flow.agent(question="What is ML?", user="user123", streaming=True):
    if isinstance(chunk, AgentThought):
        print(f"Thinking: {chunk.content}")
    elif isinstance(chunk, AgentObservation):
        print(f"Observed: {chunk.content}")
    elif isinstance(chunk, AgentAnswer):
        print(f"Answer: {chunk.content}")
        if chunk.end_of_dialog:
            break
```

**Streaming RAG**:

```python
api = Api(url="http://localhost:8088/")

# REST interface - non-streaming (existing)
rest_flow = api.flow().id("default")
response = rest_flow.graph_rag(question="What is Python?", user="user123", collection="default")
print(response)

# WebSocket interface - streaming (new)
socket_flow = api.socket().flow("default")
for chunk in socket_flow.graph_rag(
    question="What is Python?",
    user="user123",
    collection="default",
    streaming=True
):
    print(chunk.content, end="", flush=True)
    if chunk.end_of_stream:
        break
```

**Operações em Lote (Síncronas):**

```python
api = Api(url="http://localhost:8088/")

# Bulk import triples
def triple_generator():
    yield Triple(s="http://ex.com/alice", p="http://ex.com/type", o="Person")
    yield Triple(s="http://ex.com/alice", p="http://ex.com/name", o="Alice")
    yield Triple(s="http://ex.com/bob", p="http://ex.com/type", o="Person")

bulk = api.bulk()
bulk.import_triples(flow="default", triples=triple_generator())

# Bulk export triples
for triple in bulk.export_triples(flow="default"):
    print(f"{triple.s} -> {triple.p} -> {triple.o}")
```

**Operações em Lote (Assíncronas):**

```python
import asyncio

async def main():
    api = Api(url="http://localhost:8088/")

    # Async bulk import triples
    async def async_triple_generator():
        yield Triple(s="http://ex.com/alice", p="http://ex.com/type", o="Person")
        yield Triple(s="http://ex.com/alice", p="http://ex.com/name", o="Alice")
        yield Triple(s="http://ex.com/bob", p="http://ex.com/type", o="Person")

    bulk = api.async_bulk()
    await bulk.import_triples(flow="default", triples=async_triple_generator())

    # Async bulk export triples
    async for triple in bulk.export_triples(flow="default"):
        print(f"{triple.s} -> {triple.p} -> {triple.o}")

asyncio.run(main())
```

**Exemplo de REST Assíncrono:**

```python
import asyncio

async def main():
    api = Api(url="http://localhost:8088/")

    # Async REST flow operations
    flow = api.async_flow().id("default")
    response = await flow.agent(question="What is ML?", user="user123")
    print(response["response"])

asyncio.run(main())
```

**Exemplo de Streaming WebSocket Assíncrono:**

```python
import asyncio

async def main():
    api = Api(url="http://localhost:8088/")

    # Async WebSocket streaming
    socket = api.async_socket()
    flow = socket.flow("default")

    async for chunk in flow.agent(question="What is ML?", user="user123", streaming=True):
        if isinstance(chunk, AgentAnswer):
            print(chunk.content, end="", flush=True)
            if chunk.end_of_dialog:
                break

asyncio.run(main())
```

### APIs

#### New APIs

1. **Classe de API Core**:
   **Síncrono**:
     `Api.socket()` - Obter cliente WebSocket síncrono
     `Api.bulk()` - Obter cliente de operações em lote síncrono
     `Api.metrics()` - Obter cliente de métricas síncrono
     `Api.close()` - Fechar todas as conexões síncronas
     Suporte a gerenciador de contexto (`__enter__`, `__exit__`)
   **Assíncrono**:
     `Api.async_flow()` - Obter cliente de fluxo REST assíncrono
     `Api.async_socket()` - Obter cliente WebSocket assíncrono
     `Api.async_bulk()` - Obter cliente de operações em lote assíncrono
     `Api.async_metrics()` - Obter cliente de métricas assíncrono
     `Api.aclose()` - Fechar todas as conexões assíncronas
     Suporte a gerenciador de contexto assíncrono (`__aenter__`, `__aexit__`)

2. **Cliente WebSocket Síncrono**:
   `SocketClient.flow(flow_id)` - Obter instância de fluxo WebSocket
   `SocketFlowInstance.agent(..., streaming: bool = False)` - Agente com streaming opcional
   `SocketFlowInstance.text_completion(..., streaming: bool = False)` - Conclusão de texto com streaming opcional
   `SocketFlowInstance.graph_rag(..., streaming: bool = False)` - Graph RAG com streaming opcional
   `SocketFlowInstance.document_rag(..., streaming: bool = False)` - Document RAG com streaming opcional
   `SocketFlowInstance.prompt(..., streaming: bool = False)` - Prompt com streaming opcional
   `SocketFlowInstance.graph_embeddings_query()` - Consulta de embeddings de grafo
   Todos os outros métodos FlowInstance com assinaturas idênticas

3. **Cliente WebSocket Assíncrono**:
   `AsyncSocketClient.flow(flow_id)` - Obter instância de fluxo WebSocket assíncrono
   `AsyncSocketFlowInstance.agent(..., streaming: bool = False)` - Agente assíncrono com streaming opcional
   `AsyncSocketFlowInstance.text_completion(..., streaming: bool = False)` - Conclusão de texto assíncrona com streaming opcional
   `AsyncSocketFlowInstance.graph_rag(..., streaming: bool = False)` - Graph RAG assíncrono com streaming opcional
   `AsyncSocketFlowInstance.document_rag(..., streaming: bool = False)` - Document RAG assíncrono com streaming opcional
   `AsyncSocketFlowInstance.prompt(..., streaming: bool = False)` - Prompt assíncrono com streaming opcional
   `AsyncSocketFlowInstance.graph_embeddings_query()` - Consulta de embeddings de grafo assíncrona
   Todos os outros métodos FlowInstance como versões assíncronas

4. **Cliente de Operações em Lote Síncrono**:
   `BulkClient.import_triples(flow, triples)` - Importação em lote de triplas
   `BulkClient.export_triples(flow)` - Exportação em lote de triplas
   `BulkClient.import_graph_embeddings(flow, embeddings)` - Importação em lote de embeddings de grafo
   `BulkClient.export_graph_embeddings(flow)` - Exportação em lote de embeddings de grafo
   `BulkClient.import_document_embeddings(flow, embeddings)` - Importação em lote de embeddings de documentos
   `BulkClient.export_document_embeddings(flow)` - Exportação em lote de embeddings de documentos
   `BulkClient.import_entity_contexts(flow, contexts)` - Importação em lote de contextos de entidades
   `BulkClient.export_entity_contexts(flow)` - Exportação em lote de contextos de entidades
   `BulkClient.import_objects(flow, objects)` - Importação em lote de objetos

5. **Cliente de Operações em Lote Assíncrono**:
   `AsyncBulkClient.import_triples(flow, triples)` - Importação assíncrona em lote de triplas
   `AsyncBulkClient.export_triples(flow)` - Exportação assíncrona em lote de triplas
   `AsyncBulkClient.import_graph_embeddings(flow, embeddings)` - Importação assíncrona em lote de embeddings de grafo
   `AsyncBulkClient.export_graph_embeddings(flow)` - Exportação assíncrona em lote de embeddings de grafo
   `AsyncBulkClient.import_document_embeddings(flow, embeddings)` - Importação assíncrona em lote de embeddings de documentos
   `AsyncBulkClient.export_document_embeddings(flow)` - Exportação assíncrona em lote de embeddings de documentos
   `AsyncBulkClient.import_entity_contexts(flow, contexts)` - Importação assíncrona em lote de contextos de entidades
   `AsyncBulkClient.export_entity_contexts(flow)` - Exportação assíncrona em lote de contextos de entidades
   `AsyncBulkClient.import_objects(flow, objects)` - Importação assíncrona em lote de objetos

6. **Cliente de Fluxo REST Assíncrono**:
   `AsyncFlow.list()` - Listar todos os fluxos de forma assíncrona
   `AsyncFlow.get(id)` - Obter definição de fluxo de forma assíncrona
   `AsyncFlow.start(...)` - Iniciar fluxo de forma assíncrona
   `AsyncFlow.stop(id)` - Parar fluxo de forma assíncrona
   `AsyncFlow.id(flow_id)` - Obter instância de fluxo de forma assíncrona
   `AsyncFlowInstance.agent(...)` - Execução de agente assíncrona
   `AsyncFlowInstance.text_completion(...)` - Conclusão de texto assíncrona
   `AsyncFlowInstance.graph_rag(...)` - Graph RAG assíncrono
   Todos os outros métodos FlowInstance como versões assíncronas

7. **Clientes de Métricas**:
   `Metrics.get()` - Métricas Prometheus síncronas
   `AsyncMetrics.get()` - Métricas Prometheus assíncronas

8. **Aprimoramento da API de Fluxo REST**:
   `FlowInstance.graph_embeddings_query()` - Consulta de embeddings de grafo (paridade de recursos síncrona)
   `AsyncFlowInstance.graph_embeddings_query()` - Consulta de embeddings de grafo (paridade de recursos assíncrona)

#### APIs Modificadas

1. **Construtor** (melhoria menor):
   ```python
   Api(url: str, timeout: int = 60, token: Optional[str] = None)
   ```
   Adicionado parâmetro `token` (opcional, para autenticação)
   Se `None` (padrão): Nenhuma autenticação utilizada
   Se especificado: Usado como token bearer para REST (`Authorization: Bearer <token>`), parâmetro de consulta para WebSocket (`?token=<token>`)
   Nenhuma outra alteração - totalmente compatível com versões anteriores

2. **Nenhuma Alteração Significativa**:
   Todos os métodos da API REST existentes permanecem inalterados
   Todas as assinaturas existentes são preservadas
   Todos os tipos de retorno existentes são preservados

### Detalhes da Implementação

#### Tratamento de Erros

**Erros de Conexão WebSocket**:
```python
try:
    api = Api(url="http://localhost:8088/")
    socket = api.socket()
    socket_flow = socket.flow("default")
    response = socket_flow.agent(question="...", user="user123")
except ConnectionError as e:
    print(f"WebSocket connection failed: {e}")
    print("Hint: Ensure Gateway is running and WebSocket endpoint is accessible")
```

**Fallback Elegante**:
```python
api = Api(url="http://localhost:8088/")

try:
    # Try WebSocket streaming first
    socket_flow = api.socket().flow("default")
    for chunk in socket_flow.agent(question="...", user="...", streaming=True):
        print(chunk.content)
except ConnectionError:
    # Fall back to REST non-streaming
    print("WebSocket unavailable, falling back to REST")
    rest_flow = api.flow().id("default")
    response = rest_flow.agent(question="...", user="...")
    print(response["response"])
```

**Erros de Streaming Parcial:**
```python
api = Api(url="http://localhost:8088/")
socket_flow = api.socket().flow("default")

accumulated = []
try:
    for chunk in socket_flow.graph_rag(question="...", streaming=True):
        accumulated.append(chunk.content)
        if chunk.error:
            print(f"Error occurred: {chunk.error}")
            print(f"Partial response: {''.join(accumulated)}")
            break
except Exception as e:
    print(f"Streaming error: {e}")
    print(f"Partial response: {''.join(accumulated)}")
```

#### Gerenciamento de Recursos

**Suporte a Gerenciadores de Contexto**:
```python
# Automatic cleanup
with Api(url="http://localhost:8088/") as api:
    socket_flow = api.socket().flow("default")
    response = socket_flow.agent(question="...", user="user123")
# All connections automatically closed

# Manual cleanup
api = Api(url="http://localhost:8088/")
try:
    socket_flow = api.socket().flow("default")
    response = socket_flow.agent(question="...", user="user123")
finally:
    api.close()  # Explicitly close all connections (WebSocket, bulk, etc.)
```

#### Threads e Concorrência

**Segurança de Threads**:
Cada instância de `Api` mantém sua própria conexão.
O transporte WebSocket usa bloqueios para multiplexação de solicitações com segurança de thread.
Múltiplas threads podem compartilhar uma instância de `Api` com segurança.
Iteradores de streaming não são seguros para threads (consumir de uma única thread).

**Suporte Assíncrono** (consideração futura):
```python
# Phase 2 enhancement (not in initial scope)
import asyncio

async def main():
    api = await AsyncApi(url="ws://localhost:8088/")
    flow = api.flow().id("default")

    async for chunk in flow.agent(question="...", streaming=True):
        print(chunk.content)

    await api.close()

asyncio.run(main())
```

## Considerações de Segurança

### Autenticação

**Parâmetro de Token**:
```python
# No authentication (default)
api = Api(url="http://localhost:8088/")

# With authentication
api = Api(url="http://localhost:8088/", token="mytoken")
```

**Transporte REST**:
Token do transportador via cabeçalho `Authorization`
Aplicado automaticamente a todas as requisições REST
Formato: `Authorization: Bearer <token>`

**Transporte WebSocket**:
Token via parâmetro de consulta anexado à URL do WebSocket
Aplicado automaticamente durante o estabelecimento da conexão
Formato: `ws://localhost:8088/api/v1/socket?token=<token>`

**Implementação**:
```python
class SocketClient:
    def _connect(self) -> WebSocket:
        # Construct WebSocket URL with optional token
        ws_url = f"{self.url}/api/v1/socket"
        if self.token:
            ws_url = f"{ws_url}?token={self.token}"
        # Connect to WebSocket
        return websocket.connect(ws_url)
```

**Exemplo**:
```python
# REST with auth
api = Api(url="http://localhost:8088/", token="mytoken")
flow = api.flow().id("default")
# All REST calls include: Authorization: Bearer mytoken

# WebSocket with auth
socket = api.socket()
# Connects to: ws://localhost:8088/api/v1/socket?token=mytoken
```

### Comunicação Segura

Suporta os esquemas WS (WebSocket) e WSS (WebSocket Secure).
Validação de certificado TLS para conexões WSS.
Verificação de certificado opcional para desenvolvimento (com aviso).

### Validação de Entrada

Valida esquemas de URL (http, https, ws, wss).
Valida valores de parâmetros de transporte.
Valida combinações de parâmetros de streaming.
Valida tipos de dados para importação em lote.

## Considerações de Desempenho

### Melhorias de Latência

**Operações LLM em Streaming**:
**Tempo para o primeiro token**: ~500ms (vs ~30s sem streaming)
**Melhoria**: 60 vezes mais rápido em termos de desempenho percebido.
**Aplicável a**: Agente, Graph RAG, Document RAG, Geração de Texto, Prompt.

**Conexões Persistentes**:
**Sobrecarga de conexão**: Eliminada para solicitações subsequentes.
**Handshake WebSocket**: Custo único (~100ms).
**Aplicável a**: Todas as operações ao usar o transporte WebSocket.

### Melhorias de Throughput

**Operações em Lote**:
**Importação de triplas**: ~10.000 triplas/segundo (vs ~100/segundo com REST por item).
**Importação de embeddings**: ~5.000 embeddings/segundo (vs ~50/segundo com REST por item).
**Melhoria**: 100 vezes mais rápido para operações em lote.

**Multiplexação de Requisições**:
**Requisições concorrentes**: Até 15 requisições simultâneas sobre uma única conexão.
**Reutilização de conexão**: Sem sobrecarga de conexão para operações concorrentes.

### Considerações de Memória

**Respostas em Streaming**:
Uso constante de memória (processa os chunks à medida que chegam).
Sem bufferização da resposta completa.
Adequado para saídas muito longas (>1MB).

**Operações em Lote**:
Processamento baseado em iterador (uso constante de memória).
Sem carregamento do conjunto de dados inteiro na memória.
Adequado para conjuntos de dados com milhões de itens.

### Benchmarks (Esperados)

| Operação | REST (existente) | WebSocket (streaming) | Melhoria |
|-----------|----------------|----------------------|-------------|
| Agente (tempo para o primeiro token) | 30s | 0.5s | 60x |
| Graph RAG (tempo para o primeiro token) | 25s | 0.5s | 50x |
| Importação de 10K triplas | 100s | 1s | 100x |
| Importação de 1M triplas | 10.000s (2.7h) | 100s (1.6m) | 100x |
| 10 requisições pequenas concorrentes | 5s (sequencial) | 0.5s (paralelo) | 10x |

## Estratégia de Testes

### Testes Unitários

**Camada de Transporte** (`test_transport.py`):
Testar requisição/resposta de transporte REST
Testar conexão de transporte WebSocket
Testar reconexão de transporte WebSocket
Testar multiplexação de requisições
Testar análise de resposta em streaming
Simular um servidor WebSocket para testes determinísticos

**Métodos da API** (`test_flow.py`, `test_library.py`, etc.):
Testar novos métodos com transporte simulado
Testar tratamento de parâmetros em streaming
Testar iteradores de operações em lote
Testar tratamento de erros

**Tipos** (`test_types.py`):
Testar novos tipos de fragmentos em streaming
Testar serialização/desserialização de tipos

### Testes de Integração

**REST de Ponta a Ponta** (`test_integration_rest.py`):
Testar todas as operações contra o Gateway real (modo REST)
Verificar compatibilidade com versões anteriores
Testar condições de erro

**WebSocket de Ponta a Ponta** (`test_integration_websocket.py`):
Testar todas as operações contra o Gateway real (modo WebSocket)
Testar operações de streaming
Testar operações em lote
Testar requisições concorrentes
Testar recuperação de conexão

**Serviços de Streaming** (`test_streaming_integration.py`):
Testar streaming de agentes (pensamentos, observações, respostas)
Testar streaming RAG (fragmentos incrementais)
Testar streaming de conclusão de texto (token por token)
Testar streaming de prompts
Testar tratamento de erros durante o streaming

**Operações em Lote** (`test_bulk_integration.py`):
Testar importação/exportação em lote de triplas (1K, 10K, 100K itens)
Testar importação/exportação em lote de embeddings
Testar o uso de memória durante operações em lote
Testar o rastreamento de progresso

### Testes de Desempenho

**Benchmarks de Latência** (`test_performance_latency.py`):
Medir o tempo para o primeiro token (streaming vs não streaming)
Medir a sobrecarga de conexão (REST vs WebSocket)
Comparar com benchmarks esperados

**Benchmarks de Throughput** (`test_performance_throughput.py`):
Medir o throughput de importação em lote
Medir a eficiência da multiplexação de requisições
Comparar com benchmarks esperados

### Testes de Compatibilidade

**Compatibilidade com Versões Anteriores** (`test_backward_compatibility.py`):
Executar o conjunto de testes existente contra a API refatorada
Verificar a ausência de alterações que quebrem a compatibilidade
Testar o caminho de migração para padrões comuns

## Plano de Migração

### Fase 1: Migração Transparente (Padrão)

**Não são necessárias alterações no código**. O código existente continua a funcionar:

```python
# Existing code works unchanged
api = Api(url="http://localhost:8088/")
flow = api.flow().id("default")
response = flow.agent(question="What is ML?", user="user123")
```

### Fase 2: Streaming Opcional (Simples)

**Use a interface `api.socket()`** para habilitar o streaming:

```python
# Before: Non-streaming REST
api = Api(url="http://localhost:8088/")
rest_flow = api.flow().id("default")
response = rest_flow.agent(question="What is ML?", user="user123")
print(response["response"])

# After: Streaming WebSocket (same parameters!)
api = Api(url="http://localhost:8088/")  # Same URL
socket_flow = api.socket().flow("default")

for chunk in socket_flow.agent(question="What is ML?", user="user123", streaming=True):
    if isinstance(chunk, AgentAnswer):
        print(chunk.content, end="", flush=True)
```

**Pontos-chave:**
Mesma URL para REST e WebSocket
Mesmas assinaturas de método (fácil migração)
Basta adicionar `.socket()` e `streaming=True`

### Fase 3: Operações em Lote (Nova Funcionalidade)

**Use a interface `api.bulk()`** para grandes conjuntos de dados:

```python
# Before: Inefficient per-item operations
api = Api(url="http://localhost:8088/")
flow = api.flow().id("default")

for triple in my_large_triple_list:
    # Slow per-item operations
    # (no direct bulk insert in REST API)
    pass

# After: Efficient bulk loading
api = Api(url="http://localhost:8088/")  # Same URL
bulk = api.bulk()

# This is fast (10,000 triples/second)
bulk.import_triples(flow="default", triples=iter(my_large_triple_list))
```

### Atualizações na Documentação

1. **README.md**: Adicionar exemplos de streaming e WebSocket
2. **Referência da API**: Documentar todos os novos métodos e parâmetros
3. **Guia de Migração**: Guia passo a passo para habilitar o streaming
4. **Exemplos**: Adicionar scripts de exemplo para padrões comuns
5. **Guia de Desempenho**: Documentar as melhorias de desempenho esperadas

### Política de Descontinuação

**Nenhuma descontinuação**. Todas as APIs existentes permanecem suportadas. Esta é uma melhoria pura.

## Cronograma

### Semana 1: Fundação
Camada de abstração de transporte
Refatorar o código REST existente
Testes unitários para a camada de transporte
Verificação de compatibilidade com versões anteriores

### Semana 2: Transporte WebSocket
Implementação do transporte WebSocket
Gerenciamento de conexão e reconexão
Multiplexação de requisições
Testes unitários e de integração

### Semana 3: Suporte a Streaming
Adicionar parâmetro de streaming aos métodos LLM
Implementar análise de resposta de streaming
Adicionar tipos de fragmentos de streaming
Testes de integração de streaming

### Semana 4: Operações em Lote
Adicionar métodos de importação/exportação em lote
Implementar operações baseadas em iteradores
Testes de desempenho
Testes de integração de operações em lote

### Semana 5: Paridade de Recursos e Documentação
Adicionar consulta de incorporações de grafos
Adicionar API de métricas
Documentação abrangente
Guia de migração
Versão candidata

### Semana 6: Lançamento
Testes de integração finais
Benchmarking de desempenho
Documentação de lançamento
Anúncio para a comunidade

**Duração Total**: 6 semanas

## Perguntas Abertas

### Perguntas de Design da API

1. **Suporte Assíncrono**: ✅ **RESOLVIDO** - Suporte assíncrono completo incluído no lançamento inicial
   Todas as interfaces possuem variantes assíncronas: `async_flow()`, `async_socket()`, `async_bulk()`, `async_metrics()`
   Fornece total simetria entre as APIs síncronas e assíncronas
   Essencial para frameworks assíncronos modernos (FastAPI, aiohttp)

2. **Rastreamento de Progresso**: As operações em lote devem suportar callbacks de progresso?
   ```python
   def progress_callback(processed: int, total: Optional[int]):
       print(f"Processed {processed} items")

   bulk.import_triples(flow="default", triples=triples, on_progress=progress_callback)
   ```
   **Recomendação**: Adicionar na Fase 2. Não é crítico para a versão inicial.

3. **Tempo Limite de Streaming**: Como devemos tratar os tempos limite para operações de streaming?
   **Recomendação**: Usar o mesmo tempo limite que as operações não-streaming, mas resetar a cada bloco recebido.

4. **Bufferização de Blocos**: Devemos bufferizar os blocos ou retornar imediatamente?
   **Recomendação**: Retornar imediatamente para a menor latência.

5. **Serviços Globais via WebSocket**: `api.socket()` deve suportar serviços globais (biblioteca, conhecimento, coleção, configuração) ou apenas serviços específicos do fluxo?
   **Recomendação**: Começar apenas com serviços específicos do fluxo (onde o streaming é importante). Adicionar serviços globais, se necessário, na Fase 2.

### Perguntas de Implementação

1. **Biblioteca WebSocket**: Devemos usar `websockets`, `websocket-client` ou `aiohttp`?
   **Recomendação**: `websockets` (assíncrono, maduro, bem mantido). Envolver em uma interface síncrona usando `asyncio.run()`.

2. **Pool de Conexões**: Devemos suportar múltiplas instâncias concorrentes de `Api` compartilhando um pool de conexões?
   **Recomendação**: Adiar para a Fase 2. Cada instância de `Api` terá suas próprias conexões inicialmente.

3. **Reutilização de Conexões**: `SocketClient` e `BulkClient` devem compartilhar a mesma conexão WebSocket, ou usar conexões separadas?
   **Recomendação**: Conexões separadas. Implementação mais simples, separação mais clara de responsabilidades.

4. **Conexão Preguiçosa vs. Ansiosa**: A conexão WebSocket deve ser estabelecida em `api.socket()` ou na primeira requisição?
   **Recomendação**: Preguiçosa (na primeira requisição). Evita a sobrecarga da conexão se o usuário usar apenas métodos REST.

### Perguntas de Teste

1. **Gateway Mock**: Devemos criar um Gateway mock leve para testes, ou testar contra o Gateway real?
   **Recomendação**: Ambos. Usar mocks para testes unitários, Gateway real para testes de integração.

2. **Testes de Regressão de Desempenho**: Devemos adicionar testes de regressão de desempenho automatizados ao CI?
   **Recomendação**: Sim, mas com limites generosos para levar em conta a variabilidade do ambiente do CI.

## Referências

### Especificações Técnicas Relacionadas
`docs/tech-specs/streaming-llm-responses.md` - Implementação de streaming no Gateway
`docs/tech-specs/rag-streaming-support.md` - Suporte de streaming RAG

### Arquivos de Implementação
`trustgraph-base/trustgraph/api/` - Código fonte da API Python
`trustgraph-flow/trustgraph/gateway/` - Código fonte do Gateway
`trustgraph-flow/trustgraph/gateway/dispatch/mux.py` - Implementação de referência de multiplexador WebSocket

### Documentação
`docs/apiSpecification.md` - Referência completa da API
`docs/api-status-summary.md` - Resumo do status da API
`README.websocket` - Documentação do protocolo WebSocket
`STREAMING-IMPLEMENTATION-NOTES.txt` - Notas sobre a implementação de streaming

### Bibliotecas Externas
`websockets` - Biblioteca WebSocket Python (https://websockets.readthedocs.io/)
`requests` - Biblioteca HTTP Python (existente)
