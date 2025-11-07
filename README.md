
<div align="center">

[![PyPI version](https://img.shields.io/pypi/v/trustgraph.svg)](https://pypi.org/project/trustgraph/) ![E2E Tests](https://github.com/trustgraph-ai/trustgraph/actions/workflows/release.yaml/badge.svg)
[![Discord](https://img.shields.io/discord/1251652173201149994
)](https://discord.gg/sQMwkRz5GX) [![Ask DeepWiki](https://deepwiki.com/badge.svg)](https://deepwiki.com/trustgraph-ai/trustgraph)

[**Docs**](https://docs.trustgraph.ai) | [**YouTube**](https://www.youtube.com/@TrustGraphAI?sub_confirmation=1) | [**Configuration Builder**](https://config-ui.demo.trustgraph.ai/) | [**Discord**](https://discord.gg/sQMwkRz5GX) | [**Blog**](https://blog.trustgraph.ai/subscribe)

<img src="TG-fullname-logo.svg" width=100% />

</div>

# AI-Ready Data Infrastructure

TrustGraph provides an event-driven data-to-AI platform that transforms raw data into AI-ready datasets through automated structuring, knowledge graph construction, and vector embeddings mapping — all deployable privately, on-prem, or in your cloud. Deploy and manage open LLMs within the same platform, ensuring complete data sovereignty while enabling agents that generate real, actionable insights.

<details>
<summary>Table of Contents</summary>
<br>

- [**Key Features**](#key-features)<br>
- [**Why TrustGraph?**](#why-trustgraph)<br>
- [**Agentic MCP Demo**](#agentic-mcp-demo)<br>
- [**Getting Started**](#getting-started)<br>
- [**Configuration Builder**](#configuration-builder)<br>
- [**Knowledge Cores**](#knowledge-cores)<br>
- [**Integrations**](#integrations)<br>
- [**Observability & Telemetry**](#observability--telemetry)<br>
- [**Contributing**](#contributing)<br>
- [**License**](#license)<br>
- [**Support & Community**](#support--community)<br>

</details>

## Key Features

TrustGraph is not just another AI framework but a complete, production-ready platform that bridges the gap between raw data and intelligent, adaptable agent deployments.

- **AI-Ready Data Transformation**

*Convert unstructured and structured (bring your own schema) data into AI-optimized formats*.

- **Automated Knowledge Graph Construction**

*Transform unstructured data into interconnected knowledge graphs that capture relationships, context, and meaning*.

- **Semantic Retrieval**

*TrustGraph combines multiple retrieval methods optimized for each data type and use case*.

- **Event-Driven**

*Built with Apache Pulsar for high-throughput and reliable messaging*.

- **Datastore Orchestration**

*Deploy stores like Apache Cassandra, Neo4j, Qdrant, Milvus, Memgraph, or FalkorDB for structured and unstructured data storage*.

- **Data Sovereignty**

*Deploy the entire stack—data pipelines, knowledge graphs, vector stores, and LLMs—on-premises, in your VPC, or across hybrid environments*.

- **Private LLM Inferencing**

*In addition to support for all major LLM APIs, deploy and manage open models connected to all of the agentic data infrastructure*.

- **Agentic GraphRAG**

*Deploy intelligent agents with context awareness. Bring your own ontology for easy integration into interconnected systems*.

- **Production Ready**

*Containerized deployment with Docker/Kubernetes support. Built for enterprise scale with monitoring, observability, and management*.

- **MCP Integration**

*Native support for MCP enables standardized agent communication with third-party tools and services while maintaining data sovereignty*.

- **Full Stack Visibility**

*3D visualization of knowledge graphs. Grafana dashboard for observability*.

## Why TrustGraph?

[![Why TrustGraph?](https://img.youtube.com/vi/Norboj8YP2M/maxresdefault.jpg)](https://www.youtube.com/watch?v=Norboj8YP2M)

## Agentic MCP Demo

[![Agentic MCP Demo](https://img.youtube.com/vi/mUCL1b1lmbA/maxresdefault.jpg)](https://www.youtube.com/watch?v=mUCL1b1lmbA)

## Getting Started

- [**Quickstart Guide**](https://docs.trustgraph.ai/getting-started/)
- [**Configuration Builder**](#configuration-builder)
- [**Workbench**](#workbench)
- [**Developer APIs and CLI**](https://docs.trustgraph.ai/reference/)
- [**Deployment Guide**](https://docs.trustgraph.ai/deployment/)

### Watch TrustGraph 101

[![TrustGraph 101](https://img.youtube.com/vi/rWYl_yhKCng/maxresdefault.jpg)](https://www.youtube.com/watch?v=rWYl_yhKCng)

## Configuration Builder

The [**Configuration Builder**](https://config-ui.demo.trustgraph.ai/) assembles all of the selected components and builds them into a deployable package. It has 4 sections:

- **Version**: Select the version of TrustGraph you'd like to deploy
- **Component Selection**: Choose from the available deployment platforms, LLMs, graph store, VectorDB, chunking algorithm, chunking parameters, and LLM parameters
- **Customization**: Enable OCR pipelines and custom embeddings models
- **Finish Deployment**: Download the launch `YAML` files with deployment instructions

## Workbench

The **Workbench** is a UI that provides tools for interacting with all major features of the platform. The **Workbench** is enabled by default in the **Configuration Builder** and is available at port `8888` on deployment. The **Workbench** has the following capabilities:

- **Agentic, GraphRAG and LLM Chat**: Chat interface for agentic flows, GraphRAG queries, or directly interfacing with a LLM
- **Semantic Discovery**: Analyze semantic relationships with vector search, knowledge graph relationships, and 3D graph visualization
- **Data Management**: Load data into the **Librarian** for processing, create and upload **Knowledge Packages**
- **Flow Management**: Create and delete processing flow patterns
- **Prompt Management**: Edit all LLM prompts used in the platform during runtime
- **Agent Tools**: Define tools used by the Agent Flow including MCP tools
- **MCP Tools**: Connect to MCP servers

## Knowledge Cores

A challenge facing RAG architectures is the ability to quickly reuse and remove datasets from pipelines. **TrustGraph** stores the results of the data ingestion process in reusable Knowledge Cores. Knowledge cores can be loaded and removed during runtime. Some sample knowledge cores are [here](https://github.com/trustgraph-ai/catalog/tree/master/v3).

A Knowledge Core has two components:

- Knowledge graph triples
- Vector embeddings mapped to the knowledge graph

## Integrations
TrustGraph provides maximum flexibility to avoid vendor lock-in.

<details>
<summary>LLM APIs</summary>
<br>

- Anthropic<br>
- AWS Bedrock<br>
- AzureAI<br>
- AzureOpenAI<br>
- Cohere<br>
- Google AI Studio<br>
- Google VertexAI<br>
- Mistral<br>
- OpenAI<br>

</details>
<details>
<summary>LLM Orchestration</summary>
<br>

- LM Studio<br>
- Llamafiles<br>
- Ollama<br>
- TGI<br>
- vLLM<br>

</details>
<details>
<summary>VectorDBs</summary>
<br>

- Qdrant (default)<br>
- Pinecone<br>
- Milvus<br>

</details>
<details>
<summary>Graph Storage</summary>
<br>

- Apache Cassandra (default)<br>
- Neo4j<br>
- Memgraph<br>
- FalkorDB<br>

</details>
<details>
<summary>Observability</summary>
<br>  

- Prometheus<br>
- Grafana<br>

</details>
<details>
<summary>Control Plane</summary>
<br>

- Apache Pulsar<br>

</details>
<details>
<summary>Clouds</summary>
<br>

- AWS<br>
- Azure<br>
- Google Cloud<br>
- OVHcloud<br>
- Scaleway<br>

</details>

## Observability & Telemetry

Once the platform is running, access the Grafana dashboard at:

```
http://localhost:3000
```

Default credentials are:

```
user: admin
password: admin
```

The default Grafana dashboard tracks the following:

<details>
<summary>Telemetry</summary>
<br>

- LLM Latency<br>
- Error Rate<br>
- Service Request Rates<br>
- Queue Backlogs<br>
- Chunking Histogram<br>
- Error Source by Service<br>
- Rate Limit Events<br>
- CPU usage by Service<br>
- Memory usage by Service<br>
- Models Deployed<br>
- Token Throughput (Tokens/second)<br>
- Cost Throughput (Cost/second)<br>
   
</details>

## Contributing

[Developer's Guide](https://docs.trustgraph.ai/community/developer.html)

## License

**TrustGraph** is licensed under [Apache 2.0](https://www.apache.org/licenses/LICENSE-2.0).

   Copyright 2024-2025 TrustGraph

   Licensed under the Apache License, Version 2.0 (the "License");
   you may not use this file except in compliance with the License.
   You may obtain a copy of the License at

       http://www.apache.org/licenses/LICENSE-2.0

   Unless required by applicable law or agreed to in writing, software
   distributed under the License is distributed on an "AS IS" BASIS,
   WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
   See the License for the specific language governing permissions and
   limitations under the License.

## Support & Community
- Bug Reports & Feature Requests: [Discord](https://discord.gg/sQMwkRz5GX)
- Discussions & Questions: [Discord](https://discord.gg/sQMwkRz5GX)
- Documentation: [Docs](https://docs.trustgraph.ai/)
