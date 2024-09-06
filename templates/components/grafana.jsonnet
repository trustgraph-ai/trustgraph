local base = import "base/base.jsonnet";
local images = import "values/images.jsonnet";

{

    "prometheus" +: {
    
        create:: function(engine)

            local vol = engine.volume("prometheus-data").with_size("20G");

            local cfgVol = engine.configVolume(
                "prometheus-cfg", "./prometheus",
		{
		    "prometheus.cfg": importstr "prometheus/prometheus.yml",
		}
            );

            local container =
                engine.container("prometheus")
                    .with_image(images.prometheus)
                    .with_limits("0.5", "128M")
                    .with_reservations("0.1", "128M")
                    .with_port(9090, 9090, "http")
                    .with_volume_mount(cfgVol, "/etc/prometheus")
                    .with_volume_mount(vol, "/prometheus");

            local containerSet = engine.containers(
                "prometheus", [ container ]
            );

            engine.resources([
                cfgVol,
                vol,
                containerSet,
            ])

    },

    "grafana" +: {
    
        create:: function(engine)

            local vol = engine.volume("grafana-storage").with_size("20G");

            local provVol = engine.configVolume(
                "provisioning", "./grafana/",
		{
		    "dashboard.yml": importstr "grafana/dashboard.yml",
		    "datasource.yml": importstr "grafana/datasource.yml",
		}
		
            );
            local dashVol = engine.configVolume(
                "dashboards", "./grafana/",
		{
		    "dashboard.json": importstr "grafana/dashboard.json",
		}
		
            );

            local container =
                engine.container("grafana")
                    .with_image(images.grafana)
                    .with_environment({
                        // GF_AUTH_ANONYMOUS_ORG_ROLE: "Admin",
                        // GF_AUTH_ANONYMOUS_ENABLED: "true",
                        // GF_ORG_ROLE: "Admin",
                        GF_ORG_NAME: "trustgraph.ai",
                        // GF_SERVER_ROOT_URL: "https://example.com",
                    })
                    .with_limits("1.0", "256M")
                    .with_reservations("0.5", "256M")
                    .with_port(3000, 3000, "cassandra")
                    .with_volume_mount(vol, "/var/lib/grafana")
                    .with_volume_mount(provVol, "/etc/grafana/provisioning/dashboards/")
                    .with_volume_mount(dashVol, "/etc/grafana/provisioning/dash/");

            local containerSet = engine.containers(
                "grafana", [ container ]
            );

            engine.resources([
	        provVol,
		dashVol,
                containerSet,
            ])

    },

}

