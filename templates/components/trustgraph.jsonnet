local base = import "base/base.jsonnet";
local images = import "values/images.jsonnet";
local url = import "values/url.jsonnet";
local prompt = import "prompt-template.jsonnet";

{

    "chunk-size":: 250,
    "chunk-overlap":: 15,

    "chunker" +: {
    
        create:: function(engine)

            local container =
                engine.container("chunker")
                    .with_image(images.trustgraph)
                    .with_command([
                        "chunker-token",
                        "-p",
                        url.pulsar,
                        "--chunk-size",
                        std.toString($["chunk-size"]),
                        "--chunk-overlap",
                        std.toString($["chunk-overlap"]),
                    ])
                    .with_limits("0.5", "128M")
                    .with_reservations("0.1", "128M");

            local containerSet = engine.containers(
                "chunker", [ container ]
            );

            local service =
                engine.internalService(containerSet)
                .with_port(8000, 8000, "metrics");

            engine.resources([
                containerSet,
                service,
            ])

    },

    "pdf-decoder" +: {
    
        create:: function(engine)

            local container =
                engine.container("pdf-decoder")
                    .with_image(images.trustgraph)
                    .with_command([
                        "pdf-decoder",
                        "-p",
                        url.pulsar,
                    ])
                    .with_limits("0.5", "128M")
                    .with_reservations("0.1", "128M");

            local containerSet = engine.containers(
                "pdf-decoder", [ container ]
            );

            local service =
                engine.internalService(containerSet)
                .with_port(8000, 8000, "metrics");

            engine.resources([
                containerSet,
                service,
            ])

    },

    "vectorize" +: {
    
        create:: function(engine)

            local container =
                engine.container("vectorize")
                    .with_image(images.trustgraph)
                    .with_command([
                        "embeddings-vectorize",
                        "-p",
                        url.pulsar,
                    ])
                    .with_limits("1.0", "512M")
                    .with_reservations("0.5", "512M");

            local containerSet = engine.containers(
                "vectorize", [ container ]
            );

            local service =
                engine.internalService(containerSet)
                .with_port(8000, 8000, "metrics");

            engine.resources([
                containerSet,
                service,
            ])

    },

    "metering" +: {
    
        create:: function(engine)

            local container =
                engine.container("metering")
                    .with_image(images.trustgraph)
                    .with_command([
                        "metering",
                        "-p",
                        url.pulsar,
                    ])
                    .with_limits("0.5", "128M")
                    .with_reservations("0.1", "128M");

            local containerSet = engine.containers(
                "metering", [ container ]
            );

            local service =
                engine.internalService(containerSet)
                .with_port(8000, 8000, "metrics");

            engine.resources([
                containerSet,
                service,
            ])

    },

} + prompt

