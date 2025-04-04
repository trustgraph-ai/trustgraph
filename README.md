<img src="TG-horizon-repo.svg" width=100% />

<div align="center">

## Data-to-AI, Simplified.

[![PyPI version](https://img.shields.io/pypi/v/trustgraph.svg)](https://pypi.org/project/trustgraph/) [![Discord](https://img.shields.io/discord/1251652173201149994
)](https://discord.gg/sQMwkRz5GX)

🚀 [Getting Started](https://trustgraph.ai/docs/getstarted) 📺 [YouTube](https://www.youtube.com/@TrustGraphAI?sub_confirmation=1) 🧠 [Knowledge Cores](https://github.com/trustgraph-ai/catalog/tree/master/v3) ⚙️ [API Docs](docs/apis/README.md) 🧑‍💻 [CLI Docs](https://trustgraph.ai/docs/running/cli) 💬 [Discord](https://discord.gg/sQMwkRz5GX) 📖 [Blog](https://blog.trustgraph.ai/subscribe)

</div>

## The AI App Problem: Everything in Between

Building enterprise AI applications is *hard*. You're not just connecting APIs with a protocol - you're wrangling a complex ecosystem:

*   **Data Silos:** Connecting to and managing data from various sources (databases, APIs, files) is a nightmare.
*   **LLM Integration:** Choosing, integrating, and managing different LLMs adds another layer of complexity.
*   **Deployment Headaches:** Deploying, scaling, and monitoring your AI application is a constant challenge.
*   **Knowledge Graph Construction:** Taking raw knowledge and structuring it so it can be efficiently retrieved.
*   **Vector Database Juggling:** Setting up and optimizing a vector database for efficient data retrieval is crucial but complex.
*   **Data Pipelines:** Building robust ETL pipelines to prepare and transform your data is time-consuming.
*   **Data Management:** As your app grows, so does the data meaning storage and retreival becomes much more complex. 
*   **Prompt Engineering:** Building, testing, and deploying prompts for specific use cases.
*   **Reliability:** With every new connection, the complexity ramps up meaning any simple error can bring the entire system crashing down.

## What is TrustGraph?

**TrustGraph removes the biggest headache of building an AI app: connecting and managing all the data, deployments, and models.** As a full-stack platform, TrustGraph simplifies the development and deployment of data-driven AI applications. TrustGraph is a complete solution, handling everything from data ingestion to deployment, so you can focus on building innovative AI experiences.

![architecture](TG-layer-diagram.svg)

## The Stack Layers

- 📄 **Data Ingest**: Bulk ingest documents such as `.pdf`,`.txt`, and `.md`
- 📃 **OCR Pipelines**: OCR documents with PDF decode, Tesseract, or Mistral OCR services
- 🪓 **Adjustable Chunking**: Choose your chunking algorithm and parameters
- 🔁 **No-code LLM Integration**: **Anthropic**, **AWS Bedrock**, **AzureAI**, **AzureOpenAI**, **Cohere**, **Google AI Studio**, **Google VertexAI**, **Llamafiles**, **LM Studio**, **Mistral**, **Ollama**, and **OpenAI**
- 📖 **Automated Knowledge Graph Building**: No need for complex ontologies and manual graph building
- 🔢 **Knowledge Graph to Vector Embeddings Mappings**: Connect knowledge graph enhanced data directly to vector embeddings
- ❔**Natural Language Data Retrieval**: Automatically perform a semantic similiarity search and subgraph extraction for the context of LLM generative responses
- 🧠 **Knowledge Cores**: Modular data sets with semantic relationships that can saved and quickly loaded on demand
- 🤖 **Agent Manager**: Define custom tools used by a ReAct style Agent Manager that fully controls the response flow including the ability to perform Graph RAG requests
- 📚 **Multiple Knowledge Graph Options**: Full integration with **Memgraph**, **FalkorDB**, **Neo4j**, or **Cassandra**
- 🧮 **Multiple VectorDB Options**: Full integration with **Qdrant**, **Pinecone**, or **Milvus**
- 🎛️ **Production-Grade** Reliability, scalability, and accuracy
- 🔍 **Observability and Telemetry**: Get insights into system performance with **Prometheus** and **Grafana**
- 🎻 **Orchestration**: Fully containerized with **Docker** or **Kubernetes**
- 🥞 **Stack Manager**: Control and scale the stack with confidence with **Apache Pulsar**
- ☁️ **Cloud Deployments**: **AWS**, **Azure**, and **Google Cloud**
- 🪴 **Customizable and Extensible**: Tailor for your data and use cases
- 🖥️ **Configuration Builder**: Build the `YAML` configuration with drop down menus and selectable parameters
- 🕵️ **Test Suite**: A simple UI to fully test TrustGraph performance

## Why Use TrustGraph?

*   **Accelerate Development:** TrustGraph instantly connects your data and app, keeping you laser focused on your users.
*   **Reduce Complexity:** Eliminate the pain of integrating disparate tools and technologies.
*   **Focus on Innovation:** Spend your time building your core AI logic, not managing infrastructure.
*   **Improve Data Relevance:** Ensure your LLM has access to the *right* data, at the *right* time.
*   **Scale with Confidence:**  Deploy and scale your AI applications reliably and efficiently.
*   **Full RAG Solution:** Focus on optimizing your respones not building RAG pipelines.

## Quickstart Guide 🚀
- [Install the CLI](#install-the-trustgraph-cli)
- [Configuration Builder](#configuration-builder)
- [System Restarts](#system-restarts)
- [Test Suite](#test-suite)
- [Example Notebooks](#example-trustgraph-notebooks)

## Developer APIs and CLI

- [**REST API**](docs/apis/README.md#rest-apis)
- [**Websocket API**](docs/apis/README.md#websocket-api)
- [**Python SDK**](https://trustgraph.ai/docs/api/apistarted)
- [**TrustGraph CLI**](https://trustgraph.ai/docs/running/cli)

See the [API Developer's Guide](#api-documentation) for more information.

For users, **TrustGraph** has the following interfaces:

- [**Configuration Builder**](#configuration-builder)
- [**Test Suite**](#test-suite)

The `TrustGraph CLI` installs the commands for interacting with TrustGraph while running along with the Python SDK. The `Configuration Builder` enables customization of TrustGraph deployments prior to launching. The **REST API** can be accessed through port `8088` of the TrustGraph host machine with JSON request and response bodies.

### Install the TrustGraph CLI

```
pip3 install trustgraph-cli==0.21.17
```

> [!NOTE]
> The `TrustGraph CLI` version must match the desired `TrustGraph` release version.

## Configuration Builder

TrustGraph is endlessly customizable by editing the `YAML` launch files. The `Configuration Builder` provides a quick and intuitive tool for building a custom configuration that deploys with Docker, Podman, Minikube, or Google Cloud. There is a `Configuration Builder` for the both the lastest and stable `TrustGraph` releases.

- [**Configuration Builder** (Stable 0.21.17) 🚀](https://config-ui.demo.trustgraph.ai/)
- [**Configuration Builder** (Latest 0.21.17) 🚀](https://dev.config-ui.demo.trustgraph.ai/)

The `Configuration Builder` has 4 important sections:

- **Component Selection** ✅: Choose from the available deployment platforms, LLMs, graph store, VectorDB, chunking algorithm, chunking parameters, and LLM parameters
- **Customization** 🧰: Customize the prompts for the LLM System, Data Extraction Agents, and Agent Flow
- **Test Suite** 🕵️: Add the **Test Suite** to the configuration available on port `8888`
- **Finish Deployment** 🚀: Download the launch `YAML` files with deployment instructions

The `Configuration Builder` will generate the `YAML` files in `deploy.zip`. Once `deploy.zip` has been downloaded and unzipped, launching TrustGraph is as simple as navigating to the `deploy` directory and running:

```
docker compose up -d
```

> [!TIP]
> Docker is the recommended container orchestration platform for first getting started with TrustGraph.

When finished, shutting down TrustGraph is as simple as:
```
docker compose down -v
```

## System Restarts

The `-v` flag will destroy all data on shut down. To restart the system, it's necessary to keep the volumes. To keep the volumes, shut down without the `-v` flag:
```
docker compose down
```

With the volumes preserved, restarting the system is as simple as:
```
docker compose up -d
```

All data previously in TrustGraph will be saved and usable on restart.

## Test Suite

If added to the build in the `Configuration Builder`, the `Test Suite` will be available at port `8888`. The `Test Suite` has the following capabilities:

- **Graph RAG Chat** 💬: Graph RAG queries in a chat interface
- **Vector Search** 🔎: Semantic similarity search with cosine similarity scores
- **Semantic Relationships** 🕵️: See semantic relationships in a list structure
- **Graph Visualizer** 🌐: Visualize semantic relationships in **3D**
- **Data Loader** 📂: Directly load `.pdf`, `.txt`, or `.md` into the system with document metadata

## Example TrustGraph Notebooks

- [**REST API Notebooks**](https://github.com/trustgraph-ai/example-notebooks/tree/master/api-examples)
- [**Python SDK Notebooks**](https://github.com/trustgraph-ai/example-notebooks/tree/master/api-library)

## Prebuilt Configuration Files

TrustGraph `YAML` files are available [here](https://github.com/trustgraph-ai/trustgraph/releases). Download `deploy.zip` for the desired release version.

| Release Type | Release Version |
| ------------ | --------------- |
| Latest | [0.21.17](https://github.com/trustgraph-ai/trustgraph/releases/download/v0.21.17/deploy.zip) |
| Stable | [0.21.17](https://github.com/trustgraph-ai/trustgraph/releases/download/v0.21.17/deploy.zip) |

TrustGraph is fully containerized and is launched with a `YAML` configuration file. Unzipping the `deploy.zip` will add the `deploy` directory with the following subdirectories:

- `docker-compose`
- `minikube-k8s`
- `gcp-k8s`

> [!NOTE]
> As more integrations have been added, the number of possible combinations of configurations has become quite large. It is recommended to use the `Configuration Builder` to build your deployment configuration. Each directory contains `YAML` configuration files for the default component selections.

**Docker**:
```
docker compose -f <launch-file.yaml> up -d
```

**Kubernetes**:
```
kubectl apply -f <launch-file.yaml>
```

TrustGraph is designed to be modular to support as many LLMs and environments as possible. A natural fit for a modular architecture is to decompose functions into a set of modules connected through a pub/sub backbone. [Apache Pulsar](https://github.com/apache/pulsar/) serves as this pub/sub backbone. Pulsar acts as the data broker managing data processing queues connected to procesing modules.

### Pulsar Workflows

- For processing flows, Pulsar accepts the output of a processing module and queues it for input to the next subscribed module.
- For services such as LLMs and embeddings, Pulsar provides a client/server model.  A Pulsar queue is used as the input to the service.  When processed, the output is then delivered to a separate queue where a client subscriber can request that output.

## Data Extraction Agents

TrustGraph extracts knowledge documents to an ultra-dense knowledge graph using 3 automonous data extraction agents. These agents focus on individual elements needed to build the knowledge graph. The agents are:

- Topic Extraction Agent
- Entity Extraction Agent
- Relationship Extraction Agent

The agent prompts are built through templates, enabling customized data extraction agents for a specific use case. The data extraction agents are launched automatically with the loader commands.

PDF file:
```
tg-load-pdf <document.pdf>
```

Text or Markdown file:
```
tg-load-text <document.txt>
```

## Graph RAG Queries

Once the knowledge graph and embeddings have been built or a cognitive core has been loaded, RAG queries are launched with a single line:

```
tg-invoke-graph-rag -q "What are the top 3 takeaways from the document?"
```

## Agent Flow

Invoking the Agent Flow will use a ReAct style approach the combines Graph RAG and text completion requests to think through a problem solution.

```
tg-invoke-agent -v -q "Write a blog post on the top 3 takeaways from the document."
```

> [!TIP]
> Adding `-v` to the agent request will return all of the agent manager's thoughts and observations that led to the final response.

## API Documentation

[Developing on TrustGraph using APIs](docs/apis/README.md)

## Deploy and Manage TrustGraph

[🚀🙏 Full Deployment Guide 🚀🙏](https://trustgraph.ai/docs/getstarted)

## TrustGraph Developer's Guide

[Developing for TrustGraph](docs/README.development.md)
