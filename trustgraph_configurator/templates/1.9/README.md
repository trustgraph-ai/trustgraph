
# TrustGraph template generation

There are two utilities here:

- `generate`: Generates a single Docker Compose launch configuration
  based on configuration you provide.
- `generate-all`: Generates the release bundle for releases.  You won't
  need to use this unless you are managing releases.
  
## `generate-all`

Previously, this generates a full set of all vector DB / triple store / LLM
combinations, and put them in a single ZIP file.  But this got out of
hand, so at the time of writing, this generates a single configuraton
using Qdrant vector DB, Ollama LLM support and Cassandra for a triple store.

The combinations are contained withing the code, it takes two arguments:
- output ZIP file (is over-written)
- TrustGraph version number

```
templates/generate-all output.zip 0.18.11
```

## `generate`

This utility takes a configuration file describing the components to bundle,
and outputs a Docker Compose YAML file.

### Input configuration

The input configuration is a JSON file, an array of components to pull into
the configuration.  For each component, there is a name and a (possibly empty)
object describing addtional parameters for that component.

Example:

```
[
    {
        "name": "cassandra",
        "parameters": {}
    },
    {
        "name": "pulsar",
        "parameters": {}
    },
    {
        "name": "qdrant",
        "parameters": {}
    },
    {
        "name": "embeddings-hf",
        "parameters": {}
    },
    {
        "name": "graph-rag",
        "parameters": {}
    },
    {
        "name": "grafana",
        "parameters": {}
    },
    {
        "name": "trustgraph",
        "parameters": {}
    },
    {
        "name": "googleaistudio",
        "parameters": {
            "googleaistudio-temperature": 0.3,
            "googleaistudio-max-output-tokens": 2048,
            "googleaistudio-model": "gemini-1.5-pro-002"
        }
    },
    {
        "name": "prompt-template",
        "parameters": {}
    },
    {
        "name": "override-recursive-chunker",
        "parameters": {
            "chunk-size": 1000,
            "chunk-overlap": 50
        }
    },
    {
        "name": "workbench-ui",
        "parameters": {}
    },
    {
        "name": "agent-manager-react",
        "parameters": {}
    }
]
```

If you want to make your own configuration you could try changing the
configuration above:
- Components which are essential: pulsar, trustgraph, graph-rag, grafana,
  agent-manager-react
- You need a triple store, one of: cassandra, memgraph, falkordb, neo4j
- You need a vector store, one of: qdrant, pinecone
- You need an LLM, one of: azure, azure-openai, bedrock, claude, cohere,
  llamafile, ollama, openai, vertexai.
- You need an embeddings implementation, one of: embeddings-hf,
  embeddings-ollama
- Optionally add the Workbench tool: workbench-ui

Components have over-ridable parameters, look in the component definition
in `templates/components/` to see what you can override.

### Invocation

Two parameters:
- The output ZIP file
- The version number

The configuration file described above is provided on standard input

```
templates/generate out.zip 0.18.9 < config.json
```

