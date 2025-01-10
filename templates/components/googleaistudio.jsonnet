local base = import "base/base.jsonnet";
local images = import "values/images.jsonnet";
local url = import "values/url.jsonnet";
local prompts = import "prompts/mixtral.jsonnet";

{

    "googleaistudio-max-output-tokens":: 4096,
    "googleaistudio-temperature":: 0.0,
    "googleaistudio-model":: "gemini-1.5-flash-002",

    "text-completion" +: {
    
        create:: function(engine)

            local envSecrets = engine.envSecrets("googleaistudio-key")
                .with_env_var("GOOGLE_AI_STUDIO_KEY", "googleaistudio-key");

            local container =
                engine.container("text-completion")
                    .with_image(images.trustgraph)
                    .with_command([
                        "text-completion-googleaistudio",
                        "-p",
                        url.pulsar,
                        "-x",
                        std.toString($["googleaistudio-max-output-tokens"]),
                        "-t",
                        "%0.3f" % $["googleaistudio-temperature"],
                        "-m",
                        $["googleaistudio-model"],
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

} + prompts

