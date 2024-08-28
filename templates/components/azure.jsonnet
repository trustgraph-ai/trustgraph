local base = import "base/base.jsonnet";
local images = import "values/images.jsonnet";
local url = import "values/url.jsonnet";
local prompts = import "prompts/mixtral.jsonnet";
{
    services +: {

	"text-completion": base + {
	    image: images.trustgraph,
	    command: [
		"text-completion-azure",
		"-p",
		url.pulsar,
		"-k",
		"${AZURE_TOKEN}",
		"-e",
		"${AZURE_ENDPOINT}",
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
		"text-completion-azure",
		"-p",
		url.pulsar,
		"-k",
		"${AZURE_TOKEN}",
		"-e",
		"${AZURE_ENDPOINT}",
		"-i",
                "-x",
                "4096",
                "-t",
                "0.0",
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


