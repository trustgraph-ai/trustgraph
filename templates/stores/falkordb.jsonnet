local base = import "base/base.jsonnet";
local images = import "values/images.jsonnet";

{

    "falkordb" +: {
    
        create:: function(engine)

            local vol = engine.volume("falkordb").with_size("20G");

            local container =
                engine.container("falkordb")
                    .with_image(images.falkordb)
                    .with_limits("1.0", "768M")
                    .with_reservations("0.5", "768M")
                    .with_port(6379, 6379, "api")
                    .with_port(3000, 3000, "ui")
                    .with_volume_mount(vol, "/data");

            local containerSet = engine.containers(
                "falkordb", [ container ]
            );

            local service =
                engine.service(containerSet)
                .with_port(6379, 6379, "api")
                .with_port(3000, 3000, "ui");

            engine.resources([
                vol,
                containerSet,
                service,
           ])

    },

}

