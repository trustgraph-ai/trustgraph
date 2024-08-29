{
    pattern: {
	name: "cohere",
        icon: "🤖💬",
        title: "Deploy Cohere LLM endpoint support",
	description: "This pattern uses a Cohere LLM hosted in the Cohere service.  You need a Cohere subscription to be able to use this service.",
        requires: ["pulsar", "trustgraph"],
        features: ["llm"],
	args: [
	]
    },
    module: "components/cohere.jsonnet",
}
