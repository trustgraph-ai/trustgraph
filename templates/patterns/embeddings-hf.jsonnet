{
    pattern: {
	name: "embeddings-hf",
        icon: "🤖💬",
        title: "Add embeddings model which uses HuggingFace models",
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
                  { id: "all-MiniLM-L6-v2", description: "all-MiniLM-L6-v2" },
                  { id: "mixedbread-ai/mxbai-embed-large-v1", description: "mxbai-embed-large-v1" },
                ],
                default: "all-MiniLM-L6-v2",
		required: true,
	    },
	],
        category: [ "embeddings" ],
    },
    module: "components/embeddings-hf.jsonnet",
}
