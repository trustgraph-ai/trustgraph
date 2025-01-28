local base = import "base/base.jsonnet";
local images = import "values/images.jsonnet";
local url = import "values/url.jsonnet";
local falkordb = import "stores/falkordb.jsonnet";

falkordb + {

    "falkordb-url":: "falkor://falkordb:6379",

    "store-triples" +: {
    
        create:: function(engine)

            local container =
                engine.container("store-triples")
                    .with_image(images.trustgraph_flow)
                    .with_command([
                        "triples-write-falkordb",
                        "-p",
                        url.pulsar,
                        "-g",
                        $["falkordb-url"],
                    ])
                    .with_limits("0.5", "128M")
                    .with_reservations("0.1", "128M");

            local containerSet = engine.containers(
                "store-triples", [ container ]
            );

            local service =
                engine.internalService(containerSet)
                .with_port(8080, 8080, "metrics");

            engine.resources([
                containerSet,
                service,
            ])

    },

    "query-triples" +: {
    
        create:: function(engine)

            local container =
                engine.container("query-triples")
                    .with_image(images.trustgraph_flow)
                    .with_command([
                        "triples-query-falkordb",
                        "-p",
                        url.pulsar,
                        "-g",
                        $["falkordb-url"],
                    ])
                    .with_limits("0.5", "128M")
                    .with_reservations("0.1", "128M");

            local containerSet = engine.containers(
                "query-triples", [ container ]
            );

            local service =
                engine.internalService(containerSet)
                .with_port(8080, 8080, "metrics");

            engine.resources([
                containerSet,
                service,
            ])


    }

}

