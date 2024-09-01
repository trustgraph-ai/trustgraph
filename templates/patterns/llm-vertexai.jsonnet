{
    pattern: {
	name: "vertexai",
        icon: "🤖💬",
        title: "Add Google Cloud VertexAI LLM for text completion",
	description: "This pattern integrates a VertexAI endpoint hosted in Google Cloud for text completion operations.  You need a GCP subscription and to have VertexAI enabled to be able to use this service.",
        requires: ["pulsar", "trustgraph"],
        features: ["llm"],
	args: [
	    {
		name: "vertexai-max-output-tokens",
                label: "Maximum output tokens",
		type: "integer",
		description: "Limit on number tokens to generate",
                default: 4096,
		required: true,
            },
	    {
		name: "vertexai-temperature",
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
    module: "components/vertexai.jsonnet",
}
