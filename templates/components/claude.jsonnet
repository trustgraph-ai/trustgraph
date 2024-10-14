local base = import "base/base.jsonnet";
local images = import "values/images.jsonnet";
local url = import "values/url.jsonnet";
local prompts = import "prompts/mixtral.jsonnet";

{

    "claude-max-output-tokens":: 4096,
    "claude-temperature":: 0.0,

    "text-completion" +: {
    
        create:: function(engine)

            local envSecrets = engine.envSecrets("claude-credentials")
                .with_env_var("CLAUDE_KEY_TOKEN", "claude-key");

            local container =
                engine.container("text-completion")
                    .with_image(images.trustgraph)
                    .with_command([
                        "text-completion-claude",
                        "-p",
                        url.pulsar,
                        "-x",
                        std.toString($["claude-max-output-tokens"]),
                        "-t",
                        std.toString($["claude-temperature"]),
                    ])
                    .with_env_var_secrets(envSecrets)
                    .with_limits("0.5", "128M")
                    .with_reservations("0.1", "128M");

            local containerRag =
                engine.container("text-completion-rag")
                    .with_image(images.trustgraph)
                    .with_command([
                        "text-completion-claude",
                        "-p",
                        url.pulsar,
                        "-x",
                        std.toString($["claude-max-output-tokens"]),
                        "-t",
                        std.toString($["claude-temperature"]),
                        "-i",
                        "non-persistent://tg/request/text-completion-rag",
                        "-o",
                        "non-persistent://tg/response/text-completion-rag-response",
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
                .with_port(8000, 8000, "metrics");

            local serviceRag =
                engine.internalService(containerSetRag)
                .with_port(8000, 8000, "metrics");

            engine.resources([
                envSecrets,
                containerSet,
                containerSetRag,
                service,
                serviceRag,
            ])

    },

} + prompts

