local base = import "base/base.jsonnet";
local images = import "values/images.jsonnet";

{

    "prometheus" +: {
    
        create:: function(engine)

            local vol = engine.volume("prometheus-data").with_size("20G");
            local cfgVol = engine.configVolume("./prometheus")
                .with_size("20G");

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
            local cv1 = engine.configVolume("./grafana/dashboard.yml")
                .with_size("20G");
            local cv2 = engine.configVolume("./grafana/datasource.yml")
                .with_size("20G");
            local cv3 = engine.configVolume("./grafana/dashboard.json")
                .with_size("20G");

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
                    .with_volume_mount(cv1, "/etc/grafana/provisioning/dashboards/dashboard.yml")
                    .with_volume_mount(cv2, "/etc/grafana/provisioning/datasources/datasource.yml")
                    .with_volume_mount(cv3, "/var/lib/grafana/dashboards/dashboard.json");

            local containerSet = engine.containers(
                "grafana", [ container ]
            );

            engine.resources([
                vol,
                cv1,
                cv2,
                cv3,
                containerSet,
            ])

    },

}

