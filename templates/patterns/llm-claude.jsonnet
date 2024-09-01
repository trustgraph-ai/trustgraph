{
    pattern: {
	name: "claude",
        icon: "🤖💬",
        title: "Add Anthropic Claude for text completion",
	description: "This pattern integrates an Anthropic Claude LLM service for text completion operations.  You need a Claude subscription to be able to use this service.",
        requires: ["pulsar", "trustgraph"],
        features: ["llm"],
	args: [
	    {
		name: "claude-max-output-tokens",
                label: "Maximum output tokens",
		type: "integer",
		description: "Limit on number tokens to generate",
                default: 4096,
		required: true,
            },
	    {
		name: "claude-temperature",
                label: "Temperature",
		type: "slider",
		description: "Controlling predictability / creativity balance",
                min: 0,
                max: 1,
                step: 0.05,
                default: 0.5,
            },
	],
        category: [ "llm" ],
    },
    module: "components/claude.jsonnet",
}
