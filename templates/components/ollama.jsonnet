local base = import "base/base.jsonnet";
local images = import "values/images.jsonnet";
local url = import "values/url.jsonnet";
local prompts = import "prompts/slm.jsonnet";
{

    "ollama-model":: "gemma2:9b",
    "ollama-url":: "${OLLAMA_HOST}",

    services +: {

	"text-completion": base + {
	    image: images.trustgraph,
	    command: [
		"text-completion-ollama",
		"-p",
		url.pulsar,
                "-m",
                $["ollama-model"],
		"-r",
                $["ollama-url"],
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
		"text-completion-ollama",
		"-p",
		url.pulsar,
                "-m",
                $["ollama-model"],
		"-r",
                $["ollama-url"],
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
