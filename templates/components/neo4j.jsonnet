local base = import "base/base.jsonnet";
local images = import "values/images.jsonnet";
local url = import "values/url.jsonnet";
local neo4j = import "stores/neo4j.jsonnet";

neo4j + {

    "neo4j-url":: "bolt://neo4j:7687",

    "store-triples" +: {
    
        create:: function(engine)

            local container =
                engine.container("store-triples")
                    .with_image(images.trustgraph)
                    .with_command([
                        "triples-write-neo4j",
                        "-p",
                        url.pulsar,
                        "-g",
                        $["neo4j-url"],
                    ])
                    .with_limits("0.5", "128M")
                    .with_reservations("0.1", "128M");

            local containerSet = engine.containers(
                "store-triples", [ container ]
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
                        "triples-query-neo4j",
                        "-p",
                        url.pulsar,
                        "-g",
                        $["neo4j-url"],
                    ])
                    .with_limits("0.5", "128M")
                    .with_reservations("0.1", "128M");

            local containerSet = engine.containers(
                "query-triples", [ container ]
            );

            engine.resources([
                containerSet,
            ])


    }

}

