local base = import "base/base.jsonnet";
local images = import "values/images.jsonnet";
local url = import "values/url.jsonnet";
local prompts = import "prompts/openai.jsonnet";
{

    "openai-key":: "${OPENAI_KEY}",
    "openai-max-output-tokens":: 4096,
    "openai-temperature":: 0.0,
    "openai-model":: "GPT-3.5-Turbo",

    services +: {

	"text-completion": base + {
	    image: images.trustgraph,
	    command: [
		"text-completion-openai",
		"-p",
		url.pulsar,
		"-k",
		$["openai-key"],
                "-x",
                std.toString($["openai-max-output-tokens"]),
                "-t",
                std.toString($["openai-temperature"]),
                "-m",
                $["openai-model"],
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
		$["openai-key"],
                "-x",
                std.toString($["openai-max-output-tokens"]),
                "-t",
                std.toString($["openai-temperature"]),
                "-m",
                $["openai-model"],
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
