{
    pattern: {
	name: "trustgraph-base",
        icon: "🤝😂",
        title: "Add Trustgraph base processing flows",
	description: "This pattern adds a core set of Trustgraph flows, including PDF ingest, chunking, embeddings, and knowledge graph extraction.  You should also consider adding an LLM and at least one RAG processing flow.",
        requires: ["pulsar"],
        features: ["trustgraph"],
	args: [
	    {
		name: "example",
		type: "string",
		width: 20,
		description: "An example argument",
		required: false,
	    }
	]
    },
    module: "components/trustgraph.jsonnet",
}
