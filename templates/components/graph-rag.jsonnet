local base = import "base/base.jsonnet";
local images = import "values/images.jsonnet";
local url = import "values/url.jsonnet";

{

    "graph-rag-entity-limit":: 50,
    "graph-rag-triple-limit":: 30,
    "graph-rag-max-subgraph-size":: 3000,

    "kg-extract-definitions" +: {
    
        create:: function(engine)

            local container =
                engine.container("kg-extract-definitions")
                    .with_image(images.trustgraph)
                    .with_command([
                        "kg-extract-definitions",
                        "-p",
                        url.pulsar,
                    ])
                    .with_limits("0.5", "128M")
                    .with_reservations("0.1", "128M");

            local containerSet = engine.containers(
                "kg-extract-definitions", [ container ]
            );

            local service =
                engine.internalService(containerSet)
                .with_port(8000, 8000, "metrics");

            engine.resources([
                containerSet,
                service,
            ])

    },

    "kg-extract-relationships" +: {
    
        create:: function(engine)

            local container =
                engine.container("kg-extract-relationships")
                    .with_image(images.trustgraph)
                    .with_command([
                        "kg-extract-relationships",
                        "-p",
                        url.pulsar,
                    ])
                    .with_limits("0.5", "128M")
                    .with_reservations("0.1", "128M");

            local containerSet = engine.containers(
                "kg-extract-relationships", [ container ]
            );

            local service =
                engine.internalService(containerSet)
                .with_port(8000, 8000, "metrics");

            engine.resources([
                containerSet,
                service,
            ])

    },

    "kg-extract-topics" +: {
    
        create:: function(engine)

            local container =
                engine.container("kg-extract-topics")
                    .with_image(images.trustgraph)
                    .with_command([
                        "kg-extract-topics",
                        "-p",
                        url.pulsar,
                    ])
                    .with_limits("0.5", "128M")
                    .with_reservations("0.1", "128M");

            local containerSet = engine.containers(
                "kg-extract-topics", [ container ]
            );

            engine.resources([
                containerSet,
            ])

    },

    "graph-rag" +: {
    
        create:: function(engine)

            local container =
                engine.container("graph-rag")
                    .with_image(images.trustgraph)
                    .with_command([
                        "graph-rag",
                        "-p",
                        url.pulsar,
                        "--prompt-request-queue",
                        "non-persistent://tg/request/prompt-rag",
                        "--prompt-response-queue",
                        "non-persistent://tg/response/prompt-rag-response",
                        "--entity-limit",
                        std.toString($["graph-rag-entity-limit"]),
                        "--triple-limit",
                        std.toString($["graph-rag-triple-limit"]),
                        "--max-subgraph-size",
                        std.toString($["graph-rag-max-subgraph-size"]),
                    ])
                    .with_limits("0.5", "128M")
                    .with_reservations("0.1", "128M");

            local containerSet = engine.containers(
                "graph-rag", [ container ]
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

