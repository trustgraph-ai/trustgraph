local base = import "base/base.jsonnet";
local images = import "values/images.jsonnet";

{

    "cassandra" +: {
    
        create:: function(engine)

            local vol = engine.volume("cassandra").with_size("20G");

            local container =
                engine.container("cassandra")
                    .with_image(images.cassandra)
                    .with_environment({
                        JVM_OPTS: "-Xms300M -Xmx300M",
                    })
                    .with_limits("1.0", "1000M")
                    .with_reservations("0.5", "1000M")
                    .with_port(9042, 9042, "cassandra")
                    .with_volume_mount(vol, "/var/lib/cassandra");

            local containerSet = engine.containers(
                "cassandra", [ container ]
            );

            local service =
                engine.service(containerSet)
                .with_port(9042, 9042, "api");

            engine.resources([
                vol,
                containerSet,
                service,
            ])

    },

}

