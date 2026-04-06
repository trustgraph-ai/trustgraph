# Especificação Técnica de Processamento em Lote de Embeddings

## Visão Geral

Esta especificação descreve otimizações para o serviço de embeddings para suportar o processamento em lote de vários textos em um único pedido. A implementação atual processa um texto por vez, perdendo os benefícios de desempenho significativos que os modelos de embedding oferecem ao processar lotes.

1. **Ineficiência no Processamento de Texto Único**: A implementação atual envolve textos únicos em uma lista, subutilizando as capacidades de lote do FastEmbed.
2. **Sobrecarga de Pedido por Texto**: Cada texto requer uma viagem de ida e volta separada do Pulsar.
3. **Ineficiência na Inferência do Modelo**: Os modelos de embedding têm uma sobrecarga fixa por lote; lotes pequenos desperdiçam recursos de GPU/CPU.
4. **Processamento Serial nos Clientes**: Serviços importantes fazem loop sobre itens e chamam embeddings um de cada vez.

## Objetivos

**Suporte para API de Lote**: Permitir o processamento de vários textos em um único pedido.
**Compatibilidade com Versões Anteriores**: Manter o suporte para pedidos de texto único.
**Melhora Significativa no Desempenho**: Almejar uma melhora de desempenho de 5 a 10 vezes para operações em lote.
**Latência Reduzida por Texto**: Diminuir a latência amortizada ao incorporar vários textos.
**Eficiência de Memória**: Processar lotes sem consumo excessivo de memória.
**Independente do Provedor**: Suportar o processamento em lote em FastEmbed, Ollama e outros provedores.
**Migração do Cliente**: Atualizar todos os clientes de embedding para usar a API de lote sempre que for benéfico.

## Contexto

### Implementação Atual - Serviço de Embeddings

A implementação de embeddings em `trustgraph-flow/trustgraph/embeddings/fastembed/processor.py` apresenta uma ineficiência de desempenho significativa:

```python
# fastembed/processor.py line 56
async def on_embeddings(self, text, model=None):
    use_model = model or self.default_model
    self._load_model(use_model)

    vecs = self.embeddings.embed([text])  # Single text wrapped in list

    return [v.tolist() for v in vecs]
```

**Problemas:**

1. **Tamanho do Lote 1**: O método `embed()` do FastEmbed é otimizado para processamento em lote, mas sempre o chamamos com `[text]` - um lote de tamanho 1.

2. **Sobrecarga por Requisição**: Cada solicitação de incorporação incorre em:
   Serialização/desserialização de mensagens Pulsar
   Latência de ida e volta da rede
   Sobrecarga de inicialização da inferência do modelo
   Sobrecarga de agendamento assíncrono do Python

3. **Limitação do Esquema**: O esquema `EmbeddingsRequest` suporta apenas um único texto:
   ```python
   @dataclass
   class EmbeddingsRequest:
       text: str = ""  # Single text only
   ```

### Clientes Atuais - Processamento Serial

#### 1. Gateway de API

**Arquivo:** `trustgraph-flow/trustgraph/gateway/dispatch/embeddings.py`

O gateway aceita solicitações de incorporação de texto único via HTTP/WebSocket e as encaminha para o serviço de incorporação. Atualmente, não existe um endpoint para processamento em lote.

```python
class EmbeddingsRequestor(ServiceRequestor):
    # Handles single EmbeddingsRequest -> EmbeddingsResponse
    request_schema=EmbeddingsRequest,  # Single text only
    response_schema=EmbeddingsResponse,
```

**Impacto:** Clientes externos (aplicativos web, scripts) devem fazer N requisições HTTP para incorporar N textos.

#### 2. Serviço de Incorporação de Documentos

**Arquivo:** `trustgraph-flow/trustgraph/embeddings/document_embeddings/embeddings.py`

Processa blocos de documentos um de cada vez:

```python
async def on_message(self, msg, consumer, flow):
    v = msg.value()

    # Single chunk per request
    resp = await flow("embeddings-request").request(
        EmbeddingsRequest(text=v.chunk)
    )
    vectors = resp.vectors
```

**Impacto:** Cada trecho de documento requer uma chamada de embedding separada. Um documento com 100 trechos = 100 requisições de embedding.

#### 3. Serviço de Embeddings de Grafos

**Arquivo:** `trustgraph-flow/trustgraph/embeddings/graph_embeddings/embeddings.py`

Percorre as entidades e incorpora cada uma sequencialmente:

```python
async def on_message(self, msg, consumer, flow):
    for entity in v.entities:
        # Serial embedding - one entity at a time
        vectors = await flow("embeddings-request").embed(
            text=entity.context
        )
        entities.append(EntityEmbeddings(
            entity=entity.entity,
            vectors=vectors,
            chunk_id=entity.chunk_id,
        ))
```

**Impacto:** Uma mensagem com 50 entidades = 50 solicitações de incorporação serial. Isso é um grande gargalo durante a construção do grafo de conhecimento.

#### 4. Serviço de Incorporação de Linhas

**Arquivo:** `trustgraph-flow/trustgraph/embeddings/row_embeddings/embeddings.py`

Percorre textos únicos e incorpora cada um serialmente:

```python
async def on_message(self, msg, consumer, flow):
    for text, (index_name, index_value) in texts_to_embed.items():
        # Serial embedding - one text at a time
        vectors = await flow("embeddings-request").embed(text=text)

        embeddings_list.append(RowIndexEmbedding(
            index_name=index_name,
            index_value=index_value,
            text=text,
            vectors=vectors
        ))
```

**Impacto:** Processar uma tabela com 100 valores indexados únicos = 100 solicitações de incorporação seriais.

#### 5. EmbeddingsClient (Cliente Base)

**Arquivo:** `trustgraph-base/trustgraph/base/embeddings_client.py`

O cliente usado por todos os processadores de fluxo suporta apenas a incorporação de texto único:

```python
class EmbeddingsClient(RequestResponse):
    async def embed(self, text, timeout=30):
        resp = await self.request(
            EmbeddingsRequest(text=text),  # Single text
            timeout=timeout
        )
        return resp.vectors
```

**Impacto:** Todos os clientes que utilizam este componente estão limitados a operações de texto único.

#### 6. Ferramentas de Linha de Comando

**Arquivo:** `trustgraph-cli/trustgraph/cli/invoke_embeddings.py`

A ferramenta de linha de comando aceita um único argumento de texto:

```python
def query(url, flow_id, text, token=None):
    result = flow.embeddings(text=text)  # Single text
    vectors = result.get("vectors", [])
```

**Impacto:** Os usuários não podem realizar incorporações em lote a partir da linha de comando. O processamento de um arquivo de textos requer N invocações.

#### 7. SDK Python

O SDK Python fornece duas classes de cliente para interagir com os serviços da TrustGraph. Ambas suportam apenas a incorporação de um único texto.

**Arquivo:** `trustgraph-base/trustgraph/api/flow.py`

```python
class FlowInstance:
    def embeddings(self, text):
        """Get embeddings for a single text"""
        input = {"text": text}
        return self.request("service/embeddings", input)["vectors"]
```

**Arquivo:** `trustgraph-base/trustgraph/api/socket_client.py`

```python
class SocketFlowInstance:
    def embeddings(self, text: str, **kwargs: Any) -> Dict[str, Any]:
        """Get embeddings for a single text via WebSocket"""
        request = {"text": text}
        return self.client._send_request_sync(
            "embeddings", self.flow_id, request, False
        )
```

**Impacto:** Desenvolvedores Python que usam o SDK precisam iterar sobre textos e fazer N chamadas de API separadas. Não existe suporte para processamento em lote de embeddings para usuários do SDK.

### Impacto no Desempenho

Para ingestão típica de documentos (1000 trechos de texto):
**Atual:** 1000 requisições separadas, 1000 chamadas de inferência de modelo
**Em lote (batch_size=32):** 32 requisições, 32 chamadas de inferência de modelo (redução de 96,8%)

Para embedding de grafos (mensagem com 50 entidades):
**Atual:** 50 chamadas `await` sequenciais, ~5-10 segundos
**Em lote:** 1-2 chamadas em lote, ~0,5-1 segundo (melhora de 5-10x)

Bibliotecas como FastEmbed e similares alcançam escalabilidade quase linear no throughput com o tamanho do lote, até os limites do hardware (tipicamente 32-128 textos por lote).

## Design Técnico

### Arquitetura

A otimização de processamento em lote de embeddings requer alterações nos seguintes componentes:

#### 1. **Aprimoramento do Esquema**
   Estender `EmbeddingsRequest` para suportar múltiplos textos
   Estender `EmbeddingsResponse` para retornar múltiplos conjuntos de vetores
   Manter a compatibilidade retroativa com requisições de texto único

   Módulo: `trustgraph-base/trustgraph/schema/services/llm.py`

#### 2. **Aprimoramento do Serviço Base**
   Atualizar `EmbeddingsService` para lidar com requisições em lote
   Adicionar configuração do tamanho do lote
   Implementar tratamento de requisições com suporte a lote

   Módulo: `trustgraph-base/trustgraph/base/embeddings_service.py`

#### 3. **Atualizações do Processador do Provedor**
   Atualizar o processador FastEmbed para passar o lote completo para `embed()`
   Atualizar o processador Ollama para lidar com lotes (se suportado)
   Adicionar processamento sequencial como fallback para provedores sem suporte a lote

   Módulos:
   `trustgraph-flow/trustgraph/embeddings/fastembed/processor.py`
   `trustgraph-flow/trustgraph/embeddings/ollama/processor.py`

#### 4. **Aprimoramento do Cliente**
   Adicionar método de embedding em lote para `EmbeddingsClient`
   Suportar APIs de texto único e em lote
   Adicionar agrupamento automático para grandes entradas

   Módulo: `trustgraph-base/trustgraph/base/embeddings_client.py`

#### 5. **Atualizações do Chamador - Processadores de Fluxo**
   Atualizar `graph_embeddings` para agrupar contextos de entidades
   Atualizar `row_embeddings` para agrupar textos de índice
   Atualizar `document_embeddings` se o agrupamento de mensagens for viável

   Módulos:
   `trustgraph-flow/trustgraph/embeddings/graph_embeddings/embeddings.py`
   `trustgraph-flow/trustgraph/embeddings/row_embeddings/embeddings.py`
   `trustgraph-flow/trustgraph/embeddings/document_embeddings/embeddings.py`

#### 6. **Aprimoramento do Gateway de API**
   Adicionar endpoint de embedding em lote
   Suportar array de textos no corpo da requisição

   Módulo: `trustgraph-flow/trustgraph/gateway/dispatch/embeddings.py`

#### 7. **Aprimoramento da Ferramenta de Linha de Comando (CLI)**
   Adicionar suporte para múltiplos textos ou entrada de arquivo
   Adicionar parâmetro de tamanho do lote

   Módulo: `trustgraph-cli/trustgraph/cli/invoke_embeddings.py`

#### 8. **Aprimoramento do SDK Python**
   Adicionar método `embeddings_batch()` para `FlowInstance`
   Adicionar método `embeddings_batch()` para `SocketFlowInstance`
   Suportar APIs de texto único e em lote para usuários do SDK

   Módulos:
   `trustgraph-base/trustgraph/api/flow.py`
   `trustgraph-base/trustgraph/api/socket_client.py`

### Modelos de Dados

#### EmbeddingsRequest

```python
@dataclass
class EmbeddingsRequest:
    texts: list[str] = field(default_factory=list)
```

Uso:
Texto único: `EmbeddingsRequest(texts=["hello world"])`
Lote: `EmbeddingsRequest(texts=["text1", "text2", "text3"])`

#### EmbeddingsResponse

```python
@dataclass
class EmbeddingsResponse:
    error: Error | None = None
    vectors: list[list[list[float]]] = field(default_factory=list)
```

Estrutura da resposta:
`vectors[i]` contém o conjunto de vetores para `texts[i]`
Cada conjunto de vetores é `list[list[float]]` (os modelos podem retornar vários vetores por texto)
Exemplo: 3 textos → `vectors` tem 3 entradas, cada uma contendo os embeddings desse texto

### APIs

#### EmbeddingsClient

```python
class EmbeddingsClient(RequestResponse):
    async def embed(
        self,
        texts: list[str],
        timeout: float = 300,
    ) -> list[list[list[float]]]:
        """
        Embed one or more texts in a single request.

        Args:
            texts: List of texts to embed
            timeout: Timeout for the operation

        Returns:
            List of vector sets, one per input text
        """
        resp = await self.request(
            EmbeddingsRequest(texts=texts),
            timeout=timeout
        )
        if resp.error:
            raise RuntimeError(resp.error.message)
        return resp.vectors
```

#### Endpoint de Incorporação do Gateway de API

Endpoint atualizado que suporta incorporação única ou em lote:

```
POST /api/v1/embeddings
Content-Type: application/json

{
    "texts": ["text1", "text2", "text3"],
    "flow_id": "default"
}

Response:
{
    "vectors": [
        [[0.1, 0.2, ...]],
        [[0.3, 0.4, ...]],
        [[0.5, 0.6, ...]]
    ]
}
```

### Detalhes de Implementação

#### Fase 1: Alterações no Esquema

**EmbeddingsRequest:**
```python
@dataclass
class EmbeddingsRequest:
    texts: list[str] = field(default_factory=list)
```

**EmbeddingsResponse:**
```python
@dataclass
class EmbeddingsResponse:
    error: Error | None = None
    vectors: list[list[list[float]]] = field(default_factory=list)
```

**Atualizado EmbeddingsService.on_request:**
```python
async def on_request(self, msg, consumer, flow):
    request = msg.value()
    id = msg.properties()["id"]
    model = flow("model")

    vectors = await self.on_embeddings(request.texts, model=model)
    response = EmbeddingsResponse(error=None, vectors=vectors)

    await flow("response").send(response, properties={"id": id})
```

#### Fase 2: Atualização do Processador FastEmbed

**Atual (Ineficiente):**
```python
async def on_embeddings(self, text, model=None):
    use_model = model or self.default_model
    self._load_model(use_model)
    vecs = self.embeddings.embed([text])  # Batch of 1
    return [v.tolist() for v in vecs]
```

**Atualizado:**
```python
async def on_embeddings(self, texts: list[str], model=None):
    """Embed texts - processes all texts in single model call"""
    if not texts:
        return []

    use_model = model or self.default_model
    self._load_model(use_model)

    # FastEmbed handles the full batch efficiently
    all_vecs = list(self.embeddings.embed(texts))

    # Return list of vector sets, one per input text
    return [[v.tolist()] for v in all_vecs]
```

#### Fase 3: Atualização do Serviço de Incorporação de Grafos

**Atual (Serial):**
```python
async def on_message(self, msg, consumer, flow):
    entities = []
    for entity in v.entities:
        vectors = await flow("embeddings-request").embed(text=entity.context)
        entities.append(EntityEmbeddings(...))
```

**Atualizado (Lote):**
```python
async def on_message(self, msg, consumer, flow):
    # Collect all contexts
    contexts = [entity.context for entity in v.entities]

    # Single batch embedding call
    all_vectors = await flow("embeddings-request").embed(texts=contexts)

    # Pair results with entities
    entities = [
        EntityEmbeddings(
            entity=entity.entity,
            vectors=vectors[0],  # First vector from the set
            chunk_id=entity.chunk_id,
        )
        for entity, vectors in zip(v.entities, all_vectors)
    ]
```

#### Fase 4: Atualização do Serviço de Incorporação de Dados

**Atual (Serial):**
```python
for text, (index_name, index_value) in texts_to_embed.items():
    vectors = await flow("embeddings-request").embed(text=text)
    embeddings_list.append(RowIndexEmbedding(...))
```

**Atualizado (Lote):**
```python
# Collect texts and metadata
texts = list(texts_to_embed.keys())
metadata = list(texts_to_embed.values())

# Single batch embedding call
all_vectors = await flow("embeddings-request").embed(texts=texts)

# Pair results
embeddings_list = [
    RowIndexEmbedding(
        index_name=meta[0],
        index_value=meta[1],
        text=text,
        vectors=vectors[0]  # First vector from the set
    )
    for text, meta, vectors in zip(texts, metadata, all_vectors)
]
```

#### Fase 5: Melhoria da Ferramenta de Linha de Comando (CLI)

**CLI Atualizado:**
```python
def main():
    parser = argparse.ArgumentParser(...)

    parser.add_argument(
        'text',
        nargs='*',  # Zero or more texts
        help='Text(s) to convert to embedding vectors',
    )

    parser.add_argument(
        '-f', '--file',
        help='File containing texts (one per line)',
    )

    parser.add_argument(
        '--batch-size',
        type=int,
        default=32,
        help='Batch size for processing (default: 32)',
    )
```

Uso:
```bash
# Single text (existing)
tg-invoke-embeddings "hello world"

# Multiple texts
tg-invoke-embeddings "text one" "text two" "text three"

# From file
tg-invoke-embeddings -f texts.txt --batch-size 64
```

#### Fase 6: Melhoria do SDK Python

**FlowInstance (cliente HTTP):**

```python
class FlowInstance:
    def embeddings(self, texts: list[str]) -> list[list[list[float]]]:
        """
        Get embeddings for one or more texts.

        Args:
            texts: List of texts to embed

        Returns:
            List of vector sets, one per input text
        """
        input = {"texts": texts}
        return self.request("service/embeddings", input)["vectors"]
```

**SocketFlowInstance (cliente WebSocket):**

```python
class SocketFlowInstance:
    def embeddings(self, texts: list[str], **kwargs: Any) -> list[list[list[float]]]:
        """
        Get embeddings for one or more texts via WebSocket.

        Args:
            texts: List of texts to embed

        Returns:
            List of vector sets, one per input text
        """
        request = {"texts": texts}
        response = self.client._send_request_sync(
            "embeddings", self.flow_id, request, False
        )
        return response["vectors"]
```

**Exemplos de uso do SDK:**

```python
# Single text
vectors = flow.embeddings(["hello world"])
print(f"Dimensions: {len(vectors[0][0])}")

# Batch embedding
texts = ["text one", "text two", "text three"]
all_vectors = flow.embeddings(texts)

# Process results
for text, vecs in zip(texts, all_vectors):
    print(f"{text}: {len(vecs[0])} dimensions")
```

## Considerações de Segurança

**Limites de Tamanho da Requisição**: Impor o tamanho máximo do lote para evitar o esgotamento de recursos.
**Tratamento de Tempo Limite (Timeout)**: Ajustar os tempos limite de acordo com o tamanho do lote.
**Limites de Memória**: Monitorar o uso de memória para grandes lotes.
**Validação de Entrada**: Validar todos os textos no lote antes do processamento.

## Considerações de Desempenho

### Melhorias Esperadas

**Taxa de Transferência (Throughput):**
Texto único: ~10-50 textos/segundo (dependendo do modelo)
Lote (tamanho 32): ~200-500 textos/segundo (melhora de 5 a 10 vezes)

**Latência por Texto:**
Texto único: 50-200ms por texto
Lote (tamanho 32): 5-20ms por texto (média)

**Melhorias Específicas do Serviço:**

| Serviço | Atual | Em Lote | Melhoria |
|---------|---------|---------|-------------|
| Incorporações de Grafos (50 entidades) | 5-10s | 0,5-1s | 5-10x |
| Incorporações de Linhas (100 textos) | 10-20s | 1-2s | 5-10x |
| Ingestão de Documentos (1000 fragmentos) | 100-200s | 10-30s | 5-10x |

### Parâmetros de Configuração

```python
# Recommended defaults
DEFAULT_BATCH_SIZE = 32
MAX_BATCH_SIZE = 128
BATCH_TIMEOUT_MULTIPLIER = 2.0
```

## Estratégia de Testes

### Testes Unitários
Incorporação de texto única (compatibilidade com versões anteriores)
Tratamento de lotes vazios
Imposição do tamanho máximo do lote
Tratamento de erros para falhas parciais do lote

### Testes de Integração
Incorporação de lote de ponta a ponta através do Pulsar
Processamento de lote do serviço de incorporação de grafos
Processamento de lote do serviço de incorporação de linhas
Endpoint de lote do gateway de API

### Testes de Desempenho
Comparação de benchmark de taxa de transferência única versus lote
Uso de memória sob vários tamanhos de lote
Análise da distribuição de latência

## Plano de Migração

Esta é uma versão que introduz alterações significativas. Todas as fases são implementadas juntas.

### Fase 1: Alterações no Esquema
Substituir `text: str` por `texts: list[str]` em EmbeddingsRequest
Alterar o tipo de `vectors` para `list[list[list[float]]]` em EmbeddingsResponse

### Fase 2: Atualizações do Processador
Atualizar a assinatura de `on_embeddings` nos processadores FastEmbed e Ollama
Processar o lote completo em uma única chamada de modelo

### Fase 3: Atualizações do Cliente
Atualizar `EmbeddingsClient.embed()` para aceitar `texts: list[str]`

### Fase 4: Atualizações do Chamador
Atualizar graph_embeddings para incorporar contextos de entidades em lote
Atualizar row_embeddings para incorporar textos de índice em lote
Atualizar document_embeddings para usar o novo esquema
Atualizar a ferramenta de linha de comando (CLI)

### Fase 5: Gateway de API
Atualizar o endpoint de incorporação para o novo esquema

### Fase 6: SDK Python
Atualizar a assinatura de `FlowInstance.embeddings()`
Atualizar a assinatura de `SocketFlowInstance.embeddings()`

## Perguntas Abertas

**Incorporação de Lotes Grandes em Streaming**: Devemos suportar o streaming de resultados para lotes muito grandes (>100 textos)?
**Limites Específicos do Provedor**: Como devemos lidar com provedores com tamanhos máximos de lote diferentes?
**Tratamento de Falhas Parciais**: Se um texto em um lote falhar, devemos falhar o lote inteiro ou retornar resultados parciais?
**Incorporação em Lote de Documentos**: Devemos incorporar em lote em várias mensagens de Chunk ou manter o processamento por mensagem?

## Referências

[Documentação do FastEmbed](https://github.com/qdrant/fastembed)
[API de Incorporação do Ollama](https://github.com/ollama/ollama)
[Implementação do Serviço de Incorporação](trustgraph-base/trustgraph/base/embeddings_service.py)
[Otimização de Desempenho do GraphRAG](graphrag-performance-optimization.md)
