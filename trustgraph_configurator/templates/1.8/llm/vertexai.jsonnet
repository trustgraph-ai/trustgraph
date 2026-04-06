local images = import "values/images.jsonnet";
local url = import "values/url.jsonnet";
local prompts = import "prompts/mixtral.jsonnet";
local models = import "parameters/vertexai.jsonnet";

{

    with:: function(key, value)
        self + {
            ["vertexai-" + key]:: value,
        },

    "vertexai-private-key":: "/vertexai/private.json",
    "vertexai-region":: "us-central1",
    "vertexai-max-output-tokens":: 4096,
    "vertexai-temperature":: 0.0,
    "vertexai-models":: models,

    "llm-models" +:: $["vertexai-models"],

    "text-completion" +: {
    
        create:: function(engine)

            local cfgVol = engine.secretVolume(
	        "vertexai-creds",
	        "./vertexai",
		{
		    "private.json": importstr "vertexai/private.json",
		}
            );

            local container =
                engine.container("text-completion")
                    .with_image(images.trustgraph_vertexai)
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
                        "%0.3f" % $["vertexai-temperature"],
                    ])
                    .with_limits("0.5", "256M")
                    .with_reservations("0.1", "256M")
                    .with_volume_mount(cfgVol, "/vertexai");

            local containerSet = engine.containers(
                "text-completion", [ container ]
            );

            local service =
                engine.internalService(containerSet)
                .with_port(8000, 8000, "metrics");

            engine.resources([
                cfgVol,
                containerSet,
                service,
            ])

    },

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
                    .with_image(images.trustgraph_vertexai)
                    .with_command([
                        "text-completion-vertexai",
                        "-p",
                        url.pulsar,
                        "--id",
                        "text-completion-rag",
                        "-k",
                        $["vertexai-private-key"],
                        "-r",
                        $["vertexai-region"],
                        "-x",
                        std.toString($["vertexai-max-output-tokens"]),
                        "-t",
                        "%0.3f" % $["vertexai-temperature"],
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

    },

} + prompts

