local base = import "base.jsonnet";
local images = import "images.jsonnet";
local url = import "url.jsonnet";
{
    services +: {

	"text-completion": base + {
	    image: images.trustgraph,
	    command: [
		"text-completion-ollama",
		"-p",
		url.pulsar,
                "-m",
                "gemma2:9b",
		"-r",
		"${OLLAMA_HOST}",
	    ],
	},

	"text-completion-rag": base + {
	    image: images.trustgraph,
	    command: [
		"text-completion-ollama",
		"-p",
		url.pulsar,
                "-m",
                "gemma2:9b",
		"-r",
		"${OLLAMA_HOST}",
		"-i",
		"non-persistent://tg/request/text-completion-rag",
		"-o",
		"non-persistent://tg/response/text-completion-rag-response",
	    ],
	},
	
    },
}
