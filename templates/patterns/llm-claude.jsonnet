{
    pattern: {
	name: "claude",
        icon: "🤖💬",
        title: "Deploy Anthropic Claude LLM support",
	description: "This pattern uses an Anthropic Claude LLM hosted in the Anthropic cloud service.  You need an Anthropic API subscription to be able to use this service.",
        requires: ["pulsar", "trustgraph"],
        features: ["llm"],
	args: [
	]
    },
    module: import "components/claude.jsonnet",
}
