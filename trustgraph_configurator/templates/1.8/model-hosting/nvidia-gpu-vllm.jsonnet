local images = import "values/images.jsonnet";

{

    with:: function(key, value)
        self + {
            ["vllm-service-" + key]:: value,
        },

    "vllm-service-model":: "mistralai/Mistral-7B-Instruct-v0.3",
    "vllm-service-cpus":: "0.5",
    "vllm-service-memory":: "1G",
    "vllm-service-storage":: "50G",
    "vllm-service-hf-token":: null,

    "vllm-service" +: {

        create:: function(engine)

            local vol = engine.volume("vllm-storage")
                .with_size($["vllm-service-storage"]);

            local container =
                engine.container("vllm-service")
                    .with_image(images["vllm-service-nvidia"])
                    .with_command([
                        "--model",
                        $["vllm-service-model"],
                        "--served-model-name",
                        "model",
                        "--host",
                        "0.0.0.0",
                        "--port",
                        "7000",
                    ])
                    .with_runtime("nvidia")
                    .with_environment({
                        VLLM_SKIP_WARMUP: "true",
                    } + (
                        if $["vllm-service-hf-token"] != null
                            then { HF_TOKEN: $["vllm-service-hf-token"] }
                            else {}
                    ))
                    .with_privileged(true)
                    .with_ipc("host")
                    .with_capability("SYS_NICE")
                    .with_limits(
                        $["vllm-service-cpus"], $["vllm-service-memory"]
                    )
                    .with_reservations(
                        $["vllm-service-cpus"], $["vllm-service-memory"]
                    )
                    .with_port(7000, 7000, "vllm")
                    .with_volume_mount(vol, "/root/.cache/huggingface");

            local containerSet = engine.containers(
                "vllm-service", [ container ]
            );

            local service =
                engine.service(containerSet)
                .with_port(7000, 7000, "vllm");

            engine.resources([
                vol,
                containerSet,
                service,
            ])

    },

}
