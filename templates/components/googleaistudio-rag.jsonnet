local base = import "base/base.jsonnet";
local images = import "values/images.jsonnet";
local url = import "values/url.jsonnet";
local prompts = import "prompts/mixtral.jsonnet";

{

    with:: function(key, value)
        self + {
            ["googleaistudio-rag-" + key]:: value,
        },

    "googleaistudio-rag-max-output-tokens":: 4096,
    "googleaistudio-rag-temperature":: 0.0,
    "googleaistudio-rag-model":: "gemini-1.5-flash-002",

    "text-completion-rag" +: {
    
        create:: function(engine)

            local envSecrets = engine.envSecrets("googleaistudio-credentials")
                .with_env_var("GOOGLE_AI_STUDIO_KEY", "googleaistudio-key");

            local containerRag =
                engine.container("text-completion-rag")
                    .with_image(images.trustgraph)
                    .with_command([
                        "text-completion-googleaistudio",
                        "-p",
                        url.pulsar,
                        "-x",
                        std.toString(
                            $["googleaistudio-rag-max-output-tokens"]
                        ),
                        "-t",
                        "%0.3f" % $["googleaistudio-rag-temperature"],
                        "-m",
                        $["googleaistudio-rag-model"],
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

