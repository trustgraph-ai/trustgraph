local images = import "values/images.jsonnet";
local url = import "values/url.jsonnet";
local memgraph = import "backends/memgraph.jsonnet";

memgraph + {

    "memgraph-url":: "bolt://memgraph:7687",
    "memgraph-database":: "memgraph",

    "store-triples" +: {
    
        create:: function(engine)

            local container =
                engine.container("store-triples")
                    .with_image(images.trustgraph_flow)
                    .with_command([
                        "triples-write-memgraph",
                        "-p",
                        url.pulsar,
                        "-g",
                        $["memgraph-url"],
                        "--database",
                        $["memgraph-database"],
                        "--log-level",
                        $["log-level"],
                    ])
                    .with_limits("0.5", "128M")
                    .with_reservations("0.1", "128M");

            local containerSet = engine.containers(
                "store-triples", [ container ]
            );

            local service =
                engine.internalService(containerSet)
                .with_port(8000, 8000, "metrics");

            engine.resources([
                containerSet,
                service,
            ])

    },

    "query-triples" +: {
    
        create:: function(engine)

            local container =
                engine.container("query-triples")
                    .with_image(images.trustgraph_flow)
                    .with_command([
                        "triples-query-memgraph",
                        "-p",
                        url.pulsar,
                        "-g",
                        $["memgraph-url"],
                        "--database",
                        $["memgraph-database"],
                        "--log-level",
                        $["log-level"],
                    ])
                    .with_limits("0.5", "128M")
                    .with_reservations("0.1", "128M");

            local containerSet = engine.containers(
                "query-triples", [ container ]
            );

            local service =
                engine.internalService(containerSet)
                .with_port(8000, 8000, "metrics");

            engine.resources([
                containerSet,
                service,
            ])


    }

}

