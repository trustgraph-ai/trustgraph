local base = import "base/base.jsonnet";
local images = import "values/images.jsonnet";
local url = import "values/url.jsonnet";
local prompts = import "prompts/mixtral.jsonnet";

{

    "openai-max-output-tokens":: 4096,
    "openai-temperature":: 0.0,
    "openai-model":: "GPT-3.5-Turbo",

    "text-completion" +: {
    
        create:: function(engine)

            local envSecrets = engine.envSecrets("openai-credentials")
                .with_env_var("OPENAI_TOKEN", "openai-token");

            local container =
                engine.container("text-completion")
                    .with_image(images.trustgraph)
                    .with_command([
                        "text-completion-openai",
                        "-p",
                        url.pulsar,
                        "-x",
                        std.toString($["openai-max-output-tokens"]),
                        "-t",
                        "%0.3f" % $["openai-temperature"],
                        "-m",
                        $["openai-model"],
                    ])
                    .with_env_var_secrets(envSecrets)
                    .with_limits("0.5", "128M")
                    .with_reservations("0.1", "128M");

            local containerRag =
                engine.container("text-completion-rag")
                    .with_image(images.trustgraph)
                    .with_command([
                        "text-completion-openai",
                        "-p",
                        url.pulsar,
                        "-x",
                        std.toString($["openai-max-output-tokens"]),
                        "-t",
                        "%0.3f" % $["openai-temperature"],
                        "-m",
                        $["openai-model"],
                        "-i",
                        "non-persistent://tg/request/text-completion-rag",
                        "-o",
                        "non-persistent://tg/response/text-completion-rag",
                    ])
                    .with_env_var_secrets(envSecrets)
                    .with_limits("0.5", "128M")
                    .with_reservations("0.1", "128M");

            local containerSet = engine.containers(
                "text-completion", [ container ]
            );

            local containerSetRag = engine.containers(
                "text-completion-rag", [ containerRag ]
            );

            local service =
                engine.internalService(containerSet)
                .with_port(8080, 8080, "metrics");

            local serviceRag =
                engine.internalService(containerSetRag)
                .with_port(8080, 8080, "metrics");

            engine.resources([
                envSecrets,
                containerSet,
                containerSetRag,
                service,
                serviceRag,
            ])

    },

} + prompts

