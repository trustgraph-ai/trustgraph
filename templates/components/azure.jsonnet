local base = import "base.jsonnet";
local images = import "images.jsonnet";
local url = import "url.jsonnet";
{
    services +: {

	"text-completion": base + {
	    image: images.trustgraph,
	    command: [
		"text-completion-azure",
		"-p",
		url.pulsar,
		"-k",
		"${AZURE_TOKEN}",
		"-e",
		"${AZURE_ENDPOINT}",
	    ],
	},

	"text-completion-rag": base + {
	    image: images.trustgraph,
	    command: [
		"text-completion-azure",
		"-p",
		url.pulsar,
		"-k",
		"${AZURE_TOKEN}",
		"-e",
		"${AZURE_ENDPOINT}",
		"-i",
		"non-persistent://tg/request/text-completion-rag",
		"-o",
		"non-persistent://tg/response/text-completion-rag-response",
	    ],
	},
	
    },
}
