local base = import "base/base.jsonnet";
local images = import "values/images.jsonnet";

{

    "qdrant" +: {
    
        create:: function(engine)

            local vol = engine.volume("qdrant").with_size("20G");

            local container =
                engine.container("qdrant")
                    .with_image(images.qdrant)
                    .with_limits("1.0", "256M")
                    .with_reservations("0.5", "256M")
                    .with_port(6333, 6333, "api")
                    .with_port(6334, 6334, "api2")
                    .with_volume_mount(vol, "/qdrant/storage");

            local containerSet = engine.containers(
                "qdrant", [ container ]
            );

            engine.resources([
                vol,
                containerSet,
            ])

    },

}

