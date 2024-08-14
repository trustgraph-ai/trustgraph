local base = import "base.jsonnet";
local images = import "images.jsonnet";
local url = import "url.jsonnet";
local cassandra_hosts = "cassandra";
{
    volumes +: {
	cassandra: {},
    },
    services +: {

	cassandra: base + {
	    image: images.cassandra,
	    ports: [
		"9042:9042"
	    ],
	    volumes: [
		"cassandra:/var/lib/cassandra"
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

    },
}
