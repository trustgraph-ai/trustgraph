local base = import "base/base.jsonnet";
local images = import "values/images.jsonnet";
local url = import "values/url.jsonnet";
local prompts = import "prompts/mixtral.jsonnet";

{

    "openai-key":: "${OPENAI_KEY}",
    "openai-max-output-tokens":: 4096,
    "openai-temperature":: 0.0,
    "openai-model":: "GPT-3.5-Turbo",

    "text-completion" +: {
    
        create:: function(engine)

            local container =
                engine.container("text-completion")
                    .with_image(images.trustgraph)
                    .with_command([
                        "text-completion-openai",
                        "-p",
                        url.pulsar,
                        "-k",
                        $["openai-key"],
                        "-x",
                        std.toString($["openai-max-output-tokens"]),
                        "-t",
                        std.toString($["openai-temperature"]),
                        "-m",
                        $["openai-model"],
                    ])
                    .with_limits("0.5", "128M")
                    .with_reservations("0.1", "128M");

            local containerSet = engine.containers(
                "text-completion", [ container ]
            );

            local service =
                engine.internalService(containerSet)
                .with_port(8080, 8080, "metrics");

            engine.resources([
                containerSet,
                service,
            ])

    },

    "text-completion-rag" +: {
    
        create:: function(engine)

            local container =
                engine.container("text-completion-rag")
                    .with_image(images.trustgraph)
                    .with_command([
                        "text-completion-openai",
                        "-p",
                        url.pulsar,
                        "-k",
                        $["openai-key"],
                        "-x",
                        std.toString($["openai-max-output-tokens"]),
                        "-t",
                        std.toString($["openai-temperature"]),
                        "-m",
                        $["openai-model"],
                        "-i",
                        "non-persistent://tg/request/text-completion-rag",
                        "-o",
                        "non-persistent://tg/response/text-completion-rag-response",
                    ])
                    .with_limits("0.5", "128M")
                    .with_reservations("0.1", "128M");

            local containerSet = engine.containers(
                "text-completion-rag", [ container ]
            );

            local service =
                engine.internalService(containerSet)
                .with_port(8080, 8080, "metrics");

            engine.resources([
                containerSet,
                service,
            ])


    }

} + prompts

