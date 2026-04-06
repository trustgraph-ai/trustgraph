local images = import "values/images.jsonnet";

{

    with:: function(key, value)
        self + {
            ["vllm-service-" + key]:: value,
        },

    "vllm-service-model":: "teknium/OpenHermes-2.5-Mistral-7B",
    "vllm-service-cpus":: "8.0",
    "vllm-service-memory":: "16G",
    "vllm-service-storage":: "20G",
    "vllm-service-datatype":: "float16",
    "vllm-service-max-model-len":: 4096,
    "vllm-service-max-num-seqs":: 16,
    "vllm-service-hf-token":: null,

    "vllm-service" +: {

        create:: function(engine)

            local vol = engine.volume("vllm-storage")
                .with_size($["vllm-service-storage"]);

            local container =
                engine.container("vllm-service")
                    .with_image(images["vllm-service-intel-xpu"])
                    .with_command([
                        "python",
                        "-m",
                        "vllm.entrypoints.openai.api_server",
                        "--model",
                        $["vllm-service-model"],
                        "--served-model-name",
                        "model",
                        "--host",
                        "0.0.0.0",
                        "--port",
                        "7000",
                        "--device",
                        "xpu",
                        "--dtype",
                        $["vllm-service-datatype"],
                        "--enforce-eager",
                        "--max-model-len",
                        std.toString($["vllm-service-max-model-len"]),
                        "--max-num-seqs",
                        std.toString($["vllm-service-max-num-seqs"]),
                        "--block-size",
                        "64",
                        "--gpu-memory-util",
                        "0.85",
                        "--trust-remote-code",
                        "--disable-sliding-window",
                    ])
                    .with_environment({
                        VLLM_USE_V1: "1",
                        VLLM_WORKER_MULTIPROC_METHOD: "spawn",
                    } + (
                        if $["vllm-service-hf-token"] != null
                            then { HF_TOKEN: $["vllm-service-hf-token"] }
                            else {}
                    ))
                    .with_privileged(true)
                    .with_device("/dev/dri", "/dev/dri")
                    .with_ipc("host")
                    .with_group("video")
                    .with_group("render")
                    .with_capability("SYS_NICE")
                    .with_limits(
                        $["vllm-service-cpus"], $["vllm-service-memory"]
                    )
                    .with_reservations(
                        $["vllm-service-cpus"], $["vllm-service-memory"]
                    )
                    .with_port(7000, 7000, "vllm")
                    .with_bind_mount("/dev/dri/by-path", "/dev/dri/by-path")
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
