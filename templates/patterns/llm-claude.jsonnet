{
    pattern: {
	name: "claude",
        icon: "🤖💬",
        title: "Add Anthropic Claude for text completion",
	description: "This pattern integrates an Anthropic Claude LLM service for text completion operations.  You need a Claude subscription to be able to use this service.",
        requires: ["pulsar", "trustgraph"],
        features: ["llm"],
	args: [
	],
        category: [ "llm" ],
    },
    module: "components/claude.jsonnet",
}
