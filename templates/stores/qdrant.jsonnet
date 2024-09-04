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
                {
                    src: 6333,
                    dest: 6333,
                    name: "api",
                },
                {
                    src: 6334,
                    dest: 6334,
                    name: "api2",
                }
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
