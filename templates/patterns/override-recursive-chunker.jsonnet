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
		type: "integer",
		description: "Chunk size value",
                default: 2000,
		required: true,
	    },
	    {
		name: "chunk-overlap",
		type: "integer",
		description: "Overlap size value",
                default: 100,
		required: true,
	    }            
	],
        category: [ "chunking" ],
    },
    module: "components/cassandra.jsonnet",
}
