{
    pattern: {
	name: "vector-store-milvus",
        title: "Deploy a vector store using Milvus",
	description: "Adds the Milvus open-source vector DB",
        requires: ["pulsar", "trustgraph"],
        features: ["milvus", "vectordb"],
	args: [
	]
    },
    module: import "components/milvus.jsonnet",
}
