local base = import "base/base.jsonnet";
local images = import "values/images.jsonnet";

{

    "prometheus" +: {
    
        create:: function(engine)

            local vol = engine.volume("prometheus-data").with_size("20G");
            local FIXME = engine.volume("./prometheus").with_size("20G");

            local container =
                engine.container("prometheus")
                    .with_image(images.prometheus)
                    .with_limits("0.5", "128M")
                    .with_reservations("0.1", "128M")
                    .with_port(9042, 9042, "cassandra")
                    .with_volume_mount(vol, "/prometheus")
                    .with_volume_mount(FIXME, "/etc/prometheus");

            local containerSet = engine.containers(
                "prometheus", [ container ]
            );

            engine.resources([
                containerSet,
            ])

    },

    "grafana" +: {
    
        create:: function(engine)

            local vol = engine.volume("grafana").with_size("20G");
            local FIXME1 = engine.volume("./grafana/dashboard.yml").with_size("20G");
            local FIXME2 = engine.volume("./grafana/datasource.yml").with_size("20G");
            local FIXME3 = engine.volume("./grafana/dashboard.json").with_size("20G");

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
                    .with_volume_mount(FIXME1, "/etc/grafana/provisioning/dashboards/dashboard.yml")
                    .with_volume_mount(FIXME2, "/etc/grafana/provisioning/datasources/datasource.yml")
                    .with_volume_mount(FIXME3, "/var/lib/grafana/dashboards/dashboard.json");

            local containerSet = engine.containers(
                "grafana", [ container ]
            );

            engine.resources([
                containerSet,
            ])

    },

}

