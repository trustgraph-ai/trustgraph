{
    pattern: {
	name: "azure-openai",
        icon: "🤖💬",
        title: "Add Azure OpenAI LLM endpoint for text completion",
	description: "This pattern integrates an Azure OpenAI LLM endpoint hosted in the Azure cloud for text completion operations.  You need an Azure subscription to be able to use this service.",
        requires: ["pulsar", "trustgraph"],
        features: ["llm"],
	args: [
	    {
		name: "azure-openai-max-output-tokens",
                label: "Maximum output tokens",
		type: "integer",
		description: "Limit on number tokens to generate",
                default: 4096,
		required: true,
            },
	    {
		name: "azure-openai-temperature",
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
    module: "components/azure.jsonnet",
}
