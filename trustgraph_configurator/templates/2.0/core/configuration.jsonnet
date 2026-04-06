
// This puts the default configuration together.  References many things,
// flow classes, a default flow, token costs, prompts, agent tools

local images = import "values/images.jsonnet";
local url = import "values/url.jsonnet";

{

    "init-trustgraph" +: {

        "cpu-limit":: "0.5",
        "cpu-reservation":: "0.1",
        "memory-limit":: "128M",
        "memory-reservation":: "128M",

        create:: function(engine)

            local memoryLimit = self["memory-limit"];
            local memoryReservation = self["memory-reservation"];

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
                    .with_limits(self["cpu-limit"], memoryLimit)
                    .with_reservations(self["cpu-reservation"], memoryReservation)
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

