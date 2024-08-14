local base = import "base.jsonnet";
local images = import "images.jsonnet";
local url = import "url.jsonnet";
{
    services +: {

	"text-completion": base + {
	    image: images.trustgraph,
	    command: [
		"text-completion-vertexai",
		"-p",
		url.pulsar,
		"-k",
		"/vertexai/private.json",
		"-r",
		"us-west1",
	    ],
	    volumes: [
		"./vertexai:/vertexai"
	    ],
	},

	"text-completion-rag": base + {
	    image: images.trustgraph,
	    command: [
		"text-completion-vertexai",
		"-p",
		url.pulsar,
		"-k",
		"/vertexai/private.json",
		"-r",
		"us-west1",
		"-i",
		"non-persistent://tg/request/text-completion-rag",
		"-o",
		"non-persistent://tg/response/text-completion-rag-response",
	    ],
	    volumes: [
		"./vertexai:/vertexai"
	    ],
	},

    },
}
