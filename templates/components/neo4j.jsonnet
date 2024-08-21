local base = import "base.jsonnet";
local images = import "images.jsonnet";
local url = import "url.jsonnet";
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
	}

    },

}
