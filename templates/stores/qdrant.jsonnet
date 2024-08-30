local base = import "base/base.jsonnet";
local images = import "values/images.jsonnet";

{

    volumes +: {
	qdrant: {},
    },

    services +: {

	qdrant: base + {
	    image: images.qdrant,
	    ports: [
		"6333:6333",
		"6334:6334",
	    ],
	    volumes: [
		"qdrant:/qdrant/storage"
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
