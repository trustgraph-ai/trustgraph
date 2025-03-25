local base = import "base/base.jsonnet";
local images = import "values/images.jsonnet";
local url = import "values/url.jsonnet";
local prompts = import "prompts/mixtral.jsonnet";

{

    with:: function(key, value)
        self + {
            ["lmstudio-rag-" + key]:: value,
        },

    "lmstudio-rag-max-output-tokens":: 4096,
    "lmstudio-rag-temperature":: 0.0,
    "lmstudio-rag-model":: "GPT-3.5-Turbo",

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
                        "-x",
                        std.toString($["lmstudio-rag-max-output-tokens"]),
                        "-t",
                        "%0.3f" % $["lmstudio-rag-temperature"],
                        "-m",
                        $["lmstudio-rag-model"],
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

