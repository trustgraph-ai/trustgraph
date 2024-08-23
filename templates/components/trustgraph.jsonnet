
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

	vectorize: base + {
	    image: images.trustgraph,
	    command: [
		"embeddings-vectorize",
		"-p",
		url.pulsar,
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

	embeddings: base + {
	    image: images.trustgraph,
	    command: [
		"embeddings-hf",
		"-p",
		url.pulsar,
                "-m",
		"all-MiniLM-L6-v2",
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

	"kg-extract-definitions": base + {
	    image: images.trustgraph,
	    command: [
		"kg-extract-definitions",
		"-p",
		url.pulsar,
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

	"kg-extract-relationships": base + {
	    image: images.trustgraph,
	    command: [
		"kg-extract-relationships",
		"-p",
		url.pulsar,
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
                "<instructions>\nStudy the following text and derive definitions for any discovered entities.\nDo not provide definitions for entities whose definitions are incomplete\nor unknown.\nOutput relationships in JSON format as an arary of objects with fields:\n- entity: the name of the entity\n- definition: English text which defines the entity\n</instructions>\n\n<text>\n{text}\n</text>\n\n<requirements>\nYou will respond only with raw JSON format data. Do not provide\nexplanations. Do not use special characters in the abstract text. The\nabstract will be written as plain text.  Do not add markdown formatting\nor headers or prefixes.  Do not include null or unknown definitions.\n</requirements>",
                "--relationship-template",
                "<instructions>\nStudy the following text and derive entity relationships.  For each\nrelationship, derive the subject, predicate and object of the relationship.\nOutput relationships in JSON format as an arary of objects with fields:\n- subject: the subject of the relationship\n- predicate: the predicate\n- object: the object of the relationship\n- object-entity: false if the object is a simple data type: name, value or date.  true if it is an entity.\n</instructions>\n\n<text>\n{text}\n</text>\n\n<requirements>\nYou will respond only with raw JSON format data. Do not provide\nexplanations. Do not use special characters in the abstract text. The\nabstract must be written as plain text.  Do not add markdown formatting\nor headers or prefixes.\n</requirements>",
                "--knowledge-query-template",
                "Study the following set of knowledge statements. The statements are written in Cypher format that has been extracted from a knowledge graph. Use only the provided set of knowledge statements in your response. Do not speculate if the answer is not found in the provided set of knowledge statements.\n\nHere's the knowledge statements:\n{graph}\n\nUse only the provided knowledge statements to respond to the following:\n{query}\n",
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

