local images = import "values/images.jsonnet";

{

    with:: function(key, value)
        self + {
            ["vllm-service-" + key]:: value,
        },

    "vllm-service-model":: "teknium/OpenHermes-2.5-Mistral-7B",
    "vllm-service-cpus":: "64.0",
    "vllm-service-memory":: "64G",
    "vllm-service-storage":: "50G",
    "vllm-service-tensor-parallel-size":: 8,
    "vllm-service-hf-token":: null,

    "vllm-service" +: {

        create:: function(engine)

            local vol = engine.volume("vllm-storage")
                .with_size($["vllm-service-storage"]);

            local container =
                engine.container("vllm-service")
                    .with_image(images["vllm-service-gaudi"])
                    .with_command([
                        "--model",
                        $["vllm-service-model"],
                        "--served-model-name",
                        "model",
                        "--host",
                        "0.0.0.0",
                        "--port",
                        "7000",
                        "--tensor-parallel-size",
                        std.toString($["vllm-service-tensor-parallel-size"]),
                    ])
                    .with_runtime("habana")
                    .with_environment({
                        VLLM_SKIP_WARMUP: "true",
                        HABANA_VISIBLE_DEVICES: "all",
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
