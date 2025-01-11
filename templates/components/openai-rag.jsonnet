local base = import "base/base.jsonnet";
local images = import "values/images.jsonnet";
local url = import "values/url.jsonnet";
local prompts = import "prompts/mixtral.jsonnet";

{

    with:: function(key, value)
        self + {
            ["openai-rag-" + key]:: value,
        },

    "openai-rag-max-output-tokens":: 4096,
    "openai-rag-temperature":: 0.0,
    "openai-rag-model":: "GPT-3.5-Turbo",

    "text-completion-rag" +: {
    
        create:: function(engine)

            local envSecrets = engine.envSecrets("openai-credentials")
                .with_env_var("OPENAI_TOKEN", "openai-token");

            local containerRag =
                engine.container("text-completion-rag")
                    .with_image(images.trustgraph)
                    .with_command([
                        "text-completion-openai",
                        "-p",
                        url.pulsar,
                        "-x",
                        std.toString($["openai-rag-max-output-tokens"]),
                        "-t",
                        "%0.3f" % $["openai-rag-temperature"],
                        "-m",
                        $["openai-rag-model"],
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
                .with_port(8080, 8080, "metrics");

            engine.resources([
                envSecrets,
                containerSetRag,
                serviceRag,
            ])

    },

} + prompts

