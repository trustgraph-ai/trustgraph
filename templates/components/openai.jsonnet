local base = import "base.jsonnet";
local images = import "images.jsonnet";
local url = import "url.jsonnet";
{
    services +: {

	"text-completion": base + {
	    image: images.trustgraph,
	    command: [
		"text-completion-openai",
		"-p",
		url.pulsar,
		"-k",
		"${OPENAI_KEY}",
                "-x",
                "4096",
                "-t",
                "0.0",
	    ],
	},

	"text-completion-rag": base + {
	    image: images.trustgraph,
	    command: [
		"text-completion-openai",
		"-p",
		url.pulsar,
		"-k",
		"${OPENAI_KEY}",
                "-x",
                "4096",
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
