local base = import "base/base.jsonnet";
local images = import "values/images.jsonnet";
local url = import "values/url.jsonnet";
local prompts = import "prompts/mixtral.jsonnet";

{

    // Override chunking
    "chunk-size":: 150,
    "chunk-overlap":: 10,

    "cohere-temperature":: 0.0,

    "text-completion" +: {
    
        create:: function(engine)

            local envSecrets = engine.envSecrets("cohere-credentials")
                .with_env_var("COHERE_KEY", "cohere-key");

            local container =
                engine.container("text-completion")
                    .with_image(images.trustgraph)
                    .with_command([
                        "text-completion-cohere",
                        "-p",
                        url.pulsar,
                        "-t",
                        std.toString($["cohere-temperature"]),
                    ])
                    .with_limits("0.5", "128M")
                    .with_reservations("0.1", "128M");

            local containerRag =
                engine.container("text-completion-rag")
                    .with_image(images.trustgraph)
                    .with_command([
                        "text-completion-cohere",
                        "-p",
                        url.pulsar,
                        "-t",
                        std.toString($["cohere-temperature"]),
                        "-i",
                        "non-persistent://tg/request/text-completion-rag",
                        "-o",
                        "non-persistent://tg/response/text-completion-rag-response",
                    ])
                    .with_limits("0.5", "128M")
                    .with_reservations("0.1", "128M");

            local containerSet = engine.containers(
                "text-completion", [ container ]
            );

            local containerSetRag = engine.containers(
                "text-completion-rag", [ containerRag ]
            );

            local service =
                engine.internalService(containerSet)
                .with_port(8000, 8000, "metrics");

            local serviceRag =
                engine.internalService(containerSetRag)
                .with_port(8000, 8000, "metrics");

            engine.resources([
                envSecrets,
                containerSet,
                containerSetRag,
                service,
                serviceRag,
            ])

    },

} + prompts

