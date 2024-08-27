local components = {
    neo4j: import "components/neo4j.jsonnet",
    cassandra: import "components/cassandra.jsonnet",
    pulsar: import "components/pulsar.jsonnet",
    milvus: import "components/milvus.jsonnet",
    qdrant: import "components/qdrant.jsonnet",
    grafana: import "components/grafana.jsonnet",
    trustgraph: import "components/trustgraph.jsonnet",
    azure: import "components/azure.jsonnet",
    bedrock: import "components/bedrock.jsonnet",
    cohere: import "components/cohere.jsonnet",
    claude: import "components/claude.jsonnet",
    ollama: import "components/ollama.jsonnet",
    openai: import "components/openai.jsonnet",
    mix: import "components/mix.jsonnet",
    vertexai: import "components/vertexai.jsonnet",
};

local options = std.split(std.extVar("options"), ",");

local add = function(state, name) state + components[name];

local config = std.foldl(add, options, {});

std.manifestYamlDoc(config)

