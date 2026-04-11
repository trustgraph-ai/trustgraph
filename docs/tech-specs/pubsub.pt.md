# Infraestrutura Pub/Sub

## Visão Geral

Este documento cataloga todas as conexões entre o código-fonte do TrustGraph e a infraestrutura pub/sub. Atualmente, o sistema está codificado para usar o Apache Pulsar. Esta análise identifica todos os pontos de integração para informar futuras refatorações em direção a uma abstração pub/sub configurável.

## Estado Atual: Pontos de Integração do Pulsar

### 1. Uso Direto do Cliente Pulsar

**Localização:** `trustgraph-flow/trustgraph/gateway/service.py`

O gateway da API importa e instancia diretamente o cliente Pulsar:

**Linha 20:** `import pulsar`
**Linhas 54-61:** Instanciação direta de `pulsar.Client()` com `pulsar.AuthenticationToken()` opcional
**Linhas 33-35:** Configuração padrão do host Pulsar a partir de variáveis de ambiente
**Linhas 178-192:** Argumentos da linha de comando para `--pulsar-host`, `--pulsar-api-key` e `--pulsar-listener`
**Linhas 78, 124:** Passa `pulsar_client` para `ConfigReceiver` e `DispatcherManager`

Esta é a única localização que instancia diretamente um cliente Pulsar fora da camada de abstração.

### 2. Framework Base do Processador

**Localização:** `trustgraph-base/trustgraph/base/async_processor.py`

A classe base para todos os processadores fornece conectividade Pulsar:

**Linha 9:** `import _pulsar` (para tratamento de exceções)
**Linha 18:** `from . pubsub import PulsarClient`
**Linha 38:** Cria `pulsar_client_object = PulsarClient(**params)`
**Linhas 104-108:** Propriedades que expõem `pulsar_host` e `pulsar_client`
**Linha 250:** O método estático `add_args()` chama `PulsarClient.add_args(parser)` para argumentos da linha de comando
**Linhas 223-225:** Tratamento de exceções para `_pulsar.Interrupted`

Todos os processadores herdam de `AsyncProcessor`, tornando este o ponto de integração central.

### 3. Abstração do Consumidor

**Localização:** `trustgraph-base/trustgraph/base/consumer.py`

Consome mensagens de filas e invoca funções de tratamento:

**Importações do Pulsar:**
**Linha 12:** `from pulsar.schema import JsonSchema`
**Linha 13:** `import pulsar`
**Linha 14:** `import _pulsar`

**Uso específico do Pulsar:**
**Linhas 100, 102:** `pulsar.InitialPosition.Earliest` / `pulsar.InitialPosition.Latest`
**Linha 108:** Wrapper `JsonSchema(self.schema)`
**Linha 110:** `pulsar.ConsumerType.Shared`
**Linhas 104-111:** `self.client.subscribe()` com parâmetros específicos do Pulsar
**Linhas 143, 150, 65:** Métodos `consumer.unsubscribe()` e `consumer.close()`
**Linha 162:** Exceção `_pulsar.Timeout`
**Linhas 182, 205, 232:** `consumer.acknowledge()` / `consumer.negative_acknowledge()`

**Arquivo de especificação:** `trustgraph-base/trustgraph/base/consumer_spec.py`
**Linha 22:** Referencia `processor.pulsar_client`

### 4. Abstração do Produtor

**Localização:** `trustgraph-base/trustgraph/base/producer.py`

Envia mensagens para filas:

**Importações do Pulsar:**
**Linha 2:** `from pulsar.schema import JsonSchema`

**Uso específico do Pulsar:**
**Linha 49:** Wrapper `JsonSchema(self.schema)`
**Linhas 47-51:** `self.client.create_producer()` com parâmetros específicos do Pulsar (tópico, esquema, chunking_enabled)
**Linhas 31, 76:** Método `producer.close()`
**Linhas 64-65:** `producer.send()` com mensagem e propriedades

**Arquivo de especificação:** `trustgraph-base/trustgraph/base/producer_spec.py`
**Linha 18:** Referencia `processor.pulsar_client`

### 5. Abstração do Publicador

**Localização:** `trustgraph-base/trustgraph/base/publisher.py`

Publicação de mensagens assíncrona com buffer de fila:

**Importações do Pulsar:**
**Linha 2:** `from pulsar.schema import JsonSchema`
**Linha 6:** `import pulsar`

**Uso específico do Pulsar:**
**Linha 52:** Wrapper `JsonSchema(self.schema)`
**Linhas 50-54:** `self.client.create_producer()` com parâmetros específicos do Pulsar
**Linhas 101, 103:** `producer.send()` com mensagem e propriedades opcionais
**Linhas 106-107:** Métodos `producer.flush()` e `producer.close()`

### 6. Abstração do Assinante

**Localização:** `trustgraph-base/trustgraph/base/subscriber.py`

Fornece distribuição de mensagens para múltiplos destinatários a partir de filas:

**Importações do Pulsar:**
**Linha 6:** `from pulsar.schema import JsonSchema`
**Linha 8:** `import _pulsar`

**Uso específico do Pulsar:**
**Linha 55:** `JsonSchema(self.schema)` wrapper
**Linha 57:** `self.client.subscribe(**subscribe_args)`
**Linhas 101, 136, 160, 167-172:** Exceções do Pulsar: `_pulsar.Timeout`, `_pulsar.InvalidConfiguration`, `_pulsar.AlreadyClosed`
**Linhas 159, 166, 170:** Métodos do consumidor: `negative_acknowledge()`, `unsubscribe()`, `close()`
**Linhas 247, 251:** Reconhecimento de mensagens: `acknowledge()`, `negative_acknowledge()`

**Arquivo de especificação:** `trustgraph-base/trustgraph/base/subscriber_spec.py`
**Linha 19:** Referencia `processor.pulsar_client`

### 7. Sistema de Schema (Heart of Darkness)

**Localização:** `trustgraph-base/trustgraph/schema/`

Cada schema de mensagem no sistema é definido usando o framework de schema do Pulsar.

**Primitivos principais:** `schema/core/primitives.py`
**Linha 2:** `from pulsar.schema import Record, String, Boolean, Array, Integer`
Todos os schemas herdam da classe base do Pulsar `Record`
Todos os tipos de campo são tipos do Pulsar: `String()`, `Integer()`, `Boolean()`, `Array()`, `Map()`, `Double()`

**Schemas de exemplo:**
`schema/services/llm.py` (Linha 2): `from pulsar.schema import Record, String, Array, Double, Integer, Boolean`
`schema/services/config.py` (Linha 2): `from pulsar.schema import Record, Bytes, String, Boolean, Array, Map, Integer`

**Nomeação de tópicos:** `schema/core/topic.py`
**Linhas 2-3:** Formato do tópico: `{kind}://{tenant}/{namespace}/{topic}`
Esta estrutura de URI é específica do Pulsar (por exemplo, `persistent://tg/flow/config`)

**Impacto:**
Todas as definições de mensagens de solicitação/resposta em todo o código-fonte usam schemas do Pulsar
Isso inclui serviços para: config, flow, llm, prompt, query, storage, agent, collection, diagnosis, library, lookup, nlp_query, objects_query, retrieval, structured_query
As definições de schema são importadas e usadas extensivamente em todos os processadores e serviços

## Resumo

### Dependências do Pulsar por Categoria

1. **Instanciação do cliente:**
   Direto: `gateway/service.py`
   Abstrato: `async_processor.py` → `pubsub.py` (PulsarClient)

2. **Transporte de mensagens:**
   Consumidor: `consumer.py`, `consumer_spec.py`
   Produtor: `producer.py`, `producer_spec.py`
   Publicador: `publisher.py`
   Assinante: `subscriber.py`, `subscriber_spec.py`

3. **Sistema de schema:**
   Tipos base: `schema/core/primitives.py`
   Todos os schemas de serviço: `schema/services/*.py`
   Nomeação de tópicos: `schema/core/topic.py`

4. **Conceitos específicos do Pulsar necessários:**
   Mensagens baseadas em tópicos
   Sistema de schema (Registro, tipos de campo)
   Assinaturas compartilhadas
   Reconhecimento de mensagens (positivo/negativo)
   Posicionamento do consumidor (mais cedo/mais tarde)
   Propriedades da mensagem
   Posições iniciais e tipos de consumidor
   Suporte de fragmentação
   Tópicos persistentes vs não persistentes

### Desafios de Refatoração

A boa notícia: A camada de abstração (Consumidor, Produtor, Publicador, Assinante) fornece um encapsulamento limpo da maioria das interações do Pulsar.

Os desafios:
1. **Ubiquidade do sistema de schema:** Cada definição de mensagem usa `pulsar.schema.Record` e tipos de campo do Pulsar
2. **Enums específicos do Pulsar:** `InitialPosition`, `ConsumerType`
3. **Exceções do Pulsar:** `_pulsar.Timeout`, `_pulsar.Interrupted`, `_pulsar.InvalidConfiguration`, `_pulsar.AlreadyClosed`
4. **Assinaturas de método:** `acknowledge()`, `negative_acknowledge()`, `subscribe()`, `create_producer()`, etc.
5. **Formato de URI do tópico:** Estrutura do Pulsar `kind://tenant/namespace/topic`

### Próximos Passos

Para tornar a infraestrutura de pub/sub configurável, precisamos:

1. Criar uma interface de abstração para o sistema de cliente/schema
2. Abstrair enums e exceções específicos do Pulsar
3. Criar wrappers de schema ou definições de schema alternativas
4. Implementar a interface para sistemas Pulsar e sistemas alternativos (Kafka, RabbitMQ, Redis Streams, etc.)
5. Atualizar `pubsub.py` para ser configurável e suportar vários backends
6. Fornecer um caminho de migração para implantações existentes

## Abordagem Preliminar 1: Padrão Adapter com Camada de Tradução de Schema

### Principio Fundamental
O **sistema de schema** é o ponto de integração mais profundo - tudo o mais deriva dele. Precisamos resolver isso primeiro, ou teremos que reescrever todo o código-fonte.

### Estratégia: Encapsulamento Mínimo com Adapters

**1. Manter os esquemas Pulsar como a representação interna**
Não reescrever todas as definições de esquema
Os esquemas permanecem `pulsar.schema.Record` internamente
Usar adaptadores para traduzir na fronteira entre nosso código e o backend de publicação/assinatura

**2. Criar uma camada de abstração de publicação/assinatura:**

```
┌─────────────────────────────────────┐
│   Existing Code (unchanged)         │
│   - Uses Pulsar schemas internally  │
│   - Consumer/Producer/Publisher     │
└──────────────┬──────────────────────┘
               │
┌──────────────┴──────────────────────┐
│   PubSubFactory (configurable)      │
│   - Creates backend-specific client │
└──────────────┬──────────────────────┘
               │
        ┌──────┴──────┐
        │             │
┌───────▼─────┐  ┌────▼─────────┐
│ PulsarAdapter│  │ KafkaAdapter │  etc...
│ (passthrough)│  │ (translates) │
└──────────────┘  └──────────────┘
```

**3. Defina interfaces abstratas:**
`PubSubClient` - conexão do cliente
`PubSubProducer` - envio de mensagens
`PubSubConsumer` - recebimento de mensagens
`SchemaAdapter` - tradução de esquemas Pulsar para/de JSON ou formatos específicos do backend

**4. Detalhes de implementação:**

Para o **adaptador Pulsar**: Quase transparente, tradução mínima

Para **outros backends** (Kafka, RabbitMQ, etc.):
Serializa objetos de registro Pulsar para JSON/bytes
Mapeia conceitos como:
  `InitialPosition.Earliest/Latest` → auto.offset.reset do Kafka
  `acknowledge()` → commit do Kafka
  `negative_acknowledge()` → padrão de re-fila ou DLQ
  URIs de tópicos → nomes de tópicos específicos do backend

### Análise

**Prós:**
✅ Alterações mínimas no código dos serviços existentes
✅ Os esquemas permanecem como estão (sem reescrita massiva)
✅ Caminho de migração gradual
✅ Os usuários do Pulsar não percebem diferença
✅ Novos backends adicionados via adaptadores

**Contras:**
⚠️ Ainda possui dependência do Pulsar (para definições de esquema)
⚠️ Alguma incompatibilidade na tradução de conceitos

### Consideração Alternativa

Crie um sistema de esquemas **TrustGraph** que seja agnóstico de pub/sub (usando dataclasses ou Pydantic), e então gere esquemas Pulsar/Kafka/etc a partir dele. Isso requer reescrever todos os arquivos de esquema e pode causar alterações disruptivas.

### Recomendação para a Versão 1

Comece com a **abordagem de adaptador** porque:
1. É pragmática - funciona com o código existente
2. Demonstra o conceito com risco mínimo
3. Pode evoluir para um sistema de esquemas nativo posteriormente, se necessário
4. Impulsionado por configuração: uma variável de ambiente alterna entre backends

## Abordagem da Versão 2: Sistema de Esquemas Agnostic de Backend com Dataclasses

### Conceito Central

Use **dataclasses** do Python como o formato de definição de esquema neutro. Cada backend de pub/sub fornece sua própria serialização/desserialização para dataclasses, eliminando a necessidade de que os esquemas Pulsar permaneçam no código-fonte.

### Polimorfismo de Esquema no Nível da Fábrica

Em vez de traduzir esquemas Pulsar, **cada backend fornece seu próprio tratamento de esquema** que funciona com dataclasses Python padrão.

### Fluxo do Publicador

```python
# 1. Get the configured backend from factory
pubsub = get_pubsub()  # Returns PulsarBackend, MQTTBackend, etc.

# 2. Get schema class from the backend
# (Can be imported directly - backend-agnostic)
from trustgraph.schema.services.llm import TextCompletionRequest

# 3. Create a producer/publisher for a specific topic
producer = pubsub.create_producer(
    topic="text-completion-requests",
    schema=TextCompletionRequest  # Tells backend what schema to use
)

# 4. Create message instances (same API regardless of backend)
request = TextCompletionRequest(
    system="You are helpful",
    prompt="Hello world",
    streaming=False
)

# 5. Send the message
producer.send(request)  # Backend serializes appropriately
```

### Fluxo do Consumidor

```python
# 1. Get the configured backend
pubsub = get_pubsub()

# 2. Create a consumer
consumer = pubsub.subscribe(
    topic="text-completion-requests",
    schema=TextCompletionRequest  # Tells backend how to deserialize
)

# 3. Receive and deserialize
msg = consumer.receive()
request = msg.value()  # Returns TextCompletionRequest dataclass instance

# 4. Use the data (type-safe access)
print(request.system)   # "You are helpful"
print(request.prompt)   # "Hello world"
print(request.streaming)  # False
```

### O que acontece nos bastidores

**Para o backend Pulsar:**
`create_producer()` → cria um produtor Pulsar com esquema JSON ou um registro gerado dinamicamente.
`send(request)` → serializa a classe de dados para o formato JSON/Pulsar e envia para o Pulsar.
`receive()` → recebe a mensagem do Pulsar, desserializa de volta para a classe de dados.

**Para o backend MQTT:**
`create_producer()` → conecta a um broker MQTT, não é necessário registro de esquema.
`send(request)` → converte a classe de dados para JSON e publica em um tópico MQTT.
`receive()` → assina um tópico MQTT e desserializa o JSON para a classe de dados.

**Para o backend Kafka:**
`create_producer()` → cria um produtor Kafka e registra o esquema Avro, se necessário.
`send(request)` → serializa a classe de dados para o formato Avro e envia para o Kafka.
`receive()` → recebe a mensagem do Kafka e desserializa o Avro de volta para a classe de dados.

### Pontos-chave do design

1. **Criação do objeto de esquema**: A instância da classe de dados (`TextCompletionRequest(...)`) é idêntica, independentemente do backend.
2. **O backend lida com a codificação**: Cada backend sabe como serializar sua classe de dados para o formato de transmissão.
3. **Definição do esquema na criação**: Ao criar o produtor/consumidor, você especifica o tipo de esquema.
4. **Segurança de tipo preservada**: Você recebe um objeto `TextCompletionRequest` adequado, não um dicionário.
5. **Nenhum vazamento do backend**: O código da aplicação nunca importa bibliotecas específicas do backend.

### Exemplo de transformação

**Atual (específico para Pulsar):**
```python
# schema/services/llm.py
from pulsar.schema import Record, String, Boolean, Integer

class TextCompletionRequest(Record):
    system = String()
    prompt = String()
    streaming = Boolean()
```

**Novo (Independente do backend):**
```python
# schema/services/llm.py
from dataclasses import dataclass

@dataclass
class TextCompletionRequest:
    system: str
    prompt: str
    streaming: bool = False
```

### Integração com o Backend

Cada backend lida com a serialização/desserialização de dataclasses:

**Backend Pulsar:**
Gera classes `pulsar.schema.Record` dinamicamente a partir de dataclasses
Ou serializa dataclasses para JSON e usa o esquema JSON do Pulsar
Mantém a compatibilidade com implantações Pulsar existentes

**Backend MQTT/Redis:**
Serialização direta de instâncias de dataclass para JSON
Use `dataclasses.asdict()` / `from_dict()`
Leve, não requer registro de esquema

**Backend Kafka:**
Gera esquemas Avro a partir de definições de dataclass
Use o registro de esquema da Confluent
Serialização com segurança de tipo com suporte à evolução do esquema

### Arquitetura

```
┌─────────────────────────────────────┐
│   Application Code                  │
│   - Uses dataclass schemas          │
│   - Backend-agnostic                │
└──────────────┬──────────────────────┘
               │
┌──────────────┴──────────────────────┐
│   PubSubFactory (configurable)      │
│   - get_pubsub() returns backend    │
└──────────────┬──────────────────────┘
               │
        ┌──────┴──────┐
        │             │
┌───────▼─────────┐  ┌────▼──────────────┐
│ PulsarBackend   │  │ MQTTBackend       │
│ - JSON schema   │  │ - JSON serialize  │
│ - or dynamic    │  │ - Simple queues   │
│   Record gen    │  │                   │
└─────────────────┘  └───────────────────┘
```

### Detalhes de Implementação

**1. Definições de esquema:** Dataclasses simples com dicas de tipo
   `str`, `int`, `bool`, `float` para tipos primitivos
   `list[T]` para arrays
   `dict[str, T]` para mapas
   Dataclasses aninhados para tipos complexos

**2. Cada backend fornece:**
   Serializador: `dataclass → bytes/wire format`
   Deserializador: `bytes/wire format → dataclass`
   Registro de esquema (se necessário, como Pulsar/Kafka)

**3. Abstração de consumidor/produtor:**
   Já existe (consumer.py, producer.py)
   Atualizar para usar a serialização do backend
   Remover importações diretas do Pulsar

**4. Mapeamentos de tipo:**
   Pulsar `String()` → Python `str`
   Pulsar `Integer()` → Python `int`
   Pulsar `Boolean()` → Python `bool`
   Pulsar `Array(T)` → Python `list[T]`
   Pulsar `Map(K, V)` → Python `dict[K, V]`
   Pulsar `Double()` → Python `float`
   Pulsar `Bytes()` → Python `bytes`

### Caminho de Migração

1. **Criar versões de dataclass** de todos os esquemas em `trustgraph/schema/`
2. **Atualizar classes de backend** (Consumer, Producer, Publisher, Subscriber) para usar a serialização fornecida pelo backend
3. **Implementar PulsarBackend** com esquema JSON ou geração dinâmica de Record
4. **Testar com Pulsar** para garantir a compatibilidade com versões anteriores com implantações existentes
5. **Adicionar novos backends** (MQTT, Kafka, Redis, etc.) conforme necessário
6. **Remover importações do Pulsar** de arquivos de esquema

### Benefícios

✅ **Nenhuma dependência de pub/sub** nas definições de esquema
✅ **Python padrão** - fácil de entender, tipar, documentar
✅ **Ferramentas modernas** - funciona com mypy, preenchimento automático de IDE, linters
✅ **Otimizado para backend** - cada backend usa a serialização nativa
✅ **Sem sobrecarga de tradução** - serialização direta, sem adaptadores
✅ **Segurança de tipo** - objetos reais com tipos adequados
✅ **Validação fácil** - pode usar Pydantic, se necessário

### Desafios e Soluções

**Desafio:** O `Record` do Pulsar tem validação de campo em tempo de execução
**Solução:** Use dataclasses Pydantic para validação, se necessário, ou recursos de dataclass Python 3.10+ com `__post_init__`

**Desafio:** Alguns recursos específicos do Pulsar (como o tipo `Bytes`)
**Solução:** Mapear para o tipo `bytes` na dataclass, o backend lida com a codificação apropriadamente

**Desafio:** Nomenclatura de tópicos (`persistent://tenant/namespace/topic`)
**Solução:** Abstrair nomes de tópicos em definições de esquema, o backend converte para o formato adequado

**Desafio:** Evolução e versionamento de esquema
**Solução:** Cada backend lida com isso de acordo com suas capacidades (versões de esquema do Pulsar, registro de esquema do Kafka, etc.)

**Desafio:** Tipos complexos aninhados
**Solução:** Use dataclasses aninhadas, os backends serializam/desserializam recursivamente

### Decisões de Design

1. **Dataclasses simples ou Pydantic?**
   ✅ **Decisão: Usar dataclasses Python simples**
   Mais simples, sem dependências adicionais
   Validação não é necessária na prática
   Mais fácil de entender e manter

2. **Evolução de esquema:**
   ✅ **Decisão: Nenhum mecanismo de versionamento necessário**
   Os esquemas são estáveis e duradouros
   As atualizações normalmente adicionam novos campos (compatíveis com versões anteriores)
   Os backends lidam com a evolução do esquema de acordo com suas capacidades

3. **Compatibilidade com versões anteriores:**
   ✅ **Decisão: Alteração de versão principal, compatibilidade com versões anteriores não é necessária**
   Será uma alteração disruptiva com instruções de migração
   A separação limpa permite um melhor design
   Um guia de migração será fornecido para implantações existentes

4. **Tipos aninhados e estruturas complexas:**
   ✅ **Decisão: Usar dataclasses aninhadas naturalmente**
   Dataclasses Python lidam com o aninhamento perfeitamente
   `list[T]` para arrays, `dict[K, V]` para mapas
   Backends serializam/desserializam recursivamente
   Exemplo:
     ```python
     @dataclass
     class Value:
         value: str
         is_uri: bool

     @dataclass
     class Triple:
         s: Value              # Nested dataclass
         p: Value
         o: Value

     @dataclass
     class GraphQuery:
         triples: list[Triple]  # Array of nested dataclasses
         metadata: dict[str, str]
     ```

5. **Valores padrão e campos opcionais:**
   ✅ **Decisão: Mistura de campos obrigatórios, valores padrão e campos opcionais**
   Campos obrigatórios: Sem valor padrão
   Campos com valores padrão: Sempre presentes, possuem um valor padrão razoável
   Campos verdadeiramente opcionais: `T | None = None`, omitidos da serialização quando `None`
   Exemplo:
     ```python
     @dataclass
     class TextCompletionRequest:
         system: str              # Required, no default
         prompt: str              # Required, no default
         streaming: bool = False  # Optional with default value
         metadata: dict | None = None  # Truly optional, can be absent
     ```

   **Semântica de serialização importante:**

   Quando `metadata = None`:
   ```json
   {
       "system": "...",
       "prompt": "...",
       "streaming": false
       // metadata field NOT PRESENT
   }
   ```

   Quando `metadata = {}` (explicitamente vazio):
   ```json
   {
       "system": "...",
       "prompt": "...",
       "streaming": false,
       "metadata": {}  // Field PRESENT but empty
   }
   ```

   **Diferença chave:**
   `None` → campo ausente do JSON (não serializado)
   Valor vazio (`{}`, `[]`, `""`) → campo presente com valor vazio
   Isso importa semanticamente: "não fornecido" vs "explicitamente vazio"
   Os backends de serialização devem ignorar os campos `None`, não codificá-los como `null`

## Abordagem Rascunho 3: Detalhes de Implementação

### Formato Genérico de Nomes de Filas

Substitua os nomes de filas específicos do backend por um formato genérico que os backends possam mapear adequadamente.

**Formato:** `{qos}/{tenant}/{namespace}/{queue-name}`

Onde:
`qos`: Nível de Qualidade de Serviço
  `q0` = melhor esforço (enviar e esquecer, sem confirmação)
  `q1` = pelo menos uma vez (requer confirmação)
  `q2` = exatamente uma vez (confirmação de duas fases)
`tenant`: Agrupamento lógico para multi-inquilinato
`namespace`: Sub-agrupamento dentro do inquilino
`queue-name`: Nome real da fila/tópico

**Exemplos:**
```
q1/tg/flow/text-completion-requests
q2/tg/config/config-push
q0/tg/metrics/stats
```

### Mapeamento de Tópicos do Backend

Cada backend mapeia o formato genérico para o seu formato nativo:

**Backend do Pulsar:**
```python
def map_topic(self, generic_topic: str) -> str:
    # Parse: q1/tg/flow/text-completion-requests
    qos, tenant, namespace, queue = generic_topic.split('/', 3)

    # Map QoS to persistence
    persistence = 'persistent' if qos in ['q1', 'q2'] else 'non-persistent'

    # Return Pulsar URI: persistent://tg/flow/text-completion-requests
    return f"{persistence}://{tenant}/{namespace}/{queue}"
```

**Backend MQTT:**
```python
def map_topic(self, generic_topic: str) -> tuple[str, int]:
    # Parse: q1/tg/flow/text-completion-requests
    qos, tenant, namespace, queue = generic_topic.split('/', 3)

    # Map QoS level
    qos_level = {'q0': 0, 'q1': 1, 'q2': 2}[qos]

    # Build MQTT topic including tenant/namespace for proper namespacing
    mqtt_topic = f"{tenant}/{namespace}/{queue}"

    return mqtt_topic, qos_level
```

### Função de Auxílio de Tópico Atualizada

```python
# schema/core/topic.py
def topic(queue_name, qos='q1', tenant='tg', namespace='flow'):
    """
    Create a generic topic identifier that can be mapped by backends.

    Args:
        queue_name: The queue/topic name
        qos: Quality of service
             - 'q0' = best-effort (no ack)
             - 'q1' = at-least-once (ack required)
             - 'q2' = exactly-once (two-phase ack)
        tenant: Tenant identifier for multi-tenancy
        namespace: Namespace within tenant

    Returns:
        Generic topic string: qos/tenant/namespace/queue_name

    Examples:
        topic('my-queue')  # q1/tg/flow/my-queue
        topic('config', qos='q2', namespace='config')  # q2/tg/config/config
    """
    return f"{qos}/{tenant}/{namespace}/{queue_name}"
```

### Configuração e Inicialização

**Argumentos de Linha de Comando + Variáveis de Ambiente:**

```python
# In base/async_processor.py - add_args() method
@staticmethod
def add_args(parser):
    # Pub/sub backend selection
    parser.add_argument(
        '--pubsub-backend',
        default=os.getenv('PUBSUB_BACKEND', 'pulsar'),
        choices=['pulsar', 'mqtt'],
        help='Pub/sub backend (default: pulsar, env: PUBSUB_BACKEND)'
    )

    # Pulsar-specific configuration
    parser.add_argument(
        '--pulsar-host',
        default=os.getenv('PULSAR_HOST', 'pulsar://localhost:6650'),
        help='Pulsar host (default: pulsar://localhost:6650, env: PULSAR_HOST)'
    )

    parser.add_argument(
        '--pulsar-api-key',
        default=os.getenv('PULSAR_API_KEY', None),
        help='Pulsar API key (env: PULSAR_API_KEY)'
    )

    parser.add_argument(
        '--pulsar-listener',
        default=os.getenv('PULSAR_LISTENER', None),
        help='Pulsar listener name (env: PULSAR_LISTENER)'
    )

    # MQTT-specific configuration
    parser.add_argument(
        '--mqtt-host',
        default=os.getenv('MQTT_HOST', 'localhost'),
        help='MQTT broker host (default: localhost, env: MQTT_HOST)'
    )

    parser.add_argument(
        '--mqtt-port',
        type=int,
        default=int(os.getenv('MQTT_PORT', '1883')),
        help='MQTT broker port (default: 1883, env: MQTT_PORT)'
    )

    parser.add_argument(
        '--mqtt-username',
        default=os.getenv('MQTT_USERNAME', None),
        help='MQTT username (env: MQTT_USERNAME)'
    )

    parser.add_argument(
        '--mqtt-password',
        default=os.getenv('MQTT_PASSWORD', None),
        help='MQTT password (env: MQTT_PASSWORD)'
    )
```

**Função de Fábrica:**

```python
# In base/pubsub.py or base/pubsub_factory.py
def get_pubsub(**config) -> PubSubBackend:
    """
    Create and return a pub/sub backend based on configuration.

    Args:
        config: Configuration dict from command-line args
                Must include 'pubsub_backend' key

    Returns:
        Backend instance (PulsarBackend, MQTTBackend, etc.)
    """
    backend_type = config.get('pubsub_backend', 'pulsar')

    if backend_type == 'pulsar':
        return PulsarBackend(
            host=config.get('pulsar_host'),
            api_key=config.get('pulsar_api_key'),
            listener=config.get('pulsar_listener'),
        )
    elif backend_type == 'mqtt':
        return MQTTBackend(
            host=config.get('mqtt_host'),
            port=config.get('mqtt_port'),
            username=config.get('mqtt_username'),
            password=config.get('mqtt_password'),
        )
    else:
        raise ValueError(f"Unknown pub/sub backend: {backend_type}")
```

**Uso em AsyncProcessor:**

```python
# In async_processor.py
class AsyncProcessor:
    def __init__(self, **params):
        self.id = params.get("id")

        # Create backend from config (replaces PulsarClient)
        self.pubsub = get_pubsub(**params)

        # Rest of initialization...
```

### Interface de Backend

```python
class PubSubBackend(Protocol):
    """Protocol defining the interface all pub/sub backends must implement."""

    def create_producer(self, topic: str, schema: type, **options) -> BackendProducer:
        """
        Create a producer for a topic.

        Args:
            topic: Generic topic format (qos/tenant/namespace/queue)
            schema: Dataclass type for messages
            options: Backend-specific options (e.g., chunking_enabled)

        Returns:
            Backend-specific producer instance
        """
        ...

    def create_consumer(
        self,
        topic: str,
        subscription: str,
        schema: type,
        initial_position: str = 'latest',
        consumer_type: str = 'shared',
        **options
    ) -> BackendConsumer:
        """
        Create a consumer for a topic.

        Args:
            topic: Generic topic format (qos/tenant/namespace/queue)
            subscription: Subscription/consumer group name
            schema: Dataclass type for messages
            initial_position: 'earliest' or 'latest' (MQTT may ignore)
            consumer_type: 'shared', 'exclusive', 'failover' (MQTT may ignore)
            options: Backend-specific options

        Returns:
            Backend-specific consumer instance
        """
        ...

    def close(self) -> None:
        """Close the backend connection."""
        ...
```

```python
class BackendProducer(Protocol):
    """Protocol for backend-specific producer."""

    def send(self, message: Any, properties: dict = {}) -> None:
        """Send a message (dataclass instance) with optional properties."""
        ...

    def flush(self) -> None:
        """Flush any buffered messages."""
        ...

    def close(self) -> None:
        """Close the producer."""
        ...
```

```python
class BackendConsumer(Protocol):
    """Protocol for backend-specific consumer."""

    def receive(self, timeout_millis: int = 2000) -> Message:
        """
        Receive a message from the topic.

        Raises:
            TimeoutError: If no message received within timeout
        """
        ...

    def acknowledge(self, message: Message) -> None:
        """Acknowledge successful processing of a message."""
        ...

    def negative_acknowledge(self, message: Message) -> None:
        """Negative acknowledge - triggers redelivery."""
        ...

    def unsubscribe(self) -> None:
        """Unsubscribe from the topic."""
        ...

    def close(self) -> None:
        """Close the consumer."""
        ...
```

```python
class Message(Protocol):
    """Protocol for a received message."""

    def value(self) -> Any:
        """Get the deserialized message (dataclass instance)."""
        ...

    def properties(self) -> dict:
        """Get message properties/metadata."""
        ...
```

### Refatoração das Classes Existentes

As classes existentes `Consumer`, `Producer`, `Publisher`, `Subscriber` permanecem em grande parte inalteradas:

**Responsabilidades atuais (manter):**
Modelo de threading assíncrono e grupos de tarefas
Lógica de reconexão e tratamento de repetições
Coleta de métricas
Limitação de taxa
Gerenciamento de concorrência

**Alterações necessárias:**
Remover importações diretas do Pulsar (`pulsar.schema`, `pulsar.InitialPosition`, etc.)
Aceitar `BackendProducer`/`BackendConsumer` em vez do cliente Pulsar
Delegar as operações reais de publicação/assinatura para instâncias de backend
Mapear conceitos genéricos para chamadas de backend

**Exemplo de refatoração:**

```python
# OLD - consumer.py
class Consumer:
    def __init__(self, client, topic, subscriber, schema, ...):
        self.client = client  # Direct Pulsar client
        # ...

    async def consumer_run(self):
        # Uses pulsar.InitialPosition, pulsar.ConsumerType
        self.consumer = self.client.subscribe(
            topic=self.topic,
            schema=JsonSchema(self.schema),
            initial_position=pulsar.InitialPosition.Earliest,
            consumer_type=pulsar.ConsumerType.Shared,
        )

# NEW - consumer.py
class Consumer:
    def __init__(self, backend_consumer, schema, ...):
        self.backend_consumer = backend_consumer  # Backend-specific consumer
        self.schema = schema
        # ...

    async def consumer_run(self):
        # Backend consumer already created with right settings
        # Just use it directly
        while self.running:
            msg = await asyncio.to_thread(
                self.backend_consumer.receive,
                timeout_millis=2000
            )
            await self.handle_message(msg)
```

### Comportamentos Específicos do Backend

**Backend Pulsar:**
Mapeia `q0` → `non-persistent://`, `q1`/`q2` → `persistent://`
Suporta todos os tipos de consumidores (compartilhado, exclusivo, failover)
Suporta posição inicial (earliest/latest)
Reconhecimento nativo de mensagens
Suporte para registro de esquema

**Backend MQTT:**
Mapeia `q0`/`q1`/`q2` → Níveis de QoS MQTT 0/1/2
Inclui tenant/namespace no caminho do tópico para fins de namespace
Gera automaticamente IDs de cliente a partir de nomes de inscrição
Ignora a posição inicial (sem histórico de mensagens no MQTT básico)
Ignora o tipo de consumidor (o MQTT usa IDs de cliente, não grupos de consumidores)
Modelo de publicação/assinatura simples

### Resumo das Decisões de Design

1. ✅ **Nomeação genérica de filas**: Formato `qos/tenant/namespace/queue-name`
2. ✅ **QoS no ID da fila**: Determinado pela definição da fila, não pela configuração
3. ✅ **Reconexão**: Tratada pelas classes Consumer/Producer, não pelos backends
4. ✅ **Tópicos MQTT**: Incluem tenant/namespace para namespace adequado
5. ✅ **Histórico de mensagens**: O MQTT ignora o parâmetro `initial_position` (melhoria futura)
6. ✅ **IDs de cliente**: O backend MQTT gera automaticamente a partir do nome da inscrição

### Melhorias Futuras

**Histórico de mensagens MQTT:**
Poderia adicionar uma camada de persistência opcional (por exemplo, mensagens retidas, armazenamento externo)
Permitiria suportar `initial_position='earliest'`
Não é necessário para a implementação inicial

