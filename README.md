<div align="center">

<img src="TG-fullname-logo.svg" width=100% />

[![PyPI version](https://img.shields.io/pypi/v/trustgraph.svg)](https://pypi.org/project/trustgraph/) ![License](https://img.shields.io/badge/license-Apache%202.0-blue) ![E2E Tests](https://github.com/trustgraph-ai/trustgraph/actions/workflows/release.yaml/badge.svg)
[![Discord](https://img.shields.io/discord/1251652173201149994
)](https://discord.gg/kT5dAsaj8v) [![Ask DeepWiki](https://deepwiki.com/badge.svg)](https://deepwiki.com/trustgraph-ai/trustgraph)

[**Launch TrustGraph**](https://config-ui.demo.trustgraph.ai/) | [**Docs**](https://docs.trustgraph.ai) | [**YouTube**](https://www.youtube.com/@TrustGraphAI?sub_confirmation=1) | [**Discord**](https://discord.gg/sQMwkRz5GX) | [**Website**](https://trustgraph.ai) 

### The Context Orchestration Layer for Agentic AI

<a href="https://trendshift.io/repositories/17291" target="_blank"><img src="https://trendshift.io/api/badge/repositories/17291" alt="trustgraph-ai%2Ftrustgraph | Trendshift" style="width: 250px; height: 55px;" width="250" height="55"/></a>

**Open Source · Open Standards · Total Transparency**

[**Request Access to the Playground Preview**](https://docs.google.com/forms/d/e/1FAIpQLSeTnF22ZjUP20FWV--VvS5606x-5cOvnKty6AqcPdtlnPuqbQ/viewform)
</div>

---

[TrustGraph](https://trustgraph.ai) is an open-source context orchestration layer designed to power the next generation of enterprise AI.

AI applications fail without shared context. LLMs are powerful, but without a structured, unified context layer — one that bridges silos, captures complex relationships, and enforces governance — agents hallucinate, violate policies, and produce non-deterministic outcomes.

TrustGraph builds that layer. It uses hypergraphs to turn raw enterprise data into AI-ready context: a unified semantic context layer where agentic outcomes are deterministic and agent behavior is not just traceable, but cryptographically verifiable.

## The Problem: "Common Context Understanding"
To understand why AI struggles in the enterprise, consider Abbott and Costello’s classic ["Who's on First?"](https://www.youtube.com/watch?v=sYOUFGfK4bU) routine.

Abbott explains the baseball lineup: `Who` is on first base, `What` is on second base, and `I Don't Know` is on third base. Costello is driven mad because he assumes Abbott is asking questions rather than stating the names of the players: `Who`, `What`, and `I Don't Know`.

Two agents cannot communicate if they do not share the same context understanding.

## Why Vector Embeddings and Semantic Search Fail Here
If you feed this scenario into a standard RAG pipeline using vector embeddings and semantic similarity, it breaks completely.

If a user asks: "*Who is playing on first base?*"

1. The vector database converts the query into an embedding.
2. Semantic similarity searches for vectors close to "playing," "first base," and "who."
3. Because "Who" is a common pronoun, the embedding space maps it to general inquiries about identity, not the specific name of a baseball player.
4. The LLM retrieves irrelevant documents and hallucinates, failing to understand that "Who" is an entity (a Person), not a question.

Semantic similarity operates on fuzzy, statistical probability. It cannot distinguish between the linguistic usage of a word as a pronoun and its usage as a proper noun within a specific, localized context.

## Why HyperGraphs Solve Context
A HyperGraph, specifically built using standards like RDF and OWL, establishes explicit, unambiguous semantics. It doesn't rely on "guessing" based on word proximity; it relies on defined relationships.

Here is the "Who's on First" routine modeled in RDF with an OWL ontology. By structuring data this way, the LLM knows exactly what "Who" means in this context:

```turtle
@prefix : <http://trustgraph.ai/baseball#> .
@prefix rdf: <http://www.w3.org/1999/02/22-rdf-syntax-ns#> .
@prefix rdfs: <http://www.w3.org/2000/01/rdf-schema#> .
@prefix owl: <http://www.w3.org/2002/07/owl#> .

# Ontology Classes
:Player a owl:Class ;
    rdfs:subClassOf owl:Thing .

:BaseballPosition a owl:Class .

# Object Properties
:playsPosition a owl:ObjectProperty ;
    rdfs:domain :Player ;
    rdfs:range :BaseballPosition .

# Data (The Context)
:Who a :Player ;
    rdfs:label "Who" .

:What a :Player ;
    rdfs:label "What" .

:IDontKnow a :Player ;
    rdfs:label "I Don't Know" .

:FirstBase a :BaseballPosition ;
    rdfs:label "First Base" .

:SecondBase a :BaseballPosition ;
    rdfs:label "Second Base" .

:ThirdBase a :BaseballPosition ;
    rdfs:label "Third Base" .

# The Explicit Relationships
:Who :playsPosition :FirstBase .
:What :playsPosition :SecondBase .
:IDontKnow :playsPosition :ThirdBase .
```

When an agent queries a TrustGraph hypergraph, it uses SPARQL or GraphRAG to traverse these explicit paths. The agent knows that `:Who` is a `:Player` whose `:playsPosition` is `:FirstBase`. Hallucination is eliminated because context is structured, not inferred via probability.

## Going Beyond Traditional Graphs: The Hypergraph
Standard Knowledge Graphs (KGs) are limited to binary relationships (Node A → Node B). Enterprise context is rarely this simple.

TrustGraph leverages [RDF 1.2](https://www.w3.org/TR/rdf12-concepts/) and [Named Graphs](https://en.wikipedia.org/wiki/Named_graph) as [N-Quads](https://en.wikipedia.org/wiki/N-Triples#N-Quads) to achieve a cutting-edge hypergraph architecture. RDF 1.2 introduces the ability to reference entire statements (triples) as nodes themselves. Combining RDF 1.2 with Named Graphs enbables grouping complex, multi-entity events into a single, addressable conceptual unit for true n-ary relationships.

- Standard Knowledge Graph: `Document` → `Author`
- TrustGraph Hypergraph: Connects `Document`, `Author`, `Approving Manager`, `Compliance Policy`, and `Time/Location` Metadata into a single, complex relational event.
- BYOO: TrustGraph allows you to **Bring-Your-Own-Ontology** which can be loaded in [OWL](https://www.w3.org/TR/owl2-rdf-based-semantics/) format. The ontology-enabled hypergraph will use the provided ontology for semantic compliance for all ingested data, dramatically improving agentic accuracy and precision. Ontology-compliant retrieval is automated.

This hyper-relational context is what enables autonomous agents to reason through complex enterprise workflows and governance policies.

## Core Capabilities of the Interoperability Layer
TrustGraph provides the infrastructure to convert raw data into agentic context and manage it at scale.

1. Raw Data to AI-Ready Context
TrustGraph isn't just a graph database; it is a processing engine. It ingests unstructured, raw enterprise data (PDFs, wikis, APIs, databases), extracts entities and relationships using LLMs, and structures them directly into the hypergraph—transforming chaotic data into AI-ready context.

2. Hyperflows: Custom Agents and Workloads
Hyperflows are unique agentic workflows where processing capabilities are chained together. Developers can configure specific LLMs and specific Context Graph access permissions for every step of a workflow. A Hyperflow can route a query from a lightweight local model for classification, to a heavy reasoning model, drawing from different hypergraph collections at each step based on governance rules.

3. Context Management: Workspaces, Collections, and Context Cores
Managing enterprise context requires strict orchestration. TrustGraph provides purpose-built context management features:

- Workspaces: Deep, programmatic data isolation for users, agents, and hyperflows. Ensure that an HR agent cannot read financial data, and multi-tenant data remains strictly compartmentalized.
- Collections: Enterprise knowledge bases aren't just flat files. Manage, partition, and query distinct knowledge bases directly within the hypergraph. Dynamically combine a "Product Specs" collection and a "Support Tickets" collection in real-time for an agent.
- Context Cores: Modular, portable, and reusable units of context. Package domain-specific knowledge into a Context Core and plug it into any agent or workflow. It’s context-as-a-service.

## Agentic Platform Features
Beyond the hypergraph and context management, TrustGraph is built to provide the full agentic stack for enterprise AI.

- Provenance (Real-Time Traceability): TrustGraph captures all event metadata in the hypergraph, providing real-time traceability for every decision an agent makes. If an agent takes an action, you can trace the exact path through the hypergraph that led to that outcome—solving the "black box" problem for enterprise compliance.
- Open LLM Inference Stack: Don't lock your enterprise data behind proprietary API paywalls. TrustGraph includes a built-in LLM inference stack capable of running open-source models on any hardware (Nvidia, AMD, or Intel accelerators), keeping your data and compute entirely within your sovereignty.
- Deployment Flexibility: Enterprise requirements dictate where data lives. TrustGraph can be totally self-hosted (air-gapped on-premise), deployed as Bring-Your-Own-Cloud (BYOC) into your existing VPC, or consumed as a fully managed SaaS.

## TrustGraph vs. Standard Enterprise Context Search

| Capability | Standard Enterprise Search (e.g., Glean) | TrustGraph |
| :--- | :--- | :--- |
| **Core Architecture** | Search indexing over documents/connectors | **Context Interoperability Layer** via Hypergraph |
| **Context Depth** | Document retrieval & vector similarity | **Hyper-relational Context**: N-ary relationships capturing true enterprise events |
| **Context Management** | Basic RBAC tied to SSO | **Workspaces, Collections, & Cores**: Modular, isolated, reusable context units |
| **Agent Orchestration** | Basic Q&A or simple LLM chains | **Hyperflows**: Complex, chained agentic workflows with step-level LLM and graph config |
| **Traceability** | Logs of search queries | **Provenance**: Real-time hypergraph traceability for all agent reasoning |
| **Compute** | API calls to proprietary LLMs | **Open LLM Stack**: Runs open models natively on Nvidia, AMD, or Intel hardware |
| **Deployment** | SaaS only | **Flexible**: Self-hosted, BYOC, or SaaS |
     
## No API Keys Required

How many times have you cloned a repo and opened the `.env.example` to see the dozens of API keys for 3rd party dependencies needed to make the services work? There are only 3 things in TrustGraph that might need an API key:

- 3rd party LLM services like Anthropic, Cohere, Gemini, Mistral, OpenAI, etc.
- 3rd party OCR like Mistral OCR
- The API key *you set* for the TrustGraph API gateway

Everything else is included.
- [x] Managed Multi-model storage in [Cassandra](https://cassandra.apache.org/_/index.html)
- [x] Managed Vector embedding storage in [Qdrant](https://github.com/qdrant/qdrant)
- [x] Managed File and Object storage in [Garage](https://github.com/deuxfleurs-org/garage) (S3 compatible)
- [x] Managed High-speed Pub/Sub messaging fabric with [Pulsar](https://github.com/apache/pulsar) or [RabbitMQ](https://www.rabbitmq.com/)
- [x] Complete LLM inferencing stack for open LLMs with [vLLM](https://github.com/vllm-project/vllm), [TGI](https://github.com/huggingface/text-generation-inference), [Ollama](https://github.com/ollama/ollama), [LM Studio](https://github.com/lmstudio-ai), and [Llamafiles](https://github.com/mozilla-ai/llamafile) 

## Quickstart

No need to clone the repo unless you are building from source. TrustGraph deploys as a set of Docker containers. Configure it on the command line in one step:

```
npx @trustgraph/config
```

The config process will generate an app config that can be run locally with Docker, Podman, or Minikube. The process will output:
- `deploy.zip` with either a `docker-compose.yaml` file for a Docker/Podman or `resources.yaml` for Kubernetes
- Deployment instructions as `INSTALLATION.md`

<p align="center">
  <video src="https://github.com/user-attachments/assets/33434c3c-f586-4610-8bb2-d7b7b586a672"
width="80%" controls></video>
</p>

For a browser based configuration, try the [Configuration Terminal](https://config-ui.demo.trustgraph.ai/). 

## Watch What is a Context HyperGraph?

[![What is a Context Graph?](https://img.youtube.com/vi/gZjlt5WcWB4/maxresdefault.jpg)](https://www.youtube.com/watch?v=gZjlt5WcWB4) 

## Watch Building Agents with a Hypergraph

[![Real Agents from context graphs with TrustGraph](https://img.youtube.com/vi/lmhmrJ7zRE0/maxresdefault.jpg)](https://www.youtube.com/watch?v=lmhmrJ7zRE0)

## Getting Started with TrustGraph

- [**Getting Started Guides**](https://docs.trustgraph.ai/getting-started)
- [**Developer APIs and CLI**](https://docs.trustgraph.ai/reference)
- [**Deployment Guides**](https://docs.trustgraph.ai/deployment)

## TrustGraph UI

<img width="1389" height="961" alt="Image" src="https://github.com/user-attachments/assets/35c9250d-0f01-40cb-9294-1ee8fd9a1b56" />

The UI provides tools for all major features of TrustGraph. The UI deploys on port `8888` by default.

- **Agent Console** — Query your agents directly with streaming responses and live explainability event tracking, so you can watch reasoning unfold in real time
- **GraphRAG View** — Interactive graph RAG queries with a visual explainability DAG and inline provenance display, making it easy to see exactly where answers came from
- **Context Explorer** — An interactive 3D context graph explorer with dynamic graph loading, BFS neighborhood extraction, edge pulse animation, and multiple navigation views
- **Document Ingestion** — A complete upload and submission workflow with page and chunk inspection and document structure browsing
- **Ontology Workbench** — A full ontology editor with class and property trees, OWL/XML and Turtle import/export with round-trip fidelity, circular dependency detection, and safe-delete confirmation dialogs
- **Schema Workbench** — Interactive schema management with list, create, edit, and delete operations including field and index management
- **Prompt Editor** — A dedicated prompt editing workflow

## TypeScript Library for UIs

There are 3 libraries for quick UI integration of TrustGraph services.

- [@trustgraph/client](https://www.npmjs.com/package/@trustgraph/client)
- [@trustgraph/react-state](https://www.npmjs.com/package/@trustgraph/react-state)
- [@trustgraph/react-provider](https://www.npmjs.com/package/@trustgraph/react-provider)

## Contributing

[Developer's Guide](https://docs.trustgraph.ai/guides/building/introduction.html)

## License

**TrustGraph** is licensed under [Apache 2.0](https://www.apache.org/licenses/LICENSE-2.0).

   Copyright 2024-2026 TrustGraph

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
