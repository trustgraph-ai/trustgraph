local base = import "base/base.jsonnet";
local images = import "values/images.jsonnet";

{

    "memgraph" +: {
    
        create:: function(engine)

            local container =
                engine.container("memgraph")
                    .with_image(images.memgraph_mage)
                    .with_environment({
                          MEMGRAPH: "--storage-properties-on-edges=true --storage-enable-edges-metadata=true"
                    })
                    .with_limits("1.0", "1000M")
                    .with_reservations("0.5", "1000M")
                    .with_port(7474, 7474, "api")
                    .with_port(7687, 7687, "api2");

            local containerSet = engine.containers(
                "memgraph", [ container ]
            );

            local service =
                engine.service(containerSet)
                .with_port(7474, 7474, "api")
                .with_port(7687, 7687, "api2");

            engine.resources([
                containerSet,
                service,
            ])

    },

    "memgraph-lab" +: {
    
        create:: function(engine)

            local container =
                engine.container("lab")
                    .with_image(images.memgraph_lab)
                    .with_environment({
                        QUICK_CONNECT_MG_HOST: "memgraph",
                        QUICK_CONNECT_MG_PORT: "7687",
                    })
                    .with_limits("1.0", "512M")
                    .with_reservations("0.5", "512M")
                    .with_port(3010, 3000, "http");

            local containerSet = engine.containers(
                "lab", [ container ]
            );

            local service =
                engine.service(containerSet)
                .with_port(3010, 3010, "http");

            engine.resources([
                containerSet,
                service,
            ])

    },

}

