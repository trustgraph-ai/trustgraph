
# TrustGraph

## Introduction

TrustGraph is a true end-to-end (e2e) knowledge pipeline that performs a `naive extraction` on a text corpus
to build a RDF style knowledge graph coupled with a `RAG` service compatible with cloud LLMs and open-source
SLMs (Small Language Models).

The pipeline processing components are interconnected with a pub/sub engine to
maximize modularity and enable new knowledge processing functions. The core processing components decode documents, 
chunk text, perform embeddings, apply a local SLM/LLM, call a LLM API, and generate LM predictions.

The processing showcases the reliability and efficiences of Graph RAG algorithms which can capture
contextual language flags that are missed in conventional RAG approaches. Graph querying algorithms enable retrieving
not just relevant knowledge but language cues essential to understanding semantic uses unique to a text corpus.

Processing modules are executed in containers.  Processing can be scaled-up
by deploying multiple containers.

### Features

- PDF decoding
- Text chunking
- Inference of LMs deployed with [Ollama](https://ollama.com)
- Inference of LLMs: Claude, VertexAI and AzureAI serverless endpoints
- Application of a [HuggingFace](https://hf.co) embeddings models
- [RDF](https://www.w3.org/TR/rdf12-schema/)-aligned Knowledge Graph extraction
- Graph edge loading into [Apache Cassandra](https://github.com/apache/cassandra)
- Storing embeddings in [Milvus](https://github.com/milvus-io/milvus)
- Embedding query service
- Graph RAG query service
- All procesing integrates with [Apache Pulsar](https://github.com/apache/pulsar/)
- Containers, so can be deployed using Docker Compose or Kubernetes
- Plug'n'play architecture: switch different LLM modules to suit your needs

## Architecture

![architecture](architecture.png)

TrustGraph is designed to be modular to support as many Language Models and environments as possible. A natural
fit for a modular architecture is to decompose functions into a set modules connected through a pub/sub backbone.
[Apache Pulsar](https://github.com/apache/pulsar/) serves as this pub/sub backbone. Pulsar acts as the data broker
managing inputs and outputs between modules.

**Pulsar Workflows**:
- For processing flows, Pulsar accepts the output of a processing module
  and queues it for input to the next subscribed module.
- For services such as LLMs and embeddings, Pulsar provides a client/server
  model.  A Pulsar queue is used as the input to the service.  When
  processed, the output is then delivered to a separate queue where a client
  subscriber can request that output.

The entire architecture, the pub/sub backbone and set of modules, is bundled into a single Python. A container image with the
package installed can also run the entire architecture.

## Core Modules

- `chunker-recursive` - Accepts text documents and uses LangChain recursive
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
- `loader` - Takes a document and loads into the processing pipeline.  Used
  e.g. to add PDF documents.
- `pdf-decoder` - Takes a PDF doc and emits text extracted from the document.
  Text extraction from PDF is not a perfect science as PDF is a printable
  format.  For instance, the wrapping of text between lines in a PDF document
  is not semantically encoded, so the decoder will see wrapped lines as
  space-separated.
- `vector-write-milvus` - Takes vector-entity mappings and records them
  in the vector embeddings store.

## LM Specific Modules

- `llm-azure-text` - Sends request to AzureAI serverless endpoint
- `llm-claude-text` - Sends request to Anthropic's API
- `llm-ollama-text` -  Sends request to LM running using Ollama
- `llm-vertexai-text` -  Sends request to model available through VertexAI API

## Getting Started

The `Docker Compose` files have been tested on `Linux` and `MacOS`. There are currently
no plans for `Windows` support in the immediate future.

There are 4 `Docker Compose` files depending on the desired LM deployment:
- `VertexAI` through Google Cloud
- `Claude` through Anthropic's API
- `AzureAI` serverless endpoint
- Local LM deployment through `Ollama`

Docker Compose enables the following functions:
- Run the required components for full e2e `Graph RAG` knowledge pipeline
- Check processing logs
- Load test text corpus and begin knowledge extraction
- Verify extracted graph edges and number of edges
- Run a query against the vector and graph stores to generate a response
  using the chosen LM

### Clone the Repo

```
git clone https://github.com/trustgraph-ai/trustgraph trustgraph
cd trustgraph
```

### Install requirements

```
python3 -m venv env
. env/bin/activate
pip3 install pulsar-client
pip3 install cassandra-driver
export PYTHON_PATH=.
```

### Docker Compose files

Depending on your desired LM deployment, you will choose from one of the 
following `Docker Compose` files:

- `docker-compose-azure.yaml`: AzureAI endpoint. Set `AZURE_TOKEN` to the secret token and
  `AZURE_ENDPOINT` to the URL endpoint address for the deployed model.
- `docker-compose-claude.yaml`: Anthropic's API. Set `CLAUDE_KEY` to your API key.
- `docker-compose-ollama.yaml`: Local LM (currently using [Gemma2](https://ollama.com/library/gemma2) deployed through Ollama.  Set `OLLAMA_HOST` to the machine running Ollama (e.g. `localhost` for Ollama running locally on your machine)
- `docker-compose-vertexai.yaml`: VertexAI API. Requires a `private.json` authentication file to authenticate with your GCP project. Filed should stored be at path `vertexai/private.json`.

**NOTE**: All tokens, paths, and authentication files must be set **PRIOR** to launching a `Docker Compose` file.


#### AzureAI Serverless Model Deployment

```
export AZURE_ENDPOINT=https://ENDPOINT.HOST.GOES.HERE/
export AZURE_TOKEN=TOKEN-GOES-HERE
docker-compose -f docker-compose-azure.yaml up -d
```

#### Claude through Anthropic API

```
export CLAUDE_KEY=TOKEN-GOES-HERE
docker-compose -f docker-compose-claude.yaml up -d
```

#### Ollama Hosted Model Deployment

```
export OLLAMA_HOST=localhost # Set to hostname of Ollama host
docker-compose -f docker-compose-ollama.yaml up -d
```

#### VertexAI through GCP

```
mkdir -p vertexai
cp {whatever} vertexai/private.json
docker-compose -f docker-compose-vertexai.yaml up -d
```

If you're running `SELinux` on Linux you may need to set the permissions on the
VertexAI directory so that the key file can be mounted on a Docker container using
the following command:

```
chcon -Rt svirt_sandbox_file_t vertexai/
```

### Verify Docker Containers

On first running a `Docker Compose` file, it may take a while (depending on your network connection) to pull all the necessary components. Once all of the components have been pulled, check that the TrustGraph containers are running:

```
docker ps
```

Any containers that have exited unexpectedly can be found by checking the `STATUS` field
using the following:

```
docker ps -a
```

### Warm-Up

Before proceeding, allow the system to enter a stable a working state. In general
`30 seconds` should be enough time for Pulsar to stablize.

The system uses Cassandra for a Graph store. Cassandra can take `60-70 seconds`
to achieve a working state.

### Load a Text Corpus

Create a sources directory and get a test PDF file. To demonstrate the power of TrustGraph, we're using a PDF
of the [Roger's Commision Report](https://sma.nasa.gov/SignificantIncidents/assets/rogers_commission_report.pdf) from the NASA Challenger disaster. This PDF includes
complex formatting, extremely unique terms, complex concepts, unique concepts, and knowledge not commonly found in typical public knowledge sources.

```
mkdir sources
curl -o sources/Challenger-Report-Vol1.pdf https://sma.nasa.gov/SignificantIncidents/assets/rogers_commission_report.pdf
```

Load the file for knowledge extraction:

```
scripts/loader -f sources/Challenger-Report-Vol1.pdf
```

`File loaded.` indicates the PDF has been sucessfully loaded to the processing queues and extraction will begin.

### Processing Logs

At this point, many processing services are running concurrently. You can check the status of these processes with the following logs:

`PDF Decoder`:
```
docker logs trustgraph-pdf-decoder-1
```

Output should look:
```
Decoding 1f7b7055...
Done.
```

`Chunker`:
```
docker logs trustgraph-chunker-1
```

The output should be similiar to the output of the `Decode`, except it should be a sequence of many entries.

`Vectorizer`:
```
docker logs trustgraph-vectorize-1
```

Similar output to above processes, except many entries instead.


`Language Model Inference`:
```
docker logs trustgraph-llm-1
```

Output should be a sequence of entries:
```
Handling prompt fa1b98ae-70ef-452b-bcbe-21a867c5e8e2...
Send response...
Done.
```

`Knowledge Graph Definitions`:
```
docker logs trustgraph-kg-extract-definitions-1
```

Output should be an array of JSON objects with keys `entity` and `definition`:

```
Indexing 1f7b7055-p11-c1...
[
    {
        "entity": "Orbiter",
        "definition": "A spacecraft designed for spaceflight."
    },
    {
        "entity": "flight deck",
        "definition": "The top level of the crew compartment, typically where flight controls are located."
    },
    {
        "entity": "middeck",
        "definition": "The lower level of the crew compartment, used for sleeping, working, and storing equipment."
    }
]
Done.
```

`Knowledge Graph Relationshps`:
```
docker logs trustgraph-kg-extract-relationships-1
```

Output should be an array of JSON objects with keys `subject`, `predicate`, `object`, and `object-entity`:
```
Indexing 1f7b7055-p11-c3...
[
    {
        "subject": "Space Shuttle",
        "predicate": "carry",
        "object": "16 tons of cargo",
        "object-entity": false
    },
    {
        "subject": "friction",
        "predicate": "generated by",
        "object": "atmosphere",
        "object-entity": true
    }
]
Done.
```

### Graph Parsing

To check that the knowledge graph is successfully parsing data:

```
scripts/graph-show
```

The output should be a set of semantic triples in [N-Triples](https://www.w3.org/TR/rdf12-n-triples/) format.

```
http://trustgraph.ai/e/enterprise http://trustgraph.ai/e/was-carried to altitude and released for a gliding approach and landing at the Mojave Desert test center.
http://trustgraph.ai/e/enterprise http://www.w3.org/2000/01/rdf-schema#label Enterprise.
http://trustgraph.ai/e/enterprise http://www.w3.org/2004/02/skos/core#definition A prototype space shuttle orbiter used for atmospheric flight testing.
```

### Number of Graph Edges

N-Triples format is not particularly human readable. It's more useful to know how many graph edges have successfully been extracted from the text corpus:
```
scripts/graph-show  | wc -l
```

The test report has quite a long introduction and adminstrative text commonly found in official reports. The first few hundred graph edges mostly capture this more
document formatting knowledge. To fully test the ability to extract complex knowledge, wait until at least `1000` graph edges have been extracted. The full extraction for this PDF will extract many thousand graph edges.

### RAG Test Script
```
tests/test-graph-rag
```
This script forms a LM prompt asking for 20 facts regarding the Challenger disaster. Depending on how many graph edges have been extracted, the response will be similar to:

```
Here are 20 facts from the provided knowledge graph about the Space Shuttle disaster:

1. **Space Shuttle Challenger was a Space Shuttle spacecraft.**
2. **The third Spacelab mission was carried by Orbiter Challenger.**
3. **Francis R. Scobee was the Commander of the Challenger crew.**
4. **Earth-to-orbit systems are designed to transport payloads and humans from Earth's surface into orbit.**
5. **The Space Shuttle program involved the Space Shuttle.**
6. **Orbiter Challenger flew on mission 41-B.**
7. **Orbiter Challenger was used on STS-7 and STS-8 missions.**
8. **Columbia completed the orbital test.**
9. **The Space Shuttle flew 24 successful missions.**
10. **One possibility for the Space Shuttle was a winged but unmanned recoverable liquid-fuel vehicle based on the Saturn 5 rocket.**
11. **A Commission was established to investigate the space shuttle Challenger accident.**
12. **Judit h Arlene Resnik was Mission Specialist Two.**
13. **Mission 51-L was originally scheduled for December 1985 but was delayed until January 1986.**
14. **The Corporation's Space Transportation Systems Division was responsible for the design and development of the Space Shuttle Orbiter.**
15. **Michael John Smith was the Pilot of the Challenger crew.**
16. **The Space Shuttle is composed of two recoverable Solid Rocket Boosters.**
17. **The Space Shuttle provides for the broadest possible spectrum of civil/military missions.**
18. **Mission 51-L consisted of placing one satellite in orbit, deploying and retrieving Spartan, and conducting six experiments.**
19. **The Space Shuttle became the focus of NASA's near-term future.**
20. **The Commission focused its attention on safety aspects of future flights.** 
```

For an errors with the `RAG` proces, check the following log:
```
docker logs -f trustgraph-graph-rag-1
```
### More RAG Test Queries

If you want to try different RAG queries, modify the `query` in the [test script](https://github.com/trustgraph-ai/trustgraph/blob/master/tests/test-graph-rag).

### Shutting Down

When shutting down the pipeline, it's best to shut down all Docker containers and volumes.

```
docker-compose -f docker-compose-<azure/ollama/claude/vertexai>.yaml down --volumes
```

To confirm all Docker containers have been shut down, check that the following list is empty:
```
docker ps
```

To confirm all Docker volumes have been removed, check that the following list is empty:
```
docker volume ls
```

