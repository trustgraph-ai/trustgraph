local images = import "values/images.jsonnet";
local url = import "values/url.jsonnet";
local prompts = import "prompts/mixtral.jsonnet";
local models = import "parameters/ollama.jsonnet";

{

    with:: function(key, value)
        self + {
            ["ollama-" + key]:: value,
        },

    "ollama-models":: models,

    "llm-models" +:: $["ollama-models"],

    "text-completion" +: {

        create:: function(engine)

            local concurrency = self.concurrency;

            local envSecrets = engine.envSecrets("ollama-credentials")
                .with_env_var("OLLAMA_HOST", "ollama-host");

            local container =
                engine.container("text-completion")
                    .with_image(images.trustgraph_flow)
                    .with_command([
                        "text-completion-ollama",
                        "-p",
                        url.pulsar,
                        "--concurrency",
                        std.toString(concurrency),
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

            local concurrency = self.concurrency;

            local envSecrets = engine.envSecrets("ollama-credentials")
                .with_env_var("OLLAMA_HOST", "ollama-host");

            local containerRag =
                engine.container("text-completion-rag")
                    .with_image(images.trustgraph_flow)
                    .with_command([
                        "text-completion-ollama",
                        "-p",
                        url.pulsar,
                        "--id",
                        "text-completion-rag",
                        "--concurrency",
                        std.toString(concurrency),
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

