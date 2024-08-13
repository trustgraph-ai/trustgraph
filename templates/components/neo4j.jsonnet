local base = import "base.jsonnet";
local images = import "images.jsonnet";
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
	    },
	    volumes: [
		"neo4j:/data"
	    ],
	}
    },
}
