local images = import "values/images.jsonnet";
local url = import "values/url.jsonnet";
local cassandra_hosts = "cassandra";
local cassandra = import "backends/cassandra.jsonnet";

cassandra + {

    "store-rows" +: {
    
        create:: function(engine)

            local container =
                engine.container("store-rows")
                    .with_image(images.trustgraph_flow)
                    .with_command([
                        "rows-write-cassandra",
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
                "store-rows", [ container ]
            );

            local service =
                engine.internalService(containerSet)
                .with_port(8000, 8000, "metrics");

            engine.resources([
                containerSet,
                service,
            ])

    },

    "query-rows" +: {
    
        create:: function(engine)

            local container =
                engine.container("query-rows")
                    .with_image(images.trustgraph_flow)
                    .with_command([
                        "rows-query-cassandra",
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
                "query-rows", [ container ]
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

