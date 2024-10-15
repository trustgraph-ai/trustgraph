local base = import "base/base.jsonnet";
local images = import "values/images.jsonnet";

{

    etcd +: {
    
        create:: function(engine)

            local vol = engine.volume("etcd").with_size("20G");

            local container =
                engine.container("etcd")
                    .with_image(images.etcd)
                    .with_command([
                        "etcd",
                        "-advertise-client-urls=http://127.0.0.1:2379",
                        "-listen-client-urls",
                        "http://0.0.0.0:2379",
                        "--data-dir",
                        "/etcd",
                    ])
                    .with_environment({
                        ETCD_AUTO_COMPACTION_MODE: "revision",
                        ETCD_AUTO_COMPACTION_RETENTION: "1000",
                        ETCD_QUOTA_BACKEND_BYTES: "4294967296",
                        ETCD_SNAPSHOT_COUNT: "50000"
                    })
                    .with_limits("1.0", "128M")
                    .with_reservations("0.25", "128M")
                    .with_port(2379, 2379, "api")
                    .with_volume_mount(vol, "/etcd");

            local containerSet = engine.containers(
                "etcd", [ container ]
            );

            local service =
                engine.service(containerSet)
                .with_port(2379, 2379, "api");

            engine.resources([
                vol,
                containerSet,
                service,
            ])

    },

    mino +: {
    
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
                    .with_port(9001, 9001, "api")
                    .with_volume_mount(vol, "/minio_data");

            local containerSet = engine.containers(
                "etcd", [ container ]
            );

            local service =
                engine.service(containerSet)
                .with_port(9001, 9001, "api");

            engine.resources([
                vol,
                containerSet,
                service,
            ])

    },

    milvus +: {
    
        create:: function(engine)

            local vol = engine.volume("milvus").with_size("20G");

            local container =
                engine.container("milvus")
                    .with_image(images.milvus)
                    .with_command([
                        "milvus", "run", "standalone"
                    ])
                    .with_environment({
                        ETCD_ENDPOINTS: "etcd:2379",
                        MINIO_ADDRESS: "minio:9000",
                    })
                    .with_limits("1.0", "256M")
                    .with_reservations("0.5", "256M")
                    .with_port(9091, 9091, "api")
                    .with_port(19530, 19530, "api2")
                    .with_volume_mount(vol, "/var/lib/milvus");

            local containerSet = engine.containers(
                "milvus", [ container ]
            );

            local service =
                engine.service(containerSet)
                .with_port(9091, 9091, "api")
                .with_port(19530, 19530, "api2");

            engine.resources([
                vol,
                containerSet,
                service,
            ])

    },

}
