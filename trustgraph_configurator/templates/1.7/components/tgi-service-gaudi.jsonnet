local base = import "base/base.jsonnet";
local images = import "values/images.jsonnet";

{

    with:: function(key, value)
        self + {
            ["tgi-service-" + key]:: value,
        },

    "tgi-service-model":: "meta-llama/Llama-3.3-70B-Instruct",
    "tgi-service-cpus":: "64.0",
    "tgi-service-memory":: "64G",

    "tgi-service" +: {
    
        create:: function(engine)

            local vol = engine.volume("tgi-storage").with_size("50G");

            local container =
                engine.container("tgi-service")
                    .with_image(images["tgi-service-gaudi"])
                    .with_command([
                        "--model-id",
                        $["tgi-service-model"],
                        "--sharded",
                        "true",
                        "--num-shard",
                        "8",
                        "--max-input-tokens",
                        "4096",
                        "--max-total-tokens",
                        "4096",
                        "--max-batch-size",
                        "128",
//                        "--max-batch-prefill-tokens",
//                        "16384",
                        "--max-waiting-tokens",
                        "7",
//                        "--waiting-served-ratio",
//                        "1.2",
                        "--max-concurrent-requests",
                        "512",
                        "--cuda-graphs",
                        "0",
                        "--port",
                        "8899"
                    ])
                    .with_runtime("habana")
                    .with_environment({
                        HABANA_VISIBLE_DEVICES: "all",
                        OMPI_MCA_btl_vader_single_copy_mechanism: "none",
                        HF_TOKEN: $["hf-token"],
                        ENABLE_HPU_GRAPH: 'true',
                        LIMIT_HPU_GRAPH: 'true',
                        USE_FLASH_ATTENTION: 'true',
                        FLASH_ATTENTION_RECOMPUTE: 'true',
//                        PT_HPU_ENABLE_LAZY_COLLECTIVES: 'true',
//                        PREFILL_BATCH_BUCKET_SIZE: "1",
//                        BATCH_BUCKET_SIZE: "1",

                    })
                    .with_ipc("host")
                    .with_capability("SYS_NICE")
                    .with_limits(
                        $["tgi-service-cpus"], $["tgi-service-memory"]
                    )
                    .with_reservations(
                        $["tgi-service-cpus"], $["tgi-service-memory"]
                    )
                    .with_port(8899, 8899, "tgi")
                    .with_volume_mount(vol, "/data");

            local containerSet = engine.containers(
                "tgi-service", [ container ]
            );

            local service =
                engine.service(containerSet)
                .with_port(8899, 8899, "tgi");

            engine.resources([
                vol,
                containerSet,
                service,
            ])

    },

}

