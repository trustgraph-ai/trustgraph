local base = import "base/base.jsonnet";
local images = import "values/images.jsonnet";
{

    // FIXME: Should persist *something*
    volumes +: {
    },

    services +: {
	"pulsar-manager": base + {
	    image: images.pulsar_manager,
	    ports: [
		"9527:9527",
		"7750:7750",
	    ],
	    environment: {
		SPRING_CONFIGURATION_FILE: "/pulsar-manager/pulsar-manager/application.properties",
	    },
            deploy: {
		resources: {
		    limits: {
			cpus: '0.5',
			memory: '1.4G'
		    },
		    reservations: {
			cpus: '0.1',
			memory: '1.4G'
		    }
		}
	    },
	},
    }
}
