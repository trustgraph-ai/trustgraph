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
            deploy: {
		resources: {
		    limits: {
			cpus: '0.5',
			memory: '128M'
		    },
		    reservations: {
			cpus: '0.1',
			memory: '128M'
		    }
		}
	    },
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
            deploy: {
		resources: {
		    limits: {
			cpus: '0.5',
			memory: '128M'
		    },
		    reservations: {
			cpus: '0.1',
			memory: '128M'
		    }
		}
	    },
	},

    }

}


