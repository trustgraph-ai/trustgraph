{
    pattern: {
	name: "triple-store-neo4j",
        icon: "🖇️🙋‍♀️",
        title: "Adds a Neo4j store configured to act as a triple store.",
	description: "GraphRAG processing needs a triple store.  This pattern adds a Neo4j store, along with plumbing so that Neo4j is integrated with GraphRag indexing and querying.",
        requires: ["pulsar", "trustgraph"],
        features: ["neo4j", "triple-store"],
	args: [],
        category: [ "knowledge-graph" ],
    },
    module: "components/neo4j.jsonnet",
}
