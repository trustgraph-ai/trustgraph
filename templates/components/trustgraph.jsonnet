local base = import "base/base.jsonnet";
local images = import "values/images.jsonnet";
local url = import "values/url.jsonnet";
local prompts = import "prompt-template.jsonnet";

{

    "chunk-size":: 250,
    "chunk-overlap":: 15,

    services +: {

	"pdf-decoder": base + {
	    image: images.trustgraph,
	    command: [
		"pdf-decoder",
		"-p",
		url.pulsar,
	    ],
            deploy: {
		resources: {
		    limits: {
			cpus: '0.5',
			memory: '128M'
		    },
		    reservations: {
			cpus: '0.1',
			memory: '128M'
		    }
		}
            },
	},

	chunker: base + {
	    image: images.trustgraph,
	    command: [
                "chunker-token",
		"-p",
		url.pulsar,
                "--chunk-size",
                std.toString($["chunk-size"]),
                "--chunk-overlap",
                std.toString($["chunk-overlap"]),
	    ],
            deploy: {
		resources: {
		    limits: {
			cpus: '0.5',
			memory: '128M'
		    },
		    reservations: {
			cpus: '0.1',
			memory: '128M'
		    }
		}
	    },
	},

	vectorize: base + {
	    image: images.trustgraph,
	    command: [
		"embeddings-vectorize",
		"-p",
		url.pulsar,
	    ],
            deploy: {
		resources: {
		    limits: {
			cpus: '1.0',
			memory: '512M'
		    },
		    reservations: {
			cpus: '0.5',
			memory: '512M'
		    }
		}
	    },
	},

    }

} + prompts



