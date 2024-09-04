local base = import "base/base.jsonnet";
local images = import "values/images.jsonnet";
local url = import "values/url.jsonnet";
local prompts = import "prompts/mixtral.jsonnet";

{

    "claude-key":: "${CLAUDE_KEY}",
    "claude-max-output-tokens":: 4096,
    "claude-temperature":: 0.0,

    "text-completion" +: {
    
        create:: function(engine)

            local container =
                engine.container("text-completion")
                    .with_image(images.trustgraph)
                    .with_command([
                        "text-completion-claude",
                        "-p",
                        url.pulsar,
                        "-k",
                        $["claude-key"],
                        "-x",
                        std.toString($["claude-max-output-tokens"]),
                        "-t",
                        std.toString($["claude-temperature"]),
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
                        "text-completion-claude",
                        "-p",
                        url.pulsar,
                        "-k",
                        $["claude-key"],
                        "-x",
                        std.toString($["claude-max-output-tokens"]),
                        "-t",
                        std.toString($["claude-temperature"]),
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

}

