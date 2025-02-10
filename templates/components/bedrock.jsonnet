local base = import "base/base.jsonnet";
local images = import "values/images.jsonnet";
local url = import "values/url.jsonnet";
local prompts = import "prompts/mixtral.jsonnet";
local chunker = import "chunker-recursive.jsonnet";

{

    with:: function(key, value)
        self + {
            ["bedrock-" + key]:: value,
        },

    "bedrock-max-output-tokens":: 4096,
    "bedrock-temperature":: 0.0,
    "bedrock-model":: "mistral.mixtral-8x7b-instruct-v0:1",

    "text-completion" +: {
    
        create:: function(engine)

            local envSecrets = engine.envSecrets("bedrock-credentials")
                .with_env_var("AWS_ACCESS_KEY_ID", "aws-id-key")
                .with_env_var("AWS_SECRET_ACCESS_KEY", "aws-secret")
                .with_env_var("AWS_DEFAULT_REGION", "aws-region");

            local container =
                engine.container("text-completion")
                    .with_image(images.trustgraph_bedrock)
                    .with_command([
                        "text-completion-bedrock",
                        "-p",
                        url.pulsar,
                        "-x",
                        std.toString($["bedrock-max-output-tokens"]),
                        "-t",
                        "%0.3f" % $["bedrock-temperature"],
                        "-m",
                        $["bedrock-model"],
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

} + prompts + chunker

