local images = import "values/images.jsonnet";

{

    "qdrant" +: {

        // Memory settings (can be overridden by memory-profile)
        "memory-limit":: "1024M",
        "memory-reservation":: "1024M",

        // Mmap settings for low-memory mode (trades latency for memory)
        // Set to null to disable, or string value to enable
        "memmap-threshold-kb":: null,
        "on-disk-payload":: null,

        create:: function(engine)

            // Capture memory settings into locals
            local memLimit = self["memory-limit"];
            local memReserv = self["memory-reservation"];
            local mmapThreshold = self["memmap-threshold-kb"];
            local onDiskPayload = self["on-disk-payload"];

            local vol = engine.volume("qdrant").with_size("20G");

            // Build environment with optional mmap settings
            local baseEnv = {};
            local env = baseEnv
                + (if mmapThreshold != null then {
                    QDRANT__STORAGE__MEMMAP_THRESHOLD_KB: mmapThreshold,
                } else {})
                + (if onDiskPayload != null then {
                    QDRANT__STORAGE__ON_DISK_PAYLOAD: onDiskPayload,
                } else {});

            local container =
                engine.container("qdrant")
                    .with_image(images.qdrant)
                    .with_limits("1.0", memLimit)
                    .with_reservations("0.5", memReserv)
                    .with_port(6333, 6333, "api")
                    .with_port(6334, 6334, "api2")
                    .with_volume_mount(vol, "/qdrant/storage")
                    + (if std.length(env) > 0 then {
                        environment+: env,
                    } else {});

            local containerSet = engine.containers(
                "qdrant", [ container ]
            );

            local service =
                engine.service(containerSet)
                .with_port(6333, 6333, "api")
                .with_port(6334, 6334, "api2");

            engine.resources([
                vol,
                containerSet,
                service,
            ])

    },

}
