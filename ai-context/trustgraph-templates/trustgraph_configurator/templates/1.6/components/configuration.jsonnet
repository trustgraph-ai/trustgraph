
// This puts the default configuration together.  References many things,
// flow classes, a default flow, token costs, prompts, agent tools

local base = import "base/base.jsonnet";
local images = import "values/images.jsonnet";
local url = import "values/url.jsonnet";

{

    "init-trustgraph" +: {
    
        create:: function(engine)

            local cfgVol = engine.configVolume(
                "trustgraph-cfg", "trustgraph",
		{
		    "config.json": importstr "trustgraph/config.json",
		}
            );

            local container =
                engine.container("init-trustgraph")
                    .with_image(images.trustgraph_flow)
                    .with_command(
                        [
                            "tg-init-trustgraph",
                            "-p",
                            url.pulsar_admin,
                            "--config-file",
                            "/trustgraph/config.json",
                        ]
                    )
                    .with_limits("0.5", "128M")
                    .with_reservations("0.1", "128M")
                    .with_volume_mount(cfgVol, "/trustgraph/");

            local containerSet = engine.containers(
                "init-trustgraph", [ container ]
            );

            engine.resources([
                cfgVol,
                containerSet,
            ])

    },

}

