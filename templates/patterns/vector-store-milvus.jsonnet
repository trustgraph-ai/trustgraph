{
    pattern: {
	name: "vector-store-milvus",
        icon: "❓🌐",
        title: "Add Milvus, a vector embeddings store",
	description: "The Trustgraph core does not include a vector store by default.  This configuration pattern adds a simple Milvus store and integrates with embeddings handling.",
        requires: ["pulsar", "trustgraph"],
        features: ["milvus", "vectordb"],
	args: [
	],
        category: [ "vector-store" ],
    },
    module: "components/milvus.jsonnet",
}

