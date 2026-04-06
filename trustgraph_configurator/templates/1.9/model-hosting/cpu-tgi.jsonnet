local images = import "values/images.jsonnet";

{

    with:: function(key, value)
        self + {
            ["tgi-service-" + key]:: value,
        },

    "tgi-service-model":: "teknium/OpenHermes-2.5-Mistral-7B",
    "tgi-service-cpus":: "8.0",
    "tgi-service-memory":: "16G",
    "tgi-service-storage":: "20G",
    "tgi-service-hf-token":: null,

    "tgi-service" +: {

        create:: function(engine)

            local vol = engine.volume("tgi-storage")
                .with_size($["tgi-service-storage"]);

            local container =
                engine.container("tgi-service")
                    .with_image(images["tgi-service-cpu"])
                    .with_command([
                        "--model-id",
                        $["tgi-service-model"],
                        "--hostname",
                        "0.0.0.0",
                        "--port",
                        "7000",
                        "--cuda-graphs",
                        "0",
                    ])
                    .with_environment({
                    } + (
                        if $["tgi-service-hf-token"] != null
                            then { HF_TOKEN: $["tgi-service-hf-token"] }
                            else {}
                    ))
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

