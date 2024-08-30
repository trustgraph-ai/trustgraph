local base = import "base/base.jsonnet";
local images = import "values/images.jsonnet";
local url = import "values/url.jsonnet";
local cassandra_hosts = "cassandra";
local cassandra = import "stores/cassandra.jsonnet";

cassandra + {

    services +: {

	"store-triples": base + {
	    image: images.trustgraph,
	    command: [
		"triples-write-cassandra",
		"-p",
		url.pulsar,
		"-g",
		cassandra_hosts,
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

	"query-triples": base + {
	    image: images.trustgraph,
	    command: [
		"triples-query-cassandra",
		"-p",
		url.pulsar,
		"-g",
		cassandra_hosts,
	    ],
            deploy: {
		resources: {
		    limits: {
			cpus: '0.5',
			memory: '512M'
		    },
		    reservations: {
			cpus: '0.1',
			memory: '512M'
		    }
		}
	    },
	},

    },
}
