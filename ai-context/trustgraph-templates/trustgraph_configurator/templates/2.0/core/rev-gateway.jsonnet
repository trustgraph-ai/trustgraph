local images = import "values/images.jsonnet";
local url = import "values/url.jsonnet";

{

    "rev-gateway" +: {

        // Invalid, but at least means the rev-gateway won't connect to anything
        // it shouldn't.
        token:: "INVALID_TOKEN",
        uri:: "wss://127.0.0.1/api/v1/relay?token=" + self.token,
        "cpu-limit":: "0.5",
        "cpu-reservation":: "0.1",
        "memory-limit":: "256M",
        "memory-reservation":: "256M",

        create:: function(engine)

            local uri = self.uri;
            local memoryLimit = self["memory-limit"];
            local memoryReservation = self["memory-reservation"];

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
                        std.toString(uri),
                        "--log-level",
                        $["log-level"],
                    ])
                    .with_env_var_secrets(envSecrets)
                    .with_limits(self["cpu-limit"], memoryLimit)
                    .with_reservations(self["cpu-reservation"], memoryReservation)
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

