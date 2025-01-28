local base = import "base/base.jsonnet";
local images = import "values/images.jsonnet";
local url = import "values/url.jsonnet";
local prompts = import "prompts/slm.jsonnet";

{

    with:: function(key, value)
        self + {
            ["llamafile-" + key]:: value,
        },

    "llamafile-model":: "LLaMA_CPP",

    "text-completion" +: {
    
        create:: function(engine)

            local envSecrets = engine.envSecrets("llamafile-credentials")
                .with_env_var("LLAMAFILE_URL", "llamafile-url");

            local container =
                engine.container("text-completion")
                    .with_image(images.trustgraph_flow)
                    .with_command([
                        "text-completion-llamafile",
                        "-p",
                        url.pulsar,
                        "-m",
                        $["llamafile-model"],
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

