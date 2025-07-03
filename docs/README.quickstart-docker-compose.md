
# Getting Started

## Preparation

> [!TIP]
> Before launching `TrustGraph`, be sure to have the `Docker Engine`  or `Podman Machine` installed and running on the host machine. 
> 
> - [Install the Docker Engine](https://docs.docker.com/engine/install/)
> - [Install the Podman Machine](http://podman.io/)

> [!NOTE]
> `TrustGraph` has been tested on `Linux` and `MacOS` with `Docker` and `Podman`. `Windows` deployments have not been tested.

> [!TIP]
> If using `Podman`, the only change will be to substitute `podman` instead of `docker` in all commands.

## Create the configuration

This guide talks you through the Compose file launch, which is the easiest
way to lauch on a standalone machine, or a single cloud instance.
See [README](README.md) for links to other deployment mechanisms.

To create the deployment configuration, go to the
[deployment portal](https://config-ui.demo.trustgraph.ai/) and follow the
instructions.
- Select Docker Compose or Podman Compose as the deployment
  mechanism.
- Use Cassandra for the graph store, it's easiest and most tested.
- Use Qdrant for the vector store, it's easiest and most tested.
- Chunker: Recursive, chunk size of 1000, 50 overlap should be fine.
- Pick your favourite LLM model:
  - If you have enough horsepower in a local GPU, LMStudio is an easy
    starting point for a local model deployment.  Ollama is fairly easy.
  - VertexAI on Google is relatively straightforward for a cloud
    model-as-a-service LLM, and you can get some free credits.
- Max output tokens as per the model, 2048 is safe.
- Customisation, check LLM Prompt Manager and Agent Tools.
- Finish deployment, Generate and download the deployment bundle.
  Read the extra deploy steps on that page.

## Preparing TrustGraph

Below is a step-by-step guide to deploy `TrustGraph`, extract knowledge from a PDF, build the vector and graph stores, and finally generate responses with Graph RAG.

### Install requirements

```
python3 -m venv env
. env/bin/activate
pip install trustgraph-cli
```
## Running TrustGraph

```
docker-compose -f docker-compose.yaml up -d
```

After running the chosen `Docker Compose` file, all `TrustGraph` services will launch and be ready to run `Naive Extraction` jobs and provide `RAG` responses using the extracted knowledge.

### Verify TrustGraph Containers

On first running a `Docker Compose` file, it may take a while (depending on your network connection) to pull all the necessary components. Once all of the components have been pulled.

A quick check that TrustGraph processors have started:

```
tg-show-processor-state
```

Processors start quickly, but can take a while (~60 seconds) for 
Pulsar and Cassandra to start.

If you have any concerns, 
check that the TrustGraph containers are running:

```
docker ps
```

Any containers that have exited unexpectedly can be found by checking the `STATUS` field using the following:

```
docker ps -a
```

> [!TIP]
> Before proceeding, allow the system to stabilize. A safe warm up period is `120 seconds`. If services seem to be "stuck", it could be because services did not have time to initialize correctly and are trying to restart. Waiting `120 seconds` before launching any scripts should provide much more reliable operation.

### Everything running

An easy way to check all the main start is complete:

```
tg-show-flows
```

You should see a default flow.  If you see an error, leave it and try again.

### Load some sample documents

```
tg-load-sample-documents
```

### Workbench

A UI is launched on port 8888, see if you can see it at
[http://localhost:8888/](http://localhost:8888/)

Verify things are working:
- Go to the prompts page see that you can see some prompts
- Go to the library page, and check you can see the sample documents you
  just loaded.
  
### Load a document

- On the library page, select a document.  Beyond State Vigilance is a
  smallish doc to work with.
- Select the doc by clicking on it.
- Select Submit at the bottom of the screen on the action bar.
- Select a processing flow, use the default.
- Click submit.

### Look in Grafana

A Grafana is launched on port 3000, see if you can see it at
[http://localhost:3000/](http://localhost:3000/)

- Login as admin, password admin.
- Skip the password change screen / change the password.
- Verify things are working by selecting the TrustGraph dashboard
- After a short while, you should see the backlog rise to a few hundred
  document chunks.
  
Once some chunks are loaded, you can start to work with the document.
  
### Graph Parsing

To check that the knowledge graph is successfully parsing data:

```
tg-show-graph
```

The output should be a set of semantic triples in [N-Triples](https://www.w3.org/TR/rdf12-n-triples/) format.

```
http://trustgraph.ai/e/enterprise http://trustgraph.ai/e/was-carried to altitude and released for a gliding approach and landing at the Mojave Desert test center.
http://trustgraph.ai/e/enterprise http://www.w3.org/2000/01/rdf-schema#label Enterprise.
http://trustgraph.ai/e/enterprise http://www.w3.org/2004/02/skos/core#definition A prototype space shuttle orbiter used for atmospheric flight testing.
```

### Work with the document

Back on the workbench, click on the 'Vector search' tab, and
search for something e.g. state.  You should see some search results.
Click on results to start exploring the knowledge graph.

Click on Graph view on an explored page to visualize the graph.

### Queries over the document

On workbench, click Graph RAG and enter a question e.g.
What is this document about?

### Shutting Down TrustGraph

When shutting down `TrustGraph`, it's best to shut down all Docker containers and volumes. Run the `docker compose down` command that corresponds to your model and graph store deployment:

```
docker compose -f document-compose.yaml down -v -t 0
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

