local base = import "base/base.jsonnet";
local images = import "values/images.jsonnet";
local url = import "values/url.jsonnet";
local cassandra_hosts = "cassandra";
local qdrant = import "stores/qdrant.jsonnet";

qdrant + {

    "store-graph-embeddings" +: {
    
        create:: function(engine)

            local container =
                engine.container("store-graph-embeddings")
                    .with_image(images.trustgraph)
                    .with_command([
                        "ge-write-qdrant",
                        "-p",
                        url.pulsar,
                        "-t",
                        url.qdrant,
                    ])
                    .with_limits("0.5", "128M")
                    .with_reservations("0.1", "128M");

            local containerSet = engine.containers(
                "store-graph-embeddings", [ container ]
            );

            engine.resources([
                containerSet,
            ])

    },

    "query-graph-embeddings" +: {
    
        create:: function(engine)

            local container =
                engine.container("query-graph-embeddings")
                    .with_image(images.trustgraph)
                    .with_command([
                        "ge-query-qdrant",
                        "-p",
                        url.pulsar,
                        "-t",
                        url.qdrant,
                    ])
                    .with_limits("0.5", "128M")
                    .with_reservations("0.1", "128M");

            local containerSet = engine.containers(
                "query-graph-embeddings", [ container ]
            );

            engine.resources([
                containerSet,
            ])

    },

    "store-doc-embeddings" +: {
    
        create:: function(engine)

            local container =
                engine.container("store-doc-embeddings")
                    .with_image(images.trustgraph)
                    .with_command([
                        "de-write-qdrant",
                        "-p",
                        url.pulsar,
                        "-t",
                        url.qdrant,
                    ])
                    .with_limits("0.5", "128M")
                    .with_reservations("0.1", "128M");

            local containerSet = engine.containers(
                "store-doc-embeddings", [ container ]
            );

            engine.resources([
                containerSet,
            ])

    },

    "query-doc-embeddings" +: {
    
        create:: function(engine)

            local container =
                engine.container("query-doc-embeddings")
                    .with_image(images.trustgraph)
                    .with_command([
                        "de-query-qdrant",
                        "-p",
                        url.pulsar,
                        "-t",
                        url.qdrant,
                    ])
                    .with_limits("0.5", "128M")
                    .with_reservations("0.1", "128M");

            local containerSet = engine.containers(
                "query-doc-embeddings", [ container ]
            );

            engine.resources([
                containerSet,
            ])


    }

}

