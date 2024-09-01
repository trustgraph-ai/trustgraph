{
    pattern: {
	name: "azure",
        icon: "🤖💬",
        title: "Add Azure LLM endpoint for text completion",
	description: "This pattern integrates an Azure LLM endpoint hosted in the Azure cloud for text completion operations.  You need an Azure subscription and to have an endpoint deployed to be able to use this service.",
        requires: ["pulsar", "trustgraph"],
        features: ["llm"],
	args: [
	    {
		name: "azure-max-output-tokens",
                label: "Maximum output tokens",
		type: "integer",
		description: "Limit on number tokens to generate",
                default: 4096,
		required: true,
            },
	    {
		name: "azure-temperature",
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
