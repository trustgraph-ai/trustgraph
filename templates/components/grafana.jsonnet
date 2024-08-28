local base = import "base/base.jsonnet";
local images = import "values/images.jsonnet";
{
    volumes +: {
        "prometheus-data": {},
        "grafana-storage": {},
    },
    services +: {
	prometheus: base + {
	    image: images.prometheus,
	    ports: [
		"9090:9090",
	    ],
	    volumes: [
		"./prometheus:/etc/prometheus",
		"prometheus-data:/prometheus",
	    ],
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
	grafana: base + {
	    image: images.grafana,
	    ports: [
		"3000:3000",
	    ],
	    volumes: [
		"grafana-storage:/var/lib/grafana",
		"./grafana/dashboard.yml:/etc/grafana/provisioning/dashboards/dashboard.yml",
		"./grafana/datasource.yml:/etc/grafana/provisioning/datasources/datasource.yml",
		"./grafana/dashboard.json:/var/lib/grafana/dashboards/dashboard.json",
	    ], 
	    environment: {
		// GF_AUTH_ANONYMOUS_ORG_ROLE: "Admin",
		// GF_AUTH_ANONYMOUS_ENABLED: "true",
		// GF_ORG_ROLE: "Admin",
		GF_ORG_NAME: "trustgraph.ai",
		// GF_SERVER_ROOT_URL: "https://example.com",
	    },
            deploy: {
		resources: {
		    limits: {
			cpus: '1.0',
			memory: '256M'
		    },
		    reservations: {
			cpus: '0.5',
			memory: '256M'
		    }
		}
            },
	},
    },
}

    
