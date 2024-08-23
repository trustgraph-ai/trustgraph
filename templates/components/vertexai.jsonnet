local base = import "base.jsonnet";
local images = import "images.jsonnet";
local url = import "url.jsonnet";
local prompts = import "../prompts/gemini.jsonnet";
{
    services +: {

	"text-completion": base + {
	    image: images.trustgraph,
	    command: [
		"text-completion-vertexai",
		"-p",
		url.pulsar,
		"-k",
		"/vertexai/private.json",
		"-r",
		"us-central1",
                "-x",
                "4096",
                "-t",
                "0.0",
	    ],
	    volumes: [
		"./vertexai:/vertexai"
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
		"text-completion-vertexai",
		"-p",
		url.pulsar,
		"-k",
		"/vertexai/private.json",
		"-r",
		"us-central1",
                "-x",
                "4096",
                "-t",
                "0.0",
		"-i",
		"non-persistent://tg/request/text-completion-rag",
		"-o",
		"non-persistent://tg/response/text-completion-rag-response",
	    ],
	    volumes: [
		"./vertexai:/vertexai"
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


