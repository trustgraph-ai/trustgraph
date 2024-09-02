{
    pattern: {
	name: "graph-rag-neo4j",
        icon: "🖇️🙋‍♀️",
        title: "Adds a Neo4j store configured to act as a triple store.",
	description: "GraphRAG processing needs a triple store.  This pattern adds a Cassandra store, along with plumbing so that Cassandra is integrated with GraphRag indexing and querying.",
        requires: ["pulsar", "trustgraph"],
        features: ["neo4j", "triple-store"],
	args: [],
        category: [ "knowledge-graph" ],
    },
    module: "components/neo4j.jsonnet",
}
