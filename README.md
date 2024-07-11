
# TrustGraph

## Introduction

TrustGraph provides a means to run a pipeline of flexible AI processing
components in a flexible means to achieve a processing pipeline.

The processing components are interconnected with a pub/sub engine to
make it easier to switch different procesing components in and out, or
to construct different kinds of processing.  The processing components
do things like, decode documents, chunk text, perform embeddings,
apply a local SLM/LLM, call an LLM API, and invoke LLM predictions.

The processing showcases Graph RAG algorithms which can be used to
produce a knowledge graph from documents, which can then be queried by
a Graph RAG query service.

Processing items are executed in containers.  Processing can be scaled-up
by deploying multiple containers.

### Features

- PDF decoding
- Text chunking
- Invocation of LLMs hosted in Ollama
- Invocation of LLMs: Claude, VertexAI and Azure serverless endpoints
- Application of a HuggingFace embeddings algorithm
- Knowledge graph extraction
- Graph edge loading into Cassandra
- Storing embeddings in Milvus
- Embedding query service
- Graph RAG query service
- All procesing integrates with Apache Pulsar
- Containers, so can be deployed using Docker Compose or Kubernetes
- Plug'n'play, switch different LLM modules to suit your LLM options

## Architecture

![architecture](architecture.png)

A set of modules are executed which use Apache Pulsar as a pub/sub system.
This means that Pulsar provides input the modules and accept output.

Pulsar provides two types of connectivity:
- For processing flows, Pulsar accepts the output of a processing module
  and queues it for input to the next module.
- For services such as LLMs and embeddings, Pulsar provides a client/server
  model.  A Pulsar queue is used as the input to the service.  When
  processed, the output is delivered to a separate queue so that the caller
  can collect the data.

## Included modules

- `chunker-recursive` - Accepts text documents and uses LangChain recurse
  chunking algorithm to produce smaller text chunks.
- `embeddings-hf` - A service which analyses text and returns a vector
  embedding using one of the HuggingFace embeddings models.
- `embeddings-vectorize` - Uses an embeddings service to get a vector
  embedding which is added to the processor payload.
- `graph-rag` - A query service which applies a Graph RAG algorithm to
  provide a response to a text prompt.
- `graph-write-cassandra` - Takes knowledge graph edges and writes them to
  a Cassandra store.
- `kg-extract-definitions` - knowledge extractor - examines text and
  produces graph edges.
  describing discovered terms and also their defintions.  Definitions are
  derived using the input  documents.
- `kg-extract-relationships` - knowledge extractor - examines text and
  produces graph edges describing the relationships between discovered
  terms.
- `llm-azure-text` - An LLM service which uses an Azure serverless endpoint
  to answer prompts.
- `llm-claude-text` - An LLM service which uses Anthropic Claude
  to answer prompts.
- `llm-ollama-text` -  An LLM service which uses an Ollama service to answer
  prompts.
- `llm-vertexai-text` -  An LLM service which uses VertexAI
  to answer prompts.
- `loader` - Takes a document and loads into the processing pipeline.  Used
  e.g. to add PDF documents.
- `pdf-decoder` - Takes a PDF doc and emits text extracted from the document.
  Text extraction from PDF is not a perfect science as PDF is a printable
  format.  For instance, the wrapping of text between lines in a PDF document
  is not semantically encoded, so the decoder will see wrapped lines as
  space-separated.
- `vector-write-milvus` - Takes vector-entity mappings and records them
  in the vector embeddings store.

## Getting started

A good starting point is to try to run one of the Docker Compose files.
This can be run on Linux or a Macbook (maybe Windows - not tested).

There are 4 docker compose files to get you started with one of the
following LLM types:
- VertexAI on Google Cloud
- Claud Anthropic
- Azure serverless endpoint
- An Ollama-hosted LLM for an LLM running on local hardware

Using the Docker Compose you should be able to...
- Run enough components to start a Graph RAG indexing pipeline.  This includes
  stores, LLM interfaces and processing components.
- Check the logs to ensure that things started up correctly
- Load some test data and starting indexing
- Check the graph to see that some data has started to load
- Run a query which uses the vector and graph stores to produce a prompt
  which is answered using an LLM.

If you get a Graph RAG response to the query, everything is working

### Docker compose

TBD

