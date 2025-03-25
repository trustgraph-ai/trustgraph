local images = import "values/images.jsonnet";
local url = import "values/url.jsonnet";

{

    "pdf-decoder" +: {
    
        create:: function(engine)

            local container =
                engine.container("pdf-ocr")
                    .with_image(images.trustgraph_ocr)
                    .with_command([
                        "pdf-ocr",
                        "-p",
                        url.pulsar,
                    ])
                    .with_limits("1.0", "512M")
                    .with_reservations("0.1", "512M");

            local containerSet = engine.containers(
                "pdf-ocr", [ container ]
            );

            local service =
                engine.internalService(containerSet)
                .with_port(8080, 8080, "metrics");

            engine.resources([
                containerSet,
                service,
            ])

    },

}

