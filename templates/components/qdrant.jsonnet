local base = import "base/base.jsonnet";
local images = import "values/images.jsonnet";
local url = import "values/url.jsonnet";
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

        // Document embeddings writer & query service.

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

    }

}

