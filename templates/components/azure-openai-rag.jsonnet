local base = import "base/base.jsonnet";
local images = import "values/images.jsonnet";
local url = import "values/url.jsonnet";
local prompts = import "prompts/mixtral.jsonnet";

{

    with:: function(key, value)
        self + {
            ["ollama-rag-" + key]:: value,
        },

    "azure-openai-rag-model":: "GPT-3.5-Turbo",
    "azure-openai-rag-max-output-tokens":: 4192,
    "azure-openai-rag-temperature":: 0.0,

    "text-completion" +: {
    
        create:: function(engine)

            local envSecrets = engine.envSecrets("azure-openai-credentials")
                .with_env_var("AZURE_TOKEN", "azure-token");

            local containerRag =
                engine.container("text-completion-rag")
                    .with_image(images.trustgraph)
                    .with_command([
                        "text-completion-azure",
                        "-p",
                        url.pulsar,
                        "-x",
                        std.toString($["azure-openai-rag-max-output-tokens"]),
                        "-t",
                        "%0.3f" % $["azure-openai-rag-temperature"],
                        "-i",
                        "non-persistent://tg/request/text-completion-rag",
                        "-o",
                        "non-persistent://tg/response/text-completion-rag",
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

