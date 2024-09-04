local base = import "base/base.jsonnet";
local images = import "values/images.jsonnet";

{

    "pulsar" +: {

        create:: function(engine)

        local confVolume = engine.volume("pulsar-conf").with_size("2G");
        local dataVolume = engine.volume("pulsar-data").with_size("20G");

        local container =
            engine.container("pulsar")
                .with_image(images.pulsar)
                .with_command(["bin/pulsar", "standalone"])
                .with_environment({
                    "PULSAR_MEM": "-Xms700M -Xmx700M"
                })
                .with_limits("1.0", "900M")
                .with_reservations("0.5", "900M")
                .with_volume_mount(confVolume, "/pulsar/conf")
                .with_volume_mount(dataVolume, "/pulsar/data");

        local adminContainer =
            engine.container("init-pulsar")
                .with_image(images.pulsar)
                .with_command([
                    "sh",
                    "-c",
                    "pulsar-admin --admin-url http://pulsar:8080 tenants create tg && pulsar-admin --admin-url http://pulsar:8080 namespaces create tg/flow && pulsar-admin --admin-url http://pulsar:8080 namespaces create tg/request && pulsar-admin --admin-url http://pulsar:8080 namespaces create tg/response && pulsar-admin --admin-url http://pulsar:8080 namespaces set-retention --size -1 --time 3m tg/response",
                ])
                .with_limits("1.0", "900M")
                .with_reservations("0.5", "900M")
                .with_volume_mount("pulsar-conf", "/pulsar/conf")
                .with_volume_mount("pulsar-data", "/pulsar/data")
                .with_port(6650, 6650, "bookie")
                .with_port(8080, 8080, "http")
                .with_limits("0.5", "128M")
                .with_reservations("0.1", "128M");

        local containerSet = engine.containers(
            "pulsar",
            [
                container, adminContainer
            ]
        );

        local service =
            engine.service(containerSet)
            .with_port(6650, 6650)
            .with_port(8080, 8080);

        engine.resources([
            confVolume,
            dataVolume,
            containerSet,
            service,
        ])

    }

}



