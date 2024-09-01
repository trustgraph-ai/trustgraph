{
    pattern: {
	name: "cohere",
        icon: "🤖💬",
        title: "Add Cohere LLM endpoint for text completion",
	description: "This pattern integrates the Cohere LLM service for text completion operations.  You need a Cohere subscription and API keys to be able to use this service.",
        requires: ["pulsar", "trustgraph"],
        features: ["llm"],
	args: [
	    {
		name: "cohere-max-output-tokens",
                label: "Maximum output tokens",
		type: "integer",
		description: "Limit on number tokens to generate",
                default: 4096,
		required: true,
            },
	    {
		name: "cohere-temperature",
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
    module: "components/cohere.jsonnet",
}
