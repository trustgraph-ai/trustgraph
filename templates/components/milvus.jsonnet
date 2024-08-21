local base = import "base.jsonnet";
local images = import "images.jsonnet";
local url = import "url.jsonnet";
local milvus = import "stores/milvus.jsonnet";

milvus + {

    services +: {

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

    }

}


