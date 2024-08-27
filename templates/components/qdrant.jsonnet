local base = import "base.jsonnet";
local images = import "images.jsonnet";
local url = import "url.jsonnet";
local qdrant = import "stores/qdrant.jsonnet";

qdrant + {

    services +: {

	"store-graph-embeddings": base + {
	    image: images.trustgraph,
	    command: [
		"ge-write-qdrant",
		"-p",
		url.pulsar,
		"-t",
		url.qdrant,
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
		"ge-query-qdrant",
		"-p",
		url.pulsar,
		"-t",
		url.qdrant,
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

/*

// Document embeddings writer & query service.  Not currently enabled.

	"store-doc-embeddings": base + {
	    image: images.trustgraph,
	    command: [
		"de-write-qdrant",
		"-p",
		url.pulsar,
		"-t",
		url.qdrant,
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

	"query-doc-embeddings": base + {
	    image: images.trustgraph,
	    command: [
		"de-query-qdrant",
		"-p",
		url.pulsar,
		"-t",
		url.qdrant,
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

*/

    }

}

