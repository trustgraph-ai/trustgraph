local base = import "base/base.jsonnet";
local images = import "values/images.jsonnet";
local url = import "values/url.jsonnet";
local minio = import "stores/minio.jsonnet";
local cassandra = import "stores/cassandra.jsonnet";

{

    "librarian" +: {
    
        create:: function(engine)

            local container =
                engine.container("librarian")
                    .with_image(images.trustgraph_flow)
                    .with_command([
                        "librarian",
                        "-p",
                        url.pulsar,
                    ])
                    .with_limits("0.5", "256M")
                    .with_reservations("0.1", "256M");

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

}

    // Minio and Cassandra are used by the Librarian
    + minio + cassandra

