
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

	chunker: base + {
	    image: images.trustgraph,
	    command: [
		"chunker-recursive",
		"-p",
		url.pulsar,
		"--chunk-size",
		"4000",
		"--chunk-overlap",
		"120",
	    ],
	},

	"text-completion": base + {
	    image: images.trustgraph,
	    command: [
		"text-completion-cohere",
		"-p",
		url.pulsar,
		"-k",
		"${COHERE_KEY}",
		"-m",
		"c4ai-aya-23-35b",
	    ],
	},

	"text-completion-rag": base + {
	    image: images.trustgraph,
	    command: [
		"text-completion-cohere",
		"-p",
		url.pulsar,
		"-k",
		"${COHERE_KEY}",
		"-i",
		"non-persistent://tg/request/text-completion-rag",
		"-o",
		"non-persistent://tg/response/text-completion-rag-response",
		"-m",
		"c4ai-aya-23-8b",
	    ],
	},
	
    }
};

std.manifestYamlDoc(config)

