{
    pattern: {
	name: "pulsar",
        title: "Deploy messaging foundation support",
	description: "Cloud-native, distributed messaging and Streaming. Apache Pulsar is an open-source, distributed messaging and streaming platform built for the cloud.  Trustgraph uses Pulsar to manage the message flow between all components.",
        requires: [],
        features: ["pulsar"],
	args: [
	]
    },
    module: import "components/pulsar.jsonnet",
}
