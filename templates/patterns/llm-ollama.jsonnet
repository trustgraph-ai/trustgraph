{
    pattern: {
	name: "ollama",
        icon: "🤖💬",
        title: "Add Ollama LLM for text completion",
	description: "This pattern integrates an Ollama service for text completion operations.  You need to have a running Ollama service with the necessary models added in order to be able to use this service.",
        requires: ["pulsar", "trustgraph"],
        features: ["llm"],
	args: [
	    {
		name: "ollama-max-output-tokens",
                label: "Maximum output tokens",
		type: "integer",
		description: "Limit on number tokens to generate",
                default: 4096,
		required: true,
            },
	    {
		name: "ollama-temperature",
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
    module: "components/ollama.jsonnet",
}
