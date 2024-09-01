{
    pattern: {
	name: "prompt-template-document-query",
        icon: "📜️️💬",
        title: "Override document query prompt",
	description: "This pattern overrides the default document query prompt used for DocumentRAG allowing you to specify your own prompt.",
        requires: ["pulsar", "trustgraph"],
        features: ["document-query-prompt"],
	args: [
	    {
		name: "prompt-document-query-template",
		type: "multiline",
		size: 2000,
                rows: 10,
		description: "Document query prompt",
                default: "Study the following context. Use only the information provided in the context in your response. Do not speculate if the answer is not found in the provided set of knowledge statements.\n\nHere is the context:\n{documents}\n\nUse only the provided knowledge statements to respond to the following:\n{query}\n",
		required: true,
	    }
	],
        category: [ "prompting" ],
    },
    module: "components/null.jsonnet",
}
