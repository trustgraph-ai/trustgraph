{
    pattern: {
	name: "triple-store-falkordb",
        icon: "🖇️🙋‍♀️",
        title: "Adds a FalkorDB store configured to act as a triple store.",
	description: "GraphRAG processing needs a triple store.  This pattern adds a FalkorDB store, along with plumbing so that FalkorDB is integrated with GraphRag indexing and querying.",
        requires: ["pulsar", "trustgraph"],
        features: ["falkordb", "triple-store"],
	args: [],
        category: [ "knowledge-graph" ],
    },
    module: "components/falkordb.jsonnet",
}
