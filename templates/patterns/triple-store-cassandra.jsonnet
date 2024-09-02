{
    pattern: {
	name: "cassandra",
        icon: "🖇️🙋‍♀️",
        title: "Adds a Cassandra store configured to act as a triple store",
	description: "GraphRAG processing needs a triple store.  This pattern adds a Cassandra store, along with plumbing so that Cassandra is integrated with GraphRag indexing and querying.",
        requires: ["pulsar", "trustgraph"],
        features: ["cassandra", "triple-store"],
        args: [],
        category: ["knowledge-graph"],
    },
    module: "components/cassandra.jsonnet",
}
