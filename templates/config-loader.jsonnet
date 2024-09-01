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
   "override-recursive-chunker": import "components/chunker-recursive.jsonnet",
   "prompt-template-definitions": import "components/null.jsonnet",
   "prompt-template-document-query": import "components/null.jsonnet",
   "prompt-template-kq-query": import "components/null.jsonnet",
   "prompt-template-relationships": import "components/null.jsonnet",
   "prompt-template-rows-template": import "components/null.jsonnet",
   "pulsar": import "components/pulsar.jsonnet",
   "pulsar-manager": import "components/pulsar-manager.jsonnet",
   "trustgraph-base": import "components/trustgraph.jsonnet",
   "vector-store-milvus": import "components/milvus.jsonnet",
   "vector-store-qdrant": import "components/qdrant.jsonnet",
   "vertexai": import "components/vertexai.jsonnet",
   "null": {}
};

local config = function(p)
    (components[p.name] + {

        with:: function(k, v) self + {
            [k]:: v
        },

        with_params:: function(pars)
            self + std.foldl(
                function(obj, par) obj.with(par.key, par.value),
                std.objectKeysValues(pars),
                self
            ),

        }).with_params(p.parameters);

local options = import "config.json";

local add = function(state, p) state + config(p);

local output = std.foldl(add, options, {});

//std.manifestYamlDoc(config)

output

