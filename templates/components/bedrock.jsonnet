local base = import "base/base.jsonnet";
local images = import "values/images.jsonnet";
local url = import "values/url.jsonnet";
local prompts = import "prompts/mixtral.jsonnet";
local chunker = import "chunker-recursive.jsonnet";

{

    "aws-id-key":: "${AWS_ID_KEY}",
    "aws-secret-key":: "${AWS_SECRET_KEY}",
    "aws-region":: "us-west-2",
    "bedrock-max-output-tokens":: 4096,
    "bedrock-temperature":: 0.0,
    "bedrock-model":: "mistral.mixtral-8x7b-instruct-v0:1",

    "text-completion" +: {
    
        create:: function(engine)

            local container =
                engine.container("text-completion")
                    .with_image(images.trustgraph)
                    .with_command([
                        "text-completion-bedrock",
                        "-p",
                        url.pulsar,
                        "-z",
                        $["aws-id-key"],
                        "-k",
                        $["aws-secret-key"],
                        "-r",
                        $["aws-region"],
                        "-x",
                        std.toString($["bedrock-max-output-tokens"]),
                        "-t",
                        std.toString($["bedrock-temperature"]),
                        "-m",
                        $["bedrock-model"],
              	    ])
                    .with_limits("0.5", "128M")
                    .with_reservations("0.1", "128M");

            local containerSet = engine.containers(
                "text-completion", [ container ]
            );

            engine.resources([
                containerSet,
            ])

    },

    "text-completion-rag" +: {
    
        create:: function(engine)

            local container =
                engine.container("text-completion-rag")
                    .with_image(images.trustgraph)
                    .with_command([
                        "text-completion-bedrock",
                        "-p",
                        url.pulsar,
                        "-z",
                        $["aws-id-key"],
                        "-k",
                        $["aws-secret-key"],
                        "-r",
                        $["aws-region"],
                        "-x",
                        std.toString($["bedrock-max-output-tokens"]),
                        "-t",
                        std.toString($["bedrock-temperature"]),
                        "-m",
                        $["bedrock-model"],
                        "-i",
                        "non-persistent://tg/request/text-completion-rag",
                        "-o",
                        "non-persistent://tg/response/text-completion-rag-response",
              	    ])
                    .with_limits("0.5", "128M")
                    .with_reservations("0.1", "128M");

            local containerSet = engine.containers(
                "text-completion-rag", [ container ]
            );

            engine.resources([
                containerSet,
            ])


    }

} + prompts + chunker

