local images = import "values/images.jsonnet";

{

    "cassandra" +: {

        // Memory settings (can be overridden by memory-profile)
        "memory-limit":: "1000M",
        "memory-reservation":: "1000M",
        "heap":: "300M",

        create:: function(engine)

            // Capture memory settings into locals
            local memLimit = self["memory-limit"];
            local memReserv = self["memory-reservation"];
            local heap = self["heap"];

            local vol = engine.volume("cassandra").with_size("20G");

            local container =
                engine.container("cassandra")
                    .with_image(images.cassandra)
                    .with_environment({
                        JVM_OPTS: "-Xms%s -Xmx%s -Dcassandra.skip_wait_for_gossip_to_settle=0" % [
                            heap, heap,
                        ],
                    })
                    .with_limits("1.0", memLimit)
                    .with_reservations("0.5", memReserv)
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
