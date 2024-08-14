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
		"1000",
		"--chunk-overlap",
		"50",
	    ],
	},

	"text-completion": base + {
	    image: images.trustgraph,
	    command: [
		"text-completion-cohere",
		"-p",
		url.pulsar,
		"-k",
		"${COHERE_KEY}",
	    ],
	},

	"text-completion-rag": base + {
	    image: images.trustgraph,
	    command: [
		"text-completion-cohere",
		"-p",
		url.pulsar,
		"-k",
		"${COHERE_KEY}",
		"-i",
		"non-persistent://tg/request/text-completion-rag",
		"-o",
		"non-persistent://tg/response/text-completion-rag-response",
	    ],
	},

    },
}
