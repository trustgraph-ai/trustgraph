
local base = import "components/base.jsonnet";
local url = import "components/url.jsonnet";
local images = import "components/images.jsonnet";

local cassandra = import "components/cassandra.jsonnet";
local pulsar = import "components/pulsar.jsonnet";
local milvus = import "components/milvus.jsonnet";
local grafana = import "components/grafana.jsonnet";
local trustgraph = import "components/trustgraph.jsonnet";

local config = cassandra + pulsar + milvus + grafana + trustgraph + {
    services +: {

	"text-completion": base + {
	    image: images.trustgraph,
	    command: [
		"text-completion-ollama",
		"-p",
		url.pulsar,
                // "-m",
                // "llama3.1:8b",
		"-r",
		"${OLLAMA_HOST}",
	    ],
	},

	"text-completion-rag": base + {
	    image: images.trustgraph,
	    command: [
		"text-completion-ollama",
		"-p",
		url.pulsar,
                // "-m",
                // "llama3.1:8b",
		"-r",
		"${OLLAMA_HOST}",
		"-i",
		"non-persistent://tg/request/text-completion-rag",
		"-o",
		"non-persistent://tg/response/text-completion-rag-response",
	    ],
	},
	
    }
};

std.manifestYamlDoc(config)

