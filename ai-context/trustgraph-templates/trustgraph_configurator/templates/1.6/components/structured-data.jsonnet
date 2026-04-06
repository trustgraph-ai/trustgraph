local images = import "values/images.jsonnet";
local url = import "values/url.jsonnet";

{

    "nlp-query" +: {
    
        create:: function(engine)

            local container =
                engine.container("nlp-query")
                    .with_image(images.trustgraph_flow)
                    .with_command([
                        "nlp-query",
                        "-p",
                        url.pulsar,
                        "--log-level",
                        $["log-level"],
                    ])
                    .with_limits("0.5", "128M")
                    .with_reservations("0.1", "128M");

            local containerSet = engine.containers(
                "nlp-query", [ container ]
            );

            local service =
                engine.internalService(containerSet)
                .with_port(8000, 8000, "metrics");

            engine.resources([
                containerSet,
                service,
            ])

    },

    "structured-query" +: {
    
        create:: function(engine)

            local container =
                engine.container("structured-query")
                    .with_image(images.trustgraph_flow)
                    .with_command([
                        "structured-query",
                        "-p",
                        url.pulsar,
                        "--log-level",
                        $["log-level"],
                    ])
                    .with_limits("0.5", "128M")
                    .with_reservations("0.1", "128M");

            local containerSet = engine.containers(
                "structured-query", [ container ]
            );

            local service =
                engine.internalService(containerSet)
                .with_port(8000, 8000, "metrics");

            engine.resources([
                containerSet,
                service,
            ])

    },

    "structured-diag" +: {
    
        create:: function(engine)

            local container =
                engine.container("structured-diag")
                    .with_image(images.trustgraph_flow)
                    .with_command([
                        "structured-diag",
                        "-p",
                        url.pulsar,
                        "--log-level",
                        $["log-level"],
                    ])
                    .with_limits("0.5", "96M")
                    .with_reservations("0.1", "96M");

            local containerSet = engine.containers(
                "structured-diag", [ container ]
            );

            local service =
                engine.internalService(containerSet)
                .with_port(8000, 8000, "metrics");

            engine.resources([
                containerSet,
                service,
            ])

    },

    "kg-extract-objects" +: {
    
        create:: function(engine)

            local container =
                engine.container("kg-extract-objects")
                    .with_image(images.trustgraph_flow)
                    .with_command([
                        "kg-extract-objects",
                        "-p",
                        url.pulsar,
                        "--concurrency",
                        std.toString($["kg-extraction-concurrency"]),
                        "--log-level",
                        $["log-level"],
                    ])
                    .with_limits("0.5", "128M")
                    .with_reservations("0.1", "128M");

            local containerSet = engine.containers(
                "kg-extract-objects", [ container ]
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

