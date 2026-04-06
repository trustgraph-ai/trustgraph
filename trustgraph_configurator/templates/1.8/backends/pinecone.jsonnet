local images = import "values/images.jsonnet";

{

    "pinecone" +: {
    
        create:: function(engine)

            local container =
                engine.container("pinecone")
                    .with_image(images.pinecone)
                    .with_environment({

                        PORT: "5080",

                        INDEX_TYPE: "serverless",

                        // Dimension is fixed, 384 is right for miniLM
                        // sentence embedding
                        DIMENSION: 384,

                        METRIC: "cosine"

                    })
                    .with_limits("1.0", "256M")
                    .with_reservations("0.5", "256M")
                    .with_port(5080, 5080, "api");

            local containerSet = engine.containers(
                "pinecone", [ container ]
            );

            local service =
                engine.service(containerSet)
                .with_port(5080, 5080, "api");

            engine.resources([
                containerSet,
                service,
            ])

    },

}

