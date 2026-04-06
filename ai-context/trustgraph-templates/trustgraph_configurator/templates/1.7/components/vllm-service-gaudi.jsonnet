local base = import "base/base.jsonnet";
local images = import "values/images.jsonnet";

{

    with:: function(key, value)
        self + {
            ["vllm-service-" + key]:: value,
        },

    "vllm-service-model":: "teknium/OpenHermes-2.5-Mistral-7B",
    "vllm-service-cpus":: "64.0",
    "vllm-service-memory":: "64G",

    "vllm-service" +: {
    
        create:: function(engine)

            local vol = engine.volume("vllm-storage").with_size("50G");

            local container =
                engine.container("vllm-service")
                    .with_image(images["vllm-service-gaudi"])
                    .with_command([
                        "--model",
                        $["vllm-service-model"],
                        "--tensor-parallel-size=8",
                        "--port",
                        "8899",
                    ])
                    .with_runtime("habana")
                    .with_environment({
                        VLLM_SKIP_WARMUP: "true",
                        HUGGING_FACE_HUB_TOKEN: $["hf-token"],
                        HABANA_VISIBLE_DEVICES: "all",
                        VLLM_CACHE_ROOT: "/data",
                    })
                    .with_privileged(true)
                    .with_ipc("host")
                    .with_capability("SYS_NICE")
                    .with_limits(
                        $["vllm-service-cpus"], $["vllm-service-memory"]
                    )
                    .with_reservations(
                        $["vllm-service-cpus"], $["vllm-service-memory"]
                    )
                    .with_port(8899, 8899, "vllm")
                    .with_volume_mount(vol, "/data");

            local containerSet = engine.containers(
                "vllm-service", [ container ]
            );

            local service =
                engine.service(containerSet)
                .with_port(8899, 8899, "vllm");

            engine.resources([
                vol,
                containerSet,
                service,
            ])

    },

}
