local images = import "values/images.jsonnet";
local url = import "values/url.jsonnet";
local prompts = import "prompts/mixtral.jsonnet";

{

    "chunk-size":: 2000,
    "chunk-overlap":: 100,

    "chunker" +: {

        "cpu-limit":: "0.5",
        "cpu-reservation":: "0.1",
        "memory-limit":: "128M",
        "memory-reservation":: "128M",

        create:: function(engine)

            local memoryLimit = self["memory-limit"];
            local memoryReservation = self["memory-reservation"];

            local container =
                engine.container("chunker")
                    .with_image(images.trustgraph_flow)
                    .with_command([
                        "chunker-recursive",
                        "-p",
                        url.pulsar,
                        "--chunk-size",
                        std.toString($["chunk-size"]),
                        "--chunk-overlap",
                        std.toString($["chunk-overlap"]),
                        "--log-level",
                        $["log-level"],
                    ])
                    .with_limits(self["cpu-limit"], memoryLimit)
                    .with_reservations(self["cpu-reservation"], memoryReservation);

            local containerSet = engine.containers(
                "chunker", [ container ]
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

