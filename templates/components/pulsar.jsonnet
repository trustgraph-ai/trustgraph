local base = import "base/base.jsonnet";
local images = import "values/images.jsonnet";

{

    "pulsar" +: {

        create:: function(engine)

//            local confVolume = engine.volume("pulsar-conf").with_size("2G");
            local dataVolume = engine.volume("pulsar-data").with_size("20G");

            local container =
                engine.container("pulsar")
                    .with_image(images.pulsar)
                    .with_command(["bin/pulsar", "standalone"])
//                    .with_command(["/bin/sh", "-c", "sleep 9999999"])
                    .with_environment({
                        "PULSAR_MEM": "-Xms600M -Xmx600M"
                    })
                    .with_limits("2.0", "1500M")
                    .with_reservations("1.0", "1500M")
//                    .with_volume_mount(confVolume, "/pulsar/conf")
                    .with_volume_mount(dataVolume, "/pulsar/data")
                    .with_port(6650, 6650, "bookie")
                    .with_port(8080, 8080, "http");

            local adminContainer =
                engine.container("init-pulsar")
                    .with_image(images.pulsar)
                    .with_command([
                        "sh",
                        "-c",
                        "while true; do pulsar-admin --admin-url http://pulsar:8080 tenants create tg ; pulsar-admin --admin-url http://pulsar:8080 namespaces create tg/flow ; pulsar-admin --admin-url http://pulsar:8080 namespaces create tg/request ; pulsar-admin --admin-url http://pulsar:8080 namespaces create tg/response ; pulsar-admin --admin-url http://pulsar:8080 namespaces set-retention --size -1 --time 3m tg/response; sleep 20; done",
                    ])
                    .with_limits("1", "400M")
                    .with_reservations("0.1", "400M");

            local containerSet = engine.containers(
                "pulsar",
                [
                    container
                ]
            );

            local adminContainerSet = engine.containers(
                "init-pulsar",
                [
                    adminContainer
                ]
            );

            local service =
                engine.service(containerSet)
                .with_port(6650, 6650, "bookie")
                .with_port(8080, 8080, "http");

            engine.resources([
//                confVolume,
                dataVolume,
                containerSet,
                adminContainerSet,
                service,
            ])

    }

}

