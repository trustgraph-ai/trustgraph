{
    pattern: {
	name: "openai",
        icon: "🤖💬",
        title: "Deploy OpenAI LLM endpoint support",
	description: "This pattern uses an OpenAI LLM hosted in the OpenAI service.  You need an OpenAI API subscription to be able to use this service.",
        requires: ["pulsar", "trustgraph"],
        features: ["llm"],
	args: [
	]
    },
    module: import "components/openai.jsonnet",
}
