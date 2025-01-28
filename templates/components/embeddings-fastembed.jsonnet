local base = import "base/base.jsonnet";
local images = import "values/images.jsonnet";
local url = import "values/url.jsonnet";
local prompts = import "prompts/mixtral.jsonnet";

{

    "embeddings-model":: "sentence-transformers/all-MiniLM-L6-v2",

    embeddings +: {
    
        create:: function(engine)

            local container =
                engine.container("embeddings")
                    .with_image(images.trustgraph_flow)
                    .with_command([
                        "embeddings-fastembed",
                        "-p",
                        url.pulsar,
                        "-m",
                        $["embeddings-model"],
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

