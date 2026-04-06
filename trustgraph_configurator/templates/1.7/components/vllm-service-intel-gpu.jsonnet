local base = import "base/base.jsonnet";
local images = import "values/images.jsonnet";

{

    with:: function(key, value)
        self + {
            ["vllm-service-" + key]:: value,
        },

    "vllm-service-model":: "teknium/OpenHermes-2.5-Mistral-7B",
    "vllm-service-cpus":: "8.0",
    "vllm-service-memory":: "16G",

    "vllm-service" +: {
    
        create:: function(engine)

            local vol = engine.volume("vllm-storage").with_size("20G");

            local container =
                engine.container("vllm-service")
                    .with_image(images["vllm-service-intel-xpu"])
                    .with_command([
                        "python",
                        "-m",
                        "vllm.entrypoints.openai.api_server",
                        "--model",
                        $["vllm-service-model"],
                        "--dtype=float16",
                        "--device=xpu",
                        "--enforce-eager",
                        "--port",
                        "8899",
                        "--block-size",
                        "64",
                        "--gpu-memory-util",
                        "0.85",
                        "--trust-remote-code",
                        "--disable-sliding-window",
                    ])
                    .with_environment({
                        HF_TOKEN: $["hf-token"],
                        VLLM_USE_V1: "1",
                        W_LONG_MAX_MODEL_LEN: "1",
                        VLLM_WORKER_MULTIPROC_METHOD: "spawn",
                    })
                    .with_privileged(true)
                    .with_device("/dev/dri", "/dev/dri")
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
