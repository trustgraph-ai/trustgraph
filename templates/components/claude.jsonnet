local base = import "base/base.jsonnet";
local images = import "values/images.jsonnet";
local url = import "values/url.jsonnet";
local prompts = import "prompts/mixtral.jsonnet";
{

    "claude-key":: "${CLAUDE_KEY}",
    "claude-max-output-tokens":: 4096,
    "claude-temperature":: 0.0,

    services +: {

	"text-completion": base + {
	    image: images.trustgraph,
	    command: [
		"text-completion-claude",
		"-p",
		url.pulsar,
		"-k",
		$["claude-key"],
                "-x",
                std.toString($["claude-max-output-tokens"]),
                "-t",
                std.toString($["claude-temperature"]),
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
		"text-completion-claude",
		"-p",
		url.pulsar,
		"-k",
		$["claude-key"],
                "-x",
                std.toString($["claude-max-output-tokens"]),
                "-t",
                std.toString($["claude-temperature"]),
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
