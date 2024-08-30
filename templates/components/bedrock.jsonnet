local base = import "base/base.jsonnet";
local images = import "values/images.jsonnet";
local url = import "values/url.jsonnet";
local prompts = import "prompts/mixtral.jsonnet";
{
    "aws-id-key":: "${AWS_ID_KEY}",
    "aws-secret-key":: "${AWS_SECRET_KEY}",
    "aws-region":: "us-west-2",
    "bedrock-max-output-tokens":: 4096,
    "bedrock-temperature":: 0.0,
    "bedrock-model":: "mistral.mixtral-8x7b-instruct-v0:1",

    services +: {

	chunker: base + {
	    image: images.trustgraph,
	    command: [
		"chunker-recursive",
		"-p",
		url.pulsar,
		"--chunk-size",
		"2000",
		"--chunk-overlap",
		"100",
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

	"text-completion": base + {
	    image: images.trustgraph,
	    command: [
		"text-completion-bedrock",
		"-p",
		url.pulsar,
		"-z",
		$["aws-id-key"],
		"-k",
		$["aws-secret-key"],
		"-r",
		$["aws-region"],
                "-x",
                std.toString($["bedrock-max-output-tokens"]),
		"-t",
                std.toString($["bedrock-temperature"]),
		"-m",
		$["bedrock-model"],
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
		"text-completion-bedrock",
		"-p",
		url.pulsar,
		"-z",
		$["aws-id-key"],
		"-k",
		$["aws-secret-key"],
		"-r",
		$["aws-region"],
                "-x",
                std.toString($["bedrock-max-output-tokens"]),
		"-t",
                std.toString($["bedrock-temperature"]),
		"-m",
		$["bedrock-model"],
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


