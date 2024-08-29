{
    pattern: {
	name: "graph-rag-cassandra",
        icon: "🖇️🙋‍♀️",
        title: "Deploys GraphRAG indexing and querying using Cassandra",
	description: "Adds Cassandra and Graph RAG components for query and indexing of data.",
        requires: ["pulsar", "trustgraph"],
        features: ["cassandra", "rag"],
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
    module: "components/cassandra.jsonnet",
}
