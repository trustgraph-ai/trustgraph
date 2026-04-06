local images = import "values/images.jsonnet";
local url = import "values/url.jsonnet";
local prompts = import "prompts/mixtral.jsonnet";

{

    "document-rag" +: {

        "doc-limit":: 20,
        "cpu-limit":: "0.5",
        "cpu-reservation":: "0.1",
        "memory-limit":: "128M",
        "memory-reservation":: "128M",

        create:: function(engine)

            local docLimit = self["doc-limit"];
            local memoryLimit = self["memory-limit"];
            local memoryReservation = self["memory-reservation"];

            local container =
                engine.container("document-rag")
                    .with_image(images.trustgraph_flow)
                    .with_command([
                        "document-rag",
                        "-p",
                        url.pulsar,
                        "--doc-limit",
                        std.toString(docLimit),
                        "--log-level",
                        $["log-level"],
                    ])
                    .with_limits(self["cpu-limit"], memoryLimit)
                    .with_reservations(self["cpu-reservation"], memoryReservation);

            local containerSet = engine.containers(
                "document-rag", [ container ]
            );

            local service =
                engine.internalService(containerSet)
                .with_port(8000, 8000, "metrics");

            engine.resources([
                containerSet,
                service,
            ])

    },

    "document-embeddings" +: {

        "cpu-limit":: "1.0",
        "cpu-reservation":: "0.5",
        "memory-limit":: "512M",
        "memory-reservation":: "512M",

        create:: function(engine)

            local memoryLimit = self["memory-limit"];
            local memoryReservation = self["memory-reservation"];

            local container =
                engine.container("document-embeddings")
                    .with_image(images.trustgraph_flow)
                    .with_command([
                        "document-embeddings",
                        "-p",
                        url.pulsar,
                        "--log-level",
                        $["log-level"],
                    ])
                    .with_limits(self["cpu-limit"], memoryLimit)
                    .with_reservations(self["cpu-reservation"], memoryReservation);

            local containerSet = engine.containers(
                "document-embeddings", [ container ]
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

