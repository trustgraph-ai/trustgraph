local base = import "base/base.jsonnet";
local images = import "values/images.jsonnet";

{

    "pulsar" +: {

        create:: function(engine)

// FIXME: Should persist something?
//            local volume = engine.volume(...)

            local container =
                engine.container("pulsar")
                    .with_image(images.pulsar_manager)
                    .with_environment({
                        SPRING_CONFIGURATION_FILE: "/pulsar-manager/pulsar-manager/application.properties",
                    })
                    .with_limits("0.5", "1.4G")
                    .with_reservations("0.1", "1.4G")
                    .with_port(9527, 9527, "api")
                    .with_port(7750, 7750, "api2");

            local containerSet = engine.containers(
                "pulsar", [ container ]
            );

            local service =
                engine.service(containerSet)
                .with_port(9527, 9527, "api")
                .with_port(7750, 7750, "api2);

            engine.resources([
                containerSet,
                service,
            ])

    }

}

