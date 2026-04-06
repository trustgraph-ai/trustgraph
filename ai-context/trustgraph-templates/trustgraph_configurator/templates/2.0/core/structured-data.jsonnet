local images = import "values/images.jsonnet";
local url = import "values/url.jsonnet";

{

    "nlp-query" +: {

        "cpu-limit":: "0.5",
        "cpu-reservation":: "0.1",
        "memory-limit":: "128M",
        "memory-reservation":: "128M",

        create:: function(engine)

            local memoryLimit = self["memory-limit"];
            local memoryReservation = self["memory-reservation"];

            local container =
                engine.container("nlp-query")
                    .with_image(images.trustgraph_flow)
                    .with_command([
                        "nlp-query",
                        "-p",
                        url.pulsar,
                        "--log-level",
                        $["log-level"],
                    ])
                    .with_limits(self["cpu-limit"], memoryLimit)
                    .with_reservations(self["cpu-reservation"], memoryReservation);

            local containerSet = engine.containers(
                "nlp-query", [ container ]
            );

            local service =
                engine.internalService(containerSet)
                .with_port(8000, 8000, "metrics");

            engine.resources([
                containerSet,
                service,
            ])

    },

    "structured-query" +: {

        "cpu-limit":: "0.5",
        "cpu-reservation":: "0.1",
        "memory-limit":: "128M",
        "memory-reservation":: "128M",

        create:: function(engine)

            local memoryLimit = self["memory-limit"];
            local memoryReservation = self["memory-reservation"];

            local container =
                engine.container("structured-query")
                    .with_image(images.trustgraph_flow)
                    .with_command([
                        "structured-query",
                        "-p",
                        url.pulsar,
                        "--log-level",
                        $["log-level"],
                    ])
                    .with_limits(self["cpu-limit"], memoryLimit)
                    .with_reservations(self["cpu-reservation"], memoryReservation);

            local containerSet = engine.containers(
                "structured-query", [ container ]
            );

            local service =
                engine.internalService(containerSet)
                .with_port(8000, 8000, "metrics");

            engine.resources([
                containerSet,
                service,
            ])

    },

    "structured-diag" +: {

        "cpu-limit":: "0.5",
        "cpu-reservation":: "0.1",
        "memory-limit":: "96M",
        "memory-reservation":: "96M",

        create:: function(engine)

            local memoryLimit = self["memory-limit"];
            local memoryReservation = self["memory-reservation"];

            local container =
                engine.container("structured-diag")
                    .with_image(images.trustgraph_flow)
                    .with_command([
                        "structured-diag",
                        "-p",
                        url.pulsar,
                        "--log-level",
                        $["log-level"],
                    ])
                    .with_limits(self["cpu-limit"], memoryLimit)
                    .with_reservations(self["cpu-reservation"], memoryReservation);

            local containerSet = engine.containers(
                "structured-diag", [ container ]
            );

            local service =
                engine.internalService(containerSet)
                .with_port(8000, 8000, "metrics");

            engine.resources([
                containerSet,
                service,
            ])

    },

    "kg-extract-rows" +: {

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
                engine.container("kg-extract-rows")
                    .with_image(images.trustgraph_flow)
                    .with_command([
                        "kg-extract-rows",
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
                "kg-extract-rows", [ container ]
            );

            local service =
                engine.internalService(containerSet)
                .with_port(8000, 8000, "metrics");

            engine.resources([
                containerSet,
                service,
            ])

    },

    "row-embeddings" +: {

        "cpu-limit":: "1.0",
        "cpu-reservation":: "0.5",
        "memory-limit":: "256M",
        "memory-reservation":: "256M",

        create:: function(engine)

            local memoryLimit = self["memory-limit"];
            local memoryReservation = self["memory-reservation"];

            local container =
                engine.container("row-embeddings")
                    .with_image(images.trustgraph_flow)
                    .with_command([
                        "row-embeddings",
                        "-p",
                        url.pulsar,
                        "--log-level",
                        $["log-level"],
                    ])
                    .with_limits(self["cpu-limit"], memoryLimit)
                    .with_reservations(self["cpu-reservation"], memoryReservation);

            local containerSet = engine.containers(
                "row-embeddings", [ container ]
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

