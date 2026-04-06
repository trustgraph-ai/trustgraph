local base = import "base/base.jsonnet";
local images = import "values/images.jsonnet";

{

    with:: function(key, value)
        self + {
            ["vllm-service-" + key]:: value,
        },

    "vllm-service-model":: "mistralai/Mistral-7B-Instruct-v0.3",
    "vllm-service-cpus":: "0.5",
    "vllm-service-memory":: "1G",

    "vllm-service" +: {
    
        create:: function(engine)

            local vol = engine.volume("vllm-storage").with_size("50G");

            local container =
                engine.container("vllm-service")
                    .with_image(images["vllm-service-nvidia"])
                    .with_command([
                        "--model",
                        $["vllm-service-model"],
                        "--port",
                        "8899",
                    ])
                    .with_runtime("nvidia")
                    .with_environment({
                        VLLM_SKIP_WARMUP: "true",
                        HUGGING_FACE_HUB_TOKEN: $["hf-token"],
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
