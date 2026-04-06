local images = import "values/images.jsonnet";
local url = import "values/url.jsonnet";

{

    // Invalid, but at least means the rev-gateway won't connect to anything
    // it shouldn't.
    "rev-gateway-token":: "INVALID_TOKEN",
    "rev-gateway-uri":: "wss://127.0.0.1/api/v1/relay?token=" + $["rev-gateway-token"],

    "rev-gateway" +: {
    
        create:: function(engine)

            local envSecrets = engine.envSecrets("rev-gateway-secret")
                .with_env_var("REV_GATEWAY_SECRET", "rev-gateway-secret");

            local container =
                engine.container("api-gateway")
                    .with_image(images.trustgraph_flow)
                    .with_command([
                        "rev-gateway",
                        "-p",
                        url.pulsar,
                        "--websocket-uri",
                        std.toString($["rev-gateway-uri"]),
                        "--log-level",
                        $["log-level"],
                    ])
                    .with_env_var_secrets(envSecrets)
                    .with_limits("0.5", "256M")
                    .with_reservations("0.1", "256M")
                    .with_port(8000, 8000, "metrics")
                    .with_port(port, port, "api");

            local containerSet = engine.containers(
                "api-gateway", [ container ]
            );

            local service =
                engine.internalService(containerSet)
                .with_port(8000, 8000, "metrics")
                .with_port(port, port, "api");

            engine.resources([
                envSecrets,
                containerSet,
                service,
            ])

    },

}

