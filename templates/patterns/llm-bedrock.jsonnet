{
    pattern: {
	name: "bedrock",
        icon: "🤖💬",
        title: "Add AWS Bedrock for text completion",
	description: "This pattern integrates an AWS Bedrock LLM service hosted in the AWS cloud for text completion operations.  You need an AWS cloud subscription and to have Bedrock configured to be able to use this service.",
        requires: ["pulsar", "trustgraph"],
        features: ["llm"],
	args: [
	    {
		name: "bedrock-max-output-tokens",
                label: "Maximum output tokens",
		type: "integer",
		description: "Limit on number tokens to generate",
                default: 4096,
		required: true,
            },
	    {
		name: "bedrock-temperature",
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
    module: "components/bedrock.jsonnet",
}
