local images = import "values/images.jsonnet";
local url = import "values/url.jsonnet";

{

    "prompt" +: {

        concurrency:: 1,
        "cpu-limit":: "0.5",
        "cpu-reservation":: "0.1",
        "memory-limit":: "128M",
        "memory-reservation":: "128M",

        create:: function(engine)

            local concurrency = self.concurrency;
            local memoryLimit = self["memory-limit"];
            local memoryReservation = self["memory-reservation"];

            local container =
                engine.container("prompt")
                    .with_image(images.trustgraph_flow)
                    .with_command([
                        "prompt-template",
                        "-p",
                        url.pulsar,
                        "--concurrency",
                        std.toString(concurrency),
                        "--log-level",
                        $["log-level"],
                    ])
                    .with_limits(self["cpu-limit"], memoryLimit)
                    .with_reservations(self["cpu-reservation"], memoryReservation);

            local containerSet = engine.containers(
                "prompt", [ container ]
            );

            local service =
                engine.internalService(containerSet)
                .with_port(8000, 8000, "metrics");

            engine.resources([
                containerSet,
                service,
            ])

    },

    "prompt-rag" +: {

        concurrency:: 1,
        "cpu-limit":: "0.5",
        "cpu-reservation":: "0.1",
        "memory-limit":: "128M",
        "memory-reservation":: "128M",

        create:: function(engine)

            local concurrency = self.concurrency;
            local memoryLimit = self["memory-limit"];
            local memoryReservation = self["memory-reservation"];

            local container =
                engine.container("prompt-rag")
                    .with_image(images.trustgraph_flow)
                    .with_command([
                        "prompt-template",
                        "-p",
                        url.pulsar,
                        "--id",
                        "prompt-rag",
                        "--concurrency",
                        std.toString(concurrency),
                        "--log-level",
                        $["log-level"],
                    ])
                    .with_limits(self["cpu-limit"], memoryLimit)
                    .with_reservations(self["cpu-reservation"], memoryReservation);

            local containerSet = engine.containers(
                "prompt-rag", [ container ]
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

