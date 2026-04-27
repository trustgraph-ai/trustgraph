---
layout: default
title: "Embeddings Batch Processing Technical Specification"
parent: "Tech Specs"
---

# Embeddings Batch Processing Technical Specification

## Overview

This specification describes optimizations for the embeddings service to support batch processing of multiple texts in a single request. The current implementation processes one text at a time, missing the significant performance benefits that embedding models provide when processing batches.

1. **Single-Text Processing Inefficiency**: Current implementation wraps single texts in a list, underutilizing FastEmbed's batch capabilities
2. **Request-Per-Text Overhead**: Each text requires a separate Pulsar message round-trip
3. **Model Inference Inefficiency**: Embedding models have fixed per-batch overhead; small batches waste GPU/CPU resources
4. **Serial Processing in Callers**: Key services loop over items and call embeddings one at a time

## Goals

- **Batch API Support**: Enable processing multiple texts in a single request
- **Backward Compatibility**: Maintain support for single-text requests
- **Significant Throughput Improvement**: Target 5-10x throughput improvement for bulk operations
- **Reduced Latency per Text**: Lower amortized latency when embedding multiple texts
- **Memory Efficiency**: Process batches without excessive memory consumption
- **Provider Agnostic**: Support batching across FastEmbed, Ollama, and other providers
- **Caller Migration**: Update all embedding callers to use batch API where beneficial

## Background

### Current Implementation - Embeddings Service

The embeddings implementation in `trustgraph-flow/trustgraph/embeddings/fastembed/processor.py` exhibits a significant performance inefficiency:

```python
# fastembed/processor.py line 56
async def on_embeddings(self, text, model=None):
    use_model = model or self.default_model
    self._load_model(use_model)

    vecs = self.embeddings.embed([text])  # Single text wrapped in list

    return [v.tolist() for v in vecs]
```

**Problems:**

1. **Batch Size 1**: FastEmbed's `embed()` method is optimized for batch processing, but we always call it with `[text]` - a batch of size 1

2. **Per-Request Overhead**: Each embedding request incurs:
   - Pulsar message serialization/deserialization
   - Network round-trip latency
   - Model inference startup overhead
   - Python async scheduling overhead

3. **Schema Limitation**: The `EmbeddingsRequest` schema only supports a single text:
   ```python
   @dataclass
   class EmbeddingsRequest:
       text: str = ""  # Single text only
   ```

### Current Callers - Serial Processing

#### 1. API Gateway

**File:** `trustgraph-flow/trustgraph/gateway/dispatch/embeddings.py`

The gateway accepts single-text embedding requests via HTTP/WebSocket and forwards them to the embeddings service. Currently no batch endpoint exists.

```python
class EmbeddingsRequestor(ServiceRequestor):
    # Handles single EmbeddingsRequest -> EmbeddingsResponse
    request_schema=EmbeddingsRequest,  # Single text only
    response_schema=EmbeddingsResponse,
```

**Impact:** External clients (web apps, scripts) must make N HTTP requests to embed N texts.

#### 2. Document Embeddings Service

**File:** `trustgraph-flow/trustgraph/embeddings/document_embeddings/embeddings.py`

Processes document chunks one at a time:

```python
async def on_message(self, msg, consumer, flow):
    v = msg.value()

    # Single chunk per request
    resp = await flow("embeddings-request").request(
        EmbeddingsRequest(text=v.chunk)
    )
    vectors = resp.vectors
```

**Impact:** Each document chunk requires a separate embedding call. A document with 100 chunks = 100 embedding requests.

#### 3. Graph Embeddings Service

**File:** `trustgraph-flow/trustgraph/embeddings/graph_embeddings/embeddings.py`

Loops over entities and embeds each one serially:

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

**Impact:** A message with 50 entities = 50 serial embedding requests. This is a major bottleneck during knowledge graph construction.

#### 4. Row Embeddings Service

**File:** `trustgraph-flow/trustgraph/embeddings/row_embeddings/embeddings.py`

Loops over unique texts and embeds each one serially:

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

**Impact:** Processing a table with 100 unique indexed values = 100 serial embedding requests.

#### 5. EmbeddingsClient (Base Client)

**File:** `trustgraph-base/trustgraph/base/embeddings_client.py`

The client used by all flow processors only supports single-text embedding:

```python
class EmbeddingsClient(RequestResponse):
    async def embed(self, text, timeout=30):
        resp = await self.request(
            EmbeddingsRequest(text=text),  # Single text
            timeout=timeout
        )
        return resp.vectors
```

**Impact:** All callers using this client are limited to single-text operations.

#### 6. Command-Line Tools

**File:** `trustgraph-cli/trustgraph/cli/invoke_embeddings.py`

CLI tool accepts single text argument:

```python
def query(url, flow_id, text, token=None):
    result = flow.embeddings(text=text)  # Single text
    vectors = result.get("vectors", [])
```

**Impact:** Users cannot batch-embed from command line. Processing a file of texts requires N invocations.

#### 7. Python SDK

The Python SDK provides two client classes for interacting with TrustGraph services. Both only support single-text embedding.

**File:** `trustgraph-base/trustgraph/api/flow.py`

```python
class FlowInstance:
    def embeddings(self, text):
        """Get embeddings for a single text"""
        input = {"text": text}
        return self.request("service/embeddings", input)["vectors"]
```

**File:** `trustgraph-base/trustgraph/api/socket_client.py`

```python
class SocketFlowInstance:
    def embeddings(self, text: str, **kwargs: Any) -> Dict[str, Any]:
        """Get embeddings for a single text via WebSocket"""
        request = {"text": text}
        return self.client._send_request_sync(
            "embeddings", self.flow_id, request, False
        )
```

**Impact:** Python developers using the SDK must loop over texts and make N separate API calls. No batch embedding support exists for SDK users.

### Performance Impact

For typical document ingestion (1000 text chunks):
- **Current**: 1000 separate requests, 1000 model inference calls
- **Batched (batch_size=32)**: 32 requests, 32 model inference calls (96.8% reduction)

For graph embedding (message with 50 entities):
- **Current**: 50 serial await calls, ~5-10 seconds
- **Batched**: 1-2 batch calls, ~0.5-1 second (5-10x improvement)

FastEmbed and similar libraries achieve near-linear throughput scaling with batch size up to hardware limits (typically 32-128 texts per batch).

## Technical Design

### Architecture

The embeddings batch processing optimization requires changes to the following components:

#### 1. **Schema Enhancement**
   - Extend `EmbeddingsRequest` to support multiple texts
   - Extend `EmbeddingsResponse` to return multiple vector sets
   - Maintain backward compatibility with single-text requests

   Module: `trustgraph-base/trustgraph/schema/services/llm.py`

#### 2. **Base Service Enhancement**
   - Update `EmbeddingsService` to handle batch requests
   - Add batch size configuration
   - Implement batch-aware request handling

   Module: `trustgraph-base/trustgraph/base/embeddings_service.py`

#### 3. **Provider Processor Updates**
   - Update FastEmbed processor to pass full batch to `embed()`
   - Update Ollama processor to handle batches (if supported)
   - Add fallback sequential processing for providers without batch support

   Modules:
   - `trustgraph-flow/trustgraph/embeddings/fastembed/processor.py`
   - `trustgraph-flow/trustgraph/embeddings/ollama/processor.py`

#### 4. **Client Enhancement**
   - Add batch embedding method to `EmbeddingsClient`
   - Support both single and batch APIs
   - Add automatic batching for large inputs

   Module: `trustgraph-base/trustgraph/base/embeddings_client.py`

#### 5. **Caller Updates - Flow Processors**
   - Update `graph_embeddings` to batch entity contexts
   - Update `row_embeddings` to batch index texts
   - Update `document_embeddings` if message batching is feasible

   Modules:
   - `trustgraph-flow/trustgraph/embeddings/graph_embeddings/embeddings.py`
   - `trustgraph-flow/trustgraph/embeddings/row_embeddings/embeddings.py`
   - `trustgraph-flow/trustgraph/embeddings/document_embeddings/embeddings.py`

#### 6. **API Gateway Enhancement**
   - Add batch embedding endpoint
   - Support array of texts in request body

   Module: `trustgraph-flow/trustgraph/gateway/dispatch/embeddings.py`

#### 7. **CLI Tool Enhancement**
   - Add support for multiple texts or file input
   - Add batch size parameter

   Module: `trustgraph-cli/trustgraph/cli/invoke_embeddings.py`

#### 8. **Python SDK Enhancement**
   - Add `embeddings_batch()` method to `FlowInstance`
   - Add `embeddings_batch()` method to `SocketFlowInstance`
   - Support both single and batch APIs for SDK users

   Modules:
   - `trustgraph-base/trustgraph/api/flow.py`
   - `trustgraph-base/trustgraph/api/socket_client.py`

### Data Models

#### EmbeddingsRequest

```python
@dataclass
class EmbeddingsRequest:
    texts: list[str] = field(default_factory=list)
```

Usage:
- Single text: `EmbeddingsRequest(texts=["hello world"])`
- Batch: `EmbeddingsRequest(texts=["text1", "text2", "text3"])`

#### EmbeddingsResponse

```python
@dataclass
class EmbeddingsResponse:
    error: Error | None = None
    vectors: list[list[list[float]]] = field(default_factory=list)
```

Response structure:
- `vectors[i]` contains the vector set for `texts[i]`
- Each vector set is `list[list[float]]` (models may return multiple vectors per text)
- Example: 3 texts → `vectors` has 3 entries, each containing that text's embeddings

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

#### API Gateway Embeddings Endpoint

Updated endpoint supporting single or batch embedding:

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

### Implementation Details

#### Phase 1: Schema Changes

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

**Updated EmbeddingsService.on_request:**
```python
async def on_request(self, msg, consumer, flow):
    request = msg.value()
    id = msg.properties()["id"]
    model = flow("model")

    vectors = await self.on_embeddings(request.texts, model=model)
    response = EmbeddingsResponse(error=None, vectors=vectors)

    await flow("response").send(response, properties={"id": id})
```

#### Phase 2: FastEmbed Processor Update

**Current (Inefficient):**
```python
async def on_embeddings(self, text, model=None):
    use_model = model or self.default_model
    self._load_model(use_model)
    vecs = self.embeddings.embed([text])  # Batch of 1
    return [v.tolist() for v in vecs]
```

**Updated:**
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

#### Phase 3: Graph Embeddings Service Update

**Current (Serial):**
```python
async def on_message(self, msg, consumer, flow):
    entities = []
    for entity in v.entities:
        vectors = await flow("embeddings-request").embed(text=entity.context)
        entities.append(EntityEmbeddings(...))
```

**Updated (Batch):**
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

#### Phase 4: Row Embeddings Service Update

**Current (Serial):**
```python
for text, (index_name, index_value) in texts_to_embed.items():
    vectors = await flow("embeddings-request").embed(text=text)
    embeddings_list.append(RowIndexEmbedding(...))
```

**Updated (Batch):**
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

#### Phase 5: CLI Tool Enhancement

**Updated CLI:**
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

Usage:
```bash
# Single text (existing)
tg-invoke-embeddings "hello world"

# Multiple texts
tg-invoke-embeddings "text one" "text two" "text three"

# From file
tg-invoke-embeddings -f texts.txt --batch-size 64
```

#### Phase 6: Python SDK Enhancement

**FlowInstance (HTTP client):**

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

**SocketFlowInstance (WebSocket client):**

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

**SDK Usage Examples:**

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

## Security Considerations

- **Request Size Limits**: Enforce maximum batch size to prevent resource exhaustion
- **Timeout Handling**: Scale timeouts appropriately for batch size
- **Memory Limits**: Monitor memory usage for large batches
- **Input Validation**: Validate all texts in batch before processing

## Performance Considerations

### Expected Improvements

**Throughput:**
- Single-text: ~10-50 texts/second (depending on model)
- Batch (size 32): ~200-500 texts/second (5-10x improvement)

**Latency per Text:**
- Single-text: 50-200ms per text
- Batch (size 32): 5-20ms per text (amortized)

**Service-Specific Improvements:**

| Service | Current | Batched | Improvement |
|---------|---------|---------|-------------|
| Graph Embeddings (50 entities) | 5-10s | 0.5-1s | 5-10x |
| Row Embeddings (100 texts) | 10-20s | 1-2s | 5-10x |
| Document Ingestion (1000 chunks) | 100-200s | 10-30s | 5-10x |

### Configuration Parameters

```python
# Recommended defaults
DEFAULT_BATCH_SIZE = 32
MAX_BATCH_SIZE = 128
BATCH_TIMEOUT_MULTIPLIER = 2.0
```

## Testing Strategy

### Unit Testing
- Single text embedding (backward compatibility)
- Empty batch handling
- Maximum batch size enforcement
- Error handling for partial batch failures

### Integration Testing
- End-to-end batch embedding through Pulsar
- Graph embeddings service batch processing
- Row embeddings service batch processing
- API gateway batch endpoint

### Performance Testing
- Benchmark single vs batch throughput
- Memory usage under various batch sizes
- Latency distribution analysis

## Migration Plan

This is a breaking change release. All phases are implemented together.

### Phase 1: Schema Changes
- Replace `text: str` with `texts: list[str]` in EmbeddingsRequest
- Change `vectors` type to `list[list[list[float]]]` in EmbeddingsResponse

### Phase 2: Processor Updates
- Update `on_embeddings` signature in FastEmbed and Ollama processors
- Process full batch in single model call

### Phase 3: Client Updates
- Update `EmbeddingsClient.embed()` to accept `texts: list[str]`

### Phase 4: Caller Updates
- Update graph_embeddings to batch entity contexts
- Update row_embeddings to batch index texts
- Update document_embeddings to use new schema
- Update CLI tool

### Phase 5: API Gateway
- Update embeddings endpoint for new schema

### Phase 6: Python SDK
- Update `FlowInstance.embeddings()` signature
- Update `SocketFlowInstance.embeddings()` signature

## Open Questions

- **Streaming Large Batches**: Should we support streaming results for very large batches (>100 texts)?
- **Provider-Specific Limits**: How should we handle providers with different maximum batch sizes?
- **Partial Failure Handling**: If one text in a batch fails, should we fail the entire batch or return partial results?
- **Document Embeddings Batching**: Should we batch across multiple Chunk messages or keep per-message processing?

## References

- [FastEmbed Documentation](https://github.com/qdrant/fastembed)
- [Ollama Embeddings API](https://github.com/ollama/ollama)
- [EmbeddingsService Implementation](trustgraph-base/trustgraph/base/embeddings_service.py)
- [GraphRAG Performance Optimization](graphrag-performance-optimization.md)
