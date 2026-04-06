local images = import "values/images.jsonnet";
local url = import "values/url.jsonnet";
local prompts = import "prompts/mixtral.jsonnet";
local models = import "parameters/googleaistudio.jsonnet";

{

    with:: function(key, value)
        self + {
            ["googleaistudio-" + key]:: value,
        },

    "googleaistudio-max-output-tokens":: 4096,
    "googleaistudio-temperature":: 0.0,
    "googleaistudio-models":: models,

    "llm-models" +:: $["googleaistudio-models"],

    "text-completion" +: {
    
        create:: function(engine)

            local envSecrets = engine.envSecrets("googleaistudio-credentials")
                .with_env_var("GOOGLE_AI_STUDIO_KEY", "googleaistudio-key");

            local container =
                engine.container("text-completion")
                    .with_image(images.trustgraph_flow)
                    .with_command([
                        "text-completion-googleaistudio",
                        "-p",
                        url.pulsar,
                        "-x",
                        std.toString($["googleaistudio-max-output-tokens"]),
                        "-t",
                        "%0.3f" % $["googleaistudio-temperature"],
                        "--log-level",
                        $["log-level"],
                    ])
                    .with_env_var_secrets(envSecrets)
                    .with_limits("0.5", "128M")
                    .with_reservations("0.1", "128M");

            local containerSet = engine.containers(
                "text-completion", [ container ]
            );

            local service =
                engine.internalService(containerSet)
                .with_port(8000, 8000, "metrics");

            engine.resources([
                envSecrets,
                containerSet,
                service,
            ])

    },

    "text-completion-rag" +: {

        create:: function(engine)

            local envSecrets = engine.envSecrets("googleaistudio-credentials")
                .with_env_var("GOOGLE_AI_STUDIO_KEY", "googleaistudio-key");

            local containerRag =
                engine.container("text-completion-rag")
                    .with_image(images.trustgraph_flow)
                    .with_command([
                        "text-completion-googleaistudio",
                        "-p",
                        url.pulsar,
                        "--id",
                        "text-completion-rag",
                        "-x",
                        std.toString($["googleaistudio-max-output-tokens"]),
                        "-t",
                        "%0.3f" % $["googleaistudio-temperature"],
                        "--log-level",
                        $["log-level"],
                    ])
                    .with_env_var_secrets(envSecrets)
                    .with_limits("0.5", "128M")
                    .with_reservations("0.1", "128M");

            local containerSetRag = engine.containers(
                "text-completion-rag", [ containerRag ]
            );

            local serviceRag =
                engine.internalService(containerSetRag)
                .with_port(8000, 8000, "metrics");

            engine.resources([
                envSecrets,
                containerSetRag,
                serviceRag,
            ])

    },

} + prompts

