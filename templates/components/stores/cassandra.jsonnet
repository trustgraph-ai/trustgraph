local base = import "../base.jsonnet";
local images = import "../images.jsonnet";
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
	    environment: {
		JVM_OPTS: "-Xms256M -Xmx256M",
	    },
	    volumes: [
		"cassandra:/var/lib/cassandra"
	    ],
            deploy: {
		resources: {
		    limits: {
			cpus: '1.0',
			memory: '800M'
		    },
		    reservations: {
			cpus: '0.5',
			memory: '800M'
		    }
		}
            },
	},

    },
}
