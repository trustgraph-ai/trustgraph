{
    pattern: {
	name: "bedrock",
        title: "Deploy AWS Bedrock LLM endpoint support",
	description: "This pattern uses an AWS Bedrock LLM hosted in the AWS cloud service.  You need an AWS subscription to be able to use this service.",
        requires: ["pulsar", "trustgraph"],
        features: ["llm"],
	args: [
	]
    },
    module: import "components/bedrock.jsonnet",
}
