local images = import "values/images.jsonnet";
local url = import "values/url.jsonnet";
local garage = import "backends/garage.jsonnet";
local cassandra = import "backends/cassandra.jsonnet";

{

    "librarian" +: {

        "cpu-limit":: "0.5",
        "cpu-reservation":: "0.1",
        "memory-limit":: "256M",
        "memory-reservation":: "256M",

        create:: function(engine)

            local memoryLimit = self["memory-limit"];
            local memoryReservation = self["memory-reservation"];

            local container =
                engine.container("librarian")
                    .with_image(images.trustgraph_flow)
                    .with_command([
                        "librarian",
                        "-p",
                        url.pulsar,
                        "--log-level",
                        $["log-level"],
                        "--object-store-endpoint",
                        url.object_store,
                        "--object-store-access-key",
                        $.garage["access-key"],
                        "--object-store-secret-key",
                        $.garage["secret-key"],
                        "--object-store-region",
                        $.garage.region,
                    ])
                    .with_limits(self["cpu-limit"], memoryLimit)
                    .with_reservations(self["cpu-reservation"], memoryReservation);

            local containerSet = engine.containers(
                "librarian", [ container ]
            );

            local service =
                engine.internalService(containerSet)
                .with_port(8000, 8000, "metrics");

            engine.resources([
                containerSet,
                service,
            ])

    },

// Garage and Cassandra are used by the Librarian
} + garage + cassandra

