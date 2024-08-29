{
    pattern: {
	name: "graph-rag-neo4j",
        icon: "🖇️🙋‍♀️",
	description: "Adds Neo4j community edition and Graph RAG components",
        title: "Deploys GraphRAG indexing and querying using a Neo4j community edition store",
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
