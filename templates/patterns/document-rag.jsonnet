{
    pattern: {
	name: "document-rag",
        icon: "🤝😂",
        title: "Add DocumentRAG processing flow",
	description: "This pattern adds DocumentRAG components for extracting and querying documents based on document embeddings.  You should make sure a vector store is included in your plan.",
        requires: ["pulsar", "trustgraph", "llm"],
        features: ["document-rag"],
	args: [
	],
        category: [ "processing" ],
    },
    module: "components/trustgraph.jsonnet",
}
