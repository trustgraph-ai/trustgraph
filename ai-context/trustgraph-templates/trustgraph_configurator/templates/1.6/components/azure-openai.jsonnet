local base = import "base/base.jsonnet";
local images = import "values/images.jsonnet";
local url = import "values/url.jsonnet";
local prompts = import "prompts/mixtral.jsonnet";
local models = import "parameters/azure-openai.jsonnet";

{

    with:: function(key, value)
        self + {
            ["azure-openai-" + key]:: value,
        },

// Strategy is to specify the model with the AZURE_MODEL environment
// variable.  This isn't something that can just be specified dynamically,
// it has to match what was provisioned in Azure.

    "azure-openai-max-output-tokens":: 4192,
    "azure-openai-temperature":: 0.0,
    "azure-openai-models":: models,

    "llm-models" +:: $["azure-openai-models"],

    "text-completion" +: {
    
        create:: function(engine)

            local envSecrets = engine.envSecrets("azure-openai-credentials")
                .with_env_var("AZURE_TOKEN", "azure-token")
                .with_env_var("AZURE_MODEL", "azure-model")
                .with_env_var("AZURE_ENDPOINT", "azure-endpoint");

            local container =
                engine.container("text-completion")
                    .with_image(images.trustgraph_flow)
                    .with_command([
                        "text-completion-azure-openai",
                        "-p",
                        url.pulsar,
                        "-x",
                        std.toString($["azure-openai-max-output-tokens"]),
                        "-t",
                        "%0.3f" % $["azure-openai-temperature"],
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

            local envSecrets = engine.envSecrets("azure-openai-credentials")
                .with_env_var("AZURE_TOKEN", "azure-token")
                .with_env_var("AZURE_MODEL", "azure-model")
                .with_env_var("AZURE_ENDPOINT", "azure-endpoint");

            local containerRag =
                engine.container("text-completion-rag")
                    .with_image(images.trustgraph_flow)
                    .with_command([
                        "text-completion-azure-openai",
                        "-p",
                        url.pulsar,
                        "--id",
                        "text-completion-rag",
                        "-x",
                        std.toString($["azure-openai-max-output-tokens"]),
                        "-t",
                        "%0.3f" % $["azure-openai-temperature"],
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

