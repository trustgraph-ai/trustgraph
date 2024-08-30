{
    pattern: {
	name: "azure",
        icon: "🤖💬",
        title: "Add Azure LLM endpoint for text completion",
	description: "This pattern integrates an Azure LLM endpoint hosted in the Azure cloud for text completion operations.  You need an Azure subscription and to have an endpoint deployed to be able to use this service.",
        requires: ["pulsar", "trustgraph"],
        features: ["llm"],
	args: [
	]
    },
    module: "components/azure.jsonnet",
}
