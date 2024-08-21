local base = import "base.jsonnet";
local images = import "images.jsonnet";
local url = import "url.jsonnet";
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

    },
}
