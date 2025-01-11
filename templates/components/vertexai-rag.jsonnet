local base = import "base/base.jsonnet";
local images = import "values/images.jsonnet";
local url = import "values/url.jsonnet";
local prompts = import "prompts/mixtral.jsonnet";

{

    with:: function(key, value)
        self + {
            ["vertexai-rag-" + key]:: value,
        },

    "vertexai-rag-model":: "gemini-1.0-pro-001",
    "vertexai-rag-private-key":: "/vertexai/private.json",
    "vertexai-rag-region":: "us-central1",
    "vertexai-rag-max-output-tokens":: 4096,
    "vertexai-rag-temperature":: 0.0,

    "text-completion-rag" +: {
    
        create:: function(engine)

            local cfgVol = engine.secretVolume(
	        "vertexai-creds",
	        "./vertexai",
		{
		    "private.json": importstr "vertexai/private.json",
		}
            );

            local container =
                engine.container("text-completion-rag")
                    .with_image(images.trustgraph)
                    .with_command([
                        "text-completion-vertexai",
                        "-p",
                        url.pulsar,
                        "-k",
                        $["vertexai-rag-private-key"],
                        "-r",
                        $["vertexai-rag-region"],
                        "-x",
                        std.toString($["vertexai-rag-max-output-tokens"]),
                        "-t",
                        "%0.3f" % $["vertexai-rag-temperature"],
                        "-m",
                        $["vertexai-rag-model"],
                        "-i",
                        "non-persistent://tg/request/text-completion-rag",
                        "-o",
                        "non-persistent://tg/response/text-completion-rag",
                    ])
                    .with_limits("0.5", "256M")
                    .with_reservations("0.1", "256M")
                    .with_volume_mount(cfgVol, "/vertexai");

            local containerSet = engine.containers(
                "text-completion-rag", [ container ]
            );

            local service =
                engine.internalService(containerSet)
                .with_port(8000, 8000, "metrics");

            engine.resources([
                cfgVol,
                containerSet,
                service,
            ])

    }

} + prompts

