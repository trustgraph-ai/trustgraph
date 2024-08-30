{
    pattern: {
	name: "cohere",
        icon: "🤖💬",
        title: "Add Cohere LLM endpoint for text completion",
	description: "This pattern integrates the Cohere LLM service for text completion operations.  You need a Cohere subscription and API keys to be able to use this service.",
        requires: ["pulsar", "trustgraph"],
        features: ["llm"],
	args: [
	]
    },
    module: "components/cohere.jsonnet",
}
