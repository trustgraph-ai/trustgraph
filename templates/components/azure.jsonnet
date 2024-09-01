local base = import "base/base.jsonnet";
local images = import "values/images.jsonnet";
local url = import "values/url.jsonnet";
local prompts = import "prompts/mixtral.jsonnet";
{

    "azure-token":: "${AZURE_TOKEN}",
    "azure-endpoint":: "${AZURE_ENDPOINT}",
    "azure-max-output-tokens":: 4096,
    "azure-temperature":: 0.0,

    services +: {

	"text-completion": base + {
	    image: images.trustgraph,
	    command: [
		"text-completion-azure",
		"-p",
		url.pulsar,
		"-k",
		$["azure-token"],
		"-e",
		$["azure-endpoint"],
                "-x",
                std.toString($["azure-max-output-tokens"]),
                "-t",
                std.toString($["azure-temperature"]),
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
		$["azure-token"],
		"-e",
		$["azure-endpoint"],
		"-i",
                "-x",
                std.toString($["azure-max-output-tokens"]),
                "-t",
                std.toString($["azure-temperature"]),
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

