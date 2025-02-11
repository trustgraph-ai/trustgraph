local base = import "base/base.jsonnet";
local images = import "values/images.jsonnet";

{

    minio +: {
    
        create:: function(engine)

            local vol = engine.volume("minio-data").with_size("20G");

            local container =
                engine.container("minio")
                    .with_image(images.minio)
                    .with_command([
                        "minio",
                        "server",
                        "/minio_data",
                        "--console-address",
                        ":9001",
                    ])
                    .with_environment({
                        MINIO_ROOT_USER: "minioadmin",
                        MINIO_ROOT_PASSWORD: "minioadmin",
                    })
                    .with_limits("0.5", "128M")
                    .with_reservations("0.25", "128M")
                    .with_port(9000, 9000, "api")
                    .with_port(9001, 9001, "console")
                    .with_volume_mount(vol, "/minio_data");

            local containerSet = engine.containers(
                "etcd", [ container ]
            );

            local service =
                engine.service(containerSet)
                .with_port(9000, 9000, "api")
                .with_port(9001, 9001, "console");

            engine.resources([
                vol,
                containerSet,
                service,
            ])

    },

}
