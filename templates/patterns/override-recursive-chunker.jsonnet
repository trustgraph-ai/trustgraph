{
    pattern: {
	name: "override-recursive-chunker",
        icon: "✂️🪚",
        title: "Replace default chunker with recursive chunker",
	description: "The default chunker used in Trustgraph core is a token-based chunker.  This pattern replaces that with a recursive chunker, and allows ou to configure the chunking parameters.",
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
