local base = import "base/base.jsonnet";
local images = import "values/images.jsonnet";
local url = import "values/url.jsonnet";

{

    "agent-manager" +: {
    
        create:: function(engine)

            local container =
                engine.container("agent-manager")
                    .with_image(images.trustgraph_flow)
                    .with_command([
                        "agent-manager-react",
                        "-p",
                        url.pulsar,
                        "--log-level",
                        $["log-level"],
                    ])
                    .with_limits("0.5", "128M")
                    .with_reservations("0.1", "128M");

            local containerSet = engine.containers(
                "agent-manager", [ container ]
            );

            local service =
                engine.internalService(containerSet)
                .with_port(8000, 8000, "metrics");

            engine.resources([
                containerSet,
                service,
            ])

    },

}

