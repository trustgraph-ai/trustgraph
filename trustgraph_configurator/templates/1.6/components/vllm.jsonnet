local base = import "base/base.jsonnet";
local images = import "values/images.jsonnet";
local url = import "values/url.jsonnet";
local prompts = import "prompts/mixtral.jsonnet";
local models = import "parameters/vllm.jsonnet";

{

    with:: function(key, value)
        self + {
            ["vllm-" + key]:: value,
        },

    "vllm-models":: models,

    "llm-models" +:: $["vllm-models"],

    "vllm-max-output-tokens":: 1024,
    "vllm-temperature":: 0.0,

    "text-completion" +: {

        create:: function(engine)

            local envSecrets = engine.envSecrets("vllm-credentials")
                .with_env_var("VLLM_BASE_URL", "vllm-url");

            local container =
                engine.container("text-completion")
                    .with_image(images.trustgraph_flow)
                    .with_command([
                        "text-completion-vllm",
                        "-p",
                        url.pulsar,
                        "--concurrency",
                        std.toString($["text-completion-concurrency"]),
                        "-x",
                        std.toString($["vllm-max-output-tokens"]),
                        "-t",
                        "%0.3f" % $["vllm-temperature"],
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

            local envSecrets = engine.envSecrets("vllm-credentials")
                .with_env_var("VLLM_BASE_URL", "vllm-url");

            local containerRag =
                engine.container("text-completion-rag")
                    .with_image(images.trustgraph_flow)
                    .with_command([
                        "text-completion-vllm",
                        "-p",
                        url.pulsar,
                        "--id",
                        "text-completion-rag",
                        "--concurrency",
                        std.toString($["text-completion-rag-concurrency"]),
                        "-x",
                        std.toString($["vllm-max-output-tokens"]),
                        "-t",
                        "%0.3f" % $["vllm-temperature"],
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

