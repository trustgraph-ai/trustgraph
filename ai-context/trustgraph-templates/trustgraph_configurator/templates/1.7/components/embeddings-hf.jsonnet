local base = import "base/base.jsonnet";
local images = import "values/images.jsonnet";
local url = import "values/url.jsonnet";
local prompts = import "prompts/mixtral.jsonnet";
local models = import "parameters/embeddings-huggingface.jsonnet";

{

    "huggingface-embeddings-models":: models,

    "embeddings-models" +:: $["huggingface-embeddings-models"],

    embeddings +: {
    
        create:: function(engine)

            local container =
                engine.container("embeddings")
                    .with_image(images.trustgraph_hf)
                    .with_command([
                        "embeddings-hf",
                        "-p",
                        url.pulsar,
                        "--concurrency",
                        std.toString($["embeddings-concurrency"]),
                    ])
                    .with_limits("1.0", "400M")
                    .with_reservations("0.5", "400M");

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

