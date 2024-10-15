local base = import "base/base.jsonnet";
local images = import "values/images.jsonnet";
local url = import "values/url.jsonnet";
local prompts = import "prompts/mixtral.jsonnet";

{

    "googleaistudio-key":: "${GOOGLEAISTUDIO_KEY}",
    "googleaistudio-max-output-tokens":: 4096,
    "googleaistudio-temperature":: 0.0,

    "text-completion" +: {
    
        create:: function(engine)

            local container =
                engine.container("text-completion")
                    .with_image(images.trustgraph)
                    .with_command([
                        "text-completion-googleaistudio",
                        "-p",
                        url.pulsar,
                        "-k",
                        $["googleaistudio-key"],
                        "-x",
                        std.toString($["googleaistudio-max-output-tokens"]),
                        "-t",
                        std.toString($["googleaistudio-temperature"]),
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
                        "text-completion-googleaistudio",
                        "-p",
                        url.pulsar,
                        "-k",
                        $["googleaistudio-key"],
                        "-x",
                        std.toString($["googleaistudio-max-output-tokens"]),
                        "-t",
                        std.toString($["googleaistudio-temperature"]),
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

