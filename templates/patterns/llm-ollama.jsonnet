{
    pattern: {
	name: "ollama",
        icon: "🤖💬",
        title: "Add Ollama LLM for text completion",
	description: "This pattern integrates an Ollama service for text completion operations.  You need to have a running Ollama service with the necessary models added in order to be able to use this service.",
        requires: ["pulsar", "trustgraph"],
        features: ["llm"],
	args: [
	]
    },
    module: "components/ollama.jsonnet",
}
