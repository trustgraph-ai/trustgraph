{
    pattern: {
	name: "mistral",
        icon: "🤖💬",
        title: "Add Mistral LLM endpoint for text completion",
	description: "This pattern integrates a Mistral LLM service for text completion operations.  You need a Mistral subscription and have an API key to be able to use this service.",
        requires: ["pulsar", "trustgraph"],
        features: ["llm"],
	args: [
	    {
		name: "mistral-max-output-tokens",
                label: "Maximum output tokens",
		type: "integer",
		description: "Limit on number tokens to generate",
                default: 4096,
		required: true,
            },
	    {
		name: "mistral-temperature",
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
    module: "components/mistral.jsonnet",
}
