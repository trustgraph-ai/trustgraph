local base = import "base/base.jsonnet";
local images = import "values/images.jsonnet";
local url = import "values/url.jsonnet";
local prompts = import "prompts/mixtral.jsonnet";

{

    "vertexai-model":: "gemini-1.0-pro-001",
    "vertexai-private-key":: "/vertexai/private.json",
    "vertexai-region":: "us-central1",
    "vertexai-max-output-tokens":: 4096,
    "vertexai-temperature":: 0.0,

    "text-completion" +: {
    
        create:: function(engine)

            local cfgVol = engine.configVolume(
	        "vertexai-creds",
	        "./vertexai",
		{
		    "private.json": importstr "vertexai/private.json",
		}
            );

            local container =
                engine.container("text-completion")
                    .with_image(images.trustgraph)
                    .with_command([
                        "text-completion-vertexai",
                        "-p",
                        url.pulsar,
                        "-k",
                        $["vertexai-private-key"],
                        "-r",
                        $["vertexai-region"],
                        "-x",
                        std.toString($["vertexai-max-output-tokens"]),
                        "-t",
                        std.toString($["vertexai-temperature"]),
                        "-m",
                        $["vertexai-model"],
                    ])
                    .with_limits("0.5", "128M")
                    .with_reservations("0.1", "128M")
                    .with_volume_mount(cfgVol, "/vertexai");

            local containerSet = engine.containers(
                "text-completion", [ container ]
            );

            engine.resources([
                cfgVol,
                containerSet,
            ])

    },

    "text-completion-rag" +: {
    
        create:: function(engine)

            local cfgVol = engine.configVolume("./vertexai");

            local container =
                engine.container("text-completion-rag")
                    .with_image(images.trustgraph)
                    .with_command([
                        "text-completion-vertexai",
                        "-p",
                        url.pulsar,
                        "-k",
                        $["vertexai-private-key"],
                        "-r",
                        $["vertexai-region"],
                        "-x",
                        std.toString($["vertexai-max-output-tokens"]),
                        "-t",
                        std.toString($["vertexai-temperature"]),
                        "-m",
                        $["vertexai-model"],
                        "-i",
                        "non-persistent://tg/request/text-completion-rag",
                        "-o",
                        "non-persistent://tg/response/text-completion-rag-response",
                    ])
                    .with_limits("0.5", "128M")
                    .with_reservations("0.1", "128M")
                    .with_volume_mount(cfgVol, "/vertexai");

            local containerSet = engine.containers(
                "text-completion-rag", [ container ]
            );

            engine.resources([
                cfgVol,
                containerSet,
            ])


    }

} + prompts

