{
    pattern: {
	name: "openai",
        icon: "🤖💬",
        title: "Add OpenAI LLM endpoint for text completion",
	description: "This pattern integrates an OpenAI LLM service for text completion operations.  You need an OpenAI subscription and have an API key to be able to use this service.",
        requires: ["pulsar", "trustgraph"],
        features: ["llm"],
	args: [
	    {
		name: "openai-max-output-tokens",
                label: "Maximum output tokens",
		type: "integer",
		description: "Limit on number tokens to generate",
                default: 4096,
		required: true,
            },
	    {
		name: "openai-temperature",
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
    module: "components/openai.jsonnet",
}
