{
    pattern: {
	name: "grafana",
        icon: "📈🧯",
        title: "Deploy Prometheus and Grafana for monitoring and dashboards",
	description: "System monitoring and dashboarding using Grafana and Prometheus",
        requires: ["pulsar", "trustgraph"],
        features: ["prometheus", "grafana"],
	args: [
	]
    },
    module: import "components/grafana.jsonnet",
}
