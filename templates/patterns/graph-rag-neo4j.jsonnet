{
    pattern: {
	name: "graph-rag-neo4j",
        icon: "🖇️🙋‍♀️",
        title: "Deploys GraphRAG indexing and querying using a Neo4j community edition store",
	description: "The core Trustgraph deployment does not include a GraphRag store; this pattern adds the Neo4j store, and adds GraphRAG adapters so that Neo4j is integrated with GraphRag indexing and querying.",
        requires: ["pulsar", "trustgraph"],
        features: ["neo4j", "triple-store"],
	args: [],
        category: [ "knowledge-graph" ],
    },
    module: "components/neo4j.jsonnet",
}
