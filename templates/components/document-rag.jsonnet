local base = import "base/base.jsonnet";
local images = import "values/images.jsonnet";
local url = import "values/url.jsonnet";
local prompts = import "prompts/mixtral.jsonnet";

{

    "document-rag" +: {
    
        create:: function(engine)

            local container =
                engine.container("document-rag"")
                    .with_image(images.trustgraph)
                    .with_command([
                        "document-rag",
                        "-p",
                        url.pulsar,
                        "--prompt-request-queue",
                        "non-persistent://tg/request/prompt-rag",
                        "--prompt-response-queue",
                        "non-persistent://tg/response/prompt-rag-response",
                    ])
                    .with_limits("0.5", "128M")
                    .with_reservations("0.1", "128M");

            local containerSet = engine.containers(
                "document-rag"", [ container ]
            );

            engine.resources([
                containerSet,
            ])

    },

}

