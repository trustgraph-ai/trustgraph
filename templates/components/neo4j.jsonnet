local base = import "base/base.jsonnet";
local images = import "values/images.jsonnet";
local url = import "values/url.jsonnet";
local neo4j = import "stores/neo4j.jsonnet";

neo4j + {

    services +: {

	"query-triples": base + {
	    image: images.trustgraph,
	    command: [
		"triples-query-neo4j",
		"-p",
		url.pulsar,
		"-g",
		"bolt://neo4j:7687",
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

	"store-triples": base + {
	    image: images.trustgraph,
	    command: [
		"triples-write-neo4j",
		"-p",
		url.pulsar,
		"-g",
		"bolt://neo4j:7687",
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
	}

    },

}
