{
    pattern: {
	name: "graph-rag-neo4j",
        icon: "🖇️🙋‍♀️",
        title: "Deploys GraphRAG indexing and querying using a Neo4j community edition store",
	description: "The core Trustgraph deployment does not include a GraphRag store; this pattern adds the Neo4j store, and adds GraphRAG adapters so that Neo4j is integrated with GraphRag indexing and querying.",
        requires: ["pulsar", "trustgraph"],
        features: ["neo4j", "rag"],
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
    module: "components/neo4j.jsonnet",
}
