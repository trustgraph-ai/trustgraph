
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
			cpus: '0.1',
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
			cpus: '0.1',
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
			cpus: '0.1',
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
			cpus: '0.1',
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
			cpus: '0.1',
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
			cpus: '0.1',
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
		"prompt-generic",
		"-p",
		url.pulsar,
		"--text-completion-request-queue",
		"non-persistent://tg/request/text-completion",
		"--text-completion-response-queue",
		"non-persistent://tg/response/text-completion-response",
	    ],
            deploy: {
		resources: {
		    limits: {
			cpus: '0.1',
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
			cpus: '0.1',
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

