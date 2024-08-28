{
    pattern: {
	name: "azure",
        title: "Deploy Azure LLM endpoint support",
	description: "This pattern uses an Azure LLM endpoint hosted in the Azure cloud.  You need an Azure subscription and to have an endpoint deployed to be able to use this service.",
        requires: ["pulsar", "trustgraph"],
        features: ["llm"],
	args: [
	]
    },
    module: import "components/azure.jsonnet",
}
