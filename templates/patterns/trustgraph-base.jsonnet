{
    pattern: {
	name: "trustgraph-base",
        title: "Core Trustgraph processing flows",
	description: "Adds core Trustgraph flows",
        requires: ["pulsar"],
        features: ["trustgraph"],
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
    module: import "components/trustgraph.jsonnet",
}
