{
    pattern: {
	name: "vector-store-qdrant",
        icon: "❓🌐",
        title: "Deploy a vector store using Qdrant",
	description: "Adds the Qdrant open-source vector DB",
        requires: ["pulsar", "trustgraph"],
        features: ["qdrant", "vectordb"],
	args: [
	]
    },
    module: import "components/qdrant.jsonnet",
}
