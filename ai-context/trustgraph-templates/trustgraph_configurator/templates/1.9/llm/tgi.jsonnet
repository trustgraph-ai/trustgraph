local images = import "values/images.jsonnet";
local url = import "values/url.jsonnet";
local prompts = import "prompts/mixtral.jsonnet";

{

    with:: function(key, value)
        self + {
            ["tgi-" + key]:: value,
        },

    "tgi-max-output-tokens":: 1024,
    "tgi-temperature":: 0.0,

    "text-completion" +: {

        create:: function(engine)

            local concurrency = self.concurrency;

            local envSecrets = engine.envSecrets("tgi-credentials")
                .with_env_var("TGI_BASE_URL", "tgi-url");

            local container =
                engine.container("text-completion")
                    .with_image(images.trustgraph_flow)
                    .with_command([
                        "text-completion-tgi",
                        "-p",
                        url.pulsar,
                        "--concurrency",
                        std.toString(concurrency),
                        "-x",
                        std.toString($["tgi-max-output-tokens"]),
                        "-t",
                        "%0.3f" % $["tgi-temperature"],
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

            local envSecrets = engine.envSecrets("tgi-credentials")
                .with_env_var("TGI_BASE_URL", "tgi-url");

            local containerRag =
                engine.container("text-completion-rag")
                    .with_image(images.trustgraph_flow)
                    .with_command([
                        "text-completion-tgi",
                        "-p",
                        url.pulsar,
                        "--id",
                        "text-completion-rag",
                        "--concurrency",
                        std.toString(concurrency),
                        "-x",
                        std.toString($["tgi-max-output-tokens"]),
                        "-t",
                        "%0.3f" % $["tgi-temperature"],
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

