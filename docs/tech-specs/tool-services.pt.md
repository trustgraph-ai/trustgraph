# Serviços de Ferramentas: Ferramentas de Agente Dinamicamente Plugáveis

## Status

Implementado

## Visão Geral

Esta especificação define um mecanismo para ferramentas de agente dinamicamente plugáveis, chamadas "serviços de ferramentas". Ao contrário dos tipos de ferramentas integradas existentes (`KnowledgeQueryImpl`, `McpToolImpl`, etc.), os serviços de ferramentas permitem que novas ferramentas sejam introduzidas por:

1. Implantando um novo serviço baseado em Pulsar
2. Adicionando um descritor de configuração que informa ao agente como invocá-lo

Isso permite a extensibilidade sem modificar o framework de resposta do agente principal.

## Terminologia

| Termo | Definição |
|------|------------|
| **Ferramenta Integrada** | Tipos de ferramentas existentes com implementações codificadas em `tools.py` |
| **Serviço de Ferramenta** | Um serviço Pulsar que pode ser invocado como uma ferramenta de agente, definido por um descritor de serviço |
| **Ferramenta** | Uma instância configurada que referencia um serviço de ferramenta, exposta ao agente/LLM |

Este é um modelo de duas camadas, análogo às ferramentas MCP:
MCP: O servidor MCP define a interface da ferramenta → A configuração da ferramenta a referencia
Serviços de Ferramenta: O serviço de ferramenta define a interface Pulsar → A configuração da ferramenta a referencia

## Contexto: Ferramentas Existentes

### Implementação de Ferramenta Integrada

As ferramentas são atualmente definidas em `trustgraph-flow/trustgraph/agent/react/tools.py` com implementações tipadas:

```python
class KnowledgeQueryImpl:
    async def invoke(self, question):
        client = self.context("graph-rag-request")
        return await client.rag(question, self.collection)
```

Cada tipo de ferramenta:
Possui um serviço Pulsar pré-definido que ele chama (por exemplo, `graph-rag-request`)
Conhece o método exato a ser chamado no cliente (por exemplo, `client.rag()`)
Possui argumentos tipados definidos na implementação

### Registro de Ferramentas (service.py:105-214)

As ferramentas são carregadas da configuração com um campo `type` que mapeia para uma implementação:

```python
if impl_id == "knowledge-query":
    impl = functools.partial(KnowledgeQueryImpl, collection=data.get("collection"))
elif impl_id == "text-completion":
    impl = TextCompletionImpl
# ... etc
```

## Arquitetura

### Modelo de Duas Camadas

#### Camada 1: Descritor do Serviço de Ferramenta

Um serviço de ferramenta define uma interface de serviço Pulsar. Ele declara:
As filas Pulsar para solicitação/resposta
Os parâmetros de configuração que ele requer das ferramentas que o utilizam

```json
{
  "id": "custom-rag",
  "request-queue": "non-persistent://tg/request/custom-rag",
  "response-queue": "non-persistent://tg/response/custom-rag",
  "config-params": [
    {"name": "collection", "required": true}
  ]
}
```

Um serviço de ferramenta que não requer parâmetros de configuração:

```json
{
  "id": "calculator",
  "request-queue": "non-persistent://tg/request/calc",
  "response-queue": "non-persistent://tg/response/calc",
  "config-params": []
}
```

#### Nível 2: Descritor de Ferramenta

Uma ferramenta referencia um serviço de ferramenta e fornece:
Valores de parâmetros de configuração (que satisfazem os requisitos do serviço)
Metadados da ferramenta para o agente (nome, descrição)
Definições de argumentos para o LLM

```json
{
  "type": "tool-service",
  "name": "query-customers",
  "description": "Query the customer knowledge base",
  "service": "custom-rag",
  "collection": "customers",
  "arguments": [
    {
      "name": "question",
      "type": "string",
      "description": "The question to ask about customers"
    }
  ]
}
```

Múltiplas ferramentas podem referenciar o mesmo serviço com diferentes configurações:

```json
{
  "type": "tool-service",
  "name": "query-products",
  "description": "Query the product knowledge base",
  "service": "custom-rag",
  "collection": "products",
  "arguments": [
    {
      "name": "question",
      "type": "string",
      "description": "The question to ask about products"
    }
  ]
}
```

### Formato da Requisição

Quando uma ferramenta é invocada, a requisição ao serviço da ferramenta inclui:
`user`: Do pedido do agente (multi-tenência)
`config`: Valores de configuração codificados em JSON, provenientes da descrição da ferramenta
`arguments`: Argumentos codificados em JSON, provenientes do LLM

```json
{
  "user": "alice",
  "config": "{\"collection\": \"customers\"}",
  "arguments": "{\"question\": \"What are the top customer complaints?\"}"
}
```

O serviço de ferramenta recebe estes como dicionários analisados no método `invoke`.

### Implementação Genérica do Serviço de Ferramenta

Uma classe `ToolServiceImpl` invoca serviços de ferramenta com base na configuração:

```python
class ToolServiceImpl:
    def __init__(self, context, request_queue, response_queue, config_values, arguments, processor):
        self.request_queue = request_queue
        self.response_queue = response_queue
        self.config_values = config_values  # e.g., {"collection": "customers"}
        # ...

    async def invoke(self, **arguments):
        client = await self._get_or_create_client()
        response = await client.call(user, self.config_values, arguments)
        if isinstance(response, str):
            return response
        else:
            return json.dumps(response)
```

## Decisões de Design

### Modelo de Configuração de Duas Camadas

Os serviços de ferramentas seguem um modelo de duas camadas semelhante às ferramentas MCP:

1. **Serviço de Ferramenta**: Define a interface do serviço Pulsar (tópico, parâmetros de configuração necessários)
2. **Ferramenta**: Referencia um serviço de ferramenta, fornece valores de configuração, define argumentos do LLM

Essa separação permite:
Que um único serviço de ferramenta seja usado por várias ferramentas com diferentes configurações
Uma distinção clara entre a interface do serviço e a configuração da ferramenta
A reutilização das definições de serviço

### Mapeamento de Solicitações: Transmissão com Envelope

A solicitação a um serviço de ferramenta é um envelope estruturado contendo:
`user`: Propagado do pedido do agente para multi-inquilinato
Valores de configuração: Do descritor da ferramenta (por exemplo, `collection`)
`arguments`: Argumentos fornecidos pelo LLM, transmitidos como um dicionário

O gerenciador de agente analisa a resposta do LLM em `act.arguments` como um dicionário (`agent_manager.py:117-154`). Este dicionário é incluído no envelope da solicitação.

### Tratamento de Esquemas: Não Tipados

As solicitações e respostas usam dicionários não tipados. Não há validação de esquema no nível do agente - o serviço de ferramenta é responsável por validar suas entradas. Isso fornece o máximo de flexibilidade para definir novos serviços.

### Interface do Cliente: Tópicos Pulsar Diretos

Os serviços de ferramentas usam tópicos Pulsar diretos, sem a necessidade de configuração de fluxo. O descritor do serviço de ferramenta especifica os nomes completos das filas:

```json
{
  "id": "joke-service",
  "request-queue": "non-persistent://tg/request/joke",
  "response-queue": "non-persistent://tg/response/joke",
  "config-params": [...]
}
```

Isso permite que os serviços sejam hospedados em qualquer namespace.

### Tratamento de Erros: Convenção de Erro Padrão

As respostas do serviço de ferramenta seguem a convenção de esquema existente com um campo `error`:

```python
@dataclass
class Error:
    type: str = ""
    message: str = ""
```

Estrutura da resposta:
Sucesso: `error` é `None`, a resposta contém o resultado
Erro: `error` é preenchido com `type` e `message`

Isso corresponde ao padrão usado em todo o serviço existente (por exemplo, `PromptResponse`, `QueryResponse`, `AgentResponse`).

### Correlação de Requisições/Respostas

As requisições e respostas são correlacionadas usando um `id` nas propriedades da mensagem Pulsar:

A requisição inclui `id` nas propriedades: `properties={"id": id}`
A(s) resposta(s) incluem o mesmo `id`: `properties={"id": id}`

Isso segue o padrão existente usado em todo o código-fonte (por exemplo, `agent_service.py`, `llm_service.py`).

### Suporte a Streaming

Os serviços de ferramenta podem retornar respostas em streaming:

Múltiplas mensagens de resposta com o mesmo `id` nas propriedades
Cada resposta inclui o campo `end_of_stream: bool`
A resposta final tem `end_of_stream: True`

Isso corresponde ao padrão usado em `AgentResponse` e outros serviços de streaming.

### Tratamento da Resposta: Retorno de String

Todas as ferramentas existentes seguem o mesmo padrão: **receber argumentos como um dicionário, retornar a observação como uma string**.

| Ferramenta | Tratamento da Resposta |
|------|------------------|
| `KnowledgeQueryImpl` | Retorna `client.rag()` diretamente (string) |
| `TextCompletionImpl` | Retorna `client.question()` diretamente (string) |
| `McpToolImpl` | Retorna uma string, ou `json.dumps(output)` se não for uma string |
| `StructuredQueryImpl` | Formata o resultado para uma string |
| `PromptImpl` | Retorna `client.prompt()` diretamente (string) |

Os serviços de ferramenta seguem o mesmo contrato:
O serviço retorna uma resposta em string (a observação)
Se a resposta não for uma string, ela é convertida via `json.dumps()`
Nenhuma configuração de extração é necessária no descritor

Isso mantém o descritor simples e coloca a responsabilidade de retornar uma resposta de texto apropriada para o agente no serviço.

## Guia de Configuração

Para adicionar um novo serviço de ferramenta, são necessários dois itens de configuração:

### 1. Configuração do Serviço de Ferramenta

Armazenado sob a chave de configuração `tool-service`. Define as filas Pulsar e os parâmetros de configuração disponíveis.

| Campo | Obrigatório | Descrição |
|-------|----------|-------------|
| `id` | Sim | Identificador único para o serviço de ferramenta |
| `request-queue` | Sim | Tópico Pulsar completo para requisições (por exemplo, `non-persistent://tg/request/joke`) |
| `response-queue` | Sim | Tópico Pulsar completo para respostas (por exemplo, `non-persistent://tg/response/joke`) |
| `config-params` | Não | Array de parâmetros de configuração que o serviço aceita |

Cada parâmetro de configuração pode especificar:
`name`: Nome do parâmetro (obrigatório)
`required`: Se o parâmetro deve ser fornecido pelas ferramentas (padrão: falso)

Exemplo:
```json
{
  "id": "joke-service",
  "request-queue": "non-persistent://tg/request/joke",
  "response-queue": "non-persistent://tg/response/joke",
  "config-params": [
    {"name": "style", "required": false}
  ]
}
```

### 2. Configuração da Ferramenta

Armazenado sob a chave de configuração `tool`. Define uma ferramenta que o agente pode usar.

| Campo | Obrigatório | Descrição |
|-------|----------|-------------|
| `type` | Sim | Deve ser `"tool-service"` |
| `name` | Sim | Nome da ferramenta exposto para o LLM |
| `description` | Sim | Descrição do que a ferramenta faz (mostrada para o LLM) |
| `service` | Sim | ID do serviço de ferramenta a ser invocado |
| `arguments` | Não | Array de definições de argumentos para o LLM |
| *(parâmetros de configuração)* | Varia | Quaisquer parâmetros de configuração definidos pelo serviço |

Cada argumento pode especificar:
`name`: Nome do argumento (obrigatório)
`type`: Tipo de dados, por exemplo, `"string"` (obrigatório)
`description`: Descrição mostrada para o LLM (obrigatório)

Exemplo:
```json
{
  "type": "tool-service",
  "name": "tell-joke",
  "description": "Tell a joke on a given topic",
  "service": "joke-service",
  "style": "pun",
  "arguments": [
    {
      "name": "topic",
      "type": "string",
      "description": "The topic for the joke (e.g., programming, animals, food)"
    }
  ]
}
```

### Carregando a Configuração

Use `tg-put-config-item` para carregar as configurações:

```bash
# Load tool-service config
tg-put-config-item tool-service/joke-service < joke-service.json

# Load tool config
tg-put-config-item tool/tell-joke < tell-joke.json
```

O agente-gerenciador deve ser reiniciado para aplicar novas configurações.

## Detalhes da Implementação

### Esquema

Tipos de requisição e resposta em `trustgraph-base/trustgraph/schema/services/tool_service.py`:

```python
@dataclass
class ToolServiceRequest:
    user: str = ""           # User context for multi-tenancy
    config: str = ""         # JSON-encoded config values from tool descriptor
    arguments: str = ""      # JSON-encoded arguments from LLM

@dataclass
class ToolServiceResponse:
    error: Error | None = None
    response: str = ""       # String response (the observation)
    end_of_stream: bool = False
```

### Servidor: DynamicToolService

Classe base em `trustgraph-base/trustgraph/base/dynamic_tool_service.py`:

```python
class DynamicToolService(AsyncProcessor):
    """Base class for implementing tool services."""

    def __init__(self, **params):
        topic = params.get("topic", default_topic)
        # Constructs topics: non-persistent://tg/request/{topic}, non-persistent://tg/response/{topic}
        # Sets up Consumer and Producer

    async def invoke(self, user, config, arguments):
        """Override this method to implement the tool's logic."""
        raise NotImplementedError()
```

### Cliente: ToolServiceImpl

Implementação em `trustgraph-flow/trustgraph/agent/react/tools.py`:

```python
class ToolServiceImpl:
    def __init__(self, context, request_queue, response_queue, config_values, arguments, processor):
        # Uses the provided queue paths directly
        # Creates ToolServiceClient on first use

    async def invoke(self, **arguments):
        client = await self._get_or_create_client()
        response = await client.call(user, config_values, arguments)
        return response if isinstance(response, str) else json.dumps(response)
```

### Arquivos

| Arquivo | Propósito |
|------|---------|
| `trustgraph-base/trustgraph/schema/services/tool_service.py` | Esquemas de requisição/resposta |
| `trustgraph-base/trustgraph/base/tool_service_client.py` | Cliente para invocar serviços |
| `trustgraph-base/trustgraph/base/dynamic_tool_service.py` | Classe base para implementação de serviço |
| `trustgraph-flow/trustgraph/agent/react/tools.py` | Classe `ToolServiceImpl` |
| `trustgraph-flow/trustgraph/agent/react/service.py` | Carregamento de configuração |

### Exemplo: Serviço de Piadas

Um exemplo de serviço em `trustgraph-flow/trustgraph/tool_service/joke/`:

```python
class Processor(DynamicToolService):
    async def invoke(self, user, config, arguments):
        style = config.get("style", "pun")
        topic = arguments.get("topic", "")
        joke = pick_joke(topic, style)
        return f"Hey {user}! Here's a {style} for you:\n\n{joke}"
```

Configuração do serviço de ferramenta:
```json
{
  "id": "joke-service",
  "request-queue": "non-persistent://tg/request/joke",
  "response-queue": "non-persistent://tg/response/joke",
  "config-params": [{"name": "style", "required": false}]
}
```

Configuração da ferramenta:
```json
{
  "type": "tool-service",
  "name": "tell-joke",
  "description": "Tell a joke on a given topic",
  "service": "joke-service",
  "style": "pun",
  "arguments": [
    {"name": "topic", "type": "string", "description": "The topic for the joke"}
  ]
}
```

### Compatibilidade com versões anteriores

Os tipos de ferramentas integradas existentes continuam a funcionar sem alterações.
`tool-service` é um novo tipo de ferramenta, juntamente com os tipos existentes (`knowledge-query`, `mcp-tool`, etc.).

## Considerações futuras

### Serviços de autoanúncio

Uma melhoria futura poderia permitir que os serviços publicassem seus próprios descritores:

Os serviços publicam em um tópico `tool-descriptors` conhecido na inicialização.
O agente se inscreve e registra dinamicamente as ferramentas.
Permite um verdadeiro sistema de plug-and-play sem alterações de configuração.

Isso está fora do escopo da implementação inicial.

## Referências

Implementação atual da ferramenta: `trustgraph-flow/trustgraph/agent/react/tools.py`
Registro de ferramentas: `trustgraph-flow/trustgraph/agent/react/service.py:105-214`
Esquemas do agente: `trustgraph-base/trustgraph/schema/services/agent.py`
