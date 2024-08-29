{
    pattern: {
	name: "override-recursive-chunker",
        icon: "✂️🪚",
        title: "Recursive chunker configuration override",
	description: "Configuration values for recursive chunker",
        requires: ["pulsar", "trustgraph"],
        features: [],
	args: [
	    {
		name: "chunk-size",
		type: "int",
		description: "Chunk size value",
                default: 2000,
		required: true,
	    },
	    {
		name: "chunk-overlap",
		type: "int",
		description: "Overlap size value",
                default: 100,
		required: true,
	    }            
	]
    },
    module: "components/cassandra.jsonnet",
}
