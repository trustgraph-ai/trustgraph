local images = import "values/images.jsonnet";

{

    with:: function(key, value)
        self + {
            ["tgi-service-" + key]:: value,
        },

    "tgi-service-model":: "meta-llama/Llama-3.3-70B-Instruct",
    "tgi-service-cpus":: "64.0",
    "tgi-service-memory":: "64G",
    "tgi-service-storage":: "50G",
    "tgi-service-num-shard":: 8,
    "tgi-service-max-input-tokens":: 4096,
    "tgi-service-max-total-tokens":: 4096,
    "tgi-service-max-batch-size":: 128,
    "tgi-service-max-concurrent-requests":: 512,
    "tgi-service-hf-token":: null,

    "tgi-service" +: {

        create:: function(engine)

            local vol = engine.volume("tgi-storage")
                .with_size($["tgi-service-storage"]);

            local container =
                engine.container("tgi-service")
                    .with_image(images["tgi-service-gaudi"])
                    .with_command([
                        "--model-id",
                        $["tgi-service-model"],
                        "--hostname",
                        "0.0.0.0",
                        "--port",
                        "7000",
                        "--sharded",
                        "true",
                        "--num-shard",
                        std.toString($["tgi-service-num-shard"]),
                        "--max-input-tokens",
                        std.toString($["tgi-service-max-input-tokens"]),
                        "--max-total-tokens",
                        std.toString($["tgi-service-max-total-tokens"]),
                        "--max-batch-size",
                        std.toString($["tgi-service-max-batch-size"]),
                        "--max-waiting-tokens",
                        "7",
                        "--max-concurrent-requests",
                        std.toString($["tgi-service-max-concurrent-requests"]),
                        "--cuda-graphs",
                        "0",
                    ])
                    .with_runtime("habana")
                    .with_environment({
                        HABANA_VISIBLE_DEVICES: "all",
                        OMPI_MCA_btl_vader_single_copy_mechanism: "none",
                        ENABLE_HPU_GRAPH: "true",
                        LIMIT_HPU_GRAPH: "true",
                        USE_FLASH_ATTENTION: "true",
                        FLASH_ATTENTION_RECOMPUTE: "true",
                    } + (
                        if $["tgi-service-hf-token"] != null
                            then { HF_TOKEN: $["tgi-service-hf-token"] }
                            else {}
                    ))
                    .with_ipc("host")
                    .with_capability("SYS_NICE")
                    .with_limits(
                        $["tgi-service-cpus"], $["tgi-service-memory"]
                    )
                    .with_reservations(
                        $["tgi-service-cpus"], $["tgi-service-memory"]
                    )
                    .with_port(7000, 7000, "tgi")
                    .with_volume_mount(vol, "/root/.cache/huggingface");

            local containerSet = engine.containers(
                "tgi-service", [ container ]
            );

            local service =
                engine.service(containerSet)
                .with_port(7000, 7000, "tgi");

            engine.resources([
                vol,
                containerSet,
                service,
            ])

    },

}

