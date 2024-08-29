{
    pattern: {
	name: "vector-store-qdrant",
        icon: "❓🌐",
        title: "Adds Qdrant, a vector embeddings store",
	description: "The Trustgraph core does not include a vector store by default.  This configuration pattern adds a simple Qdrant store and integrates with embeddings handling.",
        requires: ["pulsar", "trustgraph"],
        features: ["qdrant", "vectordb"],
	args: [
	]
    },
    module: "components/qdrant.jsonnet",
}
