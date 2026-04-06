local images = import "values/images.jsonnet";

{

    "loki" +: {
    
        create:: function(engine)

            local vol = engine.volume("loki-data").with_size("20G");

            local cfgVol = engine.configVolume(
                "loki-cfg", "loki",
		{
		    "local-config.yaml": importstr "loki/local-config.yaml",
		}
            );

            local container =
                engine.container("loki")
                    .with_image(images.loki)
                    .with_limits("0.5", "256M")
                    .with_reservations("0.1", "256M")
                    .with_port(3100, 3100, "http")
                    .with_volume_mount(cfgVol, "/etc/loki/")
                    .with_volume_mount(vol, "/loki");

            local containerSet = engine.containers(
                "loki", [ container ]
            );

            local service =
                engine.service(containerSet)
                .with_port(3100, 3100, "http");

            engine.resources([
                cfgVol,
                vol,
                containerSet,
                service,
            ])

    },

}

