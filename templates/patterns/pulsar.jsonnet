{
    pattern: {
	name: "pulsar",
        icon: "🌟☄️",
        title: "Deploy foundation messaging fabric",
	description: "Deploy Pulsar as the inter-process messaging fabric.  Pulsar is a Cloud-native, distributed messaging and Streaming. Apache Pulsar is an open-source, distributed messaging and streaming platform built for the cloud.  Trustgraph uses Pulsar to manage the message flow between all components.",
        requires: [],
        features: ["pulsar"],
	args: [
	],
        category: [ "foundation" ],
    },
    module: "components/pulsar.jsonnet",
}
