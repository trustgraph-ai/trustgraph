# Referência da API Python do TrustGraph

## Instalação

```bash
pip install trustgraph
```

## Início Rápido

Todas as classes e tipos são importados do pacote `trustgraph.api`:

```python
from trustgraph.api import Api, Triple, ConfigKey

# Create API client
api = Api(url="http://localhost:8088/")

# Get a flow instance
flow = api.flow().id("default")

# Execute a graph RAG query
response = flow.graph_rag(
    query="What are the main topics?",
    user="trustgraph",
    collection="default"
)
```

## Tabela de Conteúdo

### Núcleo

[Api](#api)

### Clientes de Fluxo

[Flow](#flow)
[FlowInstance](#flowinstance)
[AsyncFlow](#asyncflow)
[AsyncFlowInstance](#asyncflowinstance)

### Clientes WebSocket

[SocketClient](#socketclient)
[SocketFlowInstance](#socketflowinstance)
[AsyncSocketClient](#asyncsocketclient)
[AsyncSocketFlowInstance](#asyncsocketflowinstance)

### Operações em Massa

[BulkClient](#bulkclient)
[AsyncBulkClient](#asyncbulkclient)

### Métricas

[Metrics](#metrics)
[AsyncMetrics](#asyncmetrics)

### Tipos de Dados

[Triple](#triple)
[ConfigKey](#configkey)
[ConfigValue](#configvalue)
[DocumentMetadata](#documentmetadata)
[ProcessingMetadata](#processingmetadata)
[CollectionMetadata](#collectionmetadata)
[StreamingChunk](#streamingchunk)
[AgentThought](#agentthought)
[AgentObservation](#agentobservation)
[AgentAnswer](#agentanswer)
[RAGChunk](#ragchunk)

### Exceções

[ProtocolException](#protocolexception)
[TrustGraphException](#trustgraphexception)
[AgentError](#agenterror)
[ConfigError](#configerror)
[DocumentRagError](#documentragerror)
[FlowError](#flowerror)
[GatewayError](#gatewayerror)
[GraphRagError](#graphragerror)
[LLMError](#llmerror)
[LoadError](#loaderror)
[LookupError](#lookuperror)
[NLPQueryError](#nlpqueryerror)
[RowsQueryError](#rowsqueryerror)
[RequestError](#requesterror)
[StructuredQueryError](#structuredqueryerror)
[UnexpectedError](#unexpectederror)
[ApplicationException](#applicationexception)

--

## `Api`

```python
from trustgraph.api import Api
```

Cliente principal da API TrustGraph para operações síncronas e assíncronas.

Esta classe fornece acesso a todos os serviços do TrustGraph, incluindo gerenciamento de fluxo,
operações de grafo de conhecimento, processamento de documentos, consultas RAG e muito mais. Ele suporta
tanto padrões de comunicação baseados em REST quanto baseados em WebSocket.

O cliente pode ser usado como um gerenciador de contexto para limpeza automática de recursos:
    ```python
    with Api(url="http://localhost:8088/") as api:
        result = api.flow().id("default").graph_rag(query="test")
    ```

### Métodos

### `__aenter__(self)`

Entre no gerenciador de contexto assíncrono.

### `__aexit__(self, *args)`

Saia do gerenciador de contexto assíncrono e feche as conexões.

### `__enter__(self)`

Entre no gerenciador de contexto síncrono.

### `__exit__(self, *args)`

Saia do gerenciador de contexto síncrono e feche as conexões.

### `__init__(self, url='http://localhost:8088/', timeout=60, token: str | None = None)`

Inicialize o cliente da API TrustGraph.

**Argumentos:**

`url`: URL base para a API TrustGraph (padrão: "http://localhost:8088/"")
`timeout`: Tempo limite de solicitação em segundos (padrão: 60)
`token`: Token de autorização opcional para autenticação

**Exemplo:**

```python
# Local development
api = Api()

# Production with authentication
api = Api(
    url="https://trustgraph.example.com/",
    timeout=120,
    token="your-api-token"
)
```

### `aclose(self)`

Fechar todas as conexões de cliente assíncronas.

Este método fecha as conexões assíncronas WebSocket, de operação em lote e de fluxo.
Ele é chamado automaticamente ao sair de um gerenciador de contexto assíncrono.

**Exemplo:**

```python
api = Api()
async_socket = api.async_socket()
# ... use async_socket
await api.aclose()  # Clean up connections

# Or use async context manager (automatic cleanup)
async with Api() as api:
    async_socket = api.async_socket()
    # ... use async_socket
# Automatically closed
```

### `async_bulk(self)`

Obtenha um cliente para operações em lote assíncronas.

Fornece operações de importação/exportação em lote com estilo async/await via WebSocket
para o tratamento eficiente de grandes conjuntos de dados.

**Retorna:** AsyncBulkClient: Cliente para operações em lote assíncronas.

**Exemplo:**

```python
async_bulk = api.async_bulk()

# Export triples asynchronously
async for triple in async_bulk.export_triples(flow="default"):
    print(f"{triple.s} {triple.p} {triple.o}")

# Import with async generator
async def triple_gen():
    yield Triple(s="subj", p="pred", o="obj")
    # ... more triples

await async_bulk.import_triples(
    flow="default",
    triples=triple_gen()
)
```

### `async_flow(self)`

Obtenha um cliente de fluxo baseado em REST assíncrono.

Fornece acesso com estilo async/await às operações de fluxo. Isso é preferível
para aplicativos e frameworks Python assíncronos (FastAPI, aiohttp, etc.).

**Retorna:** AsyncFlow: Cliente de fluxo assíncrono

**Exemplo:**

```python
async_flow = api.async_flow()

# List flows
flow_ids = await async_flow.list()

# Execute operations
instance = async_flow.id("default")
result = await instance.text_completion(
    system="You are helpful",
    prompt="Hello"
)
```

### `async_metrics(self)`

Obtenha um cliente de métricas assíncrono.

Fornece acesso com estilo async/await às métricas do Prometheus.

**Retorna:** AsyncMetrics: Cliente de métricas assíncrono

**Exemplo:**

```python
async_metrics = api.async_metrics()
prometheus_text = await async_metrics.get()
print(prometheus_text)
```

### `async_socket(self)`

Obtenha um cliente WebSocket assíncrono para operações de streaming.

Fornece acesso WebSocket no estilo async/await com suporte a streaming.
Este é o método preferido para streaming assíncrono em Python.

**Retorna:** AsyncSocketClient: Cliente WebSocket assíncrono

**Exemplo:**

```python
async_socket = api.async_socket()
flow = async_socket.flow("default")

# Stream agent responses
async for chunk in flow.agent(
    question="Explain quantum computing",
    user="trustgraph",
    streaming=True
):
    if hasattr(chunk, 'content'):
        print(chunk.content, end='', flush=True)
```

### `bulk(self)`

Obtenha um cliente de operações em lote síncronas para importação/exportação.

As operações em lote permitem a transferência eficiente de grandes conjuntos de dados via conexões WebSocket,
incluindo triplas, embeddings, contextos de entidades e objetos.

**Retorna:** BulkClient: Cliente de operações em lote síncronas.

**Exemplo:**

```python
bulk = api.bulk()

# Export triples
for triple in bulk.export_triples(flow="default"):
    print(f"{triple.s} {triple.p} {triple.o}")

# Import triples
def triple_generator():
    yield Triple(s="subj", p="pred", o="obj")
    # ... more triples

bulk.import_triples(flow="default", triples=triple_generator())
```

### `close(self)`

Fechar todas as conexões de cliente síncronas.

Este método fecha as conexões WebSocket e de operações em lote.
Ele é chamado automaticamente quando sai de um gerenciador de contexto.

**Exemplo:**

```python
api = Api()
socket = api.socket()
# ... use socket
api.close()  # Clean up connections

# Or use context manager (automatic cleanup)
with Api() as api:
    socket = api.socket()
    # ... use socket
# Automatically closed
```

### `collection(self)`

Obtenha um cliente de Coleção para gerenciar coleções de dados.

As Coleções organizam documentos e dados de grafos de conhecimento em
agrupamentos lógicos para isolamento e controle de acesso.

**Retorna:** Coleção: Cliente de gerenciamento de Coleção

**Exemplo:**

```python
collection = api.collection()

# List collections
colls = collection.list_collections(user="trustgraph")

# Update collection metadata
collection.update_collection(
    user="trustgraph",
    collection="default",
    name="Default Collection",
    description="Main data collection"
)
```

### `config(self)`

Obtenha um cliente de Config para gerenciar as configurações.

**Retorna:** Config: Cliente de gerenciamento de configuração

**Exemplo:**

```python
config = api.config()

# Get configuration values
values = config.get([ConfigKey(type="llm", key="model")])

# Set configuration
config.put([ConfigValue(type="llm", key="model", value="gpt-4")])
```

### `flow(self)`

Obtenha um cliente Flow para gerenciar e interagir com fluxos.

Os fluxos são as unidades de execução primárias no TrustGraph, fornecendo acesso a
serviços como agentes, consultas RAG, embeddings e processamento de documentos.

**Retorna:** Flow: Cliente de gerenciamento de fluxos

**Exemplo:**

```python
flow_client = api.flow()

# List available blueprints
blueprints = flow_client.list_blueprints()

# Get a specific flow instance
flow_instance = flow_client.id("default")
response = flow_instance.text_completion(
    system="You are helpful",
    prompt="Hello"
)
```

### `knowledge(self)`

Obtenha um cliente Knowledge para gerenciar os núcleos do grafo de conhecimento.

**Retorna:** Knowledge: Cliente de gerenciamento de grafo de conhecimento

**Exemplo:**

```python
knowledge = api.knowledge()

# List available KG cores
cores = knowledge.list_kg_cores(user="trustgraph")

# Load a KG core
knowledge.load_kg_core(id="core-123", user="trustgraph")
```

### `library(self)`

Obtenha um cliente da Biblioteca para gerenciamento de documentos.

A biblioteca fornece armazenamento de documentos, gerenciamento de metadados e
coordenação do fluxo de trabalho de processamento.

**Retorna:** Biblioteca: Cliente de gerenciamento de biblioteca de documentos

**Exemplo:**

```python
library = api.library()

# Add a document
library.add_document(
    document=b"Document content",
    id="doc-123",
    metadata=[],
    user="trustgraph",
    title="My Document",
    comments="Test document"
)

# List documents
docs = library.get_documents(user="trustgraph")
```

### `metrics(self)`

Obtém um cliente de métricas síncronas para monitoramento.

Recupera métricas formatadas em Prometheus do serviço TrustGraph
para monitoramento e observabilidade.

**Retorna:** Métricas: Cliente de métricas síncronas

**Exemplo:**

```python
metrics = api.metrics()
prometheus_text = metrics.get()
print(prometheus_text)
```

### `request(self, path, request)`

Faça uma requisição de API REST de baixo nível.

Este método é principalmente para uso interno, mas pode ser usado para acesso direto
à API quando necessário.

**Argumentos:**

`path`: Caminho do endpoint da API (relativo à URL base)
`request`: Payload da requisição como um dicionário

**Retorna:** dict: Objeto de resposta

**Levanta:**

`ProtocolException`: Se o status da resposta não for 200 ou a resposta não for JSON
`ApplicationException`: Se a resposta contiver um erro

**Exemplo:**

```python
response = api.request("flow", {
    "operation": "list-flows"
})
```

### `socket(self)`

Obtenha um cliente WebSocket síncrono para operações de streaming.

As conexões WebSocket fornecem suporte de streaming para respostas em tempo real
de agentes, consultas RAG e preenchimentos de texto. Este método retorna um
wrapper síncrono em torno do protocolo WebSocket.

**Retorna:** SocketClient: Cliente WebSocket síncrono

**Exemplo:**

```python
socket = api.socket()
flow = socket.flow("default")

# Stream agent responses
for chunk in flow.agent(
    question="Explain quantum computing",
    user="trustgraph",
    streaming=True
):
    if hasattr(chunk, 'content'):
        print(chunk.content, end='', flush=True)
```


--

## `Flow`

```python
from trustgraph.api import Flow
```

Cliente de gerenciamento de fluxo para operações de blueprint e instância de fluxo.

Esta classe fornece métodos para gerenciar blueprints de fluxo (modelos) e
instâncias de fluxo (fluxos em execução). Blueprints definem a estrutura e
os parâmetros dos fluxos, enquanto as instâncias representam fluxos ativos que podem
executar serviços.

### Métodos

### `__init__(self, api)`

Inicializar o cliente de fluxo.

**Argumentos:**

`api`: Instância pai da API para fazer requisições

### `delete_blueprint(self, blueprint_name)`

Excluir um blueprint de fluxo.

**Argumentos:**

`blueprint_name`: Nome do blueprint a ser excluído

**Exemplo:**

```python
api.flow().delete_blueprint("old-blueprint")
```

### `get(self, id)`

Obtenha a definição de uma instância de fluxo em execução.

**Argumentos:**

`id`: ID da instância de fluxo

**Retorna:** dict: Definição da instância de fluxo

**Exemplo:**

```python
flow_def = api.flow().get("default")
print(flow_def)
```

### `get_blueprint(self, blueprint_name)`

Obtenha uma definição de blueprint de fluxo por nome.

**Argumentos:**

`blueprint_name`: Nome do blueprint a ser recuperado

**Retorna:** dict: Definição do blueprint como um dicionário

**Exemplo:**

```python
blueprint = api.flow().get_blueprint("default")
print(blueprint)  # Blueprint configuration
```

### `id(self, id='default')`

Obtenha uma instância de FlowInstance para executar operações em um fluxo específico.

**Argumentos:**

`id`: Identificador do fluxo (padrão: "default")

**Retorna:** FlowInstance: Instância do fluxo para operações de serviço

**Exemplo:**

```python
flow = api.flow().id("my-flow")
response = flow.text_completion(
    system="You are helpful",
    prompt="Hello"
)
```

### `list(self)`

Listar todas as instâncias de fluxo ativas.

**Retorna:** list[str]: Lista de IDs de instâncias de fluxo

**Exemplo:**

```python
flows = api.flow().list()
print(flows)  # ['default', 'flow-1', 'flow-2', ...]
```

### `list_blueprints(self)`

Listar todos os diagramas de fluxo disponíveis.

**Retorna:** list[str]: Lista de nomes de diagramas.

**Exemplo:**

```python
blueprints = api.flow().list_blueprints()
print(blueprints)  # ['default', 'custom-flow', ...]
```

### `put_blueprint(self, blueprint_name, definition)`

Criar ou atualizar um modelo de fluxo.

**Argumentos:**

`blueprint_name`: Nome para o modelo
`definition`: Dicionário de definição do modelo

**Exemplo:**

```python
definition = {
    "services": ["text-completion", "graph-rag"],
    "parameters": {"model": "gpt-4"}
}
api.flow().put_blueprint("my-blueprint", definition)
```

### `request(self, path=None, request=None)`

Faça uma solicitação de API com escopo de fluxo.

**Argumentos:**

`path`: Sufixo de caminho opcional para os endpoints de fluxo.
`request`: Dicionário de carga útil da solicitação.

**Retorna:** dict: Objeto de resposta.

**Levanta:**

`RuntimeError`: Se o parâmetro da solicitação não for especificado.

### `start(self, blueprint_name, id, description, parameters=None)`

Inicie uma nova instância de fluxo a partir de um modelo.

**Argumentos:**

`blueprint_name`: Nome do modelo a ser instanciado.
`id`: Identificador exclusivo para a instância do fluxo.
`description`: Descrição legível por humanos.
`parameters`: Dicionário de parâmetros opcionais.

**Exemplo:**

```python
api.flow().start(
    blueprint_name="default",
    id="my-flow",
    description="My custom flow",
    parameters={"model": "gpt-4"}
)
```

### `stop(self, id)`

Interromper uma instância de fluxo em execução.

**Argumentos:**

`id`: ID da instância de fluxo a ser interrompida

**Exemplo:**

```python
api.flow().stop("my-flow")
```


--

## `FlowInstance`

```python
from trustgraph.api import FlowInstance
```

Cliente de instância de fluxo para executar serviços em um fluxo específico.

Esta classe fornece acesso a todos os serviços do TrustGraph, incluindo:
Preenchimento de texto e incorporações
Operações de agente com gerenciamento de estado
Consultas RAG de grafos e documentos
Operações de grafo de conhecimento (triplas, objetos)
Carregamento e processamento de documentos
Conversão de linguagem natural para consulta GraphQL
Análise de dados estruturados e detecção de esquema
Execução de ferramentas MCP
Modelagem de prompts

Os serviços são acessados através de uma instância de fluxo em execução, identificada por um ID.

### Métodos

### `__init__(self, api, id)`

Inicializa FlowInstance.

**Argumentos:**

`api`: Cliente Flow pai
`id`: Identificador da instância de fluxo

### `agent(self, question, user='trustgraph', state=None, group=None, history=None)`

Executa uma operação de agente com capacidades de raciocínio e uso de ferramentas.

Os agentes podem realizar raciocínio em várias etapas, usar ferramentas e manter o estado da conversa
em várias interações. Esta é uma versão síncrona não transmitida.

**Argumentos:**

`question`: Pergunta ou instrução do usuário
`user`: Identificador do usuário (padrão: "trustgraph")
`state`: Dicionário de estado opcional para conversas com estado
`group`: Identificador de grupo opcional para contextos multiusuário
`history`: Histórico de conversa opcional como uma lista de dicionários de mensagens

**Retorna:** str: Resposta final do agente

**Exemplo:**

```python
flow = api.flow().id("default")

# Simple question
answer = flow.agent(
    question="What is the capital of France?",
    user="trustgraph"
)

# With conversation history
history = [
    {"role": "user", "content": "Hello"},
    {"role": "assistant", "content": "Hi! How can I help?"}
]
answer = flow.agent(
    question="Tell me about Paris",
    user="trustgraph",
    history=history
)
```

### `detect_type(self, sample)`

Detectar o tipo de dado de uma amostra de dados estruturados.

**Argumentos:**

`sample`: Amostra de dados a ser analisada (conteúdo em string)

**Retorna:** Dicionário com detected_type, confidence e metadados opcionais.

### `diagnose_data(self, sample, schema_name=None, options=None)`

Realizar diagnóstico de dados combinado: detectar tipo e gerar descritor.

**Argumentos:**

`sample`: Amostra de dados a ser analisada (conteúdo em string)
`schema_name`: Nome de esquema de destino opcional para geração de descritor.
`options`: Parâmetros opcionais (por exemplo, delimitador para CSV).

**Retorna:** Dicionário com detected_type, confidence, descriptor e metadados.

### `document_embeddings_query(self, text, user, collection, limit=10)`

Consultar trechos de documentos usando similaridade semântica.

Encontra trechos de documentos cujo conteúdo é semanticamente similar ao
texto de entrada, usando embeddings vetoriais.

**Argumentos:**

`text`: Texto de consulta para busca semântica.
`user`: Identificador de usuário/espaço de chaves.
`collection`: Identificador de coleção.
`limit`: Número máximo de resultados (padrão: 10).

**Retorna:** Dicionário: Resultados da consulta com trechos contendo chunk_id e score.

**Exemplo:**

```python
flow = api.flow().id("default")
results = flow.document_embeddings_query(
    text="machine learning algorithms",
    user="trustgraph",
    collection="research-papers",
    limit=5
)
# results contains {"chunks": [{"chunk_id": "doc1/p0/c0", "score": 0.95}, ...]}
```

### `document_rag(self, query, user='trustgraph', collection='default', doc_limit=10)`

Execute uma consulta de Geração Aumentada por Recuperação (RAG) baseada em documentos.

O RAG baseado em documentos usa incorporações vetoriais para encontrar trechos de documentos relevantes,
e então gera uma resposta usando um LLM, utilizando esses trechos como contexto.

**Argumentos:**

`query`: Consulta em linguagem natural
`user`: Identificador de usuário/espaço de chaves (padrão: "trustgraph")
`collection`: Identificador de coleção (padrão: "default")
`doc_limit`: Número máximo de trechos de documentos a serem recuperados (padrão: 10)

**Retorna:** str: Resposta gerada incorporando o contexto do documento

**Exemplo:**

```python
flow = api.flow().id("default")
response = flow.document_rag(
    query="Summarize the key findings",
    user="trustgraph",
    collection="research-papers",
    doc_limit=5
)
print(response)
```

### `embeddings(self, texts)`

Gere incorporações vetoriais para um ou mais textos.

Converte textos em representações vetoriais densas adequadas para busca semântica e
comparação de similaridade.

**Argumentos:**

`texts`: Lista de textos de entrada a serem incorporados

**Retorna:** list[list[list[float]]]: Incorporações vetoriais, um conjunto por texto de entrada

**Exemplo:**

```python
flow = api.flow().id("default")
vectors = flow.embeddings(["quantum computing"])
print(f"Embedding dimension: {len(vectors[0][0])}")
```

### `generate_descriptor(self, sample, data_type, schema_name, options=None)`

Gerar um descritor para mapeamento de dados estruturados para um esquema específico.

**Argumentos:**

`sample`: Amostra de dados a ser analisada (conteúdo de string)
`data_type`: Tipo de dados (csv, json, xml)
`schema_name`: Nome do esquema de destino para a geração do descritor
`options`: Parâmetros opcionais (por exemplo, delimitador para CSV)

**Retorna:** dicionário com o descritor e metadados

### `graph_embeddings_query(self, text, user, collection, limit=10)`

Consultar entidades de grafo de conhecimento usando similaridade semântica.

Encontra entidades no grafo de conhecimento cujas descrições são semanticamente
similares ao texto de entrada, usando incorporações vetoriais.

**Argumentos:**

`text`: Texto de consulta para pesquisa semântica
`user`: Identificador de usuário/espaço de chaves
`collection`: Identificador de coleção
`limit`: Número máximo de resultados (padrão: 10)

**Retorna:** dicionário: Resultados da consulta com entidades similares

**Exemplo:**

```python
flow = api.flow().id("default")
results = flow.graph_embeddings_query(
    text="physicist who discovered radioactivity",
    user="trustgraph",
    collection="scientists",
    limit=5
)
# results contains {"entities": [{"entity": {...}, "score": 0.95}, ...]}
```

### `graph_rag(self, query, user='trustgraph', collection='default', entity_limit=50, triple_limit=30, max_subgraph_size=150, max_path_length=2)`

Execute consulta de Geração Aumentada por Recuperação (RAG) baseada em grafo.

O Graph RAG utiliza a estrutura do grafo de conhecimento para encontrar o contexto relevante,
percorrendo as relações entre entidades, e então gera uma resposta usando um LLM.

**Argumentos:**

`query`: Consulta em linguagem natural
`user`: Identificador de usuário/espaço de chaves (padrão: "trustgraph")
`collection`: Identificador de coleção (padrão: "default")
`entity_limit`: Número máximo de entidades a recuperar (padrão: 50)
`triple_limit`: Número máximo de triplas por entidade (padrão: 30)
`max_subgraph_size`: Número máximo total de triplas no subgrafo (padrão: 150)
`max_path_length`: Profundidade máxima de travessia (padrão: 2)

**Retorna:** str: Resposta gerada incorporando o contexto do grafo

**Exemplo:**

```python
flow = api.flow().id("default")
response = flow.graph_rag(
    query="Tell me about Marie Curie's discoveries",
    user="trustgraph",
    collection="scientists",
    entity_limit=20,
    max_path_length=3
)
print(response)
```

### `load_document(self, document, id=None, metadata=None, user=None, collection=None)`

Carregar um documento binário para processamento.

Envia um documento (PDF, DOCX, imagens, etc.) para extração e
processamento através do pipeline de documentos do fluxo.

**Argumentos:**

`document`: Conteúdo do documento como bytes
`id`: Identificador de documento opcional (gerado automaticamente se for None)
`metadata`: Metadados opcionais (lista de Triplas ou objeto com método emit)
`user`: Identificador de usuário/espaço de chaves (opcional)
`collection`: Identificador de coleção (opcional)

**Retorna:** dict: Resposta de processamento

**Levanta:**

`RuntimeError`: Se metadados forem fornecidos sem id

**Exemplo:**

```python
flow = api.flow().id("default")

# Load a PDF document
with open("research.pdf", "rb") as f:
    result = flow.load_document(
        document=f.read(),
        id="research-001",
        user="trustgraph",
        collection="papers"
    )
```

### `load_text(self, text, id=None, metadata=None, charset='utf-8', user=None, collection=None)`

Carrega o conteúdo de texto para processamento.

Carrega o conteúdo de texto para extração e processamento através do pipeline de texto do fluxo.


**Argumentos:**

`text`: Conteúdo de texto como bytes
`id`: Identificador de documento opcional (gerado automaticamente se for None)
`metadata`: Metadados opcionais (lista de Triplas ou objeto com método emit)
`charset`: Codificação de caracteres (padrão: "utf-8")
`user`: Identificador de usuário/espaço de chaves (opcional)
`collection`: Identificador de coleção (opcional)

**Retorna:** dict: Resposta de processamento

**Levanta:**

`RuntimeError`: Se metadados forem fornecidos sem id

**Exemplo:**

```python
flow = api.flow().id("default")

# Load text content
text_content = b"This is the document content..."
result = flow.load_text(
    text=text_content,
    id="text-001",
    charset="utf-8",
    user="trustgraph",
    collection="documents"
)
```

### `mcp_tool(self, name, parameters={})`

Execute uma ferramenta de Protocolo de Contexto de Modelo (MCP).

As ferramentas MCP fornecem funcionalidade extensível para agentes e fluxos de trabalho,
permitindo a integração com sistemas e serviços externos.

**Argumentos:**

`name`: Nome/identificador da ferramenta
`parameters`: Dicionário de parâmetros da ferramenta (padrão: {})

**Retorna:** str ou dict: Resultado da execução da ferramenta

**Levanta:**

`ProtocolException`: Se o formato da resposta for inválido

**Exemplo:**

```python
flow = api.flow().id("default")

# Execute a tool
result = flow.mcp_tool(
    name="search-web",
    parameters={"query": "latest AI news", "limit": 5}
)
```

### `nlp_query(self, question, max_results=100)`

Converter uma pergunta em linguagem natural em uma consulta GraphQL.

**Argumentos:**

`question`: Pergunta em linguagem natural
`max_results`: Número máximo de resultados a retornar (padrão: 100)

**Retorna:** dicionário com graphql_query, variáveis, schemas detectados, confiança

### `prompt(self, id, variables)`

Executar um modelo de prompt com substituição de variáveis.

Modelos de prompt permitem padrões de prompt reutilizáveis com variáveis dinâmicas.
de substituição, úteis para engenharia de prompt consistente.

**Argumentos:**

`id`: Identificador do modelo de prompt.
`variables`: Dicionário de mapeamentos de nomes de variáveis para valores.

**Retorna:** str ou dict: Resultado do prompt renderizado (texto ou objeto estruturado).

**Levanta:**

`ProtocolException`: Se o formato da resposta for inválido.

**Exemplo:**

```python
flow = api.flow().id("default")

# Text template
result = flow.prompt(
    id="summarize-template",
    variables={"topic": "quantum computing", "length": "brief"}
)

# Structured template
result = flow.prompt(
    id="extract-entities",
    variables={"text": "Marie Curie won Nobel Prizes"}
)
```

### `request(self, path, request)`

Faça uma solicitação de serviço nesta instância de fluxo.

**Argumentos:**

`path`: Caminho do serviço (por exemplo, "service/text-completion")
`request`: Dicionário de carga útil da solicitação

**Retorna:** dict: Resposta do serviço

### `row_embeddings_query(self, text, schema_name, user='trustgraph', collection='default', index_name=None, limit=10)`

Consulta dados de linha usando similaridade semântica em campos indexados.

Encontra linhas cujos valores de campos indexados são semanticamente semelhantes ao
texto de entrada, usando incorporações vetoriais. Isso permite a correspondência aproximada/semântica
em dados estruturados.

**Argumentos:**

`text`: Texto de consulta para pesquisa semântica
`schema_name`: Nome do esquema para pesquisar
`user`: Identificador de usuário/espaço de chaves (padrão: "trustgraph")
`collection`: Identificador de coleção (padrão: "default")
`index_name`: Nome de índice opcional para filtrar a pesquisa para um índice específico
`limit`: Número máximo de resultados (padrão: 10)

**Retorna:** dict: Resultados da consulta com correspondências contendo index_name, index_value, text e score

**Exemplo:**

```python
flow = api.flow().id("default")

# Search for customers by name similarity
results = flow.row_embeddings_query(
    text="John Smith",
    schema_name="customers",
    user="trustgraph",
    collection="sales",
    limit=5
)

# Filter to specific index
results = flow.row_embeddings_query(
    text="machine learning engineer",
    schema_name="employees",
    index_name="job_title",
    limit=10
)
```

### `rows_query(self, query, user='trustgraph', collection='default', variables=None, operation_name=None)`

Execute uma consulta GraphQL contra linhas estruturadas no grafo de conhecimento.

Consulta dados estruturados usando a sintaxe GraphQL, permitindo consultas complexas
com filtragem, agregação e travessia de relacionamentos.

**Argumentos:**

`query`: String de consulta GraphQL
`user`: Identificador de usuário/espaço de chaves (padrão: "trustgraph")
`collection`: Identificador de coleção (padrão: "default")
`variables`: Dicionário opcional de variáveis de consulta
`operation_name`: Nome de operação opcional para documentos com várias operações

**Retorna:** dict: Resposta GraphQL com os campos 'data', 'errors' e/ou 'extensions'

**Levanta:**

`ProtocolException`: Se ocorrer um erro de nível do sistema

**Exemplo:**

```python
flow = api.flow().id("default")

# Simple query
query = '''
{
  scientists(limit: 10) {
    name
    field
    discoveries
  }
}
'''
result = flow.rows_query(
    query=query,
    user="trustgraph",
    collection="scientists"
)

# Query with variables
query = '''
query GetScientist($name: String!) {
  scientists(name: $name) {
    name
    nobelPrizes
  }
}
'''
result = flow.rows_query(
    query=query,
    variables={"name": "Marie Curie"}
)
```

### `schema_selection(self, sample, options=None)`

Selecione os esquemas correspondentes para uma amostra de dados usando análise de prompt.

**Argumentos:**

`sample`: Amostra de dados a ser analisada (conteúdo de string)
`options`: Parâmetros opcionais

**Retorna:** dicionário com array schema_matches e metadados

### `structured_query(self, question, user='trustgraph', collection='default')`

Execute uma pergunta em linguagem natural contra dados estruturados.
Combina a conversão de consulta NLP e a execução GraphQL.

**Argumentos:**

`question`: Pergunta em linguagem natural
`user`: Identificador de keyspace do Cassandra (padrão: "trustgraph")
`collection`: Identificador da coleção de dados (padrão: "default")

**Retorna:** dicionário com dados e erros opcionais

### `text_completion(self, system, prompt)`

Execute a conclusão de texto usando o LLM do fluxo.

**Argumentos:**

`system`: Prompt do sistema que define o comportamento do assistente
`prompt`: Prompt/pergunta do usuário

**Retorna:** str: Texto de resposta gerado

**Exemplo:**

```python
flow = api.flow().id("default")
response = flow.text_completion(
    system="You are a helpful assistant",
    prompt="What is quantum computing?"
)
print(response)
```

### `triples_query(self, s=None, p=None, o=None, user=None, collection=None, limit=10000)`

Consultar triplas de grafos de conhecimento usando correspondência de padrões.

Procura triplas RDF que correspondam aos padrões de sujeito, predicado e/ou
objeto fornecidos. Parâmetros não especificados atuam como curingas.

**Argumentos:**

`s`: URI do sujeito (opcional, use None para curinga)
`p`: URI do predicado (opcional, use None para curinga)
`o`: URI do objeto ou Literal (opcional, use None para curinga)
`user`: Identificador de usuário/espaço de chaves (opcional)
`collection`: Identificador de coleção (opcional)
`limit`: Número máximo de resultados a retornar (padrão: 10000)

**Retorna:** list[Triple]: Lista de objetos Triple correspondentes

**Levanta:**

`RuntimeError`: Se s ou p não forem um Uri, ou o não for um Uri/Literal

**Exemplo:**

```python
from trustgraph.knowledge import Uri, Literal

flow = api.flow().id("default")

# Find all triples about a specific subject
triples = flow.triples_query(
    s=Uri("http://example.org/person/marie-curie"),
    user="trustgraph",
    collection="scientists"
)

# Find all instances of a specific relationship
triples = flow.triples_query(
    p=Uri("http://example.org/ontology/discovered"),
    limit=100
)
```


--

## `AsyncFlow`

```python
from trustgraph.api import AsyncFlow
```

Cliente de gerenciamento de fluxo assíncrono usando a API REST.

Fornece operações de gerenciamento de fluxo baseadas em async/await, incluindo listagem,
início, parada de fluxos e gerenciamento de definições de classes de fluxo. Também fornece
acesso a serviços de escopo de fluxo, como agentes, RAG e consultas, por meio de
endpoints REST não baseados em streaming.

Nota: Para suporte a streaming, use AsyncSocketClient em vez disso.

### Métodos

### `__init__(self, url: str, timeout: int, token: str | None) -> None`

Inicializa o cliente de fluxo assíncrono.

**Argumentos:**

`url`: URL base para a API TrustGraph
`timeout`: Tempo limite de solicitação em segundos
`token`: Token de autorização opcional para autenticação

### `aclose(self) -> None`

Fecha o cliente assíncrono e libera recursos.

Nota: A limpeza é tratada automaticamente pelos gerenciadores de contexto de sessão aiohttp.
Este método é fornecido para consistência com outros clientes assíncronos.

### `delete_class(self, class_name: str)`

Exclui uma definição de classe de fluxo.

Remove um modelo de classe de fluxo do sistema. Não afeta
instâncias de fluxo em execução.

**Argumentos:**

`class_name`: Nome da classe de fluxo a ser excluída

**Exemplo:**

```python
async_flow = await api.async_flow()

# Delete a flow class
await async_flow.delete_class("old-flow-class")
```

### `get(self, id: str) -> Dict[str, Any]`

Obter a definição do fluxo.

Recupera a configuração completa do fluxo, incluindo seu nome de classe,
descrição e parâmetros.

**Argumentos:**

`id`: Identificador do fluxo

**Retorna:** dict: Objeto de definição do fluxo

**Exemplo:**

```python
async_flow = await api.async_flow()

# Get flow definition
flow_def = await async_flow.get("default")
print(f"Flow class: {flow_def.get('class-name')}")
print(f"Description: {flow_def.get('description')}")
```

### `get_class(self, class_name: str) -> Dict[str, Any]`

Obter a definição da classe de fluxo.

Recupera a definição do blueprint para uma classe de fluxo, incluindo seu
esquema de configuração e associações de serviço.

**Argumentos:**

`class_name`: Nome da classe de fluxo

**Retorna:** dict: Objeto de definição da classe de fluxo

**Exemplo:**

```python
async_flow = await api.async_flow()

# Get flow class definition
class_def = await async_flow.get_class("default")
print(f"Services: {class_def.get('services')}")
```

### `id(self, flow_id: str)`

Obtenha uma instância de cliente de fluxo assíncrono.

Retorna um cliente para interagir com os serviços de um fluxo específico
(agente, RAG, consultas, embeddings, etc.).

**Argumentos:**

`flow_id`: Identificador do fluxo

**Retorna:** AsyncFlowInstance: Cliente para operações específicas do fluxo

**Exemplo:**

```python
async_flow = await api.async_flow()

# Get flow instance
flow = async_flow.id("default")

# Use flow services
result = await flow.graph_rag(
    query="What is TrustGraph?",
    user="trustgraph",
    collection="default"
)
```

### `list(self) -> List[str]`

Liste todos os identificadores de fluxo.

Recupera os IDs de todos os fluxos atualmente implementados no sistema.

**Retorna:** list[str]: Lista de identificadores de fluxo

**Exemplo:**

```python
async_flow = await api.async_flow()

# List all flows
flows = await async_flow.list()
print(f"Available flows: {flows}")
```

### `list_classes(self) -> List[str]`

Listar todos os nomes das classes de fluxo.

Recupera os nomes de todas as classes de fluxo (modelos) disponíveis no sistema.

**Retorna:** list[str]: Lista de nomes das classes de fluxo.

**Exemplo:**

```python
async_flow = await api.async_flow()

# List available flow classes
classes = await async_flow.list_classes()
print(f"Available flow classes: {classes}")
```

### `put_class(self, class_name: str, definition: Dict[str, Any])`

Criar ou atualizar uma definição de classe de fluxo.

Armazena um modelo de classe de fluxo que pode ser usado para instanciar fluxos.

**Argumentos:**

`class_name`: Nome da classe de fluxo
`definition`: Objeto de definição da classe de fluxo

**Exemplo:**

```python
async_flow = await api.async_flow()

# Create a custom flow class
class_def = {
    "services": {
        "agent": {"module": "agent", "config": {...}},
        "graph-rag": {"module": "graph-rag", "config": {...}}
    }
}
await async_flow.put_class("custom-flow", class_def)
```

### `request(self, path: str, request_data: Dict[str, Any]) -> Dict[str, Any]`

Faça uma requisição HTTP POST assíncrona para a API Gateway.

Método interno para fazer requisições autenticadas para a API TrustGraph.

**Argumentos:**

`path`: Caminho do endpoint da API (relativo à URL base)
`request_data`: Dicionário de carga útil da requisição

**Retorna:** dict: Objeto de resposta da API

**Levanta:**

`ProtocolException`: Se o status HTTP não for 200 ou a resposta não for um JSON válido
`ApplicationException`: Se a API retornar uma resposta de erro

### `start(self, class_name: str, id: str, description: str, parameters: Dict | None = None)`

Inicia uma nova instância de fluxo.

Cria e inicia um fluxo a partir de uma definição de classe de fluxo com os
parâmetros especificados.

**Argumentos:**

`class_name`: Nome da classe de fluxo a ser instanciada
`id`: Identificador para a nova instância de fluxo
`description`: Descrição legível por humanos do fluxo
`parameters`: Parâmetros de configuração opcionais para o fluxo

**Exemplo:**

```python
async_flow = await api.async_flow()

# Start a flow from a class
await async_flow.start(
    class_name="default",
    id="my-flow",
    description="Custom flow instance",
    parameters={"model": "claude-3-opus"}
)
```

### `stop(self, id: str)`

Interromper um fluxo em execução.

Interrompe e remove uma instância de fluxo, liberando seus recursos.

**Argumentos:**

`id`: Identificador do fluxo a ser interrompido

**Exemplo:**

```python
async_flow = await api.async_flow()

# Stop a flow
await async_flow.stop("my-flow")
```


--

## `AsyncFlowInstance`

```python
from trustgraph.api import AsyncFlowInstance
```

Cliente de instância de fluxo assíncrono.

Fornece acesso async/await a serviços com escopo de fluxo, incluindo agentes,
Consultas RAG, embeddings e consultas de grafo. Todas as operações retornam respostas completas (não em streaming).


Nota: Para suporte a streaming, use AsyncSocketFlowInstance.

### Métodos

### `__init__(self, flow: trustgraph.api.async_flow.AsyncFlow, flow_id: str)`

Inicializa a instância de fluxo assíncrono.

**Argumentos:**

`flow`: Cliente AsyncFlow pai
`flow_id`: Identificador do fluxo

### `agent(self, question: str, user: str, state: Dict | None = None, group: str | None = None, history: List | None = None, **kwargs: Any) -> Dict[str, Any]`

Execute uma operação de agente (não em streaming).

Executa um agente para responder a uma pergunta, com estado de conversa opcional e
histórico. Retorna a resposta completa após o agente ter terminado de
processar.

Nota: Este método não suporta streaming. Para pensamentos e observações do agente em tempo real, use AsyncSocketFlowInstance.agent() em vez disso.


**Argumentos:**

`question`: Pergunta ou instrução do usuário
`user`: Identificador do usuário
`state`: Dicionário de estado opcional para o contexto da conversa
`group`: Identificador de grupo opcional para o gerenciamento de sessões
`history`: Lista de histórico de conversa opcional
`**kwargs`: Parâmetros adicionais específicos do serviço

**Retorna:** dict: Resposta completa do agente, incluindo a resposta e metadados

**Exemplo:**

```python
async_flow = await api.async_flow()
flow = async_flow.id("default")

# Execute agent
result = await flow.agent(
    question="What is the capital of France?",
    user="trustgraph"
)
print(f"Answer: {result.get('response')}")
```

### `document_rag(self, query: str, user: str, collection: str, doc_limit: int = 10, **kwargs: Any) -> str`

Execute consulta RAG baseada em documentos (não em streaming).

Realiza a Geração Aumentada por Recuperação usando incorporações de documentos.
Recupera trechos de documentos relevantes por meio de busca semântica e, em seguida, gera
uma resposta fundamentada nos documentos recuperados. Retorna a resposta completa.

Nota: Este método não suporta streaming. Para respostas RAG em streaming,
use AsyncSocketFlowInstance.document_rag() em vez disso.

**Argumentos:**

`query`: Texto da consulta do usuário
`user`: Identificador do usuário
`collection`: Identificador da coleção contendo os documentos
`doc_limit`: Número máximo de trechos de documentos a serem recuperados (padrão: 10)
`**kwargs`: Parâmetros adicionais específicos do serviço

**Retorna:** str: Resposta completa gerada com base nos dados do documento

**Exemplo:**

```python
async_flow = await api.async_flow()
flow = async_flow.id("default")

# Query documents
response = await flow.document_rag(
    query="What does the documentation say about authentication?",
    user="trustgraph",
    collection="docs",
    doc_limit=5
)
print(response)
```

### `embeddings(self, texts: list, **kwargs: Any)`

Gere incorporações para textos de entrada.

Converte textos em representações vetoriais numéricas usando o modelo de incorporação configurado do fluxo. Útil para pesquisa semântica e comparações de similaridade.



**Argumentos:**

`texts`: Lista de textos de entrada a serem incorporados
`**kwargs`: Parâmetros adicionais específicos do serviço

**Retorna:** dict: Resposta contendo vetores de incorporação

**Exemplo:**

```python
async_flow = await api.async_flow()
flow = async_flow.id("default")

# Generate embeddings
result = await flow.embeddings(texts=["Sample text to embed"])
vectors = result.get("vectors")
print(f"Embedding dimension: {len(vectors[0][0])}")
```

### `graph_embeddings_query(self, text: str, user: str, collection: str, limit: int = 10, **kwargs: Any)`

Consulta incorporações de grafos para busca semântica de entidades.

Realiza uma busca semântica sobre as incorporações de entidades do grafo para encontrar entidades
mais relevantes para o texto de entrada. Retorna entidades classificadas por similaridade.

**Argumentos:**

`text`: Texto de consulta para a busca semântica
`user`: Identificador do usuário
`collection`: Identificador da coleção contendo as incorporações do grafo
`limit`: Número máximo de resultados a serem retornados (padrão: 10)
`**kwargs`: Parâmetros adicionais específicos do serviço

**Retorna:** dict: Resposta contendo correspondências de entidades classificadas com pontuações de similaridade

**Exemplo:**

```python
async_flow = await api.async_flow()
flow = async_flow.id("default")

# Find related entities
results = await flow.graph_embeddings_query(
    text="machine learning algorithms",
    user="trustgraph",
    collection="tech-kb",
    limit=5
)

for entity in results.get("entities", []):
    print(f"{entity['name']}: {entity['score']}")
```

### `graph_rag(self, query: str, user: str, collection: str, max_subgraph_size: int = 1000, max_subgraph_count: int = 5, max_entity_distance: int = 3, **kwargs: Any) -> str`

Execute consulta RAG baseada em grafo (não em streaming).

Realiza a geração aumentada por recuperação usando dados de grafo de conhecimento.
Identifica entidades relevantes e seus relacionamentos, e então gera uma
resposta fundamentada na estrutura do grafo. Retorna a resposta completa.

Nota: Este método não suporta streaming. Para respostas RAG em streaming,
use AsyncSocketFlowInstance.graph_rag() em vez disso.

**Argumentos:**

`query`: Texto da consulta do usuário
`user`: Identificador do usuário
`collection`: Identificador da coleção contendo o grafo de conhecimento
`max_subgraph_size`: Número máximo de triplas por subgrafo (padrão: 1000)
`max_subgraph_count`: Número máximo de subgrafos a serem recuperados (padrão: 5)
`max_entity_distance`: Distância máxima do grafo para expansão de entidades (padrão: 3)
`**kwargs`: Parâmetros adicionais específicos do serviço

**Retorna:** str: Resposta completa gerada com base nos dados do grafo

**Exemplo:**

```python
async_flow = await api.async_flow()
flow = async_flow.id("default")

# Query knowledge graph
response = await flow.graph_rag(
    query="What are the relationships between these entities?",
    user="trustgraph",
    collection="medical-kb",
    max_subgraph_count=3
)
print(response)
```

### `request(self, service: str, request_data: Dict[str, Any]) -> Dict[str, Any]`

Faça uma requisição para um serviço com escopo de fluxo.

Método interno para chamar serviços dentro desta instância de fluxo.

**Argumentos:**

`service`: Nome do serviço (por exemplo, "agent", "graph-rag", "triples")
`request_data`: Payload da requisição do serviço

**Retorna:** dict: Objeto de resposta do serviço

**Lança:**

`ProtocolException`: Se a requisição falhar ou a resposta for inválida
`ApplicationException`: Se o serviço retornar um erro

### `row_embeddings_query(self, text: str, schema_name: str, user: str = 'trustgraph', collection: str = 'default', index_name: str | None = None, limit: int = 10, **kwargs: Any)`

Consulta as incorporações de linhas para pesquisa semântica em dados estruturados.

Realiza uma pesquisa semântica sobre as incorporações do índice de linhas para encontrar linhas cujos
valores de campo indexados são mais semelhantes ao texto de entrada. Permite
correspondência fuzzy/semântica em dados estruturados.

**Argumentos:**

`text`: Texto da consulta para pesquisa semântica
`schema_name`: Nome do esquema para pesquisar
`user`: Identificador do usuário (padrão: "trustgraph")
`collection`: Identificador da coleção (padrão: "default")
`index_name`: Nome de índice opcional para filtrar a pesquisa para um índice específico
`limit`: Número máximo de resultados a serem retornados (padrão: 10)
`**kwargs`: Parâmetros adicionais específicos do serviço

**Retorna:** dict: Resposta contendo correspondências com index_name, index_value, text e score

**Exemplo:**

```python
async_flow = await api.async_flow()
flow = async_flow.id("default")

# Search for customers by name similarity
results = await flow.row_embeddings_query(
    text="John Smith",
    schema_name="customers",
    user="trustgraph",
    collection="sales",
    limit=5
)

for match in results.get("matches", []):
    print(f"{match['index_name']}: {match['index_value']} (score: {match['score']})")
```

### `rows_query(self, query: str, user: str, collection: str, variables: Dict | None = None, operation_name: str | None = None, **kwargs: Any)`

Execute uma consulta GraphQL em linhas armazenadas.

Consulta linhas de dados estruturados usando a sintaxe GraphQL. Suporta consultas complexas
com variáveis e operações nomeadas.

**Argumentos:**

`query`: String da consulta GraphQL
`user`: Identificador do usuário
`collection`: Identificador da coleção contendo as linhas
`variables`: Variáveis de consulta GraphQL opcionais
`operation_name`: Nome da operação opcional para consultas com múltiplas operações
`**kwargs`: Parâmetros adicionais específicos do serviço

**Retorna:** dict: Resposta GraphQL com dados e/ou erros

**Exemplo:**

```python
async_flow = await api.async_flow()
flow = async_flow.id("default")

# Execute GraphQL query
query = '''
    query GetUsers($status: String!) {
        users(status: $status) {
            id
            name
            email
        }
    }
'''

result = await flow.rows_query(
    query=query,
    user="trustgraph",
    collection="users",
    variables={"status": "active"}
)

for user in result.get("data", {}).get("users", []):
    print(f"{user['name']}: {user['email']}")
```

### `text_completion(self, system: str, prompt: str, **kwargs: Any) -> str`

Gerar conclusão de texto (não em fluxo).

Gera uma resposta de texto a partir de um LLM, dado um prompt do sistema e um prompt do usuário.
Retorna o texto da resposta completo.

Nota: Este método não suporta streaming. Para geração de texto em fluxo,
use AsyncSocketFlowInstance.text_completion() em vez disso.

**Argumentos:**

`system`: Prompt do sistema que define o comportamento do LLM.
`prompt`: Prompt ou pergunta do usuário.
`**kwargs`: Parâmetros adicionais específicos do serviço.

**Retorna:** str: Resposta de texto gerada completa.

**Exemplo:**

```python
async_flow = await api.async_flow()
flow = async_flow.id("default")

# Generate text
response = await flow.text_completion(
    system="You are a helpful assistant.",
    prompt="Explain quantum computing in simple terms."
)
print(response)
```

### `triples_query(self, s=None, p=None, o=None, user=None, collection=None, limit=100, **kwargs: Any)`

Consulta triplas RDF usando correspondência de padrões.

Procura triplas que correspondam aos padrões especificados de sujeito, predicado e/ou
objeto. Os padrões usam "None" como um caractere curinga para corresponder a qualquer valor.

**Argumentos:**

`s`: Padrão do sujeito (None para caractere curinga)
`p`: Padrão do predicado (None para caractere curinga)
`o`: Padrão do objeto (None para caractere curinga)
`user`: Identificador do usuário (None para todos os usuários)
`collection`: Identificador da coleção (None para todas as coleções)
`limit`: Número máximo de triplas a retornar (padrão: 100)
`**kwargs`: Parâmetros adicionais específicos do serviço

**Retorna:** dict: Resposta contendo as triplas correspondentes

**Exemplo:**

```python
async_flow = await api.async_flow()
flow = async_flow.id("default")

# Find all triples with a specific predicate
results = await flow.triples_query(
    p="knows",
    user="trustgraph",
    collection="social",
    limit=50
)

for triple in results.get("triples", []):
    print(f"{triple['s']} knows {triple['o']}")
```


--

## `SocketClient`

```python
from trustgraph.api import SocketClient
```

Cliente WebSocket síncrono para operações de streaming.

Fornece uma interface síncrona para serviços TrustGraph baseados em WebSocket,
envolvendo a biblioteca de WebSockets assíncrona com geradores síncronos para facilitar o uso.
Suporta respostas de streaming de agentes, consultas RAG e preenchimentos de texto.

Nota: Este é um wrapper síncrono em torno de operações de WebSocket assíncronas. Para
suporte assíncrono real, use AsyncSocketClient em vez disso.

### Métodos

### `__init__(self, url: str, timeout: int, token: str | None) -> None`

Inicializa o cliente WebSocket síncrono.

**Argumentos:**

`url`: URL base para a API TrustGraph (HTTP/HTTPS serão convertidos para WS/WSS)
`timeout`: Tempo limite do WebSocket em segundos
`token`: Token de autorização opcional para autenticação

### `close(self) -> None`

Fecha as conexões WebSocket.

Nota: A limpeza é tratada automaticamente pelos gerenciadores de contexto em código assíncrono.

### `flow(self, flow_id: str) -> 'SocketFlowInstance'`

Obtém uma instância de fluxo para operações de streaming de WebSocket.

**Argumentos:**

`flow_id`: Identificador do fluxo

**Retorna:** SocketFlowInstance: Instância de fluxo com métodos de streaming

**Exemplo:**

```python
socket = api.socket()
flow = socket.flow("default")

# Stream agent responses
for chunk in flow.agent(question="Hello", user="trustgraph", streaming=True):
    print(chunk.content, end='', flush=True)
```


--

## `SocketFlowInstance`

```python
from trustgraph.api import SocketFlowInstance
```

Fluxo de WebSocket síncrono para operações de streaming.

Fornece a mesma interface que o FlowInstance REST, mas com suporte a streaming baseado em WebSocket
para respostas em tempo real. Todos os métodos suportam um parâmetro opcional
`streaming` para habilitar a entrega incremental de resultados.

### Métodos

### `__init__(self, client: trustgraph.api.socket_client.SocketClient, flow_id: str) -> None`

Inicializa a instância do fluxo de socket.

**Argumentos:**

`client`: SocketClient pai
`flow_id`: Identificador do fluxo

### `agent(self, question: str, user: str, state: Dict[str, Any] | None = None, group: str | None = None, history: List[Dict[str, Any]] | None = None, streaming: bool = False, **kwargs: Any) -> Dict[str, Any] | Iterator[trustgraph.api.types.StreamingChunk]`

Executa uma operação de agente com suporte a streaming.

Os agentes podem realizar raciocínios de várias etapas com o uso de ferramentas. Este método sempre
retorna fragmentos de streaming (pensamentos, observações, respostas), mesmo quando
streaming=False, para mostrar o processo de raciocínio do agente.

**Argumentos:**

`question`: Pergunta ou instrução do usuário
`user`: Identificador do usuário
`state`: Dicionário de estado opcional para conversas com estado
`group`: Identificador de grupo opcional para contextos multiusuário
`history`: Histórico de conversas opcional como uma lista de dicionários de mensagens
`streaming`: Habilita o modo de streaming (padrão: Falso)
`**kwargs`: Parâmetros adicionais passados para o serviço do agente

**Retorna:** Iterator[StreamingChunk]: Fluxo de pensamentos, observações e respostas do agente

**Exemplo:**

```python
socket = api.socket()
flow = socket.flow("default")

# Stream agent reasoning
for chunk in flow.agent(
    question="What is quantum computing?",
    user="trustgraph",
    streaming=True
):
    if isinstance(chunk, AgentThought):
        print(f"[Thinking] {chunk.content}")
    elif isinstance(chunk, AgentObservation):
        print(f"[Observation] {chunk.content}")
    elif isinstance(chunk, AgentAnswer):
        print(f"[Answer] {chunk.content}")
```

### `agent_explain(self, question: str, user: str, collection: str, state: Dict[str, Any] | None = None, group: str | None = None, history: List[Dict[str, Any]] | None = None, **kwargs: Any) -> Iterator[trustgraph.api.types.StreamingChunk | trustgraph.api.types.ProvenanceEvent]`

Execute uma operação de agente com suporte para explicabilidade.

Transmite tanto os fragmentos de conteúdo (AgentThought, AgentObservation, AgentAnswer)
quanto os eventos de rastreabilidade (ProvenanceEvent). Os eventos de rastreabilidade contêm URIs
que podem ser acessados usando o ExplainabilityClient para obter informações detalhadas
sobre o processo de raciocínio do agente.

O rastreamento do agente consiste em:
Sessão: A pergunta inicial e os metadados da sessão
Iterações: Cada ciclo de pensamento/ação/observação
Conclusão: A resposta final

**Argumentos:**

`question`: Pergunta ou instrução do usuário
`user`: Identificador do usuário
`collection`: Identificador de coleção para armazenamento de rastreabilidade
`state`: Dicionário de estado opcional para conversas com estado
`group`: Identificador de grupo opcional para contextos multiusuário
`history`: Histórico de conversas opcional como uma lista de dicionários de mensagens
`**kwargs`: Parâmetros adicionais passados para o serviço do agente
`Yields`: 
`Union[StreamingChunk, ProvenanceEvent]`: Fragmentos do agente e eventos de rastreabilidade

**Exemplo:**

```python
from trustgraph.api import Api, ExplainabilityClient, ProvenanceEvent
from trustgraph.api import AgentThought, AgentObservation, AgentAnswer

socket = api.socket()
flow = socket.flow("default")
explain_client = ExplainabilityClient(flow)

provenance_ids = []
for item in flow.agent_explain(
    question="What is the capital of France?",
    user="trustgraph",
    collection="default"
):
    if isinstance(item, AgentThought):
        print(f"[Thought] {item.content}")
    elif isinstance(item, AgentObservation):
        print(f"[Observation] {item.content}")
    elif isinstance(item, AgentAnswer):
        print(f"[Answer] {item.content}")
    elif isinstance(item, ProvenanceEvent):
        provenance_ids.append(item.explain_id)

# Fetch session trace after completion
if provenance_ids:
    trace = explain_client.fetch_agent_trace(
        provenance_ids[0],  # Session URI is first
        graph="urn:graph:retrieval",
        user="trustgraph",
        collection="default"
    )
```

### `document_embeddings_query(self, text: str, user: str, collection: str, limit: int = 10, **kwargs: Any) -> Dict[str, Any]`

Consultar trechos de documentos usando similaridade semântica.

**Argumentos:**

`text`: Texto da consulta para busca semântica
`user`: Identificador do usuário/espaço de chaves
`collection`: Identificador da coleção
`limit`: Número máximo de resultados (padrão: 10)
`**kwargs`: Parâmetros adicionais passados para o serviço

**Retorna:** dict: Resultados da consulta com os IDs dos trechos dos documentos correspondentes

**Exemplo:**

```python
socket = api.socket()
flow = socket.flow("default")

results = flow.document_embeddings_query(
    text="machine learning algorithms",
    user="trustgraph",
    collection="research-papers",
    limit=5
)
# results contains {"chunks": [{"chunk_id": "...", "score": 0.95}, ...]}
```

### `document_rag(self, query: str, user: str, collection: str, doc_limit: int = 10, streaming: bool = False, **kwargs: Any) -> str | Iterator[str]`

Execute uma consulta RAG baseada em documentos com streaming opcional.

Utiliza incorporações vetoriais para encontrar trechos de documentos relevantes e, em seguida, gera
uma resposta usando um LLM. O modo de streaming entrega resultados incrementalmente.

**Argumentos:**

`query`: Consulta em linguagem natural
`user`: Identificador de usuário/espaço de chaves
`collection`: Identificador de coleção
`doc_limit`: Número máximo de trechos de documentos a serem recuperados (padrão: 10)
`streaming`: Habilitar o modo de streaming (padrão: Falso)
`**kwargs`: Parâmetros adicionais passados para o serviço

**Retorna:** Union[str, Iterator[str]]: Resposta completa ou fluxo de trechos de texto

**Exemplo:**

```python
socket = api.socket()
flow = socket.flow("default")

# Streaming document RAG
for chunk in flow.document_rag(
    query="Summarize the key findings",
    user="trustgraph",
    collection="research-papers",
    doc_limit=5,
    streaming=True
):
    print(chunk, end='', flush=True)
```

### `document_rag_explain(self, query: str, user: str, collection: str, doc_limit: int = 10, **kwargs: Any) -> Iterator[trustgraph.api.types.RAGChunk | trustgraph.api.types.ProvenanceEvent]`

Execute uma consulta RAG baseada em documentos com suporte para explicabilidade.

Transmite tanto os fragmentos de conteúdo (RAGChunk) quanto os eventos de rastreabilidade (ProvenanceEvent).
Os eventos de rastreabilidade contêm URIs que podem ser recuperados usando o ExplainabilityClient
para obter informações detalhadas sobre como a resposta foi gerada.

O rastreamento RAG do documento consiste em:
Pergunta: A consulta do usuário
Exploração: Fragmentos recuperados do armazenamento de documentos (chunk_count)
Síntese: A resposta gerada

**Argumentos:**

`query`: Consulta em linguagem natural
`user`: Identificador do usuário/espaço de chaves
`collection`: Identificador da coleção
`doc_limit`: Número máximo de fragmentos de documento a serem recuperados (padrão: 10)
`**kwargs`: Parâmetros adicionais passados para o serviço
`Yields`: 
`Union[RAGChunk, ProvenanceEvent]`: Fragmentos de conteúdo e eventos de rastreabilidade

**Exemplo:**

```python
from trustgraph.api import Api, ExplainabilityClient, RAGChunk, ProvenanceEvent

socket = api.socket()
flow = socket.flow("default")
explain_client = ExplainabilityClient(flow)

for item in flow.document_rag_explain(
    query="Summarize the key findings",
    user="trustgraph",
    collection="research-papers",
    doc_limit=5
):
    if isinstance(item, RAGChunk):
        print(item.content, end='', flush=True)
    elif isinstance(item, ProvenanceEvent):
        # Fetch entity details
        entity = explain_client.fetch_entity(
            item.explain_id,
            graph=item.explain_graph,
            user="trustgraph",
            collection="research-papers"
        )
        print(f"Event: {entity}", file=sys.stderr)
```

### `embeddings(self, texts: list, **kwargs: Any) -> Dict[str, Any]`

Gerar incorporações vetoriais para um ou mais textos.

**Argumentos:**

`texts`: Lista de textos de entrada a serem incorporados
`**kwargs`: Parâmetros adicionais passados para o serviço

**Retorna:** dict: Resposta contendo vetores (um conjunto por texto de entrada)

**Exemplo:**

```python
socket = api.socket()
flow = socket.flow("default")

result = flow.embeddings(["quantum computing"])
vectors = result.get("vectors", [])
```

### `graph_embeddings_query(self, text: str, user: str, collection: str, limit: int = 10, **kwargs: Any) -> Dict[str, Any]`

Consultar entidades de grafo de conhecimento usando similaridade semântica.

**Argumentos:**

`text`: Texto da consulta para busca semântica
`user`: Identificador de usuário/espaço de chaves
`collection`: Identificador de coleção
`limit`: Número máximo de resultados (padrão: 10)
`**kwargs`: Parâmetros adicionais passados para o serviço

**Retorna:** dict: Resultados da consulta com entidades similares

**Exemplo:**

```python
socket = api.socket()
flow = socket.flow("default")

results = flow.graph_embeddings_query(
    text="physicist who discovered radioactivity",
    user="trustgraph",
    collection="scientists",
    limit=5
)
```

### `graph_rag(self, query: str, user: str, collection: str, max_subgraph_size: int = 1000, max_subgraph_count: int = 5, max_entity_distance: int = 3, streaming: bool = False, **kwargs: Any) -> str | Iterator[str]`

Execute consulta RAG baseada em grafo com streaming opcional.

Utiliza a estrutura do grafo de conhecimento para encontrar o contexto relevante e, em seguida, gera
uma resposta usando um LLM. O modo de streaming entrega os resultados incrementalmente.

**Argumentos:**

`query`: Consulta em linguagem natural
`user`: Identificador de usuário/espaço de chaves
`collection`: Identificador de coleção
`max_subgraph_size`: Número máximo total de triplas no subgrafo (padrão: 1000)
`max_subgraph_count`: Número máximo de subgrafos (padrão: 5)
`max_entity_distance`: Profundidade máxima de travessia (padrão: 3)
`streaming`: Habilitar o modo de streaming (padrão: Falso)
`**kwargs`: Parâmetros adicionais passados para o serviço

**Retorna:** Union[str, Iterator[str]]: Resposta completa ou fluxo de fragmentos de texto

**Exemplo:**

```python
socket = api.socket()
flow = socket.flow("default")

# Streaming graph RAG
for chunk in flow.graph_rag(
    query="Tell me about Marie Curie",
    user="trustgraph",
    collection="scientists",
    streaming=True
):
    print(chunk, end='', flush=True)
```

### `graph_rag_explain(self, query: str, user: str, collection: str, max_subgraph_size: int = 1000, max_subgraph_count: int = 5, max_entity_distance: int = 3, **kwargs: Any) -> Iterator[trustgraph.api.types.RAGChunk | trustgraph.api.types.ProvenanceEvent]`

Execute consulta RAG baseada em grafo com suporte para explicabilidade.

Transmite tanto os fragmentos de conteúdo (RAGChunk) quanto os eventos de rastreabilidade (ProvenanceEvent).
Os eventos de rastreabilidade contêm URIs que podem ser recuperados usando ExplainabilityClient
para obter informações detalhadas sobre como a resposta foi gerada.

**Argumentos:**

`query`: Consulta em linguagem natural
`user`: Identificador de usuário/espaço de chaves
`collection`: Identificador de coleção
`max_subgraph_size`: Número máximo total de triplas no subgrafo (padrão: 1000)
`max_subgraph_count`: Número máximo de subgrafos (padrão: 5)
`max_entity_distance`: Profundidade máxima de travessia (padrão: 3)
`**kwargs`: Parâmetros adicionais passados para o serviço
`Yields`: 
`Union[RAGChunk, ProvenanceEvent]`: Fragmentos de conteúdo e eventos de rastreabilidade

**Exemplo:**

```python
from trustgraph.api import Api, ExplainabilityClient, RAGChunk, ProvenanceEvent

socket = api.socket()
flow = socket.flow("default")
explain_client = ExplainabilityClient(flow)

provenance_ids = []
response_text = ""

for item in flow.graph_rag_explain(
    query="Tell me about Marie Curie",
    user="trustgraph",
    collection="scientists"
):
    if isinstance(item, RAGChunk):
        response_text += item.content
        print(item.content, end='', flush=True)
    elif isinstance(item, ProvenanceEvent):
        provenance_ids.append(item.provenance_id)

# Fetch explainability details
for prov_id in provenance_ids:
    entity = explain_client.fetch_entity(
        prov_id,
        graph="urn:graph:retrieval",
        user="trustgraph",
        collection="scientists"
    )
    print(f"Entity: {entity}")
```

### `mcp_tool(self, name: str, parameters: Dict[str, Any], **kwargs: Any) -> Dict[str, Any]`

Execute uma ferramenta de Protocolo de Contexto de Modelo (MCP).

**Argumentos:**

`name`: Nome/identificador da ferramenta
`parameters`: Dicionário de parâmetros da ferramenta
`**kwargs`: Parâmetros adicionais passados para o serviço

**Retorna:** dict: Resultado da execução da ferramenta

**Exemplo:**

```python
socket = api.socket()
flow = socket.flow("default")

result = flow.mcp_tool(
    name="search-web",
    parameters={"query": "latest AI news", "limit": 5}
)
```

### `prompt(self, id: str, variables: Dict[str, str], streaming: bool = False, **kwargs: Any) -> str | Iterator[str]`

Execute um modelo de prompt com streaming opcional.

**Argumentos:**

`id`: Identificador do modelo de prompt
`variables`: Dicionário de mapeamentos de nome de variável para valor
`streaming`: Habilitar o modo de streaming (padrão: Falso)
`**kwargs`: Parâmetros adicionais passados para o serviço

**Retorna:** Union[str, Iterator[str]]: Resposta completa ou fluxo de fragmentos de texto

**Exemplo:**

```python
socket = api.socket()
flow = socket.flow("default")

# Streaming prompt execution
for chunk in flow.prompt(
    id="summarize-template",
    variables={"topic": "quantum computing", "length": "brief"},
    streaming=True
):
    print(chunk, end='', flush=True)
```

### `row_embeddings_query(self, text: str, schema_name: str, user: str = 'trustgraph', collection: str = 'default', index_name: str | None = None, limit: int = 10, **kwargs: Any) -> Dict[str, Any]`

Consulta dados de linhas usando similaridade semântica em campos indexados.

Encontra linhas cujos valores de campos indexados são semanticamente similares ao
texto de entrada, usando embeddings vetoriais. Isso permite correspondência aproximada/semântica
em dados estruturados.

**Argumentos:**

`text`: Texto de consulta para busca semântica
`schema_name`: Nome do esquema para pesquisar
`user`: Identificador de usuário/espaço de chaves (padrão: "trustgraph")
`collection`: Identificador de coleção (padrão: "default")
`index_name`: Nome de índice opcional para filtrar a pesquisa para um índice específico
`limit`: Número máximo de resultados (padrão: 10)
`**kwargs`: Parâmetros adicionais passados para o serviço

**Retorna:** dict: Resultados da consulta com correspondências contendo index_name, index_value, text e score

**Exemplo:**

```python
socket = api.socket()
flow = socket.flow("default")

# Search for customers by name similarity
results = flow.row_embeddings_query(
    text="John Smith",
    schema_name="customers",
    user="trustgraph",
    collection="sales",
    limit=5
)

# Filter to specific index
results = flow.row_embeddings_query(
    text="machine learning engineer",
    schema_name="employees",
    index_name="job_title",
    limit=10
)
```

### `rows_query(self, query: str, user: str, collection: str, variables: Dict[str, Any] | None = None, operation_name: str | None = None, **kwargs: Any) -> Dict[str, Any]`

Execute uma consulta GraphQL contra linhas estruturadas.

**Argumentos:**

`query`: String de consulta GraphQL
`user`: Identificador de usuário/espaço de chaves
`collection`: Identificador de coleção
`variables`: Dicionário opcional de variáveis de consulta
`operation_name`: Nome de operação opcional para documentos de múltiplas operações
`**kwargs`: Parâmetros adicionais passados para o serviço

**Retorna:** dict: Resposta GraphQL com dados, erros e/ou extensões

**Exemplo:**

```python
socket = api.socket()
flow = socket.flow("default")

query = '''
{
  scientists(limit: 10) {
    name
    field
    discoveries
  }
}
'''
result = flow.rows_query(
    query=query,
    user="trustgraph",
    collection="scientists"
)
```

### `text_completion(self, system: str, prompt: str, streaming: bool = False, **kwargs) -> str | Iterator[str]`

Execute a conclusão de texto com streaming opcional.

**Argumentos:**

`system`: Prompt do sistema que define o comportamento do assistente.
`prompt`: Prompt/pergunta do usuário.
`streaming`: Habilita o modo de streaming (padrão: Falso).
`**kwargs`: Parâmetros adicionais passados para o serviço.

**Retorna:** Union[str, Iterator[str]]: Resposta completa ou fluxo de fragmentos de texto.

**Exemplo:**

```python
socket = api.socket()
flow = socket.flow("default")

# Non-streaming
response = flow.text_completion(
    system="You are helpful",
    prompt="Explain quantum computing",
    streaming=False
)
print(response)

# Streaming
for chunk in flow.text_completion(
    system="You are helpful",
    prompt="Explain quantum computing",
    streaming=True
):
    print(chunk, end='', flush=True)
```

### `triples_query(self, s: str | Dict[str, Any] | None = None, p: str | Dict[str, Any] | None = None, o: str | Dict[str, Any] | None = None, g: str | None = None, user: str | None = None, collection: str | None = None, limit: int = 100, **kwargs: Any) -> List[Dict[str, Any]]`

Consultar triplas de grafos de conhecimento usando correspondência de padrões.

**Argumentos:**

`s`: Filtro do sujeito - String URI, dicionário de termos ou None para curinga
`p`: Filtro do predicado - String URI, dicionário de termos ou None para curinga
`o`: Filtro do objeto - String URI/literal, dicionário de termos ou None para curinga
`g`: Filtro do grafo nomeado - String URI ou None para todos os grafos
`user`: Identificador de usuário/espaço de chaves (opcional)
`collection`: Identificador de coleção (opcional)
`limit`: Número máximo de resultados a retornar (padrão: 100)
`**kwargs`: Parâmetros adicionais passados para o serviço

**Retorna:** List[Dict]: Lista de triplas correspondentes no formato de fio

**Exemplo:**

```python
socket = api.socket()
flow = socket.flow("default")

# Find all triples about a specific subject
triples = flow.triples_query(
    s="http://example.org/person/marie-curie",
    user="trustgraph",
    collection="scientists"
)

# Query with named graph filter
triples = flow.triples_query(
    s="urn:trustgraph:session:abc123",
    g="urn:graph:retrieval",
    user="trustgraph",
    collection="default"
)
```

### `triples_query_stream(self, s: str | Dict[str, Any] | None = None, p: str | Dict[str, Any] | None = None, o: str | Dict[str, Any] | None = None, g: str | None = None, user: str | None = None, collection: str | None = None, limit: int = 100, batch_size: int = 20, **kwargs: Any) -> Iterator[List[Dict[str, Any]]]`

Consultar triplas de um grafo de conhecimento com lotes de streaming.

Produz lotes de triplas à medida que chegam, reduzindo o tempo para o primeiro resultado
e a sobrecarga de memória para conjuntos de resultados grandes.

**Argumentos:**

`s`: Filtro de sujeito - String URI, dicionário de termos ou None para curinga
`p`: Filtro de predicado - String URI, dicionário de termos ou None para curinga
`o`: Filtro de objeto - String URI/literal, dicionário de termos ou None para curinga
`g`: Filtro de grafo nomeado - String URI ou None para todos os grafos
`user`: Identificador de usuário/espaço de chaves (opcional)
`collection`: Identificador de coleção (opcional)
`limit`: Número máximo de resultados a retornar (padrão: 100)
`batch_size`: Triplas por lote (padrão: 20)
`**kwargs`: Parâmetros adicionais passados para o serviço
`Yields`: 
`List[Dict]`: Lotes de triplas em formato de fio

**Exemplo:**

```python
socket = api.socket()
flow = socket.flow("default")

for batch in flow.triples_query_stream(
    user="trustgraph",
    collection="default"
):
    for triple in batch:
        print(triple["s"], triple["p"], triple["o"])
```


--

## `AsyncSocketClient`

```python
from trustgraph.api import AsyncSocketClient
```

Cliente WebSocket assíncrono

### Métodos

### `__init__(self, url: str, timeout: int, token: str | None)`

Inicialize self. Consulte help(type(self)) para a assinatura correta.

### `aclose(self)`

Fechar conexão WebSocket

### `flow(self, flow_id: str)`

Obter instância de fluxo assíncrono para operações WebSocket


--

## `AsyncSocketFlowInstance`

```python
from trustgraph.api import AsyncSocketFlowInstance
```

Fluxo assíncrono de WebSocket.

### Métodos

### `__init__(self, client: trustgraph.api.async_socket_client.AsyncSocketClient, flow_id: str)`

Inicializa self. Consulte help(type(self)) para obter a assinatura correta.

### `agent(self, question: str, user: str, state: Dict[str, Any] | None = None, group: str | None = None, history: list | None = None, streaming: bool = False, **kwargs) -> Dict[str, Any] | AsyncIterator`

Agente com streaming opcional.

### `document_rag(self, query: str, user: str, collection: str, doc_limit: int = 10, streaming: bool = False, **kwargs)`

Documento RAG com streaming opcional.

### `embeddings(self, texts: list, **kwargs)`

Gera incorporações de texto.

### `graph_embeddings_query(self, text: str, user: str, collection: str, limit: int = 10, **kwargs)`

Consulta incorporações de grafo para pesquisa semântica.

### `graph_rag(self, query: str, user: str, collection: str, max_subgraph_size: int = 1000, max_subgraph_count: int = 5, max_entity_distance: int = 3, streaming: bool = False, **kwargs)`

RAG de grafo com streaming opcional.

### `mcp_tool(self, name: str, parameters: Dict[str, Any], **kwargs)`

Executa a ferramenta MCP.

### `prompt(self, id: str, variables: Dict[str, str], streaming: bool = False, **kwargs)`

Executa o prompt com streaming opcional.

### `row_embeddings_query(self, text: str, schema_name: str, user: str = 'trustgraph', collection: str = 'default', index_name: str | None = None, limit: int = 10, **kwargs)`

Consulta incorporações de linha para pesquisa semântica em dados estruturados.

### `rows_query(self, query: str, user: str, collection: str, variables: Dict | None = None, operation_name: str | None = None, **kwargs)`

Consulta GraphQL contra linhas estruturadas.

### `text_completion(self, system: str, prompt: str, streaming: bool = False, **kwargs)`

Conclusão de texto com streaming opcional.

### `triples_query(self, s=None, p=None, o=None, user=None, collection=None, limit=100, **kwargs)`

Consulta de padrão triplo.


--

### `build_term(value: Any, term_type: str | None = None, datatype: str | None = None, language: str | None = None) -> Dict[str, Any] | None`

Cria um dicionário Term no formato de fio a partir de um valor.

Regras de detecção automática (quando term_type é None):
  Já é um dicionário com a chave 't' -> retorna como está (já é um Term)
  Começa com http://, https://, urn: -> IRI
  Envolvido em <> (por exemplo, <http://...>) -> IRI (colchetes angulares removidos)
  Qualquer outra coisa -> literal

**Argumentos:**

`value`: O valor do termo (string, dicionário ou None)
`term_type`: Um dos valores 'iri', 'literal' ou None para detecção automática
`datatype`: Tipo de dados para objetos literais (por exemplo, xsd:integer)
`language`: Etiqueta de idioma para objetos literais (por exemplo, en)

**Retorna:** dict: Dicionário Term no formato de fio, ou None se o valor for None


--

## `BulkClient`

```python
from trustgraph.api import BulkClient
```

Cliente para operações em lote síncronas para importação/exportação.

Fornece transferência eficiente de dados em lote via WebSocket para grandes conjuntos de dados.
Envolve operações assíncronas do WebSocket com geradores síncronos para facilitar o uso.

Nota: Para suporte assíncrono real, use AsyncBulkClient em vez disso.

### Métodos

### `__init__(self, url: str, timeout: int, token: str | None) -> None`

Inicializa o cliente de lote síncrono.

**Argumentos:**

`url`: URL base para a API TrustGraph (HTTP/HTTPS serão convertidos para WS/WSS)
`timeout`: Tempo limite do WebSocket em segundos
`token`: Token de autorização opcional para autenticação

### `close(self) -> None`

Fecha as conexões

### `export_document_embeddings(self, flow: str, **kwargs: Any) -> Iterator[Dict[str, Any]]`

Exporta em lote os embeddings de documentos de um fluxo.

Baixa eficientemente todos os embeddings de fragmentos de documentos via streaming WebSocket.

**Argumentos:**

`flow`: Identificador do fluxo
`**kwargs`: Parâmetros adicionais (reservados para uso futuro)

**Retorna:** Iterator[Dict[str, Any]]: Fluxo de dicionários de embedding

**Exemplo:**

```python
bulk = api.bulk()

# Export and process document embeddings
for embedding in bulk.export_document_embeddings(flow="default"):
    chunk_id = embedding.get("chunk_id")
    vector = embedding.get("embedding")
    print(f"{chunk_id}: {len(vector)} dimensions")
```

### `export_entity_contexts(self, flow: str, **kwargs: Any) -> Iterator[Dict[str, Any]]`

Exportação em massa de contextos de entidades de um fluxo.

Faz o download de todas as informações do contexto da entidade de forma eficiente via streaming WebSocket.

**Argumentos:**

`flow`: Identificador do fluxo
`**kwargs`: Parâmetros adicionais (reservados para uso futuro)

**Retorna:** Iterator[Dict[str, Any]]: Fluxo de dicionários de contexto

**Exemplo:**

```python
bulk = api.bulk()

# Export and process entity contexts
for context in bulk.export_entity_contexts(flow="default"):
    entity = context.get("entity")
    text = context.get("context")
    print(f"{entity}: {text[:100]}...")
```

### `export_graph_embeddings(self, flow: str, **kwargs: Any) -> Iterator[Dict[str, Any]]`

Exportação em massa de representações gráficas (embeddings) de um fluxo.

Faz o download de todas as representações gráficas de entidades de forma eficiente via streaming WebSocket.

**Argumentos:**

`flow`: Identificador do fluxo
`**kwargs`: Parâmetros adicionais (reservados para uso futuro)

**Retorna:** Iterator[Dict[str, Any]]: Fluxo de dicionários de representações.

**Exemplo:**

```python
bulk = api.bulk()

# Export and process embeddings
for embedding in bulk.export_graph_embeddings(flow="default"):
    entity = embedding.get("entity")
    vector = embedding.get("embedding")
    print(f"{entity}: {len(vector)} dimensions")
```

### `export_triples(self, flow: str, **kwargs: Any) -> Iterator[trustgraph.api.types.Triple]`

Exportação em massa de triplas RDF de um fluxo.

Faz o download de todas as triplas de forma eficiente via streaming WebSocket.

**Argumentos:**

`flow`: Identificador do fluxo
`**kwargs`: Parâmetros adicionais (reservados para uso futuro)

**Retorna:** Iterator[Triple]: Fluxo de objetos Triple

**Exemplo:**

```python
bulk = api.bulk()

# Export and process triples
for triple in bulk.export_triples(flow="default"):
    print(f"{triple.s} -> {triple.p} -> {triple.o}")
```

### `import_document_embeddings(self, flow: str, embeddings: Iterator[Dict[str, Any]], **kwargs: Any) -> None`

Importação em massa de embeddings de documentos em um fluxo.

Carrega eficientemente embeddings de fragmentos de documentos via streaming WebSocket
para uso em consultas RAG de documentos.

**Argumentos:**

`flow`: Identificador do fluxo
`embeddings`: Iterador que retorna dicionários de embedding
`**kwargs`: Parâmetros adicionais (reservados para uso futuro)

**Exemplo:**

```python
bulk = api.bulk()

# Generate document embeddings to import
def doc_embedding_generator():
    yield {"chunk_id": "doc1/p0/c0", "embedding": [0.1, 0.2, ...]}
    yield {"chunk_id": "doc1/p0/c1", "embedding": [0.3, 0.4, ...]}
    # ... more embeddings

bulk.import_document_embeddings(
    flow="default",
    embeddings=doc_embedding_generator()
)
```

### `import_entity_contexts(self, flow: str, contexts: Iterator[Dict[str, Any]], metadata: Dict[str, Any] | None = None, batch_size: int = 100, **kwargs: Any) -> None`

Importação em massa de contextos de entidades em um fluxo.

Carrega eficientemente informações de contexto de entidade por meio de streaming WebSocket.
Os contextos de entidade fornecem contexto textual adicional sobre as entidades do grafo
para melhorar o desempenho do RAG.

**Argumentos:**

`flow`: Identificador do fluxo
`contexts`: Iterador que retorna dicionários de contexto
`metadata`: Dicionário de metadados com id, metadados, usuário, coleção
`batch_size`: Número de contextos por lote (padrão: 100)
`**kwargs`: Parâmetros adicionais (reservados para uso futuro)

**Exemplo:**

```python
bulk = api.bulk()

# Generate entity contexts to import
def context_generator():
    yield {"entity": {"v": "entity1", "e": True}, "context": "Description..."}
    yield {"entity": {"v": "entity2", "e": True}, "context": "Description..."}
    # ... more contexts

bulk.import_entity_contexts(
    flow="default",
    contexts=context_generator(),
    metadata={"id": "doc1", "metadata": [], "user": "user1", "collection": "default"}
)
```

### `import_graph_embeddings(self, flow: str, embeddings: Iterator[Dict[str, Any]], **kwargs: Any) -> None`

Importação em massa de representações gráficas em um fluxo.

Carrega de forma eficiente as representações de entidades gráficas via streaming WebSocket.

**Argumentos:**

`flow`: Identificador do fluxo
`embeddings`: Iterador que retorna dicionários de representações
`**kwargs`: Parâmetros adicionais (reservados para uso futuro)

**Exemplo:**

```python
bulk = api.bulk()

# Generate embeddings to import
def embedding_generator():
    yield {"entity": "entity1", "embedding": [0.1, 0.2, ...]}
    yield {"entity": "entity2", "embedding": [0.3, 0.4, ...]}
    # ... more embeddings

bulk.import_graph_embeddings(
    flow="default",
    embeddings=embedding_generator()
)
```

### `import_rows(self, flow: str, rows: Iterator[Dict[str, Any]], **kwargs: Any) -> None`

Importação em massa de linhas estruturadas em um fluxo.

Carrega eficientemente linhas de dados estruturados via streaming WebSocket
para uso em consultas GraphQL.

**Argumentos:**

`flow`: Identificador do fluxo
`rows`: Iterador que retorna dicionários de linhas
`**kwargs`: Parâmetros adicionais (reservados para uso futuro)

**Exemplo:**

```python
bulk = api.bulk()

# Generate rows to import
def row_generator():
    yield {"id": "row1", "name": "Row 1", "value": 100}
    yield {"id": "row2", "name": "Row 2", "value": 200}
    # ... more rows

bulk.import_rows(
    flow="default",
    rows=row_generator()
)
```

### `import_triples(self, flow: str, triples: Iterator[trustgraph.api.types.Triple], metadata: Dict[str, Any] | None = None, batch_size: int = 100, **kwargs: Any) -> None`

Importação em massa de triplas RDF em um fluxo.

Carrega eficientemente um grande número de triplas via streaming WebSocket.

**Argumentos:**

`flow`: Identificador do fluxo
`triples`: Iterador que retorna objetos Triple
`metadata`: Dicionário de metadados com id, metadados, usuário, coleção
`batch_size`: Número de triplas por lote (padrão 100)
`**kwargs`: Parâmetros adicionais (reservados para uso futuro)

**Exemplo:**

```python
from trustgraph.api import Triple

bulk = api.bulk()

# Generate triples to import
def triple_generator():
    yield Triple(s="subj1", p="pred", o="obj1")
    yield Triple(s="subj2", p="pred", o="obj2")
    # ... more triples

# Import triples
bulk.import_triples(
    flow="default",
    triples=triple_generator(),
    metadata={"id": "doc1", "metadata": [], "user": "user1", "collection": "default"}
)
```


--

## `AsyncBulkClient`

```python
from trustgraph.api import AsyncBulkClient
```

Cliente para operações em lote assíncronas.

### Métodos

### `__init__(self, url: str, timeout: int, token: str | None) -> None`

Inicialize self. Consulte help(type(self)) para obter a assinatura correta.

### `aclose(self) -> None`

Fechar conexões

### `export_document_embeddings(self, flow: str, **kwargs: Any) -> AsyncIterator[Dict[str, Any]]`

Exportação em lote de incorporações de documentos via WebSocket.

### `export_entity_contexts(self, flow: str, **kwargs: Any) -> AsyncIterator[Dict[str, Any]]`

Exportação em lote de contextos de entidades via WebSocket.

### `export_graph_embeddings(self, flow: str, **kwargs: Any) -> AsyncIterator[Dict[str, Any]]`

Exportação em lote de incorporações de grafos via WebSocket.

### `export_triples(self, flow: str, **kwargs: Any) -> AsyncIterator[trustgraph.api.types.Triple]`

Exportação em lote de triplas via WebSocket.

### `import_document_embeddings(self, flow: str, embeddings: AsyncIterator[Dict[str, Any]], **kwargs: Any) -> None`

Importação em lote de incorporações de documentos via WebSocket.

### `import_entity_contexts(self, flow: str, contexts: AsyncIterator[Dict[str, Any]], **kwargs: Any) -> None`

Importação em lote de contextos de entidades via WebSocket.

### `import_graph_embeddings(self, flow: str, embeddings: AsyncIterator[Dict[str, Any]], **kwargs: Any) -> None`

Importação em lote de incorporações de grafos via WebSocket.

### `import_rows(self, flow: str, rows: AsyncIterator[Dict[str, Any]], **kwargs: Any) -> None`

Importação em lote de linhas via WebSocket.

### `import_triples(self, flow: str, triples: AsyncIterator[trustgraph.api.types.Triple], **kwargs: Any) -> None`

Importação em lote de triplas via WebSocket.


--

## `Metrics`

```python
from trustgraph.api import Metrics
```

Cliente de métricas síncronas

### Métodos

### `__init__(self, url: str, timeout: int, token: str | None) -> None`

Inicialize self. Consulte help(type(self)) para obter a assinatura correta.

### `get(self) -> str`

Obtenha as métricas do Prometheus como texto


--

## `AsyncMetrics`

```python
from trustgraph.api import AsyncMetrics
```

Cliente de métricas assíncronas

### Métodos

### `__init__(self, url: str, timeout: int, token: str | None) -> None`

Inicialize self. Consulte help(type(self)) para obter a assinatura correta.

### `aclose(self) -> None`

Fechar conexões

### `get(self) -> str`

Obter métricas do Prometheus como texto


--

## `ExplainabilityClient`

```python
from trustgraph.api import ExplainabilityClient
```

Cliente para buscar entidades de explicabilidade com tratamento de consistência eventual.

Utiliza detecção de quiescência: buscar, esperar, buscar novamente, comparar.
Se os resultados forem os mesmos, os dados são estáveis.

### Métodos

### `__init__(self, flow_instance, retry_delay: float = 0.2, max_retries: int = 10)`

Inicializa o cliente de explicabilidade.

**Argumentos:**

`flow_instance`: Uma instância de SocketFlowInstance para consultar triplas.
`retry_delay`: Atraso entre as tentativas (padrão: 0,2).
`max_retries`: Número máximo de tentativas (padrão: 10).

### `detect_session_type(self, session_uri: str, graph: str | None = None, user: str | None = None, collection: str | None = None) -> str`

Detecta se uma sessão é do tipo GraphRAG ou Agent.

**Argumentos:**

`session_uri`: O URI da sessão/pergunta.
`graph`: Grafo nomeado.
`user`: Identificador de usuário/espaço de chaves.
`collection`: Identificador de coleção.

**Retorna:** "graphrag" ou "agent".

### `fetch_agent_trace(self, session_uri: str, graph: str | None = None, user: str | None = None, collection: str | None = None, api: Any = None, max_content: int = 10000) -> Dict[str, Any]`

Busca o rastreamento completo do Agent a partir de um URI de sessão.

Segue a cadeia de rastreabilidade: Pergunta -> Análise(s) -> Conclusão.

**Argumentos:**

`session_uri`: O URI da sessão/pergunta do agente.
`graph`: Grafo nomeado (padrão: urn:graph:retrieval).
`user`: Identificador de usuário/espaço de chaves.
`collection`: Identificador de coleção.
`api`: Instância da API TrustGraph para acesso ao bibliotecário (opcional).
`max_content`: Comprimento máximo do conteúdo para a conclusão.

**Retorna:** Dicionário com a pergunta, iterações (lista de Análises) e entidades de conclusão.

### `fetch_docrag_trace(self, question_uri: str, graph: str | None = None, user: str | None = None, collection: str | None = None, api: Any = None, max_content: int = 10000) -> Dict[str, Any]`

Busca o rastreamento completo do DocumentRAG a partir de um URI de pergunta.

Segue a cadeia de rastreabilidade:
    Pergunta -> Fundamentação -> Exploração -> Síntese.

**Argumentos:**

`question_uri`: O URI da entidade de pergunta.
`graph`: Grafo nomeado (padrão: urn:graph:retrieval).
`user`: Identificador de usuário/espaço de chaves.
`collection`: Identificador de coleção.
`api`: Instância da API TrustGraph para acesso ao bibliotecário (opcional).
`max_content`: Comprimento máximo do conteúdo para a síntese.

**Retorna:** Dicionário com a pergunta, fundamentação, exploração e entidades de síntese.

### `fetch_document_content(self, document_uri: str, api: Any, user: str | None = None, max_content: int = 10000) -> str`

Busca o conteúdo do bibliotecário por URI de documento.

**Argumentos:**

`document_uri`: O URI do documento no bibliotecário.
`api`: Instância da API TrustGraph para acesso ao bibliotecário.
`user`: Identificador de usuário para o bibliotecário.
`max_content`: Comprimento máximo do conteúdo a ser retornado.

**Retorna:** O conteúdo do documento como uma string.

### `fetch_edge_selection(self, uri: str, graph: str | None = None, user: str | None = None, collection: str | None = None) -> trustgraph.api.explainability.EdgeSelection | None`

Busca uma entidade de seleção de arestas (usada pelo Focus).

**Argumentos:**

`uri`: O URI da seleção de arestas.
`graph`: Grafo nomeado a ser consultado.
`user`: Identificador de usuário/espaço de chaves.
`collection`: Identificador de coleção.

**Retorna:** EdgeSelection ou None se não for encontrado.

### `fetch_entity(self, uri: str, graph: str | None = None, user: str | None = None, collection: str | None = None) -> trustgraph.api.explainability.ExplainEntity | None`

Buscar uma entidade de explicabilidade por URI com tratamento de consistência eventual.

Usa detecção de quiescência:
1. Buscar triplas para o URI
2. Se não houver resultados, tentar novamente
3. Se houver resultados, esperar e buscar novamente
4. Se os resultados forem os mesmos, os dados são estáveis - analisar e retornar
5. Se os resultados forem diferentes, os dados ainda estão sendo gravados - tentar novamente

**Argumentos:**

`uri`: O URI da entidade a ser buscada
`graph`: Grafo nomeado a ser consultado (por exemplo, "urn:graph:retrieval")
`user`: Identificador de usuário/espaço de chaves
`collection`: Identificador de coleção

**Retorna:** Subclasse ExplainEntity ou None se não for encontrada

### `fetch_focus_with_edges(self, uri: str, graph: str | None = None, user: str | None = None, collection: str | None = None) -> trustgraph.api.explainability.Focus | None`

Buscar uma entidade Focus e todas as suas seleções de arestas.

**Argumentos:**

`uri`: O URI da entidade Focus
`graph`: Grafo nomeado a ser consultado
`user`: Identificador de usuário/espaço de chaves
`collection`: Identificador de coleção

**Retorna:** Focus com edge_selections preenchidos, ou None

### `fetch_graphrag_trace(self, question_uri: str, graph: str | None = None, user: str | None = None, collection: str | None = None, api: Any = None, max_content: int = 10000) -> Dict[str, Any]`

Buscar o rastreamento completo do GraphRAG a partir de um URI de pergunta.

Segue a cadeia de rastreabilidade: Pergunta -> Grounding -> Exploração -> Focus -> Síntese

**Argumentos:**

`question_uri`: O URI da entidade de pergunta
`graph`: Grafo nomeado (padrão: urn:graph:retrieval)
`user`: Identificador de usuário/espaço de chaves
`collection`: Identificador de coleção
`api`: Instância da API TrustGraph para acesso de bibliotecário (opcional)
`max_content`: Comprimento máximo do conteúdo para síntese

**Retorna:** Dicionário com as entidades de pergunta, grounding, exploração, focus e síntese

### `list_sessions(self, graph: str | None = None, user: str | None = None, collection: str | None = None, limit: int = 50) -> List[trustgraph.api.explainability.Question]`

Listar todas as sessões de explicabilidade (perguntas) em uma coleção.

**Argumentos:**

`graph`: Grafo nomeado (padrão: urn:graph:retrieval)
`user`: Identificador de usuário/espaço de chaves
`collection`: Identificador de coleção
`limit`: Número máximo de sessões a serem retornadas

**Retorna:** Lista de entidades de Pergunta ordenadas por timestamp (mais recentes primeiro)

### `resolve_edge_labels(self, edge: Dict[str, str], user: str | None = None, collection: str | None = None) -> Tuple[str, str, str]`

Resolver rótulos para todos os componentes de uma tripla de aresta.

**Argumentos:**

`edge`: Dicionário com chaves "s", "p" e "o"
`user`: Identificador de usuário/espaço de chaves
`collection`: Identificador de coleção

**Retorna:** Tupla de (s_label, p_label, o_label)

### `resolve_label(self, uri: str, user: str | None = None, collection: str | None = None) -> str`

Resolver rdfs:label para um URI, com cache.

**Argumentos:**

`uri`: O URI para o qual obter o rótulo
`user`: Identificador de usuário/espaço de chaves
`collection`: Identificador de coleção

**Retorna:** O rótulo se encontrado, caso contrário, o próprio URI


--

## `ExplainEntity`

```python
from trustgraph.api import ExplainEntity
```

Classe base para entidades de explicabilidade.

**Campos:**

`uri`: <class 'str'>
`entity_type`: <class 'str'>

### Métodos

### `__init__(self, uri: str, entity_type: str = '') -> None`

Inicialize self. Consulte help(type(self)) para a assinatura correta.


--

## `Question`

```python
from trustgraph.api import Question
```

Entidade de pergunta - a consulta do usuário que iniciou a sessão.

**Campos:**

`uri`: <class 'str'>
`entity_type`: <class 'str'>
`query`: <class 'str'>
`timestamp`: <class 'str'>
`question_type`: <class 'str'>

### Métodos

### `__init__(self, uri: str, entity_type: str = '', query: str = '', timestamp: str = '', question_type: str = '') -> None`

Inicialize self. Consulte help(type(self)) para obter a assinatura correta.


--

## `Exploration`

```python
from trustgraph.api import Exploration
```

Entidade de exploração - arestas/pedaços recuperados do repositório de conhecimento.

**Campos:**

`uri`: <class 'str'>
`entity_type`: <class 'str'>
`edge_count`: <class 'int'>
`chunk_count`: <class 'int'>
`entities`: typing.List[str]

### Métodos

### `__init__(self, uri: str, entity_type: str = '', edge_count: int = 0, chunk_count: int = 0, entities: List[str] = <factory>) -> None`

Inicialize self. Consulte help(type(self)) para obter a assinatura correta.


--

## `Focus`

```python
from trustgraph.api import Focus
```

Entidade de foco - arestas selecionadas com raciocínio LLM (apenas GraphRAG).

**Campos:**

`uri`: <class 'str'>
`entity_type`: <class 'str'>
`selected_edge_uris`: typing.List[str]
`edge_selections`: typing.List[trustgraph.api.explainability.EdgeSelection]

### Métodos

### `__init__(self, uri: str, entity_type: str = '', selected_edge_uris: List[str] = <factory>, edge_selections: List[trustgraph.api.explainability.EdgeSelection] = <factory>) -> None`

Inicialize self. Consulte help(type(self)) para obter a assinatura correta.


--

## `Synthesis`

```python
from trustgraph.api import Synthesis
```

Entidade de síntese - a resposta final.

**Campos:**

`uri`: <class 'str'>
`entity_type`: <class 'str'>
`document`: <class 'str'>

### Métodos

### `__init__(self, uri: str, entity_type: str = '', document: str = '') -> None`

Inicialize self. Consulte help(type(self)) para a assinatura correta.


--

## `Analysis`

```python
from trustgraph.api import Analysis
```

Entidade de análise - um ciclo de pensar/agir/observar (apenas para o Agente).

**Campos:**

`uri`: <class 'str'>
`entity_type`: <class 'str'>
`action`: <class 'str'>
`arguments`: <class 'str'>
`thought`: <class 'str'>
`observation`: <class 'str'>

### Métodos

### `__init__(self, uri: str, entity_type: str = '', action: str = '', arguments: str = '', thought: str = '', observation: str = '') -> None`

Inicialize self. Consulte help(type(self)) para obter a assinatura correta.


--

## `Conclusion`

```python
from trustgraph.api import Conclusion
```

Conclusão da entidade - resposta final (Agente apenas).

**Campos:**

`uri`: <class 'str'>
`entity_type`: <class 'str'>
`document`: <class 'str'>

### Métodos

### `__init__(self, uri: str, entity_type: str = '', document: str = '') -> None`

Inicialize self. Consulte help(type(self)) para obter a assinatura correta.


--

## `EdgeSelection`

```python
from trustgraph.api import EdgeSelection
```

Uma aresta selecionada com raciocínio da etapa GraphRAG Focus.

**Campos:**

`uri`: <class 'str'>
`edge`: typing.Dict[str, str] | None
`reasoning`: <class 'str'>

### Métodos

### `__init__(self, uri: str, edge: Dict[str, str] | None = None, reasoning: str = '') -> None`

Inicialize self. Consulte help(type(self)) para obter a assinatura correta.


--

### `wire_triples_to_tuples(wire_triples: List[Dict[str, Any]]) -> List[Tuple[str, str, Any]]`

Converta triplas no formato de fio em tuplas (s, p, o).


--

### `extract_term_value(term: Dict[str, Any]) -> Any`

Extraia o valor de um dicionário Term no formato de fio.


--

## `Triple`

```python
from trustgraph.api import Triple
```

Tripla RDF que representa uma declaração de um grafo de conhecimento.

**Campos:**

`s`: <class 'str'>
`p`: <class 'str'>
`o`: <class 'str'>

### Métodos

### `__init__(self, s: str, p: str, o: str) -> None`

Inicializa self. Consulte help(type(self)) para obter a assinatura correta.


--

## `Uri`

```python
from trustgraph.api import Uri
```

str(object='') -> str
str(bytes_or_buffer[, encoding[, errors]]) -> str

Crie um novo objeto string a partir do objeto fornecido. Se encoding ou
errors forem especificados, então o objeto deve expor um buffer de dados
que será decodificado usando a codificação e o manipulador de erros fornecidos.
Caso contrário, retorna o resultado de object.__str__() (se definido)
ou repr(object).
encoding tem como padrão 'utf-8'.
errors tem como padrão 'strict'.

### Métodos

### `is_literal(self)`

### `is_triple(self)`

### `is_uri(self)`


--

## `Literal`

```python
from trustgraph.api import Literal
```

str(object='') -> str
str(bytes_or_buffer[, encoding[, errors]]) -> str

Crie um novo objeto string a partir do objeto fornecido. Se encoding ou
errors forem especificados, então o objeto deve expor um buffer de dados
que será decodificado usando a codificação e o manipulador de erros fornecidos.
Caso contrário, retorna o resultado de object.__str__() (se definido)
ou repr(object).
encoding tem como padrão 'utf-8'.
errors tem como padrão 'strict'.

### Métodos

### `is_literal(self)`

### `is_triple(self)`

### `is_uri(self)`


--

## `ConfigKey`

```python
from trustgraph.api import ConfigKey
```

Identificador da chave de configuração.

**Campos:**

`type`: <class 'str'>
`key`: <class 'str'>

### Métodos

### `__init__(self, type: str, key: str) -> None`

Inicialize self. Consulte help(type(self)) para obter a assinatura correta.


--

## `ConfigValue`

```python
from trustgraph.api import ConfigValue
```

Par de chave-valor de configuração.

**Campos:**

`type`: <class 'str'>
`key`: <class 'str'>
`value`: <class 'str'>

### Métodos

### `__init__(self, type: str, key: str, value: str) -> None`

Inicialize self. Consulte help(type(self)) para obter a assinatura correta.


--

## `DocumentMetadata`

```python
from trustgraph.api import DocumentMetadata
```

Metadados para um documento na biblioteca.

**Atributos:**

`parent_id: Parent document ID for child documents (empty for top`: level docs)

**Campos:**

`id`: <class 'str'>
`time`: <class 'datetime.datetime'>
`kind`: <class 'str'>
`title`: <class 'str'>
`comments`: <class 'str'>
`metadata`: typing.List[trustgraph.api.types.Triple]
`user`: <class 'str'>
`tags`: typing.List[str]
`parent_id`: <class 'str'>
`document_type`: <class 'str'>

### Métodos

### `__init__(self, id: str, time: datetime.datetime, kind: str, title: str, comments: str, metadata: List[trustgraph.api.types.Triple], user: str, tags: List[str], parent_id: str = '', document_type: str = 'source') -> None`

Inicialize self. Consulte help(type(self)) para obter a assinatura correta.


--

## `ProcessingMetadata`

```python
from trustgraph.api import ProcessingMetadata
```

Metadados para um processo de documento ativo.

**Campos:**

`id`: <class 'str'>
`document_id`: <class 'str'>
`time`: <class 'datetime.datetime'>
`flow`: <class 'str'>
`user`: <class 'str'>
`collection`: <class 'str'>
`tags`: typing.List[str]

### Métodos

### `__init__(self, id: str, document_id: str, time: datetime.datetime, flow: str, user: str, collection: str, tags: List[str]) -> None`

Inicialize self. Consulte help(type(self)) para obter a assinatura correta.


--

## `CollectionMetadata`

```python
from trustgraph.api import CollectionMetadata
```

Metadados para uma coleção de dados.

As coleções fornecem agrupamento lógico e isolamento para documentos e
dados de grafo de conhecimento.

**Atributos:**

`name: Human`: nome da coleção legível

**Campos:**

`user`: <class 'str'>
`collection`: <class 'str'>
`name`: <class 'str'>
`description`: <class 'str'>
`tags`: typing.List[str]

### Métodos

### `__init__(self, user: str, collection: str, name: str, description: str, tags: List[str]) -> None`

Inicialize self. Consulte help(type(self)) para obter a assinatura correta.


--

## `StreamingChunk`

```python
from trustgraph.api import StreamingChunk
```

Classe base para fragmentos de resposta de streaming.

Usado para operações de streaming baseadas em WebSocket, onde as respostas são entregues
incrementalmente à medida que são geradas.

**Campos:**

`content`: <class 'str'>
`end_of_message`: <class 'bool'>

### Métodos

### `__init__(self, content: str, end_of_message: bool = False) -> None`

Inicializa self. Consulte help(type(self)) para obter a assinatura correta.


--

## `AgentThought`

```python
from trustgraph.api import AgentThought
```

Trecho de raciocínio/processo de pensamento do agente.

Representa o raciocínio interno ou as etapas de planejamento do agente durante a execução.
Esses trechos mostram como o agente está pensando sobre o problema.

**Campos:**

`content`: <class 'str'>
`end_of_message`: <class 'bool'>
`chunk_type`: <class 'str'>

### Métodos

### `__init__(self, content: str, end_of_message: bool = False, chunk_type: str = 'thought') -> None`

Inicialize self. Consulte help(type(self)) para obter a assinatura correta.


--

## `AgentObservation`

```python
from trustgraph.api import AgentObservation
```

Trecho de observação da execução da ferramenta do agente.

Representa o resultado ou a observação da execução de uma ferramenta ou ação.
Esses trechos mostram o que o agente aprendeu ao usar ferramentas.

**Campos:**

`content`: <class 'str'>
`end_of_message`: <class 'bool'>
`chunk_type`: <class 'str'>

### Métodos

### `__init__(self, content: str, end_of_message: bool = False, chunk_type: str = 'observation') -> None`

Inicialize self. Consulte help(type(self)) para obter a assinatura correta.


--

## `AgentAnswer`

```python
from trustgraph.api import AgentAnswer
```

Trecho da resposta final do agente.

Representa a resposta final do agente ao pedido do usuário após concluir
seu raciocínio e uso de ferramentas.

**Atributos:**

`chunk_type: Always "final`: answer"

**Campos:**

`content`: <class 'str'>
`end_of_message`: <class 'bool'>
`chunk_type`: <class 'str'>
`end_of_dialog`: <class 'bool'>

### Métodos

### `__init__(self, content: str, end_of_message: bool = False, chunk_type: str = 'final-answer', end_of_dialog: bool = False) -> None`

Inicialize self. Consulte help(type(self)) para obter a assinatura correta.


--

## `RAGChunk`

```python
from trustgraph.api import RAGChunk
```

RAG (Geração Aumentada por Recuperação) em blocos de fluxo.

Usado para transmitir respostas de RAG de grafos, RAG de documentos, preenchimento de texto,
e outros serviços generativos.

**Campos:**

`content`: <class 'str'>
`end_of_message`: <class 'bool'>
`chunk_type`: <class 'str'>
`end_of_stream`: <class 'bool'>
`error`: typing.Dict[str, str] | None

### Métodos

### `__init__(self, content: str, end_of_message: bool = False, chunk_type: str = 'rag', end_of_stream: bool = False, error: Dict[str, str] | None = None) -> None`

Inicializa self. Consulte help(type(self)) para obter a assinatura correta.


--

## `ProvenanceEvent`

```python
from trustgraph.api import ProvenanceEvent
```

Evento de rastreabilidade para explicabilidade.

Emitido durante as consultas GraphRAG quando o modo de explicabilidade está habilitado.
Cada evento representa um nó de rastreabilidade criado durante o processamento da consulta.

**Campos:**

`explain_id`: <class 'str'>
`explain_graph`: <class 'str'>
`event_type`: <class 'str'>

### Métodos

### `__init__(self, explain_id: str, explain_graph: str = '', event_type: str = '') -> None`

Inicialize self. Consulte help(type(self)) para obter a assinatura correta.


--

## `ProtocolException`

```python
from trustgraph.api import ProtocolException
```

Disparado quando ocorrem erros no protocolo WebSocket.


--

## `TrustGraphException`

```python
from trustgraph.api import TrustGraphException
```

Classe base para todos os erros do serviço TrustGraph.


--

## `AgentError`

```python
from trustgraph.api import AgentError
```

Erro no serviço do agente


--

## `ConfigError`

```python
from trustgraph.api import ConfigError
```

Erro no serviço de configuração.


--

## `DocumentRagError`

```python
from trustgraph.api import DocumentRagError
```

Erro de recuperação de documentos RAG.


--

## `FlowError`

```python
from trustgraph.api import FlowError
```

Erro de gerenciamento de fluxo


--

## `GatewayError`

```python
from trustgraph.api import GatewayError
```

Erro no API Gateway


--

## `GraphRagError`

```python
from trustgraph.api import GraphRagError
```

Erro de recuperação do Graph RAG.


--

## `LLMError`

```python
from trustgraph.api import LLMError
```

Erro no serviço de LLM.


--

## `LoadError`

```python
from trustgraph.api import LoadError
```

Erro ao carregar dados


--

## `LookupError`

```python
from trustgraph.api import LookupError
```

Erro de pesquisa/busca


--

## `NLPQueryError`

```python
from trustgraph.api import NLPQueryError
```

Erro no serviço de consulta de processamento de linguagem natural.


--

## `RowsQueryError`

```python
from trustgraph.api import RowsQueryError
```

Erro no serviço de consulta de linhas.


--

## `RequestError`

```python
from trustgraph.api import RequestError
```

Erro no processamento da requisição.


--

## `StructuredQueryError`

```python
from trustgraph.api import StructuredQueryError
```

Erro no serviço de consulta estruturada.


--

## `UnexpectedError`

```python
from trustgraph.api import UnexpectedError
```

Erro inesperado/desconhecido


--

## `ApplicationException`

```python
from trustgraph.api import ApplicationException
```

Classe base para todos os erros do serviço TrustGraph.


--

