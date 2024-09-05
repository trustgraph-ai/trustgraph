local base = import "base/base.jsonnet";
local images = import "values/images.jsonnet";
local url = import "values/url.jsonnet";
local cassandra_hosts = "cassandra";
local cassandra = import "stores/cassandra.jsonnet";

cassandra + {

    "store-triples" +: {
    
        create:: function(engine)

            local container =
                engine.container("store-triples")
                    .with_image(images.trustgraph)
                    .with_command([
                        "triples-write-cassandra",
                        "-p",
                        url.pulsar,
                        "-g",
                        cassandra_hosts,
                    ])
                    .with_limits("0.5", "128M")
                    .with_reservations("0.1", "128M");

            local containerSet = engine.containers(
                "stop-triples", [ container ]
            );

            engine.resources([
                containerSet,
            ])

    },

    "query-triples" +: {
    
        create:: function(engine)

            local container =
                engine.container("query-triples")
                    .with_image(images.trustgraph)
                    .with_command([
                        "triples-query-cassandra",
                        "-p",
                        url.pulsar,
                        "-g",
                        cassandra_hosts,
                    ])
                    .with_limits("0.5", "512M")
                    .with_reservations("0.1", "512M");

            local containerSet = engine.containers(
                "query-triples", [ container ]
            );

            engine.resources([
                containerSet,
            ])

    }

}

