local images = import "values/images.jsonnet";

{

    with:: function(key, value)
        self + {
            ["vllm-service-" + key]:: value,
        },

    "vllm-service-model":: "mistralai/Mistral-Nemo-Instruct-2407",
    "vllm-service-cpus":: "32.0",
    "vllm-service-memory":: "48G",
    "vllm-service-storage":: "48G",
    "vllm-service-tokenizer-mode":: "mistral",
    "vllm-service-datatype":: "float16",
    "vllm-service-quantization":: "woq_int4",
    "vllm-service-hf-token":: null,
    "vllm-service-max-model-len":: 8192,
    "vllm-service-max-num-seqs":: 16,

    "vllm-service" +: {
    
        create:: function(engine)

            local vol = engine.volume("vllm-storage")
                .with_size($["vllm-service-storage"]);

            local container =
                engine.container("vllm-service")
                    .with_image(images["vllm-service-intel-battlemage"])
                    .with_entrypoint("")  // Clear default entrypoint
                    .with_command([
                        "python",
                        "-m",
                        "ipex_llm.vllm.xpu.entrypoints.openai.api_server",
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
                        "--load-in-low-bit",
                        $["vllm-service-quantization"],
                        "--trust-remote-code",
                        "--tokenizer-mode",
                        $["vllm-service-tokenizer-mode"],
                        "--disable-sliding-window",
                    ])
                    .with_environment({
                        VLLM_WORKER_MULTIPROC_METHOD: "spawn",
                        SYCL_PI_LEVEL_ZERO_USE_IMMEDIATE_COMMANDLISTS: "1",
                    } + (
                        if $["vllm-service-hf-token"] != null
                            then { HF_TOKEN: $["vllm-service-hf-token"] }
                            else {}
                    ))
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
