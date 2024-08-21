
local base = import "base.jsonnet";

local images = import "images.jsonnet";

local url = import "url.jsonnet";

{
    services +: {

	"pdf-decoder": base + {
	    image: images.trustgraph,
	    command: [
		"pdf-decoder",
		"-p",
		url.pulsar,
	    ],
	},

	chunker: base + {
	    image: images.trustgraph,
	    command: [
		"${CHUNKER:-chunker-token}",
		"-p",
		url.pulsar,
                "--chunk-size",
                "250",
                "--chunk-overlap",
                "15",
	    ],
	},

	vectorize: base + {
	    image: images.trustgraph,
	    command: [
		"embeddings-vectorize",
		"-p",
		url.pulsar,
	    ],
	},

	embeddings: base + {
	    image: images.trustgraph,
	    command: [
		"embeddings-hf",
		"-p",
		url.pulsar,
                "-m",
		"all-MiniLM-L6-v2",
	    ],
	},

	"kg-extract-definitions": base + {
	    image: images.trustgraph,
	    command: [
		"kg-extract-definitions",
		"-p",
		url.pulsar,
	    ],
	},

	"kg-extract-relationships": base + {
	    image: images.trustgraph,
	    command: [
		"kg-extract-relationships",
		"-p",
		url.pulsar,
	    ],
	},

	"graph-rag": base + {
	    image: images.trustgraph,
	    command: [
		"graph-rag",
		"-p",
		url.pulsar,
		"--prompt-request-queue",
		"non-persistent://tg/request/prompt-rag",
		"--prompt-response-queue",
		"non-persistent://tg/response/prompt-rag-response",
		"--entity-limit",
		"50",
		"--triple-limit",
		"30",
		"--max-subgraph-size",
		"3000",
	    ],
	},

	"prompt": base + {
	    image: images.trustgraph,
	    command: [
		"prompt-generic",
		"-p",
		url.pulsar,
		"--text-completion-request-queue",
		"non-persistent://tg/request/text-completion",
		"--text-completion-response-queue",
		"non-persistent://tg/response/text-completion-response",
	    ],
	},

	"prompt-rag": base + {
	    image: images.trustgraph,
	    command: [
		"prompt-generic",
		"-p",
		url.pulsar,
                "-i",
		"non-persistent://tg/request/prompt-rag",
                "-o",
		"non-persistent://tg/response/prompt-rag-response",
		"--text-completion-request-queue",
		"non-persistent://tg/request/text-completion-rag",
		"--text-completion-response-queue",
		"non-persistent://tg/response/text-completion-rag-response",
	    ],
	},

    },

}

