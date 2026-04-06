local images = import "values/images.jsonnet";
local url = import "values/url.jsonnet";
local prompts = import "prompts/mixtral.jsonnet";
local models = import "parameters/mistral.jsonnet";

{

    with:: function(key, value)
        self + {
            ["mistral-" + key]:: value,
        },

    "mistral-max-output-tokens":: 4096,
    "mistral-temperature":: 0.0,
    "mistral-models":: models,

    "llm-models" +:: $["mistral-models"],

    "text-completion" +: {
    
        create:: function(engine)

            local envSecrets = engine.envSecrets("mistral-credentials")
                .with_env_var("MISTRAL_TOKEN", "mistral-token");

            local container =
                engine.container("text-completion")
                    .with_image(images.trustgraph_flow)
                    .with_command([
                        "text-completion-mistral",
                        "-p",
                        url.pulsar,
                        "-x",
                        std.toString($["mistral-max-output-tokens"]),
                        "-t",
                        "%0.3f" % $["mistral-temperature"],
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

            local envSecrets = engine.envSecrets("mistral-credentials")
                .with_env_var("MISTRAL_TOKEN", "mistral-token");

            local containerRag =
                engine.container("text-completion-rag")
                    .with_image(images.trustgraph_flow)
                    .with_command([
                        "text-completion-mistral",
                        "-p",
                        url.pulsar,
                        "--id",
                        "text-completion-rag",
                        "-x",
                        std.toString($["mistral-max-output-tokens"]),
                        "-t",
                        "%0.3f" % $["mistral-temperature"],
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

