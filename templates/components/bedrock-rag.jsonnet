local base = import "base/base.jsonnet";
local images = import "values/images.jsonnet";
local url = import "values/url.jsonnet";
local prompts = import "prompts/mixtral.jsonnet";
local chunker = import "chunker-recursive.jsonnet";

{

    with:: function(key, value)
        self + {
            ["bedrock-rag-" + key]:: value,
        },

    "bedrock-rag-max-output-tokens":: 4096,
    "bedrock-rag-temperature":: 0.0,
    "bedrock-rag-model":: "mistral.mixtral-8x7b-instruct-v0:1",

    "text-completion-rag" +: {
    
        create:: function(engine)

            local envSecrets = engine.envSecrets("bedrock-credentials")
                .with_env_var("AWS_ID_KEY", "aws-id-key")
                .with_env_var("AWS_SECRET", "aws-secret")
                .with_env_var("AWS_REGION", "aws-region");

            local containerRag =
                engine.container("text-completion-rag")
                    .with_image(images.trustgraph)
                    .with_command([
                        "text-completion-bedrock",
                        "-p",
                        url.pulsar,
                        "-x",
                        std.toString($["bedrock-rag-max-output-tokens"]),
                        "-t",
                        "%0.3f" % $["bedrock-rag-temperature"],
                        "-m",
                        $["bedrock-rag-model"],
                        "-i",
                        "non-persistent://tg/request/text-completion-rag",
                        "-o",
                        "non-persistent://tg/response/text-completion-rag",
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

} + prompts + chunker

