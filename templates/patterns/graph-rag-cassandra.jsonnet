{
    pattern: {
	name: "graph-rag-cassandra",
        icon: "🖇️🙋‍♀️",
        title: "Add GraphRAG indexing and querying using Cassandra",
	description: "The core Trustgraph deployment does not include a GraphRag store; this pattern adds the Cassandra store, and adds GraphRAG adapters so that Cassandra is integrated with GraphRag indexing and querying.",
        requires: ["pulsar", "trustgraph"],
        features: ["cassandra", "rag"],
        args: [],
    },
    module: "components/cassandra.jsonnet",
}
