local base = import "base/base.jsonnet";
local images = import "values/images.jsonnet";

{

    "prometheus" +: {
    
        create:: function(engine)

            local vol = engine.volume("prometheus-data").with_size("20G");

            local cfgVol = engine.configVolume(
                "prometheus-cfg", "prometheus",
		{
		    "prometheus.yml": importstr "prometheus/prometheus.yml",
		}
            );

            local container =
                engine.container("prometheus")
                    .with_image(images.prometheus)
                    .with_limits("0.5", "128M")
                    .with_reservations("0.1", "128M")
//                    .with_command(["/bin/sh", "-c", "sleep 9999999"])
                    .with_port(9090, 9090, "http")
                    .with_volume_mount(cfgVol, "/etc/prometheus/")
                    .with_volume_mount(vol, "/prometheus");

            local containerSet = engine.containers(
                "prometheus", [ container ]
            );

            local service =
                engine.service(containerSet)
                .with_port(9090, 9090, "http");

            engine.resources([
                cfgVol,
                vol,
                containerSet,
                service,
            ])

    },

    "grafana" +: {
    
        create:: function(engine)

            local vol = engine.volume("grafana-storage").with_size("20G");

            local provDashVol = engine.configVolume(
                "prov-dash", "grafana/provisioning/",
		{
		    "dashboard.yml":
                        importstr "grafana/provisioning/dashboard.yml",
		}
		
            );

            local provDataVol = engine.configVolume(
                "prov-data", "grafana/provisioning/",
		{
		    "datasource.yml":
                        importstr "grafana/provisioning/datasource.yml",
		}
		
            );

            local dashVol = engine.configVolume(
                "dashboards", "grafana/dashboards/",
		{
		    "dashboard.json":
                        importstr "grafana/dashboards/dashboard.json",
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
                    .with_volume_mount(
                        provDashVol, "/etc/grafana/provisioning/dashboards/"
                    )
                    .with_volume_mount(
                        provDataVol, "/etc/grafana/provisioning/datasources/"
                    )
                    .with_volume_mount(
                        dashVol, "/var/lib/grafana/dashboards/"
                    );

            local containerSet = engine.containers(
                "grafana", [ container ]
            );

            local service =
                engine.service(containerSet)
                .with_port(3000, 3000, "http");

            engine.resources([
                vol,
	        provDashVol,
	        provDataVol,
		dashVol,
                containerSet,
                service,
            ])

    },

}

