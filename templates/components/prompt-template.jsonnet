
// For VertexAI Gemini

local base = import "base/base.jsonnet";
local images = import "values/images.jsonnet";
local url = import "values/url.jsonnet";
local default_prompts = import "prompts/default-prompts.jsonnet";

default_prompts + {

    services +: {

	"prompt": base + {
	    image: images.trustgraph,
	    command: [
		"prompt-template",
		"-p",
		url.pulsar,
		"--text-completion-request-queue",
		"non-persistent://tg/request/text-completion",
		"--text-completion-response-queue",
		"non-persistent://tg/response/text-completion-response",
                "--definition-template",
                $["prompt-definition-template"],
                "--relationship-template",
                $["prompt-relationship-template"],
                "--knowledge-query-template",
                $["prompt-knowledge-query-template"],
                "--document-query-template",
                $["prompt-document-query-template"],
                "--rows-template",
                $["prompt-rows-template"],
	    ],
            deploy: {
		resources: {
		    limits: {
			cpus: '0.5',
			memory: '128M'
		    },
		    reservations: {
			cpus: '0.1',
			memory: '128M'
		    }
		}
	    },
	},

	"prompt-rag": base + {
	    image: images.trustgraph,
	    command: [
		"prompt-template",
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
                "--definition-template",
                $["prompt-definition-template"],
                "--relationship-template",
                $["prompt-relationship-template"],
                "--knowledge-query-template",
                $["prompt-knowledge-query-template"],
                "--document-query-template",
                $["prompt-document-query-template"],
                "--rows-template",
                $["prompt-rows-template"],
	    ],
            deploy: {
		resources: {
		    limits: {
			cpus: '0.5',
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
