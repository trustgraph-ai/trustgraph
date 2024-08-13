
local base = import "base.jsonnet";

local images = import "images.jsonnet";

local url = import "url.jsonnet";

local cassandra_hosts = "cassandra";

{
    services +: {

	"pdf-decoder": base + {
	    image: images.trustgraph,
	    command: [
		"pdf-decoder",
		"-p",
		url.pulsar,
	    ],
	},

	chunker: base + {
	    image: images.trustgraph,
	    command: [
		"chunker-recursive",
		"-p",
		url.pulsar,
	    ],
	},

	vectorize: base + {
	    image: images.trustgraph,
	    command: [
		"embeddings-vectorize",
		"-p",
		url.pulsar,
	    ],
	},

	embeddings: base + {
	    image: images.trustgraph,
	    command: [
		"embeddings-hf",
		"-p",
		url.pulsar,
		// "-m",
		// "mixedbread-ai/mxbai-embed-large-v1",
	    ],
	},

	"kg-extract-definitions": base + {
	    image: images.trustgraph,
	    command: [
		"kg-extract-definitions",
		"-p",
		url.pulsar,
	    ],
	},

	"kg-extract-relationships": base + {
	    image: images.trustgraph,
	    command: [
		"kg-extract-relationships",
		"-p",
		url.pulsar,
	    ],
	},

	"store-graph-embeddings": base + {
	    image: images.trustgraph,
	    command: [
		"ge-write-milvus",
		"-p",
		url.pulsar,
		"-t",
		url.milvus,
	    ],
	},

	"query-graph-embeddings": base + {
	    image: images.trustgraph,
	    command: [
		"ge-query-milvus",
		"-p",
		url.pulsar,
		"-t",
		url.milvus,
	    ],
	},

	"store-triples": base + {
	    image: images.trustgraph,
	    command: [
		"triples-write-cassandra",
		"-p",
		url.pulsar,
		"-g",
		cassandra_hosts,
	    ],
	},

	"query-triples": base + {
	    image: images.trustgraph,
	    command: [
		"triples-query-cassandra",
		"-p",
		url.pulsar,
		"-g",
		cassandra_hosts,
	    ],
	},

	"graph-rag": base + {
	    image: images.trustgraph,
	    command: [
		"graph-rag",
		"-p",
		url.pulsar,
		"--text-completion-request-queue",
		"non-persistent://tg/request/text-completion-rag",
		"--text-completion-response-queue",
		"non-persistent://tg/response/text-completion-rag-response",
	    ],
	},

    },

}
