local base = import "base/base.jsonnet";
local images = import "values/images.jsonnet";
local url = import "values/url.jsonnet";
local prompts = import "prompts/mixtral.jsonnet";

{

    "azure-openai-token":: "${AZURE_OPENAI_TOKEN}",
    "azure-openai-model":: "GPT-3.5-Turbo",
    "azure-openai-max-output-tokens":: 4192,
    "azure-openai-temperature":: 0.0,

    "text-completion" +: {
    
        create:: function(engine)

            local container =
                engine.container("text-completion")
                    .with_image(images.trustgraph)
                    .with_command([
                        "text-completion-azure-openai",
                        "-p",
                        url.pulsar,
                        "-k",
                        $["azure-openai-token"],
                        "-m",
                        $["azure-openai-model"],
                        "-x",
                        std.toString($["azure-openai-max-output-tokens"]),
                        "-t",
                        std.toString($["azure-openai-temperature"]),
                    ])
                    .with_limits("0.5", "128M")
                    .with_reservations("0.1", "128M");

            local containerSet = engine.containers(
                "text-completion", [ container ]
            );

            local service =
                engine.internalService(containerSet)
                .with_port(8000, 8000, "metrics");

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
                        "text-completion-azure",
                        "-p",
                        url.pulsar,
                        "-k",
                        $["azure-openai-token"],
                        "-e",
                        $["azure-openai-model"],
                        "-x",
                        std.toString($["azure-openai-max-output-tokens"]),
                        "-t",
                        std.toString($["azure-openai-temperature"]),
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
                .with_port(8000, 8000, "metrics");

            engine.resources([
                containerSet,
                service,
            ])


    }

} + prompts

