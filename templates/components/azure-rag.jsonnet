local images = import "values/images.jsonnet";
local url = import "values/url.jsonnet";
local prompts = import "prompts/mixtral.jsonnet";

{

    with:: function(key, value)
        self + {
            ["azure-rag-" + key]:: value,
        },

    "azure-rag-max-output-tokens":: 4096,
    "azure-rag-temperature":: 0.0,

    "text-completion-rag" +: {
    
        create:: function(engine)

            local envSecrets = engine.envSecrets("azure-credentials")
                .with_env_var("AZURE_TOKEN", "azure-token")
                .with_env_var("AZURE_ENDPOINT", "azure-endpoint");

            local containerRag =
                engine.container("text-completion-rag")
                    .with_image(images.trustgraph_flow)
                    .with_command([
                        "text-completion-azure",
                        "-p",
                        url.pulsar,
                        "-x",
                        std.toString($["azure-rag-max-output-tokens"]),
                        "-t",
                        "%0.3f" % $["azure-rag-temperature"],
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

    }

} + prompts

