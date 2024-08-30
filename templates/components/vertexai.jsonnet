local base = import "base/base.jsonnet";
local images = import "values/images.jsonnet";
local url = import "values/url.jsonnet";
local prompts = import "prompts/gemini.jsonnet";
{

    "vertexai-model":: "gemini-1.0-pro-001",
    "vertexai-private-key":: "/vertexai/private.json",
    "vertexai-region":: "us-central1",
    "vertexai-max-output-tokens":: 4096,
    "vertexai-temperature":: 0.0,

    services +: {

	"text-completion": base + {
	    image: images.trustgraph,
	    command: [
		"text-completion-vertexai",
		"-p",
		url.pulsar,
		"-k",
                $["vertexai-private-key"],
		"-r",
                $["vertexai-region"],
                "-x",
                std.toString($["vertexai-max-output-tokens"]),
                "-t",
                std.toString($["vertexai-temperature"]),
                "-m",
                $["vertexai-model"],
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
                $["vertexai-private-key"],
		"-r",
                $["vertexai-region"],
                "-x",
                std.toString($["vertexai-max-output-tokens"]),
                "-t",
                std.toString($["vertexai-temperature"]),
                "-m",
                $["vertexai-model"],
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

