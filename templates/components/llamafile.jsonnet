local base = import "base/base.jsonnet";
local images = import "values/images.jsonnet";
local url = import "values/url.jsonnet";
local prompts = import "prompts/slm.jsonnet";

{

    "llamafile-model":: "LLaMA_CPP",
    "llamafile-url":: "${LLAMAFILE_URL}",

    "text-completion" +: {
    
        create:: function(engine)

            local container =
                engine.container("text-completion")
                    .with_image(images.trustgraph)
                    .with_command([
                        "text-completion-llamafile",
                        "-p",
                        url.pulsar,
                        "-m",
                        $["llamafile-model"],
                        "-r",
                        $["llamafile-url"],
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
                        "text-completion-llamafile",
                        "-p",
                        url.pulsar,
                        "-m",
                        $["llamafile-model"],
                        "-r",
                        $["llamafile-url"],
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

} + prompts

