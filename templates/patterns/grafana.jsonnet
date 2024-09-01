{
    pattern: {
	name: "grafana",
        icon: "📈🧯",
        title: "Add Prometheus and Grafana for monitoring and dashboards",
	description: "System monitoring and dashboarding using Grafana and Prometheus",
        requires: ["pulsar", "trustgraph"],
        features: ["prometheus", "grafana"],
	args: [
	],
        category: ["monitoring"],
    },
    module: "components/grafana.jsonnet",
}
