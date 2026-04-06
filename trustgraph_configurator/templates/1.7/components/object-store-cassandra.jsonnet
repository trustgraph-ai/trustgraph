local base = import "base/base.jsonnet";
local images = import "values/images.jsonnet";
local url = import "values/url.jsonnet";
local cassandra_hosts = "cassandra";
local cassandra = import "stores/cassandra.jsonnet";

cassandra + {

    "store-objects" +: {
    
        create:: function(engine)

            local container =
                engine.container("store-objects")
                    .with_image(images.trustgraph_flow)
                    .with_command([
                        "objects-write-cassandra",
                        "-p",
                        url.pulsar,
                        "--cassandra-host",
                        cassandra_hosts,
                        "--log-level",
                        $["log-level"],
                    ])
                    .with_limits("0.5", "128M")
                    .with_reservations("0.1", "128M");

            local containerSet = engine.containers(
                "store-objects", [ container ]
            );

            local service =
                engine.internalService(containerSet)
                .with_port(8000, 8000, "metrics");

            engine.resources([
                containerSet,
                service,
            ])

    },

    "query-objects" +: {
    
        create:: function(engine)

            local container =
                engine.container("query-objects")
                    .with_image(images.trustgraph_flow)
                    .with_command([
                        "objects-query-cassandra",
                        "-p",
                        url.pulsar,
                        "--cassandra-host",
                        cassandra_hosts,
                        "--log-level",
                        $["log-level"],
                    ])
                    .with_limits("0.5", "512M")
                    .with_reservations("0.1", "512M");

            local containerSet = engine.containers(
                "query-objects", [ container ]
            );

            local service =
                engine.internalService(containerSet)
                .with_port(8000, 8000, "metrics");

            engine.resources([
                containerSet,
                service,
            ])

    },

}

