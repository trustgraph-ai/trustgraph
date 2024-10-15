{
    pattern: {
	name: "googleaistudio",
        icon: "🤖💬",
        title: "Add GoogleAIStudio for text completion",
	description: "This pattern integrates a GoogleAIStudio LLM service for text completion operations. You need a GoogleAISTudio API key to be able to use this service.",
        requires: ["pulsar", "trustgraph"],
        features: ["llm"],
	args: [
	    {
		name: "googleaistudio-max-output-tokens",
                label: "Maximum output tokens",
		type: "integer",
		description: "Limit on number tokens to generate",
                default: 4096,
		required: true,
            },
	    {
		name: "googleaistudio-temperature",
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
    module: "components/googleaistudio.jsonnet",
}
