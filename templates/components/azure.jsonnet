local images = import "values/images.jsonnet";
local url = import "values/url.jsonnet";
local prompts = import "prompts/mixtral.jsonnet";

{

    with:: function(key, value)
        self + {
            ["azure-" + key]:: value,
        },

    "azure-max-output-tokens":: 4096,
    "azure-temperature":: 0.0,

    "text-completion" +: {
    
        create:: function(engine)

            local envSecrets = engine.envSecrets("azure-credentials")
                .with_env_var("AZURE_TOKEN", "azure-token")
                .with_env_var("AZURE_ENDPOINT", "azure-endpoint");

            local container =
                engine.container("text-completion")
                    .with_image(images.trustgraph_flow)
                    .with_command([
                        "text-completion-azure",
                        "-p",
                        url.pulsar,
                        "-x",
                        std.toString($["azure-max-output-tokens"]),
                        "-t",
                        "%0.3f" % $["azure-temperature"],
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

    }

} + prompts

