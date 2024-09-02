{
    pattern: {
	name: "graph-rag",
        icon: "🤝😂",
        title: "Add GraphRAG processing flow",
	description: "This pattern adds GraphRAG components for extracting and querying graph edges.  You should make sure a triple store and vector store are included in your plan.",
        requires: ["pulsar", "trustgraph", "llm"],
        features: ["graph-rag"],
	args: [
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
        category: [ "processing" ],
    },
    module: "components/trustgraph.jsonnet",
}
