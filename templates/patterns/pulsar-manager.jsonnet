{
    pattern: {
	name: "pulsar-manager",
        icon: "🏻🛃",
        title: "Deploy Pulsar manager",
	description: "Adds Pulsar Manager which provides a web interface to manage Pulsar.  Pulsar Manager is a large container and deployment requiring over 1GB of RAM, so is not deployed by default",
        requires: ["pulsar"],
        features: ["pulsar-manager"],
	args: [
	    {
		name: "default-admin-password",
		type: "string",
		width: 20,
		description: "Admin password to apply",
                default: "admin98414",
		required: true,
	    }
	]
    },
    module: "components/pulsar.jsonnet",
}
