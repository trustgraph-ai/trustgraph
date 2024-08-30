local base = import "base/base.jsonnet";
local images = import "values/images.jsonnet";
local url = import "values/url.jsonnet";
local prompts = import "prompts/cohere.jsonnet";
{

    // Override chunking
    "chunk-size":: 150,
    "chunk-overlap":: 10,

    "cohere-key":: "${COHERE_KEY}",
    "cohere-temperature":: 0.0,

    services +: {

	"text-completion": base + {
	    image: images.trustgraph,
	    command: [
		"text-completion-cohere",
		"-p",
		url.pulsar,
		"-k",
		$["cohere-key"],
                "-t",
                $["cohere-temperature"],
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

	"text-completion-rag": base + {
	    image: images.trustgraph,
	    command: [
		"text-completion-cohere",
		"-p",
		url.pulsar,
		"-k",
		$["cohere-key"],
                "-t",
                $["cohere-temperature"],
		"-i",
		"non-persistent://tg/request/text-completion-rag",
		"-o",
		"non-persistent://tg/response/text-completion-rag-response",
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

    },
} + prompts
