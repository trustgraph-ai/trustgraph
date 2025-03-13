local base = import "base/base.jsonnet";
local images = import "values/images.jsonnet";
local url = import "values/url.jsonnet";
local prompts = import "prompts/mixtral.jsonnet";

{

    "document-rag-doc-limit":: 20,

    "document-rag" +: {
    
        create:: function(engine)

            local container =
                engine.container("document-rag")
                    .with_image(images.trustgraph_flow)
                    .with_command([
                        "document-rag",
                        "-p",
                        url.pulsar,
                        "--prompt-request-queue",
                        "non-persistent://tg/request/prompt-rag",
                        "--prompt-response-queue",
                        "non-persistent://tg/response/prompt-rag",
                    ])
                    .with_limits("0.5", "128M")
                    .with_reservations("0.1", "128M");

            local containerSet = engine.containers(
                "document-rag", [ container ]
            );

            local service =
                engine.internalService(containerSet)
                .with_port(8000, 8000, "metrics");

            engine.resources([
                containerSet,
                service,
            ])

    },

    "document-embeddings" +: {
    
        create:: function(engine)

            local container =
                engine.container("document-embeddings")
                    .with_image(images.trustgraph_flow)
                    .with_command([
                        "document-embeddings",
                        "-p",
                        url.pulsar,
                    ])
                    .with_limits("1.0", "512M")
                    .with_reservations("0.5", "512M");

            local containerSet = engine.containers(
                "document-embeddings", [ container ]
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

