local images = import "values/images.jsonnet";
local url = import "values/url.jsonnet";
local cassandra_hosts = "cassandra";
local qdrant = import "backends/qdrant.jsonnet";

qdrant + {

    "store-graph-embeddings" +: {

        "memory-limit":: "128M",
        "memory-reservation":: "128M",

        create:: function(engine)

            local memoryLimit = self["memory-limit"];
            local memoryReservation = self["memory-reservation"];

            local container =
                engine.container("store-graph-embeddings")
                    .with_image(images.trustgraph_flow)
                    .with_command([
                        "graph-embeddings-write-qdrant",
                        "-p",
                        url.pulsar,
                        "-t",
                        url.qdrant,
                        "--log-level",
                        $["log-level"],
                    ])
                    .with_limits("0.5", memoryLimit)
                    .with_reservations("0.1", memoryReservation);

            local containerSet = engine.containers(
                "store-graph-embeddings", [ container ]
            );

            local service =
                engine.internalService(containerSet)
                .with_port(8000, 8000, "metrics");

            engine.resources([
                containerSet,
                service,
            ])

    },

    "query-graph-embeddings" +: {

        "memory-limit":: "128M",
        "memory-reservation":: "128M",

        create:: function(engine)

            local memoryLimit = self["memory-limit"];
            local memoryReservation = self["memory-reservation"];

            local container =
                engine.container("query-graph-embeddings")
                    .with_image(images.trustgraph_flow)
                    .with_command([
                        "graph-embeddings-query-qdrant",
                        "-p",
                        url.pulsar,
                        "-t",
                        url.qdrant,
                        "--log-level",
                        $["log-level"],
                    ])
                    .with_limits("0.5", memoryLimit)
                    .with_reservations("0.1", memoryReservation);

            local containerSet = engine.containers(
                "query-graph-embeddings", [ container ]
            );

            local service =
                engine.internalService(containerSet)
                .with_port(8000, 8000, "metrics");

            engine.resources([
                containerSet,
                service,
            ])

    },

    "store-doc-embeddings" +: {

        "memory-limit":: "256M",
        "memory-reservation":: "256M",

        create:: function(engine)

            local memoryLimit = self["memory-limit"];
            local memoryReservation = self["memory-reservation"];

            local container =
                engine.container("store-doc-embeddings")
                    .with_image(images.trustgraph_flow)
                    .with_command([
                        "doc-embeddings-write-qdrant",
                        "-p",
                        url.pulsar,
                        "-t",
                        url.qdrant,
                        "--log-level",
                        $["log-level"],
                    ])
                    .with_limits("0.5", memoryLimit)
                    .with_reservations("0.1", memoryReservation);

            local containerSet = engine.containers(
                "store-doc-embeddings", [ container ]
            );

            local service =
                engine.internalService(containerSet)
                .with_port(8000, 8000, "metrics");

            engine.resources([
                containerSet,
                service,
            ])

    },

    "query-doc-embeddings" +: {

        "memory-limit":: "128M",
        "memory-reservation":: "128M",

        create:: function(engine)

            local memoryLimit = self["memory-limit"];
            local memoryReservation = self["memory-reservation"];

            local container =
                engine.container("query-doc-embeddings")
                    .with_image(images.trustgraph_flow)
                    .with_command([
                        "doc-embeddings-query-qdrant",
                        "-p",
                        url.pulsar,
                        "-t",
                        url.qdrant,
                        "--log-level",
                        $["log-level"],
                    ])
                    .with_limits("0.5", memoryLimit)
                    .with_reservations("0.1", memoryReservation);

            local containerSet = engine.containers(
                "query-doc-embeddings", [ container ]
            );

            local service =
                engine.internalService(containerSet)
                .with_port(8000, 8000, "metrics");

            engine.resources([
                containerSet,
                service,
            ])


    },

    "store-row-embeddings" +: {

        "memory-limit":: "128M",
        "memory-reservation":: "128M",

        create:: function(engine)

            local memoryLimit = self["memory-limit"];
            local memoryReservation = self["memory-reservation"];

            local container =
                engine.container("store-row-embeddings")
                    .with_image(images.trustgraph_flow)
                    .with_command([
                        "row-embeddings-write-qdrant",
                        "-p",
                        url.pulsar,
                        "-t",
                        url.qdrant,
                        "--log-level",
                        $["log-level"],
                    ])
                    .with_limits("0.5", memoryLimit)
                    .with_reservations("0.1", memoryReservation);

            local containerSet = engine.containers(
                "store-row-embeddings", [ container ]
            );

            local service =
                engine.internalService(containerSet)
                .with_port(8000, 8000, "metrics");

            engine.resources([
                containerSet,
                service,
            ])

    },

    "query-row-embeddings" +: {

        "memory-limit":: "128M",
        "memory-reservation":: "128M",

        create:: function(engine)

            local memoryLimit = self["memory-limit"];
            local memoryReservation = self["memory-reservation"];

            local container =
                engine.container("query-row-embeddings")
                    .with_image(images.trustgraph_flow)
                    .with_command([
                        "row-embeddings-query-qdrant",
                        "-p",
                        url.pulsar,
                        "-t",
                        url.qdrant,
                        "--log-level",
                        $["log-level"],
                    ])
                    .with_limits("0.5", memoryLimit)
                    .with_reservations("0.1", memoryReservation);

            local containerSet = engine.containers(
                "query-row-embeddings", [ container ]
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
