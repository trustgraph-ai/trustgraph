local base = import "base/base.jsonnet";
local images = import "values/images.jsonnet";
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
	    environment: {
                "PULSAR_MEM": "-Xms700M -Xmx700M"
	    },
	    volumes: [
		"pulsar-conf:/pulsar/conf",
		"pulsar-data:/pulsar/data",
	    ],
            deploy: {
		resources: {
		    limits: {
			cpus: '1.0',
			memory: '900M'
		    },
		    reservations: {
			cpus: '0.5',
			memory: '900M'
		    }
		}
            },
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
            deploy: {
		resources: {
		    limits: {
			cpus: '0.5',
			memory: '128M'
		    },
		    reservations: {
			cpus: '0.1',
			memory: '128M'
		    }
		}
	    },
	},
    }
}
