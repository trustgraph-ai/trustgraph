local base = import "base/base.jsonnet";
local images = import "values/images.jsonnet";
local url = import "values/url.jsonnet";

{

    "chunk-size":: 2000,
    "chunk-overlap":: 100,

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

            engine.resources([
                containerSet,
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

            engine.resources([
                containerSet,
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

            engine.resources([
                containerSet,
            ])

    },

}

