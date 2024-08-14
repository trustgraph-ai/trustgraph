local base = import "base.jsonnet";
local images = import "images.jsonnet";
local url = import "url.jsonnet";
{

    volumes +: {
	neo4j: {},
    },

    services +: {

	neo4j: base + {
	    image: images.neo4j,
	    ports: [
		"7474:7474",
                "7687:7687",
	    ],
	    environment: {
		NEO4J_AUTH: "neo4j/password",
//		NEO4J_server_bolt_listen__address: "0.0.0.0:7687",
//		NEO4J_server_default__listen__address: "0.0.0.0",
//		NEO4J_server_http_listen__address: "0.0.0.0:7474",
	    },
	    volumes: [
		"neo4j:/data"
	    ],
	},

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
