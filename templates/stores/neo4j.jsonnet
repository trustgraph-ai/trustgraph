local base = import "base/base.jsonnet";
local images = import "values/images.jsonnet";
{

    volumes +: {
	neo4j: {},
    },

    services +: {

	neo4j: base + {
	    image: images.neo4j,
	    ports: [
                {
                    src: 7474,
                    dest: 7474,
                    name: "api",
                },
                {
                    src: 7687,
                    dest: 7687,
                    name: "api2",
                }
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
			memory: '768M'
		    },
		    reservations: {
			cpus: '0.5',
			memory: '768M'
		    }
		}
            },
	},

    },

}
