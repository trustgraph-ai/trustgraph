{
    pattern: {
	name: "kq-query-prompt",
        icon: "📜️️💬",
        title: "Specify knowledge query prompt",
	description: "Prompt for definition extraction",
        requires: ["pulsar", "trustgraph"],
        features: ["kg-query-prompt"],
	args: [
	    {
		name: "prompt",
		type: "string",
		width: 2000,
		description: "Knowledge graph extraction prompt",
                default: "Study the following set of knowledge statements. The statements are written in Cypher format that has been extracted from a knowledge graph. Use only the provided set of knowledge statements in your response. Do not speculate if the answer is not found in the provided set of knowledge statements.\n\nHere's the knowledge statements:\n{graph}\n\nUse only the provided knowledge statements to respond to the following:\n{query}\n",
		required: true,
	    }
	]
    },
    module: "prompts/gemini.jsonnet",
}
