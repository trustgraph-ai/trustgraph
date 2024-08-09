
# Getting Started

[!TIP]
Before launching `TrustGraph` with `Docker Compose`, be sure to have the `Docker Engine` installed and running on the host machine. Installation instructions for the `Docker Engine` can be found [here](https://docs.docker.com/engine/install/).

[!NOTE]
The `Docker Compose` files have been tested on `Linux` and `MacOS`. `Windows` deployments have not been tested.

All `TrustGraph` components are deployed through a `Docker Compose` file. There are **7** `Docker Compose` files to choose from, depending on the desired model deployment:

- `AzureAI` serverless endpoint for deployed models in Azure
- `Bedrock` API for models deployed in AWS Bedrock
- `Claude` through Anthropic's API
- `Cohere` through Cohere's API
- `Mix` for mixed model deployments
- `Ollama` for local model deployments
- `VertexAI` for models deployed in Google Cloud

`Docker Compose` enables the following functions:

- Run the required components for full end-to-end `Graph RAG` knowledge pipeline
- Inspect processing logs
- Load text corpus and begin knowledge extraction
- Verify extracted Graph Edges
- Model agnostic, Graph RAG

## Preparing TrustGraph

Below is a step-by-step guide to deploy `TrustGraph`, extract knowledge from a PDF, build the vector and graph stores, and finally generate responses with Graph RAG.

### Install requirements

```
python3 -m venv env
. env/bin/activate
pip3 install pulsar-client
pip3 install cassandra-driver
export PYTHON_PATH=.
```

### Clone the GitHub Repo

```
git clone https://github.com/trustgraph-ai/trustgraph trustgraph
cd trustgraph
```

## TrustGraph as Docker Compose Files

Depending on your desired model deployment, you will choose from one of the following `Docker Compose` files:

- `docker-compose-azure.yaml`: AzureAI endpoint. Set `AZURE_TOKEN` to the secret token and `AZURE_ENDPOINT` to the URL endpoint address for the deployed model.
- `docker-compose-bedrock.yaml`: AWS Bedrock API. Set `AWS_ID_KEY` and `AWS_SECRET_KEY` to credentials enabled for `AWS Bedrock` access.
- `docker-compose-claude.yaml`: Anthropic's API. Set `CLAUDE_KEY` to your API key.
- `docker-compose-cohere.yaml`: Cohere's API. Set `COHERE_KEY` to your API key.
- `docker-compose-mix.yaml`: Special deployment that allows two separate model deployments for the extraction and RAG processes.
- `docker-compose-ollama.yaml`: Local LM (currently using [Gemma2](https://ollama.com/library/gemma2) deployed through Ollama.  Set `OLLAMA_HOST` to the machine running Ollama (e.g. `localhost` for Ollama running locally on your machine)
- `docker-compose-vertexai.yaml`: VertexAI API. Requires a `private.json` authentication file to authenticate with your GCP project. Filed should stored be at path `vertexai/private.json`.

[!CAUTION]
All tokens, paths, and authentication files must be set **PRIOR** to launching a `Docker Compose` file.

## Chunk Size

Extraction performance can vary signficantly with chunk size. The default chunk size is `2000` tokens. Decreasing the chunk size may increase the amount of extracted graph edges at the cost of taking longer to complete the extraction process. Adjusting the chunk size is as simple as adding 4 lines to the selected `YAML` file. In the selected `YAML` file, find the section for `chunker`. Under the commands list, add the following lines:

```
- "--chunk-size"
- "<number-of-tokens-per-chunk>"
- "--chunk-overlap"
- "<number-of-tokens-to-overlap-per-chunk>"
```

## Choose a TrustGraph Configuration

Choose one of the `Docker Compose` files that meets your preferred model deployments. Each deployment will require setting some `environment variables` and commands in the chosen `YAML` file. All variables and commands must be set prior to running the chosen `Docker Compose` file.

### AWS Bedrock API

```
export AWS_ID_KEY=<ID-KEY-HERE>
export AWS_SECRET_KEY=<TOKEN-GOES-HERE>
docker compose -f docker-compose-bedrock.yaml up -d
```

[!NOTE]
The current defaults for `AWS Bedrock` are `Mistral Large 2 (24.07)` in `US-West-2`.

To change the model and region, go the sections for `text-completion` and `text-completion-rag` in the `docker-compose-bedrock.yaml` file. Add the following lines under the `command` section:

```
- "-r"
- "<"us-east-1" or "us-west-2">
- "-m"
- "<bedrock-api-model-name-here>
```

[!TIP]
Having two separate modules for `text-completion` and `text-completion-rag` allows for using one model for extraction and a different model for RAG.

### AzureAI Serverless Model Deployment

```
export AZURE_ENDPOINT=<https://ENDPOINT.HOST.GOES.HERE/>
export AZURE_TOKEN=<TOKEN-GOES-HERE>
docker compose -f docker-compose-azure.yaml up -d
```

### Claude through Anthropic API

```
export CLAUDE_KEY=<TOKEN-GOES-HERE>
docker compose -f docker-compose-claude.yaml up -d
```

### Cohere API

```
export COHERE_KEY=<TOKEN-GOES-HERE>
docker compose -f docker-compose-cohere.yaml up -d
```

### Ollama Hosted Model Deployment

[!TIP]
The power of `Ollama` is the flexibility it provides in Language Model deployments. Being able to run LMs with `Ollama` enables fully secure AI `TrustGraph` pipelines that aren't relying on any external APIs. No data is leaving the host environment or network. More information on `Ollama` deployments can be found [here](https://trustgraph.ai/docs/deploy/localnetwork).

[!NOTE]
The current default model for an `Ollama` deployment is `Gemma2:9B`. 

```
export OLLAMA_HOST=<localhost> # Set to hostname or IP address of Ollama host
docker compose -f docker-compose-ollama.yaml up -d
```

[!NOTE]
On `MacOS`, if running `Ollama` locally set `OLLAMA_HOST=host.docker.internal`.

To change the `Ollama` model, first make sure the desired model has been pulled and fully downloaded. In the `docker-compose-ollama.yaml` file, go to the section for `text-completion`. Under `commands`, add the following two lines:

```
- "-m"
- "<model-name-here>"
```

### VertexAI through GCP

```
mkdir -p vertexai
cp <your config> vertexai/private.json
docker compose -f docker-compose-vertexai.yaml up -d
```

If you're running `SELinux` on Linux you may need to set the permissions on the VertexAI directory so that the key file can be mounted on a Docker container using the following command:

```
chcon -Rt svirt_sandbox_file_t vertexai/
```

## Mixing Models

One of the most powerful features of `TrustGraph` is the ability to use one model deployment for the `Naive Extraction` process and a different model for `RAG`. Since the `Naive Extraction` can be a one time process, it makes sense to use a more performant model to generate the most comprehensive set of graph edges and embeddings as possible. With a high-quality extraction, it's possible to use a much smaller model for `RAG` and still achieve "big" model performance.

A "split" model deployment uses `docker-compose-mix.yaml`. There are two modules: `text-completion` and `text-completion-rag`. The `text-completion` module is called only for extraction while `text-completion-rag` is called only for RAG. 

### Choosing Model Deployments

Before launching the `Docker Compose` file, the desired model deployments must be specified. The options are:

- `text-completion-azure`
- `text-completion-bedrock`
- `text-completion-claude`
- `text-completion-cohere`
- `text-completion-ollama`
- `text-completion-vertexai`

For the `text-completion` and `text-completion-rag` modules in the `docker-compose-mix.yaml`file, choose one of the above deployment options and enter that line as the first line under `command` for each `text-completion` and `text-completion-rag` module. Depending on the model deployment, other variables such as endpoints, keys, and model names must specified under the `command` section as well. Once all variables and commands have been set, the `mix` deployment can be lauched with:

```
docker compose -f docker-compose-mix.yaml up -d
```

[!TIP]
Any of the `YAML` files can be modified for a "split" deployment by adding the `text-completion-rag` module.

## Running TrustGraph

After running the chosen `Docker Compose` file, all `TrustGraph` services will launch and be ready to run `Naive Extraction` jobs and provide `RAG` responses using the extracted knowledge.

### Verify TrustGraph Containers

On first running a `Docker Compose` file, it may take a while (depending on your network connection) to pull all the necessary components. Once all of the components have been pulled, check that the TrustGraph containers are running:

```
docker ps
```

Any containers that have exited unexpectedly can be found by checking the `STATUS` field using the following:

```
docker ps -a
```

[!TIP]
Before proceeding, allow the system to enter a stable a working state. In general `30 seconds` should be enough time for Pulsar to stablize. The system uses Cassandra for a Graph store. Cassandra can take `60-70 seconds` to achieve a working state.

### Load a Text Corpus

Create a sources directory and get a test PDF file. To demonstrate the power of `TrustGraph`, the provided script loads a PDF of the public [Roger's Commision Report](https://sma.nasa.gov/SignificantIncidents/assets/rogers_commission_report.pdf) from the NASA Challenger disaster. This PDF includes complex formatting, unique terms, complex concepts, unique concepts, and information not commonly found in public knowledge sources.

```
mkdir sources
curl -o sources/Challenger-Report-Vol1.pdf https://sma.nasa.gov/SignificantIncidents/assets/rogers_commission_report.pdf
```

Load the file for knowledge extraction:

```
scripts/loader -f sources/Challenger-Report-Vol1.pdf
```

The console output `File loaded.` indicates the PDF has been sucessfully loaded to the processing queues and extraction will begin.

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
docker logs trustgraph-text-completion-1
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

The Challenger report has a long introduction with quite a bit of adminstrative text commonly found in official reports. The first few hundred graph edges mostly capture this document formatting knowledge. To fully test the ability to extract complex knowledge, wait until at least `1000` graph edges have been extracted. The full extraction for this PDF will extract many thousand graph edges.

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

For any errors with the `RAG` proces, check the following log:
```
docker logs -f trustgraph-graph-rag-1
```
### More RAG Test Queries

If you want to try different RAG queries, modify the `query` in the [test script](https://github.com/trustgraph-ai/trustgraph/blob/master/tests/test-graph-rag).

### Shutting Down TrustGraph

When shutting down `TrustGraph`, it's best to shut down all Docker containers and volumes. Run the `docker compose down` command that corresponds to your model deployment:

#### AWS Bedrock API

```
docker compose -f docker-compose-bedrock.yaml down --volumes
```

#### AzureAI Endpoint

```
docker compose -f docker-compose-azure.yaml down --volumes
```

#### Anthropic API

```
docker compose -f docker-compose-claude.yaml down --volumes
```

#### Cohere API

```
docker compose -f docker-compose-cohere.yaml down --volumes
```

#### Mixed Deployment

```
docker compose -f docker-compose-mix.yaml down --volumes
```

#### Ollama

```
docker compose -f docker-compose-ollama.yaml down --volumes
```

#### VertexAI API

```
docker compose -f docker-compose-vertexai.yaml down --volumes
```

To confirm all Docker containers have been shut down, check that the following list is empty:
```
docker ps
```

To confirm all Docker volumes have been removed, check that the following list is empty:
```
docker volume ls
```
