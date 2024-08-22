local base = import "base.jsonnet";
local images = import "images.jsonnet";
local url = import "url.jsonnet";
{
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
			cpus: '0.1',
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
		"${AWS_ID_KEY}",
		"-k",
		"${AWS_SECRET_KEY}",
		"-r",
		"us-west-2",
                "-x",
		"4096",
		"-t",
		"0.0",
		"-m",
		"mistral.mixtral-8x7b-instruct-v0:1",
	    ],
            deploy: {
		resources: {
		    limits: {
			cpus: '0.1',
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
		// "-m",
		// "mistral.mistral-large-2407-v1:0",
		"-z",
		"${AWS_ID_KEY}",
		"-k",
		"${AWS_SECRET_KEY}",
		"-r",
		"us-west-2",
                "-x",
		"4096",
		"-t",
		"0.0",
		"-m",
		"mistral.mixtral-8x7b-instruct-v0:1",
		"-i",
		"non-persistent://tg/request/text-completion-rag",
		"-o",
		"non-persistent://tg/response/text-completion-rag-response",
	    ],
            deploy: {
		resources: {
		    limits: {
			cpus: '0.1',
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
}
