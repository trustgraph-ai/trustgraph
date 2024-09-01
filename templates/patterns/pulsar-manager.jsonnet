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
		name: "initial-admin-password",
                label: "Password",
		type: "text",
		width: 40,
		description: "Admin password to apply at initialisation",
                default: "pulsaradmin",
		required: true,
	    },
	],
        category: [ "foundation" ],
    },
    module: "components/pulsar.jsonnet",
}
