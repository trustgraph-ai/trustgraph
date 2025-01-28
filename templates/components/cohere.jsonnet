local base = import "base/base.jsonnet";
local images = import "values/images.jsonnet";
local url = import "values/url.jsonnet";
local prompts = import "prompts/mixtral.jsonnet";

{

    with:: function(key, value)
        self + {
            ["cohere-" + key]:: value,
        },

    "cohere-temperature":: 0.0,

    "text-completion" +: {
    
        create:: function(engine)

            local envSecrets = engine.envSecrets("cohere-credentials")
                .with_env_var("COHERE_KEY", "cohere-key");

            local container =
                engine.container("text-completion")
                    .with_image(images.trustgraph_flow)
                    .with_command([
                        "text-completion-cohere",
                        "-p",
                        url.pulsar,
                        "-t",
                        "%0.3f" % $["cohere-temperature"],
                    ])
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

} + prompts

