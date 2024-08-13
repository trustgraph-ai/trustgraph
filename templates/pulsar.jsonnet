local base = import "base.jsonnet";
local images = import "images.jsonnet";
{
    volumes +: {
        "pulsar-conf": {},
        "pulsar-data": {},
    },
    services +: {
	pulsar: base + {
	    image: images.pulsar,
	    command: "bin/pulsar standalone",
	    ports: [
		"6650:6650",
		"8080:8080",
	    ],
	    volumes: [
		"pulsar-conf:/pulsar/conf",
		"pulsar-data:/pulsar/data",
	    ]
	},
	"init-pulsar": base + {
	    image: images.pulsar,
	    command: [
		"sh",
		"-c",
		"pulsar-admin --admin-url http://pulsar:8080 tenants create tg && pulsar-admin --admin-url http://pulsar:8080 namespaces create tg/flow && pulsar-admin --admin-url http://pulsar:8080 namespaces create tg/request && pulsar-admin --admin-url http://pulsar:8080 namespaces create tg/response && pulsar-admin --admin-url http://pulsar:8080 namespaces set-retention --size -1 --time 3m tg/response",
	    ],
	    depends_on: {
		pulsar: {
		    condition: "service_started",
		}
	    },	
	},
	"pulsar-manager": base + {
	    image: images.pulsar_manager,
	    ports: [
		"9527:9527",
		"7750:7750",
	    ],
	    environment: {
		SPRING_CONFIGURATION_FILE: "/pulsar-manager/pulsar-manager/application.properties",
	    },	
	},
    }
}
