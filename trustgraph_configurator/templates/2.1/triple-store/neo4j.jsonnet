local images = import "values/images.jsonnet";
local url = import "values/url.jsonnet";
local neo4j = import "backends/neo4j.jsonnet";

neo4j + {

    "neo4j-url":: "bolt://neo4j:7687",

    "store-triples" +: {
    
        create:: function(engine)

            local container =
                engine.container("store-triples")
                    .with_image(images.trustgraph_flow)
                    .with_command([
                        "triples-write-neo4j",
                        "-p",
                        url.pulsar,
                        "-g",
                        $["neo4j-url"],
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
                        "triples-query-neo4j",
                        "-p",
                        url.pulsar,
                        "-g",
                        $["neo4j-url"],
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

