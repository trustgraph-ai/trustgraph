{
    pattern: {
	name: "ollama",
        icon: "🤖💬",
        title: "Deploy Ollama LLM support",
	description: "This pattern uses an Ollama LLM hosting service.  You need an Ollama service to be running and have LLM models pulled using ollama pull.",
        requires: ["pulsar", "trustgraph"],
        features: ["llm"],
	args: [
	]
    },
    module: import "components/ollama.jsonnet",
}
