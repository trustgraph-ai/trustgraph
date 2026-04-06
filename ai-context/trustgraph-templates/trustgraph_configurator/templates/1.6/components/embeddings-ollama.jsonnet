local base = import "base/base.jsonnet";
local images = import "values/images.jsonnet";
local url = import "values/url.jsonnet";
local models = import "parameters/embeddings-ollama.jsonnet";

{

    "ollama-url":: "${OLLAMA_HOST}",

    "ollama-models":: models,

    "embeddings-models" +:: $["ollama-models"],

    embeddings +: {
    
        create:: function(engine)

            local container =
                engine.container("embeddings")
                    .with_image(images.trustgraph_flow)
                    .with_command([
                        "embeddings-ollama",
                        "-p",
                        url.pulsar,
                        "--concurrency",
                        std.toString($["embeddings-concurrency"]),
                        "-r",
                        $["ollama-url"],
                        "--log-level",
                        $["log-level"],
                    ])
                    .with_limits("0.5", "128M")
                    .with_reservations("0.1", "128M");

            local containerSet = engine.containers(
                "embeddings", [ container ]
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

