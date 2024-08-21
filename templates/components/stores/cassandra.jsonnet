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
	    volumes: [
		"cassandra:/var/lib/cassandra"
	    ],
	},

    },
}
