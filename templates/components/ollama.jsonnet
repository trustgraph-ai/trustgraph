local base = import "base/base.jsonnet";
local images = import "values/images.jsonnet";
local url = import "values/url.jsonnet";
local prompts = import "prompts/mixtral.jsonnet";

{

    with:: function(key, value)
        self + {
            ["ollama-" + key]:: value,
        },

    "ollama-model":: "gemma2:9b",

    "text-completion" +: {
    
        create:: function(engine)

            local envSecrets = engine.envSecrets("ollama-credentials")
                .with_env_var("OLLAMA_HOST", "ollama-host");

            local container =
                engine.container("text-completion")
                    .with_image(images.trustgraph_flow)
                    .with_command([
                        "text-completion-ollama",
                        "-p",
                        url.pulsar,
                        "-m",
                        $["ollama-model"],
                    ])
                    .with_env_var_secrets(envSecrets)
                    .with_limits("0.5", "128M")
                    .with_reservations("0.1", "128M");

            local containerSet = engine.containers(
                "text-completion", [ container ]
            );

            local service =
                engine.internalService(containerSet)
                .with_port(8080, 8080, "metrics");

            engine.resources([
                envSecrets,
                containerSet,
                service,
            ])

    },

} + prompts

