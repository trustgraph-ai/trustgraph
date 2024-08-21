local base = import "base.jsonnet";
local images = import "images.jsonnet";
local url = import "url.jsonnet";
{
    services +: {

	chunker: base + {
	    image: images.trustgraph,
	    command: [
		"${CHUNKER:-chunker-token}",
		"-p",
		url.pulsar,
		"--chunk-size",
		"150",
		"--chunk-overlap",
		"10",
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
                "-t",
                "0.0",
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
                "-t",
                "0.0",
		"-i",
		"non-persistent://tg/request/text-completion-rag",
		"-o",
		"non-persistent://tg/response/text-completion-rag-response",
	    ],
	},

    },
}
