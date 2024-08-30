{
    pattern: {
	name: "pulsar-manager",
        icon: "🏻🛃",
        title: "Add Pulsar Manager",
	description: "Adds Pulsar Manager which provides a web interface to manage Pulsar.  Pulsar Manager is a large container and deployment requiring over 1GB of RAM, so is not deployed by default.  This is not a required component, it may be useful to help manage a large operational deployment.",
        requires: ["pulsar"],
        features: ["pulsar-manager"],
	args: [
	    {
		name: "default-admin-password",
		type: "string",
		width: 20,
		description: "Admin password to apply",
                default: "pulsaradmin",
		required: true,
	    }
	]
    },
    module: "components/pulsar.jsonnet",
}
