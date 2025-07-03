# TrustGraph Documentation

Welcome to the TrustGraph documentation. This directory contains comprehensive guides for using TrustGraph's APIs and command-line tools.

## Documentation Overview

### 📚 [API Documentation](apis/README.md)
Complete reference for TrustGraph's APIs, including REST, WebSocket, Pulsar, and Python SDK interfaces. Learn how to integrate TrustGraph services into your applications.

### 🖥️ [CLI Documentation](cli/README.md)
Comprehensive guide to TrustGraph's command-line interface. Includes detailed documentation for all CLI commands, from system administration to knowledge graph management.

### 🚀 [Quick Start Guide](README.quickstart-docker-compose.md)
Step-by-step guide to get TrustGraph running using Docker Compose. Perfect for first-time users who want to quickly deploy and test TrustGraph.

## Getting Started

If you're new to TrustGraph, we recommend starting with the
[Compose - Quick Start Guide](README.quickstart-docker-compose.md)
to get a working system up and running quickly.

For developers integrating TrustGraph into applications, check out the
[API Documentation](apis/README.md) to understand the available interfaces.

For system administrators and power users, the
[CLI Documentation](cli/README.md) provides detailed information about all
command-line tools.

## Ways to deploy

If you haven't deployed TrustGraph before, the 'compose' deployment 
mentioned above is going to be the least commitment of setting things up:
See [Quick Start Guide](README.quickstart-docker-compose.md)

Other deployment mechanisms include:
- [Scaleway Kubernetes deployment using Pulumi](https://github.com/trustgraph-ai/pulumi-trustgraph-scaleway)
- [Intel Gaudi and GPU](https://github.com/trustgraph-ai/trustgraph-tiber-cloud) - tested on Intel Tiber cloud
- [Azure Kubernetes deployment using Pulumi](https://github.com/trustgraph-ai/pulumi-trustgraph-aks)
- [AWS EC2 single instance deployment using Pulumi](https://github.com/trustgraph-ai/pulumi-trustgraph-ec2)
- [GCP GKE cloud deployment using Pulumi](https://github.com/trustgraph-ai/pulumi-trustgraph-gke)
- [RKE Kubernetes on AWS deployment using Pulumi](https://github.com/trustgraph-ai/pulumi-trustgraph-aws-rke)
- It should be possible to deploy on AWS EKS, but we haven't been able to
  script anything reliable so far.

## What is TrustGraph?

TrustGraph is a comprehensive knowledge graph and retrieval-augmented generation (RAG) platform that enables:

- **Knowledge Extraction**: Extract structured knowledge from documents and text
- **Graph RAG**: Advanced retrieval-augmented generation using knowledge graphs
- **Multi-Model Support**: Integration with various AI models (OpenAI, Claude, Ollama, etc.)
- **Scalable Architecture**: Built on Apache Pulsar for high-performance processing
- **Flexible Deployment**: Docker Compose files for various configurations

## Key Features

- **Graph-Based Knowledge Representation**: Store and query knowledge as interconnected graphs
- **Document Processing**: Extract knowledge from PDFs, text files, and other documents
- **Agent-Based Interactions**: Conversational AI with access to knowledge graphs
- **Multi-Modal APIs**: REST, WebSocket, Pulsar, and Python SDK interfaces
- **Comprehensive CLI**: Command-line tools for all operations
- **Monitoring & Observability**: Built-in metrics and monitoring capabilities

## Architecture

TrustGraph consists of several key components:

- **Processing Pipeline**: Document ingestion, chunking, vectorization, and knowledge extraction
- **Storage Systems**: Vector databases, graph databases (Neo4j/Cassandra), and document storage
- **AI Services**: Text completion, embeddings, and specialized processing services
- **API Gateway**: REST and WebSocket interfaces for external integration
- **Message System**: Apache Pulsar for reliable, scalable message processing

## Support

For questions, issues, or contributions:

- **GitHub Issues**: Report bugs and feature requests
- **Documentation**: This documentation covers most use cases
- **Community**: Join discussions and share experiences

## Related Resources

- [TrustGraph GitHub Repository](https://github.com/trustgraph-ai/trustgraph)
- [Docker Hub Images](https://hub.docker.com/u/trustgraph)
- [Example Notebooks](https://github.com/trustgraph-ai/example-notebooks) -
  shows some example use of various APIs.
  

