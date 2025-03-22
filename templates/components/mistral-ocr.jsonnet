local images = import "values/images.jsonnet";
local url = import "values/url.jsonnet";

{

    with:: function(key, value)
        self + {
            ["mistral-" + key]:: value,
        },

    "pdf-decoder" +: {
    
        create:: function(engine)

            local envSecrets = engine.envSecrets("mistral-credentials")
                .with_env_var("MISTRAL_TOKEN", "mistral-token");

            local container =
                engine.container("mistral-ocr")
                    .with_image(images.trustgraph_flow)
                    .with_command([
                        "pdf-ocr-mistral",
                        "-p",
                        url.pulsar,
                    ])
                    .with_env_var_secrets(envSecrets)
                    .with_limits("0.5", "128M")
                    .with_reservations("0.1", "128M");

            local containerSet = engine.containers(
                "mistral-ocr", [ container ]
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

