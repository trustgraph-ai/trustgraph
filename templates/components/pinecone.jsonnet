local base = import "base/base.jsonnet";
local images = import "values/images.jsonnet";
local url = import "values/url.jsonnet";
local cassandra_hosts = "cassandra";

{

    "pinecone-cloud":: "aws",
    "pinecone-region":: "us-east-1",

    "store-graph-embeddings" +: {
    
        create:: function(engine)

            local envSecrets = engine.envSecrets("pinecone-api-key")
                .with_env_var("PINECONE_API_KEY", "pinecone-api-key");

            local container =
                engine.container("store-graph-embeddings")
                    .with_image(images.trustgraph)
                    .with_command([
                        "ge-write-pinecone",
                        "-p",
                        url.pulsar,
                    ])
                    .with_env_var_secrets(envSecrets)
                    .with_limits("0.5", "128M")
                    .with_reservations("0.1", "128M");

            local containerSet = engine.containers(
                "store-graph-embeddings", [ container ]
            );

            local service =
                engine.internalService(containerSet)
                .with_port(8080, 8080, "metrics");

            engine.resources([
                envSecrets,
                containerSet,
                service,
            ])

    },

    "query-graph-embeddings" +: {
    
        create:: function(engine)

            local envSecrets = engine.envSecrets("pinecone-api-key")
                .with_env_var("PINECONE_API_KEY", "pinecone-api-key");

            local container =
                engine.container("query-graph-embeddings")
                    .with_image(images.trustgraph)
                    .with_command([
                        "ge-query-pinecone",
                        "-p",
                        url.pulsar,
                    ])
                    .with_env_var_secrets(envSecrets)
                    .with_limits("0.5", "128M")
                    .with_reservations("0.1", "128M");

            local containerSet = engine.containers(
                "query-graph-embeddings", [ container ]
            );

            local service =
                engine.internalService(containerSet)
                .with_port(8080, 8080, "metrics");

            engine.resources([
                envSecrets,
                containerSet,
                service,
            ])

    },

    "store-doc-embeddings" +: {
    
        create:: function(engine)

            local envSecrets = engine.envSecrets("pinecone-api-key")
                .with_env_var("PINECONE_API_KEY", "pinecone-api-key");

            local container =
                engine.container("store-doc-embeddings")
                    .with_image(images.trustgraph)
                    .with_command([
                        "de-write-pinecone",
                        "-p",
                        url.pulsar,
                    ])
                    .with_env_var_secrets(envSecrets)
                    .with_limits("0.5", "128M")
                    .with_reservations("0.1", "128M");

            local containerSet = engine.containers(
                "store-doc-embeddings", [ container ]
            );

            local service =
                engine.internalService(containerSet)
                .with_port(8080, 8080, "metrics");

            engine.resources([
                envSecrets,
                containerSet,
                service,
            ])

    },

    "query-doc-embeddings" +: {
    
        create:: function(engine)

            local envSecrets = engine.envSecrets("pinecone-api-key")
                .with_env_var("PINECONE_API_KEY", "pinecone-api-key");

            local container =
                engine.container("query-doc-embeddings")
                    .with_image(images.trustgraph)
                    .with_command([
                        "de-query-pinecone",
                        "-p",
                        url.pulsar,
                    ])
                    .with_env_var_secrets(envSecrets)
                    .with_limits("0.5", "128M")
                    .with_reservations("0.1", "128M");

            local containerSet = engine.containers(
                "query-doc-embeddings", [ container ]
            );

            local service =
                engine.internalService(containerSet)
                .with_port(8080, 8080, "metrics");

            engine.resources([
                envSecrets,
                containerSet,
                service,
            ])


    }

}

