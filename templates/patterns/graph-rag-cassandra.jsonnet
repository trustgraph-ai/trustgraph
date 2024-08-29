{
    pattern: {
	name: "graph-rag-cassandra",
        icon: "🖇️🙋‍♀️",
        title: "Add GraphRAG indexing and querying using Cassandra",
	description: "The core Trustgraph deployment does not include a GraphRag store; this pattern adds the Cassandra store, and adds GraphRAG adapters so that Cassandra is integrated with GraphRag indexing and querying.",
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
