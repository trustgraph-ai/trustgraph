# Especificação Técnica de Respostas de LLM em Streaming

## Visão Geral

Esta especificação descreve a implementação do suporte a streaming para respostas de LLM
no TrustGraph. O streaming permite a entrega em tempo real de tokens gerados
à medida que são produzidos pelo LLM, em vez de esperar pela geração completa
da resposta.

Esta implementação suporta os seguintes casos de uso:

1. **Interfaces de Usuário em Tempo Real**: Transmita tokens para a interface do usuário à medida que são gerados,
   fornecendo feedback visual imediato.
2. **Tempo de Primeiro Token Reduzido**: Os usuários veem a saída começando imediatamente
   em vez de esperar pela geração completa.
3. **Tratamento de Respostas Longas**: Lidar com saídas muito longas que, de outra forma,
   poderiam causar timeout ou exceder os limites de memória.
4. **Aplicações Interativas**: Permitir interfaces de bate-papo e agentes responsivas.

## Objetivos

**Compatibilidade com Versões Anteriores**: Os clientes existentes que não utilizam streaming continuam a funcionar
  sem modificação.
**Design de API Consistente**: O streaming e o uso sem streaming utilizam os mesmos padrões de esquema
  com mínima divergência.
**Flexibilidade do Provedor**: Suporte ao streaming quando disponível, com uma alternativa
  suave quando não disponível.
**Implementação Gradual**: Implementação incremental para reduzir o risco.
**Suporte de Ponta a Ponta**: Streaming do provedor de LLM até as aplicações do cliente
  via Pulsar, Gateway API e Python API.

## Contexto

### Arquitetura Atual

O fluxo atual de conclusão de texto de LLM opera da seguinte forma:

1. O cliente envia `TextCompletionRequest` com os campos `system` e `prompt`.
2. O serviço de LLM processa a solicitação e espera pela geração completa.
3. Um único `TextCompletionResponse` é retornado com a string `response` completa.

Esquema atual (`trustgraph-base/trustgraph/schema/services/llm.py`):

```python
class TextCompletionRequest(Record):
    system = String()
    prompt = String()

class TextCompletionResponse(Record):
    error = Error()
    response = String()
    in_token = Integer()
    out_token = Integer()
    model = String()
```

### Limitações Atuais

**Latência**: Os usuários devem esperar pela geração completa antes de ver qualquer resultado.
**Risco de Timeout**: Gerações longas podem exceder os limites de tempo de espera do cliente.
**Má Experiência do Usuário**: A falta de feedback durante a geração cria a percepção de lentidão.
**Uso de Recursos**: As respostas completas devem ser armazenadas em memória.

Esta especificação aborda essas limitações, permitindo a entrega incremental de respostas, mantendo total compatibilidade com versões anteriores.


## Design Técnico

### Fase 1: Infraestrutura

A Fase 1 estabelece a base para o streaming, modificando esquemas, APIs e ferramentas de linha de comando.


#### Alterações no Esquema

##### Esquema LLM (`trustgraph-base/trustgraph/schema/services/llm.py`)

**Alterações na Requisição:**

```python
class TextCompletionRequest(Record):
    system = String()
    prompt = String()
    streaming = Boolean()  # NEW: Default false for backward compatibility
```

`streaming`: Quando `true`, solicita a entrega de resposta em fluxo.
Padrão: `false` (o comportamento existente é preservado).

**Alterações na Resposta:**

```python
class TextCompletionResponse(Record):
    error = Error()
    response = String()
    in_token = Integer()
    out_token = Integer()
    model = String()
    end_of_stream = Boolean()  # NEW: Indicates final message
```

`end_of_stream`: Quando `true`, indica que esta é a resposta final (ou única).
Para solicitações não em fluxo contínuo: Resposta única com `end_of_stream=true`.
Para solicitações em fluxo contínuo: Múltiplas respostas, todas com `end_of_stream=false`
  exceto a última.

##### Esquema do Prompt (`trustgraph-base/trustgraph/schema/services/prompt.py`)

O serviço de prompt envolve a conclusão de texto, portanto, ele segue o mesmo padrão:

**Alterações na Solicitação:**

```python
class PromptRequest(Record):
    id = String()
    terms = Map(String())
    streaming = Boolean()  # NEW: Default false
```

**Alterações na Resposta:**

```python
class PromptResponse(Record):
    error = Error()
    text = String()
    object = String()
    end_of_stream = Boolean()  # NEW: Indicates final message
```

#### Alterações na API Gateway

A API Gateway deve expor capacidades de streaming para clientes HTTP/WebSocket.

**Atualizações da API REST:**

`POST /api/v1/text-completion`: Aceitar o parâmetro `streaming` no corpo da requisição
O comportamento da resposta depende da flag de streaming:
  `streaming=false`: Resposta JSON única (comportamento atual)
  `streaming=true`: Fluxo de eventos enviados pelo servidor (SSE) ou mensagens WebSocket

**Formato da Resposta (Streaming):**

Cada bloco transmitido segue a mesma estrutura de esquema:
```json
{
  "response": "partial text...",
  "end_of_stream": false,
  "model": "model-name"
}
```

Trecho final:
```json
{
  "response": "final text chunk",
  "end_of_stream": true,
  "in_token": 150,
  "out_token": 500,
  "model": "model-name"
}
```

#### Alterações na API Python

A API do cliente Python deve suportar tanto o modo de streaming quanto o modo não-streaming,
mantendo a compatibilidade com versões anteriores.

**Atualizações do LlmClient** (`trustgraph-base/trustgraph/clients/llm_client.py`):

```python
class LlmClient(BaseClient):
    def request(self, system, prompt, timeout=300, streaming=False):
        """
        Non-streaming request (backward compatible).
        Returns complete response string.
        """
        # Existing behavior when streaming=False

    async def request_stream(self, system, prompt, timeout=300):
        """
        Streaming request.
        Yields response chunks as they arrive.
        """
        # New async generator method
```

**Atualizações do PromptClient** (`trustgraph-base/trustgraph/base/prompt_client.py`):

Padrão semelhante com o parâmetro `streaming` e a variante de gerador assíncrono.

#### Alterações na Ferramenta de Linha de Comando (CLI)

**tg-invoke-llm** (`trustgraph-cli/trustgraph/cli/invoke_llm.py`):

```
tg-invoke-llm [system] [prompt] [--no-streaming] [-u URL] [-f flow-id]
```

Streaming habilitado por padrão para uma melhor experiência de usuário interativa.
A flag `--no-streaming` desabilita o streaming.
Quando o streaming está habilitado: Envie os tokens para a saída padrão (stdout) à medida que chegam.
Quando o streaming não está habilitado: Aguarde a resposta completa e, em seguida, envie.

**tg-invoke-prompt** (`trustgraph-cli/trustgraph/cli/invoke_prompt.py`):

```
tg-invoke-prompt [template-id] [var=value...] [--no-streaming] [-u URL] [-f flow-id]
```

Mesmo padrão que `tg-invoke-llm`.

#### Alterações na Classe Base do Serviço LLM

**LlmService** (`trustgraph-base/trustgraph/base/llm_service.py`):

```python
class LlmService(FlowProcessor):
    async def on_request(self, msg, consumer, flow):
        request = msg.value()
        streaming = getattr(request, 'streaming', False)

        if streaming and self.supports_streaming():
            async for chunk in self.generate_content_stream(...):
                await self.send_response(chunk, end_of_stream=False)
            await self.send_response(final_chunk, end_of_stream=True)
        else:
            response = await self.generate_content(...)
            await self.send_response(response, end_of_stream=True)

    def supports_streaming(self):
        """Override in subclass to indicate streaming support."""
        return False

    async def generate_content_stream(self, system, prompt, model, temperature):
        """Override in subclass to implement streaming."""
        raise NotImplementedError()
```

--

### Fase 2: Prova de Conceito do VertexAI

A Fase 2 implementa o streaming em um único provedor (VertexAI) para validar a
infraestrutura e permitir testes de ponta a ponta.

#### Implementação do VertexAI

**Módulo:** `trustgraph-vertexai/trustgraph/model/text_completion/vertexai/llm.py`

**Alterações:**

1. Substituir `supports_streaming()` para retornar `True`
2. Implementar gerador assíncrono `generate_content_stream()`
3. Lidar com modelos Gemini e Claude (via API Anthropic do VertexAI)

**Streaming do Gemini:**

```python
async def generate_content_stream(self, system, prompt, model, temperature):
    model_instance = self.get_model(model, temperature)
    response = model_instance.generate_content(
        [system, prompt],
        stream=True  # Enable streaming
    )
    for chunk in response:
        yield LlmChunk(
            text=chunk.text,
            in_token=None,  # Available only in final chunk
            out_token=None,
        )
    # Final chunk includes token counts from response.usage_metadata
```

**Claude (via VertexAI Anthropic) Streaming:**

```python
async def generate_content_stream(self, system, prompt, model, temperature):
    with self.anthropic_client.messages.stream(...) as stream:
        for text in stream.text_stream:
            yield LlmChunk(text=text)
    # Token counts from stream.get_final_message()
```

#### Testes

Testes unitários para a montagem da resposta em streaming
Testes de integração com o VertexAI (Gemini e Claude)
Testes de ponta a ponta: CLI -> Gateway -> Pulsar -> VertexAI -> de volta
Testes de compatibilidade com versões anteriores: as solicitações não em streaming ainda funcionam

--

### Fase 3: Todos os Provedores de LLM

A Fase 3 estende o suporte a streaming para todos os provedores de LLM no sistema.

#### Status de Implementação do Provedor

Cada provedor deve:
1. **Suporte Completo a Streaming**: Implementar `generate_content_stream()`
2. **Modo de Compatibilidade**: Lidar com a flag `end_of_stream` corretamente
   (retornar uma única resposta com `end_of_stream=true`)

| Provedor | Pacote | Suporte a Streaming |
|----------|---------|-------------------|
| OpenAI | trustgraph-flow | Completo (API de streaming nativa) |
| Claude/Anthropic | trustgraph-flow | Completo (API de streaming nativa) |
| Ollama | trustgraph-flow | Completo (API de streaming nativa) |
| Cohere | trustgraph-flow | Completo (API de streaming nativa) |
| Mistral | trustgraph-flow | Completo (API de streaming nativa) |
| Azure OpenAI | trustgraph-flow | Completo (API de streaming nativa) |
| Google AI Studio | trustgraph-flow | Completo (API de streaming nativa) |
| VertexAI | trustgraph-vertexai | Completo (Fase 2) |
| Bedrock | trustgraph-bedrock | Completo (API de streaming nativa) |
| LM Studio | trustgraph-flow | Completo (compatível com OpenAI) |
| LlamaFile | trustgraph-flow | Completo (compatível com OpenAI) |
| vLLM | trustgraph-flow | Completo (compatível com OpenAI) |
| TGI | trustgraph-flow | A ser definido |
| Azure | trustgraph-flow | A ser definido |

#### Padrão de Implementação

Para provedores compatíveis com OpenAI (OpenAI, LM Studio, LlamaFile, vLLM):

```python
async def generate_content_stream(self, system, prompt, model, temperature):
    response = await self.client.chat.completions.create(
        model=model,
        messages=[
            {"role": "system", "content": system},
            {"role": "user", "content": prompt}
        ],
        temperature=temperature,
        stream=True
    )
    async for chunk in response:
        if chunk.choices[0].delta.content:
            yield LlmChunk(text=chunk.choices[0].delta.content)
```

--

### Fase 4: API do Agente

A Fase 4 estende o streaming para a API do Agente. Isso é mais complexo porque a
API do Agente já é inerentemente multi-mensagem (pensamento → ação → observação
→ repetir → resposta final).

#### Esquema Atual do Agente

```python
class AgentStep(Record):
    thought = String()
    action = String()
    arguments = Map(String())
    observation = String()
    user = String()

class AgentRequest(Record):
    question = String()
    state = String()
    group = Array(String())
    history = Array(AgentStep())
    user = String()

class AgentResponse(Record):
    answer = String()
    error = Error()
    thought = String()
    observation = String()
```

#### Alterações Propostas no Esquema do Agente

**Solicitar Alterações:**

```python
class AgentRequest(Record):
    question = String()
    state = String()
    group = Array(String())
    history = Array(AgentStep())
    user = String()
    streaming = Boolean()  # NEW: Default false
```

**Alterações na Resposta:**

O agente produz múltiplos tipos de saída durante seu ciclo de raciocínio:
Pensamentos (raciocínio)
Ações (chamadas de ferramentas)
Observações (resultados das ferramentas)
Resposta (resposta final)
Erros

Como `chunk_type` identifica o tipo de conteúdo que está sendo enviado, os campos separados
`answer`, `error`, `thought` e `observation` podem ser combinados em
um único campo `content`:

```python
class AgentResponse(Record):
    chunk_type = String()       # "thought", "action", "observation", "answer", "error"
    content = String()          # The actual content (interpretation depends on chunk_type)
    end_of_message = Boolean()  # Current thought/action/observation/answer is complete
    end_of_dialog = Boolean()   # Entire agent dialog is complete
```

**Semântica dos Campos:**

`chunk_type`: Indica o tipo de conteúdo presente no campo `content`
  `"thought"`: Raciocínio/pensamento do agente
  `"action"`: Ferramenta/ação sendo invocada
  `"observation"`: Resultado da execução da ferramenta
  `"answer"`: Resposta final à pergunta do usuário
  `"error"`: Mensagem de erro

`content`: O conteúdo transmitido, interpretado com base em `chunk_type`

`end_of_message`: Quando `true`, o tipo de bloco atual está completo
  Exemplo: Todos os tokens para o pensamento atual foram enviados
  Permite que os clientes saibam quando avançar para a próxima etapa

`end_of_dialog`: Quando `true`, toda a interação do agente está completa
  Esta é a mensagem final no fluxo

#### Comportamento de Streaming do Agente

Quando `streaming=true`:

1. **Streaming de pensamento:**
   Múltiplos blocos com `chunk_type="thought"`, `end_of_message=false`
   O bloco final do pensamento tem `end_of_message=true`
2. **Notificação de ação:**
   Um único bloco com `chunk_type="action"`, `end_of_message=true`
3. **Observação:**
   Bloco(s) com `chunk_type="observation"`, o final tem `end_of_message=true`
4. **Repita** as etapas 1-3 enquanto o agente raciocina
5. **Resposta final:**
   `chunk_type="answer"` com a resposta final em `content`
   O último bloco tem `end_of_message=true`, `end_of_dialog=true`

**Exemplo de Sequência de Streaming:**

```
{chunk_type: "thought", content: "I need to", end_of_message: false, end_of_dialog: false}
{chunk_type: "thought", content: " search for...", end_of_message: true, end_of_dialog: false}
{chunk_type: "action", content: "search", end_of_message: true, end_of_dialog: false}
{chunk_type: "observation", content: "Found: ...", end_of_message: true, end_of_dialog: false}
{chunk_type: "thought", content: "Based on this", end_of_message: false, end_of_dialog: false}
{chunk_type: "thought", content: " I can answer...", end_of_message: true, end_of_dialog: false}
{chunk_type: "answer", content: "The answer is...", end_of_message: true, end_of_dialog: true}
```

Quando `streaming=false`:
Comportamento atual preservado
Resposta única com resposta completa
`end_of_message=true`, `end_of_dialog=true`

#### Gateway e API Python

Gateway: Novo endpoint SSE/WebSocket para streaming de agentes
API Python: Novo método gerador assíncrono `agent_stream()`

--

## Considerações de Segurança

**Nenhuma nova superfície de ataque**: O streaming usa a mesma autenticação/autorização
**Limitação de taxa**: Aplique limites de taxa por token ou por bloco, se necessário
**Gerenciamento de conexão**: Termine corretamente os streams em caso de desconexão do cliente
**Gerenciamento de tempo limite**: As solicitações de streaming precisam de um tratamento de tempo limite adequado

## Considerações de Desempenho

**Memória**: O streaming reduz o uso máximo de memória (sem bufferização completa da resposta)
**Latência**: O tempo para o primeiro token é significativamente reduzido
**Sobrecarga de conexão**: As conexões SSE/WebSocket têm uma sobrecarga de keep-alive
**Throughput do Pulsar**: Múltiplas mensagens pequenas vs. uma única mensagem grande
  tradeoff

## Estratégia de Testes

### Testes Unitários
Serialização/desserialização de esquema com novos campos
Compatibilidade com versões anteriores (campos ausentes usam valores padrão)
Lógica de montagem de blocos

### Testes de Integração
Implementação de streaming de cada provedor de LLM
Pontos finais de streaming da API Gateway
Métodos de streaming do cliente Python

### Testes de Ponta a Ponta
Saída de streaming da ferramenta CLI
Fluxo completo: Cliente → Gateway → Pulsar → LLM → de volta
Cargas de trabalho mistas de streaming/não streaming

### Testes de Compatibilidade com Versões Anteriores
Clientes existentes funcionam sem modificação
As solicitações não de streaming se comportam de forma idêntica

## Plano de Migração

### Fase 1: Infraestrutura
Implante as alterações de esquema (compatível com versões anteriores)
Implante as atualizações da API Gateway
Implante as atualizações da API Python
Lance as atualizações da ferramenta CLI

### Fase 2: VertexAI
Implementar a implementação de streaming do VertexAI
Validar com cargas de trabalho de teste

### Fase 3: Todos os Provedores
Implementar as atualizações do provedor de forma incremental
Monitorar para identificar problemas

### Fase 4: API do Agente
Implementar as alterações do esquema do agente
Implementar a implementação de streaming do agente
Atualizar a documentação

## Cronograma

| Fase | Descrição | Dependências |
|-------|-------------|--------------|
| Fase 1 | Infraestrutura | Nenhum |
| Fase 2 | Prova de Conceito do VertexAI | Fase 1 |
| Fase 3 | Todos os Provedores | Fase 2 |
| Fase 4 | API do Agente | Fase 3 |

## Decisões de Design

As seguintes perguntas foram resolvidas durante a especificação:

1. **Contagem de Tokens no Streaming**: As contagens de tokens são diferenças, não totais cumulativos.
   Os consumidores podem somá-las, se necessário. Isso corresponde à forma como a maioria dos provedores relata
   o uso e simplifica a implementação.

2. **Tratamento de Erros em Streams**: Se ocorrer um erro, o campo `error` é
   preenchido e nenhum outro campo é necessário. Um erro é sempre a comunicação final - nenhuma mensagem subsequente é permitida ou esperada após
   isso.
   um erro. Para fluxos de LLM/Prompt, `end_of_stream=true`. Para fluxos de Agente,
   `chunk_type="error"` com `end_of_dialog=true`.

3. **Recuperação Parcial de Respostas**: O protocolo de mensagens (Pulsar) é resiliente,
   portanto, a repetição em nível de mensagem não é necessária. Se um cliente perder o controle do fluxo
   ou desconectar, ele deve repetir a solicitação completa do zero.

4. **Streaming de Respostas Rápidas**: O streaming é suportado apenas para respostas de texto (`text`).
   As respostas estruturadas (`object`) não são suportadas. O serviço de respostas rápidas sabe,
   desde o início, se a saída será JSON ou texto, com base no modelo da solicitação. Se
   uma solicitação de streaming for feita para uma solicitação de saída JSON, o
   serviço deve:
   Retornar o JSON completo em uma única resposta com `end_of_stream=true`, ou
   Rejeitar a solicitação de streaming com um erro.

## Perguntas Abertas

Nenhum neste momento.

## Referências

Esquema atual do LLM: `trustgraph-base/trustgraph/schema/services/llm.py`
Esquema atual do prompt: `trustgraph-base/trustgraph/schema/services/prompt.py`
Esquema atual do agente: `trustgraph-base/trustgraph/schema/services/agent.py`
Serviço base do LLM: `trustgraph-base/trustgraph/base/llm_service.py`
Provedor VertexAI: `trustgraph-vertexai/trustgraph/model/text_completion/vertexai/llm.py`
API de gateway: `trustgraph-base/trustgraph/api/`
Ferramentas de linha de comando: `trustgraph-cli/trustgraph/cli/`
