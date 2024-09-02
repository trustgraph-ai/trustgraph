local base = import "base/base.jsonnet";
local images = import "values/images.jsonnet";
local url = import "values/url.jsonnet";
local prompts = import "prompt-template.jsonnet";

{

    "embeddings-model":: "all-MiniLM-L6-v2",

    services +: {

	embeddings: base + {
	    image: images.trustgraph,
	    command: [
		"embeddings-hf",
		"-p",
		url.pulsar,
                "-m",
		$["embeddings-model"],
	    ],
            deploy: {
		resources: {
		    limits: {
			cpus: '1.0',
			memory: '256M'
		    },
		    reservations: {
			cpus: '0.5',
			memory: '256M'
		    }
		}
            },
	},

    }

} + prompts



