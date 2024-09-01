{
    pattern: {
	name: "bedrock",
        icon: "🤖💬",
        title: "Add AWS Bedrock for text completion",
	description: "This pattern integrates an AWS Bedrock LLM service hosted in the AWS cloud for text completion operations.  You need an AWS cloud subscription and to have Bedrock configured to be able to use this service.",
        requires: ["pulsar", "trustgraph"],
        features: ["llm"],
	args: [
	],
        category: [ "llm" ],
    },
    module: "components/bedrock.jsonnet",
}
