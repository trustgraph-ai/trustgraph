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
		name: "embeddings-model",
                label: "Embeddings model",
		type: "select",
		description: "Embeddings model for sentence analysis",
                options: [
                  { id: "all-MiniLM-L6-v2", description: "all-MiniLM-L6-v2" },
                ],
                default: "all-MiniLM-L6-v2",
		required: true,
	    },
	    {
		name: "graph-rag-entity-limit",
                label: "GraphRAG entity query limit",
		type: "integer",
		description: "Limit on entities to fetch from vector store",
                default: 50,
		required: true,
            },
	    {
		name: "graph-rag-triple-limit",
                label: "GraphRAG triple query limit",
		type: "integer",
		description: "Limit on triples to fetch from triple store",
                default: 30,
		required: true,
            },
	    {
		name: "graph-rag-max-subgraph-size",
                label: "GraphRAG maximum subgraph size",
		type: "integer",
		description: "Limit on size of subgraph to present to text-completion model",
                default: 3000,
		required: true,
            },
	],
        category: [ "foundation" ],
    },
    module: "components/trustgraph.jsonnet",
}
