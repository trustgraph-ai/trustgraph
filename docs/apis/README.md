
# TrustGraph APIs

## Overview

If you want to interact with TrustGraph through APIs, there are 3
forms of API which may be of interest to you:

### Pulsar APIs

Apache Pulsar is a pub/sub system used to deliver messages between TrustGraph
components. Using Pulsar, you can communicate with TrustGraph components.

Pros:
  - Provides complete access to all TrustGraph functionality
  - Simple integration with metrics and observability

Cons:
  - Integration is non-trivial, requires a special-purpose Pulsar client
    library
  - The Pulsar interfaces are likely something that you would not want to
    expose outside of the processing cluster in a production or well-secured
    deployment
    
### REST APIs

A component, `api-gateway`, provides a bridge between Pulsar internals and
the REST API which allows many services to be invoked using REST APIs.

Pros:
  - Uses standard REST approach can be easily integrated into many kinds
    of technology
  - Can be easily protected with authentication and TLS for production-grade
    or secure deployments

Cons:
  - For a complex application, a long series of REST invocations has
    latency and performance overheads - HTTP has limits on the number
    of concurrent service invocations
  - Lower coverage of functionality - service interfaces need to be added to
    `api-gateway` to permit REST invocation

### Websocket API

The `api-gateway` component also provides access to services through a
websocket API.

Pros:
  - Usable through a standard websocket library
  - Can be easily protected with authentication and TLS for production-grade
    or secure deployments
  - Supports concurrent service invocations

Cons:
  - Websocket service invocation is a little more complex to develop than
    using a basic REST API, particular if you want to cover all of the error
    scenarios well

## See also

- [TrustGraph websocket overview](websocket.md)
- [TrustGraph Pulsar overview](pulsar.md)
- API details
  - [Text completion](api-text-completion.md)
  - [Prompt completion](api-prompt.md)
  - [Graph RAG](api-graph-rag.md)
  - [Agent](api-agent.md)
  - [Embeddings](api-embeddings.md)
  - [Graph embeddings](api-graph-embeddings.md)
  - [Triples query](api-triples-query.md)
  - [Document load](api-document-load.md)

