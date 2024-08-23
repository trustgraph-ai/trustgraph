local base = import "base.jsonnet";
local images = import "images.jsonnet";
local url = import "url.jsonnet";
local prompts = import "../prompts/openai.jsonnet";
{
    services +: {

	"text-completion": base + {
	    image: images.trustgraph,
	    command: [
		"text-completion-openai",
		"-p",
		url.pulsar,
		"-k",
		"${OPENAI_KEY}",
                "-x",
                "4096",
                "-t",
                "0.0",
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
		"text-completion-openai",
		"-p",
		url.pulsar,
		"-k",
		"${OPENAI_KEY}",
                "-x",
                "4096",
                "-t",
                "0.0",
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
