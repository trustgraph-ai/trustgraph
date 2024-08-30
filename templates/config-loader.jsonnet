local components = {
   "azure": import "components/azure.jsonnet",
   "bedrock": import "components/bedrock.jsonnet",
   "claude": import "components/claude.jsonnet",
   "cohere": import "components/cohere.jsonnet",
   "grafana": import "components/grafana.jsonnet",
   "graph-rag-cassandra": import "components/cassandra.jsonnet",
   "graph-rag-neo4j": import "components/neo4j.jsonnet",
   "ollama": import "components/ollama.jsonnet",
   "openai": import "components/openai.jsonnet",
   "override-recursive-chunker": import "components/cassandra.jsonnet",
   "prompt-template-definitions": import "prompts/gemini.jsonnet",
   "prompt-template-document-query": import "prompts/gemini.jsonnet",
   "prompt-template-kq-query": import "prompts/gemini.jsonnet",
   "prompt-template-relationships": import "prompts/gemini.jsonnet",
   "prompt-template-rows-template": import "prompts/gemini.jsonnet",
   "pulsar": import "components/pulsar.jsonnet",
   "pulsar-manager": import "components/pulsar.jsonnet",
   "trustgraph-base": import "components/trustgraph.jsonnet",
   "vector-store-milvus": import "components/milvus.jsonnet",
   "vector-store-qdrant": import "components/qdrant.jsonnet",
   "vertexai": import "components/vertexai.jsonnet"
};

local options = import "config.json";

local add = function(state, p) state + components[p.name];

local config = std.foldl(add, options, {});

//std.manifestYamlDoc(config)

config

