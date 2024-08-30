{
    pattern: {
	name: "openai",
        icon: "🤖💬",
        title: "Add OpenAI LLM endpoint for text completion",
	description: "This pattern integrates an OpenAI LLM service for text completion operations.  You need an OpenAI subscription and have an API key to be able to use this service.",
        requires: ["pulsar", "trustgraph"],
        features: ["llm"],
	args: [
	]
    },
    module: "components/openai.jsonnet",
}
