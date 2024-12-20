local images = import "values/images.jsonnet";

{

    "workbench-ui" +: {
    
        create:: function(engine)

            local container =
                engine.container("workbench-ui")
                    .with_image(images["workbench-ui"])
                    .with_limits("0.1", "256M")
                    .with_reservations("0.1", "256M")
                    .with_port(8888, 8888, "ui");

            local containerSet = engine.containers(
                "workbench-ui", [ container ]
            );

            local service =
                engine.internalService(containerSet)
                .with_port(8888, 8888, "ui");

            engine.resources([
                containerSet,
                service,
            ])

    },

}

