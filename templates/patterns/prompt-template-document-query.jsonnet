{
    pattern: {
	name: "prompt-template-document-query",
        title: "Specify document query prompt",
	description: "Prompt for document query / unstructured RAG",
        requires: ["pulsar", "trustgraph"],
        features: ["document-query-prompt"],
	args: [
	    {
		name: "prompt",
		type: "string",
		width: 2000,
		description: "Document query prompt",
                default: "Study the following context. Use only the information provided in the context in your response. Do not speculate if the answer is not found in the provided set of knowledge statements.\n\nHere is the context:\n{documents}\n\nUse only the provided knowledge statements to respond to the following:\n{query}\n",
		required: true,
	    }
	]
    },
    module: import "prompts/gemini.jsonnet",
}
