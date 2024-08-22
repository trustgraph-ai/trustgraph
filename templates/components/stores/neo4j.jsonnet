local base = import "../base.jsonnet";
local images = import "../images.jsonnet";
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
            deploy: {
		resources: {
		    limits: {
			cpus: '1.0',
			memory: '256M'
		    },
		    reservations: {
			cpus: '0.5',
			memory: '256M'
		    }
		}
            },
	},

    },

}
