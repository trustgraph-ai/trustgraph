local base = import "base/base.jsonnet";
local images = import "values/images.jsonnet";
local url = import "values/url.jsonnet";
local cassandra_hosts = "cassandra";
local milvus = import "stores/milvus.jsonnet";

milvus + {

    "store-graph-embeddings" +: {
    
        create:: function(engine)

            local container =
                engine.container("store-graph-embeddings")
                    .with_image(images.trustgraph)
                    .with_command([
                        "ge-write-milvus",
                        "-p",
                        url.pulsar,
                        "-t",
                        url.milvus,
                    ])
                    .with_limits("0.5", "128M")
                    .with_reservations("0.1", "128M");

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
    
        create:: function(engine)

            local container =
                engine.container("query-graph-embeddings")
                    .with_image(images.trustgraph)
                    .with_command([
                        "ge-query-milvus",
                        "-p",
                        url.pulsar,
                        "-t",
                        url.milvus,
                    ])
                    .with_limits("0.5", "128M")
                    .with_reservations("0.1", "128M");

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
    
        create:: function(engine)

            local container =
                engine.container("store-doc-embeddings")
                    .with_image(images.trustgraph)
                    .with_command([
                        "de-write-milvus",
                        "-p",
                        url.pulsar,
                        "-t",
                        url.milvus,
                    ])
                    .with_limits("0.5", "128M")
                    .with_reservations("0.1", "128M");

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
    
        create:: function(engine)

            local container =
                engine.container("query-doc-embeddings")
                    .with_image(images.trustgraph)
                    .with_command([
                        "de-query-milvus",
                        "-p",
                        url.pulsar,
                        "-t",
                        url.milvus,
                    ])
                    .with_limits("0.5", "128M")
                    .with_reservations("0.1", "128M");

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


    }

}

