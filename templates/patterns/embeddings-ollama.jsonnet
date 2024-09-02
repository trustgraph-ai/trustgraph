{
    pattern: {
	name: "embeddings-ollama",
        icon: "🤖💬",
        title: "Add embeddings model hosted on Ollama",
	description: "This pattern integrates an embeddings model based on HuggingFace sentence-transformer library.",
        requires: ["pulsar", "trustgraph"],
        features: ["llm"],
	args: [
	    {
		name: "embeddings-model",
                label: "Embeddings model",
		type: "select",
		description: "Embeddings model for sentence analysis",
                options: [
                  { id: "mxbai-embed-large", description: "mxbai-embed-large" },
                ],
                default: "mxbai-embed-large",
		required: true,
	    },
	    {
		name: "ollama-url",
                label: "URL",
		type: "text",
		width: 120,
		description: "URL of the Ollama service",
                default: "http://ollama:11434",
		required: true,
	    },
	],
        category: [ "embeddings" ],
    },
    module: "components/embeddings-hf.jsonnet",
}
