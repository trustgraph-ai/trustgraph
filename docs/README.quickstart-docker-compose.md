
# Getting Started

> [!TIP]
> Before launching `TrustGraph`, be sure to have the `Docker Engine`  or `Podman Machine` installed and running on the host machine. 
> 
> - [Install the Docker Engine](https://docs.docker.com/engine/install/)
> - [Install the Podman Machine](http://podman.io/)

> [!NOTE]
> `TrustGraph` has been tested on `Linux` and `MacOS` with `Docker` and `Podman`. `Windows` deployments have not been tested.

> [!TIP]
> If using `Podman`, the only change will be to substitute `podman` instead of `docker` in all commands.

All `TrustGraph` components are deployed through a `Docker Compose` file. There are **16** `Docker Compose` files to choose from, depending on the desired model deployment and choosing between the graph stores `Cassandra` or `Neo4j`:

- `AzureAI` serverless endpoint for deployed models in Azure
- `Bedrock` API for models deployed in AWS Bedrock
- `Claude` through Anthropic's API
- `Cohere` through Cohere's API
- `Mix` for mixed model deployments
- `Ollama` for local model deployments
- `OpenAI` for OpenAI's API
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

Launching `TrustGraph` is a simple as running a single `Docker Compose` file. There are `Docker Compose` files for each possible model deployment and graph store configuration. Depending on your chosen model ang graph store deployment, chose one of the following launch files:

| Model Deployment | Graph Store | Launch File |
| ---------------- | ------------ | ----------- |
| AWS Bedrock | Cassandra | `tg-launch-bedrock-cassandra.yaml` |
| AWS Bedrock | Neo4j | `tg-launch-bedrock-neo4j.yaml` |
| AzureAI Serverless Endpoint | Cassandra | `tg-launch-azure-cassandra.yaml` |
| AzureAI Serverless Endpoint | Neo4j | `tg-launch-azure-neo4j.yaml` |
| Anthropic API | Cassandra | `tg-launch-claude-cassandra.yaml` |
| Anthropic API | Neo4j | `tg-launch-claude-neo4j.yaml` |
| Cohere API | Cassandra | `tg-launch-cohere-cassandra.yaml` |
| Cohere API | Neo4j | `tg-launch-cohere-neo4j.yaml` |
| Mixed Depoloyment | Cassandra | `tg-launch-mix-cassandra.yaml` |
| Mixed Depoloyment | Neo4j | `tg-launch-mix-neo4j.yaml` |
| Ollama | Cassandra | `tg-launch-ollama-cassandra.yaml` |
| Ollama | Neo4j | `tg-launch-ollama-neo4j.yaml` |
| OpenAI | Cassandra | `tg-launch-openai-cassandra.yaml` |
| OpenAI | Neo4j | `tg-launch-openai-neo4j.yaml` |
| VertexAI | Cassandra | `tg-launch-vertexai-cassandra.yaml` |
| VertexAI | Neo4j | `tg-launch-vertexai-neo4j.yaml` |

> [!CAUTION]
> All tokens, paths, and authentication files must be set **PRIOR** to launching a `Docker Compose` file.

## Chunking

Extraction performance can vary signficantly with chunk size. The default chunk size is `2000` characters using a recursive method. Decreasing the chunk size may increase the amount of extracted graph edges at the cost of taking longer to complete the extraction process. The chunking method and sizes can be adjusted in the selected `YAML` file. In the selected `YAML` file, find the section for `chunker`. Under the commands list, modify the follwing parameters:

```
- "chunker-recursive" # recursive text splitter in characters
- "chunker-token" # recursive style token splitter
- "--chunk-size"
- "<number-of-characters/tokens-per-chunk>"
- "--chunk-overlap"
- "<number-of-characters/tokens-to-overlap-per-chunk>"
```

## Model Parameters

Most configurations allow adjusting some model parameters. For configurations with adjustable parameters, the `temperature` and `max_output` tokens can be set in the selected `YAML` file:

```
- "-x"
- <max_model_output_tokens>
- "-t"
- <model_temperature>
```

> [!TIP]
> The default `temperature` in `TrustGraph` is set to `0.0`. Even for models with long input contexts, the max output might only be 2048 (like some intances of Llama3.1). Make sure `max_output` is not set higher than allowed for a given model.

## Choose a TrustGraph Configuration

Choose one of the `Docker Compose` files that meets your preferred model and graph store deployments. Each deployment will require setting some `environment variables` and commands in the chosen `YAML` file. All variables and commands must be set prior to running the chosen `Docker Compose` file.

### AWS Bedrock API

```
export AWS_ID_KEY=<ID-KEY-HERE>
export AWS_SECRET_KEY=<TOKEN-GOES-HERE>
docker compose -f tg-launch-bedrock-cassandra.yaml up -d # Using Cassandra as the graph store
docker compose -f tg-launch-bedrock-neo4j.yaml up -d # Using Neo4j as the graph store
```

> [!NOTE]
> The current defaults for `AWS Bedrock` are `Mistral Large 2 (24.07)` in `US-West-2`.

To change the model and region, go the sections for `text-completion` and `text-completion-rag` in the `tg-launch-bedrock.yaml` file. Add the following lines under the `command` section:

```
- "-r"
- "<"us-east-1" or "us-west-2">
- "-m"
- "<bedrock-api-model-name-here>
```

> [!TIP]
> Having two separate modules for `text-completion` and `text-completion-rag` allows for using one model for extraction and a different model for RAG.

### AzureAI Serverless Model Deployment

```
export AZURE_ENDPOINT=<https://ENDPOINT.HOST.GOES.HERE/>
export AZURE_TOKEN=<TOKEN-GOES-HERE>
docker compose -f tg-launch-azure-cassandra.yaml up -d # Using Cassandra as the graph store
docker compsoe -f tg-launch-azure-neo4j.yaml up -d # Using Neo4j as the graph store
```

### Claude through Anthropic API

```
export CLAUDE_KEY=<TOKEN-GOES-HERE>
docker compose -f tg-launch-claude-cassandra.yaml up -d # Using Cassandra as the graph store
docker compose -f tg-launch-claude-neo4j.yaml up -d # Using Neo4j as the graph store
```

### Cohere API

```
export COHERE_KEY=<TOKEN-GOES-HERE>
docker compose -f tg-launch-cohere-cassandra.yaml up -d # Using Cassandra as the graph store
docker compose -f tg-launch-cohere-neo4j.yaml up -d # Using Neo4j as the graph store
```

### Ollama Hosted Model Deployment

> [!TIP]
> The power of `Ollama` is the flexibility it provides in Language Model deployments. Being able to run LMs with `Ollama` enables fully secure AI `TrustGraph` pipelines that aren't relying on any external APIs. No data is leaving the host environment or network. More information on `Ollama` deployments can be found [here](https://trustgraph.ai/docs/deploy/localnetwork).

> [!NOTE]
> The current default model for an `Ollama` deployment is `Gemma2:9B`.

```
export OLLAMA_HOST=<hostname> # Set to location of machine running Ollama such as http://localhost:11434
docker compose -f tg-launch-ollama-cassandra.yaml up -d # Using Cassandra as the graph store
docker compose -f tg-launch-ollama-neo4j.yaml up -d # Using Neo4j as the graph store
```

> [!NOTE]
> On `MacOS`, if running `Ollama` locally set `OLLAMA_HOST=http://host.docker.internal:11434`.

To change the `Ollama` model, first make sure the desired model has been pulled and fully downloaded. In the `YAML` file, go to the section for `text-completion` and `text-completion-rag`. Under `commands`, add the following two lines:

```
- "-m"
- "<model-name-here>"
```

### OpenAI API

```
export OPENAI_TOKEN=<TOKEN-GOES-HERE>
docker compose -f tg-launch-openai-cassandra.yaml up -d # Using Cassandra as the graph store
docker compose -f tg-launch-openai-neo4j.yaml up -d # Using Neo4j as the graph store
```

### VertexAI through GCP

```
mkdir -p vertexai
cp <your config> vertexai/private.json
docker compose -f tg-launch-vertexai-cassandra.yaml up -d # Using Cassandra as the graph store
docker compose -f tg-launch-vertexai-neo4j.yaml up -d # Using Neo4j as the graph store
```

> [!TIP]
> If you're running `SELinux` on Linux you may need to set the permissions on the VertexAI directory so that the key file can be mounted on a Docker container using the following command:
> 
> ```
> chcon -Rt svirt_sandbox_file_t vertexai/
> ```

## Mixing Models

One of the most powerful features of `TrustGraph` is the ability to use one model deployment for the `Naive Extraction` process and a different model for `RAG`. Since the `Naive Extraction` can be a one time process, it makes sense to use a more performant model to generate the most comprehensive set of graph edges and embeddings as possible. With a high-quality extraction, it's possible to use a much smaller model for `RAG` and still achieve "big" model performance.

A "split" model deployment uses `tg-launch-mix.yaml`. There are two modules: `text-completion` and `text-completion-rag`. The `text-completion` module is called only for extraction while `text-completion-rag` is called only for RAG.

### Choosing Model Deployments

Before launching the `Docker Compose` file, the desired model deployments must be specified. The options are:

- `text-completion-azure`
- `text-completion-bedrock`
- `text-completion-claude`
- `text-completion-cohere`
- `text-completion-ollama`
- `text-completion-openai`
- `text-completion-vertexai`

For the `text-completion` and `text-completion-rag` modules in the `tg-launch-mix.yaml`file, choose one of the above deployment options and enter that line as the first line under `command` for each `text-completion` and `text-completion-rag` module. Depending on the model deployment, other variables such as endpoints, keys, and model names must specified under the `command` section as well. Once all variables and commands have been set, the `mix` deployment can be lauched with:

```
docker compose -f tg-launch-mix-cassandra.yaml up -d # Using Cassandra as the graph store
docker compose -f tg-launch-mix-neo4j.yaml up -d # Using Neo4j as the graph store
```

> [!TIP]
> Any of the `YAML` files can be modified for a "split" deployment by adding the `text-completion-rag` module.

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

> [!TIP]
> Before proceeding, allow the system to stabilize. A safe warm up period is `120 seconds`. If services seem to be "stuck", it could be because services did not have time to initialize correctly and are trying to restart. Waiting `120 seconds` before launching any scripts should provide much more reliable operation.

### Load a Text Corpus

Create a sources directory and get a test PDF file. To demonstrate the power of `TrustGraph`, the provided script loads a PDF of the public [Roger's Commision Report](https://sma.nasa.gov/SignificantIncidents/assets/rogers_commission_report.pdf) from the NASA Challenger disaster. This PDF includes complex formatting, unique terms, complex concepts, unique concepts, and information not commonly found in public knowledge sources.

```
mkdir sources
curl -o sources/Challenger-Report-Vol1.pdf https://sma.nasa.gov/SignificantIncidents/assets/rogers_commission_report.pdf
```

Load the file for knowledge extraction:

```
scripts/load-pdf -f sources/Challenger-Report-Vol1.pdf
```

> [!NOTE]
> To load a text file, use the following script:
>
> ```
> scripts/load-text -f sources/<txt-file.txt>
> ```

The console output `File loaded.` indicates the text corpus has been sucessfully loaded to the processing queues and extraction will begin.

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

### RAG Test
```
scripts/query-graph-rag -q 'Give me 20 facts about the space shuttle Challenger'
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
### Custom RAG Queries

At any point, a RAG request can be generated and run with the following script:

```
scripts/query-graph-rag -q "RAG request here"
```

### Shutting Down TrustGraph

When shutting down `TrustGraph`, it's best to shut down all Docker containers and volumes. Run the `docker compose down` command that corresponds to your model and graph store deployment:

```
docker compose -f tg-launch-<model-deployment>-<graph-store>.yaml down -v
```

> [!TIP]
> To confirm all Docker containers have been shut down, check that the following list is empty:
> ```
> docker ps
> ```
>
> To confirm all Docker volumes have been removed, check that the following list is empty:
> ```
> docker volume ls
> ```
