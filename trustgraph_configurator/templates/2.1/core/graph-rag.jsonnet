local images = import "values/images.jsonnet";
local url = import "values/url.jsonnet";

{

    "kg-extract-definitions" +: {

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
                engine.container("kg-extract-definitions")
                    .with_image(images.trustgraph_flow)
                    .with_command([
                        "kg-extract-definitions",
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
                "kg-extract-definitions", [ container ]
            );

            local service =
                engine.internalService(containerSet)
                .with_port(8000, 8000, "metrics");

            engine.resources([
                containerSet,
                service,
            ])

    },

    "kg-extract-relationships" +: {

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
                engine.container("kg-extract-relationships")
                    .with_image(images.trustgraph_flow)
                    .with_command([
                        "kg-extract-relationships",
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
                "kg-extract-relationships", [ container ]
            );

            local service =
                engine.internalService(containerSet)
                .with_port(8000, 8000, "metrics");

            engine.resources([
                containerSet,
                service,
            ])

    },

    "kg-extract-agent" +: {

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
                engine.container("kg-extract-agent")
                    .with_image(images.trustgraph_flow)
                    .with_command([
                        "kg-extract-agent",
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
                "kg-extract-agent", [ container ]
            );

            local service =
                engine.internalService(containerSet)
                .with_port(8000, 8000, "metrics");

            engine.resources([
                containerSet,
                service,
            ])

    },

    "kg-extract-ontology" +: {

        concurrency:: 1,
        "cpu-limit":: "0.5",
        "cpu-reservation":: "0.1",
        "memory-limit":: "300M",
        "memory-reservation":: "300M",

        create:: function(engine)

            local concurrency = self.concurrency;
            local memoryLimit = self["memory-limit"];
            local memoryReservation = self["memory-reservation"];

            local container =
                engine.container("kg-extract-ontology")
                    .with_image(images.trustgraph_flow)
                    .with_command([
                        "kg-extract-ontology",
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
                "kg-extract-ontology", [ container ]
            );

            local service =
                engine.internalService(containerSet)
                .with_port(8000, 8000, "metrics");

            engine.resources([
                containerSet,
                service,
            ])

    },

    "graph-rag" +: {

        concurrency:: 1,
        "entity-limit":: 50,
        "triple-limit":: 30,
        "max-subgraph-size":: 400,
        "max-path-length":: 2,
        "cpu-limit":: "0.5",
        "cpu-reservation":: "0.1",
        "memory-limit":: "128M",
        "memory-reservation":: "128M",

        create:: function(engine)

            local concurrency = self.concurrency;
            local entityLimit = self["entity-limit"];
            local tripleLimit = self["triple-limit"];
            local maxSubgraphSize = self["max-subgraph-size"];
            local maxPathLength = self["max-path-length"];
            local memoryLimit = self["memory-limit"];
            local memoryReservation = self["memory-reservation"];

            local container =
                engine.container("graph-rag")
                    .with_image(images.trustgraph_flow)
                    .with_command([
                        "graph-rag",
                        "-p",
                        url.pulsar,
                        "--concurrency",
                        std.toString(concurrency),
                        "--entity-limit",
                        std.toString(entityLimit),
                        "--triple-limit",
                        std.toString(tripleLimit),
                        "--max-subgraph-size",
                        std.toString(maxSubgraphSize),
                        "--max-path-length",
                        std.toString(maxPathLength),
                        "--log-level",
                        $["log-level"],
                    ])
                    .with_limits(self["cpu-limit"], memoryLimit)
                    .with_reservations(self["cpu-reservation"], memoryReservation);

            local containerSet = engine.containers(
                "graph-rag", [ container ]
            );

            local service =
                engine.internalService(containerSet)
                .with_port(8000, 8000, "metrics");

            engine.resources([
                containerSet,
                service,
            ])

    },

    "graph-embeddings" +: {

        "cpu-limit":: "1.0",
        "cpu-reservation":: "0.5",
        "memory-limit":: "256M",
        "memory-reservation":: "256M",

        create:: function(engine)

            local memoryLimit = self["memory-limit"];
            local memoryReservation = self["memory-reservation"];

            local container =
                engine.container("graph-embeddings")
                    .with_image(images.trustgraph_flow)
                    .with_command([
                        "graph-embeddings",
                        "-p",
                        url.pulsar,
                        "--log-level",
                        $["log-level"],
                    ])
                    .with_limits(self["cpu-limit"], memoryLimit)
                    .with_reservations(self["cpu-reservation"], memoryReservation);

            local containerSet = engine.containers(
                "graph-embeddings", [ container ]
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

