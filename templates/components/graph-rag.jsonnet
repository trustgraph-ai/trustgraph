local base = import "base/base.jsonnet";
local images = import "values/images.jsonnet";
local url = import "values/url.jsonnet";
local prompts = import "prompt-template.jsonnet";

{

    "graph-rag-entity-limit":: 50,
    "graph-rag-triple-limit":: 30,
    "graph-rag-max-subgraph-size":: 3000,

    services +: {

	"kg-extract-definitions": base + {
	    image: images.trustgraph,
	    command: [
		"kg-extract-definitions",
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

	"kg-extract-relationships": base + {
	    image: images.trustgraph,
	    command: [
		"kg-extract-relationships",
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

	"graph-rag": base + {
	    image: images.trustgraph,
	    command: [
		"graph-rag",
		"-p",
		url.pulsar,
		"--prompt-request-queue",
		"non-persistent://tg/request/prompt-rag",
		"--prompt-response-queue",
		"non-persistent://tg/response/prompt-rag-response",
		"--entity-limit",
                std.toString($["graph-rag-entity-limit"]),
		"--triple-limit",
                std.toString($["graph-rag-triple-limit"]),
		"--max-subgraph-size",
                std.toString($["graph-rag-max-subgraph-size"]),
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

    }

} + prompts



