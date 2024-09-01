{
    pattern: {
	name: "vertexai",
        icon: "🤖💬",
        title: "Add Google Cloud VertexAI LLM for text completion",
	description: "This pattern integrates a VertexAI endpoint hosted in Google Cloud for text completion operations.  You need a GCP subscription and to have VertexAI enabled to be able to use this service.",
        requires: ["pulsar", "trustgraph"],
        features: ["llm"],
	args: [
	],
        category: [ "llm" ],
    },
    module: "components/vertexai.jsonnet",
}
