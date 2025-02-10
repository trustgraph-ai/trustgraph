local base = import "base/base.jsonnet";
local images = import "values/images.jsonnet";
local url = import "values/url.jsonnet";
local prompts = import "prompts/mixtral.jsonnet";

{

    with:: function(key, value)
        self + {
            ["azure-openai-" + key]:: value,
        },

    "azure-openai-model":: "GPT-3.5-Turbo",
    "azure-openai-max-output-tokens":: 4192,
    "azure-openai-temperature":: 0.0,

    "text-completion" +: {
    
        create:: function(engine)

            local envSecrets = engine.envSecrets("azure-openai-credentials")
                .with_env_var("AZURE_TOKEN", "azure-token");

            local container =
                engine.container("text-completion")
                    .with_image(images.trustgraph_flow)
                    .with_command([
                        "text-completion-azure-openai",
                        "-p",
                        url.pulsar,
                        "-m",
                        $["azure-openai-model"],
                        "-x",
                        std.toString($["azure-openai-max-output-tokens"]),
                        "-t",
                        "%0.3f" % $["azure-openai-temperature"],
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

} + prompts

