
<div align="center">

[![PyPI version](https://img.shields.io/pypi/v/trustgraph.svg)](https://pypi.org/project/trustgraph/) ![E2E Tests](https://github.com/trustgraph-ai/trustgraph/actions/workflows/release.yaml/badge.svg)
[![Discord](https://img.shields.io/discord/1251652173201149994
)](https://discord.gg/sQMwkRz5GX) [![Ask DeepWiki](https://deepwiki.com/badge.svg)](https://deepwiki.com/trustgraph-ai/trustgraph)

[**Docs**](https://docs.trustgraph.ai) | [**YouTube**](https://www.youtube.com/@TrustGraphAI?sub_confirmation=1) | [**Configuration Builder**](https://config-ui.demo.trustgraph.ai/) | [**Discord**](https://discord.gg/sQMwkRz5GX) | [**Blog**](https://blog.trustgraph.ai/subscribe)

<img src="TG-fullname-logo.svg" width=100% />

</div>

# AI-Ready Data Infrastructure

TrustGraph provides an event-driven data-to-AI platform that automatically transforms raw data into AI-ready datasets through automated structuring, knowledge graph construction, and vector embeddings—all deployable privately, on-prem, or in your cloud. You can deploy and manage your own LLMs within the same platform, ensuring your data never leaves your infrastructure while enabling agents that generate real, actionable insights.

<details>
<summary>Table of Contents</summary>
<br>

- [**Key Features**](#key-features)<br>
- [**Why TrustGraph?**](#why-trustgraph)<br>
- [**Agentic MCP Demo**](#agentic-mcp-demo)<br>
- [**Getting Started**](#getting-started)<br>
- [**Configuration Builder**](#configuration-builder)<br>
- [**Context Engineering**](#context-engineering)<br>
- [**Knowledge Cores**](#knowledge-cores)<br>
- [**Integrations**](#integrations)<br>
- [**Observability & Telemetry**](#observability--telemetry)<br>
- [**Contributing**](#contributing)<br>
- [**License**](#license)<br>
- [**Support & Community**](#support--community)<br>

</details>

## Key Features

TrustGraph is not just another AI framework but a comprehensive context stack that bridges the gap between raw data and intelligent, adaptable agent deployments in production environments.

- **Complete Agentic Context Stack**
   - Combines all necessary layers: data streaming control plane, knowledge graphs, vector databases, LLM integrations, and data pipelines in a unified platform.
   - Enables deployment of intelligent agents grounded in domain-specific knowledge.
- **Post-Training Infrastructure**
   - Supports transforming raw and streaming data into knowledge representations for fine-tuning and in-context agent reasoning.
   - Enables continuous learning and optimization of AI agents beyond base model training.
- **Containerized Single Deployment**
   - Simplifies operations with a turnkey containerized solution.
   - Eliminates the complexity of managing multiple, disparate components and dependencies.
- **Multi-Cloud and Local Run Support**
   - Runs anywhere—locally, on-premises, or in any cloud environment (AWS, Azure, GCP, OVHcloud, Scaleway).
   - Supports data sovereignty and flexible deployment architectures.
- **Flexible Data and Model Integrations**
   - Supports multiple vector databases (Qdrant, Milvus, Pinecone) and knowledge graph stores (Neo4j, Memgraph, FalkorDB).
   - Native integration with LLM providers Anthropic, Google, Mistral, OpenAI, and local models with vLLM, Ollama, LM Studio.
- **Real-Time Data Streaming and Observability**
   - Built-in streaming data integration with Apache Pulsar.
   - Observability tooling including Prometheus and Grafana dashboards for tracking latency, costs, and system health.
- **Modular and Extensible Architecture**
   - Swap or extend parts (e.g., vector stores, LLMs, graph databases) without platform redesign.
   - Built for engineers who need flexibility and control over AI infrastructure components.
- **Domain Knowledge as a First-Class Citizen**
   - Converts data into rich knowledge graphs to ground AI agents in reliable, structured information.
   - Enables semantic retrieval for more accurate and context-aware AI responses.

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

## Context Engineering

TrustGraph features a complete context engineering solution combinging the power of Knowledge Graphs and VectorDBs. Connect your data to automatically construct Knowledge Graphs with mapped Vector Embeddings to deliver richer and more accurate context to LLMs for trustworthy agents.

- **Automated Knowledge Graph Construction:** Data Transformation Agents processes source data to automatically **extract key entities, topics, and the relationships** connecting them. Vector emebeddings are then mapped to these semantic relationships for context retrieval.
- **Deterministic Graph Retrieval:** Semantic relationsips are retrieved from the knowledge graph *without* the use of LLMs. When an agent needs to perform deep research, it first performs a **cosine similarity search** on the vector embeddings to identify potentially relevant concepts and relationships within the knowledge graph. This initial vector search **pinpoints relevant entry points** within the structured Knowledge Graph which gets built into graph queries *without* LLMs that retrieve the relevant subgraphs.
- **Context Generation via Subgraph Traversal:** Based on the ranked results from the similarity search, agents are provided with only the relevant subgraphs for **deep context**. Users can configure the **number of 'hops'** (relationship traversals) to extend the depth of knowledge availabe to the agents. This structured **subgraph**, containing entities and their relationships, forms a highly relevant and context-aware input prompt for the LLM that is endlessly configurable with options for the number of entities, relationships, and overall subgraph size.

## Knowledge Cores

One of the biggest challenges currently facing RAG architectures is the ability to quickly reuse and integrate knowledge sets like long-term memory for LLMs. **TrustGraph** solves this problem by storing the results of the data ingestion process in reusable Knowledge Cores. Being able to store and reuse the Knowledge Cores means the data transformation process has to be run only once. These reusable Knowledge Cores can be loaded back into **TrustGraph** and used for GraphRAG. Some sample knowledge cores are available for download [here](https://github.com/trustgraph-ai/catalog/tree/master/v3).

A Knowledge Core has two components:

- Set of Graph Edges
- Set of mapped Vector Embeddings

When a Knowledge Core is loaded into TrustGraph, the corresponding graph edges and vector embeddings are queued and loaded into the chosen graph and vector stores.

## Integrations
TrustGraph provides maximum flexibility so your agents are always powered by the latest and greatest components.

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
