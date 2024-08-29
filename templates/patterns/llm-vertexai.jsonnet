{
    pattern: {
	name: "vertexai",
        icon: "🤖💬",
        title: "Deploy Google Cloud VertexAI LLM support",
	description: "This pattern uses an VertexAI LLM hosted in Google Cloud.  You need a Google Cloud subscription to be able to use this service.",
        requires: ["pulsar", "trustgraph"],
        features: ["llm"],
	args: [
	]
    },
    module: "components/vertexai.jsonnet",
}
