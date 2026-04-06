local images = import "values/images.jsonnet";
local url = import "values/url.jsonnet";
local prompts = import "prompts/mixtral.jsonnet";
local models = import "parameters/lmstudio.jsonnet";

{

    with:: function(key, value)
        self + {
            ["lmstudio-" + key]:: value,
        },

    "lmstudio-max-output-tokens":: 4096,
    "lmstudio-temperature":: 0.0,
    "lmstudio-models":: models,

    "llm-models" +:: $["lmstudio-models"],

    "text-completion" +: {
    
        create:: function(engine)

            local envSecrets = engine.envSecrets("lmstudio-credentials")
                .with_env_var("LMSTUDIO_URL", "lmstudio-url");

            local container =
                engine.container("text-completion")
                    .with_image(images.trustgraph_flow)
                    .with_command([
                        "text-completion-lmstudio",
                        "-p",
                        url.pulsar,
                        "-x",
                        std.toString($["lmstudio-max-output-tokens"]),
                        "-t",
                        "%0.3f" % $["lmstudio-temperature"],
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

            local envSecrets = engine.envSecrets("lmstudio-credentials")
                .with_env_var("LMSTUDIO_URL", "lmstudio-url");

            local containerRag =
                engine.container("text-completion-rag")
                    .with_image(images.trustgraph_flow)
                    .with_command([
                        "text-completion-lmstudio",
                        "-p",
                        url.pulsar,
                        "--id",
                        "text-completion-rag",
                        "-x",
                        std.toString($["lmstudio-max-output-tokens"]),
                        "-t",
                        "%0.3f" % $["lmstudio-temperature"],
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

