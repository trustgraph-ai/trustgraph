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
	    ],
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
		"-i",
		"non-persistent://tg/request/text-completion-rag",
		"-o",
		"non-persistent://tg/response/text-completion-rag-response",
	    ],
	},
	
    },
}
