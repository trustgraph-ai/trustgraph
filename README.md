
<div align="center">

<img src="TG-fullname-logo.svg" width=100% />

[![PyPI version](https://img.shields.io/pypi/v/trustgraph.svg)](https://pypi.org/project/trustgraph/) ![E2E Tests](https://github.com/trustgraph-ai/trustgraph/actions/workflows/release.yaml/badge.svg)
[![Discord](https://img.shields.io/discord/1251652173201149994
)](https://discord.gg/sQMwkRz5GX) [![Ask DeepWiki](https://deepwiki.com/badge.svg)](https://deepwiki.com/trustgraph-ai/trustgraph)

[**Website**](https://trustgraph.ai) | [**Docs**](https://docs.trustgraph.ai) | [**YouTube**](https://www.youtube.com/@TrustGraphAI?sub_confirmation=1) | [**Configuration Builder**](https://config-ui.demo.trustgraph.ai/) | [**Discord**](https://discord.gg/sQMwkRz5GX) | [**Blog**](https://blog.trustgraph.ai/subscribe)

</div>

# Data Preparation as the Foundation for AI Accuracy

Build accurate, trustworthy AI agents powered by your own private data. TrustGraph connects your documents, databases, tools, and agents into a unified knowledge graph with precise retrieval, full observability, and deploy-anywhere control.

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

- **Unify your Data for Reliable, Accurate, and Precise AI**
- **Ship Intelligent Agents Powered with Your Data**
- **Connect Your Agents with MCP**
- **Run Anywhere**
- **Observe Your Data**
- **Serve Models for Private LLM Inference**
- **Create Many Workflows**
- **Control Data Access**

## Why TrustGraph?

Ingest structured and unstructured data (PDFs, databases, OCR, custom schemas, and ontologies) into a private knowledge bases to create deep data relationships that eliminate hallucinations from agent responses. Connect agents with the Model Context Protocol (MCP) to leverage external tools, services, and custom workflows.

Deploy all of the services, datastores, and agents locally, on premises, or in cloud. Visualize deep data relationships with 3D GraphViz and a full observability and telemetry stack. Deploy LLMs on your hardware for full control of your data.

Flows and Flow Classes enable unique agent workflows with collections and knowledge cores that manage user and agent data access.

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

The **Workbench** provides tools for all major features of TrustGraph. The **Workbench** is on port `8888` by default.

- **Vector Search**: Search the installed knowledge bases
- **Agentic, GraphRAG and LLM Chat**: Chat interface for agents, GraphRAG queries, or direct to LLMs
- **Relationships**: Analyze deep relationships in the installed knowledge bases
- **Graph Visualizer**: 3D GraphViz of the installed knowledge bases
- **Library**: Staging area for installing knowledge bases
- **Flow Classes**: Workflow preset configurations
- **Flows**: Create custom workflows and adjust LLM parameters during runtime
- **Knowledge Cores**: Manage resuable knowledge bases
- **Prompts**: Manage and adjust prompts during runtime
- **Schemas**: Define custom schemas for structured data knowledge bases
- **Ontologies**: Define custom ontologies for unstructured data knowledge bases
- **Agent Tools**: Define tools with collections, knowledge cores, MCP connections, and tool groups
- **MCP Tools**: Connect to MCP servers

## Knowledge Cores

A challenge facing GraphRAG architectures is the ability to reuse and remove datasets from agent workflows. TrustGraph can store the data ingest process as reusable Knowledge Cores. Knowledge cores can be loaded and removed during runtime. Some sample knowledge cores are [here](https://github.com/trustgraph-ai/catalog/tree/master/v3).

A Knowledge Core has two components:

- Knowledge graph triples
- Vector embeddings mapped to the knowledge graph

## Integrations
TrustGraph provides component flexibility to optimize agent workflows.

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
